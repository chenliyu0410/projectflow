"""TP-B: soft delete, copy subtree, promote/demote/move-to, one-step undo and the closed-parent rule (D74)."""
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import INCLUDE_DELETED, AuditLog, Department, Node, NodeCollaborator, NodeDependency, Project, TaskNote, TaskReport, User
from app.services import tree_service
from test_projects_nodes import login

REPORT = {'result': '達成', 'summary': '成果', 'finished_on': '2026-10-08', 'attachment_ids': []}


@pytest.fixture
def tree(client, engine):
    """Project `tp` owned by `owner`; ming owns the tasks; chen heads their department; `c` belongs to yu with no department.

    ph ─┬ a ─┬ a1 ── a1x
        │    └ a2
        ├ b
        ├ c (yu, no department)
        └ done1 ── d1 (done)
    Edges: a1 → b (leaves the subtree of a), a2 → a1x (inside it).
    """
    login(client)
    with Session(engine) as db:
        users = {u.username: u for u in db.scalars(select(User))}
        org = users['yu'].organization_id
        dept = db.scalars(select(Department).where(Department.head_user_id == users['chen'].id)).one()
        db.add_all([Project(id='tp', organization_id=org, title='樹狀專案', owner_user_id=users['owner'].id),
                    Project(id='tm', organization_id=org, title='成員負責的專案', owner_user_id=users['ming'].id)])
        db.flush()
        rows = [('ph', 'tp', 'phase', '試作階段', 'ming', 'doing', None, 10, dept.id),
                ('a', 'tp', 'task', '上層任務', 'ming', 'todo', 'ph', 20, dept.id),
                ('a1', 'tp', 'task', '子任務一', 'ming', 'todo', 'a', 30, dept.id),
                ('a1x', 'tp', 'task', '孫任務', 'ming', 'todo', 'a1', 35, dept.id),
                ('a2', 'tp', 'task', '子任務二', 'ming', 'todo', 'a', 36, dept.id),
                ('b', 'tp', 'task', '後續任務', 'ming', 'todo', 'ph', 40, dept.id),
                ('c', 'tp', 'task', '別人的任務', 'yu', 'todo', 'ph', 45, None),
                ('done1', 'tp', 'task', '已完成任務', 'ming', 'done', 'ph', 60, dept.id),
                ('d1', 'tp', 'task', '已完成子任務', 'ming', 'done', 'done1', 61, dept.id),
                ('m', 'tm', 'task', '成員的上層', 'ming', 'todo', None, 10, None),
                ('mh', 'tm', 'task', '成員看不到的子任務', 'yu', 'todo', 'm', 20, None)]
        for nid, pid, kind, title, owner, status, parent, order, department in rows:
            db.add(Node(id=nid, organization_id=org, project_id=pid, kind=kind, title=title, status=status,
                        owner_user_id=users[owner].id, department_id=department, parent_id=parent, sort_order=order))
        db.flush()
        for pred, succ in [('a1', 'b'), ('a2', 'a1x')]:
            db.add(NodeDependency(organization_id=org, project_id='tp', predecessor_id=pred, successor_id=succ, created_by=users['owner'].id))
        db.commit()
        ids = {name: user.id for name, user in users.items()}
    client.post('/auth/logout')
    return ids


def switch(client, username, org='food'):
    client.post('/auth/logout')
    login(client, org=org, username=username)


def all_nodes(engine):
    with Session(engine) as db:
        return {n.id: n for n in db.scalars(select(Node).execution_options(**{INCLUDE_DELETED: True}))}


def snapshot(engine):
    with Session(engine) as db:
        return ([(n.id, n.parent_id, n.status, n.sort_order, n.deleted_at is None) for n in db.scalars(
                    select(Node).order_by(Node.id).execution_options(**{INCLUDE_DELETED: True}))],
                sorted((e.predecessor_id, e.successor_id) for e in db.scalars(select(NodeDependency))),
                [(r.id, r.status) for r in db.scalars(select(TaskReport).order_by(TaskReport.id))],
                len(list(db.scalars(select(AuditLog)))))


def visible(client, project='tp'):
    return {n['id']: n for n in client.get(f'/projects/{project}').json()['nodes']}


def edges(client, project='tp'):
    return sorted((e['predecessor_id'], e['successor_id']) for e in client.get(f'/projects/{project}/dependencies').json()['items'])


def set_status(engine, **statuses):
    with Session(engine) as db:
        for nid, status in statuses.items():
            db.get(Node, nid).status = status
        db.commit()


def undo(client, response):
    return client.post('/undo', json={'audit_id': response.json()['undo_id']})


