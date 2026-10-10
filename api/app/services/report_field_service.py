"""Project-serialized field definitions and immutable report snapshots."""
from copy import deepcopy
from datetime import date
import math
import re
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from app.audit import log_audit
from app.models import Node
from app.permissions import can_edit_node


def clone_fields(fields):
    return [{**deepcopy(f), 'id': str(uuid4())} for f in fields]


def is_leaf(db, node):
    return node.kind == 'task' and db.scalar(select(Node.id).where(
        Node.organization_id == node.organization_id, Node.parent_id == node.id).limit(1)) is None


def editable(db, current, project, node, context):
    if not can_edit_node(db, current, project, node, context=context):
        return False
    if not is_leaf(db, node) or node.status in {'review', 'done', 'skipped'} or node.id in context.pending_reports:
        return False
    from app.services.collaboration_service import require_open_ancestors
    try:
        require_open_ancestors(db, current, node)
    except HTTPException:
        return False
    return True


def output(db, current, project, node, context):
    active = is_leaf(db, node)
    return {'fields': node.report_fields if active else [], 'version': node.report_fields_version,
            'active': active, 'can_edit': editable(db, current, project, node, context)}


def update(db, current, node_id, payload):
    from app.services.report_service import lock_node
    node, project, context = lock_node(db, current, node_id)
    if not can_edit_node(db, current, project, node, context=context):
        raise HTTPException(403, '沒有編輯此任務的權限')
    if not editable(db, current, project, node, context):
        raise HTTPException(409, '只有未關閉且沒有待確認回報的葉任務可設定欄位')
    if payload.expected_version != node.report_fields_version:
        raise HTTPException(409, '回報欄位已變更，請重新載入')
    old = {f['id']: f for f in node.report_fields}
    result = []
    seen = set()
    for field in payload.fields:
        value = field.model_dump()
        identifier = value['id']
        if identifier is not None:
            if identifier in seen or identifier not in old or value != old[identifier]:
                raise HTTPException(422, '既有欄位只能排序或移除，請新增欄位代替修改')
        else:
            identifier = str(uuid4())
            value['id'] = identifier
        seen.add(identifier)
        result.append(value)
    node.report_fields = result
    node.report_fields_version += 1
    log_audit(db, current, 'report_fields.update', node_id=node.id,
              payload={'version': node.report_fields_version, 'fields': result})
    db.commit()
    return output(db, current, project, node, context)


def snapshot(db, node, payload):
    fields = node.report_fields if is_leaf(db, node) else []
    # Legacy callers without definitions keep working; any changed schema requires a version.
    if payload.fields_version != node.report_fields_version:
        if not (payload.fields_version is None and node.report_fields_version == 0):
            raise HTTPException(409, '回報欄位已變更，請重新載入並確認輸入')
    if set(payload.field_values) - {f['id'] for f in fields}:
        raise HTTPException(422, '包含未知回報欄位')
    result = []
    for order, field in enumerate(fields):
        raw = payload.field_values.get(field['id'])
        empty = raw is None or isinstance(raw, str) and not raw.strip()
        value = None
        if empty:
            if field['required']:
                raise HTTPException(422, f'請填寫「{field["label"]}」')
        else:
            try:
                if field['type'] == 'number':
                    if isinstance(raw, bool) or not isinstance(raw, (str, int, float)):
                        raise ValueError()
                    value = float(raw)
                    if not math.isfinite(value): raise ValueError()
                else:
                    if not isinstance(raw, str) or len(raw) > 4000: raise ValueError()
                    value = raw.strip()
                    if field['type'] == 'select' and value not in field['options']: raise ValueError()
                    if field['type'] == 'date':
                        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value): raise ValueError()
                        date.fromisoformat(value)
            except (ValueError, OverflowError):
                raise HTTPException(422, f'「{field["label"]}」的值不符合欄位格式') from None
        result.append({**deepcopy(field), 'order': order, 'value': value})
    return result
