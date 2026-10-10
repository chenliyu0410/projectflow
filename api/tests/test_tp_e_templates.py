from copy import deepcopy
from datetime import date
import pytest
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models import Node, NodeDependency, NodeCondition, Workflow, WorkflowVersion, AuditLog, Gate, Project, User
from test_projects_nodes import login


def setup(client):
    login(client)
    pid=client.post('/projects',json={'title':'TP-E source'}).json()['id']
    root=client.get('/projects/'+pid).json()['nodes'][0]['id']
    def add(title,parent=root,**kw):
        r=client.post(f'/projects/{pid}/nodes',json={'title':title,'kind':'task','parent_id':parent,**kw});assert r.status_code==201,r.text
        return r.json()['id']
    a=add('組合 {產品名}');b=add('先行',a,start_date='2026-10-01',due_date='2026-10-03');c=add('後續',a,start_date='2026-10-04',due_date='2026-10-04')
    r=client.post(f'/projects/{pid}/dependencies',json={'predecessor_id':b,'successor_id':c,'relation_type':'FF','lag_days':-2,'enforcement':'soft'});assert r.status_code==201,r.text
    r=client.post(f'/projects/{pid}/conditions',json={'node_id':c,'label':'人工到貨','enforcement':'hard'});assert r.status_code==201,r.text
    assert client.post('/conditions/'+r.json()['id']+'/confirmation',json={'is_met':True,'reason':'已確認'}).status_code==200
    return pid,root,a,b,c


def save(client,a,name='子樹模板'):
    r=client.post(f'/nodes/{a}/save-template',json={'name':name});assert r.status_code==201,r.text
    return r.json()


def apply(client,target,t,**kw):
    return client.post(target+'/apply-template',json={'template_id':t['id'],'version':t['version'],'start_date':'2027-01-10',**kw})


def counts(engine):
    with Session(engine) as db:return tuple(db.scalar(select(func.count()).select_from(m)) for m in (Node,AuditLog,Workflow,WorkflowVersion,NodeDependency,NodeCondition))


def test_snapshot_apply_preserves_existing_and_undo(client,engine):
    pid,root,a,b,c=setup(client)
    with Session(engine) as db:
        n=db.get(Node,c);n.milestone=True;n.schedule_locked=True;n.weight=5;db.commit()
    t=save(client,a)
    assert t['kind']=='task' and t['version']==1 and len(t['nodes'])==3
    original=client.get('/projects/'+pid).json()['nodes']
    r=apply(client,'/nodes/'+root,t,variables={'產品名':'新產品'});assert r.status_code==201,r.text
    ids=r.json()['node_ids']
    logs=client.get('/audit-logs?action=template.apply').json()['items']
    assert logs[0]['summary']=='套用模板' and logs[0]['payload']['version']==1
    after=client.get('/projects/'+pid).json()['nodes']
    assert [n for n in after if n['id'] not in ids]==original
    with Session(engine) as db:
        copies=list(db.scalars(select(Node).where(Node.id.in_(ids))))
        assert all(n.status=='todo' and n.owner_user_id is None and not n.schedule_locked for n in copies)
        assert any(n.title=='組合 新產品' for n in copies)
        ms=next(n for n in copies if n.milestone);assert ms.start_date==date(2027,1,13) and ms.weight==5
        e=db.scalar(select(NodeDependency).where(NodeDependency.predecessor_id.in_(ids)));assert (e.relation_type,e.lag_days,e.enforcement)==('FF',-2,'soft')
        condition=db.scalar(select(NodeCondition).where(NodeCondition.node_id.in_(ids)));assert not condition.is_met and condition.confirmed_by is None and condition.reason is None
    assert client.post('/undo',json={'audit_id':r.json()['undo_id']}).status_code==200
    assert client.get('/projects/'+pid).json()['nodes']==original
    assert client.post('/undo',json={'audit_id':r.json()['undo_id']}).status_code==409


