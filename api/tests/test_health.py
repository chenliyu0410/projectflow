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


@pytest.mark.parametrize("row", [(0,), (2,), ("1",), (1, 1), None])
def test_database_probe_rejects_unexpected_result(monkeypatch, row):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test-only")
    connect = MagicMock()
    connect.return_value.__enter__.return_value.execute.return_value.fetchone.return_value = row
    monkeypatch.setattr(psycopg, "connect", connect)
    assert database_ready() is False


def test_query_failure_is_unavailable(monkeypatch):
    # 連線成功但查詢失敗（例如權限或交易狀態錯誤）也必須回報不可用，而不是讓例外外洩。
    monkeypatch.setenv("DATABASE_URL", "postgresql://test-only")
    connect = MagicMock()
    connection = connect.return_value.__enter__.return_value
    connection.execute.side_effect = psycopg.ProgrammingError("password=do-not-leak")
    monkeypatch.setattr(psycopg, "connect", connect)
    assert database_ready() is False
    connection.execute.assert_called_once_with("SELECT 1")


@pytest.mark.parametrize("result", [1, "true", "ready", [True], None])
def test_readiness_requires_boolean_true(result):
    # 只有明確的 True 才算就緒，避免 checker 回傳真值物件時誤報可用。
    with TestClient(create_app(lambda: result)) as client:
        response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {"ok": False, "database": "unavailable"}


def test_only_health_routes_exist():
    paths = set(create_app().openapi()["paths"])
    assert paths == {
        '/projects/{project_id}/operation-links',
        '/nodes/{node_id}/operation-links',
        '/projects/{project_id}/operation-links/{record_id}',
        '/nodes/{node_id}/operation-links/{record_id}',
        '/inventory/resources/{resource_id}',
        '/inventory/movements',
        '/inventory/movements/{movement_id}/reversal',
        '/operations/{order_id}/receipts',
        '/operations/{order_id}/returns',
        '/inventory/adjustments',
        '/operations/{work_id}/issues',
        '/operations/{work_id}/issue-returns',
        '/operations/{work_id}/completions',
        '/operations/{order_id}/purchase',
        '/operations/{order_id}/purchase/lines',
        '/operations/{order_id}/purchase/close',
        '/operations/{order_id}/purchase/reopen',
        '/operations/{work_id}/production',
        '/operations/{work_id}/production/plan',
        '/operations/{work_id}/production/close',
        '/operations/{work_id}/production/reopen',
        '/operations',
        '/operations/catalog',
        '/operations/{record_id}',
        '/nodes/{node_id}/documents',
        '/projects/{project_id}/documents',
        '/documents/{document_id}/versions',
        '/documents/{document_id}/text',
        '/documents/{document_id}/versions/{version}/text',
        '/documents/{document_id}/versions/{version}/download',
        '/accounts',
        '/accounts/{user_id}',
        '/accounts/{user_id}/reset-password',
        '/auth/password',
        '/document-templates',
        '/document-templates/samples',
        '/document-templates/{template_id}',
        '/document-templates/{template_id}/file',
        '/document-templates/{template_id}/status',
        '/document-templates/{template_id}/download',
        '/nodes/{node_id}/documents/from-template',
        '/projects/{project_id}/documents/from-template',
        '/documents/{document_id}/fill',
        '/documents/{document_id}/regenerate',
        "/ai/status",
        "/ai/ask",
        "/ai/preview",
        "/ai/index/refresh",
        "/ai/governance",
        "/ai/classification",
        "/ai/policy",
        "/ai/mask-preview",
        "/ai/documents/{document_id}",
        "/ai/knowledge",
        "/ai/knowledge/{document_id}",
        "/ai/answers/{answer_id}/feedback",
        "/ai/feedback/summary",
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
        "/integrations/events",
        "/integrations/events/{event_id}/result",
        "/integrations/weekly-reports/generate",
        "/integrations/daily-digest",
        "/projects/{project_id}/weekly-reports",
        "/projects/{project_id}/weekly-reports/generate",
        "/weekly-reports/{report_id}",
        "/weekly-reports/{report_id}/confirm",
        "/integrations/maintenance/backup",
        "/integrations/maintenance/expiry",
        "/accounts/me/email",
        "/mail/failed",
        "/mail/{event_id}/retry",
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
