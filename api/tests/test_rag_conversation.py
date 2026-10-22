import json
from sqlalchemy.orm import Session
from app.models import Node
from app.rag import provider, service
from app.rag.models import RagSettings
from test_rag_api import storage, upload, index, ask
from test_report_lifecycle import setup


def scoped(client, question='星際驗收密碼', history=None):
    return client.post('/rag/ask',json={'scope':{'kind':'all_visible'},'question':question,'history':history or []})


def test_all_visible_sources_status_and_historical_disabled(client,engine):
    nid,pid,_=setup(client,engine)
    doc=upload(client,nid)
    index(client,doc)
    response=scoped(client)
    assert response.status_code==200,response.text
    result=response.json()
    assert result['project_id'] is None and result['scope']=={'kind':'all_visible'}
    assert result['sources'][0]['project_id']==pid and result['sources'][0]['project_title']
    assert result['coverage']['ready']==1 and result['blocks'][0]['source_ids']==result['citations']
    assert client.get('/rag/status?scope_kind=all_visible').json()['coverage']['ready']==1
    client.put(f'/rag/documents/{doc}/enabled',json={'enabled':False})
    assert scoped(client).json()['sources']==[]
    sid=result['sources'][0]['source_id']; qid=result['query_id']
    assert client.get(f'/rag/queries/{qid}/sources/{sid}').status_code==200
    assert client.post('/rag/queries/revalidate',json={'query_ids':[qid]}).json()['queries'][0]['status']=='visible'


def test_revalidate_revocation_and_forged_history(client,engine):
    nid,pid,users=setup(client,engine)
    doc=upload(client,nid);index(client,doc)
    result=scoped(client).json()
    with Session(engine) as db:
        db.get(Node,nid).owner_user_id=users['yu'];db.commit()
    assert client.post('/rag/queries/revalidate',json={'query_ids':[result['query_id'],'fake']}).json()=={'queries':[{'query_id':result['query_id'],'status':'unavailable'},{'query_id':'fake','status':'unavailable'}]}
    follow=scoped(client,'誰負責簽核？',[{'question':'G2條件','query_id':result['query_id']}]).json()
    assert follow['code']=='access_changed' and follow['sources']==[]


def test_followup_rewrite_and_clarify(client,engine,monkeypatch):
    nid,pid,_=setup(client,engine)
    doc=upload(client,nid,'G2階段由李經理簽核。');index(client,doc)
    original=scoped(client,'G2階段').json()
    assert scoped(client,'誰負責簽核？',[{'question':'G2階段','query_id':original['query_id']}]).json()['code']=='clarification_required'
    with Session(engine) as db:
        from app.rag.models import RagIndex
        org=db.get(RagIndex,doc).organization_id
        db.add(RagSettings(organization_id=org,enabled=True,base_url='http://127.0.0.1:11434',model='fake',embedding_model=''));db.commit()
    def rewrite(config,path,payload):
        assert payload['options']['num_ctx']==16384
        content=json.loads(payload['messages'][1]['content'])
        assert content['history']==['G2階段'] and 'answer' not in content
        return {'message':{'content':json.dumps({'standalone_question':'G2階段誰簽核','needs_clarification':False,'clarification_question':''})}}
    monkeypatch.setattr(provider,'_request',rewrite)
    monkeypatch.setattr(provider,'answer',lambda c,q,s:{'answer':q,'citations':[s[0]['source_id']],'blocks':[{'text':q,'source_ids':[s[0]['source_id']]}]})
    result=scoped(client,'誰負責簽核？',[{'question':'G2階段','query_id':original['query_id']}]).json()
    assert result['kind']=='rag' and 'G2' in result['answer']


def test_scope_limit_safe_result(client,engine,monkeypatch):
    nid,pid,_=setup(client,engine);doc=upload(client,nid);index(client,doc)
    monkeypatch.setattr(service,'MAX_CANDIDATES',0)
    result=scoped(client).json()
    assert result['code']=='scope_limit' and result['sources']==[]

