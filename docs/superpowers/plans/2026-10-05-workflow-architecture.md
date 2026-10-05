# W3 工作流架構 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 完成 Demo 層級的工作流架構，讓使用者可以自行新增／編輯／套用工作流，並讓階段關卡擋住後續階段。

**Architecture:** 在既有單檔 Demo 內新增 `db.workflows[]` 作為高階工作流模板，保留舊 `db.templates[]` 任務模板。模板庫頁分成「工作流模板」與「任務模板」兩區；工作流可用表單建立與編輯，並可產生完整專案樹。關卡阻擋整合進既有 `findBlockers()`，讓現有拖曳、回報與狀態切換都共用同一套阻擋機制。

**Tech Stack:** 原生 HTML/CSS/JS；瀏覽器測試 `tests/records.html` + `tests/records.test.js`；localStorage key 維持 `projectflow-demo-v2`。

**Spec:** `docs/superpowers/specs/2026-10-05-process-control-design.md`

## Global Constraints

- 產品程式只改 `projectflow-full-demo.html`。
- 測試只改 `tests/records.test.js`。
- 資料版本由 `db.v = 4` 升到 `db.v = 5`；`load()` 必須接受 v2、v3、v4、v5 並依序升級。
- localStorage key 維持 `projectflow-demo-v2`。
- 不新增外部函式庫或 CDN。
- 介面文字一律繁體中文。
- 寫入 `db` 的使用者操作一律包在 `commit(label, fn)` 裡，並用 `log(nodeId, action, text)` 寫稽核紀錄。
- 權限沿用既有 `can(action, node)`；工作流建立／編輯／刪除使用 `can('templates')`，從工作流建立專案允許系統管理員與專案負責人。
- 輸出到 HTML 的使用者文字一律先經過 `esc()`。
- 測試方式見 `docs/WORKFLOW.md` §5；每個 Task 都要記錄 RED 與 GREEN 的 `#sum` 原文。

## Review Focus

- v4 真實資料升級：既有 `db.templates`、任務、部門和報告資料不可遺失。
- 工作流編輯防呆：空名稱、空階段、空任務、未知部門、循環前置都要拒絕。
- 權限：一般成員不可建立、編輯、刪除工作流；專案負責人可從工作流建立專案。
- 建立專案後的資料完整性：phase、task、deps、gates 都要指到存在的節點。
- 關卡阻擋與既有前置條件要能疊加：關卡通過後，任務自己的硬性前置仍然有效。

---

## File Structure

- Modify `projectflow-full-demo.html`
  - 資料與升級：`seed()`、`upgrade()`、`load()`、`save()`。
  - 工作流核心：新增 `builtinWorkflows()`、`workflowStats()`、`validateWorkflow()`、`cloneWorkflow()`、`saveWorkflow()`、`deleteWorkflow()`、`createProjectFromWorkflow()` 等 helper。
  - 模板庫 UI：改 `pageTemplates()`，新增工作流列表與表單 dialog。
  - 關卡阻擋：改 `findBlockers()`，新增 `phaseGateBlocker()` 或同等 helper。
  - 事件處理：在既有 document click / submit / change 委派中加入工作流按鈕與表單。
- Modify `tests/records.test.js`
  - 在 `// ── 新測試加在這一行上面 ──` 上方新增 W3 測試。

---

### Task 1: Workflow Data Model and Validation

**Files:**
- Modify: `projectflow-full-demo.html` around `seed()`, `upgrade()`, `load()`, `save()`
- Modify: `tests/records.test.js`

**Interfaces:**
- Produces:
  - `builtinWorkflows(): Array<Workflow>`
  - `workflowStats(wf): { stages:number, tasks:number, gates:number, deps:number, days:number }`
  - `validateWorkflow(wf): string[]`
  - `cloneWorkflow(wf, overrides?): Workflow`
  - `db.workflows`
- Consumes:
  - Existing `db.departments`, `deptName()`, `newId()`, `OLD_DEPT`, `TAG_DEPT`

