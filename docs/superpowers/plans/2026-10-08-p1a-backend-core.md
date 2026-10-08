# P1a Backend Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` for Native execution. Independent Task reviews are required by this repository. Steps use checkbox (`- [ ]`) syntax for tracking, but do not check off this file; `docs/PROGRESS.md` is the only execution ledger.
> **Gate:** D51 authorizes delivery through P1c, but this P1a plan must be reviewed before product edits, dependency installation, migrations or API implementation. P1a is backend only; P1b owns React workflow screens.

**Goal:** Add trusted login sessions, organization-scoped PostgreSQL migrations and core FastAPI APIs for ProjectFlow projects, nodes, departments, workflows, gates, reports and audit logs.

**Architecture:** Keep the P0 health surface and Compose stack, then add a backend domain layer under `api/app/`. SQLAlchemy models define the schema; Alembic applies migrations to PostgreSQL. Every business row has `organization_id`, every request resolves the organization from an HttpOnly session, and every read/write route scopes by that organization before applying `can_view` or `can_work`.

**Tech Stack:** Python 3.13, FastAPI, psycopg 3, SQLAlchemy 2.0, Alembic, PostgreSQL 17, pytest, Docker Compose.

**Spec:** [Formal Product MVP, P1a subsection](../specs/2026-10-05-formal-product-mvp-design.md). Company boundary requirement comes from [W6 §13](../specs/2026-10-08-multi-company-industry-demo-design.md).

## Global Constraints

- Scope is P1a only. Do not build React project workflow UI; P1b consumes the APIs created here.
- Do not modify either Demo HTML file or `tests/records.html`, `tests/*.test.js`. Demo baseline remains v6 / 174 tests; formal database versioning is separate.
- Only files listed in this plan may be created or edited. Generated `.venv`, build outputs, logs and local `.env` are never committed.
- Traditional Chinese visible API messages. No cloud AI, real ERP, AD/LDAP, RAG, attachment storage or production file-version editing in P1a.
- Dependencies are locked. Add only `SQLAlchemy==2.0.53` and `alembic==1.20.0` to the existing P0 backend dependencies unless a compatibility failure is proven and this plan is revised.
- Password hashing uses Python stdlib PBKDF2-HMAC-SHA256 plus per-user salt. No plaintext password, token, DSN or secret appears in Git, frontend bundles, error responses or logs.
- Sessions are server-side rows plus an HttpOnly, SameSite=Lax cookie named `pf_session`. API tests may also pass the cookie through `TestClient`; no header may override organization isolation.
- All business tables include `organization_id`. Cross-table references inside organization-scoped data use composite foreign keys `(organization_id, id)` or explicit scoped lookup before mutation. Do not assume Demo IDs are globally unique.
- Backend company/role checks cannot be replaced with frontend visibility. Every route that returns or mutates business data calls the authorization helper or an equivalent route-specific scoped query.
- Migrations are explicit Alembic revisions committed to Git. Do not create business tables with ad hoc startup DDL.
- Follow WORKFLOW §3 RED -> GREEN -> independent review -> PROGRESS commit. Formal tests record pytest summary and exit code; never claim a test passed without running it.
- Main checkout only; one `feature/*` branch at a time. No worktrees, pull, rebase, force, hard reset, destructive volume deletion, or `down -v`. Stage explicit paths only.
- P1a completion updates README and PROGRESS, gets reviewed and ff-only merged, then `git push origin main` under D50.

## Review Focus

1. Cross-company ID guessing: a valid session in organization A must get 404/403 and no data when using organization B project, node, workflow, gate, report or audit IDs. Tasks 2-4 pin this.
2. Frontend-forged organization: changing request JSON or query parameters cannot switch organization; the server uses the session organization only. Tasks 1-4 pin this.
3. Missing or stale session: business endpoints reject unauthenticated requests and logged-out sessions; no route falls back to demo-like user switching. Task 1 pins this and later tasks reuse the dependency.
4. Gate bypass: direct status updates cannot start blocked later-stage tasks while the previous gate is pending, even if the payload includes override-like fields. Task 4 pins this.
5. Audit integrity: successful business writes create same-organization audit rows; audit listing never leaks another organization's activity. Tasks 3-4 pin this.

## File Structure

```text
api/requirements.txt, api/requirements.lock, api/pyproject.toml
api/alembic.ini
api/alembic/env.py
api/alembic/versions/20261008_0001_p1a_core.py
api/app/main.py
api/app/database.py
api/app/models.py
api/app/schemas.py
api/app/security.py
api/app/auth.py
api/app/permissions.py
api/app/audit.py
api/app/seed.py
api/app/routes/__init__.py
api/app/routes/auth.py
api/app/routes/departments.py
api/app/routes/projects.py
api/app/routes/workflows.py
api/app/routes/reports.py
api/app/routes/audit_logs.py
api/tests/conftest.py
api/tests/test_auth.py
api/tests/test_migrations.py
api/tests/test_projects_nodes.py
api/tests/test_workflows_gates.py
api/tests/test_reports_audit.py
deploy/api.Dockerfile
docs/formal-development.md
README.md
docs/PROGRESS.md
```

