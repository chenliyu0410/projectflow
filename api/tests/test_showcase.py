import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import Workflow, WorkflowNode, User, Organization


def login(client, username='yu'):
    client.base_url = 'http://127.0.0.1'
    response = client.post('/auth/login', json={'organization_key': 'food', 'username': username, 'password': 'demo-'+username})
    assert response.status_code == 200
    return response


def test_catalog_has_complete_valid_industry_flows(client):
    login(client)
    response = client.get('/workflow-catalog')
    assert response.status_code == 200
    entries = response.json()['items']
    assert len(entries) >= 12
    assert {e['industry'] for e in entries} == {'food','electronics','events','software','construction'}
    from app.schemas import WorkflowWrite
    from app.services.workflow_service import validate_graph
    for e in entries:
        assert len([n for n in e['nodes'] if n['kind']=='phase']) >= 2
        assert len([n for n in e['nodes'] if n['kind']=='task']) >= 4
        validate_graph(WorkflowWrite(name=e['name'], nodes=e['nodes'], dependencies=e['dependencies']))
    assert len(next(e for e in entries if e['key']=='wf-laptop')['nodes']) == 53


@pytest.mark.parametrize("username", ["ming", "lin", "chen", "owner"])
def test_showcase_rejects_nonadmin_even_when_enabled(client, monkeypatch, username):
    monkeypatch.setenv('PF_SHOWCASE_MODE','true')
    login(client,username)
    response = client.post('/auth/showcase/switch', json={'organization_key':'electronics'})
    assert response.status_code == 403


def prepare(engine, monkeypatch):
    monkeypatch.setenv('PF_SHOWCASE_MODE','true')
    from app.showcase import provision
    with Session(engine) as db:
        result=provision(db); db.commit()
    return result


def test_provision_is_additive_idempotent_and_preserves_edits(client, engine, monkeypatch):
    from app.showcase import provision, identifier
    with Session(engine) as db:
        original=[(w.id,w.name,w.content) for w in db.scalars(select(Workflow))]
    assert prepare(engine,monkeypatch)=={'organizations':3,'users':5,'workflows':12}
    with Session(engine) as db:
        for wid,name,content in original:
            w=db.get(Workflow,wid);assert (w.name,w.content)==(name,content)
        edited=db.get(Workflow,identifier('workflow:food:food-development'))
        edited.name='使用者已自訂';edited.content={'custom':'retained'};db.commit()
        assert provision(db)=={'organizations':0,'users':0,'workflows':0}
        db.commit();assert edited.name=='使用者已自訂' and edited.content=={'custom':'retained'}


def test_switch_rotates_session_and_keeps_real_company_isolation(client,engine,monkeypatch):
    prepare(engine,monkeypatch)
    original=login(client).json()
    food_id=client.get('/projects').json()['items'][0]['id']
    cookie=client.cookies.get('pf_session')
    response=client.post('/auth/showcase/switch',json={'organization_key':'electronics'},headers={'Origin':'http://127.0.0.1'})
    assert response.status_code==200
    assert response.json()['showcase']['active'] is True
    assert response.json()['organization']['key']=='electronics'
    assert response.json()['user']['id']!=original['user']['id']
    assert 'HttpOnly' in response.headers['set-cookie']
    assert client.get('/projects/'+food_id).status_code==404
    assert len(client.get('/workflows').json()['items'])==4
    token=client.cookies.get('pf_session'); assert token!=cookie
    assert client.get('/auth/me',headers={'cookie':'pf_session='+cookie}).status_code==401
    client.cookies.clear();client.cookies.set('pf_session',token)
    assert client.post('/auth/showcase/switch',json={'organization_key':'events'}).status_code==200
    assert len(client.get('/workflows').json()['items'])==3
    monkeypatch.setenv('PF_SHOWCASE_MODE','false')
    assert client.get('/auth/me').status_code==401


