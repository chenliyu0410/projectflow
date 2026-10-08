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


def can_view_node(current: CurrentUser, node: Node) -> bool:
    if node.organization_id != current.organization.id:
        return False
    return current.user.role in {"admin", "project_owner", "reviewer", "readonly"} or node.owner_user_id == current.user.id


def can_work_node(db: Session, current: CurrentUser, node: Node) -> bool:
    if node.organization_id != current.organization.id:
        return False
    if current.user.role == "admin" or node.owner_user_id == current.user.id:
        return True
    if node.department_id is None:
        return False
    head_id = db.execute(
        select(Department.head_user_id).where(
            Department.organization_id == current.organization.id,
            Department.id == node.department_id,
        )
    ).scalar_one_or_none()
    return head_id == current.user.id
