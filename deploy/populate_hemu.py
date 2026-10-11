"""Add the approved fictional company atomically; never update existing rows."""
import argparse
import json
import secrets
import uuid
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.orm import Session
from app.audit import log_audit
from app.auth import CurrentUser
from app.database import get_engine
from app.models import Organization, User, Department, DepartmentMember, Project, Node, NodeDependency, TaskNote, AuditLog
from app.security import hash_password
from app.showcase import enabled, identifier, USERNAME
from app.schemas import ProjectCreate, NodeCreate, NodeStatusUpdate, ReportCreate, ReportReview
from app.routes.projects import create_project, create_node, update_node_status
from app.services.report_service import submit_report, review_report


class AtomicSession(Session):
    def commit(self):
        self.flush()


MARKER = str(uuid.uuid5(uuid.NAMESPACE_URL, 'projectflow:hemu:v1:import'))


def populate(db, data, *, existing_company=False):
    if not isinstance(db, AtomicSession):
        raise RuntimeError("AtomicSession required")
    key = data["company"]["key"]
    if (existing_company and key not in {"food", "electronics", "events", "software", "construction"}) or (not existing_company and key != "hemu"):
        raise RuntimeError("Unsupported import target")
    marker_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "projectflow:industries:v1:" + key)) if existing_company else MARKER
    if not enabled():
        raise RuntimeError('Local showcase mode required')
    if db.bind.dialect.name == 'postgresql':
        db.execute(text('SELECT pg_advisory_xact_lock(20261011, 7201)'))
    marker = db.get(AuditLog, marker_id)
    org = db.scalar(select(Organization).where(Organization.key == key))
    if marker:
        if org is None or marker.organization_id != org.id:
            raise RuntimeError('Import marker identity mismatch')
        return {'existing': True, 'organization_id': org.id}
    if existing_company:
        if org is None:
            raise RuntimeError('Existing showcase company required')
        admin = db.get(User, identifier('user:' + key))
        if not admin or admin.organization_id != org.id or admin.username != USERNAME or admin.role != 'admin':
            raise RuntimeError('Dedicated showcase admin identity mismatch')
    else:
        if org is not None:
            raise RuntimeError('Untracked hemu organization exists; refusing to overwrite')
        org = Organization(key=key, name=data['company']['name'])
        db.add(org); db.flush()
        admin = User(id=identifier('user:hemu'), organization_id=org.id, username=USERNAME,
                     display_name='禾沐展示管理者', role='admin', password_hash=hash_password(secrets.token_urlsafe(48)))
        db.add(admin); db.flush()
    current = CurrentUser(user=admin, organization=org, token='')
    prefix = key + '_20261011_' if existing_company else 'hemu_'
    for person in data['people']:
        if db.scalar(select(User.id).where(User.organization_id == org.id, User.username == prefix + person['key'])):
            raise RuntimeError('Reserved username collision; refusing to overwrite')
    for spec in data['departments']:
        if db.scalar(select(Department.id).where(Department.organization_id == org.id, Department.name == spec['name'])):
            raise RuntimeError('Department name collision; refusing to overwrite')
    for spec in data['projects']:
        if db.scalar(select(Project.id).where(Project.organization_id == org.id, Project.title == '【虛構展示】' + spec['code'] + ' ' + spec['title'])):
            raise RuntimeError('Project title collision; refusing to overwrite')
    log_audit(db, current, 'showcase.dataset_append' if existing_company else 'showcase.organization_create', payload={'fictional': True, 'company': data['company'], 'admin_user_id': admin.id})
    users = {}
    for person in data['people']:
        user = User(organization_id=org.id, username=prefix + person['key'], display_name=person['name'],
                    role=person['role'], password_hash=hash_password(secrets.token_urlsafe(48)))
        db.add(user); db.flush(); users[person['key']] = user
        log_audit(db, current, 'showcase.user_create', payload={'user_id': user.id, 'title': person['title'], 'fictional': True})
    departments = {}
    for spec in data['departments']:
        department = Department(organization_id=org.id, name=spec['name'], head_user_id=users[spec['head']].id)
        db.add(department); db.flush(); departments[spec['name']] = department
        for person in data['people']:
            if person['department'] == spec['name']:
                db.add(DepartmentMember(organization_id=org.id, department_id=department.id, user_id=users[person['key']].id))
        log_audit(db, current, 'showcase.department_create', payload={'department_id': department.id, 'fictional': True})
    db.flush()
    person_specs = {p['key']: p for p in data['people']}
    project_ids = []
    for spec in data['projects']:
        created = create_project(ProjectCreate(title='【虛構展示】' + spec['code'] + ' ' + spec['title']), current, db)
        project = db.get(Project, created['id'])
        project.owner_user_id = users[spec['owner']].id
        root = db.scalar(select(Node).where(Node.project_id == project.id, Node.kind == 'project'))
        root.owner_user_id = project.owner_user_id
        log_audit(db, current, 'project.assign', node_id=root.id, payload={'owner_user_id': project.owner_user_id, 'fictional': True})
        nodes = {}; states = []; phases = []
        for phase_spec in spec['phases']:
            tasks = phase_spec['tasks']
            phase = create_node(project.id, NodeCreate(title=phase_spec['title'], kind='phase', parent_id=root.id,
                owner_user_id=project.owner_user_id, start_date=min(t['start'] for t in tasks), due_date=max(t['due'] for t in tasks)), current, db)
            phases.append((phase['id'], tasks))
            for task in tasks:
                person = person_specs[task['owner']]
                node = create_node(project.id, NodeCreate(title=task['title'], kind='task', parent_id=phase['id'],
                    owner_user_id=users[task['owner']].id, department_id=departments[person['department']].id,
                    start_date=task['start'], due_date=task['due']), current, db)
                nodes[task['key']] = node['id']; states.append(task)
        for task in states:
            for predecessor in task['deps']:
                dep = NodeDependency(organization_id=org.id, project_id=project.id,
                    predecessor_id=nodes[predecessor], successor_id=nodes[task['key']], created_by=admin.id)
                db.add(dep); db.flush()
                log_audit(db, current, 'dependency.create', node_id=nodes[task['key']], payload={'predecessor_id': nodes[predecessor], 'fictional': True})
        db.flush()
        for task in states:
            nid = nodes[task['key']]
            if task['state'] in {'done', 'review', 'rejected'}:
                actor = CurrentUser(user=users[task['owner']], organization=org, token='')
                report = submit_report(db, actor, nid, ReportCreate(result='達成',
                    summary='【虛構展示】' + (task['summary'] or task['title'] + '：成果已整理並提交主管確認。'),
                    finished_on=min(task['due'], '2026-10-11')))
                if task['state'] != 'review':
                    review_report(db, current, report['id'], ReportReview(decision='approved' if task['state'] == 'done' else 'rejected',
                        comment=task['summary'] or '【虛構展示】已確認成果。'))
            elif task['state'] == 'doing':
                update_node_status(nid, NodeStatusUpdate(status='doing'), current, db)
            if task['summary']:
                note = TaskNote(organization_id=org.id, node_id=nid, author_id=admin.id, body='【虛構展示】' + task['summary'])
                db.add(note); db.flush()
                log_audit(db, current, 'note.create', node_id=nid, payload={'note_id': note.id, 'fictional': True})
        for phase_id, tasks in phases:
            state = 'done' if all(t['state'] == 'done' for t in tasks) else 'doing' if any(t['state'] != 'todo' for t in tasks) else 'todo'
            if state != 'todo':
                update_node_status(phase_id, NodeStatusUpdate(status=state), current, db)
        # Persist the complete approved reference data without inventing operational CRUD.
        dossier = {k: v for k, v in data.items() if k != 'projects'}
        for label, value in dossier.items():
            note = TaskNote(organization_id=org.id, node_id=root.id, author_id=admin.id,
                body='【' + data['company']['name'] + '虛構展示資料／參考快照】' + label + '\n' + json.dumps(value, ensure_ascii=False, indent=2))
            db.add(note); db.flush()
            log_audit(db, current, 'note.create', node_id=root.id, payload={'note_id': note.id, 'fictional': True})
        project_ids.append(project.id)
    marker = log_audit(db, current, 'showcase.industry_import' if existing_company else 'showcase.hemu_import', payload={'fictional': True, 'project_ids': project_ids, 'version': 1})
    marker.id = marker_id
    db.flush()
    return {'existing': False, 'organization_id': org.id, 'project_ids': project_ids, 'people': len(users), 'departments': len(departments)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=Path, default=Path(__file__).resolve().parents[1] / 'web/src/preview/hemu.json')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    with AtomicSession(get_engine()) as db:
        result = populate(db, json.loads(args.data.read_text(encoding='utf-8')))
        if args.apply:
            Session.commit(db)
        else:
            db.rollback()
        print(json.dumps({'applied': args.apply, **result}, ensure_ascii=False))
