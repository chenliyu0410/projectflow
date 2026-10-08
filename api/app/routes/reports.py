from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth import CurrentUser, require_session
from app.database import get_session
from app.schemas import ReportCreate, ReportReview, NodeLifecycle
from app.services import report_service

router = APIRouter(tags=["reports"])


@router.post("/nodes/{node_id}/reports", status_code=status.HTTP_201_CREATED)
def submit_report(node_id: str, payload: ReportCreate, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    return report_service.submit_report(db, current, node_id, payload)


@router.post("/reports/{report_id}/review")
def review_report(report_id: str, payload: ReportReview, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    return report_service.review_report(db, current, report_id, payload)


@router.post("/nodes/{node_id}/lifecycle")
def lifecycle(node_id: str, payload: NodeLifecycle, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    return report_service.lifecycle(db, current, node_id, payload)
