import copy
import json
import sys
from pathlib import Path
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import Organization, User, Department, Project, Node, TaskReport
from app.auth import CurrentUser
from app.showcase import provision, identifier
from app.services.node_policy import node_out
from app.services.report_service import review_report
from app.schemas import ReportReview

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'deploy'))
from populate_industries import populate_all, validate, snapshot, assert_preserved
from populate_hemu import populate, AtomicSession


def data():
    return json.loads((ROOT / 'web/src/preview/industries.json').read_text(encoding='utf-8'))


def test_five_datasets_dry_run_preservation_idempotence_real_reports_and_isolation(client, engine, monkeypatch):
    monkeypatch.setenv('PF_SHOWCASE_MODE', 'true')
    payload = data()
    with AtomicSession(engine) as db:
        provision(db)
        populate(db, json.loads((ROOT / 'web/src/preview/hemu.json').read_text(encoding='utf-8')))
        Session.commit(db)
        before = snapshot(db)
        populate_all(db, payload); db.rollback()
        assert snapshot(db) == before
        result = populate_all(db, payload); Session.commit(db)
        after = snapshot(db); assert_preserved(before, after)
        for key, item in result.items():
            org = db.get(Organization, item['organization_id'])
            actor = CurrentUser(user=db.get(User, identifier('user:' + key)), organization=org, token='')
            assert len(item['project_ids']) == 4
            tasks = list(db.scalars(select(Node).where(Node.project_id.in_(item['project_ids']), Node.kind == 'task')))
            assert len(tasks) == 26
            assert {'done', 'doing', 'review', 'todo'} <= {n.status for n in tasks}
            assert any(node_out(db, actor, db.get(Project, n.project_id), n)['blocked'] for n in tasks)
            report = db.scalar(select(TaskReport).where(TaskReport.node_id.in_([n.id for n in tasks]), TaskReport.status == 'submitted'))
            review_report(db, actor, report.id, ReportReview(decision='approved', comment='隔離驗收'))
            assert db.get(Node, report.node_id).status == 'done'
            tasks[0].title += '（使用者修改）'
        Session.commit(db)
        customized = snapshot(db)
        assert all(r['existing'] for r in populate_all(db, payload).values())
        Session.commit(db); assert snapshot(db) == customized
    client.base_url = 'http://127.0.0.1'
    assert client.post('/auth/login', json={'organization_key': 'food', 'username': 'yu', 'password': 'demo-yu'}).status_code == 200
    previous = None
    for key in result:
        switched = client.post('/auth/showcase/switch', json={'organization_key': key}, headers={'Origin': 'http://127.0.0.1'})
        assert switched.status_code == 200
        ids = {p['id'] for p in client.get('/projects').json()['items']}
        assert set(result[key]['project_ids']) <= ids
        if previous:
            assert client.get('/projects/' + previous).status_code == 404
        previous = result[key]['project_ids'][0]


def test_late_collision_and_missing_company_rollback(client, engine, monkeypatch):
    monkeypatch.setenv('PF_SHOWCASE_MODE', 'true')
    payload = data()
    with AtomicSession(engine) as db:
        # Provision is used only in this isolated test, never on the user database.
        provision(db); Session.commit(db)
        software = db.scalar(select(Organization).where(Organization.key == 'software'))
        db.add(Department(organization_id=software.id, name=payload['software']['departments'][0]['name']))
        Session.commit(db); before = snapshot(db)
        with pytest.raises(RuntimeError, match='Department name collision'):
            populate_all(db, payload)
        db.rollback(); assert snapshot(db) == before
        monkeypatch.setenv('PF_SHOWCASE_MODE', 'false')
        with pytest.raises(RuntimeError, match='mode required'):
            populate_all(db, payload)
        assert snapshot(db) == before


def test_dataset_validation_rejects_broken_links_and_cycles():
    payload = data(); validate(payload)
    bad = copy.deepcopy(payload)
    bad['events']['groups'][2]['records'][0]['links'][0]['code'] = 'missing'
    with pytest.raises(ValueError, match='Broken operational link'):
        validate(bad)
    bad = copy.deepcopy(payload)
    bad['food']['projects'][0]['phases'][0]['tasks'][0]['deps'] = ['t7']
    with pytest.raises(ValueError, match='dependency ordering'):
        validate(bad)


def test_acceptance_follows_training_equipment_and_event_dates():
    payload = data()
    software = payload['software']
    acceptance = software['projects'][1]['phases'][2]['tasks'][0]
    training = next(r for g in software['groups'] for r in g['records'] if r['code'] == 'YS-S03')
    work = next(r for g in software['groups'] for r in g['records'] if r['code'] == 'YS-W02')
    assert acceptance['start'] > training['fields']['日期']
    assert acceptance['due'] == work['fields']['驗收']
    construction = payload['construction']
    delivery = next(r for g in construction['groups'] for r in g['records'] if r['code'] == 'ZH-PO03')
    work = next(r for g in construction['groups'] for r in g['records'] if r['code'] == 'ZH-W02')
    acceptance = construction['projects'][1]['phases'][2]['tasks'][0]
    assert acceptance['start'] > delivery['fields']['交期']
    assert acceptance['due'] == work['fields']['暫排']
    event_tasks = payload['events']['projects'][0]['phases'][2]['tasks']
    assert event_tasks[0]['due'] == '2026-10-29'
    assert event_tasks[1]['start'] == event_tasks[1]['due'] == '2026-10-30'
