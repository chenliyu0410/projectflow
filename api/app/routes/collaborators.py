"""Explicit, node-scoped collaboration management."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from app.audit import log_audit
from app.auth import CurrentUser, require_session
from app.database import get_session
from app.models import Node, Project, NodeCollaborator
from app.permissions import can_manage_project, can_view_node, can_view_project
from app.schemas import CollaboratorsUpdate
from app.services.record_policy import load_policy_context
from app.services.report_service import lock_node, conflict

router = APIRouter(tags=['collaborators'])


def collaborators_out(db, node, context):
    rows = list(db.scalars(select(NodeCollaborator).where(NodeCollaborator.organization_id == node.organization_id, NodeCollaborator.node_id == node.id)))
    users = [{'id': row.user_id, 'display_name': context.users[row.user_id].display_name}
             for row in rows if row.user_id in context.users]
    departments = [{'id': row.department_id, 'name': context.departments[row.department_id].name}
                   for row in rows if row.department_id in context.departments]
    return {'users': sorted(users, key=lambda x: x['id']), 'departments': sorted(departments, key=lambda x: x['id']),
            'revision': node.collaborators_revision}


@router.get('/nodes/{node_id}/collaborators')
def get_collaborators(node_id: str, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    context = load_policy_context(db, current)
    node = db.scalar(select(Node).where(Node.id == node_id, Node.organization_id == current.organization.id))
    project = db.scalar(select(Project).where(Project.id == node.project_id, Project.organization_id == current.organization.id)) if node else None
    if (node is None or project is None or not can_view_project(current, project)
            or not can_view_node(current, node, context=context)):
        raise HTTPException(status_code=404, detail='找不到節點')
    return collaborators_out(db, node, context)


@router.put('/nodes/{node_id}/collaborators')
def replace_collaborators(node_id: str, payload: CollaboratorsUpdate,
                          current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    node, project, context = lock_node(db, current, node_id)
    if not can_manage_project(current, project):
        raise HTTPException(status_code=403, detail='沒有管理協作的權限')
    if node.collaborators_revision != payload.expected_revision:
        conflict()
    users, departments = set(payload.user_ids), set(payload.department_ids)
    if (any(uid not in context.users or context.users[uid].role == 'readonly' for uid in users)
            or any(did not in context.departments for did in departments)):
        raise HTTPException(status_code=422, detail='協作人員或部門無效')
    before = collaborators_out(db, node, context)
    if users != {u['id'] for u in before['users']} or departments != {d['id'] for d in before['departments']}:
        db.execute(delete(NodeCollaborator).where(NodeCollaborator.organization_id == node.organization_id, NodeCollaborator.node_id == node.id))
        for uid in sorted(users):
            db.add(NodeCollaborator(organization_id=node.organization_id, node_id=node.id, user_id=uid, created_by=current.user.id))
        for did in sorted(departments):
            db.add(NodeCollaborator(organization_id=node.organization_id, node_id=node.id, department_id=did, created_by=current.user.id))
        node.collaborators_revision += 1
        db.flush()
        after = collaborators_out(db, node, context)
        log_audit(db, current, 'collaborators.update', node_id=node.id, payload={'before': before, 'after': after})
        db.commit()
    return collaborators_out(db, node, context)
