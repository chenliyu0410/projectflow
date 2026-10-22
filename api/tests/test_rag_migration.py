from pathlib import Path
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
import app.database


def test_rag_upgrade_preserves_existing_rows_and_refuses_loss(tmp_path, monkeypatch):
    url = f'sqlite:///{tmp_path / "rag-migration.db"}'
    monkeypatch.setenv('DATABASE_URL', url)
    config = Config(str(Path(app.database.__file__).resolve().parents[1] / 'alembic.ini'))
    command.upgrade(config, '20261012_0019')
    engine = create_engine(url)
    with engine.begin() as db:
        db.execute(text("INSERT INTO organizations (id,key,name) VALUES ('keep','keep','Preserved')"))
    command.upgrade(config, 'head')
    assert {'rag_indexes', 'rag_chunks', 'rag_queries', 'rag_settings'} <= set(inspect(engine).get_table_names())
    with engine.begin() as db:
        assert db.scalar(text('SELECT name FROM organizations')) == 'Preserved'
        db.execute(text("INSERT INTO rag_settings VALUES ('keep',0,'','','',1)"))
    with pytest.raises(RuntimeError, match='拒絕有損降級'):
        command.downgrade(config, '20261012_0019')
    with engine.connect() as db:
        assert db.scalar(text('SELECT name FROM organizations')) == 'Preserved'
        assert db.scalar(text('SELECT count(*) FROM rag_settings')) == 1
    engine.dispose()

@pytest.fixture
def rag_migration_url(tmp_path, monkeypatch):
    """Optional disposable PostgreSQL schema; refuses production-looking database names."""
    import os, uuid
    from sqlalchemy.engine import make_url
    base = os.environ.get('PF_RAG_TEST_POSTGRES_URL')
    if not base:
        yield f'sqlite:///{tmp_path / "experience-migration.db"}'
        return
    parsed = make_url(base)
    if parsed.get_backend_name() != 'postgresql' or not (parsed.database or '').startswith('rag_'):
        raise RuntimeError('Use a dedicated rag_* PostgreSQL test database')
    admin = create_engine(base)
    schema = 'rag_test_' + uuid.uuid4().hex
    with admin.begin() as db:
        db.execute(text(f'CREATE SCHEMA {schema}'))
    url = parsed.update_query_dict({'options':f'-csearch_path={schema}'}).render_as_string(hide_password=False)
    try:
        yield url
    finally:
        with admin.begin() as db:
            db.execute(text(f'DROP SCHEMA {schema} CASCADE'))
        admin.dispose()


def test_experience_migration_preserves_query_chunk_version_and_queue(rag_migration_url, monkeypatch):
    from sqlalchemy.orm import Session
    from sqlalchemy import select
    from app.seed import seed_demo_data
    from app.models import User, Project, Document, DocumentVersion
    from app.rag.models import now
    monkeypatch.setenv('DATABASE_URL',rag_migration_url)
    config=Config(str(Path(app.database.__file__).resolve().parents[1]/'alembic.ini'))
    command.upgrade(config,'20261021_0020')
    engine=create_engine(rag_migration_url)
    with Session(engine) as db:
        seed_demo_data(db);db.commit()
        user=db.scalar(select(User).where(User.username=='ming'))
        project=db.scalar(select(Project).where(Project.organization_id==user.organization_id))
        org,uid,pid=user.organization_id,user.id,project.id
        db.add(Document(id='preserved-doc',organization_id=org,project_id=pid,current_version=1));db.flush()
        db.add(DocumentVersion(id='preserved-version',organization_id=org,document_id='preserved-doc',version=1,filename='proof.txt',storage_key='a'*32,size_bytes=1,sha256='b'*64,created_by=uid,created_at=now(),comment=''))
        db.commit()
    with engine.begin() as db:
        db.execute(text("INSERT INTO rag_indexes(document_id,organization_id,version,enabled,state,chunk_count,updated_at) VALUES('preserved-doc',:org,1,true,'queued',0,:time)"),{'org':org,'time':now()})
        db.execute(text("INSERT INTO rag_queries(id,organization_id,actor_user_id,project_id,source_ids,trace,created_at) VALUES('preserved-query',:org,:uid,:pid,'[]','{}',:time)"),{'org':org,'uid':uid,'pid':pid,'time':now()})
        db.execute(text("INSERT INTO rag_chunks(id,organization_id,document_id,version,generation,sha256,parent_id,text,parent_text,locator) VALUES('preserved-chunk',:org,'preserved-doc',1,'g',:hash,'parent','original','original','{}')"),{'org':org,'hash':'b'*64})
    def snapshot():
        with engine.connect() as db:
            return {name:[dict(r) for r in db.execute(text('SELECT * FROM '+name)).mappings()] for name in ('documents','document_versions','rag_chunks','rag_queries')}
    before=snapshot()
    command.upgrade(config,'head')
    assert snapshot()==before
    with engine.begin() as db:
        row=db.execute(text('SELECT requested_at,requested_by_user_id,attempts,next_attempt_at FROM rag_indexes')).one()
        assert tuple(row)==(None,None,0,None)
        db.execute(text("UPDATE rag_queries SET project_id=NULL WHERE id='preserved-query'"))
    with pytest.raises(RuntimeError,match='lossy downgrade'):
        command.downgrade(config,'20261021_0020')
    fks = inspect(engine).get_foreign_keys('rag_indexes')
    assert any(fk['constrained_columns']==['organization_id','requested_by_user_id'] for fk in fks)
    if engine.dialect.name == 'postgresql':
        from sqlalchemy.exc import IntegrityError
        with engine.connect() as db:
            outsider=db.scalar(text('SELECT id FROM users WHERE organization_id <> :org LIMIT 1'),{'org':org})
        assert outsider
        with pytest.raises(IntegrityError):
            with engine.begin() as db:
                db.execute(text('UPDATE rag_indexes SET requested_by_user_id=:uid'),{'uid':outsider})
    engine.dispose()
