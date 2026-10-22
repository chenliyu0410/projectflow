import os
from contextlib import asynccontextmanager
from collections.abc import Callable

import psycopg
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.requests import Request

from app.routes import collaboration, notifications, report_fields, ai, rag, documents, operations, operation_links, inventory, purchasing, production
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


UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def cross_origin(request: Request) -> bool:
    # Sec-Fetch-Site 是瀏覽器自己判定的禁用標頭，網頁改不了；以它為準，代理改寫 Host 埠號時才不會誤擋。
    # 同主機不同埠（例如 :443、:8443 的其他服務）對 SameSite 而言是同站，所以 same-site 也要擋。
    site = request.headers.get("sec-fetch-site")
    if site is not None:
        return site not in {"same-origin", "none"}
    # 舊瀏覽器沒有 Sec-Fetch-Site，但寫入請求一定帶 Origin；兩者都沒有的是 curl、腳本等非瀏覽器請求。
    origin = request.headers.get("origin")
    return origin is not None and origin != str(request.base_url).rstrip("/")


class OriginCheckMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["method"] in UNSAFE_METHODS and cross_origin(Request(scope)):
            await JSONResponse(status_code=403, content={"detail": "不允許此來源"})(scope, receive, send)
            return
        await self.app(scope, receive, send)


def create_app(checker: Callable[[], bool] | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(application):
        if os.environ.get("PF_ATTACHMENT_ROOT"):
            from app.services.attachment_store import storage_root, runtime_lock
            with runtime_lock(storage_root()):
                yield
        else:
            yield

    # 公開試用時不要把完整 API 清單送給任何人；開發要看再設 PF_API_DOCS=true。
    docs = os.environ.get("PF_API_DOCS") == "true"
    application = FastAPI(title="ProjectFlow API", lifespan=lifespan, openapi_url="/openapi.json" if docs else None,
                          docs_url="/docs" if docs else None, redoc_url="/redoc" if docs else None)
    application.add_middleware(OriginCheckMiddleware)
    application.include_router(ai.router)
    application.include_router(rag.router)
    application.include_router(documents.router)
    application.include_router(operations.router)
    application.include_router(operation_links.router)
    application.include_router(inventory.router)
    application.include_router(purchasing.router)
    application.include_router(production.router)
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
