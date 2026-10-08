# P1b React Core UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` for Native execution. Independent Task reviews are required by this repository. Steps use checkbox (`- [ ]`) syntax for tracking, but do not check off this file; `docs/PROGRESS.md` is the only execution ledger.
> **Gate:** D51 authorizes delivery through P1c. This P1b plan connects the React frontend to the P1a backend APIs; P1c owns final deployment and internal trial acceptance.

**Goal:** Replace the P0 health-only React surface with a usable MVP workflow UI: login, project list/detail, node tree, kanban status updates, workflow project creation and gate blocking feedback.

**Architecture:** Keep the existing Vite/React app and add a small typed API client plus focused React components under `web/src/`. The frontend never stores or sends organization IDs after login; it relies on the HttpOnly `pf_session` cookie and backend scoping. P1b consumes existing P1a routes and only changes backend code when the UI reveals a missing response field needed for a listed screen.

**Tech Stack:** React 19.3, TypeScript 7.0, Vite 8.3, Vitest 5, Testing Library, Playwright, FastAPI P1a API.

**Spec:** [Formal Product MVP, P1b subsection](../specs/2026-10-05-formal-product-mvp-design.md). Backend authorization and company boundary behavior come from [P1a plan](2026-10-08-p1a-backend-core.md).

## Global Constraints

- Scope is P1b only. Do not implement P1c deployment acceptance scripts, real ERP, AD/LDAP, AI/RAG, attachment storage or full document handling.
- Do not modify `projectflow-full-demo.html`, `projectflow-petfood-demo.html`, `tests/records.html` or `tests/*.test.js`. Demo baseline remains v6 / 174 tests.
- Only files listed in this plan may be created or edited. Generated `web/dist`, `web/test-results`, `.venv`, logs, local `.env` and dependency folders are never committed.
- No new frontend runtime or test dependencies unless this plan is revised. Use existing React, Vitest, Testing Library and Playwright packages.
- Visible UI text must be Traditional Chinese and match ProjectFlow tone. Do not expose backend exception text, passwords, session tokens, cookies, DSNs or secrets in the browser.
- React must use normal JSX escaping. Do not use `dangerouslySetInnerHTML` for user or API data.
- Login posts `organization_key`, `username`, `password` once to `/api/auth/login`; later requests use `credentials: "include"` and never send frontend-forged organization context.
- API errors shown to users must be short Traditional Chinese messages. Console noise is a test failure for UI flows.
- Follow WORKFLOW §3 RED -> GREEN -> independent review -> PROGRESS commit. Formal tests record Vitest/Playwright/build summaries and exit codes; never mark tests passed without running them.
- Main checkout only; one `feature/*` branch at a time. No worktrees, pull, rebase, force, hard reset, destructive volume deletion, or `down -v`. Stage explicit paths only.
- P1b completion updates README and PROGRESS, gets reviewed and ff-only merged, then `git push origin main` under D50.

## Review Focus

1. Session and organization trust: after login, UI requests must use cookies only and must not include organization IDs in project, node, workflow or gate payloads. Task 1 pins this.
2. Auth failure recovery: expired sessions and failed logins must return to the login screen without leaking raw backend details. Tasks 1 and 2 pin this.
3. Gate blocking clarity: when a later-stage task is blocked by a pending gate, the kanban must keep the old status and show the gate message. Task 3 pins this.
4. Cross-role behavior: admin/project owner can create projects and update permitted nodes; readonly sees projects but cannot mutate. Tasks 2 and 3 pin this.
5. Responsive workflow use: desktop and 375px screens must show login, project detail and kanban without horizontal overflow or overlapping controls. Task 4 pins this with Playwright.

## File Structure

```text
web/src/api.ts
web/src/types.ts
web/src/App.tsx
web/src/App.test.tsx
web/src/styles.css
web/e2e/health.spec.ts
README.md
docs/formal-development.md
docs/PROGRESS.md
```

## Data Contract

P1b consumes P1a responses as JSON. Types are defined in `web/src/types.ts`:

