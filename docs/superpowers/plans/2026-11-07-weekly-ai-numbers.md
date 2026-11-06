# WEEKLY-AI-m1：AI 週報句中數字檢查（短規格與計畫）

依使用者 2026-11-07「WEEKLY-AI-m1」。流程：WORKFLOW §14 精簡流程＋§14.1 展示收斂。分支 `feature/weekly-ai-numbers`（自 main `4daabc6`）。合併、push 另外問使用者。

## 問題

PROGRESS §5 WEEKLY-AI-m1：本機模型（gemma3:4b）會自己換算數字，例如進度 30% 寫成「仍有 70% 延遲」。提示詞禁止這樣做，但 `write_sections` 不檢查句中數字，只能靠第 4 道關卡「負責人確認才寄出」人工攔下。

## 規則

- 每一段（summary／highlights／risks／next）裡出現的阿拉伯數字，都必須出現在送給模型的 facts 資料中（計數、進度、日期的年月日、標題與摘要裡的數字都算）。
- 任務代號 `[T1]` 裡的數字不算句中數字（代號已有既有的清單檢查）。
- 有任何一個數字不在 facts 中，**那一段**改用系統條列（與既有「清單外代號」的處理相同），其他段照用 AI 文字。
- 比對時正規化：去掉千分位逗號、前導 0（`03` = `3`）、小數尾端的 0（`30.0` = `30`）。
- 全形數字先轉半形；逗號只有後面接 3 位數時才當千分位（`第1,2週` = 1 和 2）。
- 限制（審查記錄，接受）：檢查只看「數字有沒有出現在 facts 裡」，不看上下文。facts 含日期與計數，小數字（如「延遲 7 天」）可能剛好存在而通過；模型自己數出的正確數字若不在 facts 裡會被退回條列（安全方向）。仍由第 4 道關卡負責人確認。
- 不做：中文數字（七十）、模型漏寫代號（m1 第②點）。漏寫代號若改成擋下，小模型幾乎每段都會退回條列，展示效果差；維持由負責人確認。

## 範圍

| 檔案 | 改動 |
|---|---|
| `api/app/services/weekly_report_service.py` | 新增 `numbers()` 與 `write_sections` 的句中數字檢查 |
| `api/tests/test_weekly_reports.py` | 新增 1 個測試：自行換算的數字讓該段退回條列，引用 facts 的數字與代號照收 |

## Task 1

1. RED：寫測試，`model.chat` 回傳 summary 含 facts 沒有的數字（如「70%」），highlights 只引用 facts 的數字；預期 summary 退回條列、highlights 保留。
2. GREEN：實作檢查。
3. 回歸：`tests/test_weekly_reports.py`、`tests/test_n8n_complete.py`。
4. 一次獨立審查，修正後更新 PROGRESS 並 commit。
