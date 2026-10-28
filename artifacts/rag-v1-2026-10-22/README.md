# RAG 第一版驗證

本資料夾使用原本的20題與完全虛構文件，不修改標準答案或自動評分規則。內容／引用複核由獨立AI審查者執行，與人類試用簽核分開。

固定題庫見 `../rag-demo-data-2026-10-21/questions.json`。`evaluation.json` 保存原評分；`full-responses.json` 保存實際API的blocks、code、coverage與引用，包含第一筆升版尚未重索引的檢查。追問測試另記，不混入20題分母。

## 重跑

先安裝專案鎖版Python依賴並啟動本機Ollama，須有 `qwen2.5-coder:7b`、`bge-m3:latest`。從倉庫根目錄執行；輸出資料夾必須尚不存在：

```powershell
python artifacts/rag-v1-2026-10-22/evaluate.py --output .superpowers/rag-v1-rerun
python artifacts/rag-v1-2026-10-22/evaluate.py --followup --output .superpowers/rag-v1-followup-rerun
```

程式只使用暫存SQLite與虛構文件，呼叫本機Ollama；不連正式資料庫、不匯入正式專案。自動索引流程另由隔離PostgreSQL／瀏覽器驗收覆蓋，此品質腳本的手動索引不能代替自動索引驗收。

生成失敗、檢索原文降級或通用拒答，不可當成應有證據答案的成功。自動關鍵字檢查只是篩選；替代來源、日期表達以及有證據的否定都需要核對原文。各次失敗報告保留，沒有改分母或覆蓋原報告。
