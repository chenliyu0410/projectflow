# 子任務置頂回報卡 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 打開子任務（葉任務）就在標題下方看到置頂回報卡，顯示目前回報狀態與下一步動作；其他分頁在卡片下面。

**Architecture:** 全部改在 `projectflow-full-demo.html`。Task 1 新增純渲染函式 `reportCardHTML(n)`（加上共用的 `reportFieldsHTML(r)` 與 CSS），不接到畫面上；Task 2 把卡片接進 `pageNode()`，調整葉任務頁的分頁順序、「＋ 新增子任務」位置、「紀錄」分頁內容與 `enter()` 的預設分頁，並更新 README。只改畫面，不改回報／跳過的資料邏輯。

**Tech Stack:** 原生 HTML/CSS/JavaScript（單檔 Demo）、瀏覽器測試頁 `tests/records.html`、Python `http.server`（只用來在本機提供測試頁）。

**Spec:** `docs/superpowers/specs/2026-10-01-subtask-report-card-design.md`

## Global Constraints

- 只修改 `projectflow-full-demo.html`、`tests/records.test.js`、`README.md`。不引入外部函式庫或 CDN。
- 介面文字一律繁體中文，語氣與既有 Demo 一致。
- 只套用在葉任務：`n.type === 'task' && isLeaf(n)`。專案、階段、上層任務的任務頁不能有任何變化。
- 不修改 `submitReport`、`decideReport`、`skipTask`、`restoreTask` 等核心邏輯與資料結構；`db.v` 維持 3。
- 卡片按鈕沿用既有事件屬性：`data-report`、`data-rep-approve`、`data-rep-reject`、`data-restore`，不新增事件處理。
- 權限一律使用既有的 `can(action, node)`、`canReport(n)`；沒有權限只顯示內容、不顯示按鈕。
- 輸出到 HTML 的使用者文字一律經過既有的 `esc()`。
- 這是 git repo：每個 Task 測試全部通過後提交，commit message 結尾加上一行 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`。

## 檔案結構

| 檔案 | 責任 |
|---|---|
| `projectflow-full-demo.html` | CSS（`.rcard`）、`reportFieldsHTML`、`reportCardHTML`、`pageNode()`、`viewRecords()`、`enter()` |
| `tests/records.test.js` | 新測試，加在檔案最後的 `// ── 新測試加在這一行上面 ──` 註解上方 |
| `README.md` | F11 段落「位置」列補充置頂回報卡 |

## 如何執行測試（每個 Task 都用）

1. 在專案根目錄啟動伺服器（若 8000 埠已有伺服器就直接用）：
   ```bash
   python -m http.server 8000
   ```
2. 開啟 `http://localhost:8000/tests/records.html?t=<時間戳>`（Browser pane 的 navigate；加時間戳避免快取）。
3. 讀取 `#sum` 文字（例如 javascript_tool 執行 `document.getElementById('sum').textContent`），失敗訊息在 `#out`。目前基準：`全部通過 44/44`。
4. 測試頁的 iframe 可能載入快取的 Demo：修改後若結果沒變，在測試頁執行 `document.getElementById('app').contentWindow.location.reload(true)` 後重新整理測試頁。

測試輔助函式（已存在於 `tests/records.test.js`）：`T(name, fn)` 每個測試前執行 `resetAll()` 並切到 `'yu'`；`eq(a, b, msg)`、`ok(v, msg)`、`as(userId)`；常數 `good = { result: 'met', summary: '參數設定完成', finished_on: '2026-09-30', values: {} }`。

範例資料（種子）：
- `t30121`「設備參數設定」：葉任務、負責人 `ming`、狀態 `doing`、沒有自訂欄位、沒有前置阻擋。
- `t3013`「第 2 次 F0 測試」：葉任務、有必填自訂欄位「F0 值」（key `f0`）。
- `t3011`：已完成，有已核准回報（F0 值 2.6）。
- `t3012`：`t30121` 的上層任務（非葉）。
- 使用者：`yu` 專案負責人（可確認）、`ming` 成員、`lin` 協作人員、`chen` 範圍內審核人。

---

### Task 1: 回報卡渲染函式 `reportCardHTML`

