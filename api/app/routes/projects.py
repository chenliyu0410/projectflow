from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import log_audit
from app.services.dependency_service import require_dependencies
from app.auth import CurrentUser, require_session
from app.database import get_session
from app.models import Department, Gate, Node, NodeDependency, Project, User
from app.permissions import can_view_node, can_view_project, can_work_node, can_manage_project, can_edit_node
from app.schemas import NodeCreate, NodeMove, NodeUpdate, NodeStatusUpdate, ProjectCreate
from app.services.node_policy import (node_out, json_value, validate_assignments, validate_dates, blocked_by_pending_gate,
                                      require_children_finished)

from app.services.record_policy import load_policy_context
from app.services.report_service import lock_node, conflict

router = APIRouter(tags=["projects"])


def project_out(current: CurrentUser, project: Project) -> dict:
    return {"id": project.id, "title": project.title, "organization_key": current.organization.key, "owner_user_id": project.owner_user_id, "capabilities": {"create_node": can_manage_project(current, project)}}


def gate_out(gate: Gate) -> dict:
    return {"id": gate.id, "project_id": gate.project_id, "node_id": gate.node_id, "status": gate.status}


def get_project_or_404(db: Session, current: CurrentUser, project_id: str) -> Project:
    project = db.execute(
        select(Project).where(Project.organization_id == current.organization.id, Project.id == project_id)
    ).scalar_one_or_none()
    if project is None or not can_view_project(current, project):
        raise HTTPException(status_code=404, detail="找不到專案")
    return project