- [ ] **Step 1: Write failing tests**

Add these tests before the marker in `tests/records.test.js`:

```js
  // ── W3 Task 1：工作流資料模型 ──
  await T('W3：種子資料為 v5 且含兩套內建工作流', () => {
    eq(db.v, 5);
    ok(Array.isArray(db.workflows), 'db.workflows 應為陣列');
    eq(db.workflows.map((w) => w.name).sort(), ['實體活動專流', '筆電新機種專流']);
    const laptop = db.workflows.find((w) => w.name === '筆電新機種專流');
    eq(workflowStats(laptop).stages, 9);
    ok(workflowStats(laptop).tasks >= 40, '筆電工作流應包含主要任務');
    ok(workflowStats(laptop).gates >= 7, '筆電工作流應包含 G0-G6 關卡');
  });

  await T('W3：upgrade v4 到 v5 保留既有模板並新增工作流', () => {
    const d = seed(); d.v = 4; delete d.workflows;
    const o = upgrade({ v: 4, db: d, audit: freshAudit() });
    eq(o.v, 5); eq(o.db.v, 5);
    ok(o.db.templates.length >= 4, '既有任務模板要保留');
    eq(o.db.workflows.length, 2);
  });

  await T('W3：validateWorkflow 擋空資料、未知部門與循環前置', () => {
    const base = cloneWorkflow(db.workflows[0], { id: 'wf-test', name: '測試工作流', builtin: false });
    eq(validateWorkflow({ ...base, name: ' ' })[0], '工作流名稱必填');
    eq(validateWorkflow({ ...base, stages: [] })[0], '至少需要 1 個階段');
    const noTask = cloneWorkflow(base); noTask.stages[0].tasks = [];
    eq(validateWorkflow(noTask)[0], '每個階段至少需要 1 個任務');
    const badDept = cloneWorkflow(base); badDept.stages[0].tasks[0].dept = 'd-missing';
    ok(validateWorkflow(badDept).some((x) => x.includes('未知部門')), '未知部門要被擋');
    const cyc = cloneWorkflow(base);
    cyc.stages = [{ id: 's', title: '階段', dept: 'd-adm', gate: null, tasks: [
      { id: 'a', title: 'A', dept: 'd-adm', depts: [], dur: 1 },
      { id: 'b', title: 'B', dept: 'd-adm', depts: [], dur: 1 },
    ] }];
    cyc.deps = [{ from: 'a', to: 'b', type: 'FS', lag: 0, enf: 'hard' }, { from: 'b', to: 'a', type: 'FS', lag: 0, enf: 'hard' }];
    ok(validateWorkflow(cyc).some((x) => x.includes('循環前置')), '循環前置要被擋');
  });
```

- [ ] **Step 2: Run tests to verify RED**

Run `tests/records.html?t=<timestamp>` per WORKFLOW §5.

Expected RED: `失敗 3/140` because `db.v` is still 4 and workflow helpers do not exist.

- [ ] **Step 3: Implement data model**

In `projectflow-full-demo.html`:

1. Add constants/helpers near existing template helpers:

```js
const WF_DEPT = {
  '研發部': 'd-rd', '財務部': 'd-fin', '採購部': 'd-pur', '品保部': 'd-qa',
  '行銷部': 'd-sales', '業務部': 'd-sales', '製造部': 'd-mfg', '資訊部': 'd-it',
  '產品企劃部': 'd-adm', '工業設計部': 'd-adm', '認證部': 'd-qa', '客服部': 'd-sales',
  '管理層': 'd-adm',
};
const wfDept = (name, fallback) => WF_DEPT[name] || fallback || 'd-adm';
const wfTask = (id, title, dept, dur = 5, depts = []) => ({ id, title, dept, depts, dur });
```

2. Add `builtinWorkflows()` with two workflow objects. Use the rows already transcribed in `docs/reference/2026-10-05-w3-current-flow-sources.md`. The laptop workflow must include 9 stages and G0-G6 gates. The event workflow can include its 8 stages with `gate: null`.

