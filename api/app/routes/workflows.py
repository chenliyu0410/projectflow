from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import log_audit
from app.auth import CurrentUser, require_session
from app.database import get_session
from app.models import Gate, Node, Project, Workflow, WorkflowNode
from app.permissions import can_work_node, can_work_project, can_view_node
from app.schemas import GateStatusUpdate, ProjectFromWorkflowCreate, WorkflowWrite, WorkflowCopy
from app.services import workflow_service as service

router = APIRouter(tags=["workflows"])


@router.get('/workflows')
def list_workflows(current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    items=[]
    for workflow in db.scalars(select(Workflow).where(Workflow.organization_id==current.organization.id,Workflow.deleted_at.is_(None)).order_by(Workflow.name,Workflow.id)):
        value=service.detail(db,current,workflow)
        items.append({**{key:value[key] for key in ['id','name','kind','version','requires_start_date','capabilities']}, 'phase_count': sum(n['kind']=='phase' for n in value['nodes']), 'task_count': sum(n['kind']=='task' for n in value['nodes']), 'phase_titles': [n['title'] for n in value['nodes'] if n['kind']=='phase']})
    return {'items':items,'capabilities':{'create':service.can_edit(current)}}


@router.get('/workflows/{workflow_id}')
def get_workflow(workflow_id: str,current: CurrentUser = Depends(require_session),db: Session = Depends(get_session)):
    return service.detail(db,current,service.get_workflow(db,current,workflow_id))


@router.post('/workflows',status_code=201)
def create_workflow(payload: WorkflowWrite,current: CurrentUser = Depends(require_session),db: Session = Depends(get_session)):
    return service.save(db,current,payload)


@router.put('/workflows/{workflow_id}')
def update_workflow(workflow_id: str,payload: WorkflowWrite,current: CurrentUser = Depends(require_session),db: Session = Depends(get_session)):
    return service.save(db,current,payload,service.get_workflow(db,current,workflow_id,lock=True))


@router.post('/workflows/{workflow_id}/copy',status_code=201)
def copy_workflow(workflow_id: str,payload: WorkflowCopy,current: CurrentUser = Depends(require_session),db: Session = Depends(get_session)):
    source=service.get_workflow(db,current,workflow_id,lock=True)
    copied=service.read_payload(db,source)
    copied.name=payload.name or (source.name[:156]+'（複本）')
    return service.save(db,current,copied,copy_source=source.id)


@router.post('/projects/from-workflow',status_code=201)
def create_project_from_workflow(payload: ProjectFromWorkflowCreate,current: CurrentUser = Depends(require_session),db: Session = Depends(get_session)):
    return service.instantiate(db,current,payload)


@router.patch("/gates/{gate_id}")
def update_gate(gate_id: str, payload: GateStatusUpdate, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    gate = db.execute(select(Gate).where(Gate.organization_id == current.organization.id, Gate.id == gate_id)).scalar_one_or_none()
    if gate is None:
        raise HTTPException(status_code=404, detail="找不到閘門")
    from app.services.dependency_service import lock_project
    project = lock_project(db,current,gate.project_id)
    db.refresh(gate,with_for_update=True)
    node = db.execute(select(Node).where(Node.organization_id == current.organization.id, Node.id == gate.node_id)).scalar_one_or_none()
    from app.services.record_policy import load_policy_context
    if node is None or not can_view_node(current,node,context=load_policy_context(db,current)):raise HTTPException(status_code=404,detail="找不到閘門")
    scoped_reviewer = current.user.role == "reviewer" and can_work_node(db, current, node)
    if current.user.role == "readonly" or (not can_work_project(current, project) and not scoped_reviewer):
        raise HTTPException(status_code=403, detail="沒有核准閘門權限")
    gate.status = payload.status
    log_audit(db, current, "gate.approve", node_id=gate.node_id, payload={"gate_id": gate.id, "status": payload.status})
    db.commit()
    db.refresh(gate)
    return {"id": gate.id, "project_id": gate.project_id, "node_id": gate.node_id, "status": gate.status}


@router.get('/workflow-catalog')
def workflow_catalog(current: CurrentUser = Depends(require_session)):
    from app.showcase import catalog
    return {'items': catalog(), 'can_import': service.can_edit(current)}


@router.get('/workflows/{workflow_id}/versions')
def versions(workflow_id: str,current: CurrentUser=Depends(require_session),db: Session=Depends(get_session)):
    from app.models import WorkflowVersion, User
    workflow=service.get_workflow(db,current,workflow_id)
    rows=list(db.scalars(select(WorkflowVersion).where(WorkflowVersion.organization_id==current.organization.id,
        WorkflowVersion.workflow_id==workflow.id).order_by(WorkflowVersion.version.desc())))
    users={u.id:u.display_name for u in db.scalars(select(User).where(User.organization_id==current.organization.id))}
    items=[{'version':v.version,'created_at':v.created_at.isoformat(),'author':users.get(v.created_by,'既有模板')} for v in rows]
    if not any(v['version']==workflow.version for v in items):
        items.insert(0,{'version':workflow.version,'created_at':workflow.created_at.isoformat(),'author':'既有模板'})
    return {'items':items}


@router.get('/workflows/{workflow_id}/versions/{version}')
def read_version(workflow_id: str,version: int,current: CurrentUser=Depends(require_session),db: Session=Depends(get_session)):
    workflow=service.get_workflow(db,current,workflow_id)
    payload=service.version_payload(db,workflow,version)
    return {'id':workflow.id,**payload.model_dump(exclude={'expected_version'}),'version':version,
        'requires_start_date':any(n.start_offset is not None or n.due_offset is not None for n in payload.nodes),
        'capabilities':{'edit':service.can_edit(current) and version==workflow.version,'copy':service.can_edit(current) and version==workflow.version,'delete':service.can_edit(current)}}


@router.delete('/workflows/{workflow_id}')
def delete_template(workflow_id: str,current: CurrentUser=Depends(require_session),db: Session=Depends(get_session)):
    from app.models import now_utc
    workflow=service.get_workflow(db,current,workflow_id,lock=True)
    if not service.can_edit(current):raise HTTPException(status_code=403,detail='沒有管理模板權限')
    service.ensure_version(db,workflow)
    workflow.deleted_at=now_utc()
    log_audit(db,current,'workflow.delete',payload={'workflow_id':workflow.id,'name':workflow.name,'version':workflow.version})
    db.commit()
    return {'deleted':True}


from app.schemas import TemplateSave, TemplateApply
from app.services import template_service


@router.post('/nodes/{node_id}/save-template',status_code=201)
def save_node_template(node_id:str,payload:TemplateSave,current:CurrentUser=Depends(require_session),db:Session=Depends(get_session)):
    return template_service.save_source(db,current,payload,node_id=node_id)


@router.post('/projects/{project_id}/save-template',status_code=201)
def save_project_template(project_id:str,payload:TemplateSave,current:CurrentUser=Depends(require_session),db:Session=Depends(get_session)):
    return template_service.save_source(db,current,payload,project_id=project_id)


@router.post('/nodes/{node_id}/apply-template',status_code=201)
def apply_node_template(node_id:str,payload:TemplateApply,current:CurrentUser=Depends(require_session),db:Session=Depends(get_session)):
    return template_service.apply(db,current,payload,node_id=node_id)


@router.post('/projects/{project_id}/apply-template',status_code=201)
def apply_project_template(project_id:str,payload:TemplateApply,current:CurrentUser=Depends(require_session),db:Session=Depends(get_session)):
    return template_service.apply(db,current,payload,project_id=project_id)
