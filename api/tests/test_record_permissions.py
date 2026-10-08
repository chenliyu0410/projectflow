import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from app import models
from app.auth import CurrentUser
from test_projects_nodes import login


def fixture_ids(client, engine):
    login(client)
    with Session(engine) as db:
        users={u.username:u.id for u in db.scalars(select(models.User))}
        project=db.scalars(select(models.Project).where(models.Project.owner_user_id==users['yu'])).one()
        task=db.scalars(select(models.Node).where(models.Node.project_id==project.id,models.Node.kind=='task')).one()
        return project.id,task.id,users


def add_collaborator(engine,nid,users,username=None,department=None):
    assert hasattr(models,'NodeCollaborator'), 'Collaboration model is not implemented'
    with Session(engine) as db:
        node=db.get(models.Node,nid)
        db.add(models.NodeCollaborator(organization_id=node.organization_id,node_id=nid,
               user_id=users[username] if username else None,department_id=department,created_by=users['yu']))
        db.commit()


def test_explicit_collaborator_visibility_records_only_and_no_inheritance(client,engine):
    pid,nid,users=fixture_ids(client,engine)
    with Session(engine) as db:
        node=db.get(models.Node,nid);node.owner_user_id=users['yu']
        child=models.Node(organization_id=node.organization_id,project_id=pid,parent_id=nid,kind='task',title='hidden child',owner_user_id=users['yu'])
        db.add(child);db.commit();child_id=child.id
    add_collaborator(engine,nid,users,'ming')
    client.post('/auth/logout');login(client,username='ming')
    detail=client.get(f'/projects/{pid}').json()
    assert [n['id'] for n in detail['nodes']]==[nid]
    node=detail['nodes'][0]
    assert node['capabilities']['write_record'] is True
    assert node['capabilities']['submit_report'] is False
    assert node['capabilities']['edit_metadata'] is False
    assert node['capabilities']['manage_collaborators'] is False
    assert client.patch(f'/nodes/{nid}',json={'title':'forbidden'}).status_code==403
    assert client.patch(f'/nodes/{nid}/status',json={'status':'doing'}).status_code==403
    mine=client.get('/workspace/my-tasks').json()['items']
    assert [n['id'] for n in mine]==[nid]
    assert mine[0]['relations']==['collaborating']
    assert child_id not in {n['id'] for n in mine}
    with Session(engine) as db:
        db.get(models.Node,nid).owner_user_id=users['ming'];db.commit()
    mine=client.get('/workspace/my-tasks').json()['items']
    assert len(mine)==1 and mine[0]['relations']==['owned','collaborating']


def test_collaboration_department_only_head_and_revocation_is_live(client,engine):
    pid,nid,users=fixture_ids(client,engine)
    with Session(engine) as db:
        node=db.get(models.Node,nid);node.owner_user_id=users['yu']
        department=models.Department(organization_id=node.organization_id,name='協作測試部門',head_user_id=users['ming'])
        db.add(department);db.flush()
        db.add(models.DepartmentMember(organization_id=node.organization_id,department_id=department.id,user_id=users['owner']))
        db.commit();did=department.id
    add_collaborator(engine,nid,users,department=did)
    client.post('/auth/logout');login(client,username='ming')
    assert [n['id'] for n in client.get('/workspace/my-tasks').json()['items']]==[nid]
    with Session(engine) as db:
        db.get(models.Department,did).head_user_id=users['owner'];db.commit()
    assert client.get('/workspace/my-tasks').json()['items']==[]
    assert client.get(f'/projects/{pid}').json()['nodes']==[]
    client.post('/auth/logout');login(client,username='owner')
    assert [n['id'] for n in client.get('/workspace/my-tasks').json()['items']]==[nid]
    with Session(engine) as db:
        row=db.scalars(select(models.NodeCollaborator).where(models.NodeCollaborator.node_id==nid)).one()
        db.delete(row);db.commit()
    assert client.get('/workspace/my-tasks').json()['items']==[]


@pytest.mark.parametrize('actor,owner,submit,review,write',[
    ('yu','ming',True,True,True),('owner','owner',False,True,True),
    ('owner','yu',False,False,False),('ming','yu',True,False,True),
    ('chen','yu',True,True,True),('lin','lin',False,False,False),
])
def test_record_policy_role_matrix(client,engine,actor,owner,submit,review,write):
    pid,nid,users=fixture_ids(client,engine)
    from app.services import record_policy
    with Session(engine) as db:
        project=db.get(models.Project,pid);project.owner_user_id=users[owner]
        node=db.get(models.Node,nid)
        user=db.get(models.User,users[actor]);org=db.get(models.Organization,user.organization_id)
        current=CurrentUser(user,org,'test')
        context=record_policy.load_policy_context(db,current)
        assert record_policy.can_submit_report(db,current,project,node,context=context)==submit
        assert record_policy.can_review_report(db,current,project,node,context=context)==review
        assert record_policy.can_write_record(db,current,project,node,context=context)==write
        # Merely owning a project does not grant submission rights to its tasks.
        if actor=='owner': assert record_policy.can_submit_report(db,current,project,node,context=context) is False


