import hashlib
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Node
from app.rag.models import RagChunk, RagIndex, RagQuery, RagSettings
from test_report_lifecycle import setup, switch
from test_projects_nodes import login


@pytest.fixture(autouse=True)
def storage(tmp_path, monkeypatch):
    folder = tmp_path / 'rag-files'
    folder.mkdir()
    monkeypatch.setenv('PF_ATTACHMENT_ROOT', str(folder))
    monkeypatch.setenv('PF_ATTACHMENT_QUOTA_BYTES', '1000000000')


def upload(client, nid, text='星際驗收密碼是藍鯨七號。', filename='知識.txt'):
    result = client.post(f'/nodes/{nid}/documents', params={'filename': filename}, content=text.encode(),
                        headers={'Content-Type': 'application/octet-stream'})
    assert result.status_code == 201, result.text
    return result.json()['document_id']


def index(client, doc):
    result = client.post(f'/rag/documents/{doc}/index')
    assert result.status_code == 200, result.text
    assert result.json()['state'] == 'ready'
    return result.json()


def ask(client, project, question='星際驗收密碼'):
    result = client.post('/rag/ask', json={'project_id': project, 'question': question})
    assert result.status_code == 200, result.text
    return result.json()


def test_formal_lifecycle_retrieval_versions_feedback_and_privacy(client, engine):
    nid, pid, users = setup(client, engine)
    doc = upload(client, nid)
    status = client.get('/rag/status', params={'project_id': pid})
    assert status.status_code == 200, status.text
    assert status.json()['documents'][0]['state'] == 'queued'
    first = index(client, doc)
    second = index(client, doc)
    assert first == second
    answer = ask(client, pid)
    assert answer['synthetic'] is False and answer['source_mode'] == 'formal'
    assert answer['kind'] == 'retrieval' and '藍鯨七號' in answer['answer'] and answer['warning']
    assert len(answer['sources']) == 1
    source = answer['sources'][0]
    assert source['version'] == 1 and answer['citations'] == [source['source_id']]
    path = f'/rag/queries/{answer["query_id"]}/sources/{source["source_id"]}'
    assert client.get(path).json()['is_current'] is True
    assert client.put(f'/rag/queries/{answer["query_id"]}/feedback', json={'rating': 'helpful'}).json() == {'ok': True}
    assert client.post(f'/documents/{doc}/text', json={'expected_version': 1, 'content': '星際驗收密碼改為白鷺九號。'}).status_code == 201
    assert ask(client, pid)['sources'] == []
    assert client.get(path).json()['is_current'] is False
    index(client, doc)
    latest = ask(client, pid)
    assert '白鷺九號' in latest['answer'] and latest['sources'][0]['version'] == 2
    with Session(engine) as db:
        traces = db.scalars(select(RagQuery)).all()
        assert all('星際' not in str(q.trace) and '藍鯨' not in str(q.trace) for q in traces)
        assert traces[0].rating == 'helpful'
        assert db.scalar(select(RagChunk).where(RagChunk.version == 1)).sha256 == hashlib.sha256('星際驗收密碼是藍鯨七號。'.encode()).hexdigest()
    switch(client, 'yu')
    assert client.get(path).status_code == 404  # Even admin cannot read another user's query context.
    assert client.get('/rag/metrics').json()['query_count'] == 3


def test_permission_filters_before_model_and_revocation_on_source(client, engine, monkeypatch):
    from app.rag import provider
    nid, pid, users = setup(client, engine)
    doc = upload(client, nid)
    index(client, doc)
    answer = ask(client, pid)
    source = answer['sources'][0]
    with Session(engine) as db:
        db.get(Node, nid).owner_user_id = users['yu']
        db.commit()
    def forbidden(*args, **kwargs):
        raise AssertionError('Hidden document must never reach a model')
    monkeypatch.setattr(provider, 'answer', forbidden)
    monkeypatch.setattr(provider, 'embed', forbidden)
    assert ask(client, pid)['sources'] == []
    assert client.get(f'/rag/queries/{answer["query_id"]}/sources/{source["source_id"]}').status_code == 404
    client.post('/auth/logout')
    login(client, 'electronics', 'elaine')
    assert client.post('/rag/ask', json={'project_id': pid, 'question': '星際'}).status_code == 404
    assert client.post(f'/rag/documents/{doc}/index').status_code == 404


def test_disabled_unknown_readonly_and_index_failure_keep_original(client, engine):
    nid, pid, _ = setup(client, engine)
    doc = upload(client, nid)
    index(client, doc)
    assert ask(client, pid, 'unrelatedxyz')['kind'] == 'no_sources'
    assert client.put(f'/rag/documents/{doc}/enabled', json={'enabled': False}).status_code == 200
    assert ask(client, pid)['sources'] == []
    assert client.post(f'/rag/documents/{doc}/index').status_code == 409
    assert client.put(f'/rag/documents/{doc}/enabled', json={'enabled': True}).status_code == 200
    assert ask(client, pid)['sources']
    broken = upload(client, nid, '%PDF-1.4\nbad', 'bad.pdf')
    assert client.post(f'/rag/documents/{broken}/index').status_code == 422
    assert client.get(f'/documents/{broken}/versions/1/download').content == b'%PDF-1.4\nbad'
    switch(client, 'lin')
    assert client.post(f'/rag/documents/{doc}/index').status_code == 403
    assert client.put(f'/rag/documents/{doc}/enabled', json={'enabled': False}).status_code == 403
    assert client.get('/rag/metrics').status_code == 403


