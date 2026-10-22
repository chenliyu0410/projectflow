# 正式文件 RAG

本機正式文件 RAG 已部署於 http://127.0.0.1:15173 ，migration 為 `20261021_0020`。本次以 GitHub 最新提交為基準保留本機 RAG 實作，於全新資料卷還原倉庫附帶的 2026-10-12 去敏展示資料（6 公司、80 帳號、39 專案），另新增一個「RAG 試用：文件問答與引用」專案與虛構文件。沒有找到原正式環境的完整備份；此資料包不包含匯出後修改、歷史稽核、通知或 session，不能視為原環境最新完整資料。原本檔案與 Chrome 舊 Demo 儲存未變更。

試用登入：公司 `food`、帳號 `yu`、密碼 `demo-yu`。開啟 AI 副手 → 資料來源選「正式文件」→ 選「RAG 試用：文件問答與引用」。可問「試用文件的審核負責人是誰？文件保存期限是幾天？」；預期可核對王小明與 90 天及版本 1 引用。這是虛構試用內容，不是公司規章。food 公司已設定本機 `qwen2.5:3b-instruct-q4_K_M` 與 `bge-m3:latest`，容器經 `host.docker.internal:11434` 連到 Ollama。

日後重啟使用 `python deploy/start.py`，不要加 `--seed-demo`，也不要重跑資料匯入。已保存升級前與試用後的 PostgreSQL dump、文件／AI 儲存及本機設定於 ignored `.superpowers/rag-deploy-20261021/`；備份含本機資料及設定，不提交 Git。本次只開放 loopback，未啟用區網或公網服務。

## 使用流程

1. 在專案或節點的「文件」區上傳 TXT、CSV、文字 PDF 或 DOCX。
2. 開啟 AI 副手，將「資料來源」切換成「正式文件」，選擇正式專案。
3. 按「重新整理正式文件」，再對要使用的文件按「建立／更新索引」。上傳完成與索引完成是兩件事。
4. 提問後可查看檢索原文、版本及定位；「查看原文」會重新驗證權限。可按「有幫助／沒有幫助」回饋。
5. 有文件編輯權的人可以停用／恢復知識。停用不刪原檔；文件升版後舊版立即退出新問答，需再次建立索引。先前問答的歷史引用仍可開啟，但標示非現行版；權限撤銷或知識停用後不能開啟。

未啟用模型時會顯示關鍵字檢索原文。內網模型無回應、引用無法驗證時會明示降級。完全沒有來源時回覆資料不足，空引用的模型輸出會換成固定拒答文字。

## 四個模組與介面

| 模組 | 程式 | 職責 |
|---|---|---|
| A 知識生命週期 | `rag/parsing.py`、`chunking.py`、`models.py`、`service.py` | 安全解析、父子片段、版本/hash、可重試索引、停用與不可變歷史 |
| B 檢索與上下文 | `rag/retrieval.py`、`provider.py` | 中文雙字與英文詞 BM25、真實 embedding、cosine／RRF、規則重排、同義詞與可選前次問題、去重與 context 預算 |
| C 生成與應用 | `rag/service.py`、`routes/rag.py`、`FormalRagPanel.tsx` | 證據生成、限定引用 ID、降級、來源閱讀、回饋、取消與晚回應隔離 |
| D 治理與評估 | `rag/governance.py`、`evaluation.py`、`scripts/evaluate_rag.py` | 既有公司／專案／節點權限、送模型前後重查、無全文 trace、統計與可重跑評測 |

外部 HTTP 介面（開發代理／部署網站加 `/api` 前綴）：

