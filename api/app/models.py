import uuid
from datetime import date, datetime, timezone

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Date, DateTime, Index, text, ForeignKey, ForeignKeyConstraint, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

JsonType = JSON().with_variant(JSONB(), "postgresql")


def uuid_text() -> str:
    return str(uuid.uuid4())


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_text)
    key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)

    users: Mapped[list["User"]] = relationship(back_populates="organization")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("organization_id", "id"),
        UniqueConstraint("organization_id", "username"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_text)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(80), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[str] = mapped_column(String(40), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)

    organization: Mapped[Organization] = relationship(back_populates="users")


class SessionToken(Base):
    __tablename__ = "sessions"

    token: Mapped[str] = mapped_column(String(128), primary_key=True)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(["organization_id", "user_id"], ["users.organization_id", "users.id"]),
    )


class Department(Base):
    __tablename__ = "departments"
    __table_args__ = (
        UniqueConstraint("organization_id", "id"),
        UniqueConstraint("organization_id", "name"),
        ForeignKeyConstraint(["organization_id", "head_user_id"], ["users.organization_id", "users.id"]),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_text)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    head_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class DepartmentMember(Base):
    __tablename__ = "department_members"
    __table_args__ = (
        UniqueConstraint("organization_id", "department_id", "user_id"),
        ForeignKeyConstraint(["organization_id", "department_id"], ["departments.organization_id", "departments.id"]),
        ForeignKeyConstraint(["organization_id", "user_id"], ["users.organization_id", "users.id"]),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_text)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    department_id: Mapped[str] = mapped_column(String(36), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        UniqueConstraint("organization_id", "id"),
        ForeignKeyConstraint(["organization_id", "owner_user_id"], ["users.organization_id", "users.id"]),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_text)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    owner_user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)


class Node(Base):
    __tablename__ = "nodes"
    __table_args__ = (
        UniqueConstraint("organization_id", "id"),
        UniqueConstraint("organization_id", "project_id", "id", name="uq_nodes_project_id"),
        CheckConstraint("start_date IS NULL OR due_date IS NULL OR start_date <= due_date", name="ck_nodes_date_order"),
        CheckConstraint("weight >= 0 AND weight <= 100", name="ck_nodes_weight_range"),
        CheckConstraint("progress IS NULL OR (progress >= 0 AND progress <= 100)", name="ck_nodes_progress_range"),
        ForeignKeyConstraint(["organization_id", "project_id"], ["projects.organization_id", "projects.id"]),
        ForeignKeyConstraint(["organization_id", "parent_id"], ["nodes.organization_id", "nodes.id"]),
        ForeignKeyConstraint(["organization_id", "department_id"], ["departments.organization_id", "departments.id"]),
        ForeignKeyConstraint(["organization_id", "owner_user_id"], ["users.organization_id", "users.id"]),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_text)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    parent_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="todo", nullable=False)
    owner_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    department_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    collaborators_revision: Mapped[int] = mapped_column(default=0, server_default="0", nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    sort_order: Mapped[int] = mapped_column(default=0, nullable=False)
    # TP-A rollup: weight for the parent's weighted average; manual progress only for doing leaf tasks.
    weight: Mapped[int] = mapped_column(default=1, server_default="1", nullable=False)
    progress: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)


class Workflow(Base):
    __tablename__ = "workflows"
    __table_args__ = (
        UniqueConstraint("organization_id", "id"),
        UniqueConstraint("organization_id", "name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_text)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    content: Mapped[dict] = mapped_column(JsonType, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)


class WorkflowNode(Base):
    __tablename__ = "workflow_nodes"
    __table_args__ = (
        UniqueConstraint("organization_id", "id"),
        ForeignKeyConstraint(["organization_id", "workflow_id"], ["workflows.organization_id", "workflows.id"]),
        ForeignKeyConstraint(["organization_id", "parent_template_id"], ["workflow_nodes.organization_id", "workflow_nodes.id"]),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_text)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    workflow_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    parent_template_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    sort_order: Mapped[int] = mapped_column(default=0, nullable=False)
    gate_after: Mapped[bool] = mapped_column(default=False, nullable=False)


class Gate(Base):
    __tablename__ = "gates"
    __table_args__ = (
        UniqueConstraint("organization_id", "id"),
        ForeignKeyConstraint(["organization_id", "project_id"], ["projects.organization_id", "projects.id"]),
        ForeignKeyConstraint(["organization_id", "node_id"], ["nodes.organization_id", "nodes.id"]),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_text)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    node_id: Mapped[str] = mapped_column(String(36), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)


class TaskReport(Base):
    __tablename__ = "task_reports"
    __table_args__ = (
        UniqueConstraint("organization_id", "id"),
        UniqueConstraint("organization_id", "node_id", "id", name="uq_reports_node_id"),
        UniqueConstraint("organization_id", "node_id", "version", name="uq_reports_node_version"),
        ForeignKeyConstraint(["organization_id", "reviewed_by"], ["users.organization_id", "users.id"], name="fk_reports_reviewer"),
        CheckConstraint("workflow_version IS NULL OR (workflow_version = 2 AND version IS NOT NULL AND version > 0 AND finished_on IS NOT NULL AND result IN ('達成','部分達成','未達成') AND status IN ('submitted','approved','rejected'))", name="ck_reports_workflow"),
        CheckConstraint("workflow_version IS NULL OR (status = 'submitted' AND reviewed_by IS NULL AND reviewed_at IS NULL AND self_approved = false) OR (status IN ('approved','rejected') AND reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)", name="ck_reports_review_fields"),
        CheckConstraint("workflow_version IS NULL OR status != 'rejected' OR (review_comment IS NOT NULL AND length(trim(review_comment)) > 0)", name="ck_reports_reject_comment"),
        CheckConstraint("NOT self_approved OR (workflow_version IS NOT NULL AND workflow_version = 2 AND status = 'approved' AND reviewed_by = submitted_by)", name="ck_reports_self_approved"),
        Index("uq_reports_pending", "organization_id", "node_id", unique=True,
              sqlite_where=text("workflow_version = 2 AND status = 'submitted'"),
              postgresql_where=text("workflow_version = 2 AND status = 'submitted'")),
        ForeignKeyConstraint(["organization_id", "node_id"], ["nodes.organization_id", "nodes.id"]),
        ForeignKeyConstraint(["organization_id", "submitted_by"], ["users.organization_id", "users.id"]),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_text)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    node_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    workflow_version: Mapped[int | None] = mapped_column(nullable=True)
    version: Mapped[int | None] = mapped_column(nullable=True)
    finished_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    self_approved: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"), nullable=False)
    result: Mapped[str] = mapped_column(String(80), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="submitted", nullable=False)
    submitted_by: Mapped[str] = mapped_column(String(36), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)



class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        UniqueConstraint("organization_id", "id"),
        ForeignKeyConstraint(["organization_id", "actor_user_id"], ["users.organization_id", "users.id"]),
        ForeignKeyConstraint(["organization_id", "node_id"], ["nodes.organization_id", "nodes.id"]),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_text)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    actor_user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    node_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    payload: Mapped[dict] = mapped_column(JsonType, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)


class NodeCollaborator(Base):
    __tablename__ = "node_collaborators"
    __table_args__ = (
        UniqueConstraint("organization_id", "node_id", "user_id", name="uq_collaborator_user"),
        UniqueConstraint("organization_id", "node_id", "department_id", name="uq_collaborator_department"),
        CheckConstraint("(user_id IS NOT NULL AND department_id IS NULL) OR (user_id IS NULL AND department_id IS NOT NULL)", name="ck_collaborator_target"),
        ForeignKeyConstraint(["organization_id", "node_id"], ["nodes.organization_id", "nodes.id"]),
        ForeignKeyConstraint(["organization_id", "user_id"], ["users.organization_id", "users.id"]),
        ForeignKeyConstraint(["organization_id", "department_id"], ["departments.organization_id", "departments.id"]),
        ForeignKeyConstraint(["organization_id", "created_by"], ["users.organization_id", "users.id"]),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_text)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    node_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    department_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)


