# INDEX-INCREMENTAL：只更新變動來源（隔離交付）

依人類要求完成增量索引，沿用WORKFLOW §14短計畫／一次獨立審查，由本session實作；不部署正式環境。

## 設計與範圍

- 增量單位是文件版本或附件。逐來源比較metadata fingerprint、檔案大小／修改時間／ctime及索引格式版本。現行／歷史標示由業務DB即時決定，不因v1變歷史而重解析v1。
- 已有相容索引時，SQLite backup到暫存副本，只刪除已移除或變動來源的entries／chunks／FTS列，再解析新增／變動來源；未變內容與FTS詞項直接保留，不讀原檔正文／不重新斷詞。
- 無變動時自動及手動都不重建、不改索引時間。首次或舊索引格式需要一次完整建置（只換衍生索引，不migration業務DB）。版本常數供未來解析規則變更失效。
- 新增第2版只處理第2版，舊版索引保留；刪除附件／節點會清除對應來源索引。跨公司／即時權限／歷史選項及SHA-256查詢防護不變。
- 更新失敗保留原索引，下一輪重試。暫時I/O錯誤不可發布半成品；不支援格式可保留略過結果，來源未變不重試解析。
- 管理者索引狀態顯示最近一次成功發布的更新／沿用／移除來源版本數，非管理者不提供全公司增量統計。首次建置與增量區分，無變動時保留上次紀錄。
- 僅原有三開關、SQLite、單程序及500來源版本上限。仍每10秒掃描metadata，暫存發布仍複製索引DB；不是大量資料佇列、跨程序排程或完全零複製。
- 另複製auto-history.sqlite及檔案區為incremental.sqlite／incremental-files；原DB／檔案／教材hash保留。

## 允許檔案

- `api/app/ai/formal_index.py`，新增 `api/tests/test_ai_incremental_index.py`
- `api/tests/test_ai_formal_index.py`：發布失敗測試先新增來源觸發變動，對齊無變動不發布的新行為。
- `web/src/ai.ts`、`web/src/components/CopilotPanel.tsx`、`web/src/ai.test.tsx`
- 新增 `web/e2e/ai-incremental-index.spec.ts`
- 本文件、README.md、docs/PROGRESS.md、docs/ai-assistant.md
- repo外output/rag-starter-acceptance隔離副本／啟動器／說明／驗證腳本與結果

## 驗證

1. 先測：變更一個來源只解析一個，未變FTS列保留；新版本沿用舊版；刪除零解析並移除索引；手動／自動無變動零寫入；舊schema建置一次。
2. 測原檔狀態改變、略過格式沿用、發布／解析暫時失敗後原索引完整與重試、增量統計不洩漏跨角色資訊。沿用既有權限及版本回歸。
3. 副本上桌面／手機建立兩份虛構文件，新增版本後看到更新1／沿用其餘並查到新舊版本；原教材保留。做相關API／前端／build，一次唯讀審查。
4. 核對原資料保留、更新操作說明與進度、本機commit，保留試用；不push／合併。
