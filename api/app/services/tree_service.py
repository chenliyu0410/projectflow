"""TP-B tree editing: move, copy, soft delete and a one-step undo of the user's last structure change."""
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import log_audit
from app.auth import CurrentUser
from app.models import INCLUDE_DELETED, AuditLog, Node, NodeCollaborator, NodeDependency, now_utc
from app.permissions import can_manage_project, can_move_node, can_view_node
from app.services.dependency_service import lock_project
from app.services.node_policy import node_out
from app.services.record_policy import load_policy_context
from app.services.report_service import lock_node

CLOSED_PARENT = {"review", "done", "skipped"}
FINISHED = {"done", "skipped"}
UNDOABLE = ("node.create", "node.delete", "node.move", "node.copy")
COPY_LIMIT = 300
COPY_SUFFIX = "（複本）"

MOVE_CLOSED = "不能移到已完成、待確認或已略過的任務底下"
MOVE_CYCLE = "不能移到自己的子任務底下"
MOVE_DEPENDENCY = "移動後會和前置相依衝突，請先移除相依連線"
UNDO_CHANGED = "之後已有其他變更，無法復原"
UNDO_PARENT = "原本的上層已無法放回，無法復原"
UNDO_RELATED = "相關任務已有變更，無法復原"


def can_move(db: Session, current: CurrentUser, project, node, context) -> bool:
    return can_move_node(db, current, project, node, departments=context.departments)


def project_nodes(db: Session, current: CurrentUser, project_id: str, *, include_deleted=False) -> dict[str, Node]:
    statement = select(Node).where(Node.organization_id == current.organization.id, Node.project_id == project_id)
    if include_deleted:
        statement = statement.execution_options(**{INCLUDE_DELETED: True})
    return {n.id: n for n in db.scalars(statement)}


def family_of(nodes: dict[str, Node], root_id: str) -> list[str]:
    """The root and its stored descendants, parents before children, siblings in display order."""
    children: dict[str | None, list[Node]] = {}
    for item in nodes.values():
        children.setdefault(item.parent_id, []).append(item)
    order, seen, pending = [], set(), [root_id]
    while pending:
        current_id = pending.pop(0)
        if current_id in seen:
            continue
        seen.add(current_id)
        order.append(current_id)
        pending.extend(child.id for child in sorted(children.get(current_id, []), key=lambda n: (n.sort_order, n.created_at, n.id)))
    return order


def edges_touching(db: Session, current: CurrentUser, project_id: str, ids) -> list[NodeDependency]:
    ids = list(ids)
    return list(db.scalars(select(NodeDependency).where(
        NodeDependency.organization_id == current.organization.id, NodeDependency.project_id == project_id,
        NodeDependency.predecessor_id.in_(ids) | NodeDependency.successor_id.in_(ids)).order_by(NodeDependency.id)))


def project_root(nodes: dict[str, Node]) -> Node | None:
    return next((n for n in nodes.values() if n.kind == "project" and n.parent_id is None), None)


def check_placement(db: Session, current: CurrentUser, project, node: Node, target: Node | None, nodes: dict[str, Node],
                    *, closed_detail=MOVE_CLOSED, cycle_detail=MOVE_CYCLE, closed_ok=False):
    """Shared move rules: no cycle through the stored chain, no closed parent, no edge between subtree and new ancestors.

    `closed_ok` lets an undo put a finished subtree back under a finished parent (D74 only forbids open children there).
    """
    chain, cursor = [], target
    while cursor is not None:
        if cursor.id == node.id:
            raise HTTPException(status_code=409, detail=cycle_detail)
        if cursor.id in chain:
            raise HTTPException(status_code=409, detail="節點階層異常，無法移動")
        chain.append(cursor.id)
        cursor = nodes.get(cursor.parent_id) if cursor.parent_id is not None else None
    if target is not None and target.milestone:
        raise HTTPException(status_code=409, detail="里程碑不能有子任務，請先取消里程碑")
    if target is not None and target.status in CLOSED_PARENT and not closed_ok:
        raise HTTPException(status_code=409, detail=closed_detail)
    if not chain:
        return
    family = set(family_of(nodes, node.id))
    edge = db.scalar(select(NodeDependency.id).where(
        NodeDependency.organization_id == current.organization.id, NodeDependency.project_id == project.id,
        ((NodeDependency.predecessor_id.in_(family) & NodeDependency.successor_id.in_(chain))
         | (NodeDependency.predecessor_id.in_(chain) & NodeDependency.successor_id.in_(family))),
    ).limit(1))
    if edge is not None:
        raise HTTPException(status_code=409, detail=MOVE_DEPENDENCY)


