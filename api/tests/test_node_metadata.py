import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import AuditLog, Department, Node, Project, User
from test_projects_nodes import login


def setup_ids(client, engine):
    login(client)
    with Session(engine) as db:
        users = {u.username: u.id for u in db.scalars(select(User))}
        project = db.scalars(select(Project).where(Project.owner_user_id == users['yu'])).one()
        task = db.scalars(select(Node).where(Node.project_id == project.id, Node.kind == 'task')).one()
        dept = db.scalars(select(Department).where(Department.head_user_id == users['chen'])).one()
        return project.id, task.id, dept.id, users


def snapshot(engine):
    with Session(engine) as db:
        return ([tuple(getattr(n, k, None) for k in ('id','title','status','owner_user_id','department_id','start_date','due_date')) for n in db.scalars(select(Node).order_by(Node.id))],
                [(a.id, a.action, a.payload) for a in db.scalars(select(AuditLog).where(AuditLog.action.like('node.%')).order_by(AuditLog.id))])


@pytest.mark.parametrize('dates', [{}, {'start_date': None, 'due_date': None}, {'start_date':'0001-01-01'}, {'due_date':'9999-12-31'}, {'start_date':'2028-02-29','due_date':'2028-02-29'}])
def test_create_dates_and_complete_audit(client, engine, dates):
    pid, _, dept, users = setup_ids(client, engine)
    data = {'title':'  日期任務  ', 'kind':'task', 'owner_user_id':users['ming'], 'department_id':dept, **dates}
    r = client.post(f'/projects/{pid}/nodes', json=data)
    assert r.status_code == 201
    n = r.json()
    assert n['title'] == '日期任務' and n['status'] == 'todo'
    assert n['start_date'] == dates.get('start_date') and n['due_date'] == dates.get('due_date')
    assert n['owner_display_name'] == '明成員' and n['department_name'] == '品保'
    assert {k: n['capabilities'][k] for k in ('edit_metadata','assign','create_child')} == {'edit_metadata':True,'assign':True,'create_child':True}
    with Session(engine) as db:
        audit = db.scalars(select(AuditLog).where(AuditLog.node_id == n['id'])).one()
        for k in ('title','kind','parent_id','owner_user_id','department_id','start_date','due_date'):
            assert audit.payload[k] == n[k]


@pytest.mark.parametrize('invalid', [{'title':' '},{'title':None},{'title':'x'*201},{'kind':'project'},{'kind':'bad'}, {'start_date':'2026-02-29'},{'due_date':'2028-2-29'},{'due_date':12345},{'due_date':'2028-02-29T00:00:00'},{'start_date':'2028-03-01','due_date':'2028-02-29'}, {'status':'done'}])
def test_create_rejects_invalid_atomically(client, engine, invalid):
    pid, _, _, _ = setup_ids(client, engine)
    before = snapshot(engine)
    assert client.post(f'/projects/{pid}/nodes',json={'title':'test','kind':'task',**invalid}).status_code == 422
    assert snapshot(engine) == before


def test_patch_merge_clear_noop_and_audit(client, engine):
    pid, nid, _, _ = setup_ids(client, engine)
    r = client.patch(f'/nodes/{nid}',json={'title':'  改名  ','start_date':'2028-02-29','due_date':'2028-03-01'})
    assert r.status_code == 200 and r.json()['title'] == '改名'
    before = snapshot(engine)
    assert client.patch(f'/nodes/{nid}',json={'due_date':'2028-02-28','title':'不可部分更新'}).status_code == 422
    assert snapshot(engine) == before
    assert client.patch(f'/nodes/{nid}',json={'start_date':'2028-03-02'}).status_code == 422
    assert snapshot(engine) == before
    assert client.patch(f'/nodes/{nid}',json={'title':' 改名 ','due_date':'2028-03-01'}).status_code == 200
    assert snapshot(engine) == before
    r = client.patch(f'/nodes/{nid}',json={'start_date':None,'due_date':None,'owner_user_id':None,'department_id':None})
    assert r.status_code == 200
    assert all(r.json()[k] is None for k in ('start_date','due_date','owner_user_id','department_id','owner_display_name','department_name'))
    with Session(engine) as db:
        audits = list(db.scalars(select(AuditLog).where(AuditLog.node_id==nid,AuditLog.action=='node.update').order_by(AuditLog.created_at)))
        assert len(audits)==2
        assert audits[0].payload['title'] == {'before':'殺菌條件驗證','after':'改名'}
        assert audits[1].payload['start_date'] == {'before':'2028-02-29','after':None}
        assert 'title' not in audits[1].payload


