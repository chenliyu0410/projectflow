from datetime import date

import pytest
from sqlalchemy import event, select
from sqlalchemy.orm import Session

from app.models import Department, Node, Project, User
from test_projects_nodes import login


@pytest.fixture
def workspace(client, engine):
    login(client)
    with Session(engine) as db:
        users = {u.username: u for u in db.scalars(select(User))}
        org = users['yu'].organization_id
        dept = db.scalars(select(Department).where(Department.head_user_id == users['chen'].id)).one()
        # This fixture uses an isolated SQLite database; preserve seed rows but exclude them from task totals.
        for n in db.scalars(select(Node).where(Node.organization_id == org)):
            n.kind = 'phase'
        for pid, title in [('ws-a','Alpha工作'),('ws-b','Beta工作'),('ws-empty','Empty工作')]:
            db.add(Project(id=pid,organization_id=org,title=title,owner_user_id=users['owner'].id))
        db.flush()
        rows = [
            ('hidden-phase','ws-a','phase','Hidden phase','yu','todo',None,None),
            ('a1','ws-a','task','Parent TASK','ming','done','2028-03-01','hidden-phase'),
            ('a2','ws-a','task','Early','ming','todo','2028-02-01','hidden-phase'),
            ('a3','ws-a','task','Skip A','ming','skipped',None,None),
            ('a4','ws-a','task','Review','ming','review',None,None),
            ('a5','ws-a','task','Child TASK','ming','doing','2028-03-01','a1'),
            ('hidden-task','ws-a','task','Secret needle','yu','done',None,'a1'),
            ('readonly-task','ws-a','task','Readonly','lin','done',None,None),
            ('head-task','ws-a','task','Head only','chen','todo',None,None),
            ('owner-task','ws-a','task','Owner only','owner','review',None,None),
            ('b1','ws-b','task','Beta done','ming','done','2028-03-01',None),
            ('b2','ws-b','task','Skip B','ming','skipped',None,None),
            ('b-phase','ws-b','phase','Not a task','ming','done',None,None),
        ]
        for nid,pid,kind,title,owner,status,due,parent in rows:
            db.add(Node(id=nid,organization_id=org,project_id=pid,kind=kind,title=title,
                        owner_user_id=users[owner].id,department_id=dept.id,status=status,
                        due_date=date.fromisoformat(due) if due else None,parent_id=parent))
        db.commit()
        return {'org':org,'member':users['ming'].id,'dept':dept.id}


def switch(client, username, org='food'):
    client.post('/auth/logout')
    login(client,org=org,username=username)


def test_overview_visible_tasks_count_parents_and_exclude_hidden(client,engine,workspace):
    switch(client,'ming')
    response=client.get('/workspace/overview')
    assert response.status_code==200
    value=response.json()
    assert set(value)=={'project_count','task_counts','completion_percent','projects','today','overdue_count','people','departments'}
    assert value['project_count']==4
    assert value['task_counts']=={'todo':1,'doing':1,'review':1,'done':2,'skipped':2}
    assert value['completion_percent']==40
    projects={p['id']:p for p in value['projects']}
    assert projects['ws-a']=={'id':'ws-a','title':'Alpha工作','task_counts':{'todo':1,'doing':1,'review':1,'done':1,'skipped':1},'completion_percent':25,
                            'current_phase_title':None,'due_date':'2028-03-01','overdue_count':0}
    # Workloads count only visible open tasks: chen's hidden head-task must not appear for a member.
    assert value['people']==[{'user_id':workspace['member'],'display_name':'明成員','department_name':'品保','open_count':3,'overdue_count':0}]
    assert {d['id']:d['open_count'] for d in value['departments']}[workspace['dept']]==3
    assert projects['ws-b']['completion_percent']==100
    assert projects['ws-empty']['completion_percent'] is None
    with Session(engine) as db:
        db.get(Node,'hidden-task').status='todo'
        db.get(Node,'hidden-phase').title='Another secret'
        db.commit()
    assert client.get('/workspace/overview').json()==value
    text=response.text
    for secret in ('Hidden phase','Secret needle','electronics','Elaine','password_hash','session'):
        assert secret not in text


@pytest.mark.parametrize('actor',['yu','lin','owner'])
def test_broad_visibility_and_personal_ownership_are_distinct(client,workspace,actor):
    switch(client,actor)
    overview=client.get('/workspace/overview')
    assert overview.status_code==200
    assert overview.json()['task_counts']=={'todo':2,'doing':1,'review':2,'done':4,'skipped':2}
    assert overview.json()['completion_percent']==44
    mine=client.get('/workspace/my-tasks').json()['items']
    expected={'yu':['hidden-task'],'lin':['readonly-task'],'owner':['owner-task']}
    assert [n['id'] for n in mine]==expected[actor]
    if actor=='lin':
        assert {k: mine[0]['capabilities'][k] for k in ('edit_metadata','assign','create_child')}=={'edit_metadata':False,'assign':False,'create_child':False}


