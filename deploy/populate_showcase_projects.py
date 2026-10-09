"""One-time, additive local showcase maintenance; preview unless --apply.

Run with the API environment and app on PYTHONPATH. No schema changes.
"""
import argparse
from datetime import date, timedelta
import json
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session
from app.audit import log_audit
from app.auth import CurrentUser
from app.database import get_engine
from app.models import Organization, User, Project, Node, Gate, NodeDependency, AuditLog
from app.schemas import WorkflowWrite
from app.services.workflow_service import validate_graph
from app.showcase import catalog, enabled, identifier

START = date(2026, 10, 9)
TARGETS = [('food', '成貓主食罐正式版', 'food-development'),
           ('electronics', '連接器新產品正式版', 'electronics-0')]
RENAMES = {'PCB 設計': '連接器結構與端子設計', '機構模具': '連接器模具開發',
           '韌體開發': '端子材料與接觸電阻驗證', '工業設計': '連接器外觀與介面設計'}


def stable(project_id, key):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, 'projectflow:project-fill:v1:'+project_id+':'+key))


def actor(db, org):
    user = db.get(User, identifier('user:'+org.key))
    if user is None or user.organization_id != org.id or user.role != 'admin':
        raise RuntimeError('Provisioned showcase administrator required')
    return CurrentUser(user=user, organization=org, token='')


def populate(db):
    if not enabled():
        raise RuntimeError('Explicit local showcase mode required')
    result = []
    for company, title, key in TARGETS:
        org = db.scalar(select(Organization).where(Organization.key == company))
        if org is None:
            raise RuntimeError('Target organization missing')
        project = db.scalars(select(Project).where(Project.organization_id == org.id, Project.title == title).with_for_update()).one()
        current = actor(db, org)
        marker = stable(project.id, 'applied')
        if db.get(AuditLog, marker):
            result.append({'project': title, 'already_applied': True})
            continue
        entry = next(e for e in catalog() if e['key'] == key and e['industry'] == company)
        payload = WorkflowWrite(name=entry['name'], nodes=entry['nodes'], dependencies=entry['dependencies'])
        ordered = validate_graph(payload)
        roots = list(db.scalars(select(Node).where(Node.project_id == project.id, Node.parent_id.is_(None))))
        base_order = max((n.sort_order for n in roots), default=0) + 10
        mapping = {}; added = 0; reused = 0
        for template in ordered:
            matches = [n for n in roots if template.kind == 'phase' and n.kind == 'phase' and n.title == template.title]
            if len(matches) > 1:
                raise RuntimeError('Ambiguous existing phase; no changes committed')
            if matches:
                node = matches[0]; reused += 1
            else:
                node = Node(id=stable(project.id, template.id), organization_id=org.id, project_id=project.id,
                            parent_id=mapping.get(template.parent_id), kind=template.kind,
                            title=RENAMES.get(template.title, template.title) if company == 'electronics' else template.title,
                            status='todo', owner_user_id=project.owner_user_id,
                            sort_order=base_order+template.sort_order,
                            start_date=START+timedelta(days=template.start_offset) if template.start_offset is not None else None,
                            due_date=START+timedelta(days=template.due_offset) if template.due_offset is not None else None)
                db.add(node); db.flush(); added += 1
            mapping[template.id] = node.id
            if template.gate_after and not db.scalar(select(Gate.id).where(Gate.project_id == project.id, Gate.node_id == node.id)):
                db.add(Gate(organization_id=org.id, project_id=project.id, node_id=node.id))
        for edge in payload.dependencies:
            db.add(NodeDependency(organization_id=org.id, project_id=project.id,
                                 predecessor_id=mapping[edge.predecessor_id], successor_id=mapping[edge.successor_id], created_by=current.user.id))
        audit = log_audit(db, current, 'workflow.apply_existing', payload={'project_id':project.id, 'catalog_key':key,
                         'start_date':START.isoformat(), 'nodes_added':added, 'phases_reused':reused, 'title_adjustments':RENAMES if company == 'electronics' else {}})
        audit.id = marker
        result.append({'project':title, 'nodes_added':added, 'phases_reused':reused})
    # Explicit user deletion: allow only the observed empty project root.
    food = db.scalar(select(Organization).where(Organization.key == 'food'))
    matches = list(db.scalars(select(Project).where(Project.organization_id == food.id, Project.title == 'waa').with_for_update()))
    if len(matches) > 1:
        raise RuntimeError('Ambiguous waa project')
    if matches:
        project = matches[0]
        nodes = list(db.scalars(select(Node).where(Node.project_id == project.id)))
        if len(nodes) != 1 or nodes[0].kind != 'project' or nodes[0].title != 'waa' or nodes[0].status != 'todo':
            raise RuntimeError('waa changed: refuse to delete unexpected content')
        # Check every table referencing a node/project, including notes, reports and files.
        for table in Node.metadata.sorted_tables:
            if table.name in {'nodes','projects'}:
                continue
            for column in table.columns:
                if any(fk.column.table.name in {'nodes','projects'} for fk in column.foreign_keys):
                    values = [nodes[0].id] if any(fk.column.table.name == 'nodes' for fk in column.foreign_keys) else [project.id]
                    if db.execute(select(table).where(column.in_(values)).limit(1)).first():
                        raise RuntimeError('waa has related content; refuse deletion')
        pid=project.id
        db.delete(nodes[0]); db.flush(); db.delete(project); db.flush()
        log_audit(db, actor(db, food), 'project.delete', payload={'project_id':pid, 'title':'waa', 'reason':'人類要求移除空白展示專案'})
        result.append({'deleted_project':'waa'})
    db.flush()
    return result


if __name__ == '__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--apply', action='store_true'); args=parser.parse_args()
    with Session(get_engine()) as db:
        result=populate(db)
        if args.apply: db.commit()
        else: db.rollback()
        print(json.dumps({'applied':args.apply, 'result':result},ensure_ascii=False))
