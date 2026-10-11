from uuid import uuid4
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import AuditLog, InventoryMovement, PurchaseOrderLine
from test_inventory import setup
from test_operations import create
from test_projects_nodes import login
from test_report_lifecycle import switch


def arrange(client):
    flour, order, body = setup(client)
    sugar = create(client, category='resources', code='SUGAR').json()
    path = '/operations/' + order['id']
    lines = [{'resource_id': flour['id'], 'quantity': '10', 'unit': 'kg', 'note': '首批'},
             {'resource_id': sugar['id'], 'quantity': '2.5', 'unit': '包'}]
    saved = client.put(path + '/purchase/lines', json={'expected_revision': 0, 'lines': lines})
    assert saved.status_code == 200, saved.text
    return flour, sugar, order, body, path, saved.json()


def receive(client, path, resource, quantity, unit='kg', request_id=None):
    return client.post(path + '/receipts', json={'resource_id': resource['id'], 'quantity': quantity, 'unit': unit,
        'reason': '到貨', 'request_id': request_id or str(uuid4())})


def test_partial_receipts_progress_to_received_and_survive_reload(client, engine):
    flour, sugar, order, body, path, saved = arrange(client)
    assert (saved['revision'], saved['status'], saved['status_label']) == (1, 'pending', '待收貨')
    assert [(l['resource_code'], l['ordered'], l['received'], l['remaining'], l['status']) for l in saved['lines']] == [
        ('MAT', '10.000', '0.000', '10.000', 'pending'), ('SUGAR', '2.500', '0.000', '2.500', 'pending')]
    request_id = str(uuid4())
    first = receive(client, path, flour, '4.25', request_id=request_id)
    assert first.status_code == 200, first.text
    assert first.json()['line_id'] == saved['lines'][0]['id']
    assert receive(client, path, flour, '4.25', request_id=request_id).json()['id'] == first.json()['id']
    detail = client.get(path + '/purchase').json()
    assert (detail['status_label'], detail['lines'][0]['received'], detail['lines'][0]['remaining']) == ('部分收貨', '4.250', '5.750')
    over = receive(client, path, flour, '5.751')
    assert over.status_code == 409 and over.json()['detail'] == '超過未收數量，請先確認訂購數量'
    assert receive(client, path, flour, '5.75').status_code == 200
    assert receive(client, path, sugar, '2.5', unit='包').status_code == 200
    detail = client.get(path + '/purchase').json()
    assert detail['status'] == 'received' and all(line['remaining'] == '0.000' for line in detail['lines'])
    assert receive(client, path, sugar, '0.001', unit='包').status_code == 409
    listing = client.get('/operations?category=orders').json()['items']
    assert listing[0]['receiving'] == {'status': 'received', 'label': '已收齊', 'lines': 2, 'received_lines': 2}
    assert client.get('/inventory/resources/' + flour['id']).json()['quantity'] == '10.000'
    with Session(engine) as db:
        assert len(db.scalars(select(InventoryMovement).where(InventoryMovement.line_id.is_not(None))).all()) == 3
        assert db.scalars(select(AuditLog).where(AuditLog.action == 'purchase.lines')).one().payload['after']['revision'] == 1


def test_receipts_must_match_listed_item_and_unit(client):
    flour, sugar, order, body, path, saved = arrange(client)
    other = create(client, category='resources', code='OTHER').json()
    missing = receive(client, path, other, '1')
    assert missing.status_code == 409 and missing.json()['detail'] == '此物料不在採購明細中'
    assert receive(client, path, flour, '1', unit='g').json()['detail'] == '單位須與採購明細一致'
    assert client.get('/inventory/movements?order_id=' + order['id']).json()['total'] == 0


