# Formal Product MVP Implementation Plan

> **狀態：路線圖草稿，不可直接執行。** D51已授權正式版做到P1c；下列Task 1–4保留原分期提案。P0 Task 1由[2026-10-08 P0可執行計畫](2026-10-08-p0-formal-foundation.md)取代，該新計畫仍需審閱；P1a–P1c在各階段前細化。不要用本草稿代替TDD計畫，也不要把計畫發布視為實作完成。

> **For agentic workers (after approval and refinement):** Use superpowers:subagent-driven-development or superpowers:executing-plans as selected by the user. Track progress only in `docs/PROGRESS.md`; do not check off steps in this document.

**Goal:** Build the first formal ProjectFlow MVP from the completed single-file Demo, using P0 in 1–2 days and a React + FastAPI + PostgreSQL base in 1–2 weeks.

**Architecture:** Keep the Demo as the behavioral reference and introduce a new formal product structure beside it: `web/`, `api/`, and `deploy/`. Move behavior in vertical slices so each phase has a runnable product and a testable acceptance path.

**Tech Stack:** Vite, React, TypeScript, FastAPI, PostgreSQL, Docker Compose, pytest, Playwright or equivalent browser smoke tests.

**Spec:** `docs/superpowers/specs/2026-10-05-formal-product-mvp-design.md`

## Global Constraints

- Do not modify `projectflow-petfood-demo.html`.
- Keep `projectflow-full-demo.html` as the behavioral reference until the formal MVP reaches feature parity for the selected flow.
- Interface text remains Traditional Chinese.
- Formal backend authorization must be enforced on the API, not only hidden in the UI.
- P0/P1 excludes real ERP, real AD/LDAP, real AI/RAG, and production file-version editing.
- Each task must leave a runnable state and document the exact test command.
- Use the W6 v6 Demo and its 174-test baseline as the behavioral reference. Do not replace the current README or PROGRESS with versions from the paused branch.
- Preserve the approved W6 company boundary requirement: organization-scoped models, server-side API/query/authorization checks, and organization-scoped file storage when introduced. Frontend company switching alone is not authorization; Demo IDs must not be assumed globally unique.
- D51 authorizes implementation through P1c; dependencies, new formal directories and rule changes must follow each reviewed executable plan, not this outline. D50 authorizes pushing completed, reviewed stages to GitHub main after updating README and PROGRESS; no force push or automatic PR.

## Before Implementation

This restored document is a phase outline, not an execution-ready plan. Before P0 implementation:

1. D51 has confirmed the MVP scope and authorized implementation through P1c. Do not ask again whether to start the formal track; review the new executable plan before its product changes.
2. Define the P0 rules transition in AGENTS/WORKFLOW/PROGRESS, allowed paths, dependency choices, and verification commands; keep Demo rules active until that transition is approved.
3. Expand Task 1 into a complete P0 plan: dependency manifests and lockfile policy, Vite entry/config files, API package layout, Dockerfiles/Compose/environment settings, health request wiring, test configuration, exact RED/GREEN tests, and PowerShell-compatible commands from a stated working directory. The current JSX is only an example and does not fulfill the API health-call interface.
4. Before P1a execution, specify trusted company context, organization-scoped keys/relationships and authorization tests for cross-company reads/writes, workflow creation, and audit access. Plan file isolation alongside the future file API. Do not copy the Demo company selector into authentication.
5. Review the resulting executable plan. Task 2–4 below remain later-phase outlines and are not included in permission to execute P0.

## Review Focus

- Gate bypass: a generic override or direct API call must not start a later-stage task while a workflow gate is pending.
- Role visibility: a user must not read tasks outside their assigned or supervisor scope through API responses.
- Company isolation: a forged company parameter or another company's record ID must not permit reads/writes, workflow instantiation or audit access; file APIs must apply the same boundary when implemented. Task 2 owns backend checks and Task 4 integration acceptance after their plans are refined.
- Data migration from Demo concepts: nodes, departments, workflows, and reports must keep stable IDs and parent relationships.
- Fresh setup: a new machine must start the MVP using documented commands without relying on local browser state.
- UI/API mismatch: every disabled or hidden UI action must have a matching backend permission check.

---

## Timeline Summary

| Phase | Duration | Outcome |
|---|---:|---|
| P0 | 1–2 days | Formal product skeleton, rules, local dev stack |
| P1a | 2–4 days | PostgreSQL schema and FastAPI core APIs |
| P1b | 3–5 days | React UI for core ProjectFlow workflow |
| P1c | 2–3 days | Docker Compose, tests, docs, MVP acceptance |

Total target: 1–2 weeks for a formal base MVP after P0 is accepted.

---

### Task 1: P0 Repository Skeleton And Dev Stack