**Files:**
- Modify: `projectflow-full-demo.html`（CSS 的 `.rec .body{...}` 之後；`function reportHTML(r, src)` 處）
- Test: `tests/records.test.js`

**Interfaces:**
- Consumes（既有）：`pendingReport(nodeId)`、`canReport(n)`、`can(action, n)`、`approversFor(n)`、`uname(id)`、`fieldDefs(nodeId)`、`skipInfo(n)`、`esc(s)`、`RESULT`、`db.reports`
- Produces：
  - `reportFieldsHTML(r): string` — 回報自訂欄位的 `<dl class="kv">`，沒有欄位時回傳 `''`
  - `reportCardHTML(n): string` — 回傳 `<section class="panel rcard ...">` 的 HTML 字串；狀態色 class：`pend`（待確認）、`rej`（已退回）、`skip`（已跳過），其他狀態沒有額外 class

- [ ] **Step 1: 寫失敗的測試**

在 `tests/records.test.js` 的 `// ── 新測試加在這一行上面 ──` 上方加入：

```js
  // ── 子任務置頂回報卡：reportCardHTML ──
  const card = (id) => { const d = document.createElement('div'); d.innerHTML = reportCardHTML(node(id)); return d; };
  await T('回報卡：待辦／進行中顯示需填欄位、確認人與「回報完成」', () => {
    as('ming');
    const c = card('t3013');
    ok(c.textContent.includes('完成回報'), '標題');
    ok(c.textContent.includes('F0 值'), '應列出必填自訂欄位');
    ok(c.textContent.includes('力瑜'), '應列出確認人');
    const c2 = card('t30121');
    ok(c2.querySelector('[data-report="t30121"]'), '可回報時應有「回報完成」');
  });
  await T('回報卡：待確認時成員看到等待，主管看到確認／退回', async () => {
    as('ming'); await submitReport('t30121', good);
    let c = card('t30121');
    ok(c.querySelector('.rcard.pend'), '待確認色');
    ok(c.textContent.includes('v1 等待確認') && c.textContent.includes('參數設定完成'));
    ok(c.textContent.includes('等待') && !c.querySelector('[data-rep-approve]'), '成員不能確認');
    as('yu'); c = card('t30121');
    const id = pendingReport('t30121').id;
    ok(c.querySelector(`[data-rep-approve="${id}"]`) && c.querySelector(`[data-rep-reject="${id}"]`), '主管有確認與退回');
  });
  await T('回報卡：已退回顯示意見與「重新回報」', async () => {
    as('ming'); await submitReport('t30121', good);
    as('yu'); decideReport(pendingReport('t30121').id, false, '溫度紀錄不完整');
    as('ming'); const c = card('t30121');
    ok(c.querySelector('.rcard.rej'), '退回色');
    ok(c.textContent.includes('溫度紀錄不完整'), '應顯示退回意見');
    ok(c.querySelector('[data-report="t30121"]') && c.textContent.includes('重新回報'));
  });
  await T('回報卡：已完成有回報顯示自訂欄位；沒有回報顯示未附回報', () => {
    const c = card('t3011');
    ok(c.textContent.includes('已完成') && c.textContent.includes('F0 值') && c.textContent.includes('2.6'));
    ok(!c.querySelector('button'), '已完成沒有按鈕');
    node('t30121').status = 'done';
    ok(card('t30121').textContent.includes('已完成，未附回報'));
  });
  await T('回報卡：已跳過顯示理由，主管有「恢復任務」', () => {
    skipTask('t30121', '改由外包處理');
    const c = card('t30121');
    ok(c.querySelector('.rcard.skip') && c.textContent.includes('改由外包處理'));
    ok(c.querySelector('[data-restore="t30121"]'), '主管可恢復');
    as('ming'); ok(!card('t30121').querySelector('[data-restore]'), '成員不能恢復');
  });
  await T('回報卡：協作人員沒有任何動作按鈕', async () => {
    as('lin'); ok(!card('t30121').querySelector('button'), '待辦時沒有按鈕');
    as('ming'); await submitReport('t30121', good);
    as('lin'); ok(!card('t30121').querySelector('button'), '待確認時沒有按鈕');
  });
  await T('回報卡：使用者文字經過 esc()', async () => {
    as('ming'); await submitReport('t30121', { ...good, summary: '<b>粗體</b>' });
    const c = card('t30121');
    ok(!c.querySelector('.rcard b') && c.textContent.includes('<b>粗體</b>'), '摘要不能變成 HTML');
  });
```

