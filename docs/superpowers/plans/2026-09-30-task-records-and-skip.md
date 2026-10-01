# 任務紀錄（完成回報／筆記／附件）與主管跳過任務 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在單檔 Demo 中，讓每個任務可以送出完成回報（固定＋自訂欄位、需主管確認）、寫筆記、上傳附件，並讓主管可以跳過整個任務（成員可申請）。

**Architecture:** 所有程式都在 `projectflow-full-demo.html` 內。核心邏輯（資料操作，不碰 DOM）放在第一個 `<script>` 的 `notify()` 之後；畫面與對話框放在「事件繫結」區塊之前；事件處理加在既有的 click / submit 委派裡。中繼資料存在 `db`（localStorage，資料版本 v3），檔案內容存在 IndexedDB。測試是一個瀏覽器測試頁，用 iframe 載入 Demo，在 Demo 的全域環境裡直接呼叫核心函式並斷言。

**Tech Stack:** 原生 HTML/CSS/JavaScript（無框架、無打包）、localStorage、IndexedDB、`crypto.subtle`、Python `http.server`（只用來在本機提供測試頁）。

**Spec:** `docs/superpowers/specs/2026-09-30-task-records-and-skip-design.md`

## Global Constraints

- 只修改 `projectflow-full-demo.html` 與 `README.md`；新增 `tests/records.html`、`tests/records.test.js`、`.claude/launch.json`。不引入任何外部函式庫或 CDN。
- 介面文字一律繁體中文，語氣與既有 Demo 一致。
- localStorage key 維持 `projectflow-demo-v2`；資料版本 `db.v` 由 2 升為 3，必須能自動轉換 v2 資料。
- 單檔上限 10 MB（`MAX_FILE = 10 * 1024 * 1024`）。
- IndexedDB 資料庫名稱 `projectflow-files`，object store `blobs`。
- 所有會改變 `db` 的動作都包在既有的 `commit(label, fn)` 裡，並呼叫既有的 `log(nodeId, action, text)` 寫入稽核紀錄。
- 權限一律使用既有的 `can(action, node)`；確認回報、直接跳過、恢復任務都用 `can('override', n)`。
- 輸出到 HTML 的使用者文字一律經過既有的 `esc()`。
- 這個資料夾不是 git repo：計畫中沒有 commit 步驟。每個 Task 結束時跑測試頁確認全部通過即可。
- 測試頁會重置 Demo 的 localStorage 與 IndexedDB 資料（和按「重置 Demo 資料」相同）。

## 檔案結構

| 檔案 | 責任 |
|---|---|
| `projectflow-full-demo.html` | Demo 本體。新增：常數、fileStore、資料轉換、回報／筆記／附件／跳過的核心函式、「紀錄」分頁、對話框、審核中心區塊、事件處理、CSS |
| `tests/records.html` | 測試執行頁：iframe 載入 Demo，取得 `records.test.js` 並在 iframe 內執行，顯示結果 |
| `tests/records.test.js` | 測試案例（在 Demo 全域環境內執行） |
| `.claude/launch.json` | 本機靜態伺服器設定（`python -m http.server 8000`） |
| `README.md` | 新增 F11、更新 F5 與資料模型 |

## 如何執行測試（每個 Task 都用）

1. 啟動伺服器：用 Browser pane 的 `preview_start`（name: `demo`），或在專案根目錄執行：
   ```bash
   python -m http.server 8000
   ```
2. 開啟 `http://localhost:8000/tests/records.html`。
3. 讀取 `#sum` 的文字（例如用 `get_page_text`，或 javascript_tool 執行 `document.getElementById('sum').textContent`）。失敗項目的錯誤訊息列在 `#out`。
4. 修改 Demo 或測試後重新整理頁面（測試檔以 `cache: 'no-store'` 取得；Demo 本身若有快取，使用強制重新整理）。

以下「Run tests」步驟都指這個流程。

---

### Task 1: 測試頁、資料版本 v3、fileStore、resetAll

**Files:**
- Create: `.claude/launch.json`
- Create: `tests/records.html`
- Create: `tests/records.test.js`
- Modify: `projectflow-full-demo.html`（常數區、`seed()`、`load()`、`save()`、重置按鈕處理、啟動區）

**Interfaces:**
- Produces:
  - 常數 `MAX_FILE`（number）、`RESULT`（`{ met, partial, unmet }` → 中文）、`FIELD_TYPES`（`{ text, number, date, select }` → 中文）
  - `db.reportFields[]`、`db.reports[]`、`db.notes[]`、`db.attachments[]`（欄位見 spec 第 7 節）
  - `upgrade(o)`：把 `{ v, db, audit }` 從 v2 轉成 v3（原地修改並回傳 `o`）
  - `fileStore.check(): Promise<boolean>`、`fileStore.ok: boolean|null`、`fileStore.put(id, blob): Promise`、`fileStore.get(id): Promise<Blob|undefined>`、`fileStore.clear(): Promise`
  - `resetAll(): Promise`：重置 db、audit、復原堆疊、ui 狀態與 IndexedDB，並重新渲染

- [ ] **Step 1: 建立 `.claude/launch.json`**

```json
{
  "version": "0.0.1",
  "configurations": [
    { "name": "demo", "runtimeExecutable": "python", "runtimeArgs": ["-m", "http.server", "8000"], "port": 8000 }
  ]
}
```

- [ ] **Step 2: 建立測試執行頁 `tests/records.html`**

```html
<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>任務紀錄測試</title>
<style>
body{font:14px/1.6 system-ui,sans-serif;margin:16px;background:#fff;color:#222}
.pass{color:#1F5F5B}.fail{color:#B3261E;white-space:pre-wrap}
iframe{width:100%;height:600px;border:1px solid #ccc;margin-top:12px}
</style>
</head>
<body>
<h1>任務紀錄與跳過任務 測試</h1>
<p id="sum">執行中…</p>
<ol id="out"></ol>
<iframe id="app" src="../projectflow-full-demo.html"></iframe>
<script>
const frame = document.getElementById('app');
frame.addEventListener('load', async () => {
  const w = frame.contentWindow;
  let results;
  try {
    const src = await (await fetch('records.test.js', { cache: 'no-store' })).text();
    results = await w.eval(src);
  } catch (e) {
    results = [{ name: '載入測試', ok: false, err: String(e && e.stack || e) }];
  }
  const fails = results.filter((r) => !r.ok);
  document.getElementById('sum').textContent = fails.length ? `失敗 ${fails.length}/${results.length}` : `全部通過 ${results.length}/${results.length}`;
  document.getElementById('out').innerHTML = results.map((r) => `<li class="${r.ok ? 'pass' : 'fail'}">${r.ok ? '✓' : '✗'} ${r.name}${r.ok ? '' : '\n' + r.err.replace(/</g, '&lt;')}</li>`).join('');
  window.__results = results;
});
</script>
</body>
</html>
```

- [ ] **Step 3: 建立 `tests/records.test.js`，寫入第一批（會失敗的）測試**

```js
// 在 Demo 的全域環境內執行（由 tests/records.html 以 iframe.contentWindow.eval 載入）
(async () => {
  const results = [];
  const eq = (a, b, m) => { if (JSON.stringify(a) !== JSON.stringify(b)) throw new Error(`${m || ''} 預期 ${JSON.stringify(b)}，實際 ${JSON.stringify(a)}`); };
  const ok = (v, m) => { if (!v) throw new Error(m || '預期為真'); };
  const as = (u) => { ui.me = u; };
  const T = async (name, fn) => {
    try { await resetAll(); as('yu'); await fn(); results.push({ name, ok: true }); }
    catch (e) { results.push({ name, ok: false, err: String(e && e.stack || e) }); }
  };

  // ── Task 1：資料版本與儲存 ──
  await T('種子資料為 v3 且含四個新陣列', () => {
    eq(db.v, 3);
    ['reportFields', 'reports', 'notes', 'attachments'].forEach((k) => ok(Array.isArray(db[k]), k + ' 應為陣列'));
  });
  await T('種子資料：F0 測試有「F0 值」欄位，t3011 有已核准回報', () => {
    const f = db.reportFields.filter((x) => x.label === 'F0 值').map((x) => x.node_id).sort();
    eq(f, ['t3011', 't3013']);
    const r = db.reports.find((x) => x.node_id === 't3011');
    eq(r.status, 'approved'); eq(r.fields[0].value, 2.6);
  });
  await T('upgrade：v2 資料轉成 v3', () => {
    const d = seed(); d.v = 2;
    delete d.reportFields; delete d.reports; delete d.notes; delete d.attachments;
    d.overrides = [{ id: 'o1', gate: true, node: 'p1b', status: 'approved' }, { id: 'o2', node: 't302', status: 'pending' }];
    const o = upgrade({ v: 2, db: d, audit: freshAudit() });
    eq(o.v, 3); eq(o.db.v, 3);
    eq(o.db.overrides.map((x) => x.kind), ['gate', 'dep']);
    eq(o.db.reportFields.length, 2); eq(o.db.reports.length, 1);
    eq(o.db.notes, []); eq(o.db.attachments, []);
  });
  await T('fileStore：存入、讀出、清空', async () => {
    ok(await fileStore.check(), 'IndexedDB 應可使用');
    await fileStore.put('x1', new Blob(['hi'], { type: 'text/plain' }));
    eq(await (await fileStore.get('x1')).text(), 'hi');
    await fileStore.clear();
    eq(await fileStore.get('x1'), undefined);
  });

  // ── 新測試加在這一行上面 ──
  return results;
})()
```

- [ ] **Step 4: Run tests — 確認失敗**

Expected: `#sum` 顯示「失敗 …」，錯誤包含 `resetAll is not defined`。

- [ ] **Step 5: 新增常數**

在 `projectflow-full-demo.html` 找到這一行：

```js
const DEPTYPE = { FS: '完成→開始', SS: '開始→開始', FF: '完成→完成' };
```

在它下面加入：

```js
const RESULT = { met: '達成', partial: '部分達成', unmet: '未達成' };
const FIELD_TYPES = { text: '文字', number: '數字', date: '日期', select: '選項' };
const MAX_FILE = 10 * 1024 * 1024;
```

- [ ] **Step 6: 修改 `seed()`**

把：

```js
  const db = { v: 2, nodes: {}, deps: [], gates: {}, docs: [], templates: [], overrides: [], policy: 'hybrid', seq: 1000, erpSynced: 0 };
```

改成：

```js
  const db = { v: 3, nodes: {}, deps: [], gates: {}, docs: [], templates: [], overrides: [], policy: 'hybrid', seq: 1000, erpSynced: 0, reportFields: [], reports: [], notes: [], attachments: [] };
```

找到這一行（t3013 的節點）：

```js
  N('t3013', 't301', 'task', '第 2 次 F0 測試', { tag: '製程', who: 'ming', s: '2026-09-28', e: '2026-10-05' });
```

在它下面加入：

```js
  // F11：F0 測試的回報欄位與範例回報
  ['t3011', 't3013'].forEach((id) => db.reportFields.push({ id: 'rf-' + id, node_id: id, key: 'f0', label: 'F0 值', type: 'number', unit: '', options: [], required: true, order: 0 }));
  db.reports.push({ id: 'r1', node_id: 't3011', version: 1, result: 'unmet', summary: 'F0 = 2.6，未達目標 3.0，需調整殺菌時間', finished_on: '2026-09-12', fields: [{ key: 'f0', label: 'F0 值', value: 2.6, unit: '' }], status: 'approved', submitted_by: 'ming', submitted_at: '2026/09/12 16:20', reviewed_by: 'chen', reviewed_at: '2026/09/13 09:05', review_comment: '', self_approved: false });
```

- [ ] **Step 7: 新增 `upgrade()`，修改 `load()` 與 `save()`**

把：

```js
function load() {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) { const o = JSON.parse(raw); if (o && o.v === 2 && o.db && o.audit) { db = o.db; audit = o.audit; if (o.me && USERS[o.me]) ui.me = o.me; return; } }
  } catch (e) { /* 無法讀取時使用種子資料 */ }
  db = seed(); audit = freshAudit();
}
```

改成：

