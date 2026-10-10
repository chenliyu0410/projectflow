"""Workspace queries use only authorized nodes, including non-leaf tasks."""
from datetime import date, datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import CurrentUser, require_session
from app.database import get_session
from app.models import Gate
from app.permissions import can_work_node, can_work_project
from app.services.node_policy import node_out, visible_workspace_nodes
from app.services.progress import project_progress

from app.services.record_policy import load_policy_context, is_collaborator, can_review_report, authorized_page, page_timestamp

router = APIRouter(prefix="/workspace", tags=["workspace"])
STATUSES = ("todo", "doing", "review", "done", "skipped")
OPEN_STATUSES = ("todo", "doing", "review")
CLOSED_STATUSES = ("done", "skipped")
# Company calendar day (Taiwan, no DST) so "overdue" matches the users' date, not the container's UTC date.
LOCAL_TZ = timezone(timedelta(hours=8))


def empty_counts() -> dict[str, int]:
    return dict.fromkeys(STATUSES, 0)


def is_overdue(node, today: date) -> bool:
    return node.due_date is not None and node.due_date < today and node.status not in CLOSED_STATUSES


def visible_path(node, by_id: dict) -> list[dict[str, str]]:
    """Visible ancestor titles only; hidden or missing parents end the chain without leaking."""
    path, seen, parent = [], {node.id}, by_id.get(node.parent_id)
    while parent is not None and parent.id not in seen:
        seen.add(parent.id)
        path.insert(0, {"id": parent.id, "title": parent.title})
        parent = by_id.get(parent.parent_id)
    return path


def completion_percent(counts: dict[str, int]) -> int | None:
    denominator = sum(counts.values()) - counts["skipped"]
    if denominator == 0:
        return None
    # Integer half-up rounding: Python round() would turn 12.5 into 12.
    return (200 * counts["done"] + denominator) // (2 * denominator)


