from pathlib import Path

from app.database import sqlalchemy_url


def test_operations_migration_preserves_data_and_refuses_loss(tmp_path, monkeypatch):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, text
    import pytest
    url = f'sqlite:///{tmp_path / "operations.db"}'
    monkeypatch.setenv('DATABASE_URL', url)
    config = Config('api/alembic.ini')
    command.upgrade(config, '20261011_0012')
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO organizations (id,key,name) VALUES ('keep','keep','Keep data')"))
    command.upgrade(config, 'head')
    with engine.begin() as conn:
        assert conn.scalar(text('SELECT name FROM organizations')) == 'Keep data'
        assert conn.scalar(text('SELECT count(*) FROM operations_records')) == 0
        conn.execute(text("INSERT INTO operations_records (id,organization_id,category,code,title,status,visibility,fields,source,revision,created_by,updated_by,created_at,updated_at) VALUES ('a','keep','partners','A','Record','active','internal','[]','native',1,'actor','actor','2026-10-11','2026-10-11')"))
    with pytest.raises(RuntimeError, match='拒絕有損降級'):
        command.downgrade(config, '20261011_0012')
    with engine.connect() as conn:
        assert conn.scalar(text('SELECT count(*) FROM operations_records')) == 1
    engine.dispose()


def test_documents_migration_preserves_existing_data(tmp_path, monkeypatch):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, text, inspect
    url = f'sqlite:///{tmp_path / "documents-migration.db"}'
    monkeypatch.setenv('DATABASE_URL', url)
    config = Config('api/alembic.ini')
    command.upgrade(config, '20261010_0011')
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO organizations (id,key,name) VALUES ('keep','keep','Keep data')"))
    command.upgrade(config, 'head')
    with engine.connect() as conn:
        assert conn.execute(text('SELECT id,key,name FROM organizations')).all() == [('keep', 'keep', 'Keep data')]
        assert conn.scalar(text('SELECT count(*) FROM documents')) == 0
    assert {'documents', 'document_versions'} <= set(inspect(engine).get_table_names())
    command.downgrade(config, '20261010_0011')
    with engine.connect() as conn:
        assert conn.scalar(text('SELECT count(*) FROM organizations')) == 1
    engine.dispose()


def test_sqlalchemy_uses_psycopg_driver_for_postgresql():
    assert sqlalchemy_url("postgresql://user:pass@db:5432/projectflow") == "postgresql+psycopg://user:pass@db:5432/projectflow"
    assert sqlalchemy_url("sqlite:///tmp.db") == "sqlite:///tmp.db"


def test_alembic_config_uses_api_root_and_no_logging_sections_required():
    ini = Path("api/alembic.ini").read_text(encoding="utf-8")
    env = Path("api/alembic/env.py").read_text(encoding="utf-8")
    assert "script_location = %(here)s/alembic" in ini
    assert "prepend_sys_path = %(here)s" in ini
    assert "if config.config_file_name is not None and \"loggers\" in config.file_config" in env


def test_alembic_revision_contains_required_business_tables():
    revision = Path("api/alembic/versions/20261008_0001_p1a_core.py").read_text(encoding="utf-8")
    for table in [
        "organizations", "users", "sessions", "departments", "department_members",
        "projects", "nodes", "workflows", "workflow_nodes", "gates",
        "task_reports", "audit_logs",
    ]:
        assert f'create_table("{table}"' in revision
    assert "organization_id" in revision
    assert "ForeignKeyConstraint([\"organization_id\", \"project_id\"]" in revision
    assert "sa.Column(\"content\", postgresql.JSONB" in revision
    assert "ForeignKeyConstraint([\"organization_id\", \"head_user_id\"]" in revision
    assert "ForeignKeyConstraint([\"organization_id\", \"owner_user_id\"]" in revision
    assert "ForeignKeyConstraint([\"organization_id\", \"parent_template_id\"]" in revision
    assert "ForeignKeyConstraint([\"organization_id\", \"submitted_by\"]" in revision
    assert "ForeignKeyConstraint([\"organization_id\", \"actor_user_id\"]" in revision
    assert "ForeignKeyConstraint([\"organization_id\", \"node_id\"]" in revision


def seed_at_revision(url, revision, prepare):
    """Upgrade to `revision`, then copy rows built with today's ORM, keeping only columns that revision has.

    Historical migration checks cannot use the ORM directly once later stages add columns.
    """
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import MetaData, create_engine, insert, select
    from sqlalchemy.orm import Session
    from sqlalchemy.pool import StaticPool
    from app.database import Base
    import app.models  # noqa: F401  (register every table)
    command.upgrade(Config('api/alembic.ini'), revision)
    scratch = create_engine('sqlite://', poolclass=StaticPool, connect_args={'check_same_thread': False})
    Base.metadata.create_all(scratch)
    with Session(scratch) as db:
        prepare(db)
        db.commit()
    target = create_engine(sqlalchemy_url(url))
    reflected = MetaData()
    reflected.reflect(target)
    with scratch.connect() as source, target.begin() as dest:
        for table in Base.metadata.sorted_tables:
            if table.name not in reflected.tables:
                continue
            existing = reflected.tables[table.name]
            columns = [column for column in table.columns if column.name in existing.c]
            rows = [dict(row._mapping) for row in source.execute(select(*columns))]
            # Self-references (node parents, template parents) must exist before their children.
            self_refs = [fk.parent.name for fk in table.foreign_keys if fk.column.table is table and fk.parent.name != 'organization_id']
            ordered, emitted = [], set()
            while rows:
                ready = [row for row in rows if all(row[ref] is None or row[ref] in emitted for ref in self_refs)] or rows[:1]
                for row in ready:
                    rows.remove(row)
                    ordered.append(row)
                    emitted.add(row.get('id'))
            if ordered:
                dest.execute(insert(existing), ordered)
    scratch.dispose()
    target.dispose()


