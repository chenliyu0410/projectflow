# 正式文件 RAG

**2026-10-22 RAG第一版已更新本機**：保留完整專流及AI專案副手入口，開啟即問正式文件，支援範圍切換、連續追問、句旁引用、停止等待及自動索引。固定20題獨立AI內容／引用複核20/20（原自動評分18/20）；追問3/3，詳見[完整驗收](../artifacts/rag-v1-2026-10-22/驗收結果.md)。這不是人類試用簽核。

試用：http://127.0.0.1:15173/ ，公司`food`、帳號`yu`、密碼`demo-yu`。進「【虛構展示】山嵐新品 RAG 知識驗證」後開AI副手，問「G2 要具備什麼才能通過？」再問「那需要誰簽核？」；可核對三份文件及陳奕安簽核。這是完全虛構內容。

本機migration為`20261022_0021`，`PF_RAG_AUTO_INDEX=true`；沿用`qwen2.5-coder:7b`與`bge-m3:latest`，Docker經`host.docker.internal:11434`連Ollama。本輪保留6公司80帳號41專案502節點11文件12版本，33表原欄位、13原檔與32歷史引用核對完成。備份位於ignored `.superpowers/rag-v1/deployment/`。

日後重啟使用`python deploy/start.py`，不要加`--seed-demo`或重新匯入。初次部署的資料來源是倉庫附帶2026-10-12去敏展示資料，加上後續虛構RAG專案；不能視為過往原正式環境的完整還原。本次備份與保存核對針對更新前實際存在的本機資料；歷史部署來源與紀錄見[交接](rag-quality-handoff.md)。

## 使用流程

1. 在專案或節點的「文件」區上傳 TXT、CSV、文字 PDF 或 DOCX。
2. 開啟原有 AI 專案副手即可問正式文件：專案內預設該專案，其他位置預設所有可見專案；可手動切換，切換範圍會開始新對話。
3. 啟用自動索引的部署中，新上傳／改版／文字編輯會自動排入處理。「管理與設定」可看可查、排隊、處理中、失敗或不支援狀態，必要時手動重試。升級前未索引的歷史文件不會突然批次處理，需自行選擇重試。
4. 每次提問與追問都重新檢索目前有權查看的現行文件。回答旁的引用可展開專案、文件、版本、位置、原文及下載；也可回饋有幫助／沒有幫助。來源與下載都重新驗證權限。
5. 有文件編輯權的人可以個別停用／恢復知識。停用不刪原檔，改版不會擅自重新啟用。新版索引尚未完成時不拿舊版當現行證據；先前問答的歷史引用仍依當前讀權開啟，停用本身不阻擋歷史查證，撤權則不能開啟。
6. 對話只保留在本次頁面記憶體，關閉再開面板保留，刷新／登出／切公司即清空。「新對話」保留範圍，清除追問背景；不存跨裝置歷史。
7. 等待顯示實際秒數，30秒提醒仍在處理；「停止等待」只停止客戶端等待，伺服器可能仍在處理。失敗、逾時或生成降級可手動重試原題；草稿保留。展示資料與SQL、模型設定收在管理入口。

未啟用模型時會顯示關鍵字檢索原文。內網模型無回應、引用無法驗證時會明示降級。完全沒有來源時回覆資料不足，空引用的模型輸出會換成固定拒答文字。

## 四個模組與介面

| 模組 | 程式 | 職責 |
|---|---|---|
| A 知識生命週期 | `rag/parsing.py`、`chunking.py`、`models.py`、`indexing.py`、`service.py` | 安全解析、父子片段、版本/hash、持久自動排程與有界重試、停用與不可變歷史 |
| B 檢索與上下文 | `rag/retrieval.py`、`conversation.py`、`provider.py` | 授權範圍、BM25、真實 embedding、cosine／RRF、規則重排、追問改寫／澄清、去重與 context 預算 |
| C 生成與應用 | `rag/service.py`、`routes/rag.py`、`FormalRagPanel.tsx` | 證據生成、限定引用 ID、降級、來源閱讀、回饋、取消與晚回應隔離 |
| D 治理與評估 | `rag/governance.py`、`evaluation.py`、`scripts/evaluate_rag.py` | 既有公司／專案／節點權限、送模型前後重查、無全文 trace、統計與可重跑評測 |