```ts
export type Role = 'admin' | 'project_owner' | 'reviewer' | 'member' | 'readonly';
export type NodeStatus = 'todo' | 'doing' | 'review' | 'done' | 'skipped';

export interface User { id: string; username: string; display_name: string; role: Role | string; }
export interface Organization { id: string; key: string; name: string; }
export interface SessionInfo { user: User; organization: Organization; }
export interface ProjectSummary { id: string; title: string; organization_key: string; owner_user_id: string | null; }
export interface NodeItem {
  id: string;
  project_id: string;
  parent_id: string | null;
  kind: 'project' | 'phase' | 'task' | string;
  title: string;
  status: NodeStatus;
  owner_user_id: string | null;
  department_id: string | null;
  sort_order: number;
}
export interface GateItem { id: string; project_id: string; node_id: string; status: 'pending' | 'approved'; }
export interface ProjectDetail extends ProjectSummary { nodes: NodeItem[]; gates: GateItem[]; }
export interface WorkflowSummary { id: string; name: string; }
```

## Task 1: API Client And Login Session UI

**Files:**
- Create: `web/src/api.ts`, `web/src/types.ts`.
- Modify: `web/src/App.tsx`, `web/src/App.test.tsx`, `web/src/styles.css`, `README.md`, `docs/formal-development.md`, `docs/PROGRESS.md`.

**Interfaces:**
- Produces: `requestJson<T>(path: string, init?: RequestInit): Promise<T>`.
- Produces: `api.login(payload)`, `api.logout()`, `api.me()`.
- Produces: App states `checking-session`, `login`, `loading`, `ready`, `error`.

- [ ] **Step 1: Pre-flight and start branch.**

Run G3 pre-flight from `main`: verify clean worktree, no active `feature/*`, and P1a formal tests match the PROGRESS baseline.

```powershell
git rev-parse HEAD
git status --short
git branch --list "feature/*"
api/.venv/Scripts/python.exe -m pytest -c api/pyproject.toml api/tests -q
npm.cmd --prefix web test
npm.cmd --prefix web run build
npm.cmd --prefix web run e2e
```

Expected baseline before product edits: API `35 passed`, React `6 passed`, E2E `4 passed`, build exit 0. Record exact output in PROGRESS. Commit `Progress: start P1b`, then `git checkout -b feature/p1b-react-core-ui`.

- [ ] **Step 2: Write failing client and login tests.**

Replace `web/src/App.test.tsx` with tests that prove the health-only shell is gone and login uses cookies without forged organization context:

