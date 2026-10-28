# RAG-STARTER：入門文件匯入與查詢

依使用者2026-10-20「接著做，把新資料包匯入後面的工作」與「假資料用現有的公司，改一下假資料內容再匯入」執行。採WORKFLOW §14短規格／計畫，延伸既有AI展示流程。

## 目標與範圍

將24份入門文件改成現有毛研食品（food）與峰曜科技（electronics），在既有副手中選擇獨立「入門文件」資料集、搜尋、開啟引用、查歷史版本及完整未完成工單。原dataset-v1與正式資料庫不變。人資限定文件目前只授權admin，不能把一般主管當作人資；其他文件允許既有五種角色。原employee／hr測試身份對應member／admin。

這次完成新格式匯入及文字層PDF解析，並以32題檢查可檢索證據及隔離。未啟用模型時只呈現原文，不宣稱已生成預期答案；OCR、Word／Excel、正式附件自動索引、向量檢索、AI閘道及公司真實人資角色另行處理。

## 資料與介面

- 新增starter-v1分公司唯讀SQLite與manifest匯入紀錄；完整驗證後一次發布，同內容重跑不變，不同內容拒絕覆寫。
- 驗證SHA256、相對路徑、文件編號、公司／角色、日期／版本與來源文字；PDF於匯入時擷取，拒絕無文字層文件。答案卷不進索引。
- 不建立正式公司或帳號，不將虛構工單寫入生產庫。
- API新增dataset選項（預設dataset-v1，舊行為保持）、include_history選項（預設false）；公司只能由session決定。
- starter-v1不提供既有16種SQL分析；新增明確的未完成工單模式，從全部可見工單篩選，不假稱top-k完整。
- 引用與專案清單同樣按公司及角色過濾，資料集切換取消舊請求、清除對話。
- 日期顯示依資料集：舊2026-10-11、新2026-10-20。

## 允許修改

api/app/ai/starter.py（新增匯入／資料層）、api/app/ai/import_cli.py、api/app/ai/store.py、api/app/ai/service.py、api/app/routes/ai.py；api/tests/test_ai_starter.py、api/tests/test_ai.py（既有回歸）；api/requirements.txt、api/requirements.lock（PDF解析依賴）；web/src/ai.ts、web/src/components/CopilotPanel.tsx、web/src/ai.test.tsx；docs/ai-assistant.md、docs/PROGRESS.md、README.md；deploy/rag-starter/（改名後的24份教材、manifest、測試問題）、deploy/check_rag_starter.py（離線驗證）。

repo外原始產製器及輸出包同步改公司內容；保留全部虛構標示。環境快取與驗證產物不提交。

驗證補充允許檔案：`web/e2e/ai-starter.spec.ts`，用於1280／375的新增資料集主流程；Docker不可用時可用全新隔離SQLite測試登入與UI，必須明確區分這項結果與PostgreSQL部署驗收。

資料保存補充：`.gitattributes`將`deploy/rag-starter/**`標為`-text`，避免Windows換行轉換破壞manifest SHA-256；以實際Git匯出檔驗證。使用者已確認Docker仍出錯，先交付隔離測試版，保留本機feature分支，正式部署待Docker恢復。

## 步驟與驗收

1. 修訂來源包並驗證24份文件、6份PDF及公司名稱／代碼；封裝可重現測資。
2. 先補匯入、重跑、損壞來源、公司／角色隔離、歷史版本與完整工單測試，再實作。
3. 接API與副手資料集選擇，補前端切換／取消請求、引用與日期顯示測試。
4. 跑相關API完整測試、前端回歸及build；一位獨立唯讀審查者檢查資料保存／權限／展示路徑。
5. 有Docker時先隔離實測，再備份既有AI資料與正式資料，部署並匯入新增資料集；核對原資料與新資料的數量、查詢與引用。環境不可用時不宣稱已部署，保留本機匯入與可執行命令。
6. 記錄32題的檢索、權限及版本結果；模型未啟用時把答案品質明確列未驗收。更新操作文件與看板。

## 審查重點

未知dataset／公司／角色、路徑越界、損壞來源、同時／重複匯入、角色受限專案名稱外洩、跨資料集引用、切換時舊回覆混入、新舊基準日、機密資料處理與舊展示資料完整保留。
