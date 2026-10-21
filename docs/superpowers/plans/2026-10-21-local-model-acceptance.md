# LOCAL-MODEL：本地模型串接與問答驗收（隔離版）

依人類要求與 WORKFLOW §14，由本 session 實作；沿用唯一 feature 分支，不合併、推送或部署正式環境。

## 範圍

- 沿用 Ollama `/api/chat` 與既有 AI 閘道。初測既有 Gemma 4 E2B 有漏答與格式問題；交付改用同機既有 Qwen3-4B-Instruct-2507 Q4_K_M，複製到本次 Ollama 目錄，名稱 `pf-qwen3-rag:latest`。原模型權重不修改、不重新下載；獨立 loopback 服務，雲端停用。
- 複製 incremental.sqlite、incremental-files 與 AI 資料區為 local-model 隔離副本；新 API 18006、web 15176、Ollama 11436。舊服務與資料不修改。設定只寫入新 AI 目錄。
- 模型只讀取通過目前公司／角色／專案權限的來源。無來源不呼叫模型；資料不足可明確拒答；引用必須存在於本次來源。失敗保留可核對的檢索結果。
- 驗收目前版本、歷史版本、跨文件、公司隔離、敏感文件權限、無資料、文件內指令不當作使用者指示、正式文件／附件、模型斷線降級。測試只使用虛構資料。
- 固定測試題、來源、模型版本與設定，保存實際答案、引用、時間與人工逐題審閱結果。開發驗收不宣稱獨立測試準確率或通用抗提示注入能力。
- 不新增向量檢索、OCR、雲端、資料寫入工作流程；不變更正式 DB schema。

## 允許檔案與步驟

1. `api/app/ai/model.py`、`service.py` 與必要 `api/app/routes/ai.py`：本地生成設定、結構與拒答驗證，維持已有 API 相容性。
2. `api/tests/test_ai_local_model.py`、既有相關 AI 測試：先驗證缺口，再修正。`deploy/check_local_model.py`：可重跑的真模型驗收；測試資料放 `deploy/rag-starter/evaluation/`。
3. 如有必要，修改 `web/src/ai.ts`、`web/src/components/CopilotPanel.tsx`、`ModelSettings.tsx`、`web/src/ai.test.tsx`；新增 `web/e2e/ai-local-model.spec.ts`。
4. repo 外 `output/rag-starter-acceptance/` 新副本、模型啟動器、驗收報告與說明。對原副本及教材做 hash 與原列保留檢查。
5. 一次相關後端／前端驗收、Edge 桌面1280／手機375主流程、一次獨立唯讀審查；依失敗重測受影響部分。
6. 更新本文件、README、docs/ai-assistant.md、PROGRESS 與交付說明；僅本機提交。

## 技術依據

- https://docs.ollama.com/api/chat （JSON schema、think、done）
- https://docs.ollama.com/faq （本地服務、context、停用雲端）

## 完成條件

實際本地模型產生可追溯答案；拒答／權限／歷史等驗收有真實紀錄；UI 可試用；原資料未變。若品質未達標，報告逐題失敗，不把檢索成功算成模型回答成功。

## 交付決策與證據

- Ollama 0.40.6，Qwen GGUF SHA-256 `2fde00ce69dd4899c70d020845e2638353015bba0fdf161b3eb965f2bca4464e`；原權重核對一致。使用官方 `/api/create` 註冊，修正 CLI 自訂標籤可列出但舊 chat API 找不到的相容問題。
- 生成固定 temperature=0、think=false、num_predict=1200、num_ctx=16384。以UTF-8 bytes加輸出／模板預留保守限制輸入，超限不截斷來源，直接降級。模型讀取逾時180秒，連線5秒。
- 必須 done=true、done_reason=stop；answerable 必須是布林值，回答須有本次有效引用。資料不足由模型宣告後，服務回傳固定拒答文字與空引用。引用schema限定本次來源，後端仍再驗證，不信任模型自行聲稱。
- `answers-delivery.json` 為選定版本41例：37次真模型、2次無來源、1次規則工單、1次刻意斷線；結構／來源範圍41通過，額外4項權限檢查通過。37次暖機後生成0.953–4.172秒，中位數1.828秒。這是開發驗收，非獨立測試。
- 唯讀審查確認工程／隔離安全可展示，語意保留Q07未來時態、Q09額外專案關係補述、Q28窗口措辭三項輕微限制；不宣稱41題完全正確。原始Gemma／Qwen候選失敗結果保留；`answers-candidate-rejected.json`是未採用提示變體（有拒答格式退步），名稱不代表交付，交付以`answers-delivery.json`為準。
- 相關後端57通過、最後模型14通過；前端15通過、tsc/build成功；Edge桌面／手機2條真模型流程通過。原79檔hash不變、30表492原列保留，新文件容量增量吻合。未測正式PG、多worker、大量文件、OCR或獨立盲測。
