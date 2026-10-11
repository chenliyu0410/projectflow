# F1-OPS 正式營運資料

2026-10-11人類授權營運資料新增、編輯及儲存。依WORKFLOW §14精簡交付。

- 左側「營運資料」改為正式清單／分類／詳細／新增編輯表單。沿各產業供應商或客戶、資源、採購或訂單、工單或執行分類，另提供配方／組成、批號紀錄分類。欄位依分類給預設，可加減欄位，代碼／名稱／狀態必填。
- 原有虛構營運示例透過明確一次匯入命令保存，標示「展示資料」來源；相同公司／分類／代碼已存在則跳過，重跑不覆蓋。文件預覽不當成營運文件匯入；原示例入口保留，專案資料分頁仍為關聯預覽。
- 權限：公司隔離；admin／project_owner管理公司營運資料，其餘既有角色唯讀內部紀錄。每筆可設內部或機密；機密僅管理角色可見／編輯，配方預設機密，含價格／成本的匯入示例亦機密。此為整筆紀錄保護，不宣稱完成欄位級權限。
- DB migration0013僅新增operations_records；公司＋分類＋代碼唯一，JSON欄位資料、來源、建立更新人／時間、revision。提交expected_revision並鎖列防覆蓋，新增／修改同transaction稽核。查詢只回授權資料。
- 不含刪除、庫存計算、自動業務狀態轉換、跨單據連動、ERP、AI資料同步、配方核准或正式批號追溯引擎。狀態是人工紀錄，不是簽核。所有文字用React跳脫；拒絕額外／過大／重複欄位。資料庫備份且保留舊資料，檔案／env不變。
- 允許檔案：api/app/models.py、main.py、operations_catalog.json、operations_import.py、routes/operations.py；api/alembic/versions/20261011_0013_operations.py；api/tests/test_operations.py、test_health.py、test_migrations.py；web/src/components/OperationsManager.tsx、App.tsx、styles.css、operations.test.tsx；web/e2e/operations.spec.ts、ui5-preview.spec.ts；README.md、docs/PROGRESS.md、docs/formal-feature-roadmap.md及本計畫。
- 步驟：模型／migration與API→保留來源的匯入→正式UI與導覽保護→核心API／migration測試、前端回歸／build、1280／375真PG主流程與競爭測試→一次唯讀獨立審查→備份／部署／保值核對→ff-only及D50發布。
- 驗收：新增→重載→編輯→重登持久化；既有示例可編輯；公司隔離、唯讀禁止寫入、機密清單與詳情不外洩、舊revision409且保留草稿、唯一代碼衝突、切分類／公司／導覽取消離開保留草稿；原文件／任務功能保留。只跑相關完整驗收，不機械重跑未改動的附件故障矩陣。