3. Add helper implementations:

```js
function cloneWorkflow(wf, overrides = {}) { return { ...clone(wf), ...overrides }; }
function workflowStats(wf) {
  const tasks = wf.stages.reduce((a, s) => a + s.tasks.length, 0);
  const gates = wf.stages.filter((s) => s.gate).length;
  const days = wf.stages.reduce((a, s) => a + s.tasks.reduce((b, t) => b + (+t.dur || 1), 0), 0);
  return { stages: wf.stages.length, tasks, gates, deps: wf.deps.length, days };
}
function workflowTaskIds(wf) { return new Set(wf.stages.flatMap((s) => s.tasks.map((t) => t.id))); }
function workflowHasCycle(wf) {
  const graph = {};
  workflowTaskIds(wf).forEach((id) => { graph[id] = []; });
  (wf.deps || []).forEach((d) => { if (graph[d.from]) graph[d.from].push(d.to); });
  const seen = new Set(), visiting = new Set();
  const visit = (id) => {
    if (visiting.has(id)) return true;
    if (seen.has(id)) return false;
    visiting.add(id);
    const hit = (graph[id] || []).some(visit);
    visiting.delete(id); seen.add(id);
    return hit;
  };
  return Object.keys(graph).some(visit);
}
function validateWorkflow(wf) {
  const errors = [];
  const deptIds = new Set((db.departments || []).map((d) => d.id));
  if (!String(wf.name || '').trim()) errors.push('工作流名稱必填');
  if (!Array.isArray(wf.stages) || !wf.stages.length) errors.push('至少需要 1 個階段');
  (wf.stages || []).forEach((s) => {
    if (!String(s.title || '').trim()) errors.push('階段名稱必填');
    if (s.dept && !deptIds.has(s.dept)) errors.push(`未知部門：${s.dept}`);
    if (!Array.isArray(s.tasks) || !s.tasks.length) errors.push('每個階段至少需要 1 個任務');
    (s.tasks || []).forEach((t) => {
      if (!String(t.title || '').trim()) errors.push('任務名稱必填');
      if (!deptIds.has(t.dept)) errors.push(`未知部門：${t.dept}`);
      (t.depts || []).forEach((id) => { if (!deptIds.has(id)) errors.push(`未知部門：${id}`); });
      if (!Number.isFinite(+t.dur) || +t.dur < 1) errors.push(`工期至少 1 天：${t.title || t.id}`);
    });
  });
  const ids = workflowTaskIds(wf);
  (wf.deps || []).forEach((d) => {
    if (!ids.has(d.from) || !ids.has(d.to)) errors.push(`前置任務不存在：${d.from} → ${d.to}`);
    if (d.from === d.to) errors.push(`循環前置：${d.from} → ${d.to}`);
  });
  if (workflowHasCycle(wf)) errors.push('循環前置：工作流內有互相依賴');
  return [...new Set(errors)];
}
```

Use exact first errors:
- `工作流名稱必填`
- `至少需要 1 個階段`
- `每個階段至少需要 1 個任務`
- `未知部門：<id>`
- `循環前置：<from> → <to>`

4. Update `seed()` root object:

```js
const db = { v: 5, departments: defaultDepts(), nodes: {}, deps: [], gates: {}, docs: [], templates: [], workflows: builtinWorkflows(), ... };
```

5. Update `upgrade(o)`:

```js
if (o.v === 4) {
  const d = o.db;
  d.workflows = d.workflows && d.workflows.length ? d.workflows : builtinWorkflows();
  d.v = 5; o.v = 5;
}
```

6. Update `load()` accepted versions to `[2, 3, 4, 5]`.

7. Update `save()` payload version to `v: 5`.

- [ ] **Step 4: Run tests to verify GREEN**

Expected GREEN: `全部通過 140/140`.

- [ ] **Step 5: Commit**

```bash
git add projectflow-full-demo.html tests/records.test.js
git commit -m "Workflow task 1: add workflow data model"
```

