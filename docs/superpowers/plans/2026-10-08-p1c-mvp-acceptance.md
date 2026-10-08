# P1c MVP Deployment And Acceptance Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans or subagent-driven-development; follow WORKFLOW Task RED -> GREEN -> independent spec/quality reviews -> PROGRESS commit. PROGRESS is the ledger; do not check off this plan.

**Goal:** Deliver reproducible local Compose startup and a repeatable, isolated MVP acceptance run for yu, chen, ming and readonly/company boundaries.

**Architecture:** Python standard-library launchers orchestrate the existing Compose stack without new dependencies. A separate `projectflow-acceptance` Compose project, private environment file and loopback ports isolate browser acceptance from the user's `projectflow-formal` database. Existing backend permission helpers remain authoritative; member project responses apply the already-defined `can_view_node` policy, with frontend support for visible nodes whose parent is not visible.

**Tech Stack:** Existing Python 3.13/FastAPI/SQLAlchemy/Alembic, PostgreSQL17, Docker Compose, React/TypeScript, pytest, Vitest and Playwright lockfiles.

**Spec:** [Formal MVP P1c and acceptance standards](../specs/2026-10-05-formal-product-mvp-design.md). D51 authorizes through P1c; the human now directs continuing the next stage. Preserve D53's preference to review finished results and autonomously advance intermediate work within the existing MVP scope.

## Global Constraints

- Main checkout only, branch `feature/p1c-mvp-acceptance`; no worktrees, pull, rebase, force or destructive Git operations. Explicit git add paths only.
- Only modify/create files in File Structure. Demo HTML and `tests/` are unchanged; Demo v6/174 is reference evidence only.
- No new dependencies, migrations, roles, product modules, document/report UI, ERP/AI/AD/TLS or LAN publishing. This is a loopback MVP trial, not a production security certification.
- Business writes remain API-authorized and audited; company identity comes from HttpOnly session. Do not display raw errors, DSNs, cookies or passwords in logs.
- Preserve existing data and environment files; no database reset, deletion of historical test projects, volume deletion, prune or `down -v`.
- Acceptance uses a separate Compose project/volume. Generated acceptance env goes under gitignored `.superpowers/p1c/acceptance.env`; regular startup preserves ignored `deploy/.env`.
- Playwright defaults to acceptance port15175, never the user's port15173. Before test mutations, require an explicit acceptance marker endpoint enabled only in the acceptance API environment.
- Existing seed initialization is opt-in `--seed-demo`, intended for local trial with documented demo credentials; do not change existing users/passwords or silently add seed data without that switch.
- User-facing UI stays Traditional Chinese. React escaping remains default; no dangerouslySetInnerHTML.
- Tests record actual summaries and exit codes. Every Task has independent reviews; fixes before next Task. D50 permits ff-only integration and origin main push when reviewed and verified.

## File Structure

```text
deploy/start.py                         # stdlib Compose launch + optional seed
deploy/verify.py                        # acceptance orchestration and safe cleanup
deploy/docker-compose.yml               # acceptance marker env only
api/app/main.py                         # opt-in acceptance marker route
api/app/routes/projects.py              # existing node read policy enforcement
api/tests/test_deployment.py            # launcher/verification behavior tests
api/tests/test_health.py                # marker disabled/enabled behavior
api/tests/test_projects_nodes.py        # role read regression tests
api/tests/test_mvp_acceptance.py         # role/report/audit/company contracts
web/src/App.tsx                         # visible orphan roots
web/src/App.test.tsx                    # restricted node-tree regression
web/playwright.config.ts                # isolated default base URL
web/e2e/health.spec.ts                   # marker guard + precise expected errors
web/e2e/mvp.spec.ts                      # yu/chen/ming browser/API acceptance
README.md
docs/formal-development.md
docs/mvp-trial-checklist.md
docs/PROGRESS.md
```

**Testing:** WORKFLOW section5 formal-track exception. G3 baseline API35, Vitest55, build0, E2E4. Run the current E2E baseline before changing the default URL, then run all subsequent mutation smoke only on the isolated stack.

## Review Focus

1. Existing `.env` and user's Compose DB must never be overwritten or cleared; Task1 tests preservation and command arguments.
2. An accidental shared/live E2E URL must fail before business mutations; Task1 marker and Task2 guard prove this.
3. Members must not receive another owner's nodes or hidden gate metadata; Task2 asserts concrete response IDs and frontend orphan rendering.
4. Department reviewer and task owner permissions must agree across status/report/gate operations; Task2 tests real API outcomes, not frontend role toggles.
5. A failed acceptance command must retain a failing exit code while cleanup never touches the user's Compose project; Task3 tests failure/cleanup and documents trial limits.

## Task 1: Safe Compose Startup And Acceptance Environment