```js
// v2 → v3：補上任務紀錄的陣列、為覆寫紀錄補 kind、補範例的 F0 欄位與回報
function upgrade(o) {
  if (o.v === 2) {
    const d = o.db;
    Object.assign(d, { reportFields: d.reportFields || [], reports: d.reports || [], notes: d.notes || [], attachments: d.attachments || [] });
    d.overrides.forEach((x) => { if (!x.kind) x.kind = x.gate ? 'gate' : 'dep'; });
    const s = seed();
    s.reportFields.forEach((f) => { if (d.nodes[f.node_id] && !d.reportFields.some((x) => x.id === f.id)) d.reportFields.push(f); });
    s.reports.forEach((r) => { if (d.nodes[r.node_id] && !d.reports.some((x) => x.id === r.id)) d.reports.push(r); });
    d.v = 3; o.v = 3;
  }
  return o;
}
function load() {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) { const o = JSON.parse(raw); if (o && (o.v === 2 || o.v === 3) && o.db && o.audit) { upgrade(o); db = o.db; audit = o.audit; if (o.me && USERS[o.me]) ui.me = o.me; return; } }
  } catch (e) { /* 無法讀取時使用種子資料 */ }
  db = seed(); audit = freshAudit();
}
```

把 `save()` 裡的 `v: 2` 改成 `v: 3`：

```js
function save() { try { localStorage.setItem(KEY, JSON.stringify({ v: 3, db, audit, me: ui.me })); } catch (e) { /* 忽略 */ } }
```

- [ ] **Step 8: 新增 fileStore 與 resetAll**

找到第一個 `<script>` 結尾的 `notify` 函式：

```js
function notify(text, title = '活動紀錄') { ui.chat.push({ title, text }); audit.notes.unshift({ at: nowStr(), text }); if (ui.chat.length > 80) ui.chat.shift(); renderChat(); }
```

在它下面（`</script>` 之前）加入：

```js

/* ================= 任務紀錄（F11）與跳過任務 ================= */
// 附件檔案內容存在 IndexedDB（key = 附件 id），中繼資料存在 db.attachments
const fileStore = (() => {
  let dbp = null;
  const open = () => dbp || (dbp = new Promise((res, rej) => {
    try {
      const rq = indexedDB.open('projectflow-files', 1);
      rq.onupgradeneeded = () => rq.result.createObjectStore('blobs');
      rq.onsuccess = () => res(rq.result);
      rq.onerror = () => rej(rq.error);
    } catch (e) { rej(e); }
  }));
  const tx = (mode, fn) => open().then((d) => new Promise((res, rej) => {
    const t = d.transaction('blobs', mode);
    const r = fn(t.objectStore('blobs'));
    t.oncomplete = () => res(r ? r.result : undefined);
    t.onerror = () => rej(t.error);
  }));
  return {
    ok: null,
    async check() { try { await open(); this.ok = true; } catch (e) { this.ok = false; dbp = null; } return this.ok; },
    put: (id, blob) => tx('readwrite', (st) => st.put(blob, id)),
    get: (id) => tx('readonly', (st) => st.get(id)),
    clear: () => tx('readwrite', (st) => st.clear()).catch(() => {}),
  };
})();
function resetAll() {
  try { localStorage.removeItem(KEY); } catch (err) { /* 忽略 */ }
  db = seed(); audit = freshAudit(); undoStack.length = 0;
  Object.assign(ui, { page: 'node', node: 'p1', tab: 'board', chat: [], expanded: {}, redteam: '' });
  render();
  return fileStore.clear();
}
```

- [ ] **Step 9: 重置按鈕改用 resetAll，啟動時檢查 fileStore**

把：

```js
  if (t.id === 'resetBtn') { try { localStorage.removeItem(KEY); } catch (err) { /* 忽略 */ } db = seed(); audit = freshAudit(); undoStack.length = 0; Object.assign(ui, { page: 'node', node: 'p1', tab: 'board', chat: [], expanded: {}, redteam: '' }); render(); return toast('已重置 Demo 資料'); }
```

改成：

```js
  if (t.id === 'resetBtn') { resetAll(); return toast('已重置 Demo 資料'); }
```

在檔案最後的啟動區，把：

```js
render();
</script>
</body>
```

改成：

```js
render();
fileStore.check().then(() => render());
</script>
</body>
```

- [ ] **Step 10: Run tests — 確認通過**

Expected: `全部通過 4/4`。另外手動開 `http://localhost:8000/projectflow-full-demo.html`，確認畫面正常、按「重置 Demo 資料」沒有錯誤（開發者工具 Console 無紅字）。

---

### Task 2: 完成回報核心邏輯（送出、確認、退回、拖曳防呆）

**Files:**
- Modify: `projectflow-full-demo.html`（F11 核心區、`setStatus()`、`pendingCount()`）
- Test: `tests/records.test.js`

**Interfaces:**
- Consumes: `RESULT`、`MAX_FILE`、`db.reportFields`、`db.reports`（Task 1）
- Produces:
  - `fieldDefs(nodeId): Field[]`（依 `order` 排序）
  - `reportsOf(nodeId): Report[]`（新版本在前）
  - `pendingReport(nodeId): Report|null`
  - `canReport(n): boolean`
  - `validateReport(nodeId, data): string[]`；`data = { result, summary, finished_on, values: { [key]: string|number }, files?: File[] }`
  - `buildReport(nodeId, data): Report`
  - `submitReport(nodeId, data, opts?: { selfApprove?: boolean }): Promise<{ ok, errors?, blocked?, report? }>`（附件上傳在 Task 4 接上）
  - `decideReport(reportId, ok: boolean, comment?: string, opts?: { self?: boolean }): boolean`

- [ ] **Step 1: 寫測試**

在 `tests/records.test.js` 的 `// ── 新測試加在這一行上面 ──` 上方加入：

```js
  // ── Task 2：完成回報 ──
  const good = { result: 'met', summary: '參數設定完成', finished_on: '2026-09-30', values: {} };
  await T('validateReport：必填與數字檢查', () => {
    eq(validateReport('t3013', { result: '', summary: '', finished_on: '', values: {} }), ['請選擇結果', '請填寫成果說明', '請填寫實際完成日', '請填寫「F0 值」']);
    eq(validateReport('t3013', { ...good, values: { f0: 'abc' } }), ['「F0 值」必須是數字']);
    eq(validateReport('t3013', { ...good, values: { f0: '3.1' } }), []);
  });
  await T('成員送出回報 → 審核中，回報為 submitted', async () => {
    as('ming');
    const r = await submitReport('t30121', good);
    ok(r.ok, JSON.stringify(r.errors));
    eq(node('t30121').status, 'review');
    eq(pendingReport('t30121').version, 1);
    eq(pendingReport('t30121').submitted_by, 'ming');
    ok(!canReport(node('t30121')), '待確認時不能重複送出');
  });
  await T('硬性前置未滿足時不能送出', async () => {
    as('ming');
    const r = await submitReport('t3013', { ...good, values: { f0: 3.1 } });
    ok(!r.ok && r.blocked, '應回傳 blocked');
    eq(node('t3013').status, 'todo'); eq(db.reports.filter((x) => x.node_id === 't3013').length, 0);
  });
  await T('成員不能確認；主管退回（意見必填）→ 進行中；重送 → v2；確認 → 已完成', async () => {
    as('ming'); await submitReport('t30121', good);
    const r1 = pendingReport('t30121');
    ok(!decideReport(r1.id, true), '成員不能確認');
    as('yu');
    ok(!decideReport(r1.id, false, '  '), '退回必須有意見');
    ok(decideReport(r1.id, false, '請附參數截圖'));
    eq(r1.status, 'rejected'); eq(r1.review_comment, '請附參數截圖'); eq(node('t30121').status, 'doing');
    as('ming'); await submitReport('t30121', { ...good, summary: '已附截圖' });
    const r2 = pendingReport('t30121'); eq(r2.version, 2);
    as('chen'); ok(decideReport(r2.id, true), '範圍內審核人可以確認');
    eq(r2.status, 'approved'); eq(r2.reviewed_by, 'chen'); eq(node('t30121').status, 'done');
  });
  await T('主管送出並直接確認', async () => {
    const r = await submitReport('t30121', good, { selfApprove: true });
    ok(r.ok); eq(r.report.status, 'approved'); eq(r.report.self_approved, true); eq(node('t30121').status, 'done');
  });
  await T('拖曳防呆：有待確認回報時，成員拖到已完成被擋，主管拖到已完成視同確認', async () => {
    as('ming'); await submitReport('t30121', good);
    ok(!setStatus('t30121', 'done')); eq(node('t30121').status, 'review');
    ok(!setStatus('t30121', 'doing')); eq(node('t30121').status, 'review');
    as('yu'); setStatus('t30121', 'done');
    eq(node('t30121').status, 'done'); eq(db.reports.find((x) => x.node_id === 't30121').status, 'approved');
  });
  await T('待審數量包含待確認回報', async () => {
    const before = pendingCount();
    as('ming'); await submitReport('t30121', good);
    as('yu'); eq(pendingCount(), before + 1);
  });
```

- [ ] **Step 2: Run tests — 確認新測試失敗**

Expected: 新增的 7 項失敗，錯誤包含 `validateReport is not defined` 等。

- [ ] **Step 3: 實作核心函式**

在 Task 1 加入的 `resetAll()` 函式下面加入：

```js
/* ---------- 完成回報 ---------- */
function fieldDefs(nodeId) { return db.reportFields.filter((f) => f.node_id === nodeId).sort((a, b) => a.order - b.order); }
function reportsOf(nodeId) { return db.reports.filter((r) => r.node_id === nodeId).sort((a, b) => b.version - a.version); }
function pendingReport(nodeId) { return db.reports.find((r) => r.node_id === nodeId && r.status === 'submitted') || null; }
function canReport(n) { return !!n && n.type === 'task' && isLeaf(n) && can('edit', n) && !DONE(n.status) && !pendingReport(n.id); }
function validateReport(nodeId, data) {
  const errors = [];
  if (!RESULT[data.result]) errors.push('請選擇結果');
  if (!String(data.summary || '').trim()) errors.push('請填寫成果說明');
  if (!/^\d{4}-\d{2}-\d{2}$/.test(data.finished_on || '')) errors.push('請填寫實際完成日');
  fieldDefs(nodeId).forEach((f) => {
    const raw = (data.values || {})[f.key];
    const empty = raw === undefined || raw === null || String(raw).trim() === '';
    if (f.required && empty) errors.push(`請填寫「${f.label}」`);
    else if (!empty && f.type === 'number' && !Number.isFinite(Number(raw))) errors.push(`「${f.label}」必須是數字`);
    else if (!empty && f.type === 'select' && !f.options.includes(String(raw))) errors.push(`「${f.label}」的選項不正確`);
  });
  (data.files || []).forEach((x) => { if (x.size > MAX_FILE) errors.push(`「${x.name}」超過 10 MB`); });
  return errors;
}
function buildReport(nodeId, data) {
  const prev = db.reports.filter((r) => r.node_id === nodeId);
  return {
    id: newId('r'), node_id: nodeId, version: prev.length ? Math.max(...prev.map((r) => r.version)) + 1 : 1,
    result: data.result, summary: String(data.summary).trim(), finished_on: data.finished_on,
    // 標籤與單位存快照：欄位定義之後被改，舊回報仍讀得懂
    fields: fieldDefs(nodeId).map((f) => {
      const raw = (data.values || {})[f.key];
      const value = raw === undefined || raw === null || String(raw).trim() === '' ? null : f.type === 'number' ? Number(raw) : String(raw);
      return { key: f.key, label: f.label, value, unit: f.unit || '' };
    }),
    status: 'submitted', submitted_by: ui.me, submitted_at: nowStr(), reviewed_by: null, reviewed_at: null, review_comment: '', self_approved: false,
  };
}
async function submitReport(nodeId, data, opts = {}) {
  const n = node(nodeId);
  if (!canReport(n)) return { ok: false, errors: ['這個任務目前不能送出完成回報'] };
  const errors = validateReport(nodeId, data);
  if (errors.length) return { ok: false, errors };
  const hard = findBlockers(n, 'review').filter((b) => b.hard);
  if (hard.length) return { ok: false, blocked: true, errors: hard.map((b) => b.text) };
  const r = buildReport(nodeId, data);
  commit(`送出「${n.title}」完成回報`, () => { db.reports.push(r); });
  log(n.id, '完成回報', `送出「${n.title}」完成回報 v${r.version}：${RESULT[r.result]}`);
  setStatus(n.id, 'review', { system: '送出完成回報' });
  if (opts.selfApprove && can('override', n)) decideReport(r.id, true, '', { self: true });
  else notify(`${uname(ui.me)} 送出「${n.title}」完成回報 v${r.version}（${RESULT[r.result]}），等待確認：${approversFor(n).map(uname).join('、')}`, '完成回報');
  return { ok: true, report: r };
}
function decideReport(reportId, ok, comment = '', opts = {}) {
  const r = db.reports.find((x) => x.id === reportId);
  if (!r || r.status !== 'submitted') return false;
  const n = node(r.node_id);
  if (!n || !can('override', n)) { toast('你的角色無權審核此完成回報', 'warn'); return false; }
  const why = String(comment || '').trim();
  if (!ok && !why) { toast('退回時請填寫意見', 'warn'); return false; }
  commit(`${ok ? '確認' : '退回'}「${n.title}」完成回報`, () => {
    Object.assign(r, { status: ok ? 'approved' : 'rejected', reviewed_by: ui.me, reviewed_at: nowStr(), review_comment: why, self_approved: !!opts.self });
  });
  log(n.id, '完成回報', `${ok ? (opts.self ? '自行確認' : '確認') : '退回'}「${n.title}」完成回報 v${r.version}${why ? `，意見：${why}` : ''}`);
  setStatus(n.id, ok ? 'done' : 'doing', { force: true, system: ok ? (opts.self ? '完成回報自行確認' : '完成回報確認') : '完成回報退回' });
  if (!opts.self) notify(`${uname(ui.me)} ${ok ? '確認' : '退回'}了「${n.title}」的完成回報 v${r.version}${ok ? '' : `，意見：${why}`}`, '完成回報');
  return true;
}
```

