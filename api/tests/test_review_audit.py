import base64
from datetime import datetime,timezone
import json
import pytest
from sqlalchemy import event,select
from sqlalchemy.orm import Session
from app.models import AuditLog,Department,Gate,Node,NodeCollaborator,Project,TaskNote,TaskReport,User
from test_report_lifecycle import setup,switch,PAYLOAD
from test_projects_nodes import login


@pytest.mark.parametrize('actor,expected',[('yu',True),('chen',True),('ming',False),('lin',False),('owner',False)])
def test_review_queue_current_other_author_permissions(client,engine,actor,expected):
    nid,_,_=setup(client,engine)
    report=client.post(f'/nodes/{nid}/reports',json=PAYLOAD).json()
    switch(client,actor)
    response=client.get('/workspace/reviews',params={'kind':'report'})
    assert response.status_code==200
    assert [x['id'] for x in response.json()['items']]==([report['id']] if expected else [])
    if expected:
        item=response.json()['items'][0]
        assert item['type']=='report' and item['node_id']==nid and item['node_title']
        assert item['capabilities']['review_report'] is True and 'submitted_by_display_name' in item


def test_reviews_actual_owner_scoped_reviewer_revocation_and_gate_not_d60(client,engine):
    nid,pid,users=setup(client,engine)
    report=client.post(f'/nodes/{nid}/reports',json=PAYLOAD).json()
    with Session(engine) as db:
        node=db.get(Node,nid)
        gate=Gate(organization_id=node.organization_id,project_id=pid,node_id=nid)
        db.get(User,users['chen']).role='member'
        db.add(NodeCollaborator(organization_id=node.organization_id,node_id=nid,user_id=users['chen'],created_by=users['yu']))
        db.add(gate);db.commit();gid=gate.id
    switch(client,'chen')
    response=client.get('/workspace/reviews');assert response.status_code==200
    assert [x['id'] for x in response.json()['items']]==[report['id']]
    assert client.patch(f'/gates/{gid}',json={'status':'approved'}).status_code==403
    with Session(engine) as db:db.get(User,users['chen']).role='reviewer';db.commit()
    assert {x['id'] for x in client.get('/workspace/reviews').json()['items']}=={report['id'],gid}
    with Session(engine) as db:
        node=db.get(Node,nid);db.get(Department,node.department_id).head_user_id=users['yu'];db.commit()
    assert client.get('/workspace/reviews').json()['items']==[]
    assert client.post(f"/reports/{report['id']}/review",json={'decision':'approved'}).status_code==403
    switch(client,'owner')
    assert client.get('/workspace/reviews').json()['items']==[]
    with Session(engine) as db:db.get(Project,pid).owner_user_id=users['owner'];db.commit()
    assert {x['id'] for x in client.get('/workspace/reviews').json()['items']}=={report['id'],gid}


def test_review_queue_excludes_legacy_stale_and_invisible(client,engine):
    nid,pid,users=setup(client,engine,'yu')
    with Session(engine) as db:
        node=db.get(Node,nid);org=node.organization_id
        db.add(TaskReport(organization_id=org,node_id=nid,result='old',summary='legacy',submitted_by=users['ming']))
        hidden=Node(organization_id=org,project_id=pid,kind='task',title='SECRET NODE',owner_user_id=users['yu'])
        db.add(hidden);db.flush()
        db.add(Gate(organization_id=org,project_id=pid,node_id=hidden.id))
        db.get(Project,pid).owner_user_id=users['ming'];db.commit()
    switch(client,'ming')
    response=client.get('/workspace/reviews');assert response.status_code==200
    assert response.json()=={'items':[],'next_cursor':None} and 'SECRET' not in response.text


def audit(db,node,actor,action,payload,*,identifier=None,stamp=None):
    row=AuditLog(organization_id=node.organization_id,actor_user_id=actor,node_id=node.id,action=action,payload=payload)
    if identifier:row.id=identifier
    if stamp:row.created_at=stamp
    db.add(row)
    return row


