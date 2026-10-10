"""Company-scoped, batched collaboration and record authorization."""
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.models import Department, Node, NodeCollaborator, Project, TaskReport, User, NodeDependency
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
    blocked_node_ids: set[str]
    soft_warning_ids: set[str]


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
    from app.models import NodeCondition
    from app.services.dependency_service import unmet_dependencies
    nodes = {n.id: n for n in db.scalars(select(Node).where(Node.organization_id == org))}
    edges = list(db.scalars(select(NodeDependency).where(NodeDependency.organization_id == org)))
    conditions = list(db.scalars(select(NodeCondition).where(NodeCondition.organization_id == org)))
    by_project_edges = {}
    by_project_conditions = {}
    for edge in edges:
        by_project_edges.setdefault(edge.project_id, []).append(edge)
    for condition in conditions:
        by_project_conditions.setdefault(condition.project_id, []).append(condition)
    blocked = set()
    soft = set()
    for n in nodes.values():
        try:
            if any(e.enforcement == 'hard' for e in unmet_dependencies(nodes, by_project_edges.get(n.project_id, []), by_project_conditions.get(n.project_id, []), n, phase='start')):
                blocked.add(n.id)
            if any(e.enforcement == 'soft' for e in unmet_dependencies(nodes, by_project_edges.get(n.project_id, []), by_project_conditions.get(n.project_id, []), n, phase='finish')):
                soft.add(n.id)
        except Exception as exc:
            from fastapi import HTTPException
            if not isinstance(exc, HTTPException):
                raise
            blocked.add(n.id)
    return PolicyContext(org, current.user.id, users, departments, collaboration, pending, versions, blocked, soft)


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


def page_timestamp(value):
    from datetime import timezone
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def authorized_page(entries, *, organization_id, endpoint, filters, cursor, limit, descending=False):
    """Paginate only an already-authorized projection; bind cursors to its query."""
    import base64
    import json
    from datetime import datetime
    from fastapi import HTTPException
    after = None
    if cursor is not None:
        try:
            if len(cursor) > 2048:
                raise ValueError()
            data = json.loads(base64.b64decode(cursor, altchars=b'-_', validate=True))
            if (not isinstance(data, dict) or set(data) != {'organization_id', 'endpoint', 'filters', 'key'}
                    or data['organization_id'] != organization_id or data['endpoint'] != endpoint or data['filters'] != filters):
                raise ValueError()
            key = data['key']
            if (not isinstance(key, list) or len(key) != 3 or not all(isinstance(x, str) for x in key)
                    or not key[1] or len(key[1]) > 100 or key[2] not in {'audit', 'report', 'gate'}):
                raise ValueError()
            if page_timestamp(datetime.fromisoformat(key[0])) != key[0]:
                raise ValueError()
            after = tuple(key)
        except (ValueError, TypeError, KeyError, UnicodeError, OverflowError, RecursionError):
            raise HTTPException(status_code=422, detail='無效的分頁游標') from None
    ordered = sorted(entries, key=lambda entry: entry[0], reverse=descending)
    if after is not None:
        ordered = [entry for entry in ordered if (entry[0] < after if descending else entry[0] > after)]
    page = ordered[:limit]
    next_cursor = None
    if len(ordered) > limit:
        data = {'organization_id': organization_id, 'endpoint': endpoint, 'filters': filters, 'key': page[-1][0]}
        next_cursor = base64.urlsafe_b64encode(json.dumps(data, separators=(',', ':')).encode()).decode()
    return {'items': [entry[1] for entry in page], 'next_cursor': next_cursor}