def test_showcase_off_remote_origin_unknown_and_missing_target(client,engine,monkeypatch):
    login(client)
    assert client.post('/auth/showcase/switch',json={'organization_key':'events'}).status_code==404
    assert 'showcase' not in client.get('/auth/me').json()
    monkeypatch.setenv('PF_SHOWCASE_MODE','true')
    assert client.post('/auth/showcase/switch',json={'organization_key':'unknown'}).status_code==404
    assert client.post('/auth/showcase/switch',json={'organization_key':'events'}).status_code==409
    assert client.get('/auth/me').status_code==200
    assert client.post('/auth/showcase/switch',json={'organization_key':'events'},headers={'Origin':'https://example.org'}).status_code==403
    assert client.post('/auth/showcase/switch',json={'organization_key':'events'},headers={'Host':'192.168.0.1'}).status_code==404
    assert client.post('/auth/showcase/switch',json={'organization_key':'events'},headers={'sec-fetch-site':'cross-site'}).status_code==403
    client.cookies.clear()
    assert client.post('/auth/showcase/switch',json={'organization_key':'events'}).status_code==401


def test_readonly_cannot_import_catalog(client):
    login(client,'lin')
    result=client.get('/workflow-catalog').json()
    assert result['can_import'] is False
    item=result['items'][0]
    assert client.post('/workflows',json={k:item[k] for k in ['name','nodes','dependencies']}).status_code==403


LAN = 'http://172.22.32.95:15173'


def lan_login(client, username='yu'):
    client.base_url = LAN
    response = client.post('/auth/login', json={'organization_key': 'food', 'username': username, 'password': 'demo-'+username})
    assert response.status_code == 200
    return response


def test_lan_switch_needs_both_flags_and_keeps_lan_session(client, engine, monkeypatch):
    prepare(engine, monkeypatch)
    monkeypatch.setenv('PF_SHOWCASE_LAN', 'true')
    assert lan_login(client).json()['showcase']['active'] is False
    response = client.post('/auth/showcase/switch', json={'organization_key': 'electronics'}, headers={'Origin': LAN})
    assert response.status_code == 200
    assert response.json()['organization']['key'] == 'electronics'
    assert client.get('/auth/me').json()['showcase']['active'] is True
    assert client.post('/auth/showcase/switch', json={'organization_key': 'events'}, headers={'Origin': LAN}).status_code == 200
    monkeypatch.setenv('PF_SHOWCASE_LAN', 'false')
    assert client.get('/auth/me').status_code == 401


def test_lan_flag_alone_does_not_enable_showcase(client, monkeypatch):
    monkeypatch.setenv('PF_SHOWCASE_LAN', 'true')
    monkeypatch.setenv('PF_SHOWCASE_MODE', 'false')
    lan_login(client)
    assert 'showcase' not in client.get('/auth/me').json()
    assert client.post('/auth/showcase/switch', json={'organization_key': 'events'}, headers={'Origin': LAN}).status_code == 404


def test_lan_switch_without_lan_flag_stays_hidden(client, engine, monkeypatch):
    prepare(engine, monkeypatch)
    monkeypatch.delenv('PF_SHOWCASE_LAN', raising=False)
    lan_login(client)
    assert 'showcase' not in client.get('/auth/me').json()
    assert client.post('/auth/showcase/switch', json={'organization_key': 'events'}, headers={'Origin': LAN}).status_code == 404


@pytest.mark.parametrize("username", ["ming", "lin", "chen", "owner"])
def test_lan_switch_still_rejects_nonadmin(client, engine, monkeypatch, username):
    prepare(engine, monkeypatch)
    monkeypatch.setenv('PF_SHOWCASE_LAN', 'true')
    lan_login(client, username)
    assert client.post('/auth/showcase/switch', json={'organization_key': 'electronics'}, headers={'Origin': LAN}).status_code == 403


def test_lan_switch_still_rejects_cross_site(client, engine, monkeypatch):
    prepare(engine, monkeypatch)
    monkeypatch.setenv('PF_SHOWCASE_LAN', 'true')
    lan_login(client)
    assert client.post('/auth/showcase/switch', json={'organization_key': 'events'}, headers={'Origin': 'https://example.org'}).status_code == 403
    assert client.post('/auth/showcase/switch', json={'organization_key': 'events'}, headers={'sec-fetch-site': 'cross-site'}).status_code == 403
    assert client.get('/auth/me').status_code == 200
