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
from app.services.purchase_service import receipt_line
from app.services.work_order_service import check_posting

router = APIRouter(tags=['inventory'])


class StockWrite(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    request_id: UUID
    resource_id: str = Field(min_length=1, max_length=36)
    quantity: Decimal = Field(max_digits=12, decimal_places=3, ge=-999999999, le=999999999, allow_inf_nan=False)
    unit: str = Field(min_length=1, max_length=20)
    reason: str = Field(min_length=1, max_length=500)


def authorize(current):
    # Aggregated balances can disclose confidential purchase quantities.
    if not can_manage(current):
        raise HTTPException(403, '庫存與收貨僅限管理者／專案負責人')


def quantity(value):
    return format(Decimal(value) / 1000, '.3f')


def output(row):
    return {**{key: getattr(row, key) for key in ['id', 'request_id', 'resource_id', 'order_id', 'work_id', 'work_label', 'line_id', 'counted_in_plan', 'kind', 'unit',
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
    return {'items': [output(row) for row in rows], 'total': total, 'offset': offset, 'limit': limit}


def post(db, current, payload, order_id=None, *, work_id=None, work_kind=None):
    authorize(current)
    delta = int(payload.quantity * 1000)
    if delta == 0 or ((order_id is not None or work_id is not None) and delta < 0):
        raise HTTPException(422, '收貨數量須為正數，調整數量不可為零')
    kind = work_kind if work_id else 'receipt' if order_id else 'adjustment'
    if kind == 'issue':
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
            raise HTTPException(409, '同一操作識別碼不可重用於不同內容')
        result = output(previous)
        db.commit()
        return result
    # Orders with lines only accept listed items up to the ordered quantity; older orders keep free receipts.
    line = receipt_line(db, org, order.id, resource.id, payload.unit, delta) if order else None
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
    return post(db, current, payload, order_id)


@router.post('/inventory/adjustments')
def adjustment(payload: StockWrite, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    return post(db, current, payload)


@router.post('/operations/{work_id}/issues')
def issue(work_id: str, payload: StockWrite, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    return post(db, current, payload, work_id=work_id, work_kind='issue')


@router.post('/operations/{work_id}/completions')
def completion(work_id: str, payload: StockWrite, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    return post(db, current, payload, work_id=work_id, work_kind='completion')
