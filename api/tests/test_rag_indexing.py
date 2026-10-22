import pytest
from datetime import timedelta
from sqlalchemy.orm import Session
from app.rag.models import RagIndex, RagSettings, now
from app.rag import indexing, provider
from test_rag_api import storage, upload, index, ask
from test_report_lifecycle import setup
from app.models import Node


def test_auto_index_durable_and_disabled_revision(client, engine):
    nid,pid,_=setup(client,engine)
    doc=upload(client,nid)
    with Session(engine) as db:
        row=db.get(RagIndex,doc)
        assert row.requested_at and row.requested_by_user_id and row.attempts == 0
    assert indexing.run_once(engine)
    assert ask(client,pid)['sources']
    assert not indexing.run_once(engine)
    client.put(f'/rag/documents/{doc}/enabled',json={'enabled':False})
    assert client.post(f'/documents/{doc}/text',json={'expected_version':1,'content':'新版內容'}).status_code == 201
    assert not indexing.run_once(engine)
    with Session(engine) as db:
        assert db.get(RagIndex,doc).enabled is False
    client.put(f'/rag/documents/{doc}/enabled',json={'enabled':True})
    assert indexing.run_once(engine)
    with Session(engine) as db:
        assert db.get(RagIndex,doc).indexed_version == 2


def test_worker_rechecks_acl_without_model_call(client,engine,monkeypatch):
    nid,pid,users=setup(client,engine)
    doc=upload(client,nid)
    with Session(engine) as db:
        db.get(Node,nid).owner_user_id=users['yu']
        db.commit()
    monkeypatch.setattr(provider,'embed',lambda *args:pytest.fail('unauthorized model call'))
    assert indexing.run_once(engine)
    with Session(engine) as db:
        row=db.get(RagIndex,doc)
        assert row.error_code == 'access_changed' and row.requested_at is None


def test_embedding_retry_is_bounded_and_keeps_keyword_ready(client,engine,monkeypatch):
    nid,pid,_=setup(client,engine)
    doc=upload(client,nid)
    with Session(engine) as db:
        row=db.get(RagIndex,doc)
        db.add(RagSettings(organization_id=row.organization_id,enabled=True,base_url='http://127.0.0.1:11434',model='fake',embedding_model='fake'))
        db.commit()
    calls=[]
    def broken(*args):
        calls.append(1)
        raise ValueError('transport')
    monkeypatch.setattr(provider,'embed',broken)
    for attempt in range(1,4):
        assert indexing.run_once(engine)
        with Session(engine) as db:
            row=db.get(RagIndex,doc)
            assert row.attempts == attempt and row.state == 'ready' and row.error_code == 'embedding_unavailable'
            if attempt < 3:
                assert row.next_attempt_at is not None
                row.next_attempt_at=now()-timedelta(seconds=1)
                db.commit()
    assert len(calls)==3 and not indexing.run_once(engine)
    assert client.get(f'/documents/{doc}/versions/1/download').status_code == 200


def test_historical_queue_not_automatically_consumed(client,engine):
    nid,_,_=setup(client,engine)
    doc=upload(client,nid)
    with Session(engine) as db:
        row=db.get(RagIndex,doc)
        row.requested_at=None
        db.commit()
    assert not indexing.run_once(engine)

@pytest.fixture
def engine(tmp_path,monkeypatch,rag_migration_url):
    # The same worker suite can exercise real PostgreSQL by opting into a fresh schema.
    from sqlalchemy import create_engine
    from app.database import Base
    engine=create_engine(rag_migration_url)
    monkeypatch.setenv('DATABASE_URL',rag_migration_url)
    monkeypatch.setenv('PF_RAG_AUTO_INDEX','false')
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        engine.dispose()


from test_rag_migration import rag_migration_url


def test_two_workers_only_one_claim_and_publication(client,engine,monkeypatch):
    import threading
    from concurrent.futures import ThreadPoolExecutor
    from app.rag import parsing
    nid,_,_=setup(client,engine)
    doc=upload(client,nid)
    started,release=threading.Event(),threading.Event()
    original=parsing.parse_file
    calls=[]
    def held(*args):
        calls.append(1);started.set()
        assert release.wait(10)
        return original(*args)
    monkeypatch.setattr(parsing,'parse_file',held)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first=pool.submit(indexing.run_once,engine)
        assert started.wait(10)
        second=pool.submit(indexing.run_once,engine)
        assert second.result(timeout=10) is False
        release.set()
        assert first.result(timeout=10)
    assert len(calls)==1
    with Session(engine) as db:
        row=db.get(RagIndex,doc)
        assert row.state=='ready' and row.attempts==1 and row.claim is None


