import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import AuditLog, Node
from test_operations import create, PAYLOAD
from test_projects_nodes import login
from test_report_lifecycle import setup, switch


@pytest.mark.parametrize('category', ['partners', 'orders', 'work'])
def test_save_live_reload_idempotence_unlink(client, engine, category):
    nid, pid, _ = setup(client, engine, 'yu')
    row = create(client, category=category).json()
    path = f'/projects/{pid}/operation-links'
    assert client.post(path, json={'record_id': row['id']}).json()['changed'] is True
    assert client.post(path, json={'record_id': row['id']}).json()['changed'] is False
    assert client.get(f'/nodes/{nid}/operation-links').json()['items'] == []
    assert client.put(f"/operations/{row['id']}", json={**PAYLOAD, 'category': category, 'title': '最新內容', 'expected_revision': 1}).status_code == 200
    switch(client, 'yu')
    assert client.get(path).json()['items'][0]['title'] == '最新內容'
    assert client.delete(path + '/' + row['id']).json()['changed'] is True
    assert client.get(path).json()['items'] == []
    assert client.get('/operations/' + row['id']).status_code == 200
    with Session(engine) as db:
        assert len(db.scalars(select(AuditLog).where(AuditLog.action.in_(['operations.link', 'operations.unlink']))).all()) == 2


def test_permissions_confidentiality_and_deleted_scope(client, engine):
    nid, pid, _ = setup(client, engine, 'yu')
    row = create(client).json()
    secret = create(client, code='SECRET', visibility='restricted').json()
    path = f'/nodes/{nid}/operation-links'
    for record in [row, secret]:
        assert client.post(path, json={'record_id': record['id']}).status_code == 200
    switch(client, 'ming')
    assert [r['id'] for r in client.get(path).json()['items']] == [row['id']]
    assert client.post(path, json={'record_id': secret['id']}).status_code == 404
    assert client.delete(path + '/' + secret['id']).status_code == 404
    assert client.delete(path + '/' + row['id']).status_code == 200
    assert client.post(f'/projects/{pid}/operation-links', json={'record_id': row['id']}).status_code == 403
    switch(client, 'lin')
    assert client.get(path).json()['can_manage'] is False
    assert client.post(path, json={'record_id': row['id']}).status_code == 403
    switch(client, 'yu')
    with Session(engine) as db:
        from app.models import now_utc
        db.get(Node, nid).deleted_at = now_utc(); db.commit()
    assert client.get(path).status_code == 404


def test_cross_company_and_unsupported_category(client, engine):
    nid, pid, _ = setup(client, engine, 'yu')
    row = create(client, category='resources').json()
    path = f'/projects/{pid}/operation-links'
    assert client.post(path, json={'record_id': row['id']}).status_code == 422
    assert client.get(path + f'?node_id={nid}').status_code == 422
    client.post('/auth/logout'); login(client, 'electronics', 'elaine')
    foreign = create(client).json()
    assert client.get(path).status_code == 404
    assert client.post(path, json={'record_id': foreign['id']}).status_code == 404
    switch(client, 'yu')
    assert client.post(path, json={'record_id': foreign['id']}).status_code == 404


def test_new_confidentiality_applies_to_existing_links(client, engine):
    nid, _, _ = setup(client, engine, 'yu')
    row = create(client).json(); path = f'/nodes/{nid}/operation-links'
    client.post(path, json={'record_id': row['id']})
    client.put('/operations/' + row['id'], json={**PAYLOAD, 'visibility': 'restricted', 'expected_revision': 1})
    switch(client, 'ming')
    assert client.get(path).json()['items'] == []