def check_date_migration_preserves_existing_rows(url, monkeypatch):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, text
    import pytest
    from sqlalchemy.exc import IntegrityError
    monkeypatch.setenv('DATABASE_URL', url)
    config = Config('api/alembic.ini')
    command.upgrade(config, '20261008_0001')
    engine = create_engine(url)
    with engine.begin() as db:
        db.execute(text("INSERT INTO organizations VALUES ('org','org','Original')"))
        db.execute(text("INSERT INTO users VALUES ('user','org','user','User','admin','hash',CURRENT_TIMESTAMP)"))
        db.execute(text("INSERT INTO projects VALUES ('project','org','Original project','user',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"))
        db.execute(text("INSERT INTO nodes VALUES ('root','org','project',NULL,'phase','Original phase','done','user',NULL,10,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"))
        db.execute(text("INSERT INTO nodes VALUES ('child','org','project','root','task','Original task','review','user',NULL,20,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"))
        db.execute(text("INSERT INTO departments VALUES ('dept','org','Original department','user')"))
        db.execute(text("UPDATE nodes SET department_id='dept' WHERE id='child'"))
        db.execute(text("INSERT INTO audit_logs VALUES ('audit','org','user','child','node.create','{}',CURRENT_TIMESTAMP)"))
        tables = ('organizations', 'users', 'projects', 'departments', 'audit_logs')
        preserved = {table: [tuple(row) for row in db.execute(text(f'SELECT * FROM {table} ORDER BY id'))] for table in tables}
        before = [tuple(row) for row in db.execute(text('SELECT * FROM nodes ORDER BY id'))]
    command.upgrade(config, '20261008_0002')
    with engine.begin() as db:
        rows = [tuple(row) for row in db.execute(text('SELECT * FROM nodes ORDER BY id'))]
        assert rows == [row + (None, None) for row in before]
        for table, expected in preserved.items():
            assert [tuple(row) for row in db.execute(text(f'SELECT * FROM {table} ORDER BY id'))] == expected
        db.execute(text("UPDATE nodes SET start_date='2028-02-29',due_date='2028-03-01' WHERE id='child'"))
    with pytest.raises(IntegrityError):
        with engine.begin() as db:
            db.execute(text("UPDATE nodes SET due_date='2028-02-28' WHERE id='child'"))
    with engine.connect() as db:
        assert tuple(str(value) for value in db.execute(text("SELECT start_date,due_date FROM nodes WHERE id='child'")).one()) == ('2028-02-29','2028-03-01')
    engine.dispose()


def test_date_migration_preserves_existing_rows(tmp_path, monkeypatch):
    check_date_migration_preserves_existing_rows(f"sqlite:///{tmp_path / 'migration.db'}", monkeypatch)


def test_postgresql_date_migration_preserves_existing_rows(monkeypatch):
    import os
    import pytest
    from sqlalchemy.engine import make_url
    url = os.environ.get("P2A_MIGRATION_TEST_URL")
    if not url:
        pytest.skip("Set P2A_MIGRATION_TEST_URL to a fresh isolated PostgreSQL test database")
    parsed = make_url(url)
    assert parsed.get_backend_name() == "postgresql"
    assert parsed.database.startswith("p2a_migration_")
    check_date_migration_preserves_existing_rows(sqlalchemy_url(url), monkeypatch)


def test_p2b_schema_models_and_report_constraints(client, engine):
    import pytest
    from datetime import date
    from sqlalchemy import select
    from sqlalchemy.orm import Session
    from sqlalchemy.exc import IntegrityError
    from app import models
    for name in ('NodeCollaborator','TaskNote','Attachment','AttachmentQuota'):
        assert hasattr(models,name), f'Missing model {name}'
    with Session(engine) as db:
        node=db.scalars(select(models.Node).where(models.Node.kind=='task')).first()
        user=db.get(models.User,node.owner_user_id)
        values=dict(organization_id=node.organization_id,node_id=node.id,submitted_by=user.id,
                    result='達成',summary='result',workflow_version=2,version=1,finished_on=date(2026,10,8))
        db.add(models.TaskReport(**values));db.commit()
        assert node.collaborators_revision==0
        for changes in ({'version':2},{'version':0,'status':'approved'},{'version':2,'result':'invalid'}, {'version':2,'finished_on':None}):
            with pytest.raises(IntegrityError):
                db.add(models.TaskReport(**{**values,**changes}));db.commit()
            db.rollback()
        db.add(models.TaskReport(**{**values,'workflow_version':None,'version':None,'finished_on':None,'result':'legacy arbitrary'}));db.commit()


def check_p2b_migration_keeps_historical_reports(url,monkeypatch):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine,text,inspect
    monkeypatch.setenv('DATABASE_URL',url)
    config=Config('api/alembic.ini');command.upgrade(config,'20261008_0002')
    engine=create_engine(url)
    with engine.begin() as db:
        db.execute(text("INSERT INTO organizations VALUES ('org','org','Original')"))
        db.execute(text("INSERT INTO users VALUES ('user','org','user','User','admin','hash',CURRENT_TIMESTAMP)"))
        db.execute(text("INSERT INTO projects VALUES ('project','org','Original project','user',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"))
        db.execute(text("INSERT INTO departments VALUES ('dept','org','Original department','user')"))
        db.execute(text("INSERT INTO nodes VALUES ('phase','org','project',NULL,'phase','Original phase','doing','user','dept',5,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP,'2026-09-01','2026-12-31')"))
        db.execute(text("INSERT INTO nodes VALUES ('task','org','project','phase','task','Original task','done','user','dept',10,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP,'2026-10-01','2026-10-08')"))
        db.execute(text("INSERT INTO nodes VALUES ('review-task','org','project','task','task','Legacy review task','review','user','dept',20,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP,'2026-10-02','2026-10-09')"))
        for node_id in ('task', 'review-task'):
            for i in range(2):
                db.execute(text("INSERT INTO task_reports VALUES (:id,'org',:node,'old arbitrary','old summary','submitted','user',CURRENT_TIMESTAMP)"),{'id':f'{node_id}-r{i}','node':node_id})
            db.execute(text("INSERT INTO audit_logs VALUES (:id,'org','user',:node,'report.submit','{}',CURRENT_TIMESTAMP)"),{'id':f'{node_id}-audit','node':node_id})
        tables=('organizations','users','projects','departments','nodes','task_reports','audit_logs')
        before={t:[tuple(r) for r in db.execute(text(f'SELECT * FROM {t} ORDER BY id'))] for t in tables}
        counts={t:db.execute(text(f'SELECT count(*) FROM {t}')).scalar_one() for t in tables}
    command.upgrade(config,'20261009_0004')
    with engine.connect() as db:
        inspector=inspect(engine)
        assert 'node_collaborators' in inspector.get_table_names()
        for table in tables:
            assert db.execute(text(f'SELECT count(*) FROM {table}')).scalar_one()==counts[table]
        for table in ('organizations','users','projects','departments','audit_logs'):
            assert [tuple(r) for r in db.execute(text(f'SELECT * FROM {table} ORDER BY id'))]==before[table]
        nodes=[tuple(r) for r in db.execute(text('SELECT * FROM nodes ORDER BY id'))]
        assert nodes==[row+(0,) for row in before['nodes']]
        # Both legacy terminal and review states retain non-null owner/department/parent relationships.
        for node_id, expected_status, expected_parent in (('task','done','phase'),('review-task','review','task')):
            assert tuple(db.execute(text('SELECT status,parent_id,owner_user_id,department_id FROM nodes WHERE id=:id'),{'id':node_id}).one())==(expected_status,expected_parent,'user','dept')
        rows=[tuple(r) for r in db.execute(text('SELECT * FROM task_reports ORDER BY id'))]
        assert len(rows)==len(before['task_reports'])==4
        assert all(row[:8]==old and row[8:14]==(None,)*6 and not row[14] for row,old in zip(rows,before['task_reports']))
        assert db.execute(text('SELECT charged_bytes FROM attachment_quotas')).scalar_one()==0
        for table in ('node_collaborators','task_notes','attachments'):
            assert db.execute(text(f'SELECT count(*) FROM {table}')).scalar_one()==0
    engine.dispose()
    command.upgrade(config,'head')


