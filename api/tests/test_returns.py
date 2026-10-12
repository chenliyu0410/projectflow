from uuid import uuid4
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import AuditLog, InventoryMovement
from test_inventory import setup
from test_operations import create
from test_projects_nodes import login
from test_purchase_lines import arrange as ordered, receive
from test_report_lifecycle import switch
from test_work_orders import planned, post as work_post
from test_work_stock import arrange as stocked


def give_back(client, path, resource, quantity, unit='kg', request_id=None):
    return client.post(path + '/returns', json={'resource_id': resource['id'], 'quantity': quantity, 'unit': unit,
        'reason': '品質不良退回', 'request_id': request_id or str(uuid4())})


def reverse(client, movement, reason='錯帳更正', request_id=None):
    return client.post(f"/inventory/movements/{movement['id']}/reversal", json={'reason': reason, 'request_id': request_id or str(uuid4())})


def stock(client, resource):
    return client.get('/inventory/resources/' + resource['id']).json()['quantity']


def test_purchase_return_reopens_outstanding_and_reversals_restore_lines(client, engine):
    flour, sugar, order, body, path, saved = ordered(client)
    flour_line = saved['lines'][0]['id']
    receive(client, path, flour, '10')
    receive(client, path, sugar, '2.5', unit='包')
    request_id = str(uuid4())
    returned = give_back(client, path, flour, '3', request_id=request_id)
    assert returned.status_code == 200, returned.text
    assert (returned.json()['kind'], returned.json()['quantity'], returned.json()['line_id'], returned.json()['after']) == ('return', '-3.000', flour_line, '7.000')
    assert give_back(client, path, flour, '3', request_id=request_id).json()['id'] == returned.json()['id']
    detail = client.get(path + '/purchase').json()
    line = detail['lines'][0]
    # The returned quantity is outstanding again, waiting for the supplier's replacement.
    assert (detail['status_label'], line['received'], line['remaining'], line['returned'], line['status']) == ('部分收貨', '7.000', '3.000', '3.000', 'partial')
    assert give_back(client, path, flour, '7.001').json()['detail'] == '超過已收數量，無法退貨'
    assert give_back(client, path, sugar, '1').json()['detail'] == '單位須與採購明細一致'
    other = create(client, category='resources', code='OTHER').json()
    assert give_back(client, path, other, '1').json()['detail'] == '此物料不在採購明細中'
    replacement = receive(client, path, flour, '3')
    assert client.get(path + '/purchase').json()['status_label'] == '已收齊'
    # Cancelling the return now would exceed the ordered quantity; cancel the wrong replacement first.
    assert reverse(client, returned.json()).json()['detail'] == '沖銷後已收數量會超出訂購或小於零，請先調整明細或沖銷相關退貨'
    undone = reverse(client, replacement.json())
    assert undone.status_code == 200, undone.text
    assert (undone.json()['kind'], undone.json()['reversal_of'], undone.json()['quantity'], undone.json()['line_id']) == ('reversal', replacement.json()['id'], '-3.000', flour_line)
    restored = reverse(client, returned.json())
    assert restored.status_code == 200 and restored.json()['quantity'] == '3.000'
    line = client.get(path + '/purchase').json()['lines'][0]
    assert (line['received'], line['returned'], line['status']) == ('10.000', '0.000', 'received')
    assert stock(client, flour) == '10.000'
    assert reverse(client, returned.json()).json()['detail'] == '此筆異動已沖銷'
    assert reverse(client, restored.json()).json()['detail'] == '沖銷紀錄不可再沖銷，請重新入帳'
    history = {row['id']: row for row in client.get('/inventory/movements?order_id=' + order['id']).json()['items']}
    assert history[returned.json()['id']]['reversed_by'] == restored.json()['id']
    assert history[restored.json()['id']]['reversed_kind'] == 'return'
    assert history[replacement.json()['id']]['reversed_by'] == undone.json()['id']
    with Session(engine) as db:
        actions = [row.action for row in db.scalars(select(AuditLog).where(AuditLog.action.in_(['inventory.return', 'inventory.reversal'])).order_by(AuditLog.created_at))]
        assert actions == ['inventory.return', 'inventory.reversal', 'inventory.reversal']


