"""N8N batch 1: weekly report facts, recipients (D84), explicit confidential exclusion (D85), AI fallback, confirm, daily digest."""
import json
from datetime import date, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai import model
from app.models import AuditLog, Node, OutboxEvent, Project, TaskReport, User, WeeklyReport, now_utc
from app.services import weekly_report_service
from test_tp_a_planner import switch, tree  # noqa: F401  (fixture)

TOKEN = 'test-token-for-n8n-0123456789'
BEARER = {'Authorization': f'Bearer {TOKEN}'}


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv('PF_N8N_TOKEN', TOKEN)
    monkeypatch.setenv('PF_AI_ROOT', str(tmp_path / 'ai'))
    return tmp_path / 'ai'


@pytest.fixture
def week(engine, tree):
    """b is doing and overdue, a1 is due in three days, done1 has an approved report this week."""
    today = weekly_report_service.local_day(now_utc())
    with Session(engine) as db:
        b, a1 = db.get(Node, 'b'), db.get(Node, 'a1')
        b.status, b.due_date = 'doing', today - timedelta(days=1)
        a1.due_date = today + timedelta(days=3)
        db.add(TaskReport(organization_id=b.organization_id, node_id='done1', result='達成', summary='配方定稿',
                          status='approved', submitted_by=tree['ming'], finished_on=today))
        db.commit()
    return today


def generate(client, project='tp'):
    response = client.post(f'/projects/{project}/weekly-reports/generate')
    assert response.status_code == 201, response.text
    return response.json()


def events(engine, kind):
    with Session(engine) as db:
        return [(e.recipient_id, e.subject) for e in db.scalars(select(OutboxEvent).where(OutboxEvent.kind == kind))]


def test_facts_recipients_and_plain_fallback(client, engine, tree, week):
    switch(client, 'owner')
    report = generate(client)
    facts = report['facts']
    assert report['status'] == 'draft' and report['model_label'] == 'AI 未啟用' and report['excluded_count'] == 0
    assert [i['title'] for i in facts['completed']] == ['已完成任務'] and facts['completed'][0]['summary'] == '配方定稿'
    assert [i['title'] for i in facts['overdue']] == ['另一個任務'] and [i['title'] for i in facts['doing']] == ['另一個任務']
    assert [i['title'] for i in facts['due_next_week']] == ['子任務']
    assert facts['silent_members'] == ['明成員']
    assert report['recipients'] == ['專案負責', '游專案']  # D84: the member ming is not a recipient
    assert '本週完成 1 項' in report['sections']['summary']
    assert [r for r, _ in events(engine, 'weekly_draft')] == [tree['owner']]


def test_explicit_confidential_only(client, engine, tree, week, isolated):
    (isolated / 'policy').mkdir(parents=True)
    (isolated / 'policy' / 'food.json').write_text(json.dumps({'mode': 'local_only', 'company': 'confidential', 'overrides': {'node:a': 'confidential'}}))
    switch(client, 'owner')
    report = generate(client)
    titles = {i['title'] for key in ('completed', 'doing', 'due_next_week', 'overdue') for i in report['facts'][key]}
    assert report['excluded_count'] == 2 and '子任務' not in titles and '另一個任務' in titles  # a and a1 hidden; company default ignored


def test_ai_section_citing_unknown_task_falls_back(client, engine, tree, week, monkeypatch):
    monkeypatch.setattr(model, 'settings', lambda company: {'enabled': True, 'model': 'fake-local', 'base_url': 'http://127.0.0.1:1'})
    monkeypatch.setattr(model, 'chat', lambda *a: {'summary': '進度穩定 [T3]', 'highlights': ['[T99] 不存在的任務'], 'risks': [], 'next': ['準備試產']})
    switch(client, 'owner')
    report = generate(client)
    assert report['model_label'] == 'fake-local' and report['sections']['summary'] == '進度穩定 [T3]'
    assert report['sections']['highlights'] == ['[T5] 已完成任務（明成員）：達成']  # plain listing replaces the [T99] section
    assert report['sections']['next'] == ['準備試產']
    with Session(engine) as db:
        assert db.scalar(select(AuditLog).where(AuditLog.action == 'ai.weekly_report')).payload['model'] == 'fake-local'


def test_model_failure_still_produces_a_draft(client, tree, week, monkeypatch):
    monkeypatch.setattr(model, 'settings', lambda company: {'enabled': True, 'model': 'fake-local', 'base_url': 'http://127.0.0.1:1'})
    def boom(*a):
        raise TimeoutError('slow')
    monkeypatch.setattr(model, 'chat', boom)
    switch(client, 'owner')
    report = generate(client)
    assert '改用原始整理' in report['model_label'] and '本週完成 1 項' in report['sections']['summary']


