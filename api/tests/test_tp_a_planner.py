"""TP-A: weight/progress fields, weighted progress, parent completion rule, moving tasks, project records."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, Department, Node, NodeDependency, Project, TaskReport, User
from app.services.progress import percent, progress_map, project_progress
from test_projects_nodes import login

PAYLOAD = {'result': '達成', 'summary': '成果', 'finished_on': '2026-10-08', 'attachment_ids': []}


@pytest.fixture
def tree(client, engine):
    """Project `tp` owned by the project_owner user; ming owns the phase and most tasks, yu owns hidden `h`."""
    login(client)
    with Session(engine) as db:
        users = {u.username: u for u in db.scalars(select(User))}
        org = users['yu'].organization_id
        dept = db.scalars(select(Department).where(Department.head_user_id == users['chen'].id)).one()
        db.add_all([Project(id='tp', organization_id=org, title='規劃器專案', owner_user_id=users['owner'].id),
                    Project(id='tp2', organization_id=org, title='另一個專案', owner_user_id=users['owner'].id)])
        db.flush()
        rows = [('ph', 'tp', 'phase', '試作階段', 'ming', 'doing', None, 10),
                ('a', 'tp', 'task', '上層任務', 'ming', 'todo', 'ph', 20),
                ('a1', 'tp', 'task', '子任務', 'ming', 'todo', 'a', 30),
                ('b', 'tp', 'task', '另一個任務', 'ming', 'todo', 'ph', 40),
                ('h', 'tp', 'task', 'Secret hidden task', 'yu', 'todo', 'ph', 50),
                ('done1', 'tp', 'task', '已完成任務', 'ming', 'done', 'ph', 60),
                ('x', 'tp2', 'task', '別的專案任務', 'ming', 'todo', None, 10)]
        for nid, pid, kind, title, owner, status, parent, order in rows:
            db.add(Node(id=nid, organization_id=org, project_id=pid, kind=kind, title=title, status=status,
                        owner_user_id=users[owner].id, department_id=dept.id, parent_id=parent, sort_order=order))
        db.commit()
        ids = {name: user.id for name, user in users.items()}
    client.post('/auth/logout')
    return ids


def switch(client, username, org='food'):
    client.post('/auth/logout')
    login(client, org=org, username=username)


def snapshot(engine):
    with Session(engine) as db:
        return ([(n.id, n.parent_id, n.status, n.sort_order, n.weight, n.progress) for n in db.scalars(select(Node).order_by(Node.id))],
                [(r.id, r.status) for r in db.scalars(select(TaskReport).order_by(TaskReport.id))],
                [(a.id, a.action) for a in db.scalars(select(AuditLog).order_by(AuditLog.id))])


def set_status(engine, **statuses):
    with Session(engine) as db:
        for nid, status in statuses.items():
            db.get(Node, nid).status = status
        db.commit()


def nodes_of(client, project='tp'):
    return {n['id']: n for n in client.get(f'/projects/{project}').json()['nodes']}


# ---- progress formula (shared vectors with web/src/progress.ts) ----

def test_progress_vectors_match_shared_file():
    vectors = json.loads(Path('web/src/progress.vectors.json').read_text(encoding='utf-8'))
    for vector in vectors:
        nodes = [SimpleNamespace(**{'weight': 1, 'progress': None, 'created_at': None, **item}) for item in vector['nodes']]
        values = progress_map(nodes)
        assert {nid: percent(value) for nid, value in values.items()} == vector['expected'], vector['name']
        assert project_progress(nodes) == vector['project'], vector['name']


# ---- weight and manual progress ----

def test_node_out_exposes_weight_progress_and_move_capability(client, tree):
    switch(client, 'owner')
    nodes = nodes_of(client)
    assert nodes['a1']['weight'] == 1 and nodes['a1']['progress'] is None
    assert nodes['a1']['capabilities']['move'] is True and nodes['ph']['capabilities']['move'] is False
    for actor in ['ming', 'chen', 'lin']:
        switch(client, actor)
        assert not any(n['capabilities']['move'] for n in nodes_of(client).values()), actor


def test_weight_and_progress_update_with_validation_and_audit(client, engine, tree):
    switch(client, 'ming')
    response = client.patch('/nodes/a1', json={'weight': 3, 'progress': 30})
    assert response.status_code == 200
    assert (response.json()['weight'], response.json()['progress']) == (3, 30)
    before = snapshot(engine)
    for body in [{'weight': None}, {'weight': 1.5}, {'weight': 101}, {'weight': -1}, {'weight': True}, {'weight': '2'},
                 {'progress': 101}, {'progress': -1}, {'progress': 2.5}]:
        assert client.patch('/nodes/a1', json=body).status_code == 422, body
    assert client.patch('/nodes/ph', json={'progress': 10}).status_code == 422
    assert snapshot(engine) == before
    assert client.patch('/nodes/ph', json={'weight': 2}).json()['weight'] == 2
    reset = client.patch('/nodes/a1', json={'progress': None})
    assert reset.status_code == 200 and reset.json()['progress'] is None
    switch(client, 'yu')
    logs = client.get('/audit-logs', params={'node_id': 'a1', 'action': 'node.update'}).json()['items']
    assert {'weight': {'before': 1, 'after': 3}, 'progress': {'before': None, 'after': 30}} in [log['payload'] for log in logs]
    switch(client, 'lin')
    before = snapshot(engine)
    assert client.patch('/nodes/a1', json={'weight': 2}).status_code == 403
    assert snapshot(engine) == before


# ---- parent completion rule ----

def test_phase_cannot_be_done_while_any_child_is_open_even_hidden(client, engine, tree):
    switch(client, 'ming')
    before = snapshot(engine)
    response = client.patch('/nodes/ph/status', json={'status': 'done'})
    assert response.status_code == 409 and response.json()['detail'] == '子節點尚未全部完成'
    assert snapshot(engine) == before
    # Only the hidden child is left open: still refused, without naming or counting it.
    set_status(engine, a='done', a1='done', b='skipped')
    response = client.patch('/nodes/ph/status', json={'status': 'done'})
    assert response.status_code == 409 and 'Secret' not in response.text and '1' not in response.json()['detail']
    set_status(engine, h='skipped')
    assert client.patch('/nodes/ph/status', json={'status': 'done'}).json()['status'] == 'done'
    # Other phase transitions are unaffected by open children.
    set_status(engine, h='todo')
    assert client.patch('/nodes/ph/status', json={'status': 'review'}).status_code == 200


def test_parent_task_report_submit_and_approve_require_finished_children(client, engine, tree):
    switch(client, 'ming')
    before = snapshot(engine)
    response = client.post('/nodes/a/reports', json=PAYLOAD)
    assert response.status_code == 409 and response.json()['detail'] == '子節點尚未全部完成'
    switch(client, 'yu')
    assert client.post('/nodes/a/reports', json={**PAYLOAD, 'self_approve': True}).status_code == 409
    assert snapshot(engine) == before
    set_status(engine, a1='done')
    switch(client, 'ming')
    report = client.post('/nodes/a/reports', json=PAYLOAD)
    assert report.status_code == 201 and report.json()['node_status'] == 'review'
    set_status(engine, a1='doing')
    switch(client, 'owner')
    before = snapshot(engine)
    response = client.post(f"/reports/{report.json()['id']}/review", json={'decision': 'approved'})
    assert response.status_code == 409 and response.json()['detail'] == '子節點尚未全部完成'
    assert snapshot(engine) == before
    # Rejecting is still possible; once the child is done the next version can be approved.
    assert client.post(f"/reports/{report.json()['id']}/review", json={'decision': 'rejected', 'comment': '子任務未完成'}).status_code == 200
    set_status(engine, a1='done')
    switch(client, 'yu')
    assert client.post('/nodes/a/reports', json={**PAYLOAD, 'self_approve': True}).json()['node_status'] == 'done'


# ---- moving tasks ----

def test_owner_moves_task_under_another_task_with_audit(client, engine, tree):
    switch(client, 'owner')
    response = client.post('/nodes/b/move', json={'parent_id': 'a'})
    assert response.status_code == 200
    moved = response.json()
    assert moved['parent_id'] == 'a' and moved['status'] == 'todo'
    with Session(engine) as db:
        assert moved['sort_order'] > max(n.sort_order for n in db.scalars(select(Node).where(Node.project_id == 'tp', Node.id != 'b')))
    logs = client.get('/audit-logs', params={'node_id': 'b', 'action': 'node.move'}).json()['items']
    assert [(log['summary'], log['payload']) for log in logs] == [('移動節點', {'from_parent_id': 'ph', 'from_parent_title': '試作階段',
                                                                                 'to_parent_id': 'a', 'to_parent_title': '上層任務'})]
    before = snapshot(engine)
    assert client.post('/nodes/b/move', json={'parent_id': 'a'}).status_code == 200
    assert snapshot(engine) == before
    # Moving onto a phase or back to the phase is allowed for the project's manager.
    assert client.post('/nodes/b/move', json={'parent_id': 'ph'}).json()['parent_id'] == 'ph'


@pytest.mark.parametrize('actor,org,expected', [('ming', 'food', 403), ('chen', 'food', 403), ('lin', 'food', 403),
                                                ('kai', 'electronics', 404), ('yu', 'food', 200)])
def test_move_permission_matrix(client, engine, tree, actor, org, expected):
    switch(client, actor, org)
    before = snapshot(engine)
    response = client.post('/nodes/b/move', json={'parent_id': 'a'})
    assert response.status_code == expected
    if expected != 200:
        assert snapshot(engine) == before


@pytest.mark.parametrize('node,target,expected,detail', [
    ('a', 'a', 409, '不能移到自己的子任務底下'),
    ('a', 'a1', 409, '不能移到自己的子任務底下'),
    ('b', 'done1', 409, '不能移到已完成、待確認或已略過的任務底下'),
    ('b', 'x', 404, '找不到目標節點'),
    ('b', 'missing', 404, '找不到目標節點'),
    ('ph', 'a', 422, '只能移動任務'),
])
def test_move_guards_leave_data_unchanged(client, engine, tree, node, target, expected, detail):
    switch(client, 'owner')
    before = snapshot(engine)
    response = client.post(f'/nodes/{node}/move', json={'parent_id': target})
    assert response.status_code == expected and response.json()['detail'] == detail
    assert snapshot(engine) == before


@pytest.mark.parametrize('status', ['review', 'skipped'])
def test_move_refuses_review_and_skipped_targets(client, engine, tree, status):
    set_status(engine, a=status)
    switch(client, 'owner')
    before = snapshot(engine)
    assert client.post('/nodes/b/move', json={'parent_id': 'a'}).status_code == 409
    assert snapshot(engine) == before


@pytest.mark.parametrize('moved,target', [('b', 'a'), ('a', 'b')])
def test_move_refuses_dependency_between_subtree_and_new_ancestors(client, engine, tree, moved, target):
    switch(client, 'owner')
    assert client.post('/projects/tp/dependencies', json={'predecessor_id': 'a', 'successor_id': 'b'}).status_code == 201
    before = snapshot(engine)
    response = client.post(f'/nodes/{moved}/move', json={'parent_id': target})
    assert response.status_code == 409 and response.json()['detail'] == '移動後會和前置相依衝突，請先移除相依連線'
    assert snapshot(engine) == before
    with Session(engine) as db:
        assert len(list(db.scalars(select(NodeDependency)))) == 1


def test_move_rejects_bad_body(client, tree):
    switch(client, 'owner')
    for body in [{}, {'parent_id': ''}, {'parent_id': 'a', 'extra': 1}, {'parent_id': None}]:
        assert client.post('/nodes/b/move', json=body).status_code == 422, body


# ---- overview progress ----

def test_overview_progress_is_weighted_over_visible_nodes(client, engine, tree):
    with Session(engine) as db:
        db.get(Node, 'done1').weight = 3
        db.commit()
    switch(client, 'yu')
    projects = {p['id']: p for p in client.get('/workspace/overview').json()['projects']}
    # ph children a(0) b(0) h(0) done1(100×3): 300 / 6 = 50.
    assert projects['tp']['progress_percent'] == 50
    switch(client, 'ming')
    projects = {p['id']: p for p in client.get('/workspace/overview').json()['projects']}
    # ming cannot see h: 300 / 5 = 60.
    assert projects['tp']['progress_percent'] == 60


# ---- project records roll-up ----

def test_project_records_roll_up_visible_nodes_only(client, engine, tree):
    switch(client, 'ming')
    assert client.post('/nodes/a1/notes', json={'body': '子任務筆記', 'attachment_ids': []}).status_code == 201
    switch(client, 'yu')
    assert client.post('/nodes/h/notes', json={'body': 'Secret note', 'attachment_ids': []}).status_code == 201
    items = client.get('/projects/tp/records').json()['items']
    assert sorted((i['type'], i['node_title']) for i in items) == [('note', 'Secret hidden task'), ('note', '子任務')]
    page = client.get('/projects/tp/records', params={'limit': 1}).json()
    assert len(page['items']) == 1 and page['next_cursor']
    assert len(client.get('/projects/tp/records', params={'limit': 1, 'cursor': page['next_cursor']}).json()['items']) == 1
    # A project cursor is bound to this endpoint and project.
    assert client.get('/nodes/ph/records', params={'scope': 'subtree', 'cursor': page['next_cursor']}).status_code == 422
    assert client.get('/projects/tp2/records', params={'cursor': page['next_cursor']}).status_code == 422
    switch(client, 'ming')
    response = client.get('/projects/tp/records')
    assert [i['node_title'] for i in response.json()['items']] == ['子任務'] and 'Secret' not in response.text
    switch(client, 'kai', 'electronics')
    assert client.get('/projects/tp/records').status_code == 404
