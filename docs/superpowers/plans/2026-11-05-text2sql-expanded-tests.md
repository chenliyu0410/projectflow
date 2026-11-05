# TEXT2SQL-EXPANDED-TESTS：擴充模擬題與 API 邊界驗證

使用者於 2026-11-05 授權：新增陷阱題與越權案例各 100 題、執行測試、另開 PR；以含回訓的版本為基底，有問題先詢問，不擅自修產品程式。基底 a42e5fa（回訓 PR #11 已合併，與 origin/main 一致）。本輪使用 codex/text2sql-expanded-tests，在主 checkout 工作，不建立 worktree。

## 範圍與允許檔案

- api/tests/fixtures/text2sql_traps_100.json：100 個唯一問句，時間、對象狀態、混合否定、離題模糊、指令繞過各 20。
- api/tests/fixtures/text2sql_access_100.json：100 個 API 案例，未登入、角色、偽造參數、跨公司、回訓權限各 20。角色與公司矩陣是案例組合，不宣稱 100 種不同漏洞。foreignAdmin 的候選列表應回 200 空清單，其餘依契約為 401/403/404/422。
- api/tests/test_ai_expanded.py：API 層逐案參數化；檢查回應、SQL 未執行、資料集與問法未改動；另加 16 項正常分析對照及題庫完整性檢查。
- 本計畫、docs/PROGRESS.md、docs/reports/2026-11-05-text2sql-expanded-tests.md：記錄真實結果與限制。

不修改 app/、不變更資料版本、不安裝依賴、不改簡報數字。只用既有 synthetic pack 與每案例獨立的 pytest tmp_path 資料庫；不碰正式或展示服務資料。

## 驗收與步驟

1. 現有基準 test_ai.py + test_ai_learning.py：35 passed、1 skipped（專用 PostgreSQL），exit 0。
2. 題庫先固定並 commit，再執行新增測試，不依跑出來的結果調整預期值。
3. 陷阱題：合法 API 請求須回非 SQL 的 fallback/unsupported/help，analysis=None、sources=[]，受控分析執行次數=0，資料集、模型設定、問法均不改動。本輪驗的是不能直接執行，不宣稱每句原因或建議排名全對。
4. 越權：使用有效帳號與實存的外公司資料/候選，確認 HTTP 契約、拒絕回應不含資料、SQL 不執行、問法狀態與資料集不改動。空清單案例驗證不洩漏外公司候選。
5. 正常對照：16 個白名單標籤須成功執行對應分析；q02 另驗獨立可算的 2 件結果。
6. 適用回歸：test_ai.py、test_ai_fallback.py、test_ai_learning.py、test_ai_gateway.py，包含既有確認→審核→下次查詢流程。
7. 一次獨立唯讀審查；結果通過後將報告與程式提交，push 測試分支並開對 main 的 PR，不合併。

## 限制與停止條件

規則模式實測，model.chat/request 禁止連外。沒有執行真 LLM、PostgreSQL、過期憑證或所有產品權限端點，不能稱完整安全稽核；本輪也未修改產品，不偽造 RED。若測試失敗，保留題庫、預期與輸出，先問使用者再繼續。
