"""Derived knowledge and content-free query records; original documents stay immutable."""
from datetime import datetime, timezone
import uuid

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

Json = JSON().with_variant(JSONB(), 'postgresql')


def now():
    return datetime.now(timezone.utc)


class RagSettings(Base):
    __tablename__ = 'rag_settings'
    organization_id: Mapped[str] = mapped_column(ForeignKey('organizations.id'), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    base_url: Mapped[str] = mapped_column(String(200), default='', nullable=False)
    model: Mapped[str] = mapped_column(String(120), default='', nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(120), default='', nullable=False)
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class RagIndex(Base):
    __tablename__ = 'rag_indexes'
    __table_args__ = (
        ForeignKeyConstraint(['organization_id', 'document_id'], ['documents.organization_id', 'documents.id']),
        CheckConstraint("state IN ('queued','processing','ready','failed','unsupported')", name='ck_rag_index_state'),
    )
    document_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    state: Mapped[str] = mapped_column(String(16), default='queued', nullable=False)
    indexed_version: Mapped[int | None] = mapped_column(Integer)
    generation: Mapped[str | None] = mapped_column(String(36))
    fingerprint: Mapped[str | None] = mapped_column(String(64))
    embedding_key: Mapped[str | None] = mapped_column(String(64))
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(40))
    claim: Mapped[str | None] = mapped_column(String(36))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)


class RagChunk(Base):
    __tablename__ = 'rag_chunks'
    __table_args__ = (
        ForeignKeyConstraint(['organization_id', 'document_id'], ['documents.organization_id', 'documents.id']),
        ForeignKeyConstraint(['document_id', 'version'], ['document_versions.document_id', 'document_versions.version']),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    document_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    generation: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    parent_id: Mapped[str] = mapped_column(String(120), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    parent_text: Mapped[str] = mapped_column(Text, nullable=False)
    locator: Mapped[dict] = mapped_column(Json, nullable=False)
    embedding: Mapped[list | None] = mapped_column(Json)


class RagQuery(Base):
    __tablename__ = 'rag_queries'
    __table_args__ = (
        ForeignKeyConstraint(['organization_id', 'actor_user_id'], ['users.organization_id', 'users.id']),
        ForeignKeyConstraint(['organization_id', 'project_id'], ['projects.organization_id', 'projects.id']),
        CheckConstraint("rating IS NULL OR rating IN ('helpful','unhelpful')", name='ck_rag_rating'),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    actor_user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False)
    source_ids: Mapped[list] = mapped_column(Json, default=list, nullable=False)
    trace: Mapped[dict] = mapped_column(Json, default=dict, nullable=False)
    rating: Mapped[str | None] = mapped_column(String(12))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, nullable=False)