# ---- soft delete ----

def test_delete_hides_subtree_everywhere_and_keeps_records(client, engine, tree):
    switch(client, 'ming')
    assert client.post('/nodes/a1x/notes', json={'body': '孫任務筆記'}).status_code == 201
    assert client.post('/nodes/a2/reports', json=REPORT).status_code == 201
    switch(client, 'owner')
    assert visible(client)['b']['blocked'] is True
    assert any(item['node_id'] == 'a2' for item in client.get('/workspace/reviews').json()['items'])
    response = client.delete('/nodes/a')
    assert response.status_code == 200
    body = response.json()
    assert body['deleted_count'] == 4 and body['parent_id'] == 'ph' and body['undo_id']
    nodes = visible(client)
    assert not {'a', 'a1', 'a1x', 'a2'} & nodes.keys()
    # The edge out of the subtree is gone, so its successor no longer waits.
    assert nodes['b']['blocked'] is False and edges(client) == []
    assert not any(item['node_id'] == 'a2' for item in client.get('/workspace/reviews').json()['items'])
    assert '孫任務筆記' not in client.get('/projects/tp/records').text
    for method, url, kwargs in [('get', '/nodes/a1/records', {}), ('patch', '/nodes/a1', {'json': {'title': '改名'}}),
                                ('patch', '/nodes/a1/status', {'json': {'status': 'doing'}}), ('post', '/nodes/a1/move', {'json': {'parent_id': 'ph'}}),
                                ('post', '/nodes/a1/copy', {}), ('delete', '/nodes/a1', {}), ('post', '/nodes/a1/notes', {'json': {'body': 'x'}})]:
        assert getattr(client, method)(url, **kwargs).status_code == 404, url
    switch(client, 'ming')
    assert not {'a', 'a1', 'a1x', 'a2'} & {item['id'] for item in client.get('/workspace/my-tasks').json()['items']}
    assert client.get('/workspace/overview').status_code == 200
    # Rows, notes and reports stay in the database; the removed edges are kept in the audit payload.
    stored = all_nodes(engine)
    assert all(stored[n].deleted_at is not None and stored[n].deleted_by == tree['owner'] for n in ['a', 'a1', 'a1x', 'a2'])
    with Session(engine) as db:
        assert db.scalars(select(TaskNote).where(TaskNote.node_id == 'a1x')).one().body == '孫任務筆記'
        assert db.scalars(select(TaskReport).where(TaskReport.node_id == 'a2')).one().status == 'submitted'
        entry = db.scalars(select(AuditLog).where(AuditLog.action == 'node.delete')).one()
        assert entry.node_id == 'a' and entry.payload['node_ids'] == ['a', 'a1', 'a2', 'a1x']
        assert sorted((d['predecessor_id'], d['successor_id']) for d in entry.payload['dependencies']) == [('a1', 'b'), ('a2', 'a1x')]
    # The audit view keeps the deleted nodes' history and marks them.
    switch(client, 'owner')
    logs = client.get('/audit-logs', params={'node_id': 'a'}).json()['items']
    assert logs[0]['summary'] == '刪除節點' and logs[0]['node_deleted'] is True
    assert logs[0]['payload'] == {'title': '上層任務', 'count': 4, 'parent_id': 'ph', 'parent_title': '試作階段'}
    note_logs = client.get('/audit-logs', params={'node_id': 'a1x'}).json()['items']
    assert [log['action'] for log in note_logs] == ['note.create'] and note_logs[0]['node_deleted'] is True


def test_undo_delete_restores_nodes_edges_and_pending_report(client, engine, tree):
    switch(client, 'ming')
    assert client.post('/nodes/a2/reports', json=REPORT).status_code == 201
    switch(client, 'owner')
    before = snapshot(engine)
    response = client.delete('/nodes/a')
    restored = undo(client, response)
    assert restored.status_code == 200
    assert restored.json() == {'action': 'node.delete', 'project_id': 'tp', 'node_id': 'a', 'parent_id': 'ph'}
    after = snapshot(engine)
    assert after[:3] == before[:3]
    assert {'a', 'a1', 'a1x', 'a2'} <= visible(client).keys() and visible(client)['b']['blocked'] is True
    assert any(item['node_id'] == 'a2' for item in client.get('/workspace/reviews').json()['items'])
    logs = client.get('/audit-logs', params={'node_id': 'a'}).json()['items']
    assert [(log['summary'], log['payload']) for log in logs[:2]] == [('復原', {'action': 'node.delete'}),
                                                                      ('刪除節點', {'title': '上層任務', 'count': 4, 'parent_id': 'ph', 'parent_title': '試作階段'})]
    assert logs[0]['node_deleted'] is False
    # Only one step: the same token, or nothing at all, cannot be undone again.
    again = undo(client, response)
    assert again.status_code == 409 and again.json()['detail'] == '只能復原最近一次的結構操作'
    assert snapshot(engine)[:3] == before[:3]