- [ ] **Step 2: 執行測試確認失敗**

依「如何執行測試」開啟測試頁。
Expected：`失敗 7/51`，錯誤訊息含 `reportCardHTML is not defined`。

- [ ] **Step 3: 新增 CSS**

在 `projectflow-full-demo.html` 的 `.rec .body{margin-top:6px;white-space:pre-wrap;line-height:1.7}` 這一行之後加入：

```css
.rcard{border:2px solid var(--teal);margin:14px 0 6px}
.rcard.pend{border-color:var(--blue)}
.rcard.rej{border-color:var(--orange)}
.rcard.skip{border-color:var(--gray)}
.rcard .rc-row{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap}
.rcard .rc-main{min-width:0;flex:1}
.rcard h3{margin:0}
.rcard .rc-sum{margin-top:6px;white-space:pre-wrap;line-height:1.7}
.rcard .rc-acts{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
```

- [ ] **Step 4: 抽出 `reportFieldsHTML`，讓 `reportHTML` 使用它**

在 `function reportHTML(r, src) {` 正上方加入：

```js
function reportFieldsHTML(r) {
  return r.fields.length ? `<dl class="kv" style="margin-top:6px">${r.fields.map((f) => `<dt>${esc(f.label)}</dt><dd>${f.value === null ? '—' : esc(f.value)}${f.unit ? ' ' + esc(f.unit) : ''}</dd>`).join('')}</dl>` : '';
}
```

並把 `reportHTML` 裡這一行：

```js
    ${r.fields.length ? `<dl class="kv" style="margin-top:6px">${r.fields.map((f) => `<dt>${esc(f.label)}</dt><dd>${f.value === null ? '—' : esc(f.value)}${f.unit ? ' ' + esc(f.unit) : ''}</dd>`).join('')}</dl>` : ''}
```

改成：

```js
    ${reportFieldsHTML(r)}
```

- [ ] **Step 5: 新增 `reportCardHTML`**

緊接在 `reportHTML` 函式結束的 `}` 之後加入：

```js
// 子任務置頂回報卡：目前回報狀態與下一步動作（只用在葉任務頁）
function reportCardHTML(n) {
  const reps = db.reports.filter((r) => r.node_id === n.id).sort((a, b) => b.version - a.version);
  const latest = reps[0];
  const pend = pendingReport(n.id);
  const appr = reps.find((r) => r.status === 'approved');
  const who = esc(approversFor(n).map(uname).join('、'));
  const sum = (r) => `<div class="rc-sum"><span class="tag gray">${RESULT[r.result]}</span> ${esc(r.summary)}</div>${reportFieldsHTML(r)}`;
  let tone = '', title, body = '', acts = '';
  if (n.status === 'skipped') {
    tone = 'skip'; title = '⤳ 已跳過';
    body = `<div class="small muted" style="margin-top:4px">${esc(skipInfo(n)).replace(/\n/g, '　')}</div>`;
    if (can('override', n)) acts = `<button class="btn" type="button" data-restore="${n.id}">恢復任務</button>`;
  } else if (pend) {
    tone = 'pend'; title = `v${pend.version} 等待確認`;
    body = sum(pend) + `<div class="small muted" style="margin-top:6px">${esc(uname(pend.submitted_by))} 送出・${esc(pend.submitted_at)}</div>`;
    acts = can('override', n)
      ? `<button class="btn primary" type="button" data-rep-approve="${pend.id}">確認完成</button><button class="btn danger" type="button" data-rep-reject="${pend.id}">退回</button>`
      : `<span class="small muted">等待 ${who} 確認</span>`;
  } else if (n.status === 'done' && appr) {
    title = '✓ 已完成';
    body = sum(appr) + `<div class="small muted" style="margin-top:6px">${appr.self_approved ? '自行確認' : '確認'}：${esc(uname(appr.reviewed_by))} ${esc(appr.reviewed_at)}</div>`;
  } else if (n.status === 'done') {
    title = '✓ 已完成，未附回報';
  } else if (latest && latest.status === 'rejected') {
    tone = 'rej'; title = `v${latest.version} 已退回`;
    body = `<div class="note warn" style="margin-top:6px">退回意見：${esc(latest.review_comment)}（${esc(uname(latest.reviewed_by))}）</div>`;
    if (canReport(n)) acts = `<button class="btn primary" type="button" data-report="${n.id}">重新回報</button>`;
  } else {
    title = '完成回報';
    const req = ['結果', '成果說明', '實際完成日', ...fieldDefs(n.id).filter((f) => f.required).map((f) => f.label)];
    body = `<div class="small muted" style="margin-top:4px">需填：${esc(req.join('、'))}・送出後由 ${who} 確認</div>`;
    if (canReport(n)) acts = `<button class="btn primary" type="button" data-report="${n.id}">回報完成</button>`;
  }
  return `<section class="panel rcard ${tone}" aria-label="完成回報"><div class="rc-row"><div class="rc-main"><h3>${title}</h3>${body}</div>${acts ? `<div class="rc-acts">${acts}</div>` : ''}</div></section>`;
}
```

