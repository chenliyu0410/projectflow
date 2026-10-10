"""D75: plan date changes without ORM writes, then apply all changes atomically.

The caller holds the project's lock, shared with tree/dependency operations.
All calculations use the complete active tree; errors never identify hidden nodes.
"""
from datetime import date
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select

from app.audit import log_audit
from app.models import Node, NodeDependency
from app.permissions import can_edit_node, can_manage_project, can_view_node
from app.services.node_policy import json_value, validate_dates

BLOCKED = '後續任務有無法調整的項目，請由專案負責人確認'
MILESTONE_PARENT = '里程碑不能有子任務，請先取消里程碑'
DATE_CONFLICT = '日期早於自己或上層的前置任務，請先調整排程'
INVALID_GRAPH = '時程相依或階層無法計算，請先檢查連線'


def fail(message=BLOCKED, status=409):
    raise HTTPException(status_code=status, detail=message)


def tree_index(nodes):
    children = {nid: [] for nid in nodes}
    for n in nodes.values():
        if n.parent_id is not None:
            if n.parent_id not in nodes:
                fail(INVALID_GRAPH)
            children[n.parent_id].append(n.id)
    order = [nid for nid, n in nodes.items() if n.parent_id is None]
    for nid in order:
        order.extend(children[nid])
        if len(order) > len(nodes):
            fail(INVALID_GRAPH)
    if len(order) != len(nodes):
        fail(INVALID_GRAPH)
    return children, order


def ancestors(nodes, nid):
    result = set()
    while nid is not None:
        if nid in result or nid not in nodes:
            fail(INVALID_GRAPH)
        result.add(nid)
        nid = nodes[nid].parent_id
    return result


def spans(dates, children, order):
    result = {}
    for nid in reversed(order):
        start, due = dates[nid]
        starts = [start] if start is not None else []
        ends = [due] if due is not None else []
        for child in children[nid]:
            a, b = result[child]
            if a is not None: starts.append(a)
            if b is not None: ends.append(b)
        result[nid] = (min(starts) if starts else None, max(ends) if ends else None)
    return result


def validate_flags(db, current, project, node, fields, nodes):
    milestone = fields.get('milestone', bool(node.milestone))
    locked = fields.get('schedule_locked', bool(node.schedule_locked))
    manage = can_manage_project(current, project)
    if ('schedule_locked' in fields and locked != bool(node.schedule_locked) and not manage
            or node.schedule_locked and not manage and any(
                key in fields and fields[key] != getattr(node, key) for key in ('start_date', 'due_date', 'milestone'))):
        fail('只有專案負責人或系統管理員可以調整已鎖定的里程碑', 403)
    start, due = fields.get('start_date', node.start_date), fields.get('due_date', node.due_date)
    validate_dates(start, due)
    if locked and not milestone:
        fail('取消里程碑時請同時解除鎖定', 422)
    if milestone:
        if node.kind != 'task' or not start or not due or start != due:
            fail('里程碑必須是開始與截止同日的任務', 422)
        if any(n.parent_id == node.id for n in nodes.values()):
            fail(MILESTONE_PARENT)


