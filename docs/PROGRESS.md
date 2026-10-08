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
| 目前工作項目 | **P0完成並發布GitHub main；下一階段P1a後端核心計畫（至P1c已授權）** |
| 模式 | **正式軌完整流程**：Native實作、TDD、每Task獨立審查；正式版安全／重要問題均須解決。Demo歷史展示模式不作為正式版放寬標準。 |
| 下一個動作 | 細化P1a登入／公司隔離／migration／核心API可執行計畫，正常審閱後Native TDD。不要再次詢問是否啟動正式版；D51已授權到P1c。P0已完成發布，不要重做。 |
| 分支 | `main`；P0分支已ff-only合併並依G6刪除，無活動feature分支。舊`paused/p0-formal-product-plan`維持`40f8cc2`備查。 |
| 最新程式 commit | 正式版P0 Task3 `18df1ea`，合併HEAD `435af43`；Demo仍為W6 `0934e48`，未修改。 |
| 行號基準 | `dfc0126`。§5「位置」欄和 §3「執行注意」的行號都以這個 commit 為準，此欄固定不改。程式改動後行號會位移，請用函式名或程式片段搜尋 |
| 測試基準 | 2026-10-08 P0合併後：pytest `8 passed, 1 warning in 0.48s`、Vitest `6 passed (6)`、Playwright `4 passed (968ms)`、build均exit0；真DB中斷／恢復、同volume、1280／375px、5秒逾時與遲到回應已驗證。Demo仍`全部通過 174/174`，本輪再次實跑、page errors空。 |
| 資料版本 | Demo `db.v = 6`與key `projectflow-demo-v2`不變；正式PostgreSQL17僅健康探測，尚無業務schema／migration（P1a引入）。 |
| 認領中 | 無；P0執行與獨立審查已結束 |
| 阻塞／待人類 | 無P0阻塞。下一階段先細化P1a計畫並審閱，D51整體授權不變；D43、D10不擴大MVP。 |
| 遠端 | 2026-10-08已成功push origin main `4539e41..981362f`，ls-remote確認，包含完整P0與G6；本筆發布紀錄隨後同步。僅main，無force／PR／其他分支。 |

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
   - **Demo 驗證軌（保留參照）**：單檔 `projectflow-full-demo.html` 的F1–F11及W6已完成Demo驗證，P0不修改。
   - **正式產品軌（D51／D52已啟動）**：React + TS、FastAPI + PostgreSQL、內網部署；本輪到P1c。
     - README §8 的勾選框只用來追蹤正式版。Demo 已經做出來的功能**不能**拿去勾階段 1–9。
     - 何時啟動由人類決定（D11）。啟動後第一個工作項目是 P0。
3. **目前里程碑**：依序完成 W1 → W2 → W3（精簡版，D31／D42），讓 Demo 具備可自行新增、編輯、套用工作流的功能架構。2026-10-05 起依 D42，個別工作流內容之後由使用者自行添加；D41 的兩份現有專流只作內建範例與測試素材。
   - **Demo歷史展示模式**（D30，2026-10-05）：當時範圍僅Demo，W4取消、W5精簡；2026-10-08 D51／D52已另授權正式P0至P1c，正式軌恢復完整審查與安全標準。Demo歷史minor不自動擴張目前plan。
4. **Demo 驗證軌的完成條件**（2026-10-05 依 D30 精簡）
   - [x] W1、W2、W3（精簡版）都是 ✅
   - [x] W5 ✅：README §1 快速開始、§2 功能總覽反映 full demo 的現況
   - [x] 用 W3 的工作流架構新增／編輯／套用一套工作流，並以 yu、chen、ming 各走一次主要流程，桌面和 375px 都沒有水平捲動，console 沒有錯誤（2026-10-05 Claude 在 `cfd5f72` 上實測：it 新增、編輯、複製工作流；yu 用「筆電新機種專流」建立專案（9 階段、44 個任務），第二階段任務被 G0 擋下，覆寫閘門後可開始；yu、chen、ming 的看板、時程、成員、我的任務、模板庫在 1280 與 375px 都沒有 `undefined`／`NaN`／「? —」、沒有水平捲動，console 沒有錯誤。小問題記成 §5 DEMO-A-m1–m4，D43 待人類）
   - [ ] 人類確認可以拿來展示（README §8 階段 0 的驗收：「能用 Demo 向他人完整說明產品概念」）
   - 原本的「W4 全部 FIXED」「D4–D8 都有結論並執行」兩項，2026-10-05 依 D30 移除（W4 取消，D4–D8 維持現狀）。

   全部達成後，AI 在 §7 寫一份「Demo 軌結案摘要」（完成項目、遺留問題、建議的 P0 和 P1 範圍），並把 D11 標成「待人類（可決定）」。

---

## 2. 工作佇列（由上往下執行）

| 順位 | ID | 工作項目 | 狀態 | Spec | Plan | 資料版本 | 依賴 |
|---|---|---|---|---|---|---|---|
| 1 | W1 | 子任務置頂回報卡 | ✅ | [spec](superpowers/specs/2026-10-01-subtask-report-card-design.md)（`3a24c52`） | [plan](superpowers/plans/2026-10-01-subtask-report-card.md)（`ed3e24f`） | 維持 v3 | F11 ✅ |
| 2 | W2 | 部門模型 | ✅ | [spec](superpowers/specs/2026-10-01-department-model-design.md)（`edf46b6`，`dfc0126` 修訂 §4.1 和範本段，以 HEAD 版本為準） | [plan](superpowers/plans/2026-10-01-department-model.md)（`dfc0126`） | v3 → v4 | W1 已合併（D1）；2026-10-05 已 ff 合併進 `main` |
| 3 | W3 | 工作流架構（**精簡版**，D31／D42）：工作流模板 CRUD、從工作流建立專案、關卡擋住後續階段 | ✅ | [spec](superpowers/specs/2026-10-05-process-control-design.md) | [plan](superpowers/plans/2026-10-05-workflow-architecture.md) | v4 → v5 | 2026-10-05 完成；依 D42 先完成功能架構，個別工作流內容由使用者之後自行添加 |
| 4 | W4 | F11 遺留問題清理 | ✖ 取消（D30，人類 2026-10-05 指示展示模式） | — | — | — | F11-N1 併入 W2 整體修正；其餘 §5 項目延到正式版；D4–D8 維持現狀 |
| 5 | W5 | README 對齊現況（**精簡**，D30：只改 §1 快速開始、§2 功能總覽） | ✅ | — | — | — | 2026-10-05 完成；full demo 定位文字由 AI 起草，D12 改為待人類可推翻 |
| 6 | W6 | 多公司產業範例：五個獨立公司空間、產業化工作流與營運資料 | ✅ 本地 main 已完成（D46；`0934e48`） | [spec](superpowers/specs/2026-10-08-multi-company-industry-demo-design.md) | [plan](superpowers/plans/2026-10-08-multi-company-industry-demo.md) | v5 → v6 | W3、W5 ✅；2026-10-08 全部獨立審查通過並 ff-only 合併 |
| — | P0 | 正式軌技術骨架與規則 | ✅ 已發布GitHub main | [MVP範圍](superpowers/specs/2026-10-05-formal-product-mvp-design.md) | [P0可執行計畫](superpowers/plans/2026-10-08-p0-formal-foundation.md) | Demo維持v6 | 三Task與G4獨立審查通過，合併後API8／React6／E2E4與build通過 |
| — | P1a–P1c | 正式版MVP：核心後端、React流程、部署／測試／驗收 | 已授權；下一步P1a計畫（D51） | [MVP範圍](superpowers/specs/2026-10-05-formal-product-mvp-design.md) | 各階段開工前細化 | 正式DB另管migration | P0已完成；P1a→P1b→P1c，P2以後的真AI／ERP／AD／完整RAG不在本輪 |

**排程規則**
1. 永遠做順位最前面、而且沒有阻塞的項目。
2. 同一時間只能有一個進行中的 feature 分支（WORKFLOW 鐵律 4、§6）。
3. 目前的項目在等人類決定時，用 `git branch --list "feature/*"` 判斷，不要只看狀態符號：
   - **已經有 `feature/*` 分支**：不可以開新分支，也不可以在 `main` 上 commit。只能做不會產生 commit 的準備工作（研究、把草稿放在 `.superpowers/`），或寫好交接紀錄後結束 session。
   - **還沒有分支**（例如 W3 在等 brainstorming，或開工前的 Pre-flight 就被擋下）：可以先在 `main` 上記錄 D，再去做下一個不需要人類決定的項目，例如 W4。
4. 佇列做完了，但 §1 的完成條件還沒達成：不要自己發明工作項目。在本表下方加「建議（待人類排序）」，寫好交接紀錄後結束。
5. 不可以自行開工未授權的P軌；D51已授權P0至P1c，D52已確認P0計畫。
6. 人類在對話中的直接指示優先，但要先寫進看板（WORKFLOW §2「變更與暫停」）。

---

## 3. 工作項目明細

### W1 子任務置頂回報卡 — ✅

> **W1 完成摘要（2026-10-02，給接手者）**：W1 已經合併進 `main`。接手時只需要讀這一段，下面的 Task 表、驗收和執行注意是過程紀錄。
>
> **改了哪裡**（`8aed7d6..a9890e1`；產品 +76／−14，測試 +212，README 1 列）
> - `projectflow-full-demo.html`
>   - CSS：新增 `.main.vscroll{overflow-y:auto}`（D15），以及 `.rcard` 系列共 9 行：外框、pend／rej／skip 三種狀態色、`.rc-row`、`.rc-main{flex:1 1 240px}`（D14）、`.rc-sum{max-height:10.2em;overflow:auto}`（D16，約 6 行）、`.rc-acts`。
>   - `enter(id)`：進入葉任務時預設 `ui.tab = 'records'`；回到上層時，如果停在「紀錄」就改成「看板」；換節點時把 `#main` 捲回頁首。
>   - `renderMain()`：改成**先產生內容、再切換 class**（因為 `pageNode` 可能改 `ui.tab`，D17）；節點頁的紀錄、文件、資料、成員分頁加 `.vscroll`；主區域不能捲動時把 `scrollTop` 歸零。
>   - `pageNode()`：新增 `leafTask` 和 `ui.leafPage`。葉任務的「紀錄」分頁排第一；標題下方插入 `reportCardHTML(n)`；標題區的「＋ 新增子任務」主按鈕、跳過提示、恢復按鈕只在非葉節點顯示；葉任務改在 `.tools` 放次要按鈕 `btn sm`「＋ 新增子任務」；子任務變成上層任務、而且停在紀錄分頁時，切到看板（D17）。
>   - 新函式 `reportFieldsHTML(r)`：自訂欄位的 `dl.kv`，由 `reportHTML` 和回報卡共用。
>   - 新函式 `reportCardHTML(n)`：純渲染函式，依序判斷 6 種狀態：已跳過 → 待確認 → 已完成而且有已核准回報 → 已完成但沒有回報 → 最新一版被退回 → 待回報。按鈕只用既有的 `data-restore`、`data-rep-approve`、`data-rep-reject`、`data-report`，沿用既有的委派處理。
>   - `viewRecords(n)`：葉任務的區塊標題改成「回報歷史（N）」，只列歷史。原本的回報按鈕、待確認提示、確認／退回按鈕、跳過提示都移到回報卡。
> - `tests/records.test.js`：新增 20 個測試（44 → 64），涵蓋卡片 6 種狀態、協作身分沒有按鈕、`esc()` 防注入、窄螢幕換行、`enter()` 預設分頁、葉任務頁結構、非葉節點不變、D15 捲動、D16 行數上下限、D17 切到看板與反向案例。和寬度有關的測試會用 `window.frameElement` 暫時把 iframe 撐到 1200px，並在 `finally` 還原。
> - `README.md`：F11 的「位置」列（README.md:414）照 plan Task 2 Step 8 更新。
>
> **刻意沒改的地方**（spec §7，或人類決定維持現狀）
> - 資料結構：`db.v` 仍是 3，沒有升級，舊的 localStorage 原樣可用。
> - 狀態轉換：`submitReport`、`decideReport`、`skipTask`、`restoreTask`、`approversFor`、`canReport` 都沒動。
> - 其他畫面：看板卡片的「✓ 回報」快捷按鈕、審核中心沒動。沒有新增事件處理，diff 裡沒有 `addEventListener`，也沒有 inline `on*`。
> - 非葉節點：上層任務、階段、專案的頁面版面不變。唯一的外觀差異是 W1-T2-m1（第一筆回報上方的分隔線），列為 BY_DESIGN。
> - plan 檔沒有同步 D14–D17 的偏離，以本段和下面的執行注意 13、16、17 為準。
> - README §2 仍寫「紀錄分頁：完成回報…」。§2 屬於 W5 的範圍，W1 不動。
>
> **留到之後的問題**（都不擋後續工作）
> - 歸 W4（§5 OPEN）：W1-T2-m3（捲到底沒有留白）、W1-T2-m4（Windows 切換分頁時寬度差 15px）、W1-T2-m8（相依圖圖例被截掉，W1 之前就有）、W1-F-m5（長網址把回報歷史和筆記撐出主區域，W1 之前就有）。
> - W1-T2-m7（新增第一個子任務後按「復原」，分頁停在看板的空狀態）：OPEN，之後處理，或改列 BY_DESIGN。
> - BY_DESIGN：W1-T2-m1、W1-T2-m5、W1-T2-m9（D18 維持現狀）。
> - 給 D7 的觀察：W1 之後，有硬性前置的葉任務（例如 `t3013`）在卡片上就看得到醒目的「回報完成」，送出時被擋下會遺失草稿，所以 D7 的情況會更常發生。人類決定 D7 時可以列入考量。
>
> **下一個 AI 照計畫要做的事**：W2 部門模型，照 [plan](superpowers/plans/2026-10-01-department-model.md) 執行，先讀 §3 W2 的「執行注意」，特別是第 1、2、14–19 點。Claude 用 `/pf-next`；其他 AI 照 WORKFLOW G3 和 §3 手動做。

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
| 1 | `reportCardHTML(n)` 渲染函式、共用的 `reportFieldsHTML(r)`、`.rcard` CSS。這一步還不接到畫面上 | ✅ | `8aed7d6..dc50e86`（`b678dbd`；修正輪 1 `dc50e86`） | RED `失敗 7/51` → GREEN `全部通過 51/51` → 實際 RED `失敗 7/51`（7 個新測試都是 `reportCardHTML is not defined`）→ GREEN `全部通過 51/51`；修正輪 1：RED `失敗 1/52` → GREEN `全部通過 52/52`；記錄前獨立重跑 `全部通過 52/52`。<br>實測：`reportFieldsHTML` 輸出和舊寫法逐字相同；7 種狀態卡片的 class、外框色、按鈕數正確；h3 margin 0。375px 原本 `.rc-main` 只剩 118／141px（待驗證項目失敗，轉 Important，見 D14），修正後 303px，動作欄換到下方，`dl.kv` 沒有溢出；1280px 維持同一列；console 無錯誤。<br>審查：獨立（spec＋品質各 2 輪，都是 Approved） | `Subtask report card: reportCardHTML renderer and styles` |
| 2 | 把卡片接進 `pageNode()`，包括：分頁順序；`.tools` 加次要的「＋ 新增子任務」；標題區的跳過提示改由卡片顯示；`viewRecords()` 對葉任務只列回報歷史；`enter()` 預設分頁；README F11「位置」列 | ✅ | `f69d282..c4e9e36`（`0d8bf12`；D15 `8103646`；修正輪 1 `c4e9e36`；中間的 `3e59c71` 只改 PROGRESS） | RED `失敗 5/58`（plan 寫 6/57；Task 1 修正輪多 1 個測試）→ GREEN `全部通過 58/58` → 實際 RED `失敗 5/58` → GREEN `全部通過 58/58`；D15：RED `失敗 1/59` → GREEN `全部通過 59/59`，RED `失敗 1/60` → GREEN `全部通過 60/60`；修正輪 1：RED `失敗 3/63` → GREEN `全部通過 63/63`（iframe 1235px 和 345px 各跑一次）；記錄前獨立重跑 `全部通過 63/63`。<br>實測：阿明送出、力瑜退回和確認兩條路徑都走過；`t3012` 沒有卡片；375／768／1024／1280px 都通過檢查式；D15 讓 1280×720 的紀錄分頁能捲到底。第 1 輪審查的 Verify 1 實測失敗（切到相依圖停在 43px），轉 Important，修正輪 1 修好（看板、時程、相依圖都回到 0）。D16：1366×650 下卡片最高 229px，分頁列一定在畫面內；剛好 6 行沒有捲軸，縮放 0.67–2 倍也一樣。D17：「建立」「建立並繼續新增」「改用模板」、標題區「套用模板」、AI 副手「搜尋過去任務」都會切到看板。手機版不會被強制回到頁首。console 無錯誤。<br>審查：獨立（spec＋品質各 2 輪，都是 Approved） | `Subtask page: pinned report card, records tab first, secondary add-child button` |
| — | 整體審查 | ✅ | 第 1 輪 `8aed7d6..44df43a`：With fixes（沒有 Critical／Important，6 項 Minor）→ 整體修正 `26ea8eb`→ 第 2 輪 `44df43a..a5e2b7c`：**Ready to merge: Yes**（沒有 Critical／Important，2 項 trivial：W1-F-m3、m4） | 整體修正：補強斷言，加 1 個測試。這些測試是在補強已經正確的行為，沒有自然的 RED，改用變異 RED 證明鑑別力：暫時把程式改壞 10 處（拿掉「等待 {確認人}」、無條件捲回頁首、`renderMain()` 改回先切 class、拿掉 `ui.tab === 'records'`、摘要上限改 8.5em、狀態優先序、「需填」列出選填、拿掉「自行確認」、送出者、退回人），每一處都是 `失敗 1/64` 或 `失敗 2/64`，而且由新斷言抓到；改回後和備份逐位元組相同，沒有 commit → GREEN `全部通過 64/64`（iframe 0、343、1393px 各一次）。<br>另外修了 2 個新斷言的問題：D16 下限在 iframe 寬 0 時會因為橫向捲軸少 15px，改成和 D15 測試一樣先把 iframe 撐到 1200px；「已完成優先於退回」原本只驗「✓ 已完成」，「已完成，未附回報」也會通過，改成驗「確認：陳主管」而且沒有「未附回報」。<br>`git diff -w --stat main` 和 `--stat` 相同（W1-T1-m1 已改回）。審查：獨立（第 1 輪）<br>第 2 輪的 Verify 都實測過：(1) 用 CSS zoom 模擬 1.1／1.25／1.33／1.5／0.9 倍，`scrollTop` 會是小數（例如 409.6000061035156），但重新渲染前後的值完全相同，所以 `eq` 精確比較是穩的；(2) 375px 送出 15 行中文摘要，`.rc-sum` 沒有橫向捲軸，檢查式是 true。換成沒有空白的長網址，卡片內會橫向捲動，卡片右緣 359px，但紀錄分頁的回報歷史把主區域撐到 1144px。`main` 上也一樣，所以是 F11 原本就有的問題，登記為 W1-F-m5；(3) 在 `1978dde` 上獨立重跑 `全部通過 64/64`（iframe 1393px），console 無錯誤。審查：獨立（2 輪） | `Subtask report card final review fixes: …` |

