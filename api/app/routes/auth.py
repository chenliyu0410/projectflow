from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.auth import COOKIE_NAME, CurrentUser, require_session, session_expires_at
from app.database import get_session
from app.models import Organization, SessionToken, User
from app.schemas import LoginRequest, LoginResponse, MeResponse, OrganizationOut, UserOut
from app.security import new_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


def login_body(user: User, organization: Organization) -> LoginResponse:
    return LoginResponse(
        user=UserOut(id=user.id, username=user.username, display_name=user.display_name, role=user.role),
        organization=OrganizationOut(id=organization.id, key=organization.key, name=organization.name),
    )


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_session)):
    row = db.execute(
        select(User, Organization)
        .join(Organization, User.organization_id == Organization.id)
        .where(Organization.key == payload.organization_key, User.username == payload.username)
    ).first()
    if row is None:
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")
    user, organization = row
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")
    token = new_token()
    db.add(SessionToken(token=token, user_id=user.id, organization_id=organization.id, expires_at=session_expires_at()))
    db.commit()
    response.set_cookie(COOKIE_NAME, token, httponly=True, samesite="lax", max_age=7 * 24 * 60 * 60)
    return login_body(user, organization)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    db.execute(delete(SessionToken).where(SessionToken.token == current.token))
    db.commit()
    response.delete_cookie(COOKIE_NAME)
    return None


@router.get("/me", response_model=MeResponse)
def me(current: CurrentUser = Depends(require_session)):
    return login_body(current.user, current.organization)
