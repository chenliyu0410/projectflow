"""Optional dedicated PostgreSQL integration tests; never use primary or acceptance DB."""
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.database import get_session, sqlalchemy_url
from app.main import create_app
from app.models import AuditLog, Node, TaskReport, User, Project
from app.seed import seed_demo_data


def test_postgresql_report_transactions_serialize_real_api_requests(monkeypatch):
    url=os.environ.get('P2B_TEST_DATABASE_URL')
    if not url:
        pytest.skip('Dedicated p2b_test PostgreSQL URL required')
    parsed=make_url(url)
    assert parsed.get_backend_name()=='postgresql' and parsed.database.startswith('p2b_test_')
    assert os.environ.get('PF_ACCEPTANCE_MODE')=='true'
    monkeypatch.setenv('DATABASE_URL',url)
    command.upgrade(Config('api/alembic.ini'),'head')
    engine=create_engine(sqlalchemy_url(url),pool_size=5)
    with Session(engine) as db:
        seed_demo_data(db);db.commit()
        member=db.scalars(select(User).where(User.username=='ming')).one()
        project=db.scalars(select(Project).where(Project.organization_id==member.organization_id)).first()
        node=Node(organization_id=member.organization_id,project_id=project.id,kind='task',title=f'PG lifecycle {uuid4()}',owner_user_id=member.id)
        db.add(node);db.commit();nid=node.id
    app=create_app()
    def session():
        with Session(engine) as db:yield db
    app.dependency_overrides[get_session]=session
    def login(client,username):
        assert client.post('/auth/login',json={'organization_key':'food','username':username,'password':f'demo-{username}'}).status_code==200
    def race(clients,path,payloads):
        barrier=Barrier(2)
        def at_node_lock(conn,cursor,statement,parameters,context,executemany):
            if 'FROM nodes' in statement and 'FOR UPDATE' in statement:
                barrier.wait(timeout=15)
        event.listen(engine,'before_cursor_execute',at_node_lock)
        try:
            def invoke(pair):return pair[0].post(path,json=pair[1])
            with ThreadPoolExecutor(max_workers=2) as pool:
                return list(pool.map(invoke,zip(clients,payloads)))
        finally:event.remove(engine,'before_cursor_execute',at_node_lock)
    payload={'result':'達成','summary':'PG parallel','finished_on':'2026-10-08'}
    try:
        with TestClient(app) as one,TestClient(app) as two:
            login(one,'ming');login(two,'ming')
            submitted=race([one,two],f'/nodes/{nid}/reports',[payload,payload])
            assert sorted(r.status_code for r in submitted)==[201,409]
            rid=next(r.json()['id'] for r in submitted if r.status_code==201)
            with Session(engine) as db:
                assert db.get(Node,nid).status=='review'
                assert len(list(db.scalars(select(TaskReport).where(TaskReport.node_id==nid))))==1
                assert len(list(db.scalars(select(AuditLog).where(AuditLog.node_id==nid))))==1
            login(one,'yu');login(two,'yu')
            approved=race([one,two],f'/reports/{rid}/review',[{'decision':'approved'}]*2)
            assert sorted(r.status_code for r in approved)==[200,409]
            with Session(engine) as db:
                assert db.get(Node,nid).status=='done' and db.get(TaskReport,rid).status=='approved'
                assert len(list(db.scalars(select(AuditLog).where(AuditLog.node_id==nid,AuditLog.action=='report.approve'))))==1
            assert one.post(f'/nodes/{nid}/lifecycle',json={'action':'reopen','reason':'next version'}).status_code==200
            login(one,'ming')
            second=one.post(f'/nodes/{nid}/reports',json=payload)
            assert second.status_code==201 and second.json()['version']==2
            login(one,'yu')
            rejected=race([one,two],f"/reports/{second.json()['id']}/review",[{'decision':'rejected','comment':'補充'}]*2)
            assert sorted(r.status_code for r in rejected)==[200,409]
            with Session(engine) as db:
                assert db.get(Node,nid).status=='doing'
                assert db.get(TaskReport,second.json()['id']).status=='rejected'
                assert len(list(db.scalars(select(AuditLog).where(AuditLog.node_id==nid,AuditLog.action=='report.reject'))))==1
                assert len(list(db.scalars(select(TaskReport).where(TaskReport.node_id==nid))))==2
    finally:
        app.dependency_overrides.clear();engine.dispose()