@pytest.mark.parametrize('payload',[{}, {'title':None},{'title':' '},{'kind':'task'},{'parent_id':None},{'project_id':'x'},{'organization_id':'x'},{'status':'done'},{'start_date':'2026-02-29'}])
def test_patch_whitelist(client,engine,payload):
    _,nid,_,_=setup_ids(client,engine)
    before=snapshot(engine)
    assert client.patch(f'/nodes/{nid}',json=payload).status_code==422
    assert snapshot(engine)==before


@pytest.mark.parametrize('actor,project_owner,node_owner,head,visible,edit,manage',[
    ('yu','yu','ming','chen',True,True,True),
    ('owner','owner','ming','chen',True,True,True),
    ('owner','yu','ming','chen',True,False,False),
    ('ming','yu','ming','chen',True,True,False),
    ('chen','yu','ming','chen',True,True,False),
    ('ming','yu','yu','ming',True,True,False),
    ('lin','lin','lin','lin',True,False,False),
    ('lin','yu','ming','chen',True,False,False),
])
def test_metadata_permission_matrix(client,engine,actor,project_owner,node_owner,head,visible,edit,manage):
    pid,nid,dept,users=setup_ids(client,engine)
    with Session(engine) as db:
        db.get(Project,pid).owner_user_id=users[project_owner]
        db.get(Node,nid).owner_user_id=users[node_owner]
        db.get(Department,dept).head_user_id=users[head]
        db.commit()
    client.post('/auth/logout');login(client,username=actor)
    detail=client.get(f'/projects/{pid}').json()
    assign=manage or (actor==head and actor!='lin')
    assert detail['capabilities']['create_node']==manage
    nodes={n['id']:n for n in detail['nodes']}
    assert (nid in nodes)==visible
    if visible:
        assert {k: nodes[nid]['capabilities'][k] for k in ('edit_metadata','assign','create_child')}=={'edit_metadata':edit,'assign':assign,'create_child':manage}
    before=snapshot(engine)
    r=client.patch(f'/nodes/{nid}',json={'title':'changed'})
    assert r.status_code==(200 if edit else 403 if visible else 404)
    if not edit: assert snapshot(engine)==before
    before=snapshot(engine)
    r=client.patch(f'/nodes/{nid}',json={'owner_user_id':users['yu']})
    assert r.status_code==(200 if assign and visible else 403 if visible else 404)
    if not assign: assert snapshot(engine)==before
    before=snapshot(engine)
    assert client.post(f'/projects/{pid}/nodes',json={'title':'new','kind':'task'}).status_code==(201 if manage else 403)
    if not manage: assert snapshot(engine)==before
    assert client.get(f'/projects/{pid}/assignment-options').status_code==(200 if assign else 403)


def test_assignment_scope_and_options(client,engine):
    pid,nid,dept,users=setup_ids(client,engine)
    r=client.get(f'/projects/{pid}/assignment-options')
    assert r.status_code==200
    opts=r.json()
    assert {u['id'] for u in opts['users']}=={users[k] for k in ('yu','owner','chen','ming')}
    assert all(set(u)=={'id','display_name'} for u in opts['users'])
    assert all(set(d)=={'id','name'} for d in opts['departments'])
    with Session(engine) as db:
        foreign_dept=db.scalars(select(Department).where(Department.head_user_id==users['elaine'])).one().id
        foreign_project=db.scalars(select(Project).where(Project.owner_user_id==users['elaine'])).one().id
        foreign_node=db.scalars(select(Node).where(Node.project_id==foreign_project)).one().id
    for fields in ({'owner_user_id':users['lin']},{'owner_user_id':users['elaine']},{'owner_user_id':'missing'},{'department_id':foreign_dept},{'department_id':'missing'}):
        before=snapshot(engine)
        assert client.post(f'/projects/{pid}/nodes',json={'title':'bad','kind':'task',**fields}).status_code==400
        assert client.patch(f'/nodes/{nid}',json={'title':'bad',**fields}).status_code==400
        assert snapshot(engine)==before
    assert client.patch(f'/nodes/{foreign_node}',json={'title':'bad'}).status_code==404
    assert client.get(f'/projects/{foreign_project}/assignment-options').status_code==404
    assert client.patch('/nodes/missing',json={'title':'bad'}).status_code==404


