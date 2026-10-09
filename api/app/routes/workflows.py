from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import log_audit
from app.auth import CurrentUser, require_session
from app.database import get_session
from app.models import Gate, Node, Project, Workflow, WorkflowNode
from app.permissions import can_work_node, can_work_project
from app.schemas import GateStatusUpdate, ProjectFromWorkflowCreate, WorkflowWrite, WorkflowCopy
from app.services import workflow_service as service

router = APIRouter(tags=["workflows"])


@router.get('/workflows')
def list_workflows(current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    items=[]
    for workflow in db.scalars(select(Workflow).where(Workflow.organization_id==current.organization.id).order_by(Workflow.name,Workflow.id)):
        value=service.detail(db,current,workflow)
        items.append({**{key:value[key] for key in ['id','name','requires_start_date','capabilities']}, 'phase_count': sum(n['kind']=='phase' for n in value['nodes']), 'task_count': sum(n['kind']=='task' for n in value['nodes']), 'phase_titles': [n['title'] for n in value['nodes'] if n['kind']=='phase']})
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
    project = db.execute(
        select(Project).where(Project.organization_id == current.organization.id, Project.id == gate.project_id)
    ).scalar_one()
    node = db.execute(select(Node).where(Node.organization_id == current.organization.id, Node.id == gate.node_id)).scalar_one()
    scoped_reviewer = current.user.role == "reviewer" and can_work_node(db, current, node)
    if not can_work_project(current, project) and not scoped_reviewer:
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
