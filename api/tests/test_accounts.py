from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, Node, User
from test_projects_nodes import login


def sign_in(client, username, password, org='food', **kwargs):
    return client.post('/auth/login', json={'organization_key': org, 'username': username, 'password': password}, **kwargs)


def new_account(client, username='wang', role='member'):
    response = client.post('/accounts', json={'username': username, 'display_name': '王小明', 'role': role})
    assert response.status_code == 201, response.text
    return response.json()


def test_admin_creates_account_and_temporary_password_must_be_changed(client, engine):
    login(client, username='yu')
    made = new_account(client)
    temporary = made['temporary_password']
    assert made['account']['must_change_password'] is True and len(temporary) >= 10
    assert client.post('/accounts', json={'username': 'wang', 'display_name': '重複', 'role': 'member'}).status_code == 409
    client.post('/auth/logout')
    first = sign_in(client, 'wang', temporary)
    assert first.status_code == 200 and first.json()['user']['must_change_password'] is True
    assert client.get('/auth/me').status_code == 200
    assert client.get('/projects').status_code == 403
    for bad in ['short', 'wang', 'demo-1234567890']:
        assert client.post('/auth/password', json={'current_password': temporary, 'new_password': bad}).status_code == 422
    assert client.post('/auth/password', json={'current_password': 'wrong', 'new_password': 'a-good-password'}).status_code == 422
    assert client.post('/auth/password', json={'current_password': temporary, 'new_password': 'a-good-password'}).status_code == 200
    assert client.get('/projects').status_code == 200
    assert 'must_change_password' not in client.get('/auth/me').json()['user']
    client.post('/auth/logout')
    assert sign_in(client, 'wang', temporary).status_code == 401
    assert sign_in(client, 'wang', 'a-good-password').status_code == 200
    with Session(engine) as db:
        logs = db.scalars(select(AuditLog).where(AuditLog.action.like('account.%'))).all()
        assert {a.action for a in logs} == {'account.create', 'account.password_change'}
        assert temporary not in str([a.payload for a in logs]) and 'a-good-password' not in str([a.payload for a in logs])


def test_disable_ends_sessions_keeps_history_and_can_be_restored(client, engine):
    login(client, username='yu')
    with Session(engine) as db:
        ming = db.scalar(select(User).where(User.username == 'ming'))
        owned = db.scalar(select(Node.id).where(Node.owner_user_id == ming.id))
    other = client.__class__(client.app)
    assert sign_in(other, 'ming', 'demo-ming').status_code == 200
    assert other.get('/auth/me').status_code == 200
    changed = client.patch(f'/accounts/{ming.id}', json={'status': 'disabled'})
    assert changed.status_code == 200 and changed.json()['status'] == 'disabled'
    assert other.get('/auth/me').status_code == 401
    assert sign_in(other, 'ming', 'demo-ming').status_code == 401
    with Session(engine) as db:
        assert db.get(Node, owned).owner_user_id == ming.id
    assert client.patch(f'/accounts/{ming.id}', json={'status': 'active'}).status_code == 200
    assert sign_in(other, 'ming', 'demo-ming').status_code == 200


def test_reset_password_logs_out_and_requires_change(client, engine):
    login(client, username='yu')
    with Session(engine) as db:
        ming = db.scalar(select(User.id).where(User.username == 'ming'))
    other = client.__class__(client.app)
    assert sign_in(other, 'ming', 'demo-ming').status_code == 200
    temporary = client.post(f'/accounts/{ming}/reset-password').json()['temporary_password']
    assert other.get('/auth/me').status_code == 401
    assert sign_in(other, 'ming', 'demo-ming').status_code == 401
    assert sign_in(other, 'ming', temporary).json()['user']['must_change_password'] is True


def test_admin_protections_and_permissions(client, engine):
    login(client, username='yu')
    with Session(engine) as db:
        ids = {u.username: u.id for u in db.scalars(select(User))}
    assert client.patch(f'/accounts/{ids["yu"]}', json={'status': 'disabled'}).status_code == 409
    assert client.patch(f'/accounts/{ids["yu"]}', json={'role': 'member'}).status_code == 409
    assert client.patch(f'/accounts/{ids["chen"]}', json={'role': 'boss'}).status_code == 422
    assert client.post('/accounts', json={'username': 'Bad Name', 'display_name': 'x', 'role': 'member'}).status_code == 422
    listed = client.get('/accounts').json()
    names = {a['username'] for a in listed['items']}
    assert {'yu', 'chen', 'ming', 'lin', 'owner'} <= names and 'elaine' not in names
    assert all('password_hash' not in a and 'temporary_password' not in a for a in listed['items'])
    for user in ['ming', 'lin']:
        client.post('/auth/logout'); login(client, username=user)
        assert client.get('/accounts').status_code == 403
        assert client.post(f'/accounts/{ids["chen"]}/reset-password').status_code == 403
    client.post('/auth/logout'); login(client, 'electronics', 'elaine')
    assert client.patch(f'/accounts/{ids["ming"]}', json={'status': 'disabled'}).status_code == 404
    assert client.post(f'/accounts/{ids["ming"]}/reset-password').status_code == 404


def test_last_admin_cannot_be_removed(client, engine):
    login(client, username='yu')
    second = new_account(client, 'boss2', 'admin')
    with Session(engine) as db:
        yu = db.scalar(select(User.id).where(User.username == 'yu'))
    # Another admin may demote yu while a second admin remains; then yu (now member) cannot touch accounts.
    client.post('/auth/logout')
    sign_in(client, 'boss2', second['temporary_password'])
    client.post('/auth/password', json={'current_password': second['temporary_password'], 'new_password': 'boss2-password'})
    assert client.patch(f'/accounts/{yu}', json={'role': 'member'}).status_code == 200
    assert client.patch(f'/accounts/{second["account"]["id"]}', json={'status': 'disabled'}).status_code == 409


def test_demo_password_refused_on_public_host_only(client, monkeypatch):
    public = {'host': 'trial.example.ts.net'}
    assert sign_in(client, 'yu', 'demo-yu', headers=public).status_code == 403
    assert sign_in(client, 'yu', 'demo-yu').status_code == 200
    temporary = client.post('/accounts', json={'username': 'pub', 'display_name': '公開', 'role': 'member'}).json()['temporary_password']
    client.post('/auth/logout')
    assert sign_in(client, 'pub', temporary, headers=public).status_code == 200
    client.post('/auth/logout')
    monkeypatch.setenv('PF_DISABLE_DEMO_PASSWORDS', 'true')
    assert sign_in(client, 'yu', 'demo-yu').status_code == 403
    assert sign_in(client, 'yu', 'wrong').status_code == 401


def test_failed_logins_pause_only_that_account_from_that_address(client):
    assert all(sign_in(client, 'yu', 'demo-yu').status_code == 200 for _ in range(25))
    codes = [sign_in(client, 'yu', 'wrong').status_code for _ in range(21)]
    assert codes[:20] == [401] * 20 and codes[20] == 429
    assert sign_in(client, 'YU', 'demo-yu').status_code == 429
    # Everyone else behind the same address (e.g. the nginx hop) still signs in.
    assert sign_in(client, 'ming', 'demo-ming').status_code == 200
    assert sign_in(client, 'elaine', 'demo-elaine', org='electronics').status_code == 200
