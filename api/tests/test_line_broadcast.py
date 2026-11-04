"""LINE broadcast (D89): which outbox events also carry a short LINE text, exactly once per happening."""
from datetime import timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import OperationsRecord, OutboxEvent, Project, User, now_utc
from app.services import weekly_report_service
from test_tp_a_planner import switch, tree  # noqa: F401  (fixture)

TOKEN = 'test-token-for-n8n-0123456789'
BEARER = {'Authorization': f'Bearer {TOKEN}'}


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv('PF_N8N_TOKEN', TOKEN)
    monkeypatch.setenv('PF_AI_ROOT', str(tmp_path / 'ai'))
    monkeypatch.setenv('PF_BACKUP_ROOT', str(tmp_path / 'backups'))
    monkeypatch.setenv('PF_ATTACHMENT_ROOT', str(tmp_path / 'files'))
    (tmp_path / 'files').mkdir()
    return tmp_path


def lines(engine, kind):
    with Session(engine) as db:
        return [e.line_text for e in db.scalars(select(OutboxEvent).where(OutboxEvent.kind == kind).order_by(OutboxEvent.created_at))]


def test_assignment_carries_title_only_line_text(client, tree):
    switch(client, 'owner')
    assert client.patch('/nodes/b', json={'owner_user_id': tree['yu']}).status_code == 200
    item = client.get('/integrations/events', headers=BEARER).json()['items'][0]
    assert item['line_text'] == '[專流] 你被指派為任務負責人\n任務：另一個任務'
    assert '127.0.0.1' not in item['line_text']  # no link: the app is loopback-only, phones cannot open it


def test_mail_only_events_have_empty_line_text(client, engine, tree):
    with Session(engine) as db:
        from app.models import Node
        b = db.get(Node, 'b')
        b.status, b.due_date = 'doing', weekly_report_service.local_day(now_utc()) - timedelta(days=1)
        db.commit()
    assert client.post('/integrations/daily-digest', headers=BEARER).json()['enqueued'] >= 1
    items = client.get('/integrations/events', headers=BEARER).json()['items']
    assert items and all(i['line_text'] == '' for i in items if i['kind'] == 'daily_digest')
    switch(client, 'owner')
    client.post('/projects/tp/weekly-reports/generate')
    assert lines(engine, 'weekly_draft') == [None]


def test_weekly_report_broadcasts_once_without_content(client, engine, tree):
    switch(client, 'owner')
    report = client.post('/projects/tp/weekly-reports/generate').json()
    client.patch(f"/weekly-reports/{report['id']}", json={'sections': dict(report['sections'], summary='機密的摘要內文')})
    client.post(f"/weekly-reports/{report['id']}/confirm", json={})
    sent = lines(engine, 'weekly_report')
    assert len(sent) == 2 and sum(bool(x) for x in sent) == 1
    text = next(x for x in sent if x)
    assert '規劃器專案 週報已寄出' in text and '機密的摘要內文' not in text


def test_expiry_and_backup_failure_broadcast_once(client, engine, tree, monkeypatch):
    today = weekly_report_service.local_day(now_utc())
    with Session(engine) as db:
        org = db.get(Project, 'tp').organization_id
        db.add(OperationsRecord(organization_id=org, category='partners', code='CERT-L', title='ISO 證書', status='有效', visibility='internal',
                                fields=[{'label': '到期日', 'value': (today + timedelta(days=5)).isoformat()}], created_by=tree['yu'], updated_by=tree['yu']))
        db.commit()
        managers = len(list(db.scalars(select(User).where(User.organization_id == org, User.role.in_(['admin', 'project_owner'])))))
    client.post('/integrations/maintenance/expiry', headers=BEARER)
    expiry = lines(engine, 'expiry')
    assert managers >= 2 and len(expiry) == managers and sum(bool(x) for x in expiry) == 1
    assert '即將到期：ISO 證書' in next(x for x in expiry if x)

    import app.demo_pack

    def broken(*args, **kwargs):
        raise OSError('disk full')
    monkeypatch.setattr(app.demo_pack, 'export_pack', broken)
    assert client.post('/integrations/maintenance/backup', headers=BEARER).status_code == 500
    failed = lines(engine, 'backup')
    assert len(failed) >= 2 and sum(bool(x) for x in failed) == 1 and '每日備份失敗' in next(x for x in failed if x)


def test_successful_backup_does_not_broadcast(client, engine, tree, monkeypatch):
    from alembic import command
    from alembic.config import Config
    from test_migrations import ALEMBIC_INI
    command.stamp(Config(ALEMBIC_INI), 'head')
    assert client.post('/integrations/maintenance/backup', headers=BEARER).status_code == 200
    assert all(x is None for x in lines(engine, 'backup'))


def test_line_migration_round_trip(tmp_path, monkeypatch):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, inspect
    from test_migrations import ALEMBIC_INI
    url = f'sqlite:///{tmp_path / "line.db"}'
    monkeypatch.setenv('DATABASE_URL', url)
    config = Config(ALEMBIC_INI)
    command.upgrade(config, 'head')
    engine = create_engine(url)
    assert 'line_text' in {c['name'] for c in inspect(engine).get_columns('outbox_events')}
    command.downgrade(config, '20261102_0024')
    assert 'line_text' not in {c['name'] for c in inspect(create_engine(url)).get_columns('outbox_events')}
    engine.dispose()