**驗收**（spec §8、plan Task 2 Step 7）。第 2–6 項是 2026-10-02 在 `44df43a` 上實測的；`26ea8eb` 的產品程式只有兩處不改變行為的整理，所以沒有重測
- [x] `tests/records.html` 顯示 `全部通過 64/64`。新增的 20 個測試（plan 的 13 個，加上 Task 1 修正輪的窄螢幕換行測試、D15 的 2 個、Task 2 修正輪 1 的 3 個、整體修正的 1 個）要涵蓋：卡片各種狀態、協作身分沒有按鈕、`enter()` 預設分頁、葉任務頁結構、非葉節點不變、`esc()` 防注入，以及 D15–D17 的行為
- [x] 瀏覽器實測阿明的流程：打開 `t30121` 直接看到「完成回報」卡；送出後卡片變成「v1 等待確認」，只顯示「等待 … 確認」（實測顯示「等待 力瑜、陳主管、資訊室 確認」）
- [x] 瀏覽器實測力瑜的流程：在同一張卡上按「確認完成」。退回路徑也要測一次（spec 寫的是確認，plan 測的是退回，兩條都要走）（兩條都走過；重新回報時對話框預填 v1 內容和退回意見）
- [x] `t3012`（非葉節點）沒有回報卡，版面不變
- [x] 375px 寬度下沒有水平捲動（用 WORKFLOW §5 第 7 點的檢查式），console 沒有錯誤（46 個頁面和分頁組合）
- [x] `db.v` 仍是 3，沒有新增事件處理

**執行注意**（2026-10-01 研究結果，錨點已在 `dfc0126` 上逐一核對過）
1. Task 2 Step 2 的 RED 實際上是 `失敗 5/58`（plan 寫 6/57；Task 1 修正輪多了 1 個測試）。「非葉節點不變」那個測試在改程式之前就會通過，這是正常的。
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
12. **D3（2026-10-01）**：人類指示「完成後上傳到GIT」。W1 完成 G5 合併與 G6 收尾後，執行 `git push origin main`（不 force，也不 push 其他分支），然後更新「▶ 現在」的「遠端」列。這次授權只限 W1。
13. **Task 1 修正輪偏離 plan（D14）**：`.rcard .rc-main` 是 `flex:1 1 240px`，不是 plan Step 3 的 `flex:1`。原本的寫法 flex-basis 是 0，`.rc-row` 的 `flex-wrap:wrap` 永遠不會換行，375px 下文字欄只剩 118–141px。Task 2 和整體審查都**不要改回去**。D14 已決定接受（2026-10-01）；plan 不另外同步，以這一條為準。
14. **Task 2 必驗**（Task 1 審查留下的待驗證項目）：
    - 按鈕點擊流程：阿明送出；力瑜確認和退回。已列在驗收清單。
    - 卡片在實際頁面中的位置：375px、768px，以及桌面寬度下 AI 面板開和關。
    - **桌面高度**：節點頁的 `.main` 是 `overflow:hidden`，`.view` 不會捲動，所以 F11 的紀錄分頁本來就會被截掉（§5 W1-T1-m6）。Task 2 接上回報卡、葉任務預設進紀錄分頁之後，要在 1280×720 實測回報歷史、筆記、附件能不能完整看到或捲動得到，長摘要（約 15 行）也要測。**D15 已決定在 W1 修**（2026-10-01）：Task 2 的修正輪讓節點頁的紀錄、文件、資料、成員分頁改成整個主區域可以捲動（和手機版一樣，標題和回報卡跟著捲上去），看板、時程、相依圖維持原樣，並附測試。已在 `8103646` 實作：`#main` 加的是 `.vscroll`，只設 `overflow-y:auto`。沒有用原本草擬的 `.scroll`，因為它的權重比手機版的 media query 高，會把手機版的 `overflow-x` 改成 auto。`enter()` 換節點時也會捲回頁首，手機版一樣。
15. Task 1 審查留下的 Minor 是 W1-T1-m1–m5（§5），整體審查時判斷是否要在合併前修。m1（`const st ={` 少一個空白）是編輯工具把 new_string 結尾的空白去掉造成的，建議在整體修正時順手改回。之後用編輯工具替換時，new_string 結尾不要留空白。
16. **D16（2026-10-02 決定）**：卡片上的成果說明最多顯示約 6 行，超過的部分在卡片內捲動，完整內容在紀錄分頁的「回報歷史」。只改 CSS（`.rcard .rc-sum`），放在 Task 2 修正輪 1，附測試。看板、時程、相依圖仍然維持 D15 的「主區域不捲動」。已在 `c4e9e36` 實作：`max-height:10.2em;overflow:auto`（行高 1.7 × 6 行）。
17. **D17（2026-10-02 決定）**：原本是子任務、而且停在「紀錄」分頁時，新增第一個子任務後自動切到「看板」，直接看到新的子任務。從新增子任務對話框「改用模板 / 過去任務…」或標題區「套用模板」建立子任務，也算在內。放在 Task 2 修正輪 1，附測試。已在 `c4e9e36` 實作：判斷寫在 `pageNode()`（`ui.leafPage` 記住上一次畫的子任務頁），所以所有建立子任務的入口都適用；`renderMain()` 改成先產生內容，再依改過的分頁切換捲動方式。
18. **Task 2 審查後實測失敗（品質審查 Verify 1，轉 Important）**：1280×720 下，在 `t301` 的紀錄分頁捲到 300 後切到「相依圖」，主區域停在 43px，麵包屑被切掉，而且捲不回去。原因是相依圖下方的圖例說明超出 `.view`，主區域有可捲動的高度，但桌面版這三個分頁是 `overflow:hidden`。這是 D15 帶出來的問題，放在 Task 2 修正輪 1 處理：主區域不能捲動時回到頁首。已在 `c4e9e36` 修好：`renderMain()` 寫入內容後，主區域的計算樣式是 `overflowY:hidden` 時（只有桌面版節點頁的看板、時程、相依圖）把捲動位置設回 0。可以捲動的分頁和手機版維持原本的位置。
19. **D18（2026-10-02 提出，2026-10-02 人類決定維持現狀）**：卡片上的自訂欄位、退回意見、跳過理由沒有高度上限（§5 W1-T2-m9）。維持現狀，W1 不改；§5 W1-T2-m9 改列 BY_DESIGN。

### W2 部門模型 — 🔍

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
| 1 | 部門資料、v4 升級、顯示改用部門名稱 | ✅ 審查：獨立（spec＋品質兩位審查者；第 1 輪 2 個 Important，修正輪 1 後 scoped re-review Approved）。待驗證都已實測通過：獨立重跑 `全部通過 73/73`；真實 `load()` 讀 v2 資料 → `db.v` 4、10 個部門、模板部門照 D19；p1 看板／時程／相依圖／成員／總覽沒有 `undefined`、console 沒有錯誤；t301 按 AI「加入協作部門」→ `depts` `['d-qa','d-mfg']`、稽核「加入協作部門：品保、製造」；375px 下總覽、成員、我的任務、模板庫、t301、任務對話框（10 個協作部門勾選框）都沒有水平捲動。spec §7 對應：第 1 項「種子資料：v4、10 個部門、任務都有負責部門」；第 2 項「upgrade：v3 → v4 部門對應」「upgrade：模板節點負責部門依序取負責人、第一個協作部門、研發」 | `670afaf..7d48d40`（`e62b39a` 實作、`7d48d40` 修正輪 1：AI 工作量排除未指派、採購單驗收模板改存部門 id、D19 升級順序） | 5（實際 9，修正輪 +4）：RED 失敗 6/69 → GREEN 全部通過 69/69；修正輪 1 RED 失敗 4/73 → GREEN 全部通過 73/73 | 69（實際 73） |
| 2 | 可見性：只有相關的人看得到；移除「顯示全部」 | ✅ 審查：獨立（spec＝Opus、品質＝Sonnet，第 1 輪都 Approved；plan-mandated Important 記成 D20，spec 沒寫的情況記成 D21；修正輪 1 後 scoped re-review Approved）。修正輪 1：照 D20 改 `seeTask`、照 D21 做空狀態並替 `ctxProject()` 呼叫端加防護、補 spec §7 第 3 項和各條規則的鑑別測試（4 次變異 RED 各只讓對應測試失敗 `失敗 1/90`，還原後 `cmp` 相同）。待驗證都已實測：獨立重跑 `全部通過 90/90`；小安在 p1e 看板只顯示「這裡沒有與你（小安）相關的任務。」、沒有 `#showAllChk`；小安的 p1 時程 5 個階段列都在、沒有 t30122；ming／an／lin／chen 開總覽、我的任務、審核中心、t301 紀錄都沒有錯誤；render 平均 19–63ms，和 yu（不走可見性判斷）同一量級；375px 下 ming／an 的看板、時程、相依圖、成員、t30121 和空狀態都沒有水平捲動；console 沒有錯誤。spec §7 對應：第 3 項「已指派：負責人、部門主管…」「同部門成員看不到…」「單一規則：只靠…」4 個；第 4 項「未指派且部門沒有主管：只有專案負責人與系統管理員」；第 5 項「路徑：負責子任務的人看得到上層…」「未指派的子任務：負責上層任務的人也看不到」「路徑：…（D20）」 | `c2fefcc..0b981dd`（`ebab1e1` 實作、`0b981dd` 修正輪 1） | 8（實際 17，修正輪 +9）：RED 失敗 8/81 → GREEN 全部通過 81/81；修正輪 1 RED 失敗 4/85 → GREEN 全部通過 85/85，補強測試後 `全部通過 90/90` | 81（實際 90） |
| 3 | 操作權限 `canWork`、指派、改部門 | ✅ 審查：獨立（spec＝Opus、品質＝Sonnet，第 1 輪都是 Needs fixes；spec 沒寫的兩處記成 D23、D24；修正輪 1 後 scoped re-review Approved）。修正輪 1：協作人員與協作部門主管的筆記附件改用 `canNote`（執行注意 28）、`records.test.js`「成員不能拖曳已跳過的卡片…」改由小安驗證（變異 RED `失敗 1/101`）、D23 任務時程跟 `canWork`（鎖定欄位改成 `sch && can('override')`）、D24 範圍內審核人可以寫筆記、readonly 不能寫筆記、補鑑別測試（`case 'edit'` 變異 RED `失敗 3/101`）。待驗證都已實測：獨立重跑 `全部通過 101/101`；yu／chen／ming／lin 的成員頁權限表都是 10 列 × 7 欄、沒有 `undefined`；t3012 看板上 ming 的 t30121 可拖、t30122 不可拖，chen 相反；lin 在 t402 沒有可用的「回報完成」、有筆記附檔欄；375px 下成員頁、t402、t30121 和任務對話框都沒有水平捲動；console 沒有錯誤。spec §7 對應：第 6 項「canWork：負責人、部門主管、專案負責人、系統管理員」「協作人員可以寫筆記，但不能送回報、不能改狀態」「協作部門主管：不能操作，但可以寫筆記（含附檔）」；第 7 項前半「指派負責人與改負責部門的權限」（後半在 Task 5） | `accb179..717b359`（`0a9086a` 實作、`717b359` 修正輪 1） | 5（實際 11，修正輪 +6）：RED 失敗 4/95 → GREEN 全部通過 95/95；修正輪 1 RED 失敗 5/101 → GREEN 全部通過 101/101 | 95（實際 101） |
| 4 | 部門管理面板：新增、修改、刪除 | ✅ 審查：獨立（spec＝Sonnet Approved；品質＝Sonnet Needs fixes：「我的任務」標題的部門名稱沒有 `esc()`，Task 4 開放改名後變成可利用的 XSS；修正輪 1 後 scoped re-review Approved）。修正輪 1：`<h2>${esc(t)}…`（RED 失敗 1/111），補稽核、非管理員修改、清除主管、單一條件刪除、面板唯讀的測試（變異 RED：拿掉 `deptUsage` 的協作部門條件 → `失敗 1/111`，還原後 `cmp` 相同）。待驗證都已實測：獨立重跑 `全部通過 111/111`；模態對話框裡的錯誤 toast（例如「已有同名部門」）看得見；1280px 下部門表沒有內部捲動、每列約 50px；各部門「任務」數的組成（品保 29 = 負責 9 + 協作 2 + 模板節點 18；只因模板而刪不掉的是製造）；console 沒有錯誤。spec §7 對應：第 8 項「刪除部門：有任務或人員時拒絕；空部門可以刪除且可復原」「刪除部門：只被協作部門、只被模板、只有人員時，分別拒絕」 | `a5c7430..4f428fc`（`bbe808c` 實作、`4f428fc` 修正輪 1） | 5（實際 10，修正輪 +5）：RED 失敗 5/106 → GREEN 全部通過 106/106；修正輪 1 RED 失敗 1/111 → GREEN 全部通過 111/111 | 106（實際 111） |
| 5 | 任務的負責部門和負責人：對話框、看板、我的任務、總覽 | ✅ 審查：獨立（spec＝Opus、品質＝Sonnet，第 1 輪都是 Needs fixes：ERP 證照、配方重做、會議待辦三個 `addNode` 呼叫端沒傳部門，負責人被靜默清空；`saveEditor` 沒用 `can()` 把關；快速新增的預設負責人會變成未指派；修正輪 1 後 scoped re-review Approved）。修正輪 1：三個呼叫端傳負責人所屬部門（配方重做傳原部門）、`saveEditor` 依 `can('dept')`／`can('assign')` 決定是否採用表單值、快速新增預設取第一個屬於部門的人並保留明確的「未指派」、XSS 測試補已指派分支與 `deptOpts`（兩次變異 RED 各 `失敗 1/123`）、未指派上層的提示寫「未指派・部門」。待驗證都已實測：獨立重跑 `全部通過 123/123`；375px 下看板、我的任務（含 chen 的「待我指派」）、總覽、任務頁都沒有水平捲動；console 沒有錯誤。spec §7 對應：第 7 項後半「任務對話框：負責人只列出部門成員；換部門會清空不屬於新部門的負責人」「任務對話框：部門主管可以指派但不能改部門」 | `08c677b..9a7c438`（`e1e5b23` 實作、`9a7c438` 修正輪 1） | 6（實際 12，修正輪 +6）：RED 失敗 6/117 → GREEN 全部通過 117/117；修正輪 1 RED 失敗 6/123 → GREEN 全部通過 123/123 | 117（實際 123） |
| 6 | 時間軸預設收合，並可依部門篩選 | ✅ 審查：獨立（展示模式單一審查者 combined，第 1 輪 Approved、spec compliant，沒有修正輪；7 個 minor 記成 W2-T6-m1–m7，implementer 的兩項 AI 代決記成 D34、D35）。照執行注意 30 加上 `ui.tlDept` 指到已刪除部門時退回 `'all'`（plan 沒有）。實測：記錄者在 `7939a66` 上獨立重跑 `全部通過 129/129`（console 沒有錯誤）；桌面 1400×900 預設列 p1a–p1e，「品保」篩選後階段件數 1/0/2/3/0、上層 t301／t3012 淡色路徑、只剩 1 條箭頭，p4（沒有階段）不收合；真實刪除部門流程（admin 新增「測試部」→ 篩選 → 刪除 → 切回時程）退回「全部」、列 p1a–p1e，工具列和 toast 的復原都沒有錯誤；品保篩選中拖 t30122 +14 天（連動順延開啟），被篩掉的 t3013、t302、t401、t502、t503 都有順延，「↶ 復原」後全部日期回原值、篩選和展開狀態保留；375×812 篩選列換 3 行，`.tl` clientHeight 306、可捲到 p1e，§5 第 7 點檢查式 true；console 都沒有錯誤。沒有驗：Firefox／Safari 的 `:has()`（W2-T6-m2） | `af9a3b9..7939a66`（`7939a66` 實作） | 6 → 實際 RED 失敗 6/129 → GREEN 全部通過 129/129 | 129（實際 129） |
| 7 | 範本帶入負責部門、更新 README | ✅ 審查：獨立（展示模式單一審查者 combined，第 1 輪 Approved、spec compliant，沒有修正輪；5 個 minor 記成 W2-T7-m1–m5，implementer 回報的既有 375px 對話框內捲動記成 W2-T7-m6，implementer 的 5 項 AI 代決記成 D36–D40）。照執行注意 31：W2-T1-m7 拿掉 `window.applyTemplate` 包裝、改斷言新節點的 `dept`／`depts`（測試改名「採購單建立驗收任務：協作部門存 id，新任務的負責部門都是品保」，總數不變）；README「修改時程」列反映 D23，F6 改成「待我指派」（W2-T5-m9）；`applyTemplate`／`nodeToTemplate` 照 plan 用 `TAG_DEPT`（D19 只限 `upgrade()`）。照 plan 的行為變化：模板節點沒有 `who` 時負責人改成未指派（不再帶 `ui.me`），採購單「建立驗收任務」的 5 個任務都是品保的未指派任務（W2-T7-m4）。實測：記錄者在 `03c9ff5` 上獨立重跑 `全部通過 133/133`（iframe 確認是新版 `applyTemplate`，console 沒有錯誤）；驗證者以小安（非主管成員）在 t703 真實點擊套用「送驗流程」並取消預設負責人 → 節點 65→78，新根節點 dept d-qa、13 個後代 owner 全是 null，小安看得到的新節點 0 個、看板顯示空狀態；採購單「建立驗收任務」後按 toast「開啟」只出現 `toast warn`「你沒有檢視此節點的權限」、頁面不跳轉；t703 七個分頁、overview／mytasks／review／ops／templates／aigov／audit、p1／p1c／p3 各分頁 render 都沒有例外、沒有 `undefined`／`NaN`；375×812 下 t703、ops 檢查式 true。implementer 另測：模板庫預覽 32 列沒有 `undefined`、依範本建立專案的 16 個任務 owner 全是 null 且 dept 照 `PHASE_TEMPLATE`、另存模板每個節點都有 dept、AI 任務拆解不拋例外、375px 模板庫和套用對話框檢查式 true；console 都沒有錯誤。沒有驗：截圖 | `c52e39b..03c9ff5`（`03c9ff5` 實作） | 4 → 實際 RED 失敗 5/133（4 個新測試加改寫的 W2-T1-m7）→ GREEN 全部通過 133/133 | 133（實際 133） |
| — | 整體審查 | 🟢 等人類確認合併 | 第 1 輪整體審查（Claude，交接回報）：With fixes，需修執行注意 32 的 4 項，沒有其他阻塞 → 整體修正 `b2f7453`（未指派顯示、卡片負責人不換行、權限表、回報 select 防護）→ Codex 修正後自我再審：Ready to merge: Yes（非獨立審查，依 G5／§11 合併前需人類確認） | 整體修正加 4 個測試：RED `失敗 4/137` → GREEN `全部通過 137/137`（`.superpowers/sdd/final-fix-report.md`）。Codex 2026-10-05 新鮮重跑 `tests/records.html`：`全部通過 137/137`，console error 0；桌面以 yu／chen／ming 點過看板、時程、成員與權限、我的任務，沒有 `undefined`／`NaN`／`? —`；375px 看板、時程、成員與權限 `main.scrollWidth <= clientWidth`，console error 0 | 137（實際 137） |

