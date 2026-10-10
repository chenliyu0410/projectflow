"""Company department administration; references are never silently removed."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.auth import CurrentUser, require_session
from app.database import get_session
from app.audit import log_audit
from app.models import Department, DepartmentMember, User, Node, NodeCollaborator, WorkflowVersion, Organization, INCLUDE_DELETED

router = APIRouter(tags=['departments'])

class DepartmentWrite(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=120)
    head_user_id: str | None = None
    member_ids: list[str] = Field(default_factory=list, max_length=1000)


def admin_lock(db, current):
    if current.user.role != 'admin':
        raise HTTPException(403, '只有系統管理員可以管理部門')
    db.scalar(select(Organization).where(Organization.id == current.organization.id).with_for_update())


def output(db, item):
    return {'id': item.id, 'name': item.name, 'head_user_id': item.head_user_id,
            'member_ids': list(db.scalars(select(DepartmentMember.user_id).where(DepartmentMember.organization_id == item.organization_id, DepartmentMember.department_id == item.id)))}

@router.get('/departments')
def list_departments(current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    org = current.organization.id
    rows = list(db.scalars(select(Department).where(Department.organization_id == org).order_by(Department.name)))
    return {'items': [output(db, item) for item in rows], 'capabilities': {'manage': current.user.role == 'admin'},
            'users': [{'id': u.id, 'display_name': u.display_name, 'role': u.role} for u in db.scalars(select(User).where(User.organization_id == org).order_by(User.display_name))]}


def save(db, current, payload, department_id=None):
    admin_lock(db, current)
    org = current.organization.id
    item = db.scalar(select(Department).where(Department.organization_id == org, Department.id == department_id)) if department_id else Department(organization_id=org)
    if item is None:
        raise HTTPException(404, '找不到部門')
    users = {u.id: u for u in db.scalars(select(User).where(User.organization_id == org))}
    members = set(payload.member_ids)
    if not members.issubset(users) or (payload.head_user_id and (payload.head_user_id not in members or users[payload.head_user_id].role == 'readonly')):
        raise HTTPException(422, '主管必須是同公司非唯讀的部門成員')
    if db.scalar(select(Department.id).where(Department.organization_id == org, Department.name == payload.name, Department.id != (department_id or ''))):
        raise HTTPException(409, '已有同名部門')
    before = output(db, item) if department_id else None
    item.name, item.head_user_id = payload.name, payload.head_user_id
    db.add(item)
    try:
        db.flush()
        db.execute(delete(DepartmentMember).where(DepartmentMember.organization_id == org, DepartmentMember.department_id == item.id))
        db.add_all([DepartmentMember(organization_id=org, department_id=item.id, user_id=uid) for uid in sorted(members)])
        db.flush()
        result = output(db, item)
        log_audit(db, current, 'department.update' if department_id else 'department.create', payload={'before': before, 'after': result})
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, '部門資料已變更，請重新整理')
    return result

@router.post('/departments', status_code=201)
def create(payload: DepartmentWrite, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    return save(db, current, payload)

@router.patch('/departments/{department_id}')
def update(department_id: str, payload: DepartmentWrite, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    return save(db, current, payload, department_id)

@router.delete('/departments/{department_id}')
def remove(department_id: str, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    admin_lock(db, current)
    org = current.organization.id
    item = db.scalar(select(Department).where(Department.organization_id == org, Department.id == department_id))
    if item is None:
        raise HTTPException(404, '找不到部門')
    used = any(db.scalar(select(model.id).where(model.organization_id == org, model.department_id == item.id).execution_options(**{INCLUDE_DELETED: True}).limit(1)) for model in (Node, DepartmentMember, NodeCollaborator))
    def references(value):
        if isinstance(value, dict):
            return value.get('department_id') == item.id or any(references(v) for v in value.values())
        return isinstance(value, list) and any(references(v) for v in value)
    used = used or any(references(v) for v in db.scalars(select(WorkflowVersion.snapshot).where(WorkflowVersion.organization_id == org)))
    if used:
        raise HTTPException(409, '部門仍有資料引用，請先移轉')
    log_audit(db, current, 'department.delete', payload=output(db, item))
    db.delete(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, '部門仍有資料引用，請先移轉')
    return {'deleted': True}
