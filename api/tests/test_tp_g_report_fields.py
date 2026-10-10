import pytest
from sqlalchemy.orm import Session
from app.models import Node, TaskReport, CollaborationRequest
from test_tp_a_planner import tree, switch, PAYLOAD


def definition(kind='text', **kwargs):
    return {'label': '測試欄位', 'type': kind, **kwargs}


def save(client, fields, version=0, node='b'):
    return client.put(f'/nodes/{node}/report-fields', json={'expected_version': version, 'fields': fields})


def test_fields_snapshot_zero_and_history(client, engine, tree):
    switch(client, 'yu')
    r = save(client, [definition('number', required=True, unit='kg'), definition('date'), definition('select', options=['合格','不合格']), definition()])
    assert r.status_code == 200, r.text
    fields = r.json()['fields']; ids = [f['id'] for f in fields]
    assert client.post('/nodes/b/reports', json=PAYLOAD).status_code == 409
    assert client.post('/nodes/b/reports', json={**PAYLOAD, 'fields_version':1}).status_code == 422
    values = {ids[0]:0, ids[1]:'2026-10-10', ids[2]:'合格', ids[3]:'<script>保留文字</script>'}
    r = client.post('/nodes/b/reports', json={**PAYLOAD, 'fields_version':1, 'field_values':values})
    assert r.status_code == 201, r.text
    report = r.json(); assert report['fields'][0]['value'] == 0
    assert save(client, [], 1).status_code == 409
    switch(client, 'owner')
    assert client.post(f'/reports/{report["id"]}/review', json={'decision':'rejected','comment':'重測'}).status_code == 200
    assert save(client, [], 1).status_code == 200
    with Session(engine) as db:
        assert db.get(TaskReport, report['id']).fields == report['fields']
    switch(client, 'yu')
    assert client.post('/nodes/b/reports', json={**PAYLOAD,'fields_version':1,'field_values':values}).status_code == 409
    assert client.post('/nodes/b/reports', json={**PAYLOAD,'fields_version':2}).status_code == 201


@pytest.mark.parametrize('field', [definition('select',options=['x']), definition('select',options=['x','x']), definition(unit='bad'), definition(label=' '), definition('date',options=['x','y'])])
def test_definition_validation(client, tree, field):
    switch(client,'yu'); assert save(client,[field]).status_code == 422


@pytest.mark.parametrize('kind,value,extra', [('number','NaN',{}),('number',True,{}),('number','Infinity',{}),('date','2026-02-30',{}),('date','20261010',{}),('select','不在選項',{'options':['a','b']}),('text','x'*4001,{})])
def test_value_validation(client, tree, kind, value, extra):
    switch(client,'yu'); field=save(client,[definition(kind,**extra)]).json()['fields'][0]
    r=client.post('/nodes/b/reports',json={**PAYLOAD,'fields_version':1,'field_values':{field['id']:value}})
    assert r.status_code == 422,r.text


def test_permissions_order_and_stale_write(client, tree):
    switch(client,'ming')
    r=save(client,[definition(label='甲'),definition(label='乙')]); assert r.status_code == 200,r.text
    fields=r.json()['fields']
    assert save(client,list(reversed(fields)),1).status_code == 200
    assert save(client,[],1).status_code == 409
    assert save(client,[{**fields[0],'label':'改名'}],2).status_code == 422
    assert save(client,[fields[0],fields[0]],2).status_code == 422
    assert save(client,[],node='a').status_code == 409
    assert save(client,[],node='done1').status_code == 409
    switch(client,'lin'); assert save(client,[]).status_code in {403,404}
    switch(client,'elaine',org='electronics'); assert client.get('/nodes/b/report-fields').status_code == 404


def test_copy_template_and_parent_preservation(client, engine, tree):
    switch(client,'yu'); field=save(client,[definition(required=True)]).json()['fields'][0]
    copied=client.post('/nodes/b/copy',json={})
    assert copied.status_code in {200,201},copied.text
    with Session(engine) as db:
        copies=list(db.query(Node).filter(Node.project_id=='tp',Node.title.like('另一個任務%'),Node.id!='b'))
        assert len(copies)==1
        assert copies[0].report_fields[0]['id'] != field['id']
    saved=client.post('/nodes/b/save-template',json={'name':'欄位模板'})
    assert saved.status_code in {200,201},saved.text
    assert saved.json()['nodes'][0]['report_fields'][0]['label'] == field['label']
    with Session(engine) as db:
        parent=db.get(Node,'b'); db.add(Node(id='new-child',organization_id=parent.organization_id,project_id=parent.project_id,parent_id='b',kind='task',title='子',status='todo'));db.commit()
    assert client.get('/nodes/b/report-fields').json()['fields'] == []
    assert save(client,[],1).status_code == 409
    with Session(engine) as db: assert db.get(Node,'b').report_fields[0]['id'] == field['id']


