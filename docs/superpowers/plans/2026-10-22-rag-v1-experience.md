# RAG 第一版問答體驗：差距表與實作計畫

> 狀態：人類於2026-10-22核准全部範圍及三項處理方式，開始實作；審查／20題／相關驗收通過後才備份及部署。
> 執行者使用 executing-plans 按本計畫執行；依 WORKFLOW §14／§14.1，一份合併規格／計畫、單一寫入者、階段完成一次獨立唯讀審查與一次適用完整回歸。本文件不打完成勾，真實結果寫入 PROGRESS。

**Goal：**保留專流與 AI 專案副手入口，直接對正式文件提問、追問與查證引用，文件上傳後自動備妥知識。
**Architecture：**依 A 知識生命週期、B 檢索、C 生成與互動、D 治理評估分責任，共用現有 FastAPI 後端；不拆四個服務。沿用 React／PostgreSQL／Ollama，新增持久索引排程與必要契約。
**Tech Stack：**沿用鎖版 React、TypeScript、FastAPI、SQLAlchemy、Alembic、PostgreSQL、pytest、Vitest、Playwright；本輪不新增外部依賴。
**Spec：**本文件 §1 為已確認七項規格；互動視覺參考 `artifacts/rag-chat-ui-preview.html`，不把該靜態副本當產品實作。
**盤點基準：**分支 `codex/rag-quality-handoff`，HEAD `01b211d20cfa381007d4cf2bef3aced4968c5f74`。既有未提交 PROGRESS 草稿、原型及虛構資料包均保留。

## 0. 盤點方法與限制

- 規劃盤點時僅靜態閱讀程式、既有測試與歷史報告，未重跑產品測試／真模型或查寫正式DB。下表「已有」代表當時程式存在；後續實作與真實驗收結果另記PROGRESS，不能據此宣稱整個企業架構完成。
- 歷史 Q06 修正版：原20題自動19/20、獨立語意／引用20/20；Q01替代來源造成自動評分差異。新版更改生成契約後必須重跑，不能沿用此成績。
- 圖中 KnowledgePackage／KnowledgeChange／IndexStatus／RetrievalRequest／ContextBundle／TraceEvent／AccessContext／EvaluationReport 是責任介面名稱；現有程式多以函式及dict實作，不能因概念類似宣稱已有完整同名契約。
- 圖中各20點屬相對分工估算，本計畫不承諾四組等工時。

## 1. 已確認範圍

1. 名稱與入口不變，預設正式文件；展示資料與模型設定收進管理入口。
2. 專案內預設目前專案，其他位置預設所有可見專案；可手動單選專案或全部；切範圍開始新對話。
3. 使用已確認預覽的上方範圍／新對話／放大、中間對話與初始範例、下方固定輸入／管理入口；Enter送出、Shift+Enter換行，中文組字不能誤送；保留原專流功能。
4. 完整回答、必要條件不省略；句旁編號與下方來源清單，片段／專案／文件／版本／位置及完整文件入口；缺資料、明載否定、文件衝突明確區分。
5. 支援追問，每次重新檢索；指涉不明先澄清；僅記憶體保存本次對話，關面板不清除，刷新／登出清除；新對話保留範圍，換範圍清除背景。
6. 送出即出現問題與真實等待秒數；30秒提示仍處理中；可停止等待、保留下一題草稿；失敗可手動重試，無自動反覆重送；分類顯示空資料、索引中、降級、模型失敗、逾時、權限／登入失效。
7. 專案文件（含有權查看的節點文件）上傳／改版自動排入RAG，可個別停用；管理沿用文件編輯權限、模型沿用本機admin限制；索引狀態可查／可重試。舊引用按當前權限可查，停用不刪原檔。一次審查、相關回歸、20題真模型與新流程驗收，通過後才備份／本機更新／資料保存核對。

## 2. A／B／C／D 差距表

