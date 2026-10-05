# AGENTS.md：接手 AI 的入口

> 任何 AI（Claude、Codex、Gemini、Cursor…）開始工作前都要先讀這份文件。人類讀者請看 [README.md](README.md)。

## 1. 這是什麼專案

**ProjectFlow（專流）** 是以「專案」為核心的 AI 工作流工具，目前處於 **Demo 驗證階段**。

- 產品程式只有一個檔案：`projectflow-full-demo.html`。約 3,200 行，原生 HTML/CSS/JS，沒有框架，不需要建置。資料存在瀏覽器的 localStorage，附件存在 IndexedDB。
- 產品規格（F1–F11）和路線圖都寫在 `README.md`。
- 新功能一律依序走：spec（`docs/superpowers/specs/`）→ plan（`docs/superpowers/plans/`）→ 照 plan 逐個 Task 用 TDD 實作。
- `projectflow-petfood-demo.html` 是階段 0 的存檔，**不要修改**。

## 2. 開工三步（每個 session 都要做）

> 如果你是被指派特定角色的子代理（implementer、審查者、驗收者、記錄者），就照指派你的 prompt 做，跳過本節。除非 prompt 另有要求，不要切分支，也不要改 PROGRESS。

1. **看現況**
   - 執行 `git status`、`git branch -a`，然後讀 [docs/PROGRESS.md](docs/PROGRESS.md) 的「▶ 現在」。
   - 如果「▶ 現在」指向某個 feature 分支，切過去，改讀那個分支上的 PROGRESS。
   - 遇到以下情況，先照 [WORKFLOW §12 中斷復原](docs/WORKFLOW.md#12-中斷復原接手時先比對) 處理：working tree 不乾淨、分支不存在、「認領中」有殘留。
   - 如果你是從 origin clone 的，而 `git log` 裡找不到交接系統的 `Docs: handoff system` commit，代表這些文件還沒 push。先停下來問人類。
2. **照流程做**
   - 只做「▶ 現在」指定的下一步，做法照 [docs/WORKFLOW.md](docs/WORKFLOW.md)。
   - 新功能要走 G0–G6 關卡，每個 Task 都要跑 §3 的迴圈：RED → GREEN → 審查 → 記錄。
3. **收工前把進度寫回去**
   - 每個 Task 審查和修正都結束後（WORKFLOW §3 第 9 步），馬上更新 PROGRESS 並 commit。
   - 收工前寫一筆交接紀錄（[WORKFLOW 附錄 A](docs/WORKFLOW.md#附錄-a交接紀錄格式)）。
   - 不要把進度只留在對話或記憶裡，也不要在 plan 檔裡打勾。

**人類在對話中的直接指示優先於看板。** 照做之前先寫進看板：新工作就在 PROGRESS §2 加一列，回答了某個 D 就更新 §6，改變方向就照 WORKFLOW §2「變更與暫停」處理。不可以用「不在看板上」當理由拒絕人類，也不可以做了卻不記錄。

**閱讀預算**
- 不要一次讀完整個 `projectflow-full-demo.html`（約 28 萬字元）。先用搜尋找到函式名，再分段讀需要的部分。
- plan 只讀目前這個 Task 的段落。
- PROGRESS 只讀「▶ 現在」、§2，以及目前工作項目的明細。
- WORKFLOW 開工時讀 §0、§3、§8、§12，其他章節用到再查。

## 3. 硬性規則（適用 Demo 驗證軌；個別 plan 的 Global Constraints 可以再加嚴）

**產品程式**
- 產品程式只改 `projectflow-full-demo.html`。允許修改的產品檔與測試檔以該 plan 的清單為準。
  - `docs/PROGRESS.md` 的更新，以及目前工作項目的 `Spec: revise`、`Plan: fix`，不受這份清單限制。
- **不引入外部函式庫或 CDN。** Demo 原本就有的 Google Fonts 是例外，但不要再新增。
- 介面文字一律用**繁體中文**，語氣和既有 Demo 一致。
- 改到 `db` 的動作，一律包在既有的 `commit(label, fn)` 裡，並呼叫 `log(nodeId, action, text)` 寫稽核紀錄。
- 權限一律用既有的 `can(action, node)` 判斷。W2 之後，任務的操作權限以 plan 指定的 `canWork` 為準。
- 輸出到 HTML 的使用者文字，一律先經過 `esc()`。
- localStorage key 固定是 `projectflow-demo-v2`。資料結構有變動時，要升 `db.v`，並讓 `upgrade()` 能自動遷移舊版資料。目前的版本看 PROGRESS「▶ 現在」。

**測試**
- 開發一律用 TDD：先寫一個會失敗的測試，記下 RED 的 `#sum` 原文，再實作到 GREEN。沒有實際跑出結果，就不能說測試通過。

**Git**
- 用明確路徑 `git add <file>`，不要用 `-A` 或 `.`。
- 主旨照 plan 寫。trailer 寫你**實際**用的工具和模型：plan 裡寫死的 `Co-Authored-By: Claude …` 只是範例，不是 Claude 就換掉（WORKFLOW §6）。
- 直接在主 checkout 開分支：`git checkout -b feature/<wid>-<slug>`，**不用 worktree**（PROGRESS D2；測試伺服器只服務主 checkout）。plan 或 skill 要求用 worktree 時，以這條為準。
- 有 `feature/*` 分支存在期間，`main` 凍結，所有 commit 都放在該分支上（例外見 WORKFLOW §6）。同一時間只能有一個 `feature/*` 分支。合併只用 `git merge --ff-only`，不要 `git pull`。
- **不要 push**，也不要 force、hard reset、`checkout --`、`stash drop` 這類破壞性操作。

正式產品軌（React、FastAPI 等）的規則，要在 PROGRESS P0 改寫後才適用。

## 4. 跑測試（細節見 WORKFLOW §5）

1. 確認 8000 埠上的伺服器是這個 repo：執行 `curl.exe -s http://127.0.0.1:8000/AGENTS.md`，第一行應該以 `# AGENTS.md` 開頭。是的話就直接沿用。
   - 在 PowerShell 裡一定要寫 `curl.exe`。單寫 `curl` 是 Invoke-WebRequest 的別名，會報錯。
2. 沒有伺服器就自己在背景啟動，並記下 PID。Bash 的寫法如下，PowerShell 的寫法見 WORKFLOW §5 第 1 點：
   ```bash
   python -m http.server 8000 --bind 127.0.0.1 >/dev/null 2>&1 & echo $!
   ```
3. 打開 `http://127.0.0.1:8000/tests/records.html?t=<時間戳>`，等 `#sum` 從「執行中」變成 `全部通過 N/N`。目前的基準見 PROGRESS。
   - 自動化測試用 127.0.0.1。測試頁會清掉這個 origin 的 Demo 資料，這樣不會清到人類平常用 `localhost` 試用的資料。
4. 沒有瀏覽器工具的 AI，用 WORKFLOW §11 的 headless 腳本跑。
5. 收工時只關掉你自己啟動的伺服器，而且要用啟動它的那個 shell 關。

## 5. 什麼時候要停下來問人類（完整清單見 WORKFLOW §8）

- spec 或 plan 和程式碼衝突。PROGRESS「執行注意」已經裁決過的不算。
- plan 本身規定了有缺陷的做法（plan-mandated）。
- 任何 spec 沒有寫明的產品決策。
- 要修改允許清單以外的產品檔或測試檔，或要改資料版本。
- 要寫新的 spec。
- push、PR、無法 fast-forward 的合併，或 `main` 出現來源不明的新 commit。

**展示模式**（PROGRESS「▶ 現在」的「模式」欄；細節見 [WORKFLOW §13](docs/WORKFLOW.md#13-展示模式人類-2026-10-05-指示progress-d30)）：spec 沒寫到的小細節由 AI 代決，記進 PROGRESS §6 後繼續做；審查只擋會讓展示出問題的錯誤。上面其他情況照舊要停下來。

處理方式：先把問題記進 PROGRESS §6，再問人類。人類不在的話，照 PROGRESS §2 的排程規則處理，**不要用猜的**。

## 6. 文件地圖

| 文件 | 內容 |
|---|---|
| [docs/PROGRESS.md](docs/PROGRESS.md) | **進度看板**：現在在做什麼、工作佇列、各 Task 狀態、驗收清單、待處理問題、待人類決定、交接紀錄 |
| [docs/WORKFLOW.md](docs/WORKFLOW.md) | 流程：生命週期關卡、Task 迴圈、審查清單與提示範本、測試程序、Git 規則、何時停下來、中斷復原 |
| [README.md](README.md) | §4 產品規格 F1–F11、§5 資料模型、§6 架構、§9 待決定事項，這幾節都有效。**§1 快速開始、§2 功能總覽、§7 專案結構還是階段 0（petfood）的內容，W5 完成前不要拿來判斷現況。** §8 的勾選框只追蹤正式產品軌 |
| `docs/superpowers/specs/` | 各工作項目的設計規格 |
| `docs/superpowers/plans/` | 各工作項目的實作計畫（逐 Task 寫，附程式片段與測試） |
| `tests/records.html`、`tests/*.test.js` | 瀏覽器測試頁：用 iframe 載入 Demo，在 Demo 的全域環境裡執行測試 |
| `.claude/launch.json` | 本機伺服器設定（`demo`：`python -m http.server 8000`） |
| `.claude/workflows/` | Claude Code 專用的自動化（`/pf-status`、`/pf-next`）。其他 AI 不要用 node 執行；要手動做同樣的事，照 WORKFLOW §9 和 §3 |
| `CLAUDE.md`、`GEMINI.md` | 讓各工具匯入本文件的入口，裡面有各工具的補充說明 |
| `.superpowers/`（不進 git） | 本機暫存：Claude SDD 的工作區、原型、已歸檔的執行紀錄（WORKFLOW §7） |