- [ ] **Step 4: 在 `setStatus()` 加上待確認回報的防呆**

在 `setStatus` 裡找到：

```js
  if (!n || n.status === to) return true;
  if (!opts.system && !can('edit', n)) { toast('你的角色無權變更此任務', 'warn'); return false; }
```

改成：

```js
  if (!n || n.status === to) return true;
  const pr = !opts.system ? pendingReport(id) : null;
  if (pr) {
    // 有待確認的完成回報：拖到已完成＝確認（需權限），其他移動一律擋下
    if (to === 'done' && can('override', n)) return decideReport(pr.id, true);
    toast(to === 'done' ? `此任務有待確認的完成回報，需由 ${approversFor(n).map(uname).join('、')} 確認` : '此任務有待確認的完成回報，請到「紀錄」分頁確認或退回', 'warn');
    render(); return false;
  }
  if (!opts.system && !can('edit', n)) { toast('你的角色無權變更此任務', 'warn'); return false; }
```

- [ ] **Step 5: `pendingCount()` 加入待確認回報**

把：

```js
function pendingCount() {
  return db.overrides.filter((o) => o.status === 'pending' && can('override', node(o.node) || null)).length
    + db.ops.formulas.flatMap((f) => f.versions).filter((v) => v.request === 'pending' && can('formula-approve')).length;
}
```

改成：

```js
function pendingCount() {
  return db.overrides.filter((o) => o.status === 'pending' && can('override', node(o.node) || null)).length
    + db.reports.filter((r) => r.status === 'submitted' && node(r.node_id) && can('override', node(r.node_id))).length
    + db.ops.formulas.flatMap((f) => f.versions).filter((v) => v.request === 'pending' && can('formula-approve')).length;
}
```

- [ ] **Step 6: Run tests — 確認全部通過**

Expected: `全部通過 11/11`。

---

### Task 3: 自訂回報欄位（編輯器、模板、複製、刪除）

**Files:**
- Modify: `projectflow-full-demo.html`（F11 核心區、`openEditor()`、`nodeToTemplate()`、`applyTemplate()`、`copySubtree()`、`deleteNode()`、click 事件）
- Test: `tests/records.test.js`

**Interfaces:**
- Consumes: `FIELD_TYPES`、`fieldDefs()`（Task 1、2）
- Produces:
  - `pushField(nodeId, f, order): Field`（直接寫入，不包 commit；給模板與複製使用）
  - `addReportField(nodeId, { label, type, extra, required }): { ok, error?, field? }`（`extra`：數字的單位，或選項的逗號分隔清單）
  - `removeReportField(id): void`
  - `moveReportField(id): void`（和上一個欄位交換順序）
  - 模板節點新增屬性 `fields: [{ label, type, unit, options, required }]`

- [ ] **Step 1: 寫測試**

```js
  // ── Task 3：自訂回報欄位 ──
  await T('新增、上移、移除回報欄位', () => {
    eq(addReportField('t30121', { label: '', type: 'text', extra: '', required: false }).ok, false);
    eq(addReportField('t30121', { label: '結果', type: 'select', extra: '只有一個', required: false }).error, '選項欄位至少要有 2 個選項');
    ok(addReportField('t30121', { label: '溫度', type: 'number', extra: '°C', required: true }).ok);
    ok(addReportField('t30121', { label: '設備', type: 'select', extra: 'R-1, R-2，R-3', required: false }).ok);
    let d = fieldDefs('t30121');
    eq(d.map((x) => x.label), ['溫度', '設備']); eq(d[0].unit, '°C'); eq(d[1].options, ['R-1', 'R-2', 'R-3']);
    moveReportField(d[1].id);
    eq(fieldDefs('t30121').map((x) => x.label), ['設備', '溫度']);
    removeReportField(d[1].id);
    eq(fieldDefs('t30121').map((x) => x.label), ['溫度']);
  });
  await T('另存模板與套用模板會帶著回報欄位', () => {
    const t = nodeToTemplate('t301');
    const withF = t.nodes.filter((x) => (x.fields || []).length);
    eq(withF.length, 2); eq(withF[0].fields[0].label, 'F0 值');
    const before = db.reportFields.filter((f) => f.label === 'F0 值').length;
    applyTemplate(t, 'p1c', { start: TODAY, vars: {}, structure: true, deps: false, owners: false, dates: true, docs: false });
    eq(db.reportFields.filter((f) => f.label === 'F0 值').length, before + 2);
  });
  await T('複製子樹帶欄位；刪除節點清掉欄位、回報、筆記並軟刪除附件', () => {
    const nid = copySubtree('t301');
    const copied = descendants(nid).map((x) => x.id);
    eq(db.reportFields.filter((f) => copied.includes(f.node_id)).length, 2);
    db.notes.push({ id: 'ntx', node_id: 't3011', body: 'x', author: 'yu', created_at: nowStr(), edited_at: null });
    db.attachments.push({ id: 'atx', node_id: 't3011', report_id: null, note_id: null, filename: 'a.txt', mime: 'text/plain', size: 1, sha256: '', storage_key: 'atx', uploaded_by: 'yu', uploaded_at: nowStr(), deleted_at: null });
    deleteNode('t301');
    eq(db.reportFields.filter((f) => ['t3011', 't3013'].includes(f.node_id)).length, 0);
    eq(db.reports.filter((r) => r.node_id === 't3011').length, 0);
    eq(db.notes.filter((x) => x.id === 'ntx').length, 0);
    ok(db.attachments.find((a) => a.id === 'atx').deleted_at, '附件應被軟刪除');
  });
```

- [ ] **Step 2: Run tests — 確認新測試失敗**

Expected: 3 項失敗（`addReportField is not defined`）。

- [ ] **Step 3: 實作欄位函式**

在 Task 2 的 `decideReport()` 下面加入：

```js
/* ---------- 自訂回報欄位 ---------- */
function pushField(nodeId, f, order) {
  const d = { id: newId('rf'), node_id: nodeId, key: newId('f'), label: f.label, type: f.type, unit: f.unit || '', options: [...(f.options || [])], required: !!f.required, order };
  db.reportFields.push(d);
  return d;
}
function addReportField(nodeId, { label, type, extra, required }) {
  const n = node(nodeId);
  if (!n || !can('edit', n)) return { ok: false, error: '你的角色無權編輯此任務' };
  const lb = String(label || '').trim();
  if (!lb) return { ok: false, error: '請輸入欄位名稱' };
  if (!FIELD_TYPES[type]) return { ok: false, error: '欄位類型不正確' };
  const options = type === 'select' ? String(extra || '').split(/[,，、]/).map((s) => s.trim()).filter(Boolean) : [];
  if (type === 'select' && options.length < 2) return { ok: false, error: '選項欄位至少要有 2 個選項' };
  const unit = type === 'number' ? String(extra || '').trim() : '';
  const defs = fieldDefs(nodeId);
  let field;
  commit(`新增回報欄位「${lb}」`, () => { field = pushField(nodeId, { label: lb, type, unit, options, required }, defs.length ? defs[defs.length - 1].order + 1 : 0); });
  log(nodeId, '回報欄位', `「${n.title}」新增回報欄位「${lb}」（${FIELD_TYPES[type]}${required ? '，必填' : ''}）`);
  return { ok: true, field };
}
function removeReportField(id) {
  const f = db.reportFields.find((x) => x.id === id); if (!f) return;
  commit(`移除回報欄位「${f.label}」`, () => { db.reportFields = db.reportFields.filter((x) => x.id !== id); });
  log(f.node_id, '回報欄位', `移除回報欄位「${f.label}」`);
}
function moveReportField(id) {
  const defs = fieldDefs((db.reportFields.find((x) => x.id === id) || {}).node_id);
  const i = defs.findIndex((x) => x.id === id);
  if (i <= 0) return;
  commit('調整回報欄位順序', () => { const a = defs[i], b = defs[i - 1]; [a.order, b.order] = [b.order, a.order]; });
}
```

- [ ] **Step 4: 模板、複製、刪除帶上欄位**

`nodeToTemplate()` 裡把：

```js
    nodes.push({ k: pk === null ? 'r' : k, p: pk, title: x.title, tag: x.tag, off: a - r0, dur: b - a, who: x.owner, dp: x.depts, ms: x.milestone });
```

改成：

```js
    nodes.push({ k: pk === null ? 'r' : k, p: pk, title: x.title, tag: x.tag, off: a - r0, dur: b - a, who: x.owner, dp: x.depts, ms: x.milestone,
      fields: fieldDefs(x.id).map(({ label, type, unit, options, required }) => ({ label, type, unit, options, required })) });
```

`applyTemplate()` 裡把：

```js
    map[x.k] = addNode(par, { title: sub(x.title), tag: x.tag, start: S(s), end: S(Math.max(s, e)), owner: opt.owners && x.who ? x.who : ui.me, depts: opt.owners ? (x.dp || []) : [], milestone: !!x.ms });
```

改成：

```js
    map[x.k] = addNode(par, { title: sub(x.title), tag: x.tag, start: S(s), end: S(Math.max(s, e)), owner: opt.owners && x.who ? x.who : ui.me, depts: opt.owners ? (x.dp || []) : [], milestone: !!x.ms });
    (x.fields || []).forEach((f, i) => pushField(map[x.k], f, i));
```

`copySubtree()` 裡把：

```js
      db.nodes[nid] = { ...clone(src), id: nid, parent, title: src.id === id ? src.title + '（複本）' : src.title, status: 'todo', progress: null, order: src.order + 0.5 };
```

改成：

```js
      db.nodes[nid] = { ...clone(src), id: nid, parent, title: src.id === id ? src.title + '（複本）' : src.title, status: 'todo', progress: null, order: src.order + 0.5 };
      fieldDefs(src.id).forEach((f, i) => pushField(nid, f, i));
```

`deleteNode()` 裡把：

```js
    db.docs = db.docs.filter((d) => !fam.has(d.node));
```

改成：

```js
    db.docs = db.docs.filter((d) => !fam.has(d.node));
    db.reportFields = db.reportFields.filter((f) => !fam.has(f.node_id));
    db.reports = db.reports.filter((r) => !fam.has(r.node_id));
    db.notes = db.notes.filter((x) => !fam.has(x.node_id));
    db.attachments.forEach((a) => { if (fam.has(a.node_id) && !a.deleted_at) a.deleted_at = nowStr(); });
```

- [ ] **Step 5: 編輯器加上「回報欄位」區塊**

`openEditor()` 裡找到備註欄位這一行：

```js
    <div class="field"><label for="eNote">備註</label><textarea id="eNote" style="min-height:60px" ${ed ? '' : 'disabled'}>${esc(n.note)}</textarea></div>
```

在它下面加入：

```js
    ${leaf && n.type === 'task' ? `<div class="field"><span class="lb">回報欄位（完成回報時要填的自訂欄位）</span>
      ${fieldDefs(n.id).map((f) => `<div class="deprow"><span style="flex-grow:1">${esc(f.label)} <span class="tag gray">${FIELD_TYPES[f.type]}${f.unit ? '・' + esc(f.unit) : ''}</span>${f.required ? ' <span class="tag warn">必填</span>' : ''}${f.type === 'select' ? ` <span class="small muted">${esc(f.options.join('、'))}</span>` : ''}</span>
        <button class="iconbtn" type="button" data-rf-up="${f.id}" ${ed ? '' : 'disabled'} aria-label="上移">↑</button><button class="iconbtn" type="button" data-rf-del="${f.id}" ${ed ? '' : 'disabled'} aria-label="移除">✕</button></div>`).join('') || '<div class="small muted">無（只填固定欄位：結果、成果說明、完成日、附件）</div>'}
      ${ed ? `<div class="deprow"><input id="rfLabel" placeholder="欄位名稱，例如 F0 值" style="flex-grow:1;min-width:120px">
        <select id="rfType">${Object.entries(FIELD_TYPES).map(([k, l]) => `<option value="${k}">${l}</option>`).join('')}</select>
        <input id="rfExtra" placeholder="單位，或選項（逗號分隔）" style="width:170px">
        <label class="small"><input type="checkbox" id="rfReq">必填</label>
        <button class="btn sm" type="button" data-rf-add="${n.id}">加入</button></div>` : ''}</div>` : ''}
```

