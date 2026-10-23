# VECTOR-RETRIEVAL：本地向量檢索與示範題目（隔離版）

依人類2026-10-23「要有可以示範查詢的題目，並繼續把這份架構完成」，選擇先做 README 架構圖中的「向量檢索」，並同意下載本地 embedding 模型到隔離 Ollama 目錄。依 WORKFLOW §14；沿用 `feature/rag-starter-import`，不合併、推送或部署正式環境。

## 範圍

- **模型**：Ollama `bge-m3`（多語、含繁中），只下載到 `output/rag-starter-acceptance/local-model/ollama-models`。走既有本地端點驗證（只允許 loopback／私有網段、不走 proxy），`truncate=false`，超長直接失敗、不靜默截斷。
- **開關**：只有 `PF_ACCEPTANCE_MODE=true` 且設定 `PF_AI_VECTOR_MODEL` 時啟用；未設定時行為與現在完全相同（純關鍵字 FTS5＋BM25）。
- **混合檢索**：關鍵字與向量各取權限範圍內前 30 名，以 Reciprocal Rank Fusion（k=60）合併後取前 6 名。向量只在**已通過**公司／角色／專案／版本過濾的候選中計分，不擴大可見範圍。查詢向量取得失敗時退回純關鍵字，回應標示 `retrieval=keyword`。
- **入門文件（starter-v1）**：不改已發布的唯讀資料集；向量另存在 `PF_AI_ROOT/vectors/starter-v1/`，以文件內容雜湊對應，首次查詢時建立（有鎖），之後沿用。
- **正式文件索引（formal-v1）**：索引內新增 `vectors` 表，`INDEX_VERSION` 升為 2（舊索引自動重建一次）。增量更新只對新增／變更段落取向量；向量模型暫時不可用時仍發布關鍵字索引，缺少的向量在下一輪自動補齊；換向量模型時全部重算。
- **儲存與計算**：向量正規化後以 float32 二進位存放，Python 標準函式庫計算內積；不新增 numpy、sqlite-vec 或 pgvector 依賴（pgvector 留正式 PostgreSQL 階段）。
- **示範題目**：`docs/ai-demo-questions.md` 列出可現場示範的題目、預期答案與要指出的重點（現行／歷史、拒答、完整工單、權限、正式文件版本、換句話說也找得到）；副手快捷鈕改用已驗證的題目。
- 延後：OCR、資料分級繼承與遮罩、正式 PostgreSQL／pgvector、大量資料排程。

## 權限與資料

權限規則不變：向量只是排序訊號，最終結果仍經既有 ACL 與檔案雜湊驗證。沒有 migration、不改正式 DB。向量檔與索引都在 repo 外的隔離 AI 區。

## 允許檔案

新增 `api/app/ai/vectors.py`、`api/tests/test_ai_vectors.py`、`deploy/check_retrieval.py`、`deploy/rag-starter/evaluation/paraphrases.jsonl`、`docs/ai-demo-questions.md`、本文件；修改 `api/app/ai/store.py`、`starter.py`、`service.py`、`formal_index.py`、`index_worker.py`（如需）、`api/app/routes/ai.py`、`web/src/ai.ts`、`web/src/components/CopilotPanel.tsx`、`web/src/ai.test.tsx`、`docs/PROGRESS.md`、`docs/LOCAL_AI_HANDOFF.md`、`docs/ai-assistant.md`、`README.md`（§8.6 一行）；repo 外啟動器加 `PF_AI_VECTOR_MODEL` 與 `OLLAMA_MAX_LOADED_MODELS=2`（4B 對話模型約 5.1GB＋bge-m3 約 1.2GB，8GB 顯卡可同時常駐，避免每題換模型）。

## 驗收

1. 單元測試以假向量驗證：換句話說的問題能找到關鍵字找不到的文件；受限／他公司／歷史文件不因向量被帶出；向量失敗退回關鍵字；增量只算變更段落、缺向量會補、換模型重算。AI 相關 pytest、Vitest、tsc／build。
2. `deploy/check_retrieval.py`（只讀隔離副本）：原 32 題與新的換句話說題，比較關鍵字與混合檢索的必要來源命中率（recall@6）；混合不得讓原題退步。
3. 真模型 36 例重跑：結構／來源全通過、無意外降級；逐題比對 `answers-polish-3.json`，記錄差異。示範題目逐題實跑。
4. Edge 桌面／手機真模型流程；一次獨立唯讀審查；原資料保留檢查。

## 交付結果（2026-10-23）

- bge-m3（1.16GB）下載到隔離 Ollama；對話與向量模型同時常駐。正式索引自動重建為 INDEX_VERSION 2（33 來源、33 向量）。
- 檢索比較 `retrieval-2.json`：原 31 題必要來源命中率關鍵字／混合皆 1.0；12 題換句話說 0.486→0.944；無越權來源。純 RRF 版（retrieval-1）讓 Q10 掉出前 6 名，改為保留關鍵字前 3 名後解決。
- 真模型 36 例：結構／來源全通過、無降級、35 次混合檢索，暖機中位數 2.093 秒（canonical `answers-vector-1.json`）。最終程式重跑來源一致，Q03／Q04 只差一句補充說明（GPU 推論的細微不確定性，兩版皆正確）。新增已知限制：Q12 把「將準備紙本簽到表」寫成已準備。
- 示範題 13 題全通過；AI 相關 pytest 85、Vitest 17 通過，tsc／build exit 0；Edge 桌面／手機 2 pass，內建瀏覽器目視確認快捷鈕與檢索方式；原資料保留檢查通過。
- 獨立唯讀審查 Ready。已修：向量關閉時關鍵字搜尋恢復湊滿 6 筆的原行為；公司模型關閉時不建向量、不每 10 秒重試、畫面不顯示語意檢索；入門文件向量側檔損壞時自動重建；示範指南時間與索引狀態說明更正。未修（記錄）：預覽與送出各自檢索，模型只在其中一次可用時來源可能不同；向量模型本身故障時背景每 10 秒重試並顯示更新失敗（不掉資料）。
