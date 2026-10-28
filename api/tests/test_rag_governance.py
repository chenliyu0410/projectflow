import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.auth import CurrentUser
from app.models import User, Organization, Document, Node
from app.rag.governance import authorized_documents, recheck, trace_summary
from test_report_lifecycle import setup
from test_documents import upload, files


def current(db, name):
    user = db.scalar(select(User).where(User.username == name))
    return CurrentUser(user, db.get(Organization, user.organization_id), '')


def test_permission_filter_root_company_and_live_revocation(client, engine):
    nid, pid, users = setup(client, engine)
    did = upload(client, nid).json()['document_id']
    with Session(engine) as db:
        org = db.get(Node, nid).organization_id
        db.add(Document(id='root-doc', organization_id=org, project_id=pid, node_id=None, current_version=1))
        db.commit()
        actor = current(db, 'ming')
        assert {d.id for d in authorized_documents(db, actor, pid)} == {did, 'root-doc'}
        assert recheck(db, actor, did, 1).version == 1
        with Session(engine) as other:
            other.get(Node, nid).owner_user_id = users['yu']
            other.commit()
        assert {d.id for d in authorized_documents(db, actor, pid)} == {'root-doc'}
        with pytest.raises(HTTPException) as denied:
            recheck(db, actor, did, 1)
        assert denied.value.status_code == 404
        with pytest.raises(HTTPException):
            authorized_documents(db, current(db, 'elaine'), pid)
        with pytest.raises(HTTPException):
            authorized_documents(db, actor, 'missing')


def test_current_version_checked(client, engine):
    nid, _, _ = setup(client, engine)
    did = upload(client, nid).json()['document_id']
    with Session(engine) as db:
        actor = current(db, 'ming')
        db.get(Document, did).current_version = 2
        db.commit()
        with pytest.raises(HTTPException) as stale:
            recheck(db, actor, did, 1)
        assert stale.value.status_code == 409
        assert recheck(db, actor, did, 1, require_current=False).version == 1


def test_trace_strict_whitelist_and_types():
    assert trace_summary(question='secret', answer='secret', content='secret', token='secret', base_url='x', exception='x') == {}
    assert trace_summary(query_id='abc', duration_ms=1.2, chunk_count=2, version=1, model='llama:3') == dict(query_id='abc', duration_ms=1.2, chunk_count=2, version=1, model='llama:3')
    assert trace_summary(query_id='x'*129, duration_ms=float('nan'), chunk_count=True, version=-1, model={'token':'x'}, error_code='secret\ntext', embedding_model='http://private:11434') == {}


def test_trace_service_versions_and_nullable_usage():
    values = dict(stage='query', outcome='degraded', pipeline_version='formal-rag-v1', prompt_version='evidence-v1', input_tokens=None, output_tokens=4, cost=None)
    assert trace_summary(**values) == values
    assert trace_summary(input_tokens='secret', output_tokens=True, cost=float('inf')) == {}
    assert trace_summary(input_tokens=-1, output_tokens=1_000_000_001, cost=-0.1) == {}
    assert trace_summary(input_tokens=3, output_tokens=5, cost=0.01) == dict(input_tokens=3, output_tokens=5, cost=0.01)