- [ ] **Step 6: 執行測試確認通過**

Expected：`全部通過 51/51`。

- [ ] **Step 7: Commit**

```bash
git add projectflow-full-demo.html tests/records.test.js
git commit -m "Subtask report card: reportCardHTML renderer and styles

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: 把回報卡接進葉任務頁；分頁、新增子任務按鈕、紀錄分頁、預設分頁、README

**Files:**
- Modify: `projectflow-full-demo.html`（`function pageNode()`、`function viewRecords(n)`、`function enter(id)`）
- Modify: `README.md`（`### F11 任務紀錄與完成回報` 表格的「位置」列）
- Test: `tests/records.test.js`

**Interfaces:**
- Consumes：Task 1 的 `reportCardHTML(n): string`（`.rcard` section）
- Produces：葉任務頁渲染結果（`#main` 內：`.rcard` 在 `.toolbar` 之前、第一個分頁是 `data-tab="records"`、`.tools` 內有 `data-add-child` 次要按鈕）；`enter(id)` 依節點類型設定 `ui.tab`

- [ ] **Step 1: 寫失敗的測試**

在 `tests/records.test.js` 的 `// ── 新測試加在這一行上面 ──` 上方加入：

```js
  // ── 子任務置頂回報卡：任務頁整合 ──
  const page = (id) => { ui.page = 'node'; ui.node = id; render(); return document.getElementById('main'); };
  await T('葉任務頁：回報卡在分頁列上方，紀錄是第一個分頁', () => {
    as('ming'); ui.tab = 'board'; const m = page('t30121');
    const c = m.querySelector('.rcard'), bar = m.querySelector('.toolbar');
    ok(c && bar, '應有回報卡與分頁列');
    ok(c.compareDocumentPosition(bar) & Node.DOCUMENT_POSITION_FOLLOWING, '回報卡在分頁列之前');
    eq(m.querySelector('.tabs .tab').dataset.tab, 'records');
    ok(m.querySelector('.rcard'), '切到其他分頁仍顯示回報卡');
  });
  await T('葉任務頁：新增子任務改成分頁列右側的次要按鈕', () => {
    as('yu'); ui.tab = 'board'; const m = page('t30121');
    ok(!m.querySelector('.head-actions [data-add-child]'), '標題區不再有新增子任務');
    const b = m.querySelector('.tools [data-add-child="t30121"]');
    ok(b && !b.classList.contains('primary') && b.classList.contains('sm'), '分頁列右側次要按鈕');
  });
  await T('非葉節點的任務頁不變', () => {
    as('yu'); ui.tab = 'board'; const m = page('t3012');
    ok(!m.querySelector('.rcard'), '上層任務沒有回報卡');
    ok(m.querySelector('.head-actions .btn.primary[data-add-child="t3012"]'), '標題區仍有主要按鈕');
    eq(m.querySelector('.tabs .tab').dataset.tab, 'board');
  });
  await T('葉任務的紀錄分頁只列回報歷史；確認按鈕只在回報卡', async () => {
    as('ming'); await submitReport('t30121', good);
    as('yu'); ui.tab = 'records'; const m = page('t30121');
    ok(m.querySelector('.records').textContent.includes('回報歷史（1）'));
    eq(m.querySelectorAll('[data-rep-approve]').length, 1, '確認按鈕只出現一次');
    ok(m.querySelector('.rcard [data-rep-approve]'), '確認按鈕在回報卡');
    ok(!m.querySelector('.records [data-report]'), '紀錄分頁不再有回報完成按鈕');
  });
  await T('已跳過的葉任務：提示與恢復按鈕只在回報卡', () => {
    as('yu'); skipTask('t30121', '改由外包處理'); ui.tab = 'records'; const m = page('t30121');
    eq(m.querySelectorAll('[data-restore="t30121"]').length, 1, '恢復按鈕只出現一次');
    ok(m.querySelector('.rcard [data-restore]'));
    ok(!m.querySelector('.head').textContent.includes('已跳過・'), '標題區不重複顯示跳過提示');
  });
  await T('enter()：進入葉任務預設紀錄分頁；回到上層從紀錄改回看板', () => {
    as('yu'); ui.tab = 'timeline';
    enter('t30121'); eq(ui.tab, 'records');
    enter('t3012'); eq(ui.tab, 'board');
    ui.tab = 'timeline'; enter('t301'); eq(ui.tab, 'timeline', '非紀錄分頁維持不變');
  });
```

