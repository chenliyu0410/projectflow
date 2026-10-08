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


def require_dependencies(db,current,node):
    predecessor=Node.__table__.alias('predecessor')
    blocked=db.scalar(select(NodeDependency.id).outerjoin(predecessor,
        (predecessor.c.id==NodeDependency.predecessor_id)&(predecessor.c.organization_id==NodeDependency.organization_id)&(predecessor.c.project_id==NodeDependency.project_id))
        .where(NodeDependency.organization_id==current.organization.id,NodeDependency.project_id==node.project_id,
               NodeDependency.successor_id==node.id,
               (predecessor.c.id.is_(None)) | predecessor.c.status.not_in(['done','skipped'])).limit(1))
    if blocked is not None:raise HTTPException(status_code=409,detail='尚有未完成的前置任務')


def edge_out(edge):
    return {key:getattr(edge,key) for key in ['id','project_id','predecessor_id','successor_id']}


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
    edge=NodeDependency(organization_id=current.organization.id,project_id=project.id,predecessor_id=payload.predecessor_id,successor_id=payload.successor_id,created_by=current.user.id)
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
