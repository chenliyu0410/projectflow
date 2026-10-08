from pathlib import Path

from app.database import sqlalchemy_url


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
    command.upgrade(config,'head')
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
