# F1 文件管理

人類2026-10-11授權正式文件上傳、編輯、儲存及版本紀錄，並確認TXT／CSV網頁文字編輯；其他格式下載修改後上傳新版本。

- 文件依附專案或目前任務；清單僅列目前範圍，不聚合其他任務文件。專案文件沿既有專案可見權限，管理者／專案負責人可寫；任務文件沿用節點可見性與紀錄寫入權限（含協作者），readonly不可寫入。兼容舊專案沒有根任務，不補建或修改舊節點。
- 文件與不可變版本使用獨立資料表，migration 0012只新增表，不seed、不改舊資料。版本檔案沿用files volume及公司容量，檔案內容驗證沿用附件服務；單檔10MB。文字線上編輯上限1MB UTF-8。版本記錄檔名、作者、時間、說明與SHA256，舊版本可下載；文字可檢視。樂觀版本檢查避免覆蓋他人修改。
- 二進位檔案不提供網頁Office編輯、簽核、刪除或版本還原；營運預覽維持。新增文件使用上傳，文字檔可另存新版本。
- 允許檔案：api/app/models.py、main.py、routes/documents.py、services/document_store.py；api/alembic/versions/20261011_0012_documents.py；api/tests/test_documents.py、test_health.py、test_migrations.py；web/src/components/DocumentManager.tsx、App.tsx、styles.css、documents.test.tsx；web/e2e/documents.spec.ts、ui5-preview.spec.ts；README.md、docs/PROGRESS.md、docs/formal-feature-roadmap.md、本計畫。
- 步驟：資料模型與API→文件UI→有效核心測試與相關回歸→唯讀獨立審查→備份並保留資料部署→ff-only及D50發布。
- 驗收：上傳TXT→重載→編輯儲存v2→檢視與下載v1/v2；上傳二進位新版本；過期版本409、越權／跨公司404/403、無效／過大檔案拒絕、容量不足不留下可見版本。桌面1280／手機375主流程，既有資料保存及migration驗證。
- 儲存異常採保守保留：未提交DB前的臨時檔清除；完成rename後若DB提交結果不確定，保留檔案供檢查，避免刪掉可能已提交的版本。不自動清除孤立檔。