def test_unknown_fields_and_closed_ancestor(client, engine, tree):
    switch(client,'yu')
    assert client.post('/nodes/b/reports',json={**PAYLOAD,'field_values':{'unknown':'bad'}}).status_code == 422
    with Session(engine) as db: db.get(Node,'ph').status='done';db.commit()
    assert save(client,[definition()]).status_code == 409


def test_template_versions_apply_and_undo(client, engine, tree):
    switch(client,'yu')
    original=save(client,[definition('number',required=True,unit='kg')]).json()['fields'][0]
    template=client.post('/nodes/b/save-template',json={'name':'TP-G version'}).json()
    assert save(client,[],1).status_code == 200
    v2=client.post('/nodes/b/save-template',json={'name':template['name'],'template_id':template['id'],'expected_version':1})
    assert v2.status_code == 201,v2.text
    applied=client.post('/projects/tp/apply-template',json={'template_id':template['id'],'version':1})
    assert applied.status_code == 201,applied.text
    nid=applied.json()['node_ids'][0]
    fields=client.get(f'/nodes/{nid}/report-fields').json()['fields']
    assert len(fields)==1 and fields[0]['id'] != original['id'] and fields[0]['unit']=='kg'
    assert client.post('/undo',json={'audit_id':applied.json()['undo_id']}).status_code == 200
    copied=client.post(f'/workflows/{template["id"]}/copy',json={})
    assert copied.status_code == 201,copied.text
    assert copied.json()['nodes'][0]['report_fields']==[]
    with Session(engine) as db: assert db.query(TaskReport).filter(TaskReport.node_id==nid).count()==0


def test_exception_preserves_fields_and_revalidates_before_approval(client, engine, tree):
    switch(client,'ming')
    field=save(client,[definition(required=True)]).json()['fields'][0]
    payload={**PAYLOAD,'fields_version':1,'request_override':True,'override_reason':'測試例外'}
    assert client.post('/nodes/b/reports',json=payload).status_code==422
    requested=client.post('/nodes/b/reports',json={**payload,'field_values':{field['id']:'保留'}})
    assert requested.status_code==201,requested.text
    assert requested.json()['fields'][0]['value']=='保留'
    assert save(client,[],1).status_code==200
    switch(client,'yu')
    response=client.post(f'/requests/{requested.json()["id"]}/decision',json={'decision':'approved'})
    assert response.status_code==409,response.text
    with Session(engine) as db:
        assert db.query(TaskReport).filter(TaskReport.node_id=='b').count()==0
        assert db.get(CollaborationRequest,requested.json()['id']).status=='expired'
    switch(client,'ming')
    assert client.post('/nodes/b/reports',json={**payload,'fields_version':2}).status_code==201


def test_workflow_creation_and_parent_field_validation(client, tree):
    switch(client,'yu')
    payload={'name':'TP-G workflow','nodes':[{'id':'phase','title':'Phase','kind':'phase'},
        {'id':'task','parent_id':'phase','title':'Task','kind':'task','report_fields':[definition('date',required=True)]}]}
    saved=client.post('/workflows',json=payload)
    assert saved.status_code==201,saved.text
    template=saved.json()
    made=client.post('/projects/from-workflow',json={'title':'TP-G new project','workflow_id':template['id']})
    assert made.status_code==201,made.text
    tasks=[n for n in client.get(f'/projects/{made.json()["id"]}').json()['nodes'] if n['kind']=='task']
    fieldset=client.get(f'/nodes/{tasks[0]["id"]}/report-fields').json()
    assert fieldset['version']==1 and fieldset['fields'][0]['type']=='date'
    payload['name']='invalid phase';payload['nodes'][0]['report_fields']=[definition()]
    assert client.post('/workflows',json=payload).status_code==422
    del payload['nodes'][0]['report_fields']
    payload['nodes'].append({'id':'child','parent_id':'task','title':'Child','kind':'task'})
    assert client.post('/workflows',json=payload).status_code==422
