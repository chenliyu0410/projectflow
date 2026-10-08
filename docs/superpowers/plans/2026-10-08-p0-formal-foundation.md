# P0 Formal Foundation Implementation Plan

> **For agentic workers:** Use `superpowers:executing-plans` for Native execution, with independent Task reviews required by this repository. Do not check off this file; PROGRESS is the only execution ledger.
> **Gate:** D51 authorizes delivery through P1c. This new P0 execution plan must be reviewed before product edits, dependency installation or scaffolding. It replaces Task 1 of the older MVP outline; it does not claim P0 is implemented.

**Goal:** Deliver a runnable React + FastAPI + PostgreSQL foundation with real database readiness, tests, container startup, and formal-track working rules, preserving the Demo unchanged.

**Architecture:** Keep the single-file Demo as a reference. `web/` calls `/api/health/ready` through a same-origin proxy; `api/` exposes liveness and PostgreSQL-backed readiness. Compose owns an isolated database volume and serves the built React application through nginx. P0 introduces no login bypass, business CRUD, tenant selector or organization data; those belong to P1a/P1b.

**Tech Stack:** Node 24, React 19, TypeScript, Vite, Vitest, FastAPI, Python 3.13, psycopg, PostgreSQL 17, Docker Compose, pytest, Playwright.

**Spec:** [Formal Product MVP, P0 subsection](../specs/2026-10-05-formal-product-mvp-design.md); approved scope through P1c is recorded in D51. Company boundary requirement comes from [W6 §13](../specs/2026-10-08-multi-company-industry-demo-design.md).

## Global Constraints

- Scope is P0 only. P1a, P1b and P1c remain authorized follow-on milestones, each with its own detailed plan and acceptance results.
- Do not modify either Demo HTML file or `tests/records.html`, `tests/*.test.js`. Demo baseline remains v6 / 174 tests; formal API/database versioning is separate.
- Only the files listed in this plan may be created or edited. `.venv`, node_modules, build output and local `.env` are untracked generated artifacts, never committed.
- Traditional Chinese visible text. No cloud AI, real ERP, AD/LDAP, RAG or business workflow implementation in P0.
- P0 Task 1 must update AGENTS/WORKFLOW/PROGRESS to activate the formal-track rules before dependency installation. Demo rules still apply to Demo files. Explicitly permit this plan's dependencies and paths, not arbitrary repository-wide refactors.
- Follow WORKFLOW §3 RED → GREEN → independent review → PROGRESS commit. Formal tests record pytest/Vitest/Playwright summary and exit code instead of browser `#sum`; never claim a test passed without running it. Demo testing still follows WORKFLOW §5.
- Main checkout only; one `feature/*` branch at a time. No worktrees, pull, rebase, force, hard reset, or volume deletion. Stage explicit paths only.
- Each completed milestone updates README and PROGRESS, gets reviewed and ff-only merged, then `git push origin main` under D50. A plan publication is not implementation completion.
- Use named Compose project `projectflow-formal`; no `container_name`, no host network and no exposed DB port. Defaults bind only `127.0.0.1:15173` (web) and `127.0.0.1:18000` (API). Check before using ports; do not stop unrelated services.
- No secrets in Git, frontend bundles, errors or screenshots. Generate a local hex DB password into ignored `deploy/.env`; never print it. `deploy/.env.example` contains an empty required password.
- Backend company/role checks cannot be replaced with frontend visibility. P0 only documents this invariant; P1a must enforce it when business endpoints are introduced.

## Review Focus

1. Database unavailable: liveness remains 200, readiness is 503 without leaking DSN/password/exception text. Task 1 unit tests and Task 3 stop/start recovery cover it.
2. False readiness: no configured DB, connection failure or non-OK response must not show connected. Tasks 1 and 2 pin these cases.
3. Clean startup: locked dependencies, packaged API imports, static build, proxy routes and DB health ordering work in Compose, not just on the author's host. Task 3 exercises real HTTP and PostgreSQL.
4. Client failure/retry: first request loading, failure, retry, invalid payload and unmount must not leave stale or contradictory UI. Task 2 covers them.
5. Scope and isolation: no business endpoints or fake login are introduced; runtime configuration is outside the browser and the database volume is retained on restart. Tasks 1/3 verify OpenAPI routes, ignored configuration and same-volume restart.