def prepare(db, current, project, node, fields, context, cascade=False):
    nodes = {n.id: n for n in db.scalars(select(Node).where(
        Node.organization_id == current.organization.id, Node.project_id == project.id))}
    nodes[node.id] = node
    validate_flags(db, current, project, node, fields, nodes)
    # Metadata-only edits do not revalidate legacy schedule conflicts.
    date_change = any(k in fields and fields[k] != getattr(node, k) for k in ('start_date', 'due_date'))
    if not date_change and not cascade:
        return {node.id: fields}, 0
    children, order = tree_index(nodes)
    edges = list(db.scalars(select(NodeDependency).where(
        NodeDependency.organization_id == current.organization.id, NodeDependency.project_id == project.id, NodeDependency.enforcement == 'hard')))
    if any(e.predecessor_id not in nodes or e.successor_id not in nodes for e in edges):
        fail(INVALID_GRAPH)
    original = {nid: (n.start_date.toordinal() if n.start_date else None,
                      n.due_date.toordinal() if n.due_date else None) for nid, n in nodes.items()}
    dates = dict(original)
    dates[node.id] = tuple(fields.get(k, getattr(node, k)).toordinal() if fields.get(k, getattr(node, k)) else None
                           for k in ('start_date', 'due_date'))
    changed = {node.id}
    affected = ancestors(nodes, node.id)
    if cascade:
        if None in dates[node.id]:
            fail('自動順延需要完整的開始與截止日期', 422)
        # Positive FS constraints converge within N relaxations in an acyclic graph.
        # Hierarchy feedback cycles also fail atomically instead of silently truncating.
        for _ in range(len(nodes) + 1):
            moved = False
            ranges = spans(dates, children, order)
            for edge in edges:
                pred, succ = edge.predecessor_id, edge.successor_id
                if pred not in affected:
                    continue
                if None in ranges[pred]:
                    continue
                if None in dates[succ]:
                    fail()
                need = required_shift(edge, ranges[pred], ranges[succ])
                if need <= 0:
                    continue
                family = [succ]
                for nid in family:
                    family.extend(children[nid])
                    item = nodes[nid]
                    if (None in dates[nid] or item.schedule_locked or item.status in {'review', 'done', 'skipped'}
                            or not can_view_node(current, item, context=context)
                            or not can_edit_node(db, current, project, item, context=context, departments=context.departments)):
                        fail()
                    start, due = dates[nid]
                    if due + need > date.max.toordinal():
                        fail('順延日期超出允許範圍')
                    dates[nid] = (start + need, due + need)
                    changed.add(nid)
                    affected.update(ancestors(nodes, nid))
                moved = True
                ranges = spans(dates, children, order)
            if not moved:
                break
        else:
            fail(INVALID_GRAPH)
    ranges = spans(dates, children, order)
    # Check only the incoming constraints of changed nodes and their ancestors.
    # Without cascade, a later predecessor may leave its successors in conflict.
    for nid in changed:
        for target in ancestors(nodes, nid):
            for edge in edges:
                if edge.successor_id != target:
                    continue
                if edge.relation_type == 'FF' and target != nid:
                    continue
                if None not in ranges[edge.predecessor_id] and None not in ranges[target] and required_shift(edge, ranges[edge.predecessor_id], ranges[target]) > 0:
                    fail(DATE_CONFLICT)
    updates = {node.id: dict(fields)}
    for nid in changed:
        if dates[nid] != original[nid]:
            updates.setdefault(nid, {}).update({key: date.fromordinal(value) if value is not None else None
                                                for key, value in zip(('start_date', 'due_date'), dates[nid])})
    return updates, sum(nid != node.id and dates[nid] != original[nid] for nid in changed)


def apply(db, current, project, node, fields, context, cascade=False):
    updates, count = prepare(db, current, project, node, fields, context, cascade)
    operation = str(uuid4())
    for nid, values in updates.items():
        item = node if nid == node.id else db.get(Node, nid)
        changes = {k: {'before': json_value(getattr(item, k)), 'after': json_value(v)}
                   for k, v in values.items() if getattr(item, k) != v}
        if not changes:
            continue
        for key in changes:
            setattr(item, key, values[key])
        if {'start_date', 'due_date'} & changes.keys():
            changes['schedule'] = {'operation_id': operation, 'source_node_id': node.id, 'cascade': nid != node.id}
        log_audit(db, current, 'node.update', node_id=nid, payload=changes)
    return count


def required_shift(edge, predecessor, successor):
    if edge.relation_type == 'SS':
        return predecessor[0] + edge.lag_days - successor[0]
    if edge.relation_type == 'FF':
        return predecessor[1] + edge.lag_days - successor[1]
    return predecessor[1] + 1 + edge.lag_days - successor[0]
