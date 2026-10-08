"""Workspace queries use only authorized nodes, including non-leaf tasks."""
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import CurrentUser, require_session
from app.database import get_session
from app.models import Department, User
from app.services.node_policy import node_out, visible_workspace_nodes

from app.services.record_policy import load_policy_context, is_collaborator

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
