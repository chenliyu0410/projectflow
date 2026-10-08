import pytest

from test_projects_nodes import login


def seed_detail(client):
    project = client.get('/projects').json()['items'][0]
    return client.get(f"/projects/{project['id']}").json()


def workflow_project(client, title):
    workflow = client.get('/workflows').json()['items'][0]
    response = client.post('/projects/from-workflow', json={'workflow_id': workflow['id'], 'title': title})
    assert response.status_code == 201
    return client.get(f"/projects/{response.json()['id']}").json()


def test_department_member_report_and_unrelated_gate_contract(client):
    login(client)
    seed = seed_detail(client)
    own = next(n for n in seed['nodes'] if n['kind'] == 'task')
    unrelated = next(n for n in seed['nodes'] if n['kind'] == 'phase')
    project = workflow_project(client, '權限驗收')
    gate = project['gates'][0]
    client.post('/auth/logout')
    login(client, username='chen')
    assert client.patch(f"/nodes/{own['id']}/status", json={'status': 'doing'}).status_code == 200
    assert client.patch(f"/gates/{gate['id']}", json={'status': 'approved'}).status_code == 403
    client.post('/auth/logout')
    login(client, username='ming')
    assert client.patch(f"/nodes/{own['id']}/status", json={'status': 'review'}).status_code == 200
    report = client.post(f"/nodes/{own['id']}/reports", json={'result': 'pass', 'summary': '完成驗證'})
    assert report.status_code == 201
    logs = client.get('/audit-logs').json()['items']
    assert any(log['action'] == 'report.submit' and log['node_id'] == own['id']
               and log['payload']['report_id'] == report.json()['id'] for log in logs)
    assert all(log['organization_key'] == 'food' for log in logs)
    assert client.patch(f"/nodes/{unrelated['id']}/status", json={'status': 'doing'}).status_code == 403
    assert client.post(f"/nodes/{unrelated['id']}/reports", json={'result': 'pass', 'summary': '越權'}).status_code == 403
    client.post('/auth/logout')
    login(client)
    assert client.patch(f"/gates/{gate['id']}", json={'status': 'approved'}).status_code == 200


def test_readonly_all_business_writes_are_denied(client):
    login(client)
    project = workflow_project(client, '唯讀驗收')
    task = next(n for n in project['nodes'] if n['kind'] == 'task')
    client.post('/auth/logout')
    login(client, username='lin')
    assert client.patch(f"/nodes/{task['id']}/status", json={'status': 'doing'}).status_code == 403
    assert client.post(f"/nodes/{task['id']}/reports", json={'result': 'pass', 'summary': '唯讀'}).status_code == 403
    assert client.post('/projects', json={'title': '唯讀'}).status_code == 403
    assert client.post(f"/projects/{project['id']}/nodes", json={'title': '唯讀', 'kind': 'task'}).status_code == 403
    assert client.patch(f"/gates/{project['gates'][0]['id']}", json={'status': 'approved'}).status_code == 403


@pytest.mark.parametrize('username', ['yu', 'chen', 'ming', 'lin'])
def test_company_scope_cannot_be_forged(client, username):
    login(client, org='electronics', username='elaine')
    other = workflow_project(client, '跨公司驗收')
    node = next(n for n in other['nodes'] if n['kind'] == 'task')
    report = client.post(f"/nodes/{node['id']}/reports", json={'result': 'pass', 'summary': '電子公司'})
    assert report.status_code == 201
    report_id = report.json()['id']
    other_logs = {log['id'] for log in client.get('/audit-logs').json()['items']}
    client.post('/auth/logout')
    login(client, username=username)
    assert client.get(f"/projects/{other['id']}?organization_key=electronics").status_code == 404
    assert client.patch(f"/nodes/{node['id']}/status", json={'status': 'doing'}).status_code == 404
    assert client.post(f"/nodes/{node['id']}/reports", json={'result': 'pass', 'summary': '跨公司'}).status_code == 404
    assert client.patch(f"/gates/{other['gates'][0]['id']}", json={'status': 'approved'}).status_code == 404
    assert all(p['organization_key'] == 'food' for p in client.get('/projects?organization_key=electronics').json()['items'])
    logs = client.get('/audit-logs?organization_key=electronics').json()['items']
    assert not other_logs.intersection(log['id'] for log in logs)
    assert all(log['organization_key'] == 'food' and log['payload'].get('report_id') != report_id for log in logs)