def test_p2b_migration_keeps_historical_reports(tmp_path, monkeypatch):
    check_p2b_migration_keeps_historical_reports(f"sqlite:///{tmp_path / 'p2b-migration.db'}", monkeypatch)


def exercise_p2b_constraints(engine):
    from datetime import date
    import pytest
    from sqlalchemy import select, text
    from sqlalchemy.orm import Session
    from sqlalchemy.exc import IntegrityError
    from app.models import Organization, User, Project, Node, TaskReport, TaskNote, NodeCollaborator, Attachment, AttachmentQuota, Department, now_utc
    with Session(engine) as db:
        if engine.dialect.name=='sqlite': db.execute(text('PRAGMA foreign_keys=ON'))
        node=db.scalars(select(Node).where(Node.kind=='task')).first()
        org=node.organization_id; nid=node.id; uid=node.owner_user_id
        other=Organization(key='constraint-other',name='Other');db.add(other);db.flush()
        outsider=User(organization_id=other.id,username='outsider',display_name='Outsider',role='member',password_hash='hash');db.add(outsider);db.flush()
        dept=Department(organization_id=org,name='Constraint department');db.add(dept)
        second=Node(organization_id=org,project_id=node.project_id,kind='task',title='second');db.add(second);db.flush()
        note=TaskNote(organization_id=org,node_id=second.id,body='body',author_id=uid);db.add(note);db.commit()
        alien=outsider.id; did=dept.id; note_id=note.id
        base=dict(organization_id=org,node_id=nid,submitted_by=uid,result='達成',summary='new',workflow_version=2,version=1,finished_on=date(2026,10,8))
        report=TaskReport(**base);db.add(report);db.commit()
        approved={**base,'version':2,'status':'approved','reviewed_by':uid,'reviewed_at':now_utc()}
        def denied(item):
            with pytest.raises(IntegrityError):
                db.add(item);db.commit()
            db.rollback()
        denied(TaskReport(**{**base,'version':2}))  # only one pending
        good=TaskReport(**approved);db.add(good);db.commit()
        denied(TaskReport(**approved))  # same node/version
        for change in ({'version':0},{'result':'other'},{'finished_on':None},{'reviewed_by':None},{'reviewed_by':alien},{'status':'rejected','review_comment':' '},{'self_approved':True,'status':'submitted'}):
            denied(TaskReport(**{**approved,'version':3,**change}))
        common=dict(organization_id=org,node_id=nid,created_by=uid)
        denied(NodeCollaborator(**common))
        denied(NodeCollaborator(**common,user_id=uid,department_id=did))
        denied(NodeCollaborator(**common,user_id=alien))
        db.add(NodeCollaborator(**common,user_id=uid));db.commit()
        denied(NodeCollaborator(**common,user_id=uid))
        db.add(NodeCollaborator(**common,department_id=did));db.commit()
        denied(NodeCollaborator(**common,department_id=did))
        denied(TaskNote(organization_id=org,node_id=nid,body='body',author_id=alien))
        denied(TaskNote(organization_id=org,node_id=nid,body='body',author_id=uid,revision=0))
        attachment=dict(organization_id=org,node_id=nid,uploaded_by=uid,original_name='a.txt',storage_key='unique-key',size_bytes=1,state='ready',sha256='a'*64)
        for change in ({'note_id':note_id},{'uploaded_by':alien},{'size_bytes':-1},{'state':'other'},{'sha256':None},{'report_id':report.id,'note_id':note_id}):
            denied(Attachment(**{**attachment,**change}))
        db.add(Attachment(**attachment));db.commit()
        denied(Attachment(**attachment))
        denied(AttachmentQuota(organization_id=other.id,charged_bytes=-1))


def test_p2b_composite_foreign_keys_checks_and_unique(client,engine):
    exercise_p2b_constraints(engine)


def test_p2b_postgresql_migration_constraints_and_parallel_pending(monkeypatch):
    import os
    import pytest
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from datetime import date
    from sqlalchemy import create_engine, select
    from sqlalchemy.engine import make_url
    from sqlalchemy.exc import IntegrityError
    from sqlalchemy.orm import Session
    from app.models import Node,TaskReport
    url=os.environ.get('P2B_TEST_DATABASE_URL')
    if not url:
        pytest.skip('P2B_TEST_DATABASE_URL requires a fresh dedicated PostgreSQL DB and acceptance marker')
    parsed=make_url(url)
    assert parsed.get_backend_name()=='postgresql' and parsed.database.startswith('p2b_test_')
    assert os.environ.get('PF_ACCEPTANCE_MODE')=='true'
    check_p2b_migration_keeps_historical_reports(sqlalchemy_url(url),monkeypatch)
    engine=create_engine(sqlalchemy_url(url))
    exercise_p2b_constraints(engine)
    with Session(engine) as db:
        old=db.get(Node,'task')
        node=Node(organization_id=old.organization_id,project_id=old.project_id,kind='task',title='parallel')
        db.add(node);db.commit()
        nid=node.id;org=node.organization_id;uid=old.owner_user_id
    barrier=Barrier(2)
    def submit(version):
        with Session(engine) as db:
            barrier.wait(timeout=10)
            db.add(TaskReport(organization_id=org,node_id=nid,submitted_by=uid,result='達成',summary='parallel',workflow_version=2,version=version,finished_on=date(2026,10,8)))
            try:
                db.commit();return 'committed'
            except IntegrityError:
                db.rollback();return 'conflict'
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(submit,[1,2]))
    assert sorted(results)==['committed','conflict']
    with Session(engine) as db:
        assert len(list(db.scalars(select(TaskReport).where(TaskReport.node_id==nid))))==1
    engine.dispose()


