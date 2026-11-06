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
| 目前工作項目 | **README-WEEKLY ✅**（2026-11-07，main）：依使用者「根據現在的進度 github上的readme 有需要更新的嗎」→「更新並推送」：README §5週報列補上句中數字檢查、§3／§5「每次push」改為「推到main或開PR時」（CI只在push main、PR、手動觸發時跑）；product-spec §1週報描述補句中數字檢查、§6刪除已完成的「週報句中數字檢查」。前一項：**WEEKLY-AI-NUMBERS ✅**（2026-11-07，已由[PR #13](https://github.com/chenliyu0410/projectflow/pull/13)合併進main `12119cd`，本機分支已刪除）：依使用者「WEEKLY-AI-m1」，AI週報每段的阿拉伯數字必須出現在facts中，否則該段改用系統條列（全形轉半形、千分位、前導0正規化；[T1]代號不算）。`test_weekly_reports.py`新測試RED 1 fail（exit 1）→GREEN；一次獨立審查Ready、4個minor（全形、逗號已修，另2點記為限制）；回歸weekly＋n8n 22 pass（exit 0）。2026-11-07依使用者「請幫我對齊這個專案的CI」在本機照`.github/workflows/ci.yml`跑：API全量1251 pass／18 skip（exit 0，Python 3.12，無PG）、Vitest與build（exit 0）、deploy腳本編譯與n8n流程比對（exit 0）；未跑：PostgreSQL job、Demo job、Compose config（本機無Docker／Chromium）。見[短規格與計畫](superpowers/plans/2026-11-07-weekly-ai-numbers.md)。待使用者決定合併／push。前一項：**INBOX-REMOVAL ✅**（2026-11-06，已`--ff-only`合併進main並push origin `b6f5a5c`，分支已刪除；含CI更新）：依D90，簡報拿掉收件匣（P.37四個流程、P.39系統內上傳示範並重錄影片）；之後依使用者「n8n 的收件匣排程實際上還在每分鐘跑的程式 請改掉」移除收件匣資料夾掃描（n8n流程、掃描API、`inbox_service`、收件匣掛載），Excel不另做；15173的n8n已停用該流程。見[短規格與計畫](superpowers/plans/2026-11-06-inbox-removal.md)頂端框與§2。前一項：**TEXT2SQL-EXPANDED-TESTS**（組員，已由PR #12合併進main `8137c9c`）：**TEXT2SQL-EXPANDED-TESTS 🟢**：100陷阱、100權限、64正常、8回訓、2完整性分批通過；回歸89 pass／1 skip；獨立審查完成；使用者決定保留96新題＋4既有題，已開[PR #12](https://github.com/chenliyu0410/projectflow/pull/12)，待審閱、不合併；前一項： **TEXT2SQL-LEARNING 🟢 PR待使用者確認**（2026-11-05，`feature/text2sql-learning`）：確認過的問法學起來（使用者確認→管理者審核＋自動檢查→補進白名單→同一句直接答對），另補簡報第6頁兩個小項（4/4具名測試、verify.py印組數）。計畫：`docs/superpowers/plans/2026-11-04-text2sql-learning.md`。TEXT2SQL-FALLBACK已由PR #10合併進main。以下為前一項：**TEXT2SQL-FALLBACK 🟢 待使用者確認**（2026-11-04，`feature/text2sql-fallback`，未合併、未推送）：資料分析被拒答時分層降級（拒答／預寫說明／說出不支援的條件並建議最多3個分析，按下才查），見[短規格與計畫](superpowers/plans/2026-11-04-text2sql-fallback.md)與§2。前一項：**AUTOSTART-N8N ✅**（2026-11-03）：開機捷徑／`deploy/start.py`在設定過n8n時一起啟動n8n與Mailpit（見§2）。前一項：**RAG-PORT ✅**（2026-11-02）：依D88以main的AI助手（LEE版）為主體，從Mina的RAG-V1（`origin/feature/review-fixes`，PR #5）移植五項：連續追問、上傳後自動建索引、停用／恢復文件知識、回答回饋、引用原文檢視。[短規格與計畫](superpowers/plans/2026-11-02-rag-port.md)已實作、審查並`--ff-only`合併回main（見§2）。前一項：N8N-COMPLETE 🟢（見§2）；再前一項如下。**OCR-PIPE 🟢**（2026-10-28）：依架構圖做文件解析管線，計畫見[plan](superpowers/plans/2026-10-28-ocr-pipeline.md)，成果見[成果報告](ocr-pipeline-report.md)。逐頁分路（文字層／OCR／Office）、前處理、清理正規化、檔名＋頁碼metadata、1−CER與分路秒數報告；`PF_AI_OCR`開關＋可選OCR Docker映像，斷網Linux容器實測與Windows結果一致。使用者指示（2026-10-28）：正式文件索引改走ingest()（3df25c6，索引版本4，相關測試161 pass）；本機Docker已用OCR映像重啟（PF_AI_OCR=true、模型唯讀掛載、雜湊OK）。正式文件索引仍限SQLite隔離環境（Docker／PostgreSQL不建索引）；使用者選「隔離版預覽」：repo外資料夾 `output/ocr-preview/`（SQLite＋seed、OCR＋正式索引＋自動更新），`deploy/portable/serve.py` 跑在127.0.0.1:15177。2026-10-29實測：上傳「設備借用簽收單-掃描2頁.pdf」索引狀態「OCR辨識，2頁，平均信心0.96」；AI副手選「正式文件與附件」提問，來源2段各標「第1頁／第2頁」與「可能有錯字」、頁首尾已去除、斷行已接回（模型未啟用，只顯示檢索原文）。2026-10-29依要求重置預覽：舊資料夾移至資源回收筒，重建後只放回範例掃描檔。前一項：**PORTABLE＋AI-DEMO-DATA 🟢 待第三層驗證**（2026-10-24）：可攜展示包（Windows x64，內含Python、Ollama、本地模型、OCR、乾淨展示資料與重建的「原有展示資料」Text-to-SQL，只綁127.0.0.1）。前一項ACCOUNTS 🟢、DOC-TEMPLATE 🟢已推送分支。再前一項：**TEXT2SQL-FALLBACK**（已由PR #10合併進main）（2026-11-04，`feature/text2sql-fallback`，未合併、未推送）：資料分析被拒答時分層降級（拒答／預寫說明／說出不支援的條件並建議最多3個分析，按下才查），見[短規格與計畫](superpowers/plans/2026-11-04-text2sql-fallback.md)與§2。前一項：**AUTOSTART-N8N ✅**（2026-11-03）：開機捷徑／`deploy/start.py`在設定過n8n時一起啟動n8n與Mailpit（見§2）。前一項：**RAG-PORT ✅**（2026-11-02）：依D88以main的AI助手（LEE版）為主體，從Mina的RAG-V1（`origin/feature/review-fixes`，PR #5）移植五項：連續追問、上傳後自動建索引、停用／恢復文件知識、回答回饋、引用原文檢視。[短規格與計畫](superpowers/plans/2026-11-02-rag-port.md)已實作、審查並`--ff-only`合併回main（見§2）。前一項：N8N-COMPLETE 🟢（見§2）；再前一項如下。**OCR-PIPE 🟢**（2026-10-28）：依架構圖做文件解析管線，計畫見[plan](superpowers/plans/2026-10-28-ocr-pipeline.md)，成果見[成果報告](ocr-pipeline-report.md)。逐頁分路（文字層／OCR／Office）、前處理、清理正規化、檔名＋頁碼metadata、1−CER與分路秒數報告；`PF_AI_OCR`開關＋可選OCR Docker映像，斷網Linux容器實測與Windows結果一致。使用者指示（2026-10-28）：正式文件索引改走ingest()（3df25c6，索引版本4，相關測試161 pass）；本機Docker已用OCR映像重啟（PF_AI_OCR=true、模型唯讀掛載、雜湊OK）。正式文件索引仍限SQLite隔離環境（Docker／PostgreSQL不建索引）；使用者選「隔離版預覽」：repo外資料夾 `output/ocr-preview/`（SQLite＋seed、OCR＋正式索引＋自動更新），`deploy/portable/serve.py` 跑在127.0.0.1:15177。2026-10-29實測：上傳「設備借用簽收單-掃描2頁.pdf」索引狀態「OCR辨識，2頁，平均信心0.96」；AI副手選「正式文件與附件」提問，來源2段各標「第1頁／第2頁」與「可能有錯字」、頁首尾已去除、斷行已接回（模型未啟用，只顯示檢索原文）。2026-10-29依要求重置預覽：舊資料夾移至資源回收筒，重建後只放回範例掃描檔。前一項：**PORTABLE＋AI-DEMO-DATA 🟢 待第三層驗證**（2026-10-24）：可攜展示包（Windows x64，內含Python、Ollama、本地模型、OCR、乾淨展示資料與重建的「原有展示資料」Text-to-SQL，只綁127.0.0.1）。前一項ACCOUNTS 🟢、DOC-TEMPLATE 🟢已推送分支。 |
| 模式 | 展示優先精簡流程（D81／WORKFLOW §14）；使用者試用另簽核。 |
| 下一個動作 | 待使用者：到GitHub的Actions頁確認`b6f5a5c`這次CI五個job（API、PostgreSQL、Web、Demo、Deploy）都通過（本機無法查看私人repo的執行結果）；15173要重新執行`python deploy/start.py`重建API後，掃描API才會從執行中的系統移除（排程已停）。可選：§5 WEEKLY-AI-m1。 |
| 分支 | `main`（WEEKLY-AI-NUMBERS 由PR #13合併後刪除本機`feature/weekly-ai-numbers`）。之前：`main`（INBOX-REMOVAL 2026-11-06 在`feature/inbox-removal`完成後`--ff-only`合併並刪除分支）。 |
| 最新程式 commit | INBOX-REMOVAL `4706f6d`、CI `de2e205`／`b6f5a5c`（已推送）。以下為前一項：TEXT2SQL-LEARNING `371ce19`（PR）。以下為前一項：ACCOUNTS（本筆）；DOC-TEMPLATE `012ec59`。 |
| 行號基準 | `dfc0126`；舊明細行號會隨新增程式位移，請以函式名定位。 |
| 測試基準 | TEXT2SQL-LEARNING（2026-11-05）：`test_ai_learning.py` RED（collection error，exit 2）→GREEN；審查應修1 RED 2 fail（exit 1）→GREEN；D90 RED 1 fail（exit 1）→GREEN。AI相關5檔113 pass／1 skip（PG）。API全量（修正前一次）983 pass、20 fail、17 skip：19 fail是這台缺python-docx（test_doc_templates 18、test_ocr_pipeline 1，與本次無關），1 fail是`test_health`路由白名單漏新路徑，補上後重跑24 pass；之後兩個修正只重跑受影響檔。`verify.py` `queries_checked 96`／`queries_matched 96`；holdout 18/20不變。Web Vitest全量42檔387 pass、build exit 0。隔離SQLite＋`deploy/portable/serve.py` 127.0.0.1:15195（模型關）：1280走完四步（學習前→標記→審核C1–C5全過→學習後直接查詢）、「上週逾期任務」無確認鈕、375審核區無橫向捲動；資料庫逐表搜尋，問句只在`ai_learned_phrases.phrase`。以下為前一項：TEXT2SQL-FALLBACK（2026-11-04）：新增`test_ai_fallback.py`（RED：collection error，exit 2→GREEN 26 pass；審查修正RED 14 fail→GREEN 46 pass）；`test_ai.py`＋`test_ai_gateway.py`＋`test_ai_fallback.py` 65 pass；API全量942 pass、17 skip（專用PostgreSQL未設定、PIL未安裝），exit 0，約93分鐘。Web Vitest全量41檔376 pass、`npm run build` exit 0。題庫量測（模型關，`measure.py`）：調整用30題 舊5/30→新30/30（寫規則時看過題目，不當成效）；驗證20題（規則寫完才出題，先commit `4699718`才跑）舊4/20→新18/20，審查修正後仍18/20。模型開未量：這台只有`bge-m3`向量模型。以下為前一項：AUTOSTART-N8N（2026-11-03）：`api/tests/test_deployment.py`＋`test_public_trial.py` 84 pass、exit 0（只改部署腳本，未跑API全量）。以下為前一項：RAG-PORT（2026-11-02）：API pytest全量885 pass／17 skip、exit 0（審查者在`190104a`複跑；我方先跑880 pass／5 fail，修正cp950讀compose與路由白名單後重跑相關檔通過）。Web Vitest全量41檔373 pass，審查修正後相關檔32 pass；`npm run build` exit 0。專用PostgreSQL（本機暫時容器跑`.github/scripts/run_postgresql_tests.py`）：10個migration階段全過，新測試`test_postgresql_formal_index_updates_and_answers_without_acceptance_mode`通過；「API races」4個既有測試在Windows因`msvcrt`檔案鎖失敗（兩個TestClient同搶附件鎖檔，與本次無關，以CI的Linux為準）。隔離預覽127.0.0.1:15181（SQLite驗收模式）1280／375走完展示路徑，本地模型開／關各一次。以下為前一項：OCR-PIPE（2026-10-28，`feature/ocr-pipeline`）：後端全量（不含test_ai_local_model）873 pass、15 skip（14項需專用PostgreSQL、1項真模型測試路徑寫死repo外output），0 fail；新增`test_ocr_pipeline.py` 18項。一次獨立審查（§14）：唯一阻擋＝`ocr.preprocess`放大無上限（細長圖2×4000→1000×2000000，既有正式索引OCR路徑也受影響），已改為最多4倍且不超過4000萬像素並補測試（RED→GREEN）；OCR相關測試27 pass、1 skip，Demo指令重跑數字不變。非阻擋待後續：ingest未套MAX_TEXT、頁碼規則可能刪掉頁緣的單獨數字（金額／日期）、2～3頁文件頁首尾判定偏積極、單列工作表會被當表頭、`ocr.identity()`不含前處理版本、compose改`PF_AI_OCR`需重建映像。前端Vitest 38檔356 pass。真模型：Windows與`--network none` Linux容器1−CER相同（清晰92.4%、模糊89.9%、掃描2頁92.8%）。ACCOUNTS：後端全量（不含需本地模型的test_ai_local_model）766 pass、15 skip（需專用PostgreSQL）、1 fail；該fail為`test_child_creation_matrix`，原因是DOC-TEMPLATE新增資料表後舊資料包（revision 0019）匯入找不到新表檔案，已修`demo_pack.import_pack`只匯入資料包列出的表，重跑matrix＋demo_pack 3 pass。帳號相關API 12 pass；前端Vitest全量34檔330 pass（一次偶發1 fail重跑通過）、build exit0；Playwright帳號3＋樣板4＋文件2 pass（1280／375，隔離SQLite升到`20261024_0021`）。既有`health.spec`在SQLite環境3 fail：readiness只認PostgreSQL（環境限制）；另2項卡在「進入階段：小量試作」按鈕停用，為PHASE-CARDS（10/13，只開放進行中階段）後測試未更新的既有問題，與本次無關、未修。AI題庫基準不變。 |
| 資料版本 | TEXT2SQL-LEARNING新增migration `20261105_0026`（`ai_learned_phrases`表、`ai_answers.suggested_ids`預設[]；只新增，有候選時拒絕有損降級）。以下為前一項：RAG-PORT新增migration `20261102_0024`（`documents.ai_enabled`預設true、`ai_answers`表；只新增，有停用文件或回饋資料時拒絕降級）。以下為前一項：新增migration `20261024_0021`（users加status、must_change_password、last_login_at、password_changed_at，舊帳號維持啟用）與 `20261024_0020`（3張樣板表＋document_versions兩個可為空欄位；只新增，降級遇資料拒絕）。新依賴docxtpl 0.20.2（＋Jinja2、lxml、python-docx）已鎖版。AI隔離索引INDEX_VERSION仍為3；OCR模型在repo外。 |
| 認領中 | 無；保留15176／18006／11436回環隔離服務，Qwen3-4B-Instruct-2507 Q4_K_M，雲端關閉。 |
| 阻塞／待使用者 | 使用者試用簽核：2026-10-24 使用者表示「簽核都沒問題了」（依repo外`output/專流試用簽核重點.html`的10段重點，以本機SQLite一鍵啟動版`output/projectflow-local/start-projectflow.bat`試用；使用者表示不匯出簽核表）。限制：此環境沒有本地模型，AI問答段沒有在本機實測；mvp-trial-checklist逐項勾選未由AI代勾。正式Docker問題本輪未重試；向量／OCR／分級繼承／遮罩／雲端政策／大量資料排程待後續。 |
| 遠端 | 2026-10-24 依使用者「github可以推」推上 `origin/feature/rag-starter-import`；同日DOC-TEMPLATE `012ec59` 依使用者「Push feature/rag-starter-import to GitHub (branch only, no merge or PR)」再推一次；同日ACCOUNTS `e9b2db6`（含試用簽核紀錄與帳號規格）依同樣指示再推（只推分支，未合併main、未開PR、未部署）；同日TEMPLATE-TRIAL與PORTABLE（含本筆紀錄）依同樣指示再推，可攜包壓縮檔在repo外、不在git；同日AI-DEMO-DATA（含`deploy/ai-demo-data/pack`）依同樣指示再推；同日COPILOT-LAYOUT兩輪版面調整依同樣指示再推；同日COPILOT-SCENARIOS示範情境選單依同樣指示再推。mina201199的兩個遠端分支依決定暫不處理。 |

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
| ⛔ | 阻塞 | 要等決定才能繼續（寫明 D 編號） |
| ⏸ | 暫停 | 使用者要求先停，分支保留（寫明恢復條件） |
| ✖ | 取消 | 使用者決定不做，分支保留，spec 和 plan 標成 Superseded |

---

## 1. 目標層級

1. **北極星**：以「專案」為核心的 AI 工作流工具，涵蓋多層任務、前置條件、權限、文件、AI 副手和研發營運資料，部署在公司內網，資料不外流（見 [README](../README.md) 開頭）。
2. **兩條軌道**
   - **Demo 驗證軌（保留參照）**：單檔 `projectflow-full-demo.html` 的F1–F11及W6已完成Demo驗證，P0不修改。
   - **正式產品軌（D51／D52已啟動）**：React + TS、FastAPI + PostgreSQL、內網部署；本輪到P1c。
     - README §8 只列正式版還沒做的項目（D82）。Demo 已經做出來的功能**不能**當成正式版已完成。
     - 何時啟動由使用者決定（D11）。啟動後第一個工作項目是 P0。
3. **目前里程碑**：依序完成 W1 → W2 → W3（精簡版，D31／D42），讓 Demo 具備可自行新增、編輯、套用工作流的功能架構。2026-10-05 起依 D42，個別工作流內容之後由使用者自行添加；D41 的兩份現有專流只作內建範例與測試素材。
   - **Demo歷史展示模式**（D30，2026-10-05）：當時範圍僅Demo，W4取消、W5精簡；2026-10-08 D51／D52已另授權正式P0至P1c，正式軌恢復完整審查與安全標準。Demo歷史minor不自動擴張目前plan。
4. **Demo 驗證軌的完成條件**（2026-10-05 依 D30 精簡）
   - [x] W1、W2、W3（精簡版）都是 ✅
   - [x] W5 ✅：README §1 快速開始、§2 功能總覽反映 full demo 的現況
   - [x] 用 W3 的工作流架構新增／編輯／套用一套工作流，並以 yu、chen、ming 各走一次主要流程，桌面和 375px 都沒有水平捲動，console 沒有錯誤（2026-10-05 Claude 在 `cfd5f72` 上實測：it 新增、編輯、複製工作流；yu 用「筆電新機種專流」建立專案（9 階段、44 個任務），第二階段任務被 G0 擋下，覆寫閘門後可開始；yu、chen、ming 的看板、時程、成員、我的任務、模板庫在 1280 與 375px 都沒有 `undefined`／`NaN`／「? —」、沒有水平捲動，console 沒有錯誤。小問題記成 §5 DEMO-A-m1–m4，D43 待使用者）
   - [ ] 使用者確認可以拿來展示（原 README 階段 0 的驗收：「能用 Demo 向他人完整說明產品概念」）
   - 原本的「W4 全部 FIXED」「D4–D8 都有結論並執行」兩項，2026-10-05 依 D30 移除（W4 取消，D4–D8 維持現狀）。

   全部達成後，AI 在 §7 寫一份「Demo 軌結案摘要」（完成項目、遺留問題、建議的 P0 和 P1 範圍），並把 D11 標成「待使用者（可決定）」。

---

## 2. 工作佇列（由上往下執行）

- README-RESTRUCTURE ✅（2026-11-06，使用者指示「commit 並 push」後推上main）：使用者貼上README架構範例（1.解決甚麼問題 2.簡易動畫 3.用了哪些技術？為甚麼？ 4.架構 5.工程亮點 6.快速開始 7.深入閱讀 8.授權），指示「把目前的readme改寫成這樣簡單架構，動畫先空著等等補上」。做法：README改寫成這8段；原README的詳細內容不刪，原文搬到`docs/product-spec.md`（§2–§10，重新編號，§6架構原文放在新§9，開頭附舊章節對照）與`docs/getting-started.md`（§1快速開始、給接手的人）；AGENTS.md第1節與文件地圖同步。動畫在README §2留註解位置待補。同日使用者提供新架構圖並指示「架構圖用這張，然後技術亮點用表格簡單呈現，現在這樣太複雜了不知道解決甚麼問題」：圖重畫成向量檔`docs/media/architecture.svg`，README §4改為配圖＋三個編號說明，§5改成「要解決的問題／我們的做法／結果」表格。之後依指示拿掉架構圖的①②③編號（README §4說明表改用區塊名稱）；README §2動畫改用`docs/media/demo.gif`（從repo外的「四大功能動畫版」HTML以Playwright擷取，剪成約7秒、960寬：建立專案→相依圖鎖住→AI助手附出處）。使用者再指示「內容應該都是做完了，不要寫甚麼還沒做完，然後授權寫MIT那個就好」：README拿掉「可試用」「還沒做完」與路線圖連結的字樣，授權改MIT並新增`LICENSE`（著作權人暫寫ProjectFlow Team，可再改）。之後依「動畫資訊量有點太大，再簡化一點，然後功能acd不要寫」重錄GIF：拿掉「功能a／c／d」、章節列、步驟條、標籤、任務列與主機面板，字幕改短，約6.5秒。再依「動畫的相依圖拿掉」只留建立專案與AI助手兩段，約5秒。
- INBOX-REMOVAL ✅（2026-11-06，已合併並push `b6f5a5c`）：使用者討論簡報P.37時要刪掉n8n「收件匣每分鐘」排程，理由：「正常的上傳檔案方式是在這個系統裡，再跑OCR。若將檔案放到資料夾再進行掃描，讓第一次聽報告的人不理解，正常使用的時候也不會透過資料夾上傳檔案，再者是沒辦法限制權限」；之後決定「Excel 改成系統內上傳」「P.37 維持四個」，並指示「開始寫 spec」（D90）。範圍：拿掉收件匣資料夾掃描的整條路（n8n `inbox.json`、`/integrations/inbox/scan`、`inbox_service`的資料夾掃描、`PF_INBOX_ROOT`與收件匣掛載、`verify.py`收件匣步驟）；Excel營運資料匯入改成營運資料頁的系統內上傳，以登入者身分由API檢查`can_manage`。保留：備份資料夾、其他四個n8n流程、既有outbox歷史資料。[短規格與計畫](superpowers/plans/2026-11-06-inbox-removal.md)。
  - **改為只改簡報（同日）**：使用者「請你不要改程式 幫我改簡報就好 簡報內沒有Excel 不要理會Excel」；P.39選「改成系統內上傳」，文字選「信心分數改看畫面」（查證系統內上傳不寄Email／LINE，只有收件匣會寄，不改程式就錄不出Email，所以流程改成「系統內上傳 → OCR → 信心分數 → AI」）。簡報在repo外`Downloads/專流 ProjectFlow_1106/`，修改前備份為同資料夾`專流 ProjectFlow_1106.備份-改簡報前.html`。改了：P.37標題、講稿、拿掉「收件匣」卡（四個流程）；P.39標題、四步驟、說明框、標籤、講稿與影片；P.34議程03／04；P.21「n8n 四個流程」；P.19部署圖與講稿；P.40斷網驗證只列實測項目中仍存在的五項；P.42主機資料夾只留每日備份、n8n說明改「寄通知、每日摘要、週報、每日備份」。檢查：全檔已無「收件匣」字樣，headless截圖P.34／37／39／42版面正常。
  - **重錄影片**：在15173（`deploy/start.py`啟動，只綁127.0.0.1）以展示帳號`yu`用Playwright錄1280×720：專案「文件」上傳檢驗報告 → 等索引（約30秒，剪掉，用字幕卡代替）→ AI助手「正式文件」索引狀態「已索引：OCR辨識，1頁，平均信心0.96」→ 提問粗蛋白，回答12.6%附來源與第1頁。剪接成35秒1920×1080 MP4（字幕1系統內上傳／2自動OCR／3信心分數／4 AI直接查到內容），嵌入P.39，另存ignored `output/錄影素材/實際示範-系統內上傳到AI-完成版.mp4`。上傳按鈕顯示英文「Choose File」（無頭瀏覽器的原生檔案欄，未處理）。
  - **調整頁序（同日）**：使用者問「P.39 改到n8n前面是不是比較好」，同意AI建議後說「好」。示範頁移到OCR三個問題之後：P.37實際示範 → P.38 n8n → P.39 AI週報（id與「Slide N of 51」重編；`deck-motion`每頁都是相同預設值，不需調整）。同步：P.34議程03／04對調、P.21標籤與講稿順序、示範頁講稿第一句（不再說「兩塊串起來」）、n8n頁講稿開頭「剛才看到 OCR 讓資料進得來」、P.40講稿「前面 n8n 那頁手機收到 LINE」（新示範影片沒有LINE）。調整前備份`專流 ProjectFlow_1106.備份-調頁序前.html`；headless截圖P.21／34／36–39正常。
  - **README對齊現況（同日）**：使用者「根據目前的進度 請你改read.me」，先討論列出8點後指示「全部照改」：§9通知管道改為站內＋Email（n8n）＋選用LINE；§9新增D83（n8n只排程）、D90（檔案一律系統內上傳）；§6補n8n、Mailpit兩個選用容器並更新備份說明；§8.2拿掉已完成的個人通知設定；§2文件列補OCR；§7補`.github/`、`deploy/n8n/`；§1補CI五項檢查；§8.5新增週報句中數字檢查（WEEKLY-AI-m1）、§8.6「AI 收件匣」改名「AI 待辦彙整」。
  - **CI與上傳（同日）**：使用者問改程式的進度要不要上傳，同意「好 並請修改成符合這個專題的CI」。本機main `--ff-only`到origin `8137c9c`（組員PR #12），main合併進本分支（`9ebf1fd`，README取我方n8n列＋組員AI列；PROGRESS兩段都保留）。CI（`.github/workflows/ci.yml`）新增：`workflow_dispatch`；`demo` job以無頭Chromium跑`tests/records.html`（`.github/scripts/run_demo_tests.mjs`，失敗、console error、逾時都算失敗；本機174/174，約5秒）；`deploy` job檢查兩份Compose（含n8n profile、公開覆寫，用假密碼）、部署腳本編譯、n8n流程檔與`setup.py`清單一致；API job逾時30→45分（乾淨Linux容器`python:3.13-slim`只用git檔案實測全量1249 pass／18 skip、exit 0、23分20秒）。`docs/formal-development.md`加「持續整合（CI）」說明。合併後相關測試（n8n、health、deployment、public_trial、AI學習）216 pass／1 skip、exit 0。一位唯讀審查者Ready；採納兩點小建議（console過濾只排除字型網域、找不到#sum時明確失敗）。GitHub Actions實際結果需push後在網頁查看（本機沒有gh、私人repo未登入）。
  - **P.39重做（同日）**：使用者問「P.39 有更好讓人明瞭的表達方式嗎」，同意AI建議後說「好」。改成：上方一條流程（① 程式算數字 → AI 寫句子 → ② 檢查代號 → ③ 負責人確認 → ④ 只寄管理角色，關卡依流程順序重新編號）；中間放大兩列實際例子「[T4] 罐標設計 進度 60% → 罐標設計進度達到 60%…（✓ 照抄系統數字）」「[T5] 試吃測試 進度 30% → …仍有 70% 延遲…（✗ AI 自己換算）」與「這種錯在 ③ 負責人確認時改掉才會寄出」；右側縮小實際草稿截圖當佐證。講稿依新編號改寫（221字）。改前備份`C:/Users/User/Desktop/專流 ProjectFlow_1106_1.備份-P39重做前.html`。
  - **廖泓茹照片（同日）**：使用者「請把P.4 廖泓茹的大頭照縮小一點 跟其他人一樣大 其他有照片的頁面中的照片也改得跟其他人一樣大小」。各頁外框尺寸本來就一致，差在原照片取景太緊且已裁圓、綠框畫在照片裡。依使用者選擇「你提供原始照片」，使用者貼上原始證件照（1062×1480），照其他三人比例（臉寬、眼睛約在45%高度）裁成正方形，換掉簡報中她的全部10處照片（P.4 320px、P.34 440px、P.21／P.35–P.40頭像／P.51 160px）。改前備份`C:/Users/User/Desktop/專流 ProjectFlow_1106_1.備份-換照片前.html`；截圖P.4／21／34／51確認一致。
  - **合併到使用者新版簡報（同日）**：使用者提供`C:/Users/User/Desktop/專流 ProjectFlow_1106_1.html`，指示「依據這份報告為主，把剛剛改的東西放進這個報告裡」。比對後使用者改過P.4、P.21（只換圖片）、P.28–P.33、P.51；我改過P.19、P.21、P.34、P.37–P.40、P.42。做法：P.19、P.34、P.37–P.40、P.42整頁換成修改後版本，P.21只套兩處文字（標籤順序、講稿），保留使用者的圖片；使用者改的頁不動。合併前備份`C:/Users/User/Desktop/專流 ProjectFlow_1106_1.備份-合併前.html`。檢查：逐頁雜湊比對只有上述頁變動、全檔無「收件匣」、headless截圖P.21／34／37–40正常。P.40表格「n8n 自動化 7 項 7/7 通過」（11/4斷網實測含已移除的收件匣與Excel兩項）依使用者「改成 5 項」改為「5 項 5/5 通過」（這五項當時都測過且通過）；改前備份`專流 ProjectFlow_1106_1.備份-改5項前.html`。
  - **P.39版面調整（同日）**：使用者「請把P.39的 中間綠框 放到最左邊 橘框放到右邊 四道關卡放到兩個框下面 讓兩者畫面可以放大一點」。綠框（程式數字）在左、橘框（AI句子）在右，右側加圖例；四道關卡改成兩框下方的一列四格（標題＋一行說明）；為了空間拿掉副標「週五 17:00 自動產生草稿…」（併入講稿第一句）。截圖文字約放大兩成。講稿方位同步改為「左邊綠框…右邊橘框」。改前備份`專流 ProjectFlow_1106.備份-週報版面調整前.html`。
  - **精簡講稿（同日）**：使用者「請改進 可能報告5分鐘 請精簡」。P.34–P.40講稿從約2,900字縮到1,114字（約5分鐘），保留關鍵數字；修正P.39講稿方位（中間綠框是程式數字、左邊橘框是AI句子）。改前備份`專流 ProjectFlow_1106.備份-精簡講稿前.html`。
  - **P.39 AI週報畫面（同日）**：使用者「P.39 AI 週報的部分，請你幫我呈現 一個AI週報的畫面 並標示出來哪些數字是程式算的，哪些是AI寫的句子」。15173與隔離`projectflow-n8n`資料太少（且本週已寄出），改在暫存資料夾開全新SQLite環境（`app.seed`後直接寫入7個任務、3筆回報、1個相依，只在暫存庫），以`gemma3:4b`（本機Ollama）產生草稿並截圖；截圖後已停掉暫存伺服器與為此啟動的`projectflow-n8n`三個容器。P.39左側「讓 AI 直接寫週報的風險」卡換成並排截圖：橘框「AI 寫的句子」、綠框「程式計算的數字與清單」，標出「60% 引用系統的進度」與「AI 自己換算（實際進度 30%）→ 負責人確認時修正（關卡 4）」；右側四道關卡縮小保留，第2道依程式實際行為改為「代號必須在清單內：寫出 [T9] 這類清單外的代號，那一段就改用系統條列」；講稿同步。改前備份`專流 ProjectFlow_1106.備份-週報畫面前.html`。發現的問題記於§5 WEEKLY-AI-m1。
  - **移除收件匣程式（同日）**：使用者「n8n 的收件匣排程實際上還在每分鐘跑的程式 請改掉」。刪除`deploy/n8n/workflows/inbox.json`、`api/app/services/inbox_service.py`（含資料夾Excel匯入）與`POST /integrations/inbox/scan`；compose拿掉`PF_INBOX_ROOT`與收件匣掛載，`.env.example`拿掉`PF_INBOX_HOST`；`setup.py`只匯入四個流程，並對舊安裝`n8n unpublish:workflow --id=pfInbox00000001`（不存在不中斷）；`verify.py`拿掉收件匣與Excel兩步，到期測試的供應商改用`POST /operations`建立；兩份README更新。不新增系統內Excel上傳（使用者「不要理會Excel」）。測試：新增2個（掃描路由404且模組不存在；n8n只剩四個流程、setup會停用舊流程、compose無收件匣）RED 2 fail exit 1→GREEN；`test_n8n_complete`＋`test_health`＋`test_deployment`＋`test_public_trial` 120 pass exit 0；OCR／營運資料／outbox／LINE相關72 pass 1 skip exit 0；`test_integrations` 7 pass exit 0；未跑API全量（約93分鐘）。實機：15173 n8n執行unpublish並重啟，`list:workflow --active=true`只剩四個流程；API映像未重建、主機`deploy/inbox/`未刪。一位唯讀審查者結論Ready、無阻擋；採納小建議（README註明舊流程可手動刪除）。
  - **15173資料變動**：為了錄影上傳了3份同一份檢驗報告（11/6 15:59、16:02、16:05），只保留16:02那份「AI可查詢」，其餘連同11/4收件匣那份都改成「AI已停用」（可在文件頁按「恢復 AI 引用」）；沒有刪除任何資料。
- TEXT2SQL-EXPANDED-TESTS 🟢 最終紀錄（2026-11-05）：使用者決定保留4題，標示96題新增＋4題既有。64正常＋8回訓＋1完整性＝73 pass（121.90秒）；先前100陷阱＋100權限＋1完整性通過，現在共274案例（分批實跑、非一次274）。既有回歸89 pass／1 skip。獨立唯讀審查完成無阻擋；產品與原有測試零改動。完整報告 `docs/reports/2026-11-05-text2sql-expanded-tests.md`。已開 [PR #12](https://github.com/chenliyu0410/projectflow/pull/12)，待審閱，不自行合併。

- TEXT2SQL-EXPANDED-TESTS 追加核可（2026-11-05）：使用者核可正常查詢64案例＋回訓流程8案例，只改測試和測試資料。先固定預期後執行；產品 app/ 與原有測試檔不改，若失敗先討論。4題重複決定仍待確認。

- TEXT2SQL-EXPANDED-TESTS 待確認（2026-11-05）：題庫 commit `698f29a`，217 pass；相關回歸89 pass／1 skip。自查T010/T026/T027/T081與既有7題重複，實際96題新增＋4題回歸，已詢問是否替換再跑。獨立審查因額度未執行。完整紀錄：`docs/reports/2026-11-05-text2sql-expanded-tests.md`。暫不開PR、不改產品。

- TEXT2SQL-EXPANDED-TESTS 🔨（2026-11-05）：使用者授權以含回訓的 a42e5fa 為基底，新增 100 陷阱題＋100 API 越權案例，另開 PR；codex/text2sql-expanded-tests。短規格與計畫：`docs/superpowers/plans/2026-11-05-text2sql-expanded-tests.md`。既有基準35 pass／1 skip，題庫先固定再跑；若失敗先詢問，不改產品。原有未追蹤 artifacts/ 與架構 PNG 保留、不提交。


- N8N-OFFLINE 🟢（2026-11-04）：使用者要求做n8n斷網測試，確認n8n是否會把資料送出去。做法：隔離stack `projectflow-n8n` 先`down`（保留資料卷），加compose override讓`default`網路`internal: true`（無對外閘道、無外部DNS）後重建；n8n／Mailpit改用15678／18025避免與15173正式環境的5678／8025衝突。internal網路無法從本機連入，所以`verify.py`改在同一斷網網路內的容器（API映像）執行，只把127.0.0.1埠換成服務名稱、收件匣／備份資料夾掛同一個host資料夾。斷網證據：api、n8n、驗證容器連`api.line.me`／8.8.8.8／1.1.1.1全部失敗（DNS查不到或無路由）。結果：`verify.py`七項全PASS、exit 0（指派通知、每日摘要、週報（本週已寄過依規則略過）、收件匣文件、Excel匯入、到期＋建任務、備份）；週報另以electronics的elaine在「連接器新產品正式版」斷網產生並確認寄出，Mailpit收到（PASS；該公司未設本地模型，標「AI 未啟用」走原始整理，斷網下本地模型撰寫週報未測，因為Ollama在主機上，internal網路連不到）。帶LINE標記的事件Email都標sent（LINE連不到不影響Email）。發現：n8n 2.45.7 即使關閉使用統計／版本檢查／範本庫，開機後仍由內建「MCP Registry」模組連`api.n8n.io/api/mcp-servers`（只抓伺服器清單，斷網時5次EAI_AGAIN、不影響流程）；override加`N8N_DISABLED_MODULES: mcp-registry`後重跑：n8n自身連外嘗試0次，`verify.py`仍全PASS（每日摘要當天已寄過依去重略過）。依使用者「Yes, add it」於分支`feature/n8n-no-egress`把`N8N_DISABLED_MODULES: mcp-registry`加進`deploy/docker-compose.yml`的n8n環境變數，`deploy/n8n/README.md`「離線與安全」補這項與斷網實測結果；`test_deployment.py`新增1項（RED 1 failed exit 1→GREEN），`test_deployment.py`＋`test_public_trial.py` 85 pass、exit 0；用實際env跑`docker compose config`確認設定生效；`--ff-only`合併回main。依使用者「好」：重建前確認outbox無待寄（sent 10），只以`up -d --no-deps n8n`重建15173的n8n（project `projectflow-formal`、`deploy/.env`），容器內`N8N_DISABLED_MODULES=mcp-registry`，開機後log無api.n8n.io，n8n healthz 200、15173 200，之後n8n每分鐘照常呼叫`/integrations/events`與`/integrations/inbox/scan`（200）。之後stack已還原為一般網路，db／api／web照原本啟動（n8n／Mailpit照原本不跑），15173正式環境未動。腳本與log在repo外`output/n8n-demo/offline-test-20261104/`。另記15173狀態：同日在「成貓主食罐正式版」的收件匣放入虛構掃描檢驗報告兩次（14:52、14:59），同名檔重放會新增第二份文件而非新版本，產品沒有刪除文件功能，14:52那份（456cc028…）已以yu呼叫`PUT /ai/knowledge/456cc028…` enabled=false停用AI引用（有稽核、可恢復），文件列表仍有兩筆；兩次都寄出Email並推LINE廣播。對照原掃描圖發現OCR會吃掉小數點，記為§5 OCR-DECIMAL。
- LINE-BROADCAST 🟢（2026-11-04）：使用者問「n8n 發訊息通知 可以連接到line嗎」，看過三種方式後選「A」（廣播給官方帳號所有好友，不需webhook），並已自行在`deploy/.env`填入`PF_LINE_CHANNEL_TOKEN`（不進git）（D89）。短規格：migration `20261104_0025` 為`outbox_events`加可空`line_text`；`outbox_service.enqueue(..., line=None)`由產生事件的地方決定要不要推LINE，同一件事只標一筆（週報寄出、到期提醒、備份失敗只標第一位收件人，指派通知每筆都標）；標記種類＝站內通知轉寄、週報已寄出、收件匣新文件與匯入完成、到期提醒、備份失敗；每日摘要、週報草稿、備份成功不推。LINE內容只放標題與任務名稱，不放連結（專流只綁127.0.0.1，手機打不開）、內文或機密欄位。n8n「通知轉寄」在回報寄出後，若有`line_text`且有token就`POST https://api.line.me/v2/bot/message/broadcast`（`X-Line-Retry-Key`用事件id避免重複），LINE失敗不影響Email結果。限制：需外網；廣播會讓所有好友收到同樣訊息；收件人沒有Email而被略過的事件不會推LINE。允許檔案：該migration、`models.py`、`outbox_service.py`、`notification_service.py`、`weekly_report_service.py`、`maintenance_service.py`、`inbox_service.py`、`api/tests/test_line_broadcast.py`、`deploy/n8n/workflows/notify.json`、`deploy/docker-compose.yml`、`deploy/.env.example`、`deploy/n8n/README.md`、`docs/PROGRESS.md`、`README.md`。另記：2026-11-04 這台（git使用者kayla162）的本機15173已先備份（repo外`output/backups/projectflow-formal-20261104-091921.sql`）再升到DB 0024並開啟正式文件索引，資料筆數一致；該紀錄原在本機commit `e01473f`，因與origin分岔，比照使用者先前「捨棄本機紀錄」保留在`backup/main-local-1104`後把main對齊origin `973ed95`。結果：新增`test_line_broadcast.py` 7項；後端全量962 pass／16 skip；隔離stack以假token實跑n8n：指派、收件匣、匯入、到期（2位收件人只1則）各呼叫LINE一次並得401，每日摘要與備份成功不呼叫，`verify.py`七項全PASS（Email不受影響）。一次獨立唯讀審查：初審Not ready（跳過／覆寫申請通知每位審核者會重複廣播），改為同一event_key只第一封帶LINE並補測試；同時管理者依建立時間排序、README提醒標題勿含機密。未修（記錄）：第一位收件人無Email時整件不推LINE、廣播不依權限過濾、重送超過24小時Retry-Key失效可能重播。已`--ff-only`合併本機main（未push）。部署本機15173：先備份到repo外`output/backups/projectflow-formal-20261104-112520.sql`（37表），`start.py`升到0025，資料筆數不變（users 7／projects 2／nodes 3／documents 1／outbox 9／weekly 1／audit 12／operations 1），`setup.py`重新匯入並publish五個流程（通知轉寄含LINE廣播），n8n容器已取得token；部署時沒有待寄信件。2026-11-04依使用者「發測試訊息」：以yu把「殺菌條件驗證」負責人由陳主管改為明成員，11:28（台北）n8n寄出Email到ming@demo.local（Mailpit收到），同一輪「LINE 廣播」節點呼叫broadcast成功（LINE回應`{}`，無錯誤），內容為「[專流] 你被指派為任務負責人／任務：殺菌條件驗證」；使用者確認手機「有收到」。
- PITCH-TEXT2SQL-VIDEO 🟢 本機交付（2026-11-04）：人類指示簡報草稿artifacts/pitch-2026-11-03/Text2SQL_8面向.html（未進版控；先前紀錄在codex/rag-quality-handoff的PROGRESS）第1頁一句話改「主管白話提問，AI 負責理解、SQL 算準」；回饋頁「02 問題解決｜答不了的問題，變成下次答得對」左側對話示意換成人類提供的Downloads/p29_AI助手_學習前後.mp4（18秒、1280×720、無聲），以base64嵌入HTML（約1.6MB）維持單檔；方框改16:9，進入畫面從頭播一次、停在「學習後」，離開暫停歸零，頁尾加「↻ 重播」，減少動態時改顯示播放控制；刪除不再使用的fw-chat等CSS。查核：影片中的「存成候選、管理者審核後補進白名單」在main與所有遠端分支的web/src、api/app都找不到實作，頁尾「＊左側為畫面示意」保留。127.0.0.1:8000以1312×820確認7頁無溢出、第1頁一句話單行、右側四步驟各一行、影片播完停18秒、重播與離開／回來行為正確、console無錯誤。改前備份於session scratchpad。人類再指示（2026-11-04）：第3頁設計決策右邊「②我們的做法」整塊先不出現，按「所以」才出現並跑動畫；已把「所以」改成按鈕觸發（點擊後放掉焦點，避免之後空白鍵又按到），右邊面板在armed時隱藏但保留位置、觸發後淡入0.4秒再播原示範；移除「▶ 播放示範」按鈕與其CSS；→／空白鍵／Enter／↓／PageDown仍可觸發，重播回到右邊隱藏狀態；減少動態時直接全部顯示。講稿第3頁提示改「點『所以』或按 →」。127.0.0.1:8000以1312×820實測：進入時右邊hidden、滑鼠點「所以」後15步播完並選定02、重播回到hidden、PageDown觸發且這一下不捲動；7頁無溢出、console無錯誤。人類另已自行刪除系統優化頁，簡報與講稿現為6頁。人類再指示（2026-11-04）：把另一張「AI答不出來時，會告訴你怎麼查」（以前「無法判斷」→現在說明條件＋建議、16題一般問題0→14）併入回饋頁：選推薦版型，影片不動，右欄改成以前／現在、「給得出下一步 0→14／16題」、「確認過的問法，學起來：使用者確認→審核＋測試→補進白名單」、原則；標題由人類從選項選定「問題解決｜從「無法判斷」到「下次直接答對」」，副標改寫；頁尾加「0→14：16題一般問題，只開規則實測」（數字出自TEXT2SQL-FALLBACK量測）；第1頁議程03改「反問與回訓：從無法判斷到答對」並加標籤「給得出下一步 0→14」；講稿第5頁改寫約50秒。人類再指示：右上角圓圈面向標籤（t-aspect）全部拿掉，已刪5處與其CSS。Playwright（系統Chrome、減少動態）截6頁確認：標題單行、右欄三段與原則各在框內、無溢出；改前備份於session scratchpad。未改產品、未commit。
- TEXT2SQL-LEARNING 🟢 PR待使用者確認（2026-11-05）：使用者對照簡報與程式碼的清單後回覆「照建議開工」並要求做完開一個PR，視為核可整份設計（AI預設照計畫），另補簡報第6頁兩個小項（Task 0）與畫面文字照錄影（決定12）；已開`feature/text2sql-learning`。結果：Task 0（4/4具名測試、verify.py印96/96）、migration `20261105_0026`（`ai_learned_phrases`、`ai_answers.suggested_ids`）、確認／審核API與C1–C5、前端確認鈕／審核區／「直接查詢」標記。一次獨立審查無阻擋；應修1（離題問句靠快捷題被學起來）已修`ffbadb4`；應修2（展示包匯出會帶出問句原文）依D90修`371ce19`。AI代決：C2另擋新增／修改／刪除等寫入動詞（學會的問法跳過early_reply，normalize會拿掉「請幫我」等前綴）；learnable以建議的omits固定文字判斷（fallback.py不在允許清單；文字一改全部變不能學，方向安全）；前端另寫`learningJson`顯示伺服器detail（api.ts不在允許清單）。後續（不擋）：PG版migration測試沒有流程會實跑；學會的問法排在early_reply前，審核後才新增的公司簡稱不會再被拒（仍只查本公司）；兩位管理者同時審核「同句不同分析」可能都上線；審核區要先開⚙才看得到。以下為規格階段紀錄（2026-11-04）：人類要求「把系統真的用成這樣」——回饋頁影片的回訓循環（答不了→建議→使用者點選並確認結果正確→存成候選→管理者審核＋自動測試→補進白名單→下次同一句直接答對），先討論設計、人類確認後才寫程式。開工前已依人類要求`git fetch`並`--ff-only`把本機main對齊origin `983ad55`（PROGRESS本機紀錄以stash暫存後放回，衝突手動保留雙方條目；stash@{0}保留未drop）。現況查核：點建議時前端只送建議label與query_id，伺服器不知道原問句；`ai_answers`與稽核刻意不存問題原文；ALIASES寫死在service.py；無審核介面；錄影無對應原型程式。人類決定（2026-11-04）：可以，只在使用者按確認後存那一句。短規格與計畫：`docs/superpowers/plans/2026-11-04-text2sql-learning.md`（未commit）；已請一位未參與討論的審查者做builder check，5題中3題補成AI預設寫入文件（決定9：可學判斷＝所選分析無套用不到的條件，確認鈕／API／C1同一判斷；決定10：確認時規則重算建議，不存問句或指紋；決定11：確認人數算不同使用者），1題AI代決（決定8：管理者可審核自己確認的問法），1題為核可狀態。待人類：核可整份設計後才開`feature/text2sql-learning`寫程式。
- TEXT2SQL-FALLBACK 🟢（2026-11-04，待使用者確認）：使用者討論Text2SQL拒答太多不好用後指示「針對這三個目標幫我做出來」，逐條確認規則（聊天模式只回答系統怎麼用，全部預寫；題庫先給使用者看；開新分支；其他照AI建議），題目確認「題目可以，開始做」。做了：`api/app/ai/fallback.py`與`service.ask`的sql分支（拒答指令／繞過限制／其他公司／無此資料→預寫說明→條件偵測與最多3個建議，按下才以`query_id`執行；模型只能補一個清單id，不影響要列出的條件）；稽核加`fallback`原因與條件類別（不記原文）；`CopilotPanel`建議按鈕各自標出不含的條件。題庫與量測腳本在`deploy/ai-demo-data/fallback-eval/`。既有4個測試依新行為改寫（原斷言一律unsupported或舊`query_suggestion`；保留不自動執行、模型只能選id、資料不被改的斷言）。一次獨立唯讀審查：無阻擋；應修4項與建議4項已修（第9項「sql帶history」已被`Ask`驗證回422，不改）。實機：repo外scratch SQLite＋`deploy/portable/serve.py`於127.0.0.1:15190以yu走過條件建議→按下執行→使用說明。已知限制：驗證題錯H-A6（工作量／同事）、H-B5（已取消訂單建議成q05），照規矩未針對修；題目與規則由同一AI撰寫，不是獨立評測；rag路徑`service.foreign_company`仍只去一層公司後綴（與審查第4項同類，不在本次範圍）。
- PHASE-CURRENT 🟢（2026-11-03）：使用者看簡報用的「1-建立專案」影片，指出「建立好之後看起來連第一個流程都不能操作，應該有問題，你幫我看看再重錄」，並指示「只有修復這個的話可以單純當一個分支commit」。原因：PHASE-CARDS（10/13）只開放「進行中」階段，新專案所有任務都是待處理，5張階段卡全部停用（health.spec「進入階段：小量試作」停用也是同一規則）。修正（AI代決，可推翻）：第一個未完成的階段即使還沒開始也可進入，標「可開始」＋箭頭、主色；前面任何階段的閘門仍待核准時，改顯示「前一階段閘門待核准」並停用；其他未開始階段照舊停用。只改`NodeWorkspace.tsx`階段卡片判斷與`workspace.test.tsx`（新增1項，RED→GREEN），不動後端權限。分支`feature/phase-current`（自main `a920653`，與`feature/mcp-readonly`無關）；2026-11-03依使用者「推上去」推上`origin/feature/phase-current`（只推分支）；同日依使用者「開PR」開[PR #9](https://github.com/chenliyu0410/projectflow/pull/9)，GitHub回報與main衝突（origin/main已多出N8N、RAG-PORT等commit），把origin/main以merge commit併進本分支（不rebase、不force），只有PROGRESS §2開頭衝突，兩邊都保留；合併後Vitest全量41檔375 pass、build exit0。測試：本分支Vitest全量39檔359 pass、build exit0。重錄：repo外`output/demo-videos/`（SQLite＋`deploy/demo-data`資料包、`deploy/portable/serve.py`跑127.0.0.1:15180、Playwright錄影腳本），產出`output/demo-videos/out/1-建立專案.mp4`（1280×720、14秒），未動任何既有環境資料。
- AUTOSTART-N8N ✅（2026-11-03）：完成：`start.py`新增`n8n_configured()`（像Compose一樣忽略BOM、最後一筆賦值為準），正式stack有token時每個compose指令加`--profile n8n`；`docs/formal-development.md`兩處說明。驗證：新增測試RED（2 fail／6 pass，exit 1；審查後補的解析測試3 fail，exit 1）→GREEN（`test_deployment.py`＋`test_public_trial.py` 84 pass，exit 0）。實機：今早重開機後整個`projectflow-formal`都是停止狀態（見§5 AUTOSTART-N8N-m2），先啟動db並`pg_dump`到ignored `.superpowers/autostart-n8n/`，只跑`python deploy/start.py`：9秒exit 0，五個容器都起來，15173 `/api/health/ready` 200、Mailpit 200、n8n `/healthz` 200，五個流程仍為啟用，37張表筆數前後雜湊相同；另以`start(public=True)`驗公開組合可啟動（只開loopback 15174，沒動Funnel），隨即用`start.py`改回只綁127.0.0.1。一次獨立唯讀審查：Ready to merge；非阻擋已修：重複key取第一筆、BOM遮住key、文件誤寫setup.py會寫token；其餘記§5 AUTOSTART-N8N-m1。原始規劃如下。
  - 規劃（2026-11-03）：重畫部署架構圖時發現開機捷徑`開機自動啟動-公開試用.bat`→`deploy/public_trial.py`→`deploy/start.py`跑`compose up`沒帶`--profile n8n`，Compose也沒設重啟策略，所以重開機後n8n與Mailpit不會起來（通知信、收件匣、每日備份停擺）。使用者選「Yes, add n8n」。範圍（AI代決）：`start.py`的正式stack在`deploy/.env`有非空`PF_N8N_TOKEN`（代表已跑過`deploy/n8n/setup.py`）時加`--profile n8n`；沒有token的新機器與驗收stack不變，不會自動下載n8n映像。允許檔案：`deploy/start.py`、`api/tests/test_deployment.py`、`docs/formal-development.md`、本看板。不改Compose重啟策略、不動Funnel發布。驗收：相關pytest；本機`projectflow-formal`全部stop後只跑`python deploy/start.py`（不跑`public_trial.py`，不發布Funnel），n8n、Mailpit回來且流程仍啟用。
- OPS-OCR-N8N ✅（2026-11-02）：使用者問「有辦法把所有功能都加上去嗎」，RAG-PORT部署後指示「開 OCR 和 n8n」，看過下載清單後同意「同意，開始」。先`pg_dump`備份到ignored `.superpowers/ocr-n8n-deploy/`並記錄每張表雜湊；從ModelScope `RapidAI/RapidOCR`下載`chinese_cht_PP-OCRv3_rec_mobile.onnx`（11.2MB）與`chinese_cht_dict.txt`（33KB）到ignored `deploy/ocr-models/`，SHA-256與`deploy/ocr-models.sha256`相符；`deploy/.env`加`PF_AI_OCR=true`與隨機`PF_N8N_TOKEN`（43字元，不進git）；執行`deploy/n8n/setup.py --project projectflow-formal --env-file deploy/.env` exit 0（OCR版API映像、n8n 2.45.7、Mailpit v1.32.0，5個流程匯入並啟用，80個帳號填`<帳號>@demo.local`）。資料比對：只有users的email改變（排除email後與備份還原版雜湊相同）。實測：上傳虛構「報到公告（虛構掃描）.png」到「成貓主食罐正式版」，索引「OCR辨識，1頁，平均信心0.97」，問「新人報到在哪裡？要帶什麼？」由本地模型答出五樓大會議室與筆電充電器並引用該圖；用`outbox_service.enqueue`替yu排一封部署測試信，約50秒後由n8n送到Mailpit（127.0.0.1:8025），佇列標sent。所有服務只綁127.0.0.1。沒有跑`deploy/n8n/verify.py`（它會改派任務、寄週報、匯入供應商，只適合隔離示範環境）。
- RAG-PORT ✅（2026-11-02）：使用者問「LEE的那個版本rag是不是比MINA的更完整」，比對後指示「以 LEE 的版本為主體，從 Mina 那版挑上面幾項移植過來」，看過整理後確認「對沒錯，就這樣開始」（D88）。範圍：連續追問、上傳後自動建索引、停用／恢復文件知識、回答「有幫助／沒有幫助」回饋、引用原文檢視（段落、版本、下載、重查權限）。保留簡化版AI助手、OCR、Text-to-SQL、遮罩與n8n收件匣；Mina分支與PR #5只當參考，不合併。[短規格與計畫](superpowers/plans/2026-11-02-rag-port.md)經一位沒看過對話的審查者讀過，4個問題依既有討論補進文件；使用者核准「核准，開始做」。完成（細節見計畫與[AI助手說明](ai-assistant.md)）：正式文件索引只看`PF_AI_FORMAL_INDEX`，可用於Docker／PostgreSQL（AI治理頁仍限隔離驗收環境）；`followup.py`把追問改寫成完整問題（本地模型15秒，沒有模型時合併上一題）；migration `20261102_0024`（`documents.ai_enabled`、`ai_answers`）；`/ai/knowledge`讀寫AI引用開關（編輯權限、稽核`ai.knowledge`）、`/ai/answers/{id}/feedback`與`/ai/feedback/summary`（只存編號，稽核`ai.feedback`）；正式來源加`document_ref`、專案／節點、頁碼，引用視窗可下載原檔；文件管理顯示「AI：可查詢／排隊中／無法索引／已停用」；「正式文件」分類開放給六家公司。另改`api/app/demo_pack.py`一行把`ai_answers`排除在去敏展示包外（計畫AI代決14）。一次獨立審查：無阻擋、Ready to merge；非阻擋1（「那個專案…」被當追問）、2（沒開自動更新時永遠排隊中並輪詢）已修，3（停用後標籤被舊輪詢蓋回）核對後已由輪詢effect的cleanup中止，不需改；其餘記§5 RAG-PORT-m1～m7。`--ff-only`合併main，並依D50 push origin main。
  - **部署15173（同日）**：使用者「部署 15173」。先`pg_dump`並把files、ai_data兩個volume打包，備份在ignored `.superpowers/rag-port-deploy/`，同時記錄每張表的筆數與內容雜湊。`deploy/.env`加`PF_AI_FORMAL_INDEX=true`、`PF_AI_INDEX_AUTO_UPDATE=true`後執行`deploy/start.py`（只綁127.0.0.1；Tailscale Funnel原本就沒有公開ProjectFlow，這次也沒開），exit 0，DB從0021升到0024。部署前後除0022新增的兩張空表外全部相同；users以原欄位（排除0022新增的email欄位）比對也相同。毛研食品模型設定（`qwen2.5:3b`，`host.docker.internal:11434`）保留，容器連得到Ollama。實測：在「成貓主食罐正式版」上傳虛構的「G2關卡檢查表（虛構）.txt」（保留供展示），數秒內變成「AI：可查詢」；提問、追問（已理解為）、引用原文與下載、回饋、停用後不再引用而舊來源仍可開、恢復都通過；1280／375無水平溢位。走查新增的資料：1份文件與版本、9筆稽核、3筆`ai_answers`（1筆有評分）、附件容量計數、yu的`last_login_at`。
- N8N-COMPLETE 🟢（2026-11-02）：依D87（使用者「請把n8n實作完成 問題一律採用建議作法 不需要問過我」）把n8n其餘功能做完，計畫見[n8n第一批計畫](superpowers/plans/2026-11-02-n8n-batch1.md)末「完成版範圍」。完成：第一批補齊（`/accounts/me/email`與帳號頁「Email 通知」；管理者「寄送失敗的通知」與重寄；migration `20261102_0023` outbox租約5分鐘；確認寄出重查明確機密回409；分級設定檔損毀回503；週一摘要看上週五；本週已寄出時停用產生鈕；一般成員顯示說明）；第二批收件匣（`<收件匣>/<公司代碼>/<專案名稱>/`存成專案文件並解析／OCR後寄信給負責人，`已匯入`／`失敗`＋原因檔；`_營運資料匯入/<分類>.xlsx`依代碼新增或合併更新，沿用安全解析器）；第三批每日維運（完整備份zip保留7份含帳號雜湊、稽核與文件樣板檔，排除session，可用`app.demo_pack import`還原並保留密碼；營運資料「到期／有效期限」30天內寄信並在關聯節點下建立「更新到期」任務）；n8n新增「收件匣（每分鐘）」「每日維運（02:00）」流程，Compose掛載`PF_INBOX_HOST`／`PF_BACKUP_HOST`。驗證：`test_n8n_complete.py` 12項＋相關測試通過；Vitest 41檔367 pass；隔離stack `verify.py` 指派通知、週報、收件匣文件、Excel匯入、到期＋建任務、備份全PASS（每日摘要同日已寄過依去重略過）。一次獨立唯讀審查：初審Not ready（Excel更新整筆覆蓋會把restricted改回internal並刪欄位；完整備份漏文件樣板檔），已修並補測試；同時處理非阻擋：掃描改在執行緒池且同時只跑一輪、以ctime判斷複製完成、檔案鎖住只略過該檔、日期序號只轉日期欄且限合理範圍、`parse_date`接受YYYY/M/D、備份失敗清掉暫存檔、匯入中途失敗註明已匯入筆數。未修（記錄）：Excel值含「 | 」或換行會被切斷、第一張工作表以檔名排序、專案同名取最後一個、備份未用快照且整份在記憶體與未加密（README提醒權限）、週一摘要不含週末、`thisMonday`用瀏覽器時區、outbox未用SKIP LOCKED。後端全量888 pass／15 skip；乾淨容器CI模擬：專用PostgreSQL 11階段全過、限1 CPU的Web 367 pass＋build exit0。已`--ff-only`合併main並推上origin（`30b9e0b`）。本機`projectflow-formal`：先`pg_dump`備份到`output/backups/projectflow-formal-20261102-142553.sql`（36表），升級`20261102_0022`→`0023`，users 7／projects 2／nodes 3／outbox 5／weekly_reports 1／audit_logs 5 升級前後一致；五個n8n流程已publish，收件匣`deploy/inbox/<公司代碼>/`與備份`deploy/backups/`已建立，health ready、n8n／Mailpit 200。之後GitHub CI的Web job仍在`work-order.test`第40行失敗：真正原因是面板載入異動紀錄時外層fieldset停用，瀏覽器按不到選項，但jsdom仍觸發點擊，而`run()`在載入中會略過這次選擇，庫存不會載入、確認鈕永遠停用；inventory相關4處測試改為先等選項按鈕可按再點（`20db9b8`，產品程式未改）。限0.5 CPU乾淨容器：三個測試檔連跑5次皆12 pass，Web全量367 pass、build exit0。
- N8N 🟢（2026-11-02）：第一批（D83–D86）最小架構版完成，分支`feature/n8n-batch1`。[規格](superpowers/specs/2026-11-02-n8n-batch1-design.md)、[計畫](superpowers/plans/2026-11-02-n8n-batch1.md)（「最小架構範圍」一節）。完成：migration `20261102_0022`（users加email／email_notify，新增outbox_events、weekly_reports；只新增，有資料時拒絕降級）；站內通知在同一交易寫outbox事件（去重、失敗5次停、無Email或關閉通知標skipped）；`PF_N8N_TOKEN`保護的`/integrations/*`四支API（拉事件、回報結果、產生週報草稿、每日摘要）；週報服務（七區塊由程式計算、D84收件人、D85只排除明確標機密、每位收件人可見交集、本地模型撰寫且引用`[Tn]`不在清單就改原始整理、模型未啟用或失敗仍產生、確認時重驗收件人、稽核只記改了哪幾段）；每日摘要（不用AI，四類皆空不寄）；專案層「週報」分頁；Compose `--profile n8n`加入n8n 2.45.7與Mailpit v1.32.0（GHCR；Docker Hub登入問題）、三個流程JSON、`deploy/n8n/setup.py`／`verify.py`。驗證：新增pytest 16項通過；後端全量873 pass、15 skip、2 fail→`test_health`路由白名單補上新API後24 pass，`test_progress_vectors_match_shared_file`從api目錄執行找不到相對路徑檔案（repo根目錄執行pass，既有問題）；Vitest 40檔362 pass、build exit0（有>500kB chunk提醒，未查是否既有）；隔離stack `projectflow-n8n`（15183／18010／8025／5678，repo外`output/n8n-demo/.env`）`verify.py`真實n8n＋Mailpit三封信PASS；n8n停機時指派→無信，重啟後補寄成功；週報分頁1280顯示正常、375無水平捲動。一次獨立唯讀審查：Ready、無阻擋；已修3項非阻擋（排程不覆蓋已存在的草稿、草稿後刪除任務不再把收件人全移除、AI輸出截斷到可確認長度）並補2項測試。未修（記錄）：確認時不重查D85、policy檔損毀時明確機密覆寫失效、通知信含任務標題、週一摘要的「昨天」是週日、拉取未認領可能重寄、本週已寄出時「立即產生」按鈕仍可按（按下顯示409）、一般成員點週報分頁看到403文字、n8n可讀全部環境變數且首次開啟可由本機任何人註冊owner。2026-11-02 依使用者「請幫我做資料庫還沒升級」：先`pg_dump`備份到repo外`output/backups/projectflow-formal-20261102-121051.sql`（34表），停掉隔離stack的n8n與Mailpit讓出5678／8025，`deploy/.env`加`PF_N8N_TOKEN`（不進git），執行`deploy/n8n/setup.py --project projectflow-formal --env-file deploy/.env`：migration `20261024_0021`→`20261102_0022`，升級前後users 7、projects 2、nodes 3、task_reports／documents／audit_logs 0 筆數一致；7個帳號填入`@demo.local`；health ready、n8n／Mailpit 200、token呼叫`/integrations/events` 200，三個流程已publish。注意：此資料庫只有7帳號／2專案，不是OPS-LOCAL記錄的完整展示資料（80帳號／39專案），原因未查、未改。CI（`576c65d`）本機以乾淨Linux容器照ci.yml重現：API pytest 864 pass／16 skip、專用PostgreSQL 11階段全過、web Vitest＋build exit0；GitHub上`f09b096`那次顯示取消，是被下一次push依concurrency設定取消，非失敗。之後GitHub上`d809427`的Web job失敗：`returns.test.tsx`在慢的CI機器上等不到「已入帳…」訊息（findByText預設只等1秒；先前已記為偶發失敗），改為送出後的等待最多5秒、單一測試上限20秒（`3d49e64`），本機連跑3次與乾淨容器Web job（Vitest 40檔362 pass、build exit0）皆通過。其後`3874669`的CI改由`work-order.test`的`toBeEnabled`等待逾時失敗；改為整體處理（`ed0d597`）：`test-setup.ts`把findBy／waitFor等待上限由1秒改5秒、vite測試上限20秒；returns與purchase測試補「等按鈕可按再點」（原本改完數量立即點擊，按鈕尚未啟用時點擊無效，才是returns偶發失敗主因）；週報測試的假API改為記住儲存內容。本機全量連跑3次362 pass，限1 CPU的乾淨容器Web job連跑2次362 pass、build exit0。

- LOGIN-WATER ✅（2026-10-28）：使用者提供原型`login-water-e2.html`（方案E2深潭）指示「把登入介面改成這個」，成功轉場選「播完再進（約1.5秒）」。[短規格與計畫](superpowers/plans/2026-10-28-login-water.md)；分支`feature/login-water`，已`--ff-only`合併回main。完成：新增`LoginScreen.tsx`（移植原型WebGL水面shader、水花、霧面卡片；點水面／聚焦欄位／按登入起漣漪，錯誤晃動，成功卡片沉下並撥水），`App.tsx`在login API成功後等`departureMs()`（WebGL可用且未減少動態才為1600ms）再載入工作台，樣式以`.water-login`隔離。不顯示原型的提示列、預填帳密、歡迎畫面（AI代決）。測試：新增`login-screen.test.tsx` 3項；Vitest全量39檔358 pass、tsc、build exit0。15173實測：1280卡片置中、錯誤密碼顯示「帳號或密碼錯誤」並清空密碼、成功時submit→sink 63ms→進工作台1.6s，撥水畫面含水花；375卡片左右16px、無水平捲動。注意：這台電腦的Browser pane回報`prefers-reduced-motion: reduce`（Windows動畫效果關閉），此時水面靜止、直接進入，屬規格行為；動畫路徑是在該分頁覆寫matchMedia後實測。一次獨立唯讀審查：Ready；應修2項已修——全域`button:hover`把登入按鈕底色蓋成米白、白字看不見（補hover規則，實測hover仍為深綠白字）；StrictMode開發模式第二次effect會拿到已失效的WebGL context而丟錯（stop改為刪除program／shader／buffer、不loseContext，並檢查context lost與LINK_STATUS）；輕微：欄位聚焦光暈透明度.12→.3。未修：E2E每次登入多等1.6秒（headless有WebGL），未實跑E2E。
- COPILOT-SIMPLIFY ✅（2026-10-28）：使用者要求AI助手「只要能清楚看到自己問題跟AI回答」「有固定快捷鍵可以當問題」「留下必要的就好」，看過對照圖選方案B（分類標籤＋固定快捷題，拿掉5個選單、歷史勾選、示範步驟卡，進階收進⚙），並同意拿掉專案選單（「可以改」）。[短規格與計畫](superpowers/plans/2026-10-28-copilot-simplify.md)；分支`feature/copilot-simplify`，已`--ff-only`合併回main。完成：`CopilotPanel.tsx`改為標題列（AI 助手、⚙進階設定、關閉）＋分類按鈕（文件問答、資料分析〔`can_sql`〕、新人報到〔毛研食品〕、正式文件〔毛研食品且`formal_available`〕）＋對話＋固定快捷題＋輸入框；`copilotScenarios.ts`改為分類定義，快捷題自帶歷史版本／完整工單／專案（標題開頭比對）；模型狀態、預覽、正式文件索引、本地模型設定收進⚙。測試：`ai.test.tsx`改寫為21項（先RED 21 fail，實作後GREEN），`workspace.test`改為只驗快捷題與送出鍵在無資料時停用（分類與⚙刻意可按）；Vitest全量38檔355 pass（第一次`work-order.test`偶發1 fail，單獨與全量重跑皆pass，與本次無關）、`tsc`含e2e exit0、build exit0。15173實測（yu／毛研食品展示管理者）：1280文件問答「風險原因與處理方式」、新人報到「新人課程原本哪天？為什麼改期？」（本地模型答10/27講師行程，引用含MTG-002歷史版本）、資料分析「請問有哪些專案超支？」（food-PRJ2超支220000）、⚙展開正常；375對話區571／面板788px、無水平捲動。E2E 7支規格改用分類／快捷題／⚙（`e2e/copilot.ts`改為`chooseCategory`、`openAdvanced`），刪除只能靠已移除控制項表達的步驟；需隔離驗收環境，本次未實跑。一次獨立唯讀審查：Ready；應修2項——formal-index在全部專案範圍下兩種寬度同名檔案會讓嚴格定位對到兩個元素（已改為每次唯一檔名）；starter／local-model拿掉專案範圍後「資料等級：內部」可能變（未實跑，見§5）。
- OPS-LOCAL ✅：使用者2026-10-28指示「pull下來，然後幫我開本地端」。`git pull`（ff到`4a45d10`，70檔），啟動Docker Desktop後`deploy/start.py`起15173。使用者回報登不進去：DB為空（未seed），先`--seed-demo`，使用者再指示「要匯入」完整資料包：`alembic downgrade base`（清掉僅含seed的資料）→upgrade到0019匯入失敗（見§5 OPS-LOCAL-m1），改為upgrade head→暫標`alembic_version`為0019→`demo_data.py import`（27表，80帳號／39專案／500節點）→改回0021→`start.py`。yu／demo-yu登入可見8個專案。使用者再指示「把我離線的rag分支也接到正式端」，經詢問確認指已在main的rag-starter-import：照`deploy/ai-demo-data/README.md`把`pack`（dataset-v1，6公司78份文件）與`deploy/rag-starter`（starter-v1，24份）用`app.ai.import_cli`匯入`ai_data` volume；以yu（admin、本機）在副手「本地模型連線設定」設`http://host.docker.internal:11434`、`gemma4:latest`並啟用。實測「現行交付需要幾張截圖？」→本地模型回答4張、附food-SPEC-2與food-MEET-1引用，處理紀錄為本地模型、雲端關閉、檢索方式關鍵字（無向量模型，`PF_AI_VECTOR_MODEL`未設）。使用者再指示「要，全部接上」：本機`deploy/.env`加`PF_SHOWCASE_MODE=true`（.env不進git）並`start.py`重啟，使用者選單出現「切換公司（本機展示）」；依序切到electronics、events、software、construction、hemu，以各家展示管理者在副手設定同一模型並啟用。`settings/*.json`六家皆`enabled: true`；禾沐問「風險原因與處理方式」→本地模型回答、附hemu-RISK-2／RISK-1／GUIDE-1引用。未改產品程式。
- REVIEW-FIX 🔍：使用者2026-10-20先要求檢視專案「有要再修正或補齊的地方嗎」，Claude做唯讀審查（兩位子代理分別審後端與前端，主代理回原始碼核對前幾項）並條列約40項；使用者指示「全部開始修，可以同時進行的就直接開分支」，故依檔案範圍拆成四個平行session、各自worktree分支（D2例外，使用者指示平行），各分支不改PROGRESS／README以免衝突，短計畫與結果寫在`docs/superpowers/plans/2026-10-20-{api-security,api-correctness,ci-tests,web-fixes}.md`。**api-security**（`4fffaba`）：cookie依HTTPS加Secure、AI模型設定改用不可偽造的本機判斷、寫入請求統一Origin／Sec-Fetch-Site檢查、非開發環境關閉OpenAPI文件、nginx安全標頭、`verify_password`用雜湊記錄的rounds、帳號不存在時跑假雜湊消除時間差、AI SQL逾時改回可理解訊息。**api-correctness**（`fa3af45`）：engine依URL快取、階段狀態採使用者2026-10-20選定的規則A（階段可直接改review／skipped但子節點須全部done／skipped，否則409；專案根節點不能用PATCH改skipped／review）、同一請求共用授權資料（送出略過申請342–482ms→89–117ms）、GET改不加鎖讀取、稽核SQL分頁。**ci-tests**（`8797a66`）：新增`.github/workflows/ci.yml`（API SQLite、專用PostgreSQL 14個測試、web），`test_migrations`路徑不依賴cwd、`test_health`補11個邊界案例、web依賴升patch；Playwright E2E未納入CI。**web-fixes**（至`5471b5c`）：回報草稿不再被其他紀錄儲存清空、API逾時釋放鎖、節點／時程日期表單未存離開提醒、副手跨導覽保留對話、預覽頁lazy載入（主bundle 587→489kB）、Escape與tab無障礙、捲軸量測節流、下載URL延後釋放、待辦搜尋debounce、未開始空階段可新增第一個任務等。整合：`feature/review-fixes`由main依序`--no-ff`合併四個分支（web只合到`5471b5c`，其後3個UX commit留待另開PR），兩兩合併無衝突。整合測試：API全量716pass／14skip exit0（14個為專用PG，ci-tests在Linux容器實跑全過）；Vitest 35檔332pass、build（含tsc）exit0，無>500kB警告。未做：真瀏覽器E2E、實際Funnel驗證、GitHub Actions實際執行（push後確認）。遺留（不阻塞）：cookie不分埠號只能靠獨立主機名稱解決；`operation_links` GET仍加鎖；Windows上PG races受`msvcrt.locking`影響；`tree.test.tsx`高負載可能逾時；Starlette httpx棄用警告建議另案。2026-10-27 GitHub回報PR #4與main衝突（main新增59個commit，含ACCOUNTS、AI閘道、可攜包等）：在暫存worktree合併`origin/main`解衝突——`auth.py`登入改用main的`account_service`（已含假雜湊與失敗紀錄），保留本PR的Secure cookie；`ai.py`採main新介面並保留`local_request`與AI SQL錯誤處理（`can_set_policy`一併改用`local_request`）；前端保留預覽頁lazy載入、AIGovernance，副手保留main新功能並補回401登出與舊原文請求中止，AI長請求（ask／preview／refreshIndex）給180秒逾時。

- COPILOT-SCENARIOS 🟢 已併入可攜包（2026-10-24）：使用者問「不同的情境可以有不同的示範問題讓使用者選嗎」，看過方案後指示「照方案做示範情境選單，做完測試並重新打包可攜包」。新增`web/src/components/copilotScenarios.ts`（題目取自示範腳本）：副手設定區最上方「示範情境」選單，選了自動切好資料集、查詢方式、歷史版本，並在資料載入後依標題選好專案；列出該情境的題目（空白時在對話區、對話後在輸入框上方）。7個可自動的情境（新人報到、改期與歷史版本、未完成工單、正式文件現行／新舊對照／附件、OCR、Text-to-SQL、交付與成本文件）加2個「示範步驟」提示卡（換帳號看權限、AI政策與遮罩）。毛研食品以外的公司只列出有資料的情境（Text-to-SQL、交付規範文件）。手動改設定時情境回到「自行設定」。測試：新增2項先RED後GREEN；Vitest 34檔333 pass（一次`returns.test`偶發失敗，單獨重跑3次與全量重跑皆pass）、tsc exit0；15176實測選OCR情境自動切到正式文件與「OCR 示範（虛構）」，點題目答「一樓警衛室」。

- COPILOT-LAYOUT 🟢 已併入可攜包（2026-10-24）：使用者表示AI助手「現在有點複雜，看不清楚答案跟問題」，看過前後對照圖後指示「照右邊的方案做，做完重新打包可攜包」。實測原版面：設定區約450px、對話區只剩120px（桌面面板整體捲動且對話區`flex: 1 0 120px`）。改為：設定收成一行「資料集・查詢方式・專案」，第一次回答後自動收合、可再展開；問題靠右色塊、答案15px卡片；來源收成「來源 N 份」、處理紀錄維持可展開；建議問題在空白時列在對話區、對話後變成輸入框上方一排；預覽改為輸入框下方的小連結。只改`CopilotPanel.tsx`與`styles.css`，欄位名稱與功能不變。測試：新增版面測試先RED後GREEN；`workspace.test`改為允許「查詢設定」按鈕在無資料時可用（刻意的行為改變）；Vitest 34檔331 pass、tsc exit0；E2E加`e2e/copilot.ts`輔助（展開設定、展開來源），對15176跑`ai-local-model` 1280／375 pass；`ai-starter`失敗為既有問題（10/23 `ed9bce5`改了快捷問題文字但該spec停在10/20，且假設無模型），本次未修；其他AI E2E依賴已遺失的原始144專案資料，無法在此環境執行。第二輪（使用者：「還是有很多空間被浪費了，盡量讓重點對話能看清楚」）：標題與設定摘要併成一行、「預覽」改為輸入列內的小按鈕、回答下方的處理方式／來源／處理紀錄並排一行、內距與間距縮小、建議問題列變細、桌面面板寬520→640px。1024×768實測：對話區455→589px、單行回答卡125→75px；375px：標題30px一行、對話區645px、無水平捲動。Vitest 331 pass、tsc exit0、`ai-local-model` 1280／375再跑pass。另：包上一次示範題D05在剛啟動、模型未載入時答得過短（「沒有。」），重問5次皆完整，屬偶發。

- AI-DEMO-DATA 🟢 已併入可攜包（2026-10-24）：完成`deploy/ai-demo-data/`（`generate.py`固定種子產生器、`verify.py`、`pack/`進git：6公司×4專案、1,050筆、78份文件、336KB），`build_seed.py`以正式匯入器匯入並對6家都啟用本機模型，示範題新增D22–D25。驗證見§7。一次獨立唯讀審查：初審無阻擋、3項應修（重產比對受SQLite版本影響、reviewer／readonly看不到文件、隔離版跑示範題會因D22中斷）＋3項輕微，全部修正後複核Ready。偏離：允許清單外改了`deploy/check_demo_questions.py`（隔離版略過D22–D25，可攜包不略過）與檢查表。產品程式未改。背景：使用者要求可攜包含Text-to-SQL，但原始`ai-demo-data`（10/11產生、144專案）不在git、這台電腦與其Docker都找不到（Docker無任何專流volume），使用者表示「另一台拿不到」，指示「先寫一份短規格：重新產生一份較小的虛構資料給 16 種分析用，給我確認後再做」。[短規格與計畫](superpowers/plans/2026-10-24-ai-demo-data.md)使用者回覆「4 項都照建議：照規格做、資料量照寫的、資料包進 git、新增 4 題示範題」。順帶發現：副手預設選「原有展示資料」，資料不存在時一打開就顯示「資料尚未就緒」。

- PORTABLE 🟢 第一、二層驗證通過，待第三層（2026-10-24）：使用者指示「之後要包成一包，放在別人的電腦上跑」；[短規格與計畫](superpowers/plans/2026-10-24-portable.md)使用者回覆「7 項都照建議」（照規格做、只支援Windows、只綁127.0.0.1、從空資料庫重建、含OCR、第三層由使用者找電腦測、可用python-build-standalone）。完成：`deploy/portable/`（`serve.py`單一回環程序提供網頁與`/api`並明確執行API lifespan、`build_seed.py`從空資料庫重建乾淨資料、啟動／停止／還原腳本、`build.py`打包與掃描、使用說明、授權說明、[另一台電腦檢查表](../deploy/portable/另一台電腦檢查表.md)）。產物在repo外`output/portable/ProjectFlow-Portable-20261024/`與同名.zip（約7GB）。驗證見§7。一次獨立唯讀審查：初審Not ready（OCR缺VC++執行階段、serve.py會解析UNC路徑、繼承OLLAMA_*等），修正後複核Ready。AI代決與偏離：模型改在打包時建好放入包內（規格原寫第一次啟動時建立），GGUF核對SHA-256、Modelfile照驗收版（含`TEMPLATE {{ .Prompt }}`）；允許清單外改了`deploy/check_demo_questions.py`（多允許15190/api）並新增檢查表；`start.ps1`加`PF_PORTABLE_NO_BROWSER`供自動測試不開瀏覽器。已知限制：正式文件索引的變更判斷含檔案建立時間與OCR模型修改時間（`api/app/ai/formal_index.py`、`ocr.py`），解壓後第一次啟動與每次還原都會重建索引（實測約5秒、含OCR）；改它要動產品程式，未改。未push。

- TEMPLATE-TRIAL 🟢 小修（2026-10-24）：使用者指示「加入三份樣板測試」並「修正：按產生文件時被擋下的錯誤訊息要出現在使用者看得到的位置」。15176隔離版另建專案「文件樣板試用（虛構）」，三份樣板各產生一份：必填擋下（前端與API 422）、編號MTG-2026-001／Q-2026-1024-01／WO-001、報價小計3,970、稅198.5進位199、總計4,169，Word內容核對一致。修正：`DocTemplateFill`表單顯示時錯誤訊息改放在「產生文件」按鈕正上方（原在表單頂端，捲到底按時在畫面外約600px）。驗證見§7。未push。

- ACCOUNTS 🟢 隔離交付（2026-10-24）：使用者核准[短規格](superpowers/plans/2026-10-24-accounts.md)（照規格做、「不用鎖」、公開時自動關閉示範密碼），並說「照你的建議繼續做下去，不用停下來問我」。完成：帳號與密碼頁（管理者新增／改角色／停用與啟用／重設密碼；臨時密碼只顯示一次、無易混字元，首次登入強制改密碼；每人可改自己的密碼）、停用即登出、至少保留一位管理者、`*.ts.net`公開入口或`PF_DISABLE_DEMO_PASSWORDS=true`拒絕`demo-`密碼、同一來源＋同一帳號一分鐘失敗20次暫停（不鎖帳號）。一次獨立唯讀審查：初審Not ready（nginx後所有人共用位址，按位址限流會讓任何人擋住全公司），改為位址＋帳號並修最後管理者競態、帳號是否存在的時間差、重複帳號500；複核Ready。審查提醒：公開入口上有人持續猜某一帳號，可讓該帳號暫時無法從公開網址登入（本機不受影響）。驗證見▶現在。偏離：允許清單外改了NavIcons.tsx、types.ts、WorkspaceShell.tsx（新導覽頁）、AuditLogView.tsx（事件名稱）、`api/app/demo_pack.py`（修DOC-TEMPLATE造成的舊資料包匯入回歸）。未push／合併／部署。

- DOC-TEMPLATE 🟢 隔離交付（2026-10-24）：使用者核准[短規格與計畫](superpowers/plans/2026-10-24-doc-templates.md)四項（照規格做、只開管理者、可加docxtpl、沿用AI分支），AI代決細節記在該文件末。完成：樣板庫（上傳.docx掃描代號、欄位設定、編號格式、稅率與進位、換檔改版、停用／刪除、三份虛構範例）、文件分頁「用樣板建立」（必填擋下、自動欄位、明細即時計算）、產生Word存成文件版本、「修改內容重新產生」新版本、稽核只記欄位名稱。一次獨立唯讀審查：初審Not ready（XML屬性／孤立頁首可夾帶Jinja、字元參照`&#123;`繞過），已改為檢查lxml正規化後每個XML部分並加5個測試，兩輪複核Ready；非阻擋：刪除樣板不退容量、產生失敗會跳號、還原版本不保留樣板關聯。驗證見▶現在。偏離：允許清單外改了App.tsx（掛樣板庫）與AuditLogView.tsx（事件中文名稱）；因主checkout停在舊main且有他人未提交文件，改用worktree `../projectflow-rag`開發。正式Docker／PostgreSQL未實測、未push／合併／部署。

- TIME-FIX 🟢 隔離交付（2026-10-23）：使用者指示「A03跟S01繼續修」。依[短計畫](superpowers/plans/2026-10-23-time-fix.md)：改前先凍結第三份獨立題庫`51544c5`；檢索前中文時間轉HH:MM、question_times入模型內容、時間區間與是非題規則、未記載回答無引用也轉固定拒答。結果含誤判與無法比較的限制如實記錄。未push／合併／部署。

- REFUSAL-FIX 🟢 隔離交付（2026-10-23）：使用者指示「先改善過度拒答」。依[短計畫](superpowers/plans/2026-10-23-refusal-fix.md)：改提示前先凍結第二份獨立題庫`08637eb`並只看總分基準；以開發題庫調整：等價規則、移除「未記載也拒答」句、伺服器把開頭即「資料未記載」的回答轉固定拒答、他公司規則（點名他公司且可見來源未提及時不呼叫模型）。結果與退步（S01）如實記錄。未push／合併／部署。

- HOLDOUT-EVAL 🟢 隔離交付（2026-10-23）：使用者指示「繼續做獨立題庫」。依[短計畫](superpowers/plans/2026-10-23-holdout-eval.md)：只依教材原文另寫43題（措辭不沿用開發題庫）＋`deploy/check_holdout.py`自動評分；**第一次執行前commit凍結**`4f4bf9d`，執行後git diff為空。首輪37/43，結果與限制（開發者撰寫、非第三方盲測；自動判定非完整語意評分）如實記錄；本輪不改提示，避免題庫被污染。

- OCR 🟢 隔離交付（2026-10-23）：使用者指示「繼續做OCR」，選RapidOCR套件；預設簡體模型把繁體認成簡體或漏字，使用者同意（「可以繼續」）改下載RapidAI官方繁中辨識模型（ModelScope，SHA-256核對）。依[短計畫](superpowers/plans/2026-10-23-ocr.md)：圖片與無文字層PDF頁OCR、低信心行丟棄與整份略過、OCR標示與信心、像素／頁數上限、OCR開關或模型變更自動重解析、OCR套件另列不進正式主依賴。示範題加D20／D21。驗證見▶現在。未push／合併／部署。

- CLASSIFY-MASK 🟢 隔離交付（2026-10-23）：使用者指示「繼續做資料分級與遮罩」（README F9／§8.5）。依[短計畫](superpowers/plans/2026-10-23-classification-masking.md)：公司→專案→節點→文件繼承、只能更嚴格（放寬回422）、公司預設機密（AI代決：沿用原本未分級從嚴）；規則遮罩（比例、金額、電話、Email、合作夥伴名）與還原；政策三選一但無雲端供應商、任何政策都不送出（AI代決：混合與允許雲端都遮罩內部內容）；含機密整題只限本地；預覽列遮罩後雲端內容；真實「AI政策與稽核」頁（非隔離時維持原示意）；AI稽核查詢。延後：雲端供應商、欄位級分級、本地小模型偵測、正式PG資料表。驗證見▶現在。未push／合併／部署。

- VECTOR-RETRIEVAL 🟢 隔離交付（2026-10-23）：使用者指示「要有可以示範查詢的題目，並繼續把這份架構完成」，選README架構圖的「向量檢索」並同意下載本地embedding模型。依[短計畫](superpowers/plans/2026-10-23-vector-retrieval.md)：bge-m3（隔離Ollama，雙模型常駐）、入門文件向量側檔、正式索引向量表（增量／補齊／換模型重算）、關鍵字前3名保留＋RRF補足、向量只在已授權候選中計分、失敗退回關鍵字並標示。純RRF使Q10退步（retrieval-1）已撤回。新增[示範題目](ai-demo-questions.md)、`deploy/check_demo_questions.py`、`deploy/check_retrieval.py`與換句話說題庫；副手快捷鈕改用示範題。驗證見▶現在。未push／合併／部署。

- LOCAL-MODEL-POLISH 🟢 隔離交付（2026-10-23）：使用者指示「先不要碰（遠端新分支），先把我目前本地的rag分支，審查後繼續完成」。high審查9項；使用者選「放得下的先送」修正位元組當token的輸入預算（正式文件4段以上整題降級）。依[短計畫](superpowers/plans/2026-10-23-local-model-polish.md)：字元估算＋依排名送完整段落、`sent_count`與畫面標示、`as_of`入提示、Q09／Q28／Q32措辭；單一來源檔不存在只略過、Windows發布重試、document 503、starter原文依include_history、狀態錯誤自動清除。提示三版比較，第2版退步撤回；Q07仍為已知限制。延後：來源雜湊效能、峰曜一般成員驗收帳號。驗證見▶現在。未push／合併／部署。

- LOCAL-AI-HANDOFF（2026-10-21）：依使用者「做好交接檔 commit」整理[本地AI／RAG交接檔](LOCAL_AI_HANDOFF.md)，涵蓋啟動、隔離路徑、程式入口、canonical驗收、三項語意限制及後續工作。僅文件提交；核對路徑與差異，不重跑產品測試、不改執行資料、不push／合併／部署。

- LOCAL-MODEL 🟢 隔離交付（2026-10-21）：依[短規格／計畫](superpowers/plans/2026-10-21-local-model-acceptance.md)完成Qwen3 4B本地串接、嚴格完成／拒答結構、限定引用、版本metadata與真模型驗收。15176／18006／11436新副本。41例與4權限檢查、API57／前端15／Edge2及原資料保留證據見▶現在；三項輕微語意限制留後續，不宣稱完美或獨立測試。未push／合併／正式部署。

- INDEX-INCREMENTAL 🟢 隔離交付（2026-10-21）：依[短計畫](superpowers/plans/2026-10-20-incremental-index.md)完成逐來源變動判斷、未變文字與FTS沿用、刪除清理、無變動零發布、舊格式一次建置及管理者統計。API43pass、前端15pass、build與Edge桌面／手機4pass；獨立審查無實質問題。新incremental副本，原DB／檔案hash不變、30表411筆核對保留。未push／合併／正式部署。

- INDEX-AUTO-HISTORY 🟢 隔離交付（2026-10-20）：依[短計畫](superpowers/plans/2026-10-20-index-auto-history.md)完成10秒背景變動檢查、無變動不重建、失敗保留／重試、現行／歷史選項、引用與模型資料版本警語、即時權限。新auto-history隔離副本，原DB／檔案hash不變。相關API／前端／Edge證據見▶現在；獨立審查P2已修並複核。不push／合併／正式部署。

- FORMAL-INDEX 🟢 隔離交付（2026-10-20）：依[短規格／計畫](superpowers/plans/2026-10-20-formal-document-index.md)完成正式文件／附件手動索引、TXT／CSV／文字PDF／DOCX／XLSX解析、最新版本／即時權限、分段引用與機密預覽。另複製隔離DB及獨立檔案區，原資料hash與30表81筆原資料核對保留。API79pass及審查修正後相關8pass、前端316pass、build與新舊資料集Edge4pass；獨立審查P2已修並複核。僅本機分支交付，未合併／推送／正式部署。

- AI-GATEWAY-LOCAL 🟢 隔離交付（2026-10-20）：使用者授權繼續後續工作，按[本地閘道短計畫](superpowers/plans/2026-10-20-ai-gateway-local.md)完成模型統一出口、教材分級、零模型預覽與摘要稽核，程式`c964f97`。API25pass、前端全量314pass／最後相關11pass、tsc/build及桌面／手機2pass、32題來源／權限評測無退步，獨立審查與複核無實質問題。只隔離交付，正式繼承／遮罩／雲端／向量索引留後續。

- RAG-STARTER 🟢 隔離交付（2026-10-20）：使用者授權接續匯入後續工作，並指定假資料改用現有公司。依[短規格／計畫](superpowers/plans/2026-10-20-rag-starter-import.md)，改成毛研食品／峰曜科技，新增獨立starter-v1資料集、PDF文字解析、搜尋與來源、新舊版本及完整工單查詢。舊AI資料與正式DB保留；人資限定資料暫限admin。已在repo外獨立AI區匯入24份並完成17項API、前端全量311及最後相關9項、桌面／手機2項驗證；32題來源／權限驗證通過，模型答案品質未測。使用者確認Docker仍出錯，先交付15175隔離SQLite版；未匯入正式環境、未push／合併。

- RAG-SAMPLE（2026-10-20，獨立素材交付，非產品功能完成）：依要求產生一般人資易讀的RAG假資料與尚未完成工作清單。產物位於repo外的`../output/projectflow-rag-starter-20261020/`：6份會議紀錄、8份工單、4份通知／郵件、6份中文PDF，共24份文件；另附32題預期問答、來源與權限metadata、SHA-256、ZIP及系統待辦盤點。情境為新人報到、教育訓練與歡迎包，含舊版／新版、人資限定與跨公司隔離案例。以本機main `3c1294e`的README／看板／AI文件與匯入程式盤點；現有文字RAG已實作，AI閘道與正式文件索引仍待完成。本包不是既有`app.ai.import_cli`契約，需另外轉接及隔離驗證。24份來源、32題引用／公司／角色／指定證據片段與6份單頁PDF完整中文擷取檢查通過；6頁已渲染目視確認。未匯入系統、未改產品程式／正式資料、未跑RAG模型評測或產品回歸，未部署／提交／推送。

- DOCS-CLEAN ✅：使用者2026-10-20指示同步git、整理本地內容、把已完成的進度從README移除並精簡、依目前進度更新架構圖，確認後再push。fetch後origin沒有新commit，本機main領先1個（`d3fc44e` OPS-PUBLIC紀錄）。README（1045→約810行）刪除頂部逐次交付公告、協作者分支段、目前進度表與UI／TP逐段說明、Demo功能總覽；改為目前狀態、快速開始（本機／給別人試用／自動驗收／單檔Demo）、正式版功能總覽、§8只列正式版還沒做的項目；§3–§5規格保留，§9「已決定」修正前端（實際未用dnd-kit／React Flow）與文件編輯兩列。架構圖改為正式版現況：web／api／db容器、files與ai_data volume已完成，區網與Tailscale試用、AI副手與Ollama為試用級，內網HTTPS、AI閘道、pgvector待建置，備份／NAS、ERP／AD、雲端LLM為外部目標。AGENTS.md文件地圖的README列同步更新。`docs/technical-roadmap.md`（使用者本機2026-10-19的技術路線圖，原未追蹤）一併提交，只把一句對話用語改成中性說法。

- OPS-PUBLIC ✅：使用者2026-10-15回報「今天開啟又不能用了，別人點網址打不開」，並貼上`Desktop\projectflow-local\start.bat`（repo外的本地共用版：uvicorn 8001、經Tailscale分享8443）的啟動畫面。排查：本機8001回200；`tailscale funnel status`顯示8443為tailnet only。實測`tailscale serve --bg --https=8443`會印出「Removing Funnel for …:8443」並把8443移出AllowFunnel，而舊`start.bat`把輸出丟到nul，所以每次啟動都會關掉公開，對外顯示的卻是「已轉發」。另外10000正式版：Docker引擎正常但沒有容器在跑（restart=no），`shell:startup`裡沒有本repo捷徑，08:08開機後沒有人啟動。使用者選「改成公開」與「一起啟動」：開啟8443 Funnel；repo外`start.bat`改用`tailscale funnel`，失敗時顯示提示，並更新其README；`python deploy/public_trial.py` exit0，本機與公開health 200。之後使用者指示加捷徑：`shell:startup\ProjectFlow 公開試用.lnk`→`開機自動啟動-公開試用.bat`（工作目錄為repo根目錄、可見視窗），已讀回確認目標存在，未實際登出重登測試。驗證見▶現在的測試基準。8443本地共用版沒有登入，公開後任何人都能修改或重置資料；projectflow-local不在git。

- OPS-SYNC ✅：使用者2026-10-14指示「同步最新的git，並部署在本地」。fetch後origin/main為`28dbecb`（使用者在GitHub合併PR #3，含本機`ed530e5`），本機main無獨有commit，`git merge --ff-only origin/main`。因15173為公開模式，用`python deploy/public_trial.py`重新部署（只重建web）。合併把▶現在變成兩張表、README漏掉網際網路試用說明，已整併與補回。

- PR交付（2026-10-13）：依使用者要求將本分支正式介面更新納入 [PR #3](https://github.com/chenliyu0410/projectflow/pull/3)，等待審閱。以下歷史項目的「本機／未推送」為當時狀態，以本筆交付紀錄為準。前端全量30檔306pass；更新兩項過期／焦點等待測試，獨立複核無實質問題。相依圖獨立 HTML 與登入風格試稿均在儲存庫外，暫不採用、不提交；正式相依圖維持現況。

- COMPACT-HEADER ✅（2026-10-13）：新增子節點下拉移到帳號左側，專案總覽標籤與名稱同列、根頁省略重複路徑，手機帳號縮為頭像。1280／375端對端2pass；單元三檔初跑90pass／12fail（舊階段測資仍todo及根頁路徑斷言），更新測資／斷言後App56pass，另外兩檔46pass。型別／build exit0、唯讀審查無實質問題。本機交付，未推送／合併／部署。

- PHASE-CARDS ✅（2026-10-13）：副手追加改為桌面上下16px／手機12px留白，圖示每6秒微動／光暈，展開及減少動態時停用。隱藏入口造成關閉焦點回復失敗已修；工作區單元26pass、桌面／手機端對端2pass、型別／build0。追加恢復所有階段進度條（進行中主色、其餘反灰），加強卡片外框／頂邊／標題／狀態標籤；追加桌面與手機端對端2pass、型別／build exit0、唯讀複核無實質問題。新增子節點為首項、階段三狀態卡片與進行箭頭、放大浮動副手並保留上下留白。使用者已選只有進行中可點，其餘卡片停用。相關單元48pass、桌面1280／手機375端對端2pass、型別／build exit0，獨立唯讀審查無實質問題。僅本機交付，未推送／合併／部署。

- HEADER-FLOAT ✅（2026-10-13）：使用者右上角、副手右下角浮動入口、專案操作下拉；[短規格與計畫](superpowers/plans/2026-10-13-header-floating-actions.md)。桌面／手機端對端2pass、修正後相關單元45pass、型別／build0、獨立審查複核通過。全量單元初跑303pass／2個測試時序問題已修，其他歷史端對端未重跑。延續現有分支，僅本機交付，未推送／合併／部署。

- NAV-SURFACE ✅（2026-10-13）：依使用者指示在目前分支調整自動隱藏捲軸、右側專案第二層面板、頁籤與內容連接底色；[短規格與計畫](superpowers/plans/2026-10-13-navigation-surface.md)。僅前端，本輪不推送／合併／部署。

- UX-CHILD ✅（2026-10-12，協作者本機；2026-10-14經PR #3合併main `28dbecb`）：追加左側專案遮蔽修正：單一捲動、長名稱換行；5尺寸＋時程E2E 8pass、相關前端31pass、build0、獨立審查無阻塞。完成時程新增／拖曳／限制原因／位置保留／觸控修正；[短計畫](superpowers/plans/2026-10-12-ux-child-modules-navigation.md)、[檢查與後續 UI／UX 清單](ux-child-review.md)。前端 298pass（單工作程序）、型別／build exit0；資料包 80帳戶×39專案的528組同公司矩陣通過，相關API 76pass，桌面／手機／唯讀E2E 3pass。獨立審查父層失效問題已修並複核。本輪不合併／push／部署，優先於歷史 D50。
- PUBLIC-TRIAL ✅：使用者2026-10-14指示「給我本地開伺服器，讓別人能測試projectflow的方法」並附LH／PowerQueryTW的開機自動啟動.bat；被問開放範圍選「網際網路（Funnel）」、啟動方式選「開機自動啟動 .bat」，即授權本機15173經Tailscale Funnel對網際網路開放試用（D65 §14第7點）。[短計畫](superpowers/plans/2026-10-14-public-trial.md)：Funnel 10000→web新增的loopback 15174（nginx 81只收`*.ts.net` Host、對API帶`X-Forwarded-Proto: https`，公開疊加檔讓uvicorn採用），`deploy/public_trial.py`等Docker／Tailscale後發布並健檢，不覆蓋別人的10000；`--stop`只關自己的Funnel並回到本機模式；根目錄兩個ASCII／CRLF .bat。一次唯讀獨立審查Ready；非阻擋第1點（使用者目錄的Docker Desktop）已修，其他見§7。部署：`public_trial.py`與兩個.bat經cmd實跑皆exit0，本機與公開health 200；Funnel 443／8443未動；區網IP連15173／15174皆拒；公開網址帶偽造`Host: 127.0.0.1`／`localhost`回421；經15174以ts.net Host登入yu得6家切換清單，https Origin通過同源檢查（未知公司404、未實際切換），http Origin 403，AI模型設定403；之後登出。限制：內建瀏覽器擋公開網址的JS／CSS（ERR_BLOCKED_BY_CLIENT，curl取得200且本機同bundle正常），外部網路實際畫面待確認；密碼`demo-<帳號>`可推得；無帳號管理／改密碼／登入限流。

- LAN-SWITCH ✅：使用者2026-10-12問「有辦法一個帳號就切換公司嗎」，選方案A「好，照 A 做」：把既有展示公司切換開放給`--lan`區網試用的管理員（切換後身分是該公司的展示管理者）；方案B（一個帳號屬於多家公司）未選。[短計畫](superpowers/plans/2026-10-12-lan-company-switch.md)。新增API環境變數`PF_SHOWCASE_LAN`，與`PF_SHOWCASE_MODE`都為true時展示切換與展示身分session不限本機Host；`start.py`每次強制帶值（`--lan`才true），驗收環境永遠false；AI模型設定仍只限本機，前端未改。一次唯讀獨立審查Ready（另以暫存env實測compose：shell值優先於env檔）。部署：pg_dump後`start.py --lan`，API容器重建、web／DB未重建，容器內`PF_SHOWCASE_LAN=true`；127.0.0.1與區網IP health ready；以區網Host登入yu回傳6家公司切換清單後登出。未實際在區網執行切換（避免寫入稽核）；非阻擋：選單文字仍為「切換公司（本機展示）」。

- LAN-TRIAL ✅：使用者2026-10-12指示「你先弄一個我本機能跑的，我要給同網域的其他人測試」，即授權本機15173對同網路開放試用（D65 §14第7點要求的LAN使用者授權）。[短計畫](superpowers/plans/2026-10-12-lan-trial.md)：`deploy/start.py --lan`只讓web綁0.0.0.0，預設啟動強制127.0.0.1（不沿用殘留的WEB_BIND），API與DB不對外，`--lan`不可用於驗收環境。唯讀獨立審查第一輪No：區網`http://<IP>`不是安全情境，瀏覽器沒有`crypto.randomUUID`，庫存入帳／退貨／沖銷與模板新增節點會失效；以Plan fix補列前端檔，新增`newId()`改用`getRandomValues`備援，複核Ready。部署：pg_dump備份後`start.py --lan`，`compose port`為web `0.0.0.0:15173`、API `127.0.0.1:18000`，只重建web；127.0.0.1與172.22.32.95的`/api/health/ready`皆ready、首頁200，區網IP連18000失敗；瀏覽器在區網IP確認登入頁、`isSecureContext=false`、`randomUUID`不存在、bundle含備援。未做：HTTPS、帳號管理／改密碼、Host標頭強化；密碼為公開的`demo-<帳號>`，只限信任網路。防火牆與他機實測由使用者處理。

- OPS-RESTORE ✅：使用者2026-10-12問本機15173專案為何變少、切換公司去哪，選擇「搬另一台的資料庫過來」。本機DB只有10-08 P1c種子（git不同步資料），公司選單需本機`deploy/.env`的`PF_SHOWCASE_MODE=true`而本機未設。原請手動匯出pg_dump，後使用者貼上另一session的DATA-PACK交付說明，改用`deploy/demo-data`去敏資料包還原。Claude先pg_dump本機DB（119,599 bytes，pg_restore列238項，.superpowers/f1-ret-deploy/before-restore.dump）並在本機`deploy/.env`加`PF_SHOWCASE_MODE=true`；清空資料庫被自動權限判為大量刪除而拒絕，改由使用者執行：停API／web、DROP／CREATE `projectflow`、`deploy/start.py`（不seed，migrate到0019）、`deploy/demo_data.py import`。匯入27表共1758列與清單一致（逐表SHA-256核對）。Claude核對：alembic 0019、health ready、yu／demo-yu登入、左下公司選單可用（6家公司，各有專用展示管理者）、專案6家合計39（食品8、電子8、活動7、工程6、軟體6、禾沐4）、食品採購紀錄3。資料包不含稽核、通知、session與AI資料，故活動與稽核紀錄為空、AI資料區未就緒；帳號密碼皆為`demo-<帳號>`。

- DATA-PACK ✅：使用者2026-10-12要求「把資料庫內容打包上傳到GIT」，經詢問選擇去敏展示資料包（repo為private）。新增`api/app/demo_pack.py`、`deploy/demo_data.py`與`deploy/demo-data/`：匯出15173的27張業務表共1758列（migration 0019），排除sessions／audit_logs／notifications並不寫密碼雜湊，還原帳號密碼為`demo-<帳號>`，只能還原到同版本的空資料庫。`test_demo_pack.py` 2pass；隔離throwaway PG（projectflow-packcheck，已down、volume保留）實測還原→再匯出27表SHA-256全同、重複還原拒絕、yu／demo-yu登入可用。輸出掃描無密碼雜湊／token／env。未另做獨立審查。上傳時遠端已有另一session的F1-RET（0019），經使用者選擇：本機未push的資料包commit rebase到origin/main（README／PROGRESS僅新增段落衝突，兩邊保留），整合後相關API 68pass、migration 23pass；先備份（.superpowers/f1-ret-local），由使用者於本機執行start.py部署0019，3338列／1檔案／env保留，再以0019重新匯出（列內容不變）。發現Windows autocrlf clone會改寫JSON換行致SHA-256不符，新增`.gitattributes`令`deploy/demo-data/**`不轉換，並以新clone驗證。

- OPS-CLEAN ✅：使用者2026-10-12看到本機15173總覽滿是「P1b E2E …」專案，選擇「只刪測試專案」：刪除10-08 P1b自動測試直接寫入本機正式庫的11個測試專案及其44節點、11關卡、36筆相關稽核（25筆連節點、11筆建立紀錄）；兩個示範專案、帳號、部門與其稽核保留。系統無刪除專案功能，以單一DB交易（範圍與剩餘數量不符即中止）執行。事前pg_dump備份（125,901 bytes，pg_restore列238項，存.superpowers/f1-ret-deploy/before-cleanup.dump）。結果：專案13→2、節點47→3、關卡11→0、稽核39→3，帳號7、部門5、組織2、模板2不變；health ready，食品公司總覽1專案、專案與稽核端點200。

- F1-RET ✅：使用者2026-10-12指示「開始做退貨退料與沖銷」（同提案第3次交付）：採購退貨、工單退料、各類流水沖銷一次並連回原紀錄，原流水不改不刪；使用者同日選定退貨恢復未收等補貨、結案單據須先重開才能退貨／退料／沖銷；[短計畫](superpowers/plans/2026-10-12-f1-returns-reversals.md)。工程交付已合併main，依指示部署本機15173，原資料保留。

- F1-WO ✅：使用者2026-10-12指示開始同提案第2次交付「工單產量與狀態」：指定成品與計畫產量、累計領料／完工、系統計算生產狀態、完工不超計畫、人工結案／重開；手動領料保留，BOM自動扣料延後；[短計畫](superpowers/plans/2026-10-12-f1-work-output.md)。15173已部署，原資料保留。退貨／退料沖銷待指示。

- F1-PO ✅：使用者2026-10-12指示依「業務流程→AI正式資料→團隊試用」主線，先做採購明細、部分收貨進度與單據收貨狀態（超收拒絕、人工結案／重開、舊單不推算明細）；[短計畫](superpowers/plans/2026-10-12-f1-purchase-lines.md)。15173已部署，原資料保留。後續工單產量與狀態、退貨／退料沖銷依同一提案另行交付，待指示。

- F1-WORK ✅：依使用者授權完成正式工單領料與成品入庫，保留工單來源及異動流水；[短計畫](superpowers/plans/2026-10-12-f1-work-stock.md)。15173已部署，原資料保留。

- F1-INV ✅：採購收貨增加庫存、人工盤點增減、來源與前後餘額流水；[短計畫](superpowers/plans/2026-10-11-f1-inventory.md)。已部署15173，保留原資料。

- F1-LINK ✅：依使用者指示完成專案／任務資料正式關聯，支援供應商、採購、工單搜尋、保存、查看及解除；[短計畫](superpowers/plans/2026-10-11-f1-links.md)。15173已部署，3338筆舊資料及檔案設定保留。

- F1-OPS ✅：使用者2026-10-11授權正式營運資料新增／編輯／儲存；依[短計畫](superpowers/plans/2026-10-11-f1-operations.md)交付15173，六公司94筆虛構紀錄保存並標示來源。原資料保留。

- F1-DOC ✅：2026-10-11完成正式文件上傳、TXT／CSV網頁編輯、不可變版本保存／歷史下載；其他格式上傳新版本。已保留資料部署15173。依[短計畫](superpowers/plans/2026-10-11-f1-documents.md)交付，營運與其餘F1待後續。

- AI-RAG ✅：使用者要求匯入AI-DATA並開始RAG／Text-to-SQL，依[短計畫](superpowers/plans/2026-10-11-ai-rag-text2sql.md)完成獨立AI資料區、文字檢索RAG、16種受控SQL與Ollama設定，已部署15173；模型尚未設定，免模型檢索／查詢可用。見[操作說明](ai-assistant.md)。

- AI-DATA ✅（2026-10-11）：依要求完成workspace的`ai-demo-data`獨立虛構資料包；6公司、144專案、3456任務、10368筆記、1728採購、1728成本、864抽查、432風險；4644份RAG文件／4788分段／450題RAG／96題SQL附實際結果。提供ZIP、離線總覽、SQLite、隔離PostgreSQL匯入腳本、生成器、驗證器。`python -X utf8 ai-demo-data/verify.py` exit 0：96查詢重播、30獨立彙總、4644文件與ACL、4665檔SHA256通過。PostgreSQL腳本尚未實際匯入驗證；未修改產品程式、未匯入正式DB、未連接模型。資料包為模板式合成擴充，不等同正式DB ID。

- INDUSTRIES ✅：使用者2026-10-11指示其餘公司比照禾沐，生成完整展示資料並放入系統，原資料保留。見[短計畫](superpowers/plans/2026-10-11-industry-showcases.md)。

- HEMU ✅：使用者2026-10-11要求將已確認的禾沐食品公司完整展示資料放入系統，原資料全部保留。依[短計畫](superpowers/plans/2026-10-11-hemu-showcase.md)執行。

| 順位 | ID | 工作項目 | 狀態 | Spec | Plan | 資料版本 | 依賴 |
|---|---|---|---|---|---|---|---|
| 1 | W1 | 子任務置頂回報卡 | ✅ | [spec](superpowers/specs/2026-10-01-subtask-report-card-design.md)（`3a24c52`） | [plan](superpowers/plans/2026-10-01-subtask-report-card.md)（`ed3e24f`） | 維持 v3 | F11 ✅ |
| 2 | W2 | 部門模型 | ✅ | [spec](superpowers/specs/2026-10-01-department-model-design.md)（`edf46b6`，`dfc0126` 修訂 §4.1 和範本段，以 HEAD 版本為準） | [plan](superpowers/plans/2026-10-01-department-model.md)（`dfc0126`） | v3 → v4 | W1 已合併（D1）；2026-10-05 已 ff 合併進 `main` |
| 3 | W3 | 工作流架構（**精簡版**，D31／D42）：工作流模板 CRUD、從工作流建立專案、關卡擋住後續階段 | ✅ | [spec](superpowers/specs/2026-10-05-process-control-design.md) | [plan](superpowers/plans/2026-10-05-workflow-architecture.md) | v4 → v5 | 2026-10-05 完成；依 D42 先完成功能架構，個別工作流內容由使用者之後自行添加 |
| 4 | W4 | F11 遺留問題清理 | ✖ 取消（D30，使用者 2026-10-05 指示展示模式） | — | — | — | F11-N1 併入 W2 整體修正；其餘 §5 項目延到正式版；D4–D8 維持現狀 |
| 5 | W5 | README 對齊現況（**精簡**，D30：只改 §1 快速開始、§2 功能總覽） | ✅ | — | — | — | 2026-10-05 完成；full demo 定位文字由 AI 起草，D12 改為待使用者可推翻 |
| 6 | W6 | 多公司產業範例：五個獨立公司空間、產業化工作流與營運資料 | ✅ 本地 main 已完成（D46；`0934e48`） | [spec](superpowers/specs/2026-10-08-multi-company-industry-demo-design.md) | [plan](superpowers/plans/2026-10-08-multi-company-industry-demo.md) | v5 → v6 | W3、W5 ✅；2026-10-08 全部獨立審查通過並 ff-only 合併 |
| — | P0 | 正式軌技術骨架與規則 | ✅ 已發布GitHub main | [MVP範圍](superpowers/specs/2026-10-05-formal-product-mvp-design.md) | [P0可執行計畫](superpowers/plans/2026-10-08-p0-formal-foundation.md) | Demo維持v6 | 三Task與G4獨立審查通過，合併後API8／React6／E2E4與build通過 |
| — | P1a | 正式版MVP：登入、公司隔離、migration與核心後端API | ✅ 完成並發布GitHub main | [MVP範圍](superpowers/specs/2026-10-05-formal-product-mvp-design.md) | [P1a計畫](superpowers/plans/2026-10-08-p1a-backend-core.md) | 正式PostgreSQL migration `20261008_0001_p1a_core` | 四Task與G4獨立審查通過；API35／Vitest6／E2E4與build通過，真PostgreSQL migration／seed smoke通過 |
| — | P1b | 正式版MVP：React核心UI | ✅ 已合併main | [MVP範圍](superpowers/specs/2026-10-05-formal-product-mvp-design.md) | [P1b計畫](superpowers/plans/2026-10-08-p1b-react-core-ui.md) | 沿P1a正式DB | 四Task與G4獨立審查、合併後完整回歸通過 |
| — | P1c | 正式版MVP：部署／測試／內部試用驗收 | ✅ 工程交付已合併；使用者試用待簽核 | [MVP範圍](superpowers/specs/2026-10-05-formal-product-mvp-design.md) | [P1c計畫](superpowers/plans/2026-10-08-p1c-mvp-acceptance.md) | 沿P1a正式DB | 三Task獨立審查及G4 Ready to merge: Yes；main隔離回歸/cleanup通過 |

**排程規則**
**2026-10-08使用者新指示（D54）優先**：P1c之後按以下四階段移植Demo，名稱是本輪工作ID，不等同README舊階段1至9。

**任務路線圖**：[正式版Demo功能移植](formal-feature-roadmap.md)，依使用者「規劃接下來的任務以及每個階段要做什麼」完成提案；不是已審閱的逐Task實作計畫，未開始產品修改。

| 順位 | ID | 工作項目 | 狀態 | Spec／Plan | 依賴 |
|---|---|---|---|---|---|
| 已完成 | P2a | 完整任務操作：工作區、總覽、我的任務、新增／編輯、負責人與日期 | ✅ 工程交付 | [spec](superpowers/specs/2026-10-08-p2a-task-workspace-design.md)／[plan](superpowers/plans/2026-10-08-p2a-task-workspace.md) | P1c工程交付完成 |
| 已完成 | P2b | 回報／審核、筆記、附件與稽核介面 | ✅ 工程交付 | [完整spec](superpowers/specs/2026-10-08-p2b-collaboration-design.md)／[八Task plan](superpowers/plans/2026-10-08-p2b-collaboration.md)已定稿；八Task／G4雙審、G6隔離回歸及保留資料部署通過 | P2a |
| 已完成 | P2c | 時程、模板管理、硬性FS前置與簡單相依圖 | ✅ 工程交付 | [精簡規格／計畫](superpowers/plans/2026-10-09-p2c-schedule-workflow.md)，D66 A已定案 | P2a/P2b |
| 已完成 | UI1 | 前端介面對齊：Demo框架／配色／卡片／工作區／時程 | ✅ 工程交付 | [精簡規格／計畫](superpowers/plans/2026-10-09-ui1-demo-alignment.md)，D67使用者指定，既有真實功能不變 | P2a/P2b/P2c |
| 已完成 | UI2全模板 | 15套模板各有進行中的展示專案 | ✅ | [短計畫](superpowers/plans/2026-10-09-ui2-all-template-scenarios.md)；使用者要求所有模板 | UI2 |
| 已完成 | UI2追加 | 既有專案套用模板，移除waa | ✅ | 使用者直接要求；[資料操作計畫](superpowers/plans/2026-10-09-ui2-project-fill.md) | UI2 |
| 已完成 | UI2 | 產業模板與左下展示公司切換 | ✅ 工程交付 | [短計畫](superpowers/plans/2026-10-09-ui2-showcase-library.md)，D68使用者指定本機一鍵切換 | UI1 |
| 已完成 | UI3 | Demo整體框架、首頁與我的任務精準對齊 | ✅ 工程交付 | D69／D70，[短規格／計畫](superpowers/plans/2026-10-09-ui3-frame-home.md) | UI1/2 |
| 已完成 | UI4 | 工作區／看板／回報／時程／模板操作一致 | ✅ 工程交付 | D70／D72，[短規格／計畫](superpowers/plans/2026-10-09-ui4-workspace-ops.md) | UI3 |
| 已完成 | TP-A | 任務規劃器：節點分頁、看板拖曳與卡片資訊、進度彙總、父節點完成規則 | ✅ 工程交付 | D70／D73，[短規格／計畫](superpowers/plans/2026-10-10-tp-a-board-progress.md) | UI4 |
| 已完成 | TP-B | 任務規劃器：刪除、升降級、拖曳改層級、複製子樹、復原上一步 | ✅ 工程交付 | D70／D74，[短規格／計畫](superpowers/plans/2026-10-10-tp-b-tree-editing.md) | TP-A |
| 已完成 | TP-C | 任務規劃器：時程進階（父條涵蓋、部門篩選、拖出新增、里程碑、自動順延、箭頭、關鍵路徑） | ✅ 工程交付 | D70，[短計畫](superpowers/plans/2026-10-10-tp-c-advanced-timeline.md) | TP-B ✅ |
| 已完成 | TP-D | 任務規劃器：前置進階（SS／FF、延遲、軟性、人工條件、拖線建立） | ✅ | D70／D76 | TP-C ✅ |
| 已完成 | TP-E | 任務規劃器：另存模板、套用到既有節點、模板版本、刪除模板 | ✅ | D70／D77，[短計畫](superpowers/plans/2026-10-10-tp-e-advanced-templates.md)已核准 | TP-D ✅ |
| 已完成 | TP-F | 任務規劃器：跳過申請與覆寫、部門管理、成員權限頁、待我指派、負載、通知 | ✅ 工程交付 | D70；[短計畫](superpowers/plans/2026-10-10-tp-f-permissions-collaboration.md) | TP-E ✅ |
| 已完成 | TP-G | 任務規劃器：自訂回報欄位 | ✅ 工程交付 | D70／D79，[短計畫](superpowers/plans/2026-10-10-tp-g-report-fields.md) | TP-F |
| 已完成 | UI5 | 文件／資料／營運／AI展示畫面 | ✅ 工程交付 | [短計畫](superpowers/plans/2026-10-11-ui5-remaining-screens.md)，D81：三組實作一次交付，預覽與F1正式功能分開追蹤 | TP-G ✅ |
| 後續另定 | F1 | 逐頁補正式功能：文件→資料→營運→規則副手治理 | 文件、營運資料、F1-LINK、F1-INV、F1-WORK、F1-PO、F1-WO、F1-RET ✅；規則副手治理等其餘⬜ | 原P2d拆入，不再先做後端大包 | UI5 |
| 展示後另定 | F2 | 跨頁一致性與剩餘Demo差距 | ⬜ | 進階時程／相依、子樹套用、自訂回報已移入TP（D70）；真AI／ERP／LAN另定範圍 | F1 |

1. 永遠做順位最前面、而且沒有阻塞的項目。
2. 同一時間只能有一個進行中的 feature 分支（WORKFLOW 鐵律 4、§6）。
3. 目前的項目在等決定時，用 `git branch --list "feature/*"` 判斷，不要只看狀態符號：
   - **已經有 `feature/*` 分支**：不可以開新分支，也不可以在 `main` 上 commit。只能做不會產生 commit 的準備工作（研究、把草稿放在 `.superpowers/`），或寫好交接紀錄後結束 session。
   - **還沒有分支**（例如 W3 在等 brainstorming，或開工前的 Pre-flight 就被擋下）：可以先在 `main` 上記錄 D，再去做下一個不需要決定的項目，例如 W4。
4. 佇列做完了，但 §1 的完成條件還沒達成：不要自己發明工作項目。在本表下方加「建議（待排序）」，寫好交接紀錄後結束。
5. 不可以自行開工未授權的P軌；D51已授權P0至P1c，D52已確認P0計畫。
6. 使用者在對話中的直接指示優先，但要先寫進看板（WORKFLOW §2「變更與暫停」）。

---

## 3. 工作項目明細

### UI5 — ✅ 展示版本工程交付

依[唯一執行計畫](superpowers/plans/2026-10-11-ui5-remaining-screens.md)完成一個食品案例：文件卡／v1-v2／文字編輯、關聯卡與子層來源、供應商→採購→收貨預覽→工單、七營運分頁、AI六快捷／輸入／待辦擷取／引用與送出內容／建議套用／政策與路由遮罩示例。其他公司為明確空狀態；既有任務、回報、附件和權限保持真功能。

所有新增狀態只存React記憶體，示例ID不綁真實節點；文件／收貨於示例內導航保留，離開預覽、切公司、登出或刷新清除。AI僅固定案例與關鍵詞規則，不讀真任務；遮罩只展示固定對照，不宣稱實際模型／ERP／政策或正式寫入。

**真實驗收**：build exit0；ui5-preview／App／planner三檔Vitest 91pass（exit0）。初次E2E 2pass／1fail（exit1）：回報退回重送審核1280及UI5桌面pass，UI5手機切回食品公司時，測試早於Shell重掛載開導覽而逾時；補等待公司／總覽載入後，UI5桌面1280及手機375皆pass（2pass、exit0）。涵蓋六快捷、輸入→詳情→套用、文件版本、七分頁、零預覽寫入、storage不變、離開／切公司／登出清除、無頁面溢位／pageerror。未機械重跑API／PG歷史全套。截圖已看桌面營運、手機文件／副手並與既有Demo三欄與卡片布局對照；修正active tab hover對比，部署冒煙核對最終色值。

一次唯讀獨立審查無阻擋；審查後僅修App位置說明及CSS色值／優先度，複核通過。產品`92563c1..229c445` ff-only合併main。15173只build/update web --no-deps；Docker原本未啟動，啟動Docker並恢復既有正式DB／API容器，未重建API／DB、未seed、未migration。更新前後API／DB容器ID一致；ready健康、營運／AI入口、零業務寫入及pageerror=0已實測。附件／env／資料volume未動；本輪無DB變更，未另做逐表對帳。

測試／審查／截圖日誌保留於`.superpowers/ui5/`及web/test-results。隔離acceptance停止並保留volume。展示講稿及限制見[formal-development](formal-development.md#ui5-展示操作2026-10-11)，[使用者試用清單](mvp-trial-checklist.md)未代簽。依D50發布main並核對SHA；展示完成即停止，F1／F2不自動開工。

### TP-G 自訂回報欄位 — ✅ 工程交付

使用者「照此計畫實作」核准D79。[短計畫](superpowers/plans/2026-10-10-tp-g-report-fields.md)已實作四種類型、必填／單位／選項／排序、版本驗證、歷史快照、模板／複製及TP-F例外審核。父任務保留但停用葉任務定義，退回重報保留相同欄位的值。獨立唯讀審查發現兩項P2（autoOpen歷史載入與過期申請），修正與定向測試後複核Ready to merge。

**真實驗收**：完整API初跑502pass／1fail／14skip（exit1），失敗為健康路由清單需納入新端點，修正後13pass；TP-G定向18pass，加模板父任務規則1pass。真PG十階段13pass（exit0），含0011保留資料與修改定義／送出回報併發200／409；可選舊P2a PG測試未另跑。完整Vitest240pass／9fail、2runtime errors（exit1），新增請求mock與契約修正後受影響五檔97pass、新欄位UI5pass（exit0）。最終build exit0。完整E2E34pass／3fail（exit1），測試選取器與等待修正後TP-G桌面／375px兩項通過；workspace桌面／375px及權限邊界3pass（exit0）。保留初跑失敗，不冒稱全套一次全綠。

Demo與正式版1280／375px截圖已對照；正式版無水平溢位，手機必填勾選樣式已修正。測試與審查證據在忽略目錄`.superpowers/tpg/`。產品`00e56b2`已ff-only合併main，feature已刪除。15173先備份DB及附件，再以deploy/start.py升級0011，未seed；逐表逐列舊欄位值一致（249節點、55回報），附件SHA／env／DB容器一致，新增業務列0。正式入口桌面1280／1440及375px無溢位、pageerror=0、ready健康與舊任務欄位空值／version0已驗證。唯讀瀏覽後再比對仍一致。acceptance停止並保留volume。依D50發布origin/main；未代簽使用者試用。下一批UI5，LAN限制維持。

### TP-F 權限與協作 — ✅ 已交付（使用者試用未代簽）

**授權與功能**：使用者「照建議做」核准D78及[短計畫](superpowers/plans/2026-10-10-tp-f-permissions-collaboration.md)。新增申請／核准／退回／失效結案、當次前置／閘門／父節點完成覆寫、未完成子樹跳過與快照恢復；回報覆寫申請核准只進待確認，完成仍重驗。admin管理部門、主管可見並指派本部門任務，成員權限頁、待我指派、可見負載明細、個人站內通知與已讀。migration `20261010_0010`新增兩表，既有資料保留。

**獨立審查**：一位唯讀審查者（tpf_review）指出條件變更證據不足、過期申請未結案、一般閘門缺鎖與通知；修正後又指出失效列重新整理、錯誤回報schema500、待確認重複申請。均修正並補測試，最後定向複核Ready。另自查補上閉合祖先保護、唯讀閘門與可見性重驗。

**真實驗證**：完整API475pass／5fail／13skip（exit1）；五項為路由清單、新負載欄位及主管指派權限的舊斷言，修正後health包含於24pass、metadata39pass、workspace2pass（皆exit0）。TP-F新增祖先／待確認回報／閘門解鎖定向12pass／1fail（空ID SAWarning），修正後該例1pass；gate相關43pass。完整Vitest199pass／43fail／17error（exit1），修正缺capabilities防護與新增資料源mock，相關五檔136pass／3fail後App56pass，新TP-F3pass（exit0）；build exit0。完整E2E33pass／2fail（5.5分鐘，exit1），唯一任務名稱與登出完成等待修正後兩檔4pass（exit0），含1280／375主流程及1440布局。原始失敗命令未冒稱通過。

**PostgreSQL**：七個既有migration階段通過；新增TP-F初次測試設定路徑失敗，修正後TP-F migration與四項API races通過；另增加真PG兩位審核者同時核准，結果200／409且只有一筆skip稽核，通過。SQLite migration保留舊列／回退／拒絕有損降級通過。所有業務測試在隔離環境，未清空保留的acceptance資料。

**部署與保存**：`8469021`已ff-only main；15173更新前備份DB、附件及env，升級0010後两次逐值核對全部原列／欄位、249節點、15專案、112前置、55回報、43筆記及附件SHA；原表新增0列，新增兩表空白。env與DB容器不變。1280／1440／375成員權限／部門畫面與health唯讀驗證通過，無業務寫入；備份、日誌與截圖在ignored `.superpowers/tpf/`。依D50發布main，push後核對遠端SHA。

**限制／下一步**：站內通知無Email／推播；負載是可見任務數，非工時。沒有帳號／角色管理或自訂ACL。既有部門成員不自行補寫，編輯時需把主管加入成員。下一批TP-G自訂回報欄位；使用者試用未代簽、LAN未授權。

### TP-E 模板進階 — ✅ 已交付（使用者試用未代簽）

**範圍與決策**：使用者「照建議做」核准D77與[短計畫](superpowers/plans/2026-10-10-tp-e-advanced-templates.md)。任務／階段子樹另存、專案工作流另存、追加套用、完整版本快照與選版、軟刪模板完成。來源／目標強制專案管理權；公司模板由admin／project_owner維護。保留內部進階前置、權重、里程碑與部門；負責人／協作預設不帶，人工條件重新確認，狀態／鎖定重設；套用可一步結構復原。階段另存轉普通根任務，工作流只套專案。

**畫面／互動對齊**：啟用標題列「另存為模板」「套用模板」，模板庫新增任務卡、版本作者／日期／結構、刪除確認。選版載入中禁用提交，舊版預覽停用編輯／複製，錯誤保留草稿；寫入成功但重載失敗僅重載。Demo與正式版另存／套用／模板庫1280／1440／375隔離截圖已檢視；修正手機勾選框大小。無頁面水平溢出及pageerror。

**審查**：一位唯讀獨立審查者提出選版載入競態及舊版預覽誤複製最新版兩項，另有取消後通知競態；修正後定向複核Approved。文件釐清：既有Node無獨立說明欄位、不複製筆記當說明；採300節點上限與循環檢查，不另宣稱深度限制；含里程碑必須帶日期以符合既有單日DB約束。

**真實驗證**：首輪整合因新測試使用不支援的exact型別停止，修正後PG八階段（七個migration及API併發）通過；另補真PG兩人同版編輯，結果v2／409且保留v1。完整API466pass／12skip（exit0，PG條件案例另於専用DB實跑）。完整Vitest241pass／1fail（exit1），唯一失敗為TP-A舊測試要求模板入口停用；更新契約後planner與新模板測試35pass（exit0）。build exit0。完整E2E34/34（exit0，4.6分鐘）；另存／選舊版／套用／取消／復原／刪除及畫面截圖定向通過。補充權限及稽核定向通過；曾誤用admin驗證非專案管理者，修正測試角色為project_owner後通過。沒有將原始失敗命令冒稱成功。

**資料與部署**：`0e9b83f` ff-only main。15173更新前已備份DB、附件及env，升級0009後逐值比對全部原表、249節點、112連線、43筆記、55回報、附件SHA及DB容器／env均相同；只新增15筆模板v1快照，舊表新增0列。primary桌面／手機唯讀操作及health通過，未寫業務資料；acceptance down不-v保留volume。證據／備份在ignored `.superpowers/tpe/`。

**限制／下一步**：公司模板先行，個人發布、過去任務直接搜尋套用、版本比較／回退、文件／檢查清單／AI推薦延後；自訂回報欄位留TP-G。尚未提供垃圾桶還原。下一批TP-F先做對照與短計畫；使用者試用未代簽，LAN未授權。

### TP-D 前置進階 — ✅ 已交付（使用者試用未代簽）

**範圍與決策**：使用者同意TP-C，並在人工確認條件的簡單說明後回答「好」，核准D76及[短計畫](superpowers/plans/2026-10-10-tp-d-advanced-dependencies.md)。完成FS／SS／FF、-365至365天lag、硬性／軟性、連線編輯、相依圖拖線開啟確認表單與人工條件。軟性只警示；FF在自行確認與審核核准重檢；人工條件限管理者確認／撤回，必填理由並留稽核。日期順延和可見關鍵鏈支援三種類型與lag，沿用D75原子回滾。複製保留內部邊設定，條件重新確認；軟刪除／復原保留原條件證據。沒有ERP／文件串接，模板進階留TP-E。

**審查與修正**：一位唯讀獨立審查者首輪提出PATCH缺省值覆蓋既有設定及審核中心缺軟性警示；修正後定向複核Ready to merge: Yes。另修正退回訊息、條件部分更新、拖線取消／預覽及表單標籤；公司節點阻擋計算按專案分組，避免大量專案時掃描所有邊。新增兩個批次查詢使基準8→10，保留資料成長時查詢數不變的斷言。

**真實驗證**：完整API一次445pass／3fail／11skip（exit1）；三項失敗是路由清單與查詢上限的既有斷言。修正後受影響組74pass／1fail，最後剩餘overview斷言修正，TP-D21項＋該query測試共22pass（exit0）。完整Vitest236pass／1fail（exit1），更新既有建立連線payload斷言後兩個相關檔10pass（exit0，含新增審核警示測試）；build exit0。PG七階段分次通過：verify在TP-D約束測試停下，修正測試無效字串過長造成DataError後續跑TP-D migration1pass及PG併發4pass。SQLite migration1pass／1skip。原完整命令的失敗未冒稱exit0。

**瀏覽器證據**：首輪完整E2E在舊效能及標籤下出現失敗，已停止自有程序並重建隔離15175；修正後TP-D定向1pass。完整重跑33／33通過（exit0）；15173已升級0008，更新前停止API並備份DB／附件；更新後逐值核對全部既有列、112條連線預設值、249節點、附件SHA、env與DB容器，新增0列。桌面／375px唯讀驗證及health通過；自有15181除錯服務關閉，acceptance已down不-v保留volume。Demo以新context在1280／375檢視，正式版1280／1440／375截圖，無pageerror與頁面水平溢出；所有業務測試僅用隔離環境，既有acceptance資料未重設。證據與備份在ignored `.superpowers/tpd/`。

### TP-C 時程進階 — ✅ 工程交付

**範圍與決策**：使用者「照 D75」核准[短計畫](superpowers/plans/2026-10-10-tp-c-advanced-timeline.md)。父條涵蓋可見子孫、部門篩選保留匹配路徑、每列＋與底部拖出新增、左右拉伸、單日里程碑與鎖定、延遲標示、可見FS箭頭與Demo單條關鍵鏈估算均已實作。順延預設關閉，逐項檢查可見／編輯權限；鎖定、未排程、已結束或不可編輯的受影響任務使整次改期與稽核全部回滾。鎖定／解鎖及直接改鎖定日期限系統管理員與專案負責人。日期不納入復原，新增沿用結構undo。SS／FF等留TP-D，首頁延後天數預測與完整CPM不在本階段。

**實作與審查**：`77b69b4`實作、`2e81ae8`修正。migration `20261010_0007`只新增`milestone`、`schedule_locked` false欄位；新`POST /nodes/{id}/schedule`與原PATCH共用改期服務、project lock與逐節點audit。一位唯讀獨立審查 Critical 0／Important 0／Minor 2（scope依賴載入、部門篩選多留無關階段），兩者修正後複核接受；收尾三個測試檔再次定向複核 Ready to merge，無剩餘阻塞。

**真實驗證**：一次完整隔離回歸：PG六階段（P2b、P2c、TP-A、TP-B、TP-C migration與API races）全過；API428pass／1fail／10skip，唯一失敗為舊audit故障注入仍攔截projects模組，補攔截schedule_service後與新增cascade第二次audit失敗全回滾測試2pass。TP-C定向API先16pass，再補上述第17項通過；既有project/tree/health42pass；SQLite migration11pass/6skip（PG另實跑）。Vitest233pass、build exit0。完整E2E31pass／1fail：新拖出新增測試起點被sticky名稱欄覆蓋，改可見日期區真實滑鼠座標後TP-C3/3pass（含新增、undo、順延、鎖定回滾、角色限制）。失敗均已解決；未宣稱原全量命令exit0。證據在ignored `.superpowers/tpc/`。1280／1440／375截圖人工核對菱形、連線、關鍵鏈；頁面無水平溢出、TP-C pageerror 0。

**部署／試用**：已ff-only合併main並刪feature。15173 API＋web更新、migration 0006→0007；部署前停API作一致DB／附件備份，部署後逐值比對15專案、249節點、344稽核及全部其他表：既有資料值不變、節點只新增兩個false欄位、新增0列，附件SHA、env、DB容器不變。沿用部署前session做1280／375唯讀瀏覽器檢查，pageerror 0、無頁面水平溢出、ready 200，檢查後再比對仍新增0列。acceptance已down（不-v），保留資料volume與既有ui3cmp。使用者試用清單已新增，尚未代簽。Demo基準截圖在`.superpowers/tpc/baseline/`，正式隔離截圖在`.superpowers/tpc/e2e/`。

**必要測試調整**：`api/tests/test_node_metadata.py`只更新audit mock的實際呼叫位置；不改產品規則。未引入新依賴、未改Demo、未開LAN。

### TP-B 樹狀編輯：刪除、升降級、移動、複製子樹與復原 — ✅ 工程交付

**交付**：[短規格／計畫](superpowers/plans/2026-10-10-tp-b-tree-editing.md)（11列差距表，`f4b59c1`；D74 `ca50ed7`），API `2980fd9`，前端 `5f36c25`，E2E `543b6b9`、`4c8cd02`，審查修正 `d5b999b`，文件見本次Docs commit。一位唯讀獨立審查：With fixes（0 Blocking、1 Important），修正後複核 Ready to merge: Yes。Demo對照圖在ignored `.superpowers/tpb/baseline/`（編輯抽屜層級操作、刪除確認、複製後看板、升級後帶「復原」的提示、時程「↶ 復原」，1280／375），正式版截圖在`.superpowers/tpb/e2e/`（編輯表單層級操作、刪除確認、刪除後看板，1280／1440／375）。

**畫面／互動對齊**：「編輯節點」表單照Demo加「層級操作」：↖ 升級、↘ 降級、「移動到…」下拉（Demo縮排，專案層用「（專案最上層）」，已完成或待確認的節點停用）、複製子樹，左下角紅色「刪除」。按鈕不能用時在下方說明原因（已在最上層、上方沒有同層任務、目標已完成）；表單有未儲存變更時整區停用。刪除先顯示確認：「刪除「X」？」「將一併刪除 N 個子任務。」「以下任務依賴它，前置條件會被移除：A、B」「確定刪除（可復原）」。結構操作後提示列帶「復原」（複製另有「開啟」），時程工具列「↶ 復原」，Ctrl+Z／⌘Z；復原後提示「已復原：刪除「X」」。稽核頁新增「刪除節點」「複製子樹」「復原」，被刪節點的歷史仍列出並標「（已刪除）」、不給進入連結。成員與權限分頁加「複製子樹」「刪除任務」兩列。

**正式功能完成**：migration `20261010_0006`（`nodes.deleted_at`、`deleted_by`，同公司外鍵；已有刪除資料時拒絕降級）。新API `DELETE /nodes/{id}`（軟刪除任務與子樹，前置連線移除並記進稽核）、`POST /nodes/{id}/copy`（最多300節點）、`POST /undo`；`POST /nodes/{id}/move`接受`parent_id: null`（專案最上層），權限依D74放寬為管理者或可處理該任務的人；新增／移動／複製／刪除回應多`undo_id`。ORM全域條件排除已刪除節點，只有刪除、復原與稽核頁明確讀取。復原只接受自己最近一次結構操作、只一步，之後有其他稽核、子節點或連線就409。上層是待確認／完成／已略過時，新增子節點、移入、複製、重新開啟、恢復任務都409（TP-A Minor 1）。仍未提供：階段的複製與刪除（TP-E模板）、重做、非結構操作的復原、附理由覆寫（TP-F）。與Demo刻意不同：複製只限管理者、刪除是軟刪除、上層不自動改回進行中、成員移動不能帶走看不到的子任務。

**執行注意**：
- D74：移動（含升降級、移動到…、拖進卡片）放寬到任務負責人與部門主管（`can_manage_project or can_work_node`），刪除限系統管理員與專案負責人，複製維持管理者（AI代決，與正式版新增一致）；TP-A測試中「成員不能拖進卡片」與「parent_id不能為null」的斷言依D74改寫。
- 計畫外但必要的檔案：`api/app/permissions.py`（共用`can_move_node`）、`web/e2e/workspace.spec.ts`（建立回應多`undo_id`，比對前拿掉）、`web/src/components/ReportPanel.tsx`（重開／恢復的上層說明，計畫已列為「只在需要時」）。
- 與計畫不同的小處（AI代決，可推翻）：「移動到…」多一個「移動」確認鈕（避免選錯就送出）；新增節點也提示「已新增「X」」並可復原；Ctrl+Z在回報／日期表單開著或文字框有內容時不復原，改提示先送出或取消。
- 複製子樹的根節點沿用原節點的`sort_order`，同值依建立時間排在原節點之後，沒有改動其他節點的順序。

**審查與修正**：Important 1（已完成上層底下刪除已完成子任務後，復原一定被擋）已修：上層已結束時，只有被還原的子樹含未完成節點才擋，移動的復原同理。順手修Minor：Ctrl+Z草稿保護、建立節點改取專案鎖、成員移動含看不到子任務時409、複製超過300節點的訊息、補已刪除節點入口測試。

**後續Minor（未修）**：
1. 還原刪除時重建的前置連線沒有檢查子樹與上層路徑之間的衝突，也不處理後續任務已完成的情況（少見）。
2. 「新增子節點」因上層已結束而停用時，說明只在`title`，手機看不到。
3. 非管理者「復原移動」時不再檢查子樹可見性（只是回到原位）；Ctrl+Z沒有保護協作設定未儲存的勾選。
4. 成員的「升級」沒有E2E（成員看不到上層階段時升級停用，Vitest已涵蓋說明文字）；「此節點底下有你看不到的子任務」只揭露存在，同TP-A Minor 2。

**合併與15173發布**：ff-only合併main（`f2d483c`）並刪除分支。15173這次更新API、web並跑migration：先記錄全部rows／欄位值、附件SHA、env與DB容器ID（`.superpowers/tpb/preserve.py`，ignored `.superpowers/tpb/primary/`），先建新映像，停API後pg_dump＋files成套備份，用新映像`run --rm --no-deps api alembic upgrade head`（0005→0006）後才啟動新API與web；不seed、不動DB容器。health／ready／web 200，acceptance標記404；比對結果：既有每列每個欄位值、附件SHA、env、DB容器ID逐一相同，249個節點只多`deleted_at`／`deleted_by`為NULL，新增0列。以yu既有登入在內建瀏覽器實看（1280）：【展示】食品新品開發「小量試作」的「試作工單」編輯表單出現層級操作與刪除、降級停用並說明「上方沒有同層任務可以放入」、頁面無水平捲動、console無錯誤；只按「取消」，沒有在15173做任何移動、複製或刪除，瀏覽後再比對仍新增0列。使用者試用未代勾。

**測試（2026-10-10）**：API新增`test_tp_b_tree.py`20項（軟刪除各入口、資料保留、刪除與復原、複製欄位／協作／相依、上限與截短、最上層移動、D74權限矩陣、復原只一步與只限原操作者、之後有變更擋下、上層規則）、0006 SQLite與PG保留資料測試；Vitest新增`tree.test.tsx`16項；E2E新增`tree.spec.ts`4項（真Chromium）。`deploy/verify.py`一次：PG5階段（P2b、P2c、TP-A、TP-B migration、API races）全過；API412pass/9skip；Vitest222；build0；E2E28/29（P2a測試直接比對建立回應，多了`undo_id`，調整後workspace＋tree重跑7/7）。審查修正後API414pass/9skip、Vitest222、build0、tree／workspace／planner／mvp E2E14/14。使用者試用未代勾。

### TP-A 節點分頁、看板拖曳、卡片資訊與進度彙總 — ✅ 工程交付

**交付**：[短規格／計畫](superpowers/plans/2026-10-10-tp-a-board-progress.md)（16列差距表，`cff3a29`；D73 `7dd3f82`），實作`9e8daf8`，修正與E2E`8a6bbac`、`fc7c1fd`，審查修正`e77c6dc`，文件見本次Docs commit。一位唯讀獨立審查：Ready to merge: Yes（0 Blocking、0 Important）。Demo對照圖在ignored `.superpowers/tpa/baseline/`，正式版截圖在`.superpowers/tpa/e2e/`（階段看板展開卡片＋滑過高亮、階段時程、階段相依圖、專案紀錄，1280／1440／375）。

**畫面／互動對齊**：看板原生拖曳（欄位`.over`、卡片虛線`.nest`、拖曳中半透明），提示「拖曳卡片改狀態；拖到另一張卡片上 = 變成它的子任務」，空欄「把任務拖到這裡」。卡片照Demo加「N/M 子任務」、迷你進度、%、「展開／收合」與卡片內下一層清單（狀態點、名稱、孫層數）、「✓ 回報」、「等待：A、B」、滑過或聚焦時`.hl-src`／`.hl`高亮。標題meta對所有節點顯示進度（含葉任務），深度達5層加「層數較深，可考慮拆成獨立專案」；階段條用加權進度，閘門已核准用專案色、其他橘色。時程只畫目前節點與後代，表頭「展開圖・子任務（N）」，工具列「↑ 上一層：上層名稱」，上層條內填色並標「負責人・N%」；專案層維持「總覽圖・任務（N）」。相依圖只畫目前節點底下的任務，葉節點「沒有可顯示的任務。」。上層任務與專案層紀錄是唯讀彙總，開頭用Demo句子。

**正式功能完成**：migration `20261010_0005`（`nodes.weight`預設1、0–100；`nodes.progress`可空、0–100）。`PATCH /nodes/{id}`收權重與進度（進度只限任務），稽核前後值。父節點完成規則在階段改完成、送出回報（含送出並確認）、確認回報時由API強制，409訊息固定、不揭露看不到的子節點。`POST /nodes/{id}/move`（只限系統管理員與專案負責人；循環、目標狀態、子樹與新上層路徑之間的前置連線都擋；稽核`node.move`投影可見上層名稱）。`GET /projects/{id}/records`專案層彙總。總覽專案`progress_percent`（只算可見節點），側欄與總覽專案表改用它。前端只顯示四句固定的TP-A 409文字。仍未提供：附理由覆寫與跳過申請（TP-F）、上層自動連動、升降級／鍵盤移動／復原（TP-B）。

**執行注意**：
- 計畫外但必要的檔案：`api/tests/test_health.py`（路由白名單加兩條新路由）、`web/e2e/mvp.spec.ts`（卡片多了「回報完成：標題」按鈕，標題按鈕改完全比對）、`web/src/progress.vectors.json`（前後端共用進度測試向量）。TP-A截圖放在`planner.spec.ts`而不是`visual-alignment.spec.ts`。
- 舊階段migration測試：P2b檢查改停在`20261009_0004`再升head；P2c改用新`seed_at_revision`（目前ORM在暫存SQLite建資料，只複製0003已有欄位），斷言內容不變。
- 與計畫不同的小處（AI代決，可推翻）：階段條按鈕名稱維持「進入階段：X」（既有測試錨點），進度與閘門狀態改用`aria-describedby`；被前置擋住的卡片不顯示「✓ 回報」，拖到待確認／完成時說明「尚有未完成的前置任務，完成前置後才能回報」（API本來就會拒絕）；看板只在有被擋卡片或第一次滑過、聚焦、拖曳時才載入相依資料，避免多打請求。
- 失誤紀錄：做變異檢查時誤用`git checkout --`還原`report_service.py`，把尚未commit的TP-A修改一起退掉；立刻從變異前的備份還原，diff與原修改一致、TP-A API測試24/24，之後先commit再做其他檢查。沒有影響其他檔案或資料。

**審查與修正**：審查0 Blocking、0 Important。Minor 4（時程表頭在收合時變0）已修`e77c6dc`並補Vitest。

**後續Minor（未修）**：
1. 上層已完成時仍可新增子節點、重新開啟或恢復子任務，上層會停在完成（建議TP-B／TP-F一起處理上層連動）。
2. 專案負責人若本身看不到全部節點，移動的409「不能移到自己的子任務底下」或相依衝突訊息會透露隱藏節點的存在（不含名稱；計畫已核可這些訊息）。
3. 階段條閘門狀態放在說明而非名稱（見執行注意）。
4. 狀態下拉改狀態只在本機更新節點、不重抓相依資料；目前PATCH不能把任務改完成，沒有實際影響。
5. 損壞的循環資料且排序值相同時，前後端排序的平手規則略不同（只影響已損壞資料）。

**測試（2026-10-10）**：API新增`test_tp_a_planner.py`24項（權重／進度驗證與稽核、父節點規則含看不到的子節點、移動權限矩陣與各種擋下、總覽加權進度、專案紀錄可見性與游標）、TP-A migration SQLite與PG保留資料測試；變異檢查：拿掉確認回報的子節點檢查→1 failed。Vitest新增`planner.test.tsx`（共用向量、卡片、拖曳、範圍分頁、回報卡、編輯表單、App流程含模板卡建立專案正向測試）。`deploy/verify.py`一次：PG4階段（P2b、P2c、TP-A migration、API races）全過；API393pass/8skip；Vitest206；build0；E2E23 passed／2 failed（MVP測試標題按鈕比對同時抓到新的「回報完成：標題」），`fc7c1fd`改完全比對後在重建的15175重跑mvp 2/2。審查修正後Vitest206、build0、planner＋schedule E2E 8/8，之後隔離環境down不-v。使用者試用未代勾。

**合併與15173發布**：ff-only合併main（`b68aabe`）並刪除分支。15173這次更新API、web並跑migration：先記錄全部rows／欄位值、附件SHA、env與DB容器ID（`.superpowers/tpa/preserve.py`，ignored `.superpowers/tpa/primary/`），先建新映像，停API後pg_dump＋files成套備份，用新映像`run --rm --no-deps api alembic upgrade head`（0004→0005）後才啟動新API與web；不seed、不動DB容器。health／ready／web 200，acceptance標記404；比對結果：既有每列每個欄位值、附件SHA、env、DB容器ID逐一相同，249個節點只多`weight=1`、`progress=NULL`，新增0列。以yu既有登入在內建瀏覽器實看（1280）：總覽與側欄改為加權進度，【展示】食品新品開發「小量試作」階段進度90%、「完成（還有 1 項子任務未完成）」停用、待確認卡片可拖曳且沒有✓回報、頁面無水平捲動、console無錯誤；瀏覽後再比對仍新增0列。使用者試用未代勾。

### UI4 專案工作區與操作對齊 — ✅ 工程交付

**交付**：`9a47444..3bb568c`（計畫、實作`822470e`、審查修正`28e098c`、`ea9a3aa`、文件`3bb568c`），一位唯讀獨立審查（首輪Needs fixes，1項Blocking；修正後複核Ready to merge），ff-only main，D50 push。

**畫面／互動對齊**：節點頁照Demo由上而下：麵包屑、h1目前節點、meta列（負責、期間、完成率、狀態、🔒等待前置）、右側操作、任務回報卡、專案層階段條／階段層閘門列、分頁「看板・時程・相依圖・文件・資料・成員與權限・紀錄」。主區節點樹移除。看板4欄，1280每欄與Demo同為148（改版前5欄各99、卡片標題被擠成兩字一行），375為4×240在框內橫捲。時程分段鈕、270／150px標籤欄、36px列、專案色條、兩層刻度、手機同一張圖；相依圖HTML方塊由左到右、直角箭頭、灰實線／橘虛線；模板庫卡片「用這套工作流建立專案」；審核中心三區與閘門表格。對照圖在ignored `.superpowers/ui4/`（baseline為Demo與改版前，round1／e2e為改版後）。

**正式功能完成**：沒有新API、欄位或寫入規則，所有按鈕沿用既有capabilities；完成率、期間、階段條、相依圖只用API已過濾的可見節點。仍標「尚未提供」或延後：另存／套用模板（TP-E）、文件／資料（UI5／F1）、跳過申請與角色權限表（TP-F）、拖曳改狀態、卡片子任務數與迷你進度、節點自己的時程／相依圖、加權進度（TP-A）、自動順延與關鍵路徑（TP-C）、拖線建立（TP-D）、自訂回報欄位（TP-G）。刻意差異：狀態名稱沿用正式版用詞（D72）。

**執行注意**：計畫允許清單在實作commit中補上`AttachmentList.tsx`，用途只是附件標題加數量（範圍第9項「紀錄」），未改上傳邏輯。

**審查與修正**：Blocking——「取消回報」只收合表單，已上傳附件ID仍留在狀態，之後送出會夾帶看不到的附件；上傳中取消則送出鈕一直停用。修正為取消時清空附件與ready並把焦點還給「回報完成」，新增Vitest（對舊程式實跑RED：送出鈕仍disabled）。同輪順手修Minor：刻度依像素間距抽稀（避免年份打錯產生上萬標籤）、860以下圖寬跟150px標籤欄一致、審核中心初次載入錯誤不顯示（0）。複核抓到抽稀帶來的月份標籤回歸（起點殘段擋掉月初，「26/9」蓋在十月）→`ea9a3aa`改成月初優先並補Vitest（舊程式RED：收到`26/9`）。

**後續Minor（未修）**：唯讀帳號也看得到停用的「另存為模板／套用模板」（不送請求）；「用這套工作流建立專案」只有負向測試，模板編輯中途按下未儲存內容直接丟失；模板卡按鈕文字為「查看內容」（計畫寫「查看與編輯」）；visual-alignment只跑1280／375，1440與188px欄寬靠截圖核對，未截階段條與閘門列；階段條按鈕aria-label蓋掉閘門狀態文字；時程條在手機從條上起手滑動無法橫捲（拖曳已忽略touch，不會誤寫）。

**測試（2026-10-09）**：`822470e`首輪verify：PG6、API368/7skip、Vitest172pass1fail（UI3總覽測試：標題在載入中就出現，`findByRole`先返回後讀不到載入後文字；單獨重跑3次皆過，改為等待載入後文字）。`28e098c`完整`deploy/verify.py`一次全過：PG6pass、API368pass/7skip、Vitest174pass、build0、E2E20/20（本機Playwright Chromium，不再需要Edge）。`ea9a3aa`後Vitest175pass、build0、在重建的15175跑schedule＋visual-alignment E2E5/5，之後down不-v。

**15173發布**：快照後停API，pg_dump＋files成套備份（ignored `.superpowers/ui4/primary/`），`up -d --build --no-deps web`後再啟動API；不seed、不動DB容器、API映像未重建。web／`/api/health`／`/api/health/ready` 200（database ready），前端產物含UI4新畫面；全部rows／欄位值、附件SHA、env、DB容器ID逐一相同，新增0列。以yu登入實看（320px窄窗）：專案頁h1、階段條5段、7分頁（文件／資料停用）、看板4×240在框內橫捲、頁面無水平捲動、無錯誤訊息，console只有登入前預期的`/me` 401。使用者試用未代勾。

### UI3 Demo框架與首頁對齊 — ✅ 工程交付

**交付**：`03dc854..a0c9936`，一位唯讀獨立審查（首輪Ready to merge: No，2項Important；修正後複核Yes），ff-only main，D50 push。

**畫面／互動對齊**：Demo三區（1280為252｜678｜350、1440為252｜838｜350，與Demo量測相同）；導覽名稱與線條圖示；側欄專案色、完成%與進度條；側欄「＋ 建立新專案」；總覽4卡、專案表、人員／部門負載；我的任務分組表格與位置欄；1180以下副手右抽屜、860以下導覽左抽屜，Escape關閉、焦點回開關，關閉時不可聚焦。1024／375沒有水平捲動。對照圖在ignored `.superpowers/ui3/`（Demo、final、mobile strip）。

**正式功能完成**：首頁數字都來自真API（overview／my-tasks新增唯讀欄位，D71）；建立、公司切換、登出、審核、模板、稽核沿用既有功能。仍是展示預覽或未提供：AI副手內容（F1）、營運資料與AI政策頁（UI5／F1）、延後天數預測（TP-C）、待我指派與通知（TP-F）。與Demo的刻意差異：保留「可見任務完成率」第4張卡；我的任務預設列全部狀態（Demo只列未完成）並保留搜尋篩選。

**審查與修正**：Important 1（捲動後按建立，表單在畫面外）→表單捲入畫面並取得焦點；Important 2（375有鎖標籤的標題被擠成一字一行）→標題保留基準寬度、標籤換行。E2E另抓到抽屜visibility隨動畫過渡造成開啟第一瞬間仍隱藏的時序，改成visibility立即切換、只動畫滑動，並支援reduced motion。其餘Minor延後：「☰ 選單」可見文字與aria-label不同、側欄進度換頁才更新、overview在總覽頁會請求兩次、1440只靠截圖核對。

**測試（2026-10-09）**：API workspace 30pass（新增延遲／階段／負載／位置不洩漏）。`deploy/verify.py`一次：PG6pass、API368pass/7skip、Vitest173pass、build0；E2E16fail1皆為`browserType.launch: Executable doesn't exist`（本機沒有Playwright Chromium）、4pass。改用不提交的Edge channel設定：首輪15pass5fail（登入後未等側欄、抽屜開關時序），修正後完整E2E20/20；最後一個樣式修正後重跑visual-alignment＋workspace 5/5。Vitest在修正後再跑173/173。

**15173發布**：停API後pg_dump＋files成套備份（ignored `.superpowers/ui3/primary/`），`up --build --no-deps api web`，不seed、不動DB容器。health／ready／web 200，前端產物含新首頁；全部rows／欄位值、附件SHA、env、DB容器ID逐一相同，新增0列。使用者試用未代勾。

### UI2 全模板進行情境 — ✅ 全15套資料交付

使用者要求「所有模板都在進行中，像DEMO豐富」。[短計畫](superpowers/plans/2026-10-09-ui2-all-template-scenarios.md)。實際庫為12catalog＋原食品／電子＋食品複本共15套，因此新增13案、沿用2案，而不是只處理catalog。

- 食品4案38task、電子4案68task、活動3案47task、軟體2案16task、工程2案19task；每案皆有done／doing／review／todo。总計188task：39done、15doing、15review，其他119todo。前置阻擋和Gate沿真服務。
- 新案第一phase完成且Gateapproved、第二phase進行且首task待審；另加獨立專案協調taskdoing及3筆筆記。4node舊模板補日期與待審後解鎖驗收task。既有2案不改，不改模板，不偽造實際結果；新案／回報／筆記均展示標示。待審由member展示執行者提交，管理者可真審核。
- 新增13projects／208nodes／38gates／93dependencies／47reports／39notes／3展示member／231audit。全部原rows及欄位逐值保留，files SHA／env／DB容器相同；預覽rollback、停止API一致DB+files備份後apply，重跑全already-applied無重複。瀏覽器切換真session另記正常稽核。
- 一次相關隔離測試3/3 exit0；擴充15套後相關3/3 exit0。覆蓋全部15案對應、每案真狀態/blocked/禁止自審、原rows逐值、預覽回滾、最後模板衝突時整批回滾、冪等與模式關閉。未改UI/API/schema，未重跑不相關全量。一次唯讀獨立審查與15套窄複核均Ready to apply。
- 已在15173真UI依次切換五公司，專案數4/4/3/2/2、總覽完成率18/16/26/25/26%與DB相符，無空公司；目前停活動總覽。截圖與測試/備份ignored `.superpowers/ui2-all/`。使用者試用未代勾；P2d維持後移，D50 main push。

### UI2 展示進行情境 — ✅ 資料交付

使用者澄清要「像DEMO有任務進行的樣子」。[短計畫](superpowers/plans/2026-10-09-ui2-live-scenarios.md)，兩現有專案資料操作，API/UI/schema不改。

- 主食罐2done／1doing／1review／13todo；連接器3done／1doing／1review／9todo。活躍階段標doing，電子立案phase done與Gate approved。食品原已核准5Gate全保留。
- 新增8份真schema回報（食品配方v1退回、v2待審）、4筆展示筆記；全部標「展示情境」。兩公司各新增一位隨機不可知密碼的member展示執行者，兩待審任務指派給他，管理者可真核准／退回且不繞過自審限制。其餘owner不改。
- 38個上輪模板新增節點日期食品前移5日、電子10日，原有任務日期不改；新示例不是實際調查或檢驗結論。沒有刪除節點／專案／報告／附件。
- 隔離測試初次2fail1pass（日期輸入需ISO字串、模板標題比對已修），最終3/3 exit0，補活躍phase後相关3/3 exit0。涵蓋真狀態／回報版本／前置阻擋／Gate、預覽回滾、第二公司遇未知狀態時整筆回滾、冪等／關閉模式拒絕。獨立審查Ready to apply，未重跑未改UI全量。
- primary預覽回滾後停止API一致DB/files備份，再apply、補活躍phase；原row ID／非授權欄位、原task日期、food已核准Gate、files SHA／env／DB容器保留。8reports／4notes／2users／68audit新增，瀏覽器正常登入另生1session。重跑preview全already_applied。畫面實見完成率12%、完成2／進行1／待審1、等待前置任務；ignored `.superpowers/ui2-live/` 保存證據及備份。
- 工作區市場與配方可展示完整狀態，配方設計→紀錄可示範退回重送／審核。使用者試用未代勾；P2d未啟動，D50 main push。

### UI2追加 既有專案補齊 — ✅ 資料交付

2026-10-09使用者直接要求將模板套用現有專案，並明確回答「移除waa」。[短計畫](superpowers/plans/2026-10-09-ui2-project-fill.md)；僅維護脚本，沒有新增套用UI或改API／schema。

- 主食罐新增20節點、沿用市場與配方：現在5階段／17任務。連接器新增18節點：現在5階段／14任務，電子NPI中筆電專屬任務改為連接器結構／模具／端子與接觸電阻。新日期2026-10-09起算、todo／pending，不假造完成。
- waa確認僅1個project root，依授權備份後移除專案及root；未刪其他內容。新增38nodes／10gates／19dependencies／3audits。除明列waa兩row，其他舊row欄位逐值保留，files SHA及原env相同、DB容器不變。
- 隔離測試4/4 exit0：保留原值與冪等、預覽回滾、waa變更拒絕並整筆回滾、mode off拒絕。一位唯讀獨立審查Ready to apply；關聯筆記/附件拒刪分支由程式保護，未另做直接測試。不重跑未改動UI/API全量。
- primary預覽、停止API一致DB/files備份、apply一次成功，再預覽already_applied無新增；ready200。證據與私密備份ignored `.superpowers/ui2-fill/`。維護脚本預設回滾，需顯式--apply，stable audit marker防重複。
- 使用者試用未代勾，P2d仍後移。D50本輪維護脚本與交付紀錄隨main推送。

### UI2 產業模板與本機展示公司切換 — ✅ 工程交付

**範圍／授權**：D68明確選本機展示一鍵公司切換，D65精簡流程，短計畫在`superpowers/plans/2026-10-09-ui2-showcase-library.md`。12套五產業範本、搜尋／分類／卡片／階段預覽、另存公司模板與真實建立專案。公司模板補階段／任務摘要；左下選單真後端session輪替與舊token撤銷，指定五公司admin、預設關閉／loopback限定、专用展示身分標示。一般頁即切換，有表單先確認可取消；卸載舊公司畫面與清快取。

**測試（2026-10-09）**：核心RED2fail（缺catalog／switch）後API定向6pass，再增四角色拒絕。一次完整API351pass、1fail（health的舊端點精確清單）、7條件PG skip，exit1；加入新路由後showcase+health共22pass exit0。Vitest完整170/170，最後相關showcase/library9/9，build exit0。E2E完整18pass/2fail exit1（mvp取電子模板第一筆，如今新範本排序在前且要求開始日）；改按原模板名稱選，保留原隔離斷言，mvp+showcase1280/375共4/4 exit0。未冒稱第二次全量全綠；無migration／附件變更，未重跑PG及附件故障矩陣。ignored證據`.superpowers/ui2/`。

**驗證／審查**：瀏覽器真匯入、建立專案含10task/Gate、五公司輪替、取消保留表單、舊token401、跨公司404、切回原專案逐值相同，刷新保留展示身分。桌面1280／手機375截圖實看，無pageerror／非預期console。一位唯讀獨立審查Ready to merge；小項固定12標籤已改為動態結果，無剩餘阻擋。

**發布／保留**：15173停止API後備份DB+files與env，更新API/web；只增3組公司、5個專用帳號、12模板／219節點／12稽核，重跑初始化全0。全部原rows/欄位、files SHA、原env逐值相同（只增PF_SHOWCASE_MODE=true），DB容器ID未變，migration0004未改。health/ready與web200，實際CSS/JS與最終build逐bytes相同。隔離acceptance down不-v，volume保留，不seed。無新增假專案、Demo不改，P2d未啟動；使用者試用仍未代勾。

### UI1 前端介面對齊 — ✅ 工程交付

D67指定優先對齊Demo，P2d後移。依[短規格／計畫](superpowers/plans/2026-10-09-ui1-demo-alignment.md)完成252px暖灰側欄、品牌／分組導覽／可捲專案清單／真實使用者、米白深綠視覺與本機中文字體／serif標題；主區獨立捲動，手機收合導覽與Escape／選頁焦點返回。總覽真統計／專案進度卡、我的任務篩選列表、工作區節點分區／麵包屑／操作與分頁／下一層卡片，以及紀錄、時程、模板、審核、稽核共用卡片與工具列。保留API、權限、Gate、FS、日期確認與所有既有操作。沒有新增假指標、Demo切換身分或未交付模組入口。

**驗收（2026-10-09）**：一次完整Vitest為165 passed／2 failed，僅新常駐側欄造成舊全頁文字selector重複；縮小語意範圍後受影響App／workspace 78/78通過（exit0），其他89項沿完整回歸證據，非宣稱第二次全量167。build最終exit0。一次完整E2E 15 passed／3 failed（exit1）：兩項仍查header img，一項手機測試開側欄後未關就點主區新增；適配後相關health／mvp／workspace／visual 11/11 passed（exit0）。新視覺走查另補空／延遲載入／503重試／真logout後401失效，1280／375共2/2 passed（exit0）。原業務、公司權限、資料保存、回報、Gate、FS與拖拉改期斷言均保留；沒有把首輪失敗當產品RED。UI1無後端變更，未重跑PG／附件故障矩陣。

**畫面證據**：獨立Demo origin `127.0.0.1:18005`，正式走查僅隔離15175；兩者1280／375的overview/workspace/timeline/tasks/records對照PNG位於ignored `.superpowers/ui1/`，另有正式templates/reviews/audit/navigation與空／載入／錯誤／登入失效。已實看，修正長名稱側欄重疊、標題操作列與手機焦點；頁面／主內容無橫向overflow，時程／相依圖保留內部捲動。管理頁截圖等待真資料載入完成。測試的console僅允許明確401及刻意503，既有業務E2E精確允許Gate/FS預期錯誤，其餘為0。

**獨立審查**：唯讀`ui1_review`依WORKFLOW §14檢查diff與Demo／正式截圖，修正手機導覽focus後窄複核，結論 **Ready to merge**、無阻擋。沒有重跑另一套全量，沒有冒稱使用者簽核。

**限制與下一步**：對齊主要布局／色彩／資訊層級，並非Demo全部功能或逐像素一致；手機採單欄與日期表單。P2c的進階排程、自訂回報欄位與P2d文件／AI／營運仍延後。使用者UI1視覺與操作試用仍待簽核。15173已web-only更新，CSS/JS實際回應與最終build逐bytes一致，health/ready200。前後所有原row/欄位值、files SHA、env相同；API/DB容器ID、映像與啟動時間皆未變。不seed、不重啟API/DB。隔離acceptance已down不-v，雙volume保留；自啟Demo18005已關。


### P2c 時程、模板與前置 — ✅ 精簡範圍工程交付

**授權／範圍**：D65精簡流程、D66 A；使用者追加「完成後推上git」。[短規格／計畫](superpowers/plans/2026-10-09-p2c-schedule-workflow.md)。已完成模板CRUD/copy、多層task/頂層phase與Gate、相對日建立專案、日週月時程/桌面拖移拉伸/手機鍵盤日期、同專案硬性FS與安全阻擋、可見簡單相依圖。改期不順延，SS/FF/延遲/關鍵路徑/子樹套用等明列延後，不宣稱完整Demo一致。

**實作／審查**：`6c45e51..5992ce6`；後端`8804643`、UI`d1adbbc`、整合`5992ce6`。一位獨立審查Ready to merge: Yes，未發現展示主流程／資料／基本權限阻塞。phase層級沿既有create_node；新增一次安全blocked批查，query固定cap由7變8，保留成長前後一致與恰一次dependencies批查斷言。

**實測結果**：後端先取得核心RED4fail1pass→target158pass3optional skip，最後核心8pass；專用PG0003→0004保留值/約束1pass與並行4pass。UI167pass/build0。候選完整驗收一次：mandatory三個fresh PG stages 6pass（P2b1/P2c1/races4）；API344pass7conditional skip2舊capfail→query target2pass；其後Vitest167/build0；完整E2E15pass1舊模板首項排序假設fail→nested Gate target1pass。原fullverify exit1保留，不偽稱單次全GREEN，依D65只驗修正部分。7skip中6由mandatory PG另實跑，P2a舊migration1維持歷史證據未本輪重跑。

**展示／保存**：10task模板建立/copy、跨年日期、日週月、drag/resize實際變更、手機鍵盤改期/重載、FS done/skipped解鎖/Gate仍擋/20task循環拒絕、readonly/跨公司/hidden前置固定訊息；1280/375無頁面overflow及非預期HTTP/console/pageerror，parent實看兩寬度時程detail。無seed stop/start完整project/workflow/dependency snapshots相同。acceptance與p2c-backend容器已down不-v，各files/pgdata雙volume及專用DB保留。

**證據**：ignored `.superpowers/p2c/` backend-red/target/final-target/pg、ui-vitest/build、full-verify（首次fail）、query-targeted、vitest/build、e2e-full、workspace-targeted、persistence、final-*及schedule/dependencies screenshots。mandatory DB `p2b_test_f172f1ebf04f48b4b673547e6e81f266`／`p2b_test_3453be12b6894c05a7a15b063c9da72e`／`p2b_test_ea31ef747c8c46aba1e1f4fe872aa6af`保留。primary已備份後保留資料升至0004，使用者簽核不勾。

**交付部署**：ff-only main，依D65不重跑main全量；15173停止API後`primary-before.sql`+`primary-files-before.tar`成套備份、原值snapshot及私密env/SHA保存；不seed升`20261009_0004`，全部原表欄位/row值與files SHA/env相同，web/health/ready200、10001:10001/0700（`primary-preservation.txt`）。未跑primary業務測試。階段末更新README/指南/清單/看板，依指示推main，未代勾任何使用者簽核。

### P2b 回報與協作 — ✅ 工程交付完成

**授權**：使用者於P2a完成後指示「繼續進行」（D58），接續路線圖B1–B6；不是P2a試用簽核通過或新產品規則已核准。

**本次交付**：[完整spec定稿](superpowers/specs/2026-10-08-p2b-collaboration-design.md)。核對既有reports／status／audit API、permissions、models、Compose與README F6／F11。核心差異是Report POST不改status，但status PATCH可直接done；D59使用者已選A：送出review→核准done／退回doing，新版本保留歷史，API不可繞過；D60已選A，管理員／實際專案擁有者可在有送出權時明確送出並確認並保留稽核；D61已選A：指定協作人員與協作部門主管，指定節點不繼承；D62已選A：筆記作者修訂不刪、單檔10 MB及完整附件保留規則；D63已選A，固定回報欄位與管理者單任務生命週期操作，自訂欄位延P2c、跳過申請／覆寫另列後續。

**獨立文件審查**：review_finalized_docs（spec）與review_task1（plan品質）均Approved。第1輪提出commit結果不明不能刪成功附件、nonroot新files volume可寫初始化兩Important，已補spec§7.2／§9及Task4故障／fresh-volume驗收並複審關閉；舊待定措辭同步修正。此為文件審查，不是G3授權或產品GREEN。

**狀態**：D59–D63均已定案為A；完整spec與八Task plan依D64核准，G3完整隔離基準API182passed1skip／Vitest96／build0／E2E9(19.3s)全部exit0，專用PG另1passed(0.44s)。primary已pg_dump備份及env指紋存ignored .superpowers/p2b/，未改業務資料。主checkout feature已完成旅程RED及Task1–8雙獨立審查Approved，完整隔離驗收GREEN；G4文件Important已修正，階段UI說明Minor已修正，G4兩位審查Ready to merge: Yes。

| Task | 範圍 | 狀態 | 測試／commit |
|---|---|---|---|
| 1 | 保留資料migration與共用協作policy | ✅ | `a76bdb1..a7102e8`；RED12failed4passed1skip exit1→目標85passed2skip／全API197passed2skip exit0；專用PG1passed/0.36s。修正輪1補歷史review與非空父子／部門保留：SQLite7passed2skip、真PG1passed/0.33s exit0。spec／品質複審均Approved，原驗收缺口關閉，無剩餘finding。 |
| 2 | 回報審核與task生命週期 | ✅ | `b71e59e..575b270`；RED36failed8passed exit1→GREEN44passed exit0；trim補強RED1failed→GREEN7passed；最新全API251passed3skip/189.95s exit0（先前244passed結果另存）。真PG API送審／確認／退回各一成功一409且audit恰一次：1passed/0.94s exit0；spec／品質均Approved，無finding。 |
| 3 | 筆記、協作管理與紀錄查詢 | ✅ | `07661ad..134955d`；RED19failed exit1→目標48passed、全API274passed4skip exit0。audit名稱對齊note.update後目標23passed／真PG2passed（回報、筆記／協作各一成功一409）；cursor修正輪1 RED2failed1passed→51passed exit0。spec／品質複審Approved，原極端日期cursor Important關閉。 |
| 4 | 持久化附件與故障恢復 | ✅ | `333964e..a8b0e2b`；RED23failed（另部署2／長header1／故障補強2）exit1→目標80passed；最終附件34passed／API313passed5skip／真PG3passed均exit0。10MB201+SHA一致，11MB Nginx/API413；新volume10001:10001/0700、無seed重啟note/file/SHA/quota不變，live恢復拒絕、offline兩次成功無重扣。spec／品質Approved，無finding。 |
| 5 | 任務紀錄、回報與協作UI | ✅ | `ac13673..5f4b9b2`；初RED6fail→122passed；focus補強RED1fail22pass→23pass；修正輪1 legacy／附件假空RED4fail26pass→最終126passed/build0。隔離1280/375鍵盤、391字筆記/74字檔名、下載、自核／取消、雙角色送審退回重送v2確認、協作撤銷舊cursor/download404、無overflow/非預期console；parent實看新版及fix1圖片。雙審複審Approved，兩Important關閉。 |
| 6 | 審核中心與安全稽核API | ✅ | `96cb223..1174932`；RED17fail1pass exit1→首組35passed／最終目標37passed23.06s／全API333passed5skip268.68s exit0。覆蓋他人最新可審、D60不擴Gate、node-nulladmin、safe actor／payload與hidden references、cursor條件／極端時間／混合key穩定分頁／固定querycount。spec／品質均Approved，無finding。 |
| 7 | 審核中心與稽核UI | ✅ | `c0c496d..88543a7`；RED8failed exit1→145passed；fix1未知事件prototype名稱RED3failed19passed exit1→148passed/build0。隔離1280/375、鍵盤退回重送確認、Gate、安全稽核篩選與導覽、readonly權限，無overflow／非預期console。spec／品質複審Approved，Important已關閉。 |
| 8 | 隔離整合、恢復、文件交付 | ✅ | `c764dc7..46859e1`；前移旅程RED2failed→GREEN；verify能力RED2failed→部署39passed。完整verify PG1+3/API337pass5skip/Vitest148/build0/E2E13pass/cleanup0，exit0；no-seed重啟DB/檔案/SHA相同、offline pending恢復與quota正確、skip護欄非零。文件權限誤述fix1雙審Approved，Important關閉。 |

**G3證據**：ignored .superpowers/p2b/g3-baseline.txt（verify --keep-running exit0），g3-postgresql.txt（專用DB p2a_migration_a1d830b188e1，1passed/0.44s exit0）。acceptance15175保留供逐Task；primary15173不跑業務測試。primary-before.sql為本次唯讀pg_dump備份、primary-env-sha256.txt為設定指紋，均不進Git、不輸出內容。

**Task1證據**：ignored `.superpowers/p2b/task1-{red,target,full,pg}.txt`、`task1-fix1-{sqlite,pg}.txt`及`task8-journey-red.txt`。專用PG `p2b_test_483189ad3e04413f88b65bbf091b3b9d`、`p2b_test_62fcbfab1bbe43e9b794452cab619d49`保留；只在專用DB驗證，不改primary。DB兩連線pending唯一性已驗，業務送審／審核競態屬Task2。

**Task2證據**：ignored `.superpowers/p2b/task2-red.txt`、`task2-green.txt`、`task2-trim-red.txt`、`task2-extra-green.txt`、`task2-full-final.txt`、`task2-pg.txt`。專用PG `p2b_test_6eaceb7f744643179b4cda6ebf26ce9f`保留；真PG於trim小修前驗證，最新全API包含trim。非空附件暫明確拒絕，Task4接完整關聯；E2E於Task8完成，現在不宣稱已交付。

**Task3證據**：ignored `.superpowers/p2b/task3-red.txt`、`task3-target-final.txt`、`task3-full.txt`（稽核名稱修正前）、`task3-final-target.txt`、`task3-final-pg.txt`及`task3-fix1-{api-red,green}.txt`。最終專用PG `p2b_test_42cc6517b0ff41778250b83db08a2824`保留。中間誤替換edited_at的失敗log保留且已修復，不算功能RED。cursor純解析修正後跑51項目標，不冒稱HEAD全量／PG重跑。Task5最新回報以受控self分頁取得，未載完不判未回報；紀錄UI仍分頁追加。

**Task4證據與資源**：ignored `.superpowers/p2b/task4-{red,deploy-red,length-red,hardening-red,hardened-green,full-final,pg-final}.txt`及`task4-volume-*`／`task4-recovery-*`。專用PG `p2b_test_38bf2081c79745afa0c3fad532c25d73`保留；新隔離stack `projectflow-p2b-task4`運行於15177/18004，files及pgdata兩volume保留，私密task4.env不進Git。最後映像重驗原SHA、ZIP拒絕、舊volume可寫；不可寫root503且不fallback/chown。primary／原acceptance無業務測試。

**Task5證據**：ignored `.superpowers/p2b/task5-{red,green,build,ui,review-ui}.txt`及`task5-fix1-{red,green,build,ui}.txt`（126passed/build0）。新版`task5-1280-card.png`／`task5-375-attachments.png`／`task5-rejected-375.png`、fix1 legacy／read-error圖片由parent實看；原fullpage及修整前圖片保留。UI已更新隔離15177，primary尚未更新；回報卡掃self各頁，紀錄獨立分頁，成功後read失敗只GET重試。

**Task6證據**：ignored `.superpowers/p2b/task6-red.txt`、`task6-green.txt`（35passed首組）、`task6-target-final.txt`（37passed最終）、`task6-full.txt`（333passed5skip）。未改schema／交易，專用PG條件測試本輪skip，完整PG整合由Task8強制執行。無容器部署／primary業務測試；Task7先更新隔離API映像再實測。

**Task7證據**：ignored `.superpowers/p2b/task7-{red,green,build,ui}.txt`、`task7-ui-results.json`與`task7-fix1-{red,green,build,ui}.txt`。parent實看桌面審核、手機稽核與fix1未知事件圖片；修正採Object.hasOwn，未知事件保留為「其他業務事件」，無原始payload洩漏。隔離15177已更新；primary未變。

**Task8證據**：ignored `task8-full-verify.txt`、首跑失敗`task8-full-verify-audit-selector-failure.txt`、`task8-verify-red.txt`／`task8-deployment-green.txt`、`task8-pg-skip-guard.txt`、`task8-restart-recovery.txt`／`task8-restart-values.json`／`task8-recovery-quota.txt`。專用PG `p2b_test_326c1ff802db42519aeb33f368efee17`保留；acceptance容器清空且雙volume保留。parent實看375完成卡detail；所有業務測試只在隔離，primary未升級。

**G4證據**：整體 `ef39cdd..4d94d27` spec／品質雙獨立Ready to merge: Yes。文件Important與phase說明Minor均關閉；phase回歸RED2failed20passed→Vitest150passed/build0（`final-phase-{red,green,build}.txt`）。重新fetch origin/main仍`c0284f6`，無來源不明遠端變更；main維持`ef39cdd`等待ff-only。

**G6交付證據**：main `4d0323e`完整`g6-full-verify.txt` exit0：專用PG `p2b_test_ce7b5daefeb94069beaeb4a3d77ff646` migration1／競態3、API337pass5conditional skip／Vitest150／build0／E2E13pass34.0s。phase四組只讀UI、parent實看readonly375detail；`g6-phase-ui.txt`／cleanup／final容器與volume證據保留。primary停止API後`g6-primary-before.sql`與私密env指紋、原值snapshot保存；升級不seed，migration0003／health-ready200／files10001:10001/0700、before/after原有欄位與row值全相同、env未變（`g6-primary-preservation.txt`）。首次健康probe誤用不存在/live端點404，改正文件端點後通過，非產品錯誤。acceptance及Task4隔離容器已down無-v，兩組雙volume與專用DB保留。

**工程驗收（全部完成；不含使用者簽核）**
- [x] D59–D63角色／公司／可見性與無副作用矩陣。
- [x] 送審、退回重送、確認、自核及重開／略過完整流程與Gate。
- [x] 協作撤銷、筆記作者修訂、本人列表與安全紀錄／稽核。
- [x] 附件上限／配額／格式／SHA、軟刪與回報保護、故障恢復。
- [x] 真PG舊資料升級與並行競態、DB／files無seed重啟保留。
- [x] 1280／375／鍵盤／console、完整回歸、雙獨立審查與G6部署。

以上工程項目不是使用者試用簽核，P1c／P2a簽核維持未勾選。

### P2a 完整任務操作 — ✅ 工程交付完成

**本次授權（2026-10-08）**：使用者同意P2a規格與計畫及D56推薦規則，授權實作至驗收發布；既有資料保留、隔離測試、使用者簽核維持未勾選。

**意圖**：使用者明確要求开始進行先前建議的四階段，正式版需有接近Demo且能實際操作的功能，不只後端與測試完成。先聚焦可見的工作區與任務管理；正式軌流程、API公司／角色權限、單一寫入者及隔離驗收維持。

**唯讀盤點**：現有project/node可建立、讀取與更新status；尚無完整metadata編輯、Node起迄日期、工作區總覽與我的任務。Demo的pageOverview／pageMyTasks／openEditor可作功能參照，不搬入假ERP／備份／通知數據。日期需要正式migration，不重設資料庫；未改產品／測試、未新增依賴或啟動feature分支。

**2026-10-08文件交付**：[spec](superpowers/specs/2026-10-08-p2a-task-workspace-design.md)與[配套plan](superpowers/plans/2026-10-08-p2a-task-workspace.md)已依D56定稿。D56已由使用者明確核准，G1／G2定稿；G3本次API基準80 passed／1 warning／29.09s，exit0；完整verify因npm缺失exit1，未進Compose及E2E。

| Task | 範圍 | 狀態 | 測試／commit |
|---|---|---|---|
| 1 | 日期migration、metadata／指派API | ✅ | b917edc..e992a8c（plan補正4b1f1f1）；RED30failed19passed/exit1→目標GREEN49/exit0；完整API120passed1skip/65.61s/exit0。真PG専用DB另跑1passed/0.18s/exit0（ID/status/parent/owner/dept/audit保留、日期null/持久化/CHECK）。review_task1獨立spec及quality Approved，無issue |
| 2 | 多層Gate防繞過 | ✅ | cbe3586..92d798d；RED21failed18passed/39.70s/exit1；targettodo補RED12failed12passed18deselected/21.90s/exit1→GREEN51/50.07s；最終API155passed1skip3warnings/104.59s/exit0。review_task1獨立spec及quality Approved，無issue |
| 3 | 可見總覽／本人任務API | ✅ | 5fb2c35..417fa42；RED26failed/24.59s/exit1→GREEN26/25.26s/exit0；完整API182passed1skip/123.91s/exit0。review_task1独立spec/quality Approved無issue；30專案增量仍最多5 SELECT |
| 4 | 導覽與多層工作區 | ✅ | 8ec231a..ae1c366（實作5eb4d0a）；RED4failed56passed/exit1→GREEN64；独立review Important登出中node導航中斷request，補RED5failed8passed後fix ae1c366，最終Vitest69passed/build0，review_task1複審Approved。1280/375 nooverflow/console0/pageerror0，鍵盤/四層/孤兒/日期/下一層/skipped通過，主代理亦已看最終截圖 |
| 5 | 新增／編輯表單、總覽與我的任務 | ✅ | c39246f..a5d1594（實作adb70ce）；RED5failed69passed/exit1→GREEN94；雙獨立審查Important舊reload清新表單草稿，fix1 RED1failed18passed/exit1→最終Vitest96passed/3.43s/build0，review_task1與review_finalized_docs複審Approved。1280/375表單、鍵盤、本人定位、readonly/nooverflow/console0通過 |
| 6 | 隔離整合驗收與文件交付 | ✅ | 前移RED acf176e..b917edc：workspace1280/375缺導覽2failed/exit1；整合72d9d52..8dc914a。API182passed1skip、Vitest96、build0、E2E9、cleanup0，真PG1passed與無seed重啟完整detail相等。review_task1獨立spec與review_finalized_docs品質均Approved；新增通過案例如實記為回歸 |
| G4 | 完整feature整體審查 | 🟢 | acf176e..8dc914a；兩位reviewer均Ready to merge: Yes，無Critical/Important/Minor或未決plan-mandated問題 |

**G3恢復（2026-10-08）**：使用者重啟後指示繼續；WSL2.7.13／Docker29.8.2 engine可用。fetch + ff-only已最新；完整隔離verify（keep-running）API80／Vitest56／build／E2E6 exit0。D57解除，正式開工。

**環境補裝（D57，歷史）**：使用者選擇本機補裝；Node24.20.0、Docker Desktop4.94.0／Docker29.8.2／Compose5.5.1與Playwright Chromium已安裝，npm ci exit0。Vitest56（12.32s）及build exit0。WSL一般安裝因管理員權限失敗，已透過UAC啟動管理員安裝（winget Microsoft.WSL 2.7.13），StagePackageAsync仍未結束。Docker引擎log明確回Virtual Machine Platform not enabled；已以管理員DISM啟用VirtualMachinePlatform /all /norestart，exit3010需重啟。未自動重啟Windows，Linux引擎尚不可用。獨立文件複查review_finalized_docs Approved。

**G3檢查（2026-10-08）**：初始working tree乾淨；fetch + merge --ff-only origin/main已是最新`ff0cdbe`。已以本機Python3.13建立ignored api/.venv並安裝requirements.lock（exit0），API `80 passed, 1 warning in 29.09s`（exit0）。`deploy/verify.py --keep-running`因找不到npm退出1，未啟動服務。PATH、標準安裝路徑、解除安裝登錄及服務均未找到Node／Docker；WSL回報未安裝。G3未通過，沒有開feature、沒有寫Task測試／產品、没有功能RED證據；未碰.env、DB或volume。D57已授權本機補裝，正在處理。

**工程驗收清單（Task6已實跑；使用者簽核另列）**
- [x] 四層節點新增／metadata編輯／日期清除與重新登入持久化。
- [x] 權限矩陣、跨公司隔離、readonly-owner與稽核原子性。
- [x] 可見範圍統計、我的任務搜尋／狀態篩選／跨專案定位。
- [x] 深層Gate阻擋與核准，既有工作流／隱藏父節點相容。
- [x] 真PostgreSQL migration保留資料、隔離重啟與完整回歸。
- [x] 1280／375走查、獨立審查、文件更新；使用者試用另簽核。

**Task6實證**：ignored .superpowers/p2a/task6-verify.txt、task6-postgresql.txt、task6-restart.txt／task6-restart-values.json、task6-cleanup.txt、task6-workspace-{1280,375}.png（實作者與主代理已看）。專用PG DB p2a_migration_b12b66168c4c保留；重啟project 6a159d13-f536-4585-8e17-183c55d39eba完整detail相等，start=null/due=2026-10-15/owner/dept/status不變。初次E2E4failed為測試導覽/安全投影/預期401契約調整；PG首次sys.path設定失敗、verify首次E2E TypeScript型別建置失敗均已修正，未當功能RED。最終verify exit0、acceptance容器空且volume保留。README/指南/試用清單已更新；G6 main回歸與15173部署通過，詳見交接。

**Task5證據與審查補核**：ignored .superpowers/p2a/task5-red.txt、task5-fix1-red.txt、task5-fix1-green.txt、task5-fix1-build.txt、task5-ui-results.json及form/workspace-{1280,375}.png。主代理已實看兩寬表單。普通editor無指派、日期清除、取消不寫、鍵盤提交、跨專案定位通過；每寬3筆未登入auth/me 401為預期，其餘console/pageerror為0。第一輪修正已關閉舊reload競態；主代理重跑96passed與build0保存證據。review_finalized_docs另補足Task1–4第二位品質審查，均Approved、無新增issue；各Task先前review_task1的spec及quality結論保留。

**Task4走查證據**：ignored .superpowers/p2a/task4-ui.mjs、task4-ui-results.json、task4-1280.png／task4-375.png。主代理已實際view_image；desktop4欄/mobile1欄，長名稱可換行。審查登出race Important已在第1修正輪關閉，無遺留。

**Task1補正與證據**：plan漏列精確路由測試api/tests/test_health.py，依已授權新增端點同步必要測試，先獨立commit Plan: fix（4b1f1f1），保留精確斷言，沒有產品範圍擴充。RED/GREEN log位於ignored .superpowers/p2a-task1-*.txt；真PG DB p2a_migration_6ef86f59f7ce495d902fa6be98c3f511保留，未降版現有acceptance。

**執行注意**：現有Report submit只新增TaskReport及稽核，不修改Node.status；不可把P2b狀態轉換混入P2a。日期採nullable DATE；新規則與權限已依D56核准。Demo與tests/保持原樣。


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
> **刻意沒改的地方**（spec §7，或決定維持現狀）
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
> - 給 D7 的觀察：W1 之後，有硬性前置的葉任務（例如 `t3013`）在卡片上就看得到醒目的「回報完成」，送出時被擋下會遺失草稿，所以 D7 的情況會更常發生。使用者決定 D7 時可以列入考量。
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
12. **D3（2026-10-01）**：使用者指示「完成後上傳到GIT」。W1 完成 G5 合併與 G6 收尾後，執行 `git push origin main`（不 force，也不 push 其他分支），然後更新「▶ 現在」的「遠端」列。這次授權只限 W1。
13. **Task 1 修正輪偏離 plan（D14）**：`.rcard .rc-main` 是 `flex:1 1 240px`，不是 plan Step 3 的 `flex:1`。原本的寫法 flex-basis 是 0，`.rc-row` 的 `flex-wrap:wrap` 永遠不會換行，375px 下文字欄只剩 118–141px。Task 2 和整體審查都**不要改回去**。D14 已決定接受（2026-10-01）；plan 不另外同步，以這一條為準。
14. **Task 2 必驗**（Task 1 審查留下的待驗證項目）：
    - 按鈕點擊流程：阿明送出；力瑜確認和退回。已列在驗收清單。
    - 卡片在實際頁面中的位置：375px、768px，以及桌面寬度下 AI 面板開和關。
    - **桌面高度**：節點頁的 `.main` 是 `overflow:hidden`，`.view` 不會捲動，所以 F11 的紀錄分頁本來就會被截掉（§5 W1-T1-m6）。Task 2 接上回報卡、葉任務預設進紀錄分頁之後，要在 1280×720 實測回報歷史、筆記、附件能不能完整看到或捲動得到，長摘要（約 15 行）也要測。**D15 已決定在 W1 修**（2026-10-01）：Task 2 的修正輪讓節點頁的紀錄、文件、資料、成員分頁改成整個主區域可以捲動（和手機版一樣，標題和回報卡跟著捲上去），看板、時程、相依圖維持原樣，並附測試。已在 `8103646` 實作：`#main` 加的是 `.vscroll`，只設 `overflow-y:auto`。沒有用原本草擬的 `.scroll`，因為它的權重比手機版的 media query 高，會把手機版的 `overflow-x` 改成 auto。`enter()` 換節點時也會捲回頁首，手機版一樣。
15. Task 1 審查留下的 Minor 是 W1-T1-m1–m5（§5），整體審查時判斷是否要在合併前修。m1（`const st ={` 少一個空白）是編輯工具把 new_string 結尾的空白去掉造成的，建議在整體修正時順手改回。之後用編輯工具替換時，new_string 結尾不要留空白。
16. **D16（2026-10-02 決定）**：卡片上的成果說明最多顯示約 6 行，超過的部分在卡片內捲動，完整內容在紀錄分頁的「回報歷史」。只改 CSS（`.rcard .rc-sum`），放在 Task 2 修正輪 1，附測試。看板、時程、相依圖仍然維持 D15 的「主區域不捲動」。已在 `c4e9e36` 實作：`max-height:10.2em;overflow:auto`（行高 1.7 × 6 行）。
17. **D17（2026-10-02 決定）**：原本是子任務、而且停在「紀錄」分頁時，新增第一個子任務後自動切到「看板」，直接看到新的子任務。從新增子任務對話框「改用模板 / 過去任務…」或標題區「套用模板」建立子任務，也算在內。放在 Task 2 修正輪 1，附測試。已在 `c4e9e36` 實作：判斷寫在 `pageNode()`（`ui.leafPage` 記住上一次畫的子任務頁），所以所有建立子任務的入口都適用；`renderMain()` 改成先產生內容，再依改過的分頁切換捲動方式。
18. **Task 2 審查後實測失敗（品質審查 Verify 1，轉 Important）**：1280×720 下，在 `t301` 的紀錄分頁捲到 300 後切到「相依圖」，主區域停在 43px，麵包屑被切掉，而且捲不回去。原因是相依圖下方的圖例說明超出 `.view`，主區域有可捲動的高度，但桌面版這三個分頁是 `overflow:hidden`。這是 D15 帶出來的問題，放在 Task 2 修正輪 1 處理：主區域不能捲動時回到頁首。已在 `c4e9e36` 修好：`renderMain()` 寫入內容後，主區域的計算樣式是 `overflowY:hidden` 時（只有桌面版節點頁的看板、時程、相依圖）把捲動位置設回 0。可以捲動的分頁和手機版維持原本的位置。
19. **D18（2026-10-02 提出，2026-10-02 使用者決定維持現狀）**：卡片上的自訂欄位、退回意見、跳過理由沒有高度上限（§5 W1-T2-m9）。維持現狀，W1 不改；§5 W1-T2-m9 改列 BY_DESIGN。

### W2 部門模型 — ✅

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
| — | 整體審查 | 🟢 等確認合併 | 第 1 輪整體審查（Claude，交接回報）：With fixes，需修執行注意 32 的 4 項，沒有其他阻塞 → 整體修正 `b2f7453`（未指派顯示、卡片負責人不換行、權限表、回報 select 防護）→ Codex 修正後自我再審：Ready to merge: Yes（非獨立審查，依 G5／§11 合併前需確認） | 整體修正加 4 個測試：RED `失敗 4/137` → GREEN `全部通過 137/137`（`.superpowers/sdd/final-fix-report.md`）。Codex 2026-10-05 新鮮重跑 `tests/records.html`：`全部通過 137/137`，console error 0；桌面以 yu／chen／ming 點過看板、時程、成員與權限、我的任務，沒有 `undefined`／`NaN`／`? —`；375px 看板、時程、成員與權限 `main.scrollWidth <= clientWidth`，console error 0 | 137（實際 137） |

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
11. plan:23 要求用 `superpowers:using-git-worktrees` 開 worktree，plan:1164 要求用 `finishing-a-development-branch` 決定合併方式，**這兩點一律以 D2 為準**：在主 checkout 執行 `git checkout -b feature/w2-departments`，不開 worktree；合併照 WORKFLOW G5 用 ff-only。這已經裁決過，不算 Pre-flight 衝突，不需要再問使用者。
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
      - spec 確實要求改變確認人，就是 spec 和測試衝突，依 WORKFLOW §8 停下來問使用者。不要直接改 W1 的測試。
17. **測試環境**（2026-10-05 的狀態，主機是使用者的 Windows 電腦）：
    - 8000 埠被另一個不是這個 repo 的 python 伺服器占用（2026-10-05 是 PID 16860，回應 `{"detail":"Not Found"}`），不要動它。
    - 8001 埠沒有伺服器（PID 24024 已在 2026-10-02 照指示關閉）。照 WORKFLOW §5 第 1 點在 8001 自己啟動，記下 PID，收工時用同一個 shell 關掉。啟動後先用 `curl.exe -s http://127.0.0.1:8001/AGENTS.md` 確認第一行是 `# AGENTS.md`。
    - 2026-10-02 在 `172.22.32.95:8080` 開給同網域同事試用的分享伺服器（PID 27436，服務 repo 外的快照 `C:\Users\User\projectflow-share\`，不是測試伺服器），2026-10-05 實測已經不在了。要重開或更新快照等指示。
    - Browser pane 隱藏時，測試頁的 iframe 寬度會是 0。要測桌面或 375px，用 `resize_window` 設定 viewport；W1 和寬度有關的測試會自己撐開 iframe。
18. **編輯陷阱**：
    - 工作目錄是 CRLF。用 python 讀寫檔案時要加 `newline=''`，否則換行會被改掉。
    - 編輯工具會把 new_string 結尾的空白去掉，W1-T1-m1 就是這樣造成的。
    - 改完用 `git diff -w --stat` 和 `--stat` 比對，確認沒有意外的空白變更。
19. **補強測試時沒有自然的 RED**：例如整體修正時補的斷言。可以用「變異 RED」證明測試有鑑別力，W1 整體修正就是這樣做的：
    - 先備份檔案，暫時把程式改壞，記下 `#sum`。
    - 改回後用 `cmp` 確認和備份逐位元組相同，**不要 commit 變異**。
20. **D19（2026-10-02 使用者決定「照 spec」）**：`upgrade()` 的 v3 → v4 區塊，模板節點補 `dept` 的順序照 spec §3.4(4)：有 `who` 取其部門 → 否則第一個 `dp`（已轉成 id）→ 再沒有則 `d-rd`，**不用 `TAG_DEPT`**。plan Task 1 Step 8 的 `x.dept = … || TAG_DEPT[x.tag] || …` 以此為準，在 Task 1 修正輪 1 修改並補測試。只限 `upgrade()`：`seed()` 的 `chain`／`mkTpl`，以及 Task 7 的 `applyTemplate`、`nodeToTemplate` 仍照 plan 使用 `TAG_DEPT`。
21. **Task 1 審查補的兩處（plan 漏列，照 plan 自己的規則修，不算新的產品決策）**：
    - AI 風險分析「工作量最重」和 AI 問答「誰／負責／工作量」的 `load[x.owner]` 要排除 `owner === null`，寫法和 `pageOverview` 的 `if (!x.owner) return;` 一致。
    - 採購單「建立驗收任務」（`ds.poTask`）的內聯模板：`dp: ['品保']` 改成 `['d-qa']`，根節點和子節點都加 `dept: 'd-qa'`（Global Constraints 的對應表：品保→d-qa）。
22. **`isHead(uid, id)`**：Task 1 照 plan 寫成 `dept(id).head === uid`，所以 `isHead(null, 沒有主管的部門)` 會回傳 `true`。Task 2、3 呼叫時，`uid` 一律傳使用者 id，不要傳可能是 `null` 的值（例如 `n.owner`）。
23. **D20（2026-10-02 使用者決定「照 spec 字面」）**：`seeTask` 的下層規則只看「任一下層任務 `directSee`」，拿掉 plan Task 2 Step 3 的 `|| (d.owner !== null && ancestors(d).some(…))`。結果：ming 負責 t3012 → 未指派的 N → 指派給小安的 D 時，ming 看得到 D、看不到 N（D 在看板和時程上點不到，這是使用者接受的結果）。上層規則仍然只套用在已指派的任務。
24. **D21（2026-10-02 使用者決定「顯示空狀態」）**：使用者一個專案都看不到時，節點頁的主區域顯示「目前沒有你看得到的專案」，**不要**退回 `projects()[0]` 帶到他看不到的專案；`ctxProject()` 的所有呼叫端（至少 `aiAsk`、`openMinutesConfirm`）要能處理 `undefined`，不可出錯。plan Task 2 Step 4.2 的 `|| projects()[0]` 以此為準。
25. **Task 2 測試補強（spec §7 第 3 項）**：plan 的 8 個測試沒有涵蓋「協作部門含採購的任務」，也沒有任何斷言只靠單一條規則成立（協作人員、負責部門主管、協作部門主管、範圍內審核人），所以在修正輪 1 補上，並用變異 RED（執行注意 19）證明每一條都有鑑別力。
26. **D23（2026-10-02 使用者決定）**：`can('schedule', n)` 對**任務**改成 `canWork(n)`（負責人本人、負責部門主管、專案負責人、系統管理員）。審核人對不是自己負責、也不是自己主管部門的任務不能改時程：任務對話框的日期與鎖定欄位要停用，時間軸拖曳也不行。對**非任務**節點（專案、階段）維持 W2 之前的規則：專案負責人、審核人，以及 member 是該節點負責人時。`deps`、`gate`、`override`（含回報確認，W1 的 `approversFor` 依賴它）都不變。這一點推翻 spec §4.4「reviewer 不變」。
27. **D24（2026-10-02 使用者決定）**：`canNote(n)` 加上範圍內的審核人（`inReviewerScope(n)`）。readonly 一律不能寫筆記。
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

- **來源**：W2 spec 開頭的「拆分」段落原本有 7 項。2026-10-05 使用者先選「精簡版」（D31），後續又確認 W3 不要只內建某個工作流，而要完成可自行新增／編輯／套用工作流的功能架構（D42）。本項目只做：
  1. 工作流模板 CRUD：階段、任務、負責部門、協作部門、前置條件、階段關卡。
  2. 從工作流建立專案：產生專案、階段、任務、前置條件和關卡。
  3. 關卡硬性擋住後續階段（關卡沒通過，下一階段的任務不能開始或完成）。
  - 資料版本：v4 → v5，新增 `db.workflows[]`。
- **不做，延到正式版**：範本指定關卡的核准人、總經理角色、強制通過關卡與略過整個階段、完成報告必附交付物。W2 spec 列為不在範圍內的應收帳款、人員帳號的新增與編輯也一樣不做。
- **spec 怎麼產生**（D31 取代 D9 的完整 brainstorming）：AI 已把 D41 的兩份現有專流轉寫成 `docs/reference/2026-10-05-w3-current-flow-sources.md`，並依 D42 修訂短版 spec `docs/superpowers/specs/2026-10-05-process-control-design.md`。使用者已在對話確認方向。
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
- **下一步**：W5 README 對齊現況（精簡：只改 README §1 快速開始、§2 功能總覽）。W3 feature 分支完成後可 fast-forward 合併到 `main`；使用者已在對話中要求「確認後推上去」。

### W4 F11 遺留問題清理 — ✖（取消，D30）

- **2026-10-05 取消**：展示模式下不花時間在細節。F11-N1（回報對話框可能拋例外）併入 W2 整體修正（W2 執行注意 32）；D4–D8 維持現狀；§5 其餘項目留在 OPEN，延到正式版。沒有開過分支，也沒有 spec 和 plan。
- 以下是取消前的規劃，留作正式版參考。
- **範圍**：§5 中狀態是 OPEN、而且「需使用者」為「否」的項目。依 WORKFLOW G1 的例外，直接寫 `docs/superpowers/plans/<日期>-w4-cleanup.md`。每個 issue ID 對應一個 Task，每項都要附測試。
- **建議優先處理**：
  - `F11-T1-m3`：upgrade 失敗時會靜默覆蓋使用者資料
  - `F11-N1`：回報對話框會拋例外
  - `F11-T7-m3`：spec 要求的附件快照沒有做
  - `F11-T6-m3`：已刪除節點的申請會永遠卡著
  - `F11-T5-m1`：可以重複送出
  - 補測試類：`T2-m4`、`T3-m4`、`T5-m5`、`T6-m4`、`T7-m4`
- **要等決定的**：`T1-m5`、`T4-m2`、`T4-m4`、`T5-m2`、`T6-m1`。這幾項等 §6 有了結論，才能排進 W4。

### W5 README 對齊現況（精簡）— ✅

**2026-10-05 依 D30 精簡範圍**：只改展示時別人會讀的部分，也就是 §1 快速開始、§2 功能總覽（含「已知限制」），以及目錄前面的「給接手的人」段落要和 AGENTS、WORKFLOW 一致。§5、§7、§8 延到正式版。不需要 spec 和 plan，直接在 `main` 上 commit `Docs: …`（沒有 feature 分支時）。下面是原本列出的問題，只處理標「（做）」的：

README 有幾處還停留在階段 0 或 F11 之前的內容，W2 合併後一次整理：
- （做）§1 快速開始沒有提到 full demo 和測試頁。
- （做）§2 功能總覽大多是 petfood Demo 的描述。像「時程（唯讀）」「文件只有標題」「總覽、我的任務未實作」都已經過時，而且缺少 F1–F10 的列。
- （做）§2「已知限制」只適用於 petfood Demo。
- §7 專案結構缺少 `docs/`、`tests/`、`AGENTS.md`、`.claude/`。
- §8 沒有說明 full demo 和正式產品軌的關係。
- §5 `overrides` 的 `target_type` 和 `kind` 語意重疊，而且沒有記載 `restoredBy`、`restoredAt`、`note`。
- （做）目錄前面的「給接手的人：怎麼請 AI 繼續開發」是 2026-10-02 照指示新增的。這段不加編號，所以 AGENTS.md 引用的 §4、§5、§6、§9 編號不變。W5 整理時要一併檢查這段和 AGENTS、WORKFLOW 是否一致。

full demo 定位的文字由 AI 起草，使用者看一次（D12）。

**完成摘要（2026-10-05，Codex）**：
- README 頂部摘要已改成 W1／W2／W3／W5 完成、W4 取消，並說明 W3 先完成功能架構、個別工作流內容由使用者之後自行添加。
- README §1 已改以 `projectflow-full-demo.html` 為準，補上測試頁路徑，並註明 `projectflow-petfood-demo.html` 是階段 0 存檔。
- README §2 已更新 full demo 功能總覽與已知限制，涵蓋節點、看板、時程、前置與關卡、模板庫、部門權限、我的任務／審核中心、文件紀錄、AI 副手、研發營運資料，以及目前沒有後端／多人同步。
- D12 由 AI 起草完成，狀態改為「待使用者可推翻」。

**追加整理（2026-10-05，Codex）**：
- 依指定的深色部署圖版型新增 `docs/projectflow-system-architecture.svg`，用青綠／橘／灰色標示 Demo 已完成、正式版待建、外部整合。
- README §6 改成引用該圖，並分成「目前已完成的 Demo 架構」「正式產品軌尚未完成」「下一步判讀」。
- README §7 專案結構補上 `AGENTS.md`、`docs/`、`tests/`、`.claude/` 與架構圖檔。

### W6 多公司產業範例 — ✅

**目標**：把目前以寵物食品製造為主的單公司 Demo，擴充成五個可切換、資料完全獨立的公司空間，證明 ProjectFlow 能套用到不同產業。

**使用者已確認的方向（D44）**：
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

### P1a 正式版後端核心 — ✅ 完成並發布GitHub main

**授權**：D51已授權做到P1c；D53確認使用者只審成品，中間由AI自行依計畫推進，只有重大範圍／安全／無法照plan的問題才停下來問。

**計畫**：[2026-10-08-p1a-backend-core](superpowers/plans/2026-10-08-p1a-backend-core.md)，取代舊MVP outline Task2。P1a只做後端核心；P1b才接React業務流程，P1c才做整合驗收。

| Task | 交付 | 狀態 | 驗證預期 | commit主旨 |
|---|---|---|---|---|
| 1 | Session登入、資料庫層、Alembic migration骨架 | ✅ Bohr獨立審查第1輪Needs fixes：Alembic config Critical、composite FK與workflow content Important、logout精準撤銷與EOF Minor；修正commit後測試化覆蓋並通過 | RED：依賴安裝成功後，pytest `ModuleNotFoundError: No module named 'app.database'` exit1。GREEN：auth/migration `7 passed, 1 warning`、完整API `15 passed, 1 warning in 2.95s`、pip check無broken、Alembic SQLite smoke exit0。reviewer fix RED：3 failed（logout只撤目前session、Alembic config、migration FK/content）→ GREEN 7 passed | `038ce64..014c0b3`（`ae292e7`實作、`014c0b3`修正） |
| 2 | Project／Department／Node API、`can_view`／`can_work`與audit helper | ✅ Ptolemy獨立審查第1輪Needs fixes：create-node缺寫入權限Critical、readonly-owner可寫與status未限制Important；修正commit後測試化覆蓋並通過 | RED：project/node `5 failed, 1 warning`（routes missing）。GREEN：auth+project `10 passed, 1 warning`、完整API `20 passed, 1 warning`；reviewer fix RED：3 failed（readonly新增、readonly-owner狀態、非法status）→ GREEN project/node `8 passed, 1 warning`、完整API `23 passed, 1 warning in 9.07s` | `5ac1c60..df2e526`（`ae8a1b6`實作、`df2e526`修正） |
| 3 | Workflow建立專案與Gate阻擋 | ✅ Godel獨立審查第1輪Needs fixes：project_owner不能從workflow建立專案Important、override payload測試過鬆Minor；修正commit後測試化覆蓋並通過 | RED：workflow/gate `5 failed, 1 warning`（routes missing）。GREEN：workflow/gate `5 passed, 1 warning`、完整API `28 passed, 1 warning`；reviewer fix RED：project_owner建立回403 → GREEN workflow/gate `6 passed, 1 warning`、完整API `29 passed, 1 warning in 15.54s` | `ca6f902..c8c806b`（`a7e7291`實作、`c8c806b`修正） |
| 4 | Report、Audit API與真PostgreSQL migration／seed驗收 | ✅ Volta獨立審查No findings；確認report route、audit scope、SQLAlchemy URL修正與Demo無diff | RED：report/audit `2 failed, 2 passed, 1 warning`（report route missing）。GREEN：report/migration `7 passed, 1 warning`、完整API `34 passed, 1 warning in 24.91s`、Vitest `6 passed (6)`、build exit0、Playwright `4 passed`；Compose API rebuild healthy，container內Alembic PostgreSQL upgrade head、seed exit0，HTTP login/me/projects smoke 200且看見「成貓主食罐正式版」 | `995b7b8`；`P1a task 4: add reports audit and database acceptance` |
| G4 | 整體審查與修正 | ✅ Linnaeus整體審查第1輪With fixes：reviewer可核准不相關gate Important；修正後scoped re-review No findings，Ready to merge: Yes | RED：`test_reviewer_cannot_approve_unrelated_gate` 讓chen核准yu的不相關gate回200，`1 failed, 6 passed, 1 warning`。GREEN：workflow/gate `7 passed, 1 warning`、完整API `35 passed, 1 warning in 16.10s`、Vitest `6 passed (6)`、build exit0、Playwright `4 passed`、Compose PostgreSQL migration／seed／HTTP smoke通過、Demo diff exit0 | `0c9fe06`；`P1a G4 fix: scope gate reviewer approval` |

**P1a驗收**
- [x] 登入／登出／me端點使用HttpOnly `pf_session`，不能用前端公司參數切換公司。
- [x] Alembic migration建立organization-scoped核心表；業務資料都有`organization_id`並由session限制。
- [x] 種子資料至少兩家公司、不同使用者／部門／專案／節點／工作流。
- [x] Project、Node、Department、Workflow、Gate、Report、AuditLog API都強制公司隔離與後端權限檢查。
- [x] 猜測他公司project/node/workflow/report/audit ID不可讀寫。
- [x] pending gate不能被直接status API或override payload繞過。
- [x] API pytest、React Vitest、production build、P0 health E2E均通過；README／正式開發指南／PROGRESS更新並審查。

**執行注意**
1. 計畫中的SQLAlchemy／Alembic版本是2026-10-08依PyPI查得後選定的鎖版；執行時若相容性失敗，需先修plan或記D，不可改用`latest`。
2. P0 Compose刻意不暴露DB host port；seed實跑預設在API container內執行，不為seed臨時開DB對外埠。
3. P1a測試可用SQLite暫存DB檢查路由與權限，但完成驗收必須在真PostgreSQL跑migration與seed。

### P1b 正式版 React 核心 UI — ✅ 完成

**授權**：D51已授權做到P1c；使用者2026-10-08指示「開始實作」，確認P1b計畫並進入G3。Pre-flight：API `35 passed, 1 warning in 29.36s`、Vitest `6 passed (6)`、build exit0、Playwright `4 passed (1.0s)`，各exit0；無feature分支，working tree乾淨。

**計畫**：[2026-10-08-p1b-react-core-ui](superpowers/plans/2026-10-08-p1b-react-core-ui.md)。P1b只接React核心業務流程；P1c才做部署／測試／內部試用驗收。

**完成摘要**：四Task與兩位獨立審查均通過，G4 Ready to merge: Yes，ff-only合併main；合併後API35／Vitest55／E2E4與build通過。登入／專案導覽／看板／Gate／工作流建立可於 http://127.0.0.1:15173 試用。Demo、後端、migration、依賴未改。三項Minor已記§5，P1c尚未完成。

| Task | 交付 | 狀態 | 驗證預期 | commit主旨 |
|---|---|---|---|---|
| 1 | API client、登入／session UI | ✅ `d4e90ce..4f95236` | RED `10 failed, 1 passed (11)` exit1 → GREEN11 exit0；client修正RED `5 failed, 11 passed (16)` exit1；登入後載入錯誤RED `2 failed, 16 passed (18)` exit1 → GREEN `18 passed (18)` exit0；build exit0。獨立spec Boyle／quality Ramanujan修正後均Approved，品質審查獨立重跑18/build0。真API1280／375登入／登出nooverflow/pageerror，session reload／logout reload成功，截圖已看375。初始未登入me回401產生預期Chrome resource401，非應用程式錯誤，不宣稱console全空。 | `P1b task 1: connect login session UI`；`P1b task 1 fix: complete typed API client` |
| 2 | 專案清單、專案頁、節點樹與麵包屑 | ✅ `3b6f699..9d41f59` | RED `9 failed, 18 passed (27)` exit1 → GREEN `27 passed (27)` exit0、build exit0；spec Boyle／quality Ramanujan均Approved，品質獨立重跑27/build0。真API1280／375任務選取路徑「市場與配方 / 殺菌條件驗證」、nooverflow/pageerror；375長專案名與節點名20倍無溢出。截圖已看375。 | `P1b task 2: add project detail tree navigation` |
| 3 | 看板四欄、狀態更新與Gate阻擋提示 | ✅ `7aeb01d..acd4cc8` | RED `18 failed, 27 passed (45)` exit1 → GREEN `45 passed (45)` exit0、build exit0；spec Boyle／quality Ramanujan均Approved，品質獨立重跑45/build0。狀態使用select符合UI控件指示。真API375工作流試作工單409維持todo→gate核准→doing、無溢出/pageerror；1280注入gate reload500重試成功、401返回登入，nooverflow。測試專案id `f9842e65-a87a-4f06-8ade-4c94f84c06d7`，未改既有seed任務。 | `P1b task 3: add kanban gate workflow controls` |
| 4 | 工作流建立專案、Playwright真後端smoke與文件 | ✅ `f478f1d..1f76fea` | Vitest RED `9 failed, 46 passed (55)` exit1 → GREEN55 exit0；E2E RED `2 failed, 2 passed (11.8s)` exit1 → GREEN `4 passed (3.7s)` exit0；API `35 passed, 1 warning in 20.25s` exit0、build0、Compose rebuild/migration/seed0。1280/375完整login/create/Gate409→approve→doing/readonly nooverflow/pageerror0/unexpectedHTTP/console0，各預期401/409resource兩筆；seed任務前後不變。Boyle spec／Ramanujan quality均Approved，品質獨立55/build0。 | `P1b task 4: add workflow creation browser smoke` |
| G4 | 全分支 `d4e90ce..1f76fea` 審查 | ✅ Boyle與Ramanujan均Ready to merge: Yes | 無Critical/Important；三項Minor記§5。Demo／tests無diff，diff check0；截圖已看1280 Gate阻擋及375建立表單。 | 文件驗收與G5/G6收尾 |

**P1b驗收**
- [x] 登入、登出與session restore使用P1a `/auth/*`與HttpOnly cookie，不靠前端公司切換。
- [x] 專案清單、專案頁、節點樹與麵包屑渲染P1a真實資料。
- [x] 看板狀態更新呼叫`/nodes/{id}/status`，失敗時保留原狀態並顯示安全訊息。
- [x] 可從工作流模板建立專案，payload不含前端偽造的organization欄位。
- [x] pending gate可見，後續階段被擋時顯示安全的Gate訊息。
- [x] Vitest、production build、API pytest、Compose PostgreSQL migration／seed與Playwright P1b smoke通過。
- [x] 1280px與375px無水平溢出、pageerror0及非預期console error0；正常未登入401與測試409的resource訊息據實分列。
- [x] README、正式開發指南與PROGRESS更新並審查。

**執行注意**
1. P1b不得新增前端依賴；用既有React、Vitest、Testing Library與Playwright。
2. P1b只在UI payload送`organization_key`一次登入；後續專案／節點／工作流／gate請求都靠cookie session，不送organization id。
3. 若P1a API回應缺UI必需欄位，先判斷是否已在plan允許的後端變更範圍；超出時依WORKFLOW §8記D停下。
4. Task4容器alembic設定在 `/app/alembic.ini`；實跑 `docker compose --env-file deploy/.env -f deploy/docker-compose.yml exec api python -m alembic upgrade head` exit0。計畫的 `-c api/alembic.ini` 是主機路徑，不在容器存在，按既有容器預設設定修正命令，無schema變更。

### P1c 正式版部署／角色驗收 — ✅ 工程交付完成；使用者試用待簽核

**授權**：D51完整MVP範圍與本輪使用者「繼續下一個階段」；沿用先前直接指示D53「只審核成品，中間可以自己進行」，依既有spec補計畫、獨立審查後繼續實作。重大範圍／安全／破壞性變更仍須問；不新增LAN發布或模組。

**計畫**：[P1c MVP部署驗收](superpowers/plans/2026-10-08-p1c-mvp-acceptance.md)。測試分離projectflow-acceptance與使用者projectflow-formal，避免新增測試資料污染試用清單；既有P1b歷史測試專案保留，不刪除資料。

**G3基準／計畫審查**：Lagrange唯讀plan Approved；API `35 passed, 1 warning in 17.62s`、Vitest55、build0、E2E `4 passed (4.0s)`，全部exit0；main乾淨、無feature分支。基準沿用舊P1b E2E故在共享資料庫另建2個測試專案；此後改隔離驗收，不再向共享DB寫測試專案。

| Task | 交付 | 狀態 | 驗證／commits | commit主旨 |
|---|---|---|---|---|
| 1 | 安全一鍵Compose啟動、opt-in種子、隔離驗收marker | ✅ `2acd923..7eca35d` | RED `2 failed, 11 passed, 14 errors` exit1（缺start/marker）→GREEN27；env繼承RED `1 failed,14 passed`→pass；Windows實啟cp950讀DockerUTF8失敗exit1，回歸RED `1 failed,15 passed`→targeted29pass。完整API56/1warning exit0、Vitest55/build0，真隔離startup/migration/seed0，marker200/login200/count1；共享marker404/login200/count12未變。Lagrange spec/Feynman quality均Approved，quality獨立API56。 | `P1c task 1: add safe Compose trial startup` |
| 2 | 角色讀取權限修正與yu/chen/ming隔離瀏覽器驗收 | ✅ Lagrange spec／Feynman quality Approved | API RED `1 failed,14 passed` exit1→GREEN63/1warning exit0；Vitest RED1failed/55passed→GREEN56 exit0；E2E RED2failed→GREEN6passed(11.0s) exit0；build0。quality獨立API63/27.50s、Vitest56/build0；共享count12/marker404不變，隔離marker200；15173及false-marker拒絕exit1 | `a42b47b`；`P1c task 2: verify role boundaries and isolated workflows` |
| 3 | 一鍵驗收與試用交接文件 | ✅ Lagrange spec／Feynman quality Approved | targeted RED `16 passed,1 warning,17 errors in 0.54s` exit1缺verify→GREEN33/0.18s exit0；quality獨立33/0.16s exit0。verify --keep-running：API80/31.65s/1warning、Vitest56、build0、E2E6/10.0s exit0；無seed刷新shared0/count12/marker404/snapshot hash79500e1f2db0f54d311e99b7921499a3b155b28d011da8dcea62a3912b073ed7不變；重複隔離seed七帳號/env/snapshot保持，migrationhead，marker200。預設down尚待實驗，使用者簽核未勾選 | `717e443`；`P1c task 3: add repeatable MVP acceptance handoff` |

**驗收**
- [x] 一鍵啟動實跑Compose、migration、可選seed與readiness，重跑保留既有資料。
- [x] 測試只在隔離Compose／volume執行，shared marker404、acceptance marker200。
- [x] 既有can_view_node篩選回應，member只收到自己的節點，缺父節點時仍可選取任務。
- [x] yu/chen/ming、readonly與跨公司權限API／真瀏覽器驗收通過；1280／375無溢出或非預期錯誤。
- [x] 一鍵verify各階段exit code可靠，失敗與cleanup不波及使用者環境，保留volume。
- [x] README／正式開發／試用checklist／PROGRESS審查更新，完整回歸與ff-only完成；D50push結果見遠端欄。
- [ ] 使用者內部試用簽核（AI不得代勾）。

**執行注意**：P1c識別的既有讀取缺口：`api/app/routes/projects.py` detail未用`can_view_node`；本計畫按既有helper修正，不改role policy。P1b三項Minor中E2E預期HTTP次數由Task2順帶補強，其他保持原登錄。

**G4**：Lagrange完整`2acd923..e7ecd7a`與scoped `a5c9745`均Ready to merge: Yes，無Critical／Important；指出舊E2E與停機文件Minor，已於`a5c9745`／`a5048e3`對齊隔離環境，Feynman最後文件Approved。controller實跑預設verify：API80/38.36s/1warning、Vitest56、build0、E2E6/11.3s、cleanup與最終exit0；acceptance容器空、pgdata保留。shared count12／hash79500e1f2db0f54d311e99b7921499a3b155b28d011da8dcea62a3912b073ed7／marker404不變，Demo及tests diff空。使用者簽核非工程合併條件，保持未完成，不宣稱LAN部署。

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
| UI3 | Demo三區框架、導覽與側欄進度、總覽表格與負載、我的任務分組表格、預覽副手 | `03dc854..a0c9936`；一次獨立審查（2 Important修正後Yes）；PG6、API368/7skip、Vitest173、build0、E2E20/20（系統Edge）。15173更新API＋web，資料逐值保留、新增0列。使用者簽核未勾。 |
| P2c | 日週月時程/拖移與手機改期、模板CRUD/copy/相對日、硬性FS與可見相依圖 | 6c45e51..5992ce6；D65一次獨立審查Ready to merge: Yes；PG6、API344+target2、Vitest167/build0、E2E15+target1，首次fail日志保留，不重跑main全量。無seed重啟/15173成套備份升0004，原值/filesSHA/env相同。精簡範圍之外明列延後，使用者簽核未勾。 |
| P2b | 回報審核、筆記修訂、指定協作、持久附件、審核中心與安全稽核 | ef39cdd..4d0323e；八Task TDD／雙審、G4 Ready to merge: Yes、ff-only main。G6強制PG1+3、API337/5skip、Vitest150、E2E13/build/cleanup exit0；重啟/恢復/配額、15173無seed升級舊資料與env不變。使用者簽核未勾。 |
| P2a | 工作區、總覽／我的任務、四層新增／metadata編輯、D56指派與日期、多層Gate | acf176e..8dc914a；六Task TDD、兩位獨立spec／品質審查與G4 Ready to merge: Yes；ff-only main，G6 API182／Vitest96／E2E9/build/cleanup exit0，真PG與無seed重啟保留資料通過。15173已就緒，使用者簽核未勾。 |
| P1c | 本機MVP部署與隔離驗收工程交付；使用者試用簽核仍待完成 | 三Task TDD、Lagrange spec／Feynman quality Approved；G4 Ready to merge: Yes，ff-only main；API80／Vitest56／E2E6/build及預設cleanup exit0。既有共享12專案snapshot不變；只停acceptance且保留volume；Demo未變。 |
| 階段 0 | petfood 互動 Demo（`projectflow-petfood-demo.html`） | README §8 階段 0 已打勾 ✅；早於 git 歷史，包含在 `9fdcc64` 裡 |
| F1–F10 | full demo 的多層任務樹、模板、時程編輯、前置條件與關鍵路徑、權限與覆寫、協作、文件與版本、AI 副手（規則式）、分級路由與遮罩（模擬）、研發營運資料（模擬 ERP） | 早於 git 歷史，包含在 `9fdcc64` 裡。F6 的部門目前是寫死的，由 W2 處理 |
| F11 | 任務紀錄與完成回報：回報與審核、自訂回報欄位、筆記、附件（IndexedDB）、主管跳過整個任務、AI 引用紀錄 | [spec](superpowers/specs/2026-09-30-task-records-and-skip-design.md)、[plan](superpowers/plans/2026-09-30-task-records-and-skip.md)；commits `9fdcc64..aebd709`（從 `2fc8f10` 到 `aebd709` 共 10 個：7 個 Task、2 輪修正、1 次整體修正），以 fast-forward 合併進 `main`；測試 44/44。SDD 暫存已歸檔到本機的 `.superpowers/archive/2026-09-30-f11-task-records/`（不在 git 裡；重要內容已整理到本看板 §5） |
| W1 | 子任務置頂回報卡：葉任務頁標題下方固定顯示回報卡（狀態與下一步動作），「紀錄」分頁排第一並作為預設；D15 桌面版紀錄等分頁可捲動，D16 卡片摘要最多約 6 行，D17 新增第一個子任務後切到看板 | [spec](superpowers/specs/2026-10-01-subtask-report-card-design.md)、[plan](superpowers/plans/2026-10-01-subtask-report-card.md)；commits `8aed7d6..2d2c785`（2 個 Task、2 輪 Task 修正、D15、1 次整體修正），以 fast-forward 合併進 `main`；測試 64/64；`db.v` 維持 3。審查全部獨立（每個 Task spec＋品質各 2 輪，整體審查 2 輪）。SDD 暫存已歸檔到本機的 `.superpowers/archive/2026-10-01-subtask-report-card/`（不在 git 裡；重要內容已整理到本看板 §3 W1、§5、§6） |
| W2 | 部門模型：`db.departments` 可設定、預設 10 部門；任務必填負責部門且負責人可未指派；任務可見性與操作權限依負責人、部門主管、專案負責人、系統管理員等規則；時間軸預設收合成階段並可依負責部門篩選；模板帶入負責部門 | [spec](superpowers/specs/2026-10-01-department-model-design.md)、[plan](superpowers/plans/2026-10-01-department-model.md)；commits `670afaf..5f326ab`（Task 1–7、展示模式流程調整、整體修正與等待合併進度），以 fast-forward 合併進 `main`；測試 `全部通過 137/137`；`db.v = 4`。Task 1–5 是完整流程獨立審查，Task 6–7 是展示模式單一審查者，整體修正後由 Codex 自我再審並經確認合併。 |
| W3 | 工作流架構：`db.workflows[]`、工作流模板 CRUD、從工作流建立專案、工作流專案的前序階段關卡硬性擋住後續階段 | [spec](superpowers/specs/2026-10-05-process-control-design.md)、[plan](superpowers/plans/2026-10-05-workflow-architecture.md)；commits `6ea8d08..9bb9a52`；測試 `全部通過 149/149`；`db.v = 5`。展示模式單一 reviewer 找到 1 個 Important（generic 前置覆寫可繞過 pending workflow gate），已修正。 |
| W5 | README 對齊現況（精簡）：頂部進度摘要、§1 快速開始、§2 Demo 功能總覽、§6 系統架構圖、§7 專案結構更新到 full demo／W3 後狀態 | 2026-10-05 完成；只改 README／PROGRESS／架構圖，沒有改產品程式。驗證 `git diff --check`。 |
| 規劃文件 | W1 的 spec 和 plan、W2 的 spec 和 plan | `3a24c52`、`ed3e24f`、`edf46b6`、`dfc0126` |
| W6 | 五個公司空間、公司預設身分與原子切換、四產業專案／工作流／營運模組、v6 舊資料遷移與損壞修復、附件隔離與單公司重設、AI／權限／稽核隔離 | `d879db1..f3a61ec`；每Task TDD及獨立審查、整體審查一輪修正後 Ready to merge: Yes；2026-10-08 ff-only 到本地main，合併後174/174，508畫面狀態驗收通過。只為固定Demo，沒有公司CRUD／登入隔離／後端多租戶。 |
| P0 | 正式規則、FastAPI健康檢查、React狀態介面、Compose／真實PostgreSQL骨架與開發指南 | `e6082f9..435af43`；Native三Task TDD及獨立審查，Hilbert G4 Ready to merge: Yes，ff-only合併main。合併後8pytest／6Vitest／4Playwright與build通過，DB故障恢復同volume、桌面手機／逾時重試通過，Demo未變。P1a–P1c尚未實作。 |
| P1a | 正式版後端核心：登入/session、公司隔離、P1a PostgreSQL migration與seed、Project／Department／Node／Workflow／Gate／Report／Audit API | `038ce64..0c9fe06`；Native四Task TDD及逐Task獨立審查，Linnaeus G4第1輪找出reviewer gate權限Important並於`0c9fe06`修正，scoped re-review Ready to merge: Yes。API35／Vitest6／E2E4與build通過，Compose真PostgreSQL migration／seed／HTTP smoke通過，Demo未變。 |
| 交接系統 | `AGENTS.md`、`CLAUDE.md`、`GEMINI.md`、本看板、`docs/WORKFLOW.md`、`.claude/workflows/pf-status.js`、`.claude/workflows/pf-next.js`、`.gitignore` | 2026-10-01 建立；commit 用 `git log --grep "Docs: handoff system"` 查 |

---

## 5. 待處理問題（Issue register）

**AUTOSTART-N8N新增（2026-11-03）**
- OCR-DECIMAL（major，OPEN，2026-11-04）：RapidOCR會吃掉較淡的小數點，虛構檢驗報告中「粗脂肪 6.2%」辨識成「62%」、「至少 5.0%」成「至小 50%」、「至少 0.10%」成亂碼；檢驗報告會造成十倍誤差。可能做法：小字放大前處理、百分比超過100或結果與標準矛盾時標記；需改程式、補測試並重量1−CER。暫以AI來源的「OCR辨識文字，可能有錯字」提示因應。
- AUTOSTART-N8N-m1（minor，OPEN）：n8n／Mailpit跟核心服務在同一次`up --wait`；5678／8025被占用（例如同時跑隔離的`projectflow-n8n`示範stack）或離線又缺n8n映像時，整個啟動失敗、migration不會跑。可改成核心先`up`，再對n8n／Mailpit做一次失敗不擋的`up`。
- AUTOSTART-N8N-m2（major，OPEN，待使用者）：2026-11-03 07:44開機後，開機捷徑視窗顯示「[1/4] Docker 已就緒」後「[2/4] 啟動失敗」，ProjectFlow整個沒起來（api的StartedAt仍是前一天）。Docker Desktop日誌07:45:16～07:45:31連docker.com失敗（network/transient error），engine 07:45:20就緒；09:40同樣的`start()`（本機與公開組合）都成功。推測：開機頭幾十秒網路還沒通，`up --build`要向registry解析`FROM python:3.13-slim`等標籤而失敗（未實證）。建議：`public_trial.py`啟動失敗時等30秒重試，最多3次。本次未改。
**COPILOT-SIMPLIFY新增（2026-10-28，審查記錄，皆不阻塞）**
- OPS-OCR-N8N-m1（minor，OPEN）：`deploy/n8n/setup.py`用在既有`projectflow-formal`時會重建api容器但不重建web，nginx仍連舊的api位址，`/api`一律502；手動`docker compose ... restart web`後恢復。可在setup.py最後重啟web，或讓nginx每次請求重新解析api。
- RAG-PORT-m1（minor，OPEN）：追問改寫或要求補充時繞過`gateway.prepare`，稽核的gateway仍是`route:none`／`not_sent`，只有`followup`欄位看得出問題送過本地模型；可把改寫記進gateway資訊。
- RAG-PORT-m2（minor，OPEN）：預覽一律用「上一題＋這一題」，實際提問可能用模型改寫，兩者可能不同。
- RAG-PORT-m3（trivial，OPEN）：`followup='none'`時`standalone_question`為null，規格寫的是「實際拿去查詢的問題」；畫面不受影響。
- RAG-PORT-m4（minor，OPEN）：「下載原檔」是一般連結，401／403／404會開到JSON錯誤頁，不會回登入或顯示「你目前無法查看這個來源」；端點本身仍檢查權限。
- RAG-PORT-m5（minor，OPEN）：`followup.resolve`在資料集／專案／正式索引檢查之前執行，最後回404的請求也可能先花最多15秒呼叫模型；合併後的問題可能超過2000字（後續限制會吸收）。
- RAG-PORT-m6（minor，OPEN，正式上線前）：`index_worker.tick`在PostgreSQL整個更新期間（含解析與OCR）維持一個讀取交易，會阻擋DDL並延後vacuum；展示可接受。
- RAG-PORT-m7（trivial，OPEN）：索引檔以`str(db.bind.url)`當鍵，PostgreSQL換主機或帳號會整份重建並留下舊檔。
- COPILOT-SIMPLIFY-m1（minor，OPEN）：E2E `ai-starter.spec.ts`、`ai-local-model.spec.ts` 拿掉 TRAIN-10 專案範圍後，「新人課程目前哪天上？」可能撈到機密文件，使「資料等級：內部」斷言失敗；未在驗收環境實跑。不穩時改用 `page.request` 驗分級。
- COPILOT-SIMPLIFY-m2（minor，OPEN）：`ai-auto-history.spec.ts` 拿掉正式文件歷史段落開啟與「歷史版本，請勿當作現行規定」的畫面驗證，目前只有 Vitest 覆蓋；可用正式文件分類的歷史快捷題補一條 E2E。
- COPILOT-SIMPLIFY-m3（minor，FIXED 2026-10-28，使用者「修掉」；示範腳本改為點分類／快捷題，D15改為在正式文件分類輸入後於⚙預覽，未限定專案、未實跑）：`docs/ai-demo-questions.md:20,25,30,47,67,76` 仍寫選「AI資料集／查詢方式／分析種類」、勾「包含歷史版本」，應改成「點分類→點快捷題」；不在本次允許清單。
- COPILOT-SIMPLIFY-m4（minor，FIXED 2026-10-28；兩句提示改為「請點下方快捷題…」，模型建議句的「上方公司／AI專案範圍」改為「目前公司可見的AI專案範圍」；新增`test_sql_guidance_points_to_shortcuts_not_removed_menus`先RED後GREEN，AI相關後端204 pass／2 skip，15173實測建議句已更新）：`api/app/ai/service.py:56,58` SQL 無法辨識時提示「請選擇分析種類」「請從分析選單選擇查詢」，選單已移除，應改成「請點下方快捷題或換個問法」；後端檔不在本次允許清單。
- COPILOT-SIMPLIFY-m5（trivial，OPEN）：`CopilotPanel.tsx` 快捷題專案以標題開頭比對取第一個；跑過正式文件 E2E 的環境有「隔離索引展示 …」「增量索引展示 …」測試專案，可能對到測試專案。展示環境不受影響；可改為優先完全相符或比對「（虛構）」。

**OPS-LOCAL新增（2026-10-28）**
- OPS-LOCAL-m1（important，OPEN，不阻塞，需使用者：否，大小S）：照 `deploy/demo-data/README.md` 在 0019 schema 匯入資料包會失敗。`demo_pack.import_pack` 用目前 ORM 的 `users` 表插入，SQLAlchemy 會帶入 0021 新欄位 `status`、`must_change_password` 的 Python 端預設值，但 0019 沒有這兩欄，報 `sqlalchemy.exc` f405 錯誤。所以程式比資料包新時，README 的「先用相同版本還原，再 start.py 升級」走不通。2026-10-28 本機 15173 的繞法：`alembic upgrade head` → 暫把 `alembic_version` 改成 `20261012_0019` → `demo_data.py import` → 改回 `20261024_0021`。0020／0021 只新增表和欄位，結果等同「先匯入再升級」；匯入 27 表（80 帳號、39 專案、500 節點），yu／demo-yu 登入可見 8 個專案。修法擇一：插入時只帶資料庫實際存在的欄位（`inspect(conn).get_columns`），或改成在目前 schema 匯入、允許資料包版本較舊，或以 head 重新匯出資料包。位置 `api/app/demo_pack.py:129-136`。

**P1b新增**
- P1b-T1-m1（minor，OPEN，不阻塞）：API client未設timeout；pending請求須等代理或連線結束，取消目前涵蓋換請求與卸載。後續網路韌性工作補強，位置 `web/src/api.ts:12`。
- P1b-T3-m1（minor，已人工驗證，不阻塞）：Vitest未直接覆蓋gate核准成功／reload失敗／重試；主代理Playwright1280注入reload500→重試成功與401→返回登入均pass。可於後續網路韌性工作補自動回歸，位置 `web/src/App.test.tsx`。
- P1b-F-m1（minor，FIXED）：P1c Task2在E2E精確限制預期resource401/409各一次；兩位獨立reviewer確認，E2E6passed exit0。位置 `web/e2e/health.spec.ts`，commit `a42b47b`。

**P0新增**
- P0-T1-m1（minor，OPEN，不阻塞）：`api/tests/test_health.py`缺查詢結果非1、查詢階段錯誤、checker非布林的持續回歸案例；Arendt唯讀補驗均通過，後續擴充API測試時納入。
- P0-T1-m2（minor，OPEN，不阻塞）：Starlette TestClient對httpx提出棄用警告；目前鎖版8項均通過，升級測試依賴時處理，不盲目換版。

- **ID 規則**：
  - F11 的項目來自 F11 的執行紀錄，2026-10-01 已經逐項在程式碼中核對過，共 39 個 ID（N2 已併入 T4-m1）。
  - 之後的工作項目用 `W1-T1-m1`（Task）或 `W1-F-m1`（整體審查）這種格式，詳見 WORKFLOW 附錄 B。
- **嚴重度**：important、minor、trivial。**大小**：S（不到 30 分鐘）、M、L。
- **處理方式**：「需使用者」為「是」的項目，要等 §6 有了結論才能動手。修好後狀態改成 FIXED，並寫上 commit。
- **展示模式（D30，2026-10-05 起）**：W4 取消。OPEN 項目只有描述開頭標「【W2 整體修正】」的會在 W2 修，其他都延到正式版；新發現的 minor 也是記下來就好。

### OPEN

| ID | 描述 | 嚴重度 | 大小 | 需使用者 | 位置（dfc0126） |
|---|---|---|---|---|---|
| WEEKLY-AI-m1 | AI週報實測（gemma3:4b）兩點與規則不符：①模型自行換算數字（進度30%寫成「仍有 70% 延遲」），提示詞禁止但程式不檢查句中數字；②提示詞要求提到任務寫[T1]代號，模型完全沒寫，程式只擋「清單外代號」，沒代號就照收。目前靠第4道關卡「負責人確認才寄出」人工攔下。可加：句中數字必須出現在facts中，否則該段改用條列。**2026-11-07 ①已修（WEEKLY-AI-NUMBERS，PR #13 合併進main `12119cd`）**：句中數字不在facts就該段退回條列；②不做（見[短規格](superpowers/plans/2026-11-07-weekly-ai-numbers.md)） | minor | S | 否 | `api/app/services/weekly_report_service.py` `write_sections` |
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
| W2-T3-m4 | `create` 照 spec 不變，所以不能操作某個任務的人（例如透過上層規則看得到它的成員、範圍內審核人）仍可以在它底下新增子任務，讓它從葉任務變成上層任務、清掉進度、自動結案待確認的回報。spec §4.4 明寫「其餘動作不變」，要改需要另外決定 | minor | S | 否（spec 指定） | `can()`（html:801@717b359）、`addNode` |
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

### BY_DESIGN（plan 或 brief 指定的行為，要改必須先經過同意）

| ID | 描述 | 需使用者 |
|---|---|---|
| F11-T1-m5 | 「重置 Demo 資料」不會把角色重設回 yu | 是（D4） |
| F11-T4-m2 | SVG 附件透過同源 blob URL 預覽，內嵌的 script 會在 app origin 執行。在 Demo 裡只算 self-XSS，接上伺服器後就會變成 stored XSS | 是（D5） |
| F11-T5-m2 | 送出回報時被硬性前置擋下，系統改開跳過對話框，已經輸入的回報內容全部遺失 | 是（D7） |
| F11-T5-m4 | 「N 個子任務」算的是整棵子樹，和全 app 的用語慣例一致 | 否，維持現狀 |
| W1-T2-m1 | 紀錄分頁第一筆回報上方的分隔線不見了（上層節點和葉任務都一樣）。plan Task 2 Step 4 拿掉了標題外層的 `.row`，`.rec:first-of-type` 因此套到第一筆回報。外觀和「筆記」區一致，兩位審查者都建議接受 | 否，維持現狀 |
| W1-T2-m5 | 從時程往下一層進入子任務會切到「紀錄」，再從麵包屑回上層時落在「看板」，不會回到時程。這是 spec §5 規定的行為（進入葉任務預設紀錄；回到上層時從紀錄改回看板） | 否，維持現狀（要改需要決定） |
| W2-T3-b1 | D23 的連帶結果：collab 角色的人負責的任務（例如小林負責 t4031），現在可以改時程（以前不行），因為 D23 規定任務時程等於 `canWork`，而 `canWork` 含負責人本人（spec §4.2 不分角色）。對話框和時間軸行為一致 | 否，照 D23 |
| W1-T2-m9 | 回報卡上只有成果說明有高度上限（D16），自訂欄位（`dl.kv`）、退回意見、跳過理由沒有。1366×650、摘要 8 行實測：自訂欄位 0／1／2／3／5 個時，卡片高 229／261／286／311／361px；時程的內容區 39／7／0／0／0px；看板和相依圖的內容區 81／49／24／0／0px；欄位達 3 個時，時程的分頁列底部到 657px，超出畫面。檢驗類任務常有好幾個數值欄位。預設的紀錄分頁仍可捲動，不會遺失資料。D18 決定維持現狀 | 否，維持現狀（D18；要改需要另外排工作項目） |

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

**P2c-m1（Minor，可延後）**：TimelineView.tsx:128桌面寬度觸控點可編輯task條可能不定位；375手機卡片與節點名稱入口可用，不阻塞主流程。獨立審查記錄，未因小問題擴大修正。

## 6. 待決定（Decision register）

- 這些事項 AI 不可以自己決定。有預設值的，在使用者推翻之前照預設執行。
- 「來源」欄記錄這個 D 是哪個工作項目或 Task 產生的。整體審查和合併只看「來源」是本工作項目的 D。
- **使用者回答後**，照下面的方式記錄：
  1. 狀態改成「已決定 YYYY-MM-DD：<一句結論，盡量用使用者的原話>」。推翻預設時也一樣。
  2. 把連動的 §5 條目的「需使用者」改成「否（Dn）」，排進對應的工作項目。
  3. 移除因這個 D 而標的 ⛔（「▶ 現在」、§2、§3、Task 列都要檢查），清空「阻塞／待使用者」，把結論寫進該工作項目的「執行注意」，並把「下一個動作」改回原本的步驟。
  4. commit `Progress: record Dn`。如果有 `feature/*` 分支，就 commit 在那個分支上。

| ID | 來源 | 問題 | 預設／建議 | 狀態 |
|---|---|---|---|---|
| D90 | INBOX-REMOVAL | 收件匣資料夾掃描（D87第二批）要不要保留；Excel營運資料匯入改成什麼；簡報P.37的n8n流程數 | 整條拿掉；Excel改成系統內上傳；P.37維持四個流程 | 已決定2026-11-06：使用者「沒辦法限制權限」並決定「Excel 改成系統內上傳」「P.37 維持四個」；推翻D87第二批的收件匣部分；同日改為「請你不要改程式 幫我改簡報就好」「不要理會Excel」先改簡報；之後「n8n 的收件匣排程實際上還在每分鐘跑的程式 請改掉」：移除收件匣程式，不做Excel上傳 |
| D89 | LINE-BROADCAST | n8n通知要不要接LINE、用哪種方式 | 三選一：A廣播給所有好友（不需webhook）、B推播到群組（取一次groupId）、C逐人綁定（webhook常駐）；建議B | 已決定2026-11-04：使用者「我已填入Channel access token 選A」 |
| D90 | TEXT2SQL-LEARNING | 匯出去識別化展示包（`deploy/demo_data.py export`→進git的`deploy/demo-data`）時，要不要排除新表`ai_learned_phrases`（含使用者問句原文與確認者id）；`api/app/demo_pack.py`不在本計畫允許清單（獨立審查應修2） | 建議：把`ai_learned_phrases`加進`demo_pack.EXCLUDED`（一行；完整備份`BACKUP_EXCLUDED`不動，同類的`ai_answers`本來就排除）。預設：未決定前不改，PR描述註明 | 已決定2026-11-05：使用者「要，一起修」 |
| D88 | RAG-PORT | Mina的RAG-V1（`origin/feature/review-fixes`，PR #5）要不要、怎麼併入main：它的migration 0020／0021和main形成兩個head，合併有7個檔案衝突，另有一套`api/app/rag/`，並把AI助手改回下拉選單 | 不整支合併；以main的AI助手為主體，移植RAG-V1的連續追問、自動索引、停用知識、回饋、引用原文檢視 | 已決定2026-11-02：使用者「以 LEE 的版本為主體，從 Mina 那版挑上面幾項移植過來」 |
| D87 | N8N | 「請把n8n實作完成」的範圍與作法 | AI依建議代決：第一批補齊（個人Email設定、寄送失敗清單與重寄、審查非阻擋項：確認時重查D85、分級設定檔損毀時停產週報、拉取5分鐘租約防重寄、週一摘要用上個工作日、本週已寄出時停用產生鈕、一般成員顯示說明）；第二批（收件匣：`<收件匣>/<公司代碼>/<專案名稱>/`檔案自動存成專案文件並解析／OCR後寄信通知負責人，完成移到`已匯入`、失敗移到`失敗`；`<公司代碼>/_營運資料匯入/<分類>.xlsx`依代碼新增或更新營運資料）；第三批（每日完整備份到備份資料夾保留7份並寄信給管理者、營運資料「到期」欄位30天內到期寄信並在關聯任務下建立更新任務）。掃描與匯入由專流執行、n8n只排程呼叫（n8n 2.x預設不能存取主機檔案）；token維持單一環境變數（單一地端n8n） | 已決定2026-11-02：使用者「請把n8n實作完成 問題一律採用建議作法 不需要問過我」 |
| D86 | N8N | 第一批要做到完整版還是可展示即可 | 依計畫「最小架構範圍」一節：token改單一環境變數、不建服務帳號與token表、Email由seed／CLI填、前端只做週報分頁；其餘核心照規格 | 已決定2026-11-02：使用者「請你依照 最小架構實作 可以Demo的程度就好」 |
| D85 | N8N | 週報「排除機密節點」：`ai.policy`的公司預設等級是confidential（DEFAULT），沒調整政策時每個節點的有效等級都是機密，週報會被整份排除 | 建議B：只排除專案或節點上「明確標為機密」（有覆寫）的任務，公司預設不算；AI本來就只用本地模型 | 已決定2026-11-02：使用者「B 只排除明確標機密」 |
| D84 | N8N | 週報收件人：規格寫「看得到該專案的成員」且內容取全體收件人可見交集；但`can_view_node`中一般成員（member）只看得到自己負責、協作或部門主管範圍的節點，交集會讓週報幾乎是空的；系統也沒有專案成員名單 | 建議：週報寄給專案負責人＋在此專案有負責或協作任務、且角色可看全部節點（admin／project_owner／reviewer／readonly）的人；一般成員不收週報，改由每日摘要涵蓋 | 已決定2026-11-02：使用者「A 只寄管理角色」 |
| D83 | N8N | 要不要加入n8n、做哪些功能與先後 | 地端自架n8n只做對外串接；四項（文件收件＋OCR、通知外送、排程維運、Excel匯入）加AI週報，分三批；ERP轉接層不做，第一批＝共用前置＋通知外送＋AI週報（明細見§2 N8N） | 已決定2026-11-02：使用者「功能1-5 我都想做」、AI週報「放進第一批」；同日「我要地端自架 n8n」「不做第三批是 ERP 轉接層」；規格待brainstorming |
| D82 | DOCS-CLEAN | README 要不要繼續放每次交付的紀錄 | README只留目前狀態、快速開始、正式版功能總覽、規格與尚未完成的路線圖；交付紀錄、測試數字與決策只寫PROGRESS。D50的「每階段更新README」改為更新這幾處（完成的項目從§8移除、必要時調整§2） | 已決定2026-10-20：使用者「已經完成的進度從readme.md中移除，把readme弄乾淨一點，現在東西太多了」 |
| D81 | 展示目標收斂 | 避免為不影響展示的完整性耗時 | UI5一次交付、一個完整案例、其他產業最小示例、相關測試與一次展示走查；保留資料及基本安全，F1／F2後續另定 | 已決定2026-10-11：使用者要求「重新檢查整個進度與專案…主要是要能夠展示的版本」；依此收斂執行，無需重問方向 |
| D80 | UI5短計畫 | 三批範圍與示例隔離 | 按[短計畫](superpowers/plans/2026-10-11-ui5-remaining-screens.md)：A文件資料、B營運、C副手治理；靜態fixture與記憶體預覽、零正式寫入，各公司對應示例；UI5三批＋展示走查為可展示版本完成點，F1另補正式功能 | 已決定2026-10-11：使用者「把這個規劃推上git，讓下一個讀到的ai能自動接手」；授權下一AI直接開始UI5-A並依序B／C與展示修整 |
| D79 | TP-G短規格 | 欄位修改時機、歷史保存與模板帶入規則 | 按[短計畫](superpowers/plans/2026-10-10-tp-g-report-fields.md)：四種類型，未關閉且無待審回報的葉任務由既有編輯者設定；送出驗版本及保存快照；模板／複製只帶定義，舊資料不改；上限與延後項目見計畫 | 已決定2026-10-10：使用者「照此計畫實作」，核准D79及短計畫 |
| D78 | TP-F短規格 | 核准者範圍、覆寫效期、子樹恢復、部門指派與通知 | 按[短計畫](superpowers/plans/2026-10-10-tp-f-permissions-collaboration.md)：主管審本部門他人申請，管理者可直接附理由操作；覆寫限當次動作且完成仍需回報；子樹快照恢復不覆蓋後續修改；admin管理部門，主管可見並指派本部門；個人站內通知與已讀，負載沿可見任務數 | 已決定2026-10-10：使用者「照建議做」，核准D78及短計畫 |
| D77 | TP-E短規格 | 套用如何保留既有資料、模板範圍／權限、完整版本、刪除與復原語意 | 依[短計畫](superpowers/plans/2026-10-10-tp-e-advanced-templates.md)：追加子樹不覆蓋；公司模板限管理者維護，來源完整可見；完整版本可選版套用；軟刪不影響已建任務；人工條件重新確認、負責人預設不帶；階段另存轉普通根任務，工作流只套專案；套用支援一步結構復原 | 已決定2026-10-10：使用者「照建議做」，核准本列與短計畫 |
| D76 | TP-D短規格 | Demo條件型依賴未實作的採購／營運模組；需決定本批來源及前置語意 | 建議人工確認條件（管理者確認／撤回與稽核，不含文件、不假稱ERP）；其他按[短計畫](superpowers/plans/2026-10-10-tp-d-advanced-dependencies.md)：SS／FF、正負lag僅管排程、soft僅警示、FF核准重檢、D75原子順延及既有管理權限。替代為條件型延後至營運模組 | 已決定2026-10-10：使用者聽取人工確認條件與其他TP-D照計畫的說明後回答「好」，授權依此實作 |
| D75 | TP-C短規格 | 自動順延可能修改其他人的任務；遇已鎖定／未排程／已結束任務如何處理；誰能控制鎖定；關鍵路徑與日期復原的範圍 | 已核准：1.逐項可見及可編輯授權，遇任何阻擋整次改期取消，預設關閉自動順延；2.鎖定／解鎖及直接改鎖定日期限系統管理員與該專案負責人，cascade遇鎖定一律擋；3.其餘按[短計畫](superpowers/plans/2026-10-10-tp-c-advanced-timeline.md)：Demo可見範圍最晚結束單鏈估算，D74日期不復原，FS零延遲，migration 0007只新增兩個false欄位 | 已決定 2026-10-10：使用者「照 D75」；依短計畫實作 |
| D74 | TP-B規格細節 | 規格沒寫到的TP-B細節：誰能升降級／移動／複製／刪除／復原、復原涵蓋哪些操作、上層已完成時加入或重開子任務怎麼處理（TP-A Minor 1）、階段能不能複製或刪除、複製帶哪些欄位、刪除後資料怎麼保存 | 權限：AI原建議全部只限系統管理員與專案負責人；復原只涵蓋新增節點、刪除、移動（含拖曳／升降級）、複製子樹，只有一步、只限原操作者，之後有其他變更就擋下；上層是待確認／完成／已略過時擋下新增、移入、複製、重開與恢復子任務，不做Demo的自動改回進行中；只有任務能複製或刪除（階段不行）；複製名稱、負責人、部門、日期、權重、協作與子樹內前置，狀態歸待處理，不複製回報／筆記／附件；刪除是軟刪除，資料保留、前置連線移除並記錄 | 已決定 2026-10-10：權限「照 Demo 放寬」（任務負責人也能升降級、移動自己的任務；刪除限專案負責人）；復原「只限結構操作」；上層「擋下並說明」；其他「照計畫」。複製權限依正式版新增規則維持管理者（AI代決，可推翻） |
| D73 | TP-A規格細節 | 規格沒寫到的TP-A細節：拖到待確認／完成要不要略過完成回報、誰能拖進卡片與相依連線怎麼處理、父節點規則的覆寫與上層自動連動、進度要不要算看不到的節點、權重能不能填小數、側欄與總覽的%改不改、✓回報用對話框還是回報卡 | 拖到待確認／完成改開完成回報，不直接改狀態（Demo會略過回報）；拖進卡片只限系統管理員與專案負責人，目標要是待處理或進行中，有相依衝突就擋下、不刪連線（Demo會刪）；父節點規則TP-A沒有覆寫（附理由覆寫歸TP-F），不做上層自動改進行中或待確認；進度只算看得到的節點；權重是0–100整數；側欄與總覽專案表改用加權進度，第4張卡仍是可見任務完成率；✓回報進入任務並展開回報卡；拖曳用原生HTML，不加依賴，手機與鍵盤用狀態下拉 | 已決定 2026-10-10：「照 D73 做」 |
| D72 | UI4畫面細節 | 規格沒寫到的UI4細節：Demo有、正式版沒有的節點樹、加權進度、節點自己的時程與相依圖、拖曳改狀態、狀態用詞怎麼處理 | 移除主區節點樹（往下靠卡片與階段條、往上靠麵包屑、階層總覽在時程）；標題列與階段條用總覽相同的可見任務完成率，加權進度歸TP-A；時程與相依圖在每一層都顯示整個專案並加說明，節點範圍歸TP-A；保留精簡狀態下拉；狀態名稱維持正式版用詞，看板「完成」欄含已略過；另存／套用模板、文件、資料照位置停用並標尚未提供；閘門改在階段頁與審核中心核准；手機時程用同一張圖 | AI 代決 2026-10-09：照建議做（可推翻），細節見UI4短規格／計畫 |
| D71 | UI3畫面細節 | 規格沒寫到的UI3細節：首頁需要的階段、截止日、延遲、負載與位置資料從哪來；Demo有、正式版沒有的導覽與副手怎麼呈現 | `GET /workspace/overview`、`/my-tasks`只新增唯讀欄位，從既有可見節點計算，不改schema；保留「可見任務完成率」為第4張卡；拿掉「專案工作區」導覽；建立入口移到側欄；副手與營運／AI政策導覽標示未提供並停用 | AI 代決 2026-10-09：照建議做（可推翻），細節見UI3短規格／計畫 |
| D70 | 後續主線修訂 | 使用者要求「先弄得跟DEMO一樣功能的任務規劃器」；文件是否算在內、復原做到什麼程度 | UI3→UI4→TP-A至TP-G任務規劃器功能補齊→UI5→F1→F2；任務規劃器含任務樹／看板／時程／前置／模板／權限協作／回報欄位 | 已決定2026-10-09：「文件先不算，復原只做上一步，寫入D70開始」；成員權限頁移入TP-F，條件型前置的文件核准條件待文件功能交付後再接 |
| D69 | 後續主線重排 | 使用者要求先做到與Demo相同畫面、功能可慢慢補 | UI3框架首頁→UI4工作區操作→UI5其餘畫面→F1真功能→F2進階；畫面/互動及正式功能分開驗收 | 已決定2026-10-09：本次重新規劃，既有資料與功能保留；未啟動UI3、P2d改拆入後續 |
| D68 | UI2展示豐富度 | 使用者要求模板像Demo豐富、公司切換在左下 | 產業範本卡片與完整流程；五公司本機展示session切換，保留既有資料 | 已決定2026-10-09：明確選本機展示模式一鍵切換、標示展示身分；後端真session與隔離、模式預設關閉，P2d後移 |
| D67 | 下一階段順序與前端介面 | 使用者指定「把下一階段改成前端介面對齊」 | UI1排在P2d前，主要畫面以Demo布局／視覺／操作對照，接既有真API，未實作模組清楚標示 | 已決定2026-10-09：優先UI1側欄／配色／字級間距／總覽卡片／工作區與時程；不擴新後端功能、不改資料與權限，依D65精簡流程 |
| D66 | P2c範圍與啟動 | 使用者指示「繼續下一個階段」，並明確選A（推薦） | 日曆日、單任務改期、管理者／project_owner模板管理；同專案task硬性FS、done/skipped滿足、無覆寫；SS/FF/延遲/順延/關鍵路徑/子樹套用延後 | 已決定2026-10-09：採精簡範圍，短規格／計畫定稿開始實作；按D65階段一次審查/回歸，保留資料與基本權限 |
| D65 | 正式軌後續流程 | 使用者同意簡化提案，並要求不特別提專案用途，只將流程變簡單 | 每階段短規格／計畫、一次獨立審查、一次完整回歸，修正只驗受影響部分，一般畫面不強制TDD，每階段更新README／PROGRESS；展示主流程優先 | 已決定2026-10-09：採用精簡流程WORKFLOW§14；保留既有資料、隔離測試、基本公司角色權限與Git安全，不重做已完成功能，不代勾使用者簽核；尚未定案的新功能另列範圍 |
| D64 | P2b整體審閱與實作 | 使用者指示「繼續，已DEMO那個效果為主，遇到問題再問我」 | 完整spec／plan定稿，依八Task開始TDD與雙獨立審查；UI以Demo效果為主要參照，保留正式版權限、資料與隔離驗收 | 已決定2026-10-08：授權繼續至驗收交付；既定決策不重問，真正問題／範圍取捨再詢問，不解讀為降低正式軌安全或代勾使用者簽核 |
| D63 | P2b G1剩餘邊界 | 回報層級、結案結果、重開／略過、自訂欄位與審核中心／稽核範圍 | A推薦按草案§4：task獨立回報、固定欄位、管理者理由重開／單任務略過、安全稽核；自訂欄位延P2c，跳過申請／覆寫另列後續。B把自訂欄位與跳過申請也納本期、另補規格Task | 已決定2026-10-08：使用者明確選A（推薦），採草案§4整組流程邊界；完整API／migration與計畫另供整體審閱 |
| D62 | P2b G1筆記／附件 | 筆記修訂、附件保存／移除、格式與容量 | 筆記僅作者可改、不刪、留修訂；附件限PDF/PNG/JPEG/TXT/CSV/Office新格式/ZIP且只下載；一般附件軟刪、已送回報附件不可刪。A推薦單檔10 MB，B25 MB；兩者每公司初始1 GB含軟刪／未關聯，主機可調高，SHA-256／持久化volume／逐次授權 | 已決定2026-10-08：使用者選A（推薦），採單檔10 MB及草案§3整組筆記／附件規則 |
| D61 | P2b G1協作範圍 | 協作部門加入後哪些人可看與寫筆記 | A推薦：指定協作人員及協作部門主管，其他成員不自動取得；B：整個協作部門。兩者僅指定節點不繼承，不因協作授予送回報／審核／metadata權；readonly仍不可寫，我的任務納入協作task | 已決定2026-10-08：使用者選A（推薦），指定人員與協作部門主管；範圍／撤銷／隱藏父節點依草案§3 |
| D60 | P2b G1審核授權 | 誰可審核，管理者是否能確認自己提交的回報 | 同公司且可見的admin／實際專案擁有者／負責部門主管／具can_work_node範圍reviewer可審，readonly拒絕。A推薦僅admin／實際owner且有送出權可明確送出並確認並完整稽核；B同一審核範圍但一律不能自審 | 已決定2026-10-08：使用者選A（推薦）；審核者範圍及管理者明確自行確認依草案§3，不擴大Gate權限、不自動核准 |
| D59 | P2b G1完成流程 | 現有Report不改status且可直接done；P2b是否要求完成必須經回報審核 | A推薦：送出review、核准done、退回doing／重送新版本，API禁止繞過；B：回報審核與狀態分開、保留直接done。舊資料不回退、不刪歷史 | 已決定2026-10-08：使用者選A（推薦），回報驅動完成；同意不包含後續尚未確認的審核授權與附件／協作細則 |
| D58 | P2b G1啟動 | P2a交付後使用者指示「繼續進行」 | 按既定路線圖開始P2b規格與計畫，保留資料、隔離測試與使用者簽核界線 | 已決定：2026-10-08授權接續G1／G2準備；不是未定案規則已核准或P2a使用者簽核通過 |
| D1 | W1、W2 | W1 和 W2 的執行順序 | **先做 W1，再做 W2。** 理由：W1 的測試數（44→51→57）和「db.v 維持 3」只有先做才成立；W2 只需要調整一個片段；W1 的測試可以當作 W2 改寫權限時的回歸網 | 採預設 |
| D2 | 流程 | 分支與合併方式 | 每個工作項目開一個分支 `feature/<wid>-<slug>`，直接在主 checkout 開，**不用 worktree**。plan 或 skill 要求用 worktree 時，以這條為準。整體審查結論是 Ready to merge、測試全部通過，而且所有審查都是獨立進行的（不是自我審查），這時 **AI 可以在本地用 `git merge --ff-only` 合併進 `main`**，然後刪除分支（WORKFLOW G5，比照 F11 的先例）。不 push | 採預設（使用者可以改成「合併前一律問我」） |
| D3 | 流程 | 要不要 push 到 `origin` | 由使用者執行，或由使用者明確授權。AI 不會自己 push | 已決定 2026-10-01：使用者授權 push 交接系統（連同 `edf46b6`、`dfc0126`），已完成。2026-10-01 第二次授權：使用者指示「完成後上傳到GIT」，W1 完成並合併進 `main` 後，把 `main` push 到 `origin`。2026-10-02：使用者指示「推上 git」，W1 合併後已把 `main` push 到 `origin`（不 force，只推 `main`）。每次授權都只限該次，之後每次 push 仍要明確授權。2026-10-02 第三次：使用者指示「你這個階段做完就先暫停，幫我 commit and push」，W2 Task 5 完成後 push `main` 和 `feature/w2-departments`（使用者選「推兩個，README 寫在分支」）。2026-10-05：使用者指示「push上去」，Codex 已 push `main` 到 `origin/main`（`8041e14..a2f7e85`），沒有 push 或刪除遠端 feature 分支。2026-10-05：使用者指示「確認後推上去」與「git 上的 readme 也要記得更新進度」，Codex 已 push W3、W5 README 更新與看板收尾到 `origin/main` |
| D4 | F11（W4） | F11-T1-m5：重置 Demo 時要不要把角色重設回 yu | 建議重設回 yu | 已決定 2026-10-05：維持現狀（D30：展示模式下 W4 取消，使用者沒有反對這個提案；使用者可以推翻） |
| D5 | F11（W4） | F11-T4-m2：SVG 附件改成下載，還是用 `<img>` 或 sandbox 顯示 | 建議排除 SVG 預覽，改成下載（安全優先） | 已決定 2026-10-05：維持現狀（D30：展示模式下 W4 取消，使用者沒有反對這個提案；使用者可以推翻） |
| D6 | F11（W4） | F11-T4-m4：附件全部上傳失敗時，回報要不要整份不送出 | 建議先寫入 blob，失敗就不建立回報 | 已決定 2026-10-05：維持現狀（D30：展示模式下 W4 取消，使用者沒有反對這個提案；使用者可以推翻） |
| D7 | F11（W4） | F11-T5-m2：被硬性前置擋下時，要不要保留回報草稿。W1 之後更常發生：有硬性前置的葉任務，在回報卡上就看得到醒目的「回報完成」（W1 整體審查的觀察） | 建議把草稿暫存在 `ui`，跳過前置後自動重開回報對話框 | 已決定 2026-10-05：維持現狀（D30：展示模式下 W4 取消，使用者沒有反對這個提案；使用者可以推翻） |
| D8 | F11（W4） | F11-T6-m1：「部分恢復」要怎麼記錄 | 建議補寫稽核紀錄，並新增 `o.restoredNodes` | 已決定 2026-10-05：維持現狀（D30：展示模式下 W4 取消，使用者沒有反對這個提案；使用者可以推翻） |
| D9 | W3 | W3 流程控制的 brainstorming（spec 內容） | 需要參與問答，AI 不可以自行定稿 | 已決定 2026-10-05：改照 D31，W3 精簡版由 AI 依 D13 甘特圖起草短版 spec，使用者看一次就定稿，不做完整的 brainstorming |
| D10 | P 軌 | README §9 #5–#14（模型硬體、雲端供應商、預設分級、帳號、通知、協作部門權限、ERP 介面、工單、編碼規則、庫存與採購核准） | 正式導入前再決定 | 已決定2026-10-23（使用者在簽核台逐項選擇）：沿用Qwen3 4B＋bge-m3；暫不用雲端；新文件預設「內部」；本地帳號；只用站內通知；協作部門成員全部可見（取代D61，待實作）；ERP介面還不確定；工單由本系統開立後推送ERP（目前為展示）；料號沿用公司規則；庫存採購由ERP負責。另：D43展示先維持現狀；本分支推上GitHub但不合併main；mina201199兩個遠端分支暫不處理，之後比較成果再決定 |
| D11 | Demo軌→正式軌 | 正式產品軌何時啟動 | 依D51啟動P0並做到P1c；保留Demo參照與既有驗收證據，正式版按其階段重新驗收 | 已決定2026-10-08：使用者明確指示「開始做到P1c」；不再等待啟動授權 |
| D12 | W5 | W5 README 中 full demo 的定位文字 | AI 起草，使用者審閱 | AI 代決 2026-10-05：已在 README 頂部、§1、§2 起草 full demo 定位與進度摘要（可推翻） |
| D13 | W3 | 請提供「10 部門流程甘特圖（連接器新產品，6 階段）」的原檔或內容 | 轉寫成 `docs/reference/connector-10dept-gantt.md`，欄位：階段、工作項目、負責部門、關卡／核准人、交付物 | 已由 D41 取代：不再等待原本的連接器甘特圖，先依現有兩份專流表進行 |
| D14 | W1-T1 | **Important（plan-mandated，已修正）**：plan Step 3 的 `.rcard .rc-main{min-width:0;flex:1}` 讓 flex-basis 變成 0，`.rc-row` 的 `flex-wrap:wrap` 永遠不會換行。375px 下動作欄固定佔掉右半邊，文字欄只剩 118–141px，自訂欄位會溢出。已在 `dc50e86` 改成 `flex:1 1 240px`，並加 1 個版面測試，所以 W1 的測試變成 14 個 | **接受 `dc50e86` 的修正**。同意後可以視需要用 `Plan: fix` 同步 plan Step 3 和 Task 2 的預期測試數 | 已決定 2026-10-01：接受修正（使用者選「接受修正（建議）」）。plan 不另外同步，以 W1 執行注意 13 為準 |
| D15 | W1-T1 | §5 W1-T1-m6：F11 原本就有的版面問題。桌面寬度下，紀錄、文件、資料、成員分頁的內容超出畫面時會被截掉，無法捲動。W1 之後葉任務預設進紀錄分頁，上方又多了回報卡，會更常發生。要在 W1 一起修，還是登記到 W4 再修？ | **在 W1 一起修**：這幾個分頁改成整個主區域可以捲動，和手機版一樣，標題和回報卡會跟著捲上去；看板、時程、相依圖維持原樣。放在 Task 2 的修正輪處理，附測試 | 已決定 2026-10-01：在 W1 一起修（使用者選「在 W1 一起修（建議）」），放在 Task 2 的修正輪 |
| D16 | W1-T2 | **Important（plan-mandated，Task 2 品質審查 I1）**：子任務的回報摘要很長時，置頂回報卡會把葉任務的看板、時程、相依圖分頁擠到看不見。plan 的卡片 CSS 沒有高度上限，而 D15 讓這三個分頁維持主區域不捲動。1366×650 實測：摘要 8 行時，時程的內容區高度變成 0；12 行時連分頁列都被推出畫面，切不回紀錄分頁 | **限制卡片摘要高度**：卡片上的成果說明最多顯示約 6 行，超過的部分在卡片內捲動，完整內容在紀錄分頁的「回報歷史」，只改 CSS。其他選項：子任務頁全部分頁都可以捲動（改動較大，也要調整 D15）；維持現狀 | 已決定 2026-10-02：使用者回覆「都照建議」，也就是限制卡片摘要高度。放在 Task 2 修正輪 1，見 W1 執行注意 16 |
| D17 | W1-T2 | Task 2 品質審查 m3(b)（spec 沒有寫到，已實測）：在子任務頁按「＋ 新增子任務」新增第一個子任務後，它會變成上層任務，但畫面仍停在「紀錄」分頁的唯讀彙總，看不到剛新增的子任務 | **新增後切到看板**：原本是子任務、而且停在紀錄分頁時，新增第一個子任務後自動切到「看板」。另一個選項是維持現狀 | 已決定 2026-10-02：使用者回覆「都照建議」，也就是新增後切到看板。放在 Task 2 修正輪 1，見 W1 執行注意 17 |
| D19 | W2-T1 | spec 和 plan 衝突（Task 1 審查 Minor m1，執行注意沒有裁決）：v3 → v4 升級時，模板節點補 `dept` 的順序。spec §3.4(4) 是「有 `who` 取其部門 → 否則模板的第一個 `dp` → 再沒有則 d-rd」；plan Task 1 Step 8（已照做，`e62b39a`）是「`who` → `TAG_DEPT[類別]` → 第一個 `dp` → d-rd」。差別只影響舊 v3 資料升級後的系統模板，例如沒有協作部門的「簽核檢驗費用」，spec 會給研發，plan 給採購；有協作部門的節點，spec 會把協作部門當成負責部門 | **照 plan（維持 `e62b39a`）**：升級後的模板部門和新種子資料一致（`seed()` 的模板也是用 `TAG_DEPT`），不會把協作部門誤當負責部門。spec 文字差異以本條為準，不另外改 spec。另一個選項：照 spec，在 Task 1 修正輪改 `upgrade()` | 已決定 2026-10-02：照 spec（使用者選「照 spec」）。在 Task 1 修正輪 1 改 `upgrade()` 並補測試，見 W2 執行注意 20 |
| D20 | W2-T2 | **Important（plan-mandated，Task 2 spec 審查 I-1）**：`seeTask` 的下層規則。plan（已照做，`ebab1e1`）是「下層任務直接相關，**或下層任務已指派、而且它的上層任務直接相關**」時顯示為路徑；spec §4.1 字面只有「下層任務直接相關」。只在這種結構下不同：ming 負責 t3012 → 底下有未指派的 N（品保）→ N 底下有指派給小安的 D。plan：ming 看得到 N 和 D；spec 字面：ming 看得到 D，卻看不到 D 的父任務 N，D 在看板和時程上點不到（孤兒）。範本帶入負責人（spec §5.5）或 Task 3 的指派操作都可能做出這種結構 | **照 plan**：程式不改，補一個測試釘住這個行為，spec §4.1 的文字差異以本條為準。其他選項：照 spec 字面（會出現點不到的孤兒任務）；或上層規則遇到未指派節點就停（連 D 也看不到，但違反 spec 對已指派任務的上層規則） | 已決定 2026-10-02：照 spec 字面（使用者選「照 spec 字面」）。Task 2 修正輪 1 改 `seeTask`，見 W2 執行注意 23 |
| D21 | W2-T2 | spec 沒有寫的情況（Task 2 兩位審查者 Minor）：使用者**一個專案都看不到**時（例如他負責的任務全部改派給別人）。plan Step 4.2 是退回 `projects()[0]`，會帶到他看不到的專案，露出專案標題、階段列和關卡；另外 AI 副手（`aiAsk`）和會議記錄確認（`openMinutesConfirm`）在非專案頁會因為 `ctxProject()` 是 `undefined` 而出錯。種子資料的 7 個身分都至少看得到一個專案，所以目前不會發生 | **顯示空狀態**：主區域顯示「目前沒有你看得到的專案」，不帶到別人的專案；`ctxProject()` 的呼叫端加防護。放在 Task 2 修正輪，附測試。另一個選項：維持 plan（帶到第一個專案，看板顯示空狀態），只修出錯的地方 | 已決定 2026-10-02：顯示空狀態（使用者選「顯示空狀態（建議）」）。Task 2 修正輪 1 實作，見 W2 執行注意 24 |
| D22 | W2-T2 | spec 沒有寫的情況（Task 2 審查與修正輪的範圍外觀察）：W2 讓「只有相關的人看得到任務」，但有些衍生資訊沒有依可見性過濾。(a) AI 專案問答引用的文件：ming 會看到他看不到的任務的文件名稱和內容（§5 W2-T2-m2，已實測）；(b) 稽核紀錄頁、總覽的人員／部門負載、看板卡片進度和子任務數、時程的採購單交期列，會露出看不到的任務的存在、負責人或數量（§5 W2-T2-m3）。W2 之前就是這樣 | **(a) 在 W2 整體修正時改成依 `can('view')` 過濾**（AI 只引用看得到的任務的文件）；**(b) 維持現狀**，之後另外排工作項目。不擋 Task 3–7，W2 改成 🟢 之前要有結論 | 已決定 2026-10-02：都維持現狀（使用者選「都維持現狀」）。(a)(b) 都不在 W2 處理，§5 W2-T2-m2、m3 留給之後的工作項目 |
| D23 | W2-T3 | spec 沒有寫的情況（Task 3 品質審查 I-2，已實測）：審核人的「修改時程」權限（spec §4.4：不變）和任務對話框。Task 3 之後，審核人對不是自己負責、也不是自己主管部門的任務，`can('edit')` 是 false、`can('schedule')` 仍是 true。實測陳主管開 t30121：開始、結束日期和鎖定欄位可以改，儲存鈕卻是停用的，畫面寫「唯讀」，改了存不下來；時間軸拖曳仍然可以改時程。W2 之前審核人可以在對話框存時程 | **對話框可以只存時程**：沒有編輯權、但有時程權時，儲存鈕可用，儲存時只寫入開始、結束日期和鎖定，其他欄位不動。放在 Task 3 修正輪，附測試。另一個選項：對話框的日期和鎖定也改成唯讀，只能用時間軸拖曳改時程 | 已決定 2026-10-02：使用者回覆「不是他負責也不是他部門，就不關他的事啊，不能做其他動作」，追問範圍後選「只拿掉時程（建議）」。**任務**的修改時程改成和 `canWork` 一樣（負責人本人、負責部門主管、專案負責人、系統管理員），審核人不能再改別人任務的時程（對話框和時間軸拖曳都不行）；階段本身的時程、設定前置條件、範圍內的關卡核准、跳過申請核准、回報確認都照舊。這一點推翻 spec §4.4「reviewer 不變」，以本條為準。Task 3 修正輪 1 實作，見 W2 執行注意 26 |
| D24 | W2-T3 | spec 沒有寫的情況（Task 3 spec 審查 Minor 5）：誰可以寫筆記。spec §4.2 只寫「協作人員與協作部門主管照舊可以新增筆記」。照 plan 的 `canNote`，範圍內的審核人（例如陳主管對 t30121）**不能**再寫筆記，除非他是協作人員或部門主管；W2 之前審核人可以在任何任務寫筆記 | **允許範圍內的審核人寫筆記**（和 W2 之前一樣；他們看得到這些任務，也負責關卡）：`canNote` 加上 `inReviewerScope(n)`。放在 Task 3 修正輪，附測試。另一個選項：照 plan，審核人只有在是協作人員或部門主管時才能寫筆記 | 已決定 2026-10-02：允許範圍內審核人（使用者選「允許範圍內審核人（建議）」）。Task 3 修正輪 1 實作，見 W2 執行注意 27 |
| D25 | W2-T3 | spec 沒有寫的情況（Task 3 修正輪 scoped re-review 的範圍外觀察）：時間軸的「連動順延」（`cascadeFrom`／`shiftSubtree`）在某人改了自己任務的時程後，會自動順延**別人負責**的後續任務，不檢查 `can('schedule')`。D23 決定「不是他負責也不是他部門，就不能改時程」，但連動會間接改到別人的任務。W2 之前就是這樣，有稽核紀錄 | **維持現狀**：連動是依前置條件自動保持時程一致，不算個人修改。另一個選項：連動遇到沒有時程權的任務就停下來，並提示要請負責人或主管處理 | 已決定 2026-10-02：遇到沒權限的任務就停（使用者選「遇到沒權限的任務就停」）。連動碰到操作者沒有時程權（`can('schedule')`）的任務就停下來，提示要請負責人或部門主管處理。放在 W2 整體修正，附測試。**2026-10-05 改為取消，維持現狀**（使用者選「取消，維持現狀（建議）」，D30 展示模式）：連動順延照舊，不在 W2 實作 |
| D26 | W2-T4 | spec 沒有寫的情況（Task 4 品質審查 Minor 7）：部門主管可以選任何部門成員，包括協作人員（collab，例如業務部的小林）。主管有 `canWork` 和可見性的權限，所以小林被設成業務主管後，就能操作業務部所有的任務、看到未指派的業務任務 | **主管只能選成員、審核人、專案負責人這類角色，排除協作人員和唯讀**：`updateDept` 拒絕並提示，對話框的主管下拉不列出他們。放在 W2 整體修正，附測試。另一個選項：維持現狀（任何部門成員都能當主管） | 已決定 2026-10-02：排除協作人員與唯讀（使用者選「排除協作人員與唯讀（建議）」）。放在 W2 整體修正，附測試。**2026-10-05 改為取消，維持現狀**（使用者選「取消，維持現狀（建議）」，D30 展示模式）：任何部門成員都能當主管，不在 W2 實作 |
| D27 | W2-T4 | spec 文字不準確（Task 4 spec 審查 Minor 1）：部門面板「未設主管」的提示文字照 spec §5.1 寫「這個部門的未指派工作只有專案負責人看得到」，但依 Task 2 的可見性，系統管理員（和唯讀）也看得到 | **改成「這個部門的未指派工作只有專案負責人與系統管理員看得到」**，放在 W2 整體修正。另一個選項：維持 spec 原文 | 已決定 2026-10-02：維持 spec 原文（使用者選「維持 spec 原文」），不改 |
| D18 | W1-T2 | §5 W1-T2-m9（Minor，兩位審查者第 2 輪都提到）：D16 只限制了卡片上的成果說明。自訂欄位、退回意見、跳過理由很長或很多時，卡片仍會把葉任務的看板、時程、相依圖擠到看不見。1366×650 實測：自訂欄位達 2 個時，時程的內容區變成 0；達 3 個時，看板和相依圖也是 0，時程的分頁列超出畫面 | **一起限制高度**：自訂欄位最多顯示約 4 列，退回意見和跳過理由最多約 4 行，超過的在卡片內捲動，完整內容在紀錄分頁的回報歷史，只改 CSS。另一個選項：維持現狀（目前種子資料和系統模板的欄位都只有 0–1 個） | 已決定 2026-10-02：維持現狀（使用者回覆「D18 維持現狀」）。W1-T2-m9 改列 BY_DESIGN，要改需要另外排工作項目 |
| D28 | W2（流程） | `origin/main` 已經用 GitHub PR #1 的 merge commit `8041e14`（2026-10-05 09:07，parents `670afaf`、`079b035`）合入 W2 Task 1–5 的草稿。這不符合 G5（整體審查後才合併、只用 ff、不建 merge commit）和「有 `feature/*` 分支時 `main` 凍結」。W2 要怎麼繼續？ | **接受，分支跟上**：`feature/w2-departments` 用 `git merge --ff-only origin/main` 前進到 `8041e14`（程式和 `079b035` 相同，只多一個 merge commit），照原流程在分支上做 Task 6、7 和整體審查，完成後再 ff 合併回 `main`。另一個選項：在 GitHub 上 revert | 已決定 2026-10-05：接受，分支跟上（使用者選「接受，分支跟上（建議）」）。已 ff 到 `8041e14`，見 W2 執行注意 33 |
| D29 | W2（流程） | 本機 `main` 有 2 個從沒 push 的 commit（`6c39df8 Progress: note 8001 test server stopped`、`4ed2ab5 Progress: note LAN share server for the demo`，2026-10-02），和 `origin/main` 分岔（ahead 2、behind 27），無法 fast-forward。內容是 8001 測試伺服器已關、8080 區網分享伺服器在跑；2026-10-05 實測兩台都不在 | **捨棄，對齊 `origin/main`**：先留備份 tag，再把本機 `main` 指到 `origin/main`；還有用的事實改寫進分支看板。另一個選項：在本機 `main` 建 merge commit 並解 PROGRESS 衝突（違反 ff-only） | 已決定 2026-10-05：捨棄，對齊 `origin/main`（使用者選「捨棄，對齊 origin/main（建議）」）。已建本機 tag `backup/local-main-2026-10-02`（指向 `4ed2ab5`，沒有 push），用 `git branch -f main origin/main` 把 `main` 移到 `8041e14`；8001、8080 的現況寫進 W2 執行注意 17 |
| D30 | 全專案（流程） | 使用者 2026-10-05 指示：「我這個專案是展示用的，先以完成主要功能能使用為主，不用花太多時間在細節的修飾。以最快的速度完成整個專案，這樣需要修改哪些任務目標」 | AI 提案：(1) 流程改成展示模式（WORKFLOW §13）：一位審查者、最多一輪修正、只擋會讓展示出問題的錯誤、不補強測試也不做變異 RED，保留 TDD 和硬性規則；(2) W2 照做 Task 6、7，整體修正只修 4 個看得到的問題（執行注意 32），驗收精簡；(3) W3 見 D31；(4) W4 取消，F11-N1 併入 W2，D4–D8 維持現狀；(5) W5 只改 README §1、§2；(6) Demo 完成條件跟著精簡（§1 第 4 點）；正式產品軌不在範圍內 | 已決定 2026-10-05：使用者對提案回答了 D31–D33，並選 D25、D26「取消，維持現狀（建議）」，其餘部分沒有反對，照提案執行。WORKFLOW §13、AGENTS §5、CLAUDE.md、`/pf-next` 已經同步改成展示模式 |
| D31 | W3 | W3 流程控制原本 7 項（關卡硬性擋住後續階段、範本指定核准人、總經理角色、強制通過關卡與略過整個階段、完成報告必附交付物、連接器範本與示範專案、資料升到 v5），要做到什麼程度 | **精簡版**：只做連接器 6 階段範本與示範專案，加上關卡擋住後續階段；其他延到正式版。spec 由 AI 依甘特圖起草，使用者看一次。其他選項：W3 整個不做；照原本 7 項 | 已決定 2026-10-05：精簡版（使用者選「精簡版（建議）」）。見 §3 W3 |
| D32 | 全專案（流程） | spec 沒寫到的小細節，AI 可以自己照建議做、事後再給使用者看嗎 | **可以**：記進 §6，狀態寫「AI 代決 YYYY-MM-DD：…（可推翻）」，不標 ⛔，不停下來。範圍、資料版本、新 spec、push 仍然要問。另一個選項：照舊停下來問 | 已決定 2026-10-05：可以，事後給我看（使用者選「可以，事後給我看（建議）」）。見 WORKFLOW §13 |
| D33 | 全專案（流程） | 展示會用手機看嗎？（決定展示模式要不要保留 375px 檢查） | 建議只用電腦展示，不再檢查 375px。另一個選項：手機也要能看 | 已決定 2026-10-05：**手機也要能看**（使用者推翻建議）。每個 Task 和驗收都保留 375px 沒有水平捲動的檢查 |
| D34 | W2-T6 | spec 沒寫到的小細節（Task 6 implementer concern、審查 m1）：時程分頁的部門篩選列放在 `height:100%` 的 `.tl` 前面，桌面版 `.tl` 會超出 `.view` 約 40px，下緣和橫向捲軸被 `.main{overflow:hidden}` 裁掉（實測修正前 `.tl` 下緣 920 > `.main` 900） | **只用 CSS 讓有篩選列的 `.view` 改成直向 flex**：`.view:has(> .deptbar){display:flex;flex-direction:column}`、`.deptbar + .tl{flex:1 1 0;min-height:0;height:auto}`，`.deptbar` 加 `flex-shrink:0`，不改 plan 規定的 HTML 結構。缺點是依賴 `:has()`，舊版 Firefox／Safari 沒有退路（§5 W2-T6-m2）。另一個選項：時程分頁的 `.view` 加 class，或用容器包住篩選列和 `.tl` | AI 代決 2026-10-05：有篩選列時 `.view` 改成直向 flex、`.tl` 吃剩下的高度（`7939a66`；桌面 `.tl` 下緣等於 `.view` 下緣，375px 篩選列換 3 行時 `.tl` 仍有 306px 可捲動）（可推翻） |
| D35 | W2-T6 | spec 沒寫到的小細節（Task 6 implementer concern、審查 m1）：手機版（≤860px）的 `.tl-label` 只有 150px，階段列的件數「▸ N 件」會把階段名稱擠到只剩 3px，名稱完全看不到 | **手機版隱藏階段件數**：在 `@media (max-width:860px)` 加 `.tl-label .cnt{display:none}`，名稱寬度回到改動前（47px），件數仍可以在篩選列看到。這和 spec §5.4「階段列上顯示 ▸ N 件」在手機上不一致。另一個選項：縮短件數文字或加寬標籤欄 | AI 代決 2026-10-05：寬度 ≤860px 時不顯示階段列的件數（`7939a66`）（可推翻） |
| D36 | W2-T7 | spec 沒寫到的小細節（Task 7 implementer concern）：README §2 功能表新增「我的任務｜✅ 可用」列之後，原本的「其他｜分享、總覽、我的任務、AI 收件匣｜⬜ 未實作」會和它直接矛盾 | **從「其他」列拿掉「我的任務」**，只刪一個詞，不算大改 §2（執行注意 7）。另一個選項：保留原列不動 | AI 代決 2026-10-05：「其他」列改成「分享、總覽、AI 收件匣」（`03c9ff5`）（可推翻） |
| D37 | W2-T7 | spec 沒寫到的小細節（Task 7 implementer concern）：README §2 表沒有獨立的「我的任務」列，也沒有部門的列（執行注意 7 要用新增的方式），新列要怎麼寫 | **新增兩列**：「我的任務｜跨專案列出我負責的、我協作的任務；部門主管有「待我指派」｜✅ 可用」、「部門（F6）｜部門設定與負責部門｜✅ 可用」 | AI 代決 2026-10-05：照建議新增兩列（`03c9ff5`）（可推翻） |
| D38 | W2-T7 | spec 沒寫到的小細節（Task 7 implementer concern）：README F5 權限表的「修改時程」列要反映 D23，各角色欄的文字 | **照 `can('schedule')` 寫**（任務走 `canWork`，非任務照舊）：系統管理員 ✅、專案負責人 ✅、階段審核人「階段；任務限自己負責或主管部門的」、成員「自己負責或主管部門的任務」、協作人員「自己負責的任務」、唯讀空白。同表的「新增 / 編輯任務」列也受 `canWork` 影響，但執行注意 31 只點名「修改時程」，這次沒改（§5 W2-T7-m2） | AI 代決 2026-10-05：照建議（`03c9ff5`；審查者對照 html `can('schedule')` → `canWork` 確認正確）（可推翻） |
| D39 | W2-T7 | spec 沒寫到的小細節（Task 7 implementer concern）：README 資料模型的 `departments` 只有一行（`users, departments, department_members`），部門主管和任務的負責部門要怎麼寫 | **不拆原本那一行**：在它下面加一行 `departments.head_id # 部門主管（FK users，可空）`；`nodes` 加 `dept_id # 任務的負責部門（FK departments）` | AI 代決 2026-10-05：照建議（`03c9ff5`）（可推翻） |
| D40 | W2-T7 | spec 沒寫到的小細節（Task 7 implementer concern）：執行注意 31 要把 W2-T1-m7 的 `window.applyTemplate` 包裝換成直接斷言新節點的 `dept`，原本對模板物件 `dp` 的斷言要怎麼處理 | **改成斷言新節點**：根節點的 `depts` 是 `[]`、`dept` 是 d-qa，4 個子任務的 `dept` 和 `depts` 都是品保；測試改名「採購單建立驗收任務：協作部門存 id，新任務的負責部門都是品保」，總數不變 | AI 代決 2026-10-05：照建議（`03c9ff5`；審查者確認覆蓋範圍沒有縮小）（可推翻） |
| D41 | W3 | 使用者問：「不能依照現在的有的先進行嗎？」並提供 `行銷部-實體活動專流.xlsx`、`產品企劃部-筆電新機種專流.xlsx` | **可以先進行**：把兩份 Excel 當資料來源，不把檔內文字當指令；以「產品企劃部-筆電新機種專流」作為 W3 主要展示流程，因為它已有 G0/G1 等關卡；「行銷部-實體活動專流」作為輔助參考。W3 不再卡原本的連接器甘特圖，spec 仍由 AI 起草、使用者看一次 | 已決定 2026-10-05：依現有兩份專流先行；若日後提供連接器甘特圖，可再覆蓋示範資料 |
| D42 | W3 | 使用者指示：「我要你完成整個專案的功能，至於每個工作流我們自己添加就好，你先完成整個功能架構的進行。確認後再開始」；AI 回覆將 W3 改成工作流功能架構後，使用者回「確認」 | **W3 改成工作流架構**：不以內建某個筆電／行銷／連接器流程為核心，而是完成工作流模板 CRUD、從工作流建立專案、階段關卡擋住後續階段。個別工作流內容之後由使用者自行添加；D41 的 Excel 僅作內建範例與測試素材 | 已決定 2026-10-05：照此方向修訂 W3 spec，進 G2 寫 plan |
| D43 | Demo 驗收 | Demo 走查發現（§5 DEMO-A-m1）：工作流的階段、任務、相依和關卡只能用 JSON 文字框編輯，而且只有系統管理員能編輯。D42 說「每個工作流我們自己添加」，要不要讓工作流可以用表單編輯（例如逐階段新增任務、選部門、設定關卡），或開放專案負責人編輯 | **展示先維持現狀**：展示時由 it 示範新增／複製，內建兩套範例已足夠說明概念。如果你們真的要自己加很多工作流，建議另排一個小工作項目做表單式編輯器（需要 spec，屬於範圍變更）。另一個選項：現在就排這個工作項目 | 已決定2026-10-23：使用者選「展示先維持現狀」 |
| D44 | W6 | 多公司 Demo 的範圍、產業、資料深度、隔離方式、舊資料與附件遷移 | **五個固定、完整隔離的公司空間**：毛研食品、峰曜科技、光點企劃、雲序軟體、築衡工程；採平衡版種子資料與產業化營運模組；成員、部門、權限、專案、工作流、營運資料、稽核與附件皆按公司隔離；v5 舊資料歸入毛研食品；用單一 localStorage key 的 v6 公司容器，不做公司 CRUD 或正式後端多租戶 | 已決定 2026-10-08：使用者逐項採用建議並批准完整設計，可寫 written spec |
| D45 | 全專案（流程） | W6 和目前 `feature/p0-formal-product-plan` 的優先順序 | **先暫停 P0 規劃，優先完成 W6**；保留 P0 的 spec、plan 與 commit，W6 完成後恢復 | 已決定 2026-10-08：使用者批准 W6 完整設計時同意此執行順序；P0 分支已保留為 `paused/p0-formal-product-plan` |
| D46 | W6 執行 | W6 plan 的執行方式 | 由目前 session 依 Task 0–6 直接實作；主 checkout、每 Task TDD 與審查、PROGRESS 為唯一進度來源 | 已決定 2026-10-08：使用者選擇「Native execution」，授權開始 W6 plan |
| D51 | 正式版啟動 | 使用者指示「開始做到P1c」 | 授權完整P0→P1a→P1b→P1c的正式版MVP實作與必要規則轉換；不是僅恢復規劃。沿用React／FastAPI／PostgreSQL／Docker Compose、核心工作流與公司隔離要求。逐階段補齊可執行計畫、TDD與獨立審查；D50每段更新README並push繼續有效。P2以後非目標不自動納入 | 已決定2026-10-08。先前文件中的「未授權實作」已由本項取代；新計畫的使用者審閱關卡保留，不能跳過或把草稿當可執行計畫 |
| D52 | P0計畫審閱 | 使用者回覆「好開始」 | 確認2026-10-08-p0-formal-foundation計畫，立即Native執行Task1–3；正式軌按完整安全／獨立審查標準驗收 | 已決定2026-10-08；解除P0計畫待審閱 |
| D53 | P1a執行方式 | 使用者指示「繼續進行，我只會審核成品的部分，中間你可以自己進行，除非有重大的東西需要詢問」 | 確認P1a計畫可進入Native執行；中間Task由AI自行依計畫TDD與審查流程推進，不逐步請審閱。遇到重大範圍變更、安全敏感、plan無法照做、破壞性操作、遠端／合併異常等WORKFLOW §8仍停下來問 | 已決定2026-10-08；解除P1a plan待審閱 |
| D54 | P1c後續方向 | 使用者選取四階段Demo功能移植建議並指示「開始進行」 | 按完整任務操作→回報協作→時程流程→其餘Demo模組推進；先P2a。不是完整產品功能已完成，真AI／ERP另定範圍 | 已決定；2026-10-08直接授權開展G1，不代替新spec／plan審閱 |
| D55 | P2a G1 | WORKFLOW §8新spec與新增日期資料模型／編輯流程需要設計確認 | 建議第一階段包含工作區、總覽、我的任務、任務新增／編輯、負責人／部門／起迄日期；以migration保留資料，其他模組後續處理 | 2026-10-08使用者明確指示「依 docs/formal-feature-roadmap.md 繼續 P2a 規格與計畫」，已授權撰寫兩份文件；當時僅授權撰寫，後續產品規則及G1／G2已依D56核准 |
| D57 | P2a G3環境 | 本機缺Node/npm、Docker Desktop／WSL，無法跑計畫要求的隔離Compose、E2E與真PostgreSQL migration基準 | 補齊Node24與Docker Desktop Linux容器環境（可能需管理員與重啟），或切換已有Docker環境；未取得完整基準不開始產品實作，不把工具缺失當RED | 已決定2026-10-08：使用者選擇在本機補裝環境；授權安裝Node24、Docker Desktop／WSL。已補齊repo-local Python鎖版依賴並通過API80；已確認WSL2.7.13／Docker29.8.2引擎可用，完整隔離G3基準API80／Vitest56／E2E6／build exit0，環境阻塞解除 |
| D56 | P2a spec／plan審閱 | 新增／改派、一般編輯權限、層級、日期及完成率如何定案 | 推薦spec §2整組：管理者新增／改派，可見且可操作者編輯名稱日期；日期可空；完成率done/(task-skipped)，只計可見task；保留既有讀／status／Gate角色政策 | 已決定2026-10-08：使用者同意spec與plan並採用整組建議；管理者新增／改派，可見且有操作權限者編輯名稱日期，日期可空，完成率只計可見task之done/(task-skipped)。授權逐Task TDD、獨立審查、隔離驗收、更新README／PROGRESS並push；保留資料，不代勾使用者簽核。 |
| D50 | 全專案發布 | 使用者指示「做完一段就推上去github，然後每個階段都要更新readme，讓所有人知道目前進度在哪」 | 持續授權每個已完成且驗證／審查通過的階段：同步README與PROGRESS、依既有流程ff-only合併到main、`git push origin main`。不force、不推其他分支、不自動開PR；授權發布不等於授權尚未確認的產品範圍。此後階段推送不必逐次重問，直到使用者更改指示 | 已決定2026-10-08；涵蓋本次P0規劃文件恢復與先前尚未發布的W6。D3的每次需另行授權由本項持續授權滿足；遠端分岔仍依§8確認 |
| D49 | P0 恢復規劃 | 舊paused分支與main分岔，無法ff恢復最新基準 | 保留paused分支，從最新main建立feature/p0-formal-product-plan，僅帶回既有spec／plan後對齊W6；以新規劃分支為主，檢查後ff-only合併回main。不rebase、不覆蓋W6、不push | 已決定2026-10-08：使用者回答「是，並且以此分支為主，合併回去main」。只授權規劃分支恢復與本地合併，不視為授權正式產品實作 |
| D48 | W6 Task 6 審查 | 新公司沒有配方比例權限，既有機密文件判斷因此讓所有角色都無法再開啟已存文件 | 毛研保留原有 ratio 判斷；新公司機密文件限目前公司 owner／admin 且節點可見者開啟，其他角色維持拒絕。新公司 ratio 仍為 false，不借用毛研欄位權限 | AI 代決 2026-10-08（可推翻）：展示模式最小修正，修復文件被永久鎖住；自動化覆蓋四公司建立、儲存、重新開啟與未授權拒絕 |
| D47 | W6 Task 2–3 | plan 測試的空殼節點、Gate／deps 模型及範例命名與 spec 不完全相同 | 切換選第一個可見專案（空殼才 null）；Gate 驗證 `db.gates`、前置驗證 `db.deps`。專案／工作流範例名稱依 plan 明列值；毛研保留既有兩工作流與測試錨點，其他公司採產業專屬工作流。介面相依 T1→T2/3→T4→T5/6 的公司投影、ops 設定與附件鍵已核對一致 | AI 代決 2026-10-08（可推翻）：展示模式的小差異，以既有資料模型與保留毛研相容性為準；不增加功能或改變公司範圍 |

---

## 7. 交接紀錄（最新的在最上面，只保留最近 5 筆，更舊的從 git 歷史查）

### 2026-11-05｜Claude Code（Opus 5.5）｜TEXT2SQL-LEARNING

- **做了什麼**：使用者對照簡報與程式碼後「照建議開工」，依計畫完成Task 0–3並開PR（不合併）；詳見§2 TEXT2SQL-LEARNING。開分支前把本機main `--ff-only`到origin `a2c82dd`（kayla162的n8n設定），本機PROGRESS紀錄stash後apply，stash保留未drop。
- **驗證**：見▶ 現在的測試基準。
- **沒做的事**：專用PostgreSQL與Playwright未跑；這台缺python-docx，文件範本相關19個測試無法在本機驗證；未部署到15173。
- **注意**：PPT第25–31頁換成最終版另開session處理，輸出在使用者Downloads（`專流 ProjectFlow_1104_資料分析最終版_v2.pptx`），不在repo。

### 2026-11-04｜Claude Code（Opus 5.5）｜TEXT2SQL-FALLBACK

- **做了什麼**：見§2 TEXT2SQL-FALLBACK。分支`feature/text2sql-fallback`，未合併、未推送。
- **驗證**：見▶ 現在的測試基準。
- **沒做的事**：模型開的量測（這台沒有對話模型）；專用PostgreSQL與Playwright未跑（只改AI服務與副手面板）；README未更新。
- **注意**：這台git沒有設定user，commit用`-c user.name=lee851104 -c user.email=lee851104@gmail.com`（與repo近期commit同身分，未改設定）；`api/.venv`與`web/node_modules`為本次照lock新建。

### 2026-11-02｜Claude Code（Opus 5.5）｜同步git、D88、RAG-PORT

- **做了什麼**：使用者「把git上面的同步下來」：本機main有3個未push的PROGRESS commit與origin分岔，依使用者「備份後對齊遠端」保留在`backup/main-local-1028`後對齊origin/main，再`--ff-only`到`1f9cf2e`。比對LEE（main的AI助手）與Mina（PR #5 RAG-V1）後，使用者決定以LEE版為主體移植Mina的五項（D88），核准短規格後完成RAG-PORT，`--ff-only`合併main並依D50 push origin main（見§2）。
- **驗證**：見▶ 現在的測試基準。隔離預覽資料在ignored `.superpowers/rag-port/`。
- **沒做的事**：15173只部署RAG-PORT所需設定，OCR與n8n沒開；`origin/feature/review-fixes`、`codex/rag-quality-handoff`沒動（該分支合併後的`main.py`、`App.tsx`、`CopilotPanel.tsx`本身有語法錯誤）；`backup/main-local-1028`保留未刪。
- **注意**：這台`api/.venv`缺lock裡的套件（pypdf等），已照`api/requirements.lock`補裝。

### 2026-10-27｜Claude Code（Opus 5.5）｜合併 feature/rag-starter-import 進 main

- **做了什麼**：使用者指示「推上GitHub，開PR合併進main」，接著指示「照WORKFLOW G5在本地用--ff-only合併進main，然後push origin main」。先推分支（`ae332ad..72e0d8d`）並開[PR #6](https://github.com/chenliyu0410/projectflow/pull/6)，確認origin/main仍是`3c1294e`、為分支祖先，再`git merge --ff-only`（無merge commit），最後在main做這筆G6收尾並push。
- **驗證**：合併前完整pytest 804 pass／14 skip、exit 0（見下一筆）。repo沒有設定CI。
- **沒做的事**：沒有部署；沒有刪除遠端分支；Vitest／E2E與PostgreSQL本輪未重跑。

### 2026-10-27｜Claude Code（Opus 5.5）｜UTC-TIME 修正SQLite時間少8小時

- **做了什麼**：使用者直接指示「先修」TEMPLATE-TRIAL發現的時間少8小時。根因：SQLite存`DateTime(timezone=True)`時丟掉時區，讀回是無時區值，`.isoformat()`沒有`+00:00`，瀏覽器當成本地時間。PostgreSQL回傳含時區，不受影響。`models.py`新增`UTCDateTime`（寫入轉UTC、讀回無時區補UTC），43個時間欄位改用它，所以文件版本、通知、稽核、附件等約20處輸出一次修正；`records`／`ai`原有的個別補丁保留（冪等）。`demo_pack.decode`改為先拆`TypeDecorator`再判斷時間欄位。不改schema、不加migration。
- **驗證**：`test_version_times_are_explicit_utc`先RED（`utcoffset()`為None）再GREEN。完整pytest（從repo根目錄）804 pass／14 skip、exit 0；第一次在`api/`目錄跑有19個相對路徑失敗（alembic script_location、`web/src/progress.vectors.json`），改根目錄後通過，另5個`demo_pack`失敗為本修正引起並已修。15176重啟API後實看：10/27產生的會議紀錄顯示下午2:48:14（原上午6:48），與瀏覽器現在時間一致。
- **沒做的事**：Vitest／E2E未跑（前端未改）；PostgreSQL未實測（只靠既有含時區行為）；未push。
- **注意**：pytest要從repo根目錄執行；本機`%TEMP%\pytest-of-User`無權限時加`--basetemp`。

