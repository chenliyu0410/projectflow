from typing import Literal

from pydantic import BaseModel, ConfigDict


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


class NodeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    kind: str
    parent_id: str | None = None
    owner_user_id: str | None = None
    department_id: str | None = None


class ProjectFromWorkflowCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_id: str
    title: str


class GateStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["approved"]


class NodeStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["todo", "doing", "review", "done", "skipped"]