def move_node(db: Session, current: CurrentUser, node_id: str, parent_id: str | None) -> dict:
    """Re-parent a task inside its project; `parent_id=None` means the project's top level."""
    node, project, context = lock_node(db, current, node_id)
    if node.kind != "task":
        raise HTTPException(status_code=422, detail="只能移動任務")
    if not can_move(db, current, project, node, context):
        raise HTTPException(status_code=403, detail="沒有移動節點的權限")
    nodes = project_nodes(db, current, project.id)
    if not can_manage_project(current, project):
        # A task owner moves only what they can see; managers see the whole tree anyway.
        require_all_visible(current, nodes, family_of(nodes, node.id), context, "此節點底下有你看不到的子任務，無法移動")
    root = project_root(nodes)
    if parent_id is None:
        # A blank project keeps a kind=project root: its children are the project's top level.
        target = root
    else:
        target = db.scalar(select(Node).where(
            Node.organization_id == current.organization.id, Node.project_id == project.id, Node.id == parent_id,
        ).with_for_update().execution_options(populate_existing=True))
        if target is None or (target is not root and not can_view_node(current, target, context=context)):
            raise HTTPException(status_code=404, detail="找不到目標節點")
        if target.kind not in {"project", "phase", "task"}:
            raise HTTPException(status_code=422, detail="無法移到此種節點底下")
        nodes[target.id] = target
    check_placement(db, current, project, node, target, nodes)
    target_id = target.id if target is not None else None
    if node.parent_id == target_id:
        return {**node_out(db, current, project, node, context=context), "undo_id": None}
    previous, previous_order = node.parent_id, node.sort_order
    node.parent_id = target_id
    node.sort_order = max(item.sort_order for item in nodes.values()) + 10
    entry = log_audit(db, current, "node.move", node_id=node.id, payload={
        "from_parent_id": previous, "to_parent_id": target_id, "from_sort_order": previous_order})
    db.commit()
    db.refresh(node)
    return {**node_out(db, current, project, node, context=context), "undo_id": entry.id}


def require_all_visible(current: CurrentUser, nodes: dict[str, Node], ids, context, detail: str):
    if any(not can_view_node(current, nodes[i], context=context) for i in ids):
        raise HTTPException(status_code=409, detail=detail)


def copy_title(title: str) -> str:
    return title[:200 - len(COPY_SUFFIX)] + COPY_SUFFIX


