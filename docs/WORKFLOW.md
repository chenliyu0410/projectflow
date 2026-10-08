# ProjectFlow 工作流程

> 給所有接手的 AI（Claude、Codex、Gemini、Cursor…）和人類協作者。
> 進度看 [PROGRESS.md](PROGRESS.md)，入口看 [AGENTS.md](../AGENTS.md)。本文件規定**怎麼做**，PROGRESS 記錄**做到哪裡**。
> 這套流程是把 F11 實際用過的做法（superpowers 的 brainstorming → writing-plans → subagent-driven-development）寫成文字，並補上 F11 和交接演練時踩過的坑。
>
> **閱讀指引**：開工時讀 §0、§3、§8、§12，其他章節需要時再查。PROGRESS「▶ 現在」的「模式」是「展示模式」時，也要讀 §13，它優先於其他章節。

> **畢業專題模式（D65）**：PROGRESS標示此模式時，先讀§14；正式軌的逐Task TDD、雙審、反覆全量測試及記錄要求改依§14，不套用Demo歷史§13。

**詞彙**
- **SDD**：superpowers:subagent-driven-development。Claude 的執行方式：主 session（controller）把每個 Task 交給子代理實作，再交給另一個子代理審查。
- **brief**：controller 交給 implementer 子代理的任務說明，內容等於 plan 中該 Task 的全文。
- **ledger**：`.superpowers/sdd/progress.md`，SDD 單次執行的進度紀錄（只給 Claude 使用，見 §7）。
- **Task**：plan 中的一個 `### Task N`。**工作項目**：PROGRESS §2 的一列（W1、W2…）。

---

## 0. 四條鐵律

1. **只做看板指定的下一步。**
   - 先讀 PROGRESS「▶ 現在」。不要自己發明工作，不要跳順位，也不要順手改 plan 範圍以外的東西。看到值得做的事，記進 PROGRESS §5 或 §2。
   - **例外：人類在對話中的直接指示優先**，但要先寫進看板再做（見 §2「變更與暫停」）。不可以用「不在看板上」拒絕人類，也不可以做了卻不記錄。
2. **沒有 spec 和 plan，不寫產品程式碼。**
   - 只有 📋 以上的工作項目可以修改 `projectflow-full-demo.html`。
   - 問題清理型的工作項目例外，見 G1。
3. **進度只記在 PROGRESS。**
   - 每個 Task 審查結束後立刻記錄（§3 第 9 步），收工前寫交接紀錄。
   - **不要在 plan 檔的 `- [ ]` 打勾**，這樣會出現第二個進度來源。
   - 對話記憶不可靠。PROGRESS 和 `git log` 才是依據。
4. **一次只做一件事。**
   - 同一時間最多一個 `feature/*` 分支（暫停或取消的分支會改名為 `paused/*` 或 `cancelled/*`，不算在內，見 §2「變更與暫停」）。
   - 同一個 checkout 只能有一個會寫入的 AI（唯讀的檢查和審查不算）。
   - 同一時間只能有一個 agent 使用瀏覽器或測試頁，因為大家共用 `127.0.0.1:8000` 的 storage 和 Browser pane。

---

## 1. 狀態符號