def test_my_tasks_safe_projection_stable_date_sort_and_no_phase(client,workspace):
    switch(client,'ming')
    r=client.get('/workspace/my-tasks')
    assert r.status_code==200
    items=r.json()['items']
    assert [n['id'] for n in items]==['a2','a1','a5','b1','a3','a4','b2']
    assert items[1]['project_title']=='Alpha工作'
    assert items[1]['owner_display_name']=='明成員'
    assert items[1]['department_name']=='品保'
    assert items[1]['start_date'] is None and items[1]['due_date']=='2028-03-01'
    assert {k: items[1]['capabilities'][k] for k in ('edit_metadata','assign','create_child')}=={'edit_metadata':True,'assign':False,'create_child':False}
    assert all(n['kind']=='task' for n in items)
    for secret in ('Secret needle','Hidden phase','password_hash','username','session','electronics'):
        assert secret not in r.text


@pytest.mark.parametrize('query,expected',[
    ({'q':'  tAsK  '},['a1','a5']),
    ({'q':'  aLpHa  '},['a2','a1','a5','a3','a4']),
    ({'q':'Secret needle'},[]),
    ({'q':'no match'},[]),
    ({'q':'   ','status':''},['a2','a1','a5','b1','a3','a4','b2']),
    ({'status':'todo'},['a2']),({'status':'doing'},['a5']),
    ({'status':'review'},['a4']),({'status':'done'},['a1','b1']),
    ({'status':'skipped'},['a3','b2']),
    ({'q':'alpha','status':'done'},['a1']),
])
def test_search_and_filters_use_only_authorized_tasks(client,workspace,query,expected):
    switch(client,'ming')
    overview=client.get('/workspace/overview').json()
    r=client.get('/workspace/my-tasks',params=query)
    assert r.status_code==200
    assert [n['id'] for n in r.json()['items']]==expected
    assert client.get('/workspace/overview',params=query).json()==overview


def test_invalid_status_and_unauthenticated_workspace(client,workspace):
    assert client.get('/workspace/my-tasks?status=blocked').status_code==422
    assert client.get('/workspace/my-tasks?status=DONE').status_code==422
    client.post('/auth/logout')
    assert client.get('/workspace/overview').status_code==401
    assert client.get('/workspace/my-tasks').status_code==401


def test_department_head_does_not_receive_other_peoples_tasks(client,workspace):
    switch(client,'chen')
    r=client.get('/workspace/my-tasks')
    assert r.status_code==200
    assert [n['id'] for n in r.json()['items']]==['head-task']


def test_other_company_cannot_leak_through_queries(client,workspace):
    switch(client,'elaine','electronics')
    r=client.get('/workspace/overview?organization_key=food')
    assert r.status_code==200
    assert r.json()['project_count']==1
    assert r.json()['task_counts']=={'todo':1,'doing':0,'review':0,'done':0,'skipped':0}
    assert 'Alpha' not in r.text
    assert client.get('/workspace/my-tasks?q=Alpha').json()=={'items':[]}


@pytest.mark.parametrize('done,total,skipped,expected',[(0,0,0,None),(0,0,3,None),(1,8,0,13),(1,3,1,33),(0,2,0,0),(2,2,4,100)])
def test_completion_rounding_and_zero_denominator(client,engine,workspace,done,total,skipped,expected):
    with Session(engine) as db:
        # Isolated project provides exact denominators, including half-up 12.5 -> 13.
        for i in range(total+skipped):
            db.add(Node(organization_id=workspace['org'],project_id='ws-empty',kind='task',title=f'count {i}',
                        owner_user_id=workspace['member'],status='done' if i<done else 'todo' if i<total else 'skipped'))
        db.commit()
    switch(client,'ming')
    r=client.get('/workspace/overview')
    assert r.status_code==200
    project=next(p for p in r.json()['projects'] if p['id']=='ws-empty')
    assert project['completion_percent']==expected
    assert project['task_counts']['skipped']==skipped


