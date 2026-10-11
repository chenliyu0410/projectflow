"""Purchase order receiving rules. Quantities use integer thousandths like the stock ledger."""
from fastapi import HTTPException
from sqlalchemy import case, func, select

from app.models import PurchaseOrder, PurchaseOrderLine

LABELS = {'no_lines': '未建立明細', 'pending': '待收貨', 'partial': '部分收貨', 'received': '已收齊', 'closed': '已結案'}
CLOSED = '採購單已結案，不能收貨或修改明細'
NOT_LISTED = '此物料不在採購明細中'
OVER = '超過未收數量，請先確認訂購數量'
UNIT = '單位須與採購明細一致'


def classify(closed, lines, received_lines, started_lines):
    if closed:
        return 'closed'
    if not lines:
        return 'no_lines'
    if received_lines == lines:
        return 'received'
    return 'partial' if started_lines else 'pending'


def line_status(ordered, received):
    return 'received' if received >= ordered else 'partial' if received else 'pending'


def summaries(db, organization_id, order_ids):
    """Receiving status per order for one listing page, without loading lines."""
    if not order_ids:
        return {}
    closed = {row.order_id: row.closed_at is not None for row in db.scalars(select(PurchaseOrder).where(
        PurchaseOrder.organization_id == organization_id, PurchaseOrder.order_id.in_(order_ids)))}
    counts = {row.order_id: row for row in db.execute(select(PurchaseOrderLine.order_id, func.count().label('lines'),
        func.sum(case((PurchaseOrderLine.received_milli >= PurchaseOrderLine.ordered_milli, 1), else_=0)).label('done'),
        func.sum(case((PurchaseOrderLine.received_milli > 0, 1), else_=0)).label('started'))
        .where(PurchaseOrderLine.organization_id == organization_id, PurchaseOrderLine.order_id.in_(order_ids))
        .group_by(PurchaseOrderLine.order_id))}
    result = {}
    for order_id in order_ids:
        row = counts.get(order_id)
        lines, done, started = (row.lines, int(row.done), int(row.started)) if row else (0, 0, 0)
        key = classify(closed.get(order_id, False), lines, done, started)
        result[order_id] = {'status': key, 'label': LABELS[key], 'lines': lines, 'received_lines': done}
    return result


def receipt_line(db, organization_id, order_id, resource_id, unit, delta):
    """Line the receipt counts toward; None keeps free receipts for orders without lines.

    Callers hold the company lock, so the received total cannot change underneath.
    """
    header = db.scalar(select(PurchaseOrder).where(PurchaseOrder.organization_id == organization_id,
        PurchaseOrder.order_id == order_id).with_for_update().execution_options(populate_existing=True))
    if header is None:
        return None
    if header.closed_at is not None:
        raise HTTPException(409, CLOSED)
    lines = {line.resource_id: line for line in db.scalars(select(PurchaseOrderLine).where(
        PurchaseOrderLine.organization_id == organization_id, PurchaseOrderLine.order_id == order_id)
        .with_for_update().execution_options(populate_existing=True))}
    if not lines:
        return None
    line = lines.get(resource_id)
    if line is None:
        raise HTTPException(409, NOT_LISTED)
    if line.unit != unit:
        raise HTTPException(409, UNIT)
    if line.received_milli + delta > line.ordered_milli:
        raise HTTPException(409, OVER)
    return line
