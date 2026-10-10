"""Node-serialized report and lifecycle transactions."""
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit import log_audit
from app.services.dependency_service import lock_project, require_dependencies
from app.services.attachment_store import bind_attachments, attachments_for, attachment_out
from app.auth import CurrentUser
from app.models import Node, Project, TaskReport, now_utc
from app.permissions import can_manage_project, can_view_node, can_view_project
from app.services.node_policy import containing_phase, pending_gate_for_node, node_out, require_children_finished
from app.services.record_policy import load_policy_context, can_submit_report, can_review_report, can_self_approve_report


def conflict():
    raise HTTPException(status_code=409, detail="目前狀態不允許此操作，請重新整理")


def lock_node(db: Session, current: CurrentUser, node_id: str, *, require_visible=True):
    project_id = db.scalar(select(Node.project_id).where(Node.id == node_id, Node.organization_id == current.organization.id))
    if project_id is None:
        raise HTTPException(status_code=404, detail="找不到節點")
    # Global order: optional AttachmentQuota -> Project -> Node -> Attachment.
    project = lock_project(db, current, project_id)
    node = db.scalar(select(Node).where(Node.id == node_id, Node.organization_id == current.organization.id, Node.project_id == project.id)
                     .with_for_update().execution_options(populate_existing=True))
    if node is None:
        raise HTTPException(status_code=404, detail="找不到節點")
    context = load_policy_context(db, current)
    if project is None or not can_view_project(current, project) or (require_visible and not can_view_node(current, node, context=context)):
        raise HTTPException(status_code=404, detail="找不到節點")
    return node, project, context


def require_gate(db, current, node):
    if pending_gate_for_node(db, current, node):
        raise HTTPException(status_code=409, detail="前一階段閘門尚未通過")


def report_out(report, node, context, attachments=()):
    author = context.users.get(report.submitted_by)
    reviewer = context.users.get(report.reviewed_by)
    return {
        'id': report.id, 'node_id': report.node_id, 'result': report.result, 'summary': report.summary,
        'fields': report.fields, 'status': report.status, 'version': report.version, 'legacy': report.workflow_version != 2,
        'finished_on': report.finished_on.isoformat() if report.finished_on else None,
        'submitted_by': report.submitted_by, 'submitted_by_display_name': author.display_name if author else None,
        'submitted_at': report.submitted_at.isoformat(),
        'reviewed_by': report.reviewed_by, 'reviewed_by_display_name': reviewer.display_name if reviewer else None,
        'reviewed_at': report.reviewed_at.isoformat() if report.reviewed_at else None,
        'review_comment': report.review_comment, 'self_approved': report.self_approved,
        'dependency_warnings': ['軟性前置尚未滿足，仍可繼續'] if node.id in context.soft_warning_ids else [],
        'node_status': node.status, 'attachments': [attachment_out(a, context.users) for a in attachments if a.report_id == report.id],
    }


def submit_report(db, current, node_id, payload, *, commit=True):
    if payload.request_override:
        if not payload.override_reason or not payload.override_reason.strip(): raise HTTPException(422,'覆寫理由必填')
        from app.routes.collaboration import RequestWrite
        from app.services.collaboration_service import create
        return create(db,current,node_id,RequestWrite(kind='report_submit',reason=payload.override_reason,report=payload.model_dump(mode='json')))

    node, project, context = lock_node(db, current, node_id)
    if not can_submit_report(db, current, project, node, context=context):
        raise HTTPException(status_code=403, detail="沒有回報此節點的權限")
    if payload.self_approve and not can_self_approve_report(db, current, project, node, context=context):
        raise HTTPException(status_code=403, detail="沒有送出並確認權限")
    if node.status not in {'todo', 'doing', 'review'} or node.id in context.pending_reports:
        conflict()
    require_gate(db, current, node)
    from app.services.collaboration_service import check_report_override, require_open_ancestors
    require_open_ancestors(db,current,node)
    if not check_report_override(db,current,project,node,payload.override_reason,'self' if payload.self_approve else 'submit'):
        require_dependencies(db, current, node, 'finish' if payload.self_approve else 'start')
        require_children_finished(db, current, node)
    from app.services.report_field_service import snapshot
    fields = snapshot(db, node, payload)
    report = TaskReport(fields=fields, organization_id=current.organization.id, node_id=node.id,
        result=payload.result, summary=payload.summary, finished_on=payload.finished_on,
        submitted_by=current.user.id, workflow_version=2, version=context.latest_versions.get(node.id, 0) + 1,
        status='approved' if payload.self_approve else 'submitted', self_approved=payload.self_approve,
        reviewed_by=current.user.id if payload.self_approve else None,
        reviewed_at=now_utc() if payload.self_approve else None)
    db.add(report)
    try:
        db.flush()
        bind_attachments(db, current, node, payload.attachment_ids, report_id=report.id)
        node.status = 'done' if payload.self_approve else 'review'
        log_audit(db, current, 'report.submit', node_id=node.id, payload={'report_id':report.id,'version':report.version,'result':report.result})
        if payload.self_approve:
            log_audit(db, current, 'report.approve', node_id=node.id, payload={'report_id':report.id,'version':report.version,'self_approved':True})
        if commit: db.commit()
        else: db.flush()
    except IntegrityError:
        db.rollback()
        conflict()
    db.refresh(report)
    return report_out(report, node, context, attachments_for(db, current.organization.id, [node.id]))