@pytest.mark.parametrize('actor,org,expected', [('ming', 'food', 403), ('chen', 'food', 403), ('lin', 'food', 403),
                                                ('kai', 'electronics', 404)])
def test_delete_and_copy_need_a_project_manager(client, engine, tree, actor, org, expected):
    switch(client, actor, org)
    before = snapshot(engine)
    assert client.delete('/nodes/b').status_code == expected
    assert client.post('/nodes/b/copy').status_code == expected
    assert snapshot(engine) == before
    if actor != 'kai':
        caps = visible(client)['b']['capabilities']
        assert caps['delete'] is False and caps['copy'] is False


def test_delete_and_copy_guards_leave_data_unchanged(client, engine, tree):
    switch(client, 'owner')
    before = snapshot(engine)
    for url, method in [('/nodes/ph', 'delete'), ('/nodes/ph/copy', 'post')]:
        response = getattr(client, method)(url)
        assert response.status_code == 422 and response.json()['detail'] in {'只能刪除任務', '只能複製任務'}
    response = client.post('/nodes/d1/copy')
    assert response.status_code == 409 and response.json()['detail'] == '不能在已完成、待確認或已略過的節點底下新增'
    assert snapshot(engine) == before
    caps = visible(client)
    assert caps['b']['capabilities']['delete'] is True and caps['ph']['capabilities']['delete'] is False
    # A member-owner who cannot see part of the subtree cannot delete or copy it.
    switch(client, 'ming')
    for method, url, detail in [('delete', '/nodes/m', '此節點底下有你看不到的子任務，無法刪除'),
                                ('post', '/nodes/m/copy', '此節點底下有你看不到的子任務，無法複製')]:
        response = getattr(client, method)(url)
        assert response.status_code == 409 and response.json()['detail'] == detail
    assert snapshot(engine) == before


# ---- copy subtree ----

def test_copy_subtree_copies_fields_collaborators_and_inner_edges(client, engine, tree):
    with Session(engine) as db:
        a1 = db.get(Node, 'a1')
        a1.status, a1.progress, a1.weight = 'doing', 30, 3
        a1.start_date = a1.due_date = None
        db.add(NodeCollaborator(organization_id=a1.organization_id, node_id='a1', user_id=tree['chen'], created_by=tree['owner']))
        db.commit()
    switch(client, 'owner')
    response = client.post('/nodes/a/copy')
    assert response.status_code == 201
    body = response.json()
    assert body['title'] == '上層任務（複本）' and body['parent_id'] == 'ph' and body['copied_count'] == 4 and body['undo_id']
    order = [n['id'] for n in client.get('/projects/tp').json()['nodes'] if n['parent_id'] == 'ph']
    assert order[:3] == ['a', body['id'], 'b']
    nodes = visible(client)
    copies = {n['title']: n for n in nodes.values() if n['id'] not in tree_ids()}
    assert set(copies) == {'上層任務（複本）', '子任務一', '孫任務', '子任務二'}
    one = copies['子任務一']
    assert one['status'] == 'todo' and one['progress'] is None and one['weight'] == 3
    assert one['owner_user_id'] == tree['ming'] and one['parent_id'] == body['id']
    assert copies['孫任務']['parent_id'] == one['id']
    with Session(engine) as db:
        assert [r.user_id for r in db.scalars(select(NodeCollaborator).where(NodeCollaborator.node_id == one['id']))] == [tree['chen']]
    # Only the edge inside the subtree is copied; a1 → b stays with the original.
    assert edges(client) == sorted([('a1', 'b'), ('a2', 'a1x'), (copies['子任務二']['id'], copies['孫任務']['id'])])
    log = client.get('/audit-logs', params={'node_id': body['id']}).json()['items'][0]
    assert (log['summary'], log['payload']) == ('複製子樹', {'count': 4, 'source_id': 'a', 'source_title': '上層任務'})


def tree_ids():
    return {'ph', 'a', 'a1', 'a1x', 'a2', 'b', 'c', 'done1', 'd1'}