def test_postgresql_notes_and_collaborators_prevent_lost_updates(monkeypatch):
    from app.models import TaskNote, NodeCollaborator
    url=os.environ.get('P2B_TEST_DATABASE_URL')
    if not url:pytest.skip('Dedicated p2b_test PostgreSQL URL required')
    parsed=make_url(url)
    assert parsed.get_backend_name()=='postgresql' and parsed.database.startswith('p2b_test_')
    assert os.environ.get('PF_ACCEPTANCE_MODE')=='true'
    monkeypatch.setenv('DATABASE_URL',url)
    command.upgrade(Config('api/alembic.ini'),'head')
    engine=create_engine(sqlalchemy_url(url),pool_size=5)
    with Session(engine) as db:
        seed_demo_data(db);db.commit()
        users={u.username:u for u in db.scalars(select(User))}
        member=users['ming'];uid=member.id;other=users['chen'].id
        project=db.scalars(select(Project).where(Project.organization_id==member.organization_id)).first()
        node=Node(organization_id=member.organization_id,project_id=project.id,kind='task',title=f'PG records {uuid4()}',owner_user_id=uid)
        db.add(node);db.commit();nid=node.id
    app=create_app()
    def session():
        with Session(engine) as db:yield db
    app.dependency_overrides[get_session]=session
    def login(client,username):
        assert client.post('/auth/login',json={'organization_key':'food','username':username,'password':f'demo-{username}'}).status_code==200
    def race(clients,method,path,payloads):
        barrier=Barrier(2)
        def at_lock(conn,cursor,statement,parameters,context,executemany):
            if 'FROM nodes' in statement and 'FOR UPDATE' in statement:barrier.wait(timeout=15)
        event.listen(engine,'before_cursor_execute',at_lock)
        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                return list(pool.map(lambda pair: pair[0].request(method,path,json=pair[1]),zip(clients,payloads)))
        finally:event.remove(engine,'before_cursor_execute',at_lock)
    try:
        with TestClient(app) as one,TestClient(app) as two:
            login(one,'ming');login(two,'ming')
            created=one.post(f'/nodes/{nid}/notes',json={'body':'original'})
            assert created.status_code==201
            note_id=created.json()['id']
            responses=race([one,two],'PATCH',f'/notes/{note_id}',[
                {'body':'writer one','expected_revision':1},{'body':'writer two','expected_revision':1}])
            assert sorted(r.status_code for r in responses)==[200,409]
            winner=next(r.json()['body'] for r in responses if r.status_code==200)
            with Session(engine) as db:
                note=db.get(TaskNote,note_id)
                assert note.body==winner and note.revision==2
                events=list(db.scalars(select(AuditLog).where(AuditLog.node_id==nid,AuditLog.action=='note.update')))
                assert len(events)==1 and events[0].payload['after']['body']==winner
            login(one,'yu');login(two,'yu')
            responses=race([one,two],'PUT',f'/nodes/{nid}/collaborators',[
                {'user_ids':[uid],'department_ids':[],'expected_revision':0},
                {'user_ids':[other],'department_ids':[],'expected_revision':0}])
            assert sorted(r.status_code for r in responses)==[200,409]
            winner=next(r.json()['users'][0]['id'] for r in responses if r.status_code==200)
            with Session(engine) as db:
                assert db.get(Node,nid).collaborators_revision==1
                links=list(db.scalars(select(NodeCollaborator).where(NodeCollaborator.node_id==nid)))
                assert len(links)==1 and links[0].user_id==winner
                assert len(list(db.scalars(select(AuditLog).where(AuditLog.node_id==nid,AuditLog.action=='collaborators.update'))))==1
    finally:
        app.dependency_overrides.clear();engine.dispose()


