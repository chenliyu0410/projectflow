def login(client, org="food", username="yu", password=None):
    response = client.post("/auth/login", json={
        "organization_key": org,
        "username": username,
        "password": password or f"demo-{username}",
    })
    assert response.status_code == 200


def test_project_list_is_scoped_to_session_org(client):
    login(client, "food", "yu")
    food = client.get("/projects").json()["items"]
    assert [project["title"] for project in food] == ["成貓主食罐正式版"]
    client.post("/auth/logout")
    login(client, "electronics", "elaine", "demo-elaine")
    electronics = client.get("/projects").json()["items"]
    assert [project["title"] for project in electronics] == ["連接器新產品正式版"]


def test_forged_org_parameter_does_not_change_project_scope(client):
    login(client, "food", "yu")
    response = client.get("/projects?organization_key=electronics")
    assert response.status_code == 200
    assert [project["organization_key"] for project in response.json()["items"]] == ["food"]


def test_create_project_writes_audit_in_same_org(client):
    login(client, "food", "yu")
    created = client.post("/projects", json={"title": "包材替代專案"}).json()
    assert created["title"] == "包材替代專案"
    logs = client.get("/audit-logs").json()["items"]
    assert logs[0]["action"] == "project.create"
    assert logs[0]["organization_key"] == "food"


def test_node_status_requires_can_work(client):
    login(client, "food", "lin", "demo-lin")
    project = client.get("/projects").json()["items"][0]
    node = client.get(f"/projects/{project['id']}").json()["nodes"][0]
    denied = client.patch(f"/nodes/{node['id']}/status", json={"status": "doing"})
    assert denied.status_code == 403
    client.post("/auth/logout")
    login(client, "food", "ming", "demo-ming")
    ok = client.patch(f"/nodes/{node['id']}/status", json={"status": "doing"})
    assert ok.status_code == 200
    assert ok.json()["status"] == "doing"


def test_readonly_cannot_create_node(client):
    login(client, "food", "lin", "demo-lin")
    project = client.get("/projects").json()["items"][0]
    response = client.post(f"/projects/{project['id']}/nodes", json={"title": "唯讀不該新增", "kind": "task"})
    assert response.status_code == 403


def test_readonly_owner_still_cannot_update_node_status(client, engine):
    from sqlalchemy import select
    from sqlalchemy.orm import Session
    from app.models import Node, User, Project, AuditLog
    login(client)
    with Session(engine) as db:
        user = db.scalars(select(User).where(User.username == "lin")).one()
        project = db.scalars(select(Project).where(Project.organization_id == user.organization_id)).one()
        node = Node(organization_id=user.organization_id, project_id=project.id,
                    kind="task", title="歷史唯讀指派", owner_user_id=user.id)
        db.add(node)
        db.commit()
        node_id = node.id
        before = list(db.scalars(select(AuditLog.id)))
    client.post("/auth/logout")
    login(client, username="lin")
    assert client.patch(f"/nodes/{node_id}/status", json={"status":"doing"}).status_code == 403
    with Session(engine) as db:
        assert db.get(Node, node_id).status == "todo"
        assert list(db.scalars(select(AuditLog.id))) == before


def test_invalid_status_and_override_payload_are_rejected(client):
    login(client, "food", "ming", "demo-ming")
    project = client.get("/projects").json()["items"][0]
    node = client.get(f"/projects/{project['id']}").json()["nodes"][0]
    invalid = client.patch(f"/nodes/{node['id']}/status", json={"status": "blocked"})
    forged = client.patch(f"/nodes/{node['id']}/status", json={"status": "doing", "override": True})
    assert invalid.status_code == 422
    assert forged.status_code == 422
    assert client.get(f"/projects/{project['id']}").json()["nodes"][0]["status"] == "todo"


def test_cross_company_project_and_node_ids_are_not_visible(client):
    login(client, "electronics", "elaine", "demo-elaine")
    other_project_id = client.get("/projects").json()["items"][0]["id"]
    client.post("/auth/logout")
    login(client, "food", "yu")
    assert client.get(f"/projects/{other_project_id}").status_code == 404
    assert client.post(f"/projects/{other_project_id}/nodes", json={"title": "偷看", "kind": "task"}).status_code == 404


def test_member_detail_filters_nodes_and_hidden_gate_metadata(client):
    login(client)
    project = client.get("/projects").json()["items"][0]
    admin = client.get(f"/projects/{project['id']}").json()
    yu_id = client.get("/auth/me").json()["user"]["id"]
    assert client.post(f"/projects/{project['id']}/nodes", json={
        "title": "管理員任務", "kind": "task", "owner_user_id": yu_id,
    }).status_code == 201
    workflow = client.get("/workflows").json()["items"][0]
    hidden = client.post("/projects/from-workflow", json={
        "workflow_id": workflow["id"], "title": "隱藏閘門",
    }).json()
    hidden_detail = client.get(f"/projects/{hidden['id']}").json()
    assert hidden_detail["gates"]
    client.post("/auth/logout")
    login(client, username="ming")
    member_id = client.get("/auth/me").json()["user"]["id"]
    expected = {n["id"] for n in admin["nodes"] if n["owner_user_id"] == member_id}
    assert expected
    detail = client.get(f"/projects/{project['id']}").json()
    assert {n["id"] for n in detail["nodes"]} == expected
    restricted = client.get(f"/projects/{hidden['id']}").json()
    assert restricted["nodes"] == []
    assert restricted["gates"] == []
    for username in ["yu", "chen", "lin", "owner"]:
        client.post("/auth/logout")
        login(client, username=username)
        detail = client.get(f"/projects/{hidden['id']}").json()
        assert {n['id'] for n in detail['nodes']} == {n['id'] for n in hidden_detail['nodes']}
        assert detail['gates'] == hidden_detail['gates']
