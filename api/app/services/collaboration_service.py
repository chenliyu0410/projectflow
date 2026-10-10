"""Scoped exceptions: authorizations never disable dependency rules permanently."""
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.auth import CurrentUser
from app.audit import log_audit
from app.models import CollaborationRequest, Node, Gate, TaskReport, AuditLog, User, now_utc
from app.permissions import can_manage_project, can_work_node, can_view_node
from app.services.report_service import lock_node, require_gate
from app.services.node_policy import containing_phase
from app.services.dependency_service import dependency_state
from app.services.tree_service import family_of
from app.services.notification_service import emit


def family(db, current, node):
    nodes = {n.id:n for n in db.scalars(select(Node).where(Node.organization_id == current.organization.id, Node.project_id == node.project_id))}
    return [nodes[nid] for nid in family_of(nodes, node.id)]


def require_open_ancestors(db, current, node):
    containing_phase(db, current, node)
    parent = node.parent_id
    while parent:
        n = db.get(Node, parent)
        if n.status in {'done','review','skipped'}:
            raise HTTPException(409, '上層已完成、待確認或已略過，請先重新開啟上層')
        parent = n.parent_id


def can_decide(db, current, project, node, context, kind):
    if current.user.role == 'readonly' or not can_view_node(current,node,context=context): return False
    if can_manage_project(current,project): return True
    targets = family(db,current,node) if kind == 'skip' else [node]
    return all(can_view_node(current,n,context=context) and n.department_id in context.departments and context.departments[n.department_id].head_user_id == current.user.id for n in targets)


def evidence(db, current, node, kind):
    containing_phase(db,current,node)
    if kind == 'gate':
        gates = list(db.scalars(select(Gate).where(Gate.organization_id == current.organization.id, Gate.node_id == node.id)))
        return {'status': node.status, 'gates': sorted([g.id,g.status] for g in gates)}
    if kind == 'skip':
        return {'nodes': sorted([n.id,n.status,n.parent_id,n.department_id,n.owner_user_id] for n in family(db,current,node))}
    unmet = dependency_state(db,current,node,'finish' if kind in {'report_approve','report_self'} else 'start')
    blockers = sorted([type(e).__name__,e.id,str(getattr(e,'relation_type','condition')),str(getattr(e,'lag_days','')),str(getattr(e,'predecessor_id','')),str(getattr(e,'label','')),str(getattr(db.get(Node,e.predecessor_id), 'status', 'missing')) if hasattr(e,'predecessor_id') else str(e.is_met)] for e in unmet if e.enforcement == 'hard')
    children = sorted([n.id,n.status] for n in db.scalars(select(Node).where(Node.organization_id == current.organization.id, Node.parent_id == node.id, Node.status.not_in(['done','skipped'])))) if kind.startswith('report') or kind == 'phase_complete' else []
    return {'status':node.status,'blockers':blockers,'children':children}


def perform(db,current,project,node,request,context):
    kind = request.kind
    if kind != 'gate':
        require_gate(db,current,node)
        require_open_ancestors(db,current,node)
    if kind == 'skip':
        if node.kind != 'task' or node.status in {'done','skipped'}: raise HTTPException(409,'目前狀態不允許此操作，請重新整理')
        targets = family(db,current,node)
        # Do not mutate unseen descendants through a visible parent.
        if any(not can_view_node(current,n,context=context) for n in targets): raise HTTPException(403,'沒有操作完整子樹的權限')
        previous = {}
        for n in targets:
            if n.status in {'done','skipped'}: continue
            previous[n.id] = 'doing' if n.status == 'review' else n.status
            for r in db.scalars(select(TaskReport).where(TaskReport.organization_id == current.organization.id, TaskReport.node_id == n.id, TaskReport.status == 'submitted')):
                r.status='rejected';r.reviewed_by=current.user.id;r.reviewed_at=now_utc();r.review_comment='任務已跳過，回報自動結案'
                log_audit(db,current,'report.reject',node_id=n.id,payload={'report_id':r.id,'comment':r.review_comment})
            n.status='skipped'
            log_audit(db,current,'node.skip',node_id=n.id,payload={'request_id':request.id,'reason':request.reason})
        request.snapshot={'previous':previous}
    elif kind == 'start':
        if node.kind != 'task' or node.status != 'todo': raise HTTPException(409,'目前狀態不允許此操作，請重新整理')
        node.status='doing'
    elif kind == 'phase_complete':
        if node.kind != 'phase' or node.status in {'done','skipped'}: raise HTTPException(409,'目前狀態不允許此操作，請重新整理')
        node.status='done'
    elif kind == 'report_submit':
        from app.schemas import ReportCreate
        from app.services.report_service import submit_report
        requester=CurrentUser(context.users[request.requested_by],current.organization,'')
        db.info['approved_report_exception']=(node.id,request.requested_by)
        try:
            submit_report(db,requester,node.id,ReportCreate.model_validate({**request.snapshot['report'],'override_reason':request.reason,'request_override':False}),commit=False)
        finally: db.info.pop('approved_report_exception',None)
    elif kind == 'gate':
        gate=db.scalar(select(Gate).where(Gate.organization_id == current.organization.id,Gate.node_id == node.id,Gate.status == 'pending'))
        if node.kind != 'phase' or gate is None: raise HTTPException(409,'目前狀態不允許此操作，請重新整理')
        gate.status='approved'
    log_audit(db,current,'collaboration.approve',node_id=node.id,payload={'request_id':request.id,'kind':kind,'reason':request.reason})
    if kind == 'skip':
        db.flush()
        ids=list(request.snapshot['previous'])
        # Immutable audit ids form an optimistic restore fence, including notes and attachments.
        request.snapshot={**request.snapshot,'audit_ids':sorted(db.scalars(select(AuditLog.id).where(AuditLog.organization_id == current.organization.id,AuditLog.node_id.in_(ids))))}


