"""Work order production rules. Quantities use integer thousandths like the stock ledger."""
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select

from app.models import InventoryMovement, WorkOrder
from app.services.stock_service import net_issued

LABELS = {'no_plan': '未設定計畫', 'planned': '待生產', 'in_progress': '生產中', 'completed': '已達計畫產量', 'closed': '已結案'}
CLOSED = '工單已結案，不能領料、完工或修改計畫'
REOPEN = '工單已結案，請先重新開啟再退料或沖銷'
NOT_PRODUCT = '完工品項須為工單指定成品'
OVER = '超過計畫產量，請先調整計畫產量'
OVER_RETURN = '超過本工單淨領料，無法退料'
UNIT = '完工單位須與工單計畫一致'
ISSUED_RANGE = '沖銷後淨領料會小於零，請先沖銷相關退料'
PLAN_RANGE = '沖銷後已完工數量會超出計畫或小於零'


def classify(order, started):
    """order: WorkOrder or None; started: the work order already has an issue or completion."""
    if order is not None and order.closed_at is not None:
        return 'closed'
    if order is None or order.product_id is None:
        return 'no_plan'
    if order.completed_milli >= order.planned_milli:
        return 'completed'
    return 'in_progress' if started or order.completed_milli else 'planned'


def started_ids(db, organization_id, work_ids):
    return set(db.scalars(select(InventoryMovement.work_id).where(InventoryMovement.organization_id == organization_id,
        InventoryMovement.work_id.in_(work_ids)).distinct()))


def quantity(value):
    return format(Decimal(value) / 1000, '.3f')


def summaries(db, organization_id, work_ids):
    """Production status per work order for one listing page."""
    if not work_ids:
        return {}
    orders = {row.work_id: row for row in db.scalars(select(WorkOrder).where(
        WorkOrder.organization_id == organization_id, WorkOrder.work_id.in_(work_ids)))}
    started = started_ids(db, organization_id, work_ids)
    result = {}
    for work_id in work_ids:
        order = orders.get(work_id)
        key = classify(order, work_id in started)
        planned = order is not None and order.product_id is not None
        result[work_id] = {'status': key, 'label': LABELS[key], 'unit': order.unit if planned else None,
            'planned': quantity(order.planned_milli) if planned else None, 'completed': quantity(order.completed_milli) if planned else None}
    return result


def locked_order(db, organization_id, work_id, closed_message):
    order = db.scalar(select(WorkOrder).where(WorkOrder.organization_id == organization_id, WorkOrder.work_id == work_id)
        .with_for_update().execution_options(populate_existing=True))
    if order is not None and order.closed_at is not None:
        raise HTTPException(409, closed_message)
    return order


def check_posting(db, organization_id, work_id, kind, resource_id, unit, delta):
    """Plan the completion counts toward; None for issues, returns and work orders without a plan.

    Callers hold the company lock, so the completed and issued totals cannot change underneath.
    """
    order = locked_order(db, organization_id, work_id, REOPEN if kind == 'issue_return' else CLOSED)
    if kind == 'issue_return' and net_issued(db, organization_id, work_id, resource_id) < delta:
        raise HTTPException(409, OVER_RETURN)
    if kind != 'completion' or order is None or order.product_id is None:
        return None
    if resource_id != order.product_id:
        raise HTTPException(409, NOT_PRODUCT)
    if unit != order.unit:
        raise HTTPException(409, UNIT)
    if order.completed_milli + delta > order.planned_milli:
        raise HTTPException(409, OVER)
    return order


def reversal_plan(db, organization_id, original, delta):
    """Plan whose completed output a reversal changes; issued totals may not go below zero."""
    order = locked_order(db, organization_id, original.work_id, REOPEN)
    if original.kind in ('issue', 'issue_return') and net_issued(db, organization_id, original.work_id, original.resource_id) - delta < 0:
        raise HTTPException(409, ISSUED_RANGE)
    if not original.counted_in_plan:
        return None
    # Counted completions lock the plan's product and unit, so the plan still matches the entry.
    if not 0 <= order.completed_milli + delta <= order.planned_milli:
        raise HTTPException(409, PLAN_RANGE)
    return order
