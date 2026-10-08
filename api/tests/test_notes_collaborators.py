from datetime import datetime, timezone
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import Node, TaskNote, TaskReport, AuditLog, User, Department, NodeCollaborator, Project
from test_report_lifecycle import setup, switch


def audits(engine):
    with Session(engine) as db:
        return [(a.id,a.action,a.payload) for a in db.scalars(select(AuditLog).order_by(AuditLog.id))]


def test_note_author_revision_noop_and_audit(client,engine):
    nid,_,users=setup(client,engine)
    created=client.post(f'/nodes/{nid}/notes',json={'body':'  筆記  ','attachment_ids':[]})
    assert created.status_code==201
    note=created.json();assert note['body']=='筆記' and note['revision']==1 and note['attachments']==[]
    assert note['author_id']==users['ming'] and note['author_display_name']
    before=audits(engine)
    same=client.patch(f"/notes/{note['id']}",json={'body':'筆記','expected_revision':1})
    assert same.status_code==200 and same.json()['revision']==1 and audits(engine)==before
    changed=client.patch(f"/notes/{note['id']}",json={'body':'修訂','expected_revision':1})
    assert changed.status_code==200 and changed.json()['revision']==2 and changed.json()['edited_at']
    before=audits(engine)
    assert client.patch(f"/notes/{note['id']}",json={'body':'stale','expected_revision':1}).status_code==409
    assert audits(engine)==before
    edit=next(a for a in before if a[1]=='note.update')
    assert edit[2]['before']['body']=='筆記' and edit[2]['after']['body']=='修訂'
    switch(client,'yu')
    assert client.patch(f"/notes/{note['id']}",json={'body':'admin','expected_revision':2}).status_code==403
    assert client.delete(f"/notes/{note['id']}").status_code==405
    assert audits(engine)==before


@pytest.mark.parametrize('change,code',[('readonly',403),('hidden',404),('visible_no_write',403)])
def test_note_edit_rechecks_author_write_permissions(client,engine,change,code):
    nid,_,users=setup(client,engine)
    r=client.post(f'/nodes/{nid}/notes',json={'body':'original'});assert r.status_code==201
    note=r.json()
    with Session(engine) as db:
        if change=='readonly':db.get(User,users['ming']).role='readonly'
        else:
            db.get(Node,nid).owner_user_id=users['yu']
            if change=='visible_no_write':db.get(User,users['ming']).role='project_owner'
        db.commit()
    before=audits(engine)
    assert client.patch(f"/notes/{note['id']}",json={'body':'bad','expected_revision':1}).status_code==code
    assert audits(engine)==before


@pytest.mark.parametrize('payload',[{'body':' '},{'body':'x'*10001},{'body':'x','unknown':1},{'body':'x','attachment_ids':['missing']}])
def test_note_validation_has_no_side_effect(client,engine,payload):
    nid,_,_=setup(client,engine);before=audits(engine)
    assert client.post(f'/nodes/{nid}/notes',json=payload).status_code==422
    with Session(engine) as db:assert list(db.scalars(select(TaskNote)))==[]
    assert audits(engine)==before


def test_collaborators_manager_replace_deduplicate_noop_conflict_revocation(client,engine):
    nid,_,users=setup(client,engine,'yu')
    with Session(engine) as db:
        db.get(Node,nid).owner_user_id=users['yu']
        dept=db.scalars(select(Department).where(Department.organization_id==db.get(Node,nid).organization_id)).first()
        did=dept.id;db.commit()
    initial=client.get(f'/nodes/{nid}/collaborators');assert initial.status_code==200
    assert initial.json()=={'users':[],'departments':[],'revision':0}
    payload={'user_ids':[users['ming'],users['ming']],'department_ids':[did],'expected_revision':0}
    result=client.put(f'/nodes/{nid}/collaborators',json=payload)
    assert result.status_code==200 and result.json()['revision']==1
    assert result.json()['users']==[{'id':users['ming'],'display_name':result.json()['users'][0]['display_name']}]
    before=audits(engine)
    assert client.put(f'/nodes/{nid}/collaborators',json={**payload,'expected_revision':1}).json()['revision']==1
    assert audits(engine)==before
    assert client.put(f'/nodes/{nid}/collaborators',json=payload).status_code==409
    switch(client,'ming')
    assert client.get(f'/nodes/{nid}/collaborators').status_code==200
    assert client.post(f'/nodes/{nid}/notes',json={'body':'collaborator'}).status_code==201
    assert client.put(f'/nodes/{nid}/collaborators',json={**payload,'expected_revision':1}).status_code==403
    switch(client,'yu')
    assert client.put(f'/nodes/{nid}/collaborators',json={'user_ids':[],'department_ids':[],'expected_revision':1}).json()['revision']==2
    switch(client,'ming')
    assert client.get(f'/nodes/{nid}/records').status_code==404
    assert client.get(f'/nodes/{nid}/collaborators').status_code==404


