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
    assert paths == {"/auth/login", "/auth/logout", "/auth/me", "/health", "/health/ready"}
