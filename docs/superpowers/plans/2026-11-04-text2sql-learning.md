# TEXT2SQL-LEARNING：確認過的問法學起來（短規格與計畫）

依使用者 2026-11-04：看過簡報回饋頁的錄影（`Downloads/p29_AI助手_學習前後.mp4`，簡報頁「問題解決｜從『無法判斷』到『下次直接答對』」）後，指示「把系統真的用成這樣」，並要求先確認設計才寫程式。這份文件合併規格與計畫（WORKFLOW §14 精簡流程）。

**核可（2026-11-05）**：使用者對照簡報與程式後，看過「簡報說法 vs 程式碼」清單與建議做法，回覆「照建議開工」，並要求「一起做完要開一個 PR」。本文件的 AI 預設照寫；另補簡報第 6 頁兩個小項（Task 0）。

- **一句話**：資料分析答不了時，系統已經會給建議（TEXT2SQL-FALLBACK）；這次把「使用者點建議、確認結果正確」的那一句問法存成候選，由管理者按「審核＋測試」，自動檢查全過才補進白名單，之後同一句直接答對。
- **範圍**：AI 助手「資料分析」（`mode: 'sql'`、`dataset: 'dataset-v1'`）。文件問答、`starter-v1`、`formal-v1` 不在範圍。
- **底線**：**學起來的只能是「問法 → 既有 16 個分析之一」的對照。** 不新增分析、不讓模型寫 SQL、不學含條件的問句（否則會重演「上週逾期任務被答成全部逾期」）。
- **展示目標**：重現錄影的四步：學習前（反問給選項）→ 標記（使用者確認）→ 審核（管理者審核＋自動測試）→ 學習後（同一句直接答對）。

## 現況（2026-11-04，`main` `983ad55`）

| 項目 | 現況 | 影響 |
|---|---|---|
| 答不了給建議 | `fallback.suggest` 回 `kind='fallback'`、`suggestions`（≤3） | 沿用，不改 |
| 點建議 | 前端 `ask(s.label, undefined, s.query_id)`：只送建議的名稱和 `query_id` | 伺服器不知道原問句，學不起來 |
| 回答紀錄 | `ai_answers` 每次回答一列，只存 id、種類、來源 id，**不存問題與回答原文** | 要加「這次給了哪些建議」的 id |
| 稽核 | `ai.query` 只記種類與條件類別，不記原文 | 新動作沿用同規則 |
| 白名單問法 | `service.ALIASES` 寫死在程式 | 改成「寫死的＋資料庫裡已上線的」 |
| 審核畫面 | 沒有 | 新增 |

範例已實測（只開規則）：「哪些供應商常常遲交？」→ `fallback`、`reason='topic'`、無條件，建議 `q06 供應商已收貨延遲率`、`q05 供應商未交逾期訂單數與金額`（和錄影一致）；「上週逾期任務」→ `reason='condition'`、`time`。

## 已確認的決定