def test_workspace_query_count_is_constant_as_projects_and_tasks_grow(client,engine,workspace):
    switch(client,'ming')
    queries=[]
    def record(conn,cursor,statement,parameters,context,executemany):
        if statement.lstrip().upper().startswith('SELECT'): queries.append(statement)
    event.listen(engine,'before_cursor_execute',record)
    try:
        first=client.get('/workspace/my-tasks')
        assert first.status_code==200
        count=len(queries)
        with Session(engine) as db:
            for i in range(30):
                pid=f'extra-project-{i}'
                db.add(Project(id=pid,organization_id=workspace['org'],title=f'Extra {i}',owner_user_id=workspace['member']))
                db.flush()
                db.add(Node(organization_id=workspace['org'],project_id=pid,kind='task',title=f'extra {i}',owner_user_id=workspace['member'],department_id=workspace['dept']))
            db.commit()
        queries.clear()
        assert len(client.get('/workspace/my-tasks').json()['items'])==37
        # P2c adds one batched dependency lookup, independent of task count.
        assert len(queries)==count and count<=8
        assert sum('FROM node_dependencies' in query for query in queries)==1
        queries.clear()
        assert client.get('/workspace/overview').status_code==200
        assert len(queries)<=8
        assert sum('FROM node_dependencies' in query for query in queries)==1
    finally:
        event.remove(engine,'before_cursor_execute',record)


def test_company_without_projects_has_empty_workspace(client,engine):
    from app.models import Organization
    with Session(engine) as db:
        original=db.scalars(select(User).where(User.username=='yu')).one()
        org=Organization(key='empty-workspace',name='空公司')
        db.add(org);db.flush()
        db.add(User(organization_id=org.id,username='yu',display_name='空公司使用者',role='admin',password_hash=original.password_hash))
        db.commit()
    login(client,org='empty-workspace')
    empty=client.get('/workspace/overview').json()
    assert empty.pop('today')
    assert empty=={
        'project_count':0,'task_counts':{'todo':0,'doing':0,'review':0,'done':0,'skipped':0},
        'completion_percent':None,'projects':[],'overdue_count':0,'people':[],'departments':[],
    }
    assert client.get('/workspace/my-tasks').json()=={'items':[]}


def test_overview_phase_due_date_and_overdue_use_visible_nodes(client,engine,workspace):
    with Session(engine) as db:
        rows=[
            ('p-done','phase','完成階段','done',None,None,0),
            ('p-active','phase','第二階段','doing',None,None,1),
            ('p-later','phase','第三階段','todo',None,None,2),
            ('late-open','task','逾期未完成','todo','2020-01-01','p-active',0),
            ('late-done','task','逾期已完成','done','2020-01-01','p-active',1),
            ('late-skip','task','逾期已略過','skipped','2020-01-01','p-active',2),
            ('future','task','未來任務','doing','2099-01-01','p-later',0),
        ]
        for nid,kind,title,status,due,parent,order in rows:
            db.add(Node(id=nid,organization_id=workspace['org'],project_id='ws-empty',kind=kind,title=title,status=status,
                        owner_user_id=workspace['member'],department_id=workspace['dept'],sort_order=order,
                        due_date=date.fromisoformat(due) if due else None,parent_id=parent))
        db.commit()
    switch(client,'ming')
    value=client.get('/workspace/overview').json()
    project=next(p for p in value['projects'] if p['id']=='ws-empty')
    assert project['current_phase_title']=='第二階段'
    assert project['due_date']=='2099-01-01'
    assert project['overdue_count']==1 and value['overdue_count']==1
    me=next(p for p in value['people'] if p['user_id']==workspace['member'])
    assert me['open_count']==5 and me['overdue_count']==1


def test_overview_workload_for_broad_viewer_includes_other_owners(client,workspace):
    switch(client,'yu')
    value=client.get('/workspace/overview').json()
    names={p['display_name']:p['open_count'] for p in value['people']}
    assert names['明成員']==3 and sum(names.values())==5
    assert {d['id']:d['open_count'] for d in value['departments']}[workspace['dept']]==5
    assert value['departments']==sorted(value['departments'],key=lambda d:(-d['open_count'],d['name'],d['id']))


def test_my_tasks_path_lists_only_visible_ancestors(client,workspace):
    switch(client,'ming')
    items={n['id']:n for n in client.get('/workspace/my-tasks').json()['items']}
    assert items['a5']['path']==[{'id':'a1','title':'Parent TASK'}]
    assert items['a1']['path']==[] and items['b1']['path']==[]
    switch(client,'yu')
    r=client.get('/workspace/my-tasks')
    hidden=next(n for n in r.json()['items'] if n['id']=='hidden-task')
    assert hidden['path']==[{'id':'hidden-phase','title':'Hidden phase'},{'id':'a1','title':'Parent TASK'}]
