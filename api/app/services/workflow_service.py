"""Validated versioned templates; each instantiation is one atomic transaction."""
from datetime import timedelta
import uuid
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import delete,select
from sqlalchemy.exc import IntegrityError
from app.audit import log_audit
from app.models import Workflow,WorkflowNode,Project,Node,Gate,NodeDependency
from app.schemas import WorkflowWrite


def invalid(message='工作流節點或前置設定無效'):
    raise HTTPException(status_code=422,detail=message)


def can_edit(current):
    return current.user.role in {'admin','project_owner'}


def get_workflow(db,current,identifier,*,lock=False):
    query=select(Workflow).where(Workflow.organization_id==current.organization.id,Workflow.id==identifier)
    if lock:query=query.with_for_update().execution_options(populate_existing=True)
    workflow=db.scalar(query)
    if workflow is None:raise HTTPException(status_code=404,detail='找不到工作流')
    return workflow


def validate_graph(payload):
    nodes={n.id:n for n in payload.nodes}
    if len(nodes)!=len(payload.nodes):invalid('節點 ID 不可重複')
    children={nid:[] for nid in nodes};indegree={nid:0 for nid in nodes}
    for node in nodes.values():
        if node.parent_id is not None:
            if node.kind != 'task':invalid('階段必須位於模板頂層')
            if node.parent_id not in nodes or node.parent_id==node.id:invalid('父節點無效')
            children[node.parent_id].append(node.id);indegree[node.id]+=1
    ready=sorted((nid for nid in nodes if indegree[nid]==0),key=lambda nid:(nodes[nid].sort_order,nid))
    ordered=[]
    while ready:
        nid=ready.pop(0);ordered.append(nodes[nid])
        for child in sorted(children[nid],key=lambda child:(nodes[child].sort_order,child)):
            indegree[child]-=1
            if indegree[child]==0:ready.append(child)
    if len(ordered)!=len(nodes):invalid('父子節點不可循環')
    edges=set();children={nid:[] for nid in nodes};indegree=dict.fromkeys(nodes,0)
    for edge in payload.dependencies:
        a,b=edge.predecessor_id,edge.successor_id
        if a not in nodes or b not in nodes or a==b or nodes[a].kind!='task' or nodes[b].kind!='task' or (a,b) in edges:invalid('前置連線無效或重複')
        edges.add((a,b));children[a].append(b);indegree[b]+=1
    ready=[nid for nid in nodes if indegree[nid]==0];visited=0
    while ready:
        nid=ready.pop();visited+=1
        for child in children[nid]:
            indegree[child]-=1
            if indegree[child]==0:ready.append(child)
    if visited!=len(nodes):invalid('前置任務不可循環')
    return ordered


def read_payload(db,workflow):
    content=workflow.content if isinstance(workflow.content,dict) else {}
    if content.get('p2c_version') not in {None,1}:invalid('工作流內容版本無法使用')
    offsets=content.get('offsets',{}) if content.get('p2c_version')==1 else {}
    dependencies=content.get('dependencies',[]) if content.get('p2c_version')==1 else []
    if not isinstance(offsets,dict):invalid()
    nodes=[]
    for node in db.scalars(select(WorkflowNode).where(WorkflowNode.organization_id==workflow.organization_id,WorkflowNode.workflow_id==workflow.id).order_by(WorkflowNode.sort_order,WorkflowNode.id)):
        relative=offsets.get(node.id,{})
        if not isinstance(relative,dict):invalid()
        nodes.append({'id':node.id,'parent_id':node.parent_template_id,'kind':node.kind,'title':node.title,
                      'sort_order':node.sort_order,'gate_after':node.gate_after,
                      'start_offset':relative.get('start_offset'),'due_offset':relative.get('due_offset')})
    try:payload=WorkflowWrite(name=workflow.name,nodes=nodes,dependencies=dependencies)
    except ValidationError:invalid()
    validate_graph(payload)
    return payload


def detail(db,current,workflow):
    payload=read_payload(db,workflow)
    return {'id':workflow.id,**payload.model_dump(),'requires_start_date':any(n.start_offset is not None or n.due_offset is not None for n in payload.nodes),
            'capabilities':{'edit':can_edit(current),'copy':can_edit(current)}}


