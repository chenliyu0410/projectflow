from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import Department, User
from test_tp_a_planner import tree, switch


def test_admin_department_members_and_references(client,engine,tree):
    switch(client,'yu')
    payload={'name':'新部門','member_ids':[tree['ming']],'head_user_id':tree['ming']}
    r=client.post('/departments',json=payload)
    assert r.status_code == 201,r.text
    did=r.json()['id']
    assert client.post('/departments',json=payload).status_code == 409
    assert client.patch('/departments/'+did,json={**payload,'member_ids':[]}).status_code == 422
    assert client.delete('/departments/'+did).status_code == 409
    assert client.patch('/departments/'+did,json={**payload,'member_ids':[],'head_user_id':None}).status_code == 200
    assert client.delete('/departments/'+did).status_code == 200
    with Session(engine) as db: d=db.scalar(select(Department).where(Department.head_user_id == tree['chen']));did=d.id
    assert client.delete('/departments/'+did).status_code == 409
    switch(client,'ming')
    assert client.post('/departments',json=payload).status_code == 403
    switch(client,'elaine',org='electronics')
    assert client.patch('/departments/'+did,json=payload).status_code == 404