預期總數是研究時推算的，plan 本身只寫「全部通過 N/N」。以實際跑出來的數字為準。W1 最後共有 20 個測試（plan 的 13 個，加上修正輪和整體修正的 7 個），基準是 64，上表已經照這個數字調整（2026-10-02，W1-F-m1）。W1 如果還有修正增加測試，要再調整。W2 Task 1–5 的修正輪分別多了 4、9、6、5、6 個測試，Task 6 以後的預期總數已經 +30（2026-10-02）。

**驗收**（2026-10-05 依 D30 精簡）
- [x] `tests/records.html` 全部通過（W1 的 20 個測試加上 departments 的測試）：2026-10-05 Codex 在 `b2f7453`、8001 重跑，`全部通過 137/137`，console error 0
- [x] 先按「重置 Demo 資料」，再以 yu、chen、ming 各點過看板、時程、我的任務、成員與權限頁，畫面沒有 `undefined`、`NaN` 或「? —」這類錯誤，console 沒有錯誤：Codex 用 Browser locator 實測通過（我的任務列入同一輪點選；console error 0）
- [x] 未指派、而且所屬部門沒有主管（製程）的任務 `t504`，只有 yu 和 it 看得到：`departments.test.js` 已覆蓋；`final-fix-report.md` 另記錄 `visible(t504)` 只有 yu 為 true（系統管理員 it 依規則可見）
- [x] 時間軸預設收合；`ui.tlDept = 'd-qa'` 時階段列數不變，工作列只剩品保的任務：Task 6 測試與驗收已通過；`departments.test.js` 覆蓋「部門篩選只影響工作列，階段列保持完整」
- [x] README 的 F6、§2、§5 已經照 plan Task 7 Step 7 更新：Task 7 已更新 F5/F6/§2/資料模型；README 頂部「目前進度」摘要仍停在 Task 5，已列 W2-T7-m1／W2-T7-m2 或 W5 範圍，不擋展示模式合併
- [x] 375px 寬度下沒有水平捲動：Codex 以 viewport 375×812 驗證 p1 的看板、時程、成員與權限，`main.scrollWidth <= clientWidth`，console error 0
- 移除的項目（D30）：spec §7 逐項列出對應測試名稱（升級和可見性等規則都已經有測試）；yu、chen、an、ming、it 各截一次圖（改成上面 3 個身分點一遍）；v3 → v4 升級的手動實測（`upgrade()` 已有測試，Task 1 也實測過 v2 真實載入）

**執行注意**（W1 先做的情況）
1. **唯一的程式衝突**在 Task 2 Step 4.3 的 `.tools` 那一行。W1 會在那裡加 `leafTask` 的次要按鈕，這一步**只刪掉 `${mineTool}`**，保留 W1 的按鈕。
2. W1 的 20 個測試在 W2 全程都必須通過。只要有一個失敗，就是真的回歸。
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
14. **W1 已合併（2026-10-02，`a9890e1 Progress: W1 done`）**：Pre-flight 的基準測試應該是 `全部通過 64/64`。不符時照 WORKFLOW §5 第 11 點處理，不要開工。
15. **W1 讓行號往後移了**：本節第 10 點和 plan 的行號都以 `dfc0126` 為準。目前大約是：`load`／`upgrade`／`shown`／`can` 一帶 +10（例如 `load` 652→662、`can` 734→744），`resetAll` +10（972→982），`pageNode` +20（1322→1342），`pageNode` 之後到 `viewRecords` 之前 +26（例如 `graphLayout` 1698→1724、`viewGraph` 1732→1758、`openEditor` 2361→2387、`applyTemplate` 2566→2592），`reportCardHTML` 之後 +62。請用函式名或程式片段搜尋，不要依賴行號。
16. **W1 改到、W2 可能碰到的地方**：
    - `.tools` 那一行（目前是 html:1402）開頭是 W1 的 `${leafTask ? …＋ 新增子任務… : ''}`，接著才是 `${mineTool}${tools[ui.tab] || ''}`。Task 2 Step 4.3 照第 1 點只刪 `${mineTool}`。這顆次要按鈕和標題區的主按鈕用的是同一個 `can('create', n)`。W2 如果改了主按鈕的權限判斷，要一起檢查這顆按鈕。
    - `renderMain()` 要維持「先產生內容、再切換 `scroll`／`vscroll` class」的順序，有測試保護（D17）。
    - `pageNode()` 開頭的 `leafTask` 和 `ui.leafPage` 不要拿掉。`resetAll()` 沒有明確清除 `ui.leafPage`，是靠畫 p1 時順便清成 null；Task 6 改 `resetAll()` 時可以順手加上 `leafPage: null`，但不是必要的。
    - 回報卡的確認人名單來自 `approversFor(n)`，它依賴 `can('override', n)`。W1 的測試會斷言 t30121 的卡片寫著「等待 … 力瑜 … 確認」、t3011 寫著「確認：陳主管 2026/09/13 09:05」。W2 改寫權限後，如果這些斷言失敗：
      - spec 沒有要求改變確認人，就是回歸，要修程式。
      - spec 確實要求改變確認人，就是 spec 和測試衝突，依 WORKFLOW §8 停下來問人類。不要直接改 W1 的測試。
17. **測試環境**（2026-10-05 的狀態，主機是人類的 Windows 電腦）：
    - 8000 埠被另一個不是這個 repo 的 python 伺服器占用（2026-10-05 是 PID 16860，回應 `{"detail":"Not Found"}`），不要動它。
    - 8001 埠沒有伺服器（PID 24024 已在 2026-10-02 照人類指示關閉）。照 WORKFLOW §5 第 1 點在 8001 自己啟動，記下 PID，收工時用同一個 shell 關掉。啟動後先用 `curl.exe -s http://127.0.0.1:8001/AGENTS.md` 確認第一行是 `# AGENTS.md`。
    - 2026-10-02 在 `172.22.32.95:8080` 開給同網域同事試用的分享伺服器（PID 27436，服務 repo 外的快照 `C:\Users\User\projectflow-share\`，不是測試伺服器），2026-10-05 實測已經不在了。要重開或更新快照等人類指示。
    - Browser pane 隱藏時，測試頁的 iframe 寬度會是 0。要測桌面或 375px，用 `resize_window` 設定 viewport；W1 和寬度有關的測試會自己撐開 iframe。
18. **編輯陷阱**：
    - 工作目錄是 CRLF。用 python 讀寫檔案時要加 `newline=''`，否則換行會被改掉。
    - 編輯工具會把 new_string 結尾的空白去掉，W1-T1-m1 就是這樣造成的。
    - 改完用 `git diff -w --stat` 和 `--stat` 比對，確認沒有意外的空白變更。
19. **補強測試時沒有自然的 RED**：例如整體修正時補的斷言。可以用「變異 RED」證明測試有鑑別力，W1 整體修正就是這樣做的：
    - 先備份檔案，暫時把程式改壞，記下 `#sum`。
    - 改回後用 `cmp` 確認和備份逐位元組相同，**不要 commit 變異**。
20. **D19（2026-10-02 人類決定「照 spec」）**：`upgrade()` 的 v3 → v4 區塊，模板節點補 `dept` 的順序照 spec §3.4(4)：有 `who` 取其部門 → 否則第一個 `dp`（已轉成 id）→ 再沒有則 `d-rd`，**不用 `TAG_DEPT`**。plan Task 1 Step 8 的 `x.dept = … || TAG_DEPT[x.tag] || …` 以此為準，在 Task 1 修正輪 1 修改並補測試。只限 `upgrade()`：`seed()` 的 `chain`／`mkTpl`，以及 Task 7 的 `applyTemplate`、`nodeToTemplate` 仍照 plan 使用 `TAG_DEPT`。
21. **Task 1 審查補的兩處（plan 漏列，照 plan 自己的規則修，不算新的產品決策）**：
    - AI 風險分析「工作量最重」和 AI 問答「誰／負責／工作量」的 `load[x.owner]` 要排除 `owner === null`，寫法和 `pageOverview` 的 `if (!x.owner) return;` 一致。
    - 採購單「建立驗收任務」（`ds.poTask`）的內聯模板：`dp: ['品保']` 改成 `['d-qa']`，根節點和子節點都加 `dept: 'd-qa'`（Global Constraints 的對應表：品保→d-qa）。
22. **`isHead(uid, id)`**：Task 1 照 plan 寫成 `dept(id).head === uid`，所以 `isHead(null, 沒有主管的部門)` 會回傳 `true`。Task 2、3 呼叫時，`uid` 一律傳使用者 id，不要傳可能是 `null` 的值（例如 `n.owner`）。
23. **D20（2026-10-02 人類決定「照 spec 字面」）**：`seeTask` 的下層規則只看「任一下層任務 `directSee`」，拿掉 plan Task 2 Step 3 的 `|| (d.owner !== null && ancestors(d).some(…))`。結果：ming 負責 t3012 → 未指派的 N → 指派給小安的 D 時，ming 看得到 D、看不到 N（D 在看板和時程上點不到，這是人類接受的結果）。上層規則仍然只套用在已指派的任務。
24. **D21（2026-10-02 人類決定「顯示空狀態」）**：使用者一個專案都看不到時，節點頁的主區域顯示「目前沒有你看得到的專案」，**不要**退回 `projects()[0]` 帶到他看不到的專案；`ctxProject()` 的所有呼叫端（至少 `aiAsk`、`openMinutesConfirm`）要能處理 `undefined`，不可出錯。plan Task 2 Step 4.2 的 `|| projects()[0]` 以此為準。
25. **Task 2 測試補強（spec §7 第 3 項）**：plan 的 8 個測試沒有涵蓋「協作部門含採購的任務」，也沒有任何斷言只靠單一條規則成立（協作人員、負責部門主管、協作部門主管、範圍內審核人），所以在修正輪 1 補上，並用變異 RED（執行注意 19）證明每一條都有鑑別力。
26. **D23（2026-10-02 人類決定）**：`can('schedule', n)` 對**任務**改成 `canWork(n)`（負責人本人、負責部門主管、專案負責人、系統管理員）。審核人對不是自己負責、也不是自己主管部門的任務不能改時程：任務對話框的日期與鎖定欄位要停用，時間軸拖曳也不行。對**非任務**節點（專案、階段）維持 W2 之前的規則：專案負責人、審核人，以及 member 是該節點負責人時。`deps`、`gate`、`override`（含回報確認，W1 的 `approversFor` 依賴它）都不變。這一點推翻 spec §4.4「reviewer 不變」。
27. **D24（2026-10-02 人類決定）**：`canNote(n)` 加上範圍內的審核人（`inReviewerScope(n)`）。readonly 一律不能寫筆記。
28. **Task 3 審查的筆記附件（controller 裁決，不是新的產品決策）**：協作人員與協作部門主管可以寫筆記（spec §4.2「照舊可以新增筆記」，README F11 的筆記「可附檔」），所以 `addAttachments` 帶 `noteId` 時改用 `canNote(n)` 判斷（並確認該筆記屬於這個節點）；不帶 `noteId`（任務附件）仍用 `can('edit', n)`。
29. **`records.test.js`「成員不能拖曳已跳過的卡片來恢復任務」**：和 plan Task 3 Step 3 的三個跳過案例同一個原因（ming 不能再操作 t30122），改成讓小安負責 t30122 再驗證，並用變異 RED 證明「已跳過」防護仍有測試保護。這是 F11 的測試，不是 W1 的。
30. **Task 6 注意**：Task 4 開放刪除部門，`ui.tlDept` 指到已刪除的部門時要退回 `'all'`；`resetAll()` 要清 `tlDept`（第 3 點）。Task 3 之後時間軸拖曳看 `can('schedule')`（D23），不要改回。
31. **Task 7 注意**：`applyTemplate` 改成寫入 `dept` 後，把 §5 W2-T1-m7 的 `window.applyTemplate` 包裝換成直接斷言新節點的 `dept`；README 的 F6／權限表要一起反映 D23（§5 W2-T3-m1、README:242）和 §5 W2-T5-m9（README:265 還寫「我部門被指派的」）。D19 只限 `upgrade()`，`applyTemplate`／`nodeToTemplate` 仍照 plan 用 `TAG_DEPT`（第 20 點）。
32. **整體審查／整體修正**（2026-10-05 依 D30 改寫）：原本要做的 D25、D26 已經取消，維持現狀。整體修正只做下面 4 項（都是展示時看得到的問題），各附一個測試，其他 §5 的 W2-* 都延到正式版：
    - §5 W2-T5-m3：顯示負責人的地方遇到未指派，不要出現「—」或「? —」，改成「未指派」；稽核「負責人改為 未指派（已通知）」拿掉「已通知」。
    - §5 W2-T5-m2：看板卡片的「名字・部門」在窄欄位不要逐字換行。
    - §5 W2-T3-m1：成員與權限頁的權限表要和 D23 一致（審核人的「修改時程」、collab 的「修改時程」）。
    - §5 F11-N1：回報對話框的 `f.options.map` 加 `(f.options || [])` 防護。
    - W2-T5-m9（README:265）和 W2-T1-m7（測試的 `applyTemplate` 包裝）照執行注意 31 在 Task 7 處理（已在 `03c9ff5` 修好，見 §5 已關閉）。
33. **D28、D29（2026-10-05）**：GitHub 的 `main` 已經有 W2 Task 1–5 草稿（PR #1 的 `8041e14`），分支已 ff 到它，本機 `main` 也對齊到它，所以 `main` 是分支的祖先。G5 照常用 `git checkout main` + `git merge --ff-only feature/w2-departments`，不需要另外處理。整體審查的範圍仍從 `670afaf` 算起（`8041e14` 和 `079b035` 的程式相同）。從 GitHub 拿 `main` 的組員會拿到 Task 1–5 的草稿，Task 6、7 和整體修正還沒有進去。
34. **展示模式（D30，2026-10-05 起）**：Task 6、Task 7 和整體審查都照 WORKFLOW §13 做：
    - 一位審查者，最多一輪修正，只擋會讓展示出問題的錯誤。
    - 不補強測試，也不做變異 RED（第 19 點不再適用）。
    - 375px 檢查保留（D33）。
    - spec 沒寫到的小細節由 AI 代決，記成 §6 的 D（D32）。
    - 預期總數照舊：Task 6 是 129、Task 7 是 133，整體修正會再多 4 個左右（第 32 點）。

### W3 工作流架構（精簡版）— ✅

> **W3 完成摘要（2026-10-05，給接手者）**：W3 已完成工作流功能架構。Demo 現在有 `db.workflows[]`（資料版 v5）、工作流模板庫 CRUD、可從工作流建立專案、工作流專案的前序階段關卡會硬性擋住後續階段任務；個別工作流內容之後由使用者自行添加。下一個工作項目是 W5 README 精簡對齊。

- **來源**：W2 spec 開頭的「拆分」段落原本有 7 項。2026-10-05 人類先選「精簡版」（D31），後續又確認 W3 不要只內建某個工作流，而要完成可自行新增／編輯／套用工作流的功能架構（D42）。本項目只做：
  1. 工作流模板 CRUD：階段、任務、負責部門、協作部門、前置條件、階段關卡。
  2. 從工作流建立專案：產生專案、階段、任務、前置條件和關卡。
  3. 關卡硬性擋住後續階段（關卡沒通過，下一階段的任務不能開始或完成）。
  - 資料版本：v4 → v5，新增 `db.workflows[]`。
- **不做，延到正式版**：範本指定關卡的核准人、總經理角色、強制通過關卡與略過整個階段、完成報告必附交付物。W2 spec 列為不在範圍內的應收帳款、人員帳號的新增與編輯也一樣不做。
- **spec 怎麼產生**（D31 取代 D9 的完整 brainstorming）：AI 已把 D41 的兩份現有專流轉寫成 `docs/reference/2026-10-05-w3-current-flow-sources.md`，並依 D42 修訂短版 spec `docs/superpowers/specs/2026-10-05-process-control-design.md`。人類已在對話確認方向。
- **plan**：`docs/superpowers/plans/2026-10-05-workflow-architecture.md`，共 4 個 Task：資料模型與驗證、工作流模板管理 UI、從工作流建立專案、關卡阻擋與驗收。
- **結果**：
  | Task | 狀態 | 範圍 | commit／驗證 |
  |---|---|---|---|
  | 1 | ✅ | v5 工作流資料模型、內建工作流、驗證／統計／clone helper、v2→v5 升級路徑 | `c6d47ce`；RED `失敗 3/140` → GREEN `全部通過 140/140` |
  | 2 | ✅ | 模板庫顯示工作流模板／任務模板兩區，管理員新增／編輯／複製／刪除工作流，JSON 型快速編輯器 | `3102c95`；RED `失敗 4/144` → GREEN `全部通過 144/144` |
  | 3 | ✅ | 從工作流建立專案，產生專案、階段、任務、前置與關卡 | `7ec0695`；RED `失敗 2/146` → GREEN `全部通過 146/146` |
  | 4 | ✅ | 工作流專案的前序階段關卡 pending 時擋住後續階段；375px 基本溢出測試 | `c8b4c3b`；RED `失敗 1/149` → GREEN `全部通過 149/149` |
  | 審查修正 | ✅ | reviewer 指出 owner/admin 可用 generic 前置覆寫繞過 gate；已改成 gate blocker 只能走關卡審核／覆寫流程，並補回歸測試 | `9bb9a52`；GREEN `全部通過 149/149` |
- **審查**：Codex 以 `requesting-code-review` 派 read-only reviewer 審 `6ea8d08..c8b4c3b`。結果：無 Critical；1 個 Important（generic 前置覆寫可繞過 pending workflow gate）已在 `9bb9a52` 修正並重跑測試。最終自我驗證：`tests/records.html?t=1791173758864` → `全部通過 149/149`。
- **下一步**：W5 README 對齊現況（精簡：只改 README §1 快速開始、§2 功能總覽）。W3 feature 分支完成後可 fast-forward 合併到 `main`；人類已在對話中要求「確認後推上去」。