## Verified Environment And Versions

Read-only checks on 2026-10-08: Node 24.19.0, npm 11.17.0, Python 3.13.9, Docker engine 29.7.2, Compose 5.4.0; ports 15173 and 18000 were free. Recheck at execution time. No product dependencies have been installed for this planning step.

Package versions below were read from npm and PyPI registries on that date. Commit `web/package-lock.json` and the generated `api/requirements.lock`. Do not silently use `latest` during implementation. If a dependency fails compatibility/security checks, stop, diagnose and revise the plan explicitly.

References: [Vite installation](https://vite.dev/guide/), [FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/), [Compose health ordering](https://docs.docker.com/compose/how-tos/startup-order/). Dependency resolution and actual GREEN runs, not these references alone, establish compatibility.

## File Structure

```text
AGENTS.md, docs/WORKFLOW.md, docs/PROGRESS.md, README.md, .gitignore
docs/formal-development.md
api/requirements.txt, api/requirements.lock, api/pyproject.toml
api/app/__init__.py, api/app/main.py, api/tests/test_health.py
web/package.json, web/package-lock.json, web/index.html, web/tsconfig.json
web/vite.config.ts, web/src/main.tsx, web/src/App.tsx, web/src/App.test.tsx
web/src/test-setup.ts, web/src/styles.css, web/public/mark.svg
web/playwright.config.ts, web/e2e/health.spec.ts
deploy/.env.example, deploy/docker-compose.yml
deploy/api.Dockerfile, deploy/web.Dockerfile, deploy/nginx.conf
.dockerignore
```

## Task 1: Formal Rules And API Health Contract

**Files:** Modify `AGENTS.md`, `docs/WORKFLOW.md`, `.gitignore`, `docs/PROGRESS.md`, `README.md`; create `docs/formal-development.md`, `api/requirements.txt`, `api/requirements.lock` (generated), `api/pyproject.toml`, `api/app/__init__.py`, `api/app/main.py`, `api/tests/test_health.py`.

**Interfaces:** `create_app(checker: Callable[[], bool] | None = None) -> FastAPI`; `database_ready() -> bool`; module-level `app`. `GET /health` returns 200 `{"ok":true}`. `GET /health/ready` returns 200 `{"ok":true,"database":"ready"}` or 503 `{"ok":false,"database":"unavailable"}`. `DATABASE_URL` is server-only.

- [ ] **Step 1: Pre-flight and track switch.** Follow WORKFLOW G3, record exact BASE, make `Progress: start P0`, then `git checkout -b feature/p0-formal-foundation`. Record the immutable Demo hashes with `git rev-parse HEAD:projectflow-full-demo.html HEAD:projectflow-petfood-demo.html`. No app files yet.

Update AGENTS §1 to distinguish the preserved Demo from formal directories. Keep Demo-only restrictions under their existing heading, and add this formal-track block before the test section:

```markdown
**正式產品軌（D51；P0起）**
- 只修改當前已審閱plan明列的檔案；Demo與正式版分開驗收。
- 正式版允許plan明列的React／FastAPI／PostgreSQL與測試依賴，需鎖版；Demo仍不引入新依賴。
- DB變更透過後端服務與migration；有業務寫入時一併記錄稽核。公司與角色權限由API強制執行，不以切換前端狀態代替。
- React用預設文字跳脫，不用dangerouslySetInnerHTML輸出使用者資料；密碼、token、.env不得提交或送到瀏覽器。
- pytest、Vitest、Playwright各自記錄真實RED/GREEN摘要與exit code，沒有實跑不得標通過。
- Git、TDD、逐Task獨立審查、單一寫入者、主checkout與ff-only規則不變；D50已持續授權完成階段更新README並push origin main。
```

In WORKFLOW §3 step 3 and §5 append a formal-track exception: use the current plan's commands and test summaries, not the Demo `#sum`, for formal files. Keep the task review/record cycle unchanged. In §8 and Git prohibition text refer to D50 for already-authorized stage pushes, while retaining stop conditions for new PRs, force, remote divergence and unapproved scope. This is the rule switch authorized by D51, not a waiver of review.

Append to `.gitignore`:

```gitignore
api/.venv/
**/__pycache__/
.pytest_cache/
web/node_modules/
web/dist/
web/test-results/
web/playwright-report/
deploy/.env
```

- [ ] **Step 2: Prepare test tooling and failing tests.** Create `api/requirements.txt`:

```text
fastapi==0.142.4
uvicorn==0.54.0
psycopg[binary]==3.3.6
pytest==9.1.1
httpx==0.28.1
```

`api/pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
addopts = "-ra"
```

Create the empty `api/app/__init__.py` and `api/tests/test_health.py` (no `main.py` yet):

```python
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
    assert paths == {"/health", "/health/ready"}
```

From repo root in PowerShell, run each command separately and check its exit code:

```powershell
python -m venv api/.venv
api/.venv/Scripts/python.exe -m pip install -r api/requirements.txt
api/.venv/Scripts/python.exe -m pytest -c api/pyproject.toml api/tests/test_health.py -q
```

Expected RED: collection/import failure for `app.main` only after dependencies installed correctly. Do not count pip/network/import errors from missing test dependencies as a behavior RED. Preserve the actual output in PROGRESS.

- [ ] **Step 3: Implement `api/app/main.py`.**

```python
import os
from collections.abc import Callable
import psycopg
from fastapi import FastAPI
from fastapi.responses import JSONResponse


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
```

- [ ] **Step 4: GREEN and lock.** Rerun the pytest command; expected 8 passed. Run `api/.venv/Scripts/python.exe -m pip check`. Generate the reproducibility lock with the commands below, then inspect for local paths or credentials before staging. This generated dependency lock is a mechanical artifact, not a manual source edit. No editable install or host-wide pip installation.

```powershell
$lock = & api/.venv/Scripts/python.exe -m pip freeze
if ($LASTEXITCODE -ne 0) { throw 'Cannot lock API dependencies' }
[IO.File]::WriteAllLines((Join-Path (Get-Location) 'api/requirements.lock'), [string[]]$lock, (New-Object Text.UTF8Encoding $false))
```

Create `docs/formal-development.md` with these exact rules and initial commands:

```markdown
# 正式版開發

正式版目標為P0至P1c的可內部試用MVP，Demo保持獨立且不得視為正式登入／多租戶安全機制。

## 公司邊界
後續業務資料以organization_id識別公司。API從已驗證身分取得可用公司，查詢與外鍵須限制公司；不能信任前端傳來的公司參數。稽核、檔案讀寫與工作流建立同樣受限。P0只有健康檢查，尚無業務API或登入功能。

## 本機API
在repo根目錄逐行執行：
`python -m venv api/.venv`
`api/.venv/Scripts/python.exe -m pip install -r api/requirements.lock`
`api/.venv/Scripts/python.exe -m pytest -c api/pyproject.toml api/tests -q`
`api/.venv/Scripts/python.exe -m uvicorn app.main:app --app-dir api --host 127.0.0.1 --port 18000`

GET /health檢查API存活；GET /health/ready會實際查詢PostgreSQL，未設定DATABASE_URL或DB不可用時回503。不要把DSN／密碼提交到Git。

## 工作流程
主checkout一次一個feature分支，TDD、每Task獨立審查、PROGRESS唯一進度來源。每階段完成更新README、驗收後ff-only到main並依D50推送，不force。正式資料庫未導入migration前，不可建立業務表或宣稱P1a完成。
```

Update README's P0 status to Task 1 complete only after verified GREEN, linking this document and naming the missing React/Compose acceptance. Native PowerShell commands above are Windows host commands; container Linux commands appear in Task 3.

- [ ] **Step 5: Review and commit.** `git diff --check`; explicit `git add` the Task 1 file list (including reviewed `api/requirements.lock`, not `.venv`). Commit `P0 task 1: add formal rules and API health checks`. Independent review per WORKFLOW §4, fix actual Important/Critical findings, then `Progress: P0 task 1 done` with real RED/GREEN. Do not mark the P0 milestone done or push an unreviewed product stage.

## Task 2: React Health Surface

**Files:** Create `web/package.json`, `web/package-lock.json` (generated), `web/index.html`, `web/tsconfig.json`, `web/vite.config.ts`, `web/src/main.tsx`, `web/src/App.tsx`, `web/src/App.test.tsx`, `web/src/test-setup.ts`, `web/src/styles.css`, `web/public/mark.svg`; update `docs/formal-development.md`, README and PROGRESS.

**Interfaces:** Same-origin `GET /api/health/ready` proxy to Task 1 `/health/ready`. Export default `App`. Visible states: `檢查中`, `已連線`, `無法連線`; retry button `重新檢查`. No company/user login controls until P1.

- [ ] **Step 1: Configure test tooling.** `web/package.json`:

```json
{
  "name": "projectflow-web", "private": true, "version": "0.1.0", "type": "module",
  "engines": {"node": ">=24.15.0 <25"},
  "scripts": {"dev":"vite --host 127.0.0.1 --port 15173 --strictPort", "test":"vitest run", "build":"tsc --noEmit && vite build", "e2e":"playwright test"},
  "dependencies": {"react":"19.3.0", "react-dom":"19.3.0"},
  "devDependencies": {
    "@types/react":"19.3.0", "@types/react-dom":"19.3.0", "@types/node":"24.19.1",
    "vite":"8.3.3", "@vitejs/plugin-react":"6.1.2", "typescript":"7.0.2",
    "vitest":"5.0.3", "jsdom":"30.1.2", "@testing-library/react":"16.3.3",
    "@testing-library/jest-dom":"7.0.1", "@playwright/test":"1.64.0"
  }
}
```

`web/tsconfig.json`:

```json
{"compilerOptions":{"target":"ES2022","lib":["ES2022","DOM","DOM.Iterable"],"module":"ESNext","moduleResolution":"Bundler","jsx":"react-jsx","strict":true,"skipLibCheck":true,"esModuleInterop":true,"noEmit":true,"types":["vite/client","vitest/globals","@testing-library/jest-dom","node"]},"include":["src","vite.config.ts","playwright.config.ts","e2e"]}
```

`web/vite.config.ts`:

```ts
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: { proxy: { '/api': { target: process.env.API_PROXY_TARGET || 'http://127.0.0.1:18000', changeOrigin: false, rewrite: path => path.replace(/^\/api/, '') } } },
  test: { environment: 'jsdom', setupFiles: ['./src/test-setup.ts'], include: ['src/**/*.test.tsx'] },
});
```

`web/src/test-setup.ts`:

```ts
import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach, vi } from 'vitest';
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });
```

Create `web/src/App.test.tsx` before `App.tsx`:

```tsx
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import App from './App';

const good = () => Promise.resolve({ ok: true, json: async () => ({ ok: true, database: 'ready' }) });
describe('health surface', () => {
  it('shows loading until the response arrives', () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {})));
    render(<App />);
    expect(screen.getByRole('status')).toHaveTextContent('檢查中');
    expect(screen.getByRole('button', { name: '重新檢查' })).toBeDisabled();
  });
  it('uses the proxy and displays verified readiness', async () => {
    const fetcher = vi.fn(good); vi.stubGlobal('fetch', fetcher);
    render(<App />);
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('已連線'));
    expect(fetcher).toHaveBeenCalledWith('/api/health/ready', expect.objectContaining({ signal: expect.any(AbortSignal) }));
  });
  it('supports retry after network failure', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValueOnce(new Error('private')).mockImplementation(good));
    render(<App />);
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('無法連線'));
    expect(screen.queryByText('private')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '重新檢查' }));
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('已連線'));
  });
  it.each([
    { ok: false, json: async () => ({ ok: false, database: 'unavailable' }) },
    { ok: true, json: async () => ({ ok: true, database: 'unexpected' }) },
  ])('rejects non-ready responses', async response => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response));
    render(<App />);
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('無法連線'));
  });
  it('aborts the request on unmount', () => {
    const fetcher = vi.fn(() => new Promise(() => {})); vi.stubGlobal('fetch', fetcher);
    const { unmount } = render(<App />);
    const signal = (fetcher.mock.calls as unknown as [string, RequestInit][])[0][1].signal;
    unmount(); expect(signal?.aborted).toBe(true);
  });
});
```

From repo root: `npm.cmd --prefix web install` then `npm.cmd --prefix web test`. Expected RED: `./App` missing after successful tooling installation. Commit no generated lock until inspected; retain the real failure summary.

- [ ] **Step 2: Implement the surface.** `web/index.html`:

```html
<!doctype html>
<html lang="zh-Hant"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>專流 ProjectFlow</title><link rel="icon" href="/mark.svg"></head><body><div id="root"></div><script type="module" src="/src/main.tsx"></script></body></html>
```

`web/src/main.tsx`:

```tsx
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './styles.css';
createRoot(document.getElementById('root')!).render(<StrictMode><App /></StrictMode>);
```

`web/src/App.tsx`:

```tsx
import { useEffect, useState } from 'react';

export default function App() {
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<'loading' | 'ready' | 'error'>('loading');
  useEffect(() => {
    const controller = new AbortController();
    setState('loading');
    const timer = window.setTimeout(() => controller.abort(), 5000);
    let active = true;
    (async () => {
      try {
        const response = await fetch('/api/health/ready', { signal: controller.signal });
        if (!response.ok) throw new Error('unavailable');
        const value = await response.json();
        if (value.ok !== true || value.database !== 'ready') throw new Error('invalid');
        if (active) setState('ready');
      } catch {
        if (active) setState('error');
      } finally { window.clearTimeout(timer); }
    })();
    return () => { active = false; window.clearTimeout(timer); controller.abort(); };
  }, [attempt]);
  return <>
    <header><img src="/mark.svg" width="32" height="32" alt="" /><strong>專流 ProjectFlow</strong><span>系統狀態</span></header>
    <main><h1>服務狀態</h1><section aria-label="連線狀態">
      <h2>API 與資料庫</h2>
      <p role="status" className={state}>{state === 'ready' ? '已連線' : state === 'error' ? '無法連線' : '檢查中'}</p>
      <button disabled={state === 'loading'} onClick={() => setAttempt(value => value + 1)}>重新檢查</button>
    </section></main>
  </>;
}
```

`web/src/styles.css`:

```css
:root{font-family:system-ui,"Microsoft JhengHei",sans-serif;color:#232b2b;background:#f6f7f8;font-synthesis:none;letter-spacing:0}
*{box-sizing:border-box}body{margin:0}header{min-height:64px;background:#fff;border-bottom:1px solid #d8dedf;display:flex;align-items:center;gap:12px;padding:12px 24px;flex-wrap:wrap}header span{color:#616a6c;margin-left:auto;font-size:14px}
main{max-width:960px;margin:0 auto;padding:28px 24px}h1{font-size:24px;margin:0 0 24px}h2{font-size:16px;margin:0}section{border-top:1px solid #d8dedf;padding:20px 0;display:grid;grid-template-columns:minmax(0,1fr) 120px 112px;gap:16px;align-items:center}p{margin:0;font-size:14px}.ready{color:#21684f}.error{color:#ad303a}.loading{color:#525e64}
button{min-height:40px;border:1px solid #a9b5b8;background:white;color:#253a40;border-radius:6px;padding:8px 12px;font:inherit;font-size:14px;cursor:pointer}button:disabled{opacity:.55;cursor:wait}button:focus-visible{outline:3px solid #397793;outline-offset:2px}
@media(max-width:480px){header{padding:12px 16px}main{padding:24px 16px}section{grid-template-columns:minmax(0,1fr) 112px}section h2{grid-column:1/-1}header span{margin-left:0}}
```

Use an existing product mark rather than inventing a new illustration: `web/public/mark.svg` is the three-line ProjectFlow mark from the Demo header, written as a standalone local asset:

```svg
<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32"><rect width="32" height="32" rx="6" fill="#1f5f5b"/><path d="M9 10h14M9 16h10M9 22h6" stroke="white" stroke-width="2" stroke-linecap="round"/></svg>
```

- [ ] **Step 3: GREEN.** Run `npm.cmd --prefix web test` (expected 6 passed) and `npm.cmd --prefix web run build`; both must exit 0. Inspect package-lock for registry source and matching manifests. Run `npm.cmd --prefix web audit --omit=dev` and record results; investigate runtime high/critical issues before release, do not run blind `audit fix`.

Append local web commands to `docs/formal-development.md`: `npm.cmd --prefix web ci`, `npm.cmd --prefix web test`, `npm.cmd --prefix web run build`, `npm.cmd --prefix web run dev`. The dev proxy uses API port18000; no cross-origin policy bypass. State that DB readiness is unavailable until Task 3 DB is configured. UI screenshots in Task 3 cover the real stack.

- [ ] **Step 4: Review and commit.** `git diff --check`; stage explicit Task 2 paths. Commit `P0 task 2: add React health surface`. Independent Task review; progress commit `Progress: P0 task 2 done` with actual outcomes. README must say UI implemented but real-stack acceptance still pending.

## Task 3: Compose, Real PostgreSQL And Acceptance

**Files:** Create `.dockerignore`, `deploy/.env.example`, `deploy/docker-compose.yml`, `deploy/api.Dockerfile`, `deploy/web.Dockerfile`, `deploy/nginx.conf`, `web/playwright.config.ts`, `web/e2e/health.spec.ts`; modify README, PROGRESS and `docs/formal-development.md`.

**Interfaces:** Compose services `web`, `api`, `db`; `projectflow-formal_pgdata` volume; default web15173/API18000, loopback only. nginx maps `/api/health*` to API `/health*`. Health endpoints remain Task1 contracts.

- [ ] **Step 1: Write actual stack tests before Compose files.** `web/playwright.config.ts`:

```ts
import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './e2e', workers: 1, retries: 0,
  use: { baseURL: process.env.PF_BASE_URL || 'http://127.0.0.1:15173', browserName: 'chromium' },
});
```

`web/e2e/health.spec.ts`:

```ts
import { expect, test } from '@playwright/test';

test('proxy verifies actual database readiness', async ({ request }) => {
  const live = await request.get('/api/health');
  expect(live.status()).toBe(200); expect(await live.json()).toEqual({ok:true});
  const ready = await request.get('/api/health/ready');
  expect(ready.status()).toBe(200);
  expect(await ready.json()).toEqual({ok:true,database:'ready'});
});

for (const width of [1280,375]) {
  test(`usable health surface at ${width}px`, async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', error => errors.push(String(error)));
    page.on('console', message => { if(message.type()==='error') errors.push(message.text()); });
    await page.setViewportSize({width,height:900});
    await page.goto('/');
    await expect(page.getByRole('heading',{name:'服務狀態'})).toBeVisible();
    await expect(page.getByRole('status')).toHaveText('已連線');
    await page.getByRole('button',{name:'重新檢查'}).click();
    await expect(page.getByRole('status')).toHaveText('已連線');
    expect(await page.locator('header img').evaluate((img: HTMLImageElement) => img.complete && img.naturalWidth>0)).toBe(true);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({path:`test-results/p0-${width}.png`,fullPage:true});
    expect(errors).toEqual([]);
  });
}

test('unknown API path is not served as frontend HTML', async ({ request }) => {
  const response = await request.get('/api/missing');
  expect(response.status()).toBe(404);
  expect(response.headers()['content-type']).toContain('application/json');
});
```

From root, install the browser from the web package directory, then execute the new tests:

```powershell
Push-Location web
try { npm.cmd exec -- playwright install chromium } finally { Pop-Location }
npm.cmd --prefix web run e2e
```

First verify port15173 is free and no prior P0 service is running; expected RED is connection refused on the new stack, not a browser installation failure. Record all 4 failed cases. Never target an unrelated server.

- [ ] **Step 2: Add container configuration.** `.dockerignore`:

```gitignore
.git
.superpowers
**/node_modules
**/.venv
**/__pycache__
**/.pytest_cache
web/dist
web/test-results
web/playwright-report
deploy/.env
```

`deploy/.env.example`:

```dotenv
POSTGRES_PASSWORD=
WEB_PORT=15173
API_PORT=18000
```

`deploy/api.Dockerfile`:

```dockerfile
FROM python:3.13-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY api/requirements.lock ./requirements.lock
RUN pip install --no-cache-dir -r requirements.lock
COPY api/app ./app
RUN useradd --create-home appuser
USER appuser
EXPOSE 8000
CMD ["python","-m","uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
```

`deploy/web.Dockerfile`:

```dockerfile
FROM node:24-bookworm-slim AS build
WORKDIR /app
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build
FROM nginx:stable-alpine
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
```

`deploy/nginx.conf`:

```nginx
server {
  listen 80;
  root /usr/share/nginx/html;
  index index.html;
  location /api/ {
    proxy_pass http://api:8000/;
    proxy_connect_timeout 3s;
    proxy_read_timeout 8s;
  }
  location / { try_files $uri $uri/ /index.html; }
}
```

`deploy/docker-compose.yml`:

```yaml
name: projectflow-formal
services:
  db:
    image: postgres:17-alpine
    environment:
      POSTGRES_DB: projectflow
      POSTGRES_USER: projectflow
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD in deploy/.env}
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: [CMD-SHELL, 'pg_isready -U projectflow -d projectflow']
      interval: 3s
      timeout: 3s
      retries: 20
  api:
    build:
      context: ..
      dockerfile: deploy/api.Dockerfile
    environment:
      DATABASE_URL: postgresql://projectflow:${POSTGRES_PASSWORD:?Set POSTGRES_PASSWORD in deploy/.env}@db:5432/projectflow
    ports:
      - '127.0.0.1:${API_PORT:-18000}:8000'
    depends_on:
      db:
        condition: service_healthy
    healthcheck:
      test: [CMD, python, -c, 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8000/health/ready", timeout=5)']
      interval: 3s
      timeout: 6s
      retries: 20
  web:
    build:
      context: ..
      dockerfile: deploy/web.Dockerfile
    ports:
      - '127.0.0.1:${WEB_PORT:-15173}:80'
    depends_on:
      api:
        condition: service_healthy
volumes:
  pgdata:
```

Create the generated local configuration only if absent, without printing the password:

```powershell
if (-not (Test-Path -LiteralPath deploy/.env)) {
  $bytes = New-Object byte[] 32
  $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
  try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
  $password = ($bytes | ForEach-Object { $_.ToString('x2') }) -join ''
  $config = "POSTGRES_PASSWORD=$password`nWEB_PORT=15173`nAPI_PORT=18000`n"
  [IO.File]::WriteAllText((Join-Path (Get-Location) 'deploy/.env'), $config, (New-Object Text.UTF8Encoding $false))
  Remove-Variable password,config,bytes
}
git check-ignore deploy/.env
```

This is generated configuration data, never a source literal or committed artifact. The hex restriction avoids DSN encoding ambiguity. If a DB volume exists with different credentials, do not replace credentials or remove the volume; report and recover explicitly.

- [ ] **Step 3: Compose GREEN.** All commands from repository root, individually in PowerShell:

```powershell
docker compose --env-file deploy/.env -f deploy/docker-compose.yml config --quiet
docker compose --env-file deploy/.env -f deploy/docker-compose.yml up -d --build --wait
docker compose --env-file deploy/.env -f deploy/docker-compose.yml ps
api/.venv/Scripts/python.exe -m pytest -c api/pyproject.toml api/tests -q
npm.cmd --prefix web ci
npm.cmd --prefix web test
npm.cmd --prefix web run build
npm.cmd --prefix web run e2e
```

`config --quiet` must exit0 without exposing interpolated secrets. `up --wait` must succeed; e2e 4 passed plus Task1/2 tests all GREEN. View both generated screenshots with the image tool; confirm text, status, button and mark are visible, no overlap, and console errors empty. Record Docker image IDs/digests and tool versions in PROGRESS for the tested stack. Do not claim production-hardening from this dev foundation.

- [ ] **Step 4: DB outage and recovery (only this Compose project).** Run this probe from root. If a different web port was required, derive it from the existing WEB_PORT entry without dumping the .env content. This script always restarts this project's DB even on an assertion failure.

```powershell
$webPort = ((Get-Content deploy/.env | Where-Object { $_ -match '^WEB_PORT=' }) -split '=',2)[1]
$base = "http://127.0.0.1:$webPort"
$before = docker volume inspect projectflow-formal_pgdata --format '{{.Mountpoint}}'
if ($LASTEXITCODE -ne 0) { throw 'Missing database volume' }
Add-Type -AssemblyName System.Net.Http
$http = New-Object Net.Http.HttpClient
$http.Timeout = [TimeSpan]::FromSeconds(8)
try {
  docker compose --env-file deploy/.env -f deploy/docker-compose.yml stop db
  if ($LASTEXITCODE -ne 0) { throw 'Cannot stop test database' }
  $live = $http.GetAsync("$base/api/health").GetAwaiter().GetResult()
  if ([int]$live.StatusCode -ne 200) { throw 'API liveness depends on DB' }
  $live.Dispose()
  $ready = $http.GetAsync("$base/api/health/ready").GetAwaiter().GetResult()
  $body = $ready.Content.ReadAsStringAsync().GetAwaiter().GetResult() | ConvertFrom-Json
  if ([int]$ready.StatusCode -ne 503 -or $body.ok -ne $false -or $body.database -ne 'unavailable') { throw 'Wrong outage contract' }
  if ((($body.PSObject.Properties.Name | Sort-Object) -join ',') -ne 'database,ok') { throw 'Unexpected error details' }
  $ready.Dispose()
} finally {
  $http.Dispose()
  docker compose --env-file deploy/.env -f deploy/docker-compose.yml up -d --wait db
  if ($LASTEXITCODE -ne 0) { throw 'Database recovery failed' }
}
$after = docker volume inspect projectflow-formal_pgdata --format '{{.Mountpoint}}'
if ($before -ne $after) { throw 'Database volume changed' }
npm.cmd --prefix web run e2e
```

Separately exercise the visible outage state with the browser: stop this project's db, reload/retry and observe `無法連線`; restore with `up -d --wait db` in a finally block, retry and observe `已連線`. Keep page/console errors caused by expected503 separate from unexpected exceptions. Never `down -v`, prune or touch unrelated containers.

- [ ] **Step 5: Documentation and final acceptance.** Append the Task3 commands and requirements to `docs/formal-development.md`, including: Node24.15+ within24.x and Python3.13 for native development, Docker with Compose for complete stack, port overrides in deploy/.env plus matching PF_BASE_URL for e2e, generated local hex password, `npm ci` and pip lock installation, readiness behavior, DB recovery without deleting volumes, and shutdown via `docker compose --env-file deploy/.env -f deploy/docker-compose.yml down` (no `-v`). Link this guide in README and mark P0 done only after all tests, screenshots and reviews pass. State the user URL `http://127.0.0.1:15173` (or actual chosen port) and leave the healthy app available for the user; terminate temporary foreground test sessions, not unrelated services.