def test_close_blocks_receipts_and_edits_until_reopened(client, engine):
    flour, sugar, order, body, path, saved = arrange(client)
    receive(client, path, flour, '3')
    assert client.post(path + '/purchase/close', json={'expected_revision': 0, 'reason': '短交'}).status_code == 409
    closed = client.post(path + '/purchase/close', json={'expected_revision': 1, 'reason': '供應商短交，剩餘取消'})
    assert closed.status_code == 200, closed.text
    assert (closed.json()['status_label'], closed.json()['close_reason'], closed.json()['revision']) == ('已結案', '供應商短交，剩餘取消', 2)
    assert closed.json()['closed_by']
    assert receive(client, path, flour, '1').json()['detail'] == '採購單已結案，不能收貨或修改明細'
    assert client.put(path + '/purchase/lines', json={'expected_revision': 2, 'lines': []}).status_code == 409
    assert client.post(path + '/purchase/close', json={'expected_revision': 2, 'reason': '再結案'}).status_code == 409
    assert client.get('/operations?category=orders').json()['items'][0]['receiving']['label'] == '已結案'
    reopened = client.post(path + '/purchase/reopen', json={'expected_revision': 2, 'reason': '供應商補交'})
    assert reopened.json()['status_label'] == '部分收貨' and reopened.json()['closed_at'] is None
    assert client.post(path + '/purchase/reopen', json={'expected_revision': 3, 'reason': '重複'}).status_code == 409
    assert receive(client, path, flour, '1').status_code == 200
    with Session(engine) as db:
        actions = [row.action for row in db.scalars(select(AuditLog).where(AuditLog.action.like('purchase.%')).order_by(AuditLog.created_at))]
        assert actions == ['purchase.lines', 'purchase.close', 'purchase.reopen']


def test_received_lines_are_protected_and_unreceived_lines_editable(client):
    flour, sugar, order, body, path, saved = arrange(client)
    receive(client, path, flour, '4')
    flour_line, sugar_line = saved['lines']
    def put(lines, revision=1):
        return client.put(path + '/purchase/lines', json={'expected_revision': revision, 'lines': lines})
    keep = {'id': flour_line['id'], 'resource_id': flour['id'], 'quantity': '10', 'unit': 'kg'}
    assert put([]).json()['detail'] == '已有收貨的明細不可刪除或更換物料、單位'
    assert put([{**keep, 'unit': 'g'}]).json()['detail'] == '已有收貨的明細不可刪除或更換物料、單位'
    assert put([{**keep, 'resource_id': sugar['id'], 'unit': '包'}]).status_code == 409
    assert put([{**keep, 'quantity': '3.999'}]).json()['detail'] == '訂購數量不可少於已收數量'
    assert put([keep, {'resource_id': flour['id'], 'quantity': '1', 'unit': 'kg'}]).status_code == 422
    assert put([{**keep, 'id': str(uuid4())}]).json()['detail'] == '採購明細已變更，請重新載入'
    assert put([keep], revision=0).json()['detail'] == '採購明細已變更，請重新載入'
    # Remove the unreceived line, shrink the received one to exactly its receipts.
    shrunk = put([{**keep, 'quantity': '4', 'note': '其餘不交'}])
    assert shrunk.status_code == 200, shrunk.text
    assert [(l['id'], l['ordered'], l['note']) for l in shrunk.json()['lines']] == [(flour_line['id'], '4.000', '其餘不交')]
    assert shrunk.json()['status'] == 'received' and shrunk.json()['revision'] == 2
    readded = put([{'resource_id': sugar['id'], 'quantity': '1', 'unit': '包'}, {**keep, 'quantity': '4'}], revision=2)
    assert [l['resource_code'] for l in readded.json()['lines']] == ['SUGAR', 'MAT']
    assert readded.json()['status'] == 'partial'