def configure(engine, users):
    from app.models import User
    with Session(engine) as db:
        org = db.get(User, users['yu']).organization_id
        db.add(RagSettings(organization_id=org, enabled=True, base_url='http://127.0.0.1:11434',
                           model='chat-local', embedding_model='embed-local'))
        db.commit()


def test_model_and_embedding_contracts_with_explicit_fake_adapter(client, engine, monkeypatch):
    from app.rag import provider
    nid, pid, users = setup(client, engine)
    configure(engine, users)
    monkeypatch.setattr(provider, 'embed', lambda config, texts: [[1.0, 0.0] for _ in texts])
    doc = upload(client, nid)
    index(client, doc)
    monkeypatch.setattr(provider, 'answer', lambda config, q, sources: {'answer': '依來源為藍鯨七號。', 'citations': [sources[0]['source_id']]})
    answer = ask(client, pid)
    assert answer['engine'] == 'model' and answer['retrieval_mode'] == 'hybrid_rrf_rules'
    monkeypatch.setattr(provider, 'answer', lambda *args: {'answer': '沒有預算限制，隨便花。', 'citations': []})
    refusal = ask(client, pid)
    assert refusal['kind'] == 'insufficient_evidence' and '隨便花' not in refusal['answer']
    def broken(*args):
        raise ValueError('invalid_citations')
    monkeypatch.setattr(provider, 'answer', broken)
    fallback = ask(client, pid)
    assert fallback['engine'] == 'retrieval' and '生成模型' in fallback['warning']
    monkeypatch.setattr(provider, 'embed', broken)
    degraded = ask(client, pid)
    assert degraded['retrieval_mode'] == 'bm25_rules'


def test_version_change_during_parsing_never_publishes_stale_index(client, engine, monkeypatch):
    from app.rag import parsing
    nid, pid, _ = setup(client, engine)
    doc = upload(client, nid)
    original = parsing.parse_file
    def changed(*args):
        assert client.post(f'/documents/{doc}/text', json={'expected_version': 1, 'content': '新版星際密碼'}).status_code == 201
        return original(*args)
    monkeypatch.setattr(parsing, 'parse_file', changed)
    assert client.post(f'/rag/documents/{doc}/index').status_code == 409
    assert ask(client, pid)['sources'] == []
    with Session(engine) as db:
        row = db.get(RagIndex, doc)
        assert row.state == 'queued' and row.version == 2


def test_model_reply_after_revocation_is_not_returned(client, engine, monkeypatch):
    from app.rag import provider
    nid, pid, users = setup(client, engine)
    configure(engine, users)
    monkeypatch.setattr(provider, 'embed', lambda config, texts: [[1.0, 0.0] for _ in texts])
    doc = upload(client, nid)
    index(client, doc)
    def revoke(config, q, sources):
        with Session(engine) as db:
            db.get(Node, nid).owner_user_id = users['yu']
            db.commit()
        return {'answer': 'secret', 'citations': [sources[0]['source_id']]}
    monkeypatch.setattr(provider, 'answer', revoke)
    result = client.post('/rag/ask', json={'project_id': pid, 'question': '星際驗收密碼'})
    assert result.status_code == 404 and 'secret' not in result.text


def test_config_enforces_local_admin_and_private_endpoint(client, engine, monkeypatch):
    setup(client, engine, 'yu')
    payload = dict(enabled=True, base_url='https://example.com', model='local', embedding_model='embed')
    assert client.put('/rag/model', json=payload).status_code == 403
    headers = {'host': 'localhost'}
    assert client.put('/rag/model', json=payload, headers=headers).status_code == 422
    payload['base_url'] = 'http://127.0.0.1:11434'
    assert client.put('/rag/model', json=payload, headers=headers).status_code == 200
    assert client.get('/rag/model', headers=headers).json() == payload
    monkeypatch.setenv('PF_WEB_LAN', 'true')
    assert client.get('/rag/model', headers=headers).status_code == 403

@pytest.mark.parametrize('phase',['embedding','answer'])
@pytest.mark.parametrize('change',['revoke','expire'])
def test_session_revoked_during_model_stops_dispatch_and_return(client,engine,monkeypatch,phase,change):
    from app.rag import provider
    from app.models import SessionToken
    from sqlalchemy import delete
    nid,pid,users=setup(client,engine)
    configure(engine,users)
    monkeypatch.setattr(provider,'embed',lambda c,t:[[1.,0.] for _ in t])
    doc=upload(client,nid);index(client,doc)
    def revoke():
        with Session(engine) as db:
            if change=='revoke':
                db.execute(delete(SessionToken).where(SessionToken.user_id==users['ming']))
            else:
                from datetime import timedelta
                from app.rag.models import now
                from sqlalchemy import update
                db.execute(update(SessionToken).where(SessionToken.user_id==users['ming']).values(expires_at=now()-timedelta(seconds=1)))
            db.commit()
    def embedding(c,t):
        revoke()
        return [[1.,0.] for _ in t]
    def generated(c,q,s):
        if phase=='embedding': pytest.fail('generation dispatched after logout')
        revoke()
        return {'answer':'secret answer','citations':[s[0]['source_id']]}
    if phase=='embedding': monkeypatch.setattr(provider,'embed',embedding)
    monkeypatch.setattr(provider,'answer',generated)
    result=client.post('/rag/ask',json={'project_id':pid,'question':'星際驗收密碼'})
    assert result.status_code==401 and 'secret answer' not in result.text
