from datetime import date
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import Node,Project,User,TaskReport,AuditLog,Gate
from test_projects_nodes import login

PAYLOAD={'result':'達成','summary':'成果','finished_on':'2026-10-08','attachment_ids':[]}

def setup(client,engine,actor='ming'):
    login(client,username=actor)
    with Session(engine) as db:
        users={u.username:u.id for u in db.scalars(select(User))}
        node=db.scalars(select(Node).where(Node.owner_user_id==users['ming'],Node.kind=='task')).one()
        return node.id,node.project_id,users

def snapshot(engine):
    with Session(engine) as db:
        return ([(n.id,n.status) for n in db.scalars(select(Node).order_by(Node.id))],
                [(r.id,r.status,r.version,r.summary) for r in db.scalars(select(TaskReport).order_by(TaskReport.id))],
                [(a.id,a.action,a.payload) for a in db.scalars(select(AuditLog).order_by(AuditLog.id))])

def switch(client,actor):
    client.post('/auth/logout');login(client,username=actor)

def test_submit_reject_new_version_approve_atomic_history(client,engine):
    nid,pid,users=setup(client,engine)
    first=client.post(f'/nodes/{nid}/reports',json=PAYLOAD)
    assert first.status_code==201
    first=first.json();assert first['version']==1 and first['node_status']=='review' and first['legacy'] is False
    before=snapshot(engine)
    assert client.post(f'/nodes/{nid}/reports',json=PAYLOAD).status_code==409
    assert client.patch(f'/nodes/{nid}/status',json={'status':'doing'}).status_code==409
    assert snapshot(engine)==before
    switch(client,'yu')
    assert client.post(f"/reports/{first['id']}/review",json={'decision':'rejected','comment':' '}).status_code==422
    rejected=client.post(f"/reports/{first['id']}/review",json={'decision':'rejected','comment':'  補資料  '})
    assert rejected.status_code==200 and rejected.json()['review_comment']=='補資料'
    switch(client,'ming')
    second=client.post(f'/nodes/{nid}/reports',json={**PAYLOAD,'result':'未達成','summary':'新成果'}).json()
    assert second['version']==2
    switch(client,'yu')
    before=snapshot(engine)
    assert client.post(f"/reports/{first['id']}/review",json={'decision':'approved'}).status_code==409
    assert snapshot(engine)==before
    approved=client.post(f"/reports/{second['id']}/review",json={'decision':'approved'})
    assert approved.status_code==200 and approved.json()['status']=='approved'
    with Session(engine) as db:
        assert db.get(Node,nid).status=='done'
        assert db.get(TaskReport,first['id']).summary=='成果'
        assert db.get(TaskReport,first['id']).status=='rejected'
        assert db.get(TaskReport,second['id']).reviewed_by==users['yu']
        assert [a.action for a in db.scalars(select(AuditLog).where(AuditLog.node_id==nid).order_by(AuditLog.created_at))]==['report.submit','report.reject','report.submit','report.approve']

@pytest.mark.parametrize('actor,allowed',[('yu',True),('ming',False),('chen',False),('lin',False),('owner',False)])
def test_explicit_self_approval_permissions(client,engine,actor,allowed):
    nid,_,_=setup(client,engine,actor)
    before=snapshot(engine)
    r=client.post(f'/nodes/{nid}/reports',json={**PAYLOAD,'self_approve':True})
    assert r.status_code==(201 if allowed else 403)
    if not allowed:assert snapshot(engine)==before
    else:
        assert r.json()['status']=='approved' and r.json()['self_approved'] is True
        assert r.json()['node_status']=='done'
        with Session(engine) as db:
            assert {a.action for a in db.scalars(select(AuditLog).where(AuditLog.node_id==nid))}=={'report.submit','report.approve'}

@pytest.mark.parametrize('actor',['yu','chen'])
def test_normal_review_rejects_own_report_even_admin(client,engine,actor):
    nid,_,_=setup(client,engine,actor)
    r=client.post(f'/nodes/{nid}/reports',json=PAYLOAD)
    assert r.status_code==201
    before=snapshot(engine)
    for decision in ('approved','rejected'):
        assert client.post(f"/reports/{r.json()['id']}/review",json={'decision':decision,'comment':'reason'}).status_code==409
        assert snapshot(engine)==before

@pytest.mark.parametrize('source,target',[(a,b) for a in ('todo','doing','review','done','skipped') for b in ('todo','doing','review','done','skipped') if a not in ('todo','doing') or b not in ('todo','doing')])
def test_direct_task_status_cannot_bypass_lifecycle(client,engine,source,target):
    nid,_,_=setup(client,engine)
    with Session(engine) as db:db.get(Node,nid).status=source;db.commit()
    before=snapshot(engine)
    assert client.patch(f'/nodes/{nid}/status',json={'status':target}).status_code==409
    assert snapshot(engine)==before

