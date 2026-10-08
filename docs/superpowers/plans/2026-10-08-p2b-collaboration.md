# P2b Collaboration Implementation Plan

**狀態：G2定稿（2026-10-08，D64）。** D59–D63的A方案已由人類逐項核准，完整spec／plan雙獨立文件審查通過；人類指示繼續實作，以Demo操作效果為主，遇到問題再問。進度只記PROGRESS，不在本檔打勾。

**Goal:** 交付回報送審／退回／確認、筆記、指定協作、持久附件、審核中心與安全稽核，保留P2a及既有資料。

**UI參照:** 定位Demo的回報卡、紀錄時間軸、附件列及審核中心，僅讀相關片段及畫面；在React實現相近的資訊層次、狀態提示與操作感，不移植Demo前端授權或假資料。桌面／375px實際驗證效果。

**Architecture:** FastAPI共用policy context與服務處理交易；PostgreSQL列鎖／唯一約束保護並行，附件採預留配額＋持久volume＋可恢復pending狀態；React拆紀錄與審核組件、沿序號／AbortController。內部路徑無/api，外部經Nginx。

## Global Constraints

- 授權範圍只含spec D59–D63 A；自訂欄位延P2c，跳過申請／Gate覆寫／子樹批次不做。不修改Demo或tests/，不做LAN部署。
- 已獲人類授權，G3先跑隔離基準：主checkout、單一writer、`feature/p2b-collaboration`、main凍結、ff-only。每Task另一位spec reviewer與另一位quality reviewer，Critical／Important全修，最多兩輪；Task結束立刻PROGRESS-only commit。
- 僅下列File Structure；新增migration0003，不改0001／0002，不重設seed／DB／volume，不覆寫.env；不新增依賴／改lockfile。附件用raw bytes，不需multipart套件。
- API每次驗公司／可見／動作權限；Gate原權限不擴張。React安全文字、繁體中文；不回傳密碼／session／storage_key／內部路徑。
- 真實RED/GREEN摘要／名稱／exit code；工具或fixture設定錯誤不是功能RED。已實作後新增驗收用例如實記回歸，不破壞產品製造RED。
- 自動化一律隔離marker＋拒絕15173，檔案與DB都隔離；每次保留primary snapshot／.env，不向primary跑業務測試。

## File Structure（允許清單，路徑相對repo）

```text
api/app/models.py
api/app/schemas.py
api/app/permissions.py
api/app/main.py
api/app/routes/projects.py
api/app/routes/reports.py
api/app/routes/workspace.py
api/app/routes/audit_logs.py
api/app/routes/records.py                  # 新
api/app/routes/collaborators.py            # 新
api/app/routes/attachments.py              # 新
api/app/services/node_policy.py
api/app/services/record_policy.py          # 新
api/app/services/report_service.py         # 新
api/app/services/attachment_store.py       # 新
api/app/services/attachment_recovery.py    # 新，運維命令
api/alembic/versions/20261008_0003_p2b_collaboration.py
api/tests/conftest.py
api/tests/test_migrations.py
api/tests/test_health.py
api/tests/test_projects_nodes.py
api/tests/test_node_metadata.py
api/tests/test_workflows_gates.py
api/tests/test_workspace.py
api/tests/test_reports_audit.py
api/tests/test_mvp_acceptance.py
api/tests/test_deployment.py
api/tests/test_record_permissions.py       # 新
api/tests/test_report_lifecycle.py         # 新
api/tests/test_notes_collaborators.py      # 新
api/tests/test_attachments.py              # 新
api/tests/test_review_audit.py             # 新
api/tests/test_collaboration_postgresql.py # 新
web/src/App.tsx
web/src/App.test.tsx
web/src/api.ts
web/src/types.ts
web/src/styles.css
web/src/components/WorkspaceShell.tsx
web/src/components/NodeWorkspace.tsx
web/src/components/MyTasks.tsx
web/src/components/ReportPanel.tsx         # 新
web/src/components/RecordTimeline.tsx      # 新
web/src/components/NoteEditor.tsx          # 新
web/src/components/AttachmentList.tsx      # 新
web/src/components/CollaboratorEditor.tsx  # 新
web/src/components/ReviewCenter.tsx        # 新
web/src/components/AuditLogView.tsx        # 新
web/src/workspace.test.tsx
web/src/node-editor.test.tsx
web/src/records.test.tsx                   # 新
web/src/review-audit.test.tsx              # 新
web/e2e/health.spec.ts
web/e2e/mvp.spec.ts
web/e2e/workspace.spec.ts
web/e2e/collaboration.spec.ts              # 新
web/e2e/attachments.spec.ts                # 新
web/playwright.config.ts
deploy/docker-compose.yml
deploy/api.Dockerfile
deploy/nginx.conf
deploy/start.py
deploy/verify.py
README.md
docs/formal-development.md
docs/mvp-trial-checklist.md
docs/PROGRESS.md
```

