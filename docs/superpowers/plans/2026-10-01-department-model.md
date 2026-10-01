# 部門模型 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在單檔 Demo 中把「部門」變成可設定的資料：任務有負責部門、負責人可未指派、只有相關的人看得到與能操作、時間軸預設收合成階段並可依負責部門篩選。

**Architecture:** 所有程式都在 `projectflow-full-demo.html`。部門存在 `db.departments`（localStorage，資料版本由 v3 升為 v4）。可見性集中在 `directSee` / `seeTask` / `seeNode`，既有的 `visible()` 改為呼叫 `seeNode`；操作權限集中在 `canWork`，既有 `can('edit')` 對任務改用它。測試沿用瀏覽器測試頁（iframe 載入 Demo，在 Demo 全域環境內呼叫函式並斷言），新增 `tests/departments.test.js`。

**Tech Stack:** 原生 HTML/CSS/JavaScript（無框架、無打包）、localStorage、Python `http.server`（只用來在本機提供測試頁）。

**Spec:** `docs/superpowers/specs/2026-10-01-department-model-design.md`

## Global Constraints

- 只修改 `projectflow-full-demo.html`、`tests/records.html`、`tests/records.test.js`、`README.md`；新增 `tests/departments.test.js`。不引入外部函式庫或 CDN。
- 介面文字一律繁體中文，語氣與既有 Demo 一致。
- localStorage key 維持 `projectflow-demo-v2`；`db.v` 由 3 升為 4，`load()` 必須能讀 v2、v3、v4 並依序升級。
- 部門 id 固定為：`d-rd` 研發、`d-pe` 製程、`d-qa` 品保、`d-sales` 業務、`d-pc` 生管、`d-pur` 採購、`d-adm` 管理、`d-it` 資訊、`d-fin` 財務、`d-mfg` 製造（依此順序）。預設主管：`d-rd`=yu、`d-qa`=chen、`d-pur`=hua，其餘 `null`。
- 舊部門名稱對應：研發→d-rd、製程→d-pe、品保→d-qa、法規→d-qa、採購→d-pur、生產→d-mfg、行銷→d-sales、資訊→d-it；不在表內的名稱→d-rd，並寫稽核「部門「X」已併入研發」。
- 所有會改變 `db` 的動作都包在既有的 `commit(label, fn)` 裡，並呼叫既有的 `log(nodeId, action, text)`。
- 輸出到 HTML 的使用者文字（含部門名稱）一律經過既有的 `esc()`。
- 時間軸展開與篩選狀態只存在 `ui`（`ui.expanded`、`ui.tlDept`），不寫入 `db`、不進復原紀錄。
- 這是 git repo（目前在 `main`）。執行前依 superpowers:using-git-worktrees 開分支／worktree；每個 Task 結束時 commit，commit 訊息結尾加：
  ```
  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
  ```

## 檔案結構

| 檔案 | 責任 |
|---|---|
| `projectflow-full-demo.html` | Demo 本體。新增：部門常數與輔助函式、v4 升級、可見性／權限函式、部門管理核心與面板、任務對話框欄位、看板／我的任務／總覽顯示、時間軸收合與篩選、範本帶部門 |
| `tests/records.html` | 測試執行頁：依序載入 `records.test.js`、`departments.test.js` 並合併結果 |
| `tests/records.test.js` | 既有 F11 測試；調整版本斷言與 3 個依賴舊權限的案例 |
| `tests/departments.test.js` | 本計畫的新測試 |
| `README.md` | F6、功能狀態表、資料模型 |

## 如何執行測試（每個 Task 都用）

1. 啟動伺服器：Browser pane 的 `preview_start`（name: `demo`，設定在 `.claude/launch.json`），或在專案根目錄執行：
   ```bash
   python -m http.server 8000
   ```
2. 開啟 `http://localhost:8000/tests/records.html`。
3. 讀 `#sum` 的文字（`get_page_text`，或 javascript_tool 執行 `document.getElementById('sum').textContent`）。失敗項目列在 `#out`。
4. 修改後重新整理（測試檔用 `cache: 'no-store'` 取得；Demo 若有快取就強制重新整理）。

以下「Run tests」都指這個流程。**Expected: PASS** 指 `#sum` 顯示「全部通過 N/N」。

## 行號說明

行號以 commit `edf46b6` 的 `projectflow-full-demo.html` 為準，前面的 Task 會讓後面的行號位移。請以引用的程式片段搜尋定位，不要只靠行號。

---

### Task 1: 部門資料、v4 升級、顯示改用部門名稱

**Files:**
- Create: `tests/departments.test.js`
- Modify: `tests/records.html`（載入兩個測試檔）
- Modify: `tests/records.test.js:14,28`（版本斷言）
- Modify: `projectflow-full-demo.html`：常數區（約 :405-431）、`seed()`（:434-571）、`upgrade()`／`load()`／`save()`（:639-660）、節點樹輔助函式（:678 之後）、`renderMe()`（:1303）、`viewPeople()`（:1840）、`pageOverview()`（:1858-1861、:1878）、`pageMyTasks()`（:1894）、AI 推薦協作部門（:2226、:2235-2238）、`userOpts()`（:2360）、任務對話框協作部門（:2386）、切換身分訊息（:3075）

**Interfaces:**
- Produces:
  - 常數 `DEFAULT_DEPTS`（`[id, name, head][]`）、`OLD_DEPT`（舊名稱→id）、`TAG_DEPT`（類別→id）
  - `defaultDepts(): {id,name,head}[]`
  - `db.departments: {id: string, name: string, head: string|null}[]`
  - `dept(id): object|null`、`deptName(id): string`（找不到回 `'—'`）、`deptMembers(id): string[]`（依 `USERS` 鍵的順序）、`isHead(uid, id): boolean`
  - 節點欄位 `dept: string|null`（任務必填，專案／階段 `null`）；`owner` 可為 `null`；`depts[]` 存 id
  - 模板節點欄位 `dept: string`；`dp[]` 存 id
  - `USERS[x].dept` 存 id
  - `upgrade(o)`：v2→v3→v4
  - 種子資料新增未指派任務 `t404`（d-qa）、`t504`（d-pe）、`t605`（d-rd）

- [ ] **Step 1: 測試頁改成載入多個測試檔**

把 `tests/records.html` 的 `<h1>` 與 `load` 處理改成：

```html
<h1>Demo 測試</h1>
```

```js
frame.addEventListener('load', async () => {
  const w = frame.contentWindow;
  const results = [];
  for (const f of ['records.test.js', 'departments.test.js']) {
    try {
      const src = await (await fetch(f, { cache: 'no-store' })).text();
      results.push(...(await w.eval(src)));
    } catch (e) {
      results.push({ name: `載入 ${f}`, ok: false, err: String(e && e.stack || e) });
    }
  }
  const fails = results.filter((r) => !r.ok);
  document.getElementById('sum').textContent = fails.length ? `失敗 ${fails.length}/${results.length}` : `全部通過 ${results.length}/${results.length}`;
  document.getElementById('out').innerHTML = results.map((r) => `<li class="${r.ok ? 'pass' : 'fail'}">${r.ok ? '✓' : '✗'} ${r.name}${r.ok ? '' : '\n' + r.err.replace(/</g, '&lt;')}</li>`).join('');
  window.__results = results;
});
```

同時把 `<title>` 改為 `Demo 測試`。

- [ ] **Step 2: 建立 `tests/departments.test.js`（Task 1 的測試）**

