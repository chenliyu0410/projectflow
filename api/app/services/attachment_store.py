"""Persistent attachment storage with reservations and conservative recovery."""
import hashlib
import logging
import os
from pathlib import Path
import re
import struct
import uuid
import zipfile

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import log_audit
from app.models import Attachment, AttachmentQuota, Node, User, now_utc
from app.services.record_policy import can_write_record

MAX_BYTES = 10_000_000
logger = logging.getLogger(__name__)


def unavailable():
    return HTTPException(status_code=503, detail='附件暫時無法使用，請稍後重新讀取確認')


def storage_root():
    configured = os.environ.get('PF_ATTACHMENT_ROOT')
    if not configured:
        raise unavailable()
    try:
        root = Path(configured).resolve(strict=True)
        if not root.is_dir() or not root.stat().st_mode & 0o222 or not os.access(root, os.W_OK):
            raise OSError()
        return root
    except OSError:
        raise unavailable() from None


def storage_path(root, key, temporary=False):
    if not re.fullmatch(r'[0-9a-f]{32}', key):
        raise unavailable()
    path = root / (key + '.part' if temporary else key)
    if path.is_symlink() or path.resolve().parent != root:
        raise unavailable()
    return path


def quota_limit():
    try:
        value = int(os.environ.get('PF_ATTACHMENT_QUOTA_BYTES', '1000000000'))
        if value < 1:
            raise ValueError()
        return value
    except ValueError:
        raise unavailable() from None


def lock_quota(db, org):
    # ON CONFLICT also serializes first-use initialization without a savepoint race.
    if db.bind.dialect.name == 'postgresql':
        from sqlalchemy.dialects.postgresql import insert
    else:
        from sqlalchemy.dialects.sqlite import insert
    db.execute(insert(AttachmentQuota).values(organization_id=org, charged_bytes=0).on_conflict_do_nothing(index_elements=['organization_id']))
    return db.scalar(select(AttachmentQuota).where(AttachmentQuota.organization_id == org)
                     .with_for_update().execution_options(populate_existing=True))


def attachment_out(row, users=None):
    author = users.get(row.uploaded_by) if users is not None else None
    return {'id': row.id, 'node_id': row.node_id, 'original_name': row.original_name,
            'size_bytes': row.size_bytes, 'sha256': row.sha256, 'uploaded_by': row.uploaded_by,
            'uploaded_by_display_name': author.display_name if author else None,
            'created_at': row.created_at.isoformat(), 'report_id': row.report_id, 'note_id': row.note_id}


def validate_filename(filename):
    if (not filename or len(filename) > 200 or filename != filename.strip()
            or any(ord(c) < 32 or ord(c) == 127 for c in filename) or '/' in filename or '\\' in filename):
        raise HTTPException(status_code=422, detail='檔案名稱無效')
    extension = Path(filename).suffix.lower()
    if extension not in {'.pdf', '.png', '.jpg', '.jpeg', '.txt', '.csv', '.docx', '.xlsx', '.pptx', '.zip'}:
        raise HTTPException(status_code=415, detail='不支援此檔案格式')
    return extension