api.Dockerfile只增加固定非root UID/GID及files目錄ownership；不修改套件依賴。既有測試只有受新契約影響處才調整，不刪除公司／Gate／狀態拒絕與副作用斷言。未明列檔案先按WORKFLOW處理；spec／plan修訂與PROGRESS沿AGENTS例外。

## 測試方式：見 WORKFLOW §5

repo根目錄，沿正式開發指南現有鎖版環境：

```powershell
api/.venv/Scripts/python.exe -m pytest -c api/pyproject.toml api/tests -q
npm.cmd --prefix web test
npm.cmd --prefix web run build
api/.venv/Scripts/python.exe deploy/verify.py
```

G3重跑歷史基準182 API＋專用PG另驗、96 Vitest、9 E2E與build，不能拿P2a歷史log替代。專用PG測試使用新建`p2b_test_<uuid>` DB及獨立temp檔案目錄，環境變數只在子程序內，禁止列印DSN；沒有專用URL時條件skip必須另有真PG實跑證據。PG庫名與acceptance marker雙重護欄，不能降版現有acceptance／primary。

每Task預期是基準＋新案例，不固定最終總數。資料新增用唯一名稱；一般完整verify可沿原冪等seed，但停機／重啟持久化驗收不能seed。cleanup不得帶-v；files與pgdata都保留。

## Task 1 — 保留資料migration、協作可見policy

**Files:** models、schemas、permissions、services/node_policy、record_policy、新migration；routes/projects／workspace（接共用policy）；test_migrations、test_record_permissions、test_workspace、test_node_metadata、conftest。

**Interfaces:** spec §5／§6；新增全部模型及Node.collaborators_revision，record policy提供can_submit_report／can_review_report／can_write_record／is_collaborator與批次context。所有can_view_node呼叫點必須同步，以免UI與records授權分叉；status can_work_node不因協作擴張。

**Steps:**
1. 記BASE；先在Task8允許的collaboration.spec.ts寫送審→退回→重送→確認關鍵旅程，在隔離環境取得缺介面的真RED（先獨立commit）。
2. 本Task先寫migration舊回報／日期／audit逐值保留、協作直屬節點／部門主管／readonly／跨公司、總覽與本人去重／查詢數測試，跑目標pytest取得RED。
3. migration0003新增模型、nullable新回報欄位與新流程條件約束，不改舊status/result。當前資料無附件，quota初始化0；既有遷移測試保留原意，新增0002→head真PG保留測試，不靠改預期掩蓋回歸。
4. 實作共用policy與batchcontext，更新詳情／capabilities／metadata／overview／my-tasks所有讀路徑，協作只擴读／紀錄資格不擴can_work。真PG驗unique／FK／CHECK。
5. 目標及全API GREEN；獨立雙審，PROGRESS。

**Commit:** `P2b task 1: preserve records and add collaboration policies`

## Task 2 — 回報審核與task生命週期

**Files:** schemas、routes/reports／projects、services/report_service／record_policy／node_policy；test_report_lifecycle、test_reports_audit、test_workflows_gates、test_projects_nodes、test_health、test_mvp_acceptance、test_collaboration_postgresql。

**Interfaces:** spec §5矩陣及§7 reports/review/lifecycle；Node列鎖＋部分唯一索引防並行。拆出不依todo來源的pending Gate查詢，既有Gate授權不改。

**Steps:**
1. RED：角色矩陣、自審拒絕／明確管理者自核、退回理由、新版本、舊submitted拒review、legacy review恢復、done重開／skip/restore、所有直接status繞過與Gatedoing送審拒絕；拒絕後DB/audit不變。
2. 實作固定欄位及同交易report/node/audit；所有相關入口遵守鎖順序。此時附件API未有，僅接受空attachment_ids；非空以明確錯誤拒絕，Task4接完整驗證（不得默默忽略）。
3. 真PG兩連線同步競爭同node送出／核准／退回，只有一次成功；狀態與稽核一致。全API回歸更新直接done等已核准變更的舊用例，保留其他角色／Gate断言。
4. GREEN、雙審與PROGRESS。此Task引入API契約變更，E2E完整調整在Task8，期間不把舊E2E失敗稱為已交付。

**Commit:** `P2b task 2: enforce reviewed task completion`

