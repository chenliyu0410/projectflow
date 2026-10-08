from copy import deepcopy
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import Node,Project,Workflow,WorkflowNode,AuditLog
from test_projects_nodes import login


def template():
    return {'name':'  P2c 模板  ','nodes':[
        {'id':'child','parent_id':'phase','kind':'task','title':'後序輸入子任務','sort_order':0,'start_offset':1,'due_offset':3},
        {'id':'phase','parent_id':None,'kind':'phase','title':'階段','sort_order':10,'gate_after':True},
        {'id':'next','parent_id':None,'kind':'task','title':'下一任務','sort_order':20,'start_offset':4,'due_offset':5}],
        'dependencies':[{'predecessor_id':'child','successor_id':'next'}]}


def test_template_crud_copy_and_instantiate_dates_topology(client,engine):
    login(client)
    response=client.post('/workflows',json=template());assert response.status_code==201
    detail=response.json();assert detail['name']=='P2c 模板' and detail['requires_start_date'] is True
    wid=detail['id'];nodes={n['title']:n for n in detail['nodes']}
    assert nodes['後序輸入子任務']['parent_id']==nodes['階段']['id']
    assert client.get('/workflows/'+wid).json()==detail
    assert client.post('/projects/from-workflow',json={'workflow_id':wid,'title':'need date'}).status_code==422
    project=client.post('/projects/from-workflow',json={'workflow_id':wid,'title':'dated','start_date':'2026-12-30'})
    assert project.status_code==201
    instantiated=client.get('/projects/'+project.json()['id']).json()
    concrete={n['title']:n for n in instantiated['nodes']}
    assert concrete['後序輸入子任務']['start_date']=='2026-12-31' and concrete['後序輸入子任務']['due_date']=='2027-01-02'
    assert concrete['後序輸入子任務']['parent_id']==concrete['階段']['id']
    assert len(instantiated['gates'])==1
    deps=client.get('/projects/'+project.json()['id']+'/dependencies').json()
    assert len(deps['items'])==1
    copied=client.post('/workflows/'+wid+'/copy',json={'name':'複製'});assert copied.status_code==201
    assert copied.json()['id']!=wid and not {n['id'] for n in copied.json()['nodes']} & {n['id'] for n in detail['nodes']}
    changed=deepcopy(template());changed['name']='更新';changed['nodes'][0]['start_offset']=2
    assert client.put('/workflows/'+wid,json=changed).status_code==200
    assert client.get('/projects/'+project.json()['id']).json()['nodes']==instantiated['nodes']


def test_template_validation_cycles_foreign_readonly_and_atomic(client,engine):
    login(client)
    for change in ['parent-cycle','dependency-cycle','missing-parent','phase-edge','self-edge','duplicate','offset','task-gate','extra']:
        payload=template()
        if change=='parent-cycle':payload['nodes'][1]['parent_id']='child'
        elif change=='dependency-cycle':payload['dependencies'].append({'predecessor_id':'next','successor_id':'child'})
        elif change=='missing-parent':payload['nodes'][0]['parent_id']='foreign'
        elif change=='phase-edge':payload['dependencies'][0]['predecessor_id']='phase'
        elif change=='self-edge':payload['dependencies'][0]['successor_id']='child'
        elif change=='duplicate':payload['dependencies']*=2
        elif change=='offset':payload['nodes'][0]['start_offset']=4
        elif change=='task-gate':payload['nodes'][0]['gate_after']=True
        else:payload['secret']='not allowed'
        assert client.post('/workflows',json=payload).status_code==422,change
    with Session(engine) as db:assert db.scalar(select(Workflow).where(Workflow.name=='P2c 模板')) is None
    created=client.post('/workflows',json=template());assert created.status_code==201
    wid=created.json()['id']
    client.post('/auth/logout');login(client,username='lin')
    assert client.get('/workflows/'+wid).status_code==200
    assert client.post('/workflows',json=template()).status_code==403
    assert client.put('/workflows/'+wid,json=template()).status_code==403
    assert client.post('/workflows/'+wid+'/copy',json={}).status_code==403
    client.post('/auth/logout');login(client,org='electronics',username='elaine')
    assert client.get('/workflows/'+wid).status_code==404
    assert client.put('/workflows/'+wid,json=template()).status_code==404
    assert client.post('/workflows/'+wid+'/copy',json={}).status_code==404


def test_legacy_workflow_payload_and_start_date_validation(client,engine):
    login(client)
    workflow=client.get('/workflows').json()['items'][0]
    response=client.post('/projects/from-workflow',json={'workflow_id':workflow['id'],'title':'legacy'})
    assert response.status_code==201
    assert all(n['start_date'] is None and n['due_date'] is None for n in client.get('/projects/'+response.json()['id']).json()['nodes'])
    for value in ['2026-01-01T00:00:00Z',20260101,'2026-02-30']:
        assert client.post('/projects/from-workflow',json={'workflow_id':workflow['id'],'title':'bad','start_date':value}).status_code==422


def test_template_failed_replace_and_date_overflow_do_not_write(client,engine):
    login(client)
    response=client.post('/workflows',json=template());assert response.status_code==201
    original=response.json();wid=original['id']
    bad=template();bad['nodes'][0]['parent_id']='outside'
    assert client.put('/workflows/'+wid,json=bad).status_code==422
    assert client.get('/workflows/'+wid).json()==original
    with Session(engine) as db:before=(len(list(db.scalars(select(Project)))),len(list(db.scalars(select(AuditLog)))))
    assert client.post('/projects/from-workflow',json={'workflow_id':wid,'title':'overflow','start_date':'9999-12-31'}).status_code==422
    with Session(engine) as db:assert before==(len(list(db.scalars(select(Project)))),len(list(db.scalars(select(AuditLog)))))


def test_templates_keep_existing_phase_task_hierarchy(client):
    login(client)
    payload=template();payload['nodes'][1]['parent_id']='next'
    assert client.post('/workflows',json=payload).status_code==422
    payload=template();payload['nodes'].append({'id':'nested-phase','parent_id':'phase','kind':'phase','title':'invalid phase'})
    assert client.post('/workflows',json=payload).status_code==422