**Files:**
- Create: `web/package.json`
- Create: `web/src/App.tsx`
- Create: `web/src/main.tsx`
- Create: `api/pyproject.toml`
- Create: `api/app/main.py`
- Create: `deploy/docker-compose.yml`
- Modify: `README.md`

**Interfaces:**
- Produces: `GET /health` returning `{ "ok": true }`.
- Produces: React app shell that can call the API health endpoint.
- Produces: Docker Compose service names `web`, `api`, `db`.

- [ ] **Step 1: Create a branch for P0 implementation**

Only after the planning and authorization gates above. Verify a clean checkout and PROGRESS first; record the start on main and create the branch in the main checkout under WORKFLOW G3. No worktree, pull, rebase, push or non-fast-forward merge.

```bash
git checkout main
git status --short
git checkout -b feature/p0-formal-skeleton
```

- [ ] **Step 2: Create the minimal API health test**

Create `api/tests/test_health.py`:

```python
from fastapi.testclient import TestClient
from app.main import app


def test_health_returns_ok():
    client = TestClient(app)
    assert client.get("/health").json() == {"ok": True}
```

- [ ] **Step 3: Run test to verify it fails before the API exists**

Run: `cd api && pytest tests/test_health.py -q`

Expected: fail because `app.main` does not exist.

- [ ] **Step 4: Implement the minimal API**

Create `api/app/main.py`:

```python
from fastapi import FastAPI

app = FastAPI(title="ProjectFlow API")


@app.get("/health")
def health():
    return {"ok": True}
```

- [ ] **Step 5: Add minimal React shell**

Create `web/src/App.tsx`:

```tsx
export default function App() {
  return (
    <main>
      <h1>專流 ProjectFlow</h1>
      <p>正式版骨架已啟動。</p>
    </main>
  );
}
```

- [ ] **Step 6: Add Docker Compose**

Create `deploy/docker-compose.yml` with `web`, `api`, and `db` services. The API service exposes port `8000`, the web service exposes port `5173`, and PostgreSQL uses database name `projectflow`.

- [ ] **Step 7: Run verification**

Run:

```bash
cd api && pytest -q
cd ../web && npm test -- --run
docker compose -f deploy/docker-compose.yml config
```

Expected: all commands pass.

- [ ] **Step 8: Commit**

```bash
git add web/package.json web/src/App.tsx web/src/main.tsx api/pyproject.toml api/app/main.py api/tests/test_health.py deploy/docker-compose.yml README.md
git commit -m "P0: add formal product skeleton"
```

---

### Task 2: P1a Core Data Model And API

**Files:**
- Create: `api/app/models.py`
- Create: `api/app/schemas.py`
- Create: `api/app/db.py`
- Create: `api/app/routes/projects.py`
- Create: `api/app/routes/workflows.py`
- Test: `api/tests/test_projects.py`
- Test: `api/tests/test_workflows.py`

**Interfaces:**
- Produces: `GET /projects`, `POST /projects`, `GET /projects/{id}`.
- Produces: `GET /workflows`, `POST /projects/from-workflow`.
- Produces: database tables for users, departments, projects, nodes, workflows, gates, reports, and audit logs, with company boundaries as required by the spec. Exact keys and trusted identity contract must be settled in the executable P1a plan.

- [ ] **Step 1: Write failing project API test**

Create `api/tests/test_projects.py`:

```python
def test_create_project_returns_project(client):
    res = client.post("/projects", json={"name": "連接器新產品", "owner_id": "yu"})
    assert res.status_code == 201
    assert res.json()["name"] == "連接器新產品"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd api && pytest tests/test_projects.py -q`

Expected: fail with route not found.

- [ ] **Step 3: Implement project models and routes**

Implement project persistence with PostgreSQL-backed models and route handlers. `Project` must include `id`, `name`, `owner_id`, `created_at`, and `updated_at`.

- [ ] **Step 4: Add workflow seed and from-workflow API**

Create a seed workflow matching the Demo concept: stages, tasks, departments, and gates. `POST /projects/from-workflow` must create project nodes and gate records from the workflow template.

- [ ] **Step 5: Add gate bypass regression test**

Add a test where a later-stage task cannot start while the previous stage gate is pending, even if the caller attempts a generic override payload.

- [ ] **Step 6: Run verification**

Run:

```bash
cd api && pytest tests/test_projects.py tests/test_workflows.py -q
```

Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add api/app api/tests
git commit -m "P1a: add core ProjectFlow data model and APIs"
```

---

### Task 3: P1b React Core Workflow UI

**Files:**
- Create: `web/src/api/client.ts`
- Create: `web/src/pages/ProjectsPage.tsx`
- Create: `web/src/pages/ProjectDetailPage.tsx`
- Create: `web/src/pages/WorkflowLibraryPage.tsx`
- Create: `web/src/components/KanbanBoard.tsx`
- Create: `web/src/components/GateBanner.tsx`
- Test: `web/src/__tests__/project-flow.test.tsx`

**Interfaces:**
- Consumes: API endpoints from Task 2.
- Produces: a user can list projects, open a project, see nodes, move a task status, and create a project from a workflow.

- [ ] **Step 1: Write failing UI smoke test**

Create `web/src/__tests__/project-flow.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import App from "../App";