def review_report(db, current, report_id, payload):
    node_id = db.scalar(select(TaskReport.node_id).where(TaskReport.id == report_id, TaskReport.organization_id == current.organization.id))
    if node_id is None:
        raise HTTPException(status_code=404, detail="找不到回報")
    node, project, context = lock_node(db, current, node_id)
    report = db.scalar(select(TaskReport).where(TaskReport.id == report_id, TaskReport.organization_id == current.organization.id)
                       .with_for_update().execution_options(populate_existing=True))
    if not can_review_report(db, current, project, node, context=context):
        raise HTTPException(status_code=403, detail="沒有審核此回報的權限")
    if not can_review_report(db, current, project, node, report, context=context):
        conflict()
    if payload.decision == 'approved':
        require_gate(db, current, node)
        from app.services.collaboration_service import check_report_override, require_open_ancestors
        require_open_ancestors(db,current,node)
        if not check_report_override(db,current,project,node,payload.override_reason,'approve'):
            require_dependencies(db, current, node, 'finish')
            require_children_finished(db, current, node)
    else:
        containing_phase(db, current, node)
    report.status = payload.decision
    report.reviewed_by = current.user.id
    report.reviewed_at = now_utc()
    report.review_comment = payload.comment
    node.status = 'done' if payload.decision == 'approved' else 'doing'
    log_audit(db, current, 'report.approve' if payload.decision == 'approved' else 'report.reject', node_id=node.id,
              payload={'report_id':report.id,'version':report.version,'comment':payload.comment,'self_approved':False})
    db.commit()
    db.refresh(report)
    return report_out(report, node, context, attachments_for(db, current.organization.id, [node.id]))


def lifecycle(db, current, node_id, payload):
    from app.services import collaboration_service
    if payload.action == 'skip':
        from types import SimpleNamespace
        collaboration_service.create(db,current,node_id,SimpleNamespace(kind='skip',reason=payload.reason,direct=True))
        node,project,context=lock_node(db,current,node_id)
        return node_out(db,current,project,node,context=context)
    if payload.action == 'restore':
        restored=collaboration_service.restore(db,current,node_id,payload.reason)
        if restored is not None: return restored
    node, project, context = lock_node(db, current, node_id)
    if not can_manage_project(current, project):
        raise HTTPException(status_code=403, detail="沒有管理此任務的權限")
    valid_sources = {'reopen':{'done','review'}, 'skip':{'todo','doing'}, 'restore':{'skipped'}}
    if node.kind != 'task' or node.status not in valid_sources[payload.action] or node.id in context.pending_reports:
        conflict()
    require_gate(db, current, node)
    if payload.action in {'reopen', 'restore'} and node.parent_id is not None:
        # D74: a closed parent cannot regain an open child; reopen the parent first.
        parent = db.scalar(select(Node).where(Node.organization_id == current.organization.id, Node.id == node.parent_id))
        if parent is not None and parent.status in {'review', 'done', 'skipped'}:
            raise HTTPException(status_code=409, detail="上層已完成、待確認或已略過，請先重新開啟上層")
    node.status = 'skipped' if payload.action == 'skip' else 'doing'
    log_audit(db, current, f'node.{payload.action}', node_id=node.id, payload={'reason':payload.reason})
    db.commit()
    db.refresh(node)
    return node_out(db, current, project, node, context=context)
