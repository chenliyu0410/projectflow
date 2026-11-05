import hashlib
import json
from pathlib import Path
import sqlite3
from contextlib import closing

import pytest
from app.ai import store, model, service


@pytest.fixture(scope='module')
def pack(tmp_path_factory):
    p=tmp_path_factory.mktemp('ai-pack')
    db=sqlite3.connect(p/'projectflow_demo.sqlite')
    db.executescript((Path(__file__).parent/'fixtures/ai_schema.sql').read_text(encoding='utf-8'))
    docs=[]
    for cid in sorted(store.COMPANIES):
        db.execute('INSERT INTO companies VALUES (?,?,?)',(cid,cid,'synthetic'))
        db.execute('INSERT INTO people VALUES (?,?,?,?)',(cid,'p1','窗口','研發'))
        db.execute('INSERT INTO suppliers VALUES (?,?,?,?)',(cid,'s1','協力商','測試'))
        for i in (1,2):
            pid=f'{cid}-P{i}'
            db.execute('INSERT INTO projects VALUES (?,?,?,?,?)',(cid,pid,'測試專案','p1',100))
            db.execute('INSERT INTO tasks VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(cid,f'{pid}-T1',pid,'p1','測試任務','研發','doing','2026-10-01','2026-10-09',None,8,10))
            db.execute('INSERT INTO tasks VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(cid,f'{pid}-T2',pid,'p1','完成任務','研發','done','2026-10-01','2026-10-08','2026-10-09',8,10))
            db.execute('INSERT INTO expenses VALUES (?,?,?,?,?,?)',(cid,f'{pid}-E1',pid,'測試','2026-10-01',120*i))
            db.execute('INSERT INTO purchase_orders VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(cid,f'{pid}-PO1',pid,'s1','測試',2,10,20,'2026-09-01','2026-10-09',None,'pending'))
            db.execute('INSERT INTO quality_checks VALUES (?,?,?,?,?,?,?)',(cid,f'{pid}-Q1',pid,'2026-10-08',30,2,'test'))
            db.execute('INSERT INTO risks VALUES (?,?,?,?,?,?,?,?,?,?)',(cid,f'{pid}-R1',pid,'high','open','交期延遲','驗收延期','追蹤交期','p1','2026-10-14'))
        for suffix,roles,current,body,pid in [('current',['admin','project_owner','member'],True,'交付規範需要截圖4張',f'{cid}-P1'),('old',['admin','member'],False,'交付規範需要截圖2張',f'{cid}-P1'),('cost',['admin','project_owner'],True,'成本超支機密金額',f'{cid}-P1'),('other',['admin','member'],True,'另一專案交付截圖9張',f'{cid}-P2')]:
            docs.append(dict(document_id=f'{cid}-{suffix}',company_id=cid,project_id=pid,title='測試文件',document_type='report',is_current=current,allowed_roles=roles,text=body,version=2 if current else 1))
    db.commit(); db.close()
    (p/'rag').mkdir(); (p/'evaluation').mkdir()
    (p/'rag/documents.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in docs),encoding='utf-8')
    (p/'evaluation/sql_questions.jsonl').write_text(''.join(json.dumps(dict(company_id='food',sql=q['sql']))+'\n' for q in store.catalog()),encoding='utf-8')
    m=dict(counts={'counts':{'projects':12}},files={str(f.relative_to(p)).replace('\\','/'):hashlib.sha256(f.read_bytes()).hexdigest() for f in p.rglob('*') if f.is_file()})
    (p/'manifest.json').write_text(json.dumps(m),encoding='utf-8')
    return p


@pytest.fixture()
def installed(pack,tmp_path,monkeypatch):
    monkeypatch.setenv('PF_AI_ROOT',str(tmp_path/'ai'))
    store.import_pack(pack,store.root())
    return store.root()


def login(client,who='yu'):
    client.base_url='http://127.0.0.1'
    assert client.post('/auth/login',json={'organization_key':'food','username':who,'password':'demo-'+who}).status_code==200


def test_import_is_atomic_idempotent_and_physically_company_scoped(pack,installed):
    before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (installed/'dataset-v1').glob('*.sqlite')}
    assert store.import_pack(pack,installed)['already_imported']
    assert before=={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (installed/'dataset-v1').glob('*.sqlite')}
    for cid in store.COMPANIES:
        with closing(store.connect(cid)) as db:
            assert {r[0] for r in db.execute('SELECT DISTINCT company_id FROM tasks')}=={cid}
            with pytest.raises(sqlite3.OperationalError): db.execute('DELETE FROM tasks')
    with pytest.raises(FileNotFoundError): store.connect('../food')


def test_corrupt_import_does_not_publish(pack,tmp_path):
    import shutil
    copied=tmp_path/'broken'; shutil.copytree(pack,copied)
    (copied/'rag/documents.jsonl').write_text('bad',encoding='utf-8')
    with pytest.raises(ValueError): store.import_pack(copied,tmp_path/'out')
    assert not (tmp_path/'out/dataset-v1').exists()


def test_api_session_company_project_and_role_filters(client,installed):
    assert client.get('/ai/status').status_code==401
    login(client)
    status=client.get('/ai/status').json()
    assert status['ready'] and status['counts']['projects']==2 and len(status['queries'])==16
    assert not status['model_enabled']
    r=client.post('/ai/ask',json={'question':'交付截圖','project_id':'food-P1'}).json()
    assert r['kind']=='retrieval'
    assert {x['document_id'] for x in r['sources']}=={'food-current'}
    assert client.get('/ai/documents/electronics-current').status_code==404
    assert client.post('/ai/ask',json={'question':'交付','project_id':'electronics-P1'}).status_code==404
    assert client.post('/ai/ask',json={'question':'逾期','mode':'sql','company_id':'electronics'}).status_code==422
    login(client,'ming')
    assert client.get('/ai/documents/food-cost').status_code==404
    assert not client.post('/ai/ask',json={'question':'成本超支機密'}).json()['sources']
    assert client.post('/ai/ask',json={'question':'逾期','mode':'sql'}).status_code==403
    assert client.put('/ai/model',json={'enabled':False}).status_code==403


def test_four_out_of_four_cross_boundary_scenarios_are_refused(client,installed):
    # 簡報第 6 頁「4/4 越權情境」逐條列出；只整理既有行為，所以這個測試一寫好就會通過。
    login(client)
    results={
        '看不到別家公司的文件':client.get('/ai/documents/electronics-current').status_code,
        '不能指定別家公司的專案':client.post('/ai/ask',json={'question':'交付','project_id':'electronics-P1'}).status_code,
        '不能用 company_id 參數換公司':client.post('/ai/ask',json={'question':'逾期','mode':'sql','company_id':'electronics'}).status_code,
    }
    login(client,'ming')
    results['角色不足不能做資料分析']=client.post('/ai/ask',json={'question':'逾期','mode':'sql'}).status_code
    assert results=={'看不到別家公司的文件':404,'不能指定別家公司的專案':404,'不能用 company_id 參數換公司':422,'角色不足不能做資料分析':403}


def test_all_controlled_queries_and_project_filter(installed):
    with closing(store.connect('food')) as db:
        for q in store.catalog():
            for project in (None,'food-P1'):
                result=store.execute_query(db,q['query_id'],'food',project)
                assert 'sql' in result
        result=store.execute_query(db,'q02','food','food-P1')
        assert result['rows']==[{'department':'研發','overdue_count':1}]
        result=store.execute_query(db,'q04','food','food-P1')
        assert result['rows'][0]['overrun_twd']==20
        with pytest.raises(ValueError): store.execute_query(db,'DELETE FROM tasks','food')


def test_unknown_question_and_unsupported_dates_are_not_guessed(client,installed):
    login(client)
    # TEXT2SQL-FALLBACK: none of these runs; dropped conditions are named instead of silently ignored.
    expected={'明天天氣':('help',[]),'上週逾期任務':('fallback',['time']),'DELETE FROM tasks; 逾期':('unsupported',[]),'已結案的高風險清單':('fallback',['status']),
              '2026年9月逾期任務':('fallback',['time']),'已完成任務逾期數':('fallback',['status']),'林承岳的各部門逾期未完成數':('fallback',[])}
    for q,(kind,conditions) in expected.items():
        r=client.post('/ai/ask',json={'question':q,'mode':'sql'}).json()
        assert r['kind']==kind and r['analysis'] is None and r['fallback']['conditions']==conditions
    assert client.post('/ai/ask',json={'question':'火星殖民旅行'}).json()['kind']=='no_sources'


def test_model_config_and_unsafe_endpoints(client,installed):
    login(client)
    for url in ['http://8.8.8.8:11434','http://169.254.169.254','file:///etc/passwd','http://user:pass@192.168.1.2','http://example.com','http://192.168.1.2/path','http://192.168.1.2?x=1']:
        assert client.put('/ai/model',json={'enabled':True,'base_url':url,'model':'local'}).status_code==422
    config={'enabled':True,'base_url':'http://192.168.1.2:11434','model':'local'}
    assert client.put('/ai/model',json=config,headers={'Origin':'http://evil.example'}).status_code==403
    assert client.put('/ai/model',json=config).status_code==200
    assert client.get('/ai/model').json()==config
    assert model.settings('electronics')['enabled'] is False


def test_model_context_is_scoped_and_invalid_citations_fall_back(client,installed,monkeypatch):
    login(client)
    model.save('food',dict(enabled=True,base_url='http://127.0.0.1:11434',model='test'))
    def fake(config,system,prompt,schema):
        context=json.loads(prompt)
        assert [d['document_id'] for d in context['sources']]==['food-current']
        return {'answerable':True,'answer':'需4張截圖','citations':['food-current']}
    monkeypatch.setattr(model,'chat',fake)
    payload={'question':'交付截圖','project_id':'food-P1'}
    r=client.post('/ai/ask',json=payload).json()
    assert r['kind']=='rag' and r['citations']==['food-current']
    monkeypatch.setattr(model,'chat',lambda *args: {'answerable':True,'answer':'其他公司秘密','citations':['electronics-current']})
    r=client.post('/ai/ask',json=payload).json()
    assert r['kind']=='retrieval' and r['warning'] and '其他公司秘密' not in r['answer']
    monkeypatch.setattr(model,'chat',lambda *args: (_ for _ in ()).throw(TimeoutError()))
    assert client.post('/ai/ask',json=payload).json()['kind']=='retrieval'


def test_model_sql_can_only_choose_catalog_id(installed,monkeypatch):
    model.save('food',dict(enabled=True,base_url='http://127.0.0.1:11434',model='test'))
    monkeypatch.setattr(model,'chat',lambda *args: {'query_id':'DROP TABLE tasks'})
    with closing(store.connect('food')) as db:
        result=service.ask(db,'food','admin','幫我看看各部門的狀況','sql')
        assert result['analysis'] is None and 'DROP' not in json.dumps(result,ensure_ascii=False)
        assert db.execute('SELECT COUNT(*) FROM tasks').fetchone()[0]==4


def test_sql_guidance_points_to_shortcuts_not_removed_menus(installed,monkeypatch):
    # The copilot no longer has an analysis menu; unsupported and failed recognition point to its shortcut questions.
    model.save('food',dict(enabled=True,base_url='http://127.0.0.1:11434',model='test'))
    monkeypatch.setattr(model,'chat',lambda *args: (_ for _ in ()).throw(TimeoutError()))
    with closing(store.connect('food')) as db:
        result=service.ask(db,'food','admin','幫我看看工作狀況','sql')
    for text in [result['answer'],result['warning']]:
        assert '快捷題' in text and '選單' not in text and '分析種類' not in text


def test_natural_language_exact_aliases_and_model_suggestion_need_explicit_choice(installed,monkeypatch):
    for q in store.catalog(): assert service.infer(q['label'])==q['query_id']
    assert service.infer('請問各部門有幾件逾期任務？')=='q02'
    model.save('food',dict(enabled=True,base_url='http://127.0.0.1:11434',model='test'))
    monkeypatch.setattr(model,'chat',lambda *args: {'query_id':'q09'})
    with closing(store.connect('food')) as db:
        r=service.ask(db,'food','admin','已結案的高風險清單','sql')
        assert r['kind']=='fallback' and r['analysis'] is None
        assert r['suggestions'][0]['label']=='尚未結案的高風險清單' and '「已結案」' in r['suggestions'][0]['omits']
        assert '尚未執行' in r['answer']


def test_ollama_http_contract_no_proxy_redirect_and_json_validation(installed,monkeypatch):
    import httpx
    original=httpx.Client
    def transport(request):
        assert str(request.url)=='http://127.0.0.1:11434/api/chat'
        body=json.loads(request.content)
        assert body['stream'] is False and body['format']['type']=='object'
        assert body['messages'][0]['role']=='system'
        return httpx.Response(200,json={'done':True,'done_reason':'stop','message':{'content':json.dumps({'answerable':True,'answer':'4張','citations':['d1']})}})
    def client(**kwargs):
        assert kwargs['trust_env'] is False and kwargs['follow_redirects'] is False
        return original(transport=httpx.MockTransport(transport),**kwargs)
    monkeypatch.setattr(model.httpx,'Client',client)
    assert model.answer({'base_url':'http://127.0.0.1:11434','model':'test'},'截圖',[{'document_id':'d1','body':'4張'}])['answer']=='4張'
    with pytest.raises(ValueError): model.save('food',dict(enabled=True,base_url='http://127.0.0.1:11434',model='example:cloud'))
