"""Mail settings in the app: each user's own email and switch; admins see failed deliveries and can resend them."""
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import log_audit
from app.auth import CurrentUser, require_session
from app.database import get_session
from app.models import OutboxEvent, User
from app.services import outbox_service

router = APIRouter(tags=['mail'])
EMAIL = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


class EmailSettings(BaseModel):
    email: str | None = Field(default=None, max_length=254)
    email_notify: bool


def require_admin(current):
    if current.user.role != 'admin':
        raise HTTPException(403, '只有系統管理員可以查看寄送狀態')


@router.get('/accounts/me/email')
def my_email(current: CurrentUser = Depends(require_session)):
    return {'email': current.user.email, 'email_notify': current.user.email_notify}


@router.patch('/accounts/me/email')
def update_my_email(payload: EmailSettings, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    email = (payload.email or '').strip() or None
    if email is not None and not EMAIL.fullmatch(email):
        raise HTTPException(422, 'Email 格式不正確')
    user = db.get(User, current.user.id)
    changed = email != user.email
    user.email, user.email_notify = email, payload.email_notify
    # The address itself stays out of the audit log; only that it changed is recorded.
    log_audit(db, current, 'account.email_update', payload={'email_changed': changed, 'email_notify': payload.email_notify})
    db.commit()
    return {'email': user.email, 'email_notify': user.email_notify}


@router.get('/mail/failed')
def failed(current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    require_admin(current)
    rows = db.execute(select(OutboxEvent, User).join(User, (User.organization_id == OutboxEvent.organization_id) & (User.id == OutboxEvent.recipient_id))
                      .where(OutboxEvent.organization_id == current.organization.id, OutboxEvent.status == 'failed')
                      .order_by(OutboxEvent.created_at.desc()).limit(100)).all()
    return {'items': [{'id': e.id, 'subject': e.subject, 'recipient': u.display_name, 'attempts': e.attempts,
                       'last_error': e.last_error, 'created_at': e.created_at.isoformat()} for e, u in rows]}


@router.post('/mail/{event_id}/retry')
def retry(event_id: str, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    require_admin(current)
    event = db.scalar(select(OutboxEvent).where(OutboxEvent.id == event_id, OutboxEvent.organization_id == current.organization.id))
    if event is None:
        raise HTTPException(404, '找不到寄送紀錄')
    if event.status != 'failed':
        raise HTTPException(409, '只有寄送失敗的信可以重寄')
    outbox_service.retry(db, event)
    log_audit(db, current, 'mail.retry', payload={'event_id': event.id, 'kind': event.kind})
    db.commit()
    return {'status': event.status}
