from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.auth import CurrentUser,require_session
from app.database import get_session
from app.models import Node,Project,NodeDependency,NodeCondition
from app.permissions import can_manage_project,can_view_project,can_view_node
from app.schemas import DependencyCreate, DependencySettings
from app.services.record_policy import load_policy_context
from app.services.dependency_service import create_edge,delete_edge,edge_out,update_edge
router=APIRouter(tags=['dependencies'])


@router.get('/projects/{project_id}/dependencies')
def list_dependencies(project_id:str,current:CurrentUser=Depends(require_session),db:Session=Depends(get_session)):
    project=db.scalar(select(Project).where(Project.id==project_id,Project.organization_id==current.organization.id))
    if project is None or not can_view_project(current,project):raise HTTPException(status_code=404,detail='找不到專案')
    context=load_policy_context(db,current)
    nodes={n.id:n for n in db.scalars(select(Node).where(Node.organization_id==current.organization.id,Node.project_id==project_id,Node.kind=='task').order_by(Node.sort_order,Node.id)) if can_view_node(current,n,context=context)}
    edges=db.scalars(select(NodeDependency).where(NodeDependency.organization_id==current.organization.id,NodeDependency.project_id==project_id).order_by(NodeDependency.id))
    from app.services.condition_service import condition_out
    conditions = db.scalars(select(NodeCondition).where(NodeCondition.organization_id == current.organization.id, NodeCondition.project_id == project_id).order_by(NodeCondition.created_at, NodeCondition.id))
    return {'conditions': [condition_out(c) for c in conditions if c.node_id in nodes], 'items':[edge_out(e) for e in edges if e.predecessor_id in nodes and e.successor_id in nodes],
            'nodes':[{'id':n.id,'title':n.title,'status':n.status,'blocked':n.id in context.blocked_node_ids} for n in nodes.values()],
            'capabilities':{'manage':can_manage_project(current,project)}}


@router.post('/projects/{project_id}/dependencies',status_code=201)
def add_dependency(project_id:str,payload:DependencyCreate,current:CurrentUser=Depends(require_session),db:Session=Depends(get_session)):
    return create_edge(db,current,project_id,payload)


@router.delete('/dependencies/{dependency_id}')
def remove_dependency(dependency_id:str,current:CurrentUser=Depends(require_session),db:Session=Depends(get_session)):
    return delete_edge(db,current,dependency_id)


@router.patch('/dependencies/{dependency_id}')
def edit_dependency(dependency_id: str, payload: DependencySettings, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    return update_edge(db, current, dependency_id, payload)
