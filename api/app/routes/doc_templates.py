from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.auth import CurrentUser, require_session
from app.database import get_session
from app.routes.documents import require_binary
from app.services import attachment_store as files
from app.services import doc_template_service as service

router = APIRouter(tags=['document-templates'])


async def body(request):
    require_binary(request)
    data = bytearray()
    async for chunk in request.stream():
        data += chunk
        if len(data) > files.MAX_BYTES:
            from fastapi import HTTPException
            raise HTTPException(413, '單一檔案不可超過10MB')
    return bytes(data)


@router.get('/document-templates')
def listing(current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    return service.listing(db, current)


@router.post('/document-templates', status_code=201)
async def create(request: Request, filename: str, name: str = Query(max_length=100), category: str = Query('', max_length=50),
                 current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    service.require_admin(current)
    return service.create(db, current, await body(request), filename, name, category)


@router.post('/document-templates/samples', status_code=201)
def samples(current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    return service.add_samples(db, current)


@router.post('/document-templates/{template_id}/file', status_code=201)
async def replace_file(template_id: str, request: Request, filename: str, expected_version: int = Query(ge=1),
                       current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    service.load(db, current, template_id, manage=True)
    return service.replace_file(db, current, template_id, await body(request), filename, expected_version)


class FieldSetting(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(min_length=1, max_length=50)
    label: str = Field(max_length=100)
    type: str
    required: bool = Field(strict=True)
    unit: str = Field(default='', max_length=30)
    options: list[str] = Field(default_factory=list, max_length=50)


class Settings(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_version: int = Field(ge=1)
    name: str = Field(max_length=100)
    category: str = Field(default='', max_length=50)
    fields: list[FieldSetting] = Field(max_length=service.MAX_FIELDS)
    numbering: str = Field(max_length=60)
    tax_rate: str = Field(max_length=10)
    rounding: str = Field(max_length=10)


@router.put('/document-templates/{template_id}')
def update(template_id: str, data: Settings, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    payload = data.model_dump()
    return service.update_settings(db, current, template_id, payload)


class Status(BaseModel):
    model_config = ConfigDict(extra='forbid')
    status: Literal['active', 'disabled', 'deleted']


@router.post('/document-templates/{template_id}/status')
def status(template_id: str, data: Status, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    return service.set_status(db, current, template_id, data.status)


@router.get('/document-templates/{template_id}/download')
def download(template_id: str, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    template = service.load(db, current, template_id, manage=True)
    version = service.current_version(db, template)
    return Response(service.read_file(version), media_type='application/octet-stream', headers={
        'Content-Disposition': "attachment; filename*=UTF-8''" + quote(version.filename, safe=''),
        'X-Content-Type-Options': 'nosniff'})


class Fill(BaseModel):
    model_config = ConfigDict(extra='forbid')
    template_id: str = Field(min_length=1, max_length=36)
    values: dict[str, str | int | float | None] = Field(default_factory=dict, max_length=service.MAX_FIELDS)
    lines: list[dict[str, str | int | float | None]] = Field(default_factory=list, max_length=service.MAX_LINES)


@router.post('/nodes/{node_id}/documents/from-template', status_code=201)
async def node_generate(node_id: str, data: Fill, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    return await service.generate(db, current, data.template_id, data.values, data.lines, node_id=node_id)


@router.post('/projects/{project_id}/documents/from-template', status_code=201)
async def project_generate(project_id: str, data: Fill, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    return await service.generate(db, current, data.template_id, data.values, data.lines, project_id=project_id)


@router.get('/documents/{document_id}/fill')
def fill(document_id: str, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    return service.fill_detail(db, current, document_id)


class Refill(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_version: int = Field(ge=1)
    values: dict[str, str | int | float | None] = Field(default_factory=dict, max_length=service.MAX_FIELDS)
    lines: list[dict[str, str | int | float | None]] = Field(default_factory=list, max_length=service.MAX_LINES)


@router.post('/documents/{document_id}/regenerate', status_code=201)
async def regenerate(document_id: str, data: Refill, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    return await service.regenerate(db, current, document_id, data.expected_version, data.values, data.lines)
