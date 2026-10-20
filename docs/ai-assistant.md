# AI助手：RAG與受控Text-to-SQL

本輪把AI展示資料匯入獨立持久化資料區。六公司、144個AI延伸專案、3456個任務、4644份文件；資料基準日為2026-10-11，全部虛構。原有正式專案與附件保留，AI延伸案不混入正式任務樹。

## 使用

### 入門文件資料集

副手的「AI資料集」可切換原有展示資料與「入門文件：報到與教育訓練」。入門文件使用既有毛研食品及峰曜科技，不新增公司；共24份來源（毛研23、峰曜1），資料日期2026-10-20。原有資料集及其2026-10-11基準不變。這次程式與資料已在隔離環境驗證，正式環境是否已交付以PROGRESS為準。

1. 用毛研食品帳號登入，開啟AI副手，選入門文件。
2. 問「新人課程目前哪天上？」並開啟MTG-003原文，應看到10月28日10:00、B會議室。
3. 要看原10月27日安排時勾「包含歷史版本」，歷史來源會顯示標記。
4. 查完整待辦時改選「未完成工單（完整清單）」，按公司及所選專案列出；全公司應有6張未完成，WO-006逾期1個日曆日。此模式不解析姓名或日期等額外自由文字條件。
5. 一般成員看不到人資預算PDF-006；目前只有管理者可讀，未建立真正的人資部門角色。跨公司引用會回404。

新資料沒有舊SQL分析用的營運表，故該選項停用。原本的展示資料仍保留獨立查詢入口。

### 原有展示資料

登入後使用右側「AI專案副手」，手機按「AI副手」。

1. 在「AI展示專案」選一案，例如 `MY-AI-001`。
2. 選「RAG 文件問答」，問「現行交付需要幾張截圖？」或「風險原因與處理方式」。展開引用、按「開啟原文」可核對文件版本與內容。
3. 選「Text-to-SQL 資料分析」，問「各部門逾期未完成數」「哪些專案超支」，或從「分析種類」選擇16種分析。結果含表格、實際SQL、公司／專案參數與基準日。
4. 模型未設定時顯示檢索原文與資料庫結果，不假裝已生成答案。未知查詢明確拒答；不會把未支援日期或人員条件直接丟掉。
5. 模型啟用後可根據檢索文件整理回答；模型建議的分析需先核對模板與固定範圍，再按確認執行。模型不能直接執行任意SQL。

## 另一台電腦的Ollama

先在模型電腦安裝Ollama與適合該機器的聊天模型。Windows設定使用者環境變數 `OLLAMA_HOST=0.0.0.0:11434`、`OLLAMA_NO_CLOUD=1`，完全退出後重開Ollama；防火牆只允許ProjectFlow主機存取TCP 11434。兩台需有內網路由。

在ProjectFlow以管理者登入，展開助手底部「本地模型連線設定」，填 `http://模型電腦內網IP:11434` 與已安裝模型名稱，按「測試連線」，確認後勾選啟用並儲存。每家公司設定獨立，未設定的公司仍使用本地檢索。模型若在ProjectFlow同一台Windows上，Docker內請用 `http://host.docker.internal:11434`，不是容器自己的localhost。

連線測試檢查Ollama可达與模型已安裝，不代表生成品質已驗收。設定畫面只在本機管理者開放；只支援私有IPv4、localhost、host.docker.internal與IPv6 loopback，不接受公開端點、URL密碼、路徑、重導向或cloud模型名稱。實際請求不使用環境HTTP代理。請勿把本機Ollama再轉接雲端模型。

