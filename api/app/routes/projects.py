from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import log_audit
from app.auth import CurrentUser, require_session
from app.database import get_session
from app.models import Department, Gate, Node, Project, User
from app.permissions import can_view_project, can_work_node, can_work_project
from app.schemas import NodeCreate, NodeStatusUpdate, ProjectCreate

router = APIRouter(tags=["projects"])


def project_out(current: CurrentUser, project: Project) -> dict:
    return {"id": project.id, "title": project.title, "organization_key": current.organization.key, "owner_user_id": project.owner_user_id}


def node_out(node: Node) -> dict:
    return {
        "id": node.id,
        "project_id": node.project_id,
        "parent_id": node.parent_id,
        "kind": node.kind,
        "title": node.title,
        "status": node.status,
        "owner_user_id": node.owner_user_id,
        "department_id": node.department_id,
        "sort_order": node.sort_order,
    }


def gate_out(gate: Gate) -> dict:
    return {"id": gate.id, "project_id": gate.project_id, "node_id": gate.node_id, "status": gate.status}


def blocked_by_pending_gate(db: Session, current: CurrentUser, node: Node) -> bool:
    if node.status != "todo":
        return False
    if node.parent_id is None:
        return False
    phase = db.execute(
        select(Node).where(Node.organization_id == current.organization.id, Node.id == node.parent_id)
    ).scalar_one_or_none()
    if phase is None or phase.kind != "phase":
        return False
    lower_phase_ids = db.execute(
        select(Node.id).where(
            Node.organization_id == current.organization.id,
            Node.project_id == node.project_id,
            Node.kind == "phase",
            Node.sort_order < phase.sort_order,
        )
    ).scalars().all()
    if not lower_phase_ids:
        return False
    pending = db.execute(
        select(Gate.id).where(
            Gate.organization_id == current.organization.id,
            Gate.project_id == node.project_id,
            Gate.node_id.in_(lower_phase_ids),
            Gate.status == "pending",
        )
    ).first()
    return pending is not None


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
    nodes = db.execute(
        select(Node).where(Node.organization_id == current.organization.id, Node.project_id == project.id).order_by(Node.sort_order, Node.created_at)
    ).scalars()
    gates = db.execute(
        select(Gate).where(Gate.organization_id == current.organization.id, Gate.project_id == project.id).order_by(Gate.created_at)
    ).scalars()
    return {**project_out(current, project), "nodes": [node_out(node) for node in nodes], "gates": [gate_out(gate) for gate in gates]}


@router.post("/projects/{project_id}/nodes", status_code=status.HTTP_201_CREATED)
def create_node(project_id: str, payload: NodeCreate, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    project = get_project_or_404(db, current, project_id)
    if not can_work_project(current, project):
        raise HTTPException(status_code=403, detail="沒有新增節點權限")
    parent = None
    if payload.parent_id:
        parent = db.execute(
            select(Node).where(Node.organization_id == current.organization.id, Node.id == payload.parent_id, Node.project_id == project.id)
        ).scalar_one_or_none()
        if parent is None:
            raise HTTPException(status_code=400, detail="父節點不屬於此專案")
    if payload.owner_user_id is not None:
        owner = db.execute(select(User).where(User.organization_id == current.organization.id, User.id == payload.owner_user_id)).scalar_one_or_none()
        if owner is None:
            raise HTTPException(status_code=400, detail="負責人不屬於此公司")
    if payload.department_id is not None:
        department = db.execute(select(Department).where(Department.organization_id == current.organization.id, Department.id == payload.department_id)).scalar_one_or_none()
        if department is None:
            raise HTTPException(status_code=400, detail="部門不屬於此公司")
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
        sort_order=(next_order or 0) + 10,
    )
    db.add(node)
    db.flush()
    log_audit(db, current, "node.create", node_id=node.id, payload={"project_id": project.id, "title": payload.title})
    db.commit()
    db.refresh(node)
    return node_out(node)


@router.patch("/nodes/{node_id}/status")
def update_node_status(node_id: str, payload: NodeStatusUpdate, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    node = db.execute(select(Node).where(Node.organization_id == current.organization.id, Node.id == node_id)).scalar_one_or_none()
    if node is None:
        raise HTTPException(status_code=404, detail="找不到節點")
    if not can_work_node(db, current, node):
        raise HTTPException(status_code=403, detail="沒有操作此節點的權限")
    if payload.status in {"doing", "review", "done", "skipped"} and blocked_by_pending_gate(db, current, node):
        raise HTTPException(status_code=409, detail="前一階段閘門尚未通過")
    node.status = payload.status
    log_audit(db, current, "node.status", node_id=node.id, payload={"status": payload.status})
    db.commit()
    db.refresh(node)
    return node_out(node)