---

### Task 2: Workflow Library UI and CRUD

**Files:**
- Modify: `projectflow-full-demo.html`
- Modify: `tests/records.test.js`

**Interfaces:**
- Consumes: Task 1 `db.workflows`, `workflowStats()`, `validateWorkflow()`, `cloneWorkflow()`
- Produces:
  - `pageTemplates()` renders workflow section
  - `openWorkflowEditor(id?)`
  - `submitWorkflowForm(form)`
  - `duplicateWorkflow(id)`
  - `deleteWorkflow(id)`

- [ ] **Step 1: Write failing tests**

Add:

```js
  // ── W3 Task 2：工作流模板管理 ──
  await T('W3：模板庫顯示工作流模板與任務模板兩區', () => {
    as('it'); ui.page = 'templates'; render();
    const txt = document.getElementById('main').textContent;
    ok(txt.includes('工作流模板'), '應顯示工作流模板區');
    ok(txt.includes('任務模板'), '應保留任務模板區');
    ok(txt.includes('筆電新機種專流'), '應顯示內建工作流');
  });

  await T('W3：只有系統管理員可以新增工作流', () => {
    as('ming'); ui.page = 'templates'; render();
    ok(!document.getElementById('main').querySelector('[data-wf-new]'), '一般成員不能新增工作流');
    as('it'); ui.page = 'templates'; render();
    ok(document.getElementById('main').querySelector('[data-wf-new]'), '系統管理員可新增工作流');
  });

  await T('W3：新增、編輯、複製、刪除自訂工作流', () => {
    as('it');
    const before = db.workflows.length;
    const wf = {
      id: 'wf-custom', name: '客製工作流', desc: '展示用', category: '測試', version: 1, builtin: false,
      stages: [{ id: 's1', title: '第一階段', dept: 'd-adm', gate: { title: 'G0', criteria: '完成第一階段' }, tasks: [{ id: 't1', title: '第一個任務', dept: 'd-adm', depts: [], dur: 3 }] }],
      deps: [],
    };
    ok(saveWorkflow(wf).ok, '新增應成功');
    eq(db.workflows.length, before + 1);
    ok(saveWorkflow({ ...wf, name: '客製工作流 v2' }).ok, '編輯應成功');
    eq(db.workflows.find((x) => x.id === 'wf-custom').name, '客製工作流 v2');
    const copy = duplicateWorkflow('wf-custom');
    ok(copy && copy.id !== 'wf-custom' && copy.name.includes('副本'), '複製應建立新 id');
    ok(deleteWorkflow('wf-custom').ok, '自訂工作流可刪除');
  });

  await T('W3：內建工作流不能刪除，錯誤資料不能儲存', () => {
    as('it');
    const built = db.workflows.find((w) => w.builtin);
    eq(deleteWorkflow(built.id).error, '內建工作流不能刪除');
    eq(saveWorkflow({ ...built, id: 'bad', name: ' ' }).ok, false);
  });
```

- [ ] **Step 2: Run tests to verify RED**

Expected RED: `失敗 4/144`.

- [ ] **Step 3: Implement CRUD helpers**

Add near workflow helpers:

