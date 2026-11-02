"""n8n-only API (Bearer PF_N8N_TOKEN): pull mail, report delivery, trigger weekly drafts and daily digests."""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.database import get_session
from app.integration_auth import require_integration
from app.models import Organization, Project, User
from app.services import daily_digest_service, outbox_service, weekly_report_service

router = APIRouter(prefix='/integrations', tags=['integrations'], dependencies=[Depends(require_integration)])


class DeliveryResult(BaseModel):
    ok: bool
    error: str | None = Field(default=None, max_length=2000)


class GenerateRequest(BaseModel):
    project_ids: list[str] | None = None


@router.get('/events')
def events(limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_session)):
    items = outbox_service.pull(db, limit)
    db.commit()
    return {'items': items}


@router.post('/events/{event_id}/result')
def result(event_id: str, payload: DeliveryResult, db: Session = Depends(get_session)):
    event = outbox_service.record_result(db, event_id, payload.ok, payload.error)
    if event is None:
        raise HTTPException(404, '找不到事件')
    db.commit()
    return {'status': event.status, 'attempts': event.attempts}


@router.post('/weekly-reports/generate')
def generate(payload: GenerateRequest, db: Session = Depends(get_session)):
    query = select(Project, Organization, User).join(Organization, Organization.id == Project.organization_id) \
        .join(User, (User.organization_id == Project.organization_id) & (User.id == Project.owner_user_id))
    if payload.project_ids is not None:
        query = query.where(Project.id.in_(payload.project_ids))
    generated, skipped_sent, kept_draft = 0, 0, 0
    for project, organization, owner in db.execute(query.order_by(Project.id)).all():
        try:
            # n8n has no user of its own: the project owner is recorded as the author, with via=n8n in the audit.
            report = weekly_report_service.generate(db, organization, project, CurrentUser(owner, organization, ''), via='n8n')
            db.commit()
            if report is None:
                kept_draft += 1
            else:
                generated += 1
        except HTTPException as exc:
            db.rollback()
            if exc.status_code != 409:
                raise
            skipped_sent += 1
    return {'generated': generated, 'skipped_sent': skipped_sent, 'kept_draft': kept_draft}


@router.post('/daily-digest')
def daily_digest(db: Session = Depends(get_session)):
    queued = daily_digest_service.enqueue_all(db)
    db.commit()
    return {'enqueued': queued}


@router.post('/inbox/scan')
def inbox_scan(db: Session = Depends(get_session)):
    # A plain def runs in FastAPI's thread pool, so parsing and OCR never stall other requests.
    from app.services import inbox_service
    return inbox_service.scan_sync(db)


@router.post('/maintenance/backup')
def maintenance_backup(db: Session = Depends(get_session)):
    from app.services import maintenance_service
    return maintenance_service.backup(db)


@router.post('/maintenance/expiry')
def maintenance_expiry(db: Session = Depends(get_session)):
    from app.services import maintenance_service
    return maintenance_service.expiry(db)
