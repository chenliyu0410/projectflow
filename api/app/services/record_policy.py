"""Company-scoped, batched collaboration and record authorization."""
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.models import Department, Node, NodeCollaborator, Project, TaskReport, User
from app.permissions import can_manage_project, can_view_node, can_view_project, can_work_node


@dataclass
class PolicyContext:
    organization_id: str
    user_id: str
    users: dict[str, User]
    departments: dict[str, Department]
    collaborator_node_ids: set[str]
    pending_reports: dict[str, TaskReport]
    latest_versions: dict[str, int]


def load_policy_context(db: Session, current: CurrentUser) -> PolicyContext:
    org = current.organization.id
    users = {u.id: u for u in db.scalars(select(User).where(User.organization_id == org))}
    departments = {d.id: d for d in db.scalars(select(Department).where(Department.organization_id == org))}
    collaboration = set()
    for row in db.scalars(select(NodeCollaborator).where(NodeCollaborator.organization_id == org)):
        department = departments.get(row.department_id)
        if row.user_id == current.user.id or (department is not None and department.head_user_id == current.user.id):
            collaboration.add(row.node_id)
    pending = {}
    versions = {}
    for report in db.scalars(select(TaskReport).where(TaskReport.organization_id == org, TaskReport.workflow_version == 2)):
        versions[report.node_id] = max(versions.get(report.node_id, 0), report.version)
        if report.status == 'submitted':
            pending[report.node_id] = report
    return PolicyContext(org, current.user.id, users, departments, collaboration, pending, versions)


def is_collaborator(current: CurrentUser, node: Node, *, context: PolicyContext) -> bool:
    return (context.organization_id == current.organization.id == node.organization_id
            and context.user_id == current.user.id and node.id in context.collaborator_node_ids)


def visible(current, project, node, context):
    return (project.id == node.project_id and can_view_project(current, project)
            and can_view_node(current, node, context=context))


def can_submit_report(db: Session, current: CurrentUser, project: Project, node: Node, *, context: PolicyContext) -> bool:
    return (node.kind == 'task' and visible(current, project, node, context)
            and current.user.role != 'readonly' and can_work_node(db, current, node, departments=context.departments))


def can_review_report(db: Session, current: CurrentUser, project: Project, node: Node, report: TaskReport | None = None, *, context: PolicyContext) -> bool:
    if node.kind != 'task' or current.user.role == 'readonly' or not visible(current, project, node, context):
        return False
    department = context.departments.get(node.department_id)
    reviewer = (can_manage_project(current, project)
                or (department is not None and department.head_user_id == current.user.id)
                or (current.user.role == 'reviewer' and can_work_node(db, current, node, departments=context.departments)))
    if not reviewer:
        return False
    if report is None:
        return True
    return (report.organization_id == current.organization.id and report.node_id == node.id
            and report.workflow_version == 2 and report.status == 'submitted'
            and report.version == context.latest_versions.get(node.id)
            and node.status == 'review' and report.submitted_by != current.user.id)


def can_self_approve_report(db: Session, current: CurrentUser, project: Project, node: Node, *, context: PolicyContext) -> bool:
    return can_manage_project(current, project) and can_submit_report(db, current, project, node, context=context)


def can_write_record(db: Session, current: CurrentUser, project: Project, node: Node, *, context: PolicyContext) -> bool:
    return (current.user.role != 'readonly' and visible(current, project, node, context)
            and (can_work_node(db, current, node, departments=context.departments)
                 or can_manage_project(current, project)
                 or can_review_report(db, current, project, node, context=context)
                 or is_collaborator(current, node, context=context)))


def state_actions(db: Session, current: CurrentUser, project: Project, node: Node, *, context: PolicyContext) -> list[str]:
    if current.user.role == 'readonly' or not visible(current, project, node, context) or node.kind == 'project':
        return []
    work = can_work_node(db, current, node, departments=context.departments)
    if node.kind == 'phase':
        return ['todo', 'doing', 'review', 'done', 'skipped'] if work else []
    if node.kind != 'task' or node.id in context.pending_reports:
        return []
    actions = []
    if node.status in {'todo', 'doing'} and work:
        actions.extend(['todo', 'doing'])
    if node.status in {'todo', 'doing', 'review'} and can_submit_report(db, current, project, node, context=context):
        actions.append('submit_report')
        if can_self_approve_report(db, current, project, node, context=context):
            actions.append('submit_and_approve')
    if can_manage_project(current, project):
        if node.status in {'todo', 'doing'}:
            actions.append('skip')
        elif node.status in {'done', 'review'}:
            actions.append('reopen')
        elif node.status == 'skipped':
            actions.append('restore')
    return actions
