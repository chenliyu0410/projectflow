"""N8N batch 1: Bearer-only integration API and the mail outbox fed by site notifications."""
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Node, OutboxEvent, User
from test_projects_nodes import login
from test_tp_a_planner import switch, tree  # noqa: F401  (fixture)

TOKEN = 'test-token-for-n8n-0123456789'
BEARER = {'Authorization': f'Bearer {TOKEN}'}


@pytest.fixture(autouse=True)
def token(monkeypatch, tmp_path):
    monkeypatch.setenv('PF_N8N_TOKEN', TOKEN)
    monkeypatch.setenv('PF_AI_ROOT', str(tmp_path / 'ai'))


def pull(client):
    response = client.get('/integrations/events', headers=BEARER)
    assert response.status_code == 200, response.text
    return response.json()['items']


def assign(client, node_id, user_id):
    assert client.patch(f'/nodes/{node_id}', json={'owner_user_id': user_id}).status_code == 200


def test_token_is_required_and_only_works_on_integrations(client, monkeypatch):
    assert client.get('/integrations/events').status_code == 401
    assert client.get('/integrations/events', headers={'Authorization': 'Bearer wrong-token-wrong-token-xx'}).status_code == 401
    login(client)
    assert client.get('/integrations/events').status_code == 401  # a browser session is not enough
    client.post('/auth/logout')
    assert client.get('/projects', headers=BEARER).status_code == 401  # nor is the token on ordinary APIs
    monkeypatch.setenv('PF_N8N_TOKEN', 'short')
    assert client.get('/integrations/events', headers={'Authorization': 'Bearer short'}).status_code == 401


def test_notification_queues_mail_once_and_delivery_is_idempotent(client, engine, tree):
    switch(client, 'owner')
    assign(client, 'b', tree['yu'])
    with Session(engine) as db:
        db.get(Node, 'b').title = '<script>x</script>任務'
        db.commit()
    items = pull(client)
    assert [(i['to'], i['kind']) for i in items] == [('yu@demo.local', 'notification')]
    assert '你被指派為任務負責人' in items[0]['subject']
    event_id = items[0]['id']
    for _ in range(2):
        response = client.post(f'/integrations/events/{event_id}/result', json={'ok': True}, headers=BEARER)
        assert response.json()['status'] == 'sent'
    assert pull(client) == []
    with Session(engine) as db:
        assert db.scalar(select(OutboxEvent).where(OutboxEvent.id == event_id)).sent_at is not None


def test_html_body_is_escaped(client, engine, tree):
    with Session(engine) as db:
        db.get(Node, 'b').title = '<script>alert(1)</script>'
        db.commit()
    switch(client, 'owner')
    assign(client, 'b', tree['yu'])
    item = pull(client)[0]
    assert '<script>' not in item['html'] and '&lt;script&gt;' in item['html']


def test_five_failures_stop_retrying(client, tree):
    switch(client, 'owner')
    assign(client, 'b', tree['yu'])
    event_id = pull(client)[0]['id']
    for attempt in range(1, 6):
        body = client.post(f'/integrations/events/{event_id}/result', json={'ok': False, 'error': 'SMTP down'}, headers=BEARER).json()
        assert body['attempts'] == attempt
    assert body['status'] == 'failed'
    assert pull(client) == []
    assert client.post('/integrations/events/missing/result', json={'ok': True}, headers=BEARER).status_code == 404


def test_recipient_without_mail_is_skipped(client, engine, tree):
    with Session(engine) as db:
        db.get(User, tree['yu']).email_notify = False
        db.commit()
    switch(client, 'owner')
    assign(client, 'b', tree['yu'])
    assert pull(client) == []
    with Session(engine) as db:
        assert [e.status for e in db.scalars(select(OutboxEvent))] == ['skipped']


def test_rolled_back_change_queues_no_mail(client, engine, tree):
    switch(client, 'owner')
    assert client.patch('/nodes/b', json={'owner_user_id': 'no-such-user'}).status_code >= 400
    with Session(engine) as db:
        assert db.scalars(select(OutboxEvent)).all() == []


def test_migration_keeps_users_and_refuses_lossy_downgrade(tmp_path, monkeypatch):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, text
    from test_migrations import ALEMBIC_INI
    url = f'sqlite:///{tmp_path / "n8n.db"}'
    monkeypatch.setenv('DATABASE_URL', url)
    config = Config(ALEMBIC_INI)
    command.upgrade(config, '20261024_0021')
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO organizations (id,key,name) VALUES ('o','o','Org')"))
        conn.execute(text("INSERT INTO users (id,organization_id,username,display_name,role,password_hash,created_at) VALUES ('u','o','old','Old','member','x','2026-10-01')"))
    command.upgrade(config, 'head')
    with engine.begin() as conn:
        assert conn.execute(text("SELECT email, email_notify FROM users")).one() == (None, 1)
        conn.execute(text("UPDATE users SET email='old@demo.local'"))
    with pytest.raises(RuntimeError, match='拒絕有損降級'):
        command.downgrade(config, '20261024_0021')
    with engine.begin() as conn:
        conn.execute(text("UPDATE users SET email=NULL"))
    command.downgrade(config, '20261024_0021')
    engine.dispose()