```js
// 部門模型測試（由 tests/records.html 以 iframe.contentWindow.eval 載入，在 Demo 全域環境內執行）
(async () => {
  const results = [];
  const eq = (a, b, m) => { if (JSON.stringify(a) !== JSON.stringify(b)) throw new Error(`${m || ''} 預期 ${JSON.stringify(b)}，實際 ${JSON.stringify(a)}`); };
  const ok = (v, m) => { if (!v) throw new Error(m || '預期為真'); };
  const as = (u) => { ui.me = u; };
  const T = async (name, fn) => {
    try { await resetAll(); as('yu'); await fn(); results.push({ name, ok: true }); }
    catch (e) { results.push({ name, ok: false, err: String(e && e.stack || e) }); }
  };
  const USERS_ALL = ['yu', 'ming', 'an', 'hua', 'chen', 'lin', 'it'];

  // ── Task 1：部門資料與升級 ──
  await T('種子資料：v4、10 個部門、任務都有負責部門', () => {
    eq(db.v, 4);
    eq(db.departments.map((d) => d.name), ['研發', '製程', '品保', '業務', '生管', '採購', '管理', '資訊', '財務', '製造']);
    eq(dept('d-qa').head, 'chen'); eq(dept('d-pe').head, null);
    const tasks = Object.values(db.nodes).filter((n) => n.type === 'task');
    ok(tasks.every((n) => dept(n.dept)), '每個任務都要有存在的負責部門');
    ok(Object.values(db.nodes).filter((n) => n.type !== 'task').every((n) => n.dept === null), '專案與階段沒有負責部門');
    eq(tasks.filter((n) => n.owner === null).map((n) => n.id).sort(), ['t404', 't504', 't605']);
    ok(tasks.every((n) => n.owner === null || USERS[n.owner].dept === n.dept), '負責人必須屬於負責部門');
  });
  await T('使用者部門與協作部門都存 id', () => {
    eq(USERS.an.dept, 'd-qa'); eq(USERS.lin.dept, 'd-sales'); eq(USERS.it.dept, 'd-it');
    eq(node('t301').depts, ['d-qa']); eq(node('t403').depts, ['d-sales']);
    eq(deptMembers('d-qa'), ['an', 'chen']); eq(deptName('nope'), '—');
    ok(isHead('chen', 'd-qa')); ok(!isHead('an', 'd-qa')); ok(!isHead('yu', null));
  });
  await T('模板節點都有負責部門，協作部門為 id', () => {
    ok(db.templates.every((t) => t.nodes.every((x) => dept(x.dept))), '每個模板節點都要有負責部門');
    eq(db.templates[0].nodes[1].dp, ['d-qa']);
  });
  await T('upgrade：v3 → v4 部門對應', () => {
    const d = seed(); d.v = 3; delete d.departments;
    Object.values(d.nodes).forEach((n) => { delete n.dept; if (n.owner === null) n.owner = 'yu'; });
    d.nodes.t301.depts = ['品保', '法規']; d.nodes.t403.depts = ['行銷']; d.nodes.t503.depts = ['生產', '外星部'];
    d.templates.forEach((t) => t.nodes.forEach((x) => { delete x.dept; x.dp = []; }));
    d.templates[0].nodes[1].dp = ['法規'];
    const au = freshAudit();
    const o = upgrade({ v: 3, db: d, audit: au });
    eq(o.v, 4); eq(o.db.v, 4); eq(o.db.departments.length, 10);
    eq(o.db.nodes.t301.depts, ['d-qa']); eq(o.db.nodes.t403.depts, ['d-sales']); eq(o.db.nodes.t503.depts, ['d-mfg', 'd-rd']);
    eq(o.db.nodes.t301.dept, 'd-pe'); eq(o.db.nodes.t4031.dept, 'd-sales'); eq(o.db.nodes.p1.dept, null);
    eq(o.db.templates[0].nodes[1].dp, ['d-qa']);
    ok(o.db.templates.every((t) => t.nodes.every((x) => x.dept)), '模板節點要補上負責部門');
    ok(au.acts.some((a) => a.text === '部門「外星部」已併入研發'), '要寫入合併的稽核紀錄');
  });
  await T('切換身分選單顯示部門名稱', () => {
    render();
    ok(document.getElementById('meSel').textContent.includes('品保'), '應顯示部門名稱');
    ok(!document.getElementById('meSel').textContent.includes('d-qa'), '不應顯示部門 id');
  });

  // ── 新測試加在這一行上面 ──
  return results;
})()
```

- [ ] **Step 3: 調整 `tests/records.test.js` 的版本斷言**

第 14 行 `eq(db.v, 3);` 改為 `eq(db.v, 4);`，測試名稱 `'種子資料為 v3 且含四個新陣列'` 改為 `'種子資料為 v4 且含四個新陣列'`。
第 28 行 `eq(o.v, 3); eq(o.db.v, 3);` 改為 `eq(o.v, 4); eq(o.db.v, 4);`，測試名稱 `'upgrade：v2 資料轉成 v3'` 改為 `'upgrade：v2 資料轉成 v4'`。

- [ ] **Step 4: Run tests — 確認新測試失敗**

Expected: FAIL（`dept is not defined`、`db.v` 為 3 等）。

- [ ] **Step 5: 常數區**

刪除 `const DEPTS = ['研發', '製程', '品保', '法規', '採購', '生產', '行銷'];`，改為：

```js
// 部門：id、名稱、預設主管（可在「成員與權限」由系統管理員維護，存在 db.departments）
const DEFAULT_DEPTS = [['d-rd', '研發', 'yu'], ['d-pe', '製程', null], ['d-qa', '品保', 'chen'], ['d-sales', '業務', null], ['d-pc', '生管', null], ['d-pur', '採購', 'hua'], ['d-adm', '管理', null], ['d-it', '資訊', null], ['d-fin', '財務', null], ['d-mfg', '製造', null]];
const defaultDepts = () => DEFAULT_DEPTS.map(([id, name, head]) => ({ id, name, head }));
// v3 以前的部門名稱 → 部門 id
const OLD_DEPT = { 研發: 'd-rd', 製程: 'd-pe', 品保: 'd-qa', 法規: 'd-qa', 採購: 'd-pur', 生產: 'd-mfg', 行銷: 'd-sales', 資訊: 'd-it' };
// 任務類別 → 預設負責部門（模板與升級時使用）
const TAG_DEPT = { 市場: 'd-sales', 配方: 'd-rd', 試作: 'd-rd', 製程: 'd-pe', 品保: 'd-qa', 檢驗: 'd-qa', 測試: 'd-qa', 法規: 'd-qa', 採購: 'd-pur', 生產: 'd-mfg', 行銷: 'd-sales' };
```

`USERS` 的 `dept` 改成 id：yu `'d-rd'`、ming `'d-pe'`、an `'d-qa'`、hua `'d-pur'`、chen `'d-qa'`、lin `'d-sales'`、it `'d-it'`。其他欄位不變。

- [ ] **Step 6: `seed()`**

1. `const db = { v: 3, ...` 改為 `v: 4`，並在物件中加入 `departments: defaultDepts(),`。
2. `N()` 裡的 `owner: o.who || 'yu',` 改為下面兩行（放在同一個物件內）：

```js
      owner: 'who' in o ? o.who : 'yu',
      dept: type === 'task' ? (o.dept || USERS['who' in o && o.who ? o.who : 'yu'].dept) : null,
```

3. 協作部門改成 id：
   - `t301` 的 `dp: ['品保']` → `dp: ['d-qa']`
   - `t403` 的 `dp: ['行銷']` → `dp: ['d-sales']`
   - `t503` 的 `dp: ['行銷']` → `dp: ['d-sales']`
   - `t802` 的 `dp: ['品保']` → `dp: ['d-qa']`
4. 新增 3 件未指派任務（放在各自階段區塊的最後一個 `N(...)` 之後、`dep(...)` 之前）：

```js
  // 未指派：只有部門主管（與專案負責人、系統管理員）看得到
  N('t404', 'p1d', 'task', '檢驗報告判讀與宣稱比對', { tag: '品保', who: null, dept: 'd-qa', s: '2026-11-09', e: '2026-11-20' });
```

```js
  N('t504', 'p1e', 'task', '量產製程參數確認', { tag: '製程', who: null, dept: 'd-pe', s: '2026-12-01', e: '2026-12-18' });
```

```js
  N('t605', 'p2a', 'task', '關節保健成分功效評估', { tag: '配方', who: null, dept: 'd-rd', s: '2026-10-05', e: '2026-10-30' });
```

5. 模板：`chain` 與 `mkTpl` 改為帶部門：

```js
  const toIds = (arr) => [...new Set((arr || []).map((x) => OLD_DEPT[x] || x))];
  const chain = (arr) => arr.map((a, i) => ({ k: 'k' + i, p: 'r', title: a[0], tag: a[1], off: a[2], dur: a[3], dp: toIds(a[4]), dept: TAG_DEPT[a[1]] || 'd-rd' }));
  const mkTpl = (id, name, scope, desc, rootTag, list, extra = {}) => {
    const nodes = [{ k: 'r', p: null, title: name + '：{產品名}', tag: rootTag, off: 0, dur: 0, dp: [], dept: TAG_DEPT[rootTag] || 'd-rd' }, ...chain(list)];
```

（`mkTpl` 其餘不變；模板清單裡的 `['法規']` 等名稱維持原樣，由 `toIds` 轉換。）

- [ ] **Step 7: 輔助函式**

在 `const uname = ...` 那一行之後加入：

```js
const dept = (id) => (id && db.departments.find((d) => d.id === id)) || null;
const deptName = (id) => (dept(id) ? dept(id).name : '—');
const deptMembers = (id) => Object.keys(USERS).filter((u) => USERS[u].dept === id);
const isHead = (uid, id) => !!dept(id) && dept(id).head === uid;
```

- [ ] **Step 8: `upgrade()`、`load()`、`save()`**

在 `upgrade(o)` 的 `if (o.v === 2) { ... }` 區塊之後、`return o;` 之前加入（v2 區塊會把 `o.v` 設成 3，所以會接著跑這段）：

```js
  // v3 → v4：部門改為可設定的資料；任務補上負責部門；部門名稱改存 id
  if (o.v === 3) {
    const d = o.db;
    d.departments = d.departments || defaultDepts();
    const known = new Set(d.departments.map((x) => x.id));
    const merged = new Set();
    const toId = (x) => { if (known.has(x)) return x; if (OLD_DEPT[x]) return OLD_DEPT[x]; merged.add(x); return 'd-rd'; };
    const ids = (arr) => [...new Set((arr || []).map(toId))];
    Object.values(d.nodes).forEach((n) => {
      n.depts = ids(n.depts);
      n.dept = n.type === 'task' ? ((USERS[n.owner] && USERS[n.owner].dept) || 'd-rd') : null;
    });
    d.templates.forEach((t) => t.nodes.forEach((x) => {
      x.dp = ids(x.dp);
      x.dept = (x.who && USERS[x.who] && USERS[x.who].dept) || TAG_DEPT[x.tag] || x.dp[0] || 'd-rd';
    }));
    merged.forEach((nm) => o.audit.acts.unshift({ at: nowStr(), actor: 'it', node: null, action: '部門', text: `部門「${nm}」已併入研發` }));
    d.v = 4; o.v = 4;
  }
```

`load()` 的條件 `(o.v === 2 || o.v === 3)` 改為 `[2, 3, 4].includes(o.v)`。
`save()` 的 `{ v: 3, db, audit, me: ui.me }` 改為 `{ v: 4, db, audit, me: ui.me }`。

- [ ] **Step 9: 顯示部門名稱的地方**