見 [PROGRESS §0](PROGRESS.md#0-狀態符號)。正常流向是 ⬜ → ✏️ → 📋 → 🔨 → 🔍 → 🟢 → ✅。另外還有 ⛔ 阻塞（等人類決定）、⏸ 暫停、✖ 取消。

---

## 2. 工作項目生命週期（G0–G6）

每個關卡都有完成條件。完成條件沒有全部達成，就不能進下一關。

### G0 構想
（⬜）
- 在 PROGRESS §2 佇列加一列，寫上一句目標和依賴。
- 順位由人類決定。AI 可以在 §2 底部「建議（待人類排序）」提出想法，但不可以自己插隊。

### G1 規格
（⬜ → ✏️）
- **一定要和人類一起做。**
  - Claude 用 `superpowers:brainstorming`。
  - 其他 AI：一次只問一個問題，提出 2–3 個方案並說明取捨，和人類確認後才定稿。
- 產出：`docs/superpowers/specs/YYYY-MM-DD-<slug>-design.md`。結構照既有 spec：問題、目標、不在範圍、資料結構、規則、錯誤處理、測試、文件更新。
- commit：`Spec: <主題>`。完成條件：人類同意 spec。
- **例外：問題清理型工作項目**（例如 W4）不需要 G1。
  - 適用條件：只處理 PROGRESS §5 已經登錄、而且「需人類」為「否」的條目。
  - 這種項目的 spec 就是那些條目，AI 可以自行進入 G2。
  - plan 檔名用 `YYYY-MM-DD-<wid>-cleanup.md`，開頭列出涵蓋的 issue ID，每個 ID 對應一個 Task 並附測試。
  - 不可以混入需要人類決定的條目，也不可以新增產品行為。

### G2 計畫
（✏️ → 📋）
- Claude 用 `superpowers:writing-plans`。其他 AI 照 `docs/superpowers/plans/` 裡既有 plan 的格式寫。
- plan 必須包含：
  - Goal、Architecture
  - **Global Constraints**：允許修改的檔案、資料版本、權限函式
  - 檔案結構
  - 「測試方式：見 WORKFLOW §5」。直接引用，不要自己重寫一套
  - 每個 Task 的 Files、Interfaces、Steps（TDD：失敗測試 → RED → 實作 → GREEN → commit）、commit 訊息主旨
- 測試數量寫成「基準 + N 項」。F11 的經驗是修正輪會多加測試，寫死的總數就對不上。
- commit：`Plan: <主題>`。
- 更新 PROGRESS：狀態改成 📋，填上 spec、plan 連結和 commit，列出 Task 表與驗收清單（`- [ ]`）。

### G3 執行
（📋 → 🔨）
1. **Pre-flight（在 `main` 上做，還不 commit）**
   - 確認 `git branch --list "feature/*"` 是空的。如果已經有別的 feature 分支，依 §8 停下來。
   - 拿 plan 的 Global Constraints 和現況比對，加上 PROGRESS 該項目的「執行注意」。
   - 抽查 Task 1 的錨點，並依 §5 跑基準測試。
   - 有衝突或基準不符時，依 §8 停下來。**不可以邊做邊猜**。
2. **宣告開工**
   - PROGRESS 有三處要改成 🔨：「▶ 現在」、§2 佇列、§3 該項目標題。
   - 「▶ 現在」的「分支」填 `feature/<wid>-<slug>`。「下一個動作」寫「切到該分支，進度以該分支的 PROGRESS 為準」。「認領中」填執行者和時間。
   - 只 add `docs/PROGRESS.md`，commit：`Progress: start <WID>`。
3. **開分支**：`git checkout -b feature/<wid>-<slug>`。
   - 直接在主 checkout 開分支，**不用 worktree**（PROGRESS D2：測試伺服器只服務主 checkout，在 worktree 裡改的程式不會被測到）。
   - plan 或 skill 要求使用 worktree 時，一律以這條為準，不必問人類。
4. **Claude 專用：準備 SDD 工作區**
   - 如果 `.superpowers/sdd/` 已經存在，而且屬於別的 plan，先移到 `.superpowers/archive/<plan 檔名>/`（見 §7）。
5. 逐個 Task 跑 §3 的迴圈。

開工後如果發現 plan 要修，在 **feature 分支**上 commit `Plan: fix <主題> …`（見 §6 分支規則）。

### G4 整體審查
（🔨 → 🔍 → 🟢）
- 所有 Task 都 ✅ 之後，把狀態改成 🔍，依 §4.2 審查 `git merge-base main HEAD`..`HEAD` 的完整 diff。
- 發現的問題一次交給修正者處理，commit：`<前綴> final review fixes: …`。修完再審一次，**最多兩輪**。兩輪後仍有 Critical 或 Important，就標 ⛔ 問人類。
- 跑完整測試，再逐項執行 PROGRESS 的驗收清單。
- **完成條件**：
  - 審查結論是 `Ready to merge: Yes`
  - 測試全部通過，驗收清單全部打勾
  - 這個工作項目產生的 plan-mandated D 都已經有人類結論（§6 的「來源」欄是本項目）。整體審查可以先做，但這些 D 有結論之前，不能改成 🟢
- 達成後狀態改成 🟢。

### G5 合併
（🟢 → ✅）
- 照 PROGRESS D2 的設定執行。只要有任何一個 Task 或整體審查是**自我審查**（沒有交給另一個 agent 或 session），一律視為「合併前問人類」。
- 預設步驟如下。指令要分開執行，因為 Windows PowerShell 5.1 不支援 `&&`：
  ```bash
  git checkout main
  git merge --ff-only feature/<wid>-<slug>
  ```
  合併後在 main 做 G6 的收尾 commit，最後才執行 `git branch -d feature/<wid>-<slug>`。
- **不要執行 `git pull`，不要 rebase，也不要建立 merge commit。** 無法 fast-forward 時停下來問人類。
- Claude 不要使用 `superpowers:finishing-a-development-branch` 的合併選項（它會 pull，而且不加 `--ff-only`），照本節步驟做。
- **不push未授權內容**；D50已持續授權完成、獨立審查與驗收後的階段更新README／PROGRESS並push origin main，其他情況仍需人類授權。

### G6 收尾
- 確認 README 已照 plan 更新。
- 更新 PROGRESS：
  - 該項目改成 ✅，摘要移到 §4。
  - 「▶ 現在」除了「行號基準」（固定不改）以外，**每一列都要更新**：
    - 目前工作項目、下一個動作：換成 §2 的下一個項目
    - 分支：改回 `main`
    - 最新程式 commit：合併後的 HEAD
    - 測試基準、資料版本、遠端（`git log --oneline origin/main..main`）
    - 認領中：清空
    - 阻塞／待人類
  - 寫一筆交接紀錄。
- 在 main 上 commit：`Progress: <WID> done`。
- 把 `.superpowers/sdd/` 歸檔到 `.superpowers/archive/<plan 檔名>/`。

### 變更與暫停
- **人類要求新工作**：在 §2 加一列，標「人類 YYYY-MM-DD 指示」，順位依人類指定。如果目前有分支存在，要問人類新工作要接在那個分支上做，還是先暫停該分支。
- **人類回答了 D**：照 PROGRESS §6 前言記錄，並把連動的條目改掉。
- **暫停**（人類同意後才做）：
  1. 在分支上把狀態標 ⏸，寫明恢復條件，然後 commit。
  2. 把分支改名：`git branch -m feature/<wid>-<slug> paused/<wid>-<slug>`。
  3. 切回 main，commit `Progress: pause <WID>`。這次要更新「▶ 現在」和 §2，並登記保留的分支名。從這時起 main 解凍。
  4. 恢復時把分支改回 `feature/`。如果需要 rebase，先問人類。
- **取消**（人類同意後才做）：
  1. 分支保留不刪，改名為 `cancelled/<wid>-<slug>`。
  2. 在 main 上 commit `Progress: cancel <WID>`，狀態標 ✖。
  3. 在 spec 和 plan 開頭加一行 `Superseded：<日期與原因>`。
- **spec 在 📋 之後改版**：
  1. 狀態退回 ✏️，commit `Spec: revise <主題>`，再修 plan。
  2. 刪掉「執行注意」中依賴舊內容的條目。
  3. 已完成的 Task 如果受影響，在 Task 表加一列「返工」，不要改寫 git 歷史。

---

## 3. 單一 Task 的迴圈

| # | 步驟 | 要點 |
|---|---|---|
| 1 | 記下 BASE | 執行 `git rev-parse HEAD`。不要用 `HEAD~1` 推算 |
| 2 | 讀需求 | 讀 plan 中該 Task 的全文，加上 PROGRESS「執行注意」裡相關的條目。plan 和程式碼衝突時依 §8 處理。Claude 的子代理改回報 `NEEDS_CONTEXT` |
| 3 | **RED** | 照plan寫測試於指定檔案。Demo記`#sum`原文與失敗名稱；正式軌依當前plan命令，記pytest／Vitest／Playwright真實摘要、失敗名稱與exit code。沒有RED證據不算完成；不能把安裝工具失敗當功能RED。 |
| 4 | **GREEN** | 實作到全部測試通過。只寫 plan 要求的東西，沿用既有寫法 |
| 5 | UI 驗證 | 有畫面變動時，打開 Demo 實測 plan 指定的流程，確認 console 沒有錯誤。截圖不能用時改用 DOM/JS 檢查，並寫明哪些沒有實際看過 |
| 6 | 自我檢查 | 對照 §4.1 清單 |
| 7 | Commit | 用 `git add <明確路徑>`，**禁止 `git add -A` 或 `git add .`**。主旨用 plan 指定的，trailer 照 §6 |
| 8 | 審查 | 交給另一個 agent 或 session，依 §4.1 審查（提示範本見 §4.3；Claude 見 §10，其他 AI 見 §11）。<br>- 有 Critical 或 Important：開修正輪（新 commit：`<前綴> task N fix: …`），修完再審。**最多兩輪**，仍未通過就標 ⛔ 問人類。<br>- 審查者列出的「待驗證」項目：由實作者實測（測試頁、瀏覽器、DOM/JS 讀值），把證據寫進 Task 列。實測通過就結案，不需要 fix commit；實測失敗就改列為 Important |
| 9 | 記錄 | 更新 PROGRESS：<br>- Task 改成 ✅。commits 欄填 `<base7>..<head7>`（git 的 A..B 語意，A 是 BASE，不包含在內）。<br>- 測試欄保留預期值，後面接實際的 RED 和 GREEN，例如 `RED 失敗 7/51 → GREEN 全部通過 51/51`。<br>- Minor 記進 §5，plan-mandated 記進 §6（「來源」欄填本項目和 Task）。<br>- 「▶ 現在」更新下一個動作、最新程式 commit、測試基準；資料版本有變也要一起改。<br>- commit：`Progress: <WID> task N done`（只 add `docs/PROGRESS.md`）。<br>沒有測試證據（例如人類還沒回報 GREEN）時，不可以做這一步 |

**Implementer 回報狀態**（Claude 子代理用）：`DONE` | `DONE_WITH_CONCERNS` | `BLOCKED` | `NEEDS_CONTEXT`

---

## 4. 審查

### 4.1 每個 Task 的審查清單（spec 符合度＋品質）
- **Spec 符合度**：有沒有漏做（Missing）、多做（Extra）、做錯（Misunderstood）。
  - 從 diff 無法判斷的部分（例如畫面外觀、互動流程、測試是否真的通過），列成「**待驗證**」，並寫明驗證方法。不可以默默放行。
  - 待驗證不算阻塞 issue，由實作者或 Claude 的驗證者實測。實測失敗時才改列為 Important。
  - PROGRESS「執行注意」已經裁決過的做法，不算 issue。
- **專案硬性規則**（AGENTS.md §3）：
  - 改到 `db` 的地方都包在 `commit()` 裡，並呼叫 `log()`
  - 權限一律走 `can()`（或 plan 指定的函式）
  - 使用者文字輸出前一律經過 `esc()`
  - 介面文字用繁體中文
  - 沒有外部函式庫或 CDN
  - 資料結構有變時，有升 `db.v` 並寫好 `upgrade()`
  - 只改了允許的檔案。**`docs/PROGRESS.md`（`Progress:` commit），以及目前工作項目的 `Spec: revise`、`Plan: fix`，不算越界**
- **品質**：錯誤處理、邊界情況、逐字重複的邏輯、測試是否真的驗證了行為、檔案膨脹了多少。
- **嚴重度**：
  - **Critical**（必修）：功能壞掉、資料遺失、安全問題
  - **Important**（必修）：行為錯誤或脆弱、漏掉需求、吞掉錯誤、測試沒有斷言任何東西、待驗證項目實測失敗
  - **Minor**：其他
- **plan-mandated**（plan 本身規定了有缺陷的做法）：
  - **只用在 Critical 和 Important**。plan 規定的 Minor 當一般 Minor 記錄就好。
  - 照樣要報，標 Important 或 Critical (plan-mandated)，**當下就記進 PROGRESS §6**。「來源」欄填本項目和 Task。
  - Critical：立即停下。
  - Important：可以繼續後面的 Task，也可以做整體審查，但**改成 🟢 之前必須有人類結論**，或人類明確同意帶著它合併。
- **延後規則**：
  - 除了 plan-mandated 的 Important 以外，Critical 和 Important 都要在進下一個 Task 前修好。
  - Minor 記進 PROGRESS §5，可以照常往下做。
- 審查者是**唯讀**的：
  - 不改 working tree，不移動 HEAD，不使用瀏覽器（另一個 agent 可能正在用）。
  - 不相信實作報告的自述。
  - 每個 finding 都要附 `file:line`。

### 4.2 整體審查清單
- 對照 plan：偏離的地方是改進還是走偏？功能是否齊全？
- 架構與整合：和周邊程式碼的關係、效能、安全。
- 上線準備：
  - 資料遷移：舊版 localStorage 能升級
  - 向下相容
  - README 已更新
- 回顧這個工作項目新增到 §5 的 Minor，判斷是否有該在合併前修掉的。
- 結論三選一：`Ready to merge: Yes | No | With fixes`。

### 4.3 審查者提示範本（交給另一個 agent 或 session）

```text
你是唯讀審查者。不可修改任何檔案、不可 checkout、不可使用瀏覽器。
專案規則：AGENTS.md §3；審查清單：docs/WORKFLOW.md §4.1（整體審查加 §4.2）。
需求：<plan 路徑> 的 Task <N> 全文（整體審查：整份 plan 與 spec <路徑>）。
範圍：先看 git log --oneline <BASE>..<HEAD> 和 git diff --stat <BASE>..<HEAD>，再讀 git diff <BASE>..<HEAD>。
不要相信實作報告的自述，以 diff 為準；但實作者對「待驗證」項目附上的實測讀值可以採信。
PROGRESS「執行注意」已裁決的做法不算 issue。
輸出依序：Spec Compliance（Missing／Extra／Misunderstood）→ Strengths →
Issues（Critical／Important／Minor，各附 file:line、原因、修法；plan 規定的 Critical/Important 標 plan-mandated）→
Verify（從 diff 無法判斷、需要實測的項目，各附驗證方法；不算阻塞）→
結論：Task 用 Approved | Needs fixes；整體審查用 Ready to merge: Yes | No | With fixes。
```

---

## 5. 測試程序（以此為準）

**正式軌例外（D51／D52）**：`api/`、`web/`、`deploy/`依當前已審閱plan的pytest／Vitest／Playwright及真實資料庫驗收命令；記錄RED/GREEN摘要與exit code，不使用Demo的`#sum`。獨立審查與§3記錄迴圈不變。以下Demo測試程序繼續適用Demo。

1. **伺服器**
   - **確認 8000 埠**：PowerShell 執行 `Get-NetTCPConnection -LocalPort 8000 -State Listen`。出現 `ObjectNotFound` 錯誤代表沒有伺服器。也可以用 `netstat -ano | findstr :8000`。
   - **確認是這個 repo**：執行 `curl.exe -s http://127.0.0.1:8000/AGENTS.md`，看第一行是否以 ASCII 的 `# AGENTS.md` 開頭。
     - 在 PowerShell 裡一定要寫 `curl.exe`。單寫 `curl` 會變成 Invoke-WebRequest 的別名而報錯；用 Invoke-WebRequest 讀中文也會變亂碼。
     - 符合就沿用。不符合就不要動那個伺服器，改用其他埠（例如 8001），後面所有網址都要跟著換。
   - **自己啟動**：要在背景執行，並記下 PID。
     - Bash：`python -m http.server 8000 --bind 127.0.0.1 >/dev/null 2>&1 & echo $!`
     - PowerShell：`$p = Start-Process python -ArgumentList '-m','http.server','8000','--bind','127.0.0.1' -WindowStyle Hidden -PassThru; $p.Id`
     - Claude 可以用 `preview_start`（name `demo`），結束時用 `preview_stop`。注意 `launch.json` 沒有加 `--bind`。
2. **開測試頁**：`http://127.0.0.1:8000/tests/records.html?t=<時間戳>`。輪詢 `#sum`，直到它不再以「執行中」開頭，通常要 3–10 秒。超過 60 秒仍停在「執行中」，就當作失敗。
   - 自動化測試一律用 `127.0.0.1`。人類平常試用 Demo 用的是 `localhost`，兩者是不同的 origin，測試頁清資料時不會清到人類的資料。
3. **讀結果**：讀 `document.getElementById('sum').textContent`。失敗明細在 `#out`，也可以讀 `window.__results`（陣列，元素是 `{name, ok, err}`）。
4. **通過標準**：`全部通過 N/N`。把 N 記進 PROGRESS。和 plan 預期不同時，以實際數字為準，並寫明原因。
5. **快取陷阱**
   - 測試檔是用 `cache: 'no-store'` 抓的，所以新測試一定會出現在 `#out`。但 iframe 裡的 Demo 可能是快取的舊版。
   - **改了 Demo 之後，新測試一直失敗，或結果和程式狀態不符**：在測試頁執行 `document.getElementById('app').contentWindow.location.reload(true)`，再換一個新的 `?t=` 重新整理測試頁。
   - **新測試的名稱沒有出現，或 `#sum` 是 `失敗 1/1`（「載入測試」）**：這是測試檔有語法錯誤或插入位置不對，不是快取問題。
6. **注意**：測試頁會清掉這個 origin 的 Demo localStorage 和 IndexedDB。每個 `T(name, fn)` 開始前都會先執行 `resetAll()`，再切到 `yu`。可用的輔助函式有 `T`、`eq`、`ok`、`as` 和常數 `good`，定義在 `tests/records.test.js` 開頭。
7. **手動 UI 測試**
   - 打開 `http://127.0.0.1:8000/projectflow-full-demo.html`，左下角可以切換身分。資料版本有變動時，先按「重置 Demo 資料」。
   - 窄螢幕要用 375px 檢查。`.main` 設了 `overflow:hidden`，所以要用這段可以直接執行的檢查式：
     ```js
     (() => { const m = document.querySelector('main'); const c = [...document.querySelectorAll('.rcard')]; return m.scrollWidth <= m.clientWidth && c.every((e) => e.getBoundingClientRect().right <= innerWidth) && document.documentElement.scrollWidth <= innerWidth; })()
     ```
   - 測完把 viewport 設回桌面。
8. **收尾**
   - 只關掉你自己啟動的伺服器，而且要在**同一個 shell** 裡關。
     - Bash：`kill <$! 的值>`。Git Bash 的 `$!` 是 MSYS 的 PID，不是 Windows 的 PID；要用 PowerShell 關的話，先用 `cat /proc/<pid>/winpid` 換算。
     - PowerShell：`Stop-Process -Id $p.Id`。
     - 用 preview_start 啟動的，就用 `preview_stop` 關。
   - **不要用「殺掉占用 8000 埠的程序」這種方式**，那可能是人類或前一個 session 的伺服器。
9. **請人類幫忙跑測試時**
   - 先提醒人類：測試頁會清掉該 origin 的 Demo 資料和附件。請用 `http://127.0.0.1:8000/…` 或無痕視窗開，不要用平常試用 Demo 的那個 `localhost`。
   - 要分三次請人類跑，每次貼回 `#sum` 原文和失敗的測試名稱：
     1. 開工前的基準
     2. 加好測試、還沒實作時的 RED
     3. 實作後的 GREEN
   - 拿到基準之前，不要 commit `Progress: start`。拿到 GREEN 之前，不要 commit `Progress: <WID> task N done`。人類不在時，依 §8 停下來。
10. **沒有瀏覽器工具的 AI**：做法見 §11。**不可以沒有證據就說測試通過。**
11. **開工時基準不符**：照順序檢查。
    1. 伺服器是不是這個 repo（第 1 點）。
    2. 處理快取（第 5 點），並核對 `#out` 的測試數和名稱。
    3. 執行 `git status`，以及 `git log --oneline <最新程式 commit>..HEAD -- projectflow-full-demo.html tests`，找出沒有記錄的變更。
       - 如果找到的變更能解釋差異，例如中斷復原時 Task 已經 commit，新增的測試數也吻合，而且全部通過，就不算回歸，照實更新看板即可。
    4. 仍然無法解釋，就是真的回歸。這時：
       - 不要開新的 Task，也不要改測試去遷就結果。
       - 在 §5 加 `BASE-<日期>-m1`，附上失敗測試名稱和 `#out` 原文。
       - 在 §6 新增一個 D，「▶ 現在」標 ⛔。

---

## 6. Git 規則

- **分支**
  - 名稱用 `feature/<wid>-<slug>`，例如 `feature/w1-subtask-report-card`。
  - **沒有任何 `feature/*` 分支存在時**，文件類 commit（Spec、Plan、Progress、Docs）可以直接放在 `main`。G3 的 `Progress: start <WID>` 是在開分支之前 commit 的，所以也屬於這一類。
  - **有 `feature/*` 分支存在期間，`main` 凍結**：所有 commit 都放在該分支，包括 Progress、`Plan: fix`、D 的結論、新增工作項目。
    - 例外一：G5 ff 合併之後、刪除分支之前，在 main 上做的 G6 `Progress: <WID> done`。
    - 例外二：經人類同意的 `Progress: pause|cancel <WID>`（分支已改名，見 §2「變更與暫停」）。
  - 發現 `main` 有新 commit（例如人類加的），就停下來問人類，不要自己 rebase。
- **commit 訊息**：英文主旨，不用 conventional-commit 前綴。
  - 規格和計畫：`Spec: <主題>`、`Spec: revise <主題>`、`Plan: <主題>`、`Plan: fix <主題> …`
  - Task：用 plan 指定的主旨。plan 沒寫的話，用 `<前綴> task N: <摘要>`
  - 修正：`<前綴> task N fix: <修了什麼>`；整體修正：`<前綴> final review fixes: <摘要>`
  - 進度：`Progress: start <WID>`、`Progress: <WID> task N done`、`Progress: <WID> blocked`、`Progress: <WID> final review`、`Progress: <WID> awaiting merge`、`Progress: <WID> done`、`Progress: record Dn`、`Progress: reconcile <摘要>`、`Progress: release claim`、`Progress: pause <WID>`、`Progress: cancel <WID>`
  - 其他文件：`Docs: <摘要>`
- **trailer**：寫你**實際**使用的工具和模型。
  - Claude Code 照 session 的 attribution 提示寫，例如 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`。
  - plan 裡寫死的 `Co-Authored-By: Claude …` 只是範例。不是 Claude 的話就刪掉那一行，換成自己工具的慣例；沒有慣例就寫 `AI-Assisted-By: <工具> <模型>`。也不要寫兩行。
- **禁止**：`git add -A`、`git add .`、未授權的`push`、`--force`、`reset --hard`、`checkout -- <檔案>`、`stash drop`、改寫已提交歷史、跳過hooks。D50僅持續授權已驗收階段的`git push origin main`，不包含force、其他分支或PR。
- **換行**：`core.autocrlf=true`，所以 `projectflow-full-demo.html`、`tests/*`、`README.md` 在工作目錄是 CRLF。替換多行程式碼時用編輯器工具；用 `sed` 或 Python 配 `\n` 會比對不到。

---

## 7. 本機暫存（`.superpowers/`，不進 git；**只有 Claude 的 SDD 和 `/pf-next` 使用**）

| 路徑 | 用途 |
|---|---|
| `.superpowers/sdd/` | SDD 執行工作區：`task-N-brief.md`、`task-N-report.md`、`review-<base7>..<head7>-*.md`，以及 ledger `progress.md`（第一行是 `Plan: <plan 路徑>`） |
| `.superpowers/archive/<plan 檔名>/` | 已結束的執行紀錄。F11 的在 `2026-09-30-f11-task-records/` |
| `.superpowers/prototype/` | 畫面原型（W1 回報卡） |

- superpowers SDD 開始時會讀 ledger，**標成 complete 的 Task 會被跳過**。所以開始新 plan 之前，一定要先把屬於別的 plan 的 `sdd/` 歸檔。
- SDD skill 本身不會寫 `Plan:` 這一行。手動跑 SDD 時，開始前要先建立 `progress.md`，第一行寫 `Plan: <plan 路徑>`，這樣 `/pf-next` 才認得出它屬於哪份 plan。
- ledger 只是單次執行的復原依據。正式進度看 `docs/PROGRESS.md`，兩邊都要更新。
- **其他 AI 不要建立 `.superpowers/sdd/`**。RED/GREEN 證據和審查結論寫進 PROGRESS 的 Task 列和交接紀錄。
- 暫存可能被 `git clean -fdx` 清掉，換一台機器也不會跟過去。重要的結論都要寫進 PROGRESS。

---

## 8. 何時必須停下來問人類

遇到下列情況，先在 PROGRESS §6 記下問題（給一個新的 D 編號），「▶ 現在」標 ⛔，commit 之後再問。分支存在時，commit 放在該分支上。

> **展示模式**（§13）：第 1、3 點裡的小細節由 AI 代決並記進 §6，不停下來；第 2 點只有 Critical 要停。其他各點照舊。

1. spec、plan 和現有程式碼衝突，或 plan 的指示無法照做。PROGRESS「執行注意」已經裁決過的不算。
2. plan-mandated 問題（處理方式見 §4.1）：Critical 立即停；Important 要在改成 🟢 之前有結論。
3. 任何 spec 沒有寫明的產品決策，包括行為、文字、資料模型。
4. 要修改允許清單以外的產品或測試檔案、改資料版本、引入外部依賴。
5. 要寫新的 spec（G1 本來就要和人類一起做）。
6. 照 `superpowers:systematic-debugging`（其他 AI 見 §11）修了兩輪，測試仍然失敗。
7. 需要D50範圍外的push、開PR、無法fast-forward的合併、`main`／遠端出現不明的新commit，或任何破壞性的git操作。
8. 看板和 `git log` 對不上，而且**無法**從 commit 判斷真實狀態。
   - 如果可以判斷，就直接修正看板，commit `Progress: reconcile <摘要>`，並寫進交接紀錄。

**人類暫時不在時**，依 PROGRESS §2 排程規則處理：
- 已經有 `feature/*` 分支：只能做不產生 commit 的準備工作，或寫好交接紀錄後結束 session。
- 還沒有分支：可以改做下一個不需要人類決定的項目。

**人類回答了 D 之後**，依 PROGRESS §6 前言記錄。被這個 D 擋住的 ⛔ 要移除，然後從原本的步驟接著做（§12）。

**不可以猜。**

---

## 9. Session 開始與結束檢查表

**開始**
- [ ] 執行 `git status` 和 `git branch -a`。
  - working tree 不乾淨，或「▶ 現在」指向的分支不存在 → 先看 §12。
- [ ] 讀 `main` 上的 PROGRESS「▶ 現在」。如果它指向某個分支，切過去，改讀那個分支上的 PROGRESS。
  - 「認領中」以**分支上的** PROGRESS 為準。`main` 上的認領要到合併時才會更新。
- [ ] 檢查「認領中」：
  - 空白，或是你自己 → 可以繼續。
  - 是別人，而且認領時間在 4 小時內，或分支在 4 小時內有新 commit → 還沒過期，先問人類。
  - 其他情況 → 視為中斷。在交接紀錄寫「接管 <原認領>」，然後依 §12 處理。
  - 人類確認原本的 session 已經停了 → 視同過期。認領改成你自己，交接紀錄寫「接管 <原認領>（人類 <日期> 確認）」，然後 commit `Progress: reconcile take over claim`。
- [ ] 填寫認領，和下一個 Progress commit 一起提交。
- [ ] 跑一次測試，確認結果和「▶ 現在」的測試基準一致。不一致就照 §5 第 11 點處理。
- [ ] 讀這次要做的 plan Task 段落，以及「執行注意」。

**結束**
- [ ] 所有工作都已經 commit，working tree 是乾淨的。
- [ ] PROGRESS 已更新：「▶ 現在」、Task 表、§5、§6、交接紀錄（§7 只保留最近 5 筆），並清空認領。
- [ ] 關掉自己啟動的伺服器，viewport 設回桌面。
- [ ] 回覆人類：做了什麼、驗證證據、下一步、有哪些事情需要人類決定。

---

## 10. Claude Code 專用

| 用途 | 做法 |
|---|---|
| 看現況 | `/pf-status`：唯讀檢查，核對 PROGRESS、git 和測試，並給出下一步 |
| 推進工作 | `/pf-next` 依看板推進一步，可能是下列其中一種：<br>- 下一個 Task：實作 → 審查（展示模式一位，完整流程兩位）→ 實測「待驗證」項目 → 修正（展示模式最多一輪，完整流程最多兩輪）→ 記錄<br>- 整體審查<br>- 依 D2 在本地 ff 合併<br>`/pf-next all` 會連續做到工作項目完成或遇到阻塞。<br>`/pf-next dry` 只預覽，不改 repo，但在正確的分支上會跑一次測試頁（用 127.0.0.1）。<br>`/pf-next full` 單次改用完整流程（§13） |
| 寫規格 | `superpowers:brainstorming`，要和人類一起做。📋 以上的項目**不要**再跑 |
| 寫計畫 | `superpowers:writing-plans`。📋 以上的項目**不要**再跑 |
| 手動執行 plan | `superpowers:subagent-driven-development`：<br>- 先依 §7 歸檔，並建立第一行是 `Plan:` 的 ledger<br>- 不開 worktree（D2）<br>- 每個 Task 都照 §3 第 9 步 commit PROGRESS<br>- plan 開頭的「REQUIRED SUB-SKILL」優先改用 `/pf-next` |
| 合併 | 照 G5 的步驟做，不要用 finishing-a-development-branch 的合併選項 |
| 除錯 | `superpowers:systematic-debugging` |
| 瀏覽器 | 內建的 Claude_Browser 工具。8000 埠已經被這個 repo 的伺服器占用時（§5 第 1 點），直接 `navigate` 過去 |

## 11. 其他 AI 的對應做法（沒有 superpowers skills 或 Claude 工具時）

**流程**
- **brainstorming**：見 G1。一次問一個問題，提出 2–3 個方案，人類確認後才寫 spec。
- **writing-plans**：照既有 plan 的格式寫，必備內容見 G2。
- **SDD**：自己依序跑 §3。審查用 §4.3 的範本，交給另一個 agent 或 session。
  - 只能自我審查時，至少隔一個步驟再用清單逐項檢查，並在 Task 列與交接紀錄註明「自我審查」。這種工作項目**不可以由 AI 自行合併**（G5）。
- **systematic-debugging**：
  1. 先穩定重現問題。
  2. 讀 `#out` 或 `__results[].err` 的堆疊。
  3. 一次只提一個根因假設，用最小的檢查去驗證。
  4. 修正後跑完整測試。
  - 以上算一輪。兩輪仍然失敗，就依 §8 停下來。
- **`.claude/workflows/`**：只能在 Claude Code 裡用，不要用 node 執行。

**沒有瀏覽器工具時跑測試**
- 用本機的 Chrome 或 Edge，搭配 repo 外的 Playwright。**不要把 Playwright 加進專案。**
- 必須透過 HTTP 開啟（§5 第 1 點）。用 `file://` 會讓 fetch 和跨 frame eval 失敗。
- 不能用 jsdom，因為測試需要 IndexedDB。`chrome --headless --dump-dom` 只會抓到「執行中…」，也不能用。
- 腳本存成 repo 外的 `run-tests.mjs`。在那個資料夾執行 `npm i playwright`，再執行 `node run-tests.mjs`：
  ```js
  import { chromium } from 'playwright';
  const b = await chromium.launch({ channel: 'chrome' }); // 或 'msedge'，不必另外下載瀏覽器
  const p = await (await b.newContext()).newPage();
  const noise = /fonts\.(googleapis|gstatic)|ERR_FAILED/; // 擋字型產生的預期雜訊，不算 Demo 的錯誤
  const errs = []; p.on('console', (m) => m.type() === 'error' && !noise.test(m.text()) && errs.push(m.text())); p.on('pageerror', (e) => errs.push(String(e)));
  await p.route(/fonts\.(googleapis|gstatic)\.com/, (r) => r.abort()); // 無網路時避免卡住
  await p.goto(`http://127.0.0.1:8000/tests/records.html?t=${Date.now()}`);
  try { await p.waitForFunction(() => !document.getElementById('sum').textContent.startsWith('執行中'), null, { timeout: 60000 }); } catch { console.log('TIMEOUT = 失敗'); }
  console.log(await p.textContent('#sum'));
  const r = await p.evaluate(() => window.__results || []);
  console.log(r.filter((x) => !x.ok).map((x) => `✗ ${x.name}\n${x.err}`).join('\n'));
  console.log('tests:', r.length, 'console errors:', errs);
  await b.close();
  ```
- plan 裡出現的 Claude 工具名稱，照下表換成對應的寫法：

  | Claude 工具 | 對應寫法 |
  |---|---|
  | `navigate` | `page.goto(url)` |
  | `javascript_tool` | `page.evaluate(...)` |
  | `resize_window` mobile | `page.setViewportSize({ width: 375, height: 812 })`，然後 reload |
  | `read_console_messages` onlyErrors | 用 `page.on('console')` 篩出 error，再加上 `page.on('pageerror')` |
  | 截圖 | `page.screenshot({ path })` |

- 裝不了套件，或連不到 127.0.0.1 時（例如在沙箱裡）：照 §5 第 9 點，分三次請人類跑。拿到證據之前不要 commit Progress。腳本只能寫到暫存目錄時，就放在系統 temp，不要放進 repo。

---

## 12. 中斷復原（接手時先比對）

| 現象 | 判斷 | 處理 |
|---|---|---|
| working tree 有沒 commit 的產品或測試改動 | 實作途中中斷 | **不要丟棄，也不要直接 commit。** 先看 `git diff --stat`。如果改動屬於「▶ 現在」的 Task，而且都在允許清單內，就接著做：<br>1. 補 RED 證據：`git stash push -m "<WID> T<N> impl" -- projectflow-full-demo.html`，把實作收起來，跑測試記下 RED，再 `git stash pop` 還原。<br>2. 跑到 GREEN，從 §3 第 5 步接著做。<br>無法判斷時列給人類看 |
| `git log <merge-base>..HEAD` 已經有該 Task 的 commit（主旨和 plan 一樣），但看板還沒打 ✅ | 中斷在審查或記錄階段 | **不要重新實作。** BASE 取 `git rev-parse <該 Task 第一個 commit>^`，從 §3 第 8 步審查接著做。<br>RED 證據先去 `.superpowers/sdd/task-N-report.md` 或交接紀錄找原文。找不到就在 Task 列註明「RED 證據遺失（中斷復原）」，並在交接紀錄提醒人類 |
| Task 是 ⛔，§6 的 D 已經有結論 | 先前修正輪用完，或之前在等人類 | 先照 PROGRESS §6 前言移除 ⛔，再依結論接著做：已經有該 Task 的 commit，就從 §3 第 8 步開始（可以再開修正輪）；還沒有 commit，就從第 1 步開始 |
| main 的看板是 🔨，但分支不存在 | 中斷在 G3 的第 2 步和第 3 步之間 | 先依 §9 檢查認領。如果 main 的 HEAD 是 `Progress: start <WID>`，從 HEAD 執行 `git checkout -b <分支>` 接著做 |
| 看板是 🟢（包括「等待人類合併」），而分支的 commit 已經在 main 上（`git merge-base --is-ancestor <分支或最新程式 commit> main` 成立） | 中斷在 G5 和 G6 之間，或人類已經自己合併 | 在 main 上做 G6 收尾。如果分支還在，G6 commit 之後再 `git branch -d` |
| 看板已經是 ✅，但已合併的 `feature/*` 分支還在 | 中斷在 G6 commit 之後、刪分支之前 | `git branch -d <分支>`。這個分支不算「進行中的分支」 |
| 有 `.superpowers/` 以外的 untracked 檔案 | 前一個 session 沒有 commit | 列給人類看，不要自己 add 或刪除 |
| 「認領中」殘留 | 前一個 session 沒收尾 | 依 §9 判斷是否過期 |

---

## 13. 展示模式（人類 2026-10-05 指示，PROGRESS D30）

Demo 是展示用的，目標是主要功能能用，不在細節修飾上花時間。PROGRESS「▶ 現在」的「模式」欄寫「展示模式」時適用，**和本文件其他章節衝突時以本節為準**。人類要恢復完整流程時，把那一欄改成「完整流程」；`/pf-next full` 可以單次用完整流程。

**不變的部分**
- AGENTS §3 的硬性規則：`commit()`／`log()`、`can()`、`esc()`、繁體中文、不加外部函式庫、`db.v`／`upgrade()`、只改允許的檔案。
- TDD：照 plan 的測試先跑出 RED、再做到 GREEN，記下 `#sum` 原文。沒有實際跑出結果，就不能說測試通過。
- 手機版：375px 沒有水平捲動（§5 第 7 點的檢查式），console 沒有錯誤（D33：人類要求手機也要能看）。
- Git 規則（§6）、一次只做一個分支、每個 Task 記錄並 commit、交接紀錄。

**減輕的部分**

| 項目 | 完整流程 | 展示模式 |
|---|---|---|
| Task 審查（§3 第 8 步） | spec 和品質兩位審查者 | 一位審查者同時看 spec 和品質 |
| 阻塞標準（§4.1 嚴重度） | Critical、Important | 只有**會讓展示出問題**的才算 Important：功能壞掉或拋例外、資料錯誤或遺失、畫面上看得到的錯誤（`undefined`、`NaN`、版面跑掉）、375px 水平捲動、console 錯誤、安全問題（例如沒有 `esc()`）。其他都算 Minor |
| 修正輪 | 最多兩輪，每輪修完再審 | 最多一輪，修完由審查者再看一次。仍未通過就標 ⛔ |
| Minor | 記進 §5，整體審查時判斷要不要修 | 記進 §5 就好，不修（延到正式版），除非 PROGRESS 指定要修 |
| 補強測試、變異 RED（PROGRESS W2 執行注意 19） | 沒有自然 RED 時要做 | 不做 |
| 待驗證項目 | 審查者列出的都要實測 | 只列和上面阻塞標準有關的項目 |
| 整體審查（G4） | 最多兩輪 | 一輪；有阻塞問題時修一次，再審一次 |
| 驗收清單 | 照 plan 和 spec 詳列 | 照 PROGRESS 精簡後的清單 |
| spec 沒寫到的小細節（§8 第 1、3 點） | 停下來問人類 | **AI 代決**（D32）：照最合理的建議做，在 PROGRESS §6 新增一個 D，狀態寫「AI 代決 YYYY-MM-DD：<結論>（可推翻）」，不標 ⛔，也不停下來。人類事後看 §6 |
| plan-mandated Important（§4.1） | 改成 🟢 之前要有人類結論 | 照審查者建議的修法修，記成 AI 代決的 D |

**仍然要停下來問人類**
- 改範圍：新增或刪掉功能、取消或新增工作項目。
- 要寫新的 spec，或 spec 大幅改版（G1）。
- 改資料版本（plan 已經規定的除外）、引入外部依賴、修改允許清單以外的產品或測試檔。
- plan-mandated Critical。
- push、PR、無法 fast-forward 的合併、`main` 出現不明的新 commit，或任何破壞性的 git 操作。
- 測試回歸查不出原因（§5 第 11 點），或 debugging 修了兩輪仍然失敗。

---

## 附錄 A：交接紀錄格式

```markdown
### YYYY-MM-DD｜<AI 工具與模型>｜<WID> <摘要>
- **做了什麼**：…（commit SHA）
- **驗證**：RED 失敗 x/N → GREEN 全部通過 N/N；瀏覽器實測 …；審查：獨立／自我
- **沒做的事／偏離 plan**：…
- **下一步**：…（與「▶ 現在」一致）
- **注意**：…（陷阱、環境狀態、待人類的 D 編號）
```

## 附錄 B：問題記錄格式（PROGRESS §5）

```markdown
| <WID>-T<N>-m<k>（整體審查：<WID>-F-m<k>） | 描述（附重現方式） | important/minor/trivial | S/M/L | 是（D?）/否 | file:line |
```

## 附錄 C：Implementer 報告格式（只有 Claude SDD 使用：`.superpowers/sdd/task-N-report.md`）

```markdown
Status: DONE | DONE_WITH_CONCERNS | BLOCKED | NEEDS_CONTEXT
Commits: <sha> <subject>
## Implemented
## Tests
- RED：指令＋輸出（失敗 x/N 與失敗的測試名稱）
- GREEN：指令＋輸出（全部通過 N/N）
## UI checks（沒驗到的項目要列出）
## Files changed
## Self-review（§4.1 逐項）
## Concerns
```


## 14. 畢業專題模式（D65）

人類於2026-10-09確認本專案是畢業專題，不作商業產品，採用簡化提案。自本決策起適用正式版後續階段；P2a／P2b已完成紀錄與既定產品權限不變。本節優先於其他章節及舊文件中的流程要求，不自動核准尚未定案的新功能。

1. **短規格與計畫**：每階段一份短文件，合併spec／plan，列出展示目標、範圍／延後項目、基本權限、資料變更、允許檔案、實作步驟及驗收情境。不要求規格、計畫各自雙審。
2. **實作與測試**：取消一般畫面修改與每Task強制TDD；核心流程、資料保存／migration、基本公司與角色權限仍需有效測試。修bug可先補失敗測試；僅文件變更做文件核對，不偽造RED或跑產品全量。
3. **一次獨立審查**：每階段完成後由一位唯讀審查者合併檢查規格與品質，取消每Task雙審。只阻擋展示主流程失效、資料遺失、基本權限／安全問題及漏做已承諾的展示功能；小問題記錄後續。修正後只複核改動與受影響情境，不重讀所有歷史文件。無獨立審查可用時如實記錄，不冒稱已審。
4. **一次完整回歸**：每階段候選版本跑一次適用的完整驗收，含桌面／手機展示主流程。修正後只重跑受影響部分；合併後不強制再跑整套。依變更補必要的部署／健康檢查，只有新變更、失敗或未解風險才擴大驗證。不重跑既有附件故障矩陣或增加商業級壓力測試，除非本階段改到相關邏輯。
5. **每階段記錄**：README／PROGRESS於階段交付更新一次，記真實結果、限制、下一步；不逐Task額外做進度commit。遇到阻塞、方向變更或中斷仍即時留最小交接，避免遺失工作。測試輸出保持精簡，只讀失敗與摘要。
6. **展示範圍優先**：P2c優先時程→模板→前置阻擋→解鎖；P2d先選一個產業案例串文件與營運資料，AI可先明確標示規則式摘要。少見邊界與進階管理功能於短文件明列延後，不假稱Demo全部功能完成；真模型、ERP等串接仍需另定範圍。
7. **保留規則**：不拆除已完成功能、不重設資料；migration保留舊資料、API基本授權、文字跳脫、秘密不入Git、測試只用隔離環境。單一寫入者、主checkout、唯一feature分支、main凍結、明確git add、ff-only及D50發布規則維持；人類試用簽核不得代勾。不把簡化流程解讀為LAN／商業部署授權。

G0–G6仍可作階段標記：G1/G2合併短文件，G3實作，G4一次獨立審查與適用完整驗收，G5 ff-only，G6文件／必要部署檢查／push。不另建立重複審查或全量驗收關卡。