def copy_node(db: Session, current: CurrentUser, node_id: str) -> dict:
    node, project, context = lock_node(db, current, node_id)
    if node.kind != "task":
        raise HTTPException(status_code=422, detail="只能複製任務")
    if not can_manage_project(current, project):
        raise HTTPException(status_code=403, detail="沒有複製此任務的權限")
    nodes = project_nodes(db, current, project.id)
    parent = nodes.get(node.parent_id) if node.parent_id else None
    if parent is not None and parent.milestone:
        raise HTTPException(status_code=409, detail="里程碑不能有子任務，請先取消里程碑")
    if parent is not None and parent.status in CLOSED_PARENT:
        raise HTTPException(status_code=409, detail="不能在已完成、待確認或已略過的節點底下新增")
    family = family_of(nodes, node.id)
    require_all_visible(current, nodes, family, context, "此節點底下有你看不到的子任務，無法複製")
    if len(family) > COPY_LIMIT:
        raise HTTPException(status_code=422, detail=f"子樹超過 {COPY_LIMIT} 個節點，無法複製")
    mapping: dict[str, str] = {}
    for source_id in family:
        source = nodes[source_id]
        # The copied root keeps the source's sort order; ties sort by creation time, so it lands right after the source.
        copy = Node(organization_id=current.organization.id, project_id=project.id,
                    parent_id=source.parent_id if source_id == node.id else mapping[source.parent_id],
                    kind=source.kind, title=copy_title(source.title) if source_id == node.id else source.title,
                    status="todo", owner_user_id=source.owner_user_id, department_id=source.department_id,
                    start_date=source.start_date, due_date=source.due_date, sort_order=source.sort_order,
                    weight=source.weight, progress=None, milestone=source.milestone, schedule_locked=source.schedule_locked)
        db.add(copy)
        db.flush()
        mapping[source_id] = copy.id
    for row in db.scalars(select(NodeCollaborator).where(
            NodeCollaborator.organization_id == current.organization.id, NodeCollaborator.node_id.in_(family))):
        db.add(NodeCollaborator(organization_id=current.organization.id, node_id=mapping[row.node_id],
                                user_id=row.user_id, department_id=row.department_id, created_by=current.user.id))
    edges = []
    for edge in edges_touching(db, current, project.id, family):
        if edge.predecessor_id in mapping and edge.successor_id in mapping:
            copied = NodeDependency(organization_id=current.organization.id, project_id=project.id,
                                    predecessor_id=mapping[edge.predecessor_id], successor_id=mapping[edge.successor_id],
                                    created_by=current.user.id)
            db.add(copied)
            edges.append(copied)
    db.flush()
    entry = log_audit(db, current, "node.copy", node_id=mapping[node.id], payload={
        "source_id": node.id, "node_ids": [mapping[i] for i in family], "dependency_ids": [edge.id for edge in edges]})
    db.commit()
    root = db.get(Node, mapping[node.id])
    return {**node_out(db, current, project, root, context=context), "undo_id": entry.id, "copied_count": len(family)}


def delete_node(db: Session, current: CurrentUser, node_id: str) -> dict:
    """Soft delete a task and its subtree; edges touching the subtree are removed and kept in the audit payload."""
    node, project, context = lock_node(db, current, node_id)
    if node.kind != "task":
        raise HTTPException(status_code=422, detail="只能刪除任務")
    if not can_manage_project(current, project):
        raise HTTPException(status_code=403, detail="沒有刪除此任務的權限")
    nodes = project_nodes(db, current, project.id)
    family = family_of(nodes, node.id)
    require_all_visible(current, nodes, family, context, "此節點底下有你看不到的子任務，無法刪除")
    edges = edges_touching(db, current, project.id, family)
    payload = {"parent_id": node.parent_id, "title": node.title, "node_ids": family, "dependencies": [
        {"predecessor_id": e.predecessor_id, "successor_id": e.successor_id, "created_by": e.created_by,
         "created_at": e.created_at.isoformat()} for e in edges]}
    when = now_utc()
    for item_id in family:
        nodes[item_id].deleted_at = when
        nodes[item_id].deleted_by = current.user.id
    for edge in edges:
        db.delete(edge)
    entry = log_audit(db, current, "node.delete", node_id=node.id, payload=payload)
    db.commit()
    return {"undo_id": entry.id, "project_id": project.id, "parent_id": payload["parent_id"], "deleted_count": len(family)}


# ---- undo ----

def later_activity(db: Session, current: CurrentUser, entry: AuditLog, ids) -> bool:
    return db.scalar(select(AuditLog.id).where(
        AuditLog.organization_id == current.organization.id, AuditLog.node_id.in_(list(ids)),
        AuditLog.id != entry.id, AuditLog.created_at >= entry.created_at).limit(1)) is not None