| 模組／能力 | 已有程式與證據 | 本輪要補 | 後續再做 |
|---|---|---|---|
| A 文件與版本 | `api/app/services/document_store.py:68` save：不可變版本、hash、權限、稽核；同交易建立queued索引標記 | 新文件／新版本／文字編輯後自動消費排程；停用狀態不可被改版重啟 | 外部Drive等連接器、大量匯入管理 |
| A 解析／切片 | `rag/parsing.py:18` 支援TXT／CSV／文字PDF／DOCX；`chunking.py:1` 已有1200字父片段與400字子片段（步進320）、來源位置 | 沿用並驗回歸；不支援與無文字文件在UI明示 | OCR、多模態、語意切片、跨頁複雜表格 |
| A 索引生命週期 | `rag/service.py:64` 手動索引、有claim／hash／generation與競爭保護；save只標queued，沒有自動worker | 持久排程、重啟接續、有界重試、權限再查；統一狀態；啟用後必要時排隊 | 大型工作佇列平台、封存／清除政策、自動GC |
| A 舊版／停用 | `service.py:161,174,262` 新問答僅現行版本；歷史chunk保留；目前停用也阻擋舊引用 | 將「供新檢索」與「歷史原文再授權」分開；保留hash校驗 | 有效日期／權威層級等新產品規則 |
| B 範圍授權 | `governance.py:11` 每文件授權；`routes/rag.py` Ask必填單一project_id | 全部可見專案範圍、真正project_id／title映射、範圍統計；不能先跨租戶召回再遮蔽 | 多選專案、手選文件、細分密級／ABAC |
| B 檢索／證據包 | `retrieval.py:34` BM25式詞頻＋向量餘弦、RRF及規則加分；父片段去重、最多6來源／8000字／5000候選；`provider.py:35` embedding檢查 | 跨專案共用一次排序及全域上限；來源與專案明確；超量不靜默截斷；部分可查提示 | 獨立cross-encoder reranker、專用向量庫與規模優化 |
| B 追問理解 | `retrieval.py:15` 只把手填previous_question附在問題後，另有少量同義詞 | 有界對話背景、自動理解指涉／澄清；本輪重新檢索；舊答案不當證據 | 多語擴展、多查詢改寫、長期對話摘要 |
| C 問答協調 | `service.py:201` 真實模型、原文降級、生成前後再授權 | 結構化狀態／錯誤、追問協調、共享耗時預算、回答前再檢查 | 串流輸出、可確定停止GPU運算 |
| C 回答與引用 | `provider.py:67` 完整條件／否定／衝突prompt；`grounding.py` 證據ID回填原文、Decimal算術 | 逐回答區塊綁引用；服務端編號，句旁呈現；不能把一組引用自動貼到每句 | 自動完整語意蘊含判定／高階事實檢查 |
| C 介面 | `CopilotPanel.tsx:14` 預設demo；`:72` 正式面板關閉即卸載；`FormalRagPanel.tsx` 只有單一result、手填前題、文件清單同屏 | 正式預設、對話陣列與草稿、路由預設範圍、次要管理入口、放大／手機版、關閉保存 | 跨裝置歷史、分享／匯出對話 |
| C 等待／原文 | `FormalRagPanel.tsx` 有AbortController與晚回應防護、引用父片段；`rag.ts` ask 180秒；API原文已提供download_url但UI未接 | 等待秒數、30秒提示、停止等待／重試、完整文件入口、錯誤分類；保留回饋 | 真階段推送、伺服器取消佇列與任務管理 |
| D 權限 | `governance.py:29` 重讀ACL；source要求本人query；模型local_admin；node/project權限沿用document_store | 跨專案／追問／自動索引／歷史引用全部覆蓋；面板重開或已知撤權時清理受限內容 | 新角色體系、密級／部門規則平台 |
| D 追蹤／評估 | `governance.py:45` 無內容白名單trace；`routes/rag.py` metrics含p50/p95／降級與回饋；`evaluation.py` 檢漏權、版本、來源；現有20題報告 | 記錄新契約與prompt版本、失敗分類／階段耗時；新增7項流程評測及既有20題比較 | 全階段集中TraceEvent平台、完整Recall／Precision／忠實度平台、Token／成本計費（目前null） |