@pytest.mark.parametrize('target',['foreign_user','foreign_department','missing','readonly'])
def test_collaborator_invalid_targets_atomic(client,engine,target):
    nid,_,users=setup(client,engine,'yu')
    with Session(engine) as db:
        org=db.get(Node,nid).organization_id
        foreign=db.scalars(select(User).where(User.organization_id!=org)).first()
        dept=db.scalars(select(Department).where(Department.organization_id!=org)).first()
        value={'foreign_user':foreign.id,'foreign_department':dept.id,'missing':'missing','readonly':users['lin']}[target]
    before=audits(engine)
    payload={'user_ids':[value] if target!='foreign_department' else [],'department_ids':[value] if target=='foreign_department' else [],'expected_revision':0}
    assert client.put(f'/nodes/{nid}/collaborators',json=payload).status_code==422
    assert client.get(f'/nodes/{nid}/collaborators').json()['revision']==0 and audits(engine)==before


def test_records_visible_subtree_hidden_parent_cycle_stable_pages(client,engine):
    nid,pid,users=setup(client,engine)
    stamp=datetime(2026,10,8,tzinfo=timezone.utc)
    with Session(engine) as db:
        root=db.get(Node,nid);org=root.organization_id
        hidden=Node(organization_id=org,project_id=pid,parent_id=nid,kind='task',title='SECRET',owner_user_id=users['yu'])
        db.add(hidden);db.flush()
        child=Node(organization_id=org,project_id=pid,parent_id=hidden.id,kind='task',title='可見孫',owner_user_id=users['ming'])
        db.add(child);db.flush();cid=child.id
        root.parent_id=cid # corrupt physical cycle: traversal must terminate
        for node,body in [(root,'root'),(hidden,'SECRET BODY'),(child,'child')]:
            db.add(TaskNote(organization_id=org,node_id=node.id,body=body,author_id=users['ming'],created_at=stamp))
        db.add(TaskReport(organization_id=org,node_id=cid,result='legacy custom',summary='legacy',submitted_by=users['ming'],submitted_at=stamp))
        db.commit()
    single=client.get(f'/nodes/{nid}/records');assert single.status_code==200
    assert [x['body'] for x in single.json()['items']]==['root']
    items=[];cursor=None
    for _ in range(5):
        params={'scope':'subtree','limit':1}
        if cursor:params['cursor']=cursor
        response=client.get(f'/nodes/{nid}/records',params=params)
        assert response.status_code==200 and 'SECRET' not in response.text
        assert set(response.json())=={'items','next_cursor'}
        items.extend(response.json()['items']);cursor=response.json()['next_cursor']
        if not cursor:break
    assert len(items)==3 and len({(i['type'],i['id']) for i in items})==3
    assert [i['id'] for i in items]==sorted(i['id'] for i in items)
    report=next(i for i in items if i['type']=='report')
    assert report['legacy'] and report['result']=='legacy custom' and report['attachments']==[]
    assert 'username' not in str(items) and 'storage_key' not in str(items)


@pytest.mark.parametrize('params',[{'scope':'bad'},{'limit':0},{'limit':101},{'cursor':'garbage'}])
def test_records_invalid_pagination(client,engine,params):
    nid,_,_=setup(client,engine)
    assert client.get(f'/nodes/{nid}/records',params=params).status_code==422


