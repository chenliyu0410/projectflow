"""Purchase order receiving rules. Quantities use integer thousandths like the stock ledger."""
from fastapi import HTTPException
from sqlalchemy import case, func, select

from app.models import PurchaseOrder, PurchaseOrderLine
from app.services.stock_service import free_received

LABELS = {'no_lines': '未建立明細', 'pending': '待收貨', 'partial': '部分收貨', 'received': '已收齊', 'closed': '已結案'}
CLOSED = '採購單已結案，不能收貨或修改明細'
REOPEN = '採購單已結案，請先重新開啟再退貨或沖銷'
NOT_LISTED = '此物料不在採購明細中'
OVER = '超過未收數量，請先確認訂購數量'
OVER_RETURN = '超過已收數量，無法退貨'
UNIT = '單位須與採購明細一致'
LINE_RANGE = '沖銷後已收數量會超出訂購或小於零，請先調整明細或沖銷相關退貨'
FREE_RANGE = '沖銷後淨收貨會小於零，請先沖銷相關退貨'


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


def locked_lines(db, organization_id, order_id, closed_message):
    """Lock the order header and its lines; a closed order refuses every stock posting."""
    header = db.scalar(select(PurchaseOrder).where(PurchaseOrder.organization_id == organization_id,
        PurchaseOrder.order_id == order_id).with_for_update().execution_options(populate_existing=True))
    if header is None:
        return []
    if header.closed_at is not None:
        raise HTTPException(409, closed_message)
    return db.scalars(select(PurchaseOrderLine).where(PurchaseOrderLine.organization_id == organization_id,
        PurchaseOrderLine.order_id == order_id).with_for_update().execution_options(populate_existing=True)).all()


def listed_line(lines, resource_id, unit):
    line = next((line for line in lines if line.resource_id == resource_id), None)
    if line is None:
        raise HTTPException(409, NOT_LISTED)
    if line.unit != unit:
        raise HTTPException(409, UNIT)
    return line


def receipt_line(db, organization_id, order_id, resource_id, unit, delta):
    """Line the receipt counts toward; None keeps free receipts for orders without lines.

    Callers hold the company lock, so the received total cannot change underneath.
    """
    lines = locked_lines(db, organization_id, order_id, CLOSED)
    if not lines:
        return None
    line = listed_line(lines, resource_id, unit)
    if line.received_milli + delta > line.ordered_milli:
        raise HTTPException(409, OVER)
    return line


def return_line(db, organization_id, order_id, resource_id, unit, delta):
    """Line a return (negative delta) takes back from; the outstanding quantity reopens for replacement."""
    lines = locked_lines(db, organization_id, order_id, REOPEN)
    if not lines:
        if free_received(db, organization_id, order_id, resource_id) + delta < 0:
            raise HTTPException(409, OVER_RETURN)
        return None
    line = listed_line(lines, resource_id, unit)
    if line.received_milli + delta < 0:
        raise HTTPException(409, OVER_RETURN)
    return line


def reversal_line(db, organization_id, original, delta):
    """Line whose received quantity a reversal of a receipt or return changes, after range checks."""
    lines = locked_lines(db, organization_id, original.order_id, REOPEN)
    if original.line_id is None:
        if free_received(db, organization_id, original.order_id, original.resource_id) + delta < 0:
            raise HTTPException(409, FREE_RANGE)
        return None
    line = next((line for line in lines if line.id == original.line_id), None)
    if line is None or not 0 <= line.received_milli + delta <= line.ordered_milli:
        raise HTTPException(409, LINE_RANGE)
    return line
