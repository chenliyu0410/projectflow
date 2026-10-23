# 本地 AI／RAG 隔離測試版交接

交接日期：2026-10-21，2026-10-23 更新（LOCAL-MODEL-POLISH：審查修正、輸入預算、措辭）。分支：`feature/rag-starter-import`。本文件交接現有成果，不代表正式部署或使用者驗收通過；最新工作狀態以 [PROGRESS](PROGRESS.md) 為準。

## 接手先看

使用者要求全程使用隔離測試版，不影響原本資料。目前沒有合併 main、push 或部署正式環境。不要因舊文件的發布授權而直接切換正式服務。

- 程式庫：`C:\Users\User\Desktop\AI_project\work_flow\projectflow`
- 本輪執行資料：`C:\Users\User\Desktop\AI_project\work_flow\output\rag-starter-acceptance\local-model`
- 舊隔離版：15175／18005；本輪新副本：15176／18006／11436。不要將兩組資料路徑交叉使用。
- 正式 PostgreSQL、Docker volumes、早期隔離資料與原模型檔均保留。正式 Docker 問題本輪沒有重試。
- **Git 只保存程式與文件。SQLite、附件、AI 索引、模型權重、啟動器及原始驗收報告位於 repo 外的 output，沒有包含在 commit 中。** 保留整個本機 output；單靠 clone 無法還原本測試環境。

以下服務狀態與測試結果是前一輪交付紀錄；本次文件提交沒有重新啟動服務或重跑產品測試。

## 已完成範圍

| 工作 | 隔離版已完成 | 邊界 |
|---|---|---|
| 假資料與 RAG 查詢 | 改用既有毛研食品／峰曜科技，24 份簡單教材，來源引用、歷史教材及完整工單查詢 | 獨立 starter-v1；人資限定測資暫以 admin 控制 |
| 本地 AI 閘道 | 統一模型出口、教材分級、送出內容預覽、摘要稽核 | 雲端關閉；完整分級繼承及遮罩尚未做 |
| 正式文件／附件索引 | formal-v1，TXT、CSV、文字 PDF、DOCX、XLSX；分段引用、即時公司／節點權限 | 「正式文件」是資料類型，實際仍在隔離 SQLite |
| 自動更新與歷史 | 約 10 秒背景檢查、更新失敗保留舊索引；現行／歷史選項與版本標記 | 單程序；不是正式 PostgreSQL／多 worker 驗證 |
| 增量索引 | 只處理變動來源，沿用未變文字與 FTS，清除移除來源，無變動不發布 | 仍掃描 metadata、發布前複製索引；上限 500 來源版本 |
| 本地模型問答 | Ollama + Qwen3 4B，嚴格輸出結構、引用限定、無資料拒答、斷線降級；桌面／手機驗收 | 開發題庫，仍有三項語意限制；使用者未簽核 |

## 啟動及試用

在同一台電腦的 PowerShell 執行：

```powershell
& 'C:\Users\User\Desktop\AI_project\work_flow\output\rag-starter-acceptance\local-model\啟動本地AI測試.ps1'
```

啟動器使用現有資料，不 seed、不重設、不下載模型。需保留 repo 的 `.venv`、`web/node_modules`、`output/rag-starter-node/node_modules/node/bin/node.exe`，以及本機 `%LOCALAPPDATA%/Programs/Ollama/ollama.exe`。這不是跨電腦安裝包。

| 服務 | 位址／用途 |
|---|---|
| 網頁 | http://127.0.0.1:15176 |
| API 隔離健康檢查 | http://127.0.0.1:18006/health/acceptance ，應為 `acceptance: true` |
| OCR | 啟動器設 `PF_AI_OCR_MODEL_DIR`＝本資料夾 `ocr-models/`（繁中辨識模型，SHA-256 見 ai-assistant.md）；`.venv` 需另裝 `api/requirements-ocr.lock` |
| 專用 Ollama | http://127.0.0.1:11436 ，只使用本輪 `ollama-models/`（2026-10-23 重啟時本機 Ollama 已自動更新為 0.40.7）；對話模型與 `bge-m3` 向量模型同時常駐（`OLLAMA_MAX_LOADED_MODELS=2`） |

全部綁定回環位址。服務只剩部分存活或埠被占用時，先核對本資料夾的 `pids.json`、`ollama.pid`、程序命令列與日誌。PID 可能過期，不能只憑檔案數字停止程序；不要批次終止 Python、Node 或其他 Ollama。

測試帳號為虛構資料專用：`yu`／`demo-yu` 是毛研管理者；`ming`／`demo-ming` 是一般成員；`elaine`／`demo-elaine` 是峰曜管理者。尚未實作真正人資部門角色，不能將 admin 測試當成人資角色驗證。

