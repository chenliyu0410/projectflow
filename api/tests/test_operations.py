import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import OperationsRecord, AuditLog
from app.operations_import import import_records
from test_projects_nodes import login
from test_report_lifecycle import switch

PAYLOAD = {'category': 'partners', 'code': 'vendor-001', 'title': '正式供應商', 'status': '評估中',
    'visibility': 'internal', 'fields': [{'label': '窗口', 'value': '王先生'}]}


def create(client, **changes):
    return client.post('/operations', json={**PAYLOAD, **changes})


def test_create_edit_reload_and_audit(client, engine):
    login(client)
    response = create(client)
    assert response.status_code == 201, response.text
    row = response.json()
    assert row['code'] == 'VENDOR-001' and row['revision'] == 1 and row['source'] == 'native'
    edited = client.put(f"/operations/{row['id']}", json={**PAYLOAD, 'title': '修訂名稱', 'expected_revision': 1})
    assert edited.status_code == 200 and edited.json()['revision'] == 2
    switch(client, 'yu')
    assert client.get(f"/operations/{row['id']}").json()['title'] == '修訂名稱'
    assert client.get('/operations?q=修訂').json()['total'] == 1
    with Session(engine) as db:
        logs = db.scalars(select(AuditLog).where(AuditLog.action.like('operations.%')).order_by(AuditLog.created_at)).all()
        assert [log.action for log in logs] == ['operations.create', 'operations.update']
        assert logs[1].payload['before']['title'] == PAYLOAD['title']
        assert logs[1].payload['after']['title'] == '修訂名稱'


@pytest.mark.parametrize('actor', ['ming', 'chen', 'lin'])
def test_readonly_and_confidential_projections(client, actor):
    login(client)
    public = create(client).json()
    secret = create(client, code='SECRET', title='機密配方', visibility='restricted').json()
    switch(client, actor)
    assert client.get('/operations/catalog').json()['can_manage'] is False
    listing = client.get('/operations').json()
    assert listing['total'] == 1 and listing['items'][0]['id'] == public['id']
    assert client.get('/operations?q=SECRET').json()['total'] == 0
    assert client.get(f"/operations/{secret['id']}").status_code == 404
    assert create(client).status_code == 403
    assert client.put(f"/operations/{public['id']}", json={**PAYLOAD, 'expected_revision': 1}).status_code == 403
    assert '機密配方' not in client.get('/audit-logs').text


def test_cross_company_cannot_read_write_or_search(client):
    login(client)
    row = create(client).json()
    client.post('/auth/logout'); login(client, 'electronics', 'elaine')
    assert client.get('/operations').json()['items'] == []
    assert client.get(f"/operations/{row['id']}").status_code == 404
    assert client.put(f"/operations/{row['id']}", json={**PAYLOAD, 'expected_revision': 1}).status_code == 404
    assert create(client).status_code == 201  # same code in a different company


def test_stale_duplicate_and_category_change_preserve_data(client, engine):
    login(client)
    row = create(client).json()
    path = f"/operations/{row['id']}"
    assert create(client).status_code == 409
    assert client.put(path, json={**PAYLOAD, 'status': '合格', 'expected_revision': 1}).status_code == 200
    assert client.put(path, json={**PAYLOAD, 'status': '覆蓋', 'expected_revision': 1}).status_code == 409
    assert client.put(path, json={**PAYLOAD, 'category': 'orders', 'expected_revision': 2}).status_code == 422
    assert client.get(path).json()['status'] == '合格'
    with Session(engine) as db:
        assert len(db.scalars(select(OperationsRecord)).all()) == 1
        assert len(db.scalars(select(AuditLog).where(AuditLog.action.like('operations.%'))).all()) == 2


@pytest.mark.parametrize('change', [ {'title': ' '}, {'category': 'unknown'}, {'code': 'x'*81},
    {'fields': [{'label': '重複', 'value': 'a'}, {'label': '重複', 'value': 'b'}]},
    {'fields': [{'label': '', 'value': 'x'}]}, {'fields': [{'label': 'x', 'value': 'x'*4001}]},
    {'visibility': 'public'}, {'organization_id': 'other'}, {'source': 'showcase'} ], ids=['empty','category','code','duplicate-fields','empty-label','large-value','visibility','org','source'])
def test_validation(client, change):
    login(client)
    assert create(client, **change).status_code == 422
    assert client.get('/operations').json()['total'] == 0


def test_import_preserves_modified_records_and_source(client, engine):
    login(client)
    with Session(engine) as db:
        first = import_records(db)
    assert first['created'] > 0
    row = client.get('/operations').json()['items'][0]
    assert row['source'] == 'showcase'
    data = {key: row[key] for key in PAYLOAD}
    assert client.put(f"/operations/{row['id']}", json={**data, 'title': '保留我的修改', 'expected_revision': 1}).status_code == 200
    with Session(engine) as db:
        second = import_records(db)
    assert second == {'created': 0, 'skipped': first['created']}
    assert client.get(f"/operations/{row['id']}").json()['title'] == '保留我的修改'


def test_pagination_and_literal_search(client):
    login(client)
    for code in ['A', 'B', 'C']:
        assert create(client, code=code).status_code == 201
    page = client.get('/operations?limit=1&offset=1').json()
    assert page['total'] == 3 and page['items'][0]['code'] == 'B'
    assert client.get('/operations?q=%25').json()['total'] == 0
    assert client.get('/operations?category=unknown').status_code == 422