## Data Contract

Use UUID primary keys represented as strings in JSON. Seed data creates two organizations:

- `org-demo-food`: `key="food"`, name `毛研食品`
- `org-demo-electronics`: `key="electronics"`, name `峰曜科技`

Seed users:

- food: `yu / demo-yu` role `admin`, `chen / demo-chen` role `reviewer`, `ming / demo-ming` role `member`, `lin / demo-lin` role `readonly`
- electronics: `elaine / demo-elaine` role `admin`, `kai / demo-kai` role `member`

Minimal role behavior for P1a:

- `admin`: view and work on all records in their organization.
- `project_owner`: view and work on projects they own. Seed `yu` is also project owner for the food seed project.
- `reviewer`: view projects in their organization; work only on gates and nodes where they are the department head or node owner.
- `member`: view and work on nodes they own; view ancestor project and same-project nodes returned as path context only when required by an endpoint.
- `readonly`: view organization projects and nodes, no writes.

Core status values:

- Node status: `todo`, `doing`, `review`, `done`, `skipped`
- Gate status: `pending`, `approved`
- Report status: `submitted`, `approved`, `rejected`

## Task 1: Sessions, Database Layer And Migration Skeleton

**Files:**
- Modify: `api/requirements.txt`, `api/requirements.lock`, `api/pyproject.toml`, `api/app/main.py`, `deploy/api.Dockerfile`, `docs/formal-development.md`, README, PROGRESS.
- Create: `api/alembic.ini`, `api/alembic/env.py`, `api/app/database.py`, `api/app/models.py`, `api/app/schemas.py`, `api/app/security.py`, `api/app/auth.py`, `api/app/routes/__init__.py`, `api/app/routes/auth.py`, `api/tests/conftest.py`, `api/tests/test_auth.py`, `api/tests/test_migrations.py`.

**Interfaces:**
- Produces: `get_engine() -> Engine`, `get_session() -> Iterator[Session]`, `Base`.
- Produces: `hash_password(password: str, salt: bytes | None = None) -> str`, `verify_password(password: str, encoded: str) -> bool`.
- Produces: `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`.
- Produces: `require_session(request, db) -> CurrentUser` reading only the `pf_session` cookie.

- [ ] **Step 1: Pre-flight and start branch.**

Run G3 pre-flight from `main`: verify `git status --short` is clean, `git branch --list "feature/*"` is empty, and the P0 formal tests match the PROGRESS baseline. Do not run Demo tests unless P0 files or Demo files differ.

```powershell
git rev-parse HEAD
git status --short
git branch --list "feature/*"
api/.venv/Scripts/python.exe -m pytest -c api/pyproject.toml api/tests -q
npm.cmd --prefix web test
npm.cmd --prefix web run build
npm.cmd --prefix web run e2e
```

Expected baseline before product edits: API `8 passed`, React `6 passed`, E2E `4 passed`, build exit 0. Record exact output in PROGRESS. Commit `Progress: start P1a`, then `git checkout -b feature/p1a-backend-core`.

- [ ] **Step 2: Add dependency pins and failing auth/migration tests.**

Append to `api/requirements.txt`:

```text
SQLAlchemy==2.0.53
alembic==1.20.0
```

Update `api/pyproject.toml` so warnings from SQLAlchemy deprecations fail during tests:

```toml
filterwarnings = [
  "error::sqlalchemy.exc.SAWarning"
]
```

Create `api/tests/conftest.py`:

```python
import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_session
from app.main import create_app
from app.seed import seed_demo_data


@pytest.fixture()
def engine(tmp_path, monkeypatch):
    db_path = tmp_path / f"projectflow-{uuid.uuid4().hex}.db"
    url = f"sqlite+pysqlite:///{db_path}"
    monkeypatch.setenv("DATABASE_URL", url)
    engine = create_engine(url, future=True)
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture()
def client(engine):
    SessionLocal = sessionmaker(bind=engine, future=True)

    def override_session():
        with SessionLocal() as session:
            yield session

    app = create_app()
    app.dependency_overrides[get_session] = override_session
    with SessionLocal() as session:
        seed_demo_data(session)
        session.commit()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
```

Create `api/tests/test_auth.py`:

```python
def test_login_sets_http_only_session_cookie(client):
    response = client.post("/auth/login", json={
        "organization_key": "food",
        "username": "yu",
        "password": "demo-yu",
    })
    assert response.status_code == 200
    body = response.json()
    assert body == {
        "user": {"id": body["user"]["id"], "username": "yu", "display_name": "游專案", "role": "admin"},
        "organization": {"id": body["organization"]["id"], "key": "food", "name": "毛研食品"},
    }
    cookie = response.headers["set-cookie"]
    assert "pf_session=" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert "demo-yu" not in response.text


def test_login_rejects_wrong_org_or_password(client):
    bad_org = client.post("/auth/login", json={"organization_key": "missing", "username": "yu", "password": "demo-yu"})
    bad_password = client.post("/auth/login", json={"organization_key": "food", "username": "yu", "password": "wrong"})
    assert bad_org.status_code == 401
    assert bad_password.status_code == 401
    assert bad_org.json() == {"detail": "帳號或密碼錯誤"}
    assert bad_password.json() == {"detail": "帳號或密碼錯誤"}


def test_me_requires_valid_session_and_logout_revokes_it(client):
    assert client.get("/auth/me").status_code == 401
    assert client.post("/auth/login", json={"organization_key": "food", "username": "yu", "password": "demo-yu"}).status_code == 200
    assert client.get("/auth/me").status_code == 200
    assert client.post("/auth/logout").status_code == 204
    assert client.get("/auth/me").status_code == 401


def test_user_cannot_forge_organization_in_me_payload(client):
    assert client.post("/auth/login", json={"organization_key": "food", "username": "yu", "password": "demo-yu"}).status_code == 200
    response = client.get("/auth/me?organization_key=electronics")
    assert response.status_code == 200
    assert response.json()["organization"]["key"] == "food"
```

Create `api/tests/test_migrations.py`:

```python
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
```

Run:

```powershell
api/.venv/Scripts/python.exe -m pip install -r api/requirements.txt
api/.venv/Scripts/python.exe -m pytest -c api/pyproject.toml api/tests/test_auth.py api/tests/test_migrations.py -q
```

Expected RED: imports fail for missing `app.database`, `app.seed`, auth routes or missing migration file, after dependency installation succeeds. Record exact summary and exit code.

- [ ] **Step 3: Implement DB/session/auth modules and migration skeleton.**

`api/app/database.py`:

```python
import os
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


def database_url() -> str:
    value = os.environ.get("DATABASE_URL")
    if not value:
        raise RuntimeError("DATABASE_URL is required")
    return value


def get_engine():
    return create_engine(database_url(), pool_pre_ping=True, future=True)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=None, future=True)


def get_session() -> Iterator[Session]:
    engine = get_engine()
    with Session(engine) as session:
        yield session
```

`api/app/security.py`:

```python
import base64
import hashlib
import hmac
import secrets

ITERATIONS = 390000


def hash_password(password: str, salt: bytes | None = None) -> str:
    actual_salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), actual_salt, ITERATIONS)
    return "pbkdf2_sha256${}${}${}".format(
        ITERATIONS,
        base64.b64encode(actual_salt).decode("ascii"),
        base64.b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, rounds, salt, expected = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hash_password(password, base64.b64decode(salt)).split("$", 3)[3]
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def new_token() -> str:
    return secrets.token_urlsafe(32)
```

`api/app/models.py` defines SQLAlchemy ORM classes for every table listed in `test_migrations.py`. Use string UUID defaults and import `JSON` for SQLite-compatible tests:

```python
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, ForeignKeyConstraint, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def uuid_text() -> str:
    return str(uuid.uuid4())


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_text)
    key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
```

Continue the same style for `User`, `SessionToken`, `Department`, `DepartmentMember`, `Project`, `Node`, `Workflow`, `WorkflowNode`, `Gate`, `TaskReport`, `AuditLog`. For SQLite tests, use `JsonType = JSON().with_variant(JSONB, "postgresql")` for JSON columns. Add composite unique constraints on `(organization_id, id)` for organization-scoped tables and composite FKs for node/project relationships.

`api/app/schemas.py` contains Pydantic request/response models: `LoginRequest`, `UserOut`, `OrganizationOut`, `LoginResponse`, `MeResponse`. Keep `extra="forbid"` for request models that should reject forged organization payload fields.

`api/app/auth.py`:

```python
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_session
from app.models import Organization, SessionToken, User
from app.security import new_token, verify_password

COOKIE_NAME = "pf_session"


@dataclass(frozen=True)
class CurrentUser:
    user: User
    organization: Organization


def require_session(request: Request, db: Session = Depends(get_session)) -> CurrentUser:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="請先登入")
    row = db.execute(
        select(SessionToken, User, Organization)
        .join(User, SessionToken.user_id == User.id)
        .join(Organization, SessionToken.organization_id == Organization.id)
        .where(SessionToken.token == token, SessionToken.expires_at > datetime.now(timezone.utc))
    ).first()
    if row is None:
        raise HTTPException(status_code=401, detail="請先登入")
    _, user, organization = row
    return CurrentUser(user=user, organization=organization)
```

`api/app/routes/auth.py` implements login/logout/me with `pf_session` HttpOnly cookie. Login query must filter by both `Organization.key` and `User.username`; do not return whether org or password was wrong.

Update `api/app/main.py` to import and include auth routes while keeping `/health` and `/health/ready` unchanged.

