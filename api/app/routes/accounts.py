from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.auth import CurrentUser, require_session
from app.database import get_session
from app.services import account_service as service

router = APIRouter(tags=['accounts'])


@router.get('/accounts')
def listing(current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    return service.listing(db, current)


class NewAccount(BaseModel):
    model_config = ConfigDict(extra='forbid')
    username: str = Field(max_length=40)
    display_name: str = Field(max_length=120)
    role: str = Field(max_length=40)


@router.post('/accounts', status_code=201)
def create(data: NewAccount, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    return service.create(db, current, data.username, data.display_name, data.role)


class AccountChange(BaseModel):
    model_config = ConfigDict(extra='forbid')
    display_name: str | None = Field(default=None, max_length=120)
    role: str | None = Field(default=None, max_length=40)
    status: Literal['active', 'disabled'] | None = None


@router.patch('/accounts/{user_id}')
def update(user_id: str, data: AccountChange, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    return service.update(db, current, user_id, data.model_dump(exclude_unset=True))


@router.post('/accounts/{user_id}/reset-password')
def reset_password(user_id: str, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    return service.reset_password(db, current, user_id)


class PasswordChange(BaseModel):
    model_config = ConfigDict(extra='forbid')
    current_password: str = Field(max_length=200)
    new_password: str = Field(max_length=200)


@router.post('/auth/password')
def change_password(data: PasswordChange, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    return service.change_own_password(db, current, data.current_password, data.new_password)