def check_p2c_migration_preserves_collaboration(url,monkeypatch):
    from datetime import date
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine,text,select
    from sqlalchemy.orm import Session
    from app.seed import seed_demo_data
    from app.models import Node,Workflow,TaskReport,TaskNote,Attachment,AuditLog,User
    monkeypatch.setenv('DATABASE_URL',url)
    config=Config('api/alembic.ini')
    def prepare(db):
        seed_demo_data(db);db.commit()
        user=db.scalars(select(User).where(User.username=='yu')).one()
        node=db.scalars(select(Node).where(Node.organization_id==user.organization_id,Node.kind=='task')).first()
        node.status='done';node.start_date=date(2026,10,9);node.due_date=date(2026,10,12)
        workflow=db.scalars(select(Workflow).where(Workflow.organization_id==user.organization_id)).first();workflow.content={'legacy':'保留'}
        report=TaskReport(organization_id=user.organization_id,node_id=node.id,submitted_by=user.id,result='legacy-custom',summary='historical')
        note=TaskNote(organization_id=user.organization_id,node_id=node.id,author_id=user.id,body='preserved note')
        db.add_all([report,note]);db.flush()
        db.add(Attachment(organization_id=user.organization_id,node_id=node.id,uploaded_by=user.id,original_name='saved.txt',storage_key='b'*32,size_bytes=5,state='ready',sha256='c'*64,note_id=note.id))
        db.add(AuditLog(organization_id=user.organization_id,node_id=node.id,actor_user_id=user.id,action='note.create',payload={'note_id':note.id,'body':note.body}))
    seed_at_revision(url,'20261008_0003',prepare)
    engine=create_engine(sqlalchemy_url(url))
    tables=['organizations','users','departments','department_members','projects','nodes','workflows','workflow_nodes','gates','task_reports','task_notes','attachments','audit_logs','attachment_quotas','node_collaborators']
    def snapshot():
        with engine.connect() as db:return {table:[tuple(row) for row in db.execute(text('SELECT * FROM '+table+' ORDER BY '+('organization_id' if table=='attachment_quotas' else 'id')))] for table in tables}
    before=snapshot();command.upgrade(config,'20261009_0004');assert snapshot()==before
    with engine.connect() as db:assert db.execute(text('SELECT count(*) FROM node_dependencies')).scalar_one()==0
    engine.dispose()
    command.upgrade(config,'head')


def test_p2c_migration_preserves_existing_collaboration(tmp_path,monkeypatch):
    check_p2c_migration_preserves_collaboration(f"sqlite:///{tmp_path/'p2c-migration.db'}",monkeypatch)


def test_p2c_postgresql_migration_and_dependency_constraints(monkeypatch):
    import os,pytest
    from sqlalchemy import create_engine,select
    from sqlalchemy.engine import make_url
    from sqlalchemy.orm import Session
    from sqlalchemy.exc import IntegrityError
    from app.models import Node,Project,NodeDependency,User
    url=os.environ.get('P2B_TEST_DATABASE_URL')
    if not url:pytest.skip('Fresh dedicated p2b_test PostgreSQL URL required for P2c migration')
    parsed=make_url(url)
    assert parsed.get_backend_name()=='postgresql' and parsed.database.startswith('p2b_test_')
    assert os.environ.get('PF_ACCEPTANCE_MODE')=='true'
    check_p2c_migration_preserves_collaboration(url,monkeypatch)
    engine=create_engine(sqlalchemy_url(url))
    try:
        with Session(engine) as db:
            first=db.scalars(select(Node).where(Node.kind=='task')).first()
            second=Node(organization_id=first.organization_id,project_id=first.project_id,kind='task',title='successor');db.add(second);db.commit()
            values={'organization_id':first.organization_id,'project_id':first.project_id,'predecessor_id':first.id,'successor_id':second.id,'created_by':first.owner_user_id}
            db.add(NodeDependency(**values));db.commit()
            for change in [{},{'successor_id':first.id},{'project_id':'missing'}]:
                with pytest.raises(IntegrityError):db.add(NodeDependency(**{**values,**change}));db.commit()
                db.rollback()
    finally:engine.dispose()


def check_tp_a_migration_preserves_nodes(url,monkeypatch):
    from datetime import date,datetime,timezone
    import pytest
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine,text,select
    from sqlalchemy.exc import IntegrityError
    from app.seed import seed_demo_data
    from app.models import Node,NodeDependency,TaskReport,User
    monkeypatch.setenv('DATABASE_URL',url)
    config=Config('api/alembic.ini')
    def prepare(db):
        seed_demo_data(db);db.commit()
        user=db.scalars(select(User).where(User.username=='yu')).one()
        first=db.scalars(select(Node).where(Node.organization_id==user.organization_id,Node.kind=='task').order_by(Node.sort_order)).first()
        first.status='done';first.start_date=date(2026,10,1);first.due_date=date(2026,10,9)
        second=Node(organization_id=user.organization_id,project_id=first.project_id,parent_id=first.parent_id,kind='task',title='後續',status='doing',sort_order=999)
        db.add(second);db.flush()
        db.add(NodeDependency(organization_id=user.organization_id,project_id=first.project_id,predecessor_id=first.id,successor_id=second.id,created_by=user.id))
        db.add(TaskReport(organization_id=user.organization_id,node_id=first.id,submitted_by=user.id,result='達成',summary='kept',workflow_version=2,version=1,status='approved',finished_on=date(2026,10,9),reviewed_by=user.id,reviewed_at=datetime(2026,10,9,tzinfo=timezone.utc),self_approved=True))
    seed_at_revision(url,'20261009_0004',prepare)
    engine=create_engine(sqlalchemy_url(url))
    tables=['organizations','users','departments','department_members','projects','nodes','workflows','workflow_nodes','gates','task_reports','task_notes','attachments','audit_logs','attachment_quotas','node_collaborators','node_dependencies']
    def snapshot():
        with engine.connect() as db:return {table:[tuple(row) for row in db.execute(text('SELECT * FROM '+table+' ORDER BY '+('organization_id' if table=='attachment_quotas' else 'id')))] for table in tables}
    before=snapshot()
    assert before['nodes'] and before['node_dependencies'] and before['task_reports']
    command.upgrade(config,'20261010_0005')
    after=snapshot()
    # Every existing value is unchanged; each node only gains weight 1 and no manual progress.
    assert after['nodes']==[row+(1,None) for row in before['nodes']]
    assert {table:rows for table,rows in after.items() if table!='nodes'}=={table:rows for table,rows in before.items() if table!='nodes'}
    node_id=before['nodes'][0][0]
    for column,value in [('weight',-1),('weight',101),('progress',-1),('progress',101)]:
        with pytest.raises(IntegrityError):
            with engine.begin() as db:db.execute(text(f'UPDATE nodes SET {column}=:value WHERE id=:id'),{'value':value,'id':node_id})
    with engine.begin() as db:db.execute(text('UPDATE nodes SET weight=0,progress=100 WHERE id=:id'),{'id':node_id})
    with engine.begin() as db:db.execute(text('UPDATE nodes SET weight=1,progress=NULL WHERE id=:id'),{'id':node_id})
    command.downgrade(config,'20261009_0004')
    assert snapshot()==before
    command.upgrade(config,'head')
    engine.dispose()


