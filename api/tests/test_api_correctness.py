"""後端正確性與效能修正（API-CORRECTNESS）的回歸測試。"""
import contextlib
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import event, select
from sqlalchemy.orm import Session

from app import database
from app.models import AuditLog, Node, Notification, User
from app.services import record_policy
from test_report_lifecycle import setup, switch
from test_tp_a_planner import set_status, snapshot as planner_snapshot, switch as switch_planner, tree  # noqa: F401（tree 是 fixture）


# ---- 1. engine 依 URL 快取 ----

def test_engine_is_reused_per_database_url(tmp_path, monkeypatch):
    first_url = f"sqlite+pysqlite:///{tmp_path / 'first.db'}"
    second_url = f"sqlite+pysqlite:///{tmp_path / 'second.db'}"
    monkeypatch.setenv("DATABASE_URL", first_url)
    first = database.get_engine()
    assert database.get_engine() is first
    monkeypatch.setenv("DATABASE_URL", second_url)
    second = database.get_engine()
    assert second is not first and str(second.url) == second_url
    monkeypatch.setenv("DATABASE_URL", first_url)
    assert database.get_engine() is first


def test_get_session_uses_cached_engine(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{tmp_path / 'session.db'}")
    binds = []
    for _ in range(2):
        sessions = database.get_session()
        binds.append(next(sessions).get_bind())
        sessions.close()
    assert binds[0] is binds[1] is database.get_engine()


# ---- 4. 唯讀 GET 不拿 FOR UPDATE 鎖 ----

@contextlib.contextmanager
def locking_statements():
    # SQLite 編譯時會丟掉 FOR UPDATE，所以在 ORM 層檢查語句是否要求加鎖。
    seen = []

    def capture(state):
        if getattr(state.statement, '_for_update_arg', None) is not None:
            seen.append(str(state.statement).split('\n')[0])

    event.listen(Session, 'do_orm_execute', capture)
    try:
        yield seen
    finally:
        event.remove(Session, 'do_orm_execute', capture)


@pytest.fixture()
def files(tmp_path, monkeypatch):
    root = tmp_path / 'files'
    root.mkdir()
    monkeypatch.setenv('PF_ATTACHMENT_ROOT', str(root))
    monkeypatch.setenv('PF_ATTACHMENT_QUOTA_BYTES', '1000000000')
    return root


def binary(client, path, data=b'hello', name='a.txt'):
    response = client.post(path, params={'filename': name}, content=data, headers={'Content-Type': 'application/octet-stream'})
    assert response.status_code == 201, response.text
    return response.json()


def test_read_only_gets_do_not_lock_rows(client, engine, files):
    nid, pid, _ = setup(client, engine)
    doc = binary(client, f'/nodes/{nid}/documents')['document_id']
    attachment = binary(client, f'/nodes/{nid}/attachments')['id']
    paths = [f'/nodes/{nid}/report-fields', f'/nodes/{nid}/documents', f'/documents/{doc}/versions',
             f'/documents/{doc}/versions/1/text', f'/documents/{doc}/versions/1/download',
             f'/projects/{pid}/documents', f'/attachments/{attachment}/download', f'/nodes/{nid}/attachment-quota']
    for path in paths:
        with locking_statements() as seen:
            response = client.get(path)
        assert response.status_code == 200, (path, response.text)
        assert seen == [], (path, seen)


def test_write_paths_still_lock_rows(client, engine, files):
    nid, _, _ = setup(client, engine)
    doc = binary(client, f'/nodes/{nid}/documents')['document_id']
    attachment = binary(client, f'/nodes/{nid}/attachments')['id']
    with locking_statements() as seen:
        assert client.post(f'/documents/{doc}/text', json={'expected_version': 1, 'content': 'new'}).status_code == 201
    assert seen
    with locking_statements() as seen:
        assert client.delete(f'/attachments/{attachment}').status_code == 200
    assert seen


def test_read_only_gets_keep_authorization(client, engine, files):
    nid, _, _ = setup(client, engine)
    doc = binary(client, f'/nodes/{nid}/documents')['document_id']
    attachment = binary(client, f'/nodes/{nid}/attachments')['id']
    switch(client, 'lin')
    assert client.get(f'/attachments/{attachment}/download').status_code == 200
    assert client.get(f'/nodes/{nid}/attachment-quota').status_code == 403
    assert client.get(f'/documents/{doc}/versions').json()['can_write'] is False
    for path in ['/nodes/missing/report-fields', '/documents/missing/versions', '/attachments/missing/download']:
        assert client.get(path).status_code == 404


# ---- 5. 稽核在 SQL 層分頁與篩選 ----

def seed_audit_rows(engine, nid, users):
    with Session(engine) as db:
        node = db.get(Node, nid)
        hidden = Node(organization_id=node.organization_id, project_id=node.project_id, kind='task', title='SECRET', owner_user_id=users['yu'])
        db.add(hidden)
        db.flush()
        base = datetime(2099, 1, 1, tzinfo=timezone.utc)
        # 每三筆共用時間戳，另有一筆含微秒，驗證同時間以 id 排序、微秒與整秒的先後。
        stamps = [base + timedelta(seconds=i // 3) for i in range(12)] + [base + timedelta(seconds=3, microseconds=500000)]
        rows = []
        for i, stamp in enumerate(stamps):
            for prefix, target in [('v', node.id), ('h', hidden.id), ('o', None)]:
                row = AuditLog(id=f'{prefix}-{i:02d}', organization_id=node.organization_id, actor_user_id=users['ming'], node_id=target,
                               action='node.update' if i % 2 else 'node.status', payload={'status': 'doing'}, created_at=stamp)
                db.add(row)
                rows.append((stamp, row.id, prefix, row.action))
        db.commit()
    return rows


def walk(client, params, limit):
    ids, cursor = [], None
    while True:
        response = client.get('/audit-logs', params={**params, 'limit': limit, **({'cursor': cursor} if cursor else {})})
        assert response.status_code == 200, response.text
        body = response.json()
        assert set(body) == {'items', 'next_cursor'}
        ids.extend(item['id'] for item in body['items'])
        cursor = body['next_cursor']
        if cursor is None:
            return ids


@pytest.mark.parametrize('actor,prefixes', [('ming', {'v'}), ('yu', {'v', 'h', 'o'})])
def test_audit_logs_order_filters_and_cursor_chain(client, engine, actor, prefixes):
    nid, _, users = setup(client, engine)
    rows = seed_audit_rows(engine, nid, users)
    switch(client, actor)
    ordered = sorted(((stamp, ident) for stamp, ident, prefix, _ in rows if prefix in prefixes), reverse=True)
    everything = walk(client, {}, 100)
    assert everything[:len(ordered)] == [ident for _, ident in ordered]
    assert walk(client, {}, 3) == everything
    updates = [ident for stamp, ident, prefix, action in sorted(rows, reverse=True) if prefix in prefixes and action == 'node.update']
    assert walk(client, {'action': 'node.update'}, 2)[:len(updates)] == updates
    on_node = [ident for _, ident in ordered if ident.startswith('v-')]
    assert walk(client, {'node_id': nid}, 4)[:len(on_node)] == on_node


def test_audit_logs_load_only_one_page(client, engine):
    nid, _, users = setup(client, engine)
    seed_audit_rows(engine, nid, users)
    switch(client, 'yu')
    loaded = []

    def count(target, context):
        loaded.append(target.id)

    event.listen(AuditLog, 'load', count)
    try:
        first = client.get('/audit-logs', params={'limit': 5}).json()
        second = client.get('/audit-logs', params={'limit': 5, 'cursor': first['next_cursor']}).json()
    finally:
        event.remove(AuditLog, 'load', count)
    assert len(first['items']) == len(second['items']) == 5
    # 每頁最多多讀一筆來判斷有沒有下一頁。
    assert len(loaded) <= 12, len(loaded)


# ---- 3. 授權資料在同一批計算內共用 ----

REVIEWERS = ['chen', 'yu']

def request_notifications(engine):
    with Session(engine) as db:
        return sorted(db.execute(select(User.username, Notification.node_id, Notification.message)
                                 .join(User, User.id == Notification.recipient_id)).all())


def test_skip_request_notifies_the_same_reviewers(client, engine):
    nid, _, _ = setup(client, engine)
    response = client.post(f'/nodes/{nid}/requests', json={'kind': 'skip', 'reason': '不需要'})
    assert response.status_code == 201, response.text
    assert request_notifications(engine) == [(name, nid, '有新的跳過／覆寫申請待審核') for name in REVIEWERS]


def test_skip_request_computes_company_policy_data_once_for_all_reviewers(client, engine, monkeypatch):
    nid, _, _ = setup(client, engine)
    computed = []
    original = record_policy.company_policy_data

    def counted(db, organization_id):
        computed.append(organization_id)
        return original(db, organization_id)

    monkeypatch.setattr(record_policy, 'company_policy_data', counted)
    assert client.post(f'/nodes/{nid}/requests', json={'kind': 'skip', 'reason': '不需要'}).status_code == 201
    # lock_node 一次，通知審核者的整個迴圈共用一次。
    assert len(computed) <= 2, len(computed)
    computed.clear()
    # 共用範圍結束後，下一個請求照常重新計算，不會拿到舊資料。
    assert client.get(f'/nodes/{nid}/report-fields').status_code == 200
    assert computed


# ---- 2. 階段／專案根節點的 review、skipped（人類裁示規則 A） ----

def test_phase_review_or_skip_requires_every_child_closed(client, engine, tree):
    switch_planner(client, 'ming')
    before = planner_snapshot(engine)
    for target in ['review', 'skipped']:
        response = client.patch('/nodes/ph/status', json={'status': target})
        assert response.status_code == 409 and response.json()['detail'] == '子節點尚未全部完成', target
    assert planner_snapshot(engine) == before
    # 只剩看不到的子節點未完成時也要擋，且不透露它。
    set_status(engine, a='done', a1='done', b='skipped')
    response = client.patch('/nodes/ph/status', json={'status': 'skipped'})
    assert response.status_code == 409 and 'Secret' not in response.text
    set_status(engine, h='skipped')
    assert client.patch('/nodes/ph/status', json={'status': 'review'}).json()['status'] == 'review'
    set_status(engine, ph='doing')
    assert client.patch('/nodes/ph/status', json={'status': 'skipped'}).json()['status'] == 'skipped'


def test_phase_other_transitions_ignore_open_children(client, engine, tree):
    switch_planner(client, 'ming')
    assert client.patch('/nodes/ph/status', json={'status': 'todo'}).status_code == 200
    assert client.patch('/nodes/ph/status', json={'status': 'doing'}).status_code == 200


def test_project_root_cannot_be_set_to_review_or_skipped(client, engine, tree):
    with Session(engine) as db:
        ph = db.get(Node, 'ph')
        db.add(Node(id='root', organization_id=ph.organization_id, project_id='tp', kind='project', title='規劃器專案',
                    status='doing', owner_user_id=tree['owner'], sort_order=0))
        db.commit()
    for actor in ['owner', 'yu']:
        switch_planner(client, actor)
        for target in ['review', 'skipped']:
            response = client.patch('/nodes/root/status', json={'status': target})
            assert response.status_code == 409, (actor, target, response.text)
    with Session(engine) as db:
        assert db.get(Node, 'root').status == 'doing'
    assert client.patch('/nodes/root/status', json={'status': 'todo'}).status_code == 200