def test_postgresql_attachment_quota_binding_and_delete_races(monkeypatch,tmp_path):
    import threading
    from sqlalchemy import delete
    from app.models import Attachment,AttachmentQuota,TaskNote
    url=os.environ.get('P2B_TEST_DATABASE_URL')
    if not url:pytest.skip('Dedicated p2b_test PostgreSQL URL required')
    parsed=make_url(url)
    assert parsed.get_backend_name()=='postgresql' and parsed.database.startswith('p2b_test_')
    assert os.environ.get('PF_ACCEPTANCE_MODE')=='true'
    monkeypatch.setenv('DATABASE_URL',url)
    root=tmp_path/'files';root.mkdir()
    monkeypatch.setenv('PF_ATTACHMENT_ROOT',str(root))
    monkeypatch.setenv('PF_ATTACHMENT_QUOTA_BYTES','5')
    command.upgrade(Config('api/alembic.ini'),'head')
    engine=create_engine(sqlalchemy_url(url),pool_size=5)
    with Session(engine) as db:
        seed_demo_data(db);db.commit()
        member=db.scalars(select(User).where(User.username=='ming')).one();org=member.organization_id
        project=db.scalars(select(Project).where(Project.organization_id==org)).first()
        node=Node(organization_id=org,project_id=project.id,kind='task',title=f'PG files {uuid4()}',owner_user_id=member.id)
        db.add(node);db.execute(delete(AttachmentQuota).where(AttachmentQuota.organization_id==org));db.commit();nid=node.id
    app=create_app()
    def session():
        with Session(engine) as db:yield db
    app.dependency_overrides[get_session]=session
    def race(calls,sql_match):
        barrier=Barrier(2);local=threading.local()
        def at_lock(conn,cursor,statement,parameters,context,executemany):
            if sql_match(statement) and not getattr(local,'waited',False):
                local.waited=True;barrier.wait(timeout=15)
        event.listen(engine,'before_cursor_execute',at_lock)
        try:
            with ThreadPoolExecutor(max_workers=2) as pool:return list(pool.map(lambda f:f(),calls))
        finally:event.remove(engine,'before_cursor_execute',at_lock)
    try:
        with TestClient(app) as one,TestClient(app) as two:
            for client in [one,two]:
                assert client.post('/auth/login',json={'organization_key':'food','username':'ming','password':'demo-ming'}).status_code==200
            def upload(client):return client.post(f'/nodes/{nid}/attachments?filename=pg.txt',content=b'hello',headers={'Content-Type':'application/octet-stream'})
            responses=race([lambda:upload(one),lambda:upload(two)],lambda s:'INSERT INTO attachment_quotas' in s)
            assert sorted(r.status_code for r in responses)==[201,413]
            aid=next(r.json()['id'] for r in responses if r.status_code==201)
            with Session(engine) as db:
                assert db.get(AttachmentQuota,org).charged_bytes==5
                assert len(list(db.scalars(select(Attachment).where(Attachment.node_id==nid))))==1
            payload={'result':'達成','summary':'file','finished_on':'2026-10-08','attachment_ids':[aid]}
            responses=race([lambda:one.post(f'/nodes/{nid}/reports',json=payload),lambda:two.delete(f'/attachments/{aid}')],
                           lambda s:'FROM nodes' in s and 'FOR UPDATE' in s)
            assert sorted(r.status_code for r in responses) in [[201,409],[200,422]]
            with Session(engine) as db:
                row=db.get(Attachment,aid)
                assert (row.report_id is not None) != (row.deleted_at is not None)
                assert db.get(AttachmentQuota,org).charged_bytes==5
            monkeypatch.setenv('PF_ATTACHMENT_QUOTA_BYTES','20')
            uploaded=upload(one);assert uploaded.status_code==201
            aid=uploaded.json()['id']
            responses=race([lambda:one.post(f'/nodes/{nid}/notes',json={'body':'one','attachment_ids':[aid]}),
                            lambda:two.post(f'/nodes/{nid}/notes',json={'body':'two','attachment_ids':[aid]})],
                           lambda s:'FROM nodes' in s and 'FOR UPDATE' in s)
            assert sorted(r.status_code for r in responses)==[201,422]
            with Session(engine) as db:
                row=db.get(Attachment,aid)
                assert row.note_id and len(list(db.scalars(select(TaskNote).where(TaskNote.node_id==nid))))==1
                assert db.get(AttachmentQuota,org).charged_bytes==10
    finally:
        app.dependency_overrides.clear();engine.dispose()