### W4 F11 遺留問題清理 — ✖（取消，D30）

- **2026-10-05 取消**：展示模式下不花時間在細節。F11-N1（回報對話框可能拋例外）併入 W2 整體修正（W2 執行注意 32）；D4–D8 維持現狀；§5 其餘項目留在 OPEN，延到正式版。沒有開過分支，也沒有 spec 和 plan。
- 以下是取消前的規劃，留作正式版參考。
- **範圍**：§5 中狀態是 OPEN、而且「需人類」為「否」的項目。依 WORKFLOW G1 的例外，直接寫 `docs/superpowers/plans/<日期>-w4-cleanup.md`。每個 issue ID 對應一個 Task，每項都要附測試。
- **建議優先處理**：
  - `F11-T1-m3`：upgrade 失敗時會靜默覆蓋使用者資料
  - `F11-N1`：回報對話框會拋例外
  - `F11-T7-m3`：spec 要求的附件快照沒有做
  - `F11-T6-m3`：已刪除節點的申請會永遠卡著
  - `F11-T5-m1`：可以重複送出
  - 補測試類：`T2-m4`、`T3-m4`、`T5-m5`、`T6-m4`、`T7-m4`
- **要等人類決定的**：`T1-m5`、`T4-m2`、`T4-m4`、`T5-m2`、`T6-m1`。這幾項等 §6 有了結論，才能排進 W4。

### W5 README 對齊現況（精簡）— ✅

**2026-10-05 依 D30 精簡範圍**：只改展示時別人會讀的部分，也就是 §1 快速開始、§2 功能總覽（含「已知限制」），以及目錄前面的「給接手的人」段落要和 AGENTS、WORKFLOW 一致。§5、§7、§8 延到正式版。不需要 spec 和 plan，直接在 `main` 上 commit `Docs: …`（沒有 feature 分支時）。下面是原本列出的問題，只處理標「（做）」的：

README 有幾處還停留在階段 0 或 F11 之前的內容，W2 合併後一次整理：
- （做）§1 快速開始沒有提到 full demo 和測試頁。
- （做）§2 功能總覽大多是 petfood Demo 的描述。像「時程（唯讀）」「文件只有標題」「總覽、我的任務未實作」都已經過時，而且缺少 F1–F10 的列。
- （做）§2「已知限制」只適用於 petfood Demo。
- §7 專案結構缺少 `docs/`、`tests/`、`AGENTS.md`、`.claude/`。
- §8 沒有說明 full demo 和正式產品軌的關係。
- §5 `overrides` 的 `target_type` 和 `kind` 語意重疊，而且沒有記載 `restoredBy`、`restoredAt`、`note`。
- （做）目錄前面的「給接手的人：怎麼請 AI 繼續開發」是 2026-10-02 照人類指示新增的。這段不加編號，所以 AGENTS.md 引用的 §4、§5、§6、§9 編號不變。W5 整理時要一併檢查這段和 AGENTS、WORKFLOW 是否一致。

full demo 定位的文字由 AI 起草，人類看一次（D12）。

**完成摘要（2026-10-05，Codex）**：
- README 頂部摘要已改成 W1／W2／W3／W5 完成、W4 取消，並說明 W3 先完成功能架構、個別工作流內容由使用者之後自行添加。
- README §1 已改以 `projectflow-full-demo.html` 為準，補上測試頁路徑，並註明 `projectflow-petfood-demo.html` 是階段 0 存檔。
- README §2 已更新 full demo 功能總覽與已知限制，涵蓋節點、看板、時程、前置與關卡、模板庫、部門權限、我的任務／審核中心、文件紀錄、AI 副手、研發營運資料，以及目前沒有後端／多人同步。
- D12 由 AI 起草完成，狀態改為「待人類可推翻」。

**追加整理（2026-10-05，Codex）**：
- 依人類指定的深色部署圖版型新增 `docs/projectflow-system-architecture.svg`，用青綠／橘／灰色標示 Demo 已完成、正式版待建、外部整合。
- README §6 改成引用該圖，並分成「目前已完成的 Demo 架構」「正式產品軌尚未完成」「下一步判讀」。
- README §7 專案結構補上 `AGENTS.md`、`docs/`、`tests/`、`.claude/` 與架構圖檔。

### W6 多公司產業範例 — ✅

**目標**：把目前以寵物食品製造為主的單公司 Demo，擴充成五個可切換、資料完全獨立的公司空間，證明 ProjectFlow 能套用到不同產業。

**人類已確認的方向（D44）**：
- 固定五家範例公司，不做公司新增、刪除或改名。
- 五家公司是毛研食品、峰曜科技、光點企劃、雲序軟體、築衡工程，涵蓋寵物食品、電子製造、活動行銷、SaaS 與營建工程。
- 每家公司都有獨立的專案、工作流、部門、成員、權限、營運資料、稽核紀錄與目前身分；採平衡版種子資料。
- 左下角在身分切換上方加入公司選單；營運資料按產業切換欄位和內容。
- localStorage key 維持 `projectflow-demo-v2`，資料從 v5 升到 v6；舊資料完整歸入毛研食品。
- IndexedDB 附件按公司隔離；重置只影響目前公司。

**Spec**：`docs/superpowers/specs/2026-10-08-multi-company-industry-demo-design.md`。已完成 placeholder、內部一致性、範圍與歧義檢查。

**Plan**：`docs/superpowers/plans/2026-10-08-multi-company-industry-demo.md`。共 6 個實作 Task、25 項新增測試，最終目標由基準 `149/149` 增至 `174/174`；另有 Task 0 處理基準驗證與 feature 分支建立。

| Task | 內容 | 狀態 | commits | 測試（預期 → 實際） | plan 指定的 commit 主旨 |
|---|---|---|---|---|---|
| 0 | pre-flight、歷史 W3 分支改名、基準測試、建立 W6 分支 | ✅ | BASE `8aaa3ec`；本次 start commit | `149/149` → `全部通過 149/149`；Edge headless，無 page error；8001，PID 4312（本 session 啟動）。W3 ancestor 成立，改名 `completed/w3-workflow-architecture` | `Progress: start W6 implementation` |
| 1 | v6 公司容器、v2–v5 遷移與部分損壞修復 | ✅ | `d879db1..4f3a0e6` | RED `失敗 11/153`（4 項 W6 與 7 項既有版本／路徑）→ GREEN `全部通過 153/153`；審查發現配方陣列缺失／null 成員未修復，補斷言 RED `失敗 1/153` → GREEN `全部通過 153/153`。獨立審查修正後通過；Edge 重載 v5、兩種損壞 v6 都正確，僅重建毛研、保留他公司並顯示提示，無 page error。 | `W6 task 1: add v6 company storage` |
| 2 | 左下角公司選擇器、原子切換與暫態 UI 清理 | ✅ | `40c1f4c..c9689a4` | RED `失敗 4/157`（選擇器、切換、持久化、失敗原子性）→ GREEN `全部通過 157/157`；暫態補測 RED `失敗 1/157` → GREEN `全部通過 157/157`；獨立審查 PASS。1280／375 五公司切換 DOM 無水平溢出；截圖最終驗收再停用轉場檢查。 | `W6 task 2: add company switching` |
| 3 | 五家公司成員、部門、專案、工作流與稽核種子資料 | ✅ | `77e2b5f..9242e35` | RED `失敗 4/162`（最低量、主專案完整、部門、標題）；非毛研引用測試原已通過 → GREEN `全部通過 162/162`。整合修正 riskText 的採購單假設及清 UI 前先找可見專案。獨立審查 Approved；五公司 overview／templates／review／mytasks／audit 及 timeline／people／records 無無效文字／page error，十套工作流驗證合法；375px 側欄截圖已檢視。 | `W6 task 3: seed five industry companies` |
| 4 | 設定驅動的產業營運資料、連結、狀態與條件 | ✅ | `db9a240..56b94dd` | RED `失敗 4/166` → GREEN `全部通過 166/166`；legacy 事件跨公司防護 RED `失敗 1/166` → GREEN `全部通過 166/166`。獨立審查 PASS。四產業 24 分頁於1280／375 無主頁水平溢出，四筆 blocker 均可解除；手機截圖已檢視；無 page error。plan 回歸測試「採購單」改驗既有「採購」，加測七個 F10 分頁。 | `W6 task 4: render industry operations` |
| 5 | 附件公司前綴、舊鍵相容與只重設目前公司 | ✅ | `91f32d4..4e8c309`（實作 `9403a62`） | RED `失敗 4/170` → GREEN `全部通過 170/170`；跨公司上傳／回報補測及一輪審查修正皆 RED → GREEN，最後 `失敗 1/170` → `全部通過 170/170`（第二檔失敗路徑）；独立複審通過。真實上傳同ID、重載、UI確認重設毛研後雲序 blob 仍可讀。既有附件測試改以 metadata.storage_key 讀 blob，保留全部斷言。 | `W6 task 5: isolate attachments and reset` |
| 6 | 跨公司隔離強化、README 與桌面／375px 驗收 | ✅ | BASE `b99eeff`；本次 Task 6 commit | Inventory（編輯前已記錄於 `b99eeff`）：pendingCount/pageReview、condMet/projected/extBars/riskText、secretValues/maskText/aiAsk/aiAction 改 active-only；毛研 opsSuppliers/Materials/Formulas/POs/WOs/Trace/ERP、fCalc、supName/matName、poNext/woNext/erpSync、匯入／配方事件加模式防護；openNewProject/openAddLink、AI plan/suggest 產業化。RED `失敗 3/174` → GREEN `全部通過 174/174`；child-link escaping、375px 配方面板溢出、機密文件 D48 各 `失敗 1/174` → `全部通過 174/174`。獨立 reviewer Rawls 一輪修正後 Approved；最後兩次新時間戳重跑均 `全部通過 174/174`。 | `W6 task 6: harden isolation and document demo` |
| G4 | 全分支整體審查與驗收 | 🟢 | `d879db1` 至 Task 6 | 獨立 reviewer Rawls：With fixes → D48 文件權限、手機配方面板修正後 `Ready to merge: Yes`。Edge 1280／375 共508畫面狀態、10項重載、十套工作流建立、全部角色與營運狀態推進、毛研 F10 驗收通過；console/page errors 空，桌面／手機截圖已檢視。所有Task與G4均獨立審查，無待決 plan-mandated D。 | — |

**驗收**：
- [x] 固定五家公司都能切換，選擇器位於身分上方；切換後使用目標公司的預設專案負責人。
- [x] 每家公司至少有一個完整主專案、一個精簡次專案、兩套工作流、獨立成員／部門／權限／稽核，以及產業營運模組；毛研食品保留既有較豐富的專案與完整 F10。
- [x] v2–v5 升級到 v6 時保留毛研食品的節點、稽核、身分與舊附件 key；部分損壞的 v6 只修補壞公司。
- [x] 公司間的節點、營運資料、AI、權限、稽核、附件與復原紀錄不交叉；localStorage 寫入失敗不半切換。
- [x] 「重設目前公司」不改其他公司或附件；新附件有公司前綴，舊毛研附件仍可開啟。
- [x] 原有 149 項測試在毛研食品空間不回歸；新增 25 項後達 `全部通過 174/174`。
- [x] 五家公司在桌面與 375px 下主要頁面無溢出、重疊、`undefined`、`NaN` 或 console error。

**下一步**：W6 已依 D2／WORKFLOW G5 本地 ff-only 合併；Task 6 commit `0934e48`，整體審查記錄 `f3a61ec`。P0 保留暫停分支，下一個 session 可恢復規劃，不授權 P0 實作。

---

### P0 正式版技術骨架與規則 — ✅ 已發布GitHub main

**授權**：D51已授權做到P1c；D52「好開始」確認P0計畫。Native執行與逐Task獨立審查，正式規則於Task1啟用後安裝依賴。

**開工基準**：`4539e41e92804821d273864fad31f7ccd0e946d6`，working tree乾淨、無feature分支。2026-10-08 Edge實跑`全部通過 174/174`，exit 0、page errors空；本次Demo伺服器8001 PID30892（8000為其他服務，不動）。Demo blob：full `b43ca41781cac4c0da757e21e14d482a22f28cd8`；petfood `847866a8b8a18ec5e32ab865991f24cf3db7a1ff`。15173／18000空閒。

**計畫**：[2026-10-08-p0-formal-foundation](superpowers/plans/2026-10-08-p0-formal-foundation.md)，取代舊MVP outline Task1。P1a–P1c是已授權後續里程碑，不把本次計畫完成當P0完成。

**正式規則已啟用（Task1，安裝依賴前）**：AGENTS／WORKFLOW區分正式版與Demo；正式版僅允許本plan檔案與鎖版依賴，pytest／Vitest／Playwright實跑摘要、後端公司權限與migration、秘密不得入Git，逐Task獨立審查及D50發布保持。Task1 BASE=`e6082f9199e74420f85e8135b2e8f38d0429fed9`。

| Task | 交付 | 狀態 | 驗證預期 | commit主旨 |
|---|---|---|---|---|
| 1 | 正式軌規則、FastAPI存活／真實DB就緒檢查 | ✅ Arendt獨立審查通過，無Critical／Important | 預期新增8項pytest；RED `1 warning, 1 error in 0.81s`，exit 1：缺`app.main`（安裝中pytest不存在不算RED）；GREEN `8 passed, 1 warning in 0.49s` exit0，pip check通過。reviewer另驗9個負向行為通過；真DB留Task3 | `e6082f9..8e84a9b`；`P0 task 1: add formal rules and API health checks` |
| 2 | React狀態介面、載入／失敗／重試 | ✅ Faraday獨立審查Approved，無issues | 預期新增6項Vitest＋build；RED `Test Files 1 failed (1); Tests no tests` exit1，缺`./App`；GREEN `Test Files 1 passed (1); Tests 6 passed (6)` exit0、build exit0、runtime audit零漏洞。lock結構比對一致（初次JSON字串比對誤判順序，已改deepEqual驗證）。逾時／遲到請求留Task3補驗 | `b35ca9d..4a2088b`；`P0 task 2: add React health surface` |
| 3 | Docker Compose、PostgreSQL、桌面／手機與DB恢復 | ✅ Goodall獨立審查Approved，無issues | 預期新增4項E2E；RED `4 failed` exit1：proxy readiness、1280px、375px、unknown API均connection refused；GREEN `4 passed (1.1s)`、恢復後`4 passed (978ms)` exit0。API `8 passed, 1 warning in 0.50s`、React `6 passed (6)`、npm ci／build exit0。真DB與畫面中斷／恢復通過；reviewer另驗HTTP／資產／OpenAPI及部署狀態 | `7b2f806..18df1ea`；`P0 task 3: verify containerized foundation` |

**環境預檢（2026-10-08，只讀）**：Node24.19.0、npm11.17.0、Python3.13.9、Docker Engine29.7.2／Compose5.4.0可用，Docker daemon可連線；15173／18000未被占用。已查npm／PyPI版本並列於plan，未安裝產品依賴。

**P0驗收**：
- [x] 正式軌規則已啟用且Demo檔／測試保持不變（git diff main --exit-code為0）。
- [x] API8、React6、E2E4實際通過，逐Task RED/GREEN見上表。
- [x] 真實PostgreSQL就緒、中斷503、不洩漏連線資訊、恢復成功且volume不被刪除。
- [x] 1280／375畫面可用、資產載入、無水平溢出／意外console error；已看截圖。
- [x] README／正式開發指南／看板更新，三Task與G4獨立審查通過，G5已ff-only合併，合併後完整正式測試通過。G6已完成並push `981362f`，ls-remote核對成功。

**G4**：Hilbert唯讀審查`e6082f9..9b95836`，`Ready to merge: Yes`；無Critical／Important／plan-mandated，P0-T1-m1／m2允許延後。獨立實跑pytest8、Vitest6、型別／production build、pip check、HTTP及資產比對均通過，額外9個API負向案例通過。本次協調者再次Demo `全部通過 174/174` exit0、page errors空；兩Demo blob完全一致。

**Task3實測證據（2026-10-08）**：
- Compose config --quiet、up -d --build --wait成功；API／DB healthy，web正常提供靜態產物，僅127.0.0.1:15173／18000；DB無host埠。Linux pip lock安裝與pip check通過；API UID1000非root。
- plan PowerShell outage probe exit0：live200、ready503且僅`ok=false,database=unavailable`；finally恢復、volume mountpoint相同。另以Playwright實測手機無法連線→恢復重試已連線；expected503 console一則、unexpectedErrors空。5秒逾時→重試成功→釋放舊回應，狀態仍已連線。
- 桌面1280及手機375截圖`web/test-results/p0-1280.png`／`p0-375.png`已目視，圖示、文字、按鈕無重疊；outage截圖已目視（後續E2E會清理測試產物）。暫存probe `%TEMP%/pf-p0-probe.cjs`，關鍵結果已寫本表，接手不依賴暫存檔。
- 工具：Node24.19.0、npm11.17.0、Python3.13.9、Docker29.7.2／Compose5.4.0、Playwright1.64.0／Chromium156.0.8078.4。
- 實測image ID：API `sha256:d0267bda4bd990e4f4c9e1750007f2c2d4cb897a8348a670ee1e1baa02ac9436`；web `sha256:8f04cf46a074f50478d111e30f35bbb9ce97626745c8403f631607ac4c75a154`；PostgreSQL `sha256:b0f9560a2de083e2cc7382e75f808c7381a32852a7ec49117deedb300e552b24`。
- 基礎映像digest：Python3.13-slim `sha256:bf44cdfcb76cd3b41e879bc058fc37ec5872002ccfde7fcb765e218cde0cd79c`；Node24-bookworm-slim `sha256:d6aa754f16b3197301076f047b5def2f02ea1dbbc2ca920407d46d7ec7f87b20`；nginx stable-alpine `sha256:0985e772fb9f729e6fa0980da05fca5d9c468e870eed43071545afa9d2e27d94`。tag為開發方便用途，不宣稱production hardening／離線部署保證。

### P0 規劃文件恢復（歷史紀錄，非 P0 實作）

- **本段範圍**：D49授權從最新main帶回舊spec／plan，保留舊分支；新分支為主線。更新W6／v6／174項測試基準與已批准的公司邊界要求。
- **草稿限制**：舊計畫缺少啟動檔、依賴與完整測試；已撤回「可直接執行」宣稱，列出細化P0前置條件。不改產品、測試、AGENTS或WORKFLOW，不新增正式版目錄。
- **驗證／審查**：`39948a8..a1e84a6`僅四份文件，兩Demo與tests diff空；四文件相對連結missing=[]；`git diff --check`通過。獨立reviewer Planck：`Ready to merge: Yes`。本段不改產品，沒有重跑產品測試；174/174仍引用W6最後實測。
- **發布**：依D50，每段完成均更新README與本看板，審查／驗證後ff-only回main並推送origin/main。不force、不推其他分支、不自動開PR。若遠端有不明新commit或不能ff，依WORKFLOW §8停下確認。
- **下一段**：確認正式版範圍，將P0細化為可執行計畫；這不是P0技術骨架完成。