def test_tp_a_migration_preserves_nodes(tmp_path,monkeypatch):
    check_tp_a_migration_preserves_nodes(f"sqlite:///{tmp_path/'tp-a-migration.db'}",monkeypatch)


def test_tp_a_postgresql_migration_preserves_nodes(monkeypatch):
    import os,pytest
    from sqlalchemy.engine import make_url
    url=os.environ.get('P2B_TEST_DATABASE_URL')
    if not url:pytest.skip('Fresh dedicated p2b_test PostgreSQL URL required for TP-A migration')
    parsed=make_url(url)
    assert parsed.get_backend_name()=='postgresql' and parsed.database.startswith('p2b_test_')
    assert os.environ.get('PF_ACCEPTANCE_MODE')=='true'
    check_tp_a_migration_preserves_nodes(url,monkeypatch)


def check_tp_b_migration_preserves_nodes(url,monkeypatch):
    from datetime import date,datetime,timezone
    import pytest
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine,text,select
    from sqlalchemy.exc import IntegrityError
    from app.seed import seed_demo_data
    from app.models import Node,NodeDependency,TaskNote,TaskReport,User
    monkeypatch.setenv('DATABASE_URL',url)
    config=Config('api/alembic.ini')
    def prepare(db):
        seed_demo_data(db);db.commit()
        user=db.scalars(select(User).where(User.username=='yu')).one()
        first=db.scalars(select(Node).where(Node.organization_id==user.organization_id,Node.kind=='task').order_by(Node.sort_order)).first()
        first.status='done';first.weight=3;first.start_date=date(2026,10,1);first.due_date=date(2026,10,9)
        second=Node(organization_id=user.organization_id,project_id=first.project_id,parent_id=first.parent_id,kind='task',title='後續',status='doing',progress=40,sort_order=999)
        db.add(second);db.flush()
        db.add(NodeDependency(organization_id=user.organization_id,project_id=first.project_id,predecessor_id=first.id,successor_id=second.id,created_by=user.id))
        db.add(TaskReport(organization_id=user.organization_id,node_id=first.id,submitted_by=user.id,result='達成',summary='kept',workflow_version=2,version=1,status='approved',finished_on=date(2026,10,9),reviewed_by=user.id,reviewed_at=datetime(2026,10,9,tzinfo=timezone.utc),self_approved=True))
        db.add(TaskNote(organization_id=user.organization_id,node_id=second.id,body='筆記保留',author_id=user.id))
    seed_at_revision(url,'20261010_0005',prepare)
    engine=create_engine(sqlalchemy_url(url))
    tables=['organizations','users','departments','department_members','projects','nodes','workflows','workflow_nodes','gates','task_reports','task_notes','attachments','audit_logs','attachment_quotas','node_collaborators','node_dependencies']
    def snapshot():
        with engine.connect() as db:return {table:[tuple(row) for row in db.execute(text('SELECT * FROM '+table+' ORDER BY '+('organization_id' if table=='attachment_quotas' else 'id')))] for table in tables}
    before=snapshot()
    assert before['nodes'] and before['node_dependencies'] and before['task_reports'] and before['task_notes']
    command.upgrade(config,'20261010_0006')
    after=snapshot()
    # Every existing value is unchanged; each node only gains two empty soft-delete markers.
    assert after['nodes']==[row+(None,None) for row in before['nodes']]
    assert {table:rows for table,rows in after.items() if table!='nodes'}=={table:rows for table,rows in before.items() if table!='nodes'}
    node_id=before['nodes'][0][0]
    with engine.connect() as db:
        org=db.execute(text('SELECT organization_id FROM nodes WHERE id=:id'),{'id':node_id}).scalar_one()
        own=db.execute(text('SELECT id FROM users WHERE organization_id=:org ORDER BY id'),{'org':org}).scalars().first()
        other=db.execute(text('SELECT id FROM users WHERE organization_id!=:org ORDER BY id'),{'org':org}).scalars().first()
    if engine.dialect.name=='postgresql':
        # deleted_by must be a user of the same company.
        with pytest.raises(IntegrityError):
            with engine.begin() as db:db.execute(text('UPDATE nodes SET deleted_at=now(),deleted_by=:user WHERE id=:id'),{'user':other,'id':node_id})
    with engine.begin() as db:db.execute(text('UPDATE nodes SET deleted_at=:at,deleted_by=:user WHERE id=:id'),{'at':datetime(2026,10,10,tzinfo=timezone.utc),'user':own,'id':node_id})
    # A deleted row would reappear without the markers, so downgrade refuses.
    with pytest.raises(Exception):
        command.downgrade(config,'20261010_0005')
    with engine.begin() as db:db.execute(text('UPDATE nodes SET deleted_at=NULL,deleted_by=NULL WHERE id=:id'),{'id':node_id})
    command.downgrade(config,'20261010_0005')
    assert snapshot()==before
    command.upgrade(config,'head')
    engine.dispose()


def test_tp_b_migration_preserves_nodes(tmp_path,monkeypatch):
    check_tp_b_migration_preserves_nodes(f"sqlite:///{tmp_path/'tp-b-migration.db'}",monkeypatch)


def test_tp_b_postgresql_migration_preserves_nodes(monkeypatch):
    import os,pytest
    from sqlalchemy.engine import make_url
    url=os.environ.get('P2B_TEST_DATABASE_URL')
    if not url:pytest.skip('Fresh dedicated p2b_test PostgreSQL URL required for TP-B migration')
    parsed=make_url(url)
    assert parsed.get_backend_name()=='postgresql' and parsed.database.startswith('p2b_test_')
    assert os.environ.get('PF_ACCEPTANCE_MODE')=='true'
    check_tp_b_migration_preserves_nodes(url,monkeypatch)