```tsx
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import App from './App';

const session = {
  user: { id: 'u-yu', username: 'yu', display_name: '游專案', role: 'admin' },
  organization: { id: 'org-food', key: 'food', name: '毛研食品' },
};

const projects = { items: [{ id: 'p1', title: '成貓主食罐正式版', organization_key: 'food', owner_user_id: 'u-yu' }] };
const detail = {
  ...projects.items[0],
  nodes: [{ id: 'n1', project_id: 'p1', parent_id: null, kind: 'task', title: '殺菌條件驗證', status: 'todo', owner_user_id: 'u-ming', department_id: 'd-qa', sort_order: 10 }],
  gates: [],
};

describe('P1b session UI', () => {
  it('shows login when there is no active session', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce({ ok: false, status: 401, json: async () => ({ detail: '請先登入' }) }));
    render(<App />);
    expect(await screen.findByRole('heading', { name: '登入專流' })).toBeInTheDocument();
    expect(screen.getByLabelText('公司')).toHaveValue('food');
  });

  it('logs in with credentials and then loads projects', async () => {
    const fetcher = vi.fn()
      .mockResolvedValueOnce({ ok: false, status: 401, json: async () => ({ detail: '請先登入' }) })
      .mockResolvedValueOnce({ ok: true, json: async () => session })
      .mockResolvedValueOnce({ ok: true, json: async () => projects })
      .mockResolvedValueOnce({ ok: true, json: async () => detail });
    vi.stubGlobal('fetch', fetcher);
    render(<App />);
    fireEvent.change(await screen.findByLabelText('帳號'), { target: { value: 'yu' } });
    fireEvent.change(screen.getByLabelText('密碼'), { target: { value: 'demo-yu' } });
    fireEvent.click(screen.getByRole('button', { name: '登入' }));
    expect(await screen.findByText('成貓主食罐正式版')).toBeInTheDocument();
    expect(fetcher).toHaveBeenCalledWith('/api/auth/login', expect.objectContaining({
      credentials: 'include',
      method: 'POST',
      body: JSON.stringify({ organization_key: 'food', username: 'yu', password: 'demo-yu' }),
    }));
    expect(String(fetcher.mock.calls[2][1]?.body ?? '')).not.toContain('organization');
  });

  it('shows a safe message for failed login', async () => {
    vi.stubGlobal('fetch', vi.fn()
      .mockResolvedValueOnce({ ok: false, status: 401, json: async () => ({ detail: '請先登入' }) })
      .mockResolvedValueOnce({ ok: false, status: 401, json: async () => ({ detail: '帳號或密碼錯誤' }) }));
    render(<App />);
    fireEvent.change(await screen.findByLabelText('帳號'), { target: { value: 'yu' } });
    fireEvent.change(screen.getByLabelText('密碼'), { target: { value: 'wrong' } });
    fireEvent.click(screen.getByRole('button', { name: '登入' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('帳號或密碼錯誤');
    expect(screen.queryByText('wrong')).not.toBeInTheDocument();
  });
});
```

Run:

```powershell
npm.cmd --prefix web test -- App.test.tsx
```

Expected RED: tests fail because `web/src/api.ts` is missing and `App` still renders the health surface. Record summary and exit code.

- [ ] **Step 3: Implement API client and login shell.**

Create `web/src/types.ts` with the data contract above.

Create `web/src/api.ts`:

```ts
import type { ProjectDetail, ProjectSummary, SessionInfo, WorkflowSummary, NodeStatus } from './types';

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export async function requestJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...init,
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(init.headers ?? {}) },
  });
  if (response.status === 204) return undefined as T;
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new ApiError(response.status, typeof body.detail === 'string' ? body.detail : '操作失敗');
  return body as T;
}

export const api = {
  me: () => requestJson<SessionInfo>('/auth/me'),
  login: (payload: { organization_key: string; username: string; password: string }) =>
    requestJson<SessionInfo>('/auth/login', { method: 'POST', body: JSON.stringify(payload) }),
  logout: () => requestJson<void>('/auth/logout', { method: 'POST' }),
  projects: () => requestJson<{ items: ProjectSummary[] }>('/projects'),
  project: (id: string) => requestJson<ProjectDetail>(`/projects/${id}`),
  updateNodeStatus: (id: string, status: NodeStatus) =>
    requestJson('/nodes/' + id + '/status', { method: 'PATCH', body: JSON.stringify({ status }) }),
  workflows: () => requestJson<{ items: WorkflowSummary[] }>('/workflows'),
  createFromWorkflow: (payload: { workflow_id: string; title: string }) =>
    requestJson<ProjectSummary>('/projects/from-workflow', { method: 'POST', body: JSON.stringify(payload) }),
  approveGate: (id: string) => requestJson('/gates/' + id, { method: 'PATCH', body: JSON.stringify({ status: 'approved' }) }),
};
```

Modify `App.tsx` to:

- Call `api.me()` on mount.
- Show login form on 401.
- On successful login, call `api.projects()` and select the first project.
- Keep the existing `/api/health/ready` behavior out of P1b main UI; P1c can expose deeper health checks elsewhere.
- Use labels `公司`, `帳號`, `密碼`, `登入`, `登出`, `目前公司`, `專案`.

Update CSS to create a two-column app shell on desktop and a single-column shell below 720px. Use restrained colors, no hero, no nested cards, no horizontal overflow.

- [ ] **Step 4: GREEN and commit.**

