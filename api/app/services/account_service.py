"""Company accounts: admins create, edit, disable and reset; everyone changes their own password."""
from collections import deque
import os
import re
import secrets
import time

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.audit import log_audit
from app.models import Department, DepartmentMember, SessionToken, User, now_utc
from app.security import hash_password, verify_password

ROLES = ('admin', 'project_owner', 'reviewer', 'member', 'readonly')
USERNAME = re.compile(r'[a-z0-9][a-z0-9._-]{1,39}')
LOGIN_LIMIT = 20
LOGIN_WINDOW = 60
DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


def require_admin(current):
    if current.user.role != 'admin':
        raise HTTPException(403, '只有系統管理員可以管理帳號')


# No look-alike characters (0/O, 1/l/I), so the password can be read aloud or copied by hand.
TEMPORARY_ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789'


def temporary_password():
    return ''.join(secrets.choice(TEMPORARY_ALPHABET) for _ in range(12))


def is_demo_password(user, password):
    return password == f'demo-{user.username}'


def demo_blocked(request):
    """Demo passwords are guessable: refuse them on the public Funnel host, or everywhere when configured."""
    host = (request.url.hostname or '').lower()
    return os.environ.get('PF_DISABLE_DEMO_PASSWORDS') == 'true' or host.endswith('.ts.net')


def failures(request, organization_key, username):
    """Recent failed sign-ins for one account from one client address, oldest first (process memory only).

    Keyed by address and account, not address alone: behind nginx every visitor can share one address,
    and a shared bucket would let anyone stop everybody from signing in. Accounts are never locked.
    """
    attempts = getattr(request.app.state, 'login_failures', None)
    if attempts is None:
        attempts = request.app.state.login_failures = {}
    now = time.monotonic()
    if len(attempts) > 10_000:
        for key in [k for k, v in attempts.items() if not v or now - v[-1] > LOGIN_WINDOW]:
            del attempts[key]
        while len(attempts) > 10_000:
            del attempts[next(iter(attempts))]
    host = request.client.host if request.client else 'unknown'
    window = attempts.setdefault((host, organization_key.strip().lower(), username.strip().lower()), deque())
    while window and now - window[0] > LOGIN_WINDOW:
        window.popleft()
    return window


def check_rate(request, organization_key, username):
    """Pause one account's sign-in from one address after LOGIN_LIMIT failures within a minute."""
    if len(failures(request, organization_key, username)) >= LOGIN_LIMIT:
        raise HTTPException(429, '嘗試太多次，請稍後再試')


def record_failure(request, organization_key, username):
    failures(request, organization_key, username).append(time.monotonic())


def check_new_password(user, password):
    if not isinstance(password, str) or not 10 <= len(password) <= 200:
        raise HTTPException(422, '新密碼需為10到200個字元')
    if password.lower() == user.username.lower() or password.lower().startswith('demo-'):
        raise HTTPException(422, '新密碼不可與帳號相同，也不可用 demo- 開頭')


def visible_users(db, current):
    from app import showcase
    users = db.scalars(select(User).where(User.organization_id == current.organization.id).order_by(User.created_at, User.username)).all()
    return [u for u in users if not showcase.dedicated(u, current.organization)]


def out(user, departments):
    return {'id': user.id, 'username': user.username, 'display_name': user.display_name, 'role': user.role,
            'status': user.status, 'must_change_password': user.must_change_password,
            'departments': departments.get(user.id, []),
            'last_login_at': user.last_login_at.isoformat() if user.last_login_at else None}


def department_names(db, organization_id):
    rows = db.execute(select(DepartmentMember.user_id, Department.name).join(Department,
        (Department.id == DepartmentMember.department_id) & (Department.organization_id == DepartmentMember.organization_id))
        .where(DepartmentMember.organization_id == organization_id)).all()
    names = {}
    for user_id, name in rows:
        names.setdefault(user_id, []).append(name)
    return names


def listing(db, current):
    require_admin(current)
    names = department_names(db, current.organization.id)
    return {'items': [out(u, names) for u in visible_users(db, current)], 'roles': list(ROLES), 'me': current.user.id}


def load(db, current, user_id):
    require_admin(current)
    user = db.scalar(select(User).where(User.id == user_id, User.organization_id == current.organization.id).with_for_update())
    from app import showcase
    if user is None or showcase.dedicated(user, current.organization):
        raise HTTPException(404, '找不到帳號')
    return user