| # | 決定 | 來源 |
|---|---|---|
| 1 | **只在使用者按確認後，存那一句問法**，只給同公司管理者看；問句原文只存在候選資料表，不進稽核、不進 `ai_answers` | 使用者決定（2026-11-04） |
| 2 | 照錄影四步：反問給選項 → 使用者確認 → 管理者審核＋自動測試 → 補進白名單 | 使用者決定（錄影） |
| 3 | 存在 PostgreSQL，新資料表＋Alembic migration | AI 預設，可改 |
| 4 | 每家公司各自學，不跨公司共用 | AI 預設，可改 |
| 5 | 能查資料分析的人（`admin`、`project_owner`）可以按確認；**只有 `admin` 能審核、退回、停用** | AI 預設，可改 |
| 6 | 比對方式：和現有 `infer` 相同，正規化後**整句完全相同**才算，不做相似句 | AI 預設，可改 |
| 7 | 自動檢查沒全過就不能上線；不做自動上線 | AI 預設，可改 |
| 8 | 管理者**可以**審核自己按過確認的問法（一個帳號就能走完錄影流程）；確認人與審核人都記入稽核 | AI 預設，可改 |
| 9 | 「可以學」的判斷：使用者選的那個分析，規則判定**沒有它套用不到的條件**（`fallback.suggest` 的 `left_out(query_id)` 為空）。確認鈕、確認 API、檢查 C1 都用同一個判斷 | AI 預設（審查補充） |
| 10 | 確認時不靠存問句來比對：伺服器用規則對送來的問句**重算建議**，選的分析必須在重算結果裡。代價：只有模型補上、規則算不出的建議學不起來 | AI 預設（審查補充） |
| 11 | 「確認人數」算不同的人：同一人重複確認不累加 | AI 預設（審查補充） |
| 12 | 畫面文字照錄影：確認鈕「✓ 結果正確，記住這個問法」、審核區「使用者確認的問法（N 筆待審核）」、學會後「✓ 使用者確認過的問法・直接查詢」 | AI 預設（2026-11-05，讓簡報影片與實際畫面一致） |

## 使用流程

1. **學習前**：使用者問「哪些供應商常常遲交？」→ 照舊回建議（不改）。
2. **標記**：使用者點「查詢：供應商已收貨延遲率」→ 照舊執行模板、顯示結果。結果下方多一顆「✓ 結果正確，記住這個問法」。按下後顯示「已存成候選問法：「哪些供應商常常遲交」→ 供應商已收貨延遲率，等管理者審核」。
   - 只有使用者點的那個建議「沒有它套用不到的條件」（決定 9）才顯示這顆按鈕。後端在每個建議加一個布林欄位（例如 `learnable`），前端照它決定，不從 `omits` 文字推斷。含條件的（例如「上週…」）不顯示，因為結果沒有套用那個條件，學起來就是錯的。
3. **審核**：管理者在 AI 助手面板的「使用者確認過的問法（N 筆待審核）」區塊看到候選：問法、→ 分析名稱、確認人數、狀態。按「審核＋測試」→ 系統跑自動檢查（下節），逐項顯示 ✓／✕ 和原因：
   - 全過 → 狀態變「已上線」。
   - 有任何一項沒過 → 維持待審核並顯示原因，不能上線；管理者可以按「退回」。
   - 已上線的可以「停用」；停用後可以再按「審核＋測試」重新上線（會重跑檢查）。
4. **學習後**：任何同公司的人問同一句（正規化後完全相同）→ 規則直接選定該分析並執行，不問模型；回覆標「✓ 使用者確認過的問法，直接答對」。

## 自動檢查（「審核＋測試」）

全部在伺服器端、對該公司執行，不呼叫模型：

| # | 檢查 | 沒過的例子 |
|---|---|---|
| C1 | 條件：用 `fallback` 的規則（含該公司名稱詞彙）重算，這個分析不能有套用不到的時間、特定對象、狀態、排序比較條件（與確認時同一判斷，決定 9） | 「上週逾期任務」 |
| C2 | 危險與說明：`fallback.early_reply` 必須是 `None`（不是指令、繞過限制、他公司、無此資料、使用說明） | 「刪除逾期任務」「你可以查什麼」 |
| C3 | 衝突：這句不能已經被內建標籤、`ALIASES` 或另一筆已上線問法對到**別的**分析 | 同一句已上線為 q05 |
| C4 | 題庫不變：把這句加進白名單後，重跑內建檢查題庫，每題結果（種類與選定分析）和加入前相同 | 新問法剛好是某題陷阱題 |
| C5 | 實際執行：用該公司資料執行一次該分析模板（不指定專案），必須成功 | 查詢超過執行上限 |

