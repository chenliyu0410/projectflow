# 可攜展示包（開發者說明）

把專流（含本地 AI 副手、OCR、文件樣板與乾淨展示資料）打成一個資料夾，複製到另一台 Windows 10／11 x64 電腦，解壓後雙擊「啟動專流.bat」即可展示。規格見 [PORTABLE 短規格](../../docs/superpowers/plans/2026-10-24-portable.md)；給使用者的說明是 [使用說明.txt](使用說明.txt)。

## 打包

在 repo 根目錄（需要 `uv`、`web/node_modules`、repo 外的 `output/rag-starter-node`）：

```powershell
python deploy/portable/build.py `
  --gguf <Qwen_Qwen3-4B-Instruct-2507-Q4_K_M.gguf> `
  --bge-store <含 bge-m3 的 Ollama models 資料夾> `
  --ocr-models <繁中 OCR 模型資料夾> --zip
```

- 產物在 repo 外 `output/portable/ProjectFlow-Portable-<日期>/`（`--zip` 另產生同名 .zip），不進 git。
- 只下載 python-build-standalone 3.12 與鎖版套件；Ollama 從本機安裝版複製（不含會自動更新的系統匣程式）。
- GGUF 會核對 SHA-256，必須是驗收用的同一個檔；模型以驗收時的 Modelfile（含 `TEMPLATE {{ .Prompt }}`）在包內重建。
- `build_seed.py` 從空資料庫重建展示資料：migration、`deploy/demo-data` 資料包、AI 入門教材、AI 原有展示資料（[deploy/ai-demo-data](../ai-demo-data/README.md)，Text-to-SQL 用）、`demo-docs/` 的四個 AI 示範專案、三份文件樣板，並建好 AI 索引與向量；6 家公司都啟用本機模型。
- 最後掃描整包：不得有 `.git`、`.env`、gemma，以及本機或 repo 的絕對路徑；結果寫在包內 `build.json`。

## 包內結構

| 路徑 | 內容 |
|---|---|
| `啟動專流.bat`／`停止專流.bat`／`還原展示資料.bat` | 呼叫 `runtime/launcher/*.ps1` |
| `runtime/python`、`runtime/ollama` | 執行環境 |
| `app/` | 後端程式、migration、`serve.py`、`web/`（前端 build） |
| `models/ollama`、`models/ocr` | 問答模型、bge-m3、OCR 模型 |
| `seed/` | 乾淨展示資料（唯讀，還原用） |
| `data/`、`logs/` | 第一次啟動時由 `seed/` 複製；執行記錄 |

網頁與 API 同在 `http://127.0.0.1:15190`（API 在 `/api`），模型服務在 `127.0.0.1:11437`，都只綁本機。停止腳本只結束執行檔位於包內的程序。

## 驗證

照規格「怎麼在乾淨環境驗證」三層。示範題自動檢查：

```powershell
<包>\runtime\python\python.exe deploy/check_demo_questions.py --url http://127.0.0.1:15190/api --report <報告.json>
```
