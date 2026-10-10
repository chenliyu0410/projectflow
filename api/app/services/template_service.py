"""Immutable template snapshots and project-serialized additive application."""
from datetime import timedelta
import re
import uuid
from fastapi import HTTPException
from sqlalchemy import select
from app.audit import log_audit
from app.models import Node, NodeCollaborator, NodeCondition, NodeDependency, Gate, User, Department
from app.permissions import can_manage_project, can_view_node
from app.schemas import WorkflowWrite
from app.services import workflow_service as workflows
from app.services.dependency_service import lock_project
from app.services.record_policy import load_policy_context
from app.services.tree_service import project_nodes, project_root, family_of, require_all_visible, CLOSED_PARENT


def scope(db,current,project_id=None,node_id=None):
    if node_id:
        candidate=db.scalar(select(Node).where(Node.organization_id==current.organization.id,Node.id==node_id))
        if candidate is None:raise HTTPException(status_code=404,detail='找不到節點')
        project_id=candidate.project_id
    project=lock_project(db,current,project_id)
    if node_id:db.expire(candidate)
    nodes=project_nodes(db,current,project.id)
    context=load_policy_context(db,current)
    node=nodes.get(node_id) if node_id else project_root(nodes)
    if node_id and (node is None or not can_view_node(current,node,context=context)):
        raise HTTPException(status_code=404,detail='找不到節點')
    if not workflows.can_edit(current) or not can_manage_project(current,project):
        raise HTTPException(status_code=403,detail='沒有管理此專案模板的權限')
    return project,node,nodes,context


def validate_references(db,current,payload,*,owners):
    users={u.id:u for u in db.scalars(select(User).where(User.organization_id==current.organization.id))}
    departments=set(db.scalars(select(Department.id).where(Department.organization_id==current.organization.id)))
    for node in payload.nodes:
        if node.department_id is not None and node.department_id not in departments:
            workflows.invalid('模板部門已失效，請更新模板')
        if not owners:continue
        if node.owner_user_id is not None and (node.owner_user_id not in users or users[node.owner_user_id].role=='readonly'):
            workflows.invalid('模板負責人已失效，請取消帶入人員或更新模板')
        targets=set()
        for item in node.collaborators:
            key=(item.user_id,item.department_id)
            if key in targets:workflows.invalid('協作對象重複')
            targets.add(key)
            if (item.user_id is not None and item.user_id not in users) or (item.department_id is not None and item.department_id not in departments):
                workflows.invalid('模板協作對象已失效，請取消帶入人員或更新模板')


def save_source(db,current,request,*,project_id=None,node_id=None):
    project,root,nodes,context=scope(db,current,project_id,node_id)
    whole=node_id is None or root.kind=='project'
    ids=list(nodes) if whole else family_of(nodes,root.id)
    ids=[i for i in ids if nodes[i].kind!='project']
    if not ids or len(ids)>300:workflows.invalid('請保存1至300個節點')
    require_all_visible(current,nodes,ids,context,'來源含無法讀取的節點，不能另存模板')
    dates=[v for i in ids for v in (nodes[i].start_date,nodes[i].due_date) if v is not None]
    base=min(dates) if dates else None
    keys={i:str(uuid.uuid4()) for i in ids}
    gates=set(db.scalars(select(Gate.node_id).where(Gate.organization_id==current.organization.id,Gate.project_id==project.id)))
    collaborators={i:[] for i in ids}
    for c in db.scalars(select(NodeCollaborator).where(NodeCollaborator.organization_id==current.organization.id,NodeCollaborator.node_id.in_(ids))):
        collaborators[c.node_id].append({'user_id':c.user_id,'department_id':c.department_id})
    content=[]
    for i in ids:
        n=nodes[i];kind=n.kind if whole else 'task'
        content.append(dict(id=keys[i],parent_id=keys.get(n.parent_id),kind=kind,title=n.title,sort_order=n.sort_order,
            gate_after=whole and i in gates,owner_user_id=n.owner_user_id,department_id=n.department_id,
            report_fields=n.report_fields,collaborators=collaborators[i],weight=n.weight,milestone=n.milestone,
            start_offset=(n.start_date-base).days if n.start_date else None,due_offset=(n.due_date-base).days if n.due_date else None))
    edges=[]
    for e in db.scalars(select(NodeDependency).where(NodeDependency.organization_id==current.organization.id,NodeDependency.project_id==project.id)):
        if e.predecessor_id in keys and e.successor_id in keys:
            edges.append(dict(predecessor_id=keys[e.predecessor_id],successor_id=keys[e.successor_id],relation_type=e.relation_type,lag_days=e.lag_days,enforcement=e.enforcement))
    conditions=[dict(node_id=keys[c.node_id],label=c.label,enforcement=c.enforcement) for c in db.scalars(select(NodeCondition).where(
        NodeCondition.organization_id==current.organization.id,NodeCondition.project_id==project.id,NodeCondition.node_id.in_(ids)))]
    payload=WorkflowWrite(name=request.name,kind='workflow' if whole else 'task',nodes=content,dependencies=edges,conditions=conditions,
        expected_version=request.expected_version)
    target=workflows.get_workflow(db,current,request.template_id,lock=True) if request.template_id else None
    if target and request.expected_version is None:workflows.invalid('建立新版需提供目前版號')
    return workflows.save(db,current,payload,target,source_snapshot=True)