## Task 3 — 筆記、協作管理與紀錄查詢

**Files:** schemas、main、routes/records／collaborators、services/record_policy；test_notes_collaborators、test_record_permissions、test_health、test_collaboration_postgresql。

**Interfaces:** spec §7.1；records self/subtree僅可見投影，GET/PUT collaborators revision防覆蓋，筆記expected_revision防失更新；附件非空暫明確拒絕。

**Steps:**
1. 寫RED：作者可改／他人admin不可代改、失去寫權／readonly拒絕、筆記版本/no-op、管理者協作替換、跨公司外鍵、舊revision409、撤銷後查詢、subtree隱藏父／循環、分頁順序／空結果。
2. 實作完整授權後分頁，安全display_name與附件placeholder空集合；不讀隱藏節點內容來推導可見數量。
3. 真PG並行協作與筆記更新避免lost update；全API GREEN、雙審、PROGRESS。

**Commit:** `P2b task 3: add authorized notes and collaboration records`

## Task 4 — 持久化附件與失敗恢復

**Files:** main、schemas、routes/attachments／reports／records、services/attachment_store／attachment_recovery／report_service；deploy/docker-compose.yml、api.Dockerfile、nginx.conf、start.py；test_attachments、test_collaboration_postgresql、test_deployment、test_health、test_migrations。

**Interfaces:** spec §7.2；raw byte stream，10,000,000 bytes單檔、公司quota，pending/ready/failed，節點／回報／筆記關聯與SHA；文件設定追加但不覆寫.env。

**Steps:**
1. RED：真tempdir上傳/下載hash、10MB邊界、411/413/415/422、跨company/node、檔名路徑、UTF-8及容器格式、磁碟滿／DB commit失敗／commit實際成功但回覆遺失／rename後崩潰、ready前不可下載、軟刪不減quota、回報引用不可刪。
2. 實作配額預留與stream／SHA／rename／重驗授權；commit結果不明須新交易鎖定查DB，ready或已綁定永不刪檔／釋放配額，DB不可查時保留檔案及charged。temp和final都位於專用root且resolved path受限；實際bytes不能信任Content-Length。quota upsert初始化競態與總鎖順序具PG驗證。
3. 接回報／筆記attachment_ids全批檢查及同交易綁定，並行綁定／刪除僅一方成功；任一附件失敗不提交回報。
4. Dockerfile以固定UID/GID10001建立appuser，USER切換前建立owner appuser/mode0700的files目錄；Compose新files volume掛此目錄並保留copy-up。實跑全新volume上傳及帶舊檔重啟仍可寫／SHA不變；不對既有volume遞迴chown。Nginx／API雙層上限；localhost測10MB可過、11MB拒絕。root不可寫明確拒絕，不回退容器暫存。首次上傳授權失效不產生業務成功。
5. 恢復命令要求API已停止，由compose run --no-deps獨立服務執行；只清指定pending與其quota，拒ready／softdeleted及越界路徑。測中斷可重跑、清理失敗保留charged、不重複釋放。命令範例Task8寫入指南。
6. 全API／真PG／部署測試GREEN；雙審、PROGRESS。

**Commit:** `P2b task 4: persist authorized attachments with recoverable uploads`

## Task 5 — 任務紀錄、回報與協作UI

**Files:** App、api、types、styles、NodeWorkspace、MyTasks及新ReportPanel／RecordTimeline／NoteEditor／AttachmentList／CollaboratorEditor；App.test、workspace.test、node-editor.test、records.test。

**Interfaces:** spec §8；task預設紀錄分頁、回報卡、明確自核、各生命週期理由表單、協作設定與本人列表relations；不移除P2a導航/表單race回歸。

**Steps:**
1. Vitest RED：送審/自核/退回後新版本、不可直接done、理由取消、不完整上傳不能送、retry只GET、雙點擊／替換草稿／導航／登出舊回應、筆記衝突、readonly、權限撤銷、records pagination／隱藏祖先。
2. 拆組件實作API-capabilities呈現；下載用授權fetch Blob且釋放object URL，不提供內嵌預覽；上傳體驗顯示進行中及錯誤，quota超限解釋清楚。
3. 全Vitest/build GREEN，隔離1280/375鍵盤／長筆記／長檔名／表單／無溢出／非預期console檢查、保存截圖並實看。雙審、PROGRESS。

**Commit:** `P2b task 5: build task records and collaboration interfaces`

## Task 6 — 審核中心與安全稽核API