完整示範腳本（13 題，含換句話說、權限與公司隔離）見[AI副手示範題目](ai-demo-questions.md)，示範前執行 `deploy/check_demo_questions.py` 確認。快速試用：登入後開啟 AI 副手，選「入門文件：報到與教育訓練」：

1. 問「新人課程目前哪天上？」：10 月 28 日，能展開來源。
2. 勾選包含歷史版本，問「新人課程原本哪天？為什麼改期？」：原訂 10 月 27 日，因講師時間改為 28 日。
3. 問「李小晴的月薪是多少？」：資料不足，不應猜測。
4. 問「只有 2 位新人，為什麼做 20 份歡迎包？」：2 份新人、18 份備用。
5. 切正式文件與附件，選「增量索引展示…」：報到地點現行五樓，歷史版本三樓。

「模型引用」才是回答宣告引用的來源，其餘只是檢索找到的資料。

## 執行設定與程式入口

本輪資料夾內：`local-model.sqlite` 為資料庫、`files/` 為附件、`ai/` 為索引與模型設定、`ollama-models/` 為獨立模型儲存區。啟動器設置：

| 設定 | 值 |
|---|---|
| DATABASE_URL | 指向本輪 local-model.sqlite 的 sqlite:/// 絕對路徑 |
| PF_ATTACHMENT_ROOT／PF_AI_ROOT | 本輪 files／ai 絕對路徑 |
| PF_ACCEPTANCE_MODE／PF_AI_FORMAL_INDEX／PF_AI_INDEX_AUTO_UPDATE | true |
| PF_SHOWCASE_MODE | false |
| OLLAMA_HOST／OLLAMA_NO_CLOUD | 127.0.0.1:11436／1 |
| OLLAMA_MODELS | 本輪 ollama-models 絕對路徑 |

模型為 `pf-qwen3-rag:latest`（Qwen3-4B-Instruct-2507 Q4_K_M），使用 Ollama 0.40.6、RTX 4060 8GB。驗收載入 GPU 約 5.1GB。每次 chat 明確指定 context 16384、temperature 0、think false、輸出上限 1200；伺服器啟動預設 context 8192 不代表本次 chat 的實際設定。

程式入口：

- [模型呼叫與輸出驗證](../api/app/ai/model.py)：本地限定、不走環境 proxy／redirect，完成狀態、answerable、引用 ID 驗證。輸入以字元估算（實測約為真實 token 的 1.7 倍），依排名只送放得下的完整段落，其餘仍列來源並記 `sent_count`；最相關段落單獨超限才降級，不靜默截斷。提示含資料基準日 `as_of`。
- [模型單元測試](../api/tests/test_ai_local_model.py)、[真模型驗收腳本](../deploy/check_local_model.py)、[瀏覽器驗收](../web/e2e/ai-local-model.spec.ts)。
- [AI 說明](ai-assistant.md)、[本輪短規格與計畫](superpowers/plans/2026-10-21-local-model-acceptance.md)。

## 驗收證據與重跑

以下檔案均在本輪執行資料夾：

| 檔案 | 意義 |
|---|---|
| answers-vector-1.json | **2026-10-23 混合檢索版採用的問答結果**（36 例，不含 `--extended`） |
| 驗收結果-vector.json | 向量檢索輪摘要：檢索比較、答案差異、示範題、正式索引向量建置 |
| retrieval-2.json／demo-check-3.json | 關鍵字與混合檢索比較（retrieval-1 為已撤回的純 RRF）；13 題示範題實跑結果 |
| answers-polish-3.json | 純關鍵字版（LOCAL-MODEL-POLISH）結果，保留對照 |
| 驗收結果-polish.json | 本輪機器摘要、逐題語意審閱、token 估算校準、撤回候選說明 |
| answers-delivery.json | 前一輪 41 例結果（65f42a6），保留作對照 |
| 驗收結果.json／問答驗收報告.md | 前一輪機器摘要與語意審閱 |
| preservation-before.json／preservation-result.json | 原資料基準及保留結果 |
| verify_preservation.py | 重新比對保留基準的本機腳本 |
| browser-delivery/ | 桌面 1280、手機 375 的瀏覽器證據與截圖 |
| 試用說明.md／runtime.json | 操作說明與執行紀錄 |

前一輪結果：41 例包括 37 次真模型回答、2 次無來源、1 次規則工單與 1 次刻意斷線。結構／來源範圍 41 例通過，另 4 項權限檢查通過。37 次暖機生成中位數 1.828 秒；首次載入曾約 24 秒。這不是獨立盲測，也不是 41 題答案全對。

