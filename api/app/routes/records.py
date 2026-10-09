"""Safe note writes and visibility-filtered record timelines."""
import base64
import json
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import log_audit
from app.services.attachment_store import bind_attachments, attachments_for, attachment_out
from app.auth import CurrentUser, require_session
from app.database import get_session
from app.models import Node, Project, TaskNote, TaskReport, now_utc
from app.permissions import can_view_node, can_view_project
from app.schemas import NoteCreate, NoteUpdate
from app.services.record_policy import load_policy_context, can_write_record
from app.services.report_service import lock_node, report_out, conflict

router = APIRouter(tags=['records'])


def note_out(note, context, attachments=()):
    author = context.users.get(note.author_id)
    return {'id': note.id, 'node_id': note.node_id, 'body': note.body,
            'author_id': note.author_id, 'author_display_name': author.display_name if author else None,
            'revision': note.revision, 'created_at': note.created_at.isoformat(),
            'edited_at': note.edited_at.isoformat() if note.edited_at else None,
            'attachments': [attachment_out(a, context.users) for a in attachments if a.note_id == note.id]}


def require_write(db, current, node, project, context):
    if not can_write_record(db, current, project, node, context=context):
        raise HTTPException(status_code=403, detail='沒有寫入筆記的權限')


@router.post('/nodes/{node_id}/notes', status_code=201)
def create_note(node_id: str, payload: NoteCreate, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    node, project, context = lock_node(db, current, node_id)
    require_write(db, current, node, project, context)
    note = TaskNote(organization_id=current.organization.id, node_id=node.id, author_id=current.user.id, body=payload.body)
    db.add(note)
    db.flush()
    bind_attachments(db, current, node, payload.attachment_ids, note_id=note.id)
    log_audit(db, current, 'note.create', node_id=node.id, payload={'note_id': note.id, 'body': note.body, 'revision': note.revision})
    db.commit()
    return note_out(note, context, attachments_for(db, current.organization.id, [node.id]))


@router.patch('/notes/{note_id}')
def update_note(note_id: str, payload: NoteUpdate, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    node_id = db.scalar(select(TaskNote.node_id).where(TaskNote.id == note_id, TaskNote.organization_id == current.organization.id))
    if node_id is None:
        raise HTTPException(status_code=404, detail='找不到筆記')
    node, project, context = lock_node(db, current, node_id)
    note = db.scalar(select(TaskNote).where(TaskNote.id == note_id, TaskNote.organization_id == current.organization.id)
                     .with_for_update().execution_options(populate_existing=True))
    require_write(db, current, node, project, context)
    if note.author_id != current.user.id:
        raise HTTPException(status_code=403, detail='只有作者可以編輯筆記')
    if note.revision != payload.expected_revision:
        conflict()
    if note.body != payload.body:
        before = {'body': note.body, 'revision': note.revision}
        note.body = payload.body
        note.revision += 1
        note.edited_at = now_utc()
        log_audit(db, current, 'note.update', node_id=node.id,
                  payload={'note_id': note.id, 'before': before, 'after': {'body': note.body, 'revision': note.revision}})
        db.commit()
    return note_out(note, context, attachments_for(db, current.organization.id, [node.id]))


def timestamp(value):
    # SQLite drops timezone information; both engines emit the same sortable UTC key.
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def decode_cursor(cursor, organization_id, node_id, scope):
    if cursor is None:
        return None
    try:
        if len(cursor) > 2048:
            raise ValueError()
        data = json.loads(base64.b64decode(cursor, altchars=b'-_', validate=True))
        if (not isinstance(data, dict) or set(data) != {'organization_id', 'node_id', 'scope', 'key'}
                or data['organization_id'] != organization_id or data['node_id'] != node_id or data['scope'] != scope):
            raise ValueError()
        key = data['key']
        if (not isinstance(key, list) or len(key) != 3 or not all(isinstance(x, str) for x in key)
                or key[2] not in {'note', 'report', 'attachment'} or not key[1]):
            raise ValueError()
        if timestamp(datetime.fromisoformat(key[0])) != key[0]:
            raise ValueError()
        return tuple(key)
    except (ValueError, TypeError, KeyError, UnicodeError, OverflowError, RecursionError):
        raise HTTPException(status_code=422, detail='無效的分頁游標') from None


@router.get('/nodes/{node_id}/records')
def list_records(node_id: str, scope: Literal['self', 'subtree'] = 'self',
                 limit: int = Query(50, ge=1, le=100), cursor: str | None = None,
                 current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    org = current.organization.id
    context = load_policy_context(db, current)
    root = db.scalar(select(Node).where(Node.id == node_id, Node.organization_id == org))
    project = db.scalar(select(Project).where(Project.id == root.project_id, Project.organization_id == org)) if root else None
    if (root is None or project is None or not can_view_project(current, project)
            or not can_view_node(current, root, context=context)):
        raise HTTPException(status_code=404, detail='找不到節點')
    after = decode_cursor(cursor, org, node_id, scope)
    nodes = {root.id: root}
    if scope == 'subtree':
        candidates = {n.id: n for n in db.scalars(select(Node).where(Node.organization_id == org, Node.project_id == root.project_id))}
        children = {}
        for n in candidates.values():
            children.setdefault(n.parent_id, []).append(n.id)
        visited, pending = set(), [root.id]
        nodes = {}
        while pending:
            nid = pending.pop()
            if nid in visited:
                continue
            visited.add(nid)
            n = candidates[nid]
            if can_view_node(current, n, context=context):
                nodes[nid] = n
            pending.extend(children.get(nid, []))
    return record_page(db, context, org, nodes, node_id, scope, after, limit)


@router.get('/projects/{project_id}/records')
def list_project_records(project_id: str, limit: int = Query(50, ge=1, le=100), cursor: str | None = None,
                         current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    """Read-only roll-up of every record on the project's visible nodes."""
    org = current.organization.id
    context = load_policy_context(db, current)
    project = db.scalar(select(Project).where(Project.id == project_id, Project.organization_id == org))
    if project is None or not can_view_project(current, project):
        raise HTTPException(status_code=404, detail='找不到專案')
    after = decode_cursor(cursor, org, project.id, 'project')
    nodes = {n.id: n for n in db.scalars(select(Node).where(Node.organization_id == org, Node.project_id == project.id))
             if can_view_node(current, n, context=context)}
    return record_page(db, context, org, nodes, project.id, 'project', after, limit)


def record_page(db, context, org, nodes, cursor_id, scope, after, limit):
    # Query record content only for the final authorized node set, before pagination.
    entries = []
    attachments = attachments_for(db, org, nodes)
    for attachment in attachments:
        if attachment.report_id is None and attachment.note_id is None:
            key = (timestamp(attachment.created_at), attachment.id, 'attachment')
            entries.append((key, {**attachment_out(attachment, context.users), 'type': 'attachment',
                                  'node_title': nodes[attachment.node_id].title}))
    for note in db.scalars(select(TaskNote).where(TaskNote.organization_id == org, TaskNote.node_id.in_(nodes))):
        key = (timestamp(note.created_at), note.id, 'note')
        entries.append((key, {**note_out(note, context, attachments), 'type': 'note', 'node_title': nodes[note.node_id].title}))
    for report in db.scalars(select(TaskReport).where(TaskReport.organization_id == org, TaskReport.node_id.in_(nodes))):
        key = (timestamp(report.submitted_at), report.id, 'report')
        entries.append((key, {**report_out(report, nodes[report.node_id], context, attachments), 'type': 'report',
                              'created_at': report.submitted_at.isoformat(), 'node_title': nodes[report.node_id].title}))
    entries.sort(key=lambda entry: entry[0])
    if after is not None:
        entries = [entry for entry in entries if entry[0] > after]
    page = entries[:limit]
    next_cursor = None
    if len(entries) > limit:
        data = {'organization_id': org, 'node_id': cursor_id, 'scope': scope, 'key': page[-1][0]}
        next_cursor = base64.urlsafe_b64encode(json.dumps(data, separators=(',', ':')).encode()).decode()
    return {'items': [entry[1] for entry in page], 'next_cursor': next_cursor}