def test_closed_order_refuses_returns_and_reversals_until_reopened(client):
    flour, sugar, order, body, path, saved = ordered(client)
    received = receive(client, path, flour, '5').json()
    client.post(path + '/purchase/close', json={'expected_revision': 1, 'reason': '供應商停產'})
    assert give_back(client, path, flour, '1').json()['detail'] == '採購單已結案，請先重新開啟再退貨或沖銷'
    assert reverse(client, received).json()['detail'] == '採購單已結案，請先重新開啟再退貨或沖銷'
    client.post(path + '/purchase/reopen', json={'expected_revision': 2, 'reason': '處理退貨'})
    assert give_back(client, path, flour, '1').status_code == 200
    assert reverse(client, received).json()['detail'] == '沖銷後已收數量會超出訂購或小於零，請先調整明細或沖銷相關退貨'
    assert client.get(path + '/purchase').json()['lines'][0]['received'] == '4.000'


def test_orders_without_lines_return_at_most_their_free_receipts(client):
    flour, order, body = setup(client)
    path = '/operations/' + order['id']
    received = client.post(path + '/receipts', json=body).json()
    assert give_back(client, path, flour, '12.346').json()['detail'] == '超過已收數量，無法退貨'
    returned = give_back(client, path, flour, '2.345')
    assert returned.status_code == 200 and returned.json()['line_id'] is None
    assert reverse(client, received).json()['detail'] == '沖銷後淨收貨會小於零，請先沖銷相關退貨'
    assert reverse(client, returned.json()).status_code == 200
    assert reverse(client, received).status_code == 200
    assert stock(client, flour) == '0.000'
    assert client.get(path + '/purchase').json()['unlinked_receipts'] == 1


def test_returned_lines_stay_locked(client):
    flour, sugar, order, body, path, saved = ordered(client)
    receive(client, path, flour, '2')
    give_back(client, path, flour, '2')
    detail = client.get(path + '/purchase').json()
    assert [(line['received'], line['locked']) for line in detail['lines']] == [('0.000', True), ('0.000', False)]
    # A line referenced by the ledger keeps its identity even at zero received.
    assert client.put(path + '/purchase/lines', json={'expected_revision': 1, 'lines': []}).json()['detail'] == '已有收貨的明細不可刪除或更換物料、單位'
    keep = {'id': detail['lines'][0]['id'], 'resource_id': flour['id'], 'quantity': '1', 'unit': 'kg'}
    shrunk = client.put(path + '/purchase/lines', json={'expected_revision': 1, 'lines': [keep]})
    assert shrunk.status_code == 200 and [line['id'] for line in shrunk.json()['lines']] == [keep['id']]


def test_material_returns_and_work_order_reversals(client, engine):
    raw, work, product, body, path, saved = planned(client)
    issued = work_post(client, path, 'issues', raw, '3', 'kg').json()
    request_id = str(uuid4())
    back = work_post(client, path, 'issue-returns', raw, '1', 'kg', request_id=request_id)
    assert back.status_code == 200, back.text
    assert (back.json()['kind'], back.json()['quantity'], back.json()['work_id']) == ('issue_return', '1.000', work['id'])
    assert work_post(client, path, 'issue-returns', raw, '1', 'kg', request_id=request_id).json()['id'] == back.json()['id']
    detail = client.get(path + '/production').json()
    assert [(row['code'], row['quantity'], row['returned']) for row in detail['issued']] == [('MAT', '2.000', '1.000')]
    assert work_post(client, path, 'issue-returns', raw, '2.001', 'kg').json()['detail'] == '超過本工單淨領料，無法退料'
    assert work_post(client, path, 'issue-returns', product, '1').json()['detail'] == '超過本工單淨領料，無法退料'
    done = work_post(client, path, 'completions', product, '4').json()
    undone = reverse(client, done)
    assert undone.status_code == 200, undone.text
    assert (undone.json()['counted_in_plan'], undone.json()['quantity']) == (True, '-4.000')
    detail = client.get(path + '/production').json()
    assert (detail['completed'], detail['remaining'], detail['status_label']) == ('0.000', '10.000', '生產中')
    assert stock(client, product) == '0.000'
    # Net issued may not go below zero: cancel the material return before the issue it came from.
    assert reverse(client, issued).json()['detail'] == '沖銷後淨領料會小於零，請先沖銷相關退料'
    assert reverse(client, back.json()).status_code == 200
    assert reverse(client, issued).status_code == 200
    detail = client.get(path + '/production').json()
    assert [(row['quantity'], row['returned']) for row in detail['issued']] == [('0.000', '0.000')]
    assert stock(client, raw) == '12.345'
    client.post(path + '/production/close', json={'expected_revision': 1, 'reason': '停產'})
    assert work_post(client, path, 'issue-returns', raw, '1', 'kg').json()['detail'] == '工單已結案，請先重新開啟再退料或沖銷'
    again = work_post(client, path, 'completions', product, '1')
    assert again.status_code == 409
    with Session(engine) as db:
        assert db.scalars(select(AuditLog).where(AuditLog.action == 'inventory.issue_return')).one().payload['kind'] == 'issue_return'


