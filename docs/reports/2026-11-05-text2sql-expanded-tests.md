# Text-to-SQL 擴充測試報告（2026-11-05）

狀態：待使用者決定 4 題與既有題重複的處理方式，尚未開 PR。無產品程式變更。

## 基底與範圍

- 基底 a42e5fa，含問法確認、審核與回訓功能；PR #11 已合併。
- 分支 codex/text2sql-expanded-tests，固定題庫 commit 698f29a。
- 每題獨立 pytest ID 與隔離 SQLite 資料庫；規則模式，不呼叫真實 LLM。
- 測試清單與預期值見 api/tests/fixtures/text2sql_traps_100.json、text2sql_access_100.json。

## 實跑結果

| 項目 | 結果 |
|---|---|
| 原有基準 test_ai + test_ai_learning | 35 pass、1 skip |
| 100 筆陷阱題 | 100 pass（其中 4 題與原有 7 題重複） |
| 100 個 API 權限案例 | 100 pass（99 項拒絕＋1 項跨公司候選列表回空清單） |
| 正常查詢對照 | 16 pass |
| 題庫內部完整性 | 1 pass |
| 新測試合計 | 217 pass，281.86 秒，exit 0 |
| 既有相關回歸 | 89 pass、1 skip，53.13 秒，exit 0 |

執行命令（工作目錄 api/）：

```powershell
python -m pytest tests/test_ai_expanded.py -q --disable-warnings --maxfail=1
python -m pytest tests/test_ai.py tests/test_ai_fallback.py tests/test_ai_learning.py tests/test_ai_gateway.py -q --disable-warnings --maxfail=1
```

第一次從 repo 根目錄啟動誤載另一專案的同名 app 套件，收集前即失敗；改用基準測試相同的 api/ 工作目錄後正常。此為執行環境問題，沒有當成產品失敗或 RED 證據。

## 待決定問題

自查發現 T010（2026年9月逾期任務）、T026（已完成任務逾期數）、T027（已結案的高風險清單）、T081（DELETE FROM tasks; 逾期）與原本七題完全重複。題庫內部無重複，但尚不能宣稱新增 100 題：目前為 96 題新增＋4 題既有回歸。依使用者「有問題先問再繼續」要求已暫停，建議替換四題，增加與既有題庫不重複檢查，再跑受影響驗證。未修改預期、未刪失敗測試。

## 限制與審查

- 權限案例含端點、模板、角色與公司矩陣，非 100 種不同漏洞；實際資料庫未改、SQL 分析未執行、拒絕回應未提供資料。
- 陷阱通過僅證明沒有直接執行分析，不代表所有原因分類或建議排序正確。
- 未跑真實 LLM、PostgreSQL、過期憑證等未涵蓋情境，不宣稱完整安全稽核。
- 唯一 skip 為需專用 PostgreSQL 的回訓 migration 測試。
- 自我檢查及 git diff --check 完成。獨立審查代理因額度限制未能執行，不宣稱完成獨立審查；專案 WORKFLOW §14 允許無審查者時如實記錄。
- 簡報與業務資料未修改。未追蹤 artifacts/ 與架構 PNG 保留且未提交。