@pytest.mark.parametrize('status,action,target',[('done','reopen','doing'),('review','reopen','doing'),('todo','skip','skipped'),('doing','skip','skipped'),('skipped','restore','doing')])
def test_manager_reasoned_lifecycle_retains_reports(client,engine,status,action,target):
    nid,_,users=setup(client,engine,'yu')
    with Session(engine) as db:
        node=db.get(Node,nid);node.status=status
        legacy=TaskReport(organization_id=node.organization_id,node_id=nid,result='arbitrary',summary='old',submitted_by=users['ming'])
        db.add(legacy);db.commit();rid=legacy.id
    before=snapshot(engine)
    assert client.post(f'/nodes/{nid}/lifecycle',json={'action':action,'reason':' '}).status_code==422
    assert snapshot(engine)==before
    r=client.post(f'/nodes/{nid}/lifecycle',json={'action':action,'reason':' 原因 '})
    assert r.status_code==200 and r.json()['status']==target
    with Session(engine) as db:assert db.get(TaskReport,rid).summary=='old'

@pytest.mark.parametrize('changes',[{'result':'other'},{'summary':' '},{'summary':'x'*10001},{'finished_on':None},{'finished_on':'2026-2-01'},{'finished_on':123},{'attachment_ids':['missing']},{'unknown':True}])
def test_invalid_report_is_atomic(client,engine,changes):
    nid,_,_=setup(client,engine)
    before=snapshot(engine)
    assert client.post(f'/nodes/{nid}/reports',json={**PAYLOAD,**changes}).status_code==422
    assert snapshot(engine)==before

def test_legacy_review_can_resubmit_but_legacy_report_cannot_be_reviewed(client,engine):
    nid,_,users=setup(client,engine)
    with Session(engine) as db:
        node=db.get(Node,nid);node.status='review'
        old=TaskReport(organization_id=node.organization_id,node_id=nid,result='old',summary='old',submitted_by=users['ming'])
        db.add(old);db.commit();rid=old.id
    switch(client,'yu');before=snapshot(engine)
    assert client.post(f'/reports/{rid}/review',json={'decision':'approved'}).status_code==409
    assert snapshot(engine)==before
    switch(client,'ming')
    r=client.post(f'/nodes/{nid}/reports',json=PAYLOAD)
    assert r.status_code==201 and r.json()['version']==1

def test_doing_gate_blocks_reports_and_corrupt_chain_blocks_review(client,engine):
    nid,pid,users=setup(client,engine,'yu')
    with Session(engine) as db:
        node=db.get(Node,nid);node.status='doing'
        phase=db.get(Node,node.parent_id)
        prior=Node(organization_id=node.organization_id,project_id=pid,kind='phase',title='hidden prior',sort_order=phase.sort_order-1)
        db.add(prior);db.flush()
        gate=Gate(organization_id=node.organization_id,project_id=pid,node_id=prior.id)
        db.add(gate);db.commit();gid=gate.id
    before=snapshot(engine)
    assert client.post(f'/nodes/{nid}/reports',json=PAYLOAD).status_code==409
    assert snapshot(engine)==before
    assert client.patch(f'/gates/{gid}',json={'status':'approved'}).status_code==200
    switch(client,'ming');r=client.post(f'/nodes/{nid}/reports',json=PAYLOAD);assert r.status_code==201
    with Session(engine) as db:db.get(Node,nid).parent_id=nid;db.commit()
    switch(client,'yu');before=snapshot(engine)
    assert client.post(f"/reports/{r.json()['id']}/review",json={'decision':'approved'}).status_code==409
    assert snapshot(engine)==before


def test_actual_owner_can_explicitly_self_approve_only_when_also_worker(client,engine):
    nid,pid,users=setup(client,engine,'owner')
    with Session(engine) as db:
        db.get(Project,pid).owner_user_id=users['owner'];db.commit()
    before=snapshot(engine)
    assert client.post(f'/nodes/{nid}/reports',json={**PAYLOAD,'self_approve':True}).status_code==403
    assert snapshot(engine)==before
    with Session(engine) as db:db.get(Node,nid).owner_user_id=users['owner'];db.commit()
    assert client.post(f'/nodes/{nid}/reports',json={**PAYLOAD,'self_approve':True}).status_code==201


