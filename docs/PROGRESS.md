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
| 目前工作項目 | **W2 部門模型**（🔨 執行中） |
| 下一個動作 | 切到 `feature/w2-departments`，進度以該分支的 PROGRESS 為準。下一步：W2 Task 1（部門資料、v4 升級、顯示改用部門名稱） |
| 分支 | `feature/w2-departments`（從 `main` 的 `Progress: start W2` 切出） |
| 最新程式 commit | `26ea8eb`（W1 整體修正）。W1 合併後的 HEAD 是 `2d2c785` |
| 行號基準 | `dfc0126`。§5「位置」欄和 §3「執行注意」的行號都以這個 commit 為準，此欄固定不改。程式改動後行號會位移，請用函式名或程式片段搜尋 |
| 測試基準 | `tests/records.html`：`全部通過 64/64`（2026-10-02 實測，W1 合併前在 `1978dde` 上獨立重跑；iframe 0、343、1393px 都通過。W2 Pre-flight 在 `b2c96c1` 上重跑仍是 `全部通過 64/64`） |
| 資料版本 | `db.v = 3`；localStorage key 是 `projectflow-demo-v2` |
| 認領中 | Claude Opus 5.5（Claude Code，手動 SDD），2026-10-02 12:05 |
| 阻塞／待人類 | 無阻塞。D14–D19 都已決定（§6） |
| 遠端 | 2026-10-02 經人類授權（D3：執行注意 W1-12，以及人類 2026-10-02 指示「推上 git」），把 `main` push 到 `origin/main`，內容包括 W1 全部 commit、`Progress: W1 handoff summary`，以及之後的 `Docs: README section on how to direct AI agents`（同一天第二次指示「推上 git」）。push 之後 `git log --oneline origin/main..main` 應該是空的。之後每次 push 都要人類明確授權（D3） |

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
| 1 | W1 | 子任務置頂回報卡 | ✅ | [spec](superpowers/specs/2026-10-01-subtask-report-card-design.md)（`3a24c52`） | [plan](superpowers/plans/2026-10-01-subtask-report-card.md)（`ed3e24f`） | 維持 v3 | F11 ✅ |
| 2 | W2 | 部門模型 | 🔨 | [spec](superpowers/specs/2026-10-01-department-model-design.md)（`edf46b6`，`dfc0126` 修訂 §4.1 和範本段，以 HEAD 版本為準） | [plan](superpowers/plans/2026-10-01-department-model.md)（`dfc0126`） | v3 → v4 | W1 已合併（D1） |
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

### W2 部門模型 — 🔨

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
| 1 | 部門資料、v4 升級、顯示改用部門名稱 | 🔨 修正輪 1（已實作 `e62b39a`，RED 失敗 6/69 → GREEN 全部通過 69/69；要修 2 個 Important：AI 工作量把未指派算成「null」、採購單「建立驗收任務」的內聯模板仍用舊部門名稱；另照 D19 改 `upgrade()`，見執行注意 20、21） | — | 5 | 69 |
| 2 | 可見性：只有相關的人看得到；移除「顯示全部」 | ⬜ | — | 8 | 77 |
| 3 | 操作權限 `canWork`、指派、改部門 | ⬜ | — | 5 | 82 |
| 4 | 部門管理面板：新增、修改、刪除 | ⬜ | — | 5 | 87 |
| 5 | 任務的負責部門和負責人：對話框、看板、我的任務、總覽 | ⬜ | — | 6 | 93 |
| 6 | 時間軸預設收合，並可依部門篩選 | ⬜ | — | 6 | 99 |
| 7 | 範本帶入負責部門、更新 README | ⬜ | — | 4 | 103 |
| — | 整體審查 | ⬜ | — | — | — |

預期總數是研究時推算的，plan 本身只寫「全部通過 N/N」。以實際跑出來的數字為準。W1 最後共有 20 個測試（plan 的 13 個，加上修正輪和整體修正的 7 個），基準是 64，上表已經照這個數字調整（2026-10-02，W1-F-m1）。W1 如果還有修正增加測試，要再調整。

