from unittest.mock import MagicMock

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.main import create_app, database_ready


def test_liveness_does_not_check_database():
    checker = MagicMock(side_effect=AssertionError("not called"))
    with TestClient(create_app(checker)) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    checker.assert_not_called()


@pytest.mark.parametrize("available,status,label", [
    (True, 200, "ready"), (False, 503, "unavailable"),
])
def test_readiness_contract(available, status, label):
    with TestClient(create_app(lambda: available)) as client:
        response = client.get("/health/ready")
    assert response.status_code == status
    assert response.json() == {"ok": available, "database": label}


def test_unexpected_error_does_not_expose_secrets():
    checker = MagicMock(side_effect=RuntimeError("password=do-not-leak"))
    with TestClient(create_app(checker)) as client:
        response = client.get("/health/ready")
    assert response.status_code == 503
    assert "do-not-leak" not in response.text


def test_missing_database_configuration(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    connect = MagicMock()
    monkeypatch.setattr(psycopg, "connect", connect)
    assert database_ready() is False
    connect.assert_not_called()


def test_database_probe_executes_query(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test-only")
    connect = MagicMock()
    connection = connect.return_value.__enter__.return_value
    connection.execute.return_value.fetchone.return_value = (1,)
    monkeypatch.setattr(psycopg, "connect", connect)
    assert database_ready() is True
    connect.assert_called_once_with("postgresql://test-only", connect_timeout=2)
    connection.execute.assert_called_once_with("SELECT 1")


def test_connection_failure_is_unavailable(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test-only")
    monkeypatch.setattr(psycopg, "connect", MagicMock(side_effect=psycopg.OperationalError("secret")))
    assert database_ready() is False


def test_only_health_routes_exist():
    paths = set(create_app().openapi()["paths"])
    assert paths == {
        '/operations',
        '/operations/catalog',
        '/operations/{record_id}',
        '/nodes/{node_id}/documents',
        '/projects/{project_id}/documents',
        '/documents/{document_id}/versions',
        '/documents/{document_id}/text',
        '/documents/{document_id}/versions/{version}/text',
        '/documents/{document_id}/versions/{version}/download',
        "/ai/status",
        "/ai/ask",
        "/ai/documents/{document_id}",
        "/ai/model",
        "/ai/model/test",
        "/audit-logs",
        "/auth/login",
        "/auth/logout",
        "/auth/me",
        "/auth/showcase/switch",
        "/workflow-catalog",
        "/departments",
        "/departments/{department_id}",
        "/nodes/{node_id}/requests",
        "/requests/{request_id}/decision",
        "/workspace/requests",
        "/notifications",
        "/notifications/{notification_id}/read",
        "/gates/{gate_id}",
        "/health",
        "/health/acceptance",
        "/health/ready",
        "/nodes/{node_id}",
        "/nodes/{node_id}/reports",
        "/nodes/{node_id}/report-fields",
        "/nodes/{node_id}/attachments",
        "/nodes/{node_id}/attachment-quota",
        "/attachments/{attachment_id}",
        "/attachments/{attachment_id}/download",
        "/nodes/{node_id}/notes",
        "/notes/{note_id}",
        "/nodes/{node_id}/records",
        "/nodes/{node_id}/collaborators",
        "/nodes/{node_id}/lifecycle",
        "/reports/{report_id}/review",
        "/nodes/{node_id}/status",
        "/nodes/{node_id}/schedule",
        "/projects",
        "/projects/{project_id}/conditions",
        "/conditions/{condition_id}",
        "/conditions/{condition_id}/confirmation",
        "/projects/from-workflow",
        "/projects/{project_id}",
        "/projects/{project_id}/assignment-options",
        "/projects/{project_id}/nodes",
        "/nodes/{node_id}/save-template",
        "/nodes/{node_id}/apply-template",
        "/projects/{project_id}/save-template",
        "/projects/{project_id}/apply-template",
        "/workflows/{workflow_id}/versions",
        "/workflows/{workflow_id}/versions/{version}",
        "/workflows",
        "/workflows/{workflow_id}",
        "/workflows/{workflow_id}/copy",
        "/projects/{project_id}/dependencies",
        "/projects/{project_id}/records",
        "/nodes/{node_id}/move",
        "/nodes/{node_id}/copy",
        "/undo",
        "/dependencies/{dependency_id}",
        "/workspace/overview",
        "/workspace/my-tasks",
        "/workspace/reviews",
    }


@pytest.mark.parametrize('mode', [None, 'false', 'TRUE', '1'])
def test_acceptance_marker_disabled_by_default(monkeypatch, mode):
    if mode is None:
        monkeypatch.delenv('PF_ACCEPTANCE_MODE', raising=False)
    else:
        monkeypatch.setenv('PF_ACCEPTANCE_MODE', mode)
    with TestClient(create_app(lambda: True)) as client:
        assert client.get('/health/acceptance').status_code == 404


def test_acceptance_marker_requires_explicit_mode(monkeypatch):
    monkeypatch.setenv('PF_ACCEPTANCE_MODE', 'true')
    with TestClient(create_app(lambda: True)) as client:
        response = client.get('/health/acceptance')
        assert response.status_code == 200
        assert response.json() == {'acceptance': True}
