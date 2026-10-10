from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.auth import CurrentUser, require_session
from app.database import get_session
from app.schemas import ConditionCreate, ConditionEdit, ConditionConfirm
from app.services.condition_service import create_condition, mutate_condition

router = APIRouter(tags=['conditions'])


@router.post('/projects/{project_id}/conditions', status_code=201)
def create(project_id: str, payload: ConditionCreate, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    return create_condition(db, current, project_id, payload)


@router.patch('/conditions/{condition_id}')
def edit(condition_id: str, payload: ConditionEdit, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    return mutate_condition(db, current, condition_id, 'update', payload)


@router.post('/conditions/{condition_id}/confirmation')
def confirm(condition_id: str, payload: ConditionConfirm, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    return mutate_condition(db, current, condition_id, 'confirm', payload)


@router.delete('/conditions/{condition_id}')
def delete(condition_id: str, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    return mutate_condition(db, current, condition_id, 'delete')
