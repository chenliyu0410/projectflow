from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import log_audit
from app.auth import CurrentUser, require_session
from app.database import get_session
from app.models import Gate, Node, Project, Workflow, WorkflowNode
from app.permissions import can_work_project
from app.schemas import GateStatusUpdate, ProjectFromWorkflowCreate

router = APIRouter(tags=["workflows"])


@router.get("/workflows")
def list_workflows(current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    workflows = db.execute(
        select(Workflow).where(Workflow.organization_id == current.organization.id).order_by(Workflow.name)
    ).scalars()
    return {"items": [{"id": workflow.id, "name": workflow.name} for workflow in workflows]}


def created_project_out(current: CurrentUser, project: Project) -> dict:
    return {"id": project.id, "title": project.title, "organization_key": current.organization.key, "owner_user_id": project.owner_user_id}


@router.post("/projects/from-workflow", status_code=status.HTTP_201_CREATED)
def create_project_from_workflow(payload: ProjectFromWorkflowCreate, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    workflow = db.execute(
        select(Workflow).where(Workflow.organization_id == current.organization.id, Workflow.id == payload.workflow_id)
    ).scalar_one_or_none()
    if workflow is None:
        raise HTTPException(status_code=404, detail="找不到工作流")
    if current.user.role not in {"admin", "project_owner"}:
        raise HTTPException(status_code=403, detail="沒有建立專案權限")
    project = Project(organization_id=current.organization.id, title=payload.title, owner_user_id=current.user.id)
    db.add(project)
    db.flush()
    templates = db.execute(
        select(WorkflowNode)
        .where(WorkflowNode.organization_id == current.organization.id, WorkflowNode.workflow_id == workflow.id)
        .order_by(WorkflowNode.sort_order)
    ).scalars().all()
    template_to_node: dict[str, Node] = {}
    for template in templates:
        parent = template_to_node.get(template.parent_template_id) if template.parent_template_id else None
        node = Node(
            organization_id=current.organization.id,
            project_id=project.id,
            parent_id=parent.id if parent else None,
            kind=template.kind,
            title=template.title,
            owner_user_id=current.user.id,
            sort_order=template.sort_order,
        )
        db.add(node)
        db.flush()
        template_to_node[template.id] = node
        if template.gate_after:
            db.add(Gate(organization_id=current.organization.id, project_id=project.id, node_id=node.id, status="pending"))
    log_audit(db, current, "workflow.instantiate", payload={"workflow_id": workflow.id, "project_id": project.id, "title": payload.title})
    db.commit()
    db.refresh(project)
    return created_project_out(current, project)


@router.patch("/gates/{gate_id}")
def update_gate(gate_id: str, payload: GateStatusUpdate, current: CurrentUser = Depends(require_session), db: Session = Depends(get_session)):
    gate = db.execute(select(Gate).where(Gate.organization_id == current.organization.id, Gate.id == gate_id)).scalar_one_or_none()
    if gate is None:
        raise HTTPException(status_code=404, detail="找不到閘門")
    project = db.execute(
        select(Project).where(Project.organization_id == current.organization.id, Project.id == gate.project_id)
    ).scalar_one()
    if not can_work_project(current, project) and current.user.role != "reviewer":
        raise HTTPException(status_code=403, detail="沒有核准閘門權限")
    gate.status = payload.status
    log_audit(db, current, "gate.approve", node_id=gate.node_id, payload={"gate_id": gate.id, "status": payload.status})
    db.commit()
    db.refresh(gate)
    return {"id": gate.id, "project_id": gate.project_id, "node_id": gate.node_id, "status": gate.status}