def check_tp_c_migration_preserves_nodes(url, monkeypatch):
    import pytest
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, text, inspect
    from sqlalchemy.exc import IntegrityError
    from app.seed import seed_demo_data
    monkeypatch.setenv('DATABASE_URL', url)
    seed_at_revision(url, '20261010_0006', seed_demo_data)
    engine = create_engine(sqlalchemy_url(url))
    config = Config('api/alembic.ini')
    tables = [t for t in inspect(engine).get_table_names() if t != 'alembic_version']
    def snapshot():
        with engine.connect() as db:
            return {t: sorted([dict(r._mapping) for r in db.execute(text('SELECT * FROM ' + t))], key=lambda r: str(r.get('id', r.get('organization_id')))) for t in tables}
    before = snapshot()
    command.upgrade(config, '20261010_0007')
    after = snapshot()
    assert before['nodes']
    assert after['nodes'] == [dict(n, milestone=False, schedule_locked=False) for n in before['nodes']]
    assert {t: v for t, v in after.items() if t != 'nodes'} == {t: v for t, v in before.items() if t != 'nodes'}
    nid = next(n['id'] for n in before['nodes'] if n['kind'] == 'task')
    for sql in ['schedule_locked=true', "milestone=true,start_date=NULL,due_date=NULL", "milestone=true,start_date='2026-10-01',due_date='2026-10-02'"]:
        with pytest.raises(IntegrityError):
            with engine.begin() as db: db.execute(text('UPDATE nodes SET ' + sql + ' WHERE id=:id'), {'id': nid})
    with engine.begin() as db: db.execute(text("UPDATE nodes SET milestone=true,schedule_locked=true,start_date='2026-10-10',due_date='2026-10-10' WHERE id=:id"), {'id': nid})
    with pytest.raises(RuntimeError): command.downgrade(config, '20261010_0006')
    with engine.begin() as db: db.execute(text('UPDATE nodes SET milestone=false,schedule_locked=false WHERE id=:id'), {'id': nid})
    command.downgrade(config, '20261010_0006')
    assert set(inspect(engine).get_columns('nodes')[0])
    assert not {'milestone', 'schedule_locked'} & {c['name'] for c in inspect(engine).get_columns('nodes')}
    command.upgrade(config, 'head')
    engine.dispose()


def test_tp_c_migration_preserves_nodes(tmp_path, monkeypatch):
    check_tp_c_migration_preserves_nodes(f"sqlite:///{tmp_path/'tp-c.db'}", monkeypatch)


def test_tp_c_postgresql_migration_preserves_nodes(monkeypatch):
    import os, pytest
    from sqlalchemy.engine import make_url
    url = os.environ.get('P2B_TEST_DATABASE_URL')
    if not url: pytest.skip('Fresh dedicated p2b_test PostgreSQL URL required for TP-C migration')
    parsed = make_url(url)
    assert parsed.get_backend_name() == 'postgresql' and parsed.database.startswith('p2b_test_')
    assert os.environ.get('PF_ACCEPTANCE_MODE') == 'true'
    check_tp_c_migration_preserves_nodes(url, monkeypatch)


def check_tp_d_migration(url, monkeypatch):
    import pytest
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, text, inspect, select
    from sqlalchemy.exc import IntegrityError
    from app.seed import seed_demo_data
    from app.models import Node, User, NodeDependency
    monkeypatch.setenv('DATABASE_URL', url)
    def seed(db):
        seed_demo_data(db)
        db.flush()
        tasks = list(db.scalars(select(Node).where(Node.kind == 'task')))
        a = tasks[0]
        b = Node(organization_id=a.organization_id, project_id=a.project_id, kind='task', title='migration successor')
        db.add(b); db.flush()
        user = db.scalar(select(User).where(User.organization_id == a.organization_id))
        db.add(NodeDependency(organization_id=a.organization_id, project_id=a.project_id, predecessor_id=a.id, successor_id=b.id, created_by=user.id))
        db.flush()
    seed_at_revision(url, '20261010_0007', seed)
    engine = create_engine(sqlalchemy_url(url)); config = Config('api/alembic.ini')
    tables = [t for t in inspect(engine).get_table_names() if t != 'alembic_version']
    def snapshot():
        with engine.connect() as db:
            return {t: sorted([dict(r._mapping) for r in db.execute(text('SELECT * FROM ' + t))], key=lambda r: str(r.get('id',r.get('organization_id')))) for t in tables}
    before = snapshot(); command.upgrade(config, '20261010_0008'); after = snapshot()
    assert after['node_dependencies'] == [dict(e, relation_type='FS', lag_days=0, enforcement='hard') for e in before['node_dependencies']]
    assert {k:v for k,v in after.items() if k!='node_dependencies'} == {k:v for k,v in before.items() if k!='node_dependencies'}
    eid = after['node_dependencies'][0]['id']
    for sql in ["relation_type='SF'", 'lag_days=366', "enforcement='bad'"]:
        with pytest.raises(IntegrityError):
            with engine.begin() as db: db.execute(text('UPDATE node_dependencies SET '+sql+' WHERE id=:id'), {'id':eid})
    with engine.begin() as db: db.execute(text("UPDATE node_dependencies SET relation_type='SS' WHERE id=:id"),{'id':eid})
    with pytest.raises(RuntimeError): command.downgrade(config,'20261010_0007')
    with engine.begin() as db: db.execute(text("UPDATE node_dependencies SET relation_type='FS' WHERE id=:id"),{'id':eid})
    command.downgrade(config,'20261010_0007'); assert snapshot()==before
    command.upgrade(config,'head'); engine.dispose()


def test_tp_d_migration_preserves_data(tmp_path,monkeypatch):
    check_tp_d_migration(f"sqlite:///{tmp_path/'tp-d.db'}",monkeypatch)


def test_tp_d_postgresql_migration_preserves_data(monkeypatch):
    import os, pytest
    from sqlalchemy.engine import make_url
    url=os.environ.get('P2B_TEST_DATABASE_URL')
    if not url: pytest.skip('Fresh dedicated p2b_test PostgreSQL required for TP-D')
    parsed=make_url(url)
    assert parsed.get_backend_name()=='postgresql' and parsed.database.startswith('p2b_test_')
    assert os.environ.get('PF_ACCEPTANCE_MODE')=='true'
    check_tp_d_migration(url,monkeypatch)


