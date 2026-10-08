from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import Organization, SessionToken, User

COOKIE_NAME = "pf_session"
SESSION_DAYS = 7


@dataclass(frozen=True)
class CurrentUser:
    user: User
    organization: Organization
    token: str


def session_expires_at() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)


def require_session(request: Request, db: Session = Depends(get_session)) -> CurrentUser:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="請先登入")
    row = db.execute(
        select(SessionToken, User, Organization)
        .join(User, (SessionToken.organization_id == User.organization_id) & (SessionToken.user_id == User.id))
        .join(Organization, SessionToken.organization_id == Organization.id)
        .where(SessionToken.token == token, SessionToken.expires_at > datetime.now(timezone.utc))
    ).first()
    if row is None:
        raise HTTPException(status_code=401, detail="請先登入")
    _, user, organization = row
    return CurrentUser(user=user, organization=organization, token=token)
