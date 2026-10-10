from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.auth import CurrentUser, require_session
from app.database import get_session
from app.models import CollaborationRequest, Node, Project
from app.schemas import ReportCreate
from app.permissions import can_view_node
from app.services.record_policy import load_policy_context
from app.services import collaboration_service as service
router=APIRouter(tags=['collaboration'])
class RequestWrite(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    kind: Literal['skip','start','gate','report_submit','phase_complete']
    reason: str=Field(min_length=1,max_length=2000)
    direct: bool=False
    report: ReportCreate | None=None
    @model_validator(mode='after')
    def report_required(self):
        if self.kind == 'report_submit' and self.report is None: raise ValueError('完成回報內容必填')
        return self
class Decision(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    decision: Literal['approved','rejected']
    comment: str=Field(default='',max_length=2000)
    @model_validator(mode='after')
    def reason_required(self):
        if self.decision == 'rejected' and not self.comment: raise ValueError('退回理由必填')
        return self
@router.post('/nodes/{node_id}/requests',status_code=201)
def create(node_id:str,payload:RequestWrite,current:CurrentUser=Depends(require_session),db:Session=Depends(get_session)):
    return service.create(db,current,node_id,payload)
@router.get('/workspace/requests')
def listing(current:CurrentUser=Depends(require_session),db:Session=Depends(get_session)):
    context=load_policy_context(db,current);items=[]
    for r,n,p in db.execute(select(CollaborationRequest,Node,Project).join(Node,Node.id == CollaborationRequest.node_id).join(Project,Project.id == CollaborationRequest.project_id).where(CollaborationRequest.organization_id == current.organization.id,CollaborationRequest.status == 'pending').order_by(CollaborationRequest.created_at)):
        if not can_view_node(current,n,context=context): continue
        can_review=r.requested_by != current.user.id and service.can_decide(db,current,p,n,context,r.kind)
        if can_review or r.requested_by == current.user.id: items.append(service.request_out(r,n,can_review))
    return {'items':items}
@router.post('/requests/{request_id}/decision')
def decide(request_id:str,payload:Decision,current:CurrentUser=Depends(require_session),db:Session=Depends(get_session)):
    return service.decide(db,current,request_id,payload)