Run:

```powershell
npm.cmd --prefix web test -- App.test.tsx
npm.cmd --prefix web run build
```

Expected GREEN: P1b login tests pass and build exits 0. Commit:

```bash
git add web/src/api.ts web/src/types.ts web/src/App.tsx web/src/App.test.tsx web/src/styles.css README.md docs/formal-development.md
git commit -m "P1b task 1: connect login session UI"
```

Independent review per WORKFLOW §4. Fix Critical/Important findings, then update PROGRESS and commit `Progress: P1b task 1 done`.

## Task 2: Project List, Detail, Tree And Breadcrumbs

**Files:**
- Modify: `web/src/App.tsx`, `web/src/App.test.tsx`, `web/src/styles.css`, `docs/formal-development.md`, `README.md`, `docs/PROGRESS.md`.

**Interfaces:**
- Consumes: `api.projects()`, `api.project(id)`.
- Produces: visible project list, project heading, breadcrumb path and node tree.

- [ ] **Step 1: Write failing project navigation tests.**

Append to `App.test.tsx`:

```tsx
describe('P1b project navigation', () => {
  it('loads the selected project and renders a tree with breadcrumbs', async () => {
    const detailWithTree = {
      ...detail,
      nodes: [
        { id: 'root', project_id: 'p1', parent_id: null, kind: 'project', title: '成貓主食罐正式版', status: 'todo', owner_user_id: 'u-yu', department_id: null, sort_order: 0 },
        { id: 'phase', project_id: 'p1', parent_id: 'root', kind: 'phase', title: '市場與配方', status: 'todo', owner_user_id: null, department_id: null, sort_order: 10 },
        { id: 'task', project_id: 'p1', parent_id: 'phase', kind: 'task', title: '殺菌條件驗證', status: 'todo', owner_user_id: 'u-ming', department_id: 'd-qa', sort_order: 20 },
      ],
      gates: [],
    };
    vi.stubGlobal('fetch', vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => session })
      .mockResolvedValueOnce({ ok: true, json: async () => projects })
      .mockResolvedValueOnce({ ok: true, json: async () => detailWithTree }));
    render(<App />);
    expect(await screen.findByRole('heading', { name: '成貓主食罐正式版' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '殺菌條件驗證' }));
    expect(screen.getByLabelText('節點路徑')).toHaveTextContent('成貓主食罐正式版 / 市場與配方 / 殺菌條件驗證');
    expect(within(screen.getByLabelText('節點樹')).getByText('市場與配方')).toBeInTheDocument();
  });

  it('returns to login when the session expires while loading projects', async () => {
    vi.stubGlobal('fetch', vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => session })
      .mockResolvedValueOnce({ ok: false, status: 401, json: async () => ({ detail: '請先登入' }) }));
    render(<App />);
    expect(await screen.findByRole('heading', { name: '登入專流' })).toBeInTheDocument();
  });
});
```

Run:

```powershell
npm.cmd --prefix web test -- App.test.tsx
```

Expected RED: project tree, node selection and breadcrumb are missing.

- [ ] **Step 2: Implement tree helpers and project detail view.**

Inside `App.tsx`, add pure helpers near the top:

```ts
function childrenOf(nodes: NodeItem[], parentId: string | null) {
  return nodes.filter(node => node.parent_id === parentId).sort((a, b) => a.sort_order - b.sort_order);
}

function pathFor(nodes: NodeItem[], selectedId: string | null) {
  const byId = new Map(nodes.map(node => [node.id, node]));
  const path: NodeItem[] = [];
  let current = selectedId ? byId.get(selectedId) : undefined;
  while (current) {
    path.unshift(current);
    current = current.parent_id ? byId.get(current.parent_id) : undefined;
  }
  return path;
}
```

Render:

- Sidebar `aria-label="專案清單"` with buttons for each project.
- Main heading with selected project title.
- `nav aria-label="節點路徑"` displaying joined path; default to the project root if no node selected.
- `section aria-label="節點樹"` with recursive node buttons. If there are no nodes, show `這個專案還沒有節點`.