def test_review_and_lifecycle_permission_matrix(client,engine):
    nid,pid,users=setup(client,engine)
    report=client.post(f'/nodes/{nid}/reports',json=PAYLOAD).json()
    for actor in ('lin','owner'):
        switch(client,actor);before=snapshot(engine)
        assert client.post(f"/reports/{report['id']}/review",json={'decision':'approved'}).status_code==403
        assert client.post(f'/nodes/{nid}/lifecycle',json={'action':'reopen','reason':'why'}).status_code==403
        assert snapshot(engine)==before
    switch(client,'yu');before=snapshot(engine)
    assert client.post(f'/nodes/{nid}/lifecycle',json={'action':'reopen','reason':'pending'}).status_code==409
    assert snapshot(engine)==before
    with Session(engine) as db:db.get(Project,pid).owner_user_id=users['owner'];db.commit()
    switch(client,'owner')
    assert client.post(f"/reports/{report['id']}/review",json={'decision':'approved'}).status_code==200


def test_report_audit_failure_rolls_back_every_business_value(client,engine,monkeypatch):
    from app.services import report_service
    nid,_,_=setup(client,engine)
    before=snapshot(engine)
    def fail(*args,**kwargs):raise RuntimeError('audit failure')
    monkeypatch.setattr(report_service,'log_audit',fail)
    with pytest.raises(RuntimeError,match='audit failure'):
        client.post(f'/nodes/{nid}/reports',json=PAYLOAD)
    assert snapshot(engine)==before


def test_report_text_fields_trim_before_enum_validation(client,engine):
    nid,_,_=setup(client,engine)
    r=client.post(f'/nodes/{nid}/reports',json={**PAYLOAD,'result':' 達成 ','summary':' 成果 '})
    assert r.status_code==201
    assert r.json()['result']=='達成' and r.json()['summary']=='成果'


@pytest.mark.parametrize('action,source',[('reopen','done'),('skip','doing'),('restore','skipped')])
def test_lifecycle_always_rechecks_pending_gate(client,engine,action,source):
    nid,pid,_=setup(client,engine,'yu')
    with Session(engine) as db:
        node=db.get(Node,nid);node.status=source
        phase=db.get(Node,node.parent_id)
        prior=Node(organization_id=node.organization_id,project_id=pid,kind='phase',title='prior',sort_order=phase.sort_order-1)
        db.add(prior);db.flush();db.add(Gate(organization_id=node.organization_id,project_id=pid,node_id=prior.id));db.commit()
    before=snapshot(engine)
    assert client.post(f'/nodes/{nid}/lifecycle',json={'action':action,'reason':'why'}).status_code==409
    assert snapshot(engine)==before


def test_approve_rechecks_gate_but_rejection_only_checks_chain(client,engine):
    nid,pid,_=setup(client,engine)
    report=client.post(f'/nodes/{nid}/reports',json=PAYLOAD).json()
    with Session(engine) as db:
        node=db.get(Node,nid);phase=db.get(Node,node.parent_id)
        prior=Node(organization_id=node.organization_id,project_id=pid,kind='phase',title='prior',sort_order=phase.sort_order-1)
        db.add(prior);db.flush();db.add(Gate(organization_id=node.organization_id,project_id=pid,node_id=prior.id));db.commit()
    switch(client,'yu');before=snapshot(engine)
    assert client.post(f"/reports/{report['id']}/review",json={'decision':'approved'}).status_code==409
    assert snapshot(engine)==before
    assert client.post(f"/reports/{report['id']}/review",json={'decision':'rejected','comment':'補資料'}).status_code==200


def test_collaboration_does_not_grant_report_review_or_lifecycle(client,engine):
    from app.models import NodeCollaborator
    nid,_,users=setup(client,engine,'yu')
    with Session(engine) as db:
        node=db.get(Node,nid);node.owner_user_id=users['yu']
        db.add(NodeCollaborator(organization_id=node.organization_id,node_id=nid,user_id=users['ming'],created_by=users['yu']));db.commit()
    report=client.post(f'/nodes/{nid}/reports',json=PAYLOAD).json()
    switch(client,'ming');before=snapshot(engine)
    assert client.post(f'/nodes/{nid}/reports',json=PAYLOAD).status_code==403
    assert client.post(f"/reports/{report['id']}/review",json={'decision':'approved'}).status_code==403
    assert client.post(f'/nodes/{nid}/lifecycle',json={'action':'reopen','reason':'why'}).status_code==403
    assert snapshot(engine)==before


def test_review_audit_failure_rolls_back_report_and_node(client,engine,monkeypatch):
    from app.services import report_service
    nid,_,_=setup(client,engine)
    report=client.post(f'/nodes/{nid}/reports',json=PAYLOAD).json()
    switch(client,'yu');before=snapshot(engine)
    def fail(*args,**kwargs):raise RuntimeError('audit failure')
    monkeypatch.setattr(report_service,'log_audit',fail)
    with pytest.raises(RuntimeError,match='audit failure'):
        client.post(f"/reports/{report['id']}/review",json={'decision':'approved'})
    assert snapshot(engine)==before
