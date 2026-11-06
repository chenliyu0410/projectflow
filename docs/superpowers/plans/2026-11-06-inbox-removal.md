# INBOX-REMOVAL：拿掉收件匣資料夾掃描，Excel 改成系統內上傳（短規格與計畫）

> **狀態更新（2026-11-06）。** 使用者先指示「請你不要改程式 幫我改簡報就好」「不要理會Excel」，簡報改完後再指示「n8n 的收件匣排程實際上還在每分鐘跑的程式 請改掉」。**現行範圍以本框為準**：
>
> - 做：範圍表第 1、2、4、7 項（n8n 收件匣流程、掃描 API、compose 收件匣掛載、`verify.py`／README）；第 3 項改成**整個刪除** `inbox_service.py`（資料夾掃描與資料夾 Excel 匯入一起拿掉）。`setup.py` 在已安裝的 n8n 上以 `n8n unpublish:workflow --id=pfInbox00000001` 停用舊流程（n8n 2.45.7 有此指令，已確認）。
> - 不做：第 5、6 項系統內 Excel 上傳與「Excel 上傳規則」整節（使用者：「不要理會Excel」）。營運資料仍可在畫面上手動新增／編輯。
> - 測試：`/integrations/inbox/scan` 回 404、`setup.py` 不再匯入收件匣流程、workflows 資料夾只剩四個流程；刪除兩個收件匣測試。
> - 部署：使用者這句指示包含「實際上還在每分鐘跑」，所以在本機 15173 的 n8n 執行停用（只停用流程，不刪 n8n 資料、不刪主機上的 `deploy/inbox/`）。API 映像不重建（掃描 API 沒有人呼叫後無作用，下次部署時一併移除），合併與 push 另問。

依使用者 2026-11-06（D90）：討論簡報 P.37 時決定刪掉 n8n「收件匣每分鐘」排程，理由是「正常的上傳檔案方式是在這個系統裡，再跑OCR」，資料夾掃描會讓第一次聽報告的人看不懂，正常使用時也不會這樣上傳，而且「沒辦法限制權限」。後續決定「Excel 改成系統內上傳」「P.37 維持四個」。

- 流程：WORKFLOW §14 精簡流程＋§14.1 展示收斂。分支 `feature/inbox-removal`（自 main `a2c82dd`）。做完一次獨立審查、相關回歸，**合併、push、部署 15173 都另外問使用者**。
- 底線：**檔案進系統一律經過登入與權限檢查。** 不留任何「放進資料夾就被處理」的入口。

## 為什麼要拿掉（權限問題）

收件匣掃描是 n8n 拿共用的 `PF_N8N_TOKEN` 呼叫 `/integrations/inbox/scan`，系統只從資料夾名稱 `<公司代碼>/<專案名稱>/` 判斷檔案屬於哪裡，不知道是誰放的：

- 能寫入那個資料夾的人，就能把文件放進任何公司的任何專案。
- Excel 匯入以「該公司第一位啟用中的管理者」身分寫入（`inbox_service.import_records`），稽核紀錄看不出真正放檔案的人。

## 範圍

| # | 項目 | 做法 |
|---|---|---|
| 1 | n8n 收件匣流程 | 刪除 `deploy/n8n/workflows/inbox.json`；`setup.py` 不再匯入；已安裝過的 n8n 由 `setup.py` 停用並刪除 id `pfInbox00000001` 的流程（指令依 n8n 2.45.7 CLI 實測決定；CLI 做不到時改成 README 手動步驟並如實記錄） |
| 2 | 掃描 API | 移除 `POST /integrations/inbox/scan` 與 `test_health.py` 路由清單中的這一列 |
| 3 | 收件匣服務 | `inbox_service.py` 只留 Excel 解析（`excel_rows`、`as_date`、匯入列處理），移除資料夾掃描、搬檔、`store_document`、管理者代理身分；檔案改名為 `operations_import.py`（名稱不再有收件匣） |
| 4 | 部署 | `docker-compose.yml` 移除 `PF_INBOX_ROOT` 與收件匣掛載（保留備份掛載）；`setup.py` 不再寫 `PF_INBOX_HOST` |
| 5 | Excel 上傳 API | 新增 `POST /operations/import?category=<key>&filename=<name>`，請求本體是檔案（沿用 `doc_templates.body()` 的 `require_binary` 與 10MB 上限） |
| 6 | 營運資料頁 | 管理者與專案負責人在目前分類看到「上傳 Excel 匯入」；完成後顯示新增／更新筆數並重新載入清單 |
| 7 | 驗證腳本與文件 | `verify.py` 拿掉收件匣文件與 Excel 匯入兩步（到期提醒改用 API 建立測試紀錄）；更新 `deploy/n8n/README.md`、`README.md` 自動化說明 |

