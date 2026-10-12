"""Purchase order lines, receiving progress and manual close/reopen. Managers only, like the stock ledger."""
from decimal import Decimal
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.auth import CurrentUser, require_session
from app.database import get_session
from app.models import Organization, InventoryBalance, InventoryMovement, OperationsRecord, PurchaseOrder, PurchaseOrderLine, User, now_utc
from app.audit import log_audit
from app.routes.operations import get_record, visible
from app.routes.inventory import authorize, quantity
from app.services.purchase_service import CLOSED, LABELS, classify, line_status
from app.services.stock_service import returned_by_line

router = APIRouter(tags=['purchasing'])
STALE = '採購明細已變更，請重新載入'
LOCKED_LINE = '已有收貨的明細不可刪除或更換物料、單位'
BELOW = '訂購數量不可少於已收數量'
STOCK_UNIT = '明細單位須與物料既有庫存單位一致'
NOT_CLOSED = '採購單尚未結案'


class LineWrite(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    id: str | None = Field(default=None, min_length=1, max_length=36)
    resource_id: str = Field(min_length=1, max_length=36)
    quantity: Decimal = Field(max_digits=12, decimal_places=3, gt=0, le=999999999, allow_inf_nan=False)
    unit: str = Field(min_length=1, max_length=20)
    note: str = Field(default='', max_length=500)


class LinesWrite(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_revision: int = Field(ge=0)
    lines: list[LineWrite] = Field(max_length=50)


class StateWrite(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    expected_revision: int = Field(ge=0)
    reason: str = Field(min_length=1, max_length=500)


def load_order(db, current, order_id, lock=False):
    authorize(current)
    order = get_record(db, current, order_id, lock)
    if order.category != 'orders':
        raise HTTPException(422, '請選擇採購紀錄')
    return order


def detail(db, current, order):
    org = current.organization.id
    header = db.get(PurchaseOrder, (org, order.id))
    rows = db.execute(select(PurchaseOrderLine, OperationsRecord.code, OperationsRecord.title)
        .join(OperationsRecord, (OperationsRecord.organization_id == PurchaseOrderLine.organization_id) & (OperationsRecord.id == PurchaseOrderLine.resource_id))
        .where(PurchaseOrderLine.organization_id == org, PurchaseOrderLine.order_id == order.id)
        .order_by(PurchaseOrderLine.line_no, PurchaseOrderLine.id)).all()
    closed = header is not None and header.closed_at is not None
    key = classify(closed, len(rows), sum(line.received_milli >= line.ordered_milli for line, _, _ in rows),
        sum(line.received_milli > 0 for line, _, _ in rows))
    closer = db.scalar(select(User.display_name).where(User.organization_id == org, User.id == header.closed_by)) if closed else None
    returned = returned_by_line(db, org, order.id)
    used = referenced_lines(db, org, order.id)
    return {'order_id': order.id, 'revision': header.revision if header else 0, 'status': key, 'status_label': LABELS[key],
        'closed_at': header.closed_at.isoformat() if closed else None, 'closed_by': closer,
        'close_reason': header.close_reason if closed else None,
        'unlinked_receipts': db.scalar(select(func.count()).select_from(InventoryMovement).where(InventoryMovement.organization_id == org,
            InventoryMovement.order_id == order.id, InventoryMovement.line_id.is_(None), InventoryMovement.kind == 'receipt')),
        'lines': [{'id': line.id, 'line_no': line.line_no, 'resource_id': line.resource_id, 'resource_code': code, 'resource_title': title,
            'unit': line.unit, 'ordered': quantity(line.ordered_milli), 'received': quantity(line.received_milli),
            'remaining': quantity(line.ordered_milli - line.received_milli), 'returned': quantity(returned.get(line.id, 0)),
            'locked': line.id in used, 'note': line.note,
            'status': line_status(line.ordered_milli, line.received_milli)} for line, code, title in rows]}


def referenced_lines(db, organization_id, order_id):
    """Lines any ledger entry points at; they keep their identity even when returns bring them back to zero."""
    return set(db.scalars(select(InventoryMovement.line_id).where(InventoryMovement.organization_id == organization_id,
        InventoryMovement.order_id == order_id, InventoryMovement.line_id.is_not(None)).distinct()))


def begin(db, current, order_id, expected):
    """Lock in the stock ledger's order (company, then document) and reject stale revisions."""
    authorize(current)
    org = current.organization.id
    db.scalar(select(Organization).where(Organization.id == org).with_for_update())
    order = load_order(db, current, order_id, True)
    header = db.scalar(select(PurchaseOrder).where(PurchaseOrder.organization_id == org, PurchaseOrder.order_id == order.id)
        .with_for_update().execution_options(populate_existing=True))
    if (header.revision if header else 0) != expected:
        raise HTTPException(409, STALE)
    return order, header, detail(db, current, order)


def touch(db, current, order, header):
    if header is None:
        header = PurchaseOrder(organization_id=current.organization.id, order_id=order.id, revision=1,
            updated_by=current.user.id, updated_at=now_utc())
        db.add(header)
        db.flush()  # Lines reference the header.
    else:
        header.revision += 1
        header.updated_by = current.user.id
        header.updated_at = now_utc()
    return header


def finish(db, current, order, action, before, **extra):
    db.flush()
    result = detail(db, current, order)
    log_audit(db, current, action, payload={'order_id': order.id, 'order_label': f'{order.code}｜{order.title}',
        'before': before, 'after': result, **extra})
    db.commit()
    return result


@router.get('/operations/{order_id}/purchase')
def read(order_id: str, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    return detail(db, current, load_order(db, current, order_id))


@router.put('/operations/{order_id}/purchase/lines')
def save_lines(order_id: str, payload: LinesWrite, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    order, header, before = begin(db, current, order_id, payload.expected_revision)
    if header is not None and header.closed_at is not None:
        raise HTTPException(409, CLOSED)
    org = current.organization.id
    resource_ids = [item.resource_id for item in payload.lines]
    if len(set(resource_ids)) != len(resource_ids):
        raise HTTPException(422, '同一物料在一張採購單只能列一次')
    ids = [item.id for item in payload.lines if item.id]
    if len(set(ids)) != len(ids):
        raise HTTPException(422, '明細識別碼重複')
    existing = {line.id: line for line in db.scalars(select(PurchaseOrderLine).where(PurchaseOrderLine.organization_id == org,
        PurchaseOrderLine.order_id == order.id).with_for_update().execution_options(populate_existing=True))}
    if set(ids) - existing.keys():
        raise HTTPException(409, STALE)
    resources = {row.id: row for row in db.scalars(select(OperationsRecord).where(*visible(current), OperationsRecord.id.in_(resource_ids)))}
    if len(resources) != len(resource_ids):
        raise HTTPException(404, '找不到營運資料')
    if any(row.category != 'resources' for row in resources.values()):
        raise HTTPException(422, '請選擇物料／資源紀錄')
    incoming = {item.id: item for item in payload.lines if item.id}
    used = referenced_lines(db, org, order.id)
    for line in existing.values():
        if line.id not in used:
            continue
        item = incoming.get(line.id)
        if item is None or (item.resource_id, item.unit) != (line.resource_id, line.unit):
            raise HTTPException(409, LOCKED_LINE)
        if int(item.quantity * 1000) < line.received_milli:
            raise HTTPException(409, BELOW)
    stock_units = dict(db.execute(select(InventoryBalance.resource_id, InventoryBalance.unit).where(
        InventoryBalance.organization_id == org, InventoryBalance.resource_id.in_(resource_ids))).all())
    if any(stock_units.get(item.resource_id, item.unit) != item.unit for item in payload.lines):
        raise HTTPException(409, STOCK_UNIT)
    header = touch(db, current, order, header)
    # Lines without ledger references are replaced; referenced lines keep their identity.
    for line in existing.values():
        if line.id not in used:
            db.delete(line)
    db.flush()
    now = now_utc()
    for number, item in enumerate(payload.lines, 1):
        old = existing.get(item.id) if item.id else None
        if old is not None and old.id in used:
            old.line_no, old.ordered_milli, old.note, old.updated_at = number, int(item.quantity * 1000), item.note, now
            continue
        db.add(PurchaseOrderLine(id=str(uuid4()), organization_id=org, order_id=order.id, resource_id=item.resource_id,
            line_no=number, unit=item.unit, ordered_milli=int(item.quantity * 1000), received_milli=0, note=item.note,
            created_by=old.created_by if old else current.user.id, created_at=old.created_at if old else now, updated_at=now))
    return finish(db, current, order, 'purchase.lines', before)


@router.post('/operations/{order_id}/purchase/close')
def close(order_id: str, payload: StateWrite, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    order, header, before = begin(db, current, order_id, payload.expected_revision)
    if header is not None and header.closed_at is not None:
        raise HTTPException(409, CLOSED)
    header = touch(db, current, order, header)
    header.closed_at, header.closed_by, header.close_reason = now_utc(), current.user.id, payload.reason
    return finish(db, current, order, 'purchase.close', before, reason=payload.reason)


@router.post('/operations/{order_id}/purchase/reopen')
def reopen(order_id: str, payload: StateWrite, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    order, header, before = begin(db, current, order_id, payload.expected_revision)
    if header is None or header.closed_at is None:
        raise HTTPException(409, NOT_CLOSED)
    header = touch(db, current, order, header)
    header.closed_at = header.closed_by = header.close_reason = None
    return finish(db, current, order, 'purchase.reopen', before, reason=payload.reason)