`api/app/seed.py` creates the seed organizations/users/departments but no projects yet. It must be idempotent by organization key and username.

Create Alembic files:

```ini
# api/alembic.ini
[alembic]
script_location = api/alembic
prepend_sys_path = .
sqlalchemy.url = driver://user:pass@localhost/dbname
```

`api/alembic/env.py` reads `DATABASE_URL`, imports `app.models`, and sets `target_metadata = Base.metadata`.

`api/alembic/versions/20261008_0001_p1a_core.py` manually creates all P1a tables and indexes. `upgrade()` creates tables in dependency order; `downgrade()` drops them in reverse order. Use PostgreSQL `JSONB` in migration for `payload` and workflow template content.

- [ ] **Step 4: GREEN, lock and docs.**

Run:

```powershell
api/.venv/Scripts/python.exe -m pytest -c api/pyproject.toml api/tests/test_auth.py api/tests/test_migrations.py -q
api/.venv/Scripts/python.exe -m pip check
```

Expected GREEN: auth and migration tests pass. Regenerate `api/requirements.lock` with `pip freeze`, inspect for local paths or credentials, and commit only the lock file.

Update `docs/formal-development.md` with:

```markdown
## P1a 後端資料庫
P1a 使用 Alembic migration 管理正式業務 schema。啟動完整 Compose 後，從 repo 根目錄執行：
`api/.venv/Scripts/python.exe -m alembic -c api/alembic.ini upgrade head`

本機測試會使用 SQLite 暫存資料庫檢查路由與權限；完整 PostgreSQL migration 仍必須在 Compose DB 上實跑。登入使用本地種子帳號與 HttpOnly session cookie，只供 P1a/P1b MVP 驗證，不代表 AD/LDAP 已完成。
```

- [ ] **Step 5: Review and commit.**

Run `git diff --check`, then explicit `git add` Task 1 files. Commit:

```bash
git commit -m "P1a task 1: add sessions and migration foundation"
```

Independent review per WORKFLOW §4. Fix Critical/Important findings, then update PROGRESS with real RED/GREEN and commit `Progress: P1a task 1 done`.

## Task 2: Projects, Departments, Nodes And Server-Side Permissions

**Files:**
- Modify: `api/app/main.py`, `api/app/models.py`, `api/app/schemas.py`, `api/app/seed.py`, `api/alembic/versions/20261008_0001_p1a_core.py`, `docs/formal-development.md`, README, PROGRESS.
- Create: `api/app/permissions.py`, `api/app/audit.py`, `api/app/routes/departments.py`, `api/app/routes/projects.py`, `api/tests/test_projects_nodes.py`.

**Interfaces:**
- Produces: `can_view(current: CurrentUser, node: Node | Project) -> bool`, `can_work(current: CurrentUser, node: Node) -> bool`.
- Produces: `log_audit(db, current, action, node_id=None, payload=None) -> AuditLog`.
- Produces: `GET /departments`, `GET /projects`, `POST /projects`, `GET /projects/{project_id}`, `POST /projects/{project_id}/nodes`, `PATCH /nodes/{node_id}/status`.

- [ ] **Step 1: Write failing tests.**

Create `api/tests/test_projects_nodes.py`:

```python
def login(client, org="food", username="yu", password=None):
    response = client.post("/auth/login", json={
        "organization_key": org,
        "username": username,
        "password": password or f"demo-{username}",
    })
    assert response.status_code == 200


def test_project_list_is_scoped_to_session_org(client):
    login(client, "food", "yu")
    food = client.get("/projects").json()["items"]
    assert [project["title"] for project in food] == ["成貓主食罐正式版"]
    client.post("/auth/logout")
    login(client, "electronics", "elaine", "demo-elaine")
    electronics = client.get("/projects").json()["items"]
    assert [project["title"] for project in electronics] == ["連接器新產品正式版"]


def test_forged_org_parameter_does_not_change_project_scope(client):
    login(client, "food", "yu")
    response = client.get("/projects?organization_key=electronics")
    assert response.status_code == 200
    assert [project["organization_key"] for project in response.json()["items"]] == ["food"]


def test_create_project_writes_audit_in_same_org(client):
    login(client, "food", "yu")
    created = client.post("/projects", json={"title": "包材替代專案"}).json()
    assert created["title"] == "包材替代專案"
    logs = client.get("/audit-logs").json()["items"]
    assert logs[0]["action"] == "project.create"
    assert logs[0]["organization_key"] == "food"


def test_node_status_requires_can_work(client):
    login(client, "food", "lin", "demo-lin")
    project = client.get("/projects").json()["items"][0]
    node = client.get(f"/projects/{project['id']}").json()["nodes"][0]
    denied = client.patch(f"/nodes/{node['id']}/status", json={"status": "doing"})
    assert denied.status_code == 403
    client.post("/auth/logout")
    login(client, "food", "ming", "demo-ming")
    ok = client.patch(f"/nodes/{node['id']}/status", json={"status": "doing"})
    assert ok.status_code == 200
    assert ok.json()["status"] == "doing"


def test_cross_company_project_and_node_ids_are_not_visible(client):
    login(client, "electronics", "elaine", "demo-elaine")
    other_project_id = client.get("/projects").json()["items"][0]["id"]
    client.post("/auth/logout")
    login(client, "food", "yu")
    assert client.get(f"/projects/{other_project_id}").status_code == 404
    assert client.post(f"/projects/{other_project_id}/nodes", json={"title": "偷看", "kind": "task"}).status_code == 404
```

