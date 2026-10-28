from fastapi import APIRouter, Depends, HTTPException, Response, Request, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.auth import COOKIE_NAME, CurrentUser, require_session, session_expires_at
from app.database import get_session
from app.models import Organization, SessionToken, User
from app.schemas import LoginRequest, LoginResponse, MeResponse, OrganizationOut, UserOut, ShowcaseSwitch
from app import showcase
from app.audit import log_audit
from app.security import new_token, verify_password
from app.services import account_service
from app.models import now_utc

router = APIRouter(prefix="/auth", tags=["auth"])


def set_session_cookie(response: Response, request: Request, token: str) -> None:
    # 公開模式由 nginx 81 帶 X-Forwarded-Proto: https，uvicorn 採信後 scheme 才是 https；本機 http 不能設 Secure，否則登不進去。
    response.set_cookie(COOKIE_NAME, token, httponly=True, samesite="lax", secure=request.url.scheme == "https",
                        max_age=7 * 24 * 60 * 60)


def login_body(user: User, organization: Organization, request: Request) -> LoginResponse:
    return LoginResponse(
        user=UserOut(id=user.id, username=user.username, display_name=user.display_name, role=user.role,
                     must_change_password=True if user.must_change_password else None),
        organization=OrganizationOut(id=organization.id, key=organization.key, name=organization.name),
        showcase={"active": showcase.dedicated(user, organization), "companies": showcase.COMPANIES} if showcase.available(user, organization, request) else None,
    )


@router.post("/login", response_model=LoginResponse, response_model_exclude_none=True)
def login(payload: LoginRequest, response: Response, request: Request, db: Session = Depends(get_session)):
    account_service.check_rate(request, payload.organization_key, payload.username)
    row = db.execute(
        select(User, Organization)
        .join(Organization, User.organization_id == Organization.id)
        .where(Organization.key == payload.organization_key, User.username == payload.username)
    ).first()
    # Unknown accounts still pay for one hash check, so response time does not reveal which usernames exist.
    valid = verify_password(payload.password, row[0].password_hash if row else account_service.DUMMY_HASH)
    if row is None or row[0].status != 'active' or not valid:
        account_service.record_failure(request, payload.organization_key, payload.username)
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")
    user, organization = row
    if account_service.is_demo_password(user, payload.password) and account_service.demo_blocked(request):
        raise HTTPException(status_code=403, detail="示範密碼不能從公開網址登入，請管理者先重設密碼")
    user.last_login_at = now_utc()
    token = new_token()
    db.add(SessionToken(token=token, user_id=user.id, organization_id=organization.id, expires_at=session_expires_at()))
    db.commit()
    set_session_cookie(response, request, token)
    return login_body(user, organization, request)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response, request: Request, current: CurrentUser = Depends(require_session),
           db: Session = Depends(get_session)):
    db.execute(delete(SessionToken).where(SessionToken.token == current.token))
    db.commit()
    response.delete_cookie(COOKIE_NAME, httponly=True, samesite="lax", secure=request.url.scheme == "https")
    return None


@router.get("/me", response_model=MeResponse, response_model_exclude_none=True)
def me(request: Request, current: CurrentUser = Depends(require_session)):
    return login_body(current.user, current.organization, request)


@router.post('/showcase/switch', response_model=LoginResponse, response_model_exclude_none=True)
def switch_showcase(payload: ShowcaseSwitch, response: Response, request: Request,
                    current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    showcase.check_switch_request(request)
    if not showcase.available(current.user, current.organization, request):
        raise HTTPException(403, '沒有展示切換權限')
    if payload.organization_key not in {c['key'] for c in showcase.COMPANIES}:
        raise HTTPException(404, '找不到展示公司')
    org = db.scalar(select(Organization).where(Organization.key == payload.organization_key))
    user = db.get(User, showcase.identifier('user:' + payload.organization_key))
    if not org or not user or user.organization_id != org.id or not showcase.dedicated(user, org) or user.role != 'admin':
        raise HTTPException(409, '展示資料尚未準備完成')
    # Consume the source session atomically, including concurrent switch attempts.
    removed = db.execute(delete(SessionToken).where(SessionToken.token == current.token))
    if removed.rowcount != 1:
        db.rollback()
        raise HTTPException(401, '登入已失效')
    token = new_token()
    db.add(SessionToken(token=token, user_id=user.id, organization_id=org.id, expires_at=session_expires_at()))
    log_audit(db, current, 'showcase.switch', payload={'target_company': org.key})
    db.commit()
    set_session_cookie(response, request, token)
    return login_body(user, org, request)