def test_audit_visibility_unknown_fields_names_and_hidden_reference_redaction(client,engine):
    nid,pid,users=setup(client,engine)
    with Session(engine) as db:
        node=db.get(Node,nid);org=node.organization_id
        hidden=Node(organization_id=org,project_id=pid,kind='task',title='SECRET hidden',owner_user_id=users['yu'])
        db.add(hidden);db.flush()
        hidden_note=TaskNote(organization_id=org,node_id=hidden.id,body='SECRET note',author_id=users['yu'])
        own_note=TaskNote(organization_id=org,node_id=nid,body='safe',author_id=users['ming'])
        db.add_all([hidden_note,own_note]);db.flush()
        audit(db,node,users['ming'],'unknown.event',{'password':'SECRET password','node_id':hidden.id})
        audit(db,node,users['ming'],'note.update',{'note_id':hidden_note.id,'before':{'body':'SECRET before','revision':1},'after':{'body':'SECRET after','revision':2}})
        audit(db,node,users['ming'],'note.update',{'note_id':own_note.id,'before':{'body':'old','revision':1,'secret':'SECRET extra'},'after':{'body':'new','revision':2},'storage_key':'SECRET key'})
        audit(db,hidden,users['yu'],'node.status',{'status':'done'})
        db.add(AuditLog(organization_id=org,actor_user_id=users['yu'],node_id=None,action='workflow.instantiate',payload={'title':'SECRET node-null'}))
        db.commit();hidden_id=hidden.id;hnid=hidden_note.id
    response=client.get('/audit-logs');assert response.status_code==200
    assert 'SECRET' not in response.text and hidden_id not in response.text and hnid not in response.text
    assert 'actor_username' not in response.text and 'storage_key' not in response.text
    items=response.json()['items'];assert len(items)==3
    assert all(x['actor_user_id']==users['ming'] and x['actor_display_name'] for x in items)
    safe=next(x for x in items if x['payload'].get('note_id'))
    assert safe['payload']['before']=={'body':'old','revision':1} and safe['payload']['after']=={'body':'new','revision':2}
    assert next(x for x in items if x['action']=='unknown.event')['payload']=={}
    switch(client,'yu')
    assert any(x['node_id'] is None for x in client.get('/audit-logs').json()['items'])


def test_audit_node_metadata_references_and_unknown_shapes_are_safe(client,engine):
    nid,pid,users=setup(client,engine)
    with Session(engine) as db:
        node=db.get(Node,nid)
        hidden=Node(organization_id=node.organization_id,project_id=pid,kind='task',title='SECRET',owner_user_id=users['yu'])
        db.add(hidden);db.flush()
        audit(db,node,users['ming'],'node.create',{'title':'safe','kind':'task','parent_id':hidden.id,'parent_title':'SECRET','project_id':pid,'owner_user_id':users['ming'],'department_id':None})
        audit(db,node,users['ming'],'node.update',{'title':{'before':'old','after':'new'},'owner_user_id':{'before':'foreign','after':users['ming']},'parent_id':{'before':hidden.id,'after':None},'session':'SECRET'})
        audit(db,node,users['ming'],'note.update',{'note_id':['bad'],'before':['SECRET'],'after':{'body':{'password':'SECRET'}}})
        db.commit();hid=hidden.id
    response=client.get('/audit-logs');assert response.status_code==200
    assert 'SECRET' not in response.text and hid not in response.text and 'foreign' not in response.text
    assert any(x['payload'].get('title')=={'before':'old','after':'new'} for x in response.json()['items'])


def test_audit_authorize_before_stable_pagination_and_revocation(client,engine):
    nid,pid,users=setup(client,engine)
    stamp=datetime(2026,10,8,tzinfo=timezone.utc)
    with Session(engine) as db:
        node=db.get(Node,nid)
        hidden=Node(organization_id=node.organization_id,project_id=pid,kind='task',title='SECRET',owner_user_id=users['yu'])
        db.add(hidden);db.flush()
        for i in range(10):audit(db,hidden,users['yu'],'node.status',{'status':'done'},identifier=f'hidden-{i}',stamp=stamp)
        for i in range(3):audit(db,node,users['ming'],'node.status',{'status':'doing'},identifier=f'visible-{i}',stamp=stamp)
        db.commit()
    result=client.get('/audit-logs',params={'limit':1});assert result.status_code==200
    assert set(result.json())=={'items','next_cursor'}
    cursor=result.json()['next_cursor'];assert cursor
    ids=[result.json()['items'][0]['id']]
    while cursor:
        response=client.get('/audit-logs',params={'limit':1,'cursor':cursor})
        assert response.status_code==200 and 'hidden' not in response.text
        ids.extend(x['id'] for x in response.json()['items']);cursor=response.json()['next_cursor']
    assert ids==['visible-2','visible-1','visible-0']
    with Session(engine) as db:db.get(Node,nid).owner_user_id=users['yu'];db.commit()
    assert client.get('/audit-logs').json()=={'items':[],'next_cursor':None}
    assert client.get('/audit-logs',params={'node_id':nid}).json()['items']==[]


@pytest.mark.parametrize('path,params',[('/workspace/reviews',{'kind':'invalid'}),('/workspace/reviews',{'limit':0}),
    ('/audit-logs',{'limit':101}),('/audit-logs',{'cursor':'garbage'}),('/workspace/reviews',{'cursor':'garbage'})])
def test_new_pagination_invalid_inputs(client,engine,path,params):
    setup(client,engine)
    assert client.get(path,params=params).status_code==422


