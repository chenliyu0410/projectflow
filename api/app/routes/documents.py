from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import CurrentUser, require_session
from app.database import get_session
from app.models import Document, DocumentVersion
from app.services import document_store as store

router = APIRouter(tags=['documents'])


@router.get('/nodes/{node_id}/documents')
def listing(node_id: str, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    allowed, context = store.permission(db, current, node_id)
    rows = db.scalars(select(DocumentVersion).join(Document, Document.id == DocumentVersion.document_id).where(
        Document.organization_id == current.organization.id, Document.node_id == node_id,
        DocumentVersion.version == Document.current_version).order_by(DocumentVersion.created_at.desc())).all()
    return {'items': [store.out(row, context) for row in rows], 'can_write': allowed}


@router.post('/nodes/{node_id}/documents', status_code=201)
async def upload(node_id: str, request: Request, filename: str, comment: str = Query('', max_length=500),
                 current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    require_binary(request)
    return await store.save(db, current, node_id, request.stream(), filename, comment)


def require_binary(request):
    if request.headers.get('content-type', '').split(';')[0].strip().lower() != 'application/octet-stream':
        raise HTTPException(415, '請使用原始檔案上傳')


@router.get('/documents/{document_id}/versions')
def versions(document_id: str, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    doc, allowed, context = store.get_document(db, current, document_id)
    rows = db.scalars(select(DocumentVersion).where(DocumentVersion.document_id == doc.id,
        DocumentVersion.organization_id == current.organization.id).order_by(DocumentVersion.version.desc())).all()
    return {'items': [store.out(row, context) for row in rows], 'can_write': allowed, 'current_version': doc.current_version}


@router.post('/documents/{document_id}/versions', status_code=201)
async def upload_version(document_id: str, request: Request, filename: str, expected_version: int = Query(ge=1),
                         comment: str = Query('', max_length=500), current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    require_binary(request)
    doc, _, _ = store.get_document(db, current, document_id, True)
    return await store.save(db, current, doc.node_id, request.stream(), filename, comment,
        document_id=doc.id, expected=expected_version, project_id=doc.project_id)


class TextEdit(BaseModel):
    expected_version: int = Field(ge=1)
    content: str = Field(min_length=1, max_length=store.TEXT_LIMIT)
    comment: str = Field(default='', max_length=500)


@router.post('/documents/{document_id}/text', status_code=201)
async def edit(document_id: str, data: TextEdit, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    doc, _, _ = store.get_document(db, current, document_id, True)
    store.check_expected(doc, data.expected_version)
    row, _, _ = store.get_version(db, current, doc.id, doc.current_version)
    if Path(row.filename).suffix.lower() not in {'.txt', '.csv'} or row.size_bytes > store.TEXT_LIMIT:
        raise HTTPException(415, '此格式請上傳新版本')
    content = data.content.encode('utf-8')
    if len(content) > store.TEXT_LIMIT:
        raise HTTPException(413, '文字編輯上限1MB')
    async def chunks():
        yield content
    return await store.save(db, current, doc.node_id, chunks(), row.filename, data.comment,
        document_id=doc.id, expected=data.expected_version, project_id=doc.project_id)


@router.get('/documents/{document_id}/versions/{version}/text')
def text(document_id: str, version: int, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    row, _, _ = store.get_version(db, current, document_id, version)
    if Path(row.filename).suffix.lower() not in {'.txt', '.csv'} or row.size_bytes > store.TEXT_LIMIT:
        raise HTTPException(415, '此格式請下載查看')
    return {'content': store.version_path(row).read_text(encoding='utf-8')}


@router.get('/documents/{document_id}/versions/{version}/download')
def download(document_id: str, version: int, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    row, _, _ = store.get_version(db, current, document_id, version)
    return FileResponse(store.version_path(row), media_type='application/octet-stream', headers={
        'Content-Disposition': "attachment; filename*=UTF-8''" + quote(row.filename, safe=''),
        'X-Content-Type-Options': 'nosniff'})


@router.get('/projects/{project_id}/documents')
def project_listing(project_id: str, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    allowed, context = store.permission(db, current, None, project_id=project_id)
    rows = db.scalars(select(DocumentVersion).join(Document, Document.id == DocumentVersion.document_id).where(
        Document.organization_id == current.organization.id, Document.project_id == project_id,
        Document.node_id.is_(None), DocumentVersion.version == Document.current_version).order_by(DocumentVersion.created_at.desc())).all()
    return {'items': [store.out(row, context) for row in rows], 'can_write': allowed}


@router.post('/projects/{project_id}/documents', status_code=201)
async def project_upload(project_id: str, request: Request, filename: str, comment: str = Query('', max_length=500),
                         current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    require_binary(request)
    return await store.save(db, current, None, request.stream(), filename, comment, project_id=project_id)
