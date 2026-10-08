from datetime import date
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_key: str
    username: str
    password: str


class UserOut(BaseModel):
    id: str
    username: str
    display_name: str
    role: str


class OrganizationOut(BaseModel):
    id: str
    key: str
    name: str


class LoginResponse(BaseModel):
    user: UserOut
    organization: OrganizationOut


MeResponse = LoginResponse


class ProjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str


class NodeMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start_date: date | None = None
    due_date: date | None = None
    owner_user_id: str | None = None
    department_id: str | None = None

    @field_validator("start_date", "due_date", mode="before")
    @classmethod
    def calendar_date(cls, value):
        if value is None:
            return None
        if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
            raise ValueError("日期格式必須為 YYYY-MM-DD")
        return date.fromisoformat(value)

    @field_validator("title", check_fields=False)
    @classmethod
    def clean_title(cls, value):
        if value is None or not 1 <= len(value.strip()) <= 200:
            raise ValueError("名稱需為 1–200 字元")
        return value.strip()

    @model_validator(mode="after")
    def date_order(self):
        if self.start_date and self.due_date and self.start_date > self.due_date:
            raise ValueError("開始日期不得晚於到期日")
        return self


class NodeCreate(NodeMetadata):
    title: str
    kind: Literal["phase", "task"]
    parent_id: str | None = None


class NodeUpdate(NodeMetadata):
    title: str | None = None

    @model_validator(mode="after")
    def nonempty(self):
        if not self.model_fields_set:
            raise ValueError("請提供要更新的欄位")
        return self


class ProjectFromWorkflowCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_id: str
    title: str


class GateStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["approved"]


class ReportCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    result: str
    summary: str


class NodeStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["todo", "doing", "review", "done", "skipped"]