def check_display(name):
    name = (name or '').strip()
    if not 1 <= len(name) <= 120:
        raise HTTPException(422, '顯示名稱需為1到120字')
    return name


def create(db, current, username, display_name, role):
    require_admin(current)
    username = (username or '').strip().lower()
    if not USERNAME.fullmatch(username):
        raise HTTPException(422, '帳號需為2到40個英數字，可用 . _ -，開頭須為英數字')
    if role not in ROLES:
        raise HTTPException(422, '角色無效')
    display_name = check_display(display_name)
    if db.scalar(select(User.id).where(User.organization_id == current.organization.id, User.username == username)):
        raise HTTPException(409, '這個帳號已經有人使用')
    password = temporary_password()
    user = User(organization_id=current.organization.id, username=username, display_name=display_name, role=role,
                password_hash=hash_password(password), status='active', must_change_password=True)
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, '這個帳號已經有人使用') from None
    log_audit(db, current, 'account.create', payload={'user_id': user.id, 'username': username, 'role': role})
    db.commit()
    return {'account': out(user, {}), 'temporary_password': password}


def active_admins(db, organization_id):
    """Lock and count the company's active admins, so two admins demoting each other cannot both succeed."""
    from app import showcase
    return len(db.scalars(select(User.id).where(User.organization_id == organization_id, User.role == 'admin',
        User.status == 'active', User.username != showcase.USERNAME).with_for_update()).all())


def update(db, current, user_id, changes):
    user = load(db, current, user_id)
    before = {'display_name': user.display_name, 'role': user.role, 'status': user.status}
    if 'display_name' in changes and changes['display_name'] is not None:
        user.display_name = check_display(changes['display_name'])
    role, status = changes.get('role'), changes.get('status')
    if role is not None and role not in ROLES:
        raise HTTPException(422, '角色無效')
    if status is not None and status not in ('active', 'disabled'):
        raise HTTPException(422, '狀態無效')
    if user.id == current.user.id and ((role is not None and role != user.role) or (status is not None and status != user.status)):
        raise HTTPException(409, '不能變更自己的角色或停用自己')
    losing_admin = user.role == 'admin' and user.status == 'active' and ((role is not None and role != 'admin') or status == 'disabled')
    if losing_admin and active_admins(db, user.organization_id) <= 1:
        raise HTTPException(409, '公司至少要保留一位啟用中的管理者')
    if role is not None:
        user.role = role
    if status is not None:
        user.status = status
        if status == 'disabled':
            db.execute(delete(SessionToken).where(SessionToken.user_id == user.id, SessionToken.organization_id == user.organization_id))
    after = {'display_name': user.display_name, 'role': user.role, 'status': user.status}
    if after != before:
        log_audit(db, current, 'account.update', payload={'user_id': user.id, 'username': user.username,
            'before': before, 'after': after})
    db.commit()
    return out(user, department_names(db, current.organization.id))


def reset_password(db, current, user_id):
    user = load(db, current, user_id)
    password = temporary_password()
    user.password_hash = hash_password(password)
    user.must_change_password = True
    db.execute(delete(SessionToken).where(SessionToken.user_id == user.id, SessionToken.organization_id == user.organization_id))
    log_audit(db, current, 'account.reset_password', payload={'user_id': user.id, 'username': user.username})
    db.commit()
    return {'temporary_password': password}


def change_own_password(db, current, old_password, new_password):
    user = db.scalar(select(User).where(User.id == current.user.id, User.organization_id == current.organization.id).with_for_update())
    if not verify_password(old_password or '', user.password_hash):
        raise HTTPException(422, '目前密碼不正確')
    check_new_password(user, new_password)
    if new_password == old_password:
        raise HTTPException(422, '新密碼不可與目前密碼相同')
    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    user.password_changed_at = now_utc()
    # Keep this browser signed in; every other session for the account ends.
    db.execute(delete(SessionToken).where(SessionToken.user_id == user.id, SessionToken.organization_id == user.organization_id,
                                          SessionToken.token != current.token))
    log_audit(db, current, 'account.password_change', payload={'user_id': user.id})
    db.commit()
    return {'ok': True}
