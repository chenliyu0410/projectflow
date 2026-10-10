"""Visibility-filtered audit events with action-specific safe projections."""
from datetime import date
import re

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import CurrentUser, require_session
from app.database import get_session
from app.models import Attachment, AuditLog, Gate, TaskNote, TaskReport, Workflow
from app.services.node_policy import visible_workspace_nodes
from app.services.record_policy import load_policy_context, authorized_page, page_timestamp

router = APIRouter(tags=['audit'])


def text_value(value, maximum):
    return value if isinstance(value, str) and len(value) <= maximum else None


def integer_value(value, minimum=0):
    return value if type(value) is int and value >= minimum else None


def safe_id(value, mapping):
    return value if isinstance(value, str) and value in mapping else None


def date_value(value):
    if not isinstance(value, str):
        return None
    try:
        return value if date.fromisoformat(value).isoformat() == value else None
    except ValueError:
        return None


def reference(payload, field, mapping, node_id):
    key = safe_id(payload.get(field), mapping)
    row = mapping.get(key)
    return key if row is not None and row.node_id == node_id else None


def project_payload(action, raw, node, context, projects, references):
    """Never copy arbitrary mappings; linked content requires the same visible node."""
    if not isinstance(raw, dict):
        return {}
    node_id = node.id if node else None
    if action.startswith('report.') and action in {'report.submit', 'report.approve', 'report.reject'}:
        rid = reference(raw, 'report_id', references['reports'], node_id)
        if rid is None:
            return {}
        result = {'report_id': rid}
        for key, value in [('version', integer_value(raw.get('version'), 1)),
                           ('result', text_value(raw.get('result'), 80)), ('comment', text_value(raw.get('comment'), 2000))]:
            if value is not None:
                result[key] = value
        if type(raw.get('self_approved')) is bool:
            result['self_approved'] = raw['self_approved']
        return result
    if action in {'note.create', 'note.update'}:
        nid = reference(raw, 'note_id', references['notes'], node_id)
        if nid is None:
            return {}
        result = {'note_id': nid}
        def body_revision(value):
            if not isinstance(value, dict):
                return {}
            projected = {}
            body = text_value(value.get('body'), 10000)
            revision = integer_value(value.get('revision'), 1)
            if body is not None:
                projected['body'] = body
            if revision is not None:
                projected['revision'] = revision
            return projected
        if action == 'note.create':
            result.update(body_revision(raw))
        else:
            result.update({key: body_revision(raw.get(key)) for key in ['before', 'after']})
        return result
    if action in {'attachment.upload', 'attachment.delete'}:
        aid = reference(raw, 'attachment_id', references['attachments'], node_id)
        if aid is None:
            return {}
        result = {'attachment_id': aid}
        name, size, digest = text_value(raw.get('original_name'), 200), integer_value(raw.get('size_bytes')), raw.get('sha256')
        if name is not None:
            result['original_name'] = name
        if size is not None:
            result['size_bytes'] = size
        if isinstance(digest, str) and re.fullmatch('[0-9a-f]{64}', digest):
            result['sha256'] = digest
        return result
    if action == 'gate.approve':
        gid = reference(raw, 'gate_id', references['gates'], node_id)
        return {'gate_id': gid, 'status': 'approved'} if gid and raw.get('status') == 'approved' else {}
    if action == 'workflow.instantiate':
        pid, wid = safe_id(raw.get('project_id'), projects), safe_id(raw.get('workflow_id'), references['workflows'])
        if pid is None or wid is None:
            return {}
        return {'project_id': pid, 'workflow_id': wid, 'title': text_value(raw.get('title'), 200)}
    if node is None:
        return {}
    if action == 'project.create':
        return {'project_id': node.project_id, 'title': text_value(raw.get('title'), 200)} if raw.get('project_id') == node.project_id else {}
    if action == 'node.status':
        return {'status': raw['status']} if isinstance(raw.get('status'), str) and raw['status'] in {'todo', 'doing', 'review', 'done', 'skipped'} else {}
    if action in {'node.reopen', 'node.skip', 'node.restore'}:
        reason = text_value(raw.get('reason'), 2000)
        return {'reason': reason} if reason is not None else {}
    if action == 'node.delete':
        result = {'title': text_value(raw.get('title'), 200)}
        if isinstance(raw.get('node_ids'), list):
            result['count'] = len(raw['node_ids'])
        parent = safe_id(raw.get('parent_id'), references['nodes'])
        if parent and references['nodes'][parent].project_id == node.project_id:
            result.update({'parent_id': parent, 'parent_title': references['nodes'][parent].title})
        return result
    if action == 'node.copy':
        result = {}
        if isinstance(raw.get('node_ids'), list):
            result['count'] = len(raw['node_ids'])
        source = safe_id(raw.get('source_id'), references['nodes'])
        if source and references['nodes'][source].project_id == node.project_id:
            result.update({'source_id': source, 'source_title': references['nodes'][source].title})
        return result
    if action == 'node.undo':
        return {'action': raw['action']} if raw.get('action') in {'node.create', 'node.delete', 'node.move', 'node.copy'} else {}
    if action == 'node.move':
        result = {}
        for key in ['from_parent_id', 'to_parent_id']:
            parent = safe_id(raw.get(key), references['nodes'])
            if parent and references['nodes'][parent].project_id == node.project_id:
                result[key] = parent
                result[key.replace('_id', '_title')] = references['nodes'][parent].title
        return result
    if action in {'node.create', 'node.update'}:
        fields = {'title': lambda value: text_value(value, 200),
                  'start_date': date_value, 'due_date': date_value,
                  'milestone': lambda value: value if type(value) is bool else None,
                  'schedule_locked': lambda value: value if type(value) is bool else None,
                  'weight': lambda value: value if type(value) is int and 0 <= value <= 100 else None,
                  'progress': lambda value: value if type(value) is int and 0 <= value <= 100 else None,
                  'owner_user_id': lambda value: safe_id(value, context.users),
                  'department_id': lambda value: safe_id(value, context.departments)}
        result = {}
        if action == 'node.create':
            for key, convert in fields.items():
                if key in raw:
                    result[key] = convert(raw[key])
            if raw.get('project_id') == node.project_id:
                result['project_id'] = node.project_id
            parent = safe_id(raw.get('parent_id'), references['nodes'])
            if parent and references['nodes'][parent].project_id == node.project_id:
                result['parent_id'] = parent
            if isinstance(raw.get('kind'), str) and raw['kind'] in {'project', 'phase', 'task'}:
                result['kind'] = raw['kind']
        else:
            for key, convert in fields.items():
                value = raw.get(key)
                if isinstance(value, dict):
                    result[key] = {side: convert(value[side]) for side in ['before', 'after'] if side in value}
        return result
    if action == 'collaborators.update':
        result = {}
        for side in ['before', 'after']:
            value = raw.get(side)
            if not isinstance(value, dict):
                continue
            projected = {}
            revision = integer_value(value.get('revision'))
            if revision is not None:
                projected['revision'] = revision
            for key, mapping, label in [('users', context.users, 'display_name'), ('departments', context.departments, 'name')]:
                if not isinstance(value.get(key), list):
                    continue
                ids = {safe_id(item.get('id'), mapping) for item in value[key] if isinstance(item, dict)} - {None}
                projected[key] = [{'id': identifier, label: getattr(mapping[identifier], label)} for identifier in sorted(ids)]
            result[side] = projected
        return result
    return {}