- [ ] **Step 6: click 事件**

在 click 委派裡找到：

```js
  if (ds.depDel) {
```

在它上面加入：

```js
  if (ds.rfAdd) {
    const r = addReportField(ds.rfAdd, { label: $('rfLabel').value, type: $('rfType').value, extra: $('rfExtra').value, required: $('rfReq').checked });
    if (!r.ok) return toast(r.error, 'warn');
    return openEditor(ds.rfAdd);
  }
  if (ds.rfUp) { const f = db.reportFields.find((x) => x.id === ds.rfUp); moveReportField(ds.rfUp); return openEditor(f.node_id); }
  if (ds.rfDel) { const f = db.reportFields.find((x) => x.id === ds.rfDel); removeReportField(ds.rfDel); return openEditor(f.node_id); }
```

- [ ] **Step 7: Run tests — 確認全部通過**

Expected: `全部通過 14/14`。再手動開 Demo：進入「第 2 次 F0 測試」→ 編輯，看到「F0 值・必填」；新增一個「批號（文字）」欄位、上移、移除都正常。

---

### Task 4: 筆記與附件核心邏輯

**Files:**
- Modify: `projectflow-full-demo.html`（F11 核心區、`submitReport()`）
- Test: `tests/records.test.js`

**Interfaces:**
- Consumes: `fileStore`、`MAX_FILE`、`submitReport()`（Task 1、2）
- Produces:
  - `canNote(n): boolean`
  - `addNote(nodeId, body): { ok, error?, note? }`
  - `editNote(noteId, body): { ok, error?, note? }`
  - `sha256Hex(blob): Promise<string>`（不支援時回傳 `''`）
  - `addAttachments(nodeId, files: File[], link?: { reportId?, noteId? }): Promise<{ ok, errors: string[], added: Attachment[] }>`
  - `canDeleteAttachment(a): boolean`
  - `deleteAttachment(id): { ok, error? }`
  - `openAttachment(id): Promise<void>`
  - `submitReport` 會把 `data.files` 上傳並以 `report_id` 關聯

- [ ] **Step 1: 寫測試**

```js
  // ── Task 4：筆記與附件 ──
  const txt = (name, s) => new File([s], name, { type: 'text/plain' });
  await T('新增筆記；只有作者能修改，修改後標記已編輯並寫入稽核', () => {
    as('ming');
    eq(addNote('t30121', '   ').ok, false);
    const r = addNote('t30121', '設備溫度校正完成');
    ok(r.ok); eq(r.note.author, 'ming'); eq(r.note.edited_at, null);
    as('yu'); eq(editNote(r.note.id, '改掉').error, '只有作者可以修改筆記');
    as('ming'); ok(editNote(r.note.id, '設備溫度校正完成（121°C）').ok);
    ok(r.note.edited_at, '應有 edited_at');
    ok(audit.acts[0].text.includes('原內容：設備溫度校正完成'), '稽核紀錄應保留原內容');
  });
  await T('協作人員不能在未指派給他的任務寫筆記', () => { as('it'); ok(canNote(node('t30121'))); as('lin'); ok(!canNote(node('t30121'))); });
  await T('上傳附件：存入 IndexedDB、記錄中繼資料；超過 10 MB 被擋', async () => {
    as('ming');
    const big = new File([new Uint8Array(MAX_FILE + 1)], 'big.bin');
    const r = await addAttachments('t30121', [txt('參數.txt', '121C 30min'), big]);
    eq(r.added.length, 1); eq(r.errors, ['「big.bin」超過 10 MB，未上傳']);
    const a = r.added[0];
    eq([a.filename, a.size, a.uploaded_by, a.report_id, a.note_id], ['參數.txt', 10, 'ming', null, null]);
    eq(a.sha256.length, 64);
    eq(await (await fileStore.get(a.id)).text(), '121C 30min');
  });
  await T('刪除附件為軟刪除；回報附件不能刪除', async () => {
    as('ming');
    const a = (await addAttachments('t30121', [txt('a.txt', 'a')])).added[0];
    ok(deleteAttachment(a.id).ok); ok(db.attachments.find((x) => x.id === a.id).deleted_at);
    const rep = await submitReport('t30121', { result: 'met', summary: '完成', finished_on: '2026-09-30', values: {}, files: [txt('報告.txt', 'r')] });
    const ra = db.attachments.find((x) => x.report_id === rep.report.id);
    eq(ra.filename, '報告.txt');
    ok(!canDeleteAttachment(ra)); eq(deleteAttachment(ra.id).ok, false);
  });
```

注意：`lin` 是協作人員，`t30121` 不是指派給他的，所以 `can('edit')` 為假。

- [ ] **Step 2: Run tests — 確認新測試失敗**

Expected: 4 項失敗（`addNote is not defined`）。

- [ ] **Step 3: 實作筆記與附件函式**

在 Task 3 的 `moveReportField()` 下面加入：

```js
/* ---------- 筆記 ---------- */
function canNote(n) { return !!n && can('edit', n); }
function addNote(nodeId, body) {
  const n = node(nodeId);
  if (!canNote(n)) return { ok: false, error: '你的角色無權在此任務寫筆記' };
  const b = String(body || '').trim();
  if (!b) return { ok: false, error: '筆記內容不能空白' };
  const note = { id: newId('nt'), node_id: nodeId, body: b, author: ui.me, created_at: nowStr(), edited_at: null };
  commit('新增筆記', () => { db.notes.push(note); });
  log(nodeId, '筆記', `在「${n.title}」新增筆記`);
  return { ok: true, note };
}
function editNote(noteId, body) {
  const x = db.notes.find((y) => y.id === noteId);
  if (!x) return { ok: false, error: '找不到這則筆記' };
  if (x.author !== ui.me) return { ok: false, error: '只有作者可以修改筆記' };
  const b = String(body || '').trim();
  if (!b) return { ok: false, error: '筆記內容不能空白' };
  if (b === x.body) return { ok: true, note: x };
  const old = x.body;
  commit('修改筆記', () => { x.body = b; x.edited_at = nowStr(); });
  log(x.node_id, '筆記', `修改筆記（原內容：${old}）`);
  return { ok: true, note: x };
}

/* ---------- 附件 ---------- */
async function sha256Hex(blob) {
  try {
    const buf = await crypto.subtle.digest('SHA-256', await blob.arrayBuffer());
    return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, '0')).join('');
  } catch (e) { return ''; }
}
async function addAttachments(nodeId, files, link = {}) {
  const n = node(nodeId);
  if (!n || !can('edit', n)) return { ok: false, errors: ['你的角色無權上傳附件'], added: [] };
  if (!(await fileStore.check())) return { ok: false, errors: ['此瀏覽器無法儲存檔案'], added: [] };
  const errors = [], added = [];
  for (const f of files) {
    if (f.size > MAX_FILE) { errors.push(`「${f.name}」超過 10 MB，未上傳`); continue; }
    const id = newId('at');
    try { await fileStore.put(id, f); } catch (e) { errors.push(`「${f.name}」儲存失敗`); continue; }
    added.push({ id, node_id: nodeId, report_id: link.reportId || null, note_id: link.noteId || null, filename: f.name, mime: f.type || 'application/octet-stream', size: f.size, sha256: await sha256Hex(f), storage_key: id, uploaded_by: ui.me, uploaded_at: nowStr(), deleted_at: null });
  }
  if (added.length) {
    commit(`上傳 ${added.length} 個附件`, () => { db.attachments.push(...added); });
    log(nodeId, '附件', `上傳附件：${added.map((a) => a.filename).join('、')}`);
  }
  return { ok: errors.length === 0, errors, added };
}
// 回報送出後就鎖定，所以回報的附件不能刪
function canDeleteAttachment(a) { const n = node(a.node_id); return !!n && !a.deleted_at && !a.report_id && (a.uploaded_by === ui.me || can('delete', n)); }
function deleteAttachment(id) {
  const a = db.attachments.find((x) => x.id === id);
  if (!a || !canDeleteAttachment(a)) return { ok: false, error: a && a.report_id ? '回報的附件已鎖定，不能刪除' : '你無權刪除這個附件' };
  commit(`刪除附件「${a.filename}」`, () => { a.deleted_at = nowStr(); });
  log(a.node_id, '附件', `刪除附件「${a.filename}」`);
  return { ok: true };
}
async function openAttachment(id) {
  const a = db.attachments.find((x) => x.id === id);
  const blob = a && !a.deleted_at ? await fileStore.get(a.storage_key).catch(() => undefined) : undefined;
  if (!blob) return toast('找不到檔案內容（可能是在其他瀏覽器上傳，或資料已重置）', 'warn');
  const url = URL.createObjectURL(blob);
  if (/^image\/|pdf$/.test(a.mime)) window.open(url, '_blank');
  else { const el = document.createElement('a'); el.href = url; el.download = a.filename; el.click(); }
  setTimeout(() => URL.revokeObjectURL(url), 60000);
}
```

- [ ] **Step 4: `submitReport()` 上傳回報附件**

在 `submitReport()` 裡把：

```js
  log(n.id, '完成回報', `送出「${n.title}」完成回報 v${r.version}：${RESULT[r.result]}`);
  setStatus(n.id, 'review', { system: '送出完成回報' });
```

改成：

```js
  log(n.id, '完成回報', `送出「${n.title}」完成回報 v${r.version}：${RESULT[r.result]}`);
  if ((data.files || []).length) {
    const up = await addAttachments(n.id, data.files, { reportId: r.id });
    if (up.errors.length) toast(up.errors.join('；'), 'warn');
  }
  setStatus(n.id, 'review', { system: '送出完成回報' });
```

- [ ] **Step 5: Run tests — 確認全部通過**

Expected: `全部通過 18/18`。

---

### Task 5: 「紀錄」分頁、回報對話框、看板按鈕、審核中心區塊

**Files:**
- Modify: `projectflow-full-demo.html`（CSS、`pageNode()`、`cardHTML()`、`pageReview()`、UI 函式、click / submit 事件）
- Test: `tests/records.test.js`

**Interfaces:**
- Consumes: Task 2–4 的所有核心函式
- Produces:
  - `viewRecords(n): string`（HTML）
  - `reportHTML(r, src: boolean): string`、`noteHTML(x, src: boolean): string`、`attRows(list, src: boolean): string`
  - `openReportDialog(nodeId)`、`openRejectReport(reportId)`、`openNoteEdit(noteId)`
  - DOM：分頁 `data-tab="records"`；按鈕 `data-report`、`data-rep-approve`、`data-rep-reject`、`data-note-edit`、`data-att-open`、`data-att-del`；表單 `#reportForm`、`#rejectForm`、`#noteForm`、`#noteEditForm`、`#attForm`

- [ ] **Step 1: 寫測試（畫面有正確的元素）**

```js
  // ── Task 5：紀錄分頁與審核中心 ──
  await T('葉節點的紀錄分頁：回報按鈕、筆記表單、附件表單', () => {
    as('ming'); ui.page = 'node'; ui.node = 't30121'; ui.tab = 'records'; render();
    const m = document.getElementById('main');
    ok(m.querySelector('[data-tab="records"][aria-selected="true"]'), '應有「紀錄」分頁');
    ok(m.querySelector('[data-report="t30121"]'), '應有回報完成按鈕');
    ok(m.querySelector('#noteForm') && m.querySelector('#attForm'), '應有筆記與附件表單');
  });
  await T('上層節點的紀錄分頁彙總子樹且唯讀', () => {
    ui.page = 'node'; ui.node = 't301'; ui.tab = 'records'; render();
    const m = document.getElementById('main');
    ok(m.textContent.includes('F0 = 2.6'), '應顯示子任務 t3011 的回報');
    ok(!m.querySelector('#noteForm') && !m.querySelector('[data-report]'), '上層節點不能新增');
  });
  await T('回報對話框含自訂欄位；看板卡片有回報按鈕', () => {
    as('yu'); ui.page = 'node'; ui.node = 't3012'; ui.tab = 'board'; render();
    ok(document.querySelector('.card [data-report="t30121"]'), '進行中的卡片應有回報按鈕');
    openReportDialog('t3013');
    ok(document.getElementById('rv_f0'), '應有 F0 值欄位');
    ok(document.querySelector('#reportForm button[value="self"]'), '主管應有「送出並直接確認」');
    closeDlg();
  });
  await T('審核中心列出待確認回報', async () => {
    as('ming'); await submitReport('t30121', { result: 'met', summary: '完成', finished_on: '2026-09-30', values: {} });
    as('yu'); ui.page = 'review'; render();
    const m = document.getElementById('main');
    ok(m.textContent.includes('待確認的完成回報（1）'));
    ok(m.querySelector(`[data-rep-approve="${pendingReport('t30121').id}"]:not([disabled])`));
  });
```

