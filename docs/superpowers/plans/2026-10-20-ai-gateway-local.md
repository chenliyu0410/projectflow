# AI-GATEWAY-LOCAL：本地閘道第一版短規格與計畫

依使用者「後面的工作項目可以先繼續完成」與既定隔離交付方向，套用 WORKFLOW §14。由目前 session 使用 executing-plans 執行；本階段一次獨立審查。

## 目標與範圍

一般人資在既有 AI 副手中能看懂：哪些資料會提供給模型、資料等級、本次是否嘗試模型，以及雲端維持關閉。既有 RAG／受控 SQL／完整工單流程保留。

- 將 RAG 回答及 SQL 種類辨識統一經由 `gateway.py`；只能使用既有內網 Ollama。模型健康檢查仍為不帶業務文字的 `/api/tags`。
- 文件等級沿用教材 metadata（public/internal/confidential），多份取最高；自由問題至少內部；缺少或未知等級按機密處理。這是已匯入資料的分級，尚非正式公司／專案／欄位繼承。
- 閘道再次驗公司及角色；非法 metadata 拒絕送模型。模型設定即使被直接改檔，請求時仍驗私有位址與非 cloud 名稱。未啟用／無來源／規則查詢不發模型請求。異常維持可讀原文退路。
- API 預覽重用實際檢索／規劃，完全不呼叫模型；回傳目前可見的問題與來源內容（SQL 辨識僅問題與分析目錄）。正式送出時重新查詢，不把預覽當凍結的授權快照。畫面明示這是資料部分，不含固定系統指令或 HTTP 包裝。
- 每次完成的查詢／預覽以既有稽核記錄等級、路由、原因、模型嘗試與結果；不記原問題、答案、文件正文或模型位址。不新增全文稽核頁或宣稱送出前持久化保證。
- 雲端固定關閉，無可啟用的雲端介面。未做遮罩／還原、本地模型自動分級、真模型品質、雲端供應商、正式附件／向量索引。

## 保護與資料變更

沿用 `feature/rag-starter-import`；不新增依賴或 migration，不修改匯入包及既有資料庫檔。只有既有查詢稽核新增 metadata。測試用隔離 SQLite；試用仍 15175／18005。Docker／正式 PostgreSQL 阻塞保留，不 merge／push／部署正式版。

## 允許檔案

- `api/app/ai/gateway.py`、`api/app/ai/service.py`、`api/app/ai/model.py`
- `api/app/routes/ai.py`、`api/tests/test_ai_gateway.py`
- `web/src/ai.ts`、`web/src/components/CopilotPanel.tsx`、`web/src/ai.test.tsx`
- `web/e2e/ai-starter.spec.ts`
- 本文件、`README.md`、`docs/ai-assistant.md`、`docs/PROGRESS.md`
- repo 外 `output/rag-starter-acceptance/` 交付說明／證據（保留原 DB）。

## 實作及驗收

1. 補閘道有效測試：預覽零模型呼叫、公司／角色／專案／歷史版本、機密分級、舊資料保守處理、直接竄改模型設定仍擋雲端、失敗回退、SQL／工單不送資料列、稽核不含正文。
2. 實作共用規劃與模型出口；副手增加內容預覽及簡短路由結果。切公司／資料集／專案／模式／問題／版本後清除舊預覽，慢回應不能回填。
3. 一次相關新舊 AI API、前端全量、tsc/build 與桌面 1280／手機 375 主路徑驗證；32 題既有檢索評測不應退步。獨立唯讀審查，修正後只驗受影響部分。
4. 更新尚未完成清單、試用說明及 PROGRESS；本機提交。真模型僅模擬契約測試，不冒稱品質已驗收。
