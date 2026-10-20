# RAG入門教材

公司已改為系統現有的毛研食品（food）及峰曜科技（electronics）；所有人名、工單及規定仍為虛構示例。

共24份來源：6份會議紀錄、8份工單、4份通知、6份有文字層的PDF。毛研食品23份、峰曜科技1份；MTG-002為歷史版本。來源在corpus，evaluation是32題答案卷，不能建立索引。

使用新匯入器：

```powershell
$env:PYTHONPATH = 'api'
.\.venv\Scripts\python.exe -m app.ai.import_cli deploy/rag-starter --dataset starter-v1 --destination <獨立AI資料目錄>
```

新資料寫入指定目錄的starter-v1，不覆蓋dataset-v1；相同內容可重跑，不同內容拒絕覆蓋。PDF匯入時實際擷取文字，不支援掃描件OCR、Word或Excel。此匯入器限定本次24份資料契約，不是任意文件上傳器。

原始metadata的employee、hr及admin是教材測試角色。匯入後一般文件對應現行五種角色，機密PDF-006只授權admin；現行系統尚未新增真正的人資角色。32題中的employee以member測，hr以admin測，不代表員工可自行切換角色。

在副手選「入門文件：報到與教育訓練」，可查詢並開啟引用。詢問改期歷史時勾選「包含歷史版本」。完整待辦請選「未完成工單（完整清單）」；該模式按公司與專案列出完整清單，不解析額外自由文字條件。

舊展示資料與新資料分開：日期分別為2026-10-11及2026-10-20；新資料沒有原來16種SQL分析所需的營運資料。模型未啟用時回傳檢索原文，不能把32題來源驗證視為模型答案正確率。