**驗收**
- [ ] `tests/records.html` 全部通過：W1 的 20 個測試加上 departments 的 39 個測試都是綠燈
- [ ] spec §7 的第 1–10 項，每一項至少對應一個測試，在 commits 欄旁列出測試名稱
- [ ] 先按「重置 Demo 資料」，再以 yu、chen、an、ming、it 各截一次圖，確認看板、時程、我的任務、成員與權限頁都符合 spec §4、§5
- [ ] 未指派、而且所屬部門沒有主管（製程）的任務 `t504`，只有 yu 和 it 看得到
- [ ] 時間軸預設收合；`ui.tlDept = 'd-qa'` 時階段列數不變，工作列只剩品保的任務
- [ ] 舊的 v3 資料能升級成 v4（`db.v === 4`），對應正確：法規→`d-qa`、生產→`d-mfg`、行銷→`d-sales`
- [ ] README 的 F6、§2、§5 已經照 plan Task 7 Step 7 更新
- [ ] 375px 寬度下沒有水平捲動，console 沒有錯誤

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
17. **測試環境**（2026-10-02 的狀態）：
    - 8000 埠被另一個不是這個 repo 的 python 伺服器占用（回應 `{"detail":"Not Found"}`），不要動它。
    - 8001 埠有前一個 session 留下的這個 repo 的伺服器（Windows PID 24024）。先用 `curl.exe -s http://127.0.0.1:8001/AGENTS.md` 確認第一行是 `# AGENTS.md`，符合就直接沿用；不符合就換別的埠。
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
- 目錄前面的「給接手的人：怎麼請 AI 繼續開發」是 2026-10-02 照人類指示新增的。這段不加編號，所以 AGENTS.md 引用的 §4、§5、§6、§9 編號不變。W5 整理時要一併檢查這段和 AGENTS、WORKFLOW 是否一致。

full demo 定位的文字需要人類審閱（D12）。

---

## 4. 已完成

| 項目 | 內容 | 證據 |
|---|---|---|
| 階段 0 | petfood 互動 Demo（`projectflow-petfood-demo.html`） | README §8 階段 0 已打勾 ✅；早於 git 歷史，包含在 `9fdcc64` 裡 |
| F1–F10 | full demo 的多層任務樹、模板、時程編輯、前置條件與關鍵路徑、權限與覆寫、協作、文件與版本、AI 副手（規則式）、分級路由與遮罩（模擬）、研發營運資料（模擬 ERP） | 早於 git 歷史，包含在 `9fdcc64` 裡。F6 的部門目前是寫死的，由 W2 處理 |
| F11 | 任務紀錄與完成回報：回報與審核、自訂回報欄位、筆記、附件（IndexedDB）、主管跳過整個任務、AI 引用紀錄 | [spec](superpowers/specs/2026-09-30-task-records-and-skip-design.md)、[plan](superpowers/plans/2026-09-30-task-records-and-skip.md)；commits `9fdcc64..aebd709`（從 `2fc8f10` 到 `aebd709` 共 10 個：7 個 Task、2 輪修正、1 次整體修正），以 fast-forward 合併進 `main`；測試 44/44。SDD 暫存已歸檔到本機的 `.superpowers/archive/2026-09-30-f11-task-records/`（不在 git 裡；重要內容已整理到本看板 §5） |
| W1 | 子任務置頂回報卡：葉任務頁標題下方固定顯示回報卡（狀態與下一步動作），「紀錄」分頁排第一並作為預設；D15 桌面版紀錄等分頁可捲動，D16 卡片摘要最多約 6 行，D17 新增第一個子任務後切到看板 | [spec](superpowers/specs/2026-10-01-subtask-report-card-design.md)、[plan](superpowers/plans/2026-10-01-subtask-report-card.md)；commits `8aed7d6..2d2c785`（2 個 Task、2 輪 Task 修正、D15、1 次整體修正），以 fast-forward 合併進 `main`；測試 64/64；`db.v` 維持 3。審查全部獨立（每個 Task spec＋品質各 2 輪，整體審查 2 輪）。SDD 暫存已歸檔到本機的 `.superpowers/archive/2026-10-01-subtask-report-card/`（不在 git 裡；重要內容已整理到本看板 §3 W1、§5、§6） |
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
| W1-T2-m3 | 紀錄等可以捲動的分頁，捲到底時最後一個區塊貼齊主區域底部，沒有留白（實測差 0px；手機版本來就是這樣）。修法：`.main.vscroll > .view{flex-shrink:0}`（整體審查建議：歸 W4） | minor | S | 否 | `.main.vscroll`、`.view` CSS（html:64、:114@c4e9e36） |
| W1-T2-m4 | Windows 上同一個節點切換分頁時，捲軸出現或消失會讓主區域寬度差 15px（實測紀錄 663px、看板 678px），標題和卡片左右跳動。修法：節點頁的 `.main` 加 `scrollbar-gutter:stable`（整體審查建議：歸 W4） | minor | S | 否 | `renderMain`（html:1331@c4e9e36）、`.main.vscroll` CSS |
| W1-T2-m7 | D17 只處理「子任務變成上層任務」。新增第一個子任務、自動切到看板之後按 toast 的「復原」，節點變回子任務，回報卡和「紀錄排第一」都恢復，但分頁停在看板，顯示「這個節點還沒有子任務」的空狀態（實測）。符合執行注意 7。可選的修法：D17 切換時記下節點，同一個節點又變回子任務、而且仍停在看板時改回紀錄（整體審查建議：之後處理或改列 BY_DESIGN，不擋合併） | minor | S | 否 | `pageNode`（html:1351@c4e9e36） |
| W1-T2-m8 | （W1 之前就有）桌面版相依圖下方的圖例說明超出主區域，被截掉約 43px（1280×720）。`.graph` 是 `height:100%`，圖例 `<p>` 落在 `.view` 外面。W1 修正輪 1 只確保主區域不會停在偏移的位置。修法例如：讓相依圖的 `.view` 改成直向 flex，或把圖例移到工具列（整體審查建議：歸 W4） | minor | S | 否 | `viewGraph`（html:1773@c4e9e36）、`.graph` CSS（:199） |
| W1-F-m5 | （W1 之前就有）回報歷史和筆記的內文（`.rec .body`）遇到沒有空白的長字串（例如長網址）不會換行，375px 下主區域被撐到 1144px，可以橫向捲動，WORKFLOW §5 第 7 點的檢查式變成 false。`main` 上用同樣的回報實測也是 1144px。筆記（`noteHTML`）用的是同一條 CSS，沒有另外實測。回報卡的 `.rc-sum` 會在卡片內捲動，不受影響。重現：375px，阿明在 `t30121` 送出摘要「參考資料：https://example.com/…」（100 字以上、中間沒有空白）。修法：`.rec .body` 加 `overflow-wrap:anywhere`（`.rc-sum` 也可以一起加），並附 375px 的測試 | minor | S | 否 | `.rec .body` CSS（html:256@1978dde）、`reportHTML`、`noteHTML` |