def request_out(r, node, can_review=False):
    return {'id':r.id,'node_id':r.node_id,'node_title':node.title,'project_id':r.project_id,'kind':r.kind,'reason':r.reason,'status':r.status,'created_at':r.created_at.isoformat(),'can_review':can_review,'comment':r.comment,'report':r.snapshot.get('report') if r.kind == 'report_submit' else None}


def create(db,current,node_id,payload):
    node,project,context=lock_node(db,current,node_id)
    if current.user.role == 'readonly' or not (can_manage_project(current,project) or can_work_node(db,current,node,departments=context.departments)):
        raise HTTPException(403,'沒有申請權限')
    if payload.kind in {'gate','phase_complete'} and node.kind != 'phase' or payload.kind not in {'gate','phase_complete'} and node.kind != 'task': raise HTTPException(422,'此節點不支援此操作')
    if payload.kind != 'gate':
        require_gate(db,current,node)
        require_open_ancestors(db,current,node)
        if node.status in {'done','skipped'} or payload.kind == 'start' and node.status != 'todo': raise HTTPException(409,'目前狀態不允許此操作，請重新整理')
    if payload.direct and not can_manage_project(current,project): raise HTTPException(403,'只有專案管理者可以直接覆寫')
    if db.scalar(select(CollaborationRequest.id).where(CollaborationRequest.organization_id == current.organization.id,CollaborationRequest.node_id == node.id,CollaborationRequest.kind == payload.kind,CollaborationRequest.status == 'pending')):
        raise HTTPException(409,'已有待審核申請')
    r=CollaborationRequest(organization_id=current.organization.id,project_id=project.id,node_id=node.id,kind=payload.kind,reason=payload.reason,requested_by=current.user.id,evidence=evidence(db,current,node,payload.kind))
    if payload.kind == 'report_submit':
        if node.id in context.pending_reports or node.status not in {'todo','doing'}: raise HTTPException(409,'目前狀態不允許此操作，請重新整理')
        from app.schemas import ReportCreate
        report=payload.report
        if report.self_approve: raise HTTPException(422,'申請覆寫仍須由他人確認完成回報')
        r.snapshot={'report':report.model_dump(mode='json')}
    db.add(r);db.flush()
    log_audit(db,current,'collaboration.request',node_id=node.id,payload={'request_id':r.id,'kind':r.kind,'reason':r.reason})
    if payload.direct:
        r.status='approved';r.decided_by=current.user.id;r.decided_at=now_utc()
        perform(db,current,project,node,r,context)
    else:
        for user in context.users.values():
            reviewer=CurrentUser(user,current.organization,'')
            from app.services.record_policy import load_policy_context
            if can_decide(db,reviewer,project,node,load_policy_context(db,reviewer),r.kind):
                emit(db,current,node,user.id,'有新的跳過／覆寫申請待審核',r.id+':requested')
    try: db.commit()
    except IntegrityError:
        db.rollback();raise HTTPException(409,'已有待審核申請')
    return request_out(r,node)


def expire(db,current,node,r):
    r.status='expired';r.decided_by=current.user.id;r.decided_at=now_utc();r.comment='申請內容已變更，請重新申請'
    log_audit(db,current,'collaboration.expire',node_id=node.id,payload={'request_id':r.id})
    emit(db,current,node,r.requested_by,r.comment,r.id+':expired')
    db.commit()
    raise HTTPException(409,'申請已失效結案，請重新申請')


