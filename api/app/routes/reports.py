from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import log_audit
from app.auth import CurrentUser, require_session
from app.database import get_session
from app.models import Node, TaskReport
from app.permissions import can_work_node
from app.schemas import ReportCreate

router = APIRouter(tags=["reports"])


@router.post("/nodes/{node_id}/reports", status_code=status.HTTP_201_CREATED)
def submit_report(node_id: str, payload: ReportCreate, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    node = db.execute(select(Node).where(Node.organization_id == current.organization.id, Node.id == node_id)).scalar_one_or_none()
    if node is None:
        raise HTTPException(status_code=404, detail="找不到節點")
    if not can_work_node(db, current, node):
        raise HTTPException(status_code=403, detail="沒有回報此節點的權限")
    if not payload.result.strip() or not payload.summary.strip():
        raise HTTPException(status_code=422, detail="回報結果與摘要必填")
    report = TaskReport(
        organization_id=current.organization.id,
        node_id=node.id,
        result=payload.result,
        summary=payload.summary,
        status="submitted",
        submitted_by=current.user.id,
    )
    db.add(report)
    db.flush()
    log_audit(db, current, "report.submit", node_id=node.id, payload={"report_id": report.id, "result": payload.result})
    db.commit()
    db.refresh(report)
    return {
        "id": report.id,
        "node_id": report.node_id,
        "result": report.result,
        "summary": report.summary,
        "status": report.status,
        "submitted_by": report.submitted_by,
        "submitted_at": report.submitted_at.isoformat(),
    }
