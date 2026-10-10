from datetime import date
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import Node, NodeDependency, NodeCondition, AuditLog
from test_dependencies import pair
from test_report_lifecycle import switch, PAYLOAD, snapshot


def edge(client, pid, a, b, **settings):
    r = client.post(f'/projects/{pid}/dependencies', json={'predecessor_id': a, 'successor_id': b, **settings})
    assert r.status_code == 201, r.text
    return r.json()


@pytest.mark.parametrize('kind,status,allowed', [('FS','doing',False),('FS','done',True),('SS','todo',False),('SS','doing',True),('SS','review',True),('SS','skipped',True),('FF','todo',True)])
def test_start_matrix(client, engine, kind, status, allowed):
    a,b,pid,_ = pair(client, engine)
    edge(client,pid,a,b,relation_type=kind,lag_days=5)
    with Session(engine) as db: db.get(Node,a).status=status; db.commit()
    r = client.patch(f'/nodes/{b}/status',json={'status':'doing'})
    assert r.status_code == (200 if allowed else 409)


def test_ff_submission_and_approval_recheck_atomic(client,engine):
    a,b,pid,_=pair(client,engine)
    edge(client,pid,a,b,relation_type='FF')
    before=snapshot(engine)
    assert client.post(f'/nodes/{b}/reports',json={**PAYLOAD,'self_approve':True}).status_code==409
    assert snapshot(engine)==before
    switch(client,'ming')
    r=client.post(f'/nodes/{b}/reports',json=PAYLOAD); assert r.status_code==201,r.text
    rid=r.json()['id']; switch(client,'yu'); before=snapshot(engine)
    assert client.post(f'/reports/{rid}/review',json={'decision':'approved'}).status_code==409
    assert snapshot(engine)==before
    with Session(engine) as db: db.get(Node,a).status='done'; db.commit()
    assert client.post(f'/reports/{rid}/review',json={'decision':'approved'}).status_code==200


def test_soft_hidden_warning_no_disclosure_and_edit_validation(client,engine):
    a,b,pid,_=pair(client,engine)
    e=edge(client,pid,a,b,enforcement='soft')
    for bad in [{'relation_type':'XX'},{'lag_days':366},{'lag_days':1.5},{'lag_days':True},{'enforcement':'override'}]:
        assert client.patch('/dependencies/'+e['id'],json=bad).status_code==422
    switch(client,'ming')
    r=client.patch(f'/nodes/{b}/status',json={'status':'doing'}); assert r.status_code==200
    assert r.json()['dependency_warnings']==['軟性前置尚未滿足，仍可繼續']
    assert 'hidden predecessor' not in r.text and a not in r.text
    assert client.patch('/dependencies/'+e['id'],json={'relation_type':'SS'}).status_code==403
    switch(client,'yu')
    assert client.patch('/dependencies/'+e['id'],json={'relation_type':'SS','lag_days':-2,'enforcement':'hard'}).status_code==200
    with Session(engine) as db: assert db.get(NodeDependency,e['id']).lag_days==-2


def test_manual_condition_confirm_revoke_copy_delete_undo(client,engine):
    a,b,pid,_=pair(client,engine)
    r=client.post(f'/projects/{pid}/conditions',json={'node_id':b,'label':'到貨已確認'}); assert r.status_code==201,r.text
    cid=r.json()['id']
    assert client.patch(f'/nodes/{b}/status',json={'status':'doing'}).status_code==409
    assert client.post(f'/conditions/{cid}/confirmation',json={'is_met':True,'reason':' '}).status_code==422
    switch(client,'ming')
    assert client.post(f'/conditions/{cid}/confirmation',json={'is_met':True,'reason':'不能代確認'}).status_code==403
    switch(client,'yu')
    assert client.post(f'/conditions/{cid}/confirmation',json={'is_met':True,'reason':'驗收到貨'}).status_code==200
    assert client.patch(f'/nodes/{b}/status',json={'status':'doing'}).status_code==200
    assert client.post(f'/conditions/{cid}/confirmation',json={'is_met':False,'reason':'重新確認'}).status_code==200
    # Revoking does not retroactively prevent a report on an active task.
    assert client.post(f'/nodes/{b}/reports',json=PAYLOAD).status_code==201
    r=client.post(f'/nodes/{b}/copy'); assert r.status_code==201,r.text
    copied=r.json()['id']
    with Session(engine) as db:
        c=db.scalar(select(NodeCondition).where(NodeCondition.node_id==copied))
        assert c.label=='到貨已確認' and not c.is_met and c.confirmed_by is None
    r=client.delete(f'/nodes/{b}'); assert r.status_code==200,r.text
    assert client.post(f'/conditions/{cid}/confirmation',json={'is_met':True,'reason':'已刪除'}).status_code==404
    assert client.post('/undo',json={'audit_id':r.json()['undo_id']}).status_code==200
    listing=client.get(f'/projects/{pid}/dependencies').json()
    assert any(c['id']==cid and c['reason']=='重新確認' for c in listing['conditions'])
    logs=client.get(f'/audit-logs?node_id={b}').json()['items']
    assert any(x['action']=='condition.confirm' and x['payload']['after']['reason']=='重新確認' for x in logs)


@pytest.mark.parametrize('kind,lag,expected', [('SS',2,6),('SS',-2,2),('FF',2,6),('FS',-1,6)])
def test_schedule_formulas_cascade(client,engine,kind,lag,expected):
    a,b,pid,_=pair(client,engine)
    with Session(engine) as db:
        for nid,start,end in [(a,1,3),(b,2,4)]:
            n=db.get(Node,nid); n.start_date=date(2026,10,start); n.due_date=date(2026,10,end)
        db.commit()
    edge(client,pid,a,b,relation_type=kind,lag_days=lag)
    r=client.post(f'/nodes/{a}/schedule',json={'start_date':'2026-10-04','due_date':'2026-10-06','cascade':True})
    assert r.status_code==200,r.text
    with Session(engine) as db: assert db.get(Node,b).start_date==date(2026,10,expected)


def test_condition_visibility_soft_and_company_scope(client,engine):
    a,b,pid,_=pair(client,engine)
    hidden=client.post(f'/projects/{pid}/conditions',json={'node_id':a,'label':'secret confirmation'}).json()
    soft=client.post(f'/projects/{pid}/conditions',json={'node_id':b,'label':'可稍後確認','enforcement':'soft'}).json()
    switch(client,'ming')
    listing=client.get(f'/projects/{pid}/dependencies')
    assert hidden['id'] not in listing.text and 'secret confirmation' not in listing.text
    assert client.patch(f'/nodes/{b}/status',json={'status':'doing'}).status_code==200
    switch(client,'lin')
    assert client.delete('/conditions/'+soft['id']).status_code==403