```js
function canManageWorkflows() { return can('templates'); }
function saveWorkflow(wf) {
  if (!canManageWorkflows()) return { ok: false, error: '你的角色無權管理工作流' };
  const errors = validateWorkflow(wf);
  if (errors.length) return { ok: false, error: errors[0], errors };
  const clean = cloneWorkflow(wf, { version: wf.version || 1, builtin: !!wf.builtin });
  const i = db.workflows.findIndex((x) => x.id === clean.id);
  commit(i >= 0 ? `更新工作流「${clean.name}」` : `新增工作流「${clean.name}」`, () => {
    if (i >= 0) db.workflows[i] = clean; else db.workflows.push(clean);
  });
  log(null, '工作流', `${i >= 0 ? '更新' : '新增'}工作流「${clean.name}」`);
  return { ok: true, workflow: clean };
}
function duplicateWorkflow(id) {
  if (!canManageWorkflows()) return null;
  const src = db.workflows.find((w) => w.id === id);
  if (!src) return null;
  const copy = cloneWorkflow(src, { id: newId('wf'), name: `${src.name} 副本`, builtin: false, version: 1 });
  return saveWorkflow(copy).ok ? copy : null;
}
function deleteWorkflow(id) {
  if (!canManageWorkflows()) return { ok: false, error: '你的角色無權管理工作流' };
  const wf = db.workflows.find((w) => w.id === id);
  if (!wf) return { ok: false, error: '找不到工作流' };
  if (wf.builtin) return { ok: false, error: '內建工作流不能刪除' };
  commit(`刪除工作流「${wf.name}」`, () => { db.workflows = db.workflows.filter((x) => x.id !== id); });
  log(null, '工作流', `刪除工作流「${wf.name}」`);
  return { ok: true };
}
```

- [ ] **Step 4: Implement UI**

Modify `pageTemplates()`:

- Add `<h2>工作流模板</h2>`.
- Render `db.workflows` cards before existing `db.templates`.
- Add admin-only `＋ 新增工作流` button (`data-wf-new`).
- Card buttons:
  - `data-wf-create`
  - `data-wf-edit`
  - `data-wf-copy`
  - `data-wf-del`
- Wrap old template cards under `<h2>任務模板</h2>`.

Add `openWorkflowEditor(id)`:

- Use a compact form in a wide dialog.
- For the implementation plan, use textarea-based JSON for stages/deps if needed to keep Demo fast, but labels must be user-facing:
  - Basic inputs for name/category/desc.
  - Textarea `#wfJson` containing editable JSON for `stages` and `deps`.
  - Validation errors shown by toast.
- This is acceptable for Demo mode if the card/list UX is clear and tests cover helpers. If there is time, use repeated field rows.

Add event handlers in click/submit delegates:

```js
if (ds.wfNew !== undefined) return openWorkflowEditor();
if (ds.wfEdit) return openWorkflowEditor(ds.wfEdit);
if (ds.wfCopy) { duplicateWorkflow(ds.wfCopy); return render(); }
if (ds.wfDel) { const r = deleteWorkflow(ds.wfDel); if (!r.ok) toast(r.error, 'warn'); return render(); }
if (f.id === 'wfForm') return submitWorkflowForm(f);
```

- [ ] **Step 5: Run tests to verify GREEN**

Expected GREEN: `全部通過 144/144`.

- [ ] **Step 6: Commit**

```bash
git add projectflow-full-demo.html tests/records.test.js
git commit -m "Workflow task 2: manage workflow templates"
```

---

### Task 3: Create Projects From Workflows

**Files:**
- Modify: `projectflow-full-demo.html`
- Modify: `tests/records.test.js`

**Interfaces:**
- Consumes: Task 1 workflow structure, Task 2 workflow cards
- Produces:
  - `createProjectFromWorkflow(workflowId, opts): { ok, projectId, count }`
  - `openWorkflowProjectDialog(workflowId)`

- [ ] **Step 1: Write failing tests**

Add:

```js
  // ── W3 Task 3：從工作流建立專案 ──
  await T('W3：從工作流建立專案會產生專案、階段、任務、前置與關卡', () => {
    as('it');
    const wf = db.workflows.find((w) => w.name === '筆電新機種專流');
    const r = createProjectFromWorkflow(wf.id, { name: '展示筆電專案', start: '2026-10-01', owner: 'yu' });
    ok(r.ok, r.error);
    const p = node(r.projectId);
    eq(p.title, '展示筆電專案');
    eq(kids(p.id).filter((x) => x.type === 'phase').length, workflowStats(wf).stages);
    ok(descendants(p.id).filter((x) => x.type === 'task').length >= workflowStats(wf).tasks);
    ok(Object.keys(db.gates).some((id) => projectOf(node(id)).id === p.id), '應建立階段關卡');
    ok(db.deps.some((d) => node(d.from) && node(d.to) && projectOf(node(d.to)).id === p.id), '應建立前置條件');
  });

  await T('W3：專案負責人可從工作流建立專案，一般成員不可', () => {
    const wf = db.workflows[0];
    as('ming'); eq(createProjectFromWorkflow(wf.id, { name: '不應建立', start: TODAY, owner: 'ming' }).ok, false);
    as('yu'); ok(createProjectFromWorkflow(wf.id, { name: '負責人建立', start: TODAY, owner: 'yu' }).ok);
  });
```