test("shows ProjectFlow project list entry", async () => {
  render(<App />);
  expect(await screen.findByText("專流 ProjectFlow")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails if the shell is not wired**

Run: `cd web && npm test -- --run`

Expected: fail until the App renders the formal shell with routes.

- [ ] **Step 3: Implement API client and pages**

Implement a small API client with typed methods:

```ts
export async function listProjects(): Promise<ProjectSummary[]>;
export async function getProject(id: string): Promise<ProjectDetail>;
export async function createProjectFromWorkflow(workflowId: string): Promise<ProjectDetail>;
```

- [ ] **Step 4: Implement core UI routes**

Routes:

- `/projects`
- `/projects/:projectId`
- `/workflows`

The project detail page must show a simple board and a gate banner when a later-stage task is blocked.

- [ ] **Step 5: Run verification**

Run:

```bash
cd web && npm test -- --run
cd ../api && pytest -q
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add web/src
git commit -m "P1b: add React core ProjectFlow workflow UI"
```

---

### Task 4: P1c Deployment, Permission Tests, And MVP Acceptance

**Files:**
- Modify: `deploy/docker-compose.yml`
- Create: `api/tests/test_permissions.py`
- Create: `tests/formal-mvp-acceptance.md`
- Modify: `README.md`
- Modify: `docs/PROGRESS.md`

**Interfaces:**
- Consumes: API and UI from previous tasks.
- Produces: documented acceptance flow for yu, chen, and ming.

- [ ] **Step 1: Write failing permission tests**

Create `api/tests/test_permissions.py`:

```python
def test_user_cannot_read_unrelated_task(client, seeded_db):
    res = client.get("/nodes/t-unrelated", headers={"X-User": "ming"})
    assert res.status_code == 403


def test_gate_blocks_later_stage_status_change(client, seeded_db):
    res = client.patch(
        "/nodes/t-stage2/status",
        headers={"X-User": "yu"},
        json={"status": "doing"},
    )
    assert res.status_code == 409
    assert "gate" in res.json()["error"]
```

- [ ] **Step 2: Run test to verify it fails before permission middleware exists**

Run: `cd api && pytest tests/test_permissions.py -q`

Expected: fail until permission and gate checks are implemented server-side.

- [ ] **Step 3: Implement permission middleware and route checks**

Every read and write route for nodes must call backend permission helpers, not only rely on the UI.

- [ ] **Step 4: Document MVP acceptance**

Create `tests/formal-mvp-acceptance.md` with this acceptance path:

1. Start Docker Compose.
2. Log in or switch role as `yu`.
3. Create a project from a workflow.
4. Confirm a later-stage task is blocked by gate.
5. Switch to `chen` and confirm visibility differs.
6. Switch to `ming` and confirm unrelated tasks are hidden.
7. Export or inspect audit logs for the attempted blocked action.

- [ ] **Step 5: Run full verification**

Run:

```bash
docker compose -f deploy/docker-compose.yml up -d --build
cd api && pytest -q
cd ../web && npm test -- --run
docker compose -f ../deploy/docker-compose.yml down
```

Expected: all pass; compose starts and stops cleanly.

- [ ] **Step 6: Commit**

```bash
git add deploy/docker-compose.yml api/tests/test_permissions.py tests/formal-mvp-acceptance.md README.md docs/PROGRESS.md
git commit -m "P1c: document and verify formal MVP acceptance"
```

---

## Self-Review

**Spec coverage:** P0 covers skeleton and rules; P1a covers backend data model and APIs; P1b covers React core UI; P1c covers deployment, tests, and MVP acceptance. AI/RAG/ERP/AD are explicitly out of scope for P0/P1 MVP.

**Execution readiness:** Not ready. The restored phase outline omits dependency/bootstrap files, concrete Compose configuration, full test code and several API types/fixtures. The prerequisites above are required before execution; the original assertion that nothing blocked execution is withdrawn.

**Type consistency:** Endpoint names are retained as proposals; complete request/response types, test fixtures and organization-scoped identity contracts are not yet defined.

**Review Focus ownership:** Gate bypass, role/company isolation and UI/API authorization belong to Tasks 2 and 4; fresh setup to Tasks 1 and 4; migration identity/relationships to Task 2. These are coverage requirements, not claims of implemented or executed tests.