相關 API 57 pass；最後模型測試 14 pass；前端相關 15 pass，型別／build exit 0；Edge 桌面／手機真模型 2 pass。資料保留檢查為原 79 檔 SHA-256 一致、30 表 492 原列保留；不是正式資料庫的全量稽核。

本輪（2026-10-23）36 例結構／來源全通過、無意外降級，34 次真模型，暖機中位數 1.906 秒；AI 相關 pytest 75、Vitest 17 通過，tsc／build exit 0，Edge 桌面／手機真模型 2 pass，原 79 檔與 30 表 492 列保留檢查通過。`--extended`（注入、斷線、權限）本輪沒有重跑。

混合檢索輪（2026-10-23，VECTOR-RETRIEVAL）：36 例結構／來源全通過、無意外降級，35 次真模型皆為混合檢索，暖機中位數 2.093 秒；AI 相關 pytest 85、Vitest 17 通過，tsc／build exit 0，Edge 桌面／手機 2 pass；13 題示範題全通過；獨立審查 Ready；原資料保留檢查通過。正式文件索引因 INDEX_VERSION 升為 2 已自動重建（33 來源、33 向量）。

`answers-initial.json`、`answers-qwen.json`、`answers-qwen-valid.json`、`answers-final.json`、`answers-candidate-rejected.json`、`answers-polish.json`、`answers-polish-2.json` 都是未採用候選（後兩份原因見驗收結果-polish.json），不要用檔案修改時間取代 canonical 指定。

需要重新驗收時，先啟動上述副本，再從 repo 根目錄執行，輸出到新名稱以保留既有證據：

```powershell
Set-Location 'C:\Users\User\Desktop\AI_project\work_flow\projectflow'
.\.venv\Scripts\python.exe deploy/check_local_model.py --report ../output/rag-starter-acceptance/local-model/answers-rerun.json
```

加入 `--extended` 才會納入測試指令文件、斷線復原及權限案例；它會在副本新增虛構文件，並暫時更改副本模型端點後還原，**不得與使用者試用同時執行**。意外中斷時核對副本模型端點已回復 `http://127.0.0.1:11436`。腳本自動檢查結構／引用，答案語意仍需逐題審閱。瀏覽器測試須指向 15176，不得套用正式入口。

## 已知問題與下一步

1. **措辭（2026-10-23 已處理大部分）**：Q09、Q28 已修正，Q32 拒答格式維持。Q07 仍照抄來源未標時態的「10月26日由林怡安發給新人」；加例句的提示反而寫成「已發給新人」，已撤回。另有 Q12 措辭混雜、Q23 引用過多、Q29 結尾多餘三項輕微問題。4B 模型對提示措辭敏感，再改提示務必重跑全部 36 例並逐題比對。**API 沒有自動重新載入**：改 `model.py` 後必須重啟 18006 才會生效，否則驗收跑到舊程式。
1b. 混合檢索後 Q12 誤把「將準備紙本簽到表」寫成已準備；示範腳本已避開 Q07 類時態題。
1a. 審查延後項：每次查詢與開啟引用都重新讀取並雜湊來源檔（大型附件會變慢）；驗收腳本的峰曜科技題一律用管理者 elaine 登入，沒有驗到一般成員。
2. 建立未參與提示調整的獨立題庫，分開評估事實、引用、拒答、跨公司／角色、文件內指令及歷史版本。使用者試用簽核仍待完成。
3. 後續工程：手寫／表格／直書 OCR 與正式映像的 OCR 相依（Linux 需 libGL 等）、雲端供應商轉接（需人類決定供應商、合約與金鑰）、欄位級分級與正式 PostgreSQL 版分級資料表、正式 PostgreSQL 的 pgvector、較大量資料的排程與多 worker。分級繼承、規則遮罩與 AI 政策已在隔離版完成（CLASSIFY-MASK，見 ai-assistant.md 與示範題 D14–D19）；隔離副本新增虛構「遮罩示範（虛構）」專案、〈配方成本試算.txt〉與合作夥伴「青禾原料行」，設定已改回預設。向量檢索已在隔離版完成（bge-m3，見 ai-assistant.md）；向量以 Python 標準函式庫計算，適合數千段以內，資料量變大前要改 pgvector 或專用索引。
4. 正式環境另案處理：Docker 恢復後先備份與隔離 PostgreSQL 驗證，確認切換範圍再部署；不要把本輪 SQLite 成功當成正式上線證據。

接手修改前先讀 AGENTS、PROGRESS，核對 branch／status。延續目前 feature 分支，保留所有原資料；這次交接本身僅提交文件。