Run:

```powershell
api/.venv/Scripts/python.exe -m pytest -c api/pyproject.toml api/tests/test_projects_nodes.py -q
```

Expected RED: routes missing or unimplemented. Record real summary and exit code.

- [ ] **Step 2: Implement permissions and audit helpers.**

`api/app/permissions.py`:

```python
from app.auth import CurrentUser
from app.models import Node, Project


def can_view_project(current: CurrentUser, project: Project) -> bool:
    return project.organization_id == current.organization.id and current.user.role in {"admin", "project_owner", "reviewer", "member", "readonly"}


def can_work_project(current: CurrentUser, project: Project) -> bool:
    return project.organization_id == current.organization.id and (
        current.user.role == "admin" or project.owner_user_id == current.user.id
    )


def can_view_node(current: CurrentUser, node: Node) -> bool:
    if node.organization_id != current.organization.id:
        return False
    return current.user.role in {"admin", "project_owner", "reviewer", "readonly"} or node.owner_user_id == current.user.id


def can_work_node(current: CurrentUser, node: Node) -> bool:
    if node.organization_id != current.organization.id:
        return False
    return current.user.role == "admin" or node.owner_user_id == current.user.id or node.department_head_user_id == current.user.id
```

When implementing, prefer deriving `department_head_user_id` through relationships or a query instead of denormalizing unless the model already has that property in the task implementation. The route must be testable for `ming` owning the seed task and `lin` readonly denial.

`api/app/audit.py` inserts `AuditLog` rows. It must receive `CurrentUser`, copy `organization_id` from the session, and never accept `organization_id` from request payload.

- [ ] **Step 3: Implement department/project/node routes.**

`GET /departments` returns departments from `current.organization.id` only.

`GET /projects` returns project summaries in session organization. For P1a, `member` and `readonly` may see the seeded organization projects; detailed node write checks still protect mutations.

`POST /projects` accepts:

```json
{"title":"包材替代專案"}
```

Only `admin` may create projects in P1a. The owner is the current user. Create one root project node of kind `project` with the same title, then write `project.create` audit.

`GET /projects/{project_id}` uses `where(Project.organization_id == current.organization.id, Project.id == project_id)`. If not found, return 404. Return project plus nodes ordered by `sort_order`.

`POST /projects/{project_id}/nodes` accepts `title`, `kind`, optional `parent_id`, `owner_user_id`, `department_id`. Validate that parent, owner and department all belong to the current organization. Write `node.create` audit.

`PATCH /nodes/{node_id}/status` accepts only `status`. Reject any payload containing `organization_id`, `override`, `force` or unknown keys by using Pydantic `extra="forbid"`. Load node by session organization and apply `can_work_node`; write `node.status` audit.

Register routes in `create_app()`.

- [ ] **Step 4: Seed organization-scoped data.**

Expand `seed_demo_data(session)` to create:

- food departments: `研發`, `品保`, `採購`
- food project `成貓主食罐正式版` owned by `yu`
- food nodes: phase `市場與配方`, task `殺菌條件驗證` owned by `ming`, task department `品保`
- electronics departments: `研發`, `製造`
- electronics project `連接器新產品正式版` owned by `elaine`
- electronics node: task `端子耐久測試` owned by `kai`

Use deterministic seed keys in a `seed_key` column or idempotent unique titles per organization; do not reuse Demo localStorage IDs.

- [ ] **Step 5: GREEN, docs and commit.**

Run:

```powershell
api/.venv/Scripts/python.exe -m pytest -c api/pyproject.toml api/tests/test_auth.py api/tests/test_projects_nodes.py -q
api/.venv/Scripts/python.exe -m pytest -c api/pyproject.toml api/tests -q
```

Expected GREEN: all current API tests pass. Update `docs/formal-development.md` with the seed login list and API examples using `TestClient`/curl without printing passwords beyond the documented demo passwords. Commit:

```bash
git commit -m "P1a task 2: add scoped projects and node permissions"
```

Independent review, fixes if needed, then `Progress: P1a task 2 done`.

## Task 3: Workflows And Gate Enforcement

**Files:**
- Modify: `api/app/main.py`, `api/app/models.py`, `api/app/schemas.py`, `api/app/seed.py`, `api/app/routes/projects.py`, `api/app/permissions.py`, `api/app/audit.py`, `api/alembic/versions/20261008_0001_p1a_core.py`, `docs/formal-development.md`, README, PROGRESS.
- Create: `api/app/routes/workflows.py`, `api/tests/test_workflows_gates.py`.