### BY_DESIGN（plan 或 brief 指定的行為，要改必須先經過人類同意）

| ID | 描述 | 需人類 |
|---|---|---|
| F11-T1-m5 | 「重置 Demo 資料」不會把角色重設回 yu | 是（D4） |
| F11-T4-m2 | SVG 附件透過同源 blob URL 預覽，內嵌的 script 會在 app origin 執行。在 Demo 裡只算 self-XSS，接上伺服器後就會變成 stored XSS | 是（D5） |
| F11-T5-m2 | 送出回報時被硬性前置擋下，系統改開跳過對話框，已經輸入的回報內容全部遺失 | 是（D7） |
| F11-T5-m4 | 「N 個子任務」算的是整棵子樹，和全 app 的用語慣例一致 | 否，維持現狀 |
| W1-T2-m1 | 紀錄分頁第一筆回報上方的分隔線不見了（上層節點和葉任務都一樣）。plan Task 2 Step 4 拿掉了標題外層的 `.row`，`.rec:first-of-type` 因此套到第一筆回報。外觀和「筆記」區一致，兩位審查者都建議接受 | 否，維持現狀 |
| W1-T2-m5 | 從時程往下一層進入子任務會切到「紀錄」，再從麵包屑回上層時落在「看板」，不會回到時程。這是 spec §5 規定的行為（進入葉任務預設紀錄；回到上層時從紀錄改回看板） | 否，維持現狀（要改需要人類決定） |
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
| D3 | 流程 | 要不要 push 到 `origin` | 由人類執行，或由人類明確授權。AI 不會自己 push | 已決定 2026-10-01：人類授權 push 交接系統（連同 `edf46b6`、`dfc0126`），已完成。2026-10-01 第二次授權：人類指示「完成後上傳到GIT」，W1 完成並合併進 `main` 後，把 `main` push 到 `origin`。2026-10-02：人類指示「推上 git」，W1 合併後已把 `main` push 到 `origin`（不 force，只推 `main`）。每次授權都只限該次，之後每次 push 仍要人類明確授權 |
| D4 | F11（W4） | F11-T1-m5：重置 Demo 時要不要把角色重設回 yu | 建議重設回 yu | 待人類 |
| D5 | F11（W4） | F11-T4-m2：SVG 附件改成下載，還是用 `<img>` 或 sandbox 顯示 | 建議排除 SVG 預覽，改成下載（安全優先） | 待人類 |
| D6 | F11（W4） | F11-T4-m4：附件全部上傳失敗時，回報要不要整份不送出 | 建議先寫入 blob，失敗就不建立回報 | 待人類 |
| D7 | F11（W4） | F11-T5-m2：被硬性前置擋下時，要不要保留回報草稿。W1 之後更常發生：有硬性前置的葉任務，在回報卡上就看得到醒目的「回報完成」（W1 整體審查的觀察） | 建議把草稿暫存在 `ui`，跳過前置後自動重開回報對話框 | 待人類 |
| D8 | F11（W4） | F11-T6-m1：「部分恢復」要怎麼記錄 | 建議補寫稽核紀錄，並新增 `o.restoredNodes` | 待人類 |
| D9 | W3 | W3 流程控制的 brainstorming（spec 內容） | 需要人類參與問答，AI 不可以自行定稿 | 待人類（W2 合併後） |
| D10 | P 軌 | README §9 #5–#14（模型硬體、雲端供應商、預設分級、帳號、通知、協作部門權限、ERP 介面、工單、編碼規則、庫存與採購核准） | 正式導入前再決定。W2 會在 Demo 層級回答 #10（同部門的其他成員看不到） | 待人類 |
| D11 | Demo 軌 | 正式產品軌何時啟動，以及確認 §1 第 4 點的 Demo 軌完成條件 | 等 Demo 軌完成條件全部達成後再評估 | 待人類 |
| D12 | W5 | W5 README 中 full demo 的定位文字 | AI 起草，人類審閱 | 待人類（W2 之後） |
| D13 | W3 | 請提供「10 部門流程甘特圖（連接器新產品，6 階段）」的原檔或內容 | 轉寫成 `docs/reference/connector-10dept-gantt.md`，欄位：階段、工作項目、負責部門、關卡／核准人、交付物 | 待人類（W3 brainstorming 前必須到位） |
| D14 | W1-T1 | **Important（plan-mandated，已修正）**：plan Step 3 的 `.rcard .rc-main{min-width:0;flex:1}` 讓 flex-basis 變成 0，`.rc-row` 的 `flex-wrap:wrap` 永遠不會換行。375px 下動作欄固定佔掉右半邊，文字欄只剩 118–141px，自訂欄位會溢出。已在 `dc50e86` 改成 `flex:1 1 240px`，並加 1 個版面測試，所以 W1 的測試變成 14 個 | **接受 `dc50e86` 的修正**。同意後可以視需要用 `Plan: fix` 同步 plan Step 3 和 Task 2 的預期測試數 | 已決定 2026-10-01：接受修正（人類選「接受修正（建議）」）。plan 不另外同步，以 W1 執行注意 13 為準 |
| D15 | W1-T1 | §5 W1-T1-m6：F11 原本就有的版面問題。桌面寬度下，紀錄、文件、資料、成員分頁的內容超出畫面時會被截掉，無法捲動。W1 之後葉任務預設進紀錄分頁，上方又多了回報卡，會更常發生。要在 W1 一起修，還是登記到 W4 再修？ | **在 W1 一起修**：這幾個分頁改成整個主區域可以捲動，和手機版一樣，標題和回報卡會跟著捲上去；看板、時程、相依圖維持原樣。放在 Task 2 的修正輪處理，附測試 | 已決定 2026-10-01：在 W1 一起修（人類選「在 W1 一起修（建議）」），放在 Task 2 的修正輪 |
| D16 | W1-T2 | **Important（plan-mandated，Task 2 品質審查 I1）**：子任務的回報摘要很長時，置頂回報卡會把葉任務的看板、時程、相依圖分頁擠到看不見。plan 的卡片 CSS 沒有高度上限，而 D15 讓這三個分頁維持主區域不捲動。1366×650 實測：摘要 8 行時，時程的內容區高度變成 0；12 行時連分頁列都被推出畫面，切不回紀錄分頁 | **限制卡片摘要高度**：卡片上的成果說明最多顯示約 6 行，超過的部分在卡片內捲動，完整內容在紀錄分頁的「回報歷史」，只改 CSS。其他選項：子任務頁全部分頁都可以捲動（改動較大，也要調整 D15）；維持現狀 | 已決定 2026-10-02：人類回覆「都照建議」，也就是限制卡片摘要高度。放在 Task 2 修正輪 1，見 W1 執行注意 16 |
| D17 | W1-T2 | Task 2 品質審查 m3(b)（spec 沒有寫到，已實測）：在子任務頁按「＋ 新增子任務」新增第一個子任務後，它會變成上層任務，但畫面仍停在「紀錄」分頁的唯讀彙總，看不到剛新增的子任務 | **新增後切到看板**：原本是子任務、而且停在紀錄分頁時，新增第一個子任務後自動切到「看板」。另一個選項是維持現狀 | 已決定 2026-10-02：人類回覆「都照建議」，也就是新增後切到看板。放在 Task 2 修正輪 1，見 W1 執行注意 17 |
| D19 | W2-T1 | spec 和 plan 衝突（Task 1 審查 Minor m1，執行注意沒有裁決）：v3 → v4 升級時，模板節點補 `dept` 的順序。spec §3.4(4) 是「有 `who` 取其部門 → 否則模板的第一個 `dp` → 再沒有則 d-rd」；plan Task 1 Step 8（已照做，`e62b39a`）是「`who` → `TAG_DEPT[類別]` → 第一個 `dp` → d-rd」。差別只影響舊 v3 資料升級後的系統模板，例如沒有協作部門的「簽核檢驗費用」，spec 會給研發，plan 給採購；有協作部門的節點，spec 會把協作部門當成負責部門 | **照 plan（維持 `e62b39a`）**：升級後的模板部門和新種子資料一致（`seed()` 的模板也是用 `TAG_DEPT`），不會把協作部門誤當負責部門。spec 文字差異以本條為準，不另外改 spec。另一個選項：照 spec，在 Task 1 修正輪改 `upgrade()` | 已決定 2026-10-02：照 spec（人類選「照 spec」）。在 Task 1 修正輪 1 改 `upgrade()` 並補測試，見 W2 執行注意 20 |
| D18 | W1-T2 | §5 W1-T2-m9（Minor，兩位審查者第 2 輪都提到）：D16 只限制了卡片上的成果說明。自訂欄位、退回意見、跳過理由很長或很多時，卡片仍會把葉任務的看板、時程、相依圖擠到看不見。1366×650 實測：自訂欄位達 2 個時，時程的內容區變成 0；達 3 個時，看板和相依圖也是 0，時程的分頁列超出畫面 | **一起限制高度**：自訂欄位最多顯示約 4 列，退回意見和跳過理由最多約 4 行，超過的在卡片內捲動，完整內容在紀錄分頁的回報歷史，只改 CSS。另一個選項：維持現狀（目前種子資料和系統模板的欄位都只有 0–1 個） | 已決定 2026-10-02：維持現狀（人類回覆「D18 維持現狀」）。W1-T2-m9 改列 BY_DESIGN，要改需要人類另外排工作項目 |