def test_permissions_edit_confirm_and_recheck(client, engine, tree, week):
    switch(client, 'ming')
    assert client.get('/projects/tp/weekly-reports').status_code == 403
    assert client.post('/projects/tp/weekly-reports/generate').status_code == 403
    switch(client, 'owner')
    report = generate(client)
    sections = dict(report['sections'], summary='負責人改寫的摘要')
    assert client.patch(f"/weekly-reports/{report['id']}", json={'sections': {'summary': 1}}).status_code == 422
    assert client.patch(f"/weekly-reports/{report['id']}", json={'sections': sections}).json()['sections']['summary'] == '負責人改寫的摘要'
    switch(client, 'lin')
    assert client.get('/projects/tp/weekly-reports').json()['items'] == []  # readonly sees sent reports only
    assert client.post(f"/weekly-reports/{report['id']}/confirm", json={}).status_code == 403
    with Session(engine) as db:
        db.get(User, tree['yu']).status = 'disabled'
        db.commit()
    switch(client, 'owner')
    confirmed = client.post(f"/weekly-reports/{report['id']}/confirm", json={}).json()
    assert confirmed['removed'] == ['游專案'] and confirmed['report']['status'] == 'sent'
    sent = events(engine, 'weekly_report')
    assert [r for r, _ in sent] == [tree['owner']] and '規劃器專案 週報' in sent[0][1]
    with Session(engine) as db:
        body = db.scalar(select(OutboxEvent).where(OutboxEvent.kind == 'weekly_report')).body_text
        assert '負責人改寫的摘要' in body and '【AI 建議】' in body
        audit = db.scalar(select(AuditLog).where(AuditLog.action == 'weekly_report.confirm'))
        assert audit.payload['edited'] == ['summary'] and '負責人改寫的摘要' not in json.dumps(audit.payload, ensure_ascii=False)
    assert client.post('/projects/tp/weekly-reports/generate').status_code == 409
    assert client.post(f"/weekly-reports/{report['id']}/confirm", json={}).status_code == 409
    switch(client, 'lin')
    assert len(client.get('/projects/tp/weekly-reports').json()['items']) == 1


def test_old_draft_becomes_unsent(client, engine, tree, week):
    with Session(engine) as db:
        project = db.get(Project, 'tp')
        db.add(WeeklyReport(organization_id=project.organization_id, project_id='tp', week_start=date(2020, 1, 6), status='draft',
                            model_label='AI 未啟用', generated_by=tree['owner']))
        db.commit()
    switch(client, 'owner')
    generate(client)
    with Session(engine) as db:
        assert db.scalar(select(WeeklyReport.status).where(WeeklyReport.week_start == date(2020, 1, 6))) == 'unsent'


def test_integration_generate_and_daily_digest(client, engine, tree, week):
    response = client.post('/integrations/weekly-reports/generate', json={'project_ids': ['tp']}, headers=BEARER)
    assert response.json() == {'generated': 1, 'skipped_sent': 0, 'kept_draft': 0}
    with Session(engine) as db:
        assert db.scalar(select(AuditLog).where(AuditLog.action == 'weekly_report.generate')).payload['via'] == 'n8n'
    first = client.post('/integrations/daily-digest', headers=BEARER).json()['enqueued']
    assert first >= 1 and client.post('/integrations/daily-digest', headers=BEARER).json()['enqueued'] == 0
    digests = {r: s for r, s in events(engine, 'daily_digest')}
    assert tree['ming'] in digests  # ming owns the overdue task b
    with Session(engine) as db:
        body = db.scalar(select(OutboxEvent).where(OutboxEvent.kind == 'daily_digest', OutboxEvent.recipient_id == tree['ming'])).body_text
        assert '已逾期（1）' in body and '另一個任務' in body


def test_schedule_keeps_edited_draft_and_deleted_task_keeps_recipients(client, engine, tree, week):
    switch(client, 'owner')
    report = generate(client)
    client.patch(f"/weekly-reports/{report['id']}", json={'sections': dict(report['sections'], summary='手動改過')})
    again = client.post('/integrations/weekly-reports/generate', json={'project_ids': ['tp']}, headers=BEARER).json()
    assert again == {'generated': 0, 'skipped_sent': 0, 'kept_draft': 1}
    with Session(engine) as db:
        db.get(Node, 'a1').deleted_at = now_utc()
        db.commit()
    confirmed = client.post(f"/weekly-reports/{report['id']}/confirm", json={}).json()
    assert confirmed['removed'] == [] and confirmed['report']['sections']['summary'] == '手動改過'
    assert len(events(engine, 'weekly_report')) == 2


def test_long_ai_output_is_capped(client, tree, week, monkeypatch):
    monkeypatch.setattr(model, 'settings', lambda company: {'enabled': True, 'model': 'fake-local', 'base_url': 'http://127.0.0.1:1'})
    monkeypatch.setattr(model, 'chat', lambda *a: {'summary': '長' * 3000, 'highlights': ['點' * 900] * 30, 'risks': [], 'next': []})
    switch(client, 'owner')
    report = generate(client)
    assert len(report['sections']['summary']) == 2000 and len(report['sections']['highlights']) == 20
    assert client.post(f"/weekly-reports/{report['id']}/confirm", json={}).status_code == 200
