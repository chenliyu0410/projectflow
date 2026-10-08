def login(client, org="food", username="yu", password=None):
    response = client.post("/auth/login", json={
        "organization_key": org,
        "username": username,
        "password": password or f"demo-{username}",
    })
    assert response.status_code == 200


def test_workflow_list_is_scoped_by_organization(client):
    login(client, "food", "yu")
    food_names = [item["name"] for item in client.get("/workflows").json()["items"]]
    assert food_names == ["食品新品開發"]
    client.post("/auth/logout")
    login(client, "electronics", "elaine", "demo-elaine")
    electronics_names = [item["name"] for item in client.get("/workflows").json()["items"]]
    assert electronics_names == ["電子新品開發"]


def test_create_project_from_workflow_creates_nodes_gates_and_audit(client):
    login(client, "food", "yu")
    workflow_id = client.get("/workflows").json()["items"][0]["id"]
    created = client.post("/projects/from-workflow", json={"workflow_id": workflow_id, "title": "犬用鮮食上市"}).json()
    assert created["title"] == "犬用鮮食上市"
    detail = client.get(f"/projects/{created['id']}").json()
    assert [node["title"] for node in detail["nodes"]] == ["市場與配方", "小量試作", "配方設計", "試作工單"]
    assert detail["gates"][0]["status"] == "pending"
    assert client.get("/audit-logs").json()["items"][0]["action"] == "workflow.instantiate"


def test_cross_company_workflow_id_cannot_instantiate_project(client):
    login(client, "electronics", "elaine", "demo-elaine")
    other_workflow = client.get("/workflows").json()["items"][0]["id"]
    client.post("/auth/logout")
    login(client, "food", "yu")
    response = client.post("/projects/from-workflow", json={"workflow_id": other_workflow, "title": "不該建立"})
    assert response.status_code == 404


def test_project_owner_can_create_project_from_workflow(client):
    login(client, "food", "owner", "demo-owner")
    workflow_id = client.get("/workflows").json()["items"][0]["id"]
    response = client.post("/projects/from-workflow", json={"workflow_id": workflow_id, "title": "Owner建立"})
    assert response.status_code == 201
    assert response.json()["title"] == "Owner建立"


def test_pending_gate_blocks_later_stage_even_with_override_payload(client):
    login(client, "food", "yu")
    workflow_id = client.get("/workflows").json()["items"][0]["id"]
    project = client.post("/projects/from-workflow", json={"workflow_id": workflow_id, "title": "Gate測試"}).json()
    detail = client.get(f"/projects/{project['id']}").json()
    later_task = next(node for node in detail["nodes"] if node["title"] == "試作工單")
    blocked = client.patch(f"/nodes/{later_task['id']}/status", json={"status": "doing", "override": True})
    assert blocked.status_code == 422
    clean_blocked = client.patch(f"/nodes/{later_task['id']}/status", json={"status": "doing"})
    assert clean_blocked.status_code == 409
    assert clean_blocked.json() == {"detail": "前一階段閘門尚未通過"}


def test_gate_approval_allows_later_stage_for_authorized_user(client):
    login(client, "food", "yu")
    workflow_id = client.get("/workflows").json()["items"][0]["id"]
    project = client.post("/projects/from-workflow", json={"workflow_id": workflow_id, "title": "Gate核准"}).json()
    detail = client.get(f"/projects/{project['id']}").json()
    gate = detail["gates"][0]
    assert client.patch(f"/gates/{gate['id']}", json={"status": "approved"}).status_code == 200
    later_task = next(node for node in client.get(f"/projects/{project['id']}").json()["nodes"] if node["title"] == "試作工單")
    ok = client.patch(f"/nodes/{later_task['id']}/status", json={"status": "doing"})
    assert ok.status_code == 200


def test_reviewer_cannot_approve_unrelated_gate(client):
    login(client, "food", "yu")
    workflow_id = client.get("/workflows").json()["items"][0]["id"]
    project = client.post("/projects/from-workflow", json={"workflow_id": workflow_id, "title": "Gate審核範圍"}).json()
    gate = client.get(f"/projects/{project['id']}").json()["gates"][0]
    client.post("/auth/logout")

    login(client, "food", "chen", "demo-chen")
    response = client.patch(f"/gates/{gate['id']}", json={"status": "approved"})
    assert response.status_code == 403

# P2a: Gate enforcement follows stored ancestry, independent of node visibility.
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import AuditLog, Gate, Node, Project, User


def nested_gate_fixture(client, engine, with_root=False):
    login(client)
    workflow = client.get('/workflows').json()['items'][0]
    project = client.post('/projects/from-workflow', json={'workflow_id':workflow['id'], 'title':'巢狀 Gate'}).json()
    detail = client.get(f"/projects/{project['id']}").json()
    phase = next(n for n in detail['nodes'] if n['title']=='小量試作')
    task = next(n for n in detail['nodes'] if n['title']=='試作工單')
    with Session(engine) as db:
        member = db.scalars(select(User).where(User.username=='ming')).one()
        member_id = member.id
        if with_root:
            root = Node(organization_id=member.organization_id, project_id=project['id'], kind='project', title='歷史根')
            db.add(root); db.flush()
            for n in db.scalars(select(Node).where(Node.project_id==project['id'], Node.kind=='phase')):
                n.parent_id=root.id
            db.commit()
    child = client.post(f"/projects/{project['id']}/nodes", json={'title':'深層任務','kind':'task','parent_id':task['id'],'owner_user_id':member_id})
    assert child.status_code==201
    return project['id'], phase['id'], task['id'], child.json()['id'], detail['gates'][0]['id']