On 401 from any loading call, clear session and show login. On other failures, show `無法載入專案資料`.

- [ ] **Step 3: GREEN and commit.**

Run:

```powershell
npm.cmd --prefix web test -- App.test.tsx
npm.cmd --prefix web run build
```

Commit:

```bash
git add web/src/App.tsx web/src/App.test.tsx web/src/styles.css README.md docs/formal-development.md
git commit -m "P1b task 2: add project detail tree navigation"
```

Independent review, fixes if needed, then `Progress: P1b task 2 done`.

## Task 3: Kanban Status Updates And Gate Feedback

**Files:**
- Modify: `web/src/App.tsx`, `web/src/App.test.tsx`, `web/src/styles.css`, `docs/formal-development.md`, `README.md`, `docs/PROGRESS.md`.

**Interfaces:**
- Consumes: `api.updateNodeStatus(id, status)`, `api.approveGate(id)`.
- Produces: four-column kanban, status update controls and pending gate banner.

- [ ] **Step 1: Write failing kanban and gate tests.**

Append to `App.test.tsx`:

```tsx
describe('P1b kanban and gates', () => {
  it('moves a task after a successful status update', async () => {
    const fetcher = vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => session })
      .mockResolvedValueOnce({ ok: true, json: async () => projects })
      .mockResolvedValueOnce({ ok: true, json: async () => detail })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ ...detail.nodes[0], status: 'doing' }) });
    vi.stubGlobal('fetch', fetcher);
    render(<App />);
    const task = await screen.findByText('殺菌條件驗證');
    fireEvent.click(task);
    fireEvent.click(screen.getByRole('button', { name: '移到進行中' }));
    await waitFor(() => expect(within(screen.getByLabelText('進行中')).getByText('殺菌條件驗證')).toBeInTheDocument());
    expect(fetcher).toHaveBeenLastCalledWith('/api/nodes/n1/status', expect.objectContaining({
      method: 'PATCH',
      body: JSON.stringify({ status: 'doing' }),
      credentials: 'include',
    }));
  });

  it('keeps the old column and shows gate message when blocked', async () => {
    vi.stubGlobal('fetch', vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => session })
      .mockResolvedValueOnce({ ok: true, json: async () => projects })
      .mockResolvedValueOnce({ ok: true, json: async () => detail })
      .mockResolvedValueOnce({ ok: false, status: 409, json: async () => ({ detail: '前一階段閘門尚未通過' }) }));
    render(<App />);
    fireEvent.click(await screen.findByText('殺菌條件驗證'));
    fireEvent.click(screen.getByRole('button', { name: '移到進行中' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('前一階段閘門尚未通過');
    expect(within(screen.getByLabelText('待處理')).getByText('殺菌條件驗證')).toBeInTheDocument();
  });
});
```

Run:

```powershell
npm.cmd --prefix web test -- App.test.tsx
```

Expected RED: kanban columns and move buttons do not exist.

- [ ] **Step 2: Implement kanban and gate controls.**

Render four stable columns:

```ts
const columns: { status: NodeStatus; label: string; moveLabel: string }[] = [
  { status: 'todo', label: '待處理', moveLabel: '移到待處理' },
  { status: 'doing', label: '進行中', moveLabel: '移到進行中' },
  { status: 'review', label: '待確認', moveLabel: '移到待確認' },
  { status: 'done', label: '完成', moveLabel: '移到完成' },
];
```

Only task nodes appear on the kanban. When a move succeeds, update local `project.nodes` with the returned status. When it fails, keep local state unchanged and show a role `alert`.

Gate banner:

- If `project.gates.some(gate => gate.status === 'pending')`, show `尚有階段閘門待核准，後續階段可能被阻擋`.
- For each pending gate, show a button `核准閘門`. On success, reload the current project.
- If gate approval returns 403, show `沒有核准此閘門的權限`.

- [ ] **Step 3: GREEN, full formal web regression and commit.**