def test_cross_project_global_sources_do_not_include_hidden_nodes(client,engine,monkeypatch):
    from app.models import Project, User
    from sqlalchemy import select
    nid,pid,users=setup(client,engine)
    doc=upload(client,nid,'星際驗收密碼是藍鯨七號。');index(client,doc)
    with Session(engine) as db:
        org=db.get(User,users['ming']).organization_id
        other=Project(organization_id=org,title='另一專案',owner_user_id=users['ming'])
        db.add(other);db.commit();other_id=other.id
    response=client.post(f'/projects/{other_id}/documents',params={'filename':'知識.txt'},content='星際驗收密碼是白鷺九號。'.encode(),headers={'Content-Type':'application/octet-stream'})
    assert response.status_code==201,response.text
    other_doc=response.json()['document_id'];index(client,other_doc)
    result=scoped(client).json()
    assert {s['project_id'] for s in result['sources']}=={pid,other_id}
    # A pending third document causes partial coverage, without stale evidence reuse.
    upload(client,nid,'星際驗收尚在準備。','pending.txt')
    assert scoped(client).json()['coverage']['partial'] is True
    with Session(engine) as db:
        db.get(Node,nid).owner_user_id=users['yu'];db.commit()
    result=scoped(client).json()
    assert {s['project_id'] for s in result['sources']}=={other_id}
    assert result['coverage']['ready']==1 and result['coverage']['queued']==0
    assert '藍鯨' not in str(result)


def test_history_new_version_retrieves_current_and_scope_change_rejected(client,engine):
    nid,pid,_=setup(client,engine)
    doc=upload(client,nid);index(client,doc)
    original=scoped(client).json()
    assert client.post(f'/documents/{doc}/text',json={'expected_version':1,'content':'星際驗收密碼是新版。'}).status_code==201
    index(client,doc)
    check=client.post('/rag/queries/revalidate',json={'query_ids':[original['query_id']]}).json()
    assert check['queries'][0]['status']=='source_changed'
    result=scoped(client,'星際驗收密碼',[{'question':'舊題','query_id':original['query_id']}]).json()
    assert result['sources'][0]['version']==2
    switched=client.post('/rag/ask',json={'scope':{'kind':'project','project_id':pid},'question':'星際驗收密碼','history':[{'question':'舊題','query_id':original['query_id']}]}).json()
    assert switched['code']=='access_changed' and switched['sources']==[]


def test_complete_question_is_not_a_followup_and_short_ellipsis_clarifies(client,engine):
    setup(client,engine)
    complete='R-01 是已確認延遲嗎？誰追蹤，修訂時程由誰核准？'
    assert scoped(client,complete).json()['code']!='clarification_required'
    assert scoped(client,'誰負責簽核？').json()['code']=='clarification_required'


def test_history_reauthorized_after_rewrite(client,engine,monkeypatch):
    from app.rag.models import RagIndex
    nid,_,users=setup(client,engine)
    doc=upload(client,nid);index(client,doc)
    original=scoped(client).json()
    with Session(engine) as db:
        org=db.get(RagIndex,doc).organization_id
        db.add(RagSettings(organization_id=org,enabled=True,base_url='http://127.0.0.1:11434',model='fake',embedding_model=''));db.commit()
    def rewrite(*args):
        with Session(engine) as db:
            db.get(Node,nid).owner_user_id=users['yu'];db.commit()
        return {'message':{'content':json.dumps({'standalone_question':'secret reformulated context','needs_clarification':False,'clarification_question':''})}}
    monkeypatch.setattr(provider,'_request',rewrite)
    def forbidden(*args): raise AssertionError('stale history reached retrieval')
    monkeypatch.setattr(service,'candidates',forbidden)
    result=scoped(client,'誰負責簽核？',[{'question':'星際驗收','query_id':original['query_id']}]).json()
    assert result['code']=='access_changed' and result['sources']==[]