- [ ] **Step 2: Run tests — 確認新測試失敗**

Expected: 4 項失敗。

- [ ] **Step 3: CSS**

找到：

```css
.stack{display:flex;flex-direction:column;gap:14px}
```

在它下面加入：

```css
.records{display:grid;gap:14px;max-width:920px}
.records h3{margin:0}
.rec{border-top:1px solid var(--line);padding:10px 0}
.rec:first-of-type{border-top:none}
.rec .body{margin-top:6px;white-space:pre-wrap;line-height:1.7}
```

- [ ] **Step 4: UI 函式**

找到：

```js
/* ================= 事件繫結 ================= */
```

在它上面加入：

```js
/* ================= 任務紀錄（F11）畫面 ================= */
const fmtSize = (b) => (b < 1024 ? b + ' B' : b < 1048576 ? (b / 1024).toFixed(1) + ' KB' : (b / 1048576).toFixed(1) + ' MB');
const attLink = (a) => `<button class="iconbtn" type="button" data-att-open="${a.id}">📎 ${esc(a.filename)}</button>`;
const srcLink = (id) => `<button class="iconbtn" type="button" data-enter="${id}">↳ ${esc(node(id).title)}</button>`;
function attOwner(a) { if (a.report_id) { const r = db.reports.find((x) => x.id === a.report_id); return r ? `回報 v${r.version}` : '回報'; } return a.note_id ? '筆記' : '任務'; }
function reportHTML(r, src) {
  const st = { submitted: '<span class="tag blue">待確認</span>', approved: '<span class="tag">已確認</span>', rejected: '<span class="tag warn">已退回</span>' }[r.status];
  const atts = db.attachments.filter((a) => a.report_id === r.id && !a.deleted_at);
  return `<div class="rec">
    <div class="row" style="justify-content:space-between"><div><b>v${r.version}</b> ${st} <span class="tag gray">${RESULT[r.result]}</span>${src ? ' ' + srcLink(r.node_id) : ''}</div>
      <span class="small muted">${esc(uname(r.submitted_by))} ${esc(r.submitted_at)}・完成日 ${ymd(r.finished_on)}</span></div>
    <div class="body">${esc(r.summary)}</div>
    ${r.fields.length ? `<dl class="kv" style="margin-top:6px">${r.fields.map((f) => `<dt>${esc(f.label)}</dt><dd>${f.value === null ? '—' : esc(f.value)}${f.unit ? ' ' + esc(f.unit) : ''}</dd>`).join('')}</dl>` : ''}
    ${atts.length ? `<div class="small" style="margin-top:6px">附件：${atts.map(attLink).join('、')}</div>` : ''}
    ${r.status !== 'submitted' ? `<div class="small muted" style="margin-top:6px">${r.status === 'approved' ? (r.self_approved ? '自行確認' : '確認') : '退回'}：${esc(uname(r.reviewed_by))} ${esc(r.reviewed_at)}${r.review_comment ? `・意見：${esc(r.review_comment)}` : ''}</div>` : ''}
  </div>`;
}
function noteHTML(x, src) {
  const atts = db.attachments.filter((a) => a.note_id === x.id && !a.deleted_at);
  return `<div class="rec">
    <div class="row" style="justify-content:space-between"><span class="row">${av(x.author, 22)}<b>${esc(uname(x.author))}</b><span class="small muted">${esc(x.created_at)}${x.edited_at ? `・已編輯 ${esc(x.edited_at)}` : ''}</span>${src ? srcLink(x.node_id) : ''}</span>
      ${!src && x.author === ui.me ? `<button class="iconbtn" type="button" data-note-edit="${x.id}">修改</button>` : ''}</div>
    <div class="body">${esc(x.body)}</div>
    ${atts.length ? `<div class="small" style="margin-top:6px">附件：${atts.map(attLink).join('、')}</div>` : ''}
  </div>`;
}
function attRows(list, src) {
  return `<div class="tbl-wrap"><table class="tbl"><thead><tr><th>檔名</th><th>大小</th><th>上傳者</th><th>時間</th><th>所屬</th>${src ? '<th>任務</th>' : ''}<th></th></tr></thead><tbody>
    ${list.map((a) => `<tr><td>${attLink(a)}</td><td class="small">${fmtSize(a.size)}</td><td>${esc(uname(a.uploaded_by))}</td><td class="small">${esc(a.uploaded_at)}</td><td class="small">${attOwner(a)}</td>${src ? `<td>${srcLink(a.node_id)}</td>` : ''}
      <td>${!src && canDeleteAttachment(a) ? `<button class="iconbtn" type="button" data-att-del="${a.id}" aria-label="刪除">✕</button>` : ''}</td></tr>`).join('')}</tbody></table></div>`;
}
function viewRecords(n) {
  const leaf = n.type === 'task' && isLeaf(n);
  const scope = leaf ? [n] : [n, ...descendants(n.id)].filter(visible);
  const ids = new Set(scope.map((x) => x.id));
  const src = !leaf;
  const reps = db.reports.filter((r) => ids.has(r.node_id)).sort((a, b) => b.submitted_at.localeCompare(a.submitted_at) || b.version - a.version);
  const notes = db.notes.filter((x) => ids.has(x.node_id)).reverse();
  const atts = db.attachments.filter((a) => ids.has(a.node_id) && !a.deleted_at).reverse();
  const pend = leaf ? pendingReport(n.id) : null;
  const noStore = fileStore.ok === false ? '<div class="note warn" style="margin:8px 0">此瀏覽器無法儲存檔案（IndexedDB 無法使用），回報與筆記仍可正常使用。</div>' : '';
  const upload = fileStore.ok !== false;
  return `<div class="records">
    ${src ? `<div class="note">這是上層節點，以下彙總整棵子樹（${scope.length - 1} 個子任務）的紀錄，只能檢視；要新增請進入個別任務。</div>` : ''}
    <section class="panel"><div class="row" style="justify-content:space-between"><h3>完成回報（${reps.length}）</h3>${leaf && canReport(n) ? `<button class="btn sm primary" type="button" data-report="${n.id}">回報完成</button>` : ''}</div>
      ${leaf && n.status === 'skipped' ? '<div class="note" style="margin-top:8px">此任務已跳過，不需要完成回報。</div>' : ''}
      ${pend ? `<div class="note" style="margin-top:8px">v${pend.version} 等待確認：${esc(approversFor(n).map(uname).join('、'))}${can('override', n) ? `<div class="row" style="margin-top:8px"><button class="btn sm primary" type="button" data-rep-approve="${pend.id}">確認完成</button><button class="btn sm danger" type="button" data-rep-reject="${pend.id}">退回</button></div>` : ''}</div>` : ''}
      ${reps.map((r) => reportHTML(r, src)).join('') || '<div class="empty">還沒有完成回報。</div>'}</section>
    <section class="panel"><h3>筆記（${notes.length}）</h3>
      ${leaf && canNote(n) ? `<form id="noteForm" data-node="${n.id}" style="margin-top:10px"><div class="field"><label for="nBody">新增筆記</label><textarea id="nBody" style="min-height:70px" placeholder="進度、討論、觀察…"></textarea></div>
        <div class="row" style="justify-content:space-between">${upload ? '<input id="nFiles" type="file" multiple aria-label="筆記附件">' : '<span></span>'}<button class="btn sm primary" type="submit">新增筆記</button></div></form>` : ''}
      ${notes.map((x) => noteHTML(x, src)).join('') || '<div class="empty">還沒有筆記。</div>'}</section>
    <section class="panel"><h3>附件（${atts.length}）</h3>${noStore}
      ${leaf && can('edit', n) && upload ? `<form id="attForm" data-node="${n.id}" class="row" style="margin:10px 0"><input id="aFiles" type="file" multiple aria-label="選擇附件"><button class="btn sm" type="submit">上傳</button><span class="small muted">每個檔案 10 MB 以內</span></form>` : ''}
      ${atts.length ? attRows(atts, src) : '<div class="empty">還沒有附件。</div>'}</section>
  </div>`;
}
function openReportDialog(nodeId) {
  const n = node(nodeId);
  if (!canReport(n)) return toast(pendingReport(nodeId) ? '已有待確認的完成回報' : '你無法對此任務送出完成回報', 'warn');
  const defs = fieldDefs(nodeId);
  const last = reportsOf(nodeId)[0];
  const redo = last && last.status === 'rejected';
  const input = (f) => {
    const id = 'rv_' + f.key;
    const old = redo ? (last.fields.find((x) => x.key === f.key) || {}).value : null;
    if (f.type === 'select') return `<select id="${id}"><option value="">—</option>${f.options.map((o) => `<option ${old === o ? 'selected' : ''}>${esc(o)}</option>`).join('')}</select>`;
    return `<input id="${id}" type="${f.type === 'number' ? 'number' : f.type === 'date' ? 'date' : 'text'}" ${f.type === 'number' ? 'step="any"' : ''} value="${old === null || old === undefined ? '' : esc(old)}">`;
  };
  openDlg(`<form id="reportForm" data-node="${nodeId}"><h2 class="serif">回報完成：${esc(n.title)}</h2>
    ${redo ? `<div class="note warn" style="margin-bottom:12px">上一版 v${last.version} 被 ${esc(uname(last.reviewed_by))} 退回：${esc(last.review_comment)}</div>` : ''}
    <div class="field"><span class="lb">結果</span><div class="chips">${Object.entries(RESULT).map(([k, l]) => `<label><input type="radio" name="rResult" value="${k}" ${(redo ? last.result : 'met') === k ? 'checked' : ''}>${l}</label>`).join('')}</div></div>
    <div class="field"><label for="rSummary">成果說明（必填）</label><textarea id="rSummary" placeholder="做了什麼、結果如何、有沒有需要後續處理的事">${redo ? esc(last.summary) : ''}</textarea></div>
    <div class="frow"><div class="field"><label for="rDate">實際完成日</label><input id="rDate" type="date" value="${TODAY}"></div><div></div></div>
    ${defs.length ? `<div class="frow">${defs.map((f) => `<div class="field"><label for="rv_${f.key}">${esc(f.label)}${f.unit ? `（${esc(f.unit)}）` : ''}${f.required ? '（必填）' : ''}</label>${input(f)}</div>`).join('')}</div>` : ''}
    <div class="field"><label for="rFiles">附件（每個檔案 10 MB 以內）</label><input id="rFiles" type="file" multiple ${fileStore.ok === false ? 'disabled' : ''}></div>
    <div class="note">送出後任務會移到「審核中」，回報內容會鎖定；由 ${esc(approversFor(n).map(uname).join('、'))} 確認完成。</div>
    <div class="dlg-actions"><button class="btn" type="button" data-close-dlg>取消</button>
      ${can('override', n) ? '<button class="btn" type="submit" value="self">送出並直接確認</button>' : ''}<button class="btn primary" type="submit" value="submit">送出回報</button></div></form>`);
}
function openRejectReport(reportId) {
  const r = db.reports.find((x) => x.id === reportId); if (!r) return;
  openDlg(`<form id="rejectForm" data-report="${reportId}"><h2 class="serif">退回完成回報</h2>
    <p class="small muted" style="margin-top:-8px">「${esc(node(r.node_id).title)}」v${r.version}，由 ${esc(uname(r.submitted_by))} 送出</p>
    <div class="field"><label for="rjComment">退回意見（必填）</label><textarea id="rjComment" style="min-height:80px" placeholder="例如：請補上殺菌釜溫度紀錄截圖"></textarea></div>
    <div class="dlg-actions"><button class="btn" type="button" data-close-dlg>取消</button><button class="btn warn" type="submit">退回</button></div></form>`);
}
function openNoteEdit(noteId) {
  const x = db.notes.find((y) => y.id === noteId); if (!x) return;
  openDlg(`<form id="noteEditForm" data-note="${noteId}"><h2 class="serif">修改筆記</h2>
    <div class="field"><label for="neBody">內容</label><textarea id="neBody" style="min-height:100px">${esc(x.body)}</textarea></div>
    <p class="small muted">修改後會標示「已編輯」，原內容保留在稽核紀錄。</p>
    <div class="dlg-actions"><button class="btn" type="button" data-close-dlg>取消</button><button class="btn primary" type="submit">儲存</button></div></form>`);
}
```

