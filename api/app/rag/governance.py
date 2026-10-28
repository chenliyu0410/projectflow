"""Formal document permissions shared by retrieval and citation opening."""
import math
import re
from fastapi import HTTPException
from sqlalchemy import select
from app.models import Document, Project, SessionToken, User, Organization
from app.rag.models import now
from app.permissions import can_view_project
from app.services import document_store
from app.services.dependency_service import read_project


def session_access(db, current):
    """Interactive calls must retain a live login; workers never call this helper."""
    # Discard identity-map state; READ COMMITTED reloads the current login and ACL.
    db.expire_all()
    user_id, org_id = current.user.id, current.organization.id
    token = db.scalar(select(SessionToken.token).where(
        SessionToken.token == current.token, SessionToken.user_id == user_id,
        SessionToken.organization_id == org_id, SessionToken.expires_at > now()))
    if not current.token or token is None:
        raise HTTPException(401, '請重新登入')
    db.refresh(current.user)
    db.refresh(current.organization)


def authorized_documents(db, current, project_id):
    # Expire identity-map values: a prior retrieval must not cache revoked ACLs.
    db.expire_all()
    if project_id is not None:
        read_project(db, current, project_id)
    visible = [project_id] if project_id is not None else [p.id for p in db.scalars(select(Project).where(Project.organization_id == current.organization.id)) if can_view_project(current,p)]
    ids = list(db.scalars(select(Document.id).where(
        Document.organization_id == current.organization.id,
        Document.project_id.in_(visible))))
    result = []
    for document_id in ids:
        try:
            doc, _, _ = document_store.get_document(db, current, document_id)
        except HTTPException as error:
            if error.status_code == 404:
                continue
            raise
        result.append(doc)
    return result


def recheck(db, current, document_id, version, require_current=True):
    db.expire_all()
    row, _, _ = document_store.get_version(db, current, document_id, version)
    doc, _, _ = document_store.get_document(db, current, document_id)
    if require_current and doc.current_version != version:
        raise HTTPException(409, '引用文件已有新版本，請重新查詢')
    return row


_IDS = {'query_id', 'project_id', 'document_id', 'source_id', 'chunk_id', 'actor_id', 'organization_id'}
_CODES = {'kind', 'engine', 'retrieval_mode', 'error_code', 'model', 'embedding_model', 'model_name', 'stage', 'outcome', 'pipeline_version', 'prompt_version', 'contract_version', 'scope_kind'}
_COUNTS = {'version', 'indexed_version', 'chunk_count', 'source_count', 'citation_count', 'candidate_count', 'document_count', 'authorized_count', 'context_chars'}
_DURATIONS = {'duration_ms', 'retrieval_ms', 'generation_ms', 'embedding_ms', 'total_ms'}
_SAFE = re.compile(r'^[A-Za-z0-9_.:/@+\-]+$')


def trace_summary(**fields):
    """Drop unknown keys and malformed values; never stringify arbitrary objects."""
    output = {}
    for key, value in fields.items():
        if key in _IDS | _CODES:
            if isinstance(value, str) and 0 < len(value) <= 128 and _SAFE.fullmatch(value) and '://' not in value:
                output[key] = value
        elif key in {'input_tokens', 'output_tokens'}:
            if value is None or (type(value) is int and 0 <= value <= 1_000_000_000):
                output[key] = value
        elif key == 'cost':
            if value is None or (type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1_000_000):
                output[key] = value
        elif key in _COUNTS:
            if type(value) is int and 0 <= value <= 1_000_000_000:
                output[key] = value
        elif key in _DURATIONS:
            if type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 86_400_000:
                output[key] = value
    return output