**Interfaces:**
- Produces: `GET /workflows`, `POST /projects/from-workflow`.
- Produces: `PATCH /gates/{gate_id}`.
- Produces: `blocked_by_pending_gate(db, current, node) -> bool`.

- [ ] **Step 1: Write failing workflow/gate tests.**

Create `api/tests/test_workflows_gates.py`:

```python
def login(client, org="food", username="yu", password=None):
    response = client.post("/auth/login", json={
        "organization_key": org,
        "username": username,
        "password": password or f"demo-{username}",
    })
    assert response.status_code == 200


def test_workflow_list_is_scoped_by_organization(client):
    login(client, "food", "yu")
    food_names = [item["name"] for item in client.get("/workflows").json()["items"]]
    assert food_names == ["食品新品開發"]
    client.post("/auth/logout")
    login(client, "electronics", "elaine", "demo-elaine")
    electronics_names = [item["name"] for item in client.get("/workflows").json()["items"]]
    assert electronics_names == ["電子新品開發"]


def test_create_project_from_workflow_creates_nodes_gates_and_audit(client):
    login(client, "food", "yu")
    workflow_id = client.get("/workflows").json()["items"][0]["id"]
    created = client.post("/projects/from-workflow", json={"workflow_id": workflow_id, "title": "犬用鮮食上市"}).json()
    assert created["title"] == "犬用鮮食上市"
    detail = client.get(f"/projects/{created['id']}").json()
    assert [node["title"] for node in detail["nodes"]] == ["市場與配方", "小量試作", "配方設計", "試作工單"]
    assert detail["gates"][0]["status"] == "pending"
    assert client.get("/audit-logs").json()["items"][0]["action"] == "workflow.instantiate"


def test_cross_company_workflow_id_cannot_instantiate_project(client):
    login(client, "electronics", "elaine", "demo-elaine")
    other_workflow = client.get("/workflows").json()["items"][0]["id"]
    client.post("/auth/logout")
    login(client, "food", "yu")
    response = client.post("/projects/from-workflow", json={"workflow_id": other_workflow, "title": "不該建立"})
    assert response.status_code == 404


def test_pending_gate_blocks_later_stage_even_with_override_payload(client):
    login(client, "food", "yu")
    workflow_id = client.get("/workflows").json()["items"][0]["id"]
    project = client.post("/projects/from-workflow", json={"workflow_id": workflow_id, "title": "Gate測試"}).json()
    detail = client.get(f"/projects/{project['id']}").json()
    later_task = next(node for node in detail["nodes"] if node["title"] == "試作工單")
    blocked = client.patch(f"/nodes/{later_task['id']}/status", json={"status": "doing", "override": True})
    assert blocked.status_code in {409, 422}
    clean_blocked = client.patch(f"/nodes/{later_task['id']}/status", json={"status": "doing"})
    assert clean_blocked.status_code == 409
    assert clean_blocked.json() == {"detail": "前一階段閘門尚未通過"}


def test_gate_approval_allows_later_stage_for_authorized_user(client):
    login(client, "food", "yu")
    workflow_id = client.get("/workflows").json()["items"][0]["id"]
    project = client.post("/projects/from-workflow", json={"workflow_id": workflow_id, "title": "Gate核准"}).json()
    detail = client.get(f"/projects/{project['id']}").json()
    gate = detail["gates"][0]
    assert client.patch(f"/gates/{gate['id']}", json={"status": "approved"}).status_code == 200
    later_task = next(node for node in client.get(f"/projects/{project['id']}").json()["nodes"] if node["title"] == "試作工單")
    ok = client.patch(f"/nodes/{later_task['id']}/status", json={"status": "doing"})
    assert ok.status_code == 200
```

Run:

```powershell
api/.venv/Scripts/python.exe -m pytest -c api/pyproject.toml api/tests/test_workflows_gates.py -q
```

Expected RED: routes/gate enforcement missing. Record output.

- [ ] **Step 2: Implement workflow routes and seed templates.**

Seed workflows with ordered template nodes:

Food workflow `食品新品開發`:

1. phase `市場與配方`
2. phase `小量試作`, gated by previous phase
3. task `配方設計` under phase 1
4. task `試作工單` under phase 2

Electronics workflow `電子新品開發`:

1. phase `規格確認`
2. phase `試產驗證`, gated by previous phase
3. task `端子規格審查`
4. task `小量試產`

`GET /workflows` scopes by session organization.

`POST /projects/from-workflow` loads workflow by `(organization_id, id)`, requires admin/project owner role, creates a new project, nodes and pending gates in one transaction, and writes `workflow.instantiate` audit.

- [ ] **Step 3: Enforce gates in status changes.**

