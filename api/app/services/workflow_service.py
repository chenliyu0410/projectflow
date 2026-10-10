"""Validated versioned templates; each instantiation is one atomic transaction."""
import uuid
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import delete,select
from sqlalchemy.exc import IntegrityError
from app.audit import log_audit
from app.models import Workflow,WorkflowNode,WorkflowVersion,Project
from app.schemas import WorkflowWrite


def invalid(message='工作流節點或前置設定無效'):
    raise HTTPException(status_code=422,detail=message)


def can_edit(current):
    return current.user.role in {'admin','project_owner'}


def get_workflow(db,current,identifier,*,lock=False):
    query=select(Workflow).where(Workflow.organization_id==current.organization.id,Workflow.id==identifier,Workflow.deleted_at.is_(None))
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
    if payload.kind == 'task' and (not nodes or sum(n.parent_id is None for n in nodes.values()) != 1 or any(n.kind != 'task' for n in nodes.values())):
        invalid('任務模板必須有一個根任務')
    for node in nodes.values():
        if node.kind != 'task' and node.report_fields: invalid('只有任務可設定回報欄位')
        field_ids=[f.id for f in node.report_fields if f.id is not None]
        if len(set(field_ids)) != len(field_ids): invalid('回報欄位識別碼不可重複')
        if node.milestone and (node.kind != 'task' or node.start_offset is None or node.start_offset != node.due_offset or any(n.parent_id == node.id for n in nodes.values())):
            invalid('里程碑必須是單日葉任務')
        ancestors=set(); parent=node.parent_id
        while parent is not None:
            if parent in ancestors: invalid('父子節點不可循環')
            ancestors.add(parent); parent=nodes[parent].parent_id
        for edge in payload.dependencies:
            if (edge.predecessor_id == node.id and edge.successor_id in ancestors) or (edge.successor_id == node.id and edge.predecessor_id in ancestors):
                invalid('前置不可連接祖先與子孫')
    if any(c.node_id not in nodes or nodes[c.node_id].kind != 'task' for c in payload.conditions):
        invalid('人工條件必須屬於模板任務')
    return ordered


def read_payload(db,workflow):
    if isinstance(workflow.content, dict) and workflow.content.get('tpe_version') == 1:
        try:
            payload = WorkflowWrite.model_validate(workflow.content['snapshot'])
            validate_graph(payload)
            return payload
        except (ValidationError, KeyError):
            invalid('模板內容無效')
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
    return {'id':workflow.id,**payload.model_dump(exclude={'expected_version'}),'version':workflow.version,'kind':workflow.kind,'requires_start_date':any(n.start_offset is not None or n.due_offset is not None for n in payload.nodes),
            'capabilities':{'edit':can_edit(current),'copy':can_edit(current),'delete':can_edit(current)}}


