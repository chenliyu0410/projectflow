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
    command.upgrade(config, 'head')
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