Add `blocked_by_pending_gate(db, current, node)`. For P1a, a node is blocked when its phase has a lower-sort sibling phase in the same project with a pending gate and the target status would move from `todo` to `doing`, `review`, `done` or `skipped`.

In `PATCH /nodes/{node_id}/status`, after `can_work_node` succeeds, call the gate helper. Return `409 {"detail":"前一階段閘門尚未通過"}` before changing status. Unknown override payload keys must be rejected by schema before route logic.

`PATCH /gates/{gate_id}` loads by session organization and allows only `admin`, project owner, or reviewer in the same organization. Write `gate.approve` audit.

- [ ] **Step 4: GREEN and commit.**

Run:

```powershell
api/.venv/Scripts/python.exe -m pytest -c api/pyproject.toml api/tests/test_workflows_gates.py -q
api/.venv/Scripts/python.exe -m pytest -c api/pyproject.toml api/tests -q
```

Update docs with workflow/gate endpoint examples. Commit:

```bash
git commit -m "P1a task 3: add workflows and gate enforcement"
```

Independent review, fixes if needed, then `Progress: P1a task 3 done`.

## Task 4: Reports, Audit API And Real PostgreSQL Acceptance

**Files:**
- Modify: `api/app/main.py`, `api/app/models.py`, `api/app/schemas.py`, `api/app/permissions.py`, `api/app/audit.py`, `api/app/seed.py`, `api/alembic/versions/20261008_0001_p1a_core.py`, `docs/formal-development.md`, README, PROGRESS.
- Create: `api/app/routes/reports.py`, `api/app/routes/audit_logs.py`, `api/tests/test_reports_audit.py`.

**Interfaces:**
- Produces: `POST /nodes/{node_id}/reports`.
- Produces: `GET /audit-logs`.
- Produces: Compose/PostgreSQL migration and seed acceptance commands.

- [ ] **Step 1: Write failing report/audit tests.**

Create `api/tests/test_reports_audit.py`:

```python
def login(client, org="food", username="yu", password=None):
    response = client.post("/auth/login", json={
        "organization_key": org,
        "username": username,
        "password": password or f"demo-{username}",
    })
    assert response.status_code == 200


def first_owned_node(client):
    project = client.get("/projects").json()["items"][0]
    nodes = client.get(f"/projects/{project['id']}").json()["nodes"]
    return nodes[0]


def test_submit_report_requires_can_work_and_writes_audit(client):
    login(client, "food", "ming", "demo-ming")
    node = first_owned_node(client)
    response = client.post(f"/nodes/{node['id']}/reports", json={"result": "達成", "summary": "已完成測試"})
    assert response.status_code == 201
    assert response.json()["status"] == "submitted"
    logs = client.get("/audit-logs").json()["items"]
    assert logs[0]["action"] == "report.submit"
    assert logs[0]["node_id"] == node["id"]


def test_readonly_cannot_submit_report(client):
    login(client, "food", "lin", "demo-lin")
    project = client.get("/projects").json()["items"][0]
    node = client.get(f"/projects/{project['id']}").json()["nodes"][0]
    response = client.post(f"/nodes/{node['id']}/reports", json={"result": "達成", "summary": "不應成功"})
    assert response.status_code == 403


def test_audit_logs_are_scoped_to_session_organization(client):
    login(client, "electronics", "elaine", "demo-elaine")
    electronics_project = client.post("/projects", json={"title": "電子稽核"}).json()
    assert electronics_project["title"] == "電子稽核"
    client.post("/auth/logout")
    login(client, "food", "yu")
    logs = client.get("/audit-logs").json()["items"]
    assert all(item["organization_key"] == "food" for item in logs)
    assert "電子稽核" not in str(logs)


def test_cross_company_node_cannot_receive_report(client):
    login(client, "electronics", "elaine", "demo-elaine")
    other_project = client.get("/projects").json()["items"][0]
    other_node = client.get(f"/projects/{other_project['id']}").json()["nodes"][0]
    client.post("/auth/logout")
    login(client, "food", "yu")
    response = client.post(f"/nodes/{other_node['id']}/reports", json={"result": "達成", "summary": "偷寫"})
    assert response.status_code == 404
```

Run:

```powershell
api/.venv/Scripts/python.exe -m pytest -c api/pyproject.toml api/tests/test_reports_audit.py -q
```

Expected RED: routes missing. Record output.

- [ ] **Step 2: Implement report and audit routes.**

`POST /nodes/{node_id}/reports`:

- Load node by `(organization_id, id)`; return 404 if absent.
- Require `can_work_node`.
- Accept only `result` and `summary`, both non-empty strings. Reject unknown keys.
- Insert `TaskReport` with `status="submitted"`.
- Insert `report.submit` audit in same transaction.
- Return 201 report response.

`GET /audit-logs`:

- Require session.
- Return newest 50 rows filtered by `current.organization.id`.
- Include `organization_key`, `action`, `node_id`, `actor_username`, `payload`, `created_at`.
- Do not accept `organization_id` or `organization_key` query parameters in P1a; if present, ignore them and still use session scope.

