from uuid import uuid4
import pytest
from test_inventory import setup
from test_operations import create, PAYLOAD
from test_projects_nodes import login
from test_report_lifecycle import switch


def arrange(client):
    resource, order, body = setup(client)
    client.post('/operations/' + order['id'] + '/receipts', json=body)
    work = create(client, category='work', code='WO').json()
    product = create(client, category='resources', code='FG').json()
    return resource, work, product, {**body, 'request_id': str(uuid4())}


def test_issue_and_completion_persist_separate_stock_and_source(client):
    raw, work, product, body = arrange(client)
    path = '/operations/' + work['id']
    issued = client.post(path + '/issues', json={**body, 'quantity': '2.005'})
    assert issued.status_code == 200, issued.text
    assert issued.json()['quantity'] == '-2.005' and issued.json()['after'] == '10.340'
    assert client.post(path + '/issues', json={**body, 'quantity': '2.005'}).json()['id'] == issued.json()['id']
    assert client.post(path + '/completions', json={**body, 'quantity': '2.005'}).status_code == 409
    payload = {**body, 'resource_id': product['id'], 'quantity': '5', 'unit': '件', 'request_id': str(uuid4())}
    done = client.post(path + '/completions', json=payload)
    assert done.status_code == 200 and done.json()['after'] == '5.000'
    assert client.post(path + '/completions', json=payload).json()['id'] == done.json()['id']
    assert client.post(path + '/completions', json={**payload, 'request_id': str(uuid4())}).json()['after'] == '10.000'
    client.put(path, json={**PAYLOAD, 'category': 'work', 'code': 'WO', 'title': '新工單名稱', 'expected_revision': 1})
    switch(client, 'yu')
    history = client.get('/inventory/movements?work_id=' + work['id']).json()
    assert history['total'] == 3
    assert all(row['work_label'] == issued.json()['work_label'] for row in history['items'])
    assert all(row['order_id'] is None for row in history['items'])
    assert client.get('/inventory/resources/' + raw['id']).json()['quantity'] == '10.340'
    assert client.get('/inventory/resources/' + product['id']).json()['quantity'] == '10.000'


@pytest.mark.parametrize('endpoint', ['issues', 'completions'])
def test_work_validation_permissions_and_transaction_failure(client, monkeypatch, endpoint):
    raw, work, product, body = arrange(client)
    path = '/operations/' + work['id'] + '/' + endpoint
    for q in ['0', '-1', '0.0001', 'NaN']:
        assert client.post(path, json={**body, 'quantity': q}).status_code == 422
    assert client.post('/operations/' + raw['id'] + '/' + endpoint, json=body).status_code == 422
    assert client.post(path, json={**body, 'resource_id': work['id']}).status_code == 422
    if endpoint == 'issues':
        assert client.post(path, json={**body, 'quantity': '20'}).status_code == 409
        assert client.post(path, json={**body, 'resource_id': product['id']}).status_code == 409
    assert client.post(path, json={**body, 'unit': '件'}).status_code == 409
    for actor in ['ming', 'chen', 'lin']:
        switch(client, actor)
        assert client.post(path, json=body).status_code == 403
        assert client.get('/inventory/movements?work_id=' + work['id']).status_code == 403
    client.post('/auth/logout'); login(client, 'electronics', 'elaine')
    assert client.post(path, json=body).status_code == 404
    assert client.get('/inventory/movements?work_id=' + work['id']).status_code == 404
    foreign = create(client, category='work').json()
    switch(client, 'yu')
    assert client.post('/operations/' + foreign['id'] + '/' + endpoint, json=body).status_code == 404
    from app.routes import inventory
    def fail(*args, **kwargs): raise RuntimeError('audit failure')
    monkeypatch.setattr(inventory, 'log_audit', fail)
    with pytest.raises(RuntimeError, match='audit failure'):
        client.post(path, json=body)
    assert client.get('/inventory/resources/' + raw['id']).json()['quantity'] == '12.345'
    assert client.get('/inventory/movements?work_id=' + work['id']).json()['total'] == 0
