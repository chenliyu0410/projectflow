from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import Node,Project,User,AuditLog,Gate
from test_report_lifecycle import setup,switch,PAYLOAD


def pair(client,engine):
    nid,pid,users=setup(client,engine,'yu')
    with Session(engine) as db:
        original=db.get(Node,nid)
        predecessor=Node(organization_id=original.organization_id,project_id=pid,kind='task',title='hidden predecessor',owner_user_id=users['yu'])
        db.add(predecessor);db.commit();pre=predecessor.id
    return pre,nid,pid,users


def test_hidden_predecessor_blocks_status_and_reports_without_disclosure(client,engine):
    pre,nid,pid,users=pair(client,engine)
    edge=client.post(f'/projects/{pid}/dependencies',json={'predecessor_id':pre,'successor_id':nid});assert edge.status_code==201
    switch(client,'ming')
    listing=client.get(f'/projects/{pid}/dependencies');assert listing.status_code==200
    assert listing.json()['items']==[] and pre not in listing.text and 'hidden predecessor' not in listing.text
    assert next(n for n in listing.json()['nodes'] if n['id']==nid)['blocked'] is True
    assert client.patch(f'/nodes/{nid}/status',json={'status':'doing'}).status_code==409
    blocked=client.post(f'/nodes/{nid}/reports',json=PAYLOAD)
    assert blocked.status_code==409 and blocked.json()['detail']=='尚有未完成的前置任務'
    with Session(engine) as db:db.get(Node,pre).status='skipped';db.commit()
    assert client.patch(f'/nodes/{nid}/status',json={'status':'doing'}).status_code==200
    with Session(engine) as db:db.get(Node,pre).status='doing';db.commit()
    assert client.post(f'/nodes/{nid}/reports',json=PAYLOAD).status_code==409
    switch(client,'yu')
    assert client.post(f'/nodes/{nid}/reports',json={**PAYLOAD,'self_approve':True}).status_code==409
    assert client.delete('/dependencies/'+edge.json()['id']).status_code==200
    assert client.post(f'/nodes/{nid}/reports',json={**PAYLOAD,'self_approve':True}).status_code==201


def test_dependencies_cycles_scope_and_permissions(client,engine):
    pre,nid,pid,users=pair(client,engine)
    created=client.post(f'/projects/{pid}/dependencies',json={'predecessor_id':pre,'successor_id':nid});assert created.status_code==201
    for a,b in [(pre,nid),(nid,pre),(pre,pre)]:
        assert client.post(f'/projects/{pid}/dependencies',json={'predecessor_id':a,'successor_id':b}).status_code in {409,422}
    with Session(engine) as db:
        original=db.get(Node,nid)
        project=Project(organization_id=original.organization_id,title='other',owner_user_id=users['yu']);db.add(project);db.flush()
        other=Node(organization_id=original.organization_id,project_id=project.id,kind='task',title='outside');db.add(other);db.commit();oid=other.id
    assert client.post(f'/projects/{pid}/dependencies',json={'predecessor_id':oid,'successor_id':nid}).status_code==404
    switch(client,'lin')
    assert client.post(f'/projects/{pid}/dependencies',json={'predecessor_id':nid,'successor_id':pre}).status_code==403
    assert client.delete('/dependencies/'+created.json()['id']).status_code==403
    switch(client,'ming')
    assert client.post(f'/projects/{pid}/dependencies',json={'predecessor_id':nid,'successor_id':pre}).status_code==403


def test_twenty_task_cycle_and_gate_still_independent(client,engine):
    pre,nid,pid,users=pair(client,engine)
    with Session(engine) as db:
        node=db.get(Node,nid);org=node.organization_id
        chain=[Node(organization_id=org,project_id=pid,kind='task',title=f'chain-{i}',owner_user_id=users['yu']) for i in range(20)]
        db.add_all(chain);db.flush();ids=[n.id for n in chain]
        phase=Node(organization_id=org,project_id=pid,kind='phase',title='prior',sort_order=-1,owner_user_id=users['yu']);db.add(phase);db.flush()
        gate=Gate(organization_id=org,project_id=pid,node_id=phase.id);db.add(gate)
        db.get(Node,pre).status='done';db.commit();gid=gate.id
    for a,b in zip(ids,ids[1:]):assert client.post(f'/projects/{pid}/dependencies',json={'predecessor_id':a,'successor_id':b}).status_code==201
    assert client.post(f'/projects/{pid}/dependencies',json={'predecessor_id':ids[-1],'successor_id':ids[0]}).status_code==409
    assert client.post(f'/projects/{pid}/dependencies',json={'predecessor_id':pre,'successor_id':nid}).status_code==201
    assert client.patch(f'/nodes/{nid}/status',json={'status':'doing'}).status_code==409
    assert client.post(f'/nodes/{nid}/reports',json=PAYLOAD).status_code==409
    assert client.patch(f'/gates/{gid}',json={'status':'approved'}).status_code==200
    assert client.patch(f'/nodes/{nid}/status',json={'status':'doing'}).status_code==200
