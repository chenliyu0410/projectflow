"""Manual prerequisite evidence, serialized with all other project writes."""
from fastapi import HTTPException
from sqlalchemy import select
from app.audit import log_audit
from app.models import Node, NodeCondition, now_utc
from app.permissions import can_manage_project, can_view_node
from app.services.dependency_service import lock_project
from app.services.record_policy import load_policy_context


def condition_out(item):
    return {key: (getattr(item, key).isoformat() if key in {'confirmed_at', 'created_at'} and getattr(item, key) else getattr(item, key))
            for key in ('id', 'project_id', 'node_id', 'label', 'enforcement', 'is_met', 'confirmed_by', 'confirmed_at', 'reason', 'created_by', 'created_at')}


def authorize(db, current, project_id, node_id):
    project = lock_project(db, current, project_id)
    if not can_manage_project(current, project):
        raise HTTPException(status_code=403, detail='沒有設定人工確認條件權限')
    context = load_policy_context(db, current)
    node = db.scalar(select(Node).where(Node.organization_id == current.organization.id, Node.project_id == project.id, Node.id == node_id))
    if node is None or not can_view_node(current, node, context=context):
        raise HTTPException(status_code=404, detail='找不到任務')
    if node.kind != 'task':
        raise HTTPException(status_code=422, detail='人工確認條件只能設定在任務上')


def create_condition(db, current, project_id, payload):
    authorize(db, current, project_id, payload.node_id)
    item = NodeCondition(organization_id=current.organization.id, project_id=project_id, created_by=current.user.id, **payload.model_dump())
    db.add(item)
    db.flush()
    log_audit(db, current, 'condition.create', node_id=item.node_id, payload=condition_out(item))
    db.commit()
    return condition_out(item)


def mutate_condition(db, current, condition_id, action, payload=None):
    found = db.scalar(select(NodeCondition).where(NodeCondition.organization_id == current.organization.id, NodeCondition.id == condition_id))
    if found is None:
        raise HTTPException(status_code=404, detail='找不到人工確認條件')
    authorize(db, current, found.project_id, found.node_id)
    item = db.scalar(select(NodeCondition).where(NodeCondition.organization_id == current.organization.id, NodeCondition.id == condition_id).with_for_update().execution_options(populate_existing=True))
    if item is None:
        raise HTTPException(status_code=404, detail='找不到人工確認條件')
    before = condition_out(item)
    if action == 'confirm':
        item.is_met = payload.is_met
        item.reason = payload.reason
        item.confirmed_by = current.user.id
        item.confirmed_at = now_utc()
    elif action == 'update':
        # Editing the meaning invalidates earlier confirmation evidence.
        values = payload.model_dump(exclude_unset=True)
        if 'label' in values and item.label != values['label']:
            item.is_met = False
            item.confirmed_by = item.confirmed_at = item.reason = None
        for key, value in values.items():
            setattr(item, key, value)
    elif action == 'delete':
        db.delete(item)
    after = condition_out(item)
    log_audit(db, current, 'condition.' + action, node_id=item.node_id, payload={'before': before, 'after': None if action == 'delete' else after})
    db.commit()
    return {'id': condition_id, 'deleted': True} if action == 'delete' else after