**不做／延後**：簡報檔在 repo 外，P.37、P.39（重錄）、P.34、P.42 由使用者自行修改。主機上既有的 `deploy/inbox/` 資料夾與裡面的檔案不刪，只是不再被讀。多工作表 Excel 仍延後（README 路線圖既有項目）。

## Excel 上傳規則（AI 代決，可推翻）

| # | 規則 | 決定 |
|---|---|---|
| 1 | 誰能匯入 | 與手動新增相同：`can_manage`（管理者、專案負責人），由 API 檢查；一般成員看不到按鈕，直接呼叫回 403 |
| 2 | 以誰的身分寫入 | 登入者本人，每筆照舊寫 `operations.create`／`operations.update` 稽核，另寫一筆 `operations.import`（分類、檔名、新增數、更新數） |
| 3 | 分類 | 匯入到畫面上目前選的分類，不再看檔名 |
| 4 | 檔案格式 | 只收 `.xlsx`，讀第一個工作表，第一列是欄名且必須有「代碼」「名稱」；其他欄照舊存成欄位，日期欄照舊轉成 YYYY-MM-DD |
| 5 | 先檢查再寫入 | 先把每一列檢查完（必要欄、欄位格式、代碼重複）；有任何一列不合格就整份不寫入，回 422 並列出前 20 個錯誤列號與原因 |
| 6 | 更新既有紀錄 | 同分類同代碼就更新：只改 Excel 有的欄位，保留其他欄位、狀態（Excel 沒填時）與機密設定（沿用現行合併邏輯） |
| 7 | 通知 | 不寄 Email、不推 LINE；上傳者在畫面上直接看到結果。舊的 `inbox_document`／`inbox_import` outbox 歷史資料保留，不改 schema |
| 8 | 資料變更 | 無 migration |

## Task

1. **後端（TDD）**：新增 `/operations/import`，測試涵蓋：管理者新增後再更新同代碼、專案負責人可匯入、一般成員 403、缺「代碼」欄 422、一列錯誤時整份不寫入、非 `.xlsx` 與超過 10MB 被拒、不同公司的同代碼互不影響、稽核記到登入者。把 `test_n8n_complete.py` 的兩個收件匣測試改寫或移除。
2. **移除收件匣**：刪 `inbox.json`、掃描路由、資料夾掃描程式與 compose 掛載；`setup.py` 停用舊流程；`verify.py` 改步驟；`test_health.py`、`test_deployment.py`（如有涉及）同步。
3. **前端**：`OperationsManager` 加「上傳 Excel 匯入」與結果／錯誤列顯示；Vitest 涵蓋可見性、成功、錯誤列。
4. **文件與記錄**：兩份 README、PROGRESS；一次獨立審查。

## 驗收

- API：相關 pytest（`test_operations*`、`test_n8n_complete.py`、`test_health.py`、`test_deployment.py`）通過並記 exit code；改到共用的營運資料儲存，另跑 API 全量一次。
- Web：相關 Vitest 與 `npm run build`。
- 實機（隔離環境，不碰 15173）：以專案負責人上傳一份供應商 Excel，看到新增筆數，再上傳改過的同一份看到更新筆數；以一般成員登入看不到按鈕。`setup.py` 跑完後 n8n 只剩四個流程。
- 桌面 1280、手機 375 看營運資料頁的上傳入口不溢位。
