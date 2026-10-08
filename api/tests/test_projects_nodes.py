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


def test_readonly_owner_still_cannot_update_node_status(client):
    login(client, "food", "yu")
    project = client.get("/projects").json()["items"][0]
    me = client.get("/auth/me").json()
    # Create a node assigned to readonly user lin, then verify ownership alone is not enough.
    client.post("/auth/logout")
    login(client, "food", "lin", "demo-lin")
    readonly_id = client.get("/auth/me").json()["user"]["id"]
    client.post("/auth/logout")
    login(client, "food", "yu")
    created = client.post(f"/projects/{project['id']}/nodes", json={
        "title": "唯讀負責節點",
        "kind": "task",
        "owner_user_id": readonly_id,
    })
    assert created.status_code == 201
    node_id = created.json()["id"]
    client.post("/auth/logout")
    login(client, "food", "lin", "demo-lin")
    denied = client.patch(f"/nodes/{node_id}/status", json={"status": "doing"})
    assert denied.status_code == 403
    assert me["organization"]["key"] == "food"


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
