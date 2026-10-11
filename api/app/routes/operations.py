"""Company-scoped operations data maintenance, with record-level confidentiality."""
import json
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import CurrentUser, require_session
from app.database import get_session
from app.models import OperationsRecord, User, now_utc
from app.audit import log_audit
from app.services.purchase_service import summaries

router = APIRouter(tags=['operations'])
CATALOG = json.loads((Path(__file__).parents[1] / 'operations_catalog.json').read_text(encoding='utf-8'))
CATEGORIES = {'partners', 'resources', 'orders', 'work', 'formulas', 'batches'}


def can_manage(current):
    return current.user.role in {'admin', 'project_owner'}


def visible(current):
    clauses = [OperationsRecord.organization_id == current.organization.id]
    if not can_manage(current):
        clauses.append(OperationsRecord.visibility == 'internal')
    return clauses


class RecordField(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    label: str = Field(min_length=1, max_length=80)
    value: str = Field(max_length=4000)


class RecordWrite(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    category: Literal['partners', 'resources', 'orders', 'work', 'formulas', 'batches']
    code: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=200)
    status: str = Field(min_length=1, max_length=80)
    visibility: Literal['internal', 'restricted'] = 'internal'
    fields: list[RecordField] = Field(default_factory=list, max_length=40)

    @field_validator('code')
    @classmethod
    def normalize_code(cls, value):
        return value.upper()

    @field_validator('fields')
    @classmethod
    def unique_labels(cls, values):
        if len({v.label for v in values}) != len(values):
            raise ValueError('欄位名稱不可重複')
        return values


class RecordUpdate(RecordWrite):
    expected_revision: int = Field(ge=1)


def output(db, row):
    users = {u.id: u.display_name for u in db.scalars(select(User).where(User.organization_id == row.organization_id,
        User.id.in_([row.created_by, row.updated_by])))}
    return {**{key: getattr(row, key) for key in ['id', 'category', 'code', 'title', 'status', 'visibility', 'fields', 'source', 'revision']},
        'created_at': row.created_at.isoformat(), 'updated_at': row.updated_at.isoformat(),
        'created_by': users.get(row.created_by, '使用者'), 'updated_by': users.get(row.updated_by, '使用者')}


@router.get('/operations/catalog')
def catalog(current: CurrentUser = Depends(require_session)):
    groups = CATALOG.get(current.organization.key, CATALOG['food'])
    return {'categories': [{k: group[k] for k in ['key', 'label', 'fields']} for group in groups], 'can_manage': can_manage(current)}


@router.get('/operations')
def listing(category: str = Query('partners', max_length=32), q: str = Query('', max_length=100),
            offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100),
            current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    if category not in CATEGORIES:
        raise HTTPException(422, '無效的資料分類')
    filters = [*visible(current), OperationsRecord.category == category]
    if q.strip():
        filters.append(or_(OperationsRecord.code.contains(q.strip().upper(), autoescape=True), OperationsRecord.title.contains(q.strip(), autoescape=True)))
    total = db.scalar(select(func.count()).select_from(OperationsRecord).where(*filters))
    rows = db.scalars(select(OperationsRecord).where(*filters).order_by(OperationsRecord.code, OperationsRecord.id).offset(offset).limit(limit)).all()
    # Receiving progress follows the stock ledger's manager-only rule.
    receiving = summaries(db, current.organization.id, [row.id for row in rows]) if category == 'orders' and can_manage(current) else {}
    return {'items': [{**output(db, row), **({'receiving': receiving[row.id]} if row.id in receiving else {})} for row in rows],
        'total': total, 'offset': offset, 'limit': limit}


def get_record(db, current, record_id, lock=False):
    query = select(OperationsRecord).where(*visible(current), OperationsRecord.id == record_id)
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    row = db.scalar(query)
    if row is None:
        raise HTTPException(404, '找不到營運資料')
    return row


@router.get('/operations/{record_id}')
def detail(record_id: str, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    return output(db, get_record(db, current, record_id))


def save(db, current, payload, record_id=None, *, source='native'):
    if not can_manage(current):
        raise HTTPException(403, '沒有管理營運資料的權限')
    row = get_record(db, current, record_id, True) if record_id else None
    if row and row.revision != payload.expected_revision:
        raise HTTPException(409, '營運資料已變更，請重新載入')
    if row and row.category != payload.category:
        raise HTTPException(422, '既有紀錄不可變更分類')
    before = output(db, row) if row else None
    values = payload.model_dump(exclude={'expected_revision'})
    if row is None:
        row = OperationsRecord(organization_id=current.organization.id, source=source,
            created_by=current.user.id, updated_by=current.user.id, **values)
        db.add(row)
    else:
        for key, value in values.items():
            setattr(row, key, value)
        row.updated_by = current.user.id
        row.updated_at = now_utc()
        row.revision += 1
    try:
        db.flush()
        result = output(db, row)
        log_audit(db, current, 'operations.update' if before else 'operations.create',
            payload={'record_id': row.id, 'before': before, 'after': result})
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, '代碼重複或資料已變更，請重新確認') from None
    return result


@router.post('/operations', status_code=201)
def create(payload: RecordWrite, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    return save(db, current, payload)


@router.put('/operations/{record_id}')
def update(record_id: str, payload: RecordUpdate, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    return save(db, current, payload, record_id)