def gate_snapshot(engine):
    with Session(engine) as db:
        return ([(n.id,n.status,n.parent_id) for n in db.scalars(select(Node).order_by(Node.id))],
                [(a.id,a.action,a.payload) for a in db.scalars(select(AuditLog).order_by(AuditLog.id))])


@pytest.mark.parametrize('status',['doing','review','done','skipped'])
@pytest.mark.parametrize('with_root',[False,True])
def test_deep_tasks_cannot_bypass_hidden_phase_gate(client,engine,status,with_root):
    pid,phase,task,child,gate=nested_gate_fixture(client,engine,with_root)
    client.post('/auth/logout');login(client,username='ming')
    visible=client.get(f'/projects/{pid}').json()
    assert {n['id'] for n in visible['nodes']}=={child} and visible['gates']==[]
    before=gate_snapshot(engine)
    denied=client.patch(f'/nodes/{child}/status',json={'status':status})
    assert denied.status_code==409
    assert denied.json()=={'detail':'前一階段閘門尚未通過'}
    assert gate_snapshot(engine)==before
    # Metadata does not start work and remains editable behind a Gate.
    assert client.patch(f'/nodes/{child}',json={'title':'仍可編輯名稱'}).status_code==200
    client.post('/auth/logout');login(client)
    assert client.patch(f'/gates/{gate}',json={'status':'approved'}).status_code==200
    client.post('/auth/logout');login(client,username='ming')
    assert client.patch(f'/nodes/{child}/status',json={'status':status}).status_code==200


def test_phase_itself_is_blocked_and_approval_releases_it(client,engine):
    _,phase,_,_,gate=nested_gate_fixture(client,engine)
    before=gate_snapshot(engine)
    assert client.patch(f'/nodes/{phase}/status',json={'status':'doing'}).status_code==409
    assert gate_snapshot(engine)==before
    assert client.patch(f'/gates/{gate}',json={'status':'approved'}).status_code==200
    assert client.patch(f'/nodes/{phase}/status',json={'status':'doing'}).status_code==200


def test_top_level_task_and_phase_without_gate_remain_workable(client,engine):
    pid,phase,_,_,gate=nested_gate_fixture(client,engine)
    top=client.post(f'/projects/{pid}/nodes',json={'title':'頂層','kind':'task'}).json()
    assert client.patch(f"/nodes/{top['id']}/status",json={'status':'doing'}).status_code==200
    with Session(engine) as db:
        db.delete(db.get(Gate,gate));db.commit()
    assert client.patch(f'/nodes/{phase}/status',json={'status':'doing'}).status_code==200


@pytest.mark.parametrize('damage',['self','task_cycle','above_phase_cycle','missing','other_project','other_company'])
@pytest.mark.parametrize('initial',['todo','doing'])
@pytest.mark.parametrize('target',['todo','done'])
def test_corrupt_ancestry_fails_closed_without_audit(client,engine,damage,initial,target):
    pid,phase,task,child,gate=nested_gate_fixture(client,engine)
    with Session(engine) as db:
        db.get(Node,child).status=initial
        if damage=='self': db.get(Node,child).parent_id=child
        elif damage=='task_cycle': db.get(Node,task).parent_id=child
        elif damage=='above_phase_cycle': db.get(Node,phase).parent_id=child
        elif damage=='missing': db.get(Node,phase).parent_id='missing'
        elif damage=='other_project':
            foreign=db.scalars(select(Node).where(Node.project_id!=pid,Node.organization_id==db.get(Node,child).organization_id)).first()
            db.get(Node,phase).parent_id=foreign.id
        else:
            foreign=db.scalars(select(Node).where(Node.organization_id!=db.get(Node,child).organization_id)).first()
            db.get(Node,phase).parent_id=foreign.id
        db.commit()
    before=gate_snapshot(engine)
    r=client.patch(f'/nodes/{child}/status',json={'status':target})
    assert r.status_code==409
    assert r.json()=={'detail':'節點階層異常，無法變更狀態'}
    assert gate_snapshot(engine)==before


def test_gate_scope_and_existing_non_todo_transition_semantics(client,engine):
    pid,phase,task,child,gate=nested_gate_fixture(client,engine)
    with Session(engine) as db:
        # A pending Gate still does not block an already-started valid node.
        db.get(Node,child).status='doing'
        db.commit()
    assert client.patch(f'/nodes/{child}/status',json={'status':'done'}).status_code==200
    assert client.patch(f'/nodes/{child}/status',json={'status':'todo'}).status_code==200
    with Session(engine) as db:
        prior_phase = db.get(Gate,gate).node_id
        db.delete(db.get(Gate,gate))
        other=db.scalars(select(Node).where(Node.organization_id!=db.get(Node,child).organization_id)).first()
        # Deliberately damaged foreign Gate references must not affect this company.
        db.add(Gate(organization_id=other.organization_id, project_id=pid,node_id=prior_phase,status='pending'))
        db.commit()
    assert client.patch(f'/nodes/{child}/status',json={'status':'doing'}).status_code==200
