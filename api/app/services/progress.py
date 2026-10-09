"""Weighted progress over the nodes a user can see (README F1; TP-A).

Mirrors web/src/progress.ts operation by operation so both sides round to the same
percent: leaf tasks todo 0 / doing manual-or-50 / review 90 / done and skipped 100;
other leaves 100 when closed; parents are the weight-averaged visible children.
"""
import math

LEAF_TASK = {"todo": 0.0, "review": 90.0, "done": 100.0, "skipped": 100.0}


def leaf_progress(node) -> float:
    if node.kind == "task":
        if node.status == "doing":
            return float(node.progress if node.progress is not None else 50)
        return LEAF_TASK.get(node.status, 0.0)
    return 100.0 if node.status in ("done", "skipped") else 0.0


def weight_of(node) -> int:
    return node.weight if node.weight is not None else 1


def percent(value: float) -> int:
    # Half-up; the epsilon absorbs binary rounding of exact .5 averages.
    return math.floor(value + 0.5 + 1e-9)


def _order(node):
    return (node.sort_order, node.created_at.isoformat() if node.created_at else "", node.id)


def visible_roots(nodes) -> list:
    """Visible nodes whose parent is hidden or missing; damaged cycles keep one entry."""
    ids = {node.id for node in nodes}
    children = _children(nodes)
    roots = [node for node in nodes if node.parent_id is None or node.parent_id not in ids]
    visited: set[str] = set()

    def visit(start):
        pending = [start]
        while pending:
            item = pending.pop()
            if item.id in visited:
                continue
            visited.add(item.id)
            pending.extend(children.get(item.id, []))

    for root in roots:
        visit(root)
    for node in sorted(nodes, key=_order):
        if node.id not in visited:
            roots.append(node)
            visit(node)
    return sorted(roots, key=_order)


def _children(nodes) -> dict:
    ids = {node.id for node in nodes}
    children: dict[str, list] = {}
    for node in sorted(nodes, key=_order):
        if node.parent_id in ids and node.parent_id != node.id:
            children.setdefault(node.parent_id, []).append(node)
    return children


def progress_map(nodes) -> dict[str, float]:
    children = _children(nodes)
    memo: dict[str, float] = {}
    active: set[str] = set()

    def compute(node) -> float:
        if node.id in memo:
            return memo[node.id]
        active.add(node.id)
        kids = [child for child in children.get(node.id, []) if child.id not in active]
        if not kids:
            value = leaf_progress(node)
        else:
            total = 0
            weighted = 0.0
            for child in kids:
                weight = weight_of(child)
                total += weight
                weighted += compute(child) * weight
            value = weighted / total if total else 0.0
        active.discard(node.id)
        memo[node.id] = value
        return value

    for root in visible_roots(nodes):
        compute(root)
    for node in nodes:
        compute(node)
    return memo


def project_progress(nodes) -> int | None:
    """Weight-averaged visible top level; None when the user sees no node."""
    roots = visible_roots(nodes)
    if not roots:
        return None
    values = progress_map(nodes)
    total = 0
    weighted = 0.0
    for root in roots:
        weight = weight_of(root)
        total += weight
        weighted += values[root.id] * weight
    return percent(weighted / total if total else 0.0)
