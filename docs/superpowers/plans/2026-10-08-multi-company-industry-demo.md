# W6 多公司產業範例 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 將 ProjectFlow Demo 從單一寵物食品公司升級成五個固定、彼此隔離的公司空間，並讓各產業呈現自己的成員、專案、工作流、營運資料、稽核與附件。

**Architecture:** localStorage key 仍是 `projectflow-demo-v2`，內容升級為 v6 portfolio 容器；每家公司各自擁有 `db`、`audit`、`me`、成員、欄位權限與營運設定。執行期只把目前公司投影到既有的 `db`、`audit`、`USERS` 等全域名稱，藉此保留單檔 Demo 現有功能。切換公司先建立完整候選狀態並成功寫入，再一次換掉執行期投影；附件以公司前綴隔離，舊 v5 附件鍵保留給毛研食品。

**Tech Stack:** 原生 HTML/CSS/JavaScript；localStorage；IndexedDB；瀏覽器測試 `tests/records.html`、`tests/records.test.js`、`tests/departments.test.js`、新增 `tests/companies.test.js`；不需要建置工具。

**Spec:** `docs/superpowers/specs/2026-10-08-multi-company-industry-demo-design.md`

## Global Constraints

- 產品程式只改 `projectflow-full-demo.html`；`projectflow-petfood-demo.html` 不得修改。
- 測試只改 `tests/records.html`、`tests/records.test.js`、`tests/departments.test.js`，並新增 `tests/companies.test.js`。
- 文件只改 `README.md`、`docs/PROGRESS.md`、本 plan；若實作證明規格需修正，只能同步修訂本工作項目的 spec。
- 資料版本由 v5 升到 v6；`upgrade()` 必須接受 v2、v3、v4、v5 舊資料與部分損壞的 v6 容器。
- localStorage key 固定為 `projectflow-demo-v2`，不得新增第二個公司資料 key。
- 不新增外部函式庫或 CDN；介面文字一律繁體中文。
- 寫入目前公司 `db` 的使用者動作一律包在既有 `commit(label, fn)` 內，並呼叫 `log(nodeId, action, text)`。
- 權限沿用既有 `can(action, node)` 與 `canWork(node)`；切換公司後不得沿用前一公司的身分或權限物件。
- 輸出到 HTML 的公司、成員、專案、營運資料文字一律先經過 `esc()`。
- 公司切換與重設必須先成功持久化候選狀態，再更新畫面和執行期全域；寫入失敗時，不得出現半切換、資料丟失或附件先刪除。
- 每個 Task 都要依 WORKFLOW §3 完成 RED → GREEN → implementer 自檢 → spec reviewer → quality reviewer → 修正 → 記錄，並把實際 `#sum` 原文寫進 `docs/PROGRESS.md`。
- 每個 Task 使用 plan 指定的 commit 主旨；`git add` 必須列明確檔案，不使用 `-A` 或 `.`。
- 依 D2 在主 checkout 建立 `feature/w6-multi-company-industry-demo`，不用 worktree；不得 push。
- 展示模式只允許一輪 reviewer 與一輪修正，但 375px 行動版仍是必要驗收。

## Review Focus

1. **原子持久化失敗**：Task 2 必須注入 localStorage 寫入失敗，證明公司、身分、頁面和 undo 都維持原狀。
2. **部分損壞的 v6 修復**：Task 1 必須證明只補回缺失／無效的公司，不覆蓋其他公司已有的自訂資料。
3. **跨公司 ID 碰撞與資料外洩**：Task 6 必須刻意建立同 ID 節點、營運記錄與敏感文字，檢查頁面、權限、AI、稽核只讀目前公司。
4. **附件與重設隔離**：Task 5 必須同時驗證新公司前綴鍵、舊 v5 毛研食品鍵、重設單一公司及寫入失敗時不先刪附件。
5. **惡意／損壞營運資料**：Task 4 必須驗證未知 module、遺失 record、HTML payload 與不存在的 link 不會崩潰或直接輸出未跳脫文字。

---

## File Structure

- Modify `projectflow-full-demo.html`
  - v6 容器與執行期投影：`seed()`、`seedPortfolio()`、`upgrade()`、`load()`、`save()`、`activateCompany()`。
  - 公司選擇器：`renderMe()`、`switchCompany()`、`resetTransientCompanyUI()` 與 change 委派。
  - 五產業資料：公司定義、成員、部門、專案、工作流、稽核及營運種子 helper。
  - 產業營運頁：保留毛研食品 F10，新增設定驅動的通用 renderer、狀態推進、連結與條件判斷。
  - 附件與重設：IndexedDB 公司前綴、舊鍵相容、只重設目前公司。
  - 隔離掃描：移除非毛研食品公司對 `db.ops.pos`、配方、工單等硬編碼路徑的依賴。
- Modify `tests/records.html`
  - 在既有測試後載入 `tests/companies.test.js`。
- Modify `tests/records.test.js`
  - 將 v5 升級斷言改成 v6 portfolio 路徑；保留既有 149 項功能驗證。
- Modify `tests/departments.test.js`
  - 將需要 `upgrade()` 回傳單一 db 的斷言改成 `companies.petfood.db`。
- Create `tests/companies.test.js`
  - 放置 W6 的資料遷移、切換、五產業、營運、附件及隔離測試，共新增 25 項；最終目標為基準 149 + 25 = `全部通過 174/174`。
- Modify `README.md`
  - 更新 Demo 操作、資料版本與固定五公司限制。
- Modify `docs/PROGRESS.md`
  - 每個 Task 記 RED、GREEN、review、commit 與下一步；最後記 G4–G6 驗收結果。

---

### Task 0: Execution Preflight and Branch Setup

**Files:**
- Modify: `docs/PROGRESS.md`

- [ ] **Step 1: Verify the historical feature branch is already integrated**

Run:

```powershell
git status --short --branch
git merge-base --is-ancestor feature/w3-workflow-architecture main
git log -1 --oneline feature/w3-workflow-architecture
```

Expected: working tree clean; `merge-base` exits 0. If it does not, stop and record the conflict in PROGRESS §6 before asking the human.

- [ ] **Step 2: Preserve the completed branch under a non-active name**

Run:

```powershell
git branch -m feature/w3-workflow-architecture completed/w3-workflow-architecture
git branch --list "feature/*"
```

Expected: no `feature/*` branch remains. This only renames the local historical branch and does not push.

- [ ] **Step 3: Record W6 execution start and create its branch**

Update PROGRESS W6 to `🔧 實作中`, set the next action to Task 1 RED, add the plan link, and add six Task rows with all states `⬜`.

Run:

```powershell
git add docs/PROGRESS.md
git commit -m "Progress: start W6 implementation" -m "Co-Authored-By: Codex <noreply@openai.com>"
git checkout -b feature/w6-multi-company-industry-demo
```

- [ ] **Step 4: Run the unmodified baseline**

Serve the repository per WORKFLOW §5 and load `tests/records.html?t=20261008w6baseline`.

Expected baseline: `全部通過 149/149`. Record the exact `#sum` text in PROGRESS. If the baseline differs, stop before product edits and diagnose it.

---

### Task 1: v6 Company Container and Legacy Migration

**Files:**
- Modify: `projectflow-full-demo.html` around `TAGS`, `USERS`, `FIELD_ACCESS`, `seed()`, `upgrade()`, `load()`, `save()`, `resetAll()`
- Modify: `tests/records.html`
- Modify: `tests/records.test.js`
- Modify: `tests/departments.test.js`
- Create: `tests/companies.test.js`

