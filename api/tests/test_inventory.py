from uuid import uuid4
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import InventoryMovement, AuditLog
from test_operations import create, PAYLOAD
from test_projects_nodes import login
from test_report_lifecycle import switch


def setup(client):
    login(client)
    resource = create(client, category='resources', code='MAT', visibility='restricted').json()
    order = create(client, category='orders', code='PO', visibility='restricted').json()
    body = {'resource_id': resource['id'], 'quantity': '12.345', 'unit': 'kg', 'reason': '到貨驗收', 'request_id': str(uuid4())}
    return resource, order, body


def test_receipt_adjustment_history_and_retry(client, engine):
    resource, order, body = setup(client)
    path = '/operations/' + order['id'] + '/receipts'
    response = client.post(path, json=body)
    assert response.status_code == 200, response.text
    row = response.json()
    assert (row['quantity'], row['before'], row['after']) == ('12.345', '0.000', '12.345')
    assert row['order_label'].startswith('PO｜') and row['actor_name']
    assert client.post(path, json=body).json()['id'] == row['id']
    assert client.post(path, json={**body, 'quantity': '1'}).status_code == 409
    adj = client.post('/inventory/adjustments', json={**body, 'quantity': '-2.005', 'request_id': str(uuid4()), 'reason': '盤點短少'})
    assert adj.status_code == 200 and adj.json()['after'] == '10.340'
    # Subsequent title edits must not rewrite historical labels.
    client.put('/operations/' + order['id'], json={**PAYLOAD, 'category': 'orders', 'code': 'PO', 'title': '更名單據', 'expected_revision': 1})
    switch(client, 'yu')
    assert client.get('/inventory/resources/' + resource['id']).json() == {'resource_id': resource['id'], 'quantity': '10.340', 'unit': 'kg'}
    history = client.get('/inventory/movements?resource_id=' + resource['id']).json()
    assert history['total'] == 2
    assert history['items'][1]['order_label'] == row['order_label']
    assert client.get('/inventory/movements?order_id=' + order['id']).json()['total'] == 1
    assert client.get('/inventory/movements?limit=1&offset=1').json()['items'][0]['id'] == row['id']
    with Session(engine) as db:
        assert len(db.scalars(select(InventoryMovement)).all()) == 2
        assert len(db.scalars(select(AuditLog).where(AuditLog.action.like('inventory.%'))).all()) == 2


@pytest.mark.parametrize('change', [{'quantity': '0'}, {'quantity': '-1'}, {'quantity': '0.0001'}, {'quantity': 'NaN'}, {'quantity': 'Infinity'}, {'quantity': '1000000000'}, {'unit': ' '}, {'reason': ' '}, {'request_id': 'not-uuid'}])
def test_invalid_receipt_never_changes_stock(client, change):
    resource, order, body = setup(client)
    assert client.post('/operations/' + order['id'] + '/receipts', json={**body, **change}).status_code == 422
    assert client.get('/inventory/resources/' + resource['id']).json()['quantity'] == '0.000'
    assert client.get('/inventory/movements').json()['total'] == 0


def test_unit_insufficient_stock_and_classification(client):
    resource, order, body = setup(client)
    path = '/operations/' + order['id'] + '/receipts'
    assert client.post('/inventory/adjustments', json={**body, 'quantity': '-1'}).status_code == 409
    assert client.post(path, json=body).status_code == 200
    assert client.post(path, json={**body, 'unit': '件', 'request_id': str(uuid4())}).status_code == 409
    assert client.post('/inventory/adjustments', json={**body, 'quantity': '-20', 'request_id': str(uuid4())}).status_code == 409
    assert client.post('/operations/' + resource['id'] + '/receipts', json=body).status_code == 422
    assert client.post(path, json={**body, 'resource_id': order['id']}).status_code == 422
    assert client.get('/inventory/resources/' + order['id']).status_code == 422
    assert client.get('/inventory/movements?resource_id=' + order['id']).status_code == 422
    assert client.get('/inventory/resources/' + resource['id']).json()['quantity'] == '12.345'


@pytest.mark.parametrize('actor', ['ming', 'chen', 'lin'])
def test_stock_requires_management_role(client, actor):
    resource, order, body = setup(client)
    client.post('/operations/' + order['id'] + '/receipts', json=body)
    switch(client, actor)
    for url in ['/inventory/movements', '/inventory/resources/' + resource['id']]:
        assert client.get(url).status_code == 403
    assert client.post('/operations/' + order['id'] + '/receipts', json=body).status_code == 403
    assert client.post('/inventory/adjustments', json=body).status_code == 403
    assert '到貨驗收' not in client.get('/audit-logs').text


def test_cross_company_isolation(client):
    resource, order, body = setup(client)
    client.post('/operations/' + order['id'] + '/receipts', json=body)
    client.post('/auth/logout'); login(client, 'electronics', 'elaine')
    assert client.get('/inventory/movements').json()['total'] == 0
    assert client.get('/inventory/resources/' + resource['id']).status_code == 404
    assert client.get('/inventory/movements?order_id=' + order['id']).status_code == 404
    assert client.post('/operations/' + order['id'] + '/receipts', json=body).status_code == 404
    assert client.post('/inventory/adjustments', json=body).status_code == 404


def test_audit_failure_rolls_back_balance_and_history(client, monkeypatch):
    resource, order, body = setup(client)
    from app.routes import inventory
    def fail(*args, **kwargs):
        raise RuntimeError('audit failure')
    monkeypatch.setattr(inventory, 'log_audit', fail)
    with pytest.raises(RuntimeError, match='audit failure'):
        client.post('/operations/' + order['id'] + '/receipts', json=body)
    assert client.get('/inventory/resources/' + resource['id']).json()['quantity'] == '0.000'
    assert client.get('/inventory/movements').json()['total'] == 0
