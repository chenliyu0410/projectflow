# AI 原有展示資料（dataset-v1，重建的小型虛構版）

AI 副手「原有展示資料」用的資料包：Text-to-SQL 的 16 種固定分析與文件問答。全部虛構，由程式產生。規格見 [AI-DEMO-DATA 短規格](../../docs/superpowers/plans/2026-10-24-ai-demo-data.md)。

原本 2026-10-11 產生的大型資料包（144 個專案）不在 git，也已無法取得；這份是 2026-10-24 依同一份資料規格重建的小型版本。

| 內容 | 數量 |
|---|---|
| 公司 | 6（毛研食品、禾沐寵物營養、峰曜科技、光點企劃、雲序軟體、築衡工程） |
| 每家 | 10 人、4 個專案（標題加「（AI 延伸案）」）、60 個任務、4 家供應商、24 張採購單、20 筆成本、12 批抽查、6 筆風險、30 則筆記、13 份文件 |
| 基準日 | 2026-10-11（「本週」為 10/05–10/11） |

每家公司照同一套劇本，讓每種分析都有重點：PRJ2 超支、S2 有逾期未交、S3 延遲率最高、PRJ4 不良率最高、PRJ3 退回與受阻最多、本週到期未完成 4 筆、至少 2 批零不良。成本報告只限管理者與專案負責人。

## 產生與驗證

```powershell
python deploy/ai-demo-data/generate.py --out <新資料夾>   # 每次產生的內容完全相同
python deploy/ai-demo-data/verify.py                       # 驗證 pack/
```

`verify.py` 用產品的匯入器匯入、執行 6 家 × 16 種分析並與 `evaluation/expected.json`（產生器不經 SQL 算出）比對，檢查劇本、文件權限與重產一致。`pack/` 進 git，位元組不可改（`.gitattributes`）；要改內容請改產生器後重新產生並更新 `pack/`。

## 匯入

可攜展示包由 `deploy/portable/build_seed.py` 自動匯入。正式 Docker 版：

```powershell
docker cp deploy/ai-demo-data/pack projectflow-formal-api-1:/tmp/ai-pack
docker exec projectflow-formal-api-1 python -m app.ai.import_cli /tmp/ai-pack
```

已匯入其他版本的 `dataset-v1` 時，匯入器會拒絕覆蓋。