def validate_content(path, extension):
    try:
        if extension in {'.txt', '.csv'}:
            content = path.read_bytes().decode('utf-8')
            if '\x00' in content:
                raise ValueError()
        elif extension in {'.pdf', '.png', '.jpg', '.jpeg'}:
            with path.open('rb') as handle:
                header = handle.read(8)
            signature = {'.pdf': b'%PDF-', '.png': b'\x89PNG\r\n\x1a\n', '.jpg': b'\xff\xd8\xff', '.jpeg': b'\xff\xd8\xff'}[extension]
            if not header.startswith(signature):
                raise ValueError()
        else:
            # Inspect the bounded central directory before ZipFile allocates entry metadata.
            size = path.stat().st_size
            with path.open('rb') as handle:
                handle.seek(max(0, size - 65557))
                tail = handle.read()
            offset = tail.rfind(b'PK\x05\x06')
            if offset < 0 or len(tail) - offset < 22:
                raise ValueError()
            _, disk, directory_disk, disk_count, count, directory_size, directory_offset, comment_length = struct.unpack('<4s4H2IH', tail[offset:offset+22])
            if (disk or directory_disk or disk_count != count or count > 1000 or directory_size > 1_000_000
                    or directory_offset + directory_size > size or offset + 22 + comment_length != len(tail)):
                raise ValueError()
            with zipfile.ZipFile(path) as archive:
                entries = archive.infolist()
                if len(entries) != count:
                    raise ValueError()
                for item in entries:
                    with path.open('rb') as handle:
                        if item.header_offset < 0 or item.header_offset + 30 > directory_offset:
                            raise ValueError()
                        handle.seek(item.header_offset)
                        local = handle.read(30)
                    if len(local) != 30 or local[:4] != b'PK\x03\x04':
                        raise ValueError()
                    name_length, extra_length = struct.unpack('<HH', local[26:30])
                    if item.header_offset + 30 + name_length + extra_length + item.compress_size > directory_offset:
                        raise ValueError()
                    name = item.filename
                    if (len(name) > 200 or '\\' in name or name.startswith('/') or '..' in name.split('/')
                            or any(ord(c) < 32 for c in name) or item.flag_bits & 1):
                        raise ValueError()
                names = {item.filename for item in entries}
                required = {'.docx': 'word/document.xml', '.xlsx': 'xl/workbook.xml', '.pptx': 'ppt/presentation.xml'}
                if extension in required and not {'[Content_Types].xml', required[extension]} <= names:
                    raise ValueError()
    except (ValueError, UnicodeError, zipfile.BadZipFile, struct.error):
        raise HTTPException(status_code=422, detail='檔案內容與格式不符') from None


def write_chunk(handle, chunk):
    handle.write(chunk)


def mark_ready(db, current, row, digest):
    row.state = 'ready'
    row.sha256 = digest
    log_audit(db, current, 'attachment.upload', node_id=row.node_id,
              payload={'attachment_id': row.id, 'original_name': row.original_name, 'size_bytes': row.size_bytes, 'sha256': digest})
    db.commit()


def reconcile_upload(bind, org, attachment_id, root):
    """Fresh transaction: never remove a committed, bound, or uncertain upload."""
    with Session(bind) as db:
        quota = lock_quota(db, org)
        node_id = db.scalar(select(Attachment.node_id).where(Attachment.id == attachment_id, Attachment.organization_id == org))
        if node_id is None:
            return None
        db.scalar(select(Node).where(Node.id == node_id, Node.organization_id == org).with_for_update())
        row = db.scalar(select(Attachment).where(Attachment.id == attachment_id, Attachment.organization_id == org).with_for_update())
        if row.state == 'ready' or row.report_id or row.note_id or row.deleted_at:
            if row.state == 'ready':
                user = db.get(User, row.uploaded_by)
                return attachment_out(row, {user.id: user} if user and user.organization_id == org else {})
            return None
        if row.state == 'failed':
            return None
        for temporary in (True, False):
            storage_path(root, row.storage_key, temporary).unlink(missing_ok=True)
        quota.charged_bytes -= row.size_bytes
        row.state = 'failed'
        db.commit()
        return None


