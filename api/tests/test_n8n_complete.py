"""N8N complete (D87): mail settings, failed-mail resend, outbox lease, weekly safeguards, inbox, Excel import, backup, expiry."""
import io
import json
import os
import time
import zipfile
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (AuditLog, Document, Node, OperationLink, OperationsRecord, OutboxEvent, Project, TaskReport, User,
                        now_utc)
from app.services import daily_digest_service, weekly_report_service
from test_tp_a_planner import switch, tree  # noqa: F401  (fixture)

TOKEN = 'test-token-for-n8n-0123456789'
BEARER = {'Authorization': f'Bearer {TOKEN}'}


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv('PF_N8N_TOKEN', TOKEN)
    monkeypatch.setenv('PF_AI_ROOT', str(tmp_path / 'ai'))
    monkeypatch.setenv('PF_INBOX_ROOT', str(tmp_path / 'inbox'))
    monkeypatch.setenv('PF_BACKUP_ROOT', str(tmp_path / 'backups'))
    monkeypatch.setenv('PF_ATTACHMENT_ROOT', str(tmp_path / 'files'))
    (tmp_path / 'inbox').mkdir()
    (tmp_path / 'files').mkdir()
    from app.services import inbox_service
    # Files written by the test are "settled" except the one that simulates a copy still in progress.
    monkeypatch.setattr(inbox_service, 'settled', lambda path: path.name != '還在複製.txt')
    return tmp_path