結論：已有可用的單專案RAG核心與治理基礎，缺口不是只有畫面。必須補自動索引、跨專案、對話理解、逐段引用與狀態契約；不是重寫整套檢索，也不是四個新服務。

## 3. 已核准的具體技術方案

### 3.1 共用契約

以下為擬新增／擴充的契約，不是現有API描述。新增 `api/app/rag/contracts.py`、擴充 `web/src/rag.ts`。

```ts
type RagScope = { kind: 'project'; project_id: string } | { kind: 'all_visible' };
type TurnContext = { question: string; query_id?: string };
type AskV1 = { scope: RagScope; question: string; history?: TurnContext[] };
type AnswerBlock = { text: string; source_ids: string[] };
```

- history至多最近6輪、每題2000字、合計6000字；只供理解，無assistant答案正文。完整當次對話留前端記憶體，不因推理限制偷偷刪除畫面紀錄。
- `POST /rag/ask` 支援AskV1；相容原project_id／previous_question呼叫供既有評測工具使用，不接受兩種格式混用。scope全由後端解析，不信任客戶端列出的可見專案或ACL。
- 原回應answer／citations／sources保留，新增blocks、scope、code及coverage；all_visible時project_id為null。sources增加project_title，內容仍由服務端建立。
- coverage只計授權文件：ready、queued、processing、failed、unsupported、disabled及partial；停用文件不納入可用母數。不得用不可見文件的數量洩漏存在性。
- `GET /rag/status?scope_kind=all_visible` 彙總可見範圍；單專案仍接受project_id。documents帶project_id／project_title及indexed_version，管理清單按專案分組。
- `POST /rag/queries/revalidate` 接收最多100個query_id；只檢查本公司本人紀錄，回傳可顯示／不可顯示／來源已更新的狀態，不返回隱藏文件資訊。大量對話分批查。
- `RagQuery.project_id` 改nullable以表示跨專案；trace記scope_kind，既有單專案值不改。仍只保存無內容的query metadata／source_ids，對話正文不落DB。

### 3.2 A：持久自動索引

- 新增 `rag/indexing.py`，與API同程序啟停的小型worker，5秒檢查一次，單worker同時處理1份；沿用DB原子claim防重複。多API程序也不得同時發布同份文件。
- RagIndex新增nullable `requested_by_user_id`、`requested_at`；新增 `attempts`（預設0）、nullable `next_attempt_at`。requested_by使用同公司user外鍵；不保存session token。
- save在原文件交易內設上述排程欄位；新文件預設enabled=true，改版保留false；停止文件不被worker拾取。upload成功不等待模型，也不因索引失敗回滾原檔。
- worker每次以新DB Session載入組織與排程發起人，依其當前文件編輯權限執行；模型傳送前／發布索引前再授權。帳號失效、失權或文件刪除即拒絕，不冒用admin。內部執行身分不代表可登入的使用者session。
- 重試僅限暫時故障：總共至多3次，30／120秒退避；解析不支援、內容無文字、權限失效不自動重試。現有embedding_unavailable保留關鍵字可查，同時有界重試向量，不用「ready」掩蓋降級。
- service拆出可供手動／worker共用的執行函式，避免worker先claim後又被index_document重複claim擋下；generation／版本／enabled／設定指紋檢查沿用。過期claim五分鐘可回收；晚到舊工作不能覆蓋新版本。
- 服務重啟後接續持久排程；關閉停止接新工作，進行中無法完成則由claim到期恢復。不用僅存記憶體的BackgroundTasks作為唯一保證。
- 升級不自動啟動所有歷史queued文件：舊列requested_at保持null；管理者可點重試，之後新上傳／改版自動入列。此為避免升級時意外大量模型處理的方案，不宣稱舊文件已自動補齊。
- 新版未索引完成時，維持現有「新問答不使用舊版」；清楚顯示目前版本準備中、先前已索引版本，其他就緒文件仍可查並提示partial。
- 停用只排除新檢索；歷史引用仍需query屬主、公司、目前文件讀權、不可變版本及hash校驗。移除的是歷史讀取的enabled限制，不是ACL。