def check_tp_e_migration(url,monkeypatch):
    import pytest
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, select, MetaData, Table
    from sqlalchemy.orm import Session
    from app.seed import seed_demo_data
    from app.models import Workflow, WorkflowVersion
    from app.services.workflow_service import read_payload, version_payload
    monkeypatch.setenv('DATABASE_URL',url)
    seed_at_revision(url,'20261010_0008',seed_demo_data)
    engine=create_engine(sqlalchemy_url(url));config=Config('api/alembic.ini')
    meta=MetaData();meta.reflect(engine)
    def snapshot():
        with engine.connect() as db:return {t.name:sorted([dict(r) for r in db.execute(select(t)).mappings()],key=lambda r:str(r.get('id'))) for t in meta.sorted_tables if t.name!='alembic_version'}
    before=snapshot();command.upgrade(config,'20261010_0009');assert snapshot()==before
    with Session(engine) as db:
        for w in db.scalars(select(Workflow)):
            v=db.scalar(select(WorkflowVersion).where(WorkflowVersion.workflow_id==w.id))
            assert v.version==1 and w.version==1 and w.kind=='workflow' and w.deleted_at is None
            from app.schemas import WorkflowWrite
            assert WorkflowWrite.model_validate(v.snapshot)==read_payload(db,w)
        w=db.scalars(select(Workflow)).first();w.version=2;db.commit()
    with pytest.raises(RuntimeError):command.downgrade(config,'20261010_0008')
    with Session(engine) as db:
        for w in db.scalars(select(Workflow)):w.version=1
        db.commit()
    command.downgrade(config,'20261010_0008');assert snapshot()==before
    command.upgrade(config,'head');engine.dispose()


def test_tp_e_migration_preserves_templates(tmp_path,monkeypatch):
    check_tp_e_migration(f"sqlite:///{tmp_path/'tp-e.db'}",monkeypatch)


def test_tp_e_postgresql_migration_preserves_templates(monkeypatch):
    import os,pytest
    from sqlalchemy.engine import make_url
    url=os.environ.get('P2B_TEST_DATABASE_URL')
    if not url:pytest.skip('Fresh dedicated p2b_test PostgreSQL required for TP-E')
    parsed=make_url(url)
    assert parsed.get_backend_name()=='postgresql' and parsed.database.startswith('p2b_test_')
    assert os.environ.get('PF_ACCEPTANCE_MODE')=='true'
    check_tp_e_migration(url,monkeypatch)
    # Real PostgreSQL row locking: two editors start with v1, exactly one becomes v2.
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from fastapi import HTTPException
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session
    from app.auth import CurrentUser
    from app.models import User, Organization, Workflow, WorkflowVersion
    from app.services import workflow_service
    from app.schemas import WorkflowWrite
    engine=create_engine(sqlalchemy_url(url))
    with Session(engine) as db:
        user=db.scalar(select(User).where(User.username=='yu'))
        workflow=db.scalar(select(Workflow).where(Workflow.organization_id==user.organization_id))
        wid,uid,oid=workflow.id,user.id,user.organization_id
        body=workflow_service.read_payload(db,workflow).model_dump()
    barrier=Barrier(2)
    def edit(label):
        with Session(engine) as db:
            current=CurrentUser(user=db.get(User,uid),organization=db.get(Organization,oid),token='test')
            barrier.wait(timeout=10)
            target=workflow_service.get_workflow(db,current,wid,lock=True)
            payload=WorkflowWrite.model_validate({**body,'name':label,'expected_version':1})
            try:return workflow_service.save(db,current,payload,target)['version']
            except HTTPException as error:
                db.rollback();return error.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(edit,['併發模板A','併發模板B']))
    assert sorted(results)==[2,409]
    with Session(engine) as db:
        assert db.get(Workflow,wid).version==2
        assert sorted(db.scalars(select(WorkflowVersion.version).where(WorkflowVersion.workflow_id==wid)))==[1,2]
    engine.dispose()


def check_tp_f_migration(url,monkeypatch):
    import pytest
    from sqlalchemy import create_engine, MetaData, select, text
    from alembic import command
    from alembic.config import Config
    from sqlalchemy.orm import Session
    from app.seed import seed_demo_data
    from app.models import Notification, User, Node
    monkeypatch.setenv('DATABASE_URL',url)
    config=Config('api/alembic.ini')
    seed_at_revision(url,'20261010_0009',seed_demo_data)
    engine=create_engine(sqlalchemy_url(url))
    meta=MetaData();meta.reflect(engine)
    def snapshot():
        with engine.connect() as db:
            return {t.name:sorted([dict(r) for r in db.execute(select(t)).mappings()],key=lambda r:str(r.get('id'))) for t in meta.sorted_tables if t.name!='alembic_version'}
    before=snapshot();command.upgrade(config,'head');assert snapshot()==before
    command.downgrade(config,'20261010_0009');assert snapshot()==before
    command.upgrade(config,'head')
    with Session(engine) as db:
        u=db.scalar(select(User).where(User.username=='yu'));n=db.scalar(select(Node).where(Node.organization_id==u.organization_id))
        db.add(Notification(organization_id=u.organization_id,recipient_id=u.id,node_id=n.id,event_key='preserve',message='保留'));db.commit()
    with pytest.raises(RuntimeError): command.downgrade(config,'20261010_0009')
    engine.dispose()


def test_tp_f_migration_preserves_data(tmp_path,monkeypatch):
    check_tp_f_migration(f"sqlite:///{tmp_path/'tp-f.db'}",monkeypatch)