@router.get("/projects")
def list_projects(current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    projects = db.execute(
        select(Project).where(Project.organization_id == current.organization.id).order_by(Project.created_at)
    ).scalars()
    return {"items": [project_out(current, project) for project in projects if can_view_project(current, project)]}


@router.post("/projects", status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    if current.user.role != "admin":
        raise HTTPException(status_code=403, detail="沒有建立專案權限")
    project = Project(organization_id=current.organization.id, title=payload.title, owner_user_id=current.user.id)
    db.add(project)
    db.flush()
    root = Node(
        organization_id=current.organization.id,
        project_id=project.id,
        kind="project",
        title=payload.title,
        owner_user_id=current.user.id,
        sort_order=0,
    )
    db.add(root)
    log_audit(db, current, "project.create", node_id=root.id, payload={"project_id": project.id, "title": payload.title})
    db.commit()
    db.refresh(project)
    return project_out(current, project)


@router.get("/projects/{project_id}")
def get_project(project_id: str, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    project = get_project_or_404(db, current, project_id)
    context = load_policy_context(db, current)
    nodes = db.execute(
        select(Node).where(Node.organization_id == current.organization.id, Node.project_id == project.id).order_by(Node.sort_order, Node.created_at)
    ).scalars()
    gates = db.execute(
        select(Gate).where(Gate.organization_id == current.organization.id, Gate.project_id == project.id).order_by(Gate.created_at)
    ).scalars()
    visible_nodes = [node for node in nodes if can_view_node(current, node, context=context)]
    visible_ids = {node.id for node in visible_nodes}
    return {
        **project_out(current, project),
        "nodes": [node_out(db, current, project, node, context=context) for node in visible_nodes],
        "gates": [gate_out(gate) for gate in gates if gate.node_id in visible_ids],
    }


@router.post("/projects/{project_id}/nodes", status_code=status.HTTP_201_CREATED)
def create_node(project_id: str, payload: NodeCreate, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    project = get_project_or_404(db, current, project_id)
    context = load_policy_context(db, current)
    if not can_manage_project(current, project):
        raise HTTPException(status_code=403, detail="沒有新增節點權限")
    parent = None
    if payload.parent_id is not None:
        parent = db.execute(
            select(Node).where(Node.organization_id == current.organization.id, Node.id == payload.parent_id, Node.project_id == project.id)
        ).scalar_one_or_none()
        if parent is None or not can_view_node(current, parent, context=context):
            raise HTTPException(status_code=400, detail="父節點不屬於此專案")
    if parent is not None and (
        parent.kind not in {"project", "phase", "task"}
        or (parent.kind in {"phase", "task"} and payload.kind != "task")
    ):
        raise HTTPException(status_code=400, detail="無法在此父節點新增此種類")
    validate_assignments(db, current, payload.model_dump())
    next_order = db.execute(
        select(Node.sort_order).where(Node.organization_id == current.organization.id, Node.project_id == project.id).order_by(Node.sort_order.desc())
    ).scalar()
    node = Node(
        organization_id=current.organization.id,
        project_id=project.id,
        parent_id=parent.id if parent else None,
        kind=payload.kind,
        title=payload.title,
        owner_user_id=payload.owner_user_id,
        department_id=payload.department_id,
        start_date=payload.start_date,
        due_date=payload.due_date,
        sort_order=(next_order or 0) + 10,
    )
    db.add(node)
    db.flush()
    log_audit(db, current, "node.create", node_id=node.id, payload={"project_id": project.id, **payload.model_dump(mode="json")})
    db.commit()
    db.refresh(node)
    return node_out(db, current, project, node, context=context)


@router.patch("/nodes/{node_id}/status")
def update_node_status(node_id: str, payload: NodeStatusUpdate, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    node, project, context = lock_node(db, current, node_id, require_visible=False)
    if not can_work_node(db, current, node):
        raise HTTPException(status_code=403, detail="沒有操作此節點的權限")
    # Every status mutation validates ancestry; Gates only block starting work.
    blocked = blocked_by_pending_gate(db, current, node)
    if payload.status in {"doing", "review", "done", "skipped"} and blocked:
        raise HTTPException(status_code=409, detail="前一階段閘門尚未通過")
    if node.kind == "task" and (node.status not in {"todo", "doing"} or payload.status not in {"todo", "doing"} or node.id in context.pending_reports):
        conflict()
    if node.kind == "task" and node.status == "todo" and payload.status == "doing":
        require_dependencies(db, current, node)
    if payload.status == "done" and node.status != "done":
        require_children_finished(db, current, node)
    node.status = payload.status
    log_audit(db, current, "node.status", node_id=node.id, payload={"status": payload.status})
    db.commit()
    db.refresh(node)
    project = db.get(Project, node.project_id)
    return node_out(db, current, project, node, context=context)


@router.get("/projects/{project_id}/assignment-options")
def assignment_options(project_id: str, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    project = get_project_or_404(db, current, project_id)
    context = load_policy_context(db, current)
    if not can_manage_project(current, project):
        raise HTTPException(status_code=403, detail="沒有指派權限")
    users = db.scalars(select(User).where(User.organization_id == current.organization.id, User.role != "readonly").order_by(User.display_name, User.id))
    departments = db.scalars(select(Department).where(Department.organization_id == current.organization.id).order_by(Department.name, Department.id))
    return {
        "users": [{"id": u.id, "display_name": u.display_name} for u in users],
        "departments": [{"id": d.id, "name": d.name} for d in departments],
    }


@router.patch("/nodes/{node_id}")
def update_node(node_id: str, payload: NodeUpdate, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    context = load_policy_context(db, current)
    node = db.scalar(select(Node).where(Node.organization_id == current.organization.id, Node.id == node_id))
    if node is None or not can_view_node(current, node, context=context):
        raise HTTPException(status_code=404, detail="找不到節點")
    project = get_project_or_404(db, current, node.project_id)
    if not can_edit_node(db, current, project, node, context=context, departments=context.departments):
        raise HTTPException(status_code=403, detail="沒有編輯此節點的權限")
    fields = payload.model_dump(exclude_unset=True)
    if {"owner_user_id", "department_id"} & fields.keys() and not can_manage_project(current, project):
        raise HTTPException(status_code=403, detail="沒有指派權限")
    if "progress" in fields and node.kind != "task":
        raise HTTPException(status_code=422, detail="只有任務可以填寫進度")
    validate_dates(fields.get("start_date", node.start_date), fields.get("due_date", node.due_date))
    validate_assignments(db, current, fields)
    changes = {key: {"before": json_value(getattr(node, key)), "after": json_value(value)}
               for key, value in fields.items() if getattr(node, key) != value}
    if changes:
        for key in changes:
            setattr(node, key, fields[key])
        log_audit(db, current, "node.update", node_id=node.id, payload=changes)
        db.commit()
        db.refresh(node)
    return node_out(db, current, project, node, context=context)


@router.post("/nodes/{node_id}/move")
def move_node(node_id: str, payload: NodeMove, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    """Re-parent a task inside its project; structure changes are a project-manager action."""
    node, project, context = lock_node(db, current, node_id)
    if not can_manage_project(current, project):
        raise HTTPException(status_code=403, detail="沒有移動節點的權限")
    if node.kind != "task":
        raise HTTPException(status_code=422, detail="只能移動任務")
    target = db.scalar(select(Node).where(
        Node.organization_id == current.organization.id, Node.project_id == project.id, Node.id == payload.parent_id,
    ).with_for_update().execution_options(populate_existing=True))
    if target is None or not can_view_node(current, target, context=context):
        raise HTTPException(status_code=404, detail="找不到目標節點")
    if target.kind not in {"project", "phase", "task"}:
        raise HTTPException(status_code=422, detail="無法移到此種節點底下")
    # Walk the complete stored chain (hidden ancestors included) to refuse cycles.
    nodes = {n.id: n for n in db.scalars(select(Node).where(
        Node.organization_id == current.organization.id, Node.project_id == project.id))}
    chain, cursor = [], target
    while cursor is not None:
        if cursor.id == node.id:
            raise HTTPException(status_code=409, detail="不能移到自己的子任務底下")
        if cursor.id in chain:
            raise HTTPException(status_code=409, detail="節點階層異常，無法移動")
        chain.append(cursor.id)
        cursor = nodes.get(cursor.parent_id) if cursor.parent_id is not None else None
    if target.status in {"review", "done", "skipped"}:
        raise HTTPException(status_code=409, detail="不能移到已完成、待確認或已略過的任務底下")
    if node.parent_id == target.id:
        return node_out(db, current, project, node, context=context)
    children: dict[str | None, list[str]] = {}
    for item in nodes.values():
        children.setdefault(item.parent_id, []).append(item.id)
    family, pending = set(), [node.id]
    while pending:
        current_id = pending.pop()
        if current_id not in family:
            family.add(current_id)
            pending.extend(children.get(current_id, []))
    ancestors = set(chain)
    edge = db.scalar(select(NodeDependency.id).where(
        NodeDependency.organization_id == current.organization.id, NodeDependency.project_id == project.id,
        ((NodeDependency.predecessor_id.in_(family) & NodeDependency.successor_id.in_(ancestors))
         | (NodeDependency.predecessor_id.in_(ancestors) & NodeDependency.successor_id.in_(family))),
    ).limit(1))
    if edge is not None:
        raise HTTPException(status_code=409, detail="移動後會和前置相依衝突，請先移除相依連線")
    previous = node.parent_id
    node.parent_id = target.id
    node.sort_order = max(item.sort_order for item in nodes.values()) + 10
    log_audit(db, current, "node.move", node_id=node.id, payload={"from_parent_id": previous, "to_parent_id": target.id})
    db.commit()
    db.refresh(node)
    return node_out(db, current, project, node, context=context)
