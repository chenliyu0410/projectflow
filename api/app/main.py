import os
from contextlib import asynccontextmanager
from collections.abc import Callable

import psycopg
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.routes import collaboration, notifications, report_fields, ai, documents, operations, operation_links, inventory, purchasing
from app.routes import audit_logs, auth, departments, projects, reports, workflows, workspace, records, collaborators, attachments, dependencies, conditions


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
    @asynccontextmanager
    async def lifespan(application):
        if os.environ.get("PF_ATTACHMENT_ROOT"):
            from app.services.attachment_store import storage_root, runtime_lock
            with runtime_lock(storage_root()):
                yield
        else:
            yield

    application = FastAPI(title="ProjectFlow API", lifespan=lifespan)
    application.include_router(ai.router)
    application.include_router(documents.router)
    application.include_router(operations.router)
    application.include_router(operation_links.router)
    application.include_router(inventory.router)
    application.include_router(purchasing.router)
    probe = checker if checker is not None else database_ready
    application.include_router(report_fields.router)
    application.include_router(collaboration.router)
    application.include_router(notifications.router)
    application.include_router(auth.router)
    application.include_router(departments.router)
    application.include_router(projects.router)
    application.include_router(audit_logs.router)
    application.include_router(workflows.router)
    application.include_router(reports.router)
    application.include_router(workspace.router)
    application.include_router(records.router)
    application.include_router(collaborators.router)
    application.include_router(attachments.router)
    application.include_router(dependencies.router)
    application.include_router(conditions.router)

    @application.get("/health")
    def health():
        return {"ok": True}

    @application.get("/health/acceptance")
    def acceptance_marker():
        if os.environ.get("PF_ACCEPTANCE_MODE") != "true":
            return JSONResponse(status_code=404, content={"detail": "Not found"})
        return {"acceptance": True}

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