API契約依Ollama官方[Chat](https://docs.ollama.com/api/chat)、[結構化輸出](https://docs.ollama.com/capabilities/structured-outputs)與[網路／本地模式設定](https://docs.ollama.com/faq)。採文字搜尋RAG（中文雙字詞FTS5與BM25），目前不需要embedding模型；向量檢索、OCR與正式附件索引尚未實作。

入門資料匯入器另支援有文字層的PDF、Markdown及TXT；這不代表正式附件會自動建立索引，也不支援掃描PDF的OCR。

## 資料與權限

- `projectflow-formal_ai_data`是獨立Docker volume；`dataset-v1/`中每公司一個唯讀SQLite，`settings/`保存每公司模型設定。查詢無權寫入AI資料庫，設定操作與查詢摘要會寫入既有稽核（不記問題全文／模型答案／位址）。
- 公司由登入session決定，API不接受任意company_id。文件依allowed_roles過濾，成本月報僅admin/project_owner；其他角色可能沒有可見文件。分析限admin/project_owner。
- 這些是公司層級展示專案，不是正式節點，所以不使用正式node_id或假裝繼承其ACL。查詢前依公司、角色、所選AI專案過濾；引用原文再次驗權限。切公司、離頁、登出清除對話並中止前端請求。
- 只檢索現行版本，全文檢索前六筆。引用編號必須出自檢索結果；這是引用有效性檢查，不保證模型每句結論正確。模型不可達、格式錯誤或引用不符時回退原文並提示。
- SQL是程式內固定白名單、參數化、read-only連線，另有authorizer、執行步數與200列上限。公司實體分庫，專案篩選用受控CTE；不接正式業務DB分析。
- 金額為未稅TWD整數。expenses是已入帳成本；訂單是採購承諾，兩者不重複相加。不良率合計分子與分母。逾期為due_date早於基準日且狀態非done。

## 匯入與重現

### 新入門資料（starter-v1）

來源包在`deploy/rag-starter`。先在獨立目錄驗證：

```powershell
$env:PYTHONPATH = 'api'
.\.venv\Scripts\python.exe deploy/check_rag_starter.py --destination ../output/rag-starter-local-ai --report ../output/rag-starter-evaluation.json
```

檢查器匯入後用32題核對權限、版本與必要來源；Q31使用明確的完整工單模式。它不呼叫模型、不測模型答案正確率。29題有指定來源，其餘3題屬資料不足或未授權；拒答語意仍需模型啟用後另驗。

正式Docker引擎正常、先完成備份與部署更新後，才執行：

```powershell
docker cp deploy/rag-starter projectflow-formal-api-1:/tmp/rag-starter
docker exec projectflow-formal-api-1 python -m app.ai.import_cli /tmp/rag-starter --dataset starter-v1
```

只新增`ai_data/starter-v1`，不改原`dataset-v1`或PostgreSQL。若不同版本已存在會拒絕覆蓋，不能刪原資料來繞過；需另外規劃更新流程。同內容重跑及同時匯入可安全完成。這些命令不是本次已部署的證明。

### 舊資料（dataset-v1）

資料包位於workspace的 `ai-demo-data/pack`（另有ZIP與生成器）。先備份正式DB與附件，再更新API/web映像。不可重設DB或重新seed正式環境。

```powershell
docker cp ../ai-demo-data/pack projectflow-formal-api-1:/tmp/ai-pack
docker exec projectflow-formal-api-1 python -m app.ai.import_cli /tmp/ai-pack
```

匯入器驗證manifest SHA256、SQLite完整性、外鍵、文件專案與固定SQL目錄，先建立暫存分庫／索引，全部完成才原子發布。相同manifest重跑不修改已匯入資料；不同manifest拒絕覆寫。匯入器不需要PostgreSQL管理權限。

開發驗證從repo根目錄執行（歷史migration測試依賴此cwd）：

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'api')
./api/.venv/Scripts/python.exe -m pytest api/tests/test_ai.py -q
```

前端 `npm test`、`npm run build` 在web目錄執行。Playwright的 `ai.spec.ts` 使用15175隔離驗收環境及已匯入的測試AI volume，拒絕15173。Ollama尚未在使用者另一台電腦設定；目前只有模擬API契約測試，沒有遠端真模型推論驗收。