### 3.3 B：跨專案與追問

- 新增 `rag/conversation.py`；解析scope、授權與指涉，不把來源內容當指令。
- 全部專案先列本公司可見專案，再逐文件套用既有權限；一次合併候選、全域5000上限，超過回傳請縮小範圍，不偷偷只查前5000筆。維持6來源／8000字上限，跨專案不宣稱窮盡所有資料。
- public_source的project_id取文件真實project_id；provider收到project_title，回答不同專案分開寫。
- history中的query_id逐一驗本人、公司與同scope；舊來源已失權則停止沿用背景；來源有改版只作題意提示，證據一定重查現行版。
- 指涉問題用本機模型產生有界JSON `{standalone_question, needs_clarification, clarification_question}`；只給本次／歷史問題及再授權的來源標題。不能提供答案或執行工具；模糊時回傳澄清問題，不假裝知道。
- 不含指涉的獨立問題直接檢索；改寫失敗時，能獨立理解的問題原樣查詢，依賴指涉的問題要求使用者補明對象。
- 所有文字為不可信輸入；query_id不是權限憑證。最後回答只依這次新證據，不依歷史模型說法。

### 3.4 C：引用與對話

- provider新增帶evidence IDs的回答區塊；grounding逐塊解析成來源ID與原文對應，未知ID拒收；UI依首次出現順序產生[1]、[2]，不接受模型生成連結或原始HTML。
- 陳述事實的區塊須有證據；澄清／無資料為明確kind，不能用無引用正文夾帶事實答案。ID／quote合法不等於語意正確，仍須20題內容複核。
- Decimal計算維持伺服器產生結果，計算區塊附操作數來源，不能因新blocks回到模型自由算術。
- 前端以message.id綁query_id、sources、狀態與原文抽屜，不能以最新result覆蓋舊問題引用；保留既有有幫助／無幫助回饋。
- WorkspaceShell傳實際route.projectId給面板，不能拿scope標題反查ID。手動範圍在同一位置保留；路由所屬專案改變才套新預設、重設對話。同專案節點／頁籤切換不清除。
- 對話state置於不隨open卸載的層；登出／切帳號／切公司清空，開關面板不清；禁用localStorage／sessionStorage持久化對話。
- 背景權限變動不可能靠純前端瞬間得知：面板重開／視窗恢復焦點先遮住舊答案並revalidate，顯示中30秒輪詢；收到撤權即清除相關答案／引用，新查詢及原文API總是即時授權。不宣稱已顯示過的內容可以遠端抹除。
- 新增 `RagConversation.tsx`、`RagKnowledgeManager.tsx`、`RagSourceViewer.tsx`，FormalRagPanel做協調；舊展示流程保留於管理入口內，不刪SQL／舊模型功能。
- download_url經既有同源/API路徑規則使用，不能把`/documents/...`錯連到前端頁面；服務端下載再授權，401/403/404清晰提示。原文位置高亮只用安全文字節點，不用dangerouslySetInnerHTML。

### 3.5 C／D：等待與錯誤