def test_versions_are_immutable_and_stale_updates_rejected(client,engine):
    pid,root,a,b,c=setup(client);t=save(client,a)
    assert client.patch('/nodes/'+b,json={'title':'新版標題'}).status_code==200
    r=client.post('/nodes/'+a+'/save-template',json={'name':t['name'],'template_id':t['id'],'expected_version':1});assert r.status_code==201,r.text
    assert r.json()['version']==2
    v1=client.get(f"/workflows/{t['id']}/versions/1").json();assert any(n['title']=='先行' for n in v1['nodes'])
    assert len(client.get(f"/workflows/{t['id']}/versions").json()['items'])==2
    assert apply(client,'/nodes/'+root,t).status_code==201
    before=counts(engine)
    assert client.post('/nodes/'+a+'/save-template',json={'name':t['name'],'template_id':t['id'],'expected_version':1}).status_code==409
    assert counts(engine)==before
    assert client.post('/nodes/'+a+'/save-template',json={'name':t['name']}).status_code==409
    copied=client.post('/workflows/'+t['id']+'/copy',json={});assert copied.status_code==201,copied.text
    assert copied.json()['version']==1 and copied.json()['kind']=='task'


def test_delete_blocks_all_entrypoints_but_preserves_instances_and_versions(client,engine):
    pid,root,a,b,c=setup(client);t=save(client,a);assert apply(client,'/nodes/'+root,t).status_code==201
    before=client.get('/projects/'+pid).json()['nodes']
    assert client.delete('/workflows/'+t['id']).status_code==200
    assert t['id'] not in [w['id'] for w in client.get('/workflows').json()['items']]
    for suffix in ['', '/versions','/versions/1']:assert client.get('/workflows/'+t['id']+suffix).status_code==404
    assert apply(client,'/nodes/'+root,t).status_code==404
    assert client.post('/workflows/'+t['id']+'/copy',json={}).status_code==404
    assert client.get('/projects/'+pid).json()['nodes']==before
    with Session(engine) as db:assert db.scalar(select(WorkflowVersion).where(WorkflowVersion.workflow_id==t['id'])) is not None


@pytest.mark.parametrize('user',['ming','lin'])
def test_role_denied_and_cross_company(client,engine,user):
    pid,root,a,b,c=setup(client);t=save(client,a);before=counts(engine)
    client.post('/auth/logout');login(client,username=user)
    assert client.post('/nodes/'+a+'/save-template',json={'name':'no'}).status_code in {403,404}
    assert apply(client,'/nodes/'+root,t).status_code in {403,404}
    assert client.delete('/workflows/'+t['id']).status_code==403
    assert counts(engine)==before
    client.post('/auth/logout');login(client,org='electronics',username='elaine')
    assert client.get('/workflows/'+t['id']+'/versions/1').status_code==404
    assert apply(client,'/nodes/'+root,t).status_code==404


@pytest.mark.parametrize('options',[{'start_date':'9999-12-31'},{'variables':{'產品名':'x'*201}},{'version':999}])
def test_failed_apply_is_atomic(client,engine,options):
    pid,root,a,b,c=setup(client);t=save(client,a);before=counts(engine)
    assert apply(client,'/nodes/'+root,t,**options).status_code in {422,404}
    assert counts(engine)==before


def test_options_closed_ancestor_and_changed_undo(client,engine):
    pid,root,a,b,c=setup(client);t=save(client,a)
    r=apply(client,'/nodes/'+root,t,structure=False,dependencies=False,dates=False);assert r.status_code==201,r.text
    assert r.json()['created_count']==1
    nid=r.json()['node_ids'][0]
    assert client.patch('/nodes/'+nid,json={'title':'modified'}).status_code==200
    assert client.post('/undo',json={'audit_id':r.json()['undo_id']}).status_code==409
    with Session(engine) as db:db.get(Node,a).status='done';db.commit()
    before=counts(engine);assert apply(client,'/nodes/'+b,t).status_code==409;assert counts(engine)==before