def would_cycle(edges: list[tuple[str, str]]) -> bool:
    outgoing: dict[str, list[str]] = {}
    for predecessor, successor in edges:
        outgoing.setdefault(predecessor, []).append(successor)
    state: dict[str, int] = {}
    for start in list(outgoing):
        if state.get(start):
            continue
        stack = [(start, iter(outgoing.get(start, [])))]
        state[start] = 1
        while stack:
            current_id, successors = stack[-1]
            following = next(successors, None)
            if following is None:
                state[current_id] = 2
                stack.pop()
            elif state.get(following) == 1:
                return True
            elif not state.get(following):
                state[following] = 1
                stack.append((following, iter(outgoing.get(following, []))))
    return False


def soft_delete(nodes: dict[str, Node], ids, current: CurrentUser):
    when = now_utc()
    for item_id in ids:
        nodes[item_id].deleted_at = when
        nodes[item_id].deleted_by = current.user.id


def undo_create(db, current, entry, project, nodes, context):
    node = nodes.get(entry.node_id)
    if (node is None or node.deleted_at is not None or any(n.parent_id == node.id and n.deleted_at is None for n in nodes.values())
            or edges_touching(db, current, project.id, [node.id]) or later_activity(db, current, entry, [node.id])):
        raise HTTPException(status_code=409, detail=UNDO_CHANGED)
    soft_delete(nodes, [node.id], current)


def undo_copy(db, current, entry, project, nodes, context):
    ids = entry.payload.get("node_ids") if isinstance(entry.payload.get("node_ids"), list) else []
    copied_edges = set(entry.payload.get("dependency_ids") or [])
    if not ids or any(nodes.get(i) is None or nodes[i].deleted_at is not None for i in ids):
        raise HTTPException(status_code=409, detail=UNDO_CHANGED)
    family = set(ids)
    edges = edges_touching(db, current, project.id, family)
    if (any(n.parent_id in family and n.id not in family and n.deleted_at is None for n in nodes.values())
            or any(edge.id not in copied_edges for edge in edges) or len(edges) != len(copied_edges)
            or later_activity(db, current, entry, family)):
        raise HTTPException(status_code=409, detail=UNDO_CHANGED)
    for edge in edges:
        db.delete(edge)
    soft_delete(nodes, ids, current)


def undo_delete(db, current, entry, project, nodes, context):
    ids = entry.payload.get("node_ids") if isinstance(entry.payload.get("node_ids"), list) else []
    if not ids or any(nodes.get(i) is None or nodes[i].deleted_at is None for i in ids):
        raise HTTPException(status_code=409, detail=UNDO_CHANGED)
    parent_id = entry.payload.get("parent_id")
    if parent_id is not None:
        parent = nodes.get(parent_id)
        # A finished subtree may return under a finished parent; an open one may not (D74).
        if (parent is None or parent.deleted_at is not None
                or parent.milestone
                or (parent.status in CLOSED_PARENT and any(nodes[i].status not in FINISHED for i in ids))):
            raise HTTPException(status_code=409, detail=UNDO_PARENT)
    restored = set(ids)
    live = {i for i, n in nodes.items() if n.deleted_at is None} | restored
    existing = {(e.predecessor_id, e.successor_id) for e in db.scalars(select(NodeDependency).where(
        NodeDependency.organization_id == current.organization.id, NodeDependency.project_id == project.id))}
    recorded = [d for d in entry.payload.get("dependencies") or [] if isinstance(d, dict)]
    pairs = [(d.get("predecessor_id"), d.get("successor_id")) for d in recorded]
    if any(p not in live or s not in live for p, s in pairs) or would_cycle(list(existing | set(pairs))):
        raise HTTPException(status_code=409, detail=UNDO_RELATED)
    for item_id in ids:
        nodes[item_id].deleted_at = None
        nodes[item_id].deleted_by = None
    for record, pair in zip(recorded, pairs):
        if pair in existing:
            continue
        created_by = record.get("created_by") if record.get("created_by") in context.users else current.user.id
        try:
            created_at = datetime.fromisoformat(record.get("created_at"))
        except (TypeError, ValueError):
            created_at = now_utc()
        db.add(NodeDependency(organization_id=current.organization.id, project_id=project.id, predecessor_id=pair[0],
                              successor_id=pair[1], created_by=created_by, created_at=created_at))
        existing.add(pair)