- 初版僅「查詢文件並整理回答」與elapsed，不做SSE或虛構階段百分比。30秒輕提示，180秒前端逾時沿用，nginx195秒沿用。
- ask後端總預算170秒；查詢向量至多90秒、可選改寫15秒、生成60秒，且各階段取剩餘預算（索引embedding獨立維持120秒）。耗時需實測，不能把預算當保證回應時間。
- stop只abort本次客戶端等待、使request generation失效；保留題目，允許下一題，晚到回應不得覆寫。提示「已停止等待；伺服器可能仍在處理」。不增加後端強制取消承諾。
- 管理狀態、來源讀取與問答各自busy／controller，不共用一個busy鎖住整個面板。
- 定義安全機器碼：no_documents、index_pending、partial_coverage、embedding_unavailable、generation_unavailable、generation_timeout、scope_limit、source_changed、access_changed、clarification_required。前端白名單映射繁中訊息；傳輸401／403／404仍尊重現有ApiError。provider原始錯誤不直送瀏覽器。
- 生成失敗可保留現有原文降級，但必須明示「未產生回答，以下是檢索原文」，不得當成功模型答案。每題重試使用原題與原scope，換scope後不能誤重送舊範圍。
- trace擴充scope_kind、契約／prompt版本與階段耗時／失敗碼，不記問題、答案、原文、憑證。usage無真值仍null。

## 4. 實作順序、檔案與交付點

以下已於2026-10-22核准；分工是責任而非同檔多代理同時寫入。

### Task 1 — D先定契約與資料保存，A/B/C共用

新增 `api/app/rag/contracts.py`、`api/alembic/versions/20261022_0021_rag_experience.py`；修改 `api/app/rag/models.py`、`api/tests/test_rag_migration.py`；新增 `api/tests/test_rag_contracts.py`。

1. 先以隔離資料庫建立既有單專案queries／indexes／versions／chunks，測升級後列值、FK與hash不變。
2. 按§3.1／3.2新增nullable project_id與排程欄位；舊資料不回填自動任務。保留原公司複合FK；回退遇跨專案query或排程資料不得靜默刪欄丟資料。
3. 契約測試：空scope、混用格式、超量history、超長問題皆422；原評測單專案格式仍可用；前端不能傳ACL。
4. 通過後提交 `Feat: define scoped RAG contracts and durable index metadata`。

### Task 2 — A自動索引與生命週期

新增 `api/app/rag/indexing.py`、`api/tests/test_rag_indexing.py`；修改 `api/app/services/document_store.py`、`api/app/rag/service.py`、`api/app/main.py`、`api/tests/test_documents.py`、`api/tests/test_rag_api.py`、`deploy/docker-compose.yml`、`deploy/.env.example`。

1. 新增失敗情境：上傳後無手動index也完成；worker重啟可接續；disabled改版不排入；版本競爭只發布最新版；原檔保留；失權不呼叫模型；暫時故障有界重試。
2. 實作§3.2，main lifespan由 `PF_RAG_AUTO_INDEX=true`控制worker；部署範本明示、測試預設關閉，測worker用隔離DB。原有附件runtime_lock必須維持。
3. 手動index仍可使用；重試重設attempts並記排程發起人；啟用後必要時enqueue。文件save回傳仍相容DocumentManager。
4. 歷史source read不因停用拒絕，但撤權必須拒絕；新增此差異測試並更新舊斷言。
5. 提交 `Feat: automatically index authorized document revisions`。

### Task 3 — B跨專案與追問

新增 `api/app/rag/conversation.py`、`api/tests/test_rag_conversation.py`；修改 `api/app/rag/governance.py`、`api/app/rag/retrieval.py`、`api/app/rag/service.py`、`api/app/rag/provider.py`、`api/app/routes/rag.py`、`api/tests/test_rag_api.py`、`api/tests/test_rag_governance.py`、`api/tests/test_rag_pipeline.py`。

1. 用兩個可見專案、一個不可見專案、不同公司的相同文件名測跨專案檢索與來源標記，驗模型輸入不含禁讀內容。
2. 實作scope解析／候選／status／coverage，單專案保留；測候選上限明確拒絕而非截斷。
3. 實作bounded history、改寫／澄清及共享耗時預算；測「G2→誰簽核」、兩階段歧義、偽造query_id、換scope、歷史失權與新版取代。
4. 新增revalidate API；撤權不得只在畫面隱藏；回答回傳前仍再授權。
5. 提交 `Feat: retrieve authorized projects and resolve follow-up questions`。

### Task 4 — C句旁引用與可驗證回答

