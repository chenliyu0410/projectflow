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
    showcase: dict | None = None


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
    milestone: bool = Field(default=False, strict=True)
    schedule_locked: bool = Field(default=False, strict=True)
    title: str
    kind: Literal["phase", "task"]
    parent_id: str | None = None


class NodeUpdate(NodeMetadata):
    milestone: bool = Field(default=False, strict=True)
    schedule_locked: bool = Field(default=False, strict=True)
    title: str | None = None
    weight: int | None = Field(default=None, ge=0, le=100, strict=True)
    progress: int | None = Field(default=None, ge=0, le=100, strict=True)

    @model_validator(mode="after")
    def nonempty(self):
        if not self.model_fields_set:
            raise ValueError("請提供要更新的欄位")
        if "weight" in self.model_fields_set and self.weight is None:
            raise ValueError("權重需為 0–100 的整數")
        return self


class ScheduleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    start_date: date | None
    due_date: date | None
    cascade: bool = Field(default=False, strict=True)

    @field_validator("start_date", "due_date", mode="before")
    @classmethod
    def calendar_date(cls, value):
        return NodeMetadata.calendar_date(value)


class NodeMove(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # None moves the task to the project's top level (under the project root when one exists).
    parent_id: str | None = Field(min_length=1, max_length=36)


class UndoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    audit_id: str = Field(min_length=1, max_length=36)


class ProjectFromWorkflowCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_id: str
    version: int | None = Field(default=None, ge=1, strict=True)
    title: str = Field(min_length=1, max_length=200)
    start_date: date | None = None

    @field_validator('start_date', mode='before')
    @classmethod
    def calendar_start(cls, value):
        return NodeMetadata.calendar_date(value)

    @field_validator('title', mode='before')
    @classmethod
    def trim_title(cls, value):
        return value.strip() if isinstance(value, str) else value


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


class TemplateCollaborator(BaseModel):
    model_config = ConfigDict(extra='forbid')
    user_id: str | None = Field(default=None, max_length=36)
    department_id: str | None = Field(default=None, max_length=36)

    @model_validator(mode='after')
    def one_target(self):
        if (self.user_id is None) == (self.department_id is None):
            raise ValueError('協作對象需擇一')
        return self


class TemplateCondition(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    node_id: str = Field(min_length=1, max_length=36)
    label: str = Field(min_length=1, max_length=200)
    enforcement: Literal['hard', 'soft'] = 'hard'


class WorkflowNodeInput(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    id: str = Field(min_length=1, max_length=36)
    parent_id: str | None = Field(default=None, min_length=1, max_length=36)
    kind: Literal['phase', 'task']
    title: str = Field(min_length=1, max_length=200)
    sort_order: int = Field(default=0, ge=0, strict=True)
    gate_after: bool = False
    owner_user_id: str | None = Field(default=None, max_length=36)
    department_id: str | None = Field(default=None, max_length=36)
    collaborators: list[TemplateCollaborator] = Field(default_factory=list, max_length=100)
    weight: int = Field(default=1, ge=0, le=100, strict=True)
    milestone: bool = False
    start_offset: int | None = Field(default=None, ge=0, strict=True)
    due_offset: int | None = Field(default=None, ge=0, strict=True)

    @model_validator(mode='after')
    def valid_node(self):
        if self.gate_after and self.kind != 'phase':
            raise ValueError('只有階段可以設定閘門')
        if self.start_offset is not None and self.due_offset is not None and self.start_offset > self.due_offset:
            raise ValueError('開始日偏移不得晚於截止日')
        return self


class WorkflowDependencyInput(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    predecessor_id: str = Field(min_length=1, max_length=36)
    successor_id: str = Field(min_length=1, max_length=36)
    relation_type: Literal['FS', 'SS', 'FF'] = 'FS'
    lag_days: int = Field(default=0, ge=-365, le=365, strict=True)
    enforcement: Literal['hard', 'soft'] = 'hard'


class WorkflowWrite(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=160)
    kind: Literal['workflow', 'task'] = 'workflow'
    expected_version: int | None = Field(default=None, ge=1, strict=True)
    nodes: list[WorkflowNodeInput] = Field(max_length=300)
    conditions: list[TemplateCondition] = Field(default_factory=list, max_length=300)
    dependencies: list[WorkflowDependencyInput] = Field(default_factory=list)


class WorkflowCopy(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    name: str | None = Field(default=None, min_length=1, max_length=160)


class ShowcaseSwitch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    organization_key: str


class DependencySettings(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    relation_type: Literal['FS', 'SS', 'FF'] = 'FS'
    lag_days: int = Field(default=0, ge=-365, le=365, strict=True)
    enforcement: Literal['hard', 'soft'] = 'hard'


class DependencyCreate(DependencySettings):
    predecessor_id: str = Field(min_length=1, max_length=36)
    successor_id: str = Field(min_length=1, max_length=36)


class ConditionCreate(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    node_id: str = Field(min_length=1, max_length=36)
    label: str = Field(min_length=1, max_length=200)
    enforcement: Literal['hard', 'soft'] = 'hard'


class ConditionEdit(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    label: str | None = Field(default=None, min_length=1, max_length=200)
    enforcement: Literal['hard', 'soft'] | None = None

    @model_validator(mode='after')
    def reject_explicit_null(self):
        if any(getattr(self, key) is None for key in self.model_fields_set):
            raise ValueError('條件設定不可為空值')
        return self


class ConditionConfirm(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    is_met: bool = Field(strict=True)
    reason: str = Field(min_length=1, max_length=1000)


class TemplateSave(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=160)
    template_id: str | None = None
    expected_version: int | None = Field(default=None, ge=1, strict=True)


class TemplateApply(BaseModel):
    model_config = ConfigDict(extra='forbid')
    template_id: str
    version: int = Field(ge=1, strict=True)
    start_date: date | None = None
    structure: bool = True
    dependencies: bool = True
    owners: bool = False
    dates: bool = True
    variables: dict[str, str] = Field(default_factory=dict, max_length=50)

    @field_validator('start_date', mode='before')
    @classmethod
    def calendar_start(cls, value):
        return NodeMetadata.calendar_date(value)