def test_records_empty_and_cross_company_cursor(client,engine):
    nid,_,_=setup(client,engine)
    empty=client.get(f'/nodes/{nid}/records');assert empty.status_code==200
    assert empty.json()=={'items':[],'next_cursor':None}
    for text in ['one','two']:assert client.post(f'/nodes/{nid}/notes',json={'body':text}).status_code==201
    cursor=client.get(f'/nodes/{nid}/records',params={'limit':1}).json()['next_cursor']
    assert cursor
    client.post('/auth/logout')
    from test_projects_nodes import login
    login(client,org='electronics',username='elaine')
    with Session(engine) as db:
        user=db.scalars(select(User).where(User.username=='elaine')).one()
        other=db.scalars(select(Node).where(Node.organization_id==user.organization_id)).first().id
    assert client.get(f'/nodes/{other}/records',params={'cursor':cursor}).status_code==422



@pytest.mark.parametrize('route', ['notes','collaborators'])
def test_record_writes_audit_failure_rolls_back(client,engine,monkeypatch,route):
    nid,_,users=setup(client,engine,'yu')
    from app.routes import records,collaborators
    def fail(*args,**kwargs):raise RuntimeError('audit unavailable')
    monkeypatch.setattr(records if route=='notes' else collaborators,'log_audit',fail)
    before=audits(engine)
    with pytest.raises(RuntimeError,match='audit unavailable'):
        if route=='notes':client.post(f'/nodes/{nid}/notes',json={'body':'not saved'})
        else:client.put(f'/nodes/{nid}/collaborators',json={'user_ids':[users['ming']],'expected_revision':0})
    with Session(engine) as db:
        assert list(db.scalars(select(TaskNote)))==[]
        assert list(db.scalars(select(NodeCollaborator)))==[]
        assert db.get(Node,nid).collaborators_revision==0
    assert audits(engine)==before


def test_note_cross_company_and_patch_schema(client,engine):
    nid,_,_=setup(client,engine)
    note=client.post(f'/nodes/{nid}/notes',json={'body':'original'}).json()
    before=audits(engine)
    for payload in [{'body':'x'}, {'body':'x','expected_revision':0}, {'body':'x','expected_revision':True},
                    {'body':' ','expected_revision':1}, {'body':'x','expected_revision':1,'attachment_ids':[]}]:
        assert client.patch(f"/notes/{note['id']}",json=payload).status_code==422
    client.post('/auth/logout')
    from test_projects_nodes import login
    login(client,org='electronics',username='elaine')
    assert client.patch(f"/notes/{note['id']}",json={'body':'bad','expected_revision':1}).status_code==404
    assert client.get(f'/nodes/{nid}/collaborators').status_code==404
    assert client.put(f'/nodes/{nid}/collaborators',json={'expected_revision':0}).status_code==404
    assert client.post(f'/nodes/{nid}/notes',json={'body':'bad'}).status_code==404
    assert audits(engine)==before


def test_subtree_excludes_foreign_project_and_company_links(client,engine):
    nid,pid,users=setup(client,engine,'yu')
    with Session(engine) as db:
        root=db.get(Node,nid)
        otherproject=Project(organization_id=root.organization_id,title='another project',owner_user_id=users['yu'])
        db.add(otherproject);db.flush()
        foreignuser=db.scalars(select(User).where(User.organization_id!=root.organization_id)).first()
        foreignproject=db.scalars(select(Project).where(Project.organization_id==foreignuser.organization_id)).first()
        for org,project,owner in [(root.organization_id,otherproject.id,users['yu']),
                                  (foreignuser.organization_id,foreignproject.id,foreignuser.id)]:
            node=Node(organization_id=org,project_id=project,parent_id=nid,kind='task',title='SECRET boundary',owner_user_id=owner)
            db.add(node);db.flush()
            db.add(TaskNote(organization_id=org,node_id=node.id,body='SECRET body',author_id=owner))
        db.commit()
    result=client.get(f'/nodes/{nid}/records',params={'scope':'subtree'})
    assert result.status_code==200 and result.json()=={'items':[],'next_cursor':None}
