# TP-G 自訂回報欄位：短規格與計畫

日期：2026-10-10。人類指定「TP-G：自訂回報欄位」。依D70／D65完成原始碼對照與提案；人類「照此計畫實作」，D79已核准。

## 對照與目標

Demo的fieldDefs、addReportField、moveReportField、validateReport、buildReport及reportFieldsHTML提供四種欄位、新增／移除／上移、必填驗證與歷史快照。正式版ReportPanel／report_service尚無自訂值；TP-E模板及TP-B複製也未帶欄位。目標是設定任務欄位→填寫完成回報→審核與歷史顯示→模板再利用。此階段是原始碼對照，畫面對照留實作驗收。

## D79建議規則

1. **定義**：可設定文字、數字、日期、單選；支援名稱、必填、數字單位、單選選項、新增／移除／上移及下移。沿Demo先不提供原地改類型或改名稱，需移除後新增。每任務最多30欄；名稱100字、單位30字、文字值4000字；單選2至50個不重複且非空選項、每項100字。日期須為有效年月日；數字須有限，接受0及負值，空值和0分開。
2. **適用與權限**：設定入口放任務編輯器；限可編輯該任務者，沿既有can_edit_node，由API強制檢查。只有未關閉且沒有待確認回報的葉任務可修改定義；已完成／已略過及關閉上層下不可改。樹操作使葉任務成為父任務時保留原定義與歷史、暫停欄位設定；再次成為葉任務可沿用。正式版既有父任務回報規則維持，父任務回報不套用暫存的葉任務欄位。
3. **送出與歷史**：回報表單載入定義及版本，後端重驗必填、型別、選項與未知欄位。定義在填寫期間改變則409，保留輸入並要求重新載入；不能悄悄丟棄值。提交保存欄位識別碼、名稱、型別、單位、選項、順序與值快照。審核與歷史只讀該快照，不受之後移除影響；退回重報以目前定義驗證，相同識別碼可帶回舊值。無欄位的舊回報顯示維持不變。
4. **模板及複製**：專案／子樹另存、模板版本／複製、建立專案、套用模板及TP-B複製子樹都帶定義，不帶回報值；實體新任務產生新欄位識別碼。舊模板缺欄位時視為空集合，不補寫歷史版本。模板編輯／預覽提供同款欄位設定與摘要；僅模板葉任務可新增設定。套用仍追加不覆蓋。結構刪除／復原保留定義；欄位寫入留稽核，後續修改阻擋過期結構復原。
5. **邊界**：所有讀寫沿公司與節點可見性，不因模板或回報API繞過權限；定義修改、提交、模板套用與樹操作沿專案→節點鎖順序並在同交易記稽核。TP-F完成回報例外申請也保存定義版本及值，核准時重驗，衝突不送出過期內容；覆寫不得跳過必填與型別。延後公式、檔案型欄位、多選、條件顯示、跨任務共用欄位庫、報表統計及欄位編輯復原。

## 資料與允許檔案

- migration `20261010_0011`：任務欄位定義與版本、回報快照；以新增表／欄位實作，同公司及節點約束。舊資料保留原值，新快照預設空；不seed、不重建DB，有新資料時拒絕有損降級。模板JSON增加可選欄位定義並保留舊版相容。
- API：api/app/{models,schemas,main}.py；routes/{reports,records,projects,workflows,workspace,collaboration}.py；services/{report_service,node_policy,tree_service,template_service,workflow_service,collaboration_service}.py；新增routes/report_fields.py、services/report_field_service.py；api/alembic/versions/20261010_0011_tp_g_report_fields.py。
- Web：web/src/{api,types,styles}對應ts／css；components/{NodeEditor,NodeWorkspace,ReportPanel,RecordTimeline,ReviewCenter,WorkflowLibrary,TemplateDialogs,CollaborationDialogs}.tsx；新增components/ReportFieldEditor.tsx。
- 測試：新增api/tests/test_tp_g_report_fields.py、web/src/report-fields.test.tsx、web/e2e/report-fields.spec.ts；既有test_migrations.py、test_health.py與直接相關reports／report_lifecycle／tp_b_tree／tp_e_templates／tp_f_collaboration／workflows測試及前端records／templates／node-editor契約測試；deploy/verify.py加入隔離PG驗證。
- 文件：本計畫、docs/PROGRESS.md、README.md、docs/formal-development.md、docs/mvp-trial-checklist.md。不修改Demo、不新增依賴。

## 實作與驗收

1. D79確認後，在主checkout建立唯一feature/tp-g-report-fields；對照Demo與正式版桌面及375px畫面。
2. migration及欄位API：有效型別、選項、必填、0值、非法日期、未授權／跨公司、關閉任務、待審回報、版本衝突與稽核；真PG驗證migration保留資料及修改定義／送出回報併發。
3. 接完成回報、重報、審核、歷史及TP-F例外；驗證舊快照不變，失敗不部分寫入。
4. 接模板完整鏈及樹複製／刪除／復原；驗證新識別碼、舊模板相容、歷史版本不變及無回報值複製。
5. 桌面／手機走新增四種類型→排序／刪除→必填錯誤→成功回報→退回重報→審核→歷史→另存／套用模板。驗證鍵盤、長名稱、取消及網路失敗保留輸入。
6. 一位唯讀獨立審查者；一次隔離完整API／Vitest／build／E2E與適用PG驗收，修正後只驗受影響部分，記錄真實摘要及exit code。
7. ff-only合併、更新交付文件；15173部署前成套備份DB／附件／env，不seed升版，比對原值與附件SHA並檢查健康；依D50 push main核對SHA，不代簽人類試用、不開LAN。

## 實作補記

D79核准後採nodes新增JSON欄位report_fields及整數report_fields_version、task_reports新增JSON快照fields；公司及節點邊界沿既有複合外鍵。定義獨立PUT以版本避免覆蓋，NodeEditor內另按「儲存回報欄位」，取消欄位變更不改其他節點輸入。父任務原定義保留但不啟用，模板父任務僅允許保留既有定義；新實體重建識別碼。TP-F申請另外保存欄位快照供審閱，版本過期走既有expired結案，可重送。

新增請求契約的相關planner／timeline-advanced測試補上reportFields唯讀mock；這是NodeEditor／ReportPanel直接受影響的既有測試。獨立審查發現的autoOpen歷史載入與過期申請問題已修正並補回歸，複核Ready to merge；最終驗收與部署結果以PROGRESS為準。

驗收修訂：web/e2e/workspace.spec.ts等待本次搜尋q的真實API回應，並限定「我負責的」表格選任務，避免選到站內通知中的同名按鈕；不刪除舊測試資料。此為本階段NodeEditor回歸直接暴露的既有測試修正，納入允許清單。
