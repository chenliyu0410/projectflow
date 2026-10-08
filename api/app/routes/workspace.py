"""Workspace queries use only authorized nodes, including non-leaf tasks."""
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import CurrentUser, require_session
from app.database import get_session
from app.models import Gate
from app.permissions import can_work_node, can_work_project
from app.services.node_policy import node_out, visible_workspace_nodes

from app.services.record_policy import load_policy_context, is_collaborator, can_review_report, authorized_page, page_timestamp

router = APIRouter(prefix="/workspace", tags=["workspace"])
STATUSES = ("todo", "doing", "review", "done", "skipped")


def empty_counts() -> dict[str, int]:
    return dict.fromkeys(STATUSES, 0)


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
    counts = empty_counts()
    per_project = {pid: empty_counts() for pid in projects}
    for node in nodes:
        if node.kind == "task":
            counts[node.status] += 1
            per_project[node.project_id][node.status] += 1
    return {
        "project_count": len(projects),
        "task_counts": counts,
        "completion_percent": completion_percent(counts),
        "projects": [
            {"id": project.id, "title": project.title, "task_counts": per_project[project.id],
             "completion_percent": completion_percent(per_project[project.id])}
            for project in projects.values()
        ],
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
    return {"items": [
        {**node_out(db, current, projects[node.project_id], node, context=context),
         "project_title": projects[node.project_id].title,
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