def save(db,current,payload,workflow=None,*,copy_source=None,source_snapshot=False):
    if not can_edit(current):raise HTTPException(status_code=403,detail='沒有管理工作流權限')
    ordered=validate_graph(payload)
    if not source_snapshot and copy_source is None:
        previous={n.id:n for n in read_payload(db,workflow).nodes} if workflow else {}
        for n in payload.nodes:
            if n.report_fields and any(c.parent_id==n.id for c in payload.nodes):
                old=previous.get(n.id)
                if old is None or n.report_fields != old.report_fields:
                    invalid('只有模板葉任務可新增回報欄位')
    from app.services.template_service import validate_references
    validate_references(db,current,payload,owners=True)
    if workflow is not None:
        if payload.expected_version is not None and payload.expected_version != workflow.version:
            raise HTTPException(status_code=409,detail='模板已有新版，請重新載入')
        if payload.kind != workflow.kind: invalid('不能變更模板種類')
        ensure_version(db,workflow)
    if copy_source is None:
        existing=list(db.scalars(select(WorkflowNode).where(WorkflowNode.id.in_([n.id for n in payload.nodes]))))
        if any(workflow is None or n.workflow_id!=workflow.id or n.organization_id!=current.organization.id for n in existing):invalid('不可參照其他模板的節點')
    action='workflow.update' if workflow else ('workflow.copy' if copy_source else 'workflow.create')
    if workflow is None:
        workflow=Workflow(organization_id=current.organization.id,name=payload.name,content={});db.add(workflow)
    try:
        workflow.name=payload.name;workflow.kind=payload.kind
        if action == 'workflow.update': workflow.version += 1
        db.flush()
        old=list(db.scalars(select(WorkflowNode).where(WorkflowNode.organization_id==current.organization.id,WorkflowNode.workflow_id==workflow.id)))
        for node in old:node.parent_template_id=None
        db.flush()
        db.execute(delete(WorkflowNode).where(WorkflowNode.organization_id==current.organization.id,WorkflowNode.workflow_id==workflow.id))
        identifiers={n.id:str(uuid.uuid4()) for n in ordered}
        for node in ordered:
            db.add(WorkflowNode(id=identifiers[node.id],organization_id=current.organization.id,workflow_id=workflow.id,
                parent_template_id=identifiers.get(node.parent_id),kind=node.kind,title=node.title,sort_order=node.sort_order,gate_after=node.gate_after))
            db.flush()
        snapshot=payload.model_dump(exclude={'expected_version'})
        for n in snapshot['nodes']:
            n['id']=identifiers[n['id']];n['parent_id']=identifiers.get(n['parent_id'])
        for e in snapshot['dependencies']:
            e['predecessor_id']=identifiers[e['predecessor_id']];e['successor_id']=identifiers[e['successor_id']]
        for c in snapshot['conditions']:c['node_id']=identifiers[c['node_id']]
        workflow.content={'tpe_version':1,'snapshot':snapshot}
        db.add(WorkflowVersion(organization_id=workflow.organization_id,workflow_id=workflow.id,version=workflow.version,
                               snapshot=snapshot,created_by=current.user.id))
        log_audit(db,current,action,payload={'workflow_id':workflow.id,'name':workflow.name,'version':workflow.version})
        db.commit()
    except IntegrityError:
        db.rollback();raise HTTPException(status_code=409,detail='工作流名稱已存在或資料發生衝突') from None
    return detail(db,current,workflow)


def ensure_version(db,workflow):
    existing=db.scalar(select(WorkflowVersion).where(WorkflowVersion.organization_id==workflow.organization_id,
        WorkflowVersion.workflow_id==workflow.id,WorkflowVersion.version==workflow.version))
    if existing is None:
        db.add(WorkflowVersion(organization_id=workflow.organization_id,workflow_id=workflow.id,version=workflow.version,
            snapshot=read_payload(db,workflow).model_dump(exclude={'expected_version'}),created_at=workflow.created_at))
        db.flush()


def version_payload(db,workflow,version):
    if version == workflow.version:return read_payload(db,workflow)
    row=db.scalar(select(WorkflowVersion).where(WorkflowVersion.organization_id==workflow.organization_id,
        WorkflowVersion.workflow_id==workflow.id,WorkflowVersion.version==version))
    if row is None:raise HTTPException(status_code=404,detail='找不到模板版本')
    try:payload=WorkflowWrite.model_validate(row.snapshot)
    except ValidationError:invalid('模板版本內容無效')
    validate_graph(payload)
    return payload


def instantiate(db,current,request):
    from app.services.template_service import expand
    from app.schemas import TemplateApply
    workflow=get_workflow(db,current,request.workflow_id,lock=True)
    if not can_edit(current):raise HTTPException(status_code=403,detail='沒有建立專案權限')
    if workflow.kind != 'workflow':invalid('請使用工作流模板建立專案')
    version=request.version or workflow.version
    payload=version_payload(db,workflow,version)
    project=Project(organization_id=current.organization.id,title=request.title,owner_user_id=current.user.id)
    db.add(project);db.flush()
    options=TemplateApply(template_id=workflow.id,version=version,start_date=request.start_date.isoformat() if request.start_date else None)
    expand(db,current,project,None,payload,options,legacy_owner=current.user.id if 'tpe_version' not in workflow.content else None)
    log_audit(db,current,'workflow.instantiate',payload={'workflow_id':workflow.id,'version':version,'project_id':project.id,'title':project.title})
    db.commit();db.refresh(project)
    return {'id':project.id,'title':project.title,'organization_key':current.organization.key,'owner_user_id':project.owner_user_id}
