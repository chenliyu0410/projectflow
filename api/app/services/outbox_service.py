"""Mail outbox for n8n: events are queued with the change that caused them and pulled by n8n to send."""
import html
import os
from datetime import timedelta

from sqlalchemy import or_, select

from app.models import OutboxEvent, User, now_utc

MAX_ATTEMPTS = 5
# A pulled event is not offered again until this passes, so a slow send is not duplicated.
LEASE = timedelta(minutes=5)


def site_url():
    return os.environ.get('PF_PUBLIC_URL', 'http://127.0.0.1:15173').rstrip('/')


def enqueue(db, organization_id, kind, recipient_id, subject, text, dedupe_key):
    """Queue one mail; the same dedupe key in one organization is only ever queued once."""
    if db.scalar(select(OutboxEvent.id).where(OutboxEvent.organization_id == organization_id, OutboxEvent.dedupe_key == dedupe_key)):
        return None
    url = site_url()
    body = '<p>' + html.escape(text).replace('\n', '<br>') + f'</p><p><a href="{html.escape(url)}">在專流開啟</a></p>'
    event = OutboxEvent(organization_id=organization_id, kind=kind, recipient_id=recipient_id, subject=subject[:300],
                        body_text=f'{text}\n\n在專流開啟：{url}', body_html=body, dedupe_key=dedupe_key[:200])
    db.add(event)
    return event


def deliverable(user):
    return user is not None and user.status == 'active' and bool(user.email) and user.email_notify


def pull(db, limit):
    """Pending events with a deliverable recipient; the rest are marked skipped so they are not retried."""
    rows = db.execute(select(OutboxEvent, User)
                      .join(User, (User.organization_id == OutboxEvent.organization_id) & (User.id == OutboxEvent.recipient_id))
                      .where(OutboxEvent.status == 'pending', or_(OutboxEvent.claimed_at.is_(None), OutboxEvent.claimed_at < now_utc() - LEASE))
                      .order_by(OutboxEvent.created_at, OutboxEvent.id).limit(limit)).all()
    items = []
    for event, user in rows:
        if not deliverable(user):
            event.status = 'skipped'
            continue
        event.claimed_at = now_utc()
        items.append({'id': event.id, 'kind': event.kind, 'to': user.email, 'name': user.display_name,
                      'subject': event.subject, 'text': event.body_text, 'html': event.body_html})
    return items


def record_result(db, event_id, ok, error=None):
    event = db.get(OutboxEvent, event_id)
    if event is None:
        return None
    if event.status != 'pending':
        return event
    if ok:
        event.status, event.sent_at = 'sent', now_utc()
    else:
        event.attempts += 1
        event.claimed_at = None  # a reported failure may be retried on the next pull
        event.last_error = (error or '寄送失敗')[:500]
        if event.attempts >= MAX_ATTEMPTS:
            event.status = 'failed'
    return event


def retry(db, event):
    """Admin resend of a failed event: back to pending with a fresh attempt count."""
    event.status, event.attempts, event.claimed_at, event.last_error = 'pending', 0, None, None
    return event