---

## 4. 已完成

| 項目 | 內容 | 證據 |
|---|---|---|
| 階段 0 | petfood 互動 Demo（`projectflow-petfood-demo.html`） | README §8 階段 0 已打勾 ✅；早於 git 歷史，包含在 `9fdcc64` 裡 |
| F1–F10 | full demo 的多層任務樹、模板、時程編輯、前置條件與關鍵路徑、權限與覆寫、協作、文件與版本、AI 副手（規則式）、分級路由與遮罩（模擬）、研發營運資料（模擬 ERP） | 早於 git 歷史，包含在 `9fdcc64` 裡。F6 的部門目前是寫死的，由 W2 處理 |
| F11 | 任務紀錄與完成回報：回報與審核、自訂回報欄位、筆記、附件（IndexedDB）、主管跳過整個任務、AI 引用紀錄 | [spec](superpowers/specs/2026-09-30-task-records-and-skip-design.md)、[plan](superpowers/plans/2026-09-30-task-records-and-skip.md)；commits `9fdcc64..aebd709`（從 `2fc8f10` 到 `aebd709` 共 10 個：7 個 Task、2 輪修正、1 次整體修正），以 fast-forward 合併進 `main`；測試 44/44。SDD 暫存已歸檔到本機的 `.superpowers/archive/2026-09-30-f11-task-records/`（不在 git 裡；重要內容已整理到本看板 §5） |
| W1 | 子任務置頂回報卡：葉任務頁標題下方固定顯示回報卡（狀態與下一步動作），「紀錄」分頁排第一並作為預設；D15 桌面版紀錄等分頁可捲動，D16 卡片摘要最多約 6 行，D17 新增第一個子任務後切到看板 | [spec](superpowers/specs/2026-10-01-subtask-report-card-design.md)、[plan](superpowers/plans/2026-10-01-subtask-report-card.md)；commits `8aed7d6..2d2c785`（2 個 Task、2 輪 Task 修正、D15、1 次整體修正），以 fast-forward 合併進 `main`；測試 64/64；`db.v` 維持 3。審查全部獨立（每個 Task spec＋品質各 2 輪，整體審查 2 輪）。SDD 暫存已歸檔到本機的 `.superpowers/archive/2026-10-01-subtask-report-card/`（不在 git 裡；重要內容已整理到本看板 §3 W1、§5、§6） |
| W2 | 部門模型：`db.departments` 可設定、預設 10 部門；任務必填負責部門且負責人可未指派；任務可見性與操作權限依負責人、部門主管、專案負責人、系統管理員等規則；時間軸預設收合成階段並可依負責部門篩選；模板帶入負責部門 | [spec](superpowers/specs/2026-10-01-department-model-design.md)、[plan](superpowers/plans/2026-10-01-department-model.md)；commits `670afaf..5f326ab`（Task 1–7、展示模式流程調整、整體修正與等待合併進度），以 fast-forward 合併進 `main`；測試 `全部通過 137/137`；`db.v = 4`。Task 1–5 是完整流程獨立審查，Task 6–7 是展示模式單一審查者，整體修正後由 Codex 自我再審並經人類確認合併。 |
| W3 | 工作流架構：`db.workflows[]`、工作流模板 CRUD、從工作流建立專案、工作流專案的前序階段關卡硬性擋住後續階段 | [spec](superpowers/specs/2026-10-05-process-control-design.md)、[plan](superpowers/plans/2026-10-05-workflow-architecture.md)；commits `6ea8d08..9bb9a52`；測試 `全部通過 149/149`；`db.v = 5`。展示模式單一 reviewer 找到 1 個 Important（generic 前置覆寫可繞過 pending workflow gate），已修正。 |
| W5 | README 對齊現況（精簡）：頂部進度摘要、§1 快速開始、§2 Demo 功能總覽、§6 系統架構圖、§7 專案結構更新到 full demo／W3 後狀態 | 2026-10-05 完成；只改 README／PROGRESS／架構圖，沒有改產品程式。驗證 `git diff --check`。 |
| 規劃文件 | W1 的 spec 和 plan、W2 的 spec 和 plan | `3a24c52`、`ed3e24f`、`edf46b6`、`dfc0126` |
| W6 | 五個公司空間、公司預設身分與原子切換、四產業專案／工作流／營運模組、v6 舊資料遷移與損壞修復、附件隔離與單公司重設、AI／權限／稽核隔離 | `d879db1..f3a61ec`；每Task TDD及獨立審查、整體審查一輪修正後 Ready to merge: Yes；2026-10-08 ff-only 到本地main，合併後174/174，508畫面狀態驗收通過。只為固定Demo，沒有公司CRUD／登入隔離／後端多租戶。 |
| P0 | 正式規則、FastAPI健康檢查、React狀態介面、Compose／真實PostgreSQL骨架與開發指南 | `e6082f9..435af43`；Native三Task TDD及獨立審查，Hilbert G4 Ready to merge: Yes，ff-only合併main。合併後8pytest／6Vitest／4Playwright與build通過，DB故障恢復同volume、桌面手機／逾時重試通過，Demo未變。P1a–P1c尚未實作。 |
| 交接系統 | `AGENTS.md`、`CLAUDE.md`、`GEMINI.md`、本看板、`docs/WORKFLOW.md`、`.claude/workflows/pf-status.js`、`.claude/workflows/pf-next.js`、`.gitignore` | 2026-10-01 建立；commit 用 `git log --grep "Docs: handoff system"` 查 |

---

## 5. 待處理問題（Issue register）

**P0新增**
- P0-T1-m1（minor，OPEN，不阻塞）：`api/tests/test_health.py`缺查詢結果非1、查詢階段錯誤、checker非布林的持續回歸案例；Arendt唯讀補驗均通過，後續擴充API測試時納入。
- P0-T1-m2（minor，OPEN，不阻塞）：Starlette TestClient對httpx提出棄用警告；目前鎖版8項均通過，升級測試依賴時處理，不盲目換版。

- **ID 規則**：
  - F11 的項目來自 F11 的執行紀錄，2026-10-01 已經逐項在程式碼中核對過，共 39 個 ID（N2 已併入 T4-m1）。
  - 之後的工作項目用 `W1-T1-m1`（Task）或 `W1-F-m1`（整體審查）這種格式，詳見 WORKFLOW 附錄 B。
- **嚴重度**：important、minor、trivial。**大小**：S（不到 30 分鐘）、M、L。
- **處理方式**：「需人類」為「是」的項目，要等 §6 有了結論才能動手。修好後狀態改成 FIXED，並寫上 commit。
- **展示模式（D30，2026-10-05 起）**：W4 取消。OPEN 項目只有描述開頭標「【W2 整體修正】」的會在 W2 修，其他都延到正式版；新發現的 minor 也是記下來就好。

### OPEN

| ID | 描述 | 嚴重度 | 大小 | 需人類 | 位置（dfc0126） |
|---|---|---|---|---|---|
| F11-T1-m3 | `load()` 裡的 `upgrade()` 拋出例外時會被靜默吞掉，改用種子資料；下一次 `save()` 就會覆蓋使用者原本的資料。建議先把原始資料備份到另一個 key，並提示使用者 | minor（優先） | S | 否 | html:653-657 |
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
| W1-T2-m3 | 紀錄等可以捲動的分頁，捲到底時最後一個區塊貼齊主區域底部，沒有留白（實測差 0px；手機版本來就是這樣）。修法：`.main.vscroll > .view{flex-shrink:0}`（整體審查建議：歸 W4） | minor | S | 否 | `.main.vscroll`、`.view` CSS（html:64、:114@c4e9e36） |
| W1-T2-m4 | Windows 上同一個節點切換分頁時，捲軸出現或消失會讓主區域寬度差 15px（實測紀錄 663px、看板 678px），標題和卡片左右跳動。修法：節點頁的 `.main` 加 `scrollbar-gutter:stable`（整體審查建議：歸 W4） | minor | S | 否 | `renderMain`（html:1331@c4e9e36）、`.main.vscroll` CSS |
| W1-T2-m7 | D17 只處理「子任務變成上層任務」。新增第一個子任務、自動切到看板之後按 toast 的「復原」，節點變回子任務，回報卡和「紀錄排第一」都恢復，但分頁停在看板，顯示「這個節點還沒有子任務」的空狀態（實測）。符合執行注意 7。可選的修法：D17 切換時記下節點，同一個節點又變回子任務、而且仍停在看板時改回紀錄（整體審查建議：之後處理或改列 BY_DESIGN，不擋合併） | minor | S | 否 | `pageNode`（html:1351@c4e9e36） |
| W1-T2-m8 | （W1 之前就有）桌面版相依圖下方的圖例說明超出主區域，被截掉約 43px（1280×720）。`.graph` 是 `height:100%`，圖例 `<p>` 落在 `.view` 外面。W1 修正輪 1 只確保主區域不會停在偏移的位置。修法例如：讓相依圖的 `.view` 改成直向 flex，或把圖例移到工具列（整體審查建議：歸 W4） | minor | S | 否 | `viewGraph`（html:1773@c4e9e36）、`.graph` CSS（:199） |
| W1-F-m5 | （W1 之前就有）回報歷史和筆記的內文（`.rec .body`）遇到沒有空白的長字串（例如長網址）不會換行，375px 下主區域被撐到 1144px，可以橫向捲動，WORKFLOW §5 第 7 點的檢查式變成 false。`main` 上用同樣的回報實測也是 1144px。筆記（`noteHTML`）用的是同一條 CSS，沒有另外實測。回報卡的 `.rc-sum` 會在卡片內捲動，不受影響。重現：375px，阿明在 `t30121` 送出摘要「參考資料：https://example.com/…」（100 字以上、中間沒有空白）。修法：`.rec .body` 加 `overflow-wrap:anywhere`（`.rc-sum` 也可以一起加），並附 375px 的測試 | minor | S | 否 | `.rec .body` CSS（html:256@1978dde）、`reportHTML`、`noteHTML` |
| W2-T1-m2 | `isHead(uid, id)` 在 `uid` 為 `null`、部門沒有主管時回傳 `true`（plan 程式碼）。目前呼叫端都傳使用者 id，見 W2 執行注意 22。修法：`!!uid && …` | minor | S | 否 | html:726@7d48d40 |
| W2-T1-m3 | 缺少測試：`load()` 讀 v2／v3／v4 與 `save()` 寫 v4（目前只有直接呼叫 `upgrade()` 的測試；Task 1 驗收時已手動實測 v2 的真實載入路徑）；Step 9 的顯示處（成員頁、總覽、模板預覽、對話框勾選框）只有 `meSel` 有斷言 | minor | S | 否 | tests/departments.test.js |
| W2-T1-m4 | `seed()` 的 `toIds`（`OLD_DEPT[x] \|\| x`，不驗證）和 `upgrade()` 的 `toId`／`ids`（未知名稱併入研發）是兩份相近的名稱轉 id 邏輯（plan 程式碼） | trivial | S | 否 | html:566、:679@7d48d40 |
| W2-T1-m5 | （W2 之前就有）切換身分選單的 `${x.name}` 沒有 `esc()`；`USERS` 是程式常數，沒有實際風險 | trivial | S | 否 | html:1355@7d48d40 |
| W2-T1-m6 | 某專案的未完成葉任務全部未指派時，AI「誰負責最多工作」的分布是空清單，沒有任何提示（修正輪 1 照執行注意 21 排除未指派，不顯示「未指派」；要提示屬於產品決策） | trivial | S | 否 | `aiAsk`（html:2328@7d48d40） |
| W2-T2-m1 | 模板庫的「套用到目前節點」用 `ui.node`，只檢查 `can('create', n)`（非 collab 一律為真），不檢查可見性。一個專案都看不到、或停在模板庫時切換身分，會顯示並能套用到看不到的專案（有寫入面）。W2 之前就是這樣，W2 讓「看不到的專案」變成常態才明顯。修法：`openApplyTpl` 加 `can('view', n)` 檢查，或 `pageTemplates` 在看不到時不顯示按鈕（整體審查時處理） | minor（優先） | S | 否 | `pageTemplates`（html:2023@0b981dd）、`openApplyTpl`（:2655） |
| W2-T2-m2 | AI 專案問答引用的文件沒有依可見性過濾：ming 在 p1 問「這個專案目前的狀況如何？」，回覆裡出現他看不到的 t103「供應商評估表」和 t403「標示草稿 v2」（2026-10-02 實測）。見 D22 | minor（優先） | S | 否（D22：W2 維持現狀，之後另排） | `aiAsk`（html:2317-2330@0b981dd） |
| W2-T2-m3 | 其他依可見性之外的衍生資訊：稽核紀錄頁列出所有紀錄；總覽的人員負載、部門負載統計看得到的專案底下全部任務；看板卡片進度和子任務數、時程的採購單交期列都算進看不到的子任務。W2 之前就是這樣。見 D22 | minor | M | 否（D22：W2 維持現狀，之後另排） | `pageAudit`（html:2059）、`pageOverview`（:1926-1932）、`viewBoard`（:1483、:1498）、`viewTimeline`（:1530-1537）@0b981dd |
| W2-T2-m4 | 一個專案都看不到時，AI 快速指令（6 個 `data-act` 按鈕）是靜默不動作；同一狀態下 `aiAsk` 會回覆、`openMinutesConfirm` 會 toast，行為不一致 | trivial | S | 否 | `aiAction`（html:2262@0b981dd） |
| W2-T2-m5 | 效能小改善：`inScopeOf` 先算 `phaseOf(n)` 才檢查角色；`graphLayout` 先算 `visible(x)` 才檢查 `isLeaf(x)`。種子資料量下沒有影響 | trivial | S | 否 | html:762、:1767@0b981dd |
| W2-T2-m6 | plan Task 2 的 `seeTask` 最後一行和 Step 4.2 的 `\|\| projects()[0]` 仍是 D20、D21 之前的寫法。以執行注意 23、24 為準；整體審查時可視需要 `Plan: fix` | trivial | S | 否 | plan:398、:416 |
| W2-T3-m2 | 「你在此節點可以」清單在專案、階段節點顯示「✗ 指派負責人」（`can('assign')` 只對任務成立），表格卻寫專案負責人 ✅。修法：非任務節點改成「底下有可以指派的任務」 | minor | S | 否 | `viewPeople`（html:1927@717b359）、`can()`（:807） |
| W2-T3-m3 | 權限表和說明文字不精確（plan 指定的文字）：「新增 / 編輯任務」寫「自己負責／部門主管」，但 `create` 沒變；說明文字「未指派負責人的任務只有部門主管看得到」漏了專案負責人、系統管理員、唯讀和「負責上層任務的人看得到子任務」 | minor | S | 否 | html:1910-1925@717b359 |
| W2-T3-m4 | `create` 照 spec 不變，所以不能操作某個任務的人（例如透過上層規則看得到它的成員、範圍內審核人）仍可以在它底下新增子任務，讓它從葉任務變成上層任務、清掉進度、自動結案待確認的回報。spec §4.4 明寫「其餘動作不變」，要改需要人類另外決定 | minor | S | 否（spec 指定） | `can()`（html:801@717b359）、`addNode` |
| W2-T3-m5 | 帶 `noteId` 上傳筆記附件時沒有要求上傳者是筆記作者。UI 只會在建立筆記時附檔，所以不可達；直接呼叫函式時 `uploaded_by` 與稽核會記下實際上傳者。可選的加固：`note.author === ui.me` | trivial | S | 否 | `addAttachments`（html:1212@717b359） |
| W2-T3-m6 | （W2 之前就有）時間軸上沒有時程權的人仍可以拖工作列，放開後才跳 toast 並還原；編輯對話框的「里程碑」核取方塊看 `ed && leaf`，會把結束日設成開始日 | trivial | S | 否 | html:1738、:2471@717b359 |
| W2-T4-m1 | `USERS` 是程式常數，沒有移轉人員或編輯模板的畫面，所以：新部門永遠沒有成員、不能設主管，但對話框寫「建立後再設定主管」；被模板引用的部門（例如製造，只因模板節點）永遠刪不掉，卻提示「請先移轉」。這是 spec §3.6 的限制。文案可以改成不承諾能做到 | minor | S | 否 | `openDeptDlg`（html:1963@4f428fc）、`deptPanelHTML`（:1957） |
| W2-T4-m2 | 部門面板的「任務」數包含協作部門引用和模板節點（品保 29 = 負責 9 + 協作 2 + 模板 18），`deptUsage` 也沒有限制 `type === 'task'`。數字和刪除訊息一致，但和看板上的任務數對不上；可以拆成「任務／模板」兩欄，或改欄名 | minor | S | 否 | `deptUsage`（html:1912-1916@4f428fc） |
| W2-T4-m3 | `submitDept` 在部門不存在時 `$('dpHead')` 為 null 會出錯（模態對話框下正常操作到不了）；`updateDept` 沒有任何變更時仍寫一筆復原和稽核；`deptAdminErr` 不走 `can()`（brief 指定）；動作欄 `<td class="row">` 讓 td 變成 flex | trivial | S | 否 | html:1917、:1935、:1955、:1967@4f428fc |
| W2-T4-m4 | 測試小缺口：刪除部門的稽核斷言只比對部門名稱（拿掉 `deleteDept` 的 `log` 仍會通過）；XSS 測試的 `window.__xss === undefined` 是同步檢查，沒有作用（真正擋的是 img 數量）；面板唯讀測試沒有同時斷言面板有畫出來；`deptUsage` 的 `n.dept === id` 沒有單獨測試 | trivial | S | 否 | tests/departments.test.js（Task 4 段）@4f428fc |
| W2-T4-m5 | 窄螢幕（約 313px 的 pane）下，部門表的部門名稱一字一行，動作按鈕要在表格內橫向捲動才看得到；375px 的 WORKFLOW §5 檢查式通過（`.tbl-wrap` 內部捲動） | trivial | S | 否 | `deptPanelHTML` |
| W2-T5-m1 | AI 建議任務（html:2431）和 AI 擬定專案計畫（:2866）的 `addNode` 用 `ui.me` 當負責人；上層是別部門的任務時會被清成未指派（`log` 沒有宣稱指派給誰）。是否改成「部門取 `ui.me` 的部門」屬於產品決策；`applyTemplate`、依範本建立專案是 Task 7 | minor | S | 否 | html:2431、:2866@9a7c438 |
| W2-T5-m4 | `deptOpts` 遇到無效的 `n.dept` 沒有佔位選項，會預設選研發，spec §6「請選擇負責部門」的 toast 碰不到；`ownerOpts` 遇到不屬於部門的負責人也會顯示「未指派」而不 toast。只有資料被手動改過才會發生 | minor | S | 否 | `deptOpts`、`ownerOpts`（html:2513-2514@9a7c438） |
| W2-T5-m5 | `ownerOpts` 會列出資訊室（`it`，系統管理員帳號），原本的 `userOpts` 和協作人員清單都排除 `it` | trivial | S | 否 | html:2514@9a7c438 |
| W2-T5-m6 | 快速新增的預設部門 `qaDept` 和 `addNode` 的預設部門是兩份相同的公式，qaForm 沒有把 `dept` 傳下去 | trivial | S | 否 | html:2607、:2447、:3316@9a7c438 |
| W2-T5-m7 | 測試缺口：總覽測試沒有斷言各部門件數與「未指派不算進人員負載」；會議待辦沒寫名字的情況沒有測試；XSS 測試的未指派分支沒做變異 RED；配方重做測試設了 `ui.opsTab = 'formulas'`，`resetAll()` 不會重置 `opsTab` | trivial | S | 否 | tests/departments.test.js（Task 5 段）、`resetAll`（html:1037）@9a7c438 |
| W2-T5-m8 | 375px 下任務對話框的進度欄 `#eProg` 超出表單 14px（`#edForm` scrollWidth 311 > clientWidth 297），頁面本身沒有水平捲動。Task 5 沒有改這一列，推論是 W2 之前就有 | trivial | S | 否 | `openEditor`（進度那一列） |
| W2-T6-m2 | D34 的 `.view:has(> .deptbar)` 沒有退路：不支援 `:has()` 的瀏覽器（Firefox <121、Safari <15.4）會丟掉那一行，但 `.deptbar + .tl{height:auto}` 仍然生效，`.tl` 失去高度限制，被桌面版 `.main{overflow:hidden}` 裁掉下方的列，也沒有垂直捲軸。展示用的 Chromium 不受影響（Task 6 只在 Chromium 驗過）。修法：時程分頁給 `.view` 加 class（例如 `view tlview`），或用一層 `display:flex;flex-direction:column;height:100%` 的容器包住篩選列和 `.tl` | minor | S | 否 | `.deptbar` CSS（html:160-161@7939a66） |
| W2-T6-m3 | `tlDeptMatch()` 判斷子孫是否符合篩選時沒有套 `visible()`：使用者看得到上層任務、看不到符合篩選的子任務時，上層仍以淡色路徑出現、有展開鈕，展開後卻是空的。用 yu（專案負責人）展示時不會發生。修法：`descendants(x.id).some((d) => d.type === 'task' && d.dept === ui.tlDept && visible(d))` | minor | S | 否 | `tlDeptMatch`（html:1545@7939a66） |
| W2-T6-m4 | spec §5.4 寫「點階段列的名稱可展開或收合」，但名稱按鈕仍是 `data-enter`（進入展開圖），只有 ▸ 展開鈕能切換；`.cnt` 的「▸ N 件」不能點，箭頭也和展開鈕重複（plan Step 5 的格式）。修法：`.cnt` 改成帶 `data-twist` 的按鈕，或拿掉 `.cnt` 裡的箭頭 | minor | S | 否 | `viewTimeline`（html:1618@7939a66） |
| W2-T6-m5 | 時間軸表頭「總覽圖・任務（N）」用 `rows.length`，把階段列也算進去：收合後顯示「任務（5）」，其實是 5 個階段；篩選後也不是任務數（既有寫法，收合以後更容易誤會）。修法：N 改成 `rows.filter((r) => r.n.type === 'task').length`，或用篩選列目前按鈕的件數 | minor | S | 否 | `viewTimeline`（html:1599@7939a66） |
| W2-T6-m6 | （plan 指定的寫法）`viewTimeline()` 外層的 `const bar`（篩選列）被 `rows.forEach` 內層的 `const bar`（時程條）遮蔽，行為正確但容易看錯；`drawArrows()` 的 `ui.tlDept !== 'all'` 和 `tlDeptMatch()` 開頭的判斷重複。修法：外層改名 `deptBar` | minor | S | 否 | `viewTimeline`（html:1597、:1608@7939a66）、`drawArrows`（:1670） |
| W2-T6-m7 | 外部 ERP 採購交期列（`data-ext`）不受部門篩選影響，篩選（例如財務、品保）時仍然顯示；spec 沒有提到。可以考慮篩選時只顯示 `node` 符合 `tlDeptMatch` 的採購單列 | minor | S | 否 | `viewTimeline`（html:1623@7939a66） |
| W2-T7-m1 | README §2 功能表的「時程」列仍是「8 個月甘特圖｜✅ 可用（唯讀）」，沒有反映 spec §8 要的時間軸說明（預設收合成階段、可依負責部門篩選）。plan Step 7 沒列這一項，F6 段落末尾已經寫了，只是文件不完整。審查建議：說明改成「8 個月甘特圖；預設只顯示階段，可依負責部門篩選」，「（唯讀）」是否過時留給 W5；要不要在 W2 整體修正時順手改，由整體審查判斷（執行注意 32 的範圍沒有它） | minor | S | 否 | README.md:153@03c9ff5 |
| W2-T7-m2 | README F5 權限表的「新增 / 編輯任務」列，成員和階段審核人仍是 ✅，但 Task 3 起 `can('edit', task)` 走 `canWork`（負責人、負責部門主管、專案負責人、系統管理員），表格和實作不一致。執行注意 31 只點名「修改時程」，Task 7 沒改（D38）。審查建議：整體修正時和 W2-T3-m1 一起處理，任務的部分改成「自己負責或主管部門的任務」 | minor | S | 否 | README.md:281@03c9ff5 |
| W2-T7-m3 | 測試「依範本建立專案：任務依範本帶部門且未指派」只斷言 `PHASE_TEMPLATE` 常數的形狀，沒有呼叫 `createProject` 驗證新任務的 `dept` 和 `owner === null`（plan Step 1 原樣）。implementer 已用 DOM/JS 實測：16 個任務的 owner 都是 null，dept 和範本一致。展示模式不補強，延到正式版 | minor | S | 否 | tests/departments.test.js:596-598@03c9ff5 |
| W2-T7-m4 | spec §5.5 移除 `ui.me` 預設帶出的體驗問題：非部門主管的成員（例如小安）在自己的任務下套用模板，或按採購單「建立驗收任務」，新任務都是未指派；依 spec §4.1 未指派任務不會經由上層路徑被看到，所以建立者自己看不到。toast 卻寫「已建立 N 個任務」，採購單 toast 的「開啟」只跳出「你沒有檢視此節點的權限」（2026-10-05 實測，沒有錯誤或例外）。可選的改善：toast 加一句「未指派的任務由部門主管指派，指派前你可能看不到」，或建立者看不到根節點時拿掉「開啟」 | minor | S | 否 | `submitTpl`、`poTask`（html:2760、3258-3260@03c9ff5） |
| W2-T7-m5 | 負責部門的退路 `x.dept \|\| TAG_DEPT[x.tag] \|\| 'd-rd'` 在 `nodeToTemplate` 和 `applyTemplate` 逐字重複，`mkTpl` 也有類似寫法（plan 原樣，量很小）。正式版可以抽成 `tplDept(x)` | minor | S | 否 | `nodeToTemplate`、`applyTemplate`（html:2742、2759@03c9ff5）、`mkTpl`（:577-578） |
| W2-T7-m6 | （W2 之前就有，Task 7 implementer 回報）375px 下套用模板對話框的「開始日／{產品名}」那一列在對話框內出現水平捲動（scrollWidth 383 > clientWidth 341，`overflow-x:auto`）。頁面本身沒有水平捲動，§5 第 7 點檢查式是 true | trivial | S | 否 | `openApplyTpl`（html:2767@03c9ff5） |
| DEMO-A-m1 | （Demo 走查，2026-10-05）工作流編輯器的階段、任務、相依和關卡只能在「階段與相依設定（JSON）」文字框裡改，而且只有系統管理員（資訊室 it）能新增或編輯，專案負責人 yu 也不行。D42 說個別工作流之後由使用者自行添加，但不懂 JSON 的人很難自己加。見 D43 | minor | M | 是（D43） | `openWorkflowEditor`（html:2767-2781@cfd5f72）、`canManageWorkflows`（:564） |
| DEMO-A-m2 | （Demo 走查）工作流專案的任務被階段關卡擋住時，阻擋對話框仍寫「你有覆寫權限…」並顯示「覆寫並繼續」；填了理由按下去，只會跳出「請先審核或覆寫前一階段關卡，不能用一般前置覆寫繞過」。行為正確（不能繞過關卡），但按鈕誤導。重現：yu 用「筆電新機種專流」建立專案，把第三階段任務拖到進行中。修法：阻擋原因只有關卡時，把覆寫按鈕換成「開啟閘門」 | minor | S | 否 | 阻擋對話框（`gateBlock`，html:2951@cfd5f72） |
| DEMO-A-m3 | （Demo 走查）375px 下工作流編輯抽屜的「工作流名稱／分類」兩欄不換行，「分類」超出表單約 133px（`#wfForm` scrollWidth 430 > clientWidth 297），要在抽屜內橫向捲動。頁面本身沒有水平捲動，§5 第 7 點檢查式是 true | trivial | S | 否 | `openWorkflowEditor`（html:2775-2776@cfd5f72） |
| DEMO-A-m4 | （Demo 走查）模板庫的「用這套工作流建立專案」按鈕對 reviewer、member（例如陳主管、阿明）也顯示，按下只跳「你的角色無權從工作流建立專案」。修法：依 `canCreateWorkflowProject()` 隱藏或停用按鈕 | minor | S | 否 | 模板庫工作流卡片（html:2336 附近@cfd5f72）、`canCreateWorkflowProject`（:594） |