def test_closed_work_order_refuses_reversals(client):
    raw, work, product, body, path, saved = planned(client)
    issued = work_post(client, path, 'issues', raw, '1', 'kg').json()
    client.post(path + '/production/close', json={'expected_revision': 1, 'reason': '停產'})
    assert reverse(client, issued).json()['detail'] == '工單已結案，請先重新開啟再退料或沖銷'
    client.post(path + '/production/reopen', json={'expected_revision': 2, 'reason': '更正'})
    assert reverse(client, issued).status_code == 200


def test_adjustment_reversal_and_stock_shortage(client):
    raw, work, product, body = stocked(client)
    adjusted = client.post('/inventory/adjustments', json={**body, 'quantity': '-2.345', 'reason': '盤點短少'}).json()
    assert reverse(client, adjusted).json()['after'] == '12.345'
    receipt = client.get('/inventory/movements?resource_id=' + raw['id']).json()['items'][-1]
    assert receipt['kind'] == 'receipt'
    work_post(client, '/operations/' + work['id'], 'issues', raw, '12', 'kg')
    assert reverse(client, receipt).json()['detail'] == '庫存不足，無法沖銷'
    assert stock(client, raw) == '0.345'


def test_reversal_retries_and_reused_request_ids(client):
    raw, work, product, body = stocked(client)
    adjusted = client.post('/inventory/adjustments', json={**body, 'quantity': '1', 'reason': '盤點'}).json()
    request_id = str(uuid4())
    first = reverse(client, adjusted, request_id=request_id)
    assert reverse(client, adjusted, request_id=request_id).json()['id'] == first.json()['id']
    assert reverse(client, adjusted, reason='其他理由', request_id=request_id).json()['detail'] == '同一操作識別碼不可重用於不同內容'
    other = client.post('/inventory/adjustments', json={**body, 'quantity': '1', 'reason': '盤點', 'request_id': str(uuid4())}).json()
    assert reverse(client, other, request_id=adjusted['request_id']).json()['detail'] == '同一操作識別碼不可重用於不同內容'
    assert reverse(client, {'id': str(uuid4())}).status_code == 404
    for change in [{'reason': ' '}, {'extra': 1}, {'request_id': 'x'}]:
        assert client.post(f"/inventory/movements/{other['id']}/reversal", json={'reason': 'r', 'request_id': str(uuid4()), **change}).status_code == 422
    for q in ['0', '-1', '0.0001']:
        assert client.post('/operations/' + work['id'] + '/issue-returns', json={**body, 'quantity': q}).status_code == 422


@pytest.mark.parametrize('actor', ['ming', 'chen', 'lin'])
def test_returns_and_reversals_require_management_role(client, actor):
    flour, sugar, order, body, path, saved = ordered(client)
    received = receive(client, path, flour, '1').json()
    switch(client, actor)
    assert give_back(client, path, flour, '1').status_code == 403
    assert client.post('/operations/' + order['id'] + '/issue-returns', json={**body, 'resource_id': flour['id']}).status_code == 403
    assert reverse(client, received).status_code == 403


def test_returns_and_reversals_are_company_isolated(client):
    flour, sugar, order, body, path, saved = ordered(client)
    received = receive(client, path, flour, '1').json()
    client.post('/auth/logout'); login(client, 'electronics', 'elaine')
    assert reverse(client, received).status_code == 404
    assert give_back(client, path, flour, '1').status_code == 404
    switch(client, 'yu')
    assert client.get(path + '/purchase').json()['lines'][0]['received'] == '1.000'


def test_audit_failure_rolls_back_return_and_reversal(client, engine, monkeypatch):
    flour, sugar, order, body, path, saved = ordered(client)
    received = receive(client, path, flour, '4').json()
    from app.routes import inventory
    def fail(*args, **kwargs):
        raise RuntimeError('audit failure')
    monkeypatch.setattr(inventory, 'log_audit', fail)
    with pytest.raises(RuntimeError, match='audit failure'):
        give_back(client, path, flour, '1')
    with pytest.raises(RuntimeError, match='audit failure'):
        reverse(client, received)
    assert client.get(path + '/purchase').json()['lines'][0]['received'] == '4.000'
    assert stock(client, flour) == '4.000'
    with Session(engine) as db:
        assert db.scalars(select(InventoryMovement).where(InventoryMovement.kind.in_(['return', 'reversal']))).all() == []