修改 `api/app/rag/provider.py`、`api/app/rag/grounding.py`、`api/app/rag/service.py`、`api/app/rag/governance.py`、`api/tests/test_rag_grounding.py`、`api/tests/test_rag_pipeline.py`、`api/tests/test_rag_governance.py`。

1. 固定模型adapter測：每塊來源正確、未知ID拒收、無證據事實拒收、引用去重編號、衝突引用雙方、Decimal來源連結；不硬編Q06答案。
2. 擴充evidence映射至blocks，同時保留answer／citations供舊工具使用。trace的prompt_version同步更新，不仍記evidence-v2。
3. 原Q06／改名／免簽核／Q18 opt-in真模型案例在候選契約上重跑，失敗不得以原文降級視為通過。
4. 提交 `Feat: bind answer statements to verified document citations`。

### Task 5 — C問答介面與管理入口

新增 `web/src/components/RagConversation.tsx`、`RagKnowledgeManager.tsx`、`RagSourceViewer.tsx`、`web/src/rag-conversation.test.tsx`；修改 `web/src/components/FormalRagPanel.tsx`、`CopilotPanel.tsx`、`WorkspaceShell.tsx`、`web/src/App.tsx`、`web/src/rag.ts`、`web/src/styles.css`、`web/src/rag.test.tsx`、`web/src/ai.test.tsx`、`web/src/workspace.test.tsx`。後者同步核准需求衍生的正式預設斷言，保留Esc／焦點／launcher驗證，不改產品範圍。

1. 按§1／§3.4／§3.5串接新契約；沿用名稱／launcher、焦點返回及Esc操作，放大不得遮住關閉／輸入。
2. 新建對話state與每題狀態；拆出來源及管理UI；模型設定權限保留local_admin，不因收進管理而放寬。
3. Vitest假時鐘驗30秒提示、180秒逾時、停止後晚回應、重試不重複題、IME、關閉重開、換scope／logout／公司隔離；測來源對應舊問題而非最新答案。
4. 既有展示／SQL功能從管理入口可達；正式畫面不暴露模型參數與全部文件清單。新範例問題僅是提問，不硬編答案。
5. 提交 `Feat: make formal RAG the default copilot conversation`。

### Task 6 — D相關回歸、品質及獨立審查

修改 `web/e2e/rag.spec.ts`、`api/app/rag/evaluation.py`、`api/tests/test_rag_evaluation.py`；新增 `web/e2e/rag-conversation.spec.ts`、`artifacts/rag-v1-2026-10-22/evaluate.py`、`artifacts/rag-v1-2026-10-22/README.md`。評測輸出新檔，不覆蓋舊20題、標準答案或報告。

- API在api工作目錄使用既有venv執行：`python -m pytest tests/test_rag_contracts.py tests/test_rag_indexing.py tests/test_rag_conversation.py tests/test_rag_api.py tests/test_rag_pipeline.py tests/test_rag_grounding.py tests/test_rag_governance.py tests/test_rag_evaluation.py tests/test_rag_migration.py tests/test_documents.py -q`。
- live測試另設`PF_RAG_LIVE_TESTS=1`執行 `python -m pytest tests/test_rag_grounding.py -k live -q`，環境不存在要記skip，不可報通過。
- web工作目錄：`npm test -- src/rag.test.tsx src/rag-conversation.test.tsx src/ai.test.tsx src/documents.test.tsx`、`npm run build`；修改共享shell另加現有workspace/app相關測試（按檔案實際測試名選取，不藉此重跑歷史全部API）。
- Playwright以既有隔離15175環境與acceptance marker，`npm run e2e -- e2e/rag.spec.ts e2e/rag-conversation.spec.ts`；1280／375兩尺寸。禁止寫入15173，沿用playwright.config.ts的拒絕保護。
- 隔離PostgreSQL驗0020→0021 migration與worker並行claim，不只以SQLite證明資料安全。
- 真模型新runner沿用 `artifacts/rag-demo-data-2026-10-21/run_demo.py` 的固定20題來源／題目，支援新blocks並保存實際輸出／檢索來源／版本／模型／prompt版本／耗時。獨立語意與引用複核必須20/20；自動評分若有替代來源誤判逐題附證據，不改題目湊分。
- 另增跨專案衝突、G2追問簽核、兩階段歧義澄清、無來源、部分索引、停用舊引用、權限撤銷等流程案例，不塞入原20題分母。
- 一次獨立唯讀審查檢查七項／權限／資料保存／核心競爭；修正後只重跑受影響部分。測試摘要、exit code、skip原因與真模型結果完整保存。
- 提交 `Test: verify the RAG conversation and knowledge lifecycle`。