def test_tp_f_postgresql_migration_preserves_data(monkeypatch):
    import os, pytest
    from sqlalchemy.engine import make_url
    url=os.environ.get('P2B_TEST_DATABASE_URL')
    if not url: pytest.skip('Dedicated PostgreSQL required')
    assert make_url(url).database.startswith('p2b_test_') and os.environ.get('PF_ACCEPTANCE_MODE')=='true'
    check_tp_f_migration(url,monkeypatch)

    # Two reviewers compete for the same pending request against real PostgreSQL locks.
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session
    from app.models import User, Organization, Project, Node, CollaborationRequest, AuditLog
    from app.auth import CurrentUser
    from app.routes.collaboration import RequestWrite, Decision
    from app.services import collaboration_service
    from fastapi import HTTPException
    engine=create_engine(sqlalchemy_url(url))
    with Session(engine) as db:
        admin=db.scalar(select(User).where(User.username=='yu'));member=db.scalar(select(User).where(User.username=='ming'))
        org=db.get(Organization,admin.organization_id)
        project=Project(organization_id=org.id,title='TP-F race',owner_user_id=admin.id);db.add(project);db.flush()
        node=Node(organization_id=org.id,project_id=project.id,title='Race task',kind='task',owner_user_id=member.id);db.add(node);db.commit()
        uid,oid,nid=admin.id,org.id,node.id
        result=collaboration_service.create(db,CurrentUser(member,org,''),nid,RequestWrite(kind='skip',reason='test'))
        rid=result['id']
    barrier=Barrier(2)
    def approve(_):
        with Session(engine) as db:
            current=CurrentUser(db.get(User,uid),db.get(Organization,oid),'')
            barrier.wait(timeout=10)
            try: collaboration_service.decide(db,current,rid,Decision(decision='approved'));return 200
            except HTTPException as e: db.rollback();return e.status_code
    with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(approve,range(2)))
    assert sorted(results)==[200,409]
    with Session(engine) as db:
        assert db.get(Node,nid).status=='skipped'
        assert len(list(db.scalars(select(AuditLog).where(AuditLog.node_id==nid,AuditLog.action=='node.skip'))))==1
    engine.dispose()


def check_tp_g_migration(url, monkeypatch):
    import pytest
    from sqlalchemy import create_engine, MetaData, select
    from sqlalchemy.orm import Session
    from alembic import command
    from alembic.config import Config
    from app.seed import seed_demo_data
    from app.models import Node
    monkeypatch.setenv('DATABASE_URL', url)
    seed_at_revision(url, '20261010_0010', seed_demo_data)
    config = Config('api/alembic.ini')
    engine = create_engine(sqlalchemy_url(url))
    meta = MetaData(); meta.reflect(engine)
    def snapshot():
        with engine.connect() as db:
            return {t.name: sorted([dict(r) for r in db.execute(select(t)).mappings()], key=lambda r: str(r.get('id'))) for t in meta.sorted_tables if t.name != 'alembic_version'}
    before = snapshot()
    command.upgrade(config, 'head'); assert snapshot() == before
    command.downgrade(config, '20261010_0010'); assert snapshot() == before
    command.upgrade(config, 'head')
    with Session(engine) as db:
        node = db.scalars(select(Node)).first()
        assert node.report_fields == [] and node.report_fields_version == 0
        node.report_fields_version = 1
        db.commit()
    with pytest.raises(RuntimeError): command.downgrade(config, '20261010_0010')
    engine.dispose()


def test_tp_g_migration_preserves_data(tmp_path, monkeypatch):
    check_tp_g_migration(f"sqlite:///{tmp_path/'tp-g.db'}", monkeypatch)


def test_tp_g_postgresql_migration_and_field_submit_race(monkeypatch):
    import os, pytest
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session
    from sqlalchemy.engine import make_url
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from fastapi import HTTPException
    from app.models import User, Organization, Project, Node, TaskReport
    from app.auth import CurrentUser
    from app.schemas import ReportCreate, ReportFieldsUpdate
    from app.services.report_field_service import update
    from app.services.report_service import submit_report
    url = os.environ.get('P2B_TEST_DATABASE_URL')
    if not url: pytest.skip('Dedicated PostgreSQL required')
    assert make_url(url).database.startswith('p2b_test_') and os.environ.get('PF_ACCEPTANCE_MODE') == 'true'
    check_tp_g_migration(url, monkeypatch)
    engine = create_engine(sqlalchemy_url(url))
    with Session(engine) as db:
        user = db.scalar(select(User).where(User.username == 'yu')); org = db.get(Organization, user.organization_id)
        project = Project(organization_id=org.id, title='TP-G race', owner_user_id=user.id); db.add(project); db.flush()
        node = Node(organization_id=org.id, project_id=project.id, kind='task', title='Race', owner_user_id=user.id)
        db.add(node); db.commit(); uid, oid, nid = user.id, org.id, node.id
    barrier = Barrier(2)
    def run(operation):
        with Session(engine) as db:
            current = CurrentUser(db.get(User, uid), db.get(Organization, oid), '')
            barrier.wait(timeout=10)
            try:
                if operation == 'edit': update(db, current, nid, ReportFieldsUpdate(expected_version=0, fields=[{'label':'Required','type':'text','required':True}]))
                else: submit_report(db, current, nid, ReportCreate(result='達成', summary='Race', finished_on='2026-10-10', fields_version=0))
                return 200
            except HTTPException as error: db.rollback(); return error.status_code
    with ThreadPoolExecutor(max_workers=2) as pool: results = list(pool.map(run, ['edit', 'submit']))
    assert sorted(results) == [200, 409]
    with Session(engine) as db:
        node = db.get(Node, nid)
        reports = list(db.scalars(select(TaskReport).where(TaskReport.node_id == nid)))
        assert (node.report_fields_version == 1 and reports == []) or (node.report_fields_version == 0 and len(reports) == 1 and reports[0].fields == [])
    engine.dispose()


def test_operation_links_migration_preserves_operations_and_refuses_loss(tmp_path, monkeypatch):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, text
    import pytest
    url = f'sqlite:///{tmp_path / "links.db"}'
    monkeypatch.setenv('DATABASE_URL', url)
    config = Config('api/alembic.ini')
    command.upgrade(config, '20261011_0013')
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO organizations (id,key,name) VALUES ('keep','keep','Keep data')"))
        conn.execute(text("INSERT INTO operations_records (id,organization_id,category,code,title,status,visibility,fields,source,revision,created_by,updated_by,created_at,updated_at) VALUES ('a','keep','partners','A','Record','active','internal','[]','native',1,'actor','actor','2026-10-11','2026-10-11')"))
    command.upgrade(config, 'head')
    with engine.begin() as conn:
        assert conn.scalar(text('SELECT title FROM operations_records')) == 'Record'
        assert conn.scalar(text('SELECT count(*) FROM operation_links')) == 0
        conn.execute(text("INSERT INTO operation_links (id,organization_id,project_id,record_id,created_by,created_at) VALUES ('link','keep','project','a','actor','2026-10-11')"))
    with pytest.raises(RuntimeError, match='拒絕有損降級'):
        command.downgrade(config, '20261011_0013')
    with engine.connect() as conn:
        assert conn.scalar(text('SELECT count(*) FROM operation_links')) == 1
        assert conn.scalar(text('SELECT title FROM operations_records')) == 'Record'
    engine.dispose()