async def upload_attachment(db, current, node_id, request, filename):
    from app.services.report_service import lock_node
    extension = validate_filename(filename)
    if request.headers.get('content-type', '').split(';')[0].strip().lower() != 'application/octet-stream':
        raise HTTPException(status_code=415, detail='請使用原始檔案上傳')
    length = request.headers.get('content-length')
    if length is None:
        raise HTTPException(status_code=411, detail='缺少檔案長度')
    if len(length) > 20 or not re.fullmatch(r'[0-9]+', length):
        raise HTTPException(status_code=422, detail='檔案長度無效')
    size = int(length)
    if size > MAX_BYTES:
        raise HTTPException(status_code=413, detail='單一檔案不可超過 10 MB')
    if size == 0:
        raise HTTPException(status_code=422, detail='不可上傳空檔案')
    root = storage_root()
    org = current.organization.id
    actor = current.user.id
    attachment_id = str(uuid.uuid4())
    key = uuid.uuid4().hex
    bind = db.get_bind()
    try:
        quota = lock_quota(db, org)
        node, project, context = lock_node(db, current, node_id)
        if not can_write_record(db, current, project, node, context=context):
            raise HTTPException(status_code=403, detail='沒有上傳附件的權限')
        if quota.charged_bytes + size > quota_limit():
            raise HTTPException(status_code=413, detail='公司附件容量已滿')
        quota.charged_bytes += size
        db.add(Attachment(id=attachment_id, organization_id=org, node_id=node_id, uploaded_by=actor,
                          original_name=filename, storage_key=key, size_bytes=size, state='pending'))
        db.commit()
        # No database transaction is held while consuming the request stream.
        total, digest = 0, hashlib.sha256()
        temporary = storage_path(root, key, True)
        with temporary.open('xb') as handle:
            async for chunk in request.stream():
                total += len(chunk)
                if total > MAX_BYTES:
                    raise HTTPException(status_code=413, detail='單一檔案不可超過 10 MB')
                if total > size:
                    raise HTTPException(status_code=422, detail='檔案長度不符')
                write_chunk(handle, chunk)
                digest.update(chunk)
            handle.flush()
            os.fsync(handle.fileno())
        if total != size:
            raise HTTPException(status_code=422, detail='檔案長度不符')
        validate_content(temporary, extension)
        db.expire_all()
        node, project, context = lock_node(db, current, node_id)
        if not can_write_record(db, current, project, node, context=context):
            raise HTTPException(status_code=403, detail='上傳權限已失效')
        row = db.scalar(select(Attachment).where(Attachment.id == attachment_id, Attachment.organization_id == org).with_for_update())
        if row.state != 'pending':
            raise HTTPException(status_code=409, detail='附件狀態已變更')
        os.replace(temporary, storage_path(root, key))
        mark_ready(db, current, row, digest.hexdigest())
        return attachment_out(row, context.users)
    except Exception as error:
        # Rollback of this session is not evidence that COMMIT did not persist.
        try:
            db.rollback()
        except Exception:
            logger.error('Upload session rollback unavailable; checking a fresh transaction')
        try:
            recovered = reconcile_upload(bind, org, attachment_id, root)
            if recovered is not None:
                return recovered
        except Exception:
            logger.error('Attachment reconciliation unavailable; pending data retained')
        if isinstance(error, HTTPException):
            raise error
        raise unavailable() from None


def bind_attachments(db, current, node, ids, *, report_id=None, note_id=None):
    """Caller holds Node; lock the entire attachment batch in ID order before writes."""
    unique = sorted(set(ids))
    if not unique:
        return []
    rows = list(db.scalars(select(Attachment).where(Attachment.organization_id == current.organization.id,
                            Attachment.id.in_(unique)).order_by(Attachment.id).with_for_update().execution_options(populate_existing=True)))
    if len(rows) != len(unique) or any(row.node_id != node.id or row.uploaded_by != current.user.id
            or row.state != 'ready' or row.deleted_at is not None or row.report_id is not None or row.note_id is not None for row in rows):
        raise HTTPException(status_code=422, detail='附件不存在或無法關聯，請重新確認')
    for row in rows:
        row.report_id, row.note_id = report_id, note_id
    return rows


def attachments_for(db, org, node_ids):
    return list(db.scalars(select(Attachment).where(Attachment.organization_id == org, Attachment.node_id.in_(node_ids),
                            Attachment.state == 'ready', Attachment.deleted_at.is_(None)).order_by(Attachment.created_at, Attachment.id)))


from contextlib import contextmanager


@contextmanager
def runtime_lock(root, *, exclusive=False):
    """API holds a shared volume lock; offline recovery requires its exclusive lock."""
    path = root / '.api-runtime.lock'
    if path.is_symlink() or path.resolve().parent != root:
        raise unavailable()
    with path.open('a+b') as handle:
        if os.name == 'nt':
            import msvcrt
            if path.stat().st_size == 0:
                handle.write(b'0'); handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), (fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH) | fcntl.LOCK_NB)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
