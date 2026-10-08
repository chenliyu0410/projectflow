from datetime import date
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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
    result: Literal["達成", "部分達成", "未達成"]
    summary: str
    finished_on: date
    attachment_ids: list[str] = Field(default_factory=list)
    self_approve: bool = False

    @field_validator("result", mode="before")
    @classmethod
    def trim_result(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("summary")
    @classmethod
    def valid_summary(cls, value):
        value = value.strip()
        if not 1 <= len(value) <= 10000:
            raise ValueError("成果說明需為 1–10000 字元")
        return value

    @field_validator("finished_on", mode="before")
    @classmethod
    def valid_date(cls, value):
        if value is None:
            raise ValueError("實際完成日必填")
        return NodeMetadata.calendar_date(value)


class ReportReview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["approved", "rejected"]
    comment: str = ""

    @field_validator("comment")
    @classmethod
    def valid_comment(cls, value):
        value = value.strip()
        if len(value) > 2000:
            raise ValueError("審核意見上限 2000 字元")
        return value

    @model_validator(mode="after")
    def required_rejection(self):
        if self.decision == "rejected" and not self.comment:
            raise ValueError("退回意見必填")
        return self


class NodeLifecycle(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["reopen", "skip", "restore"]
    reason: str

    @field_validator("reason")
    @classmethod
    def valid_reason(cls, value):
        value = value.strip()
        if not 1 <= len(value) <= 2000:
            raise ValueError("原因需為 1–2000 字元")
        return value


class NodeStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["todo", "doing", "review", "done", "skipped"]


class NoteCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    body: str = Field(min_length=1, max_length=10000)
    attachment_ids: list[str] = Field(default_factory=list)

    @field_validator('body', mode='before')
    @classmethod
    def trim_body(cls, value):
        return value.strip() if isinstance(value, str) else value


class NoteUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    body: str = Field(min_length=1, max_length=10000)
    expected_revision: int = Field(ge=1, strict=True)

    @field_validator('body', mode='before')
    @classmethod
    def trim_body(cls, value):
        return value.strip() if isinstance(value, str) else value


class CollaboratorsUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    user_ids: list[str] = Field(default_factory=list)
    department_ids: list[str] = Field(default_factory=list)
    expected_revision: int = Field(ge=0, strict=True)
