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