Before commit:

```powershell
git diff --check
git status --short
git diff --name-only main...HEAD
git diff main --exit-code -- projectflow-full-demo.html projectflow-petfood-demo.html tests
git check-ignore deploy/.env api/.venv web/node_modules
```

All Demo files must be unchanged; no generated secrets or temporary output may be staged. Explicitly stage Task3 files plus README/PROGRESS/development guide. Commit `P0 task 3: verify containerized foundation`. Independent Task review and `Progress: P0 task 3 done`. G4 reviewer reads whole P0 branch; all blocker fixes receive actual regression tests and fresh GREEN runs. G5 ff-only merge, G6 update stage summary, delete merged feature branch, push origin/main under D50 and verify remote HEAD. Preserve every existing unrelated branch.

## Completion And Next Stage

P0 is complete only when rules have switched, API unit tests (8), React tests (6), stack tests (4), both viewports and real DB outage/recovery pass. Counts are initial baseline + tests added for discovered defects, not a cap. Do not substitute Demo174 for formal validation. Development image tags are convenience tags, not an offline or production release guarantee; record the tested digests.

After P0: P1a defines trusted identity/session handling, organization keys and scoped relationships, migrations, Project/Node/Department/Workflow/Gate/Report/Audit APIs, and bypass/isolation tests. P1b connects the real React workflows, not the health-only shell. P1c verifies clean setup, user-role flows and deployment. D51 already authorizes work through P1c; new detailed plans still need their normal review gates. Do not ask again whether the user wants to start the formal track.

## Self-Review

- Scope maps to the existing P0 spec: Task1 rules/API/testing/company-boundary guide; Task2 React; Task3 Compose/PostgreSQL/deployment verification.
- Task interfaces agree on `/health/ready`, `/api` rewrite, boolean readiness and ports; configuration is server-only.
- Every Review Focus item has an owning task and test/probe; no business API is silently declared complete.
- Exact file lists and contents are provided. Dependency locks are explicitly generated from isolated tooling and verified, not handwritten dependency guesses.
- This is a plan; none of the future commands above has been claimed as executed by writing it.