---

## 7. 交接紀錄（最新的在最上面，只保留最近 5 筆，更舊的從 git 歷史查）

格式見 [WORKFLOW.md 附錄 A](WORKFLOW.md#附錄-a交接紀錄格式)。

### 2026-10-02｜Claude Opus 5.5｜W1 交接摘要、push
- **做了什麼**：
  - 人類要求把 W1 改了哪裡、沒改哪裡整理成文件，讓下一個 AI 能照計畫接手，然後推上 git。
  - 在 §3 W1 開頭加了「W1 完成摘要」。
  - 在 §3 W2 的執行注意加了第 14–19 點：W1 合併後的基準、行號位移、W1 改到而 W2 可能碰到的程式、測試環境、編輯陷阱、變異 RED。
  - D7 補上 W1 整體審查的觀察。
  - 依 D3 把 `main` push 到 `origin`。
  - 人類接著要求把「怎麼請 AI 繼續開發」寫進 README，然後推上 git。這段放在 README 目錄前面，不加編號，內容是給人類的操作說明：Claude Code 的 `/pf-status`、`/pf-next`、`all`／`dry`，其他 AI 的開場提示，AI 什麼時候會停下來問、人類怎麼回答 D，以及測試會清掉 127.0.0.1 的資料。W5 段落已登記要一併檢查。
- **驗證**：push 後 `git log --oneline origin/main..main` 是空的。這次只改文件，沒有重跑測試，基準仍是 W1 合併前的 `全部通過 64/64`。
- **沒做的事／偏離 plan**：沒有開始 W2，也沒有做 W2 的 Pre-flight。
- **下一步**：W2 開工（見「▶ 現在」）。
- **注意**：8001 上 PID 24024 的伺服器沒有關（不是這個 session 啟動的）。

### 2026-10-02｜Claude Opus 5.5｜W1 完成並合併
- **做了什麼**：
  - 人類回覆「D18 維持現狀」，記在 `1978dde`；W1-T2-m9 改列 BY_DESIGN。
  - 獨立的整體審查第 2 輪（`44df43a..a5e2b7c`）結論是 Ready to merge: Yes，只有 2 項 trivial（W1-F-m3、m4），在 `2d2c785` 修正並把 W1 標成 🟢。報告在 `.superpowers/sdd/review-44df43a..a5e2b7c-final-r1.md`，已隨 SDD 歸檔。
  - 依 D2 在本地 `git merge --ff-only`（`8aed7d6..2d2c785`），然後在 `main` 上做這筆 G6 收尾，並刪除分支。
- **驗證**：第 2 輪的 Verify 都實測過：CSS zoom 0.9–1.5 倍時 `scrollTop` 的精確比較是穩的；375px 下 15 行摘要沒有橫向捲軸；合併前在 `1978dde` 上獨立重跑 `全部通過 64/64`，console 無錯誤。審查：獨立。
- **沒做的事／偏離 plan**：長網址會把紀錄分頁的回報歷史撐出主區域。這是 F11 原本就有的問題，`main` 上也一樣，登記為 §5 W1-F-m5，歸 W4。
- **下一步**：W2 開工（見「▶ 現在」）。
- **注意**：
  - 8000 埠仍被另一個不是這個 repo 的伺服器占用。8001 上是前一個 session 啟動的這個 repo 的伺服器（Windows PID 24024），這個 session 都是用它跑測試。這個 session 也試著在 8001 啟動伺服器，但因為埠已被占用，一啟動就結束了。24024 不是這個 session 啟動的，所以沒有關（WORKFLOW §5 第 8 點），要不要關由人類決定。
  - W1 的 commit 都還沒有 push，push 需要人類授權（D3）。

### 2026-10-02｜Claude Opus 5.5｜W1 整體審查第 1 輪與整體修正
- **做了什麼**：
  - 驗收清單 6 項都在瀏覽器實測通過（`44df43a`）。
  - 獨立的整體審查者（唯讀）結論是 Ready to merge: With fixes，沒有 Critical 或 Important。報告在 `.superpowers/sdd/review-8aed7d6..44df43a-final-r0.md`。
  - 整體修正 `26ea8eb`：W1-T1-m1–m5、W1-T2-m2、W1-F-m2。產品程式只有兩處不改變行為的整理，其餘都是測試。
  - W1-F-m1（W2 段落的測試數）在這次的 `Progress:` commit 修正。
- **驗證**：沒有自然的 RED，改用變異 RED：10 處變異都被新斷言抓到（`失敗 1/64` 或 `失敗 2/64`）。改回後和備份逐位元組相同 → GREEN `全部通過 64/64`（iframe 0、343、1393px）。審查：獨立（第 1 輪）。
- **沒做的事／偏離 plan**：
  - 「剛好 6 行沒有捲軸」沒有寫成測試，審查也同意可以不做。Task 2 已經實測過。
  - 審查報告寫的 (b)「需填」用 t30121，實作改用 t30122，因為 t30121 在同一個測試的 (a) 已經自行確認完成了。
- **下一步**：W1 整體審查第 2 輪，範圍 `44df43a..HEAD`（見「▶ 現在」）。
- **注意**：
  - 8000 埠仍被另一個不是這個 repo 的伺服器占用。測試用的是 8001 上前一個 session 留下的伺服器（PID 24024）。
  - 新的 D16 下限斷言用的是 `clientHeight`。iframe 寬 0 時會多出橫向捲軸，所以這個測試也先把 iframe 撐到 1200px。
  - D18 待人類，不擋合併。

### 2026-10-02｜Claude Opus 5.5｜W1 Task 2 完成
- **做了什麼**：
  - 接手前一個 session 的進度：Task 2 已有 `0d8bf12`（plan 本體）和 `8103646`（D15），第 1 輪兩位審查者都是 Approved，但品質審查列的待驗證項目實測失敗 1 項。兩份審查報告是從前一個 session 的紀錄找回來的，存在 `.superpowers/sdd/review-f69d282..8103646-*-r0.md`。
  - 人類回覆 D16、D17「都照建議」，記在 `3e59c71`。
  - 修正輪 1 `c4e9e36`：主區域不能捲動時回到頁首；D16 卡片摘要最多 6 行；D17 新增第一個子任務後切到看板；另加 3 個測試。
  - 兩位獨立審查者複審都是 Approved。他們列的待驗證項目都已實測，只有 W1-T2-m9 需要人類決定，登記為 D18。
- **驗證**：基準 `全部通過 60/60` → 修正輪 RED `失敗 3/63` → GREEN `全部通過 63/63`（iframe 1235px 和 345px 各一次）→ 記錄前獨立重跑 `全部通過 63/63`。瀏覽器實測細節在 Task 2 列和 `.superpowers/sdd/task-2-report.md`。審查：獨立。
- **沒做的事／偏離 plan**：D16、D17 是人類決定的增補。plan 沒有同步，以執行注意 16–18 為準。
- **下一步**：W1 整體審查與驗收（見「▶ 現在」）。
- **注意**：
  - 接管 2026-10-01 16:09 的認領（前一個 session 中斷）。
  - 8000 埠被另一個不是這個 repo 的 python 伺服器占用（PID 5932，2026-10-02 07:36 啟動，回應 `{"detail":"Not Found"}`），沒有動它。這個 session 改在 8001 啟動自己的伺服器（PID 24024）。
  - Browser pane 隱藏時，測試頁寬度會是 0。新的回到頁首測試會自己把 iframe 撐到 1200px，所以結果和 pane 寬度無關。
  - D18 待人類，不擋合併。

### 2026-10-01｜Claude Opus 5.5｜W1 開工、Task 1 完成
- **做了什麼**：
  - 在 `main` 上做 Pre-flight（抽查 Task 1 錨點和介面，基準 `全部通過 44/44`），然後開工：`8aed7d6 Progress: start W1`，開分支 `feature/w1-subtask-report-card`，建立 `.superpowers/sdd/`（ledger 第一行是 `Plan:`）。
  - Task 1：`b678dbd`（`reportCardHTML`、`reportFieldsHTML`、`.rcard` CSS、7 個測試）。修正輪 1：`dc50e86`（`.rc-main` 改成 `flex:1 1 240px`，加 1 個窄螢幕換行測試）。
  - 人類在對話中指示「完成後上傳到GIT」，已記進 D3（`826be0e`）和 W1 執行注意 12。
- **驗證**：
  - RED `失敗 7/51` → GREEN `全部通過 51/51`；修正輪 RED `失敗 1/52` → GREEN `全部通過 52/52`；記錄前獨立重跑 `全部通過 52/52`。
  - 瀏覽器實測：`reportFieldsHTML` 和舊寫法逐字相同；7 種狀態的卡片；375px 和 1280px 的卡片版面；console 沒有錯誤。
  - 審查：獨立（spec 和品質審查者各 2 輪，結論都是 Approved）。
- **沒做的事／偏離 plan**：
  - plan Step 3 的 `.rc-main` CSS 改成 `flex:1 1 240px`（D14）。plan 本身還沒同步。
  - 這個 session 沒有載入 `/pf-next`，改成手動照同一套流程執行：實作、記錄由主 session 做，審查交給兩位獨立的唯讀子代理。
- **下一步**：W1 Task 2（見「▶ 現在」）。
- **注意**：
  - D14、D15 待人類。
  - Task 2 的預期是 RED `失敗 5/58`、GREEN `全部通過 58/58`。
  - 測試頁跑完會在 127.0.0.1 留下待確認的回報；手動實測前先執行 `resetAll()`。
  - port 8000 的伺服器是這個 session 用 `preview_start`（demo）啟動的。