- [ ] **Step 2: Run tests to verify RED**

Expected RED: `失敗 2/146`.

- [ ] **Step 3: Implement project creation**

Add:

```js
function canCreateWorkflowProject() { return ['admin', 'owner'].includes(me().role); }
function createProjectFromWorkflow(workflowId, opts) {
  if (!canCreateWorkflowProject()) return { ok: false, error: '你的角色無權從工作流建立專案' };
  const wf = db.workflows.find((w) => w.id === workflowId);
  if (!wf) return { ok: false, error: '找不到工作流' };
  const errors = validateWorkflow(wf);
  if (errors.length) return { ok: false, error: errors[0], errors };
  const name = String(opts.name || '').trim();
  if (!name) return { ok: false, error: '專案名稱必填' };
  let projectId, count = 0;
  commit(`從工作流建立專案「${name}」`, () => {
    const start = D(opts.start || TODAY);
    const owner = opts.owner && USERS[opts.owner] ? opts.owner : ui.me;
    const map = {}, phaseMap = {};
    const orders = Object.values(db.nodes).map((n) => n.order || 0);
    let order = Math.max(0, ...orders) + 1, cursor = start;
    projectId = newId('p');
    db.nodes[projectId] = {
      id: projectId, parent: null, type: 'project', title: name, tag: '', status: 'todo', progress: null, weight: 1,
      start: S(start), end: S(start), milestone: false, locked: false, owner, dept: null, collabs: [], depts: [],
      level: 'internal', ai: false, note: '', links: [], order: order++, color: '#2E6F8E',
      goal: `依工作流「${wf.name}」建立`, due: '',
    };
    wf.stages.forEach((s) => {
      const ph = newId('n');
      phaseMap[s.id] = ph;
      db.nodes[ph] = { ...db.nodes[projectId], id: ph, parent: projectId, type: 'phase', title: s.title, start: S(cursor), end: S(cursor), owner, dept: null, order: order++, goal: undefined, due: undefined };
      let phaseEnd = cursor;
      (s.tasks || []).forEach((t) => {
        const id = newId('n');
        const dur = Math.max(1, +t.dur || 1);
        map[t.id] = id;
        db.nodes[id] = {
          id, parent: ph, type: 'task', title: t.title, tag: '', status: 'todo', progress: null, weight: 1,
          start: S(cursor), end: S(cursor + dur - 1), milestone: false, locked: false, owner: null,
          dept: t.dept, collabs: [], depts: t.depts || [], level: null, ai: false, note: '', links: [], order: order++,
        };
        phaseEnd = Math.max(phaseEnd, cursor + dur - 1);
        cursor += dur; count++;
      });
      db.nodes[ph].end = S(phaseEnd);
      if (s.gate) db.gates[ph] = { criteria: s.gate.criteria, approver: '專案負責人', status: 'pending' };
    });
    (wf.deps || []).forEach((d) => {
      if (map[d.from] && map[d.to]) db.deps.push({ id: newId('d'), from: map[d.from], to: map[d.to], type: d.type || 'FS', lag: +d.lag || 0, enf: d.enf || 'hard', cond: null, overridden: false });
    });
    const spans = descendants(projectId).map(span);
    if (spans.length) { db.nodes[projectId].start = S(Math.min(...spans.map((x) => x[0]))); db.nodes[projectId].end = S(Math.max(...spans.map((x) => x[1]))); }
  });
  log(projectId, '工作流', `從「${wf.name}」建立專案「${name}」`);
  return { ok: true, projectId, count };
}
```

