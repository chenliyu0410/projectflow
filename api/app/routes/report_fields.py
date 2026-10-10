from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.auth import CurrentUser, require_session
from app.database import get_session
from app.schemas import ReportFieldsUpdate
from app.services import report_field_service as service
from app.services.report_service import lock_node

router = APIRouter()


@router.get('/nodes/{node_id}/report-fields')
def read(node_id: str, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    node, project, context = lock_node(db, current, node_id)
    return service.output(db, current, project, node, context)


@router.put('/nodes/{node_id}/report-fields')
def update(node_id: str, payload: ReportFieldsUpdate, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    return service.update(db, current, node_id, payload)