### BY_DESIGN（plan 或 brief 指定的行為，要改必須先經過人類同意）

| ID | 描述 | 需人類 |
|---|---|---|
| F11-T1-m5 | 「重置 Demo 資料」不會把角色重設回 yu | 是（D4） |
| F11-T4-m2 | SVG 附件透過同源 blob URL 預覽，內嵌的 script 會在 app origin 執行。在 Demo 裡只算 self-XSS，接上伺服器後就會變成 stored XSS | 是（D5） |
| F11-T5-m2 | 送出回報時被硬性前置擋下，系統改開跳過對話框，已經輸入的回報內容全部遺失 | 是（D7） |
| F11-T5-m4 | 「N 個子任務」算的是整棵子樹，和全 app 的用語慣例一致 | 否，維持現狀 |
| W1-T2-m1 | 紀錄分頁第一筆回報上方的分隔線不見了（上層節點和葉任務都一樣）。plan Task 2 Step 4 拿掉了標題外層的 `.row`，`.rec:first-of-type` 因此套到第一筆回報。外觀和「筆記」區一致，兩位審查者都建議接受 | 否，維持現狀 |
| W1-T2-m5 | 從時程往下一層進入子任務會切到「紀錄」，再從麵包屑回上層時落在「看板」，不會回到時程。這是 spec §5 規定的行為（進入葉任務預設紀錄；回到上層時從紀錄改回看板） | 否，維持現狀（要改需要人類決定） |
| W2-T3-b1 | D23 的連帶結果：collab 角色的人負責的任務（例如小林負責 t4031），現在可以改時程（以前不行），因為 D23 規定任務時程等於 `canWork`，而 `canWork` 含負責人本人（spec §4.2 不分角色）。對話框和時間軸行為一致 | 否，照 D23 |
| W1-T2-m9 | 回報卡上只有成果說明有高度上限（D16），自訂欄位（`dl.kv`）、退回意見、跳過理由沒有。1366×650、摘要 8 行實測：自訂欄位 0／1／2／3／5 個時，卡片高 229／261／286／311／361px；時程的內容區 39／7／0／0／0px；看板和相依圖的內容區 81／49／24／0／0px；欄位達 3 個時，時程的分頁列底部到 657px，超出畫面。檢驗類任務常有好幾個數值欄位。預設的紀錄分頁仍可捲動，不會遺失資料。D18 決定維持現狀 | 否，維持現狀（D18；要改需要人類另外排工作項目） |

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
| W1-T1-I1 | FIXED `dc50e86`（plan Step 3 的 `.rc-main{flex:1}` 讓窄螢幕無法換行；待驗證項目實測失敗後轉 Important，修正輪改成 `flex:1 1 240px`。屬於 plan-mandated，見 D14） |
| W1-T1-m6 | FIXED `8103646`（D15：桌面版節點頁的紀錄、文件、資料、成員分頁讓主區域上下捲動，1280×720 實測能捲到底）。帶出來的「切到相依圖停在偏移位置」見 W1-T2-I2 |
| W1-T2-I1 | FIXED `c4e9e36`（長摘要把葉任務的看板、時程、相依圖擠到看不見；plan-mandated，D16 決定卡片上的成果說明最多約 6 行） |
| W1-T2-I2 | FIXED `c4e9e36`（D15 帶出的問題：紀錄分頁捲動後切到相依圖，主區域停在 43px 而且捲不回去；第 1 輪審查的待驗證項目實測失敗後轉 Important） |
| W1-T2-m6 | FIXED `c4e9e36`（D17：在子任務頁新增第一個子任務或套用模板後，從唯讀的彙總紀錄改到看板） |
| W1-T1-m1 | FIXED `26ea8eb`（`reportHTML` 改回 `const st = {`；`git diff -w --stat main` 和 `--stat` 相同） |
| W1-T1-m2 | FIXED `26ea8eb`（`reportCardHTML` 改用 `reportsOf()`） |
| W1-T1-m3、W1-T1-m4、W1-T1-m5 | FIXED `26ea8eb`（卡片斷言補上確認人名單、欄位值、送出者、退回人、確認人；新增 1 個測試：自行確認、「需填」只列必填、已完成優先於最新一版退回。變異 RED 驗過鑑別力） |
| W1-T2-m2 | FIXED `26ea8eb`（計算後的 overflow、重新渲染保留捲動位置、D16 下限、D17 反向案例和切換後沒有 `vscroll`。變異 RED 驗過鑑別力） |
| W1-F-m1 | FIXED `a5e2b7c`（W1 整體修正後的 `Progress:` commit：W2 段落的預期總數和「W1 的 N 個測試」改成 20 個／基準 64） |
| W1-F-m3、W1-F-m4 | FIXED（`Progress: W1 ready to merge`：「下一個動作」改成合併，W1-F-m1 補上 hash） |
| W1-F-m2 | FIXED `26ea8eb`（7 個分頁都斷言有回報卡和 `.tools` 的「＋ 新增子任務」） |
| W2-T1-m1 | FIXED `4f428fc`（W2 Task 4 修正輪 1：「我的任務」標題改成 `esc(t)`，附 XSS 測試；Task 4 開放改名後這裡變成可利用的 XSS，所以沒有等到 Task 5） |
| W2-T1-m7 | FIXED `03c9ff5`（W2 Task 7：拿掉 `window.applyTemplate` 包裝，改成直接斷言新節點的 `dept`／`depts`；執行注意 31、D40） |
| W2-T5-m9 | FIXED `03c9ff5`（W2 Task 7：README F6「我的任務」改成「我負責的、我協作的；部門主管另有『待我指派』」） |
| W2-T6-m1 | FIXED（`Progress: W2 task 6 done`：Task 6 審查指出兩項 AI 代決——`:has()` 版面、手機隱藏階段件數——還沒有記成 D，記錄者補成 §6 的 D34、D35） |
| F11-N1 | FIXED `b2f7453`（回報對話框 select 欄位改成 `(f.options || [])`，新增「select 欄位沒有 options 也能打開」測試） |
| W2-T3-m1 | FIXED `b2f7453`（成員與權限頁「修改時程」列照 D23 更新；README 的同列已在 `03c9ff5` 更新） |
| W2-T5-m2 | FIXED `b2f7453`（看板卡片的名字・部門包進 `.whonm`，CSS `white-space:nowrap`，窄欄位不逐字換行） |
| W2-T5-m3 | FIXED `b2f7453`（未指派負責人顯示「未指派」，通知、時間軸、AI 週報、稽核不再出現 `—`／`? —` 或不合理的「已通知」） |

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
| D3 | 流程 | 要不要 push 到 `origin` | 由人類執行，或由人類明確授權。AI 不會自己 push | 已決定 2026-10-01：人類授權 push 交接系統（連同 `edf46b6`、`dfc0126`），已完成。2026-10-01 第二次授權：人類指示「完成後上傳到GIT」，W1 完成並合併進 `main` 後，把 `main` push 到 `origin`。2026-10-02：人類指示「推上 git」，W1 合併後已把 `main` push 到 `origin`（不 force，只推 `main`）。每次授權都只限該次，之後每次 push 仍要人類明確授權。2026-10-02 第三次：人類指示「你這個階段做完就先暫停，幫我 commit and push」，W2 Task 5 完成後 push `main` 和 `feature/w2-departments`（人類選「推兩個，README 寫在分支」）。2026-10-05：人類指示「push上去」，Codex 已 push `main` 到 `origin/main`（`8041e14..a2f7e85`），沒有 push 或刪除遠端 feature 分支。2026-10-05：人類指示「確認後推上去」與「git 上的 readme 也要記得更新進度」，Codex 已 push W3、W5 README 更新與看板收尾到 `origin/main` |
| D4 | F11（W4） | F11-T1-m5：重置 Demo 時要不要把角色重設回 yu | 建議重設回 yu | 已決定 2026-10-05：維持現狀（D30：展示模式下 W4 取消，人類沒有反對這個提案；人類可以推翻） |
| D5 | F11（W4） | F11-T4-m2：SVG 附件改成下載，還是用 `<img>` 或 sandbox 顯示 | 建議排除 SVG 預覽，改成下載（安全優先） | 已決定 2026-10-05：維持現狀（D30：展示模式下 W4 取消，人類沒有反對這個提案；人類可以推翻） |
| D6 | F11（W4） | F11-T4-m4：附件全部上傳失敗時，回報要不要整份不送出 | 建議先寫入 blob，失敗就不建立回報 | 已決定 2026-10-05：維持現狀（D30：展示模式下 W4 取消，人類沒有反對這個提案；人類可以推翻） |
| D7 | F11（W4） | F11-T5-m2：被硬性前置擋下時，要不要保留回報草稿。W1 之後更常發生：有硬性前置的葉任務，在回報卡上就看得到醒目的「回報完成」（W1 整體審查的觀察） | 建議把草稿暫存在 `ui`，跳過前置後自動重開回報對話框 | 已決定 2026-10-05：維持現狀（D30：展示模式下 W4 取消，人類沒有反對這個提案；人類可以推翻） |
| D8 | F11（W4） | F11-T6-m1：「部分恢復」要怎麼記錄 | 建議補寫稽核紀錄，並新增 `o.restoredNodes` | 已決定 2026-10-05：維持現狀（D30：展示模式下 W4 取消，人類沒有反對這個提案；人類可以推翻） |
| D9 | W3 | W3 流程控制的 brainstorming（spec 內容） | 需要人類參與問答，AI 不可以自行定稿 | 已決定 2026-10-05：改照 D31，W3 精簡版由 AI 依 D13 甘特圖起草短版 spec，人類看一次就定稿，不做完整的 brainstorming |
| D10 | P 軌 | README §9 #5–#14（模型硬體、雲端供應商、預設分級、帳號、通知、協作部門權限、ERP 介面、工單、編碼規則、庫存與採購核准） | 正式導入前再決定。W2 會在 Demo 層級回答 #10（同部門的其他成員看不到） | 待人類 |
| D11 | Demo軌→正式軌 | 正式產品軌何時啟動 | 依D51啟動P0並做到P1c；保留Demo參照與既有驗收證據，正式版按其階段重新驗收 | 已決定2026-10-08：人類明確指示「開始做到P1c」；不再等待啟動授權 |
| D12 | W5 | W5 README 中 full demo 的定位文字 | AI 起草，人類審閱 | AI 代決 2026-10-05：已在 README 頂部、§1、§2 起草 full demo 定位與進度摘要（可推翻） |
| D13 | W3 | 請提供「10 部門流程甘特圖（連接器新產品，6 階段）」的原檔或內容 | 轉寫成 `docs/reference/connector-10dept-gantt.md`，欄位：階段、工作項目、負責部門、關卡／核准人、交付物 | 已由 D41 取代：不再等待原本的連接器甘特圖，先依現有兩份專流表進行 |
| D14 | W1-T1 | **Important（plan-mandated，已修正）**：plan Step 3 的 `.rcard .rc-main{min-width:0;flex:1}` 讓 flex-basis 變成 0，`.rc-row` 的 `flex-wrap:wrap` 永遠不會換行。375px 下動作欄固定佔掉右半邊，文字欄只剩 118–141px，自訂欄位會溢出。已在 `dc50e86` 改成 `flex:1 1 240px`，並加 1 個版面測試，所以 W1 的測試變成 14 個 | **接受 `dc50e86` 的修正**。同意後可以視需要用 `Plan: fix` 同步 plan Step 3 和 Task 2 的預期測試數 | 已決定 2026-10-01：接受修正（人類選「接受修正（建議）」）。plan 不另外同步，以 W1 執行注意 13 為準 |
| D15 | W1-T1 | §5 W1-T1-m6：F11 原本就有的版面問題。桌面寬度下，紀錄、文件、資料、成員分頁的內容超出畫面時會被截掉，無法捲動。W1 之後葉任務預設進紀錄分頁，上方又多了回報卡，會更常發生。要在 W1 一起修，還是登記到 W4 再修？ | **在 W1 一起修**：這幾個分頁改成整個主區域可以捲動，和手機版一樣，標題和回報卡會跟著捲上去；看板、時程、相依圖維持原樣。放在 Task 2 的修正輪處理，附測試 | 已決定 2026-10-01：在 W1 一起修（人類選「在 W1 一起修（建議）」），放在 Task 2 的修正輪 |
| D16 | W1-T2 | **Important（plan-mandated，Task 2 品質審查 I1）**：子任務的回報摘要很長時，置頂回報卡會把葉任務的看板、時程、相依圖分頁擠到看不見。plan 的卡片 CSS 沒有高度上限，而 D15 讓這三個分頁維持主區域不捲動。1366×650 實測：摘要 8 行時，時程的內容區高度變成 0；12 行時連分頁列都被推出畫面，切不回紀錄分頁 | **限制卡片摘要高度**：卡片上的成果說明最多顯示約 6 行，超過的部分在卡片內捲動，完整內容在紀錄分頁的「回報歷史」，只改 CSS。其他選項：子任務頁全部分頁都可以捲動（改動較大，也要調整 D15）；維持現狀 | 已決定 2026-10-02：人類回覆「都照建議」，也就是限制卡片摘要高度。放在 Task 2 修正輪 1，見 W1 執行注意 16 |
| D17 | W1-T2 | Task 2 品質審查 m3(b)（spec 沒有寫到，已實測）：在子任務頁按「＋ 新增子任務」新增第一個子任務後，它會變成上層任務，但畫面仍停在「紀錄」分頁的唯讀彙總，看不到剛新增的子任務 | **新增後切到看板**：原本是子任務、而且停在紀錄分頁時，新增第一個子任務後自動切到「看板」。另一個選項是維持現狀 | 已決定 2026-10-02：人類回覆「都照建議」，也就是新增後切到看板。放在 Task 2 修正輪 1，見 W1 執行注意 17 |
| D19 | W2-T1 | spec 和 plan 衝突（Task 1 審查 Minor m1，執行注意沒有裁決）：v3 → v4 升級時，模板節點補 `dept` 的順序。spec §3.4(4) 是「有 `who` 取其部門 → 否則模板的第一個 `dp` → 再沒有則 d-rd」；plan Task 1 Step 8（已照做，`e62b39a`）是「`who` → `TAG_DEPT[類別]` → 第一個 `dp` → d-rd」。差別只影響舊 v3 資料升級後的系統模板，例如沒有協作部門的「簽核檢驗費用」，spec 會給研發，plan 給採購；有協作部門的節點，spec 會把協作部門當成負責部門 | **照 plan（維持 `e62b39a`）**：升級後的模板部門和新種子資料一致（`seed()` 的模板也是用 `TAG_DEPT`），不會把協作部門誤當負責部門。spec 文字差異以本條為準，不另外改 spec。另一個選項：照 spec，在 Task 1 修正輪改 `upgrade()` | 已決定 2026-10-02：照 spec（人類選「照 spec」）。在 Task 1 修正輪 1 改 `upgrade()` 並補測試，見 W2 執行注意 20 |
| D20 | W2-T2 | **Important（plan-mandated，Task 2 spec 審查 I-1）**：`seeTask` 的下層規則。plan（已照做，`ebab1e1`）是「下層任務直接相關，**或下層任務已指派、而且它的上層任務直接相關**」時顯示為路徑；spec §4.1 字面只有「下層任務直接相關」。只在這種結構下不同：ming 負責 t3012 → 底下有未指派的 N（品保）→ N 底下有指派給小安的 D。plan：ming 看得到 N 和 D；spec 字面：ming 看得到 D，卻看不到 D 的父任務 N，D 在看板和時程上點不到（孤兒）。範本帶入負責人（spec §5.5）或 Task 3 的指派操作都可能做出這種結構 | **照 plan**：程式不改，補一個測試釘住這個行為，spec §4.1 的文字差異以本條為準。其他選項：照 spec 字面（會出現點不到的孤兒任務）；或上層規則遇到未指派節點就停（連 D 也看不到，但違反 spec 對已指派任務的上層規則） | 已決定 2026-10-02：照 spec 字面（人類選「照 spec 字面」）。Task 2 修正輪 1 改 `seeTask`，見 W2 執行注意 23 |
| D21 | W2-T2 | spec 沒有寫的情況（Task 2 兩位審查者 Minor）：使用者**一個專案都看不到**時（例如他負責的任務全部改派給別人）。plan Step 4.2 是退回 `projects()[0]`，會帶到他看不到的專案，露出專案標題、階段列和關卡；另外 AI 副手（`aiAsk`）和會議記錄確認（`openMinutesConfirm`）在非專案頁會因為 `ctxProject()` 是 `undefined` 而出錯。種子資料的 7 個身分都至少看得到一個專案，所以目前不會發生 | **顯示空狀態**：主區域顯示「目前沒有你看得到的專案」，不帶到別人的專案；`ctxProject()` 的呼叫端加防護。放在 Task 2 修正輪，附測試。另一個選項：維持 plan（帶到第一個專案，看板顯示空狀態），只修出錯的地方 | 已決定 2026-10-02：顯示空狀態（人類選「顯示空狀態（建議）」）。Task 2 修正輪 1 實作，見 W2 執行注意 24 |
| D22 | W2-T2 | spec 沒有寫的情況（Task 2 審查與修正輪的範圍外觀察）：W2 讓「只有相關的人看得到任務」，但有些衍生資訊沒有依可見性過濾。(a) AI 專案問答引用的文件：ming 會看到他看不到的任務的文件名稱和內容（§5 W2-T2-m2，已實測）；(b) 稽核紀錄頁、總覽的人員／部門負載、看板卡片進度和子任務數、時程的採購單交期列，會露出看不到的任務的存在、負責人或數量（§5 W2-T2-m3）。W2 之前就是這樣 | **(a) 在 W2 整體修正時改成依 `can('view')` 過濾**（AI 只引用看得到的任務的文件）；**(b) 維持現狀**，之後另外排工作項目。不擋 Task 3–7，W2 改成 🟢 之前要有結論 | 已決定 2026-10-02：都維持現狀（人類選「都維持現狀」）。(a)(b) 都不在 W2 處理，§5 W2-T2-m2、m3 留給之後的工作項目 |
| D23 | W2-T3 | spec 沒有寫的情況（Task 3 品質審查 I-2，已實測）：審核人的「修改時程」權限（spec §4.4：不變）和任務對話框。Task 3 之後，審核人對不是自己負責、也不是自己主管部門的任務，`can('edit')` 是 false、`can('schedule')` 仍是 true。實測陳主管開 t30121：開始、結束日期和鎖定欄位可以改，儲存鈕卻是停用的，畫面寫「唯讀」，改了存不下來；時間軸拖曳仍然可以改時程。W2 之前審核人可以在對話框存時程 | **對話框可以只存時程**：沒有編輯權、但有時程權時，儲存鈕可用，儲存時只寫入開始、結束日期和鎖定，其他欄位不動。放在 Task 3 修正輪，附測試。另一個選項：對話框的日期和鎖定也改成唯讀，只能用時間軸拖曳改時程 | 已決定 2026-10-02：人類回覆「不是他負責也不是他部門，就不關他的事啊，不能做其他動作」，追問範圍後選「只拿掉時程（建議）」。**任務**的修改時程改成和 `canWork` 一樣（負責人本人、負責部門主管、專案負責人、系統管理員），審核人不能再改別人任務的時程（對話框和時間軸拖曳都不行）；階段本身的時程、設定前置條件、範圍內的關卡核准、跳過申請核准、回報確認都照舊。這一點推翻 spec §4.4「reviewer 不變」，以本條為準。Task 3 修正輪 1 實作，見 W2 執行注意 26 |
| D24 | W2-T3 | spec 沒有寫的情況（Task 3 spec 審查 Minor 5）：誰可以寫筆記。spec §4.2 只寫「協作人員與協作部門主管照舊可以新增筆記」。照 plan 的 `canNote`，範圍內的審核人（例如陳主管對 t30121）**不能**再寫筆記，除非他是協作人員或部門主管；W2 之前審核人可以在任何任務寫筆記 | **允許範圍內的審核人寫筆記**（和 W2 之前一樣；他們看得到這些任務，也負責關卡）：`canNote` 加上 `inReviewerScope(n)`。放在 Task 3 修正輪，附測試。另一個選項：照 plan，審核人只有在是協作人員或部門主管時才能寫筆記 | 已決定 2026-10-02：允許範圍內審核人（人類選「允許範圍內審核人（建議）」）。Task 3 修正輪 1 實作，見 W2 執行注意 27 |
| D25 | W2-T3 | spec 沒有寫的情況（Task 3 修正輪 scoped re-review 的範圍外觀察）：時間軸的「連動順延」（`cascadeFrom`／`shiftSubtree`）在某人改了自己任務的時程後，會自動順延**別人負責**的後續任務，不檢查 `can('schedule')`。D23 決定「不是他負責也不是他部門，就不能改時程」，但連動會間接改到別人的任務。W2 之前就是這樣，有稽核紀錄 | **維持現狀**：連動是依前置條件自動保持時程一致，不算個人修改。另一個選項：連動遇到沒有時程權的任務就停下來，並提示要請負責人或主管處理 | 已決定 2026-10-02：遇到沒權限的任務就停（人類選「遇到沒權限的任務就停」）。連動碰到操作者沒有時程權（`can('schedule')`）的任務就停下來，提示要請負責人或部門主管處理。放在 W2 整體修正，附測試。**2026-10-05 改為取消，維持現狀**（人類選「取消，維持現狀（建議）」，D30 展示模式）：連動順延照舊，不在 W2 實作 |
| D26 | W2-T4 | spec 沒有寫的情況（Task 4 品質審查 Minor 7）：部門主管可以選任何部門成員，包括協作人員（collab，例如業務部的小林）。主管有 `canWork` 和可見性的權限，所以小林被設成業務主管後，就能操作業務部所有的任務、看到未指派的業務任務 | **主管只能選成員、審核人、專案負責人這類角色，排除協作人員和唯讀**：`updateDept` 拒絕並提示，對話框的主管下拉不列出他們。放在 W2 整體修正，附測試。另一個選項：維持現狀（任何部門成員都能當主管） | 已決定 2026-10-02：排除協作人員與唯讀（人類選「排除協作人員與唯讀（建議）」）。放在 W2 整體修正，附測試。**2026-10-05 改為取消，維持現狀**（人類選「取消，維持現狀（建議）」，D30 展示模式）：任何部門成員都能當主管，不在 W2 實作 |
| D27 | W2-T4 | spec 文字不準確（Task 4 spec 審查 Minor 1）：部門面板「未設主管」的提示文字照 spec §5.1 寫「這個部門的未指派工作只有專案負責人看得到」，但依 Task 2 的可見性，系統管理員（和唯讀）也看得到 | **改成「這個部門的未指派工作只有專案負責人與系統管理員看得到」**，放在 W2 整體修正。另一個選項：維持 spec 原文 | 已決定 2026-10-02：維持 spec 原文（人類選「維持 spec 原文」），不改 |
| D18 | W1-T2 | §5 W1-T2-m9（Minor，兩位審查者第 2 輪都提到）：D16 只限制了卡片上的成果說明。自訂欄位、退回意見、跳過理由很長或很多時，卡片仍會把葉任務的看板、時程、相依圖擠到看不見。1366×650 實測：自訂欄位達 2 個時，時程的內容區變成 0；達 3 個時，看板和相依圖也是 0，時程的分頁列超出畫面 | **一起限制高度**：自訂欄位最多顯示約 4 列，退回意見和跳過理由最多約 4 行，超過的在卡片內捲動，完整內容在紀錄分頁的回報歷史，只改 CSS。另一個選項：維持現狀（目前種子資料和系統模板的欄位都只有 0–1 個） | 已決定 2026-10-02：維持現狀（人類回覆「D18 維持現狀」）。W1-T2-m9 改列 BY_DESIGN，要改需要人類另外排工作項目 |
| D28 | W2（流程） | `origin/main` 已經用 GitHub PR #1 的 merge commit `8041e14`（2026-10-05 09:07，parents `670afaf`、`079b035`）合入 W2 Task 1–5 的草稿。這不符合 G5（整體審查後才合併、只用 ff、不建 merge commit）和「有 `feature/*` 分支時 `main` 凍結」。W2 要怎麼繼續？ | **接受，分支跟上**：`feature/w2-departments` 用 `git merge --ff-only origin/main` 前進到 `8041e14`（程式和 `079b035` 相同，只多一個 merge commit），照原流程在分支上做 Task 6、7 和整體審查，完成後再 ff 合併回 `main`。另一個選項：在 GitHub 上 revert | 已決定 2026-10-05：接受，分支跟上（人類選「接受，分支跟上（建議）」）。已 ff 到 `8041e14`，見 W2 執行注意 33 |
| D29 | W2（流程） | 本機 `main` 有 2 個從沒 push 的 commit（`6c39df8 Progress: note 8001 test server stopped`、`4ed2ab5 Progress: note LAN share server for the demo`，2026-10-02），和 `origin/main` 分岔（ahead 2、behind 27），無法 fast-forward。內容是 8001 測試伺服器已關、8080 區網分享伺服器在跑；2026-10-05 實測兩台都不在 | **捨棄，對齊 `origin/main`**：先留備份 tag，再把本機 `main` 指到 `origin/main`；還有用的事實改寫進分支看板。另一個選項：在本機 `main` 建 merge commit 並解 PROGRESS 衝突（違反 ff-only） | 已決定 2026-10-05：捨棄，對齊 `origin/main`（人類選「捨棄，對齊 origin/main（建議）」）。已建本機 tag `backup/local-main-2026-10-02`（指向 `4ed2ab5`，沒有 push），用 `git branch -f main origin/main` 把 `main` 移到 `8041e14`；8001、8080 的現況寫進 W2 執行注意 17 |
| D30 | 全專案（流程） | 人類 2026-10-05 指示：「我這個專案是展示用的，先以完成主要功能能使用為主，不用花太多時間在細節的修飾。以最快的速度完成整個專案，這樣需要修改哪些任務目標」 | AI 提案：(1) 流程改成展示模式（WORKFLOW §13）：一位審查者、最多一輪修正、只擋會讓展示出問題的錯誤、不補強測試也不做變異 RED，保留 TDD 和硬性規則；(2) W2 照做 Task 6、7，整體修正只修 4 個看得到的問題（執行注意 32），驗收精簡；(3) W3 見 D31；(4) W4 取消，F11-N1 併入 W2，D4–D8 維持現狀；(5) W5 只改 README §1、§2；(6) Demo 完成條件跟著精簡（§1 第 4 點）；正式產品軌不在範圍內 | 已決定 2026-10-05：人類對提案回答了 D31–D33，並選 D25、D26「取消，維持現狀（建議）」，其餘部分沒有反對，照提案執行。WORKFLOW §13、AGENTS §5、CLAUDE.md、`/pf-next` 已經同步改成展示模式 |
| D31 | W3 | W3 流程控制原本 7 項（關卡硬性擋住後續階段、範本指定核准人、總經理角色、強制通過關卡與略過整個階段、完成報告必附交付物、連接器範本與示範專案、資料升到 v5），要做到什麼程度 | **精簡版**：只做連接器 6 階段範本與示範專案，加上關卡擋住後續階段；其他延到正式版。spec 由 AI 依甘特圖起草，人類看一次。其他選項：W3 整個不做；照原本 7 項 | 已決定 2026-10-05：精簡版（人類選「精簡版（建議）」）。見 §3 W3 |
| D32 | 全專案（流程） | spec 沒寫到的小細節，AI 可以自己照建議做、事後再給人類看嗎 | **可以**：記進 §6，狀態寫「AI 代決 YYYY-MM-DD：…（可推翻）」，不標 ⛔，不停下來。範圍、資料版本、新 spec、push 仍然要問。另一個選項：照舊停下來問 | 已決定 2026-10-05：可以，事後給我看（人類選「可以，事後給我看（建議）」）。見 WORKFLOW §13 |
| D33 | 全專案（流程） | 展示會用手機看嗎？（決定展示模式要不要保留 375px 檢查） | 建議只用電腦展示，不再檢查 375px。另一個選項：手機也要能看 | 已決定 2026-10-05：**手機也要能看**（人類推翻建議）。每個 Task 和驗收都保留 375px 沒有水平捲動的檢查 |
| D34 | W2-T6 | spec 沒寫到的小細節（Task 6 implementer concern、審查 m1）：時程分頁的部門篩選列放在 `height:100%` 的 `.tl` 前面，桌面版 `.tl` 會超出 `.view` 約 40px，下緣和橫向捲軸被 `.main{overflow:hidden}` 裁掉（實測修正前 `.tl` 下緣 920 > `.main` 900） | **只用 CSS 讓有篩選列的 `.view` 改成直向 flex**：`.view:has(> .deptbar){display:flex;flex-direction:column}`、`.deptbar + .tl{flex:1 1 0;min-height:0;height:auto}`，`.deptbar` 加 `flex-shrink:0`，不改 plan 規定的 HTML 結構。缺點是依賴 `:has()`，舊版 Firefox／Safari 沒有退路（§5 W2-T6-m2）。另一個選項：時程分頁的 `.view` 加 class，或用容器包住篩選列和 `.tl` | AI 代決 2026-10-05：有篩選列時 `.view` 改成直向 flex、`.tl` 吃剩下的高度（`7939a66`；桌面 `.tl` 下緣等於 `.view` 下緣，375px 篩選列換 3 行時 `.tl` 仍有 306px 可捲動）（可推翻） |
| D35 | W2-T6 | spec 沒寫到的小細節（Task 6 implementer concern、審查 m1）：手機版（≤860px）的 `.tl-label` 只有 150px，階段列的件數「▸ N 件」會把階段名稱擠到只剩 3px，名稱完全看不到 | **手機版隱藏階段件數**：在 `@media (max-width:860px)` 加 `.tl-label .cnt{display:none}`，名稱寬度回到改動前（47px），件數仍可以在篩選列看到。這和 spec §5.4「階段列上顯示 ▸ N 件」在手機上不一致。另一個選項：縮短件數文字或加寬標籤欄 | AI 代決 2026-10-05：寬度 ≤860px 時不顯示階段列的件數（`7939a66`）（可推翻） |
| D36 | W2-T7 | spec 沒寫到的小細節（Task 7 implementer concern）：README §2 功能表新增「我的任務｜✅ 可用」列之後，原本的「其他｜分享、總覽、我的任務、AI 收件匣｜⬜ 未實作」會和它直接矛盾 | **從「其他」列拿掉「我的任務」**，只刪一個詞，不算大改 §2（執行注意 7）。另一個選項：保留原列不動 | AI 代決 2026-10-05：「其他」列改成「分享、總覽、AI 收件匣」（`03c9ff5`）（可推翻） |
| D37 | W2-T7 | spec 沒寫到的小細節（Task 7 implementer concern）：README §2 表沒有獨立的「我的任務」列，也沒有部門的列（執行注意 7 要用新增的方式），新列要怎麼寫 | **新增兩列**：「我的任務｜跨專案列出我負責的、我協作的任務；部門主管有「待我指派」｜✅ 可用」、「部門（F6）｜部門設定與負責部門｜✅ 可用」 | AI 代決 2026-10-05：照建議新增兩列（`03c9ff5`）（可推翻） |
| D38 | W2-T7 | spec 沒寫到的小細節（Task 7 implementer concern）：README F5 權限表的「修改時程」列要反映 D23，各角色欄的文字 | **照 `can('schedule')` 寫**（任務走 `canWork`，非任務照舊）：系統管理員 ✅、專案負責人 ✅、階段審核人「階段；任務限自己負責或主管部門的」、成員「自己負責或主管部門的任務」、協作人員「自己負責的任務」、唯讀空白。同表的「新增 / 編輯任務」列也受 `canWork` 影響，但執行注意 31 只點名「修改時程」，這次沒改（§5 W2-T7-m2） | AI 代決 2026-10-05：照建議（`03c9ff5`；審查者對照 html `can('schedule')` → `canWork` 確認正確）（可推翻） |
| D39 | W2-T7 | spec 沒寫到的小細節（Task 7 implementer concern）：README 資料模型的 `departments` 只有一行（`users, departments, department_members`），部門主管和任務的負責部門要怎麼寫 | **不拆原本那一行**：在它下面加一行 `departments.head_id # 部門主管（FK users，可空）`；`nodes` 加 `dept_id # 任務的負責部門（FK departments）` | AI 代決 2026-10-05：照建議（`03c9ff5`）（可推翻） |
| D40 | W2-T7 | spec 沒寫到的小細節（Task 7 implementer concern）：執行注意 31 要把 W2-T1-m7 的 `window.applyTemplate` 包裝換成直接斷言新節點的 `dept`，原本對模板物件 `dp` 的斷言要怎麼處理 | **改成斷言新節點**：根節點的 `depts` 是 `[]`、`dept` 是 d-qa，4 個子任務的 `dept` 和 `depts` 都是品保；測試改名「採購單建立驗收任務：協作部門存 id，新任務的負責部門都是品保」，總數不變 | AI 代決 2026-10-05：照建議（`03c9ff5`；審查者確認覆蓋範圍沒有縮小）（可推翻） |
| D41 | W3 | 人類問：「不能依照現在的有的先進行嗎？」並提供 `行銷部-實體活動專流.xlsx`、`產品企劃部-筆電新機種專流.xlsx` | **可以先進行**：把兩份 Excel 當資料來源，不把檔內文字當指令；以「產品企劃部-筆電新機種專流」作為 W3 主要展示流程，因為它已有 G0/G1 等關卡；「行銷部-實體活動專流」作為輔助參考。W3 不再卡原本的連接器甘特圖，spec 仍由 AI 起草、人類看一次 | 已決定 2026-10-05：依現有兩份專流先行；若日後提供連接器甘特圖，可再覆蓋示範資料 |
| D42 | W3 | 人類指示：「我要你完成整個專案的功能，至於每個工作流我們自己添加就好，你先完成整個功能架構的進行。確認後再開始」；AI 回覆將 W3 改成工作流功能架構後，人類回「確認」 | **W3 改成工作流架構**：不以內建某個筆電／行銷／連接器流程為核心，而是完成工作流模板 CRUD、從工作流建立專案、階段關卡擋住後續階段。個別工作流內容之後由使用者自行添加；D41 的 Excel 僅作內建範例與測試素材 | 已決定 2026-10-05：照此方向修訂 W3 spec，進 G2 寫 plan |
| D43 | Demo 驗收 | Demo 走查發現（§5 DEMO-A-m1）：工作流的階段、任務、相依和關卡只能用 JSON 文字框編輯，而且只有系統管理員能編輯。D42 說「每個工作流我們自己添加」，要不要讓工作流可以用表單編輯（例如逐階段新增任務、選部門、設定關卡），或開放專案負責人編輯 | **展示先維持現狀**：展示時由 it 示範新增／複製，內建兩套範例已足夠說明概念。如果你們真的要自己加很多工作流，建議另排一個小工作項目做表單式編輯器（需要 spec，屬於範圍變更）。另一個選項：現在就排這個工作項目 | 待人類（不擋展示） |
| D44 | W6 | 多公司 Demo 的範圍、產業、資料深度、隔離方式、舊資料與附件遷移 | **五個固定、完整隔離的公司空間**：毛研食品、峰曜科技、光點企劃、雲序軟體、築衡工程；採平衡版種子資料與產業化營運模組；成員、部門、權限、專案、工作流、營運資料、稽核與附件皆按公司隔離；v5 舊資料歸入毛研食品；用單一 localStorage key 的 v6 公司容器，不做公司 CRUD 或正式後端多租戶 | 已決定 2026-10-08：人類逐項採用建議並批准完整設計，可寫 written spec |
| D45 | 全專案（流程） | W6 和目前 `feature/p0-formal-product-plan` 的優先順序 | **先暫停 P0 規劃，優先完成 W6**；保留 P0 的 spec、plan 與 commit，W6 完成後恢復 | 已決定 2026-10-08：人類批准 W6 完整設計時同意此執行順序；P0 分支已保留為 `paused/p0-formal-product-plan` |
| D46 | W6 執行 | W6 plan 的執行方式 | 由目前 session 依 Task 0–6 直接實作；主 checkout、每 Task TDD 與審查、PROGRESS 為唯一進度來源 | 已決定 2026-10-08：人類選擇「Native execution」，授權開始 W6 plan |
| D51 | 正式版啟動 | 人類指示「開始做到P1c」 | 授權完整P0→P1a→P1b→P1c的正式版MVP實作與必要規則轉換；不是僅恢復規劃。沿用React／FastAPI／PostgreSQL／Docker Compose、核心工作流與公司隔離要求。逐階段補齊可執行計畫、TDD與獨立審查；D50每段更新README並push繼續有效。P2以後非目標不自動納入 | 已決定2026-10-08。先前文件中的「未授權實作」已由本項取代；新計畫的人類審閱關卡保留，不能跳過或把草稿當可執行計畫 |
| D52 | P0計畫審閱 | 人類回覆「好開始」 | 確認2026-10-08-p0-formal-foundation計畫，立即Native執行Task1–3；正式軌按完整安全／獨立審查標準驗收 | 已決定2026-10-08；解除P0計畫待審閱 |
| D50 | 全專案發布 | 人類指示「做完一段就推上去github，然後每個階段都要更新readme，讓所有人知道目前進度在哪」 | 持續授權每個已完成且驗證／審查通過的階段：同步README與PROGRESS、依既有流程ff-only合併到main、`git push origin main`。不force、不推其他分支、不自動開PR；授權發布不等於授權尚未確認的產品範圍。此後階段推送不必逐次重問，直到人類更改指示 | 已決定2026-10-08；涵蓋本次P0規劃文件恢復與先前尚未發布的W6。D3的每次需另行授權由本項持續授權滿足；遠端分岔仍依§8確認 |
| D49 | P0 恢復規劃 | 舊paused分支與main分岔，無法ff恢復最新基準 | 保留paused分支，從最新main建立feature/p0-formal-product-plan，僅帶回既有spec／plan後對齊W6；以新規劃分支為主，檢查後ff-only合併回main。不rebase、不覆蓋W6、不push | 已決定2026-10-08：人類回答「是，並且以此分支為主，合併回去main」。只授權規劃分支恢復與本地合併，不視為授權正式產品實作 |
| D48 | W6 Task 6 審查 | 新公司沒有配方比例權限，既有機密文件判斷因此讓所有角色都無法再開啟已存文件 | 毛研保留原有 ratio 判斷；新公司機密文件限目前公司 owner／admin 且節點可見者開啟，其他角色維持拒絕。新公司 ratio 仍為 false，不借用毛研欄位權限 | AI 代決 2026-10-08（可推翻）：展示模式最小修正，修復文件被永久鎖住；自動化覆蓋四公司建立、儲存、重新開啟與未授權拒絕 |
| D47 | W6 Task 2–3 | plan 測試的空殼節點、Gate／deps 模型及範例命名與 spec 不完全相同 | 切換選第一個可見專案（空殼才 null）；Gate 驗證 `db.gates`、前置驗證 `db.deps`。專案／工作流範例名稱依 plan 明列值；毛研保留既有兩工作流與測試錨點，其他公司採產業專屬工作流。介面相依 T1→T2/3→T4→T5/6 的公司投影、ops 設定與附件鍵已核對一致 | AI 代決 2026-10-08（可推翻）：展示模式的小差異，以既有資料模型與保留毛研相容性為準；不增加功能或改變公司範圍 |

