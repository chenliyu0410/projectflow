"""Authorized binary attachment endpoints."""
import logging
from urllib.parse import quote
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.audit import log_audit
from app.auth import CurrentUser, require_session
from app.database import get_session
from app.models import Attachment, AttachmentQuota, now_utc
from app.permissions import can_manage_project
from app.services.record_policy import can_write_record
from app.services.report_service import lock_node, read_node
from app.services import attachment_store as store

router = APIRouter(tags=['attachments'])


@router.post('/nodes/{node_id}/attachments', status_code=201)
async def upload(node_id: str, request: Request, filename: str, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    return await store.upload_attachment(db, current, node_id, request, filename)


def authorized_attachment(db, current, attachment_id, *, lock=True):
    node_id = db.scalar(select(Attachment.node_id).where(Attachment.id == attachment_id, Attachment.organization_id == current.organization.id))
    if node_id is None:
        raise HTTPException(status_code=404, detail='找不到附件')
    node, project, context = (lock_node if lock else read_node)(db, current, node_id)
    query = select(Attachment).where(Attachment.id == attachment_id, Attachment.organization_id == current.organization.id)
    row = db.scalar(query.with_for_update().execution_options(populate_existing=True) if lock else query)
    if row.state != 'ready' or row.deleted_at is not None:
        raise HTTPException(status_code=404, detail='找不到附件')
    return row, node, project, context


@router.get('/attachments/{attachment_id}/download')
def download(attachment_id: str, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    row, _, _, _ = authorized_attachment(db, current, attachment_id, lock=False)
    path = store.storage_path(store.storage_root(), row.storage_key)
    if not path.is_file():
        logging.getLogger(__name__).error('Ready attachment file is missing: %s', row.id)
        raise store.unavailable()
    return FileResponse(path, media_type='application/octet-stream', headers={
        'Content-Disposition': "attachment; filename*=UTF-8''" + quote(row.original_name, safe=''),
        'X-Content-Type-Options': 'nosniff'})


@router.delete('/attachments/{attachment_id}')
def delete_attachment(attachment_id: str, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    row, node, project, context = authorized_attachment(db, current, attachment_id)
    if not can_write_record(db, current, project, node, context=context) or (row.uploaded_by != current.user.id and not can_manage_project(current, project)):
        raise HTTPException(status_code=403, detail='沒有移除附件的權限')
    if row.report_id is not None:
        raise HTTPException(status_code=409, detail='已提交回報的附件不可移除')
    row.deleted_at, row.deleted_by = now_utc(), current.user.id
    log_audit(db, current, 'attachment.delete', node_id=node.id, payload={'attachment_id': row.id, 'original_name': row.original_name})
    db.commit()
    return {'id': row.id, 'deleted': True}


@router.get('/nodes/{node_id}/attachment-quota')
def get_quota(node_id: str, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    node, project, context = read_node(db, current, node_id)
    if not can_write_record(db, current, project, node, context=context):
        raise HTTPException(status_code=403, detail='沒有上傳附件的權限')
    charged = db.scalar(select(AttachmentQuota.charged_bytes).where(AttachmentQuota.organization_id == current.organization.id)) or 0
    limit = store.quota_limit()
    return {'limit_bytes': limit, 'charged_bytes': charged, 'remaining_bytes': max(0, limit-charged)}