| 方法與路徑 | 內容 |
|---|---|
| `GET /rag/status?project_id=...` | 可見專案／文件、索引狀態與可操作權限 |
| `POST /rag/documents/{id}/index` | 同步建立現行版索引；有編輯權者可重試 |
| `PUT /rag/documents/{id}/enabled` | `{enabled: true/false}` |
| `POST /rag/ask` | `{project_id, question, previous_question?}`；回精確 chunk／版本引用 |
| `GET /rag/queries/{query}/sources/{source}` | 只允許該問答使用者，重查當前權限後開原文 |
| `PUT /rag/queries/{query}/feedback` | `{rating: "helpful" 或 "unhelpful"}` |
| `GET/PUT /rag/model` | 僅本機 admin 設定內網端點、對話／embedding 模型 |
| `GET /rag/metrics` | 公司 admin 的問答總數、最近 1000 筆樣本回饋、降級與延遲 |

`/ai/*` 仍使用獨立展示資料，不會把展示公司的專案 ID 當成正式專案。資料庫新增 `rag_settings`、`rag_indexes`、`rag_chunks`、`rag_queries`；原始文件與歷史版本不重寫。查詢紀錄不存問題、答案、prompt 或文件全文；只存來源 ID、白名單 trace 與回饋。token／費用未量測時為 null。統計針對已完成問答，不能當作全面的安全事件監控。

## 本機模型

由本機 admin 在正式文件面板展開「正式文件本機模型設定」，填入已安裝的 Ollama 端點與模型。LAN 模式禁止修改模型設定，沿用既有安全限制。伺服器在 Docker 時端點需能從容器連到模型，例如 `http://host.docker.internal:11434`；不要把容器內 `127.0.0.1` 誤認為主機。

更換 embedding 模型／端點後需重建索引；舊向量不與新設定混用。初版指紋識別端點與模型名稱，請使用固定模型版本／標籤；在相同標籤下替換權重不會自動辨識。生成與向量介面採 [Ollama 官方 API](https://docs.ollama.com/api/embed)，embedding 禁止靜默截斷。PDF 使用鎖版 [pypdf 6.14.2](https://pypi.org/project/pypdf/6.14.2/)。

## 限制與邊界

- 最多 200 頁／24 萬擷取字元／200 個子片段；每次查詢最多 5000 個已授權片段，模型 context 最多 8000 字元。超量會明示錯誤。
- PDF 在獨立程序解析，30 秒期限；每頁解碼內容 2 MB、累計 20 MB。解壓單一串流仍可能先配置到 parser 自身的上限；這不是 OS 記憶體沙箱。沒有 OCR，加密或無文字 PDF 不索引。
- DOCX 只抽取內文段落與表格文字，限制解壓量與 XML；圖片、Excel、ZIP 等既有可上傳格式不代表可以索引。
- 索引由編輯者明確啟動；queued 是持久化標記，沒有背景排程服務。中斷的 processing 可在 5 分鐘後重試。取消前端等待不保證後端已停止，應重新整理確認狀態。
- 向量存 JSON 做精確搜尋，適合此有界展示規模；未實作 pgvector／ANN、neural reranker、附件索引與法規保留期清理。歷史派生片段保留以支援舊引用。
- 引用 ID 驗證不等於每一句事實都正確；正式使用前仍需領域問答集評測及來源核對。

## 重跑驗證

```powershell
python -m pytest -c api/pyproject.toml api/tests/test_rag_api.py api/tests/test_rag_pipeline.py api/tests/test_rag_governance.py api/tests/test_rag_migration.py api/tests/test_rag_evaluation.py -q
npm.cmd --prefix web test -- --run
npm.cmd --prefix web run build
python api/scripts/evaluate_rag.py --service --report rag-service-report.json
```

`--service` 會在暫存 SQLite 與合成資料中實際執行上傳、索引、檢索、停用、升版和跨公司拒絕，不接觸原資料庫，不呼叫模型。省略 `--service` 僅測試評測器 fixture 契約。瀏覽器 `web/e2e/rag.spec.ts` 僅在帶 acceptance marker 的獨立環境執行，拒絕共用服務埠。實測結果及真模型冒煙範圍記在 PROGRESS，不能以 fixture 通過代替品質或安全完整驗收。