def undo_move(db, current, entry, project, nodes, context):
    node = nodes.get(entry.node_id)
    if node is None or node.deleted_at is not None or node.parent_id != entry.payload.get("to_parent_id"):
        raise HTTPException(status_code=409, detail=UNDO_CHANGED)
    target_id = entry.payload.get("from_parent_id")
    target = nodes.get(target_id) if target_id is not None else None
    if target_id is not None and (target is None or target.deleted_at is not None):
        raise HTTPException(status_code=409, detail=UNDO_PARENT)
    live = {i: n for i, n in nodes.items() if n.deleted_at is None}
    finished = all(live[i].status in FINISHED for i in family_of(live, node.id))
    check_placement(db, current, project, node, target, live, closed_detail=UNDO_PARENT, cycle_detail=UNDO_PARENT, closed_ok=finished)
    node.parent_id = target_id
    order = entry.payload.get("from_sort_order")
    node.sort_order = order if type(order) is int else max(n.sort_order for n in live.values()) + 10


def undo(db: Session, current: CurrentUser, audit_id: str) -> dict:
    """Reverse the current user's most recent structure change, once, if nothing has touched it since."""
    entry = db.scalar(select(AuditLog).where(AuditLog.organization_id == current.organization.id, AuditLog.id == audit_id)
                      .with_for_update().execution_options(populate_existing=True))
    if entry is None or entry.actor_user_id != current.user.id or entry.action not in UNDOABLE or entry.node_id is None:
        raise HTTPException(status_code=404, detail="沒有可以復原的操作")
    latest = db.scalar(select(AuditLog.id).where(
        AuditLog.organization_id == current.organization.id, AuditLog.actor_user_id == current.user.id,
        AuditLog.action.in_(UNDOABLE + ("node.undo",))).order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(1))
    if latest != entry.id:
        raise HTTPException(status_code=409, detail="只能復原最近一次的結構操作")
    subject = db.scalar(select(Node).where(Node.organization_id == current.organization.id, Node.id == entry.node_id)
                        .execution_options(**{INCLUDE_DELETED: True}))
    if subject is None:
        raise HTTPException(status_code=404, detail="沒有可以復原的操作")
    project = lock_project(db, current, subject.project_id)
    context = load_policy_context(db, current)
    nodes = {n.id: n for n in db.scalars(select(Node).where(
        Node.organization_id == current.organization.id, Node.project_id == project.id)
        .with_for_update().execution_options(**{INCLUDE_DELETED: True}, populate_existing=True))}
    subject = nodes[subject.id]
    allowed = (can_move(db, current, project, subject, context) if entry.action == "node.move"
               else can_manage_project(current, project))
    if not allowed or not can_view_node(current, subject, context=context):
        raise HTTPException(status_code=403, detail="沒有復原此操作的權限")
    {"node.create": undo_create, "node.copy": undo_copy, "node.delete": undo_delete, "node.move": undo_move}[entry.action](
        db, current, entry, project, nodes, context)
    log_audit(db, current, "node.undo", node_id=entry.node_id, payload={"audit_id": entry.id, "action": entry.action})
    db.commit()
    return {"action": entry.action, "project_id": project.id, "node_id": entry.node_id,
            "parent_id": nodes[entry.node_id].parent_id}
