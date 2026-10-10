"""Project-serialized finish-to-start edges and non-disclosing enforcement."""
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.audit import log_audit
from app.models import Project,Node,NodeDependency
from app.permissions import can_manage_project,can_view_project,can_view_node
from app.services.record_policy import load_policy_context


def lock_project(db,current,project_id):
    project=db.scalar(select(Project).where(Project.organization_id==current.organization.id,Project.id==project_id)
                      .with_for_update().execution_options(populate_existing=True))
    if project is None or not can_view_project(current,project):raise HTTPException(status_code=404,detail='找不到專案')
    return project


def unmet_dependencies(nodes, edges, conditions, node, *, phase='start'):
    """Evaluate complete company data without exposing predecessors to callers."""
    chain = set()
    cursor = node
    while cursor is not None:
        if cursor.id in chain:
            raise HTTPException(status_code=409, detail='節點階層異常，無法變更狀態')
        chain.add(cursor.id)
        if cursor.parent_id is None:
            break
        parent = nodes.get(cursor.parent_id)
        if parent is None or parent.project_id != node.project_id:
            raise HTTPException(status_code=409, detail='節點階層異常，無法變更狀態')
        cursor = parent
    unmet = []
    for edge in edges:
        if edge.project_id != node.project_id:
            continue
        is_finish = edge.relation_type == 'FF'
        relevant = (phase == 'finish' and edge.successor_id == node.id) if is_finish else edge.successor_id in chain
        if not relevant:
            continue
        pred = nodes.get(edge.predecessor_id)
        statuses = {'doing', 'review', 'done', 'skipped'} if edge.relation_type == 'SS' else {'done', 'skipped'}
        if pred is None or pred.project_id != node.project_id or pred.status not in statuses:
            unmet.append(edge)
    # Manual conditions only guard the transition out of todo, never retroactively stop an active task.
    if node.status == 'todo':
        unmet.extend(c for c in conditions if c.project_id == node.project_id and c.node_id in chain and not c.is_met)
    return unmet


def dependency_state(db, current, node, phase='start'):
    from app.models import NodeCondition
    nodes = {n.id: n for n in db.scalars(select(Node).where(Node.organization_id == current.organization.id, Node.project_id == node.project_id))}
    edges = list(db.scalars(select(NodeDependency).where(NodeDependency.organization_id == current.organization.id, NodeDependency.project_id == node.project_id)))
    conditions = list(db.scalars(select(NodeCondition).where(NodeCondition.organization_id == current.organization.id, NodeCondition.project_id == node.project_id)))
    return unmet_dependencies(nodes, edges, conditions, node, phase=phase)


def require_dependencies(db, current, node, phase='start'):
    unmet = dependency_state(db, current, node, phase)
    if any(item.enforcement == 'hard' for item in unmet):
        raise HTTPException(status_code=409, detail='尚有未完成的前置任務')
    return ['軟性前置尚未滿足，仍可繼續'] if unmet else []


def edge_out(edge):
    return {key:getattr(edge,key) for key in ['id','project_id','predecessor_id','successor_id','relation_type','lag_days','enforcement']}


def create_edge(db,current,project_id,payload):
    project=lock_project(db,current,project_id)
    if not can_manage_project(current,project):raise HTTPException(status_code=403,detail='沒有設定前置任務權限')
    context=load_policy_context(db,current)
    ids={payload.predecessor_id,payload.successor_id}
    nodes={n.id:n for n in db.scalars(select(Node).where(Node.organization_id==current.organization.id,Node.project_id==project.id,Node.id.in_(ids)).order_by(Node.id).with_for_update())}
    if len(nodes)!=len(ids) or any(not can_view_node(current,n,context=context) for n in nodes.values()):raise HTTPException(status_code=404,detail='找不到任務')
    if len(ids)!=2 or any(n.kind!='task' for n in nodes.values()):raise HTTPException(status_code=422,detail='前置必須是兩個不同任務')
    rows=list(db.scalars(select(NodeDependency).where(NodeDependency.organization_id==current.organization.id,NodeDependency.project_id==project.id)))
    outgoing={}
    for row in rows:
        if row.predecessor_id==payload.predecessor_id and row.successor_id==payload.successor_id:raise HTTPException(status_code=409,detail='前置連線已存在')
        outgoing.setdefault(row.predecessor_id,[]).append(row.successor_id)
    pending=[payload.successor_id];visited=set()
    while pending:
        nid=pending.pop()
        if nid==payload.predecessor_id:raise HTTPException(status_code=409,detail='前置任務不可循環')
        if nid not in visited:visited.add(nid);pending.extend(outgoing.get(nid,[]))
    edge=NodeDependency(organization_id=current.organization.id,project_id=project.id,predecessor_id=payload.predecessor_id,successor_id=payload.successor_id,created_by=current.user.id,
                        relation_type=payload.relation_type, lag_days=payload.lag_days, enforcement=payload.enforcement)
    db.add(edge);db.flush()
    log_audit(db,current,'dependency.create',node_id=edge.successor_id,payload=edge_out(edge))
    db.commit();return edge_out(edge)


def delete_edge(db,current,edge_id):
    project_id=db.scalar(select(NodeDependency.project_id).where(NodeDependency.organization_id==current.organization.id,NodeDependency.id==edge_id))
    if project_id is None:raise HTTPException(status_code=404,detail='找不到前置連線')
    project=lock_project(db,current,project_id)
    if not can_manage_project(current,project):raise HTTPException(status_code=403,detail='沒有設定前置任務權限')
    edge=db.scalar(select(NodeDependency).where(NodeDependency.organization_id==current.organization.id,NodeDependency.id==edge_id).with_for_update().execution_options(populate_existing=True))
    if edge is None:raise HTTPException(status_code=404,detail='找不到前置連線')
    context=load_policy_context(db,current)
    nodes=list(db.scalars(select(Node).where(Node.organization_id==current.organization.id,Node.project_id==project_id,Node.id.in_([edge.predecessor_id,edge.successor_id]))))
    if len(nodes)!=2 or any(not can_view_node(current,n,context=context) for n in nodes):raise HTTPException(status_code=404,detail='找不到前置連線')
    log_audit(db,current,'dependency.delete',node_id=edge.successor_id,payload=edge_out(edge))
    db.delete(edge);db.commit();return {'id':edge_id,'deleted':True}


def update_edge(db, current, edge_id, payload):
    project_id = db.scalar(select(NodeDependency.project_id).where(NodeDependency.organization_id == current.organization.id, NodeDependency.id == edge_id))
    if project_id is None:
        raise HTTPException(status_code=404, detail='找不到前置連線')
    project = lock_project(db, current, project_id)
    if not can_manage_project(current, project):
        raise HTTPException(status_code=403, detail='沒有設定前置任務權限')
    edge = db.scalar(select(NodeDependency).where(NodeDependency.organization_id == current.organization.id, NodeDependency.id == edge_id).with_for_update().execution_options(populate_existing=True))
    if edge is None:
        raise HTTPException(status_code=404, detail='找不到前置連線')
    context = load_policy_context(db, current)
    nodes = list(db.scalars(select(Node).where(Node.organization_id == current.organization.id, Node.project_id == project_id, Node.id.in_([edge.predecessor_id, edge.successor_id]))))
    if len(nodes) != 2 or any(not can_view_node(current, n, context=context) for n in nodes):
        raise HTTPException(status_code=404, detail='找不到前置連線')
    before = edge_out(edge)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(edge, key, value)
    log_audit(db, current, 'dependency.update', node_id=edge.successor_id, payload={'before': before, 'after': edge_out(edge)})
    db.commit()
    return edge_out(edge)