逐一替換（用片段搜尋）：

1. `renderMe()`：`${x.name}｜${ROLES[x.role]}｜${x.dept}` → `${x.name}｜${ROLES[x.role]}｜${esc(deptName(x.dept))}`
2. 切換身分訊息（change 事件 `meSel`）：`${me().dept}` → `${deptName(me().dept)}`
3. `viewPeople()` 協作部門：`${n.depts.map((d) => \`<span class="tag gray">${esc(d)}</span>\`)` → `${n.depts.map((d) => \`<span class="tag gray">${esc(deptName(d))}</span>\`)`
4. `pageOverview()`：
   - 人員負載那行 `${esc(USERS[u]?.dept || '')}` → `${esc(USERS[u] ? deptName(USERS[u].dept) : '')}`
   - `open.forEach((x) => { const d = USERS[x.owner]?.dept || '—'; deptLoad[d] = (deptLoad[d] || 0) + 1; });` → `open.forEach((x) => { const d = deptName(x.dept); deptLoad[d] = (deptLoad[d] || 0) + 1; });`
   - `open.forEach((x) => { load[x.owner] = ...` 這行開頭加上 `if (!x.owner) return;`，即改為 `open.forEach((x) => { if (!x.owner) return; load[x.owner] = load[x.owner] || ...`（其餘不變）