def xlsx(rows):
    """Minimal workbook with inline strings, enough for the hardened parser."""
    def cell(ref, value):
        if isinstance(value, (int, float)):
            return f'<c r="{ref}"><v>{value}</v></c>'
        return f'<c r="{ref}" t="inlineStr"><is><t>{value}</t></is></c>'
    sheet = ''.join(f'<row r="{n}">' + ''.join(cell(f'{chr(65 + i)}{n}', v) for i, v in enumerate(row)) + '</row>' for n, row in enumerate(rows, 1))
    files = {
        '[Content_Types].xml': '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>',
        '_rels/.rels': '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        'xl/workbook.xml': '<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="供應商" sheetId="1" r:id="rId1"/></sheets></workbook>',
        'xl/_rels/workbook.xml.rels': '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>',
        'xl/worksheets/sheet1.xml': f'<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>{sheet}</sheetData></worksheet>',
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        for name, body in files.items():
            archive.writestr(name, body)
    return buffer.getvalue()


def drop(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    old = time.time() - 60
    os.utime(path, (old, old))  # already "settled", as if copied in a minute ago


def kinds(engine, kind):
    with Session(engine) as db:
        return list(db.scalars(select(OutboxEvent).where(OutboxEvent.kind == kind)))


# ---- batch 1 completion -------------------------------------------------------------------------

def test_email_settings_and_audit_without_address(client, engine, tree):
    switch(client, 'ming')
    assert client.get('/accounts/me/email').json() == {'email': 'ming@demo.local', 'email_notify': True}
    assert client.patch('/accounts/me/email', json={'email': 'not-an-email', 'email_notify': True}).status_code == 422
    assert client.patch('/accounts/me/email', json={'email': ' ming@corp.example ', 'email_notify': False}).json() == {'email': 'ming@corp.example', 'email_notify': False}
    with Session(engine) as db:
        audit = db.scalar(select(AuditLog).where(AuditLog.action == 'account.email_update'))
        assert audit.payload == {'email_changed': True, 'email_notify': False} and 'corp.example' not in json.dumps(audit.payload)


def test_failed_mail_list_and_retry_are_admin_only(client, engine, tree):
    switch(client, 'owner')
    assert client.patch('/nodes/b', json={'owner_user_id': tree['yu']}).status_code == 200
    event_id = client.get('/integrations/events', headers=BEARER).json()['items'][0]['id']
    for _ in range(5):
        client.post(f'/integrations/events/{event_id}/result', json={'ok': False, 'error': 'SMTP 550'}, headers=BEARER)
    assert client.get('/mail/failed').status_code == 403
    switch(client, 'yu')
    rows = client.get('/mail/failed').json()['items']
    assert [(r['id'], r['last_error']) for r in rows] == [(event_id, 'SMTP 550')]
    assert client.post(f'/mail/{event_id}/retry').json() == {'status': 'pending'}
    assert client.post(f'/mail/{event_id}/retry').status_code == 409
    assert [i['id'] for i in client.get('/integrations/events', headers=BEARER).json()['items']] == [event_id]


def test_pulled_event_is_leased_for_five_minutes(client, engine, tree):
    switch(client, 'owner')
    client.patch('/nodes/b', json={'owner_user_id': tree['yu']})
    assert len(client.get('/integrations/events', headers=BEARER).json()['items']) == 1
    assert client.get('/integrations/events', headers=BEARER).json()['items'] == []  # still leased
    with Session(engine) as db:
        db.scalar(select(OutboxEvent)).claimed_at = now_utc() - timedelta(minutes=6)
        db.commit()
    assert len(client.get('/integrations/events', headers=BEARER).json()['items']) == 1


def test_damaged_policy_stops_weekly_reports(client, isolated, tree):
    (isolated / 'ai' / 'policy').mkdir(parents=True)
    (isolated / 'ai' / 'policy' / 'food.json').write_text('{broken', encoding='utf-8')
    switch(client, 'owner')
    response = client.post('/projects/tp/weekly-reports/generate')
    assert response.status_code == 503 and '分級' in response.json()['detail']


def test_task_marked_confidential_after_draft_blocks_confirm(client, isolated, tree):
    switch(client, 'owner')
    report = client.post('/projects/tp/weekly-reports/generate').json()
    (isolated / 'ai' / 'policy').mkdir(parents=True)
    (isolated / 'ai' / 'policy' / 'food.json').write_text(json.dumps({'mode': 'local_only', 'company': 'confidential', 'overrides': {'node:b': 'confidential'}}))
    response = client.post(f"/weekly-reports/{report['id']}/confirm", json={})
    assert response.status_code == 409 and '機密' in response.json()['detail']


def test_monday_digest_looks_back_to_friday(client, engine, tree):
    monday = datetime(2026, 11, 2, 1, 0, tzinfo=timezone.utc)  # 09:00 in Taipei
    with Session(engine) as db:
        b = db.get(Node, 'b')
        db.add(TaskReport(organization_id=b.organization_id, node_id='done1', result='達成', summary='完成', status='approved',
                          submitted_by=tree['ming'], finished_on=date(2026, 10, 30)))
        db.commit()
        assert daily_digest_service.enqueue_all(db, monday) == 1
        db.commit()
        body = db.scalar(select(OutboxEvent).where(OutboxEvent.kind == 'daily_digest')).body_text
    assert '上個工作日完成（1）' in body and '已完成任務' in body


# ---- batch 2: inbox -----------------------------------------------------------------------------

def test_inbox_document_is_stored_parsed_and_owner_notified(client, engine, isolated, tree):
    folder = isolated / 'inbox' / 'food' / '規劃器專案'
    drop(folder / '會議紀錄.txt', '殺菌溫度改為 121 度。'.encode('utf-8'))
    drop(folder / '工具.exe', b'MZ')
    fresh = folder / '還在複製.txt'
    fresh.write_bytes(b'copying')
    summary = client.post('/integrations/inbox/scan', headers=BEARER).json()
    assert summary == {'documents': 1, 'imports': 0, 'failed': 1}
    assert fresh.exists()  # too new to touch
    assert [p.name.split('-', 2)[-1] for p in (folder / '已匯入').iterdir()] == ['會議紀錄.txt']
    failed = sorted(p.name for p in (folder / '失敗').iterdir())
    assert len(failed) == 2 and any(n.endswith('.原因.txt') for n in failed)
    with Session(engine) as db:
        assert db.scalar(select(Document).where(Document.project_id == 'tp')) is not None
        owner = db.get(Project, 'tp').owner_user_id
    mail = kinds(engine, 'inbox_document')
    assert [m.recipient_id for m in mail] == [owner] and '規劃器專案' in mail[0].body_text and '解析結果' in mail[0].body_text


def test_excel_import_creates_then_updates_records(client, engine, isolated, tree):
    folder = isolated / 'inbox' / 'food' / '_營運資料匯入'
    drop(folder / '供應商.xlsx', xlsx([['代碼', '名稱', '狀態', '電話', '到期日'], ['sup-x', '新供應商', '合作中', '02-1234', 46387]]))
    assert client.post('/integrations/inbox/scan', headers=BEARER).json()['imports'] == 1
    with Session(engine) as db:
        db.scalar(select(OperationsRecord).where(OperationsRecord.code == 'SUP-X')).visibility = 'restricted'
        db.commit()
    drop(folder / '供應商.xlsx', xlsx([['代碼', '名稱', '電話', '保存日數'], ['SUP-X', '新供應商（更名）', '02-9999', 30000]]))
    assert client.post('/integrations/inbox/scan', headers=BEARER).json()['imports'] == 1
    drop(folder / '供應商.xlsx', xlsx([['名稱'], ['沒有代碼']]))
    assert client.post('/integrations/inbox/scan', headers=BEARER).json()['failed'] == 1
    drop(folder / '不存在的分類.xlsx', xlsx([['代碼', '名稱'], ['A', 'B']]))
    assert client.post('/integrations/inbox/scan', headers=BEARER).json()['failed'] == 1
    with Session(engine) as db:
        record = db.scalar(select(OperationsRecord).where(OperationsRecord.code == 'SUP-X'))
        assert record.title == '新供應商（更名）' and record.revision == 2 and record.source == 'import'
        # An update merges: the restricted visibility, the status and fields missing from the sheet are kept.
        assert record.visibility == 'restricted' and record.status == '合作中'
        assert {f['label']: f['value'] for f in record.fields} == {'電話': '02-9999', '到期日': '2026-12-31', '保存日數': '30000'}
    assert len(kinds(engine, 'inbox_import')) == 2


# ---- batch 3: backup and expiry -----------------------------------------------------------------

def test_backup_is_full_restorable_pack_and_keeps_seven(client, engine, isolated, tree):
    backups = isolated / 'backups'
    backups.mkdir()
    from app.models import DocumentTemplate, DocumentTemplateVersion
    (isolated / 'files' / 'template-key').write_bytes(b'docx bytes')
    with Session(engine) as db:
        org = db.get(Project, 'tp').organization_id
        db.add(DocumentTemplate(id='tpl', organization_id=org, name='報價單', category='報價', current_version=1, status='active',
                                created_by=tree['yu'], created_at=now_utc()))
        db.flush()
        db.add(DocumentTemplateVersion(id='tplv', organization_id=org, template_id='tpl', version=1, filename='報價單.docx',
                                       storage_key='template-key', size_bytes=10, sha256='0' * 64, fields=[], numbering='Q-{seq}',
                                       tax_rate='0.05', rounding='round', has_lines=False, created_by=tree['yu'], created_at=now_utc()))
        db.commit()
    for n in range(8):
        (backups / f'projectflow-backup-2020010{n}-000000.zip').write_bytes(b'old')
    result = client.post('/integrations/maintenance/backup', headers=BEARER).json()
    files = sorted(p.name for p in backups.iterdir())
    assert len(files) == 7 and result['file'] in files
    with zipfile.ZipFile(backups / result['file']) as archive:
        manifest = json.loads(archive.read('manifest.json'))
        users = json.loads(archive.read('tables/users.json'))
    assert manifest['full'] is True and 'audit_logs' in manifest['tables'] and 'sessions' not in manifest['tables']
    assert all(u.get('password_hash') for u in users)
    assert set(manifest['files']) == {'template-key'}  # Word template files travel with a backup
    with Session(engine) as db:
        admins = set(db.scalars(select(User.id).where(User.role == 'admin')))
    assert {m.recipient_id for m in kinds(engine, 'backup')} == admins


def test_expiry_reminds_and_opens_one_task_under_linked_node(client, engine, tree):
    today = weekly_report_service.local_day(now_utc())
    with Session(engine) as db:
        org = db.get(Project, 'tp').organization_id
        record = OperationsRecord(organization_id=org, category='partners', code='CERT-1', title='HACCP 證書', status='有效', visibility='internal',
                                  fields=[{'label': '證書到期日', 'value': (today + timedelta(days=10)).isoformat()}], created_by=tree['yu'], updated_by=tree['yu'])
        later = OperationsRecord(organization_id=org, category='partners', code='CERT-2', title='遠期證書', status='有效', visibility='internal',
                                 fields=[{'label': '到期日', 'value': (today + timedelta(days=90)).isoformat()}], created_by=tree['yu'], updated_by=tree['yu'])
        db.add_all([record, later])
        db.flush()
        db.add(OperationLink(organization_id=org, project_id='tp', node_id='ph', record_id=record.id, created_by=tree['yu']))
        db.commit()
    first = client.post('/integrations/maintenance/expiry', headers=BEARER).json()
    assert first['tasks'] == 1 and first['reminded'] >= 2
    assert client.post('/integrations/maintenance/expiry', headers=BEARER).json() == {'reminded': 0, 'tasks': 0}
    with Session(engine) as db:
        task = db.scalar(select(Node).where(Node.title.like('更新到期：HACCP 證書%')))
        assert task.parent_id == 'ph' and task.kind == 'task' and task.owner_user_id == tree['ming']
        assert db.scalar(select(Node).where(Node.title.like('更新到期：遠期證書%'))) is None
    assert all('HACCP' in m.subject for m in kinds(engine, 'expiry'))


def test_full_backup_restores_into_empty_database_with_real_passwords(client, engine, tmp_path, monkeypatch):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine
    from app.demo_pack import export_pack, import_pack
    from test_migrations import ALEMBIC_INI
    command.stamp(Config(ALEMBIC_INI), 'head')  # the fixture database is built with create_all, so give it a revision
    pack = export_pack(engine, tmp_path / 'files', full=True)
    url = f'sqlite:///{tmp_path / "restored.db"}'
    monkeypatch.setenv('DATABASE_URL', url)
    command.upgrade(Config(ALEMBIC_INI), 'head')
    target = create_engine(url)
    (tmp_path / 'restored-files').mkdir()
    counts = import_pack(target, pack.__getitem__, tmp_path / 'restored-files')
    assert counts['users'] >= 5 and 'audit_logs' in counts
    with Session(engine) as db:
        original = {u.username: u.password_hash for u in db.scalars(select(User))}
    with Session(target) as db:
        assert {u.username: u.password_hash for u in db.scalars(select(User))} == original
    target.dispose()
