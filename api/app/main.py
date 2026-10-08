import os
from collections.abc import Callable

import psycopg
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.routes import audit_logs, auth, departments, projects


def database_ready() -> bool:
    url = os.environ.get("DATABASE_URL")
    if not url:
        return False
    try:
        with psycopg.connect(url, connect_timeout=2) as connection:
            return connection.execute("SELECT 1").fetchone() == (1,)
    except psycopg.Error:
        return False


def create_app(checker: Callable[[], bool] | None = None) -> FastAPI:
    application = FastAPI(title="ProjectFlow API")
    probe = checker if checker is not None else database_ready
    application.include_router(auth.router)
    application.include_router(departments.router)
    application.include_router(projects.router)
    application.include_router(audit_logs.router)

    @application.get("/health")
    def health():
        return {"ok": True}

    @application.get("/health/ready")
    def readiness():
        try:
            available = probe() is True
        except Exception:
            available = False
        return JSONResponse(
            status_code=200 if available else 503,
            content={"ok": available, "database": "ready" if available else "unavailable"},
        )

    return application


app = create_app()