- 檢查題庫放在 `api/app/ai/learning_checks.json`（API 映像檔只有 `api/app`，拿不到 `deploy/` 和測試檔）。內容從 `api/tests/test_ai.py` 的 7 題陷阱題與 `deploy/ai-demo-data/fallback-eval/` 的題目抄入，附上預期結果；題庫本身由 pytest 驗證和現行行為一致。
- 每次檢查結果（項目代碼、通過與否、原因代碼）存在候選資料列，畫面顯示最近一次。

## 資料變更

新 migration（接在 `20261104_0025` 之後）：

1. 新表 `ai_learned_phrases`
   - `id`、`organization_id`（FK）、`phrase`（正規化後的問句，≤60 字）、`query_id`（`q01`–`q16`）
   - `status`：`pending`／`approved`／`rejected`／`disabled`
   - `confirmed_by`（JSON 陣列，確認過的使用者 id，不重複；人數＝長度）、`first_confirmed_at`、`last_confirmed_at`
   - `reviewed_by`、`reviewed_at`、`checks`（JSON，最近一次檢查結果）
   - 唯一：`(organization_id, phrase, query_id)`
2. `ai_answers` 加 `suggested_ids`（JSON 陣列，預設 `[]`，只存分析 id）：記錄這次回覆給了哪些建議。**不存問句，也不存問句指紋。**
- 升級保留既有資料；downgrade 可回復。

## API

| 方法 | 路徑 | 權限 | 說明 |
|---|---|---|---|
| POST | `/ai/learning/confirm` | `admin`、`project_owner` | body：`answer_id`（那次建議回覆的 id）、`query_id`、`question`。驗證下列條件後新增或累加候選 |
| GET | `/ai/learning` | `admin` | 同公司候選清單（含最近檢查結果、分析名稱） |
| POST | `/ai/learning/{id}/approve` | `admin` | 跑 C1–C5；全過才 `approved` |
| POST | `/ai/learning/{id}/reject` | `admin` | `pending` → `rejected` |
| POST | `/ai/learning/{id}/disable` | `admin` | `approved` → `disabled` |

確認時伺服器驗證（任一不符回 4xx，不存任何東西）：
- `answer_id` 是這位使用者、這家公司的回答，`kind='fallback'`，且 `query_id` 在它的 `suggested_ids` 裡。
- 送來的 `question` 用規則重算（不呼叫模型）：`infer` 對不到、`early_reply` 為 `None`，而且 `query_id` 在**重算出的建議**裡、沒有套用不到的條件（決定 9、10）。這樣即使拿別次回覆的 `answer_id` 配一句不相干的問句，規則重算也對不上而被拒；剩下的語意判斷由管理者審核。
- 同一句（正規化後）＋同一分析已存在：`rejected` 維持不動；其他狀態把使用者 id 併入 `confirmed_by`（已在其中就不變）。

執行時：`routes/ai.evaluate` 讀該公司 `approved` 的問法，交給 `service.ask`；`service.infer` 先比內建、再比已學會的；以學會的問法選定時，回覆加 `learned: true`。

稽核（payload 只有 id 與代碼，**不含問句**）：`ai.learning.confirm`、`ai.learning.approve`（含通過與否、沒過的檢查代碼）、`ai.learning.reject`、`ai.learning.disable`。

## 畫面

- `CopilotPanel`：點建議時記住「原問句＋那次回覆的 `answer_id`」；執行結果下方在符合條件時顯示「✓ 結果正確，記住這個問法」，按下後換成已存成候選的說明；`learned: true` 的回覆顯示「✓ 使用者確認過的問法・直接查詢」。
- 新元件（例如 `LearningReview.tsx`）：只有 `admin` 看得到，摺疊區塊「使用者確認過的問法（N 筆待審核）」，列出候選與按鈕（審核＋測試、退回、停用），顯示每項檢查 ✓／✕ 與白話原因。
- 文字用正體中文、沿用現有 AI 助手樣式；使用者文字靠 React 預設跳脫。

## 不做（延後）

