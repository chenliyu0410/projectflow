from uuid import uuid4
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import AuditLog, InventoryMovement, WorkOrder
from test_operations import create
from test_projects_nodes import login
from test_report_lifecycle import switch
from test_work_stock import arrange


def planned(client, quantity='10'):
    raw, work, product, body = arrange(client)
    path = '/operations/' + work['id']
    saved = client.put(path + '/production/plan', json={'expected_revision': 0, 'product_id': product['id'], 'quantity': quantity, 'unit': '件', 'note': '首批試產'})
    assert saved.status_code == 200, saved.text
    return raw, work, product, body, path, saved.json()


def post(client, path, kind, resource, quantity, unit='件', request_id=None):
    return client.post(f'{path}/{kind}', json={'resource_id': resource['id'], 'quantity': quantity, 'unit': unit,
        'reason': '生產', 'request_id': request_id or str(uuid4())})


def test_plan_issue_and_batch_completion_progress(client, engine):
    raw, work, product, body, path, saved = planned(client)
    assert (saved['status'], saved['status_label'], saved['planned'], saved['completed'], saved['remaining']) == ('planned', '待生產', '10.000', '0.000', '10.000')
    assert saved['product']['code'] == 'FG' and saved['note'] == '首批試產'
    assert post(client, path, 'issues', raw, '2.005', 'kg').status_code == 200
    assert post(client, path, 'issues', raw, '1', 'kg').status_code == 200
    detail = client.get(path + '/production').json()
    assert detail['status_label'] == '生產中'
    assert [(row['code'], row['unit'], row['quantity']) for row in detail['issued']] == [('MAT', 'kg', '3.005')]
    request_id = str(uuid4())
    first = post(client, path, 'completions', product, '4', request_id=request_id)
    assert first.status_code == 200 and first.json()['counted_in_plan'] is True
    assert post(client, path, 'completions', product, '4', request_id=request_id).json()['id'] == first.json()['id']
    assert post(client, path, 'completions', product, '6.001').json()['detail'] == '超過計畫產量，請先調整計畫產量'
    assert post(client, path, 'completions', raw, '1', 'kg').json()['detail'] == '完工品項須為工單指定成品'
    assert post(client, path, 'completions', product, '1', 'kg').json()['detail'] == '完工單位須與工單計畫一致'
    assert post(client, path, 'completions', product, '6').status_code == 200
    detail = client.get(path + '/production').json()
    assert (detail['status'], detail['status_label'], detail['completed'], detail['remaining']) == ('completed', '已達計畫產量', '10.000', '0.000')
    # A retry after reaching the plan returns the original entry instead of failing or counting again.
    assert post(client, path, 'completions', product, '4', request_id=request_id).json()['id'] == first.json()['id']
    listing = client.get('/operations?category=work').json()['items']
    assert listing[0]['production'] == {'status': 'completed', 'label': '已達計畫產量', 'unit': '件', 'planned': '10.000', 'completed': '10.000'}
    assert client.get('/inventory/resources/' + product['id']).json()['quantity'] == '10.000'
    assert client.get('/inventory/resources/' + raw['id']).json()['quantity'] == '9.340'
    with Session(engine) as db:
        assert len(db.scalars(select(InventoryMovement).where(InventoryMovement.counted_in_plan.is_(True))).all()) == 2
        assert db.scalars(select(AuditLog).where(AuditLog.action == 'production.plan')).one().payload['after']['revision'] == 1


def test_close_blocks_postings_and_plan_until_reopened(client, engine):
    raw, work, product, body, path, saved = planned(client)
    request_id = str(uuid4())
    first = post(client, path, 'completions', product, '1', request_id=request_id)
    assert client.post(path + '/production/close', json={'expected_revision': 0, 'reason': '停產'}).status_code == 409
    closed = client.post(path + '/production/close', json={'expected_revision': 1, 'reason': '原料品質異常，停止試產'})
    assert closed.status_code == 200, closed.text
    assert (closed.json()['status_label'], closed.json()['close_reason'], closed.json()['revision']) == ('已結案', '原料品質異常，停止試產', 2)
    assert closed.json()['closed_by']
    assert post(client, path, 'issues', raw, '1', 'kg').json()['detail'] == '工單已結案，不能領料、完工或修改計畫'
    assert post(client, path, 'completions', product, '1').status_code == 409
    assert post(client, path, 'completions', product, '1', request_id=request_id).json()['id'] == first.json()['id']
    plan = {'expected_revision': 2, 'product_id': product['id'], 'quantity': '10', 'unit': '件'}
    assert client.put(path + '/production/plan', json=plan).status_code == 409
    assert client.post(path + '/production/close', json={'expected_revision': 2, 'reason': '再結案'}).status_code == 409
    assert client.get('/operations?category=work').json()['items'][0]['production']['label'] == '已結案'
    reopened = client.post(path + '/production/reopen', json={'expected_revision': 2, 'reason': '更換原料後續產'})
    assert reopened.json()['status_label'] == '生產中' and reopened.json()['closed_at'] is None
    assert client.post(path + '/production/reopen', json={'expected_revision': 3, 'reason': '重複'}).json()['detail'] == '工單尚未結案'
    assert post(client, path, 'issues', raw, '1', 'kg').status_code == 200
    with Session(engine) as db:
        actions = [row.action for row in db.scalars(select(AuditLog).where(AuditLog.action.like('production.%')).order_by(AuditLog.created_at))]
        assert actions == ['production.plan', 'production.close', 'production.reopen']