def test_worker_old_version_cannot_overwrite_new_request(client,engine,monkeypatch):
    from app.rag import parsing
    nid,_,_=setup(client,engine)
    doc=upload(client,nid)
    original=parsing.parse_file
    def replace(*args):
        assert client.post(f'/documents/{doc}/text',json={'expected_version':1,'content':'新版本證據'}).status_code==201
        return original(*args)
    monkeypatch.setattr(parsing,'parse_file',replace)
    assert indexing.run_once(engine)
    with Session(engine) as db:
        row=db.get(RagIndex,doc)
        assert row.version==2 and row.state=='queued' and row.requested_at and row.attempts==0
    monkeypatch.setattr(parsing,'parse_file',original)
    assert indexing.run_once(engine)
    with Session(engine) as db:
        assert db.get(RagIndex,doc).indexed_version==2


def test_pg_revision_can_commit_while_embedding_transport_is_waiting(client,engine,monkeypatch):
    if engine.dialect.name!='postgresql': pytest.skip('PostgreSQL row-lock concurrency')
    import threading
    from concurrent.futures import ThreadPoolExecutor, TimeoutError
    nid,_,_=setup(client,engine);doc=upload(client,nid)
    with Session(engine) as db:
        org=db.get(RagIndex,doc).organization_id
        db.add(RagSettings(organization_id=org,enabled=True,base_url='http://127.0.0.1:11434',model='',embedding_model='fake'));db.commit()
    transport_started,release=threading.Event(),threading.Event()
    def held(config,texts):
        config['_authorize']()
        transport_started.set()
        assert release.wait(10)
        return [[1.,0.] for _ in texts]
    monkeypatch.setattr(provider,'embed',held)
    with ThreadPoolExecutor(max_workers=2) as pool:
        indexing_job=pool.submit(indexing.run_once,engine)
        assert transport_started.wait(10)
        revision=pool.submit(client.post,f'/documents/{doc}/text',json={'expected_version':1,'content':'傳輸期間提交新版'})
        timely=True
        try:
            response=revision.result(timeout=2)
        except TimeoutError:
            timely=False
        finally:
            release.set()
        indexing_job.result(timeout=10)
        response=revision.result(timeout=10)
    assert timely,'Model transport held a project/node row lock and blocked document revision'
    assert response.status_code==201,response.text
    with Session(engine) as db:
        row=db.get(RagIndex,doc)
        assert row.version==2 and row.state=='queued' and row.claim is None


def test_pg_publication_and_revision_use_same_lock_order(client,engine,monkeypatch):
    if engine.dialect.name!='postgresql': pytest.skip('PostgreSQL row-lock concurrency')
    import threading
    from concurrent.futures import ThreadPoolExecutor
    from sqlalchemy import event
    from app.rag import parsing
    from app.services import document_store
    nid,_,_=setup(client,engine);doc=upload(client,nid)
    parsing_started,writer_locked,publisher_at_permission=threading.Event(),threading.Event(),threading.Event()
    worker_id=[];write_calls=[];database_errors=[]
    original_parse,original_get=parsing.parse_file,document_store.get_document
    def parse(*args):
        worker_id.append(threading.get_ident());parsing_started.set()
        assert writer_locked.wait(10)
        return original_parse(*args)
    def get_document(db,current,document_id,write=False):
        if write and worker_id:
            if threading.get_ident()==worker_id[0]:
                publisher_at_permission.set()
            else:
                write_calls.append(1)
                # Route authorization, save preflight, then save's commit authorization.
                # The third call happens after receiving bytes, while
                # holding the same Project/Node locks needed by publication.
                if len(write_calls)==3:
                    writer_locked.set()
                    assert publisher_at_permission.wait(10)
        return original_get(db,current,document_id,write)
    def sql_error(context): database_errors.append(str(context.original_exception))
    event.listen(engine,'handle_error',sql_error)
    monkeypatch.setattr(parsing,'parse_file',parse)
    monkeypatch.setattr(document_store,'get_document',get_document)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            publication=pool.submit(indexing.run_once,engine)
            assert parsing_started.wait(10)
            revision=pool.submit(client.post,f'/documents/{doc}/text',json={'expected_version':1,'content':'鎖順序新版'})
            response=revision.result(timeout=15)
            publication.result(timeout=15)
        assert response.status_code==201,response.text
        assert database_errors==[],database_errors
        with Session(engine) as db:
            row=db.get(RagIndex,doc)
            assert row.version==2 and row.state=='queued' and row.claim is None
    finally:
        writer_locked.set();publisher_at_permission.set()
        event.remove(engine,'handle_error',sql_error)