**Interfaces:**
- Produces:
  - `COMPANY_ORDER: string[]`
  - `COMPANY_META: Record<string, {id,name,industry,defaultUserId}>`
  - `seedCompany(companyId): CompanyState`
  - `seedPortfolio(): PortfolioV6`
  - `upgradeLegacy(payload): LegacyV5Payload`
  - `upgrade(payload, repairedIds?): PortfolioV6`
  - `repairPortfolio(portfolio, repairedIds?): PortfolioV6`
  - `activateCompany(companyId, options?): void`
  - `activeCompanySnapshot(): CompanyState`
  - `syncActiveCompany(candidate): PortfolioV6`
  - `persistPortfolio(candidate): boolean`
- Runtime aliases: `company`, `db`, `audit`, `USERS`, `FIELD_ACCESS`, `TAGS`, `TAG_DEPT`, `OPS_CONFIG`
- Preserves: `seed()` returns a fresh petfood `db` so existing tests and helpers stay usable.

- [ ] **Step 1: Register the W6 test file**

In `tests/records.html`, extend the existing fetched-test array so the new suite runs in the same Demo iframe after the prior suites:

```js
for (const f of ['records.test.js', 'departments.test.js', 'companies.test.js']) {
```

Create `tests/companies.test.js` with the same `T()`, `ok()`, `eq()`, `resetAll()` conventions as the existing test files and a final marker comment:

```js
  // ── 新測試加在這一行上面 ──
```

- [ ] **Step 2: Write failing migration and repair tests**

Add this legacy-payload helper and the tests below:

```js
function makeLegacyPayload(version){
  const d = seed();
  d.v = version;
  d.nodes.p1.title = `保留 v${version} 節點`;
  if(version < 5) delete d.workflows;
  if(version < 4){
    delete d.departments;
    Object.values(d.nodes).forEach(n => { delete n.dept; });
    d.templates.forEach(t => t.nodes.forEach(n => { delete n.dept; }));
  }
  if(version < 3){
    delete d.reportFields; delete d.reports; delete d.notes; delete d.attachments;
    d.overrides.forEach(x => { delete x.kind; });
  }
  return {
    payload: {v:version, db:d, audit:freshAudit(), me:'yu'},
    expectedTitle: `保留 v${version} 節點`,
    expectedMe: 'yu'
  };
}

await T('W6：v6 容器固定包含五家公司', () => {
  const p = seedPortfolio();
  eq(p.v, 6);
  eq(p.activeCompanyId, 'petfood');
  eq(Object.keys(p.companies).sort(), ['construction','electronics','events','petfood','software']);
  eq(p.companies.petfood.me, 'yu');
  eq(p.companies.petfood.db.v, 6);
});

await T('W6：v5 升級完整保留毛研資料與舊附件鍵', () => {
  const oldDb = seed();
  oldDb.v = 5;
  oldDb.nodes.p1.title = '人類保留節點';
  oldDb.attachments.push({ id:'legacy-file', node_id:'p1', report_id:null, note_id:null, filename:'舊附件.pdf', mime:'application/pdf', size:12, sha256:'', storage_key:'legacy-file', uploaded_by:'yu', uploaded_at:'2026/10/08 08:00', deleted_at:null });
  const oldAudit = freshAudit();
  oldAudit.acts.unshift({ at:'2026/10/08 08:00', actor:'yu', node:'p1', action:'測試', text:'保留稽核' });
  const p = upgrade({ v:5, db:oldDb, audit:oldAudit, me:'lin' });
  eq(p.v, 6);
  eq(p.companies.petfood.db.nodes.p1.title, '人類保留節點');
  eq(p.companies.petfood.db.attachments.find(a => a.id === 'legacy-file').storage_key, 'legacy-file');
  eq(p.companies.petfood.audit.acts[0].text, '保留稽核');
  eq(p.companies.petfood.me, 'lin');
  eq(p.companies.electronics.id, 'electronics');
});

await T('W6：部分損壞 v6 只修補壞公司', () => {
  const p = seedPortfolio();
  p.companies.petfood.db.nodes.p1.title = '不可被蓋掉';
  p.companies.events = null;
  delete p.companies.software;
  p.activeCompanyId = 'missing';
  const repaired = [];
  const fixed = upgrade(p, repaired);
  eq(fixed.companies.petfood.db.nodes.p1.title, '不可被蓋掉');
  eq(fixed.companies.events.id, 'events');
  eq(fixed.companies.software.id, 'software');
  eq(fixed.activeCompanyId, 'petfood');
  eq(repaired.sort(), ['events','software']);
});

await T('W6：v2 到 v4 都能逐版升到 v6', () => {
  [2, 3, 4].forEach(version => {
    const legacy = makeLegacyPayload(version);
    const p = upgrade(legacy.payload);
    eq(p.v, 6, `v${version} 容器版本`);
    eq(p.companies.petfood.db.nodes.p1.title, legacy.expectedTitle, `v${version} 節點保留`);
    eq(p.companies.petfood.me, legacy.expectedMe, `v${version} 身分保留`);
  });
});
```

Update existing upgrade assertions in `records.test.js` and `departments.test.js` from `o.db` to `o.companies.petfood.db`, and expected version from 5 to 6. Do not remove any behavioral assertion. Task 1 adds exactly 4 W6 tests.

- [ ] **Step 3: Run tests to verify RED**

Load `tests/records.html?t=20261008w6t1red`.

Expected RED: the new W6 tests fail because `seedPortfolio` and v6 company storage do not exist. Record the exact `#sum` text in PROGRESS before implementation.

- [ ] **Step 4: Add metadata and v6 shapes**

Add stable metadata near the current user and field constants:

```js
const COMPANY_ORDER = ['petfood','electronics','events','software','construction'];
const COMPANY_META = {
  petfood:      { id:'petfood',      name:'毛研食品', industry:'寵物食品製造', defaultUserId:'yu' },
  electronics:  { id:'electronics',  name:'峰曜科技', industry:'電子產品製造', defaultUserId:'el-lin' },
  events:       { id:'events',       name:'光點企劃', industry:'活動行銷',     defaultUserId:'ev-jia' },
  software:     { id:'software',     name:'雲序軟體', industry:'SaaS 軟體服務', defaultUserId:'sw-yi' },
  construction: { id:'construction', name:'築衡工程', industry:'營建工程',     defaultUserId:'ct-chen' },
};
```

Rename the current petfood seed constants to `PETFOOD_TAGS`, `PETFOOD_USERS`, `PETFOOD_FIELD_ACCESS` and `PETFOOD_TAG_DEPT`. Initialize mutable runtime aliases from them:

```js
let TAGS = PETFOOD_TAGS;
let USERS = PETFOOD_USERS;
let FIELD_ACCESS = PETFOOD_FIELD_ACCESS;
let TAG_DEPT = PETFOOD_TAG_DEPT;
let OPS_CONFIG = { mode:'petfood' };
```

The petfood `seed()` builder and v2→v5 legacy migrations must read the `PETFOOD_*` constants directly, so calling `seedPortfolio()` while another company is active cannot seed petfood nodes with the wrong users or departments. Shared rendering and permission helpers continue reading the active aliases.

Use this persisted shape:

