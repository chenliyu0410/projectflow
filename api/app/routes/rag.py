"""Formal document RAG; demo AI remains a separate API and dataset."""
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import CurrentUser, require_session
from app.database import get_session
from app.audit import log_audit
from app.ai.model import validate_endpoint
from app.routes.ai import local_admin, local_request
from app.rag import service
from app.rag.contracts import Ask, Revalidate
from app.rag.models import RagQuery, RagSettings

router = APIRouter(prefix='/rag', tags=['formal-rag'])


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Enabled(Strict):
    enabled: bool


class Feedback(Strict):
    rating: Literal['helpful', 'unhelpful']


class ModelConfig(Strict):
    enabled: bool = False
    base_url: str = Field(default='', max_length=200)
    model: str = Field(default='', max_length=120, pattern=r'^[a-zA-Z0-9._:/-]*$')
    embedding_model: str = Field(default='', max_length=120, pattern=r'^[a-zA-Z0-9._:/-]*$')


@router.get('/status')
def status(request: Request, project_id: str | None = None, scope_kind: Literal['project','all_visible'] | None = None, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    if scope_kind == 'all_visible' and project_id or scope_kind == 'project' and not project_id:
        raise HTTPException(422, '範圍格式不正確')
    result = service.status(db, current, project_id, scope_kind)
    result['can_configure'] = current.user.role == 'admin' and local_request(request)
    return result


@router.post('/documents/{document_id}/index')
def index(document_id: str, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    return service.index_document(db, current, document_id)


@router.put('/documents/{document_id}/enabled')
def enabled(document_id: str, payload: Enabled, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    return service.set_enabled(db, current, document_id, payload.enabled)


@router.post('/ask')
def ask(payload: Ask, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    if not payload.question.strip():
        raise HTTPException(422, '請輸入問題')
    scope = payload.resolved_scope()
    return service.ask(db, current, scope.get('project_id'), payload.question.strip(), payload.previous_question, scope=scope, history=[t.model_dump() for t in payload.history])


@router.get('/queries/{query_id}/sources/{source_id}')
def source(query_id: str, source_id: str, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    return service.source_text(db, current, query_id, source_id)


@router.put('/queries/{query_id}/feedback')
def feedback(query_id: str, payload: Feedback, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    row = service.own_query(db, current, query_id)
    row.rating = payload.rating
    db.commit()
    return {'ok': True}


@router.get('/model')
def model(request: Request, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    local_admin(request, current)
    return service.settings(db, current.organization.id)


@router.put('/model')
def configure(payload: ModelConfig, request: Request, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    local_admin(request, current)
    values = payload.model_dump()
    try:
        if values['base_url']:
            values['base_url'] = validate_endpoint(values['base_url'])
        if values['enabled'] and (not values['base_url'] or not (values['model'] or values['embedding_model'])):
            raise ValueError()
        if any('cloud' in values[key].lower() for key in ('model', 'embedding_model')):
            raise ValueError()
    except ValueError:
        raise HTTPException(422, '請使用內網位址與已安裝的本機模型') from None
    row = db.get(RagSettings, current.organization.id)
    if row is None:
        row = RagSettings(organization_id=current.organization.id, revision=1, **values)
        db.add(row)
    else:
        for key, value in values.items():
            setattr(row, key, value)
        row.revision += 1
    log_audit(db, current, 'rag.model.configure', payload={'enabled': values['enabled']})
    db.commit()
    return {'ok': True}


@router.get('/metrics')
def metrics(current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    if current.user.role != 'admin':
        raise HTTPException(403, '僅管理者可查看統計')
    scope = RagQuery.organization_id == current.organization.id
    total = db.scalar(select(func.count()).select_from(RagQuery).where(scope))
    rows = db.scalars(select(RagQuery).where(scope).order_by(RagQuery.created_at.desc()).limit(1000)).all()
    durations = sorted(r.trace['duration_ms'] for r in rows if isinstance(r.trace.get('duration_ms'), (int, float)))
    def percentile(p):
        return durations[min(len(durations) - 1, int((len(durations) - 1) * p))] if durations else None
    return dict(query_count=total, sample_count=len(rows), sample_limit=1000,
        helpful=sum(r.rating == 'helpful' for r in rows), unhelpful=sum(r.rating == 'unhelpful' for r in rows),
        degraded=sum(r.trace.get('outcome') == 'degraded' for r in rows),
        no_sources=sum(r.trace.get('kind') == 'no_sources' for r in rows),
        p50_ms=percentile(.5), p95_ms=percentile(.95), cost=None, input_tokens=None, output_tokens=None)


@router.post('/queries/revalidate')
def revalidate(payload: Revalidate, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    return service.revalidate(db, current, payload.query_ids)