def test_copy_title_is_truncated_and_size_is_limited(client, engine, tree, monkeypatch):
    with Session(engine) as db:
        db.get(Node, 'b').title = '長' * 200
        db.commit()
    switch(client, 'owner')
    title = client.post('/nodes/b/copy').json()['title']
    assert len(title) == 200 and title.endswith('（複本）')
    monkeypatch.setattr(tree_service, 'COPY_LIMIT', 3)
    before = snapshot(engine)
    response = client.post('/nodes/a/copy')
    assert response.status_code == 422 and response.json()['detail'] == '子樹超過 3 個節點，無法複製'
    assert snapshot(engine) == before


def test_undo_copy_removes_the_copy_unless_it_was_touched(client, engine, tree):
    switch(client, 'owner')
    before = snapshot(engine)
    response = client.post('/nodes/a/copy')
    assert undo(client, response).status_code == 200
    assert snapshot(engine)[1:3] == before[1:3]
    assert visible(client).keys() == tree_ids()
    assert not any(n['title'].endswith('（複本）') for n in visible(client).values())
    # A note on the copy (anyone's later activity) blocks the undo and changes nothing.
    response = client.post('/nodes/a/copy')
    copy_child = next(n for n in visible(client).values() if n['parent_id'] == response.json()['id'])
    assert client.post(f"/nodes/{copy_child['id']}/notes", json={'body': '後來的筆記'}).status_code == 201
    touched = snapshot(engine)
    refused = undo(client, response)
    assert refused.status_code == 409 and refused.json()['detail'] == '之後已有其他變更，無法復原'
    assert snapshot(engine) == touched


# ---- move, promote, demote ----

def test_move_to_top_level_and_undo_restores_parent_and_order(client, engine, tree):
    switch(client, 'owner')
    response = client.post('/nodes/b/move', json={'parent_id': None})
    assert response.status_code == 200 and response.json()['parent_id'] is None and response.json()['undo_id']
    assert undo(client, response).status_code == 200
    node = all_nodes(engine)['b']
    assert (node.parent_id, node.sort_order) == ('ph', 40)
    log = client.get('/audit-logs', params={'node_id': 'b'}).json()['items']
    assert [item['summary'] for item in log[:2]] == ['復原', '移動節點']


def test_move_to_top_level_of_a_blank_project_uses_its_root(client, engine, tree):
    switch(client, 'yu')
    project = client.post('/projects', json={'title': '空白專案'}).json()
    root = next(n for n in visible(client, project['id']).values() if n['kind'] == 'project')
    phase = client.post(f"/projects/{project['id']}/nodes", json={'title': '階段', 'kind': 'phase', 'parent_id': root['id']}).json()
    task = client.post(f"/projects/{project['id']}/nodes", json={'title': '任務', 'kind': 'task', 'parent_id': phase['id']}).json()
    moved = client.post(f"/nodes/{task['id']}/move", json={'parent_id': None})
    assert moved.status_code == 200 and moved.json()['parent_id'] == root['id']


def test_task_owner_and_department_head_may_move_but_others_may_not(client, engine, tree):
    # D74: ming owns b and a; chen heads their department. Neither can move yu's task `c` (no department).
    switch(client, 'ming')
    response = client.post('/nodes/b/move', json={'parent_id': 'a'})
    assert response.status_code == 200
    assert undo(client, response).status_code == 200
    assert client.post('/nodes/c/move', json={'parent_id': 'a'}).status_code == 404
    switch(client, 'chen')
    before = snapshot(engine)
    assert client.post('/nodes/c/move', json={'parent_id': 'a'}).status_code == 403
    assert visible(client)['c']['capabilities']['move'] is False
    assert snapshot(engine) == before
    assert client.post('/nodes/b/move', json={'parent_id': 'a'}).status_code == 200


def test_undo_move_is_refused_after_a_later_move_or_closed_parent(client, engine, tree):
    switch(client, 'owner')
    first = client.post('/nodes/b/move', json={'parent_id': 'a'})
    switch(client, 'chen')
    assert client.post('/nodes/b/move', json={'parent_id': 'ph'}).status_code == 200
    switch(client, 'owner')
    before = snapshot(engine)
    refused = undo(client, first)
    assert refused.status_code == 409 and refused.json()['detail'] == '之後已有其他變更，無法復原'
    assert snapshot(engine) == before
    second = client.post('/nodes/a2/move', json={'parent_id': 'b'})
    set_status(engine, a='done')
    before = snapshot(engine)
    refused = undo(client, second)
    assert refused.status_code == 409 and refused.json()['detail'] == '原本的上層已無法放回，無法復原'
    assert snapshot(engine) == before


# ---- undo rules ----