def test_readonly_collaboration_has_no_writes_and_foreign_links_do_not_grant_access(client,engine):
    pid,nid,users=fixture_ids(client,engine)
    add_collaborator(engine,nid,users,'lin')
    client.post('/auth/logout');login(client,username='lin')
    mine=client.get('/workspace/my-tasks').json()['items']
    assert [n['id'] for n in mine]==[nid]
    assert all(not v for v in mine[0]['capabilities'].values())
    assert mine[0]['state_actions']==[]
    client.post('/auth/logout');login(client,org='electronics',username='kai')
    assert nid not in {n['id'] for n in client.get('/workspace/my-tasks').json()['items']}


def test_collaboration_does_not_turn_project_management_into_global_read(client,engine):
    pid,nid,users=fixture_ids(client,engine)
    with Session(engine) as db:
        db.get(models.Project,pid).owner_user_id=users['ming']
        db.get(models.Node,nid).owner_user_id=users['yu'];db.commit()
    client.post('/auth/logout');login(client,username='ming')
    assert client.get(f'/projects/{pid}').json()['nodes']==[]
    add_collaborator(engine,nid,users,'ming')
    node=client.get(f'/projects/{pid}').json()['nodes'][0]
    assert node['capabilities']['edit_metadata'] and node['capabilities']['manage_collaborators']
    assert not node['capabilities']['submit_report']


def test_review_policy_rechecks_latest_workflow_self_and_visibility(client,engine):
    from datetime import date
    from app.services import record_policy
    pid,nid,users=fixture_ids(client,engine)
    with Session(engine) as db:
        node=db.get(models.Node,nid);node.status='review'
        report=models.TaskReport(organization_id=node.organization_id,node_id=nid,submitted_by=users['ming'],result='達成',summary='new',workflow_version=2,version=1,finished_on=date(2026,10,8))
        db.add(report);db.commit()
        project=db.get(models.Project,pid);user=db.get(models.User,users['yu'])
        current=CurrentUser(user,db.get(models.Organization,user.organization_id),'test')
        context=record_policy.load_policy_context(db,current)
        assert record_policy.can_review_report(db,current,project,node,report,context=context)
        report.submitted_by=user.id
        assert not record_policy.can_review_report(db,current,project,node,report,context=context)
        report.submitted_by=users['ming'];report.workflow_version=None
        assert not record_policy.can_review_report(db,current,project,node,report,context=context)
        report.workflow_version=2;context.latest_versions[nid]=2
        assert not record_policy.can_review_report(db,current,project,node,report,context=context)
        assert record_policy.can_self_approve_report(db,current,project,node,context=context)
        db.rollback()


def test_collaboration_queries_remain_constant_and_overview_updates(client,engine):
    from sqlalchemy import event
    pid,nid,users=fixture_ids(client,engine)
    with Session(engine) as db:
        node=db.get(models.Node,nid);node.owner_user_id=users['yu'];db.commit()
    client.post('/auth/logout');login(client,username='ming')
    assert client.get('/workspace/overview').json()['task_counts']['todo']==0
    add_collaborator(engine,nid,users,'ming')
    assert client.get('/workspace/overview').json()['task_counts']['todo']==1
    queries=[]
    def record(conn,cursor,statement,parameters,context,executemany):
        if statement.lstrip().upper().startswith('SELECT'):queries.append(statement)
    event.listen(engine,'before_cursor_execute',record)
    try:
        assert client.get('/workspace/my-tasks').status_code==200
        count=len(queries)
        with Session(engine) as db:
            for i in range(20):
                node=models.Node(organization_id=db.get(models.Project,pid).organization_id,project_id=pid,kind='task',title=f'collab {i}',owner_user_id=users['yu'])
                db.add(node);db.flush()
                db.add(models.NodeCollaborator(organization_id=node.organization_id,node_id=node.id,user_id=users['ming'],created_by=users['yu']))
            db.commit()
        queries.clear()
        assert len(client.get('/workspace/my-tasks').json()['items'])==21
        assert len(queries)==count and count<=7
    finally:
        event.remove(engine,'before_cursor_execute',record)
