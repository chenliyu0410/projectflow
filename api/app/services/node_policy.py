"""Shared metadata validation and permission-scoped node projection."""
from datetime import date

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.models import Department, Gate, Node, Project, User
from app.permissions import can_edit_node, can_manage_project, can_view_node, can_view_project


def json_value(value):
    return value.isoformat() if isinstance(value, date) else value


def validate_dates(start_date, due_date):
    if start_date is not None and due_date is not None and start_date > due_date:
        raise HTTPException(status_code=422, detail="開始日期不得晚於到期日")


def validate_assignments(db: Session, current: CurrentUser, fields: dict):
    if fields.get('owner_user_id') is not None:
        owner = db.scalar(select(User).where(User.organization_id == current.organization.id, User.id == fields['owner_user_id']))
        if owner is None or owner.role == 'readonly':
            raise HTTPException(status_code=400, detail="無法指派此負責人")
    if fields.get('department_id') is not None:
        department = db.scalar(select(Department).where(Department.organization_id == current.organization.id, Department.id == fields['department_id']))
        if department is None:
            raise HTTPException(status_code=400, detail="無法指派此部門")


def node_out(db: Session, current: CurrentUser, project: Project, node: Node, *, users=None, departments=None) -> dict:
    # Callers with a collection can supply company-scoped maps to avoid per-node queries.
    if users is None:
        users = {u.id: u for u in db.scalars(select(User).where(User.organization_id == current.organization.id))}
    if departments is None:
        departments = {d.id: d for d in db.scalars(select(Department).where(Department.organization_id == current.organization.id))}
    owner = users.get(node.owner_user_id)
    department = departments.get(node.department_id)
    visible = can_view_project(current, project) and can_view_node(current, node)
    manage = visible and can_manage_project(current, project)
    return {
        **{key: json_value(getattr(node, key)) for key in (
            'id', 'project_id', 'parent_id', 'kind', 'title', 'status', 'owner_user_id',
            'department_id', 'sort_order', 'start_date', 'due_date')},
        'owner_display_name': owner.display_name if owner is not None and owner.organization_id == current.organization.id else None,
        'department_name': department.name if department is not None and department.organization_id == current.organization.id else None,
        'capabilities': {
            'edit_metadata': can_edit_node(db, current, project, node, departments=departments),
            'assign': manage and node.kind in {'phase','task'},
            'create_child': manage and node.kind in {'project','phase','task'},
        },
    }


def containing_phase(db: Session, current: CurrentUser, node: Node) -> Node | None:
    """Find the nearest phase, validating the *entire* stored parent chain.

    Do not use a visible-node tree: invisible ancestors still enforce Gates.
    Finding a phase does not end validation, because its own ancestry may be
    cyclic, missing, or linked to another project/company.
    """
    cursor = node
    phase = None
    visited = set()
    while True:
        if cursor.id in visited or cursor.organization_id != current.organization.id:
            raise HTTPException(status_code=409, detail="節點階層異常，無法變更狀態")
        visited.add(cursor.id)
        if phase is None and cursor.kind == "phase":
            phase = cursor
        if cursor.parent_id is None:
            return phase
        parent = db.scalar(select(Node).where(
            Node.id == cursor.parent_id,
            Node.organization_id == current.organization.id,
            Node.project_id == node.project_id,
        ))
        if parent is None:
            raise HTTPException(status_code=409, detail="節點階層異常，無法變更狀態")
        cursor = parent


def blocked_by_pending_gate(db: Session, current: CurrentUser, node: Node) -> bool:
    phase = containing_phase(db, current, node)
    if node.status != "todo" or phase is None:
        return False
    lower_phase_ids = select(Node.id).where(
        Node.organization_id == current.organization.id,
        Node.project_id == node.project_id,
        Node.kind == "phase",
        Node.sort_order < phase.sort_order,
    )
    return db.scalar(select(Gate.id).where(
        Gate.organization_id == current.organization.id,
        Gate.project_id == node.project_id,
        Gate.node_id.in_(lower_phase_ids),
        Gate.status == "pending",
    ).limit(1)) is not None


def visible_workspace_nodes(db: Session, current: CurrentUser) -> tuple[dict[str, Project], list[Node]]:
    """Authorize the complete company-scoped collection before aggregation/filtering."""
    projects = {
        project.id: project
        for project in db.scalars(select(Project).where(
            Project.organization_id == current.organization.id,
        ).order_by(Project.created_at, Project.id))
        if can_view_project(current, project)
    }
    nodes = [
        node for node in db.scalars(select(Node).where(Node.organization_id == current.organization.id))
        if node.project_id in projects and can_view_node(current, node)
    ]
    return projects, nodes
