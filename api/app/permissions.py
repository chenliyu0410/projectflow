from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.models import Department, Node, Project


def can_view_project(current: CurrentUser, project: Project) -> bool:
    return project.organization_id == current.organization.id and current.user.role in {"admin", "project_owner", "reviewer", "member", "readonly"}


def can_work_project(current: CurrentUser, project: Project) -> bool:
    return project.organization_id == current.organization.id and (
        current.user.role == "admin" or project.owner_user_id == current.user.id
    )


def can_view_node(current: CurrentUser, node: Node, *, context=None) -> bool:
    if node.organization_id != current.organization.id:
        return False
    return current.user.role in {"admin", "project_owner", "reviewer", "readonly"} or node.owner_user_id == current.user.id or (
        context is not None and context.organization_id == current.organization.id
        and context.user_id == current.user.id and node.id in context.collaborator_node_ids
    )


def can_work_node(db: Session, current: CurrentUser, node: Node, *, departments=None) -> bool:
    if node.organization_id != current.organization.id:
        return False
    if current.user.role == "readonly":
        return False
    if current.user.role == "admin" or node.owner_user_id == current.user.id:
        return True
    if node.department_id is None:
        return False
    if departments is not None:
        department = departments.get(node.department_id)
        return department is not None and department.organization_id == current.organization.id and department.head_user_id == current.user.id
    head_id = db.execute(
        select(Department.head_user_id).where(
            Department.organization_id == current.organization.id,
            Department.id == node.department_id,
        )
    ).scalar_one_or_none()
    return head_id == current.user.id


def can_manage_project(current: CurrentUser, project: Project) -> bool:
    return current.user.role != "readonly" and can_work_project(current, project)


def can_edit_node(db: Session, current: CurrentUser, project: Project, node: Node, *, departments=None, context=None) -> bool:
    return (
        node.kind in {"phase", "task"}
        and current.user.role != "readonly"
        and node.project_id == project.id
        and can_view_project(current, project)
        and can_view_node(current, node, context=context)
        and (can_manage_project(current, project) or can_work_node(db, current, node, departments=departments))
    )