5. `pageMyTasks()`：`` [`我部門（${u.dept}）被指派的`, `` → `` [`我部門（${deptName(u.dept)}）被指派的`, ``（Task 5 會移除這組）
6. AI 欄位權限訊息：`${me().name}（${me().dept}）無法查詢` → `${me().name}（${deptName(me().dept)}）無法查詢`
7. AI 推薦協作部門：`deptMap` 改為 id，顯示時轉名稱：

```js
      const deptMap = { 檢驗: ['d-qa'], 法規: ['d-sales', 'd-qa'], 試作: ['d-mfg', 'd-qa'], 製程: ['d-qa', 'd-mfg'], 採購: ['d-qa'], 品保: ['d-pe'], 行銷: ['d-qa'], 測試: ['d-sales'], 生產: ['d-pe', 'd-pur'], 配方: ['d-pur', 'd-qa'] };
      const depts = deptMap[n.tag] || ['d-qa'];
```

   同一個 `return { text: ... }` 裡：`推薦協作部門：${depts.join('、')}` → `推薦協作部門：${depts.map(deptName).join('、')}`；`（目前已有：${n.depts.join('、')}）` → `（目前已有：${n.depts.map(deptName).join('、')}）`。
   `runAIAction` 的 `addDepts` 稽核文字：`加入協作部門：${a.payload.depts.join('、')}` → `加入協作部門：${a.payload.depts.map(deptName).join('、')}`。
8. `userOpts()`：`${u.name}（${u.dept}）` → `${esc(u.name)}（${esc(deptName(u.dept))}）`
9. 任務對話框協作部門：

```js
    <div class="field"><span class="lb">協作部門</span><div class="chips">${db.departments.map((x) => `<label><input type="checkbox" class="eDp" value="${x.id}" ${n.depts.includes(x.id) ? 'checked' : ''} ${ed && me().role !== 'collab' ? '' : 'disabled'}>${esc(x.name)}</label>`).join('')}</div></div>
```

10. 模板庫預覽：`${x.dp && x.dp.length ? '，' + x.dp.join('/') : ''}` → `${x.dp && x.dp.length ? '，' + esc(x.dp.map(deptName).join('/')) : ''}`

確認沒有遺漏：在 `projectflow-full-demo.html` 搜尋 `DEPTS`（應只剩 `DEFAULT_DEPTS`）與 `.dept}`、`.dept ||`，逐一確認都經過 `deptName()` 或是 id 比對。

- [ ] **Step 10: Run tests**

Expected: PASS（所有既有測試與 Task 1 新測試）。

- [ ] **Step 11: Commit**

```bash
git add projectflow-full-demo.html tests/records.html tests/records.test.js tests/departments.test.js
git commit -m "Departments task 1: department data, v4 upgrade, show department names"
```

---

### Task 2: 可見性（只有相關的人看得到）

**Files:**
- Modify: `projectflow-full-demo.html`：權限區（:715-733）、`pageNode()`（:1324、:1359、:1376）、`viewBoard()`（:1437）、change 事件（`meSel`、`showAllChk`）、所有 `shown(` 呼叫
- Test: `tests/departments.test.js`

**Interfaces:**
- Consumes: `dept`、`isHead`、節點 `dept`／`owner`（Task 1）
- Produces:
  - `inScopeOf(n, u): boolean`（審核人範圍）；`inReviewerScope(n)` 改為 `inScopeOf(n, me())`
  - `directSee(n, u): boolean`、`seeTask(n, u = me()): boolean`、`seeNode(n, u = me()): boolean`
  - `SEE_ALL = ['admin', 'owner', 'readonly']`
  - `visible(n)` = `seeNode(n)`；`shown()`、`related()`、`relSelf()`、`assigned()`、`fullViewAllowed()`、`ui.showAll` 全部移除

- [ ] **Step 1: 寫失敗測試**（加在 `departments.test.js` 的「新測試加在這一行上面」之前）

```js
  // ── Task 2：可見性 ──
  const see = (u, id) => { as(u); return visible(node(id)); };
  const who = (id) => USERS_ALL.filter((u) => see(u, id));
  await T('未指派任務：只有部門主管、專案負責人、系統管理員看得到', () => {
    eq(who('t404'), ['yu', 'chen', 'it']);
  });
  await T('未指派且部門沒有主管：只有專案負責人與系統管理員', () => {
    eq(who('t504'), ['yu', 'it']);
  });
  await T('已指派：負責人、部門主管、協作人員、協作部門主管、範圍內審核人', () => {
    eq(who('t30121'), ['yu', 'ming', 'chen', 'it']);
    eq(who('t403'), ['yu', 'an', 'chen', 'lin', 'it']);
    eq(who('t802'), ['yu', 'hua', 'chen', 'it']);
  });
  await T('同部門成員看不到已指派給別人的任務', () => {
    eq(see('an', 't30122'), false);
  });
  await T('路徑：負責子任務的人看得到上層與專案的所有階段；負責上層的人看得到子任務', () => {
    node('t30122').owner = 'an';
    ok(see('an', 't3012'), '看得到上層任務'); ok(see('an', 'p1'), '看得到專案'); ok(see('an', 'p1a'), '看得到同專案的其他階段');
    ok(!see('an', 't3013'), '看不到旁支任務');
    ok(see('ming', 't30122'), '負責上層任務的人看得到子任務');
  });
  await T('未指派的子任務：負責上層任務的人也看不到', () => {
    db.nodes['t-un'] = { ...clone(node('t30122')), id: 't-un', owner: null, dept: 'd-pe', collabs: [], depts: [] };
    eq(see('ming', 't-un'), false); eq(see('yu', 't-un'), true);
  });
  await T('唯讀角色看得到全部；看不到任何任務的專案不顯示', () => {
    ok(seeNode(node('t504'), { id: 'x', role: 'readonly', dept: 'd-it' }));
    eq(see('lin', 'p2'), false);
  });
  await T('拿掉「顯示全部任務」開關', () => {
    as('ming'); ui.page = 'node'; ui.node = 'p1'; ui.tab = 'board'; render();
    ok(!document.getElementById('showAllChk'), '不應有顯示全部開關');
    ok(!document.querySelector('[data-id="t404"]'), '看板不應出現看不到的任務');
  });
```

- [ ] **Step 2: Run tests — 確認失敗**

Expected: FAIL（`seeNode is not defined`、可見名單不符）。

- [ ] **Step 3: 實作可見性**

把 `function assigned(...)` 到 `function inReviewerScope(...)`（:715-733）整段換成：

```js
/* 可見性：只有相關的人看得到任務 */
function inScopeOf(n, u) { const ph = phaseOf(n); return u.role === 'reviewer' && !!ph && (u.scope || []).includes(ph.title); }
function inReviewerScope(n) { return inScopeOf(n, me()); }
// 直接相關：未指派時只有部門主管；已指派時是負責人、協作人員、負責部門或協作部門的主管、範圍內的審核人
function directSee(n, u) {
  if (!n || n.type !== 'task') return false;
  if (n.owner === null) return isHead(u.id, n.dept);
  return n.owner === u.id || n.collabs.includes(u.id) || isHead(u.id, n.dept) || n.depts.some((d) => isHead(u.id, d)) || inScopeOf(n, u);
}
const SEE_ALL = ['admin', 'owner', 'readonly'];
// 任務：直接相關；或上層任務直接相關（未指派任務除外）；或下層任務直接相關（顯示路徑）
function seeTask(n, u = me()) {
  if (SEE_ALL.includes(u.role)) return true;
  if (directSee(n, u)) return true;
  if (n.owner !== null && ancestors(n).some((a) => directSee(a, u))) return true;
  return descendants(n.id).some((d) => directSee(d, u) || (d.owner !== null && ancestors(d).some((a) => directSee(a, u))));
}
// 專案與階段：專案底下有任何看得到的任務，就看得到專案與它的所有階段
function seeNode(n, u = me()) {
  if (!n) return false;
  if (SEE_ALL.includes(u.role)) return true;
  if (n.type === 'task') return seeTask(n, u);
  const p = n.type === 'project' ? n : projectOf(n);
  return descendants(p.id).some((d) => d.type === 'task' && seeTask(d, u));
}
function visible(n) { return seeNode(n); }
```

注意 `seeTask` 下層規則：子任務「看得到」可能來自它自己的上層規則，所以檢查 `directSee(d)` 或 `d` 的上層直接相關（未指派除外）。`can()` 裡 `case 'view': return !n || visible(n);` 不必改。

- [ ] **Step 4: 移除 `shown()` 與「顯示全部」**

1. 在 `projectflow-full-demo.html` 把所有 `shown(` 改成 `visible(`（`.filter(shown)` 改成 `.filter(visible)`、`projects().find(shown)` 改成 `projects().find(visible)`）。
2. `pageNode()`：`if (!n || !can('view', n) || !shown(n)) { n = projects().find(shown) || projects().find(visible); ui.node = n.id; }` → `if (!n || !can('view', n)) { n = projects().find(visible) || projects()[0]; ui.node = n.id; }`
3. `pageNode()`：刪除 `const mineTool = ...;` 整行；`<div class="tools">${mineTool}${tools[ui.tab] || ''}</div>` → `<div class="tools">${tools[ui.tab] || ''}</div>`
4. `viewBoard()`：`` `<div class="panel empty">這裡沒有與你（${esc(me().name)}）相關的任務。${fullViewAllowed() ? '可勾選右上方「顯示全部任務」查看其他人的任務。' : ''}</div>` `` → `` `<div class="panel empty">這裡沒有與你（${esc(me().name)}）相關的任務。</div>` ``
5. change 事件 `meSel`：刪除 `ui.showAll = false;`，`!shown(node(ui.node))` → `!visible(node(ui.node))`，`projects().find(shown)` → `projects().find(visible)`。
6. 刪除 `if (t.id === 'showAllChk') { ui.showAll = t.checked; return render(); }`。
7. 搜尋確認 `shown(`、`showAll`、`fullViewAllowed`、`related(`、`relSelf`、`assigned(` 都不存在。

- [ ] **Step 5: Run tests**

Expected: PASS。若 `records.test.js` 有案例因可見性失敗，先看是否屬於 Task 3 要調整的三個跳過案例（那三個在 Task 3 修）；其他失敗代表實作有誤。

> 如果 Task 2 結束時 `records.test.js` 的「成員申請跳過」三個案例已經失敗（因為 ming 看不到 t30122），可以把 Task 3 Step 3 的測試調整提前到這裡做。

- [ ] **Step 6: Commit**

```bash
git add projectflow-full-demo.html tests/departments.test.js tests/records.test.js
git commit -m "Departments task 2: only related people can see tasks; remove show-all toggle"
```

---

### Task 3: 操作權限（canWork、指派、改部門）

**Files:**
- Modify: `projectflow-full-demo.html`：`can()`（:734-752）、`canNote()`（:1115）、`viewPeople()` 權限矩陣（:1829-1834、:1843）
- Modify: `tests/records.test.js`（3 個跳過案例改用 an）
- Test: `tests/departments.test.js`

**Interfaces:**
- Consumes: `isHead`（Task 1）、`seeNode`（Task 2）
- Produces:
  - `canWork(n, u = me()): boolean`：任務的改狀態、進度、送回報、編輯
  - `can('edit', task)` = `canWork(task)`；`can('assign', n)`、`can('dept', n)` 新動作
  - `canNote(n)`：`can('edit')` 或協作人員或協作部門主管

- [ ] **Step 1: 寫失敗測試**

```js
  // ── Task 3：操作權限 ──
  const w = (u, id) => { as(u); return canWork(node(id)); };
  await T('canWork：負責人、部門主管、專案負責人、系統管理員', () => {
    ok(w('ming', 't30121')); ok(w('yu', 't30121')); ok(w('it', 't30121'));
    ok(!w('chen', 't30121'), '審核人不是負責人也不是部門主管');
    node('t30122').owner = 'an';
    ok(w('an', 't30122'), '負責人'); ok(w('chen', 't30122'), '部門主管');
    ok(!w('lin', 't403'), '協作人員不能操作');
    ok(w('chen', 't404'), '主管可以操作未指派任務'); ok(!w('an', 't404'), '同部門成員不能操作未指派任務');
  });
  await T('協作人員可以寫筆記，但不能送回報、不能改狀態', () => {
    as('lin');
    ok(canNote(node('t403')), '協作人員可以寫筆記');
    ok(!canReport(node('t4032')));
    eq(setStatus('t4032', 'doing'), false);
  });
  await T('指派負責人與改負責部門的權限', () => {
    as('chen'); ok(can('assign', node('t404')), '部門主管可以指派'); ok(!can('dept', node('t404')), '部門主管不能改部門');
    as('an'); ok(!can('assign', node('t404')));
    as('yu'); ok(can('assign', node('t504'))); ok(can('dept', node('t504')));
    as('ming'); ok(!can('assign', node('t30121')), '負責人不能自己改派');
  });
  await T('修改時程：成員只能改自己負責或自己主管部門的任務', () => {
    as('ming'); ok(can('schedule', node('t30121'))); ok(!can('schedule', node('t30122')));
    as('hua'); ok(can('schedule', node('t8024')));
  });
  await T('權限表顯示「指派負責人」', () => {
    ui.page = 'node'; ui.node = 'p1'; ui.tab = 'people'; render();
    ok(document.getElementById('main').textContent.includes('指派負責人'));
  });
```

- [ ] **Step 2: Run tests — 確認失敗**

Expected: FAIL（`canWork is not defined`）。

- [ ] **Step 3: 調整 `tests/records.test.js` 的三個跳過案例**

這三個案例原本用 ming 申請跳過 t30122（負責人 chen）。新規則下 ming 看不到也不能操作 t30122，改成讓 an 負責：

1. `'成員申請跳過 → 範圍內審核人核准 → 已跳過、進度 100%'`：第一行 `as('ming');` → `node('t30122').owner = 'an'; as('an');`
2. `'成員不能核准跳過申請'`：`as('ming'); skipTask('t30122', '想跳過');` → `node('t30122').owner = 'an'; as('an'); skipTask('t30122', '想跳過');`
3. `'跳過上層任務時結案子任務的跳過申請；恢復後子任務回到原狀態'`：`as('ming'); skipTask('t30122', '想跳過');` → `node('t30122').owner = 'an'; as('an'); skipTask('t30122', '想跳過');`

- [ ] **Step 4: 實作**

在 `function can(a, n) {` 之前加入：

```js
// 任務的操作（改狀態、進度、送回報、編輯）：負責人、負責部門主管、專案負責人、系統管理員
function canWork(n, u = me()) {
  if (!n || n.type !== 'task') return false;
  if (u.role === 'admin' || u.role === 'owner') return true;
  if (u.role === 'readonly') return false;
  return isHead(u.id, n.dept) || (n.owner !== null && n.owner === u.id);
}
```

`can()` 的 switch 改為：

```js
    case 'view': return !n || visible(n);
    case 'edit': if (n && n.type === 'task') return canWork(n); return r === 'collab' ? !!n && n.owner === u.id : true;
    case 'create': return r !== 'collab' || (!!n && n.owner === u.id);
    case 'delete': return r === 'owner';
    case 'schedule': return r === 'owner' || r === 'reviewer' || (r === 'member' && !!n && canWork(n));
    case 'deps': return r === 'owner' || r === 'reviewer';
    case 'gate': return r === 'owner' || (r === 'reviewer' && !!n && inReviewerScope(n));
    case 'override': return r === 'owner' || (r === 'reviewer' && !!n && inReviewerScope(n));
    case 'assign': return !!n && n.type === 'task' && (r === 'owner' || isHead(u.id, n.dept));
    case 'dept': return !!n && n.type === 'task' && r === 'owner';
    case 'members': return r === 'owner';
    case 'templates': return false;
    case 'formula-approve': return r === 'owner';
    default: return false;
```

（`admin` 在 switch 之前已回傳 `true`，`readonly` 只有 `view`。）

`canNote` 改為：

```js
function canNote(n) { return !!n && (can('edit', n) || n.collabs.includes(ui.me) || n.depts.some((d) => isHead(ui.me, d))); }
```

`viewPeople()` 的 `acts` 與 `matrix` 改為：

```js
  const acts = [['view', '檢視'], ['edit', '新增 / 編輯任務'], ['assign', '指派負責人'], ['delete', '刪除任務'], ['schedule', '修改時程'], ['deps', '設定前置條件'], ['gate', '核准階段閘門'], ['override', '覆寫（跳過）前置 / 閘門'], ['members', '管理成員與權限'], ['templates', '管理模板庫']];
  const matrix = {
    admin: ['✅', '✅', '✅', '✅', '✅', '✅', '✅', '✅', '✅', '✅'], owner: ['✅', '✅', '✅', '✅', '✅', '✅', '✅', '✅', '✅', ''],
    reviewer: ['相關任務', '自己負責／部門主管', '部門主管', '', '✅', '✅', '指定階段', '指定階段', '', ''],
    member: ['相關任務', '自己負責／部門主管', '部門主管', '', '自己負責／部門主管', '', '', '', '', ''],
    collab: ['相關任務', '自己負責', '', '', '', '', '', '', '', ''], readonly: ['✅', '', '', '', '', '', '', '', '', ''],
  };
```

說明文字 `<p class="small muted">協作人員只看得到被指派的節點（及必要的上層摘要）。權限預設繼承上層，可在子樹覆寫。</p>` 改為：

```html
<p class="small muted">每件任務只有相關的人看得到：負責人、協作人員、負責部門與協作部門的主管、範圍內的審核人。未指派負責人的任務只有部門主管看得到。</p>
```

- [ ] **Step 5: Run tests**

Expected: PASS。

- [ ] **Step 6: Commit**

```bash
git add projectflow-full-demo.html tests/departments.test.js tests/records.test.js
git commit -m "Departments task 3: canWork, assign and department permissions"
```

---

### Task 4: 部門管理（新增、修改、刪除與面板）

**Files:**
- Modify: `projectflow-full-demo.html`：在 `viewPeople()` 之前加核心函式與面板；`viewPeople()` 結尾插入面板；click 事件（`ds.deptAdd`、`ds.deptEdit`、`ds.deptDel`）；submit 事件（`deptForm`）
- Test: `tests/departments.test.js`

**Interfaces:**
- Consumes: `dept`、`deptName`、`deptMembers`（Task 1）
- Produces:
  - `deptUsage(id): { tasks: number, users: number }`
  - `addDept(name): { ok, id? , error? }`、`updateDept(id, { name, head }): { ok, error? }`、`deleteDept(id): { ok, error? }`
  - `deptPanelHTML(): string`、`openDeptDlg(id|null)`、`submitDept(id|'')`

- [ ] **Step 1: 寫失敗測試**

```js
  // ── Task 4：部門管理 ──
  await T('部門管理只限系統管理員', () => {
    as('yu'); eq(addDept('品管').error, '只有系統管理員可以管理部門');
    eq(deleteDept('d-fin').ok, false);
  });
  await T('新增部門：名稱必填、不可重複', () => {
    as('it');
    eq(addDept('  ').error, '請填寫部門名稱');
    eq(addDept('研發').error, '已有同名部門');
    const r = addDept('倉儲'); ok(r.ok); eq(dept(r.id).name, '倉儲'); eq(dept(r.id).head, null);
  });
  await T('修改部門：主管必須是部門成員、名稱不可重複', () => {
    as('it');
    eq(updateDept('d-qa', { name: '品保', head: 'ming' }).error, '主管必須是部門成員');
    eq(updateDept('d-qa', { name: '研發', head: null }).error, '已有同名部門');
    ok(updateDept('d-qa', { name: '品質保證', head: 'an' }).ok);
    eq(deptName('d-qa'), '品質保證'); eq(dept('d-qa').head, 'an');
  });
  await T('刪除部門：有任務或人員時拒絕；空部門可以刪除且可復原', () => {
    as('it');
    const u = deptUsage('d-qa');
    eq(u.users, 2); ok(u.tasks > 0);
    eq(deleteDept('d-qa').error, `部門還有 ${u.tasks} 件任務、2 位人員，請先移轉`);
    ok(deleteDept('d-fin').ok); eq(dept('d-fin'), null);
    undo(); ok(dept('d-fin'), '復原後部門回來');
  });
  await T('部門面板：管理員有編輯按鈕，其他人唯讀；標示未設主管', () => {
    ui.page = 'node'; ui.node = 'p1'; ui.tab = 'people';
    as('it'); render();
    ok(document.querySelector('[data-dept-add]'), '管理員看得到新增部門');
    ok(document.querySelector('[data-dept-edit="d-qa"]'));
    as('ming'); render();
    ok(!document.querySelector('[data-dept-add]'), '成員看不到新增部門');
    ok(document.getElementById('main').textContent.includes('未設主管'));
  });
```

- [ ] **Step 2: Run tests — 確認失敗**

Expected: FAIL（`addDept is not defined`）。

- [ ] **Step 3: 核心函式**（放在 `function viewPeople(n) {` 之前）

```js
/* ---------- 部門管理 ---------- */
function deptUsage(id) {
  const tasks = Object.values(db.nodes).filter((n) => n.dept === id || (n.depts || []).includes(id)).length
    + db.templates.reduce((a, t) => a + t.nodes.filter((x) => x.dept === id || (x.dp || []).includes(id)).length, 0);
  return { tasks, users: deptMembers(id).length };
}
const deptAdminErr = () => (me().role === 'admin' ? null : '只有系統管理員可以管理部門');
function addDept(name) {
  const err = deptAdminErr(); if (err) return { ok: false, error: err };
  const nm = String(name || '').trim();
  if (!nm) return { ok: false, error: '請填寫部門名稱' };
  if (db.departments.some((d) => d.name === nm)) return { ok: false, error: '已有同名部門' };
  const id = commit(`新增部門「${nm}」`, () => { const nid = newId('d-'); db.departments.push({ id: nid, name: nm, head: null }); return nid; });
  log(null, '部門', `新增部門「${nm}」`);
  return { ok: true, id };
}
function updateDept(id, { name, head }) {
  const err = deptAdminErr(); if (err) return { ok: false, error: err };
  const d = dept(id); if (!d) return { ok: false, error: '找不到部門' };
  const nm = String(name || '').trim();
  if (!nm) return { ok: false, error: '請填寫部門名稱' };
  if (db.departments.some((x) => x.id !== id && x.name === nm)) return { ok: false, error: '已有同名部門' };
  if (head && !deptMembers(id).includes(head)) return { ok: false, error: '主管必須是部門成員' };
  const old = d.name;
  commit(`修改部門「${old}」`, () => { d.name = nm; d.head = head || null; });
  log(null, '部門', `修改部門「${old}」：名稱「${nm}」，主管 ${head ? uname(head) : '未設'}`);
  return { ok: true };
}
function deleteDept(id) {
  const err = deptAdminErr(); if (err) return { ok: false, error: err };
  const d = dept(id); if (!d) return { ok: false, error: '找不到部門' };
  const u = deptUsage(id);
  if (u.tasks || u.users) return { ok: false, error: `部門還有 ${u.tasks} 件任務、${u.users} 位人員，請先移轉` };
  commit(`刪除部門「${d.name}」`, () => { db.departments = db.departments.filter((x) => x.id !== id); });
  log(null, '部門', `刪除部門「${d.name}」`);
  return { ok: true };
}
function deptPanelHTML() {
  const adm = me().role === 'admin';
  return `<div class="panel"><div class="row" style="justify-content:space-between"><h3>部門</h3>${adm ? '<button class="btn sm" type="button" data-dept-add>＋ 新增部門</button>' : ''}</div>
    <div class="tbl-wrap"><table class="tbl"><thead><tr><th>部門</th><th>主管</th><th>成員</th><th>任務</th>${adm ? '<th></th>' : ''}</tr></thead><tbody>
    ${db.departments.map((d) => { const u = deptUsage(d.id); return `<tr><td>${esc(d.name)}</td>
      <td>${d.head ? `${av(d.head, 22)} ${esc(uname(d.head))}` : '<span class="tag warn" title="這個部門的未指派工作只有專案負責人看得到">未設主管</span>'}</td>
      <td>${u.users}</td><td>${u.tasks}</td>
      ${adm ? `<td class="row"><button class="btn sm" type="button" data-dept-edit="${d.id}">編輯</button><button class="btn sm danger" type="button" data-dept-del="${d.id}">刪除</button></td>` : ''}</tr>`; }).join('')}
    </tbody></table></div>
    <p class="small muted">${adm ? '刪除前需先移轉部門的任務與人員。' : '部門與主管由系統管理員維護。'}</p></div>`;
}
function openDeptDlg(id) {
  const d = id ? dept(id) : null;
  openDlg(`<form id="deptForm" data-id="${id || ''}"><h2 class="serif">${d ? '編輯部門' : '新增部門'}</h2>
    <div class="field"><label for="dpName">部門名稱</label><input id="dpName" value="${esc(d ? d.name : '')}" required></div>
    ${d ? `<div class="field"><label for="dpHead">主管</label><select id="dpHead"><option value="">未設主管</option>${deptMembers(d.id).map((u) => `<option value="${u}" ${u === d.head ? 'selected' : ''}>${esc(uname(u))}</option>`).join('')}</select></div>` : '<p class="small muted">新部門還沒有成員，建立後再設定主管。</p>'}
    <div class="dlg-actions"><button class="btn" type="button" data-close-dlg>取消</button><button class="btn primary" type="submit">儲存</button></div></form>`);
}
function submitDept(id) {
  const r = id ? updateDept(id, { name: $('dpName').value, head: $('dpHead').value || null }) : addDept($('dpName').value);
  if (!r.ok) return toast(r.error, 'warn');
  closeDlg(); toast(id ? '已更新部門' : '已新增部門');
}
```

- [ ] **Step 4: 面板與事件**

1. `viewPeople()` 的回傳字串最後 `</tbody></table></div></div>\`;` 改為 `</tbody></table></div>${deptPanelHTML()}</div>\`;`（面板放在權限矩陣之後、外層 `.stack` 之內）。
2. click 事件（`document.addEventListener('click', ...)` 內、`if (ds.go) return go(ds.go);` 之後）加入：

```js
  if ('deptAdd' in ds) return openDeptDlg(null);
  if (ds.deptEdit) return openDeptDlg(ds.deptEdit);
  if (ds.deptDel) { const r = deleteDept(ds.deptDel); return r.ok ? toast('已刪除部門', null, { label: '復原', fn: undo }) : toast(r.error, 'warn'); }
```

3. submit 事件（`if (f.id === 'edForm') return saveEditor(f.dataset.id);` 之後）加入：

```js
  if (f.id === 'deptForm') return submitDept(f.dataset.id);
```

- [ ] **Step 5: Run tests**

Expected: PASS。

- [ ] **Step 6: Commit**

```bash
git add projectflow-full-demo.html tests/departments.test.js
git commit -m "Departments task 4: department management panel (add, edit, delete)"
```

---

### Task 5: 任務的負責部門與負責人（對話框、新增、看板、我的任務、總覽）

**Files:**
- Modify: `projectflow-full-demo.html`：`addNode()`（:2297-2306）、`userOpts()` 附近（新增 `deptOpts`、`ownerOpts`）、`openEditor()` 負責人列（:2376-2377）、`saveEditor()`（:2418-2440）、`openQuickAdd()` 的 `qWho`（:2461）、qaForm 送出（:3104）、change 事件（`eDept`）、`cardHTML()`（:1431）、`pageNode()` 標題 meta（:1337）、`pageMyTasks()`（:1891-1903）、`pageOverview()` 部門負載（:1861、:1881）
- Test: `tests/departments.test.js`

**Interfaces:**
- Consumes: `dept`、`deptName`、`deptMembers`、`isHead`（Task 1）；`can('assign')`、`can('dept')`（Task 3）
- Produces:
  - `addNode(parent, o)`：接受 `o.dept`；`o.owner` 未給時預設目前使用者（若屬於該部門）；負責人不屬於部門時一律設為 `null`
  - `deptOpts(sel): string`、`ownerOpts(deptId, sel): string`、`whoHTML(n): string`

- [ ] **Step 1: 寫失敗測試**

```js
  // ── Task 5：負責部門與負責人 ──
  await T('addNode：預設上層任務的部門；負責人不在部門時為未指派', () => {
    as('yu'); const a = commit('t', () => addNode('t3012', { title: 'A' }));
    eq(node(a).dept, 'd-pe'); eq(node(a).owner, null);
    as('ming'); const b = commit('t', () => addNode('t3012', { title: 'B' }));
    eq(node(b).owner, 'ming');
    as('yu'); const c = commit('t', () => addNode('p1a', { title: 'C' }));
    eq(node(c).dept, 'd-rd'); eq(node(c).owner, 'yu');
    const d = commit('t', () => addNode('p1a', { title: 'D', dept: 'd-qa', owner: 'ming' }));
    eq(node(d).owner, null, '負責人不屬於部門時清空');
  });
  await T('任務對話框：負責人只列出部門成員；換部門會清空不屬於新部門的負責人', () => {
    as('yu'); openEditor('t404');
    eq([...$('eOwner').options].map((o) => o.value), ['', 'an', 'chen']);
    closeDrawer();
    openEditor('t30121');
    $('eDept').value = 'd-qa'; $('eDept').dispatchEvent(new Event('change', { bubbles: true }));
    eq($('eOwner').value, '');
    $('eOwner').value = 'an'; saveEditor('t30121');
    eq(node('t30121').dept, 'd-qa'); eq(node('t30121').owner, 'an');
  });
  await T('任務對話框：部門主管可以指派但不能改部門', () => {
    as('chen'); openEditor('t404');
    ok($('eDept').disabled, '部門欄停用'); ok(!$('eOwner').disabled, '負責人欄可用');
    $('eOwner').value = 'an'; saveEditor('t404');
    eq(node('t404').owner, 'an');
  });
  await T('看板：未指派卡片顯示「未指派・部門」', () => {
    as('yu'); ui.page = 'node'; ui.node = 'p1d'; ui.tab = 'board'; render();
    ok(document.querySelector('[data-id="t404"]').textContent.includes('未指派・品保'));
  });
  await T('我的任務：部門主管有「待我指派」，成員沒有', () => {
    as('chen'); ui.page = 'mytasks'; render();
    const m = document.getElementById('main');
    ok(m.textContent.includes('待我指派（1）'), m.textContent.slice(0, 200));
    ok(m.querySelector('[data-edit="t404"]'), '有指派按鈕');
    ok(!m.textContent.includes('被指派的'), '移除部門被指派的群組');
    as('an'); render();
    ok(!document.getElementById('main').textContent.includes('待我指派'));
  });
  await T('總覽：部門負載依負責部門統計，未指派不算進人員負載', () => {
    as('yu'); ui.page = 'overview'; render();
    const m = document.getElementById('main').textContent;
    ok(m.includes('製造'), '列出所有部門'); ok(!m.includes('null'), '不應出現 null');
  });
```

- [ ] **Step 2: Run tests — 確認失敗**

Expected: FAIL（`eDept` 不存在、`addNode` 沒有部門）。

- [ ] **Step 3: `addNode()`**

在 `const id = newId('n');` 之後加入：

```js
  const pt = node(parent);
  const dpt = o.dept || (pt && pt.type === 'task' ? pt.dept : null) || (USERS[ui.me] && USERS[ui.me].dept) || 'd-rd';
  const want = o.owner !== undefined ? (o.owner || null) : ui.me;
  const own = want && USERS[want] && USERS[want].dept === dpt ? want : null;
```

`db.nodes[id] = { ... owner: o.owner || ui.me, ...` 改成 `owner: own, dept: dpt,`（其餘欄位不變）。

- [ ] **Step 4: 下拉選項與負責顯示**

在 `function userOpts(sel) {...}` 之後加入：

```js
function deptOpts(sel) { return db.departments.map((d) => `<option value="${d.id}" ${d.id === sel ? 'selected' : ''}>${esc(d.name)}</option>`).join(''); }
function ownerOpts(deptId, sel) { return '<option value="">未指派</option>' + deptMembers(deptId).map((u) => `<option value="${u}" ${u === sel ? 'selected' : ''}>${esc(USERS[u].name)}</option>`).join(''); }
// 任務的負責人顯示：已指派顯示人名與部門，未指派顯示「未指派・部門」
function whoHTML(n) { return n.owner ? `${esc(uname(n.owner))}<span class="small muted">・${esc(deptName(n.dept))}</span>` : `<span class="tag warn">未指派・${esc(deptName(n.dept))}</span>`; }
```

- [ ] **Step 5: 任務對話框**

`openEditor()` 裡這一段：

```js
    <div class="frow"><div class="field"><label for="eOwner">負責人</label><select id="eOwner" ${ed && me().role !== 'collab' ? '' : 'disabled'}>${userOpts(n.owner)}</select></div>
      <div class="field"><label for="eLevel">資料等級</label>...</select></div></div>
```

改成（`eLevel` 那個 `<div class="field">` 原樣保留，只是移到新的 frow）：

```js
    ${n.type === 'task' ? `<div class="frow"><div class="field"><label for="eDept">負責部門</label><select id="eDept" ${can('dept', n) ? '' : 'disabled'}>${deptOpts(n.dept)}</select></div>
      <div class="field"><label for="eOwner">負責人</label><select id="eOwner" ${can('assign', n) ? '' : 'disabled'}>${ownerOpts(n.dept, n.owner)}</select></div></div>
    <div class="frow">` : `<div class="frow"><div class="field"><label for="eOwner">負責人</label><select id="eOwner" ${ed && me().role !== 'collab' ? '' : 'disabled'}>${userOpts(n.owner)}</select></div>`}
      <div class="field"><label for="eLevel">資料等級</label>...（原樣）</div></div>
```

change 事件（`if (t.id === 'cascadeChk')` 之前）加入：

```js
  if (t.id === 'eDept') { const cur = $('eOwner').value; $('eOwner').innerHTML = ownerOpts(t.value, deptMembers(t.value).includes(cur) ? cur : ''); return; }
```

`saveEditor()`：在 `const status = v('eStatus');` 之後加入：

```js
  const isTask = n.type === 'task';
  const newDept = isTask ? v('eDept') : null;
  if (isTask && !dept(newDept)) return toast('請選擇負責部門', 'warn');
  let newOwner = isTask ? (v('eOwner') || null) : v('eOwner');
  if (isTask && newOwner && (!USERS[newOwner] || USERS[newOwner].dept !== newDept)) { newOwner = null; toast('負責人不屬於所選部門，已改為未指派', 'warn'); }
```

`Object.assign(n, { title, tag: v('eTag'), owner: v('eOwner'), ...` 改成 `Object.assign(n, { title, tag: v('eTag'), owner: newOwner, ...`，並在同一個 `commit` 內 `Object.assign` 之後加 `if (isTask) n.dept = newDept;`。
稽核文字 `負責人改為 ${uname(n.owner)}（已通知）` → `負責人改為 ${n.owner ? uname(n.owner) : '未指派'}（已通知）`，並在其後加上 `${isTask && oldDept !== n.dept ? `，負責部門改為 ${deptName(n.dept)}` : ''}`；`const oldS = n.start, oldE = n.end, oldOwner = n.owner;` 改為 `const oldS = n.start, oldE = n.end, oldOwner = n.owner, oldDept = n.dept;`。

- [ ] **Step 6: 快速新增**

`openQuickAdd()`：在 `const p = node(parent);` 之後加 `const qaDept = (p.type === 'task' && p.dept) || (USERS[ui.me] && USERS[ui.me].dept) || 'd-rd';`，`qWho` 的 `${userOpts(me().role === 'collab' ? ui.me : opt.owner || p.owner || ui.me)}` 改為 `${ownerOpts(qaDept, me().role === 'collab' ? ui.me : opt.owner || p.owner || ui.me)}`，標籤 `負責人` 改為 `` 負責人（${esc(deptName(qaDept))}） ``。
qaForm 送出：`owner = $('qWho').value` 改為 `owner = $('qWho').value || null`。

- [ ] **Step 7: 看板卡片與任務頁標題**

`cardHTML()`：`<span class="who">${av(c.owner, 22)}${esc(uname(c.owner))}${c.collabs.length ? ...` 改為 `<span class="who">${c.owner ? av(c.owner, 22) : ''}${whoHTML(c)}${c.collabs.length ? ...`（其餘不變）。
`pageNode()` meta：`` `<span>負責人：${esc(uname(n.owner))}</span>` `` 改為 `` n.type === 'task' ? `<span>負責：${whoHTML(n)}</span>` : `<span>負責人：${esc(uname(n.owner))}</span>` ``。

- [ ] **Step 8: 我的任務**

`pageMyTasks()` 的 `groups` 改為：

```js
  const heads = db.departments.filter((d) => d.head === u.id).map((d) => d.id);
  const groups = [
    ...(heads.length ? [['待我指派', all.filter((n) => n.owner === null && heads.includes(n.dept)), true]] : []),
    ['我負責的', all.filter((n) => n.owner === u.id)],
    ['我協作的', all.filter((n) => n.owner !== u.id && n.collabs.includes(u.id))],
  ];
```

`row` 改為接受第二個參數 `assign`，在最後一欄之後加：`${assign ? `<td><button class="btn sm" type="button" data-edit="${n.id}">指派</button></td>` : ''}`。表頭：`<th>期間</th>` 之後加 `${assign ? '<th></th>' : ''}`。`groups.map(([t, list]) => ...` 改為 `groups.map(([t, list, assign]) => ...`，`.map(row)` 改為 `.map((n) => row(n, assign))`。
說明文字 `（含我負責、我協作、部門被指派）` 改為 `（含我負責、我協作${heads.length ? '、待我指派' : ''}）`。

- [ ] **Step 9: 總覽部門負載**

`pageOverview()` 的部門負載：

```js
  const deptLoad = db.departments.map((d) => [d.name, open.filter((x) => x.dept === d.id).length]);
```

取代 Task 1 改過的 `const deptLoad = {}; open.forEach(...)` 兩行；顯示處 `${Object.entries(deptLoad).sort(...)` 改為 `${deptLoad.slice().sort((a, b) => b[1] - a[1]).map(([d, c]) => ...)`（迴圈內容不變）。

- [ ] **Step 10: Run tests**

Expected: PASS。

- [ ] **Step 11: Commit**

```bash
git add projectflow-full-demo.html tests/departments.test.js
git commit -m "Departments task 5: owner department and optional owner in editor, board, my tasks, overview"
```

---

### Task 6: 時間軸預設收合與部門篩選

**Files:**
- Modify: `projectflow-full-demo.html`：CSS（`.tl-row.tlh` 附近）、`ui` 初始值（:622）、`resetAll()`（:975）、`tlOpen()`（:1450）、`tlRows()`（:1451-1460）、`viewTimeline()`（:1498-1520）、`drawArrows()`（:1567-1570）、click 事件（`ds.tlDept`）
- Test: `tests/departments.test.js`

**Interfaces:**
- Consumes: `visible`（Task 2）、`deptName`（Task 1）
- Produces:
  - `ui.tlDept: 'all' | string`
  - `tlDeptMatch(x): boolean`
  - `tlCount(x): number`（階段列顯示的件數）

- [ ] **Step 1: 寫失敗測試**

```js
  // ── Task 6：時間軸收合與部門篩選 ──
  const tlRowIds = () => [...document.querySelectorAll('#tl .tl-row[data-row]')].map((r) => r.dataset.row);
  await T('時間軸：專案預設只顯示階段列', () => {
    as('yu'); ui.page = 'node'; ui.node = 'p1'; ui.tab = 'timeline'; render();
    eq(tlRowIds(), ['p1a', 'p1b', 'p1c', 'p1d', 'p1e']);
  });
  await T('時間軸：點階段展開，可同時展開多個', () => {
    ui.page = 'node'; ui.node = 'p1'; ui.tab = 'timeline'; render();
    document.querySelector('[data-twist="p1c"]').click();
    document.querySelector('[data-twist="p1d"]').click();
    const ids = tlRowIds();
    ok(ids.includes('t301') && ids.includes('t401'), ids.join(','));
    ok(!ids.includes('t101'), '未展開的階段不顯示工作');
  });
  await T('時間軸：部門篩選只影響工作列，階段列保持完整', () => {
    ui.page = 'node'; ui.node = 'p1'; ui.tab = 'timeline';
    ['p1a', 'p1b', 'p1c', 'p1d', 'p1e'].forEach((p) => { ui.expanded['t' + p] = true; });
    render();
    document.querySelector('[data-tl-dept="d-qa"]').click();
    const ids = tlRowIds();
    ['p1a', 'p1b', 'p1c', 'p1d', 'p1e'].forEach((p) => ok(ids.includes(p), '階段列 ' + p));
    const tasks = ids.map(node).filter((x) => x.type === 'task');
    ok(tasks.length > 0, '應有品保的工作');
    ok(tasks.every((x) => x.dept === 'd-qa' || descendants(x.id).some((d) => d.dept === 'd-qa')), tasks.map((x) => x.id).join(','));
    ok(ids.includes('t404'), '品保的未指派工作（專案負責人看得到）');
    ok(!ids.includes('t102'), '研發的工作（沒有品保子任務）被篩掉');
    ok(document.querySelector('[data-tl-dept="d-qa"][aria-pressed="true"]'));
  });
  await T('時間軸：篩選後作為路徑的上層任務以淡色顯示', () => {
    ui.page = 'node'; ui.node = 'p1'; ui.tab = 'timeline'; ui.expanded.tp1c = true; ui.expanded.tt301 = true; ui.expanded.tt3012 = true; ui.tlDept = 'd-qa'; render();
    ok(document.querySelector('#tl .tl-row.dim[data-row="t301"]'), 't301 是製程的任務，因子任務 t30122 屬於品保而以淡色路徑出現');
    ok(!document.querySelector('#tl .tl-row.dim[data-row="t30122"]'), '符合篩選的任務不淡化');
  });
  await T('時間軸：沒有階段的專案不收合，篩選直接套用', () => {
    ui.page = 'node'; ui.node = 'p4'; ui.tab = 'timeline'; ui.tlDept = 'd-pur'; render();
    const ids = tlRowIds();
    ok(ids.includes('t801') && ids.includes('t802'), ids.join(','));
    ui.tlDept = 'd-fin'; render();
    eq(tlRowIds(), []);
  });
  await T('時間軸篩選狀態不寫入資料、不進復原紀錄', () => {
    const before = undoStack.length;
    ui.page = 'node'; ui.node = 'p1'; ui.tab = 'timeline'; render();
    document.querySelector('[data-tl-dept="d-qa"]').click();
    eq(undoStack.length, before); ok(!('tlDept' in db));
  });
```

- [ ] **Step 2: Run tests — 確認失敗**

Expected: FAIL（階段預設展開、沒有 `data-tl-dept`）。

- [ ] **Step 3: 狀態與收合**

1. `const ui = { ... gsel: null };` 改為 `... gsel: null, tlDept: 'all' };`
2. `resetAll()` 的 `Object.assign(ui, { page: 'node', node: 'p1', tab: 'board', chat: [], expanded: {}, redteam: '' });` 加上 `tlDept: 'all'`。
3. `tlOpen()` 改為（專案總覽圖中，階段預設收合；其他上層節點維持原本的預設展開）：

```js
// 總覽圖（專案層）的階段預設收合；沒有階段的專案，第一層任務預設展開；個別任務展開圖只列出自己與下一層
function tlOpen(x) { const k = ui.expanded['t' + x.id]; if (k !== undefined) return k; const n = node(ui.node); return n.type === 'project' && x.parent === n.id && x.type !== 'phase'; }
```

- [ ] **Step 4: 篩選**

在 `function tlRows(n) {` 之前加入：

```js
// 部門篩選：只看負責部門；子任務符合時上層任務留著當路徑；階段與專案不受影響
function tlDeptMatch(x) { return ui.tlDept === 'all' || x.type !== 'task' || x.dept === ui.tlDept || descendants(x.id).some((d) => d.type === 'task' && d.dept === ui.tlDept); }
function tlCount(x) { return descendants(x.id).filter((d) => d.type === 'task' && visible(d) && (ui.tlDept === 'all' || d.dept === ui.tlDept)).length; }
```

`tlRows()` 的 `kids(x.id).filter(visible)`（Task 2 已由 `shown` 改名）改為 `kids(x.id).filter((c) => visible(c) && tlDeptMatch(c))`。

- [ ] **Step 5: 畫面**

1. CSS（`.tl-row.tlh{...}` 之後）加入：

```css
.deptbar{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 10px}
.deptbar button{height:30px;padding:0 10px;border:1px solid var(--line2);border-radius:15px;background:#fff;font-size:13px}
.deptbar button[aria-pressed="true"]{background:var(--teal);border-color:var(--teal);color:#fff}
.deptbar button.zero{opacity:.5}
.tl-row.dim .tl-label .nm,.tl-row.dim .gb{opacity:.45}
.tl-label .cnt{margin-left:6px;font-size:12px;color:var(--muted);white-space:nowrap}
```

2. `viewTimeline()`：`let html = \`<div class="tl" id="tl">...` 之前加入篩選列，並讓 `html` 從它開始：

```js
  const pool = descendants(n.id).filter((d) => d.type === 'task' && visible(d));
  const cnt = (id) => (id === 'all' ? pool.length : pool.filter((d) => d.dept === id).length);
  const bar = `<div class="deptbar" role="group" aria-label="依負責部門篩選工作">${[['all', '全部'], ...db.departments.map((d) => [d.id, d.name])].map(([id, nm]) => `<button type="button" data-tl-dept="${id}" aria-pressed="${ui.tlDept === id}" class="${cnt(id) ? '' : 'zero'}">${esc(nm)} ${cnt(id)}</button>`).join('')}</div>`;
```

   `let html = \`<div class="tl" id="tl">` 改為 `let html = bar + \`<div class="tl" id="tl">`。
3. 每一列：`html += \`<div class="tl-row ${hasK ? 'parent' : ''} ${self ? 'self' : ''}" data-row="${x.id}">` 改為：

```js
    const dim = ui.tlDept !== 'all' && x.type === 'task' && x.dept !== ui.tlDept;
    html += `<div class="tl-row ${hasK ? 'parent' : ''} ${self ? 'self' : ''} ${dim ? 'dim' : ''}" data-row="${x.id}"><div class="tl-label" style="padding-left:${8 + lvl * 16}px">
```

   （`const dim` 放在 `rows.forEach` 迴圈內、`html +=` 之前；原本 `<div class="tl-label" ...>` 那段保留。）
4. 階段列顯示件數：在名稱按鈕 `...${esc(x.title)}</button>\`}` 之後加入 `${x.type === 'phase' ? `<span class="cnt">${open ? '▾' : '▸'} ${tlCount(x)} 件</span>` : ''}`。
5. `hasK` 對階段也要成立才能展開：階段只要有子節點就有展開鈕（原邏輯已是 `kids(x.id).length > 0`，不需改）。

- [ ] **Step 6: 箭頭與點擊**

`drawArrows()` 的 `if (d.cond || !node(d.from) || !node(d.to)) return;` 之後加入：

```js
    if (ui.tlDept !== 'all' && (!tlDeptMatch(node(d.from)) || !tlDeptMatch(node(d.to)))) return;
```

click 事件（`if (ds.twist) ...` 之前）加入：

```js
  if (ds.tlDept) { ui.tlDept = ds.tlDept; return render(); }
```

- [ ] **Step 7: Run tests**

Expected: PASS。另用 Browser pane 開 `http://localhost:8000/projectflow-full-demo.html`，在「時程」分頁點幾個部門與階段，截圖確認版面正常（篩選列換行、淡色路徑、箭頭）。

- [ ] **Step 8: Commit**

```bash
git add projectflow-full-demo.html tests/departments.test.js
git commit -m "Departments task 6: timeline collapses to phases with department filter"
```

---

### Task 7: 範本帶負責部門、README

**Files:**
- Modify: `projectflow-full-demo.html`：`PHASE_TEMPLATE`（:425-431）、AI 任務拆解（:2218）、`nodeToTemplate()`（:2557）、`applyTemplate()`（:2573）、建立新專案（:2688-2700）、模板庫預覽（:1950）
- Modify: `README.md`
- Test: `tests/departments.test.js`

**Interfaces:**
- Consumes: `TAG_DEPT`、`deptName`（Task 1）；`addNode` 的 `dept`／`owner`（Task 5）
- Produces:
  - `PHASE_TEMPLATE[i][3]`：`[title, deptId][]`
  - `applyTemplate()` 建立的任務帶 `dept`；未勾「預設負責人」時 `owner: null`

- [ ] **Step 1: 寫失敗測試**

```js
  // ── Task 7：範本 ──
  await T('套用模板：任務帶負責部門；未勾預設負責人時全部未指派', () => {
    as('yu');
    const t = db.templates.find((x) => x.id === 'tp1');
    const res = commit('套用', () => applyTemplate(t, 'p1d', { start: '2026-10-01', vars: { 產品名: 'X' }, structure: true, deps: true, owners: false, dates: true, docs: false }));
    const made = [node(res.root), ...descendants(res.root)];
    ok(made.every((x) => x.owner === null), '全部未指派');
    eq(node(res.root).dept, 'd-qa');
    eq(made.find((x) => x.title === '選定檢驗單位並詢價').dept, 'd-pur');
  });
  await T('另存為模板會帶入負責部門', () => {
    const t = nodeToTemplate('t301');
    eq(t.nodes[0].dept, 'd-pe'); ok(t.nodes.every((x) => x.dept));
  });
  await T('依範本建立專案：任務依範本帶部門且未指派', () => {
    eq(PHASE_TEMPLATE[2][3][0], ['殺菌條件驗證（F0 值）', 'd-pe']);
  });
  await T('模板庫預覽顯示負責部門', () => {
    ui.page = 'templates'; render();
    ok(document.getElementById('main').textContent.includes('採購負責'));
  });
```

- [ ] **Step 2: Run tests — 確認失敗**

- [ ] **Step 3: `PHASE_TEMPLATE`**

```js
const PHASE_TEMPLATE = [
  ['市場與配方', '配方定案；主要原料至少 1 家供應商通過', '研發主管', [['競品分析與產品定位', 'd-sales'], ['營養標準比對', 'd-rd'], ['配方設計', 'd-rd'], ['供應商評估', 'd-pur']]],
  ['小量試作', '試作品經內部審核通過', '研發主管', [['小量試作', 'd-rd'], ['質地與外觀調整', 'd-rd'], ['原料送樣確認', 'd-pur']]],
  ['殺菌與保存', 'F0 值達標；保存試驗符合預定保存期限', '品保主管', [['殺菌條件驗證（F0 值）', 'd-pe'], ['加速保存試驗', 'd-qa']]],
  ['檢驗與適口性', '檢驗報告符合宣稱；適口性達標；標示審查通過', '品保主管、法規', [['營養成分送驗', 'd-qa'], ['適口性測試（雙碗試驗）', 'd-rd'], ['包裝標示審查', 'd-qa']]],
  ['量產上市', '首批量產完成並出貨上架', '專案負責人', [['量產 SOP', 'd-pe'], ['首批量產', 'd-mfg'], ['包材與設備確認', 'd-pur'], ['通路上架', 'd-sales']]],
];
```

AI 任務拆解：`const list = [...(tpl ? tpl[3] : []), ...extra]` → `const list = [...(tpl ? tpl[3].map((x) => x[0]) : []), ...extra]`。

- [ ] **Step 4: 建立新專案**

1. `db.nodes[pid] = { id: pid, parent: null, type: 'project', ...` 物件內加 `dept: null,`。
2. `tasks.forEach((t, k) => { const id = addNode(ph, { title: t, ai: true, ...` 改為 `tasks.forEach(([t, dp], k) => { const id = addNode(ph, { title: t, dept: dp, owner: null, ai: true, ...`（其餘不變）。

- [ ] **Step 5: `nodeToTemplate()` 與 `applyTemplate()`**

`nodeToTemplate()` 的 `nodes.push({ ... who: x.owner, dp: x.depts, ms: x.milestone,` 改為 `nodes.push({ ... who: x.owner, dp: x.depts, dept: x.dept || TAG_DEPT[x.tag] || 'd-rd', ms: x.milestone,`。

`applyTemplate()` 的 `map[x.k] = addNode(par, { ..., owner: opt.owners && x.who ? x.who : ui.me, depts: opt.owners ? (x.dp || []) : [], ...` 改為：

```js
    const dp = x.dept || TAG_DEPT[x.tag] || 'd-rd';
    map[x.k] = addNode(par, { title: sub(x.title), tag: x.tag, start: S(s), end: S(Math.max(s, e)), dept: dp, owner: opt.owners && x.who ? x.who : null, depts: opt.owners ? (x.dp || []) : [], milestone: !!x.ms });
```

（`addNode` 會在負責人不屬於部門時清空。）

`openApplyTpl()` 的核取方塊文字 `預設負責人 / 協作部門` 改為 `預設負責人 / 協作部門（不勾＝全部未指派，由部門主管指派）`。

- [ ] **Step 6: 模板庫預覽**

`pageTemplates()` 的預覽列 `<li>${esc(x.title)} <span class="muted">（第 ${x.off} 天起，${x.dur} 天${...dp...}）</span>` 改為：

```js
<li>${esc(x.title)} <span class="muted">（${esc(deptName(x.dept))}負責・第 ${x.off} 天起，${x.dur} 天${x.dp && x.dp.length ? '，協作：' + esc(x.dp.map(deptName).join('/')) : ''}）</span>
```

- [ ] **Step 7: README**

1. F6（協作人員與部門）段落末尾加：

```markdown
- 部門：系統管理員在「成員與權限 → 部門」維護部門與部門主管（預設 10 個：研發、製程、品保、業務、生管、採購、管理、資訊、財務、製造）。
- 每件任務有必填的「負責部門」，負責人可以先不指派。未指派的任務只有該部門主管（與專案負責人、系統管理員）看得到，由主管從部門成員中指派。
- 任務只有相關的人看得到：負責人、協作人員、負責部門與協作部門的主管、範圍內的審核人。同部門其他成員看不到。
- 可操作任務（改狀態、進度、送回報）的是負責人、部門主管、專案負責人、系統管理員；協作人員可以寫筆記。
- 時程頁預設只顯示階段，點階段展開；上方可依負責部門篩選。
```

2. Demo 功能狀態表：「我的任務」一列說明補上「部門主管有『待我指派』」；新增一列「部門設定與負責部門｜✅」。
3. 資料模型：`nodes` 表加 `dept_id`（任務的負責部門，FK departments）；`departments` 表加 `head_id`（FK users，可空）。

- [ ] **Step 8: Run tests**

Expected: PASS。

- [ ] **Step 9: Commit**

```bash
git add projectflow-full-demo.html tests/departments.test.js README.md
git commit -m "Departments task 7: templates carry owner department; README"
```

---

## 完成後

- 用 Browser pane 以 yu、chen、an、ming、it 各切換一次身分，確認看板、時程、我的任務、成員與權限頁的顯示符合 spec 第 4、5 節，並截圖。
- 依 superpowers:finishing-a-development-branch 決定合併方式。