def decide(db,current,request_id,payload):
    r=db.scalar(select(CollaborationRequest).where(CollaborationRequest.organization_id == current.organization.id,CollaborationRequest.id == request_id))
    if r is None: raise HTTPException(404,'找不到申請')
    node,project,context=lock_node(db,current,r.node_id)
    db.refresh(r,with_for_update=True)
    if r.status != 'pending': raise HTTPException(409,'申請已處理，請重新整理')
    if r.requested_by == current.user.id or not can_decide(db,current,project,node,context,r.kind): raise HTTPException(403,'沒有核准此申請的權限')
    if payload.decision == 'approved':
        if r.kind == 'report_submit' and (node.id in context.pending_reports or node.status not in {'todo','doing'}): expire(db,current,node,r)
        requester=context.users.get(r.requested_by)
        if requester is None or requester.role == 'readonly': expire(db,current,node,r)
        requester_current=CurrentUser(requester,current.organization,'')
        from app.services.record_policy import load_policy_context
        requester_context=load_policy_context(db,requester_current)
        if not can_view_node(requester_current,node,context=requester_context) or not (can_manage_project(requester_current,project) or can_work_node(db,requester_current,node,departments=requester_context.departments)):
            expire(db,current,node,r)
    if payload.decision == 'approved' and evidence(db,current,node,r.kind) != r.evidence:
        # JSON snapshots use lists, never tuples, so comparisons survive database round trips.
        expire(db,current,node,r)
    r.status=payload.decision;r.decided_by=current.user.id;r.decided_at=now_utc();r.comment=payload.comment
    if payload.decision == 'approved': perform(db,current,project,node,r,context)
    else: log_audit(db,current,'collaboration.reject',node_id=node.id,payload={'request_id':r.id,'comment':payload.comment})
    emit(db,current,node,r.requested_by,'你的跳過／覆寫申請已'+('核准' if payload.decision == 'approved' else '退回'),r.id+':decision')
    db.commit()
    return request_out(r,node)


def restore(db,current,node_id,reason):
    node,project,context=lock_node(db,current,node_id)
    if not can_manage_project(current,project): raise HTTPException(403,'沒有管理此任務的權限')
    r=db.scalar(select(CollaborationRequest).where(CollaborationRequest.organization_id == current.organization.id,CollaborationRequest.node_id == node.id,CollaborationRequest.kind == 'skip',CollaborationRequest.status == 'approved',CollaborationRequest.restored_at.is_(None)).order_by(CollaborationRequest.created_at.desc()))
    if r is None: return None
    require_open_ancestors(db,current,node)
    previous=r.snapshot.get('previous',{})
    targets={n.id:n for n in family(db,current,node)}
    audit_ids=sorted(db.scalars(select(AuditLog.id).where(AuditLog.organization_id == current.organization.id,AuditLog.node_id.in_(previous))))
    if audit_ids != r.snapshot.get('audit_ids') or any(nid not in targets or targets[nid].status != 'skipped' for nid in previous): raise HTTPException(409,'跳過後已有修改，無法整組恢復')
    for nid,status in previous.items():
        targets[nid].status=status
        log_audit(db,current,'node.restore',node_id=nid,payload={'request_id':r.id,'reason':reason})
    r.restored_at=now_utc();db.commit()
    from app.services.node_policy import node_out
    return node_out(db,current,project,node,context=context)


def check_report_override(db,current,project,node,reason,phase):
    if not reason: return False
    reason=reason.strip()
    if not reason: raise HTTPException(422,'覆寫理由必填')
    from app.services.record_policy import load_policy_context
    context=load_policy_context(db,current)
    approved = phase == 'submit' and db.info.get('approved_report_exception') == (node.id,current.user.id)
    if not approved and not (can_manage_project(current,project) if phase in {'submit','self'} else can_decide(db,current,project,node,context,'report_'+phase)): raise HTTPException(403,'沒有覆寫此回報的權限')
    require_gate(db,current,node);require_open_ancestors(db,current,node)
    r=CollaborationRequest(organization_id=current.organization.id,project_id=project.id,node_id=node.id,kind='report_'+phase,reason=reason,requested_by=current.user.id,status='approved',decided_by=current.user.id,decided_at=now_utc(),evidence=evidence(db,current,node,'report_'+phase))
    db.add(r)
    log_audit(db,current,'collaboration.override',node_id=node.id,payload={'kind':r.kind,'reason':reason})
    return True