---

## 7. 交接紀錄（最新的在最上面，只保留最近 5 筆，更舊的從 git 歷史查）

格式見 [WORKFLOW.md 附錄 A](WORKFLOW.md#附錄-a交接紀錄格式)。

### 2026-10-08｜Codex GPT-5｜P0 Native foundation完成
- **做了什麼**：D52記錄人類「好開始」確認P0計畫；主checkout建立feature/p0-formal-foundation，正式規則切換後逐Task TDD完成API／React／Compose，依D2 ff-only合併main。更新README、正式開發指南及進度看板；依D50已push `4539e41..981362f`並核對遠端，本筆發布紀錄同步推送。
- **驗證／審查**：API RED缺app.main→8passed；React RED缺App→6passed；E2E RED4connection refused→4passed。真DBlive200／ready503不洩漏→恢復200、volume不變；1280／375截圖、重試、5秒timeout及遲到回應均通過，非預期console／page errors空。Task1 Arendt、Task2 Faraday、Task3 Goodall Approved；Hilbert整體Ready to merge: Yes。合併後pytest8／Vitest6／E2E4及build再次exit0；兩minor記§5。
- **環境／清理**：保留健康Compose供人類使用，入口http://127.0.0.1:15173；DB無host埠、API18000loopback。密碼僅ignored deploy/.env，不進Git。只關本次Demo8001 PID30892，未動8000或其他容器，未刪DB volume。Demo174/174再驗證，兩HTML與tests無diff；舊paused分支不動。
- **下一步**：P1a登入／公司授權隔離／migration／核心API的詳細plan，再依正常審閱與TDD；D51已授權到P1c，不重新問是否開始。P0不含登入、專案或工作流業務功能，不得標P1c完成。每階段README／PROGRESS與GitHub同步。

### 2026-10-08｜Codex GPT-5｜D51 授權到 P1c，P0 計畫待審閱
- **做了什麼**：人類明確指示「開始做到P1c」，已記D51並解除D11啟動待決；更新README／spec／舊outline的過時授權文字。以既有MVP範圍補齊P0三Task可執行計畫，包含正式軌規則轉換、完整檔案／依賴、API8測試、React6測試、Compose與4項E2E、真實DB outage/recovery、獨立審查與D50發布。
- **驗證**：只讀環境預檢確認Node/Python/Docker daemon/Compose可用；npm／PyPI查版本。計畫中2份Python程式以AST解析、2份JSON解析、7段PowerShell語法解析均通過；這些不是產品測試GREEN。文件連結與diff check另在commit前檢查。
- **沒做的事**：新可執行計畫尚待人類審閱；未建立api／web／deploy、未安裝產品依賴、未改AGENTS／WORKFLOW或Demo。不能宣稱P0、P1a、P1b、P1c已實作。
- **下一步**：請人類審閱新P0計畫，沿用Native執行並依repo逐Task獨立審查；通過後Task1先記RED。整體交付到P1c已明確授權，不要再次詢問是否啟動正式版。每階段更新README／看板並依D50推送。

### 2026-10-08｜Codex GPT-5｜P0 規劃恢復與階段發布
- **做了什麼**：先確認舊P0與main互非祖先並登記D49；人類批准後，以`39948a8`建立新的`feature/p0-formal-product-plan`為主線，保留舊paused分支於`40f8cc2`。帶回兩份規劃文件、對齊W6公司邊界，明示舊計畫仍是待細化草稿；更新README／PROGRESS。新增D50記錄每完成階段更新README並push GitHub的持續授權。
- **驗證／審查**：文件commit `a1e84a6`；兩Demo與tests相對基準完全不變，四文件相對連結無缺失，diff check通過。獨立Planck給`Ready to merge: Yes`。沒有重跑產品測試，也沒有宣稱P0實作完成。
- **Git／發布**：依D49已ff-only合併main，依D50成功push `e452173..5b02e47`，發布W6與本段P0規劃；本筆收尾同步推送。只push origin main，不force、不rebase、不開PR。舊paused分支不推送或改寫；合併後新feature分支依G6刪除，後續以main為準。
- **下一步**：確認範圍並細化P0可執行計畫；正式產品實作仍須授權。每階段同步README與看板後發布。

### 2026-10-08｜Codex GPT-6｜W6 Native execution 完成
- **做了什麼**：依人類選擇直接執行Task 0–6，每Task TDD、獨立reviewer與進度commit。完成五公司v6容器、切換、產業化種子與營運頁、附件隔離及單公司重設、共用AI／權限／事件加固。修正審查發現的損壞資料修復、非同步失敗上傳跨公司風險、D48機密文件鎖死；修正375px配方頁溢出。
- **驗證**：149→153→157→162→166→170→174，各Task的RED原文見§3。最後兩次新時間戳與ff合併後均 `全部通過 174/174`；1280／375px共508畫面、10項持久化重載、十工作流建立、所有營運模組與F10驗收通過，console/page errors空；截圖人工檢視。`git diff --check`通過，archive petfood檔未改。
- **審查／Git**：六個Task與G4均由獨立子代理唯讀審查；Rawls複審 `Task 6: Approved`、`Ready to merge: Yes`。依D2本地ff-only合併到main；產品最後commit `0934e48`，進度 `f3a61ec`，G6收尾後刪除已合併feature分支。不push。
- **偏離／代決**：D47沿用既有Gate／deps模型與plan標題；D48新公司機密文件限可見節點的owner/admin。UI驗收用外部Playwright／Edge腳本；8000非此repo，使用自行啟動的8001 PID4312，收尾關閉。W6未在`.superpowers/sdd/`產生暫存；既有W2／W3舊檔不移動。
- **下一步**：依D45下一session恢復P0規劃（原分支保留，需先帶入W6邊界）；沒有授權P0實作。人類展示確認、D43工作流表單編輯器與push均未執行。

### 2026-10-08｜Codex GPT-5｜W6 implementation plan 待審
- **做了什麼**：人類批准 W6 written spec 後完成 G2 plan。計畫拆成 Task 0 pre-flight 與 6 個 TDD 實作 Task：v6 容器／遷移、公司原子切換、五產業種子資料、設定驅動營運頁、附件與單公司重設、跨公司隔離與驗收。
- **驗證**：逐節對照 spec §4–§12 與現有程式介面，修正了 `db.projects[]`、附件 `storage_key`、`undoStack`、audit `acts[]`、users object 與 fetched-test runner 等模型差異；五類 Review Focus 都有歸屬 Task 和自動化測試。plan 明定新增 25 項，目標 `174/174`；`git diff --check` 與 commit 驗證在本次 G2 commit 前執行。這輪只改文件，沒有執行產品測試。
- **沒做的事／偏離 plan**：尚未建立 W6 feature 分支、修改產品程式或測試；沒有 push。P0 仍依 D45 暫停。
- **下一步**：人類審閱 `docs/superpowers/plans/2026-10-08-multi-company-industry-demo.md` 並選擇執行方式；建議 Native execution。開始後照 Task 0 先確認／改名歷史 W3 feature branch、跑 `149/149` 基準，再建立 `feature/w6-multi-company-industry-demo`。
- **注意**：執行時 `resetAll()` 保留為測試用完整重設，產品左下角改走 `resetActiveCompany()`；v6 執行期投影不得掃描其他公司，切換／重設必須先成功持久化候選資料。