import pytest
@pytest.mark.parametrize('previous,clarify,standalone',[
    ('G2 要具備什麼才能通過？',False,'G2 需要誰簽核？'),
    ('K7 要具備什麼才能通過？',False,'K7 需要誰簽核？'),
    ('G2 與 M04 各要具備什麼才能通過？',True,''),
])
def test_followup_reference_context_is_latest_user_subject_not_source_titles(client,engine,monkeypatch,previous,clarify,standalone):
    from app.rag.models import RagIndex
    nid,_,users=setup(client,engine)
    doc=upload(client,nid);index(client,doc)
    original=scoped(client,previous).json()
    with Session(engine) as db:
        org=db.get(RagIndex,doc).organization_id
        db.add(RagSettings(organization_id=org,enabled=True,base_url='http://127.0.0.1:11434',model='fake',embedding_model=''));db.commit()
    requests=[]
    def rewrite(config,path,payload):
        body=json.loads(payload['messages'][1]['content'])
        # The most recent user question is the referent; the document list is not
        # a competing list of subjects. Live tests separately check model behavior.
        assert body['reference_question']==previous
        assert body['history']==[previous]
        assert body['question']=='那需要誰簽核？'
        assert '來源標題不是對話中的候選對象' in payload['messages'][0]['content']
        requests.append(body)
        return {'message':{'content':json.dumps({'standalone_question':standalone,'needs_clarification':clarify,'clarification_question':'請指定階段' if clarify else ''})}}
    monkeypatch.setattr(provider,'_request',rewrite)
    monkeypatch.setattr(provider,'answer',lambda c,q,s:{'answer':q,'citations':[s[0]['source_id']],'blocks':[{'text':q,'source_ids':[s[0]['source_id']]}]})
    # Inspect the resolved query even when a synthetic source has no lexical match.
    queries=[]
    original_rank=service.retrieval.rank
    def rank(question,*args,**kwargs):
        queries.append(question)
        return original_rank(question,*args,**kwargs)
    monkeypatch.setattr(service.retrieval,'rank',rank)
    result=scoped(client,'那需要誰簽核？',[{'question':previous,'query_id':original['query_id']}]).json()
    assert len(requests)==(0 if clarify else 1)
    if clarify:
        assert result['code']=='clarification_required' and result['sources']==[]
    else:
        assert standalone in queries[0]
        assert result['code']!='clarification_required'


@pytest.mark.parametrize('previous,question,ambiguous',[
    ('G2 與包裝版面核准，各需要什麼條件？','那需要誰簽核？',True),
    ('K7 和 Z9 分別需要什麼條件？','誰負責簽核？',True),
    ('設計評審與設備放行，各需要什麼條件？','那需要誰簽核？',True),
    ('G2 需要供應商聲明與檢驗報告才能通過嗎？','那需要誰簽核？',False),
    ('K7 要具備什麼才能通過？','那需要誰簽核？',False),
    ('G2 與包裝版面核准，各需要什麼條件？','G2 需要誰簽核？',False),
    ('K7 和 Z9 分別需要什麼條件？','兩者各自需要誰簽核？',False),
])
def test_server_enforces_parallel_subject_ambiguity_without_treating_document_list_as_subjects(monkeypatch,previous,question,ambiguous):
    import time
    from app.rag import conversation,governance
    monkeypatch.setattr(conversation,'validate_history',lambda *args:['規則','角色表','里程碑'])
    monkeypatch.setattr(governance,'session_access',lambda *args:None)
    calls=[]
    def overconfident(*args):
        calls.append(1)
        # A model that combines two subjects into an answer must not bypass
        # the server's required clarification for an unresolved single referent.
        return {'message':{'content':json.dumps({'standalone_question':'resolved question','needs_clarification':False,'clarification_question':''})}}
    monkeypatch.setattr(provider,'_request',overconfident)
    query,clarification=conversation.resolve(None,None,{'kind':'all_visible'},question,[{'question':previous}],{'enabled':True,'model':'fake'},time.monotonic()+170)
    if ambiguous:
        assert query is None and clarification and calls==[]
    else:
        assert clarification is None and query


@pytest.mark.parametrize('previous,ambiguous',[
    ('G2與包裝版面核准，各由誰負責？',True),
    ('G2由誰負責？',False),
])
def test_parallel_short_responsibility_subject_guard(previous,ambiguous):
    from app.rag.conversation import unresolved_parallel_subjects
    assert unresolved_parallel_subjects('那需要誰簽核？',[{'question':previous}]) is ambiguous
