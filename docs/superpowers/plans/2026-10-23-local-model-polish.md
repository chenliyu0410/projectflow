# LOCAL-MODEL-POLISH：審查修正、輸入預算與三題措辭（隔離版）

依人類2026-10-23「先把我目前本地的rag分支，審查後繼續完成」與 WORKFLOW §14。沿用 `feature/rag-starter-import`，不碰遠端新分支、不合併、不推送、不部署正式環境。

## 範圍

- **輸入預算（人類選「放得下的先送」）**：原本以 UTF-8 位元組當 token 上限，中文一字算 3，正式文件 4 段以上完整段落就整題降級。改為字元估算（非 ASCII 每字 1.5、ASCII 每字 1，仍偏保守），依檢索排名只送放得下的段落；閘道紀錄新增 `sent_count`，畫面標示幾段因長度未送出，來源清單照列。單一段落就超限時不呼叫模型，`reason=context_too_large`。
- **三題措辭**（交接檔第1項）：送給模型的內容加入資料基準日 `as_of`，晚於基準日的事項寫成預計／排定（Q07）；與問題無關的來源直接略過，不評論它和所問專案的關係（Q09）；人員職責照來源原文，窗口不寫成核准人（Q28）。
- **審查修正**：單一來源檔案讀不到時只略過該來源，不讓整次索引失敗（儲存區整體不可用仍整次失敗、保留舊索引）；Windows 發布索引遇到讀取中的檔案時短暫重試；`formal_index.document` 索引讀取錯誤回 503；starter 原文 API 依 `include_history` 限制歷史版本，前端開啟原文帶同一選項；狀態輪詢成功時清除舊錯誤訊息。
- 延後：每次查詢重新雜湊來源檔的效能問題、電子公司一般成員驗收帳號、獨立題庫、向量檢索／OCR、正式環境。

## 權限與資料

不改權限規則，不改正式 DB schema，沒有 migration。真模型驗收只在 `output/rag-starter-acceptance/local-model` 副本（15176／18006／11436）執行，不加 `--extended`，輸出到新檔名，保留既有證據。

## 允許檔案

`api/app/ai/model.py`、`gateway.py`、`service.py`、`formal_index.py`、`api/app/routes/ai.py`；`api/tests/test_ai_local_model.py`、`test_ai_gateway.py`、`test_ai_formal_index.py`、`test_ai_incremental_index.py`、`test_ai_starter.py`；`web/src/ai.ts`、`web/src/components/CopilotPanel.tsx`、`web/src/ai.test.tsx`；本文件、`docs/PROGRESS.md`、`docs/LOCAL_AI_HANDOFF.md`、`docs/ai-assistant.md`。

## 驗收

1. 相關 pytest（AI 全部檔案）、相關 Vitest、tsc／build。
2. 啟動隔離副本，`deploy/check_local_model.py` 重跑 36 例，對照 `answers-delivery.json`：結構／來源全通過、無意外降級；Q07／Q09／Q28 改善，拒答（Q 李小晴月薪）與歷史題不退步。另以真模型核對估算值不低於 Ollama 回報的 `prompt_eval_count`。
3. 一次獨立唯讀審查；只修展示阻塞、資料或權限問題。

## 交付結果（2026-10-23）

- 36 例結構／來源全通過、無意外降級、34 次真模型；canonical `answers-polish-3.json`，最終程式重跑答案與引用一致。token 估算為 Ollama `prompt_eval_count` 的 1.73–1.81 倍。
- Q09、Q28 修正，Q32 維持拒答格式；Q07 未改善（來源原文未標時態），加例句變體反而寫成已發卡，已撤回。Q12／Q23／Q29 有輕微措辭問題，明列於交接檔。
- AI 相關 pytest 75、Vitest 17 通過，tsc／build exit 0，Edge 桌面／手機真模型 2 pass；原 79 檔與 30 表 492 列保留。`--extended` 本輪未重跑。
- 獨立唯讀審查 Ready；非阻擋項已修兩項（模型未啟用時不記 `sent_count`；正式文件 `as_of` 改用伺服器當地日期），其餘（罕用字估算、分級含未送出來源、starter 舊版原文需 include_history）記錄於此。
