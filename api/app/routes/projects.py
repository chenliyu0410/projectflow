from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import log_audit
from app.services.dependency_service import lock_project, require_dependencies
from app.auth import CurrentUser, require_session
from app.database import get_session
from app.models import Department, Gate, Node, Project, User, NodeCollaborator
from app.permissions import can_view_node, can_view_project, can_work_node, can_manage_project, can_edit_node, can_assign_node
from app.schemas import NodeCreate, NodeMove, NodeUpdate, NodeStatusUpdate, ProjectCreate, UndoRequest, ScheduleUpdate
from app.services import tree_service, schedule_service
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
        "owner_display_name": context.users[project.owner_user_id].display_name if project.owner_user_id in context.users else None,
        "collaborators": [{"user_id":c.user_id,"department_id":c.department_id,
                           "display_name":context.users[c.user_id].display_name if c.user_id in context.users else context.departments[c.department_id].name if c.department_id in context.departments else '未設定'}
                          for c in db.scalars(select(NodeCollaborator).where(NodeCollaborator.organization_id == current.organization.id,NodeCollaborator.node_id.in_(visible_ids)))],
        "nodes": [node_out(db, current, project, node, context=context) for node in visible_nodes],
        "gates": [gate_out(gate) for gate in gates if gate.node_id in visible_ids],
    }


@router.post("/projects/{project_id}/nodes", status_code=status.HTTP_201_CREATED)
def create_node(project_id: str, payload: NodeCreate, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    # Serialized with delete/undo (TP-B) so a parent cannot be soft-deleted while a child is added under it.
    project = lock_project(db, current, project_id)
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
    if parent is not None and parent.status in tree_service.CLOSED_PARENT:
        raise HTTPException(status_code=409, detail="不能在已完成、待確認或已略過的節點底下新增")
    if parent is not None and parent.milestone:
        schedule_service.fail(schedule_service.MILESTONE_PARENT)
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
        milestone=payload.milestone,
        schedule_locked=payload.schedule_locked,
        sort_order=(next_order or 0) + 10,
    )
    from uuid import uuid4
    node.id = str(uuid4())
    initial = {"start_date": payload.start_date, "due_date": payload.due_date, "milestone": payload.milestone, "schedule_locked": payload.schedule_locked}
    node.start_date = node.due_date = None
    node.milestone = node.schedule_locked = False
    schedule_service.prepare(db, current, project, node, initial, context)
    for key, value in initial.items():
        setattr(node, key, value)
    db.add(node)
    db.flush()
    entry = log_audit(db, current, "node.create", node_id=node.id, payload={"project_id": project.id, **payload.model_dump(mode="json")})
    db.commit()
    db.refresh(node)
    return {**node_out(db, current, project, node, context=context), "undo_id": entry.id}


@router.patch("/nodes/{node_id}/status")
def update_node_status(node_id: str, payload: NodeStatusUpdate, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    node, project, context = lock_node(db, current, node_id, require_visible=False)
    if not can_work_node(db, current, node):
        raise HTTPException(status_code=403, detail="沒有操作此節點的權限")
    from app.services.collaboration_service import require_open_ancestors
    if payload.status in {'doing','review','done'}: require_open_ancestors(db,current,node)
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
    if current.user.role == "readonly" or not (can_manage_project(current, project) or any(d.head_user_id == current.user.id for d in context.departments.values())):
        raise HTTPException(status_code=403, detail="沒有指派權限")
    users = db.scalars(select(User).where(User.organization_id == current.organization.id, User.role != "readonly").order_by(User.display_name, User.id))
    departments = db.scalars(select(Department).where(Department.organization_id == current.organization.id).order_by(Department.name, Department.id))
    return {
        "users": [{"id": u.id, "display_name": u.display_name} for u in users],
        "departments": [{"id": d.id, "name": d.name} for d in departments],
    }


@router.patch("/nodes/{node_id}")
def update_node(node_id: str, payload: NodeUpdate, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    node, project, context = lock_node(db, current, node_id)
    if not can_edit_node(db, current, project, node, context=context, departments=context.departments):
        raise HTTPException(status_code=403, detail="沒有編輯此節點的權限")
    fields = payload.model_dump(exclude_unset=True)
    if "department_id" in fields and not can_manage_project(current, project):
        raise HTTPException(status_code=403, detail="沒有變更部門權限")
    if "owner_user_id" in fields and not can_assign_node(db, current, project, node, context=context):
        raise HTTPException(status_code=403, detail="沒有指派權限")
    if "progress" in fields and node.kind != "task":
        raise HTTPException(status_code=422, detail="只有任務可以填寫進度")
    validate_dates(fields.get("start_date", node.start_date), fields.get("due_date", node.due_date))
    validate_assignments(db, current, fields)
    schedule_service.apply(db, current, project, node, fields, context)
    db.commit()
    db.refresh(node)
    return node_out(db, current, project, node, context=context)


@router.post("/nodes/{node_id}/move")
def move_node(node_id: str, payload: NodeMove, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    """Re-parent a task inside its project (TP-A drag, TP-B promote/demote/move-to)."""
    return tree_service.move_node(db, current, node_id, payload.parent_id)


@router.post("/nodes/{node_id}/copy", status_code=status.HTTP_201_CREATED)
def copy_node(node_id: str, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    return tree_service.copy_node(db, current, node_id)


@router.delete("/nodes/{node_id}")
def delete_node(node_id: str, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    return tree_service.delete_node(db, current, node_id)


@router.post("/undo")
def undo(payload: UndoRequest, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    return tree_service.undo(db, current, payload.audit_id)


@router.post("/nodes/{node_id}/schedule")
def update_schedule(node_id: str, payload: ScheduleUpdate, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    node, project, context = lock_node(db, current, node_id)
    if not can_edit_node(db, current, project, node, context=context, departments=context.departments):
        raise HTTPException(status_code=403, detail="沒有編輯此節點的權限")
    count = schedule_service.apply(db, current, project, node, {"start_date": payload.start_date, "due_date": payload.due_date}, context, payload.cascade)
    db.commit()
    db.refresh(node)
    return {"node": node_out(db, current, project, node, context=context), "shifted_count": count}