def test_cursor_binds_company_endpoint_filters_and_extreme_input(client,engine):
    nid,_,users=setup(client,engine)
    with Session(engine) as db:
        node=db.get(Node,nid)
        for _ in range(2):audit(db,node,users['ming'],'node.status',{'status':'doing'})
        db.commit()
    response=client.get('/audit-logs',params={'limit':1});assert response.status_code==200
    cursor=response.json()['next_cursor'];assert cursor
    assert client.get('/workspace/reviews',params={'cursor':cursor}).status_code==422
    assert client.get('/audit-logs',params={'cursor':cursor,'action':'node.status'}).status_code==422
    assert client.get('/audit-logs',params={'cursor':cursor,'node_id':nid}).status_code==422
    data=json.loads(base64.urlsafe_b64decode(cursor))
    for stamp in ['0001-01-01T00:00:00+01:00','9999-12-31T23:59:59-01:00']:
        data['key'][0]=stamp
        bad=base64.urlsafe_b64encode(json.dumps(data).encode()).decode()
        assert client.get('/audit-logs',params={'cursor':bad}).status_code==422
    nested=base64.urlsafe_b64encode(('['*760+'0'+']'*760).encode()).decode()
    assert client.get('/audit-logs',params={'cursor':nested}).status_code==422
    client.post('/auth/logout');login(client,org='electronics',username='elaine')
    assert client.get('/audit-logs',params={'cursor':cursor}).status_code==422


@pytest.mark.parametrize('path',['/audit-logs','/workspace/reviews'])
def test_query_count_is_constant_with_more_visible_events(client,engine,path):
    nid,pid,users=setup(client,engine,'yu')
    def count():
        statements=[]
        def before(*args):
            if args[2].lstrip().upper().startswith('SELECT'):statements.append(args[2])
        event.listen(engine,'before_cursor_execute',before)
        try:assert client.get(path).status_code==200
        finally:event.remove(engine,'before_cursor_execute',before)
        return len(statements)
    baseline=count()
    with Session(engine) as db:
        original=db.get(Node,nid)
        for i in range(30):
            node=Node(organization_id=original.organization_id,project_id=pid,kind='task',title=f'visible {i}',owner_user_id=users['yu'])
            db.add(node);db.flush()
            audit(db,node,users['yu'],'node.status',{'status':'doing'})
            db.add(Gate(organization_id=node.organization_id,project_id=pid,node_id=node.id))
        db.commit()
    assert count()==baseline


def test_mixed_review_types_have_stable_cursor_and_filter_binding(client,engine):
    nid,pid,users=setup(client,engine,'yu')
    stamp=datetime(2026,10,8,tzinfo=timezone.utc)
    with Session(engine) as db:
        node=db.get(Node,nid);node.status='review'
        db.add(TaskReport(id='same-id',organization_id=node.organization_id,node_id=nid,workflow_version=2,
                          version=1,result='達成',summary='queued',finished_on=stamp.date(),submitted_by=users['ming'],submitted_at=stamp))
        db.add(Gate(id='same-id',organization_id=node.organization_id,project_id=pid,node_id=nid,created_at=stamp))
        db.commit()
    first=client.get('/workspace/reviews',params={'limit':1}).json()
    assert first['items'][0]['type']=='gate' and first['next_cursor']
    second=client.get('/workspace/reviews',params={'limit':1,'cursor':first['next_cursor']}).json()
    assert second['items'][0]['type']=='report' and second['next_cursor'] is None
    assert client.get('/workspace/reviews',params={'kind':'report','cursor':first['next_cursor']}).status_code==422
    with Session(engine) as db:db.get(Node,nid).status='doing';db.commit()
    assert client.get('/workspace/reviews',params={'kind':'report'}).json()['items']==[]


def test_audit_all_hidden_record_references_remove_dependent_payload(client,engine):
    from app.models import Attachment
    nid,pid,users=setup(client,engine)
    with Session(engine) as db:
        node=db.get(Node,nid);org=node.organization_id
        hidden=Node(organization_id=org,project_id=pid,kind='task',title='SECRET',owner_user_id=users['yu'])
        db.add(hidden);db.flush()
        report=TaskReport(organization_id=org,node_id=hidden.id,result='old',summary='SECRET',submitted_by=users['yu'])
        attachment=Attachment(organization_id=org,node_id=hidden.id,uploaded_by=users['yu'],original_name='SECRET.txt',storage_key='a'*32,size_bytes=1,state='ready',sha256='0'*64)
        gate=Gate(organization_id=org,project_id=pid,node_id=hidden.id)
        db.add_all([report,attachment,gate]);db.flush()
        audit(db,node,users['ming'],'report.reject',{'report_id':report.id,'comment':'SECRET review','version':1})
        audit(db,node,users['ming'],'attachment.upload',{'attachment_id':attachment.id,'original_name':'SECRET.txt','size_bytes':1})
        audit(db,node,users['ming'],'gate.approve',{'gate_id':gate.id,'status':'approved'})
        audit(db,node,users['ming'],'collaborators.update',{'before':{'users':[{'id':'foreign','display_name':'SECRET'}]},
            'after':{'users':[{'id':users['ming'],'display_name':'SECRET forged'}],'revision':1}})
        db.commit();hidden_refs=[report.id,attachment.id,gate.id]
    response=client.get('/audit-logs');assert response.status_code==200
    assert 'SECRET' not in response.text and all(ref not in response.text for ref in hidden_refs)
    for item in response.json()['items']:
        if item['action']!='collaborators.update':assert item['payload']=={}
        else:
            assert item['payload']['before']['users']==[]
            assert item['payload']['after']['users'][0]['id']==users['ming']
