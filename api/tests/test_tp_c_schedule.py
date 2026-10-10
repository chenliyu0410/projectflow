"""D75 schedule transactions: permissions, propagation, atomicity and structural invariants."""
from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, Node, NodeDependency, Project, User
from test_projects_nodes import login


@pytest.fixture
def schedule(client, engine):
    login(client)
    with Session(engine) as db:
        users = {u.username: u for u in db.scalars(select(User))}
        org = users['yu'].organization_id
        db.add(Project(id='sc', organization_id=org, title='時程專案', owner_user_id=users['owner'].id))
        db.flush()
        for nid, start, due, parent in [('a', 1, 3, None), ('b', 4, 5, None), ('c', 6, 8, None), ('d', 4, 7, None)]:
            db.add(Node(id=nid, organization_id=org, project_id='sc', kind='task', title=nid,
                        owner_user_id=users['ming'].id, start_date=date(2026, 10, start), due_date=date(2026, 10, due), parent_id=parent))
        db.flush()
        for pred, succ in [('a', 'b'), ('b', 'c')]:
            db.add(NodeDependency(organization_id=org, project_id='sc', predecessor_id=pred, successor_id=succ, created_by=users['yu'].id))
        db.commit()
        return {k: u.id for k, u in users.items()}


def update(client, nid='a', start='2026-10-04', due='2026-10-06', cascade=True):
    return client.post(f'/nodes/{nid}/schedule', json={'start_date': start, 'due_date': due, 'cascade': cascade})


def snapshot(engine):
    with Session(engine) as db:
        return ([(n.id, n.start_date, n.due_date, n.milestone, n.schedule_locked) for n in db.scalars(select(Node).order_by(Node.id))],
                [(a.id, a.payload) for a in db.scalars(select(AuditLog).order_by(AuditLog.id))])


def change(engine, nid, **values):
    with Session(engine) as db:
        n = db.get(Node, nid)
        for k, v in values.items(): setattr(n, k, v)
        db.commit()


def switch(client, username, org='food'):
    client.post('/auth/logout')
    login(client, username=username, org=org)


def test_chain_atomic_audit_and_no_auto_advance(client, engine, schedule):
    r = update(client)
    assert r.status_code == 200, r.text
    assert r.json()['shifted_count'] == 2
    with Session(engine) as db:
        assert db.get(Node, 'b').start_date == date(2026, 10, 7)
        assert db.get(Node, 'c').due_date == date(2026, 10, 11)
        audits = list(db.scalars(select(AuditLog).where(AuditLog.node_id.in_(['a', 'b', 'c']))))
        assert len(audits) == 3
        assert len({a.payload['schedule']['operation_id'] for a in audits}) == 1
    assert update(client, start='2026-10-01', due='2026-10-03').json()['shifted_count'] == 0
    with Session(engine) as db: assert db.get(Node, 'b').start_date == date(2026, 10, 7)


@pytest.mark.parametrize('problem', ['locked', 'done', 'review', 'skipped', 'unscheduled', 'hidden', 'no_permission'])
def test_blocked_chain_has_no_partial_writes_or_audit(client, engine, schedule, problem):
    if problem == 'locked': change(engine, 'c', milestone=True, schedule_locked=True, due_date=date(2026, 10, 6))
    elif problem in {'done', 'review', 'skipped'}: change(engine, 'c', status=problem)
    elif problem == 'unscheduled': change(engine, 'c', start_date=None)
    else:
        change(engine, 'c', owner_user_id=schedule['yu'])
        switch(client, 'ming' if problem == 'hidden' else 'chen')
        if problem == 'no_permission':
            change(engine, 'a', owner_user_id=schedule['chen'])
            change(engine, 'b', owner_user_id=schedule['chen'])
    before = snapshot(engine)
    r = update(client)
    assert r.status_code == 409, r.text
    assert r.json()['detail'] == '後續任務有無法調整的項目，請由專案負責人確認'
    assert snapshot(engine) == before


def test_single_change_conflicts_incoming_and_patch_cannot_bypass(client, engine, schedule):
    assert update(client, cascade=False).status_code == 200
    with Session(engine) as db: assert db.get(Node, 'b').start_date == date(2026, 10, 4)
    before = snapshot(engine)
    for route in ['schedule', 'patch']:
        r = update(client, 'b', '2026-10-06', '2026-10-07', False) if route == 'schedule' else client.patch('/nodes/b', json={'start_date': '2026-10-06', 'due_date': '2026-10-07'})
        assert r.status_code == 409
        assert snapshot(engine) == before


def test_lock_permissions_and_milestone_constraints(client, engine, schedule):
    assert client.patch('/nodes/d', json={'milestone': True}).status_code == 422
    assert client.patch('/nodes/d', json={'milestone': True, 'due_date': '2026-10-04', 'schedule_locked': True}).status_code == 200
    switch(client, 'ming')
    for fields in [{'schedule_locked': False}, {'start_date': '2026-10-05', 'due_date': '2026-10-05'}, {'milestone': False}]:
        assert client.patch('/nodes/d', json=fields).status_code == 403
    assert client.patch('/nodes/d', json={'title': '仍可編輯名稱'}).status_code == 200
    switch(client, 'owner')
    assert update(client, 'd', '2026-10-05', '2026-10-05', False).status_code == 200
    assert client.patch('/nodes/d', json={'milestone': False}).status_code == 422
    assert client.patch('/nodes/d', json={'milestone': False, 'schedule_locked': False}).status_code == 200


