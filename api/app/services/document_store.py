"""Immutable document files with node authorization and optimistic versions."""
import hashlib
import os
from pathlib import Path
import uuid

from fastapi import HTTPException
from sqlalchemy import select

from app.audit import log_audit
from app.models import Document, DocumentVersion, Node, now_utc
from app.services import attachment_store as files
from app.services.record_policy import can_write_record, load_policy_context
from app.services.dependency_service import lock_project, read_project
from app.permissions import can_view_project, can_manage_project
from app.services.report_service import lock_node, read_node

TEXT_LIMIT = 1_000_000


def permission(db, current, node_id, write=False, project_id=None):
    # 只有寫入路徑需要鎖住專案／節點來序列化；讀取不能擋住其他人的寫入。
    if node_id is None:
        project = (lock_project if write else read_project)(db, current, project_id)
        if project is None or not can_view_project(current, project):
            raise HTTPException(404, '找不到專案')
        context = load_policy_context(db, current)
        allowed = can_manage_project(current, project)
    else:
        node, project, context = (lock_node if write else read_node)(db, current, node_id)
        allowed = can_write_record(db, current, project, node, context=context)
    if write and not allowed:
        raise HTTPException(403, '沒有編輯文件的權限')
    return allowed, context


def get_document(db, current, document_id, write=False):
    doc = db.scalar(select(Document).where(Document.id == document_id, Document.organization_id == current.organization.id))
    if doc is None:
        raise HTTPException(404, '找不到文件')
    allowed, context = permission(db, current, doc.node_id, write, doc.project_id)
    db.refresh(doc)
    return doc, allowed, context


def get_version(db, current, document_id, version):
    doc, allowed, context = get_document(db, current, document_id)
    row = db.scalar(select(DocumentVersion).where(DocumentVersion.document_id == doc.id,
        DocumentVersion.organization_id == current.organization.id, DocumentVersion.version == version))
    if row is None:
        raise HTTPException(404, '找不到文件版本')
    return row, allowed, context


def out(row, context):
    author = context.users.get(row.created_by)
    return dict(document_id=row.document_id, version=row.version, filename=row.filename,
        size_bytes=row.size_bytes, sha256=row.sha256, created_at=row.created_at.isoformat(),
        created_by=author.display_name if author else '使用者', comment=row.comment,
        editable=Path(row.filename).suffix.lower() in {'.txt', '.csv'} and row.size_bytes <= TEXT_LIMIT,
        from_template=row.template_version_id is not None)


def check_expected(doc, expected):
    if doc.current_version != expected:
        raise HTTPException(409, '文件已有新版本，請重新載入後再編輯')


async def save(db, current, node_id, chunks, filename, comment, *, document_id=None, expected=0, project_id=None, template=None):
    """template: optional (template_version_id, fill_values, field names) for versions generated from a document template."""
    extension = files.validate_filename(filename)
    if len(comment) > 500:
        raise HTTPException(422, '版本說明過長')
    permission(db, current, node_id, True, project_id)
    if document_id:
        doc, _, _ = get_document(db, current, document_id, True)
        check_expected(doc, expected)
    # Release read locks while receiving bytes. Authorization is checked again at commit.
    org, actor = current.organization.id, current.user.id
    if node_id is not None:
        project_id = db.scalar(select(Node.project_id).where(Node.id == node_id, Node.organization_id == org))
    db.rollback()
    root = files.storage_root()
    key = uuid.uuid4().hex
    temporary = files.storage_path(root, key, True)
    total, digest = 0, hashlib.sha256()
    try:
        with temporary.open('xb') as handle:
            async for chunk in chunks:
                total += len(chunk)
                if total > files.MAX_BYTES:
                    raise HTTPException(413, '單一檔案不可超過10MB')
                handle.write(chunk)
                digest.update(chunk)
            handle.flush()
            os.fsync(handle.fileno())
        if not total:
            raise HTTPException(422, '不可儲存空檔案')
        files.validate_content(temporary, extension)
        quota = files.lock_quota(db, org)
        _, context = permission(db, current, node_id, True, project_id)
        if quota.charged_bytes + total > files.quota_limit():
            raise HTTPException(413, '公司容量已滿')
        if document_id:
            doc, _, context = get_document(db, current, document_id, True)
            check_expected(doc, expected)
        else:
            doc = Document(id=str(uuid.uuid4()), organization_id=org, node_id=node_id, project_id=project_id, current_version=0)
            db.add(doc)
            db.flush()
        doc.current_version += 1
        row = DocumentVersion(id=str(uuid.uuid4()), organization_id=org, document_id=doc.id,
            version=doc.current_version, filename=filename, storage_key=key, size_bytes=total,
            sha256=digest.hexdigest(), created_by=actor, created_at=now_utc(), comment=comment.strip())
        db.add(row)
        quota.charged_bytes += total
        log_audit(db, current, 'document.version', node_id=node_id,
            payload={'project_id': project_id, 'document_id': doc.id, 'version': row.version, 'filename': filename, 'sha256': row.sha256})
        if template:
            row.template_version_id, row.fill_values, names = template
            # Field names only; the filled content stays in the document version, never in the audit log.
            log_audit(db, current, 'doc_template.generate', node_id=node_id, payload={'project_id': project_id,
                'document_id': doc.id, 'version': row.version, 'template_id': row.fill_values['template_id'],
                'template_version': row.fill_values['template_version'], 'fields': names})
        result = out(row, context)
        db.flush()
        os.replace(temporary, files.storage_path(root, key))
        # Once renamed, never unlink on an ambiguous database commit.
        db.commit()
        return result
    except Exception as error:
        db.rollback()
        if isinstance(error, HTTPException):
            raise
        raise files.unavailable() from None
    finally:
        temporary.unlink(missing_ok=True)


def version_path(row):
    path = files.storage_path(files.storage_root(), row.storage_key)
    if not path.is_file():
        raise files.unavailable()
    return path