Run:

```powershell
npm.cmd --prefix web test -- App.test.tsx
npm.cmd --prefix web run build
```

Commit:

```bash
git add web/src/App.tsx web/src/App.test.tsx web/src/styles.css README.md docs/formal-development.md
git commit -m "P1b task 3: add kanban gate workflow controls"
```

Independent review, fixes if needed, then `Progress: P1b task 3 done`.

## Task 4: Workflow Project Creation And Browser Smoke

**Files:**
- Modify: `web/src/App.tsx`, `web/src/App.test.tsx`, `web/src/styles.css`, `web/e2e/health.spec.ts`, `README.md`, `docs/formal-development.md`, `docs/PROGRESS.md`.

**Interfaces:**
- Consumes: `api.workflows()`, `api.createFromWorkflow(payload)`.
- Produces: workflow template list, create-project form, Playwright P1b smoke over real Compose stack.

- [ ] **Step 1: Write failing workflow creation tests.**

Append to `App.test.tsx`:

```tsx
describe('P1b workflow creation', () => {
  it('creates a project from a workflow without sending organization fields', async () => {
    const workflow = { items: [{ id: 'w1', name: '食品新品開發' }] };
    const newProject = { id: 'p2', title: '犬用鮮食上市', organization_key: 'food', owner_user_id: 'u-yu' };
    const fetcher = vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => session })
      .mockResolvedValueOnce({ ok: true, json: async () => projects })
      .mockResolvedValueOnce({ ok: true, json: async () => detail })
      .mockResolvedValueOnce({ ok: true, json: async () => workflow })
      .mockResolvedValueOnce({ ok: true, json: async () => newProject })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ items: [...projects.items, newProject] }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ ...newProject, nodes: [], gates: [] }) });
    vi.stubGlobal('fetch', fetcher);
    render(<App />);
    fireEvent.click(await screen.findByRole('button', { name: '新增專案' }));
    fireEvent.change(screen.getByLabelText('工作流模板'), { target: { value: 'w1' } });
    fireEvent.change(screen.getByLabelText('新專案名稱'), { target: { value: '犬用鮮食上市' } });
    fireEvent.click(screen.getByRole('button', { name: '建立專案' }));
    await waitFor(() => expect(fetcher).toHaveBeenCalledWith('/api/projects/from-workflow', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({ workflow_id: 'w1', title: '犬用鮮食上市' }),
    })));
    expect(screen.getByRole('heading', { name: '犬用鮮食上市' })).toBeInTheDocument();
  });
});
```

Run:

```powershell
npm.cmd --prefix web test -- App.test.tsx
```

Expected RED: workflow list and create form do not exist.

- [ ] **Step 2: Implement workflow creation UI.**

Add a toolbar button `新增專案`. On click:

- Load workflows with `api.workflows()` if not already loaded.
- Show an inline form, not a modal, with `工作流模板`, `新專案名稱`, `建立專案`, `取消`.
- Disable submit until both fields are non-empty.
- On success, reload project list, select the created project, load its detail and clear the form.
- On 403 show `沒有建立專案權限`; on 404 show `找不到工作流模板`.

- [ ] **Step 3: Update Playwright smoke for real P1b flow.**

Modify `web/e2e/health.spec.ts` to keep the P0 readiness assertion and add a P1b login/project smoke. The test must run against the Compose/Vite entry at `http://127.0.0.1:15173` and use the P1a seed account:

```ts
test('yu can log in and see the seeded project workflow', async ({ page }) => {
  await page.goto('/');
  await page.getByLabel('帳號').fill('yu');
  await page.getByLabel('密碼').fill('demo-yu');
  await page.getByRole('button', { name: '登入' }).click();
  await expect(page.getByRole('heading', { name: '成貓主食罐正式版' })).toBeVisible();
  await expect(page.getByLabel('專案清單')).toContainText('成貓主食罐正式版');
  await expect(page.getByLabel('待處理')).toContainText('殺菌條件驗證');
});
```