```js
{
  v: 6,
  activeCompanyId: 'petfood',
  companies: {
    petfood: {
      id: 'petfood',
      name: '毛研食品',
      industry: '寵物食品製造',
      defaultUserId: 'yu',
      me: 'yu',
      users: {},
      fieldAccess: {},
      tags: [],
      tagDept: {},
      opsConfig: {},
      db: {},
      audit: {}
    }
  }
}
```

For Task 1, `seedCompany()` may give the four new companies valid minimal shells with their real `defaultUserId`, one matching owner user, one matching department, `db.nodes = {}`, `db.deps = []`, empty workflows/templates and compatible empty legacy ops arrays. This lets Task 2 switch identity and render empty states safely before Task 3 adds full content. Projects continue to be root nodes with `type === 'project'`; do not introduce a parallel `db.projects` collection.

- [ ] **Step 5: Implement migration, repair, projection and persistence**

Keep the current v2→v5 migration in `upgradeLegacy()`. Then implement v6 conversion with these rules:

```js
function validCompanyState(x, id){
  return !!(x && x.id === id && x.defaultUserId && x.db && x.db.nodes && Array.isArray(x.db.deps)
    && Array.isArray(x.db.departments) && Array.isArray(x.db.workflows) && Array.isArray(x.db.attachments)
    && x.audit && Array.isArray(x.audit.acts) && x.users && typeof x.users === 'object');
}

function repairPortfolio(input, repairedIds = []){
  const out = structuredClone(input);
  out.v = 6;
  out.companies = out.companies && typeof out.companies === 'object' ? out.companies : {};
  COMPANY_ORDER.forEach(id => {
    if(!validCompanyState(out.companies[id], id)){
      out.companies[id] = seedCompany(id);
      repairedIds.push(id);
    }
    out.companies[id].db.v = 6;
  });
  if(!COMPANY_ORDER.includes(out.activeCompanyId)) out.activeCompanyId = 'petfood';
  return out;
}
```

Do not use JSON round-tripping for values that can be cloned with `structuredClone()`. If the browser lacks it, use the project’s existing JSON-safe data shape through one `cloneData()` helper.

`activateCompany()` must assign all active aliases from one company state and preserve `state.me` on reload unless `options.resetIdentity === true` or the saved member no longer exists. `activeCompanySnapshot()` returns a cloned company state with the current `db`, `audit`, `ui.me`, users, field access, tags, tag-department map and operations config. `syncActiveCompany(candidate)` writes that snapshot into a candidate clone and returns the candidate; it must not mutate the live `portfolio`.

`persistPortfolio(candidate)` returns `true` only after `localStorage.setItem(KEY, JSON.stringify(candidate))` succeeds. On exception it returns `false`; it must not mutate `portfolio` or show UI itself, so callers can choose the correct message. `save()` clones `portfolio`, calls `syncActiveCompany(candidate)`, persists it, and only then replaces the live container reference; current `db` and `audit` aliases remain the same active objects.

`load()` passes a fresh `repairedIds` array into `upgrade()`. After the first successful render, show one warning toast naming the repaired companies; do not persist `repairedIds` in the v6 payload.

Update `resetAll()` in this task so the existing test harness gets a fresh `seedPortfolio()`, activates petfood with user `yu`, clears transient UI/undo and clears the IndexedDB test store. Task 5 later disconnects the product reset button from this test helper and adds active-company-only reset.

- [ ] **Step 6: Run focused and full GREEN**

Load `tests/records.html?t=20261008w6t1green`.

Expected: all existing tests plus Task 1 tests pass. Verify the existing petfood Demo still loads from a cleared origin and from an injected v5 payload.

- [ ] **Step 7: Review, record and commit**

Run the WORKFLOW §3 review prompts with special attention to Review Focus 2. Apply the one allowed correction round, rerun the full suite, update PROGRESS, then commit:

```powershell
git add projectflow-full-demo.html tests/records.html tests/records.test.js tests/departments.test.js tests/companies.test.js docs/PROGRESS.md
git commit -m "W6 task 1: add v6 company storage" -m "Co-Authored-By: Codex <noreply@openai.com>"
```

---

### Task 2: Company Selector and Atomic Switching

**Files:**
- Modify: `projectflow-full-demo.html` around `ui`, `renderMe()`, `render()`, change delegation
- Modify: `tests/companies.test.js`

**Interfaces:**
- Produces:
  - `resetTransientCompanyUI(): void`
  - `switchCompany(companyId, writer = persistPortfolio): {ok:boolean,error?:string}`
  - `<select id="companySel">`
- Consumes: `portfolio`, `company`, `activateCompany()`, `syncActiveCompany(candidate)`, `render()`, `COMPANY_ORDER`, `COMPANY_META`

- [ ] **Step 1: Write failing UI and transaction tests**

Add tests for all of these outcomes:

```js
await T('W6：公司選擇器位於身分選擇器上方', () => {
  render();
  const companySel = document.querySelector('#companySel');
  const meSel = document.querySelector('#meSel');
  ok(companySel && meSel, '兩個選擇器都應存在');
  ok(companySel.compareDocumentPosition(meSel) & Node.DOCUMENT_POSITION_FOLLOWING, '公司要在身分上方');
  eq([...companySel.options].map(x => x.textContent), [
    '毛研食品｜寵物食品製造','峰曜科技｜電子產品製造','光點企劃｜活動行銷',
    '雲序軟體｜SaaS 軟體服務','築衡工程｜營建工程'
  ]);
});

await T('W6：切換公司使用目標預設負責人並清空暫態 UI', () => {
  ui.page = 'ops'; ui.node = 'p1'; ui.connect = {from:'p1'}; ui.opsTab = 'po'; ui.chat = [{role:'user',text:'舊公司'}];
  undoStack.push({ label:'舊公司動作', snap:JSON.stringify(db) });
  const result = switchCompany('electronics');
  ok(result.ok, '切換應成功');
  eq(company.id, 'electronics');
  eq(me().id, 'el-lin');
  eq(ui.page, 'overview');
  eq(ui.node, null);
  eq(ui.connect, null);
  eq(ui.chat.length, 0);
  eq(undoStack.length, 0);
});

await T('W6：公司資料來回切換會持久化且不互改', () => {
  projects()[0].title = '毛研自訂名稱'; save();
  switchCompany('electronics');
  const electronicsName = projects()[0]?.title;
  switchCompany('petfood');
  eq(projects()[0].title, '毛研自訂名稱');
  ok(electronicsName !== '毛研自訂名稱', '不同公司不得共用專案物件');
  load();
  eq(company.id, 'petfood');
  eq(projects()[0].title, '毛研自訂名稱');
});

await T('W6：持久化失敗時公司切換完全不生效', () => {
  ui.page = 'ops'; ui.node = 'p1'; undoStack.push({label:'保留', snap:JSON.stringify(db)});
  const before = { company:company.id, me:me().id, page:ui.page, node:ui.node, undo:undoStack.length };
  const result = switchCompany('electronics', () => false);
  ok(!result.ok, '切換應失敗');
  eq(company.id, before.company); eq(me().id, before.me);
  eq(ui.page, before.page); eq(ui.node, before.node); eq(undoStack.length, before.undo);
});
```

- [ ] **Step 2: Run tests to verify RED**

Load `tests/records.html?t=20261008w6t2red` and record the exact `#sum`. Expected failures: missing selector and `switchCompany()`.

- [ ] **Step 3: Render the selector above identity**

