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
