"""Personal, permission-filtered notifications committed with their source transaction."""
from uuid import uuid4
from sqlalchemy import select, event
from sqlalchemy.orm import Session
from app.auth import CurrentUser
from app.models import Notification, Node, NodeDependency, NodeCondition, Gate
from app.permissions import can_view_node
from app.services.record_policy import load_policy_context, shared_policy_data


def emit(db, current, node, recipient_id, message, event_key):
    if not recipient_id or recipient_id == current.user.id:
        return
    context = load_policy_context(db, current)
    user = context.users.get(recipient_id)
    if user is None:
        return
    recipient = CurrentUser(user, current.organization, '')
    rc = load_policy_context(db, recipient)
    if not can_view_node(recipient, node, context=rc):
        return
    if db.scalar(select(Notification.id).where(Notification.organization_id == current.organization.id, Notification.recipient_id == recipient_id, Notification.event_key == event_key)):
        return
    db.add(Notification(organization_id=current.organization.id, recipient_id=recipient_id, node_id=node.id, event_key=event_key, message=message))


def states(db, current, project_id):
    from app.services.dependency_service import unmet_dependencies
    nodes = {n.id: n for n in db.scalars(select(Node).where(Node.organization_id == current.organization.id, Node.project_id == project_id))}
    edges = list(db.scalars(select(NodeDependency).where(NodeDependency.organization_id == current.organization.id, NodeDependency.project_id == project_id)))
    conditions = list(db.scalars(select(NodeCondition).where(NodeCondition.organization_id == current.organization.id, NodeCondition.project_id == project_id)))
    gates = list(db.scalars(select(Gate).where(Gate.organization_id == current.organization.id, Gate.project_id == project_id, Gate.status == 'pending')))
    result = {}
    for n in nodes.values():
        if n.kind != 'task':
            continue
        try:
            blocked = any(e.enforcement == 'hard' for e in unmet_dependencies(nodes, edges, conditions, n))
            chain, cursor = set(), n
            phase = None
            while cursor is not None and cursor.id not in chain:
                chain.add(cursor.id)
                if phase is None and cursor.kind == 'phase': phase = cursor
                cursor = nodes.get(cursor.parent_id)
            blocked = blocked or (n.status == 'todo' and phase is not None and any(g.node_id in nodes and nodes[g.node_id].sort_order < phase.sort_order for g in gates))
        except Exception as exc:
            from fastapi import HTTPException
            if not isinstance(exc, HTTPException): raise
            blocked = True
        result[n.id] = (bool(blocked), n.owner_user_id, n.status)
    return result


def watch(db, current, project_id):
    watches = db.info.setdefault('notification_watches', {})
    if project_id not in watches:
        watches[project_id] = (current, states(db, current, project_id))


@event.listens_for(Session, 'before_commit')
def finish_notifications(db):
    watches = db.info.pop('notification_watches', {})
    if not watches:
        return
    db.flush()
    operation = str(uuid4())
    # 這裡只新增通知；一次操作改到多個任務時，每封通知不必各自重算整個公司的授權資料。
    with shared_policy_data(db):
        for pid, (current, before) in watches.items():
            after = states(db, current, pid)
            for nid, (blocked, owner, status) in after.items():
                old = before.get(nid)
                node = db.get(Node, nid)
                if owner and (old is None or old[1] != owner):
                    emit(db, current, node, owner, '你被指派為任務負責人', operation + ':assign:' + nid)
                if old and old[0] and not blocked and status in {'todo','doing'}:
                    emit(db, current, node, owner, '前置條件已滿足，任務現在可以開始', operation + ':unlock:' + nid)


@event.listens_for(Session, 'after_rollback')
def clear_notifications(db):
    db.info.pop('notification_watches', None)