In `renderMe()`, render one compact select with label `切換公司（Demo，用來體驗不同產業）` before `#meSel`. Every option value uses the stable company ID and its text uses `esc(meta.name)` plus `esc(meta.industry)`. Match the existing sidebar density and controls; do not add a marketing card or explanatory paragraph.

- [ ] **Step 4: Implement transactional switching**

Implement this sequence without mutating live aliases before the write succeeds:

```js
function switchCompany(targetId, writer = persistPortfolio){
  if(!COMPANY_ORDER.includes(targetId)) return { ok:false, error:'找不到公司' };
  if(targetId === company.id) return { ok:true };
  const candidate = syncActiveCompany(cloneData(portfolio));
  candidate.activeCompanyId = targetId;
  candidate.companies[targetId].me = COMPANY_META[targetId].defaultUserId;
  if(!writer(candidate)) return { ok:false, error:'無法儲存公司切換' };
  portfolio = candidate;
  activateCompany(targetId, { resetIdentity:true });
  resetTransientCompanyUI();
  render();
  return { ok:true };
}
```

`resetTransientCompanyUI()` must reset page to overview and clear selected node, search, ops tab, open menu/dialog/chat/import state, AI draft/stream state, notifications tied to the old company and the undo stack. It must not clear persisted data.

Add a `change` handler for `#companySel`. On success show `已切換至〈公司名稱〉`; on failure restore the select value to `company.id` and show `資料無法儲存，尚未切換公司`.

Task 2 adds exactly 4 W6 tests.

- [ ] **Step 5: Run GREEN and manual switching checks**

Load `tests/records.html?t=20261008w6t2green`. Then manually switch all five options at desktop width and 375px. Verify the select text fits, the target company opens overview, and switching back restores petfood edits.

- [ ] **Step 6: Review, record and commit**

Run the required review round with Review Focus 1, rerun the full suite, update PROGRESS, then commit:

```powershell
git add projectflow-full-demo.html tests/companies.test.js docs/PROGRESS.md
git commit -m "W6 task 2: add company switching" -m "Co-Authored-By: Codex <noreply@openai.com>"
```

---

### Task 3: Five Industry Seed Workspaces

**Files:**
- Modify: `projectflow-full-demo.html` around company seed helpers
- Modify: `tests/companies.test.js`

**Interfaces:**
- Produces:
  - `COMPANY_SEEDS`
  - `seedIndustryCompany(companyId): CompanyState`
  - `buildIndustryProject(db, definition): string` returning the root project node ID
  - `buildIndustryWorkflow(definition): Workflow`
- Consumes: existing node, dependency, gate, report, note, department and workflow shapes.

- [ ] **Step 1: Write failing five-company completeness tests**

Test exact company counts and representative content:

```js
await T('W6：五家公司符合專案與工作流最低量且角色完整', () => {
  const p = seedPortfolio();
  COMPANY_ORDER.forEach(id => {
    const c = p.companies[id];
    const projectCount = Object.values(c.db.nodes).filter(n => n.type === 'project').length;
    if(id === 'petfood') ok(projectCount >= 2, '毛研既有豐富專案必須保留');
    else eq(projectCount, 2, `${id} 專案數`);
    eq(c.db.workflows.length, 2, `${id} 工作流數`);
    const roles = new Set(Object.values(c.users).map(u => u.role));
    ['owner','reviewer','member','collab','admin'].forEach(role => ok(roles.has(role), `${id} 缺少 ${role}`));
    ok(c.db.departments.length >= 9, `${id} 部門不足`);
  });
});

await T('W6：各產業主專案含關卡、前置、報告、註記、稽核與營運連結', () => {
  const p = seedPortfolio();
  COMPANY_ORDER.forEach(id => {
    const c = p.companies[id];
    const nodes = Object.values(c.db.nodes);
    const root = nodes.find(n => n.type === 'project');
    ok(root, `${id} 主專案 root`);
    ok(nodes.some(n => n.type === 'gate'), `${id} 關卡`);
    ok(nodes.some(n => Array.isArray(n.deps) && n.deps.length), `${id} 前置`);
    ok(c.db.reports.some(r => nodes.some(n => n.id === r.node_id)), `${id} 報告`);
    ok(c.db.notes.some(note => nodes.some(n => n.id === note.node_id)), `${id} 註記`);
    ok(nodes.some(n => Array.isArray(n.links) && n.links.length), `${id} 營運連結`);
    ok(c.audit.acts.length, `${id} 稽核`);
  });
});

await T('W6：非毛研公司不引用毛研成員', () => {
  const p = seedPortfolio();
  const petIds = new Set(Object.keys(p.companies.petfood.users));
  COMPANY_ORDER.slice(1).forEach(id => {
    const serialized = JSON.stringify(p.companies[id].db.nodes);
    petIds.forEach(uid => ok(!serialized.includes(`\"${uid}\"`), `${id} 不得引用 ${uid}`));
  });
});
```

Task 3 adds exactly 5 W6 tests. Add the remaining two with these assertions:

```js
await T('W6：四個新產業部門名稱正確', () => {
  const p = seedPortfolio();
  const expected = {
    electronics: ['產品企劃','硬體研發','工業設計','採購','品保','製造','認證','業務','資訊','財務'],
    events: ['策略企劃','創意','客戶服務','活動製作','媒體','公關','採購','財務','資訊'],
    software: ['產品','前端','後端','品質保證','DevOps','資安','客戶成功','業務','資訊'],
    construction: ['專案管理','設計','機電','採購','工務','品管','職安','財務','行政','資訊']
  };
  Object.entries(expected).forEach(([id, names]) => eq(p.companies[id].db.departments.map(d => d.name), names, id));
});

