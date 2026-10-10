from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import Node, TaskReport, CollaborationRequest, Notification, Department
from test_tp_a_planner import tree, switch, PAYLOAD


def test_skip_decision_restores_subtree(client,engine,tree):
    switch(client,'ming')
    response=client.post('/nodes/a/requests',json={'kind':'skip','reason':'工作不再需要'})
    assert response.status_code == 201,response.text
    rid=response.json()['id']
    assert client.post('/requests/'+rid+'/decision',json={'decision':'approved'}).status_code == 403
    switch(client,'chen')
    assert client.get('/workspace/requests').json()['items'][0]['can_review']
    result=client.post('/requests/'+rid+'/decision',json={'decision':'approved'})
    assert result.status_code == 200,result.text
    with Session(engine) as db:
        assert db.get(Node,'a').status == db.get(Node,'a1').status == 'skipped'
    assert client.post('/requests/'+rid+'/decision',json={'decision':'approved'}).status_code == 409
    switch(client,'owner')
    result=client.post('/nodes/a/lifecycle',json={'action':'restore','reason':'重新執行'})
    assert result.status_code == 200,result.text
    with Session(engine) as db:
        assert db.get(Node,'a').status == db.get(Node,'a1').status == 'todo'


def test_direct_and_restore_fence(client,engine,tree):
    switch(client,'owner')
    assert client.post('/nodes/a/requests',json={'kind':'skip','reason':'略過','direct':True}).status_code == 201
    assert client.patch('/nodes/a1',json={'title':'新名稱'}).status_code == 200
    assert client.post('/nodes/a/lifecycle',json={'action':'restore','reason':'恢復'}).status_code == 409


def test_request_change_and_permissions(client,engine,tree):
    switch(client,'ming')
    assert client.post('/nodes/a/requests',json={'kind':'skip','reason':' ','direct':False}).status_code == 422
    assert client.post('/nodes/a/requests',json={'kind':'skip','reason':'略過','direct':True}).status_code == 403
    rid=client.post('/nodes/a/requests',json={'kind':'skip','reason':'略過'}).json()['id']
    assert client.post('/nodes/a/requests',json={'kind':'skip','reason':'重複'}).status_code == 409
    with Session(engine) as db:
        db.get(Node,'a1').status='done';db.commit()
    switch(client,'owner')
    assert client.post('/requests/'+rid+'/decision',json={'decision':'approved'}).status_code == 409
    assert client.post('/requests/'+rid+'/decision',json={'decision':'rejected','comment':'狀態已變'}).status_code == 409
    with Session(engine) as db: assert db.get(CollaborationRequest,rid).status == 'expired'
    switch(client,'elaine',org='electronics')
    assert client.post('/nodes/a/requests',json={'kind':'skip','reason':'跨公司'}).status_code == 404


def test_head_sees_unassigned_and_can_assign(client,engine,tree):
    with Session(engine) as db:
        d=db.scalar(select(Department).where(Department.head_user_id == tree['chen']))
        d.head_user_id=tree['ming'];db.get(Node,'h').owner_user_id=None;db.commit()
    switch(client,'ming')
    items=client.get('/workspace/my-tasks').json()['items']
    assert 'awaiting_assignment' in next(n for n in items if n['id']=='h')['relations']
    response=client.patch('/nodes/h',json={'owner_user_id':tree['chen']})
    assert response.status_code == 200,response.text
    switch(client,'chen')
    assert any(n['node_id']=='h' for n in client.get('/notifications').json()['items'])


def test_start_override_is_not_permanent(client,engine,tree):
    switch(client,'owner')
    assert client.post('/projects/tp/dependencies',json={'predecessor_id':'b','successor_id':'a'}).status_code == 201
    r=client.post('/nodes/a/requests',json={'kind':'start','reason':'先行工作','direct':True})
    assert r.status_code == 201,r.text
    switch(client,'ming')
    assert client.patch('/nodes/a/status',json={'status':'todo'}).status_code == 200
    assert client.patch('/nodes/a/status',json={'status':'doing'}).status_code == 409


def test_report_exception_preserves_review_process(client,engine,tree):
    switch(client,'ming')
    r=client.post('/nodes/a/reports',json={**PAYLOAD,'override_reason':'先回報父任務','request_override':True})
    assert r.status_code == 201,r.text
    rid=r.json()['id']
    with Session(engine) as db: assert db.get(Node,'a').status=='todo'
    switch(client,'chen')
    r=client.post('/requests/'+rid+'/decision',json={'decision':'approved'})
    assert r.status_code == 200,r.text
    with Session(engine) as db:
        assert db.get(Node,'a').status=='review'
        report=db.scalar(select(TaskReport).where(TaskReport.node_id=='a'));report_id=report.id
    assert client.post('/reports/'+report_id+'/review',json={'decision':'approved'}).status_code==409
    r=client.post('/reports/'+report_id+'/review',json={'decision':'approved','override_reason':'確認例外完成'})
    assert r.status_code==200,r.text


def test_changed_condition_expires_request(client,engine,tree):
    switch(client,'owner')
    condition=client.post('/projects/tp/conditions',json={'node_id':'a','label':'原條件','enforcement':'hard'}).json()
    switch(client,'ming')
    rid=client.post('/nodes/a/requests',json={'kind':'start','reason':'先行'}).json()['id']
    switch(client,'owner')
    assert client.patch('/conditions/'+condition['id'],json={'label':'全新條件'}).status_code==200
    assert client.post('/requests/'+rid+'/decision',json={'decision':'approved'}).status_code==409
    with Session(engine) as db:
        assert db.get(Node,'a').status=='todo'
        assert db.get(CollaborationRequest,rid).status=='expired'


def test_invalid_report_request_and_pending_report_rejected(client,engine,tree):
    switch(client,'ming')
    assert client.post('/nodes/b/requests',json={'kind':'report_submit','reason':'缺內容'}).status_code==422
    assert client.post('/nodes/b/reports',json=PAYLOAD).status_code==201
    assert client.post('/nodes/b/reports',json={**PAYLOAD,'override_reason':'重送','request_override':True}).status_code==409


def test_parent_override_does_not_authorize_closed_ancestor_work(client,engine,tree):
    switch(client,'owner')
    r=client.post('/nodes/ph/requests',json={'kind':'phase_complete','reason':'階段結案','direct':True})
    assert r.status_code==201,r.text
    switch(client,'ming')
    assert client.patch('/nodes/b/status',json={'status':'doing'}).status_code==409
    assert client.post('/nodes/b/reports',json=PAYLOAD).status_code==409


def test_skip_pending_report_restores_doing_and_readonly_denied(client,engine,tree):
    switch(client,'ming')
    assert client.post('/nodes/a1/reports',json=PAYLOAD).status_code==201
    switch(client,'owner')
    assert client.post('/nodes/a/requests',json={'kind':'skip','reason':'暫停','direct':True}).status_code==201
    with Session(engine) as db:
        report=db.scalar(select(TaskReport).where(TaskReport.node_id=='a1'))
        assert report.status=='rejected'
    assert client.post('/nodes/a/lifecycle',json={'action':'restore','reason':'恢復'}).status_code==200
    with Session(engine) as db: assert db.get(Node,'a1').status=='doing'
    switch(client,'lin')
    assert client.post('/nodes/a/requests',json={'kind':'skip','reason':'不允許'}).status_code==403