def test_project_phase_templates_and_gate_undo(client,engine):
    pid,root,a,b,c=setup(client)
    phase=client.post(f'/projects/{pid}/nodes',json={'title':'階段','kind':'phase'}).json()['id']
    with Session(engine) as db:
        db.add(Gate(organization_id=db.get(Node,phase).organization_id,project_id=pid,node_id=phase));db.commit()
    task=save(client,phase,'階段子樹');assert task['nodes'][0]['kind']=='task' and not task['nodes'][0]['gate_after']
    t=client.post(f'/projects/{pid}/save-template',json={'name':'專案工作流'}).json();assert t['kind']=='workflow'
    assert apply(client,'/nodes/'+a,t).status_code==422
    result=apply(client,'/projects/'+pid,t);assert result.status_code==201,result.text
    ids=result.json()['node_ids']
    with Session(engine) as db:gate=db.scalar(select(Gate).where(Gate.node_id.in_(ids)));gid=gate.id
    assert client.post('/undo',json={'audit_id':result.json()['undo_id']}).status_code==200
    assert client.patch('/gates/'+gid,json={'status':'approved'}).status_code==404


def test_template_validation_and_advanced_editor_roundtrip(client,engine):
    pid,root,a,b,c=setup(client);t=save(client,a)
    payload={k:t[k] for k in ('name','kind','nodes','dependencies','conditions')};payload['expected_version']=1
    r=client.put('/workflows/'+t['id'],json=payload);assert r.status_code==200,r.text
    assert r.json()['dependencies'][0]['enforcement']=='soft' and r.json()['conditions'][0]['label']=='人工到貨'
    bad=deepcopy(payload);bad['name']='invalid';bad['nodes'][0]['owner_user_id']='outside'
    assert client.post('/workflows',json=bad).status_code==422
    bad=deepcopy(payload);bad['nodes']=bad['nodes']*101
    assert client.post('/workflows',json=bad).status_code==422


def test_not_project_owner_and_deleted_source_rejected(client,engine):
    pid,root,a,b,c=setup(client);t=save(client,a)
    with Session(engine) as db:
        other=db.scalar(select(User).where(User.username=='ming'));db.get(Project,pid).owner_user_id=other.id
        db.scalar(select(User).where(User.username=='yu')).role='project_owner';db.commit()
    assert apply(client,'/nodes/'+root,t).status_code==403
    assert client.post('/nodes/'+a+'/save-template',json={'name':'no'}).status_code==403
    with Session(engine) as db:
        owner=db.scalar(select(User).where(User.username=='yu'));db.get(Project,pid).owner_user_id=owner.id;db.commit()
    assert client.delete('/nodes/'+a).status_code==200
    assert client.post('/nodes/'+a+'/save-template',json={'name':'deleted'}).status_code==404


def test_milestone_requires_dates_and_old_version_copy_is_disabled(client,engine):
    pid,root,a,b,c=setup(client)
    with Session(engine) as db:db.get(Node,c).milestone=True;db.commit()
    t=save(client,a);before=counts(engine)
    assert apply(client,'/nodes/'+root,t,dates=False).status_code==422
    assert counts(engine)==before
    assert client.post('/nodes/'+a+'/save-template',json={'name':t['name'],'template_id':t['id'],'expected_version':1}).status_code==201
    assert client.get('/workflows/'+t['id']+'/versions/1').json()['capabilities']['copy'] is False


def test_explicit_people_option_and_invalid_reference_fallback(client,engine):
    pid,root,a,b,c=setup(client)
    with Session(engine) as db:
        owner=db.scalar(select(User).where(User.username=='ming'));db.get(Node,b).owner_user_id=owner.id;uid=owner.id;db.commit()
    t=save(client,a)
    r=apply(client,'/nodes/'+root,t,owners=True);assert r.status_code==201
    with Session(engine) as db:assert any(n.owner_user_id==uid for n in db.scalars(select(Node).where(Node.id.in_(r.json()['node_ids']))))
    with Session(engine) as db:db.get(User,uid).role='readonly';db.commit()
    before=counts(engine);assert apply(client,'/nodes/'+root,t,owners=True).status_code==422;assert counts(engine)==before
    assert apply(client,'/nodes/'+root,t,owners=False).status_code==201