await T('W6：五家公司種子標題與營運連結有效', () => {
  const p = seedPortfolio();
  const expected = {
    petfood: ['成貓主食罐・鮪魚雞肉','高齡犬關節保健罐','筆電新機種專流'],
    electronics: ['AstraBook AI 筆電 NPI','65W 充電器降本','筆電 NPI 專流'],
    events: ['夏季新品發表會','年度經銷商大會','活動執行專流'],
    software: ['企業 SSO 上線','通知中心改版','版本發佈專流'],
    construction: ['總部辦公室裝修','空調主機汰換','裝修工程專流']
  };
  Object.entries(expected).forEach(([id, [main, secondary, workflow]]) => {
    const c = p.companies[id];
    const titles = Object.values(c.db.nodes).filter(n => n.type === 'project').map(n => n.title);
    ok(titles.includes(main) && titles.includes(secondary), `${id} 專案標題`);
    ok(c.db.workflows.some(w => w.name === workflow), `${id} 工作流標題`);
    Object.values(c.db.nodes).flatMap(n => n.links || []).forEach(link => {
      const found = id === 'petfood'
        ? ({supplier:'suppliers',formula:'formulas',po:'pos',wo:'wos'}[link.t]
          && c.db.ops[{supplier:'suppliers',formula:'formulas',po:'pos',wo:'wos'}[link.t]].some(r => r.id === link.id))
        : (c.db.ops.records[link.t] || []).some(r => r.id === link.id);
      ok(found, `${id} 找不到 ${link.t}/${link.id}`);
    });
  });
});
```

- [ ] **Step 2: Run tests to verify RED**

Load `tests/records.html?t=20261008w6t3red`. Record the exact failing summary; the four new company shells should fail project/workflow/content assertions.

- [ ] **Step 3: Define company members and departments**

Use stable IDs and keep every company independent:

| Company | Members |
|---|---|
| 峰曜科技 | `el-lin` 林怡君 owner／產品企劃；`el-hao` 陳志豪 member／硬體研發；`el-mei` 張雅雯 reviewer／品保；`el-kai` 黃冠凱 member／採購；`el-ting` 吳佳庭 collab／業務；`el-it` 資訊室 admin／資訊 |
| 光點企劃 | `ev-jia` 許嘉玲 owner／策略企劃；`ev-bo` 周柏宇 member／創意；`ev-xin` 李欣怡 member／客戶服務；`ev-wei` 劉威廷 member／活動製作；`ev-ru` 蔡佩如 reviewer／財務；`ev-an` 黃筱安 collab／公關；`ev-it` 資訊室 admin／資訊 |
| 雲序軟體 | `sw-yi` 王怡文 owner／產品；`sw-jun` 李明駿 member／後端；`sw-ting` 陳雅婷 member／前端；`sw-hao` 黃信豪 reviewer／品質保證；`sw-yan` 林子彥 member／DevOps；`sw-an` 張安琪 collab／資安；`sw-it` 資訊室 admin／資訊 |
| 築衡工程 | `ct-chen` 陳建宏 owner／專案管理；`ct-lin` 林芷晴 member／設計；`ct-wu` 吳俊達 member／機電；`ct-huang` 黃冠宇 member／工務；`ct-tsai` 蔡美玲 reviewer／品管；`ct-an` 周安琪 collab／職安；`ct-it` 資訊室 admin／資訊 |

Department names must be exactly:

| Company | Departments |
|---|---|
| 峰曜科技 | 產品企劃、硬體研發、工業設計、採購、品保、製造、認證、業務、資訊、財務 |
| 光點企劃 | 策略企劃、創意、客戶服務、活動製作、媒體、公關、採購、財務、資訊 |
| 雲序軟體 | 產品、前端、後端、品質保證、DevOps、資安、客戶成功、業務、資訊 |
| 築衡工程 | 專案管理、設計、機電、採購、工務、品管、職安、財務、行政、資訊 |

Create independent `fieldAccess`, tag and tag-department maps from each company’s departments. Never reuse mutable arrays or objects between companies.

- [ ] **Step 4: Seed balanced projects and workflows**

Implement these exact content sets through declarative definitions passed to `buildIndustryProject()` and `buildIndustryWorkflow()`:

| Company | Complete main project | Simpler secondary project | Workflows |
|---|---|---|---|
| 峰曜科技 | `AstraBook AI 筆電 NPI`：市場立案、產品定義、設計開發、試產驗證、量產上市；包含市場／競品、Business Case、目標成本、PRD、工業設計、法規盤點、PCB、散熱、韌體、EVT、可靠度、認證、DVT/PVT、首批量產、上市 | `65W 充電器降本`：成本分析、替代料驗證、ECN 發行 | 筆電 NPI 專流、ECN 變更專流 |
| 光點企劃 | `夏季新品發表會`：策略與 brief、創意與場地、供應商製作、宣傳與報名、彩排與活動、結案；包含受眾/KPI、預算、主題、場地、視聽舞台、物料、宣傳、報名、彩排、執行、結案 | `年度經銷商大會`：議程、講者、場地、執行 | 活動執行專流、整合行銷專流 |
| 雲序軟體 | `企業 SSO 上線`：需求探索、設計開發、測試資安、發佈、監控；包含需求與 IdP、後端、前端管理頁、自動測試、滲透測試、staging、production 部署、監控 | `通知中心改版`：需求、開發、測試、上線 | 版本發佈專流、事件處理專流 |
| 築衡工程 | `總部辦公室裝修`：設計、採購、施工、查驗、交付；包含現勘、圖說、預算、承包商、材料、拆除、機電、裝修、職安、查驗、缺失改善、點交 | `空調主機汰換`：評估、採購、施工、驗收 | 裝修工程專流、變更與查驗專流 |

Each main project must include at least one gate that depends on an operations record, one hard task dependency, one report, one note, one audit entry and one operations link. Each secondary project must remain navigable and contain at least two phases.

- [ ] **Step 5: Run GREEN and inspect all company pages**

Load `tests/records.html?t=20261008w6t3green`. Manually visit overview, timeline, workflow library, reports, review center and member identity options in every company. Verify no petfood names appear in the other four companies.

- [ ] **Step 6: Review, record and commit**

Review for shared mutable data, broken node references and accidental cross-company member IDs. Rerun the full suite, update PROGRESS, then commit:

```powershell
git add projectflow-full-demo.html tests/companies.test.js docs/PROGRESS.md
git commit -m "W6 task 3: seed five industry companies" -m "Co-Authored-By: Codex <noreply@openai.com>"
```

---

### Task 4: Config-Driven Industry Operations

**Files:**
- Modify: `projectflow-full-demo.html` around `condMet()`, `linkedNodes()`, `pageOps()`, operations events and link cards
- Modify: `tests/companies.test.js`

**Interfaces:**
- Produces:
  - `OPS_CONFIG` active alias
  - `opsModule(moduleId)`
  - `opsRecords(moduleId)`
  - `opsRecord(moduleId, recordId)`
  - `pagePetfoodOps()`
  - `pageGenericOps()`
  - `renderOpsValue(record, column)`
  - `advanceOpsRecord(moduleId, recordId)`
- Extends:
  - `pageOps()` dispatches on `OPS_CONFIG.mode`
  - `condMet()` accepts `{kind:'ops',module,id,field,need,label}`
  - node links continue using `{t,id}` where `t` is the module ID.

- [ ] **Step 1: Write failing module, safety and condition tests**

Assert exact module labels:

| Company | Modules |
|---|---|
| 峰曜科技 | 供應商、零件、BOM、採購單、試產批次、驗證項目 |
| 光點企劃 | 供應商、場地、預算、採購、場次、交付物 |
| 雲序軟體 | 需求、版本、缺陷、環境、部署、事件 |
| 築衡工程 | 承包商、材料、合約、工單、查驗、變更單 |

Add these behavior tests:

```js
await T('W6：四個新產業各有六個正確營運模組', () => {
  const expected = {
    electronics: ['供應商','零件','BOM','採購單','試產批次','驗證項目'],
    events: ['供應商','場地','預算','採購','場次','交付物'],
    software: ['需求','版本','缺陷','環境','部署','事件'],
    construction: ['承包商','材料','合約','工單','查驗','變更單']
  };
  Object.entries(expected).forEach(([id, labels]) => {
    switchCompany(id);
    eq(OPS_CONFIG.modules.map(m => m.label), labels, id);
    ok(OPS_CONFIG.modules.every(m => m.columns.every(c => c.key && c.label && c.type)), `${id} 欄位定義`);
  });
});

await T('W6：通用營運頁跳脫文字並容忍未知資料', () => {
  switchCompany('software');
  db.ops.records.requirement[0].title = '<img src=x onerror=alert(1)>';
  ui.opsTab = 'requirement';
  const html = pageOps();
  ok(html.includes('&lt;img'), '營運文字必須跳脫');
  ok(!html.includes('<img src=x'), '不得輸出原始標籤');
  eq(opsRecords('missing').length, 0);
  eq(opsRecord('requirement', 'missing'), null);
});

