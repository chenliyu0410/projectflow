"""Work order production plan, output progress and manual close/reopen. Managers only, like the stock ledger."""
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.auth import CurrentUser, require_session
from app.database import get_session
from app.models import Organization, InventoryBalance, InventoryMovement, OperationsRecord, User, WorkOrder, now_utc
from app.audit import log_audit
from app.routes.operations import get_record
from app.routes.inventory import authorize, quantity
from app.services.work_order_service import CLOSED, LABELS, classify, started_ids
from app.services.stock_service import issued_by_resource

router = APIRouter(tags=['production'])
STALE = '工單計畫已變更，請重新載入'
LOCKED_PLAN = '已有完工的計畫不可更換成品或單位'
BELOW = '計畫產量不可少於已完工數量'
STOCK_UNIT = '計畫單位須與成品既有庫存單位一致'
NOT_CLOSED = '工單尚未結案'


class PlanWrite(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    expected_revision: int = Field(ge=0)
    product_id: str = Field(min_length=1, max_length=36)
    quantity: Decimal = Field(max_digits=12, decimal_places=3, gt=0, le=999999999, allow_inf_nan=False)
    unit: str = Field(min_length=1, max_length=20)
    note: str = Field(default='', max_length=500)


class StateWrite(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    expected_revision: int = Field(ge=0)
    reason: str = Field(min_length=1, max_length=500)


def load_work(db, current, work_id, lock=False):
    authorize(current)
    work = get_record(db, current, work_id, lock)
    if work.category != 'work':
        raise HTTPException(422, '請選擇工單紀錄')
    return work


def label(db, org, record_id):
    row = db.execute(select(OperationsRecord.code, OperationsRecord.title).where(
        OperationsRecord.organization_id == org, OperationsRecord.id == record_id)).one()
    return {'id': record_id, 'code': row.code, 'title': row.title}


def detail(db, current, work):
    org = current.organization.id
    order = db.get(WorkOrder, (org, work.id))
    planned = order is not None and order.product_id is not None
    closed = order is not None and order.closed_at is not None
    # Net of material returns and reversals; a fully returned material stays listed at zero.
    issued = issued_by_resource(db, org, work.id)
    unlinked = db.scalar(select(func.count()).select_from(InventoryMovement).where(InventoryMovement.organization_id == org,
        InventoryMovement.work_id == work.id, InventoryMovement.kind == 'completion', InventoryMovement.counted_in_plan.is_(False)))
    key = classify(order, bool(started_ids(db, org, [work.id])))
    closer = db.scalar(select(User.display_name).where(User.organization_id == org, User.id == order.closed_by)) if closed else None
    return {'work_id': work.id, 'revision': order.revision if order else 0, 'status': key, 'status_label': LABELS[key],
        'product': label(db, org, order.product_id) if planned else None, 'unit': order.unit if planned else None,
        'planned': quantity(order.planned_milli) if planned else None, 'completed': quantity(order.completed_milli) if planned else None,
        'remaining': quantity(order.planned_milli - order.completed_milli) if planned else None, 'note': order.note if order else '',
        'closed_at': order.closed_at.isoformat() if closed else None, 'closed_by': closer, 'close_reason': order.close_reason if closed else None,
        'unlinked_completions': unlinked,
        'issued': [{'resource_id': row.resource_id, 'code': row.code, 'title': row.title, 'unit': row.unit, 'quantity': quantity(row.total),
            'returned': quantity(row.returned)} for row in issued]}


def begin(db, current, work_id, expected):
    """Lock in the stock ledger's order (company, then document) and reject stale revisions."""
    authorize(current)
    org = current.organization.id
    db.scalar(select(Organization).where(Organization.id == org).with_for_update())
    work = load_work(db, current, work_id, True)
    order = db.scalar(select(WorkOrder).where(WorkOrder.organization_id == org, WorkOrder.work_id == work.id)
        .with_for_update().execution_options(populate_existing=True))
    if (order.revision if order else 0) != expected:
        raise HTTPException(409, STALE)
    return work, order, detail(db, current, work)


def touch(db, current, work, order):
    if order is None:
        order = WorkOrder(organization_id=current.organization.id, work_id=work.id, completed_milli=0, note='', revision=1,
            updated_by=current.user.id, updated_at=now_utc())
        db.add(order)
    else:
        order.revision += 1
        order.updated_by = current.user.id
        order.updated_at = now_utc()
    return order


def finish(db, current, work, action, before, **extra):
    db.flush()
    result = detail(db, current, work)
    log_audit(db, current, action, payload={'work_id': work.id, 'work_label': f'{work.code}｜{work.title}',
        'before': before, 'after': result, **extra})
    db.commit()
    return result


@router.get('/operations/{work_id}/production')
def read(work_id: str, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    return detail(db, current, load_work(db, current, work_id))


@router.put('/operations/{work_id}/production/plan')
def save_plan(work_id: str, payload: PlanWrite, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    work, order, before = begin(db, current, work_id, payload.expected_revision)
    if order is not None and order.closed_at is not None:
        raise HTTPException(409, CLOSED)
    org = current.organization.id
    product = get_record(db, current, payload.product_id)
    if product.category != 'resources':
        raise HTTPException(422, '請選擇物料／資源紀錄作為成品')
    planned = int(payload.quantity * 1000)
    if order is not None and order.completed_milli > 0:
        if (payload.product_id, payload.unit) != (order.product_id, order.unit):
            raise HTTPException(409, LOCKED_PLAN)
        if planned < order.completed_milli:
            raise HTTPException(409, BELOW)
    stock = db.get(InventoryBalance, (org, payload.product_id))
    if stock is not None and stock.unit != payload.unit:
        raise HTTPException(409, STOCK_UNIT)
    order = touch(db, current, work, order)
    order.product_id, order.unit, order.planned_milli, order.note = payload.product_id, payload.unit, planned, payload.note
    return finish(db, current, work, 'production.plan', before)


@router.post('/operations/{work_id}/production/close')
def close(work_id: str, payload: StateWrite, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    work, order, before = begin(db, current, work_id, payload.expected_revision)
    if order is not None and order.closed_at is not None:
        raise HTTPException(409, CLOSED)
    order = touch(db, current, work, order)
    order.closed_at, order.closed_by, order.close_reason = now_utc(), current.user.id, payload.reason
    return finish(db, current, work, 'production.close', before, reason=payload.reason)


@router.post('/operations/{work_id}/production/reopen')
def reopen(work_id: str, payload: StateWrite, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    work, order, before = begin(db, current, work_id, payload.expected_revision)
    if order is None or order.closed_at is None:
        raise HTTPException(409, NOT_CLOSED)
    order = touch(db, current, work, order)
    order.closed_at = order.closed_by = order.close_reason = None
    return finish(db, current, work, 'production.reopen', before, reason=payload.reason)