Implementation details:

- Project node:
  - `type: 'project'`
  - `owner: opts.owner || ui.me`
  - `start: opts.start || TODAY`
  - `end`: latest generated task end.
- Phase dates:
  - Start at cumulative day offset.
  - Phase end is max task end in that phase.
- Task owners:
  - Default `owner: null` so W2 department assignment is visible.
  - `dept` from workflow task.
  - `depts` from workflow task.
- Gates:
  - `db.gates[phaseId] = { criteria: gate.criteria, approver: '專案負責人', status: 'pending' }`
- Deps:
  - Translate workflow internal `from`/`to` to real node ids.

Add dialog:

- `openWorkflowProjectDialog(workflowId)`.
- Form fields: project name, start date, owner.
- Submit calls `createProjectFromWorkflow()`, then `enter(projectId)`.

Wire `data-wf-create`.

- [ ] **Step 4: Run tests to verify GREEN**

Expected GREEN: `全部通過 146/146`.

- [ ] **Step 5: Commit**

```bash
git add projectflow-full-demo.html tests/records.test.js
git commit -m "Workflow task 3: create projects from workflows"
```

---

### Task 4: Gate Blocking and Demo Verification

**Files:**
- Modify: `projectflow-full-demo.html`
- Modify: `tests/records.test.js`
- Optional Modify: `README.md` only if a W3-specific sentence is needed before W5

**Interfaces:**
- Consumes: Task 3 generated projects with gates
- Produces:
  - `phaseGateBlocker(n, to)` or equivalent helper used by `findBlockers()`
  - Later-stage tasks blocked by earliest pending prior phase gate

- [ ] **Step 1: Write failing tests**

Add:

```js
  // ── W3 Task 4：階段關卡阻擋後續階段 ──
  await T('W3：關卡 pending 時，後續階段任務不能開始；核准後可開始', () => {
    as('it');
    const wf = db.workflows.find((w) => w.name === '筆電新機種專流');
    const r = createProjectFromWorkflow(wf.id, { name: '關卡阻擋測試', start: '2026-10-01', owner: 'yu' });
    const p = node(r.projectId);
    const phases = kids(p.id).filter((x) => x.type === 'phase');
    const gatePhase = phases.find((ph) => db.gates[ph.id]);
    const later = descendants(phases[phases.indexOf(gatePhase) + 1].id).find((x) => x.type === 'task');
    const bl = findBlockers(later, 'doing').map((b) => b.text).join('；');
    ok(bl.includes('階段關卡未通過'), bl);
    ok(!setStatus(later.id, 'doing'), 'pending gate 應擋住開始');
    db.gates[gatePhase.id].status = 'approved';
    ok(setStatus(later.id, 'doing'), 'gate approved 後可開始');
  });

  await T('W3：關卡通過後，任務自己的硬性前置仍有效', () => {
    as('it');
    const wf = cloneWorkflow(db.workflows[0], { id: 'wf-dep-test', name: '前置測試', builtin: false });
    wf.stages = [
      { id: 's1', title: '一', dept: 'd-adm', gate: { title: 'G1', criteria: '完成一' }, tasks: [{ id: 'a', title: 'A', dept: 'd-adm', depts: [], dur: 1 }] },
      { id: 's2', title: '二', dept: 'd-adm', gate: null, tasks: [{ id: 'b', title: 'B', dept: 'd-adm', depts: [], dur: 1 }] },
    ];
    wf.deps = [{ from: 'a', to: 'b', type: 'FS', lag: 0, enf: 'hard' }];
    saveWorkflow(wf);
    const r = createProjectFromWorkflow(wf.id, { name: '前置測試專案', start: TODAY, owner: 'yu' });
    const p = node(r.projectId), phases = kids(p.id).filter((x) => x.type === 'phase');
    db.gates[phases[0].id].status = 'approved';
    const b = descendants(phases[1].id).find((x) => x.title === 'B');
    ok(!setStatus(b.id, 'doing'), '自己的硬性前置未完成仍要阻擋');
    ok(findBlockers(b, 'doing').some((x) => x.text.includes('前置：A')), '應顯示原本前置');
  });

  await T('W3：375px 下工作流頁與建立專案對話框不水平溢出', () => {
    const fr = window.frameElement, w = fr && fr.style.width;
    if (fr) { fr.style.width = '375px'; fr.getBoundingClientRect(); }
    try {
      as('it'); ui.page = 'templates'; render();
      const m = document.getElementById('main');
      ok(m.scrollWidth <= m.clientWidth + 1, `模板庫不應水平溢出 ${m.scrollWidth}/${m.clientWidth}`);
      openWorkflowProjectDialog(db.workflows[0].id);
      const dlg = document.querySelector('.dlg');
      ok(dlg.scrollWidth <= dlg.clientWidth + 1, `建立專案對話框不應水平溢出 ${dlg.scrollWidth}/${dlg.clientWidth}`);
      closeDlg();
    } finally { if (fr) fr.style.width = w; }
  });
```

