from pathlib import Path


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