def test_milestone_leaf_create_move_copy_and_undo(client, engine, schedule):
    child = client.post('/projects/sc/nodes', json={'kind': 'task', 'title': 'child', 'parent_id': 'd'})
    cid = child.json()['id']
    assert client.patch('/nodes/d', json={'milestone': True, 'due_date': '2026-10-04'}).status_code == 409
    removed = client.delete(f'/nodes/{cid}')
    assert client.patch('/nodes/d', json={'milestone': True, 'due_date': '2026-10-04', 'schedule_locked': True}).status_code == 200
    assert client.post('/undo', json={'audit_id': removed.json()['undo_id']}).status_code == 409
    assert client.post('/projects/sc/nodes', json={'kind': 'task', 'title': 'child', 'parent_id': 'd'}).status_code == 409
    assert client.post('/nodes/a/move', json={'parent_id': 'd'}).status_code == 409
    copied = client.post('/nodes/d/copy')
    assert copied.status_code == 201
    assert copied.json()['milestone'] is True and copied.json()['schedule_locked'] is True


def test_parent_span_and_fork_join(client, engine, schedule):
    with Session(engine) as db:
        a, d = db.get(Node, 'a'), db.get(Node, 'd')
        d.parent_id = 'b'
        db.add(NodeDependency(organization_id=a.organization_id, project_id='sc', predecessor_id='a', successor_id='c', created_by=schedule['yu']))
        db.commit()
    r = update(client)
    assert r.status_code == 200, r.text
    with Session(engine) as db:
        assert db.get(Node, 'd').due_date == date(2026, 10, 10)
        assert db.get(Node, 'c').start_date == date(2026, 10, 11)
    # Editing a child rechecks an ancestor's incoming FS constraint.
    assert update(client, 'd', '2026-10-02', '2026-10-04', False).status_code == 409
    assert client.post('/projects/sc/nodes', json={'kind': 'task', 'title': 'early', 'parent_id': 'b', 'start_date': '2026-10-01', 'due_date': '2026-10-02'}).status_code == 409


def test_cycles_and_date_overflow_are_atomic(client, engine, schedule):
    before = snapshot(engine)
    assert update(client, start='9999-12-30', due='9999-12-31').status_code == 409
    assert snapshot(engine) == before
    with Session(engine) as db:
        n = db.get(Node, 'a')
        db.add(NodeDependency(organization_id=n.organization_id, project_id='sc', predecessor_id='c', successor_id='a', created_by=schedule['yu']))
        db.commit()
    assert update(client).status_code == 409
    assert snapshot(engine) == before


def test_company_readonly_deleted_and_null_dates(client, engine, schedule):
    switch(client, 'lin')
    assert update(client).status_code == 403
    switch(client, 'kai', 'electronics')
    assert update(client).status_code == 404
    switch(client, 'yu')
    assert update(client, start=None, due=None).status_code == 422
    assert update(client, start=None, due=None, cascade=False).status_code == 200
    assert client.delete('/nodes/a').status_code == 200
    assert update(client).status_code == 404


def test_incomplete_predecessor_does_not_invent_a_finish_date(client, engine, schedule):
    change(engine, 'a', due_date=None)
    assert update(client, 'b', '2026-09-28', '2026-09-30', False).status_code == 200


def test_more_than_thirty_successors_are_all_shifted(client, engine, schedule):
    with Session(engine) as db:
        parent = db.get(Node, 'c')
        for i in range(35):
            nid = f'long-{i}'
            db.add(Node(id=nid, organization_id=parent.organization_id, project_id='sc', kind='task', title=nid,
                        owner_user_id=schedule['ming'], start_date=date(2026, 10, 9), due_date=date(2026, 10, 9)))
            db.flush()
            db.add(NodeDependency(organization_id=parent.organization_id, project_id='sc', predecessor_id=parent.id,
                                  successor_id=nid, created_by=schedule['yu']))
            parent = db.get(Node, nid)
        db.commit()
    r = update(client)
    assert r.status_code == 200, r.text
    assert r.json()['shifted_count'] == 37
    with Session(engine) as db: assert db.get(Node, 'long-34').due_date == date(2026, 11, 15)


def test_cascade_audit_failure_rolls_back_every_date(client, engine, schedule, monkeypatch):
    from app.services import schedule_service
    before = snapshot(engine)
    real = schedule_service.log_audit
    calls = []
    def fail_second(*args, **kwargs):
        calls.append(kwargs['node_id'])
        if len(calls) == 2: raise RuntimeError('simulated cascade audit failure')
        return real(*args, **kwargs)
    monkeypatch.setattr(schedule_service, 'log_audit', fail_second)
    with pytest.raises(RuntimeError, match='simulated cascade audit'):
        update(client)
    assert len(calls) == 2 and snapshot(engine) == before
