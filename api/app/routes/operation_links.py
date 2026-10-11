"""Live operations associations, authorized at both ends on every request."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.auth import CurrentUser, require_session
from app.database import get_session
from app.models import OperationLink, OperationsRecord
from app.audit import log_audit
from app.routes.operations import get_record, output, visible
from app.services.dependency_service import lock_project
from app.services.report_service import lock_node
from app.services.record_policy import can_write_record
from app.permissions import can_manage_project

router = APIRouter(tags=['operation-links'])


class LinkWrite(BaseModel):
    model_config = ConfigDict(extra='forbid')
    record_id: str = Field(min_length=1, max_length=36)


def scope(db, current, project_id, node_id, write=False):
    if node_id and project_id:
        raise HTTPException(422, "不可混用專案與節點範圍")
    if node_id:
        node, project, context = lock_node(db, current, node_id)
        allowed = can_write_record(db, current, project, node, context=context)
    else:
        project = lock_project(db, current, project_id)
        allowed = can_manage_project(current, project)
    if write and not allowed:
        raise HTTPException(403, '沒有編輯關聯的權限')
    return project.id, allowed


def filters(current, project_id, node_id):
    return (OperationLink.organization_id == current.organization.id,
            OperationLink.project_id == project_id, OperationLink.node_id == node_id)


@router.get('/projects/{project_id}/operation-links')
@router.get('/nodes/{node_id}/operation-links')
def listing(project_id: str | None = None, node_id: str | None = None,
            current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    project_id, allowed = scope(db, current, project_id, node_id)
    rows = db.scalars(select(OperationsRecord).join(OperationLink, OperationLink.record_id == OperationsRecord.id)
        .where(*filters(current, project_id, node_id), *visible(current)).order_by(OperationsRecord.category, OperationsRecord.code)).all()
    return {'items': [output(db, row) for row in rows], 'can_manage': allowed}


def mutate(db, current, project_id, node_id, record_id, remove=False):
    project_id, _ = scope(db, current, project_id, node_id, True)
    row = get_record(db, current, record_id, True)
    if row.category not in {'partners', 'orders', 'work'}:
        raise HTTPException(422, '此分類不支援關聯')
    link = db.scalar(select(OperationLink).where(*filters(current, project_id, node_id), OperationLink.record_id == record_id))
    changed = (link is not None) if remove else (link is None)
    if changed:
        if remove:
            db.delete(link)
        else:
            db.add(OperationLink(organization_id=current.organization.id, project_id=project_id,
                node_id=node_id, record_id=record_id, created_by=current.user.id))
        log_audit(db, current, 'operations.unlink' if remove else 'operations.link', node_id=node_id,
            payload={'project_id': project_id, 'record_id': record_id})
    db.commit()
    return {'ok': True, 'changed': changed}


@router.post('/projects/{project_id}/operation-links')
@router.post('/nodes/{node_id}/operation-links')
def add(payload: LinkWrite, project_id: str | None = None, node_id: str | None = None,
        current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    return mutate(db, current, project_id, node_id, payload.record_id)


@router.delete('/projects/{project_id}/operation-links/{record_id}')
@router.delete('/nodes/{node_id}/operation-links/{record_id}')
def remove(record_id: str, project_id: str | None = None, node_id: str | None = None,
           current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    return mutate(db, current, project_id, node_id, record_id, True)