- [ ] **Step 2: 執行測試確認失敗**

Expected：`失敗 6/57`（新增的 6 個測試失敗，其餘通過）。

- [ ] **Step 3: 修改 `pageNode()`**

在 `function pageNode()` 中做以下修改。

(a) 把：

```js
  const tabs = [['board', '看板'], ['timeline', '時程'], ['graph', '相依圖'], ['docs', '文件'], ['data', '資料'], ['people', '成員與權限'], ['records', '紀錄']];
```

改成：

```js
  const leafTask = n.type === 'task' && isLeaf(n);
  const tabs = [['board', '看板'], ['timeline', '時程'], ['graph', '相依圖'], ['docs', '文件'], ['data', '資料'], ['people', '成員與權限'], ['records', '紀錄']];
  if (leafTask) tabs.unshift(tabs.pop()); // 子任務把「紀錄」放第一個
```

(b) 把：

```js
      ${n.status === 'skipped' ? `<div class="note" style="margin-top:8px">⤳ 已跳過・${esc(skipInfo(n)).replace(/\n/g, '　')}</div>` : ''}
```

改成：

```js
      ${n.status === 'skipped' && !leafTask ? `<div class="note" style="margin-top:8px">⤳ 已跳過・${esc(skipInfo(n)).replace(/\n/g, '　')}</div>` : ''}
```

(c) 把：

```js
      ${n.status === 'skipped' && can('override', n) ? `<button class="btn" type="button" data-restore="${n.id}">恢復任務</button>` : ''}
```

改成：

```js
      ${n.status === 'skipped' && can('override', n) && !leafTask ? `<button class="btn" type="button" data-restore="${n.id}">恢復任務</button>` : ''}
```

(d) 把：

```js
      <button class="btn primary" type="button" data-add-child="${n.id}" ${can('create', n) ? '' : 'disabled'}>＋ 新增子任務</button>
    </div></header>`;
```

改成：

```js
      ${leafTask ? '' : `<button class="btn primary" type="button" data-add-child="${n.id}" ${can('create', n) ? '' : 'disabled'}>＋ 新增子任務</button>`}
    </div></header>`;
  if (leafTask) html += reportCardHTML(n);
```

(e) 把：

```js
    <div class="tools">${mineTool}${tools[ui.tab] || ''}</div></div>`;
```

改成：

```js
    <div class="tools">${leafTask ? `<button class="btn sm" type="button" data-add-child="${n.id}" ${can('create', n) ? '' : 'disabled'}>＋ 新增子任務</button>` : ''}${mineTool}${tools[ui.tab] || ''}</div></div>`;
```

- [ ] **Step 4: 修改 `viewRecords(n)`**

(a) 刪除這一行：

```js
  const pend = leaf ? pendingReport(n.id) : null;
```

(b) 把「完成回報」區塊的這三行：

