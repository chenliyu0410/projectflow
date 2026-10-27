# INDEX-AUTO-HISTORY：自動更新與歷史版本（隔離版）

依人類明確要求延伸現有正式文件索引；沿用WORKFLOW §14精簡流程，由本session實作並做一次獨立唯讀審查。

## 目標與設計

- API運行時每10秒檢查隔離來源，啟動時立即檢查；新增、增版、刪除及來源檔案狀態變動後自動重建。沒有變動不重建，不呼叫模型。不新增Windows排程或外部服務。
- 需要原有兩個隔離開關、SQLite及新的 `PF_AI_INDEX_AUTO_UPDATE=true`（預設關閉）。背景工作有獨立Session，採公司現存admin的既有來源可見性；查詢永遠以實際登入者的即時權限為準。沒有管理者的公司不自動索引。
- 不改原上傳／增版／刪除API，不新增業務資料表或migration。保留管理者手動更新；自動／手動共用更新鎖與原子替換，失敗保留原索引並下一輪重試，顯示不含正文／路徑的錯誤。
- 索引納入DocumentVersion的既有歷史版本，不製造版本或恢復刪除資料。附件沒有版本模型，維持單一來源。
- 預設只查現行版本，明確勾選歷史才加入舊版；結果、預覽提供給模型的文字及引用標示歷史／版本。引用API也需history選項才讀舊版，仍檢查公司、節點、原檔完整性及刪除狀態。
- 索引狀態按可見來源版本計數，列現行／歷史；顯示自動更新開關、最近檢查與錯誤。前端在正式資料集開啟時定期更新狀態，切換資料集／關閉時取消，不增加模型請求。
- 複製上一階段formal-index.sqlite及檔案區成新的auto-history隔離環境，原DB／檔案／教材hash不變；衍生索引依DB身分另建。
- 每公司500個來源版本、現有檔案解析上限不變。單程序輪詢，完整重建而非增量；正式PG、多worker協調、大量資料佇列、OCR、向量、語意版本比較留後續。

## 允許檔案

- 修改 `api/app/ai/formal_index.py`、`api/app/ai/service.py`、`api/app/routes/ai.py`、`api/app/main.py`
- 新增 `api/app/ai/index_worker.py`、`api/tests/test_ai_index_auto_history.py`
- 修改 `api/tests/test_health.py`：本輪啟動回歸發現路由清單漏列前階段已存在的preview／index-refresh，補齊既有契約。
- 修改 `api/tests/test_ai_formal_index.py`（既有版本預期對齊）、`web/src/ai.ts`、`web/src/components/CopilotPanel.tsx`、`web/src/ai.test.tsx`
- 新增 `web/e2e/ai-auto-history.spec.ts`；必要時修改既有formal索引E2E以容許自動更新
- 本計畫、README、docs/PROGRESS.md、docs/ai-assistant.md
- repo外 `output/rag-starter-acceptance/` 隔離副本、啟動器、說明及驗證證據

## 實作與驗收

1. 核心測試先驗歷史開關／引用權限、背景新增／增版／刪除、無變動不重建、失敗保留及重試、開關與生命週期。
2. 擴充來源版本識別、動態現行標記及衍生索引快照；加入可停的背景輪詢，啟停綁定FastAPI lifespan。
3. 接上歷史選項、狀態輪詢與版本提示，測試切換清除及正確請求參數。
4. 在新複製隔離版走桌面1280／手機375：不用手動更新，上傳v1、增版v2、預設只見新版、勾選可查舊版並開引用；既有教材流程保持正常。
5. 一次獨立唯讀審查與相關API／前端／build回歸；修正只重跑受影響處。核對原資料hash後更新試用說明與進度，本機commit，不push／合併／正式部署。