def save(db,current,payload,workflow=None,*,copy_source=None):
    if not can_edit(current):raise HTTPException(status_code=403,detail='沒有管理工作流權限')
    ordered=validate_graph(payload)
    if copy_source is None:
        existing=list(db.scalars(select(WorkflowNode).where(WorkflowNode.id.in_([n.id for n in payload.nodes]))))
        if any(workflow is None or n.workflow_id!=workflow.id or n.organization_id!=current.organization.id for n in existing):invalid('不可參照其他模板的節點')
    action='workflow.update' if workflow else ('workflow.copy' if copy_source else 'workflow.create')
    if workflow is None:
        workflow=Workflow(organization_id=current.organization.id,name=payload.name,content={});db.add(workflow)
    try:
        workflow.name=payload.name;db.flush()
        old=list(db.scalars(select(WorkflowNode).where(WorkflowNode.organization_id==current.organization.id,WorkflowNode.workflow_id==workflow.id)))
        for node in old:node.parent_template_id=None
        db.flush()
        db.execute(delete(WorkflowNode).where(WorkflowNode.organization_id==current.organization.id,WorkflowNode.workflow_id==workflow.id))
        identifiers={n.id:str(uuid.uuid4()) for n in ordered}
        for node in ordered:
            db.add(WorkflowNode(id=identifiers[node.id],organization_id=current.organization.id,workflow_id=workflow.id,
                parent_template_id=identifiers.get(node.parent_id),kind=node.kind,title=node.title,sort_order=node.sort_order,gate_after=node.gate_after))
            db.flush()
        workflow.content={'p2c_version':1,'offsets':{identifiers[n.id]:{'start_offset':n.start_offset,'due_offset':n.due_offset} for n in ordered},
                          'dependencies':[{'predecessor_id':identifiers[e.predecessor_id],'successor_id':identifiers[e.successor_id]} for e in payload.dependencies]}
        log_audit(db,current,action,payload={'workflow_id':workflow.id,'name':workflow.name})
        db.commit()
    except IntegrityError:
        db.rollback();raise HTTPException(status_code=409,detail='工作流名稱已存在或資料發生衝突') from None
    return detail(db,current,workflow)


def instantiate(db,current,request):
    workflow=get_workflow(db,current,request.workflow_id,lock=True)
    if not can_edit(current):raise HTTPException(status_code=403,detail='沒有建立專案權限')
    payload=read_payload(db,workflow);ordered=validate_graph(payload)
    requires_date=any(n.start_offset is not None or n.due_offset is not None for n in ordered)
    if requires_date and request.start_date is None:invalid('此工作流需指定專案開始日')
    dates={}
    try:
        for node in ordered:
            dates[node.id]=(request.start_date+timedelta(days=node.start_offset) if node.start_offset is not None else None,
                            request.start_date+timedelta(days=node.due_offset) if node.due_offset is not None else None)
    except (OverflowError,ValueError):invalid('偏移日期超出有效範圍')
    project=Project(organization_id=current.organization.id,title=request.title,owner_user_id=current.user.id)
    db.add(project);db.flush();mapping={}
    for template in ordered:
        node=Node(organization_id=current.organization.id,project_id=project.id,parent_id=mapping.get(template.parent_id),kind=template.kind,
                  title=template.title,owner_user_id=current.user.id,sort_order=template.sort_order,
                  start_date=dates[template.id][0],due_date=dates[template.id][1])
        db.add(node);db.flush();mapping[template.id]=node.id
        if template.gate_after:db.add(Gate(organization_id=current.organization.id,project_id=project.id,node_id=node.id))
    for edge in payload.dependencies:
        db.add(NodeDependency(organization_id=current.organization.id,project_id=project.id,predecessor_id=mapping[edge.predecessor_id],
                              successor_id=mapping[edge.successor_id],created_by=current.user.id))
    log_audit(db,current,'workflow.instantiate',payload={'workflow_id':workflow.id,'project_id':project.id,'title':project.title})
    db.commit();db.refresh(project)
    return {'id':project.id,'title':project.title,'organization_key':current.organization.key,'owner_user_id':project.owner_user_id}