- [ ] **Step 5: 加上「紀錄」分頁**

`pageNode()` 裡把：

```js
  const tabs = [['board', '看板'], ['timeline', '時程'], ['graph', '相依圖'], ['docs', '文件'], ['data', '資料'], ['people', '成員與權限']];
```

改成：

```js
  const tabs = [['board', '看板'], ['timeline', '時程'], ['graph', '相依圖'], ['docs', '文件'], ['data', '資料'], ['people', '成員與權限'], ['records', '紀錄']];
```

把：

```js
    people: '',
  };
```

改成：

```js
    people: '',
    records: '',
  };
```

把：

```js
  const views = { board: viewBoard, timeline: viewTimeline, graph: viewGraph, docs: viewDocs, data: viewData, people: viewPeople };
```

改成：

```js
  const views = { board: viewBoard, timeline: viewTimeline, graph: viewGraph, docs: viewDocs, data: viewData, people: viewPeople, records: viewRecords };
```

- [ ] **Step 6: 看板卡片**

`cardHTML()` 裡把：

```js
      ${soft.length ? `<span class="tag ai" title="${esc(soft.map((b) => b.text).join('\n'))}">⚠ 軟性前置</span>` : ''}</div>
```

改成：

```js
      ${soft.length ? `<span class="tag ai" title="${esc(soft.map((b) => b.text).join('\n'))}">⚠ 軟性前置</span>` : ''}
      ${pendingReport(c.id) ? '<span class="tag blue">待確認回報</span>' : ''}</div>
```

把：

```js
      <span>${c.milestone ? md(S(s)) : `${md(S(s))}–${md(S(e))}`}<button class="iconbtn" type="button" data-edit="${c.id}" aria-label="編輯">✎</button></span></div>
```

改成：

```js
      <span>${c.milestone ? md(S(s)) : `${md(S(s))}–${md(S(e))}`}${canReport(c) && (c.status === 'todo' || c.status === 'doing') ? `<button class="iconbtn" type="button" data-report="${c.id}" title="回報完成">✓ 回報</button>` : ''}<button class="iconbtn" type="button" data-edit="${c.id}" aria-label="編輯">✎</button></span></div>
```

- [ ] **Step 7: 審核中心**

`pageReview()` 裡把：

```js
  const fReq = db.ops.formulas.flatMap((f) => f.versions.filter((v) => v.request === 'pending').map((v) => ({ f, v })));
  return `<div class="pagehead"><div><h1 class="serif">審核中心</h1><p>跳過申請、階段閘門、配方定案簽核。所有決定寫入不可刪除的稽核紀錄。</p></div></div>
```

改成：

```js
  const fReq = db.ops.formulas.flatMap((f) => f.versions.filter((v) => v.request === 'pending').map((v) => ({ f, v })));
  const reps = db.reports.filter((r) => r.status === 'submitted' && node(r.node_id) && visible(node(r.node_id)));
  return `<div class="pagehead"><div><h1 class="serif">審核中心</h1><p>完成回報、跳過申請、階段閘門、配方定案簽核。所有決定寫入不可刪除的稽核紀錄。</p></div></div>
  <div class="stack" style="margin-bottom:14px"><h2>待確認的完成回報（${reps.length}）</h2>
  ${reps.length ? reps.map((r) => { const n = node(r.node_id); const okp = can('override', n); return `<div class="panel">${reportHTML(r, true)}
    <div class="row" style="margin-top:8px"><button class="btn sm primary" type="button" data-rep-approve="${r.id}" ${okp ? '' : 'disabled'}>確認完成</button><button class="btn sm danger" type="button" data-rep-reject="${r.id}" ${okp ? '' : 'disabled'}>退回</button>
    ${okp ? '' : `<span class="small muted">可確認的人：${esc(approversFor(n).map(uname).join('、'))}</span>`}</div></div>`; }).join('') : '<div class="empty">沒有待確認的完成回報。試試用「阿明（成員）」到任務的「紀錄」分頁按「回報完成」。</div>'}</div>
```

- [ ] **Step 8: click 事件**

在 click 委派裡找到：

```js
  if (ds.gate) return openGate(ds.gate);
```

在它下面加入：

```js
  if (ds.report) { closeDrawer(); return openReportDialog(ds.report); }
  if (ds.repApprove) { decideReport(ds.repApprove, true); return toast('已確認完成'); }
  if (ds.repReject) return openRejectReport(ds.repReject);
  if (ds.noteEdit) return openNoteEdit(ds.noteEdit);
  if (ds.attOpen) return openAttachment(ds.attOpen);
  if (ds.attDel) { const r = deleteAttachment(ds.attDel); return r.ok ? toast('已刪除附件', null, { label: '復原', fn: undo }) : toast(r.error, 'warn'); }
```

- [ ] **Step 9: submit 事件**

在 submit 委派裡找到：

```js
  if (f.id === 'blockForm') {
```

在它上面加入：

```js
  if (f.id === 'reportForm') {
    const nid = f.dataset.node; const n = node(nid);
    const data = {
      result: (document.querySelector('input[name="rResult"]:checked') || {}).value,
      summary: $('rSummary').value, finished_on: $('rDate').value,
      values: Object.fromEntries(fieldDefs(nid).map((d) => [d.key, $('rv_' + d.key).value])),
      files: [...($('rFiles').files || [])],
    };
    const self = !!e.submitter && e.submitter.value === 'self';
    submitReport(nid, data, { selfApprove: self }).then((r) => {
      if (r.ok) { closeDlg(); return toast(self ? '已送出並確認完成' : '已送出完成回報，等待確認'); }
      if (r.blocked) { closeDlg(); return openBlockDialog(n, 'doing', findBlockers(n, 'doing')); }
      toast(r.errors.join('；'), 'warn');
    });
    return;
  }
  if (f.id === 'rejectForm') { if (decideReport(f.dataset.report, false, $('rjComment').value)) { closeDlg(); toast('已退回完成回報'); } return; }
  if (f.id === 'noteForm') {
    const files = [...($('nFiles') && $('nFiles').files || [])];
    if (files.some((x) => x.size > MAX_FILE)) return toast('有檔案超過 10 MB，請移除後再送出', 'warn');
    const r = addNote(f.dataset.node, $('nBody').value);
    if (!r.ok) return toast(r.error, 'warn');
    if (files.length) addAttachments(f.dataset.node, files, { noteId: r.note.id }).then((x) => { if (x.errors.length) toast(x.errors.join('；'), 'warn'); });
    return toast('已新增筆記');
  }
  if (f.id === 'noteEditForm') { const r = editNote(f.dataset.note, $('neBody').value); if (!r.ok) return toast(r.error, 'warn'); closeDlg(); return toast('已修改筆記'); }
  if (f.id === 'attForm') {
    const files = [...($('aFiles').files || [])];
    if (!files.length) return toast('請先選擇檔案', 'warn');
    addAttachments(f.dataset.node, files).then((x) => toast(x.errors.length ? x.errors.join('；') : `已上傳 ${x.added.length} 個附件`, x.errors.length ? 'warn' : undefined));
    return;
  }
```

- [ ] **Step 10: Run tests — 確認全部通過**

Expected: `全部通過 22/22`。

- [ ] **Step 11: 手動確認畫面**

在 Browser pane 開 `http://localhost:8000/projectflow-full-demo.html`（先按「重置 Demo 資料」），切換成阿明：
1. 進入「設備參數設定」→「紀錄」→「回報完成」→ 填寫並附一個檔案 → 送出，任務變「審核中」。
2. 新增一則附檔案的筆記、修改它，看到「已編輯」；上傳一個附件後刪除。
3. 切換成力瑜 → 審核中心 → 退回（填意見）→ 切回阿明重送，看到 v2 與退回意見 → 力瑜確認。
4. 點附件名稱能開啟或下載。
5. 用手機寬度（`resize_window` preset mobile）看「紀錄」分頁不會橫向捲動；結束後改回 desktop。

---

### Task 6: 主管跳過整個任務（直接跳過、申請、核准、恢復）

**Files:**
- Modify: `projectflow-full-demo.html`（F11 核心區、`submitBlock()`、`submitGate()`、`decideOverride()`、`openEditor()`、`cardHTML()`、`pageNode()`、`pageReview()`、UI 函式、click / submit 事件）
- Test: `tests/records.test.js`

**Interfaces:**
- Consumes: `db.overrides`、`decideOverride()`、`announceUnlocks()`
- Produces:
  - `skipTargets(n): Node[]`（本身與所有未完成的子孫）
  - `pendingSkip(id): Override|null`
  - `skipTask(id, reason): { ok, error?, mode?: 'skipped'|'requested' }`
  - `applySkip(o)`：把 `o.prev` 記成 `{ nodeId: 原狀態 }` 並設為 `skipped`（只在 `commit` 內呼叫）
  - `restoreTask(id): { ok, error? }`
  - `skipInfo(n): string`
  - `openSkipDialog(id)`；DOM：`data-skip`、`data-restore`、表單 `#skipForm`
  - 覆寫紀錄新增 `kind: 'dep' | 'gate' | 'task'`；task 類型另有 `prev`、`restoredBy`、`restoredAt`

- [ ] **Step 1: 寫測試**

```js
  // ── Task 6：跳過任務 ──
  await T('成員申請跳過 → 範圍內審核人核准 → 已跳過、進度 100%', () => {
    as('ming');
    eq(skipTask('t30122', '').error, '請填寫理由');
    const r = skipTask('t30122', '品保已在現場確認');
    eq(r.mode, 'requested'); eq(node('t30122').status, 'todo');
    const o = pendingSkip('t30122'); eq(o.kind, 'task');
    eq(skipTask('t30122', '再申請一次').error, '已有待審核的跳過申請');
    as('chen'); decideOverride(o.id, true);
    eq(node('t30122').status, 'skipped'); eq(prog(node('t30122')), 100); eq(o.prev, { t30122: 'todo' });
  });
  await T('主管直接跳過上層任務：未完成子任務一起跳過；恢復後回到原狀態', () => {
    const r = skipTask('t3012', '改用新的殺菌釜，不需調整');
    eq(r.mode, 'skipped');
    eq(['t3012', 't30121', 't30122'].map((id) => node(id).status), ['skipped', 'skipped', 'skipped']);
    ok(!canReport(node('t30121')), '已跳過不能送回報');
    ok(restoreTask('t3012').ok);
    eq(['t3012', 't30121', 't30122'].map((id) => node(id).status), ['doing', 'doing', 'todo']);
  });
  await T('跳過時自動結案待確認的回報', async () => {
    as('ming'); await submitReport('t30121', { result: 'met', summary: '完成', finished_on: '2026-09-30', values: {} });
    as('yu'); skipTask('t30121', '不需要了');
    const rep = db.reports.find((x) => x.node_id === 't30121');
    eq(rep.status, 'rejected'); eq(rep.review_comment, '任務已跳過，回報自動結案');
  });
  await T('只恢復被連帶跳過的子任務時，只動它自己', () => {
    skipTask('t3012', '整段不做');
    ok(restoreTask('t30122').ok);
    eq(['t3012', 't30121', 't30122'].map((id) => node(id).status), ['doing', 'skipped', 'todo']);
  });
  await T('成員不能恢復；編輯器狀態選單不提供「已跳過」', () => {
    skipTask('t30122', '不做');
    as('ming'); eq(restoreTask('t30122').ok, false);
    as('yu'); openEditor('t30121');
    ok(![...document.querySelectorAll('#eStatus option')].some((o) => o.value === 'skipped'), '未跳過的任務不能從選單選「已跳過」');
    ok(document.querySelector('#edForm [data-skip="t30121"]'), '編輯器應有跳過按鈕');
    closeDrawer();
  });
  await T('既有覆寫紀錄帶有 kind', () => {
    as('ming'); submitBlock('t3013', 'doing', '先開始');
    eq(db.overrides[0].kind, 'dep');
  });
```

- [ ] **Step 2: Run tests — 確認新測試失敗**

Expected: 6 項失敗（`skipTask is not defined`）。

- [ ] **Step 3: 實作跳過核心函式**

在 Task 4 的 `openAttachment()` 下面加入：

