# 安裝、試用與接手開發

> 2026-11-06 從 [README](../README.md) 搬出：原本 README「§1 快速開始」的完整內容與「給接手的人」都在這裡。README 只留最短的啟動步驟。

## 目錄

- [正式版（本機）](#正式版本機)
- [給別人試用](#給別人試用)
- [可攜展示包（放到別人的 Windows 電腦）](#可攜展示包放到別人的-windows-電腦)
- [自動驗收（開發者）](#自動驗收開發者)
- [單檔 Demo（保留參照）](#單檔-demo保留參照)
- [給接手的人：怎麼請 AI 繼續開發](#給接手的人怎麼請-ai-繼續開發)

---

## 正式版（本機）

需要 Python 3.13 與 Docker Desktop（Linux 容器）。在 repo 根目錄執行：

```powershell
python deploy/start.py --seed-demo   # 第一次：建立示範帳號
python deploy/start.py               # 之後重啟：保留資料，不要再加 --seed-demo
```

開啟 <http://127.0.0.1:15173>，以公司 `food`、帳號 `yu`、密碼 `demo-yu` 登入。資料存在 PostgreSQL volume，不要刪除 volume 或重設資料庫。

**在另一台電腦還原展示資料**：先用 `python deploy/start.py` 建立空環境，再執行 `python deploy/demo_data.py import`。資料包是去敏的虛構資料，帳號密碼都是 `demo-<帳號>`，只能還原到同版本的空資料庫，見[資料包說明](../deploy/demo-data/README.md)。

## 給別人試用

| 範圍 | 怎麼開 | 注意 |
|---|---|---|
| 同一個網路 | `python deploy/start.py --lan`，對方開 `http://<這台電腦的IP>:15173` | 只開放網頁，API 與資料庫仍只在本機。Windows 防火牆要自己開；不是 HTTPS。不加 `--lan` 重啟就關閉 |
| 網際網路 | 雙擊 `開機自動啟動-公開試用.bat`（或執行 `python deploy/public_trial.py`），經 Tailscale Funnel 發布 `https://<這台電腦>.<tailnet>.ts.net:10000` | 停止用 `停止公開試用.bat`。把捷徑放進 `shell:startup` 會在登入時自動啟動。公開模式下直接執行 `start.py` 會關掉公開入口，要恢復就再跑一次啟動器 |

展示密碼 `demo-<帳號>` 猜得到，只給信任的測試者，用完就停。AI 模型設定只能從本機操作。細節見正式版開發指南的[同網域試用](formal-development.md#同網域試用lan-trial)與[網際網路試用](formal-development.md#網際網路試用public-trial)。

## 可攜展示包（放到別人的 Windows 電腦）

`python deploy/portable/build.py …` 會打包出一個約 7GB 的資料夾：內含 Python、Ollama、本地問答模型、OCR 與乾淨展示資料，對方解壓後雙擊「啟動專流.bat」就能用，不需安裝或連網，只綁 127.0.0.1。打包參數與驗證方式見 [deploy/portable/README.md](../deploy/portable/README.md)。

## 自動驗收（開發者）

先照[正式版開發指南](formal-development.md)安裝鎖版的 API／Web 測試依賴，再執行：

```powershell
api/.venv/Scripts/python.exe deploy/verify.py --keep-running
```

這個命令在獨立的 `projectflow-acceptance` 環境（入口 15175）依序跑 PostgreSQL 遷移與並行驗收、API、Vitest、build 和 E2E，不會寫入 15173 的資料。失敗時回傳非零 exit code；拿掉 `--keep-running` 會在結束後停止驗收服務。人類試用請照[試用清單](mvp-trial-checklist.md)。

每次 push 到 `main` 或開 PR，GitHub Actions 會自動跑五項檢查：API（pytest）、專用 PostgreSQL、Web（Vitest＋build）、單檔 Demo 測試頁，以及部署設定（Compose 與 n8n 流程檔）。各項在本機怎麼跑見[正式版開發指南的 CI 段落](formal-development.md#持續整合ci)。

## 單檔 Demo（保留參照）

`projectflow-full-demo.html` 是早期的完整互動 Demo，不需要安裝。資料存在瀏覽器 localStorage，附件存在 IndexedDB，左下角可以切換公司與身分。`projectflow-petfood-demo.html` 是階段 0 存檔。兩個檔案都不再修改。

```bash
start projectflow-full-demo.html        # Windows；macOS 用 open
python -m http.server 8000              # 或起一個本機伺服器
# Demo：http://localhost:8000/projectflow-full-demo.html
# 測試：http://127.0.0.1:8000/tests/records.html?t=任意時間戳
```

測試頁會清掉 `127.0.0.1` 這個網址下的 Demo 資料；自己試用請開 `localhost`。

---

## 給接手的人：怎麼請 AI 繼續開發

開發進度、流程和決策都寫在 repo 裡，任何 AI 都可以照文件接手，不需要靠對話記憶。

| 文件 | 用途 |
|---|---|
| [docs/PROGRESS.md](PROGRESS.md) | 進度看板：「▶ 現在」、工作佇列、測試基準、待人類決定（§6） |
| [docs/WORKFLOW.md](WORKFLOW.md) | 開發流程，目前用 §14 精簡流程 |
| [AGENTS.md](../AGENTS.md) | AI 入口與硬性規則 |
| [docs/formal-development.md](formal-development.md) | 正式版開發、部署與試用的操作細節 |
| [docs/technical-roadmap.md](technical-roadmap.md) | 技術選型、功能對應的程式檔、資料表 |

**取得最新的 `main`**

```bash
git fetch origin
git checkout main
git pull --ff-only origin main
```

**用 Claude Code（建議）**：在專案資料夾開一個新的 session，輸入：

| 想做什麼 | 輸入 |
|---|---|
| 看現在的狀況（不改 repo） | `/pf-status` |
| 往前推進一步 | `/pf-next` |
| 一路做到目前的工作項目完成，遇到要人類決定的事就停下來 | `/pf-next all` |
| 只預覽下一步（不改 repo） | `/pf-next dry` |

**用其他 AI（Codex、Gemini、Cursor 等）**：開場貼這段：

```text
請先讀 AGENTS.md，照「開工三步」做：看 docs/PROGRESS.md 的「▶ 現在」，照 docs/WORKFLOW.md 推進下一步。
每完成一段都要更新 PROGRESS 並 commit；遇到 AGENTS.md §5 列的情況就停下來問我。
```

**AI 什麼時候會停下來問你**

- **需要產品決定**，或 spec／plan 和程式衝突時：AI 會先在 PROGRESS §6 登記 D 編號再問你。直接回結論就好，例如「D7 照建議」。
- **spec 沒寫到的小細節**：AI 會照建議做，記成「AI 代決（可推翻）」。想改就說「Dn 改成…」。
- **push 與合併**：完成並通過審查的階段會依 D50 推上 `main`；其他 push、PR 和無法 fast-forward 的合併，都要你明確指示。
- 你在對話中直接下的指示優先於看板，AI 會先寫進 PROGRESS 再照做。PROGRESS §6 已經裁決的事項，不要照 plan 的舊寫法改回去。