def test_undo_create_and_only_the_actor_latest_action(client, engine, tree):
    switch(client, 'owner')
    created = client.post('/projects/tp/nodes', json={'title': '新任務', 'kind': 'task', 'parent_id': 'b'})
    assert created.status_code == 201 and created.json()['undo_id']
    copied = client.post('/nodes/b/copy')
    refused = undo(client, created)
    assert refused.status_code == 409 and refused.json()['detail'] == '只能復原最近一次的結構操作'
    for actor, org, status in [('yu', 'food', 404), ('kai', 'electronics', 404), ('lin', 'food', 404)]:
        switch(client, actor, org)
        assert undo(client, copied).status_code == status, actor
    switch(client, 'owner')
    assert undo(client, copied).status_code == 200
    assert undo(client, copied).status_code == 409
    # A lifecycle change is not a structure change, so it does not consume the undo either.
    created = client.post('/projects/tp/nodes', json={'title': '再新增', 'kind': 'task', 'parent_id': 'b'})
    assert client.post('/nodes/c/lifecycle', json={'action': 'skip', 'reason': '不做'}).status_code == 200
    assert undo(client, created).status_code == 200
    assert created.json()['id'] not in visible(client)
    for bad in [{}, {'audit_id': ''}, {'audit_id': 'x', 'extra': 1}]:
        assert client.post('/undo', json=bad).status_code == 422
    assert client.post('/undo', json={'audit_id': 'missing'}).status_code == 404


def test_undo_create_refused_after_activity(client, engine, tree):
    switch(client, 'owner')
    created = client.post('/projects/tp/nodes', json={'title': '新任務', 'kind': 'task', 'parent_id': 'b'})
    assert client.patch(f"/nodes/{created.json()['id']}", json={'title': '改過名'}).status_code == 200
    before = snapshot(engine)
    refused = undo(client, created)
    assert refused.status_code == 409 and refused.json()['detail'] == '之後已有其他變更，無法復原'
    assert snapshot(engine) == before


def test_undo_delete_refused_when_parent_closed_or_edges_changed(client, engine, tree):
    switch(client, 'owner')
    deleted = client.delete('/nodes/a2')
    set_status(engine, a='done', a1='done', a1x='done')
    before = snapshot(engine)
    refused = undo(client, deleted)
    assert refused.status_code == 409 and refused.json()['detail'] == '原本的上層已無法放回，無法復原'
    assert snapshot(engine) == before
    # Restoring c → a1 → b would close a loop once someone adds b → c.
    set_status(engine, a='todo', a1='todo', a1x='todo')
    assert client.post('/projects/tp/dependencies', json={'predecessor_id': 'c', 'successor_id': 'a1'}).status_code == 201
    deleted = client.delete('/nodes/a1')
    switch(client, 'yu')
    assert client.post('/projects/tp/dependencies', json={'predecessor_id': 'b', 'successor_id': 'c'}).status_code == 201
    switch(client, 'owner')
    before = snapshot(engine)
    refused = undo(client, deleted)
    assert refused.status_code == 409 and refused.json()['detail'] == '相關任務已有變更，無法復原'
    assert snapshot(engine) == before


# ---- closed parent rule (TP-A Minor 1) ----

def test_closed_parent_refuses_new_or_reopened_children(client, engine, tree):
    switch(client, 'owner')
    before = snapshot(engine)
    response = client.post('/projects/tp/nodes', json={'title': '新任務', 'kind': 'task', 'parent_id': 'done1'})
    assert response.status_code == 409 and response.json()['detail'] == '不能在已完成、待確認或已略過的節點底下新增'
    response = client.post('/nodes/d1/lifecycle', json={'action': 'reopen', 'reason': '要補做'})
    assert response.status_code == 409 and response.json()['detail'] == '上層已完成、待確認或已略過，請先重新開啟上層'
    set_status(engine, d1='skipped')
    response = client.post('/nodes/d1/lifecycle', json={'action': 'restore', 'reason': '要補做'})
    assert response.status_code == 409 and response.json()['detail'] == '上層已完成、待確認或已略過，請先重新開啟上層'
    set_status(engine, d1='done')
    assert snapshot(engine) == before
    # Reopening the parent first lets the child reopen.
    assert client.post('/nodes/done1/lifecycle', json={'action': 'reopen', 'reason': '要補做'}).status_code == 200
    assert client.post('/nodes/d1/lifecycle', json={'action': 'reopen', 'reason': '要補做'}).status_code == 200
    assert client.post('/projects/tp/nodes', json={'title': '新任務', 'kind': 'task', 'parent_id': 'done1'}).status_code == 201
