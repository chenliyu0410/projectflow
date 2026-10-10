from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import Node, Notification, NodeDependency
from test_tp_a_planner import tree, switch


def test_notification_read_rechecks_visibility(client,engine,tree):
    switch(client,'owner')
    assert client.patch('/nodes/b',json={'owner_user_id':tree['ming']}).status_code == 200
    assert client.patch('/nodes/b',json={'owner_user_id':tree['yu']}).status_code == 200
    assert client.patch('/nodes/b',json={'owner_user_id':tree['ming']}).status_code == 200
    switch(client,'ming')
    page=client.get('/notifications').json();assert page['unread_count']==1
    nid=page['items'][0]['id']
    assert client.post('/notifications/'+nid+'/read').status_code == 200
    assert client.get('/notifications').json()['unread_count']==0
    switch(client,'owner')
    assert client.patch('/nodes/b',json={'owner_user_id':tree['yu']}).status_code == 200
    switch(client,'ming')
    assert client.get('/notifications').json()['items']==[]
    assert client.post('/notifications/'+nid+'/read').status_code == 404
    switch(client,'elaine',org='electronics')
    assert client.post('/notifications/'+nid+'/read').status_code == 404


def test_dependency_unlock_notifies_once(client,engine,tree):
    switch(client,'owner')
    assert client.post('/projects/tp/dependencies',json={'predecessor_id':'b','successor_id':'a'}).status_code == 201
    assert client.post('/nodes/b/requests',json={'kind':'skip','reason':'不需要','direct':True}).status_code == 201
    switch(client,'ming')
    rows=client.get('/notifications').json()['items']
    assert len([r for r in rows if r['node_id']=='a' and '前置' in r['message']])==1


def test_normal_gate_approval_notifies_unlock(client,engine,tree):
    from app.models import Gate
    with Session(engine) as db:
        ph=db.get(Node,'ph');ph.sort_order=20
        prior=Node(id='prior',organization_id=ph.organization_id,project_id='tp',kind='phase',title='前階段',sort_order=10,owner_user_id=tree['owner']);db.add(prior);db.flush()
        db.add(Gate(id='normal-gate',organization_id=ph.organization_id,project_id='tp',node_id='prior'));db.commit()
    switch(client,'owner')
    r=client.patch('/gates/normal-gate',json={'status':'approved'})
    assert r.status_code==200,r.text
    switch(client,'ming')
    assert any(r['node_id']=='a' and '前置' in r['message'] for r in client.get('/notifications').json()['items'])
