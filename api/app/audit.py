from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.models import AuditLog


def log_audit(db: Session, current: CurrentUser, action: str, node_id: str | None = None, payload: dict | None = None) -> AuditLog:
    entry = AuditLog(
        organization_id=current.organization.id,
        actor_user_id=current.user.id,
        node_id=node_id,
        action=action,
        payload=payload or {},
    )
    db.add(entry)
    return entry
