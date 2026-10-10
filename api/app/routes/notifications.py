from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.auth import CurrentUser, require_session
from app.database import get_session
from app.models import Notification, Node, now_utc
from app.permissions import can_view_node
from app.services.record_policy import load_policy_context
router = APIRouter(prefix='/notifications', tags=['notifications'])


def visible_rows(db, current):
    context = load_policy_context(db, current)
    rows = db.execute(select(Notification, Node).join(Node, (Node.id == Notification.node_id) & (Node.organization_id == Notification.organization_id)).where(Notification.organization_id == current.organization.id, Notification.recipient_id == current.user.id).order_by(Notification.created_at.desc(), Notification.id.desc()))
    return [(r,n) for r,n in rows if can_view_node(current,n,context=context)]

@router.get('')
def listing(offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100), current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    rows = visible_rows(db,current)
    return {'items': [{'id':r.id,'message':r.message,'node_title':n.title,'node_id':n.id,'project_id':n.project_id,'created_at':r.created_at.isoformat(),'read':r.read_at is not None} for r,n in rows[offset:offset+limit]], 'unread_count': sum(r.read_at is None for r,n in rows), 'next_offset': offset+limit if offset+limit < len(rows) else None}

@router.post('/{notification_id}/read')
def mark(notification_id: str, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    row = next((r for r,n in visible_rows(db,current) if r.id == notification_id), None)
    if row is None: raise HTTPException(404, '找不到通知')
    row.read_at = row.read_at or now_utc()
    db.commit()
    return {'read': True}