```js
/* ---------- 跳過整個任務 ---------- */
function skipTargets(n) { return [n, ...descendants(n.id)].filter((x) => !DONE(x.status)); }
function pendingSkip(id) { return db.overrides.find((o) => o.kind === 'task' && o.node === id && o.status === 'pending') || null; }
function skipRecordOf(id) { return db.overrides.find((x) => x.kind === 'task' && x.status === 'approved' && !x.restoredAt && x.prev && id in x.prev) || null; }
function skipInfo(n) { const o = skipRecordOf(n.id); return o ? `理由：${o.reason}\n核准：${uname(o.decidedBy)} ${o.decidedAt}` : '已跳過'; }
// 只在 commit 內呼叫
function applySkip(o) {
  const n = node(o.node); o.prev = {};
  skipTargets(n).forEach((x) => { o.prev[x.id] = x.status; x.status = 'skipped'; });
  db.reports.forEach((r) => { if (r.node_id in o.prev && r.status === 'submitted') Object.assign(r, { status: 'rejected', reviewed_by: o.decidedBy || ui.me, reviewed_at: nowStr(), review_comment: '任務已跳過，回報自動結案' }); });
  for (let p = n.parent ? node(n.parent) : null; p && p.type !== 'project'; p = p.parent ? node(p.parent) : null) {
    if (kids(p.id).every((c) => DONE(c.status)) && !DONE(p.status)) { p.status = 'review'; notify(`「${p.title}」的子任務全部完成或跳過，已移到「審核中」，請確認後標為完成。`); }
  }
}
function skipTask(id, reason) {
  const n = node(id); const why = String(reason || '').trim();
  if (!n || n.type !== 'task' || DONE(n.status)) return { ok: false, error: '這個任務不能跳過' };
  if (!why) return { ok: false, error: '請填寫理由' };
  if (pendingSkip(id)) return { ok: false, error: '已有待審核的跳過申請' };
  const tg = skipTargets(n);
  const rec = { id: newId('o'), kind: 'task', node: id, to: 'skipped', blockers: [`跳過整個任務${tg.length > 1 ? `（含 ${tg.length - 1} 項未完成子任務）` : ''}`], depIds: [], reason: why, by: ui.me, at: nowStr() };
  if (can('override', n)) {
    commit(`跳過「${n.title}」`, () => { db.overrides.unshift({ ...rec, status: 'approved', decidedBy: ui.me, decidedAt: nowStr(), self: true }); applySkip(db.overrides[0]); });
    log(id, '跳過', `跳過「${n.title}」${tg.length > 1 ? `與 ${tg.length - 1} 項子任務` : ''}，理由：${why}`);
    announceUnlocks(n);
    return { ok: true, mode: 'skipped' };
  }
  if (!can('edit', n)) return { ok: false, error: '你的角色無權跳過此任務' };
  commit(`申請跳過「${n.title}」`, () => { db.overrides.unshift({ ...rec, status: 'pending' }); });
  log(id, '跳過申請', `申請跳過「${n.title}」，理由：${why}`);
  notify(`已送出跳過申請：「${n.title}」（整個任務）\n已通知：${approversFor(n).map(uname).join('、')}`, '跳過申請');
  return { ok: true, mode: 'requested' };
}
function restoreTask(id) {
  const n = node(id);
  if (!n || n.status !== 'skipped') return { ok: false, error: '這個任務沒有被跳過' };
  if (!can('override', n)) return { ok: false, error: '只有有覆寫權限的人可以恢復任務' };
  const o = skipRecordOf(id);
  // 恢復的是當初被跳過的那個任務：整批還原；只恢復連帶跳過的子任務：只動它自己
  const prev = !o ? { [id]: 'todo' } : o.node === id ? o.prev : { [id]: o.prev[id] };
  commit(`恢復「${n.title}」`, () => {
    Object.entries(prev).forEach(([k, st]) => { const x = node(k); if (x && x.status === 'skipped') x.status = st; });
    if (o && o.node === id) { o.restoredBy = ui.me; o.restoredAt = nowStr(); }
    for (let p = n.parent ? node(n.parent) : null; p && p.type !== 'project'; p = p.parent ? node(p.parent) : null) {
      if ((DONE(p.status) || p.status === 'review') && kids(p.id).some((c) => !DONE(c.status))) p.status = 'doing';
    }
  });
  log(id, '恢復', `恢復「${n.title}」，回到跳過前的狀態`);
  return { ok: true };
}
```

- [ ] **Step 4: 既有覆寫紀錄補 kind，decideOverride 支援 task**

`submitBlock()` 裡把：

```js
  const rec = { id: newId('o'), node: id, to, blockers: bl.map((b) => b.text), depIds: bl.filter((b) => b.dep).map((b) => b.dep.id), reason, by: ui.me, at: nowStr() };
```

改成：

```js
  const rec = { id: newId('o'), kind: 'dep', node: id, to, blockers: bl.map((b) => b.text), depIds: bl.filter((b) => b.dep).map((b) => b.dep.id), reason, by: ui.me, at: nowStr() };
```

`submitGate()` 裡有兩處 `{ id: newId('o'), node: phId, gate: true,`，都改成 `{ id: newId('o'), kind: 'gate', node: phId, gate: true,`（其餘不變）。

`decideOverride()` 整個函式改成：

```js
function decideOverride(oid, ok) {
  const o = db.overrides.find((x) => x.id === oid); if (!o) return;
  const n = node(o.node);
  const isTask = o.kind === 'task';
  commit(`${ok ? '核准' : '退回'}跳過申請`, () => {
    o.status = ok ? 'approved' : 'rejected'; o.decidedBy = ui.me; o.decidedAt = nowStr();
    if (ok && o.gate) { db.gates[o.node].status = 'overridden'; db.gates[o.node].by = ui.me; db.gates[o.node].at = nowStr(); }
    if (ok && isTask && n) applySkip(o);
    if (ok && !o.gate && !isTask) db.deps.forEach((d) => { if (o.depIds.includes(d.id)) d.overridden = true; });
  });
  log(o.node, '審核', `${ok ? '核准' : '退回'} ${uname(o.by)} 的${o.gate ? '閘門' : isTask ? '跳過任務' : '跳過'}申請：「${n?.title}」`);
  notify(`${uname(ui.me)} ${ok ? '核准' : '退回'}了 ${uname(o.by)} 的申請：「${n?.title}」${ok && !o.gate ? `，已移到「${STLBL[o.to]}」` : ''}`, '審核結果');
  if (ok && isTask && n) announceUnlocks(n);
  if (ok && !o.gate && !isTask && n) setStatus(n.id, o.to, { force: true, system: '跳過申請核准', reason: o.reason, actor: ui.me });
}
```

- [ ] **Step 5: 跳過對話框**

在 Task 5 的 `openNoteEdit()` 下面加入：

```js
function openSkipDialog(id) {
  const n = node(id);
  if (!n || n.type !== 'task' || DONE(n.status)) return toast('這個任務不能跳過', 'warn');
  const canOv = can('override', n);
  if (!canOv && !can('edit', n)) return toast('你的角色無權跳過此任務', 'warn');
  if (pendingSkip(id)) return toast('已有待審核的跳過申請', 'warn');
  const tg = skipTargets(n);
  const fam = new Set(tg.map((x) => x.id));
  const unlock = [...new Set(db.deps.filter((d) => fam.has(d.from) && !fam.has(d.to) && node(d.to) && !DONE(node(d.to).status)).map((d) => node(d.to).title))];
  openDlg(`<form id="skipForm" data-id="${id}"><h2 class="serif">⤳ 跳過任務：${esc(n.title)}</h2>
    <p style="margin-top:-6px">以下 ${tg.length} 項會標為「已跳過」，進度算 100%：</p>
    <div class="listpick">${tg.map((x) => `<label><span class="dot ${x.status}"></span>${esc(x.title)}<span class="muted" style="margin-left:auto">${STLBL[x.status]}</span></label>`).join('')}</div>
    ${unlock.length ? `<div class="small muted" style="margin-top:8px">可能解鎖的後續任務：${esc(unlock.join('、'))}</div>` : ''}
    <div class="note" style="margin-top:12px">${canOv ? '你有覆寫權限，會直接跳過並寫入稽核紀錄；之後可在任務頁按「恢復任務」。' : `你的角色（${ROLES[me().role]}）無法自行跳過，會送出跳過申請給：${esc(approversFor(n).map(uname).join('、'))}。`}</div>
    <div class="field" style="margin-top:12px"><label for="sReason">理由（必填）</label><textarea id="sReason" style="min-height:80px" placeholder="例如：客戶取消此規格，這項測試不需要做了"></textarea></div>
    <div class="dlg-actions"><button class="btn" type="button" data-close-dlg>取消</button><button class="btn ${canOv ? 'warn' : 'primary'}" type="submit">${canOv ? '跳過任務' : '送出跳過申請'}</button></div></form>`);
}
```

- [ ] **Step 6: 編輯器**

`openEditor()` 裡把狀態選單：

```js
      <div class="field"><label for="eStatus">狀態</label><select id="eStatus" ${ed ? '' : 'disabled'}>${Object.entries(STLBL).map(([k, l]) => `<option value="${k}" ${k === n.status ? 'selected' : ''}>${l}</option>`).join('')}</select></div></div>
```

改成（「已跳過」只能透過跳過流程設定，已跳過的任務要用「恢復任務」）：

```js
      <div class="field"><label for="eStatus">狀態</label><select id="eStatus" ${ed && n.status !== 'skipped' ? '' : 'disabled'}>${Object.entries(STLBL).filter(([k]) => k !== 'skipped' || n.status === 'skipped').map(([k, l]) => `<option value="${k}" ${k === n.status ? 'selected' : ''}>${l}</option>`).join('')}</select></div></div>
```

把：

```js
    <div class="dlg-actions"><div class="left"><button class="btn sm danger" type="button" data-del="${n.id}" ${can('delete', n) && n.type !== 'phase' ? '' : 'disabled'}>刪除</button><button class="btn sm" type="button" data-enter="${n.id}">進入此節點</button></div>
```

改成：

```js
    <div class="dlg-actions"><div class="left"><button class="btn sm danger" type="button" data-del="${n.id}" ${can('delete', n) && n.type !== 'phase' ? '' : 'disabled'}>刪除</button><button class="btn sm" type="button" data-enter="${n.id}">進入此節點</button>
      ${n.type === 'task' && !DONE(n.status) ? `<button class="btn sm" type="button" data-skip="${n.id}" ${can('override', n) || can('edit', n) ? '' : 'disabled'}>⤳ 跳過任務</button>` : ''}
      ${n.status === 'skipped' && can('override', n) ? `<button class="btn sm" type="button" data-restore="${n.id}">恢復任務</button>` : ''}</div>
```

- [ ] **Step 7: 看板卡片與任務頁標頭**

`cardHTML()` 裡把 Task 5 加的：

```js
      ${pendingReport(c.id) ? '<span class="tag blue">待確認回報</span>' : ''}</div>
```

改成：

```js
      ${pendingReport(c.id) ? '<span class="tag blue">待確認回報</span>' : ''}
      ${c.status === 'skipped' ? `<span class="tag gray" title="${esc(skipInfo(c))}">⤳ 已跳過</span>` : ''}
      ${pendingSkip(c.id) ? '<span class="tag ai">跳過申請中</span>' : ''}</div>
```

同一個函式裡，在 `✓ 回報` 按鈕後面、✎ 按鈕前面加入跳過按鈕，也就是把：

```js
<button class="iconbtn" type="button" data-edit="${c.id}" aria-label="編輯">✎</button></span></div>
```

改成：

```js
${c.type === 'task' && !DONE(c.status) && !pendingSkip(c.id) && (can('override', c) || can('edit', c)) ? `<button class="iconbtn" type="button" data-skip="${c.id}" title="跳過任務" aria-label="跳過任務">⤳</button>` : ''}<button class="iconbtn" type="button" data-edit="${c.id}" aria-label="編輯">✎</button></span></div>
```

`pageNode()` 裡把：

```js
      ${n.note ? `<div class="note" style="margin-top:8px">${esc(n.note)}</div>` : ''}
```

改成：

```js
      ${n.note ? `<div class="note" style="margin-top:8px">${esc(n.note)}</div>` : ''}
      ${n.status === 'skipped' ? `<div class="note" style="margin-top:8px">⤳ 已跳過・${esc(skipInfo(n)).replace(/\n/g, '　')}</div>` : ''}
```

把：

```js
      ${n.type !== 'project' ? `<button class="btn" type="button" data-edit="${n.id}">編輯</button>` : ''}
```

改成：

```js
      ${n.status === 'skipped' && can('override', n) ? `<button class="btn" type="button" data-restore="${n.id}">恢復任務</button>` : ''}
      ${n.type !== 'project' ? `<button class="btn" type="button" data-edit="${n.id}">編輯</button>` : ''}
```

- [ ] **Step 8: 審核中心標示**