**Files:** routes/workspace／audit_logs、schemas、services/record_policy；test_review_audit、test_reports_audit、test_workspace、test_workflows_gates、test_health、test_mvp_acceptance。

**Interfaces:** spec §7.3；reviews type=report/gate，原Gate授權＋可見性，audit先授權後分頁和action白名單投影。

**Steps:**
1. RED：非自己回報且當下可審、scope reviewer、不把D60部門主管權限套Gate、readonly無待審操作、未知／隱藏payload不洩漏、node-null僅admin、跨公司cursor、穩定分頁／invalid422、權限變更後重驗。
2. 實作安全read models，不把原任意payload或actor_username回傳。調整既有精確API回歸保留公司邊界及既有提交事件檢查。
3. 全API GREEN、固定批次查詢數測試、雙審、PROGRESS。

**Commit:** `P2b task 6: add scoped review queues and audit projections`

## Task 7 — 審核中心與稽核UI

**Files:** App、api、types、styles、WorkspaceShell、新ReviewCenter／AuditLogView；App.test、workspace.test、新review-audit.test。

**Interfaces:** 保留三入口增加兩入口；兩種審核分列表、點擊定位、核准／退回理由、安全稽核條件與載入更多。

**Steps:**
1. RED：只顯API可審內容、退回意見必填、核准與Gate不混用、409保留安全狀態、成功後reload失敗不重送、切頁舊回應不污染、401/403/404、空資料與讀取失敗有別。
2. 實作兩組件及mobile導航；表單、稽核文字安全跳脫，事件翻譯不展示內部payload。
3. 全Vitest/build GREEN、隔離真角色桌面／375走查與截圖／console；雙審、PROGRESS。

**Commit:** `P2b task 7: build review center and audit views`

## Task 8 — 隔離整合驗收、恢復與文件交付

**Files:** web/e2e的health、mvp、workspace、collaboration、attachments五檔、playwright.config.ts；api/tests/test_collaboration_postgresql、test_migrations、test_mvp_acceptance、test_deployment；deploy/verify.py；README、正式指南、試用清單、PROGRESS。

**Interfaces:** Task1前移E2E真RED沿用，之後加測已完成行為如實記回歸；verify保留原隔離marker及finally down不加-v。專用PG結果需納入完整驗收，不讓skip掩蓋未測。

**Steps:**
1. 真實登入兩公司角色完成送出→退回→新版本→他人確認、管理者自核、協作增／撤、筆記作者修訂、上傳下載hash、附件刪除／回報鎖定、跨公司拒絕及audit安全；1280/375無溢出／非預期console。
2. 更新P2a直接status done等E2E改走新流程，保留原Gate、隔離與錯誤斷言；api/routes權限不能用前端hidden代替。每個E2E寫入前拒15173與驗marker。
3. 完整verify納專用PG並行與遷移命令：腳本建立唯一p2b_test DB，僅子程序傳URL，確認名稱護欄與檔案temp隔離；最終保留證據、禁止降版已保存日期的acceptance。若執行條件不滿足，整體驗收非零而非忽略。
4. 使用唯一測試資料保存note/report/attachment，snapshot DB值及SHA；stop/start保留兩volume、不seed，重新登入核對一致。驗pending恢復只在隔離環境，不刪ready／歷史附件。
5. 文件說明新API相容變更、升級流程、公司quota、不可預覽、DB＋files一致備份與停止API後pending修復命令；人類試用新增待辦全不勾。
6. 全verify GREEN／雙獨立Task審查，記PROGRESS。G4完整merge-base..HEAD雙審，修清Critical/Important，最多兩輪；驗收清單逐項有證據。
7. G5 ff-only，G6 main全隔離回歸。之後才在既有15173升級程式／migration與新增files volume（不seed、不覆寫env、不重建資料），先保存DB備份及env指紋；健康／migration檢查，不跑primary業務測試。失敗保留資料與備份，不自動downgrade。
8. README／PROGRESS收尾，依D50 push main，驗遠端一致；只清本次隔離容器不刪volume，人類簽核保留。

**Commit:** `P2b task 8: verify collaboration and document delivery`

## 完成條件與審閱重點

八Task與G4獨立spec／品質通過，真RED/GREEN、真PG並行／舊資料升級、附件故障恢復及重啟、1280/375完整旅程、G6回歸和保留資料部署；全部才能宣稱工程交付。

重點：D60不是一般owner自行審核、D61不擴can_work、read scope與audit一致；歷史submitted不進新隊列；Node與Attachment列鎖及quota崩潰一致性；一般PATCH不能繞過D59／D63；所有UI舊回應／retry不重送；附檔例外與未交付功能如實列出。