外部 HTTP 介面（開發代理／部署網站加 `/api` 前綴）：

| 方法與路徑 | 內容 |
|---|---|
| `GET /rag/status?project_id=...` | 可見專案／文件、索引狀態與可操作權限；全部範圍用 `scope_kind=all_visible` |
| `POST /rag/documents/{id}/index` | 同步建立現行版索引；有編輯權者可重試 |
| `PUT /rag/documents/{id}/enabled` | `{enabled: true/false}` |
| `POST /rag/ask` | `{scope, question, history?}`，scope為project（含project_id）或all_visible；history最多6題／6000字；回blocks、code、coverage及版本引用。相容原project_id格式，但不可混用 |
| `POST /rag/queries/revalidate` | `{query_ids}`最多100筆；檢查本公司本人的舊答案是否仍可顯示 |
| `GET /rag/queries/{query}/sources/{source}` | 只允許該問答使用者，重查當前權限後開原文 |
| `PUT /rag/queries/{query}/feedback` | `{rating: "helpful" 或 "unhelpful"}` |
| `GET/PUT /rag/model` | 僅本機 admin 設定內網端點、對話／embedding 模型 |
| `GET /rag/metrics` | 公司 admin 的問答總數、最近 1000 筆樣本回饋、降級與延遲 |

`/ai/*` 仍使用獨立展示資料，不會把展示公司的專案 ID 當成正式專案。資料庫新增 `rag_settings`、`rag_indexes`、`rag_chunks`、`rag_queries`；原始文件與歷史版本不重寫。查詢紀錄不存問題、答案、prompt 或文件全文；只存來源 ID、白名單 trace 與回饋。token／費用未量測時為 null。統計針對已完成問答，不能當作全面的安全事件監控。

## 本機模型

由本機 admin 在「管理與設定」展開模型設定，填入已安裝的 Ollama 端點與模型。LAN 模式禁止修改模型設定，沿用既有安全限制。伺服器在 Docker 時端點需能從容器連到模型，例如 `http://host.docker.internal:11434`；不要把容器內 `127.0.0.1` 誤認為主機。

更換 embedding 模型／端點後需重建索引；舊向量不與新設定混用。初版指紋識別端點與模型名稱，請使用固定模型版本／標籤；在相同標籤下替換權重不會自動辨識。生成與向量介面採 [Ollama 官方 API](https://docs.ollama.com/api/embed)，embedding 禁止靜默截斷。PDF 使用鎖版 [pypdf 6.14.2](https://pypi.org/project/pypdf/6.14.2/)。

## 限制與邊界

- 最多 200 頁／24 萬擷取字元／200 個子片段；每次查詢最多 5000 個已授權片段，模型 context 最多 8000 字元。超量會明示錯誤。
- PDF 在獨立程序解析，30 秒期限；每頁解碼內容 2 MB、累計 20 MB。解壓單一串流仍可能先配置到 parser 自身的上限；這不是 OS 記憶體沙箱。沒有 OCR，加密或無文字 PDF 不索引。
- DOCX 只抽取內文段落與表格文字，限制解壓量與 XML；圖片、Excel、ZIP 等既有可上傳格式不代表可以索引。
- `PF_RAG_AUTO_INDEX=true`啟用持久排程，worker每5秒檢查、每程序一次處理1份，以排程發起者當前編輯權限執行。暫時故障最多3次，間隔30／120秒；中斷claim在5分鐘後可回收。未啟用時可手動索引。模型等待期間不持有專案編輯鎖。
- 升級到`20261022_0021`保留既有文件、版本及索引；舊queued列的requested_at保持null，不自動大量補建。換版期間僅就緒文件可回答，其他文件會顯示準備中。
- 問答總預算170秒，改寫最多15秒、查詢向量90秒、生成60秒，均受剩餘預算限制。停止等待不保證GPU運算已停止。
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