- [ ] **Step 3: GREEN all API tests and migration on real PostgreSQL.**

Run all API tests:

```powershell
api/.venv/Scripts/python.exe -m pytest -c api/pyproject.toml api/tests -q
```

Expected GREEN: P0 health tests plus P1a tests all pass.

Start real Compose if not already running, preserving volume:

```powershell
docker compose --env-file deploy/.env -f deploy/docker-compose.yml up -d --build --wait
api/.venv/Scripts/python.exe -m alembic -c api/alembic.ini upgrade head
```

Add a small command or module entry point in `api/app/seed.py`:

```python
if __name__ == "__main__":
    from app.database import get_engine
    from sqlalchemy.orm import Session
    with Session(get_engine()) as session:
        seed_demo_data(session)
        session.commit()
```

Because the P0 Compose file intentionally does not expose PostgreSQL to the host, run the seed command inside the API container:

```powershell
docker compose --env-file deploy/.env -f deploy/docker-compose.yml exec api python -m app.seed
```

Then verify through HTTP without printing secrets or cookie values:

```powershell
$apiPort = ((Get-Content deploy/.env | Where-Object { $_ -match '^API_PORT=' }) -split '=',2)[1]
if (-not $apiPort) { $apiPort = '18000' }
$base = "http://127.0.0.1:$apiPort"
$login = Invoke-WebRequest -Uri "$base/auth/login" -Method Post -ContentType 'application/json' -Body '{"organization_key":"food","username":"yu","password":"demo-yu"}' -SessionVariable pf
Invoke-WebRequest -Uri "$base/auth/me" -WebSession $pf
Invoke-WebRequest -Uri "$base/projects" -WebSession $pf
```

Record status codes and key response shapes, not `Set-Cookie` values.

- [ ] **Step 4: Full formal regression and docs.**

Run:

```powershell
api/.venv/Scripts/python.exe -m pytest -c api/pyproject.toml api/tests -q
npm.cmd --prefix web test
npm.cmd --prefix web run build
npm.cmd --prefix web run e2e
```

Expected GREEN: all API tests, React tests, build and health E2E pass. P1a changed backend routes, but the P0 health UI must remain usable.

Update `docs/formal-development.md` with:

- Migration command.
- Seed command.
- Demo login table.
- Auth cookie behavior.
- P1a endpoint list.
- Warning that P1b UI does not yet expose these business APIs.

Update README current progress: P1a backend plan/execution status, API business endpoints available after migration/seed, P1b still next.

- [ ] **Step 5: Review, commit and G4/G5/G6.**

Run:

```powershell
git diff --check
git status --short
git diff main --exit-code -- projectflow-full-demo.html projectflow-petfood-demo.html tests
git check-ignore deploy/.env api/.venv web/node_modules
```

Stage explicit Task 4 files. Commit:

```bash
git commit -m "P1a task 4: add reports audit and database acceptance"
```

Independent Task review, fixes if needed, then `Progress: P1a task 4 done`.

Run G4 whole-branch review against this plan and the Formal Product MVP spec. Fix blockers with tests and fresh GREEN. If ready, perform G5 ff-only merge and G6 stage completion under D50: update README and PROGRESS summary, delete the merged feature branch, push `origin main`, and verify remote HEAD. Preserve the healthy P0/P1a Compose stack for the user unless it was started solely for a temporary test and the user asks to stop it.

## Completion And Next Stage

P1a is complete only when all of these are true:

- Auth/session endpoints pass tests and reject forged organization context.
- Alembic migration creates organization-scoped core tables in PostgreSQL.
- Seed data creates at least two organizations with distinct users, departments, projects, nodes and workflows.
- Project, node, department, workflow, gate, report and audit APIs enforce session organization and route-level permission checks.
- Cross-company ID, workflow, node, report and audit leakage tests pass.
- Gate bypass regression passes.
- Full formal regression passes: API pytest, React Vitest, build and P0 health E2E.
- README, formal development docs and PROGRESS are updated and reviewed.

After P1a: P1b connects React login, project list/detail, kanban status updates, workflow creation and gate banners to these real APIs. P1c then packages deployment/testing/MVP acceptance. Do not declare P1c complete from backend tests alone.

## Self-Review

- Spec coverage: P1a migration, models, core CRUD APIs, seed data, `can_view`/`can_work`, login/session and company boundary tests are mapped to Tasks 1-4.
- Placeholder scan: no `TBD`, `TODO` or "add tests for the above" remains; each task names files, interfaces, commands and expected RED/GREEN.
- Type consistency: route names, cookie name, session dependency, organization key and status values are consistent across tasks.
- Review Focus coverage: each of the five risk classes is pinned by tests in Tasks 1-4.
- Scope check: React business UI, real ERP, AD/LDAP, file storage, AI/RAG and full attachment handling are intentionally left to later phases.
