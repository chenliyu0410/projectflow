# Text-to-SQL 擴充測試報告（2026-11-05）

狀態：實作與分批測試通過，獨立唯讀審查完成，準備獨立 PR。只變更新增測試、題庫與紀錄，產品程式與原有測試檔未修改。

## 基底與測試範圍

基底 `a42e5fa`（含問法回訓，PR #11 已合併），分支 `codex/text2sql-expanded-tests`。
題庫先固定再執行：200案例與執行器 `698f29a`；64正常查詢／8回訓流程 `9af0615`。

| 類別 | 案例數與結果 | 驗證內容 |
|---|---|---|
| 陷阱題 | 100/100 通過 | 96個新增問句＋4個既有題；非SQL回覆、沒有執行分析、未改資料 |
| API權限 | 100/100 通過 | 99項拒絕＋1項外公司候選清單回空；未登入、角色限制、參數偽造、跨公司、回訓權限 |
| 正常查詢 | 64/64 通過 | 16模板 × 標準問法、禮貌前綴／標點、專案範圍、合法空資料 |
| 完整回訓 | 8/8 通過 | 提問→點建議實查→確認pending→管理者C1–C5→同句直接查→外公司不繼承 |
| 題庫完整性 | 2/2 通過 | 題庫數量、唯一ID、案例矩陣與預期空值 |
| 既有相關回歸 | 89通過、1跳過 | test_ai／fallback／learning／gateway |

現在兩個新增測試檔共274個案例，分批實跑涵蓋：第一批217 pass中保留100陷阱＋100權限＋1完整性，舊16正常對照已被新矩陣取代；第二批73 pass為64正常＋8回訓＋1完整性。**不是宣稱一次執行274項**。收集檢查 `274 tests collected`。

## 實跑命令與紀錄

工作目錄 `api/`：

```powershell
python -m pytest tests/test_ai_expanded.py -q --disable-warnings --maxfail=1
# 初版：217 passed，281.86秒，exit 0（含後來移除的舊16正常對照）
python -m pytest tests/test_ai_normal_learning_matrix.py -q --disable-warnings --maxfail=1
# 73 passed，121.90秒，exit 0
python -m pytest tests/test_ai.py tests/test_ai_fallback.py tests/test_ai_learning.py tests/test_ai_gateway.py -q --disable-warnings --maxfail=1
# 89 passed、1 skipped，53.13秒，exit 0
python -m pytest tests/test_ai_expanded.py tests/test_ai_normal_learning_matrix.py --collect-only -q
# 274 tests collected，exit 0
```

唯一 skip：`test_learning_postgresql_migration_preserves_answers_and_refuses_loss` 需要專用 PostgreSQL。第一次從repo根目錄啟動曾載入其他專案同名app，收集前失敗；改在api/執行後正常，未把環境問題當產品RED。

## 預期結果與隔離

- 使用原有 synthetic pack 的副本，僅在 pytest 暫存目錄增加已收貨準時／延遲、未到期／取消訂單、退回／受阻任務與零不良批次。16模板均有非空結果可核對。
- `text2sql_normal_64.json` 固定人工可算預期：例如每專案4任務、1完成（25%）、3逾期未完成；2已收貨、1延遲（50%）；50樣本、2不良（4%）；採購承諾200，取消100不納入。
- 空資料保留公司與專案，只清測試資料包的明細；q16回零，其他模板回空清單。
- 專案案例結果與全公司結果不同，能檢出漏套篩選。逐案比較完整rows、query_id、公司／基準日／專案參數與實際執行次數。
- 每案例獨立tmp_path；拒答與越權前後檔案雜湊、問法內容／狀態不變；正常查詢也不修改資料。回訓只允許預期的候選→approved狀態變化。

## 重複題決定

使用者於本次對話明確選擇保留 T010、T026、T027、T081 與原本七題重複的四題，PR標示「96題新增＋4題既有回歸」。不宣稱新增100個不重複問句。

## 限制與審查

- 規則模式與API測試，model.chat/request禁止連外，沒有測真實LLM辨識品質。陷阱通過僅證明未直接執行，不保證每句原因分類／建議排名正確。
- 100權限案例包含模板、端點、角色、公司矩陣，不是100種不同漏洞；未涵蓋過期憑證與全部產品端點，不宣稱完整安全稽核。
- 未跑專用PostgreSQL、未改產品，因此未重跑與這次無關的前端／部署全量。
- 獨立唯讀審查完成：未發現阻擋問題；固定數值、專案／空資料驗證、完整回訓API流程與隔離合理。審查者未執行測試，實跑由主代理完成。第一次審查因額度失敗，追加回合已完成審查。
- `git diff --check` 通過；與基底比較 `api/app`、`web`、`deploy` 零差異。未追蹤 artifacts/ 與架構PNG未提交，簡報數字未修改。