Also add a mobile viewport assertion in the same file:

```ts
test('P1b core UI has no horizontal overflow at 375px', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto('/');
  await page.getByLabel('帳號').fill('yu');
  await page.getByLabel('密碼').fill('demo-yu');
  await page.getByRole('button', { name: '登入' }).click();
  await expect(page.getByRole('heading', { name: '成貓主食罐正式版' })).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
  expect(overflow).toBe(false);
});
```

- [ ] **Step 4: Full GREEN including real backend smoke.**

Run:

```powershell
npm.cmd --prefix web test -- App.test.tsx
npm.cmd --prefix web run build
api/.venv/Scripts/python.exe -m pytest -c api/pyproject.toml api/tests -q
docker compose --env-file deploy/.env -f deploy/docker-compose.yml up -d --build --wait
docker compose --env-file deploy/.env -f deploy/docker-compose.yml exec api python -m alembic -c api/alembic.ini upgrade head
docker compose --env-file deploy/.env -f deploy/docker-compose.yml exec api python -m app.seed
npm.cmd --prefix web run e2e
```

Expected GREEN: API `35 passed`, React unit tests pass, build exits 0, Playwright health plus P1b login/project/mobile smoke pass. Record exact summaries and exit codes.

- [ ] **Step 5: Docs, review, commit and G4/G5/G6.**

Update README and `docs/formal-development.md` with:

- P1b UI scope and current URL.
- Demo login table for `yu`, `chen`, `ming`, `lin`.
- Note that P1b uses HttpOnly cookie sessions and does not accept frontend organization switching.
- P1c remains deployment/testing/internal trial acceptance.

Run:

```powershell
git diff --check
git status --short
git diff main --exit-code -- projectflow-full-demo.html projectflow-petfood-demo.html tests
```

Commit:

```bash
git add web/src/App.tsx web/src/App.test.tsx web/src/styles.css web/e2e/health.spec.ts README.md docs/formal-development.md
git commit -m "P1b task 4: add workflow creation browser smoke"
```

Independent Task review, fixes if needed, then `Progress: P1b task 4 done`.

Run G4 whole-branch review against this plan and the Formal Product MVP spec. Fix blockers with tests and fresh GREEN. If ready, perform G5 ff-only merge and G6 stage completion under D50: update README and PROGRESS summary, delete the merged feature branch, push `origin main`, and verify remote HEAD. Preserve the healthy Compose stack for user trial unless it was started solely for temporary testing and the user asks to stop it.

## Completion And Next Stage

P1b is complete only when all of these are true:

- Login, logout and session restore use P1a `/auth/*` endpoints and HttpOnly cookie sessions.
- Project list, project detail, node tree and breadcrumbs render real P1a project data.
- Kanban status updates call `/nodes/{id}/status`, enforce backend errors and preserve UI state on failed moves.
- Workflow templates can create a project through `/projects/from-workflow`.
- Pending gates are visible and blocked later-stage work shows the backend gate message.
- Unit tests, production build, API regression and Playwright P1b browser smoke pass.
- 1280px and 375px P1b screens have no horizontal overflow and no console errors during smoke flows.
- README, formal development docs and PROGRESS are updated and reviewed.

After P1b: P1c packages the MVP into deployment/test acceptance, including internal trial scripts for `yu`, `chen` and `ming`. Do not declare P1c complete from P1b UI tests alone.

## Self-Review

- Spec coverage: P1b login/role switch, project list/page, node tree/breadcrumb, kanban status updates, workflow creation and gate blocking UI are mapped to Tasks 1-4.
- Placeholder scan: no `TBD`, `TODO` or "add tests for the above" remains; each task names files, interfaces, commands and expected RED/GREEN.
- Type consistency: API client names, route paths, status values and UI labels are consistent across tasks.
- Review Focus coverage: each risk class has a test in Tasks 1-4.
- Scope check: P1c deployment acceptance, real ERP, AD/LDAP, AI/RAG and attachments are intentionally left to later phases.