SUMMARIES = {'project.create': '建立專案', 'workflow.instantiate': '套用工作流', 'node.create': '新增節點',
             'node.update': '更新節點資料', 'node.status': '更新節點狀態', 'node.move': '移動節點', 'node.reopen': '恢復工作',
             'node.delete': '刪除節點', 'node.copy': '複製子樹', 'node.undo': '復原',
             'node.skip': '略過任務', 'node.restore': '恢復略過任務', 'gate.approve': '核准閘門',
             'report.submit': '送出回報', 'report.approve': '確認回報', 'report.reject': '退回回報',
             'note.create': '新增筆記', 'note.update': '修訂筆記', 'collaborators.update': '更新協作設定',
             'attachment.upload': '上傳附件', 'attachment.delete': '移除附件'}


@router.get('/audit-logs')
def list_audit_logs(node_id: str | None = None, action: str = Query('', max_length=80),
                    cursor: str | None = None, limit: int = Query(50, ge=1, le=100),
                    current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    context = load_policy_context(db, current)
    # Deleted nodes keep their history in the audit view (TP-B soft delete).
    projects, visible_nodes = visible_workspace_nodes(db, current, context=context, include_deleted=True)
    nodes = {node.id: node for node in visible_nodes}
    org = current.organization.id
    references = {'nodes': nodes}
    for key, model in [('reports', TaskReport), ('notes', TaskNote), ('attachments', Attachment), ('gates', Gate)]:
        references[key] = {row.id: row for row in db.scalars(select(model).where(model.organization_id == org, model.node_id.in_(nodes)))}
    references['workflows'] = {row.id: row for row in db.scalars(select(Workflow).where(Workflow.organization_id == org))}
    action, node_id = action.strip(), node_id.strip() if node_id else None
    entries = []
    for log in db.scalars(select(AuditLog).where(AuditLog.organization_id == org)):
        node = nodes.get(log.node_id)
        if (log.node_id is None and current.user.role != 'admin') or (log.node_id is not None and node is None):
            continue
        if (node_id is not None and log.node_id != node_id) or (action and log.action != action):
            continue
        actor = context.users.get(log.actor_user_id)
        item = {'id': log.id, 'organization_key': current.organization.key, 'action': log.action,
                'summary': ('自動順延' if log.payload['schedule'].get('cascade') else '調整時程') if log.action == 'node.update' and isinstance(log.payload, dict) and isinstance(log.payload.get('schedule'), dict) else SUMMARIES.get(log.action, '其他業務事件'), 'node_id': log.node_id,
                'node_title': node.title if node else None, 'project_id': node.project_id if node else None,
                'node_deleted': node is not None and node.deleted_at is not None,
                'project_title': projects[node.project_id].title if node else None,
                'actor_user_id': actor.id if actor else None, 'actor_display_name': actor.display_name if actor else None,
                'payload': project_payload(log.action, log.payload, node, context, projects, references),
                'created_at': log.created_at.isoformat()}
        entries.append(((page_timestamp(log.created_at), log.id, 'audit'), item))
    return authorized_page(entries, organization_id=org, endpoint='audit', filters={'node_id': node_id, 'action': action},
                           cursor=cursor, limit=limit, descending=True)