**Files:** Create deploy/start.py, api/tests/test_deployment.py; modify deploy/docker-compose.yml, api/app/main.py, api/tests/test_health.py, docs/formal-development.md.

**Interfaces:**
- `initialize_env(path: Path, web_port: int, api_port: int, acceptance: bool) -> None`: exclusive create only; existing bytes unchanged.
- `start(root: Path, *, acceptance: bool = False, seed_demo: bool = False) -> dict[str, str]`: returns `web_url`, `project`, `env_file`; raises sanitized RuntimeError on command/readiness failure.
- CLI `python deploy/start.py [--acceptance] [--seed-demo]` exits0 only after migration and HTTP readiness; failures exit1.
- Compose API environment `PF_ACCEPTANCE_MODE: ${PF_ACCEPTANCE_MODE:-false}`.
- GET `/health/acceptance`: 200 `{"acceptance": true}` only when PF_ACCEPTANCE_MODE is exactly `true`; otherwise404. No authorization bypass or secrets.

- [ ] Step1: Write failing tests in api/tests/test_deployment.py, loading the deploy module via importlib/path (no dependency install). Tests use tmp_path and monkeypatched subprocess/HTTP to verify behavior.

```python
def test_existing_env_is_preserved(tmp_path, start_module):
    path = tmp_path / '.env'
    path.write_bytes(b'EXISTING=unchanged\n')
    start_module.initialize_env(path, 15175, 18002, True)
    assert path.read_bytes() == b'EXISTING=unchanged\n'

def test_acceptance_never_targets_shared_project(tmp_path, start_module, monkeypatch):
    calls = []
    def run(args, **kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, '127.0.0.1:15175\n' if 'port' in args else '', '')
    monkeypatch.setattr(start_module.subprocess, 'run', run)
    # Stub readiness with an actual JSON response object; no network in this unit test.
    monkeypatch.setattr(start_module, 'check_readiness', lambda url: None)
    result = start_module.start(tmp_path, acceptance=True, seed_demo=True)
    assert result['project'] == 'projectflow-acceptance'
    assert result['web_url'] == 'http://127.0.0.1:15175'
    assert all('projectflow-acceptance' in args for args in calls)
    assert not any('-v' in args or 'down' in args for args in calls)
    assert any('alembic' in args and 'head' in args for args in calls)
```

Use meaningful command-order assertions (config -> up --wait -> migration -> optional seed -> port -> HTTP readiness), opt-in seed absent by default, failed command stops later commands, missing Docker sanitized error, invalid/non-loopback port output rejected, new env contains strong URL-safe generated password and isolated ports/marker. Add marker tests:

```python
def test_acceptance_marker_is_opt_in(monkeypatch):
    monkeypatch.delenv('PF_ACCEPTANCE_MODE', raising=False)
    with TestClient(create_app(lambda: True)) as client:
        assert client.get('/health/acceptance').status_code == 404
    monkeypatch.setenv('PF_ACCEPTANCE_MODE', 'true')
    with TestClient(create_app(lambda: True)) as client:
        assert client.get('/health/acceptance').json() == {'acceptance': True}
```

- [ ] Step2: Run `api/.venv/Scripts/python.exe -m pytest -c api/pyproject.toml api/tests/test_deployment.py api/tests/test_health.py -q`. Expected RED missing launcher/marker, not missing dependency. Record names/exit.
- [ ] Step3: Implement launcher with subprocess argument arrays and captured errors. Default project `projectflow-formal`/env deploy/.env/ports15173+18000; acceptance project `projectflow-acceptance`/env .superpowers/p1c/acceptance.env/ports15175+18002. Env creation uses secrets.token_hex(32), exclusive open and no secret output. Preserve existing env, never rotate its credentials. Respect caller's configured ports via `docker compose ... port web 80`, parsing only loopback host + valid integer. Do not dump compose config (contains secrets).

```python
prefix = ['docker', 'compose', '--project-name', project,
          '--env-file', str(env_file), '-f', str(root / 'deploy/docker-compose.yml')]
run(prefix + ['config', '--quiet'])
run(prefix + ['up', '-d', '--build', '--wait'])
run(prefix + ['exec', '-T', 'api', 'python', '-m', 'alembic', 'upgrade', 'head'])
if seed_demo:
    run(prefix + ['exec', '-T', 'api', 'python', '-m', 'app.seed'])
```

