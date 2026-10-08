from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import CurrentUser, require_session
from app.database import get_session
from app.models import Department

router = APIRouter(tags=["departments"])


@router.get("/departments")
def list_departments(current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    departments = db.execute(
        select(Department).where(Department.organization_id == current.organization.id).order_by(Department.name)
    ).scalars()
    return {"items": [{"id": item.id, "name": item.name, "head_user_id": item.head_user_id} for item in departments]}
