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