`pageReview()` 待審清單裡把：

```js
    return `<div class="panel"><div class="row" style="justify-content:space-between"><div><b>${esc(n?.title || '（已刪除）')}</b> → ${STLBL[o.to] || o.to}　<span class="small muted">${esc(uname(o.by))} 於 ${esc(o.at)} 申請</span></div>
```

改成：

```js
    return `<div class="panel"><div class="row" style="justify-content:space-between"><div><b>${esc(n?.title || '（已刪除）')}</b> → ${STLBL[o.to] || o.to}${o.kind === 'task' ? ' <span class="tag ai">整個任務</span>' : ''}　<span class="small muted">${esc(uname(o.by))} 於 ${esc(o.at)} 申請</span></div>
```

把空白提示：

```js
  }).join('') : '<div class="empty">沒有待審核的跳過申請。試試用「阿明（成員）」身分把被 🔒 擋住的任務拖到「進行中」。</div>'}
```

改成：

```js
  }).join('') : '<div class="empty">沒有待審核的跳過申請。示範：用「阿明（成員）」在自己的任務卡片按 ⤳ 送出跳過申請，再切換成「力瑜」到這裡核准；或把被 🔒 擋住的任務拖到「進行中」。</div>'}
```

審核紀錄表格裡把：

```js
${esc(node(o.node)?.title || o.target || '')}${o.gate ? '（閘門）' : ''}</td>
```

改成：

```js
${esc(node(o.node)?.title || o.target || '')}${o.gate ? '（閘門）' : o.kind === 'task' ? '（跳過任務）' : ''}${o.restoredAt ? ' <span class="tag gray">已恢復</span>' : ''}</td>
```

- [ ] **Step 9: 事件**

click 委派裡，在 Task 5 加的 `if (ds.report) ...` 上面加入：

```js
  if (ds.skip) { closeDrawer(); return openSkipDialog(ds.skip); }
  if (ds.restore) { closeDrawer(); const r = restoreTask(ds.restore); return r.ok ? toast('已恢復任務') : toast(r.error, 'warn'); }
```

submit 委派裡，在 Task 5 加的 `if (f.id === 'reportForm') {` 上面加入：

```js
  if (f.id === 'skipForm') { const r = skipTask(f.dataset.id, $('sReason').value); if (!r.ok) return toast(r.error, 'warn'); closeDlg(); return toast(r.mode === 'skipped' ? '已跳過任務' : '已送出跳過申請'); }
```

- [ ] **Step 10: 更新歡迎訊息**

啟動區的歡迎訊息裡把：

```js
· 用「阿明（成員）」把 🔒 任務拖到進行中 → 送出跳過申請\n
```

改成：

```js
· 用「阿明（成員）」把 🔒 任務拖到進行中 → 送出跳過申請\n· 任務頁「紀錄」分頁：回報完成、寫筆記、上傳附件；卡片上的 ⤳ 可以跳過整個任務\n
```

- [ ] **Step 11: Run tests — 確認全部通過**

Expected: `全部通過 28/28`。

- [ ] **Step 12: 手動確認**

重置資料後：阿明在「品保確認」卡片按 ⤳ → 送出申請，卡片出現「跳過申請中」；切換成陳主管到審核中心核准，卡片變「⤳ 已跳過」，滑過顯示理由。力瑜在「調整殺菌時間」卡片按 ⤳ 直接跳過，進入該任務按「恢復任務」，子任務回到原狀態。

---

### Task 7: AI 副手可引用回報與筆記、README 更新、整體驗證

**Files:**
- Modify: `projectflow-full-demo.html`（AI 區塊 `aiAsk()`）
- Modify: `README.md`
- Test: `tests/records.test.js`

**Interfaces:**
- Consumes: `db.reports`、`db.notes`、`RESULT`
- Produces: `recordsSnapshot(p): string`、`recordHits(p, q): string[]`

- [ ] **Step 1: 寫測試**

```js
  // ── Task 7：AI 可查詢回報與筆記 ──
  await T('recordHits 找得到 F0 回報；機密節點不會被引用', () => {
    const hits = recordHits(node('p1'), 'F0 測試結果');
    ok(hits.length && hits[0].includes('2.6'), JSON.stringify(hits));
    db.notes.push({ id: 'ntc', node_id: 't1022', body: '機密配方比例 62%', author: 'yu', created_at: nowStr(), edited_at: null });
    ok(!recordsSnapshot(node('p1')).includes('機密配方比例'), '機密節點（t1022）的筆記不能出現');
  });
  await T('專案問答：問回報會回答並寫入 AI 稽核', () => {
    ui.page = 'node'; ui.node = 'p1';
    const n0 = audit.ai.length;
    aiAsk('第 1 次 F0 測試的回報結果是多少');
    eq(audit.ai.length, n0 + 1);
    ok(ui.chat.at(-1).text.includes('2.6'), ui.chat.at(-1).text);
  });
```

- [ ] **Step 2: Run tests — 確認新測試失敗**

Expected: 2 項失敗（`recordHits is not defined`）。

- [ ] **Step 3: 實作**

在 AI 區塊找到：

```js
function aiRun(feature, level, prompt, answer) {
```

在它上面加入：

```js
// F11：回報與筆記給 AI 引用（排除機密節點；只含使用者看得到的節點）
function recordsSnapshot(p) {
  return descendants(p.id).filter((x) => visible(x) && effLevel(x) !== 'confidential').flatMap((x) => [
    ...db.reports.filter((r) => r.node_id === x.id && r.status !== 'rejected').map((r) => `[回報 ${x.title} v${r.version}｜${RESULT[r.result]}｜${r.status === 'approved' ? '已確認' : '待確認'}] ${r.summary}${r.fields.map((f) => `；${f.label}=${f.value ?? '—'}${f.unit}`).join('')}`),
    ...db.notes.filter((nt) => nt.node_id === x.id).map((nt) => `[筆記 ${x.title}｜${uname(nt.author)} ${nt.created_at}] ${nt.body}`),
  ]).join('\n');
}
function recordHits(p, q) {
  const grams = []; for (let i = 0; i < q.length - 1; i++) grams.push(q.slice(i, i + 2));
  return recordsSnapshot(p).split('\n').filter(Boolean)
    .map((l) => ({ l, sc: grams.filter((g) => l.includes(g)).length }))
    .filter((x) => x.sc > 0).sort((a, b) => b.sc - a.sc).map((x) => x.l);
}
```

`aiAsk()` 裡把：

```js
  aiRun('專案問答', 'internal', `問題：${q}\n專案：${p.title}\n可引用內容：\n${publicSnapshot(p)}\n${db.docs.filter((d) => d.level !== 'confidential' && node(d.node) && projectOf(node(d.node)).id === p.id).map((d) => `[${d.title}] ${d.versions.at(-1).body}`).join('\n')}`, () => {
```

改成：

```js
  aiRun('專案問答', 'internal', `問題：${q}\n專案：${p.title}\n可引用內容：\n${publicSnapshot(p)}\n${db.docs.filter((d) => d.level !== 'confidential' && node(d.node) && projectOf(node(d.node)).id === p.id).map((d) => `[${d.title}] ${d.versions.at(-1).body}`).join('\n')}\n${recordsSnapshot(p)}`, () => {
    if (/回報|結果|筆記|紀錄|F0|數值/.test(q)) {
      const hits = recordHits(p, q);
      if (hits.length) return { text: `${hits.slice(0, 3).map((h, i) => `[${i + 1}] ${h}`).join('\n')}\n\n來源：任務完成回報與筆記（只檢索你有權限、非機密的節點）` };
    }
```

- [ ] **Step 4: Run tests — 確認全部通過**

Expected: `全部通過 30/30`。

- [ ] **Step 5: 更新 README**

(a) 目錄：在 `   - [F10 研發營運資料（供應商、原料、配方、採購、工單）](#f10-研發營運資料供應商原料配方採購工單)` 下一行加入：

```markdown
   - [F11 任務紀錄與完成回報](#f11-任務紀錄與完成回報)
```

(b) 開頭檔案說明：把 `projectflow-full-demo.html` 那一行裡的 `研發營運資料與模擬 ERP）` 改成 `研發營運資料與模擬 ERP、任務完成回報／筆記／附件、主管跳過任務）`。

(c) F5 規則：在 `- 有權限者自己跳過也必須填理由` 下一行加入：

```markdown
- **跳過整個任務**：任務不用做時，有覆寫權限的人（專案負責人、範圍內的階段審核人）可直接標為「已跳過」，進度算 100%、後續任務解鎖；跳過上層任務時未完成的子任務一起跳過。成員只能送出跳過申請，由主管在審核中心核准。已跳過的任務可由主管「恢復任務」，回到跳過前的狀態
```

(d) 在 `## 5. 資料模型` 這一行的上面（F10 最後一段之後、`---` 之前的位置維持原樣），加入新的一節：

```markdown
### F11 任務紀錄與完成回報

**需求**：每個任務都有回報完成、寫筆記、上傳檔案的地方；表單資料結構化存進資料庫，之後讓 Agent 查詢。

| 項目 | 規格 |
|---|---|
| 位置 | 任務頁「紀錄」分頁；上層節點唯讀彙總整棵子樹；看板卡片有「✓ 回報」快捷按鈕 |
| 完成回報 | 固定欄位：結果（達成／部分達成／未達成）、成果說明、實際完成日、附件；自訂欄位：文字／數字（含單位）／日期／選項，可設必填，模板會帶著走 |
| 流程 | 送出 → 審核中（回報鎖定）→ 專案負責人或範圍內審核人「確認完成」或「退回」（意見必填）；重送為新版本，舊版保留；主管自己送出可「送出並直接確認」 |
| 筆記 | 時間軸、可附檔；只有作者能修改，舊內容留在稽核紀錄；不提供刪除 |
| 附件 | 可附在任務、回報或筆記；單檔 10 MB；軟刪除；回報的附件不能刪；存 SHA-256 |
| Agent 查詢 | 回報的自訂欄位存「標籤＋數值＋單位」快照；AI 專案問答會引用回報與筆記（排除機密節點） |

> **Demo 範圍**：中繼資料存在瀏覽器 localStorage，檔案存在 IndexedDB；正式版改為 PostgreSQL ＋ 主機／NAS 檔案儲存（階段 4）。

```

(e) 第 5 節資料模型：在 `documents, document_versions` 那一段（含下一行 `  id, node_id, title, storage_key, version, created_by, created_at`）下面空一行後加入：

```text
report_field_defs           # 完成回報的自訂欄位（F11）
  id, node_id | template_id, key, label, type, unit, options, required, order

task_reports                # 完成回報，每次送出一個版本
  id, node_id, version, result, summary, finished_on
  fields jsonb              # [{ key, label, value, unit }] 快照
  status                    # submitted | approved | rejected
  submitted_by, submitted_at, reviewed_by, reviewed_at, review_comment, self_approved

task_notes
  id, node_id, body, author, created_at, edited_at

attachments
  id, node_id, report_id?, note_id?, filename, mime, size, sha256
  storage_key, uploaded_by, uploaded_at, deleted_at
```

- [ ] **Step 6: 整體驗證（瀏覽器實測）**

先按「重置 Demo 資料」，依 spec 第 10 節逐項操作並確認：

1. 阿明送出回報（含附件與必填自訂欄位）→ 審核中。（自訂欄位：先用力瑜在「第 2 次 F0 測試」以外的任務加一個必填欄位，或用力瑜覆寫「第 2 次 F0 測試」的前置後由阿明回報。）
2. 力瑜退回（填意見）→ 進行中 → 阿明重送 → v2。
3. 力瑜確認 → 已完成、後續任務解鎖、通知出現。
4. 阿明申請跳過 → 陳主管核准 → 已跳過、進度 100%。
5. 力瑜直接跳過有子任務的上層任務 → 恢復。
6. 上層節點「紀錄」分頁正確彙總。
7. 超過 10 MB 被擋；重新整理後資料仍在；重置後全部清空。
8. 在 Console 執行下列程式模擬 v2 資料後重新整理，確認沒有錯誤且回報存在：
   ```js
   const o = JSON.parse(localStorage.getItem('projectflow-demo-v2')); o.v = 2; o.db.v = 2; delete o.db.reports; delete o.db.reportFields; delete o.db.notes; delete o.db.attachments; localStorage.setItem('projectflow-demo-v2', JSON.stringify(o));
   ```
9. 切換成小林（協作人員）：看不到未被指派節點的紀錄，也不能送出。
10. 在 AI 副手問「第 1 次 F0 測試的回報結果是多少」，回答引用 F0 = 2.6。

同時確認 Console 沒有錯誤，最後再跑一次測試頁：`全部通過 30/30`。