- [ ] **Step 2: Run tests to verify RED**

Expected RED: `失敗 3/149`.

- [ ] **Step 3: Implement gate blocking**

Add helper:

```js
function phaseGateBlocker(n) {
  if (!n || n.type !== 'task') return null;
  const ph = phaseOf(n); if (!ph) return null;
  const p = projectOf(n);
  const phases = kids(p.id).filter((x) => x.type === 'phase');
  const idx = phases.findIndex((x) => x.id === ph.id);
  for (let i = 0; i < idx; i++) {
    const g = db.gates[phases[i].id];
    if (g && !['approved', 'overridden'].includes(g.status)) {
      return { phase: phases[i], gate: g, text: `階段關卡未通過：${phases[i].title}／${g.criteria}` };
    }
  }
  return null;
}
```

Modify `findBlockers(n, to)`:

- Before returning, when `n.type === 'task'` and `n.status === 'todo' && to !== 'todo'` or `to === 'done'`, add a hard blocker from `phaseGateBlocker(n)`.
- Do not block tasks in the same phase as the pending gate; only later phases.

Make sure `doneBlockers()`, `submitReport()`, `decideReport()`, drag/drop and status buttons inherit this automatically.

- [ ] **Step 4: Run tests to verify GREEN**

Expected GREEN: `全部通過 149/149`.

- [ ] **Step 5: Manual UI verification**

Use `tests/records.html` and the Demo:

- Confirm `#sum` is `全部通過 149/149`.
- As `it`, open 模板庫:
  - See 工作流模板 and 任務模板.
  - Create a custom workflow with 1 stage / 1 task.
  - Duplicate it.
  - Delete the duplicate.
- As `yu`, create a project from a workflow.
- Try to start a later-stage task before previous gate approval: verify blocked message.
- Approve the gate and try again: verify the task can start if its own deps are met.
- At 375px width, check 模板庫、工作流編輯對話框、建立專案對話框、看板 and task page have no horizontal overflow.
- Console error count must be 0.

- [ ] **Step 6: Commit**

```bash
git add projectflow-full-demo.html tests/records.test.js
git commit -m "Workflow task 4: block later stages by gates"
```

---

## Final Review and Merge Checklist

After all tasks:

1. Update `docs/PROGRESS.md` task table for W3 with RED/GREEN evidence.
2. Run full `tests/records.html?t=<timestamp>`.
3. Perform展示模式 whole-branch review:
   - one reviewer/self-review is acceptable only if recorded, but merge then needs human confirmation if not independent.
   - block only demo-breaking bugs.
4. Run compact manual acceptance:
   - `it`: create/edit/copy/delete workflow.
   - `yu`: create project from workflow.
   - `chen` or reviewer role: approve gate.
   - `ming`: verify blocked/unblocked task behavior where visible.
   - 375px no horizontal overflow.
5. If ready, update W3 to 🟢 or ask for human confirmation if review was self-review.
