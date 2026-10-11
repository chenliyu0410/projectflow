# AI-RAG：匯入展示資料與可查證副手

人類2026-10-11直接要求匯入先前資料包並實作RAG與Text-to-SQL；模型主機尚未設定。依D65一次整合交付，先完成免模型可用的檢索與受控SQL，提供Ollama連線入口；不能宣稱已完成遠端模型實測。

## 範圍與資料
- 匯入六公司的AI延伸資料（144案、4644文件）至獨立持久化AI volume，依公司分開SQLite。保持正式PostgreSQL業務列與附件不變；AI專案在助手選單瀏覽，不混入正式任務樹。
- 匯入器驗證來源hash、外鍵、公司一致性，先建暫存目錄再原子發布；同一資料包重跑冪等，不覆寫已有版本。
- RAG：中文字詞分段／FTS檢索、現行版本與角色過濾、專案篩選、可開啟原文引用。模型未設時回傳檢索原文；設定後將檢索片段送到本地Ollama整理，引用編號限於檢索結果。這是文字檢索RAG，向量索引／embedding留後續。
- Text-to-SQL：自然語言辨識16種已定義分析意圖→參數化SQL→唯讀隔離資料庫→表格與SQL。模型可輸出受控query_id；不执行任意模型SQL。未辨識問題明確說明，不猜查詢。支援公司與專案範圍，基準日固定2026-10-11。
- 角色：已登入且現有公司key匹配；文件依allowed_roles驗權限；資料表分析限admin/project_owner。AI資料為公司內合成展示專案，不繼承正式節點ID，明示來源。Ollama設定僅本機admin，設定持久化，僅接受內網IP／localhost／host.docker.internal端點，禁止URL憑證與重導向；後端請求不讀代理環境。
- 切公司／離頁中止請求、清空對話。模型失敗回到可查證原文／表格並明示，無雲端fallback。

## 允許檔案
api/app/ai/*、api/app/routes/ai.py、api/app/main.py、api/tests/test_ai.py；deploy/import_ai_data.py、deploy/api.Dockerfile、deploy/docker-compose.yml、deploy/.env.example；web/src/ai.ts、web/src/components/CopilotPanel.tsx、web/src/components/ModelSettings.tsx、web/src/components/WorkspaceShell.tsx、web/src/components/AIGovernancePreview.tsx、web/src/App.tsx、web/src/styles.css、web/src/ai.test.tsx、web/src/ui5-preview.test.tsx、web/e2e/ai.spec.ts及受影響舊UI5 e2e；docs/PROGRESS.md、README.md、本計畫、docs/ai-assistant.md；本機ai-demo-data資料包和隔離驗證腳本。

## 步驟與验收
補充允許檔案：deploy/nginx.conf（模型請求75秒逾時，原API維持8秒）；固定受控SQL目錄位於api/app/ai/queries.json，匯入資料不得自帶可執行SQL。
測試配套：api/tests/fixtures/ai_schema.sql提供隔離合成資料結構；web/src/test-setup.ts對新增AI背景狀態請求設置預設mock，避免消耗舊業務測試的fetch佇列；AI自身測試覆寫完整回應。
既有契約更新：api/tests/test_health.py新增AI路由白名單，web/src/workspace.test.tsx把已過期的「所有副手操作不可用」改為未匯入狀態與抽屜鍵盤驗證；保留舊文件預覽測試，移除被新助手取代的固定回覆預期。
審查修正：自然語言只接受完整分析標籤／有限別名，防止忽略日期／狀態條件。模型辨識僅提出明確模板建議，使用者確認固定範圍後才查詢；不自動執行模型猜测。
1. 建立匯入器與隔離SQLite／FTS、16種分析定義及後端API；測試冪等、無部分發布、讀取公司與角色隔離、未知問題、SQL唯讀、模型失敗與錯誤引用。
2. 替換副手示例，加入模式、AI專案選單、引用、表格、SQL及模型設定。
3. 備份正式DB及記錄業務列／附件hash；啟動Docker並只更新API/web，匯入獨立AI volume，不seed、不migration。核對正式資料保留。
4. 適用API／前端回歸、build、隔離E2E桌面1280／手機375與一次唯讀獨立審查。文件記錄結果與尚未設定模型限制；依既有D50交付發布。