class TaskNote(Base):
    __tablename__ = "task_notes"
    __table_args__ = (
        UniqueConstraint("organization_id", "node_id", "id", name="uq_notes_node_id"),
        CheckConstraint("revision > 0", name="ck_notes_revision"),
        ForeignKeyConstraint(["organization_id", "node_id"], ["nodes.organization_id", "nodes.id"]),
        ForeignKeyConstraint(["organization_id", "author_id"], ["users.organization_id", "users.id"]),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_text)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    node_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    author_id: Mapped[str] = mapped_column(String(36), nullable=False)
    revision: Mapped[int] = mapped_column(default=1, server_default="1", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Attachment(Base):
    __tablename__ = "attachments"
    __table_args__ = (
        CheckConstraint("size_bytes >= 0", name="ck_attachments_size"),
        CheckConstraint("state IN ('pending','ready','failed')", name="ck_attachments_state"),
        CheckConstraint("report_id IS NULL OR note_id IS NULL", name="ck_attachments_target"),
        CheckConstraint("state != 'ready' OR (sha256 IS NOT NULL AND length(sha256) = 64)", name="ck_attachments_ready_hash"),
        ForeignKeyConstraint(["organization_id", "node_id"], ["nodes.organization_id", "nodes.id"]),
        ForeignKeyConstraint(["organization_id", "uploaded_by"], ["users.organization_id", "users.id"]),
        ForeignKeyConstraint(["organization_id", "deleted_by"], ["users.organization_id", "users.id"]),
        ForeignKeyConstraint(["organization_id", "node_id", "report_id"], ["task_reports.organization_id", "task_reports.node_id", "task_reports.id"]),
        ForeignKeyConstraint(["organization_id", "node_id", "note_id"], ["task_notes.organization_id", "task_notes.node_id", "task_notes.id"]),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_text)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    node_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    uploaded_by: Mapped[str] = mapped_column(String(36), nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    state: Mapped[str] = mapped_column(String(16), default="pending", server_default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    report_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    note_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class AttachmentQuota(Base):
    __tablename__ = "attachment_quotas"
    __table_args__ = (CheckConstraint("charged_bytes >= 0", name="ck_quota_nonnegative"),)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), primary_key=True)
    charged_bytes: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0", nullable=False)


class NodeDependency(Base):
    __tablename__ = "node_dependencies"
    __table_args__ = (
        UniqueConstraint("organization_id", "project_id", "predecessor_id", "successor_id", name="uq_dependencies_edge"),
        CheckConstraint("predecessor_id != successor_id", name="ck_dependencies_not_self"),
        ForeignKeyConstraint(["organization_id", "project_id"], ["projects.organization_id", "projects.id"]),
        ForeignKeyConstraint(["organization_id", "project_id", "predecessor_id"], ["nodes.organization_id", "nodes.project_id", "nodes.id"]),
        ForeignKeyConstraint(["organization_id", "project_id", "successor_id"], ["nodes.organization_id", "nodes.project_id", "nodes.id"]),
        ForeignKeyConstraint(["organization_id", "created_by"], ["users.organization_id", "users.id"]),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_text)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    predecessor_id: Mapped[str] = mapped_column(String(36), nullable=False)
    successor_id: Mapped[str] = mapped_column(String(36), nullable=False)
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