### Task 7 — 核准實作且驗收通過後的交付程序

修改 `README.md`、`docs/formal-rag.md`、`docs/PROGRESS.md`、`docs/rag-quality-handoff.md`；新驗收報告 `artifacts/rag-v1-2026-10-22/驗收結果.md`。

1. 先判定所有阻擋驗收均通過，確認實作／部署授權有效；目前使用者要求只規劃，此步絕不能提前執行。
2. 將pg_dump／原檔／設定與現況指紋保存於ignored `.superpowers/rag-v1-deploy-20261022/`，確認備份可讀；秘密不提交。
3. 有窗口後暫停寫入、停止新增worker任務，做一致備份，再升migration及更新API／web。DB容器不重建、不seed、不restore正式資料。新派生資料／索引／trace分開與原業務表核對。
4. 驗health、正式入口、模型連線及現有資料查詢；核對原資料／檔案hash、歷史引用與版本不變；新增欄位為預期差異。
5. 舊queued文件不全量自動啟用；列出仍待處理文件供管理者確認。僅處理本輪合法enqueue與必要的已知索引相容工作。
6. 若失敗停止新worker並維護模式，不用可能遺失新資料的強制downgrade；保留現場，依相容舊映像／前向修復決策處理，不自動覆蓋還原。
7. 提供試用入口、限制及人類驗收清單；不代勾人類簽核。不新增push／PR／merge授權。

## 5. 驗收矩陣與停止條件

| 已確認項目 | 必須實證 |
|---|---|
| 1 入口 | 開啟即正式文件；名稱／launcher不變；管理入口仍可到展示／SQL |
| 2 範圍 | 專案與總覽預設正確；手動切換重設；同專案頁籤不誤清；跨公司／禁讀節點零洩漏 |
| 3 畫面 | 1280／375無橫向溢位；固定輸入、放大／關閉、鍵盤／中文組字；正式主介面功能保存 |
| 4 引用 | 每則引用對應正確query；句旁編號可查原文、版本／專案／位置；完整下載再授權；Q06／Q18及20題 |
| 5 追問 | 真實連續追問、歧義澄清、每次新檢索；關閉保留、刷新／登出／切公司清除；重開先再授權 |
| 6 等待 | 即刻顯題、30秒提示、stop／晚到隔離、重試、逾時、部分索引與降級明示 |
| 7 知識與交付 | 三種寫入（新檔／新版本／文字編輯）自動排程、重啟恢復、停用與競爭、原資料保存、權限與備份證據 |

任一資料遺失／越權、未完成承諾主流程、20題內容不合格或必要migration保存測試失敗，均不得更新本機交付。UI細小間距等不影響流程問題記後續，不擴充未核准功能。

## 6. 本輪不做

OCR／圖片理解、外部知識連接器、多選範圍、長期對話儲存／分享、獨立重排序模型、新向量資料庫、真正GPU取消、SSE、密級平台、全面可觀測性／成本系統、資料自動清除／封存。保留現有功能，不以刪除其入口當作簡化。

## 7. 本次規劃交接

已確認七項產品範圍與A/B/C/D責任。本文件的worker／契約／migration／預算是程式盤點後提出的實作方案，待人類確認。僅新增本計畫與PROGRESS工作紀錄；未修改產品／測試／部署、未運行真模型或資料遷移。下一步是人類審閱，不自動開工。
