from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import CurrentUser, require_session
from app.database import get_session
from app.models import AuditLog, User

router = APIRouter(tags=["audit"])


@router.get("/audit-logs")
def list_audit_logs(current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    rows = db.execute(
        select(AuditLog, User.username)
        .join(User, (AuditLog.organization_id == User.organization_id) & (AuditLog.actor_user_id == User.id))
        .where(AuditLog.organization_id == current.organization.id)
        .order_by(AuditLog.created_at.desc())
        .limit(50)
    ).all()
    return {
        "items": [
            {
                "id": log.id,
                "organization_key": current.organization.key,
                "action": log.action,
                "node_id": log.node_id,
                "actor_username": username,
                "payload": log.payload,
                "created_at": log.created_at.isoformat(),
            }
            for log, username in rows
        ]
    }