def check_target(target,nodes):
    seen=set();cursor=target
    while cursor is not None:
        if cursor.id in seen:raise HTTPException(status_code=409,detail='節點階層異常')
        seen.add(cursor.id)
        if cursor.status in CLOSED_PARENT:raise HTTPException(status_code=409,detail='不能在待確認、完成或已略過的節點底下套用')
        if cursor.milestone:raise HTTPException(status_code=409,detail='里程碑不能有子任務')
        if cursor.parent_id is not None and cursor.parent_id not in nodes:raise HTTPException(status_code=409,detail='節點階層異常')
        cursor=nodes.get(cursor.parent_id)


def expand(db,current,project,target,payload,options,*,legacy_owner=None):
    ordered=workflows.validate_graph(payload)
    if payload.kind=='workflow' and not options.structure:workflows.invalid('工作流需保留完整結構')
    if not options.structure:ordered=[n for n in ordered if n.parent_id is None]
    selected=payload.model_copy(update={'nodes':ordered})
    validate_references(db,current,selected,owners=options.owners)
    if not ordered:workflows.invalid('模板沒有節點')
    if options.dates and any(n.start_offset is not None or n.due_offset is not None for n in ordered) and options.start_date is None:
        workflows.invalid('請指定模板開始日')
    if not options.dates and any(n.milestone for n in ordered):
        workflows.invalid('此模板含單日里程碑，請帶入日期')
    prepared=[]
    for n in ordered:
        title=re.sub(r'\{([^{}]+)\}',lambda m:options.variables.get(m[1],m[0]),n.title).strip()
        if not title or len(title)>200:workflows.invalid('替換變數後標題需為1至200字')
        try:
            start=options.start_date+timedelta(days=n.start_offset) if options.dates and n.start_offset is not None else None
            due=options.start_date+timedelta(days=n.due_offset) if options.dates and n.due_offset is not None else None
        except (OverflowError,ValueError):workflows.invalid('偏移日期超出有效範圍')
        prepared.append((n,title,start,due))
    existing=project_nodes(db,current,project.id)
    offset=max((n.sort_order for n in existing.values()),default=-10)+10
    mapping={};edges=[]
    for n,title,start,due in prepared:
        node=Node(organization_id=current.organization.id,project_id=project.id,parent_id=mapping.get(n.parent_id,target.id if target else None),
            kind=n.kind,title=title,sort_order=offset+n.sort_order,owner_user_id=n.owner_user_id if options.owners else legacy_owner,
            department_id=n.department_id,weight=n.weight,milestone=n.milestone,start_date=start,due_date=due,status='todo',schedule_locked=False)
        from app.services.report_field_service import clone_fields
        node.report_fields=clone_fields([f.model_dump() for f in n.report_fields])
        node.report_fields_version=1 if node.report_fields else 0
        db.add(node);db.flush();mapping[n.id]=node.id
        if n.gate_after:db.add(Gate(organization_id=current.organization.id,project_id=project.id,node_id=node.id))
        if options.owners:
            for c in n.collaborators:db.add(NodeCollaborator(organization_id=current.organization.id,node_id=node.id,created_by=current.user.id,**c.model_dump()))
    if options.dependencies:
        for e in payload.dependencies:
            if e.predecessor_id in mapping and e.successor_id in mapping:
                edge=NodeDependency(organization_id=current.organization.id,project_id=project.id,created_by=current.user.id,
                    predecessor_id=mapping[e.predecessor_id],successor_id=mapping[e.successor_id],relation_type=e.relation_type,lag_days=e.lag_days,enforcement=e.enforcement)
                db.add(edge);edges.append(edge)
        for c in payload.conditions:
            if c.node_id in mapping:db.add(NodeCondition(organization_id=current.organization.id,project_id=project.id,node_id=mapping[c.node_id],
                label=c.label,enforcement=c.enforcement,is_met=False,created_by=current.user.id))
    db.flush()
    return list(mapping.values()),[e.id for e in edges]


def apply(db,current,options,*,project_id=None,node_id=None):
    project,target,nodes,context=scope(db,current,project_id,node_id)
    check_target(target,nodes)
    workflow=workflows.get_workflow(db,current,options.template_id,lock=True)
    if workflow.kind=='workflow' and target is not None and target.kind!='project':workflows.invalid('工作流只能套用到專案')
    payload=workflows.version_payload(db,workflow,options.version)
    ids,edges=expand(db,current,project,target,payload,options)
    entry=log_audit(db,current,'template.apply',node_id=ids[0],payload={'workflow_id':workflow.id,'version':options.version,
        'node_ids':ids,'dependency_ids':edges,'project_id':project.id})
    db.commit()
    return {'project_id':project.id,'node_ids':ids,'created_count':len(ids),'undo_id':entry.id}
