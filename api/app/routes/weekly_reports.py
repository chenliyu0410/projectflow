"""Weekly report tab: owners/admins generate, edit and confirm drafts; other manager roles read sent reports."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import CurrentUser, require_session
from app.database import get_session
from app.models import User, WeeklyReport
from app.permissions import can_work_project
from app.routes.projects import get_project_or_404
from app.services import weekly_report_service as service

router = APIRouter(tags=['weekly-reports'])


class SectionsIn(BaseModel):
    sections: dict


class ConfirmIn(BaseModel):
    sections: dict | None = None


def out(report, names):
    return {'id': report.id, 'week_start': report.week_start.isoformat(), 'status': report.status, 'sections': report.sections,
            'facts': {k: v for k, v in report.facts.items() if k != 'node_ids'}, 'excluded_count': report.excluded_count,
            'model_label': report.model_label, 'recipients': [names.get(i, '已刪除帳號') for i in report.recipient_ids],
            'generated_by': names.get(report.generated_by), 'generated_at': report.generated_at.isoformat(),
            'confirmed_by': names.get(report.confirmed_by), 'confirmed_at': report.confirmed_at.isoformat() if report.confirmed_at else None}


def names_of(db, current):
    return {u.id: u.display_name for u in db.scalars(select(User).where(User.organization_id == current.organization.id))}


def managed_report(db, current, report_id):
    report = db.scalar(select(WeeklyReport).where(WeeklyReport.id == report_id, WeeklyReport.organization_id == current.organization.id))
    if report is None:
        raise HTTPException(404, '找不到週報')
    project = get_project_or_404(db, current, report.project_id)
    if not can_work_project(current, project):
        raise HTTPException(403, '只有專案負責人或管理者可以處理週報')
    return project, report


@router.get('/projects/{project_id}/weekly-reports')
def listing(project_id: str, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    project = get_project_or_404(db, current, project_id)
    manage = can_work_project(current, project)
    if not manage and current.user.role not in service.MANAGER_ROLES:
        raise HTTPException(403, '一般成員請看每日摘要')
    rows = db.scalars(select(WeeklyReport).where(WeeklyReport.organization_id == current.organization.id, WeeklyReport.project_id == project.id)
                      .order_by(WeeklyReport.week_start.desc()))
    names = names_of(db, current)
    return {'can_manage': manage, 'items': [out(r, names) for r in rows if manage or r.status == 'sent']}


@router.post('/projects/{project_id}/weekly-reports/generate', status_code=201)
def generate(project_id: str, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    project = get_project_or_404(db, current, project_id)
    if not can_work_project(current, project):
        raise HTTPException(403, '只有專案負責人或管理者可以產生週報')
    report = service.generate(db, current.organization, project, current)
    db.commit()
    return out(report, names_of(db, current))


@router.patch('/weekly-reports/{report_id}')
def edit(report_id: str, payload: SectionsIn, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    project, report = managed_report(db, current, report_id)
    if report.status != 'draft':
        raise HTTPException(409, '只有草稿可以修改')
    report.sections = service.clean_sections(payload.sections)
    db.commit()
    return out(report, names_of(db, current))


@router.post('/weekly-reports/{report_id}/confirm')
def confirm(report_id: str, payload: ConfirmIn, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    project, report = managed_report(db, current, report_id)
    removed = service.confirm(db, current, project, report, payload.sections)
    db.commit()
    return {'report': out(report, names_of(db, current)), 'removed': removed}