def test_plan_is_protected_after_completion_and_editable_before(client):
    raw, work, product, body, path, saved = planned(client)
    def put(revision, **change):
        return client.put(path + '/production/plan', json={'expected_revision': revision, 'product_id': product['id'], 'quantity': '10', 'unit': '件', **change})
    # Before any completion the product may change, but must use its existing stock unit.
    assert put(1, product_id=raw['id']).json()['detail'] == '計畫單位須與成品既有庫存單位一致'
    switched = put(1, product_id=raw['id'], unit='kg')
    assert switched.status_code == 200 and switched.json()['product']['code'] == 'MAT'
    assert put(2).status_code == 200
    post(client, path, 'completions', product, '4')
    assert put(3, product_id=raw['id'], unit='kg').json()['detail'] == '已有完工的計畫不可更換成品或單位'
    assert put(3, unit='箱').json()['detail'] == '已有完工的計畫不可更換成品或單位'
    assert put(3, quantity='3.999').json()['detail'] == '計畫產量不可少於已完工數量'
    assert put(2).json()['detail'] == '工單計畫已變更，請重新載入'
    shrunk = put(3, quantity='4', note='剩餘改下批')
    assert (shrunk.json()['status'], shrunk.json()['remaining'], shrunk.json()['note'], shrunk.json()['revision']) == ('completed', '0.000', '剩餘改下批', 4)


def test_plan_validation(client):
    raw, work, product, body = arrange(client)
    path = '/operations/' + work['id'] + '/production/plan'
    plan = {'expected_revision': 0, 'product_id': product['id'], 'quantity': '1', 'unit': '件'}
    for change in [{'quantity': '0'}, {'quantity': '-1'}, {'quantity': '0.0001'}, {'quantity': 'NaN'}, {'unit': ' '}, {'extra': 1}]:
        assert client.put(path, json={**plan, **change}).status_code == 422
    assert client.put(path, json={**plan, 'product_id': work['id']}).status_code == 422
    order = create(client, category='orders', code='PO-X').json()
    assert client.put('/operations/' + order['id'] + '/production/plan', json=plan).status_code == 422
    assert client.get('/operations/' + raw['id'] + '/production').status_code == 422
    assert client.get('/operations/' + work['id'] + '/production').json()['revision'] == 0


def test_unplanned_work_keeps_free_postings_and_reports_unlinked(client):
    raw, work, product, body = arrange(client)
    path = '/operations/' + work['id']
    assert post(client, path, 'completions', product, '2').status_code == 200
    assert post(client, path, 'completions', raw, '1', 'kg').status_code == 200
    detail = client.get(path + '/production').json()
    assert (detail['status'], detail['unlinked_completions'], detail['product']) == ('no_plan', 2, None)
    saved = client.put(path + '/production/plan', json={'expected_revision': 0, 'product_id': product['id'], 'quantity': '5', 'unit': '件'}).json()
    # Earlier free completions are not guessed into the plan.
    assert (saved['completed'], saved['unlinked_completions'], saved['status']) == ('0.000', 2, 'in_progress')


@pytest.mark.parametrize('actor', ['ming', 'chen', 'lin'])
def test_production_requires_management_role(client, actor):
    raw, work, product, body, path, saved = planned(client)
    switch(client, actor)
    assert client.get(path + '/production').status_code == 403
    assert client.put(path + '/production/plan', json={'expected_revision': 1, 'product_id': product['id'], 'quantity': '1', 'unit': '件'}).status_code == 403
    assert client.post(path + '/production/close', json={'expected_revision': 1, 'reason': 'x'}).status_code == 403
    assert client.post(path + '/production/reopen', json={'expected_revision': 1, 'reason': 'x'}).status_code == 403
    assert all('production' not in item for item in client.get('/operations?category=work').json()['items'])


def test_cross_company_isolation(client):
    raw, work, product, body, path, saved = planned(client)
    client.post('/auth/logout'); login(client, 'electronics', 'elaine')
    assert client.get(path + '/production').status_code == 404
    assert client.post(path + '/production/close', json={'expected_revision': 1, 'reason': 'x'}).status_code == 404
    own = create(client, category='work', code='WO-E').json()
    stolen = client.put('/operations/' + own['id'] + '/production/plan', json={'expected_revision': 0, 'product_id': product['id'], 'quantity': '1', 'unit': '件'})
    assert stolen.status_code == 404


def test_audit_failure_rolls_back_plan_and_completion(client, engine, monkeypatch):
    raw, work, product, body, path, saved = planned(client)
    from app.routes import inventory, production
    def fail(*args, **kwargs):
        raise RuntimeError('audit failure')
    monkeypatch.setattr(production, 'log_audit', fail)
    with pytest.raises(RuntimeError, match='audit failure'):
        client.post(path + '/production/close', json={'expected_revision': 1, 'reason': '停產'})
    monkeypatch.setattr(inventory, 'log_audit', fail)
    with pytest.raises(RuntimeError, match='audit failure'):
        post(client, path, 'completions', product, '1')
    detail = client.get(path + '/production').json()
    assert (detail['revision'], detail['status'], detail['completed']) == (1, 'planned', '0.000')
    with Session(engine) as db:
        assert db.scalars(select(WorkOrder)).one().completed_milli == 0