await T('W6：通用營運條件由狀態推進解除', () => {
  switchCompany('software');
  const cond = {kind:'ops',module:'deployment',id:'SW-DEP-PROD',field:'status',need:'已完成',label:'正式環境部署'};
  ok(!condMet(cond), '部署前應阻擋');
  let steps = 0;
  while(!condMet(cond) && steps < 6){ advanceOpsRecord('deployment', 'SW-DEP-PROD'); steps += 1; }
  ok(steps < 6, '狀態流程應在有限步驟內完成');
  ok(condMet(cond), '推進後應通過');
  ok(Object.values(audit).flat().some(x => x.text.includes('SW-DEP-PROD')), '推進要寫稽核');
});

await T('W6：毛研食品仍使用完整配方採購工單追溯頁', () => {
  switchCompany('petfood');
  const html = pageOps();
  ['配方','採購單','工單','追溯'].forEach(text => ok(html.includes(text), `缺少 ${text}`));
});
```

Task 4 adds exactly 4 W6 tests: `W6：四個新產業各有六個正確營運模組`, the two generic behavior tests shown above, and the petfood regression test.

- [ ] **Step 2: Run tests to verify RED**

Load `tests/records.html?t=20261008w6t4red` and record the exact `#sum`. Expected: generic company modules and generic condition helpers fail.

- [ ] **Step 3: Add serializable operations configurations and records**

Each non-petfood company gets:

```js
opsConfig: {
  mode: 'generic',
  title: '產品營運資料',
  description: '峰曜科技的供應鏈、試產與驗證記錄',
  modules: [{
    id: 'verification',
    label: '驗證項目',
    description: '試產後的品質、可靠度與認證結果',
    columns: [
      {key:'id', label:'編號', type:'text'},
      {key:'title', label:'項目', type:'text'},
      {key:'owner', label:'負責人', type:'member'},
      {key:'status', label:'狀態', type:'status'},
      {key:'cost', label:'驗證費用', type:'money', access:'cost'}
    ],
    flow: ['待驗證','驗證中','待複驗','通過'],
    syncLabel: '推進驗證狀態',
    events: [{recordId:'EL-V-THERMAL',atStatus:'通過',targetNodeId:'el-gate-verify',text:'散熱驗證已通過，可重新檢查試產 Gate'}]
  }]
}
```

Use the same schema with company-specific title, description, six modules and columns. `type` supports `text`, `date`, `number`, `money`, `member`, `status` and `progress`; optional `access` names a key in active `FIELD_ACCESS`. Persist generic records in `db.ops.records[moduleId]`. `events` defines record/status-triggered notification text and target nodes without branching on company ID.

Required blocking records:

- Electronics: `EL-V-THERMAL`, module `verification`, starts `待複驗`, reaches `通過`.
- Events: `EV-D-STAGE`, module `deliverable`, starts `待核准`, reaches `已核准`.
- Software: `SW-DEP-PROD`, module `deployment`, starts `待核准`, reaches `已完成`.
- Construction: `CT-INSP-FIRE`, module `inspection`, starts `待複驗`, reaches `通過`.

Attach each condition to a main-project gate or task and link that node back to the same record.

- [ ] **Step 4: Preserve petfood F10 and add the generic renderer**

Rename the existing specialized `pageOps()` body to `pagePetfoodOps()`. Add this dispatcher:

```js
function pageOps(){
  return OPS_CONFIG?.mode === 'petfood' ? pagePetfoodOps() : pageGenericOps();
}
```

`pageGenericOps()` renders tabs from `OPS_CONFIG.modules`, chooses the first valid module when `ui.opsTab` is invalid, and renders a compact table/list from declared columns. It must pass labels and values through `esc()`, format only declared types, and mask a column when `column.access` exists and `seeField(column.access)` is false. Empty and malformed modules show `目前沒有營運資料` rather than throwing.

`advanceOpsRecord()` validates the module, record, flow and permission before writing. The mutation must run inside `commit('推進營運狀態', fn)`, call `log(record.id, '營運更新', text)`, update status to the next flow value, and notify on success. When an `events` entry matches the new status, use its escaped text and existing target node ID for the notification/audit entry. Final states remain unchanged.

Extend `condMet()` without removing `{kind:'po'}` support:

```js
if(c.kind === 'ops'){
  const record = opsRecord(c.module, c.id);
  return !!record && record[c.field || 'status'] === c.need;
}
```

Generic node-link cards use the active module label and record fields; unknown references render `找不到營運記錄` with escaped IDs.

- [ ] **Step 5: Replace the sidebar label and wire events**

Change `研發營運資料` to `營運資料`. Add delegated clicks for module tabs and `data-ops-advance`. Ensure petfood’s existing formula, PO, work-order and trace handlers still run only in petfood mode.

- [ ] **Step 6: Run GREEN and manual industry checks**

Load `tests/records.html?t=20261008w6t4green`. For each company, inspect all six tabs, advance the required blocking record, return to its linked task/gate, and verify the blocker is cleared. On petfood, run the existing PO→工單→ERP sync path.

- [ ] **Step 7: Review, record and commit**

Review with special attention to Review Focus 5 and user-text escaping. Rerun the suite, update PROGRESS, then commit:

```powershell
git add projectflow-full-demo.html tests/companies.test.js docs/PROGRESS.md
git commit -m "W6 task 4: render industry operations" -m "Co-Authored-By: Codex <noreply@openai.com>"
```

---

### Task 5: Attachment Namespace and Active-Company Reset

**Files:**
- Modify: `projectflow-full-demo.html` around `fileStore`, attachment handlers, `resetAll()` and reset dialog events
- Modify: `tests/companies.test.js`

**Interfaces:**
- Produces:
  - `attachmentStorageKey(attachmentId, companyId = company.id): string`
  - `attachmentBlob(attachment): Promise<Blob|undefined>`
  - `fileStore.del(key): Promise<void>`
  - `fileStore.removeMany(keys): Promise<void>`
  - `resetActiveCompany(writer = persistPortfolio): Promise<{ok:boolean,error?:string}>`
  - `openResetCompany(): void`
- Preserves:
  - Existing v5 petfood attachment IDs are read without a prefix.
  - `resetAll()` remains a test-only full reset helper for the existing browser suite; the product UI uses `resetActiveCompany()`.

- [ ] **Step 1: Write failing IndexedDB and reset tests**

Add asynchronous tests that clear the test database before and after themselves and assert:

