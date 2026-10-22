# RAG 品質修正與換機接續（2026-10-22）

## 目前狀態

本輪修正 CSV 欄位語意、伺服器證據編號、綁定來源的數字編號、Decimal 四則運算、模型上下文容量，以及Q06必要條件與Q18有據否定回答。原始文件／題庫／基線報告保持不變。**2026-10-22品質版已更新本機**，生成模型 `qwen2.5-coder:7b`，embedding 保持 `bge-m3:latest`。入口 http://127.0.0.1:15173 ，food／yu／demo-yu；AI副手選正式文件與「【虛構展示】山嵐新品 RAG 知識驗證」。

- 最終 `evaluation-q06-final.json`：自動19/20、獨立AI語意與引用複核20/20；Q01替代來源直接支持答案，原判分未改。詳見[Q06修正驗證結果](../artifacts/rag-demo-data-2026-10-21/Q06修正驗證結果.md)。人類試用簽核仍待本人。
- 部署前pg_dump可列目錄、附件tar逐檔SHA吻合；更新後29張既有資料表、13個原檔案、env與資料掛載一致，6公司80帳號41專案502節點11文件12版本保留。2筆歷史引用仍200且內容不變。
- API與web代理已更新，DB容器未重建；web靜態資源逐檔SHA不變。RAG專用代理195秒解決原8秒504，前端既有等待上限仍180秒。11份文件重新索引，舊chunk保留。

以下是保留的歷史候選結果：

- 原始 3B：20 題自動粗篩 16/20，逐題內容複核 15/20。
- 中間候選：`evaluation-after.json` 14/20、`evaluation-final.json` 15/20；檔名 final 是實驗名稱，**不是驗收通過**。
- 最終程式的 7B 重點比較：Q04/Q05/Q07/Q08/Q10/Q13/Q14/Q18 答案符合預期，僅是 8 題定向比較，不能視為 20 題通過。
- 早一輪 `evaluation-accepted.json` 自動17/20，當時複核記19/20；本次獨立審查更正：Q18通用拒答漏傳達已知狀態，按完整性標準該輪應18/20（Q06、Q18）。舊報告保留。Q01替代來源與Q15日期空格是粗篩誤判；PR #5維持Draft，本次本機修正未push。
- 相關 API／pipeline／計算／權限／migration／文件測試：65 passed，exit 0。獨立程式審查已修正異常格式與小數精度問題，後續證據／數字映射複核無阻擋。
- 歷史交接時原版容器僅重新啟動，尚未部署品質版；現已完成上方記載的備份及更新。最新本機成果需另推送才會出現在遠端PR，本次未推送／合併。

## 在另一台電腦取回程式

交接分支為 `codex/rag-quality-handoff`，[PR #5](https://github.com/chenliyu0410/projectflow/pull/5) 以現有 `feature/review-fixes` 分支為基底。原 PR #4 保持不變。遠端與本機各有同內容的 E2E 修正提交，交接分支將本機成果的檔案樹接在遠端提交之後，避免 force push；原始本機提交仍保留。

新資料夾可執行：

```powershell
git clone https://github.com/chenliyu0410/projectflow.git
cd projectflow
git switch codex/rag-quality-handoff
```

如果已有修改，先備份並看 `git status`，不要直接覆寫。從 `AGENTS.md`、本文件及 `docs/superpowers/plans/2026-10-21-rag-quality.md` 開始；中間失敗報告保留供比較，不重新產製或改寫題庫。

## 接續驗證與部署

1. Q06與Q18已修正；先讀最新驗證結果，換機仍需確認程式包含本輪本機提交，再於隔離環境重跑固定20題，不以模型名稱相同代替實測。
2. 使用 API 鎖定依賴、啟動本機 Ollama，確認有 `bge-m3:latest` 與 `qwen2.5-coder:7b`。模型權重不在 GitHub。
3. 隔離評測指令（新檔名，避免覆蓋結果）：

   ```powershell
   python artifacts/rag-demo-data-2026-10-21/run_demo.py --model qwen2.5-coder:7b --report artifacts/rag-demo-data-2026-10-21/evaluation-next-machine.json
   ```

   預設使用暫存 SQLite 與暫存附件目錄。**不要使用 `--import-local` 重複匯入既有展示專案。** 自動字詞／指定文件判分只是粗篩，需逐題核對語意、引用、拒答與是否降級。
4. 更新部署前再備份現場 DB 與附件並記錄指紋；先確認資料卷對應正確。只更新 API，保留 DB／附件；變更生成模型設定須記錄原值。pipeline v2 要明確重建衍生索引，舊 chunk 保留供歷史引用。
5. 部署後比對原業務資料與檔案、檢查健康狀態及實際問答；索引／新查詢／稽核可有預期變更，但不可把業務資料變更當成正常。未完成前不要宣稱資料保存驗收或部署成功。

## 原電腦資料不會跟 PR 搬走

GitHub 包含程式、合成題庫與報告，**不包含** `.env`、PostgreSQL 資料卷、附件、Ollama 模型或 ignored `.superpowers/`。

原電腦最新更新前備份位於 `C:\Users\User\Desktop\專流\.superpowers\rag-q06-20261022\`：

- `before.dump`：SHA-256 `cb180aa9c6cd550b9656b15567d84f9cd5528183c67eb7900267bc5f82cc0e7c`，pg_restore可列目錄。
- `before-storage.tar`：SHA-256 `4b32b02bdaad769af8ee9b8b158c2009e50d9d35a4e769dd8a375d1606144842`，13個檔案逐一讀回、SHA與現場一致。
- `before.json`／`after.json`、`metadata-before.json`、`preservation-result.json`、本機私密`deployment.env`及容器image／mounts紀錄。備份不進Git。

更早的 `.superpowers/rag-quality-20261021/` 備份保留：

- `before.dump`：SHA-256 `1f253ad90789f1acd48b9f6b4af4cae7e5c9e491013f36d8b4afec3740644eef`，已確認 pg_restore 能列目錄。
- `before-storage.tar`：SHA-256 `4b32b02bdaad769af8ee9b8b158c2009e50d9d35a4e769dd8a375d1606144842`。
- `before.json`：部署前逐列／附件指紋；另有 `backup-result.json`。

若要在新電腦接續同一批資料，需安全複製備份與必要部署設定，驗證雜湊，再依既有還原流程處理；不要把備份或 `.env` 提交到 Git。10/12 倉庫展示包不是原電腦現行完整資料的替代品。

本機另有未提交的 SYS-PACK4 看板草稿及使用者解壓的 `RAG虛構資料包/`，不混入此 PR，也沒有刪除。