def test_line_unit_must_match_existing_stock_and_validation(client):
    flour, order, body = setup(client)
    path = '/operations/' + order['id'] + '/purchase/lines'
    client.post('/inventory/adjustments', json={**body, 'quantity': '1'})
    line = {'resource_id': flour['id'], 'quantity': '1', 'unit': 'g'}
    assert client.put(path, json={'expected_revision': 0, 'lines': [line]}).json()['detail'] == '明細單位須與物料既有庫存單位一致'
    for change in [{'quantity': '0'}, {'quantity': '-1'}, {'quantity': '0.0001'}, {'quantity': 'NaN'}, {'unit': ' '}, {'extra': 1}]:
        assert client.put(path, json={'expected_revision': 0, 'lines': [{**line, 'unit': 'kg', **change}]}).status_code == 422
    assert client.put(path, json={'expected_revision': 0, 'lines': [{**line, 'unit': 'kg'}] * 51}).status_code == 422
    assert client.put(path, json={'expected_revision': 0, 'lines': [{**line, 'unit': 'kg', 'resource_id': order['id']}]}).status_code == 422
    assert client.put('/operations/' + flour['id'] + '/purchase/lines', json={'expected_revision': 0, 'lines': []}).status_code == 422
    assert client.get('/operations/' + order['id'] + '/purchase').json()['revision'] == 0


def test_orders_without_lines_keep_free_receipts_and_report_unlinked(client):
    flour, order, body = setup(client)
    path = '/operations/' + order['id']
    assert client.post(path + '/receipts', json=body).status_code == 200
    detail = client.get(path + '/purchase').json()
    assert (detail['status'], detail['unlinked_receipts'], detail['lines']) == ('no_lines', 1, [])
    saved = client.put(path + '/purchase/lines', json={'expected_revision': 0, 'lines': [{'resource_id': flour['id'], 'quantity': '5', 'unit': 'kg'}]}).json()
    # Earlier free receipts are not guessed into the new lines.
    assert (saved['lines'][0]['received'], saved['unlinked_receipts'], saved['status']) == ('0.000', 1, 'pending')


@pytest.mark.parametrize('actor', ['ming', 'chen', 'lin'])
def test_purchase_progress_requires_management_role(client, actor):
    flour, sugar, order, body, path, saved = arrange(client)
    internal = create(client, category='orders', code='PO-OPEN').json()
    switch(client, actor)
    assert client.get(path + '/purchase').status_code == 403
    assert client.get('/operations/' + internal['id'] + '/purchase').status_code == 403
    assert client.put('/operations/' + internal['id'] + '/purchase/lines', json={'expected_revision': 0, 'lines': []}).status_code == 403
    assert client.post('/operations/' + internal['id'] + '/purchase/close', json={'expected_revision': 0, 'reason': 'x'}).status_code == 403
    assert all('receiving' not in item for item in client.get('/operations?category=orders').json()['items'])


def test_cross_company_isolation(client):
    flour, sugar, order, body, path, saved = arrange(client)
    client.post('/auth/logout'); login(client, 'electronics', 'elaine')
    assert client.get(path + '/purchase').status_code == 404
    assert client.put(path + '/purchase/lines', json={'expected_revision': 1, 'lines': []}).status_code == 404
    assert client.post(path + '/purchase/close', json={'expected_revision': 1, 'reason': 'x'}).status_code == 404
    own = create(client, category='orders', code='PO-E').json()
    stolen = client.put('/operations/' + own['id'] + '/purchase/lines', json={'expected_revision': 0, 'lines': [{'resource_id': flour['id'], 'quantity': '1', 'unit': 'kg'}]})
    assert stolen.status_code == 404


def test_audit_failure_rolls_back_lines_and_receipt_progress(client, engine, monkeypatch):
    flour, sugar, order, body, path, saved = arrange(client)
    from app.routes import inventory, purchasing
    def fail(*args, **kwargs):
        raise RuntimeError('audit failure')
    monkeypatch.setattr(purchasing, 'log_audit', fail)
    with pytest.raises(RuntimeError, match='audit failure'):
        client.post(path + '/purchase/close', json={'expected_revision': 1, 'reason': '短交'})
    monkeypatch.setattr(inventory, 'log_audit', fail)
    with pytest.raises(RuntimeError, match='audit failure'):
        receive(client, path, flour, '1')
    detail = client.get(path + '/purchase').json()
    assert (detail['revision'], detail['status'], detail['lines'][0]['received']) == (1, 'pending', '0.000')
    with Session(engine) as db:
        assert all(line.received_milli == 0 for line in db.scalars(select(PurchaseOrderLine)))