- 相似句、同義詞比對；自動上線；模型微調或讓模型參與審核。
- 跨公司共用；學習含條件的問句；新增分析模板；學習只有模型提出、規則重算不出來的建議（決定 10）。
- 文件問答（RAG）的回訓；刪除候選原文的功能（退回的列保留，避免同一句反覆送審）。
- 部署到使用者本機 15173 另定（見待決定）。

## 驗收情境

1. 員工角色不能確認（403）、`project_owner` 不能審核（403）；A 公司的候選與已上線問法對 B 公司完全無影響。
2. 「哪些供應商常常遲交？」→ 建議 → 點 q06 → 確認 → 管理者審核＋測試全過 → 再問同一句直接回 q06 結果並標「直接答對」。
3. 「上週逾期任務」的建議結果不顯示確認鈕；直接呼叫確認 API 也被拒。
4. 拿不屬於自己的 `answer_id`、不在 `suggested_ids` 的 `query_id`、或用這次的 `answer_id` 配一句規則重算不出該分析的問句確認 → 都被拒；同一人重複確認，人數不增加。
5. C1–C5 各有一個沒過的案例，狀態維持 `pending` 並顯示原因。
6. 停用後同一句回到給建議。
7. `ai_answers`、稽核紀錄裡找不到任何問句文字。
8. migration 升級保留既有資料、可 downgrade。

## Task

0. **簡報第 6 頁兩個小項（2026-11-05 補）**：
   - `api/tests/test_ai.py` 新增一個具名測試，明確列出「4/4 越權情境」：①看不到別家公司的文件（404）②不能指定別家公司的專案（404）③不能用 `company_id` 參數換公司（422）④角色不足不能做資料分析（403）。只整理既有行為，不改產品程式。
   - `deploy/ai-demo-data/verify.py` 的輸出加上比對組數（例如 `queries_checked`、`queries_matched`），讓「96/96」重跑看得到。
1. **資料與 migration**：`models.py`、新 migration；migration 測試。
2. **後端規則與 API**：新模組 `api/app/ai/learning.py`（正規化、確認驗證、C1–C5、讀取已上線問法）、`learning_checks.json`、`service.py`、`routes/ai.py`；`api/tests/test_ai_learning.py` 涵蓋驗收 1、3–8 與確認流程。
3. **前端**：`web/src/ai.ts`、`CopilotPanel.tsx`、新審核元件、`styles.css`；Vitest。
4. **驗收與記錄**：桌面與手機各走一次驗收 2；一次獨立審查；API pytest 全量＋Vitest 全量；PROGRESS、README 更新；簡報回饋頁頁尾「＊左側為畫面示意」改由使用者決定是否拿掉。

## 允許修改的檔案

`api/alembic/versions/<新 migration>.py`、`api/app/models.py`、`api/app/ai/learning.py`（新）、`api/app/ai/learning_checks.json`（新）、`api/app/ai/service.py`、`api/app/routes/ai.py`、`api/tests/test_ai_learning.py`（新）、既有 AI／migration 測試中因新欄位需要調整的斷言、`web/src/ai.ts`、`web/src/components/CopilotPanel.tsx`、`web/src/components/LearningReview.tsx`（新）、`web/src/styles.css`、對應 Vitest 檔、`docs/PROGRESS.md`、`README.md`；Task 0 另加 `api/tests/test_ai.py`、`deploy/ai-demo-data/verify.py`。

## 分支與 Git

- 新分支 `feature/text2sql-learning`（從 `main` 開，主 checkout，不用 worktree）。本機另有舊的未合併 `feature/review-fixes`（2026-10-22），與本工作無關、不動。
- 使用者 2026-11-05 要求做完開 PR：推送本分支到 origin 並開 PR（base `main`），**不自行合併**，等使用者確認。

## 留給實作者決定

- 檔案內部結構、函式命名、API 回應的細部欄位名稱。
- 正規化細節以現有 `infer` 為準；長度上限可微調。
- 檢查結果原因代碼與白話文字。
- 審核區塊在面板中的確切位置與樣式（參考錄影：AI 助手面板內）。
