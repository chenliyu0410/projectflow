"""Atomic receipts and append-only stock movements. Quantities use integer thousandths."""
from decimal import Decimal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.auth import CurrentUser, require_session
from app.database import get_session
from app.models import Organization, InventoryBalance, InventoryMovement, now_utc
from app.audit import log_audit
from app.routes.operations import can_manage, get_record
from app.services.purchase_service import receipt_line, return_line, reversal_line
from app.services.work_order_service import check_posting, reversal_plan

router = APIRouter(tags=['inventory'])
# Payload quantities are positive for document postings; these kinds take stock out.
OUTGOING = {'return', 'issue'}
REUSED = '同一操作識別碼不可重用於不同內容'
ALREADY_REVERSED = '此筆異動已沖銷'
REVERSAL_FINAL = '沖銷紀錄不可再沖銷，請重新入帳'
NO_STOCK = '庫存不足，無法沖銷'


class StockWrite(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    request_id: UUID
    resource_id: str = Field(min_length=1, max_length=36)
    quantity: Decimal = Field(max_digits=12, decimal_places=3, ge=-999999999, le=999999999, allow_inf_nan=False)
    unit: str = Field(min_length=1, max_length=20)
    reason: str = Field(min_length=1, max_length=500)


class ReversalWrite(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    request_id: UUID
    reason: str = Field(min_length=1, max_length=500)


def authorize(current):
    # Aggregated balances can disclose confidential purchase quantities.
    if not can_manage(current):
        raise HTTPException(403, '庫存與收貨僅限管理者／專案負責人')


def quantity(value):
    return format(Decimal(value) / 1000, '.3f')


def output(row):
    return {**{key: getattr(row, key) for key in ['id', 'request_id', 'resource_id', 'order_id', 'work_id', 'work_label', 'line_id', 'counted_in_plan', 'reversal_of', 'kind', 'unit',
        'resource_label', 'order_label', 'reason', 'actor_name']},
        'quantity': quantity(row.delta_milli), 'before': quantity(row.before_milli), 'after': quantity(row.after_milli),
        'created_at': row.created_at.isoformat()}


@router.get('/inventory/resources/{resource_id}')
def balance(resource_id: str, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    authorize(current)
    resource = get_record(db, current, resource_id)
    if resource.category != 'resources':
        raise HTTPException(422, '請選擇物料／資源紀錄')
    row = db.get(InventoryBalance, (current.organization.id, resource_id))
    return {'resource_id': resource_id, 'quantity': quantity(row.quantity_milli if row else 0), 'unit': row.unit if row else None}


@router.get('/inventory/movements')
def movements(resource_id: str | None = None, order_id: str | None = None, work_id: str | None = None,
              offset: int = Query(0, ge=0), limit: int = Query(30, ge=1, le=100),
              current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    authorize(current)
    filters = [InventoryMovement.organization_id == current.organization.id]
    for record_id, column, category in [(resource_id, InventoryMovement.resource_id, 'resources'), (order_id, InventoryMovement.order_id, 'orders'), (work_id, InventoryMovement.work_id, 'work')]:
        if record_id is not None:
            record = get_record(db, current, record_id)
            if record.category != category:
                raise HTTPException(422, '無效的紀錄分類')
            filters.append(column == record_id)
    total = db.scalar(select(func.count()).select_from(InventoryMovement).where(*filters))
    rows = db.scalars(select(InventoryMovement).where(*filters).order_by(InventoryMovement.created_at.desc(), InventoryMovement.id.desc()).offset(offset).limit(limit)).all()
    org = current.organization.id
    # Entries show whether they were reversed, and reversals show what they cancelled.
    reversed_by = dict(db.execute(select(InventoryMovement.reversal_of, InventoryMovement.id).where(InventoryMovement.organization_id == org,
        InventoryMovement.reversal_of.in_([row.id for row in rows]))).all())
    reversed_kind = dict(db.execute(select(InventoryMovement.id, InventoryMovement.kind).where(InventoryMovement.organization_id == org,
        InventoryMovement.id.in_([row.reversal_of for row in rows if row.reversal_of]))).all())
    return {'items': [{**output(row), 'reversed_by': reversed_by.get(row.id), 'reversed_kind': reversed_kind.get(row.reversal_of)} for row in rows],
        'total': total, 'offset': offset, 'limit': limit}


def post(db, current, payload, kind, *, order_id=None, work_id=None):
    authorize(current)
    delta = int(payload.quantity * 1000)
    if delta == 0 or (kind != 'adjustment' and delta < 0):
        raise HTTPException(422, '收貨數量須為正數，調整數量不可為零')
    if kind in OUTGOING:
        delta = -delta
    org = current.organization.id
    # Same lock order for every posting, including first balance creation and retries.
    db.scalar(select(Organization).where(Organization.id == org).with_for_update())
    resource = get_record(db, current, payload.resource_id, True)
    order = get_record(db, current, order_id, True) if order_id is not None else None
    work = get_record(db, current, work_id, True) if work_id else None
    if work and work.category != 'work':
        raise HTTPException(422, '請選擇工單紀錄')
    if resource.category != 'resources' or (order and order.category != 'orders'):
        raise HTTPException(422, '請使用採購紀錄與物料／資源紀錄')
    previous = db.scalar(select(InventoryMovement).where(InventoryMovement.organization_id == org, InventoryMovement.request_id == str(payload.request_id)))
    if previous:
        if (previous.resource_id, previous.order_id, previous.work_id, previous.kind, previous.delta_milli, previous.unit, previous.reason) != (payload.resource_id, order_id, work_id, kind, delta, payload.unit, payload.reason):
            raise HTTPException(409, REUSED)
        result = output(previous)
        db.commit()
        return result
    # Orders with lines only accept listed items up to the ordered quantity, and return at most what was received;
    # older orders keep free receipts.
    line = None if not order else receipt_line(db, org, order.id, resource.id, payload.unit, delta) if kind == 'receipt' \
        else return_line(db, org, order.id, resource.id, payload.unit, delta)
    # Planned work orders only complete their product up to the planned output; closed ones refuse any posting.
    plan = check_posting(db, org, work.id, kind, resource.id, payload.unit, delta) if work else None
    stock = db.get(InventoryBalance, (org, resource.id))
    if stock and stock.unit != payload.unit:
        raise HTTPException(409, '庫存單位不一致，請使用既有單位')
    before = stock.quantity_milli if stock else 0
    after = before + delta
    if after < 0 or after > 999999999999:
        raise HTTPException(409, '庫存不足或超出可保存範圍')
    if stock is None:
        stock = InventoryBalance(organization_id=org, resource_id=resource.id, unit=payload.unit, quantity_milli=after)
        db.add(stock)
    else:
        stock.quantity_milli = after
    row = InventoryMovement(organization_id=org, request_id=str(payload.request_id), resource_id=resource.id,
        order_id=order_id, work_id=work_id, work_label=f'{work.code}｜{work.title}' if work else None,
        line_id=line.id if line else None, counted_in_plan=plan is not None, kind=kind, unit=payload.unit,
        delta_milli=delta, before_milli=before, after_milli=after, resource_label=f'{resource.code}｜{resource.title}',
        order_label=f'{order.code}｜{order.title}' if order else None, reason=payload.reason,
        created_by=current.user.id, actor_name=current.user.display_name)
    if line:
        line.received_milli += delta
        line.updated_at = now_utc()
    if plan:
        plan.completed_milli += delta
        plan.updated_at = now_utc()
    db.add(row); db.flush()
    result = output(row)
    log_audit(db, current, 'inventory.' + row.kind, payload=result)
    db.commit()
    return result


@router.post('/operations/{order_id}/receipts')
def receipt(order_id: str, payload: StockWrite, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    return post(db, current, payload, 'receipt', order_id=order_id)


@router.post('/operations/{order_id}/returns')
def purchase_return(order_id: str, payload: StockWrite, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    return post(db, current, payload, 'return', order_id=order_id)


@router.post('/inventory/adjustments')
def adjustment(payload: StockWrite, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    return post(db, current, payload, 'adjustment')


@router.post('/operations/{work_id}/issues')
def issue(work_id: str, payload: StockWrite, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    return post(db, current, payload, 'issue', work_id=work_id)


@router.post('/operations/{work_id}/issue-returns')
def issue_return(work_id: str, payload: StockWrite, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    return post(db, current, payload, 'issue_return', work_id=work_id)


@router.post('/operations/{work_id}/completions')
def completion(work_id: str, payload: StockWrite, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    return post(db, current, payload, 'completion', work_id=work_id)


@router.post('/inventory/movements/{movement_id}/reversal')
def reversal(movement_id: str, payload: ReversalWrite, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    """Cancel one entry with an opposite entry linked to it; the original is never changed."""
    authorize(current)
    org = current.organization.id
    db.scalar(select(Organization).where(Organization.id == org).with_for_update())
    original = db.scalar(select(InventoryMovement).where(InventoryMovement.organization_id == org, InventoryMovement.id == movement_id))
    if original is None:
        raise HTTPException(404, '找不到異動紀錄')
    # The entry's material and document must still be visible to the caller.
    resource = get_record(db, current, original.resource_id, True)
    order = get_record(db, current, original.order_id, True) if original.order_id else None
    work = get_record(db, current, original.work_id, True) if original.work_id else None
    previous = db.scalar(select(InventoryMovement).where(InventoryMovement.organization_id == org, InventoryMovement.request_id == str(payload.request_id)))
    if previous:
        if (previous.kind, previous.reversal_of, previous.reason) != ('reversal', original.id, payload.reason):
            raise HTTPException(409, REUSED)
        result = output(previous)
        db.commit()
        return result
    if original.kind == 'reversal':
        raise HTTPException(409, REVERSAL_FINAL)
    if db.scalar(select(InventoryMovement.id).where(InventoryMovement.organization_id == org, InventoryMovement.reversal_of == original.id)):
        raise HTTPException(409, ALREADY_REVERSED)
    delta = -original.delta_milli
    line = reversal_line(db, org, original, delta) if order else None
    plan = reversal_plan(db, org, original, delta) if work else None
    stock = db.get(InventoryBalance, (org, resource.id))
    before = stock.quantity_milli if stock else 0
    after = before + delta
    if stock is None or after < 0:
        raise HTTPException(409, NO_STOCK)
    if after > 999999999999:
        raise HTTPException(409, '庫存不足或超出可保存範圍')
    stock.quantity_milli = after
    row = InventoryMovement(organization_id=org, request_id=str(payload.request_id), resource_id=resource.id,
        order_id=original.order_id, work_id=original.work_id, work_label=f'{work.code}｜{work.title}' if work else None,
        line_id=original.line_id, counted_in_plan=original.counted_in_plan, reversal_of=original.id, kind='reversal', unit=original.unit,
        delta_milli=delta, before_milli=before, after_milli=after, resource_label=f'{resource.code}｜{resource.title}',
        order_label=f'{order.code}｜{order.title}' if order else None, reason=payload.reason,
        created_by=current.user.id, actor_name=current.user.display_name)
    if line:
        line.received_milli += delta
        line.updated_at = now_utc()
    if plan:
        plan.completed_milli += delta
        plan.updated_at = now_utc()
    db.add(row); db.flush()
    result = output(row)
    log_audit(db, current, 'inventory.reversal', payload={**result, 'reversed_kind': original.kind})
    db.commit()
    return result