```js
await T('W6：新附件鍵含公司前綴且舊毛研鍵仍可讀', async () => {
  switchCompany('petfood');
  eq(attachmentStorageKey('new-file'), 'petfood:new-file');
  await fileStore.put('legacy-file', new Blob(['old'], {type:'text/plain'}));
  ok(await attachmentBlob({id:'legacy-file', storage_key:'legacy-file'}), '舊附件鍵應可讀');
  switchCompany('software');
  eq(attachmentStorageKey('new-file'), 'software:new-file');
});

await T('W6：相同附件 ID 在不同公司使用不同 blob', async () => {
  await fileStore.put('petfood:same-file', new Blob(['petfood']));
  await fileStore.put('software:same-file', new Blob(['software']));
  eq(await (await fileStore.get('petfood:same-file')).text(), 'petfood');
  eq(await (await fileStore.get('software:same-file')).text(), 'software');
});

await T('W6：重設目前公司不改其他公司或其附件', async () => {
  switchCompany('petfood');
  projects()[0].title = '待重設毛研'; save();
  await fileStore.put('petfood:pf-a', new Blob(['petfood']));
  db.attachments.push({id:'pf-a',node_id:projects()[0].id,report_id:null,note_id:null,filename:'pf.txt',mime:'text/plain',size:7,sha256:'',storage_key:'petfood:pf-a',uploaded_by:ui.me,uploaded_at:nowStr(),deleted_at:null});
  save();
  switchCompany('software');
  projects()[0].title = '保留雲序'; save();
  await fileStore.put('software:sw-a', new Blob(['software']));
  db.attachments.push({id:'sw-a',node_id:projects()[0].id,report_id:null,note_id:null,filename:'sw.txt',mime:'text/plain',size:8,sha256:'',storage_key:'software:sw-a',uploaded_by:ui.me,uploaded_at:nowStr(),deleted_at:null});
  save();
  switchCompany('petfood');
  const result = await resetActiveCompany();
  ok(result.ok, '重設應成功');
  ok(!(await fileStore.get('petfood:pf-a')), '目前公司附件應刪除');
  ok(await fileStore.get('software:sw-a'), '其他公司附件要保留');
  switchCompany('software');
  eq(projects()[0].title, '保留雲序');
  ok(db.attachments.some(a => a.storage_key === 'software:sw-a'), '其他公司附件 metadata 要保留');
});

await T('W6：重設持久化失敗不改資料也不刪附件', async () => {
  switchCompany('software');
  const before = projects()[0].title;
  await fileStore.put('software:keep-a', new Blob(['keep']));
  db.attachments.push({id:'keep-a',node_id:projects()[0].id,report_id:null,note_id:null,filename:'keep.txt',mime:'text/plain',size:4,sha256:'',storage_key:'software:keep-a',uploaded_by:ui.me,uploaded_at:nowStr(),deleted_at:null});
  save();
  const result = await resetActiveCompany(() => false);
  ok(!result.ok, '重設應失敗');
  eq(projects()[0].title, before);
  ok(await fileStore.get('software:keep-a'), '附件不得先刪');
});
```

`openAttachment()` must call `attachmentBlob(attachment)`, and the assertion above must execute that shared lookup path rather than merely compare a string.

Task 5 adds exactly 4 W6 tests: the new/legacy key test, same-ID isolation test, reset isolation test and failed-persistence test shown above.

- [ ] **Step 2: Run tests to verify RED**

Load `tests/records.html?t=20261008w6t5red` and record the exact `#sum`. Expected failures: namespaced key helpers and active-company reset are missing.

- [ ] **Step 3: Namespace new files and retain legacy fallback**

All new writes use `${companyId}:${attachmentId}` and store that exact value in the existing `storage_key` field. Existing v5 petfood metadata already has an unprefixed `storage_key`; preserve and read it unchanged. If damaged legacy metadata lacks `storage_key`, only petfood may fall back to `attachment.id`.

Add `fileStore.del()` and `removeMany()` using readwrite IndexedDB transactions. Do not call `fileStore.clear()` from the product reset path because it would erase other companies.

- [ ] **Step 4: Implement atomic active-company reset**

Capture the current company’s attachment storage keys. Build a cloned portfolio where only `companies[company.id]` is replaced with `seedCompany(company.id)`, `activeCompanyId` remains unchanged, and the replacement identity is the default owner. Persist that candidate first. Only after success:

1. assign `portfolio = candidate`;
2. activate the reset company;
3. clear transient UI and render;
4. remove the captured attachment keys;
5. report any IndexedDB cleanup error without rolling back the already-saved reset.

If persistence fails, leave all live aliases, UI and IndexedDB blobs untouched.

- [ ] **Step 5: Replace reset UI copy**

The lower-left action remains in the same location but opens a confirmation dialog naming the active company: `重設「毛研食品」的示範資料？` The supporting copy explicitly says `其他四家公司的資料與附件都會保留。` The destructive button text is `重設目前公司`.

Keep `resetAll()` as a test compatibility helper that clears the test origin, recreates the full portfolio, activates petfood and clears the IndexedDB store. The product reset button must no longer call it; the UI calls `openResetCompany()` and then `resetActiveCompany()`. This preserves deterministic isolation for the existing 149 tests without exposing a global reset in the Demo UI.

- [ ] **Step 6: Run GREEN and browser persistence checks**

Load `tests/records.html?t=20261008w6t5green`. Manually attach one file in petfood and one in software, reload, open both, reset petfood and confirm the software file still opens.

- [ ] **Step 7: Review, record and commit**

Review with Review Focus 4. Rerun the full suite, update PROGRESS, then commit:

```powershell
git add projectflow-full-demo.html tests/companies.test.js docs/PROGRESS.md
git commit -m "W6 task 5: isolate attachments and reset" -m "Co-Authored-By: Codex <noreply@openai.com>"
```

---

### Task 6: Cross-Company Hardening, Documentation and Acceptance

**Files:**
- Modify: `projectflow-full-demo.html` at every remaining `db.ops` hard-coded access and company-sensitive helper
- Modify: `tests/companies.test.js`
- Modify: `README.md`
- Modify: `docs/PROGRESS.md`

**Interfaces:**
- Produces:
  - `isPetfoodOps(): boolean`
  - `legacyOps(): {suppliers:[],materials:[],formulas:[],pos:[],wos:[]}` safe fallback
  - `buildAIContext(question = ''): object`
- Hardens: review counts, timeline, secret masking, AI context, import/export actions, node link rendering, operation events and invalid identity fallback.

- [ ] **Step 1: Inventory all company-sensitive direct reads**

Run:

```powershell
rg -n "db\.ops|USERS|FIELD_ACCESS|TAGS|TAG_DEPT|audit|fileStore|localStorage" projectflow-full-demo.html
```

Classify every `db.ops.pos`, `db.ops.formulas`, `db.ops.wos`, supplier/material and ERP access as either petfood-only or generic. Add the classification with line/function names to the Task 6 PROGRESS entry before editing.

- [ ] **Step 2: Write failing collision and malformed-data tests**

Add tests that deliberately place the same IDs and a unique secret in two companies:

```js
await T('W6：同 ID 的節點、營運資料與稽核不跨公司', () => {
  switchCompany('petfood');
  db.nodes['shared-id'] = {id:'shared-id',type:'task',title:'毛研秘密',owner:'yu',dept:'d-rd',depts:[],reports:[],notes:[],links:[]};
  audit.acts.unshift({at:nowStr(),actor:'yu',node:'shared-id',action:'測試',text:'毛研稽核秘密'});
  save();
  switchCompany('software');
  db.nodes['shared-id'] = {id:'shared-id',type:'task',title:'雲序公開',owner:'sw-yi',dept:'d-product',depts:[],reports:[],notes:[],links:[]};
  db.ops.records.requirement.push({id:'PO-2601',title:'雲序同號需求',owner:'sw-yi',status:'已確認'});
  audit.acts.unshift({at:nowStr(),actor:'sw-yi',node:'shared-id',action:'測試',text:'雲序稽核'});
  save();
  eq(node('shared-id').title, '雲序公開');
  eq(opsRecord('requirement', 'PO-2601').title, '雲序同號需求');
  const html = pageAudit();
  ok(!html.includes('毛研秘密'), '不得顯示其他公司節點');
  ok(!html.includes('毛研稽核秘密'), '不得顯示其他公司稽核');
});

await T('W6：AI、權限與敏感資料只使用目前公司', () => {
  switchCompany('petfood');
  const petSecret = 'PF-SECRET-ONLY';
  db.ops.suppliers[0].contact = petSecret; save();
  switchCompany('software');
  const context = buildAIContext('目前專案風險');
  ok(!JSON.stringify(context).includes(petSecret), 'AI context 不得讀其他公司');
  ok(!secretValues().includes(petSecret), '敏感字詞不得讀其他公司');
  ok(!seeField('ratio'), '雲序成員不應繼承毛研配方欄位權限');
});

await T('W6：損壞營運連結與不存在成員不會使頁面崩潰', () => {
  switchCompany('construction');
  const root = projects()[0];
  root.links = [{t:'missing-module',id:'missing-record'}];
  company.me = 'missing-user';
  activateCompany('construction');
  eq(me().id, 'ct-chen');
  ui.node = root.id;
  const html = pageNode();
  ok(html.includes('找不到營運記錄'), '損壞連結要安全顯示');
});

await T('W6：五家公司主要頁面沒有 undefined 或 NaN', () => {
  COMPANY_ORDER.forEach(id => {
    switchCompany(id);
    ['overview','mytasks','review','ops','templates','aigov','audit'].forEach(page => {
      ui.page = page; renderMain();
      const text = document.querySelector('main').textContent;
      ok(!/\bundefined\b|\bNaN\b/.test(text), `${id}/${page} 出現無效文字`);
    });
  });
});
```