@router.get("/overview")
def overview(current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    context = load_policy_context(db, current)
    projects, nodes = visible_workspace_nodes(db, current, context=context)
    today = datetime.now(LOCAL_TZ).date()
    counts = empty_counts()
    per_project = {pid: empty_counts() for pid in projects}
    overdue = dict.fromkeys(projects, 0)
    latest_due: dict[str, date | None] = dict.fromkeys(projects)
    phases: dict[str, list] = {pid: [] for pid in projects}
    project_nodes: dict[str, list] = {pid: [] for pid in projects}
    people: dict[str, dict] = {}
    department_open = dict.fromkeys(context.departments, 0)
    for node in nodes:
        project_nodes[node.project_id].append(node)
        if node.due_date is not None and (latest_due[node.project_id] is None or node.due_date > latest_due[node.project_id]):
            latest_due[node.project_id] = node.due_date
        if node.kind == "phase" and node.parent_id is None:
            phases[node.project_id].append(node)
        if node.kind != "task":
            continue
        counts[node.status] += 1
        per_project[node.project_id][node.status] += 1
        late = is_overdue(node, today)
        overdue[node.project_id] += int(late)
        if node.status not in OPEN_STATUSES:
            continue
        if node.department_id in department_open:
            department_open[node.department_id] += 1
        owner = context.users.get(node.owner_user_id)
        if owner is None:
            continue
        entry = people.setdefault(owner.id, {"open": 0, "overdue": 0, "departments": {}})
        entry["open"] += 1
        entry["overdue"] += int(late)
        if node.department_id in context.departments:
            entry["departments"][node.department_id] = entry["departments"].get(node.department_id, 0) + 1

    def current_phase(pid: str) -> str | None:
        active = [p for p in sorted(phases[pid], key=lambda p: (p.sort_order, p.id)) if p.status not in CLOSED_STATUSES]
        return active[0].title if active else None

    def main_department(entry: dict) -> str | None:
        # Users have no stored home department; show where most of their visible open work sits.
        ranked = sorted(entry["departments"].items(), key=lambda item: (-item[1], context.departments[item[0]].name))
        return context.departments[ranked[0][0]].name if ranked else None

    return {
        "project_count": len(projects),
        "task_counts": counts,
        "completion_percent": completion_percent(counts),
        "today": today.isoformat(),
        "overdue_count": sum(overdue.values()),
        "projects": [
            {"id": project.id, "title": project.title, "task_counts": per_project[project.id],
             "completion_percent": completion_percent(per_project[project.id]),
             "progress_percent": project_progress(project_nodes[project.id]),
             "current_phase_title": current_phase(project.id),
             "due_date": latest_due[project.id].isoformat() if latest_due[project.id] else None,
             "overdue_count": overdue[project.id]}
            for project in projects.values()
        ],
        "people": sorted(
            ({"user_id": uid, "display_name": context.users[uid].display_name, "department_name": main_department(entry),
              "open_count": entry["open"], "overdue_count": entry["overdue"]} for uid, entry in people.items()),
            key=lambda item: (-item["open_count"], item["display_name"], item["user_id"])),
        "departments": sorted(
            ({"id": did, "name": context.departments[did].name, "open_count": count} for did, count in department_open.items()),
            key=lambda item: (-item["open_count"], item["name"], item["id"])),
    }


@router.get("/my-tasks")
def my_tasks(
    q: str = "",
    status: Literal["", "todo", "doing", "review", "done", "skipped"] = "",
    current: CurrentUser = Depends(require_session),
    db: Session = Depends(get_session),
):
    context = load_policy_context(db, current)
    projects, nodes = visible_workspace_nodes(db, current, context=context)
    query = q.strip().casefold()
    tasks = [
        node for node in nodes
        if node.kind == "task" and (node.owner_user_id == current.user.id or is_collaborator(current, node, context=context))
        and (not status or node.status == status)
        and (not query or query in node.title.casefold() or query in projects[node.project_id].title.casefold())
    ]
    tasks.sort(key=lambda node: (node.due_date is None, node.due_date or date.max, node.project_id, node.id))
    by_id = {node.id: node for node in nodes}
    return {"items": [
        {**node_out(db, current, projects[node.project_id], node, context=context),
         "project_title": projects[node.project_id].title,
         "path": visible_path(node, by_id),
         "relations": (["owned"] if node.owner_user_id == current.user.id else [])
                      + (["collaborating"] if is_collaborator(current, node, context=context) else [])}
        for node in tasks
    ]}


@router.get('/reviews')
def reviews(kind: Literal['report', 'gate', 'all'] = 'all', limit: int = Query(50, ge=1, le=100),
            cursor: str | None = None, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    context = load_policy_context(db, current)
    projects, visible_nodes = visible_workspace_nodes(db, current, context=context)
    nodes = {node.id: node for node in visible_nodes}
    entries = []
    if kind in {'all', 'report'}:
        for report in context.pending_reports.values():
            node = nodes.get(report.node_id)
            if node is None or not can_review_report(db, current, projects[node.project_id], node, report, context=context):
                continue
            author = context.users.get(report.submitted_by)
            item = {'type': 'report', 'id': report.id, 'node_id': node.id, 'node_title': node.title,
                    'project_id': node.project_id, 'project_title': projects[node.project_id].title,
                    'created_at': report.submitted_at.isoformat(), 'status': report.status, 'version': report.version,
                    'result': report.result, 'summary': report.summary,
                    'finished_on': report.finished_on.isoformat() if report.finished_on else None,
                    'submitted_by': report.submitted_by, 'submitted_by_display_name': author.display_name if author else None,
                    'dependency_warnings': ['軟性前置尚未滿足，仍可繼續'] if node.id in context.soft_warning_ids else [],
                    'capabilities': {'review_report': True}}
            entries.append(((page_timestamp(report.submitted_at), report.id, 'report'), item))
    if kind in {'all', 'gate'}:
        for gate in db.scalars(select(Gate).where(Gate.organization_id == current.organization.id, Gate.status == 'pending')):
            node = nodes.get(gate.node_id)
            if node is None or gate.project_id != node.project_id or current.user.role == 'readonly':
                continue
            project = projects[node.project_id]
            scoped_reviewer = current.user.role == 'reviewer' and can_work_node(db, current, node, departments=context.departments)
            if not can_work_project(current, project) and not scoped_reviewer:
                continue
            item = {'type': 'gate', 'id': gate.id, 'node_id': node.id, 'node_title': node.title,
                    'project_id': project.id, 'project_title': project.title, 'status': gate.status,
                    'created_at': gate.created_at.isoformat(), 'capabilities': {'approve_gate': True}}
            entries.append(((page_timestamp(gate.created_at), gate.id, 'gate'), item))
    return authorized_page(entries, organization_id=current.organization.id, endpoint='reviews', filters={'kind': kind},
                           cursor=cursor, limit=limit)
