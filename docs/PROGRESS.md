# ProjectFlow 開發進度看板

> **這份文件是開發進度的唯一依據。** 接手時先讀「▶ 現在」，收工前更新它。
> - 入口說明：[AGENTS.md](../AGENTS.md)
> - 流程與規則：[WORKFLOW.md](WORKFLOW.md)
> - 產品規格與路線圖：[README.md](../README.md)
>
> **閱讀預算**：只需要讀「▶ 現在」、§2，以及目前工作項目在 §3 的明細。其他章節用到時再查。

---

## ▶ 現在

| 欄位 | 值 |
|---|---|
| 目前工作項目 | **W1 子任務置頂回報卡**（📋 已規劃，尚未開始） |
| 下一個動作 | 照 [WORKFLOW §2 G3](WORKFLOW.md#g3-執行) 開工，依序：<br>1. 在 `main` 上做 Pre-flight 和基準測試<br>2. 把 W1 改成 🔨，共三處：本表、§2、§3 標題。另外，本表的「分支」填 `feature/w1-subtask-report-card`，「下一個動作」改成「切到該分支，照該分支的 PROGRESS 執行 Task 1」，並填寫認領<br>3. commit `Progress: start W1`<br>4. `git checkout -b feature/w1-subtask-report-card`<br>5. 執行 W1 Task 1（見 §3 W1） |
| 分支 | `main`（目前沒有進行中的 feature 分支） |
| 最新程式 commit | `aebd709`（F11 final fixes）。每個 Task 記錄時更新 |
| 行號基準 | `dfc0126`。§5「位置」欄和 §3「執行注意」的行號都以這個 commit 為準，此欄固定不改。程式改動後行號會位移，請用函式名或程式片段搜尋 |
| 測試基準 | `tests/records.html`：`全部通過 44/44`（2026-10-01 實測） |
| 資料版本 | `db.v = 3`；localStorage key 是 `projectflow-demo-v2` |
| 認領中 | （無）。開工時填「執行者／開始時間」，收工時清空 |
| 阻塞／待人類 | 無。W1 不受任何 D 阻塞 |
| 遠端 | 2026-10-01 經人類授權，已 push 到 `origin/main`，內容包括 `edf46b6`、`dfc0126` 和交接系統的 `Docs:` commit。之後的狀態用 `git log --oneline origin/main..main` 查看。每次 push 都要人類明確授權（D3） |

---

## 0. 狀態符號

| 符號 | 意義 | 進入條件 |
|---|---|---|
| ⬜ | 未開始 | 已列入佇列，只有一句目標 |
| ✏️ | 規格中 | 正在 brainstorming 或寫 spec |
| 📋 | 已規劃 | spec 和 plan 都已 commit（問題清理型只需要 plan，見 WORKFLOW G1） |
| 🔨 | 執行中 | 已開分支，正在跑 Task 迴圈 |
| 🔍 | 審查中 | 所有 Task 都完成，正在整體審查或修正 |
| 🟢 | 可合併 | 整體審查結論是 Ready to merge，等待合併 |
| ✅ | 完成 | 已合併進 `main`，README 也已更新 |
| ⛔ | 阻塞 | 要等人類決定才能繼續（寫明 D 編號） |
| ⏸ | 暫停 | 人類要求先停，分支保留（寫明恢復條件） |
| ✖ | 取消 | 人類決定不做，分支保留，spec 和 plan 標成 Superseded |

---

## 1. 目標層級

1. **北極星**：以「專案」為核心的 AI 工作流工具，涵蓋多層任務、前置條件、權限、文件、AI 副手和研發營運資料，部署在公司內網，資料不外流（見 [README](../README.md) 開頭）。
2. **兩條軌道**
   - **Demo 驗證軌（目前所在）**：在單檔 `projectflow-full-demo.html` 上逐項驗證產品互動。F1–F11 已經在 Demo 層級完成，接下來照 §2 佇列擴充。
   - **正式產品軌（還沒啟動）**：README §8 的階段 1–9，例如 Vite + React + TS、FastAPI + PostgreSQL、內網部署。
     - README §8 的勾選框只用來追蹤正式版。Demo 已經做出來的功能**不能**拿去勾階段 1–9。
     - 何時啟動由人類決定（D11）。啟動後第一個工作項目是 P0。
3. **目前里程碑**：依序完成 W1 → W2 → W3，讓 Demo 的部門和流程控制對上「10 部門流程甘特圖（連接器新產品，6 階段）」的情境。這份甘特圖的原檔目前不在 repo 裡（D13）。
4. **Demo 驗證軌的完成條件**（草案，等人類在 D11 確認）
   - [ ] W1、W2、W3 都是 ✅
   - [ ] W4：§5 OPEN 中「需人類」為「否」的 important 和 minor 全部 FIXED（trivial 可以轉到正式軌）
   - [ ] §6 的 D4–D8 都有結論，而且已經執行
   - [ ] W5 ✅：README §1、§2、§7、§8 都反映 full demo 的現況
   - [ ] 用 W3 的「連接器新產品 6 階段」示範專案，以 yu、chen、an、ming、it 各走一次，console 沒有錯誤
   - [ ] 人類確認符合 README §8 階段 0 的驗收：「能用 Demo 向他人完整說明產品概念」

   全部達成後，AI 在 §7 寫一份「Demo 軌結案摘要」（完成項目、遺留問題、建議的 P0 和 P1 範圍），並把 D11 標成「待人類（可決定）」。

---

## 2. 工作佇列（由上往下執行）

| 順位 | ID | 工作項目 | 狀態 | Spec | Plan | 資料版本 | 依賴 |
|---|---|---|---|---|---|---|---|
| 1 | W1 | 子任務置頂回報卡 | 📋 | [spec](superpowers/specs/2026-10-01-subtask-report-card-design.md)（`3a24c52`） | [plan](superpowers/plans/2026-10-01-subtask-report-card.md)（`ed3e24f`） | 維持 v3 | F11 ✅ |
| 2 | W2 | 部門模型 | 📋 | [spec](superpowers/specs/2026-10-01-department-model-design.md)（`edf46b6`，`dfc0126` 修訂 §4.1 和範本段，以 HEAD 版本為準） | [plan](superpowers/plans/2026-10-01-department-model.md)（`dfc0126`） | v3 → v4 | W1 已合併（D1） |
| 3 | W3 | 流程控制 | ⬜ 需先寫 spec | — | — | v4 → v5 | W2 已合併；D13 甘特圖到位；brainstorming 需要人類參與（D9） |
| 4 | W4 | F11 遺留問題清理 | ⬜ 需先寫小 plan（問題清理型，AI 可以自己寫，見 WORKFLOW G1 例外） | PROGRESS §5 | — | 維持 | 沒有進行中的分支時才能做。建議排在 W2 合併後，因為它會改到 `load()` 這類 W2 的錨點。如果提前做，W2 的預期測試數和錨點都要重新核對 |
| 5 | W5 | README 對齊現況 | ⬜ | — | — | — | 排在 W2 之後（W2 會改 README）。full demo 定位的文字需要人類審閱（D12） |
| — | P0 | 正式軌工作規則 | ⬜ 未啟動 | — | — | — | D11 決定後才做：和人類一起定技術骨架，改寫 AGENTS §3–§4、WORKFLOW §5、G2 的必備內容。P0 ✅ 之前不能開工 P1 |
| — | P1–P9 | 正式產品軌（README §8 階段 1–9） | ⬜ 未啟動 | README §8 | — | — | P0 ✅；階段 4 以後依賴 README §9 #5–#14 |

**排程規則**
1. 永遠做順位最前面、而且沒有阻塞的項目。
2. 同一時間只能有一個進行中的 feature 分支（WORKFLOW 鐵律 4、§6）。
3. 目前的項目在等人類決定時，用 `git branch --list "feature/*"` 判斷，不要只看狀態符號：
   - **已經有 `feature/*` 分支**：不可以開新分支，也不可以在 `main` 上 commit。只能做不會產生 commit 的準備工作（研究、把草稿放在 `.superpowers/`），或寫好交接紀錄後結束 session。
   - **還沒有分支**（例如 W3 在等 brainstorming，或開工前的 Pre-flight 就被擋下）：可以先在 `main` 上記錄 D，再去做下一個不需要人類決定的項目，例如 W4。
4. 佇列做完了，但 §1 的完成條件還沒達成：不要自己發明工作項目。在本表下方加「建議（待人類排序）」，寫好交接紀錄後結束。
5. 不可以自行開工 P 軌。
6. 人類在對話中的直接指示優先，但要先寫進看板（WORKFLOW §2「變更與暫停」）。

---

## 3. 工作項目明細

### W1 子任務置頂回報卡 — 📋

- **目標**：打開子任務（葉任務，`n.type === 'task' && isLeaf(n)`）時，標題下方固定顯示回報卡，卡上有目前狀態和下一步動作。葉任務頁的「紀錄」分頁排第一，並且是預設分頁。
- **分支**：`feature/w1-subtask-report-card`（從 `main` 切出）。
- **commit 前綴**：`Subtask report card`。
  - Task commit 的主旨照 plan 指定。
  - 修正輪用 `Subtask report card task N fix: …`。
  - 整體修正用 `Subtask report card final review fixes: …`。
- **允許修改的檔案**：`projectflow-full-demo.html`、`tests/records.test.js`、`README.md`（plan Global Constraints）。`docs/PROGRESS.md` 本來就可以改。
- **原型參考**：`.superpowers/prototype/report-card-demo.html` 是方案 B 的執行期原型，只放在本機、不提交。可以起伺服器打開來看預期效果。plan 就是從這個原型整理成正式寫法的。

| Task | 內容 | 狀態 | commits | 測試（預期 → 實際） | plan 指定的 commit 主旨 |
|---|---|---|---|---|---|
| 1 | `reportCardHTML(n)` 渲染函式、共用的 `reportFieldsHTML(r)`、`.rcard` CSS。這一步還不接到畫面上 | ⬜ | — | RED `失敗 7/51` → GREEN `全部通過 51/51` | `Subtask report card: reportCardHTML renderer and styles` |
| 2 | 把卡片接進 `pageNode()`，包括：分頁順序；`.tools` 加次要的「＋ 新增子任務」；標題區的跳過提示改由卡片顯示；`viewRecords()` 對葉任務只列回報歷史；`enter()` 預設分頁；README F11「位置」列 | ⬜ | — | RED `失敗 5/57`（plan 誤寫成 6/57）→ GREEN `全部通過 57/57` | `Subtask page: pinned report card, records tab first, secondary add-child button` |
| — | 整體審查 | ⬜ | — | — | — |

**驗收**（spec §8、plan Task 2 Step 7）
- [ ] `tests/records.html` 顯示 `全部通過 57/57`。新增的 13 個測試要涵蓋：卡片各種狀態、協作身分沒有按鈕、`enter()` 預設分頁、葉任務頁結構、非葉節點不變、`esc()` 防注入
- [ ] 瀏覽器實測阿明的流程：打開 `t30121` 直接看到「完成回報」卡；送出後卡片變成「v1 等待確認」，只顯示「等待 … 確認」
- [ ] 瀏覽器實測力瑜的流程：在同一張卡上按「確認完成」。退回路徑也要測一次（spec 寫的是確認，plan 測的是退回，兩條都要走）
- [ ] `t3012`（非葉節點）沒有回報卡，版面不變
- [ ] 375px 寬度下沒有水平捲動（用 WORKFLOW §5 第 7 點的檢查式），console 沒有錯誤
- [ ] `db.v` 仍是 3，沒有新增事件處理

**執行注意**（2026-10-01 研究結果，錨點已在 `dfc0126` 上逐一核對過）
1. Task 2 Step 2 的 RED 實際上是 `失敗 5/57`。「非葉節點不變」那個測試在改程式之前就會通過，這是正常的。
2. 工作目錄是 CRLF（`core.autocrlf=true`）。多行錨點（Step 3d 有 2 行、4b 有 4 行）要用編輯器工具替換，不要用 `sed` 或 `\n` 字串比對。
3. 375px 檢查：`.main` 設了 `overflow:hidden`，只看 `document.documentElement.scrollWidth` 會誤判通過。請用 WORKFLOW §5 第 7 點的檢查式。
4. `t3013` 的卡片會顯示「回報完成」，但它有硬性前置，送出時會被擋下。手動測試請用 `t30121`。
5. 確認人名單裡會出現「資訊室」（admin `it`）。這是 F11 原本的行為，不是錯誤。
6. 種子資料沒有 readonly 使用者，「唯讀身分沒有按鈕」只能用 `lin`（協作人員）來測。
7. 不經過 `enter()` 的導覽（刪除節點後、`pageNode` fallback、切換身分）不會設定預設分頁。spec 沒有規範這些情況，維持現狀即可。
8. Task 2 第 1 個測試（「葉任務頁：回報卡在分頁列上方，紀錄是第一個分頁」）最後一個斷言的訊息是「切到其他分頁仍顯示回報卡」。它實際上是在 `ui.tab = 'board'` 的狀態下檢查的，結果正確，照抄即可。
9. `git add` 只加 plan 指定的檔案路徑。
10. plan 的 commit 指令寫死了 `Co-Authored-By: Claude Opus 5.5`，請換成你實際使用的工具和模型（WORKFLOW §6）。
11. plan 開頭寫「REQUIRED SUB-SKILL: subagent-driven-development」，plan 內的測試段落也寫了 Claude 工具的名稱。Claude 優先用 `/pf-next`。其他 AI 照 WORKFLOW §3 和 §11 的對照表做。

### W2 部門模型 — 📋

- **目標**：
  - 部門變成可以設定的資料，存在 `db.departments`。預設 10 個部門，其中只有研發（yu）、品保（chen）、採購（hua）有預設主管，其餘 7 個沒有主管。
  - 任務必須填負責部門，負責人可以先不指派。
  - 只有相關的人看得到、能操作任務。
  - 時間軸預設收合成階段，可以依負責部門篩選。
- **分支**：`feature/w2-departments`（W1 合併後從 `main` 切出）。
- **commit 前綴**：`Departments`。每個 Task 的 commit 主旨由 plan 指定，例如 `Departments task 1: …`。
- **允許修改的檔案**：`projectflow-full-demo.html`、`tests/records.html`、`tests/records.test.js`、`README.md`，另外新增 `tests/departments.test.js`。`docs/PROGRESS.md` 本來就可以改。

| Task | 內容 | 狀態 | commits | 新測試 | 預期總數（W1 先做時） |
|---|---|---|---|---|---|
| 1 | 部門資料、v4 升級、顯示改用部門名稱 | ⬜ | — | 5 | 62 |
| 2 | 可見性：只有相關的人看得到；移除「顯示全部」 | ⬜ | — | 8 | 70 |
| 3 | 操作權限 `canWork`、指派、改部門 | ⬜ | — | 5 | 75 |
| 4 | 部門管理面板：新增、修改、刪除 | ⬜ | — | 5 | 80 |
| 5 | 任務的負責部門和負責人：對話框、看板、我的任務、總覽 | ⬜ | — | 6 | 86 |
| 6 | 時間軸預設收合，並可依部門篩選 | ⬜ | — | 6 | 92 |
| 7 | 範本帶入負責部門、更新 README | ⬜ | — | 4 | 96 |
| — | 整體審查 | ⬜ | — | — | — |

預期總數是研究時推算的，plan 本身只寫「全部通過 N/N」。以實際跑出來的數字為準。

**驗收**
- [ ] `tests/records.html` 全部通過：W1 的 13 個測試加上 departments 的 39 個測試都是綠燈
- [ ] spec §7 的第 1–10 項，每一項至少對應一個測試，在 commits 欄旁列出測試名稱
- [ ] 先按「重置 Demo 資料」，再以 yu、chen、an、ming、it 各截一次圖，確認看板、時程、我的任務、成員與權限頁都符合 spec §4、§5
- [ ] 未指派、而且所屬部門沒有主管（製程）的任務 `t504`，只有 yu 和 it 看得到
- [ ] 時間軸預設收合；`ui.tlDept = 'd-qa'` 時階段列數不變，工作列只剩品保的任務
- [ ] 舊的 v3 資料能升級成 v4（`db.v === 4`），對應正確：法規→`d-qa`、生產→`d-mfg`、行銷→`d-sales`
- [ ] README 的 F6、§2、§5 已經照 plan Task 7 Step 7 更新
- [ ] 375px 寬度下沒有水平捲動，console 沒有錯誤

**執行注意**（W1 先做的情況）
1. **唯一的程式衝突**在 Task 2 Step 4.3 的 `.tools` 那一行。W1 會在那裡加 `leafTask` 的次要按鈕，這一步**只刪掉 `${mineTool}`**，保留 W1 的按鈕。
2. W1 的 13 個測試在 W2 全程都必須通過。只要有一個失敗，就是真的回歸。
3. spec §5.4 寫的是 `ui.tlOpen`，plan 用的是既有的 `ui.expanded`，**以 plan 為準**。Task 6 要把 `tlDept` 加進 `resetAll()`，否則篩選狀態會帶到後面的測試。
4. plan:427 對三個跳過案例失敗原因的說明不正確。這三個測試在 Task 2 時仍然通過，到 Task 3 才會失敗，原因是 `skipTask` 要求 `can('edit')`，改成 `canWork` 之後 ming 就不能送出申請。照 Task 3 Step 3 修改即可。
5. 有兩處 RED 不會全紅，都是正常的：
   - Task 1：「切換身分選單顯示部門名稱」在實作前就可能通過。
   - Task 3：「修改時程：成員只能改自己負責的…」在實作前也會通過，因為現行的 schedule 規則已經限定負責人本人。所以 Task 3 的 RED 是新測試失敗 4 個。
6. Task 2 Step 4.1：只替換 `shown(` 呼叫，以及 `.filter(shown)`、`.find(shown)`，不要全域替換 `shown` 這個識別字。
   - `graphLayout` 裡的 `shown(x)` 要改成 `visible(x)`。
   - `graphLayout` 回傳物件的鍵 `shown:`，以及 `viewGraph` 裡的 `const { shown, pos }`，都保留不動。
7. README 的指示和現況不一致：
   - §2 表沒有獨立的「我的任務」列，只有「其他｜分享、總覽、我的任務、AI 收件匣｜⬜」這一列合併寫；也沒有「時間軸」列，README 用的名稱是「時程」。
   - `departments` 在資料模型裡只有一行。
   - 處理方式：**新增**需要的列，不要順手大改 §2 表，那是 W5 的範圍。
8. 瀏覽器驗收前先按「重置 Demo 資料」。舊的 v3 localStorage 升級後不會出現新的未指派示範任務。
9. Task 1 到 Task 5 之間新建立的任務沒有 `dept`。負責人本人和上層任務的負責人仍然看得到，但部門主管看不到，也不能操作。這是預期中的暫時狀態，Task 5 會在 `addNode` 補上。
10. plan 的行號有幾處差一行：
    - `applyTemplate` 寫 :2573，實際在 :2574。
    - `openEditor` 的負責人列寫 :2376-2377，實際在 :2377-2378。

    另外，Task 7 Step 4.2 的錨點 `tasks.forEach…addNode(ph…` 在原始碼裡跨 2 行，要用編輯器工具做多行替換。
11. plan:23 要求用 `superpowers:using-git-worktrees` 開 worktree，plan:1164 要求用 `finishing-a-development-branch` 決定合併方式，**這兩點一律以 D2 為準**：在主 checkout 執行 `git checkout -b feature/w2-departments`，不開 worktree；合併照 WORKFLOW G5 用 ff-only。這已經裁決過，不算 Pre-flight 衝突，不需要再問人類。
12. plan 的 Global Constraints 寫死了 Claude 的 trailer，但各 Task 的 `git commit` 指令又沒有附 trailer。一律寫你實際使用的工具和模型（WORKFLOW §6）。
13. plan「如何執行測試」那一段缺少 `?t=` 和快取處理，**以 WORKFLOW §5 為準**。

### W3 流程控制 — ⬜（需先寫 spec）

- **來源**：W2 spec 開頭的「拆分」段落，範圍有：
  1. 關卡硬性擋住後續階段
  2. 範本指定關卡的核准人
  3. 總經理角色
  4. 強制通過關卡，以及略過整個階段
  5. 完成報告必須附交付物（可能會建立在 W1 的回報卡上）
  6. 連接器範本與示範專案
  7. 資料升到 v5
- **未分配的項目**：應收帳款（「開發票、請款」目前是一般任務）、人員帳號的新增與編輯。W2 spec 把這兩項列為不在範圍內，也沒有分給第二份 spec。W3 brainstorming 時請人類確認是否仍然排除。
- **下一步**：W2 合併、D13 的甘特圖到位之後，依 WORKFLOW G1 和人類一起 brainstorming，產出 `docs/superpowers/specs/<日期>-process-control-design.md`，再寫 plan（D9）。

### W4 F11 遺留問題清理 — ⬜

- **範圍**：§5 中狀態是 OPEN、而且「需人類」為「否」的項目。依 WORKFLOW G1 的例外，直接寫 `docs/superpowers/plans/<日期>-w4-cleanup.md`。每個 issue ID 對應一個 Task，每項都要附測試。
- **建議優先處理**：
  - `F11-T1-m3`：upgrade 失敗時會靜默覆蓋使用者資料
  - `F11-N1`：回報對話框會拋例外
  - `F11-T7-m3`：spec 要求的附件快照沒有做
  - `F11-T6-m3`：已刪除節點的申請會永遠卡著
  - `F11-T5-m1`：可以重複送出
  - 補測試類：`T2-m4`、`T3-m4`、`T5-m5`、`T6-m4`、`T7-m4`
- **要等人類決定的**：`T1-m5`、`T4-m2`、`T4-m4`、`T5-m2`、`T6-m1`。這幾項等 §6 有了結論，才能排進 W4。

### W5 README 對齊現況 — ⬜

README 有幾處還停留在階段 0 或 F11 之前的內容，W2 合併後一次整理：
- §1 快速開始沒有提到 full demo 和測試頁。
- §2 功能總覽大多是 petfood Demo 的描述。像「時程（唯讀）」「文件只有標題」「總覽、我的任務未實作」都已經過時，而且缺少 F1–F10 的列。
- §2「已知限制」只適用於 petfood Demo。
- §7 專案結構缺少 `docs/`、`tests/`、`AGENTS.md`、`.claude/`。
- §8 沒有說明 full demo 和正式產品軌的關係。
- §5 `overrides` 的 `target_type` 和 `kind` 語意重疊，而且沒有記載 `restoredBy`、`restoredAt`、`note`。

full demo 定位的文字需要人類審閱（D12）。

---

## 4. 已完成

| 項目 | 內容 | 證據 |
|---|---|---|
| 階段 0 | petfood 互動 Demo（`projectflow-petfood-demo.html`） | README §8 階段 0 已打勾 ✅；早於 git 歷史，包含在 `9fdcc64` 裡 |
| F1–F10 | full demo 的多層任務樹、模板、時程編輯、前置條件與關鍵路徑、權限與覆寫、協作、文件與版本、AI 副手（規則式）、分級路由與遮罩（模擬）、研發營運資料（模擬 ERP） | 早於 git 歷史，包含在 `9fdcc64` 裡。F6 的部門目前是寫死的，由 W2 處理 |
| F11 | 任務紀錄與完成回報：回報與審核、自訂回報欄位、筆記、附件（IndexedDB）、主管跳過整個任務、AI 引用紀錄 | [spec](superpowers/specs/2026-09-30-task-records-and-skip-design.md)、[plan](superpowers/plans/2026-09-30-task-records-and-skip.md)；commits `9fdcc64..aebd709`（從 `2fc8f10` 到 `aebd709` 共 10 個：7 個 Task、2 輪修正、1 次整體修正），以 fast-forward 合併進 `main`；測試 44/44。SDD 暫存已歸檔到本機的 `.superpowers/archive/2026-09-30-f11-task-records/`（不在 git 裡；重要內容已整理到本看板 §5） |
| 規劃文件 | W1 的 spec 和 plan、W2 的 spec 和 plan | `3a24c52`、`ed3e24f`、`edf46b6`、`dfc0126` |
| 交接系統 | `AGENTS.md`、`CLAUDE.md`、`GEMINI.md`、本看板、`docs/WORKFLOW.md`、`.claude/workflows/pf-status.js`、`.claude/workflows/pf-next.js`、`.gitignore` | 2026-10-01 建立；commit 用 `git log --grep "Docs: handoff system"` 查 |

---

## 5. 待處理問題（Issue register）

- **ID 規則**：
  - F11 的項目來自 F11 的執行紀錄，2026-10-01 已經逐項在程式碼中核對過，共 39 個 ID（N2 已併入 T4-m1）。
  - 之後的工作項目用 `W1-T1-m1`（Task）或 `W1-F-m1`（整體審查）這種格式，詳見 WORKFLOW 附錄 B。
- **嚴重度**：important、minor、trivial。**大小**：S（不到 30 分鐘）、M、L。
- **處理方式**：「需人類」為「是」的項目，要等 §6 有了結論才能動手。其他項目都歸到 W4。修好後狀態改成 FIXED，並寫上 commit。

### OPEN

| ID | 描述 | 嚴重度 | 大小 | 需人類 | 位置（dfc0126） |
|---|---|---|---|---|---|
| F11-T1-m3 | `load()` 裡的 `upgrade()` 拋出例外時會被靜默吞掉，改用種子資料；下一次 `save()` 就會覆蓋使用者原本的資料。建議先把原始資料備份到另一個 key，並提示使用者 | minor（優先） | S | 否 | html:653-657 |
| F11-N1 | 回報對話框的 `f.options.map` 沒有加 `(f.options \|\| [])` 防護，options 不存在時打開對話框會拋例外（:994、:2389 都有加） | minor（優先） | S | 否 | html:2892 |
| F11-T7-m3 | spec §8 要求 AI 引用附件的檔名和所屬（不送出內容），但 `recordsSnapshot` 沒有包含附件。這是 plan 漏寫 | minor | S | 否 | html:2140-2145 |
| F11-T6-m3 | 節點刪除後，它待審的跳過申請：`decideOverride` 允許 owner 和 admin 審核，UI 卻把按鈕停用；`deleteNode` 也不會結案這些申請，結果永遠卡在待審 | minor | S | 否 | html:2500、:2340-2356 |
| F11-T5-m1 | 上傳附件期間對話框仍開著，送出按鈕也沒有停用；重複送出時會出現誤導的錯誤訊息 | minor | S | 否 | html:3125-3129 |
| F11-T4-m3 | `openAttachment` 在 `await` 之後才呼叫 `window.open`，可能被彈出視窗攔截器擋下 | minor | S | 否 | html:1174-1177 |
| F11-T7-m1 | `aiAsk` 回報分支的關鍵字太寬，而且排在時程和工作量分支之前 | minor | S | 否 | html:2256、:2150 |
| FF-c1 | 自動結案的覆寫申請把說明寫在 `note`，但 UI 不顯示，審核紀錄看起來像是人工退回 | minor | S | 否 | html:1935 |
| F11-T2-m4 | 缺少測試：送出、確認、退回時的稽核與通知內容；沒有 override 權限的人帶 `selfApprove` 送出的情況 | minor | S | 否 | tests |
| F11-T3-m4 | 缺少測試：非編輯者不能新增、移除、調整回報欄位 | minor | S | 否 | tests |
| F11-T1-m2 | IndexedDB 開啟失敗後，被 reject 的 `dbp` 會一直被快取住 | trivial | S | 否 | html:949、:957 |
| F11-T1-m4 | upgrade 的測試沒有涵蓋「v3 原樣通過」和「重複呼叫」 | trivial | S | 否 | tests:23-32 |
| F11-T2-m1 | `validateReport` 對 `finished_on` 只檢查格式，不檢查日期是否真的存在 | trivial | S | 否 | html:988 |
| F11-T2-m2 | 數字欄位用 `Number()` 驗證，`1e3`、`0x10` 也能通過 | trivial | S | 否 | html:993、:1007 |
| F11-T2-m3 | `setStatus` 的待確認防呆排在 `can('edit')` 之前，沒有權限的人看到的提示不對 | trivial | S | 否 | html:899-907 |
| F11-T2-m5 | 復原堆疊滿 60 筆時，一次回報動作會多擠掉幾筆舊紀錄 | trivial | S | 否 | html:663、:1014-1018 |
| F11-T3-m3 | `nodeToTemplate` 直接引用 `options` 陣列，沒有複製一份 | trivial | S | 否 | html:2558 |
| F11-T4-m1 | `addAttachments` 在 `await` 之後才讀 `ui.me`；`submitReport` 自行確認時也沒有檢查 `decideReport` 的回傳值（已把 N2 併入這一項） | trivial | S | 否 | html:1148-1158、:1039 |
| F11-T4-m5 | `onabort` 時用 `t.error` reject，但它可能是 null | trivial | S | 否 | html:962 |
| F11-T4-m6 | 上傳附件後按復原，IndexedDB 裡會留下孤兒 blob | trivial | M | 否 | html:964-970 |
| F11-T5-m3 | `reportHTML` 遇到未知的 status 會顯示 "undefined"。W1 會改到這個函式，建議等 W1 之後再修 | trivial | S | 否 | html:2832 |
| F11-T5-m5 | 缺少測試：回報被退回後重開對話框，應該預填上一版的內容 | trivial | S | 否 | tests |
| F11-T6-m4 | 缺少測試：退回「跳過整個任務」的申請 | trivial | S | 否 | tests |
| F11-T7-m2 | `recordsSnapshot` 在沒有 `f.unit` 時會顯示 "undefined" | trivial | S | 否 | html:2142 |
| F11-T7-m4 | Task 7 第 2 個測試沒有斷言「AI 稽核的 prompt 不含機密筆記」 | trivial | S | 否 | tests:284-290 |
| F11-T4-m4 | 附件全部上傳失敗時，`submitReport` 仍然回傳 ok；回報已經鎖定，也沒有辦法補附件 | minor | S | **是（D6）** | html:1032-1042 |
| F11-T6-m1 | 只恢復被連帶跳過的子任務時，上層任務會變成 doing，但既沒有寫稽核，也沒有 `restoredAt` | minor | M | **是（D8）** | html:1232-1240 |

### BY_DESIGN（plan 或 brief 指定的行為，要改必須先經過人類同意）

| ID | 描述 | 需人類 |
|---|---|---|
| F11-T1-m5 | 「重置 Demo 資料」不會把角色重設回 yu | 是（D4） |
| F11-T4-m2 | SVG 附件透過同源 blob URL 預覽，內嵌的 script 會在 app origin 執行。在 Demo 裡只算 self-XSS，接上伺服器後就會變成 stored XSS | 是（D5） |
| F11-T5-m2 | 送出回報時被硬性前置擋下，系統改開跳過對話框，已經輸入的回報內容全部遺失 | 是（D7） |
| F11-T5-m4 | 「N 個子任務」算的是整棵子樹，和全 app 的用語慣例一致 | 否，維持現狀 |

### 已關閉

| ID | 結果 |
|---|---|
| F11-T1-m1 | FIXED `903f333` |
| F11-T2-DI | FIXED `aebd709`（確認時用 `doneBlockers` 重新檢查硬性前置） |
| F11-T3-m1、F11-T3-m2 | FIXED `aebd709` |
| F11-T5-PMI | FIXED `aebd709`（確認按鈕會看 `decideReport` 的回傳值） |
| F11-T6-m2 | FIXED `aebd709` |
| F11-T7-m5 | FIXED `aebd709` |
| FF-c2 | NA（port 8000 的伺服器沒關是環境狀態，相關規則已寫進 WORKFLOW §5） |

---

## 6. 待人類決定（Decision register）

- 這些事項 AI 不可以自己決定。有預設值的，在人類推翻之前照預設執行。
- 「來源」欄記錄這個 D 是哪個工作項目或 Task 產生的。整體審查和合併只看「來源」是本工作項目的 D。
- **人類回答後**，照下面的方式記錄：
  1. 狀態改成「已決定 YYYY-MM-DD：<一句結論，盡量用人類的原話>」。推翻預設時也一樣。
  2. 把連動的 §5 條目的「需人類」改成「否（Dn）」，排進對應的工作項目。
  3. 移除因這個 D 而標的 ⛔（「▶ 現在」、§2、§3、Task 列都要檢查），清空「阻塞／待人類」，把結論寫進該工作項目的「執行注意」，並把「下一個動作」改回原本的步驟。
  4. commit `Progress: record Dn`。如果有 `feature/*` 分支，就 commit 在那個分支上。

| ID | 來源 | 問題 | 預設／建議 | 狀態 |
|---|---|---|---|---|
| D1 | W1、W2 | W1 和 W2 的執行順序 | **先做 W1，再做 W2。** 理由：W1 的測試數（44→51→57）和「db.v 維持 3」只有先做才成立；W2 只需要調整一個片段；W1 的測試可以當作 W2 改寫權限時的回歸網 | 採預設 |
| D2 | 流程 | 分支與合併方式 | 每個工作項目開一個分支 `feature/<wid>-<slug>`，直接在主 checkout 開，**不用 worktree**。plan 或 skill 要求用 worktree 時，以這條為準。整體審查結論是 Ready to merge、測試全部通過，而且所有審查都是獨立進行的（不是自我審查），這時 **AI 可以在本地用 `git merge --ff-only` 合併進 `main`**，然後刪除分支（WORKFLOW G5，比照 F11 的先例）。不 push | 採預設（人類可以改成「合併前一律問我」） |
| D3 | 流程 | 要不要 push 到 `origin` | 由人類執行，或由人類明確授權。AI 不會自己 push | 已決定 2026-10-01：人類授權 push 交接系統（連同 `edf46b6`、`dfc0126`）。這次授權只限這一次，之後每次 push 仍要人類明確授權 |
| D4 | F11（W4） | F11-T1-m5：重置 Demo 時要不要把角色重設回 yu | 建議重設回 yu | 待人類 |
| D5 | F11（W4） | F11-T4-m2：SVG 附件改成下載，還是用 `<img>` 或 sandbox 顯示 | 建議排除 SVG 預覽，改成下載（安全優先） | 待人類 |
| D6 | F11（W4） | F11-T4-m4：附件全部上傳失敗時，回報要不要整份不送出 | 建議先寫入 blob，失敗就不建立回報 | 待人類 |
| D7 | F11（W4） | F11-T5-m2：被硬性前置擋下時，要不要保留回報草稿 | 建議把草稿暫存在 `ui`，跳過前置後自動重開回報對話框 | 待人類 |
| D8 | F11（W4） | F11-T6-m1：「部分恢復」要怎麼記錄 | 建議補寫稽核紀錄，並新增 `o.restoredNodes` | 待人類 |
| D9 | W3 | W3 流程控制的 brainstorming（spec 內容） | 需要人類參與問答，AI 不可以自行定稿 | 待人類（W2 合併後） |
| D10 | P 軌 | README §9 #5–#14（模型硬體、雲端供應商、預設分級、帳號、通知、協作部門權限、ERP 介面、工單、編碼規則、庫存與採購核准） | 正式導入前再決定。W2 會在 Demo 層級回答 #10（同部門的其他成員看不到） | 待人類 |
| D11 | Demo 軌 | 正式產品軌何時啟動，以及確認 §1 第 4 點的 Demo 軌完成條件 | 等 Demo 軌完成條件全部達成後再評估 | 待人類 |
| D12 | W5 | W5 README 中 full demo 的定位文字 | AI 起草，人類審閱 | 待人類（W2 之後） |
| D13 | W3 | 請提供「10 部門流程甘特圖（連接器新產品，6 階段）」的原檔或內容 | 轉寫成 `docs/reference/connector-10dept-gantt.md`，欄位：階段、工作項目、負責部門、關卡／核准人、交付物 | 待人類（W3 brainstorming 前必須到位） |

---

## 7. 交接紀錄（最新的在最上面，只保留最近 5 筆，更舊的從 git 歷史查）

格式見 [WORKFLOW.md 附錄 A](WORKFLOW.md#附錄-a交接紀錄格式)。

### 2026-10-01｜Claude Opus 5.5｜建立交接系統
- **做了什麼**：
  - 建立 `AGENTS.md`、`CLAUDE.md`、`GEMINI.md`、`docs/PROGRESS.md`、`docs/WORKFLOW.md`、`.claude/workflows/pf-status.js`、`.claude/workflows/pf-next.js`、`.gitignore`，以一個 `Docs: handoff system …` commit 提交。
  - 用平行研究整理出路線圖、F11 的執行流程、W1 和 W2 的錨點與順序。F11 的 39 個遺留問題 ID 已逐項在程式碼中核對，整理在 §5。
  - F11 的 SDD 暫存從 `.superpowers/sdd/` 移到 `.superpowers/archive/2026-09-30-f11-task-records/`，避免下一次執行時被誤讀成已完成而跳過 Task。
- **驗證**：
  - `tests/records.html` 在 `dfc0126` 實測為 `全部通過 44/44`。`/pf-status` 實跑後確認看板和 git 一致，Demo 的 console 沒有錯誤。
  - 第一輪：文件與 workflow 經過 6 位獨立審查者檢查（事實稽核、流程稽核、Claude 冷啟動模擬、非 Claude 冷啟動模擬、腳本審查、完整性批評），共 93 項發現，已修正或納入規則。
  - 第二輪：3 位審查者共提出 38 項（沒有 critical）。第一次 push（`abf9102`）時只修了一部分，其餘已在後續的 `Docs: handoff system round-2 fixes` commit 中全部處理，主要包括：PowerShell 的 `curl` 別名改用 `curl.exe`；自動化測試改用 127.0.0.1；⏸ 和 ✖ 解除凍結；清除 ⛔ 的規則；認領釋放；新增待驗證項目與 Verify 步驟；§6 加「來源」欄；人類合併後的 G6 路徑；一次只能有一個 `feature/*` 分支。
  - `pf-next` 的控制流程用模擬 agent 驗證過四種模式：dry、單一 Task、修正輪、all。
- **沒做的事**：產品程式碼完全沒有改動。W1 和 W2 都還沒開工，也沒有 push。
- **下一步**：W1 開工（見「▶ 現在」）。新的 session 才會載入 `/pf-status` 和 `/pf-next`。
- **注意**：port 8000 可能還有之前留下的 python 伺服器，PID 會變。照 WORKFLOW §5 第 1 點確認是這個 repo 之後，可以直接沿用。