If AI context is assembled inline, first extract the active-company inputs to `buildAIContext(question = '')` and make the existing AI flow consume that helper. Task 6 adds exactly 4 W6 tests.

- [ ] **Step 3: Run tests to verify RED**

Load `tests/records.html?t=20261008w6t6red` and record the exact `#sum`. At least one hard-coded petfood path or malformed-data assertion must fail before hardening; if all pass, add a focused test for the first unguarded inventory item before editing.

- [ ] **Step 4: Guard petfood-only paths and make shared paths generic**

Add:

```js
function isPetfoodOps(){ return OPS_CONFIG?.mode === 'petfood'; }
function legacyOps(){
  const ops = db.ops || {};
  return {
    suppliers: Array.isArray(ops.suppliers) ? ops.suppliers : [],
    materials: Array.isArray(ops.materials) ? ops.materials : [],
    formulas: Array.isArray(ops.formulas) ? ops.formulas : [],
    pos: Array.isArray(ops.pos) ? ops.pos : [],
    wos: Array.isArray(ops.wos) ? ops.wos : []
  };
}
```

Then fix every inventory item:

- Petfood-only cards, AI commands, formula costing, purchase/work-order/ERP actions and trace queries must be hidden or return `此公司不使用這項營運功能` outside petfood mode.
- Shared pending counts, timeline, review center and search must derive only from active `db`, `audit` and active generic operations.
- `seeField(field)` must treat a missing `FIELD_ACCESS[field]` as denied instead of calling `.includes()` on `undefined`.
- `secretValues()` and `maskText()` must derive sensitive values from the active company’s declared secure columns plus active petfood values; they must not scan portfolio-wide serialized data.
- Member fallback uses `company.defaultUserId`, then the first active-company member if that ID is also missing, and writes a `console.warn`; unknown owner IDs render a neutral escaped fallback rather than another company’s user.
- Import/export, notifications, AI chat and undo may only mutate the active company and must call `save()` afterward.
- Generic links and conditions must remain safe when module, record, field or flow is missing.

- [ ] **Step 5: Update README**

Update the Demo feature table and quick-start text so it states:

- Lower-left sidebar has company switching above identity switching.
- Five fixed sample companies are included, each with independent members, projects, workflows, operations, audit and attachments.
- `研發營運資料` is now `營運資料`, with industry-specific modules.
- Browser data is a v6 portfolio under `projectflow-demo-v2`.
- This remains a fixed Demo; it does not include company CRUD, login isolation or backend multi-tenancy.

Do not rewrite README sections unrelated to the Demo or claim the formal React/FastAPI product exists.

- [ ] **Step 6: Run automated acceptance**

Load `tests/records.html?t=20261008w6acceptance` and capture the exact `全部通過 N/N` text. Reload the test page once with a new timestamp to prove isolation from prior in-memory state.

Also run:

```powershell
git diff --check
git status --short
git diff --name-only main...HEAD
```

Expected: no whitespace errors; `projectflow-petfood-demo.html` does not appear in the changed-file list; only the files allowed by this plan are changed.

- [ ] **Step 7: Run manual G4 acceptance at desktop and 375px**

For each of the five companies:

1. Switch from the lower-left selector and verify the default owner, overview, projects and members.
2. Open the complete main project and simpler secondary project, then workflow library, timeline, reports, review center and all six industry operations tabs; for petfood also spot-check the additional preserved projects.
3. Complete one linked operations state transition and verify its task/gate condition changes.
4. Change identity to reviewer, member, collaborator and admin and verify controls follow current-company permissions.
5. Reload and confirm active company and edits persist.
6. At 375px, verify sidebar/select text, operations tables, node detail, dialogs and buttons do not overlap or overflow.

For petfood, additionally verify formula costing, PO, work order, ERP sync and traceability still behave as before.

- [ ] **Step 8: Review, record and commit**

Run the required review round with Review Focus 3, apply the one correction round, rerun automated and manual checks, update PROGRESS, then commit:

```powershell
git add projectflow-full-demo.html tests/companies.test.js README.md docs/PROGRESS.md
git commit -m "W6 task 6: harden isolation and document demo" -m "Co-Authored-By: Codex <noreply@openai.com>"
```

---

## Spec Coverage

| Spec section | Owning tasks |
|---|---|
| §4 公司切換、身分與重設體驗 | Tasks 2, 5 |
| §5 v6 容器、v2–v5 遷移、公司 ID 與附件 key | Tasks 1, 5 |
| §6 五家公司最低內容、成員與部門 | Task 3 |
| §7 設定驅動營運資料、專案連結與產業事件 | Tasks 3, 4 |
| §8 身分、權限、AI、稽核與資料隔離 | Tasks 2, 6 |
| §9 暫態 UI 與復原隔離 | Task 2 |
| §10 寫入失敗、損壞資料、空狀態與 IndexedDB 錯誤 | Tasks 1, 2, 4, 5, 6 |
| §11 自動化與桌面／375px 驗收 | Tasks 1–6 and G4–G6 |
| §12 文件與允許修改檔案 | Global Constraints, Task 6 |
| §13 正式產品銜接 | README note and D45 handoff; no formal backend work in W6 |

---

## G4–G6 Completion Checklist

- [ ] G4 functional acceptance records the final automated `#sum`, desktop pass and 375px pass in PROGRESS.
- [ ] G4 explicitly checks that v5 custom petfood data and legacy attachments survive first v6 load.
- [ ] G4 explicitly checks that reset affects only the active company.
- [ ] G5 runs a final spec compliance review, code quality review and `git diff main...HEAD --check`.
- [ ] G5 verifies every Review Focus item has a named automated test and a passing result.
- [ ] G5 verifies `git status --short`, `git log --oneline main..HEAD`, and the allowed-file list.
- [ ] G6 updates W6 to complete, records version `v6`, closes its acceptance checklist and writes a handoff entry.
- [ ] G6 fast-forwards only after human approval:

```powershell
git checkout main
git merge --ff-only feature/w6-multi-company-industry-demo
```

- [ ] Do not push. After W6 is integrated and the human confirms the next priority, resume P0 from `paused/p0-formal-product-plan` according to D45.
