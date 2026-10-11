import json
import sys
from pathlib import Path
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import Base
from app.models import Organization, Project, Node, TaskReport, User
from app.seed import seed_demo_data
from app.auth import CurrentUser
from app.services.node_policy import node_out
from app.routes.projects import get_project
from app.schemas import ReportReview
from app.services.report_service import review_report
from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'deploy'))
from populate_hemu import populate, AtomicSession


def data():
    return json.loads((ROOT / 'web/src/preview/hemu.json').read_text(encoding='utf-8'))


def snapshot(db):
    return {t.name: [dict(r) for r in db.execute(select(t)).mappings()] for t in Base.metadata.sorted_tables}


def test_import_preservation_idempotence_and_real_workflow(engine, monkeypatch):
    monkeypatch.setenv('PF_SHOWCASE_MODE', 'true')
    with AtomicSession(engine) as db:
        seed_demo_data(db); Session.commit(db)
        before = snapshot(db)
        result = populate(db, data()); Session.commit(db)
        after = snapshot(db)
        for table, rows in before.items():
            assert all(row in after[table] for row in rows), table
        assert len(result['project_ids']) == 4
        org = db.get(Organization, result['organization_id'])
        users = list(db.scalars(select(User).where(User.organization_id == org.id)))
        assert len(users) == 13
        admin = next(user for user in users if user.username == '_showcase_demo')
        current = CurrentUser(user=admin, organization=org, token='')
        nodes = list(db.scalars(select(Node).where(Node.organization_id == org.id)))
        assert len([n for n in nodes if n.kind == 'task']) == 25
        assert {'done', 'doing', 'review', 'todo'} <= {n.status for n in nodes}
        blocked = next(n for n in nodes if n.title == '試產及製程紀錄')
        assert node_out(db, current, db.get(Project, blocked.project_id), blocked)['blocked']
        # A rerun must keep a user's subsequent edits, not restore initial seed data.
        edited = next(n for n in nodes if n.title == '罐身與易開蓋相容性確認')
        edited.title += '（使用者補充）'; Session.commit(db)
        customized = snapshot(db)
        assert populate(db, data())['existing']; Session.commit(db)
        assert snapshot(db) == customized
        report = db.scalar(select(TaskReport).where(TaskReport.organization_id == org.id, TaskReport.status == 'submitted'))
        review_report(db, current, report.id, ReportReview(decision='approved', comment='隔離驗收'))
        assert db.get(Node, report.node_id).status == 'done'
        other = db.scalar(select(Organization).where(Organization.key == 'food'))
        other_admin = db.scalar(select(User).where(User.organization_id == other.id, User.role == 'admin'))
        with pytest.raises(HTTPException) as exc:
            get_project(result['project_ids'][0], CurrentUser(user=other_admin, organization=other, token=''), db)
        assert exc.value.status_code == 404


def test_dry_run_collision_and_disabled(engine, monkeypatch):
    monkeypatch.setenv('PF_SHOWCASE_MODE', 'true')
    with AtomicSession(engine) as db:
        before = snapshot(db)
        populate(db, data()); db.rollback()
        assert snapshot(db) == before
        db.add(Organization(key='hemu', name='使用者原有公司')); Session.commit(db)
        before = snapshot(db)
        with pytest.raises(RuntimeError, match='refusing to overwrite'):
            populate(db, data())
        db.rollback(); assert snapshot(db) == before
        monkeypatch.setenv('PF_SHOWCASE_MODE', 'false')
        with pytest.raises(RuntimeError, match='mode required'):
            populate(db, data())


def test_late_failure_rolls_back_all(engine, monkeypatch):
    monkeypatch.setenv('PF_SHOWCASE_MODE', 'true')
    payload = data()
    payload['projects'][-1]['phases'][-1]['tasks'][-1]['deps'] = ['missing']
    with AtomicSession(engine) as db:
        before = snapshot(db)
        with pytest.raises(KeyError):
            populate(db, payload)
        db.rollback()
        assert snapshot(db) == before


def test_existing_admin_can_switch_to_hemu(client, engine, monkeypatch):
    monkeypatch.setenv('PF_SHOWCASE_MODE', 'true')
    with AtomicSession(engine) as db:
        result = populate(db, data()); Session.commit(db)
    client.base_url = 'http://127.0.0.1'
    login = client.post('/auth/login', json={'organization_key': 'food', 'username': 'yu', 'password': 'demo-yu'})
    assert login.status_code == 200
    old_project = client.get('/projects').json()['items'][0]['id']
    switched = client.post('/auth/showcase/switch', json={'organization_key': 'hemu'}, headers={'Origin': 'http://127.0.0.1'})
    assert switched.status_code == 200
    assert switched.json()['organization']['id'] == result['organization_id']
    assert len(client.get('/projects').json()['items']) == 4
    assert client.get('/projects/' + old_project).status_code == 404
