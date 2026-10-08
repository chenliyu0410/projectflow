def login(client, org="food", username="yu", password=None):
    response = client.post("/auth/login", json={
        "organization_key": org,
        "username": username,
        "password": password or f"demo-{username}",
    })
    assert response.status_code == 200


def first_owned_node(client):
    project = client.get("/projects").json()["items"][0]
    nodes = client.get(f"/projects/{project['id']}").json()["nodes"]
    return nodes[0]


def test_submit_report_requires_can_work_and_writes_audit(client):
    login(client, "food", "ming", "demo-ming")
    node = first_owned_node(client)
    response = client.post(f"/nodes/{node['id']}/reports", json={"result": "達成", "summary": "已完成測試"})
    assert response.status_code == 201
    assert response.json()["status"] == "submitted"
    logs = client.get("/audit-logs").json()["items"]
    assert logs[0]["action"] == "report.submit"
    assert logs[0]["node_id"] == node["id"]


def test_readonly_cannot_submit_report(client):
    login(client, "food", "lin", "demo-lin")
    project = client.get("/projects").json()["items"][0]
    node = client.get(f"/projects/{project['id']}").json()["nodes"][0]
    response = client.post(f"/nodes/{node['id']}/reports", json={"result": "達成", "summary": "不應成功"})
    assert response.status_code == 403


def test_audit_logs_are_scoped_to_session_organization(client):
    login(client, "electronics", "elaine", "demo-elaine")
    electronics_project = client.post("/projects", json={"title": "電子稽核"}).json()
    assert electronics_project["title"] == "電子稽核"
    client.post("/auth/logout")
    login(client, "food", "yu")
    logs = client.get("/audit-logs").json()["items"]
    assert all(item["organization_key"] == "food" for item in logs)
    assert "電子稽核" not in str(logs)


def test_cross_company_node_cannot_receive_report(client):
    login(client, "electronics", "elaine", "demo-elaine")
    other_project = client.get("/projects").json()["items"][0]
    other_node = client.get(f"/projects/{other_project['id']}").json()["nodes"][0]
    client.post("/auth/logout")
    login(client, "food", "yu")
    response = client.post(f"/nodes/{other_node['id']}/reports", json={"result": "達成", "summary": "偷寫"})
    assert response.status_code == 404