Readiness checks `/api/health/ready` JSON equals `{ok:true,database:'ready'}` with bounded urllib timeout. Acceptance additionally requires `/api/health/acceptance` true. No shell=True. CLI prints only project and web URL; no raw subprocess stderr. Document host Python + Docker requirement, demo-seed explicit initialization and persistent volume.
- [ ] Step4: Full API GREEN, Vitest/build regression. Execute `api/.venv/Scripts/python.exe deploy/start.py --acceptance --seed-demo`, then HTTP health/marker/seed login on15175 (never print cookies). Existing15173 remains available; verify its project count unchanged across isolated startup.
- [ ] Step5: Explicit add permitted files and commit `P1c task 1: add safe Compose trial startup`; independent reviews; record PROGRESS.

## Task 2: Role Boundaries And Isolated Browser Acceptance

**Files:** Modify api/app/routes/projects.py, api/tests/test_projects_nodes.py, web/src/App.tsx, web/src/App.test.tsx, web/playwright.config.ts, web/e2e/health.spec.ts; create api/tests/test_mvp_acceptance.py, web/e2e/mvp.spec.ts; docs permitted.

**Interfaces:** Existing API shapes/roles remain unchanged. `can_view_node` filters node serialization. Gates are included only if their node is visible. React roots include visible nodes with null or absent parent ID; breadcrumbs stop at missing parents. No invented permissions.

- [ ] Step1: Add natural RED role-read test: yu creates a task assigned to yu in the food seed project; ming reads detail and must receive exactly ming-owned seed task IDs, no yu-only phase/task IDs. Add gate exclusion for hidden gate node and reviewer/admin/readonly visibility preservation. Unit browser regression shows owned task whose parent is absent as a selectable root and kanban item.

```python
def test_member_detail_uses_existing_can_view_node(client):
    login(client, username='yu')
    project = client.get('/projects').json()['items'][0]
    admin_detail = client.get(f"/projects/{project['id']}").json()
    client.post('/auth/logout')
    login(client, username='ming', password='demo-ming')
    member_id = client.get('/auth/me').json()['user']['id']
    expected = {n['id'] for n in admin_detail['nodes'] if n['owner_user_id'] == member_id}
    detail = client.get(f"/projects/{project['id']}").json()
    assert {n['id'] for n in detail['nodes']} == expected
```

Add API MVP contract tests using existing client fixture: chen can update the QA seed task via department-head permission; ming can update/report own task and audit logs contain report.submit; ming cannot update/report an unrelated node; chen cannot approve an unrelated workflow gate; yu can approve it; readonly cannot status/report/create/gate writes; food IDs cannot access electronics projects/nodes/gates/reports/audit; forged organization params cannot expand scope. Keep each fixture isolated, preserve existing can_work behavior.
- [ ] Step2: Run pytest targeted and Vitest App test. Expected RED member IDs/hidden gates leak and orphan tree misses owned task. Existing correct role tests may already pass; record true counts.
- [ ] Step3: Apply read filtering before node/gate response serialization; use current permission helper rather than reimplementing policy. Update NodeTree root selection only when parent not in visible nodes, retaining child ordering and recursion. No backend models/migration changes.
- [ ] Step4: Move browser default URL to15175. Both existing health smoke and new MVP smoke check marker before any mutations:

```ts
test.beforeEach(async ({ request }) => {
  const marker = await request.get('/api/health/acceptance');
  expect(marker.status(), 'Acceptance requires the isolated test stack').toBe(200);
  expect(await marker.json()).toEqual({ acceptance: true });
});
```

Reject default shared15173 URL before E2E. Keep PF_BASE_URL for other loopback acceptance ports, gated by marker. Existing expected errors match exact endpoint/status/count (one initial me401 and one task409 per health workflow test); unexpected console/page errors fail.

New mvp.spec.ts at1280 and375 logs into separate contexts/pages as yu/chen/ming (real logins, no role state spoofing). Snapshot seed task status first. chen updates owned department task doing, ming sees own task but no other owner's phases and updates review; submit a report through same-context request and assert its scoped audit record. yu creates unique workflow project, demonstrates gate409, approves and updates task. chen unrelated gate approval403 and ming unrelated task403 are API-context assertions (no browser console noise). Readonly and cross-company boundaries are exercised. Restore seed status with yu in finally; snapshot user-preview15173 is not involved. Screenshots and overflow/pageerrors checks for each role. Authentication and failure payload assertions must not log tokens or passwords.
- [ ] Step5: Run all API/Vitest/build. Run isolated E2E RED for new member-view assertion against old container if needed, rebuild acceptance stack with launcher, then full E2E GREEN. Assert `/api/health/acceptance` on shared15173 is404 after its final refresh. Document role matrix and report/audit API-only limitations.
- [ ] Step6: Commit `P1c task 2: verify role boundaries and isolated workflows`; independent reviews and PROGRESS record.

## Task 3: Acceptance Command And Trial Handoff

**Files:** Create deploy/verify.py and docs/mvp-trial-checklist.md; modify api/tests/test_deployment.py, README.md, docs/formal-development.md, docs/PROGRESS.md.