```js
    <section class="panel"><div class="row" style="justify-content:space-between"><h3>完成回報（${reps.length}）</h3>${leaf && canReport(n) ? `<button class="btn sm primary" type="button" data-report="${n.id}">回報完成</button>` : ''}</div>
      ${leaf && n.status === 'skipped' ? '<div class="note" style="margin-top:8px">此任務已跳過，不需要完成回報。</div>' : ''}
      ${pend ? `<div class="note" style="margin-top:8px">v${pend.version} 等待確認：${esc(approversFor(n).map(uname).join('、'))}${can('override', n) ? `<div class="row" style="margin-top:8px"><button class="btn sm primary" type="button" data-rep-approve="${pend.id}">確認完成</button><button class="btn sm danger" type="button" data-rep-reject="${pend.id}">退回</button></div>` : ''}</div>` : ''}
      ${reps.map((r) => reportHTML(r, src)).join('') || '<div class="empty">還沒有完成回報。</div>'}</section>
```

改成（目前狀態與動作已移到置頂回報卡）：

```js
    <section class="panel"><h3>${leaf ? '回報歷史' : '完成回報'}（${reps.length}）</h3>
      ${reps.map((r) => reportHTML(r, src)).join('') || `<div class="empty">${leaf ? '還沒有回報紀錄。' : '還沒有完成回報。'}</div>`}</section>
```

- [ ] **Step 5: 修改 `enter(id)`**

把：

```js
function enter(id) { const n = node(id); if (!n) return; if (!can('view', n)) return toast('你沒有檢視此節點的權限', 'warn'); ui.page = 'node'; ui.node = id; ui.gsel = null; ui.connect = null; $('app').classList.remove('side-open'); render(); }
```

改成：

```js
function enter(id) {
  const n = node(id); if (!n) return; if (!can('view', n)) return toast('你沒有檢視此節點的權限', 'warn');
  // 子任務預設打開「紀錄」；回到上層時從「紀錄」改回「看板」
  if (n.type === 'task' && isLeaf(n)) ui.tab = 'records'; else if (ui.tab === 'records') ui.tab = 'board';
  ui.page = 'node'; ui.node = id; ui.gsel = null; ui.connect = null; $('app').classList.remove('side-open'); render();
}
```

- [ ] **Step 6: 執行測試確認通過**

Expected：`全部通過 57/57`。

- [ ] **Step 7: 瀏覽器實測**

開啟 `http://localhost:8000/projectflow-full-demo.html`，用 javascript_tool 執行 `resetAll()` 後：
1. 左下角切換成「阿明」，進入「設備參數設定」（`enter('t30121')`）：標題下方有「完成回報」卡與「回報完成」按鈕；第一個分頁是「紀錄」；分頁列右側有小的「＋ 新增子任務」。點「回報完成」送出回報 → 卡片變成藍框「v1 等待確認」，只顯示「等待 … 確認」。
2. 切換成「力瑜」，同一任務的卡片上有「確認完成」「退回」；按「退回」填意見 → 切回阿明，卡片變成橘框「v1 已退回」與「重新回報」。
3. 進入上層「調整殺菌時間」（`t3012`）：沒有回報卡，標題區仍是主要按鈕「＋ 新增子任務」，分頁停在「看板」。
4. 用 `resize_window` 設成 mobile（375 寬）重新整理，進入葉任務：沒有水平捲動（`document.documentElement.scrollWidth <= innerWidth`）。完成後 `resize_window` 設回 desktop。
5. `read_console_messages`（onlyErrors）沒有錯誤。

- [ ] **Step 8: 更新 README**

在 `README.md` 的 `### F11 任務紀錄與完成回報` 表格中，把：

```markdown
| 位置 | 任務頁「紀錄」分頁；上層節點唯讀彙總整棵子樹；看板卡片有「✓ 回報」快捷按鈕 |
```

改成：

```markdown
| 位置 | 子任務頁標題下方固定顯示「回報卡」（目前狀態與下一步：回報完成／等待確認／確認或退回／重新回報／已完成摘要），打開子任務預設進入「紀錄」分頁（回報歷史、筆記、附件）；上層節點的「紀錄」分頁唯讀彙總整棵子樹；看板卡片有「✓ 回報」快捷按鈕 |
```

- [ ] **Step 9: Commit**

```bash
git add projectflow-full-demo.html tests/records.test.js README.md
git commit -m "Subtask page: pinned report card, records tab first, secondary add-child button

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