def test_hierarchy_legacy_and_hidden_parent(client,engine):
    pid,nid,_,users=setup_ids(client,engine)
    root_project=client.post('/projects',json={'title':'root'}).json()['id']
    root=client.get(f'/projects/{root_project}').json()['nodes'][0]
    assert {k: root['capabilities'][k] for k in ('edit_metadata','assign','create_child')}=={'edit_metadata':False,'assign':False,'create_child':True}
    before=snapshot(engine)
    assert client.patch(f"/nodes/{root['id']}",json={'title':'no'}).status_code==403
    assert snapshot(engine)==before
    phase=client.post(f'/projects/{root_project}/nodes',json={'title':'phase','kind':'phase','parent_id':root['id']}).json()
    task=client.post(f'/projects/{root_project}/nodes',json={'title':'task','kind':'task','parent_id':phase['id']}).json()
    child=client.post(f'/projects/{root_project}/nodes',json={'title':'child','kind':'task','parent_id':task['id']})
    assert child.status_code==201 and child.json()['owner_user_id'] is None
    for parent in (phase['id'],task['id']):
        before=snapshot(engine)
        assert client.post(f'/projects/{root_project}/nodes',json={'title':'bad','kind':'phase','parent_id':parent}).status_code==400
        assert snapshot(engine)==before
    for parent in ('missing',nid):
        assert client.post(f'/projects/{root_project}/nodes',json={'title':'bad','kind':'task','parent_id':parent}).status_code==400
    with Session(engine) as db:
        db.get(Project,pid).owner_user_id=users['ming']
        db.get(Node,nid).owner_user_id=users['yu']
        db.commit()
    client.post('/auth/logout');login(client,username='ming')
    before=snapshot(engine)
    assert client.post(f'/projects/{pid}/nodes',json={'title':'bad','kind':'task','parent_id':nid}).status_code==400
    assert snapshot(engine)==before
    assert client.post(f'/projects/{pid}/nodes',json={'title':'top','kind':'phase'}).status_code==201


def test_historical_readonly_assignment_does_not_block_metadata_edit(client,engine):
    pid,nid,_,users=setup_ids(client,engine)
    with Session(engine) as db:
        db.get(Node,nid).owner_user_id=users['lin']
        db.commit()
    r=client.patch(f'/nodes/{nid}',json={'title':'歷史仍可編輯'})
    assert r.status_code==200 and r.json()['owner_display_name']=='林唯讀'
    assert client.patch(f'/nodes/{nid}',json={'owner_user_id':users['lin']}).status_code==400


def test_audit_failure_rolls_back_metadata_and_creation(client,engine,monkeypatch):
    from app.routes import projects
    pid,nid,_,_=setup_ids(client,engine)
    before=snapshot(engine)
    def fail_audit(*args,**kwargs):
        raise RuntimeError('simulated audit write failure')
    monkeypatch.setattr(projects,'log_audit',fail_audit)
    from app.services import schedule_service
    monkeypatch.setattr(schedule_service,'log_audit',fail_audit)
    with pytest.raises(RuntimeError,match='simulated audit'):
        client.patch(f'/nodes/{nid}',json={'title':'must roll back'})
    assert snapshot(engine)==before
    with pytest.raises(RuntimeError,match='simulated audit'):
        client.post(f'/projects/{pid}/nodes',json={'title':'must roll back','kind':'task'})
    assert snapshot(engine)==before


def test_management_does_not_expand_status_permission(client,engine):
    pid,nid,_,users=setup_ids(client,engine)
    with Session(engine) as db:
        db.get(Project,pid).owner_user_id=users['owner']
        db.commit()
    client.post('/auth/logout');login(client,username='owner')
    assert client.patch(f'/nodes/{nid}',json={'title':'manager edit'}).status_code==200
    before=snapshot(engine)
    assert client.patch(f'/nodes/{nid}/status',json={'status':'doing'}).status_code==403
    assert snapshot(engine)==before