**Interfaces:** `verify(root: Path, *, keep_running: bool = False) -> int`; CLI `api/.venv/Scripts/python.exe deploy/verify.py [--keep-running]`. Invokes isolated start, API tests, Vitest, build, E2E. Does not run E2E on15173 or delete volumes.

- [ ] Step1: Write RED tests proving verify command order, PF_BASE_URL is the returned acceptance web_url, pytest/npm failure returns nonzero, no later tests after failure, and cleanup targets only projectflow-acceptance with `down` without `-v`. keep_running avoids down. Startup failure must not stop an unrelated project; no raw secret error text appears.

```python
def test_acceptance_failure_keeps_failure_exit_and_safe_cleanup(tmp_path, verify_module, monkeypatch):
    calls = []
    monkeypatch.setattr(verify_module, 'start', lambda root, **kwargs: {
        'project': 'projectflow-acceptance', 'web_url': 'http://127.0.0.1:15175',
        'env_file': str(root/'.superpowers/p1c/acceptance.env')})
    def run(args, **kwargs):
        calls.append(args)
        return subprocess.CompletedProcess(args, 1 if 'pytest' in args else 0)
    monkeypatch.setattr(verify_module.subprocess, 'run', run)
    monkeypatch.setattr(verify_module.shutil, 'which', lambda name: name)
    result = verify_module.verify(tmp_path)
    assert result != 0
    assert not any('playwright' in str(args) or 'e2e' in args for args in calls)
    cleanup = calls[-1]
    assert 'projectflow-acceptance' in cleanup and 'down' in cleanup
    assert '-v' not in cleanup and 'projectflow-formal' not in cleanup
```

Implement tests with concrete stubs/CompletedProcess and verify args/env, not regex snapshots. Run targeted pytest RED.
- [ ] Step2: Implement verify with existing host interpreter, npm.cmd on Windows/npm elsewhere, argument arrays, named stages and inherited sanitized test output. Use launcher via import (same deploy directory), no dependency installer or alternate shell. Capture/sanitize orchestration failures, preserve nonzero return through finally; no global env mutation. Expected commands:

```python
[sys.executable, '-m', 'pytest', '-c', str(root/'api/pyproject.toml'), str(root/'api/tests'), '-q']
[npm, '--prefix', str(root/'web'), 'test']
[npm, '--prefix', str(root/'web'), 'run', 'build']
[npm, '--prefix', str(root/'web'), 'run', 'e2e']
```

- [ ] Step3: Write Traditional Chinese trial checklist with verified automated items, human-only trial signoff left unchecked, role account matrix, startup/acceptance commands, loopback-only limitations, API-only reports/audit, DB volume preservation, no cloud AI/ERP/AD. README quick start separates formal MVP from Demo and correctly reports P0-P1c automated delivery versus human acceptance.
- [ ] Step4: Full GREEN with `api/.venv/Scripts/python.exe deploy/verify.py --keep-running`. Refresh primary stack using `api/.venv/Scripts/python.exe deploy/start.py` without seed; it preserves existing data and remains15173. Confirm primary project/node snapshot unchanged across isolated run and marker404; acceptance marker200. Validate fresh acceptance startup/repeat startup preserves seed accounts/records and migrationhead. Check diff and no Demo changes.
- [ ] Step5: Commit `P1c task 3: add repeatable MVP acceptance handoff`; independent reviews, G4 fullbranch review/acceptance, ff-only merge, main verification and G6 docs/push under D50. Stop only task-owned acceptance services without deleting volume; leave primary Compose available.

## Completion Criteria

- One-command startup performs config validation, Compose build/wait, migration, optional seed and bounded readiness.
- Opt-in initialization contains admin yu and roles chen/ming/readonly; repeated startup preserves existing data/credentials.
- Acceptance runs in isolated Compose project and refuses non-acceptance API before mutations.
- Node read permission leak fixed using existing helper; assigned member task remains selectable without hidden parent.
- Real yu/chen/ming workflows and readonly/company boundaries pass API/browser checks at1280/375, without unexpected console/pageerrors or overflow.
- Automation summaries/exit codes, reviews, limits and human pending trial signoff are recorded; no claim to have simulated human approval or deployed to LAN.
- README/PROGRESS/checklist updated, independent reviews clean, ff-only main pushed. Existing shared historical test projects are not deleted.

## Self-Review

Spec P1c deliverables map to Tasks1(start/admin seed),2(roles/API/frontend smoke),3(repeatable acceptance/README/trial). Permission change applies existing can_view_node, no new role policy. File allowlist includes every product/test edit. Secrets stay in ignored env files. Only known acceptance project may be stopped; no volume deletion. Human trial signoff stays pending.
