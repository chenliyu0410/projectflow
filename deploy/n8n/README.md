# n8n 地端自架：通知外送與 AI 週報

n8n 只負責排程和寄信，資料、權限、AI 與稽核都留在專流。規格見 [N8N 第一批規格](../../docs/superpowers/specs/2026-11-02-n8n-batch1-design.md)。

```
n8n ──每分鐘拉待送信件（Bearer PF_N8N_TOKEN）──▶ 專流 /integrations/*
 └──SMTP──▶ Mailpit（展示用假信箱，信件不會離開這台電腦）
```

## 三個流程（`workflows/`）

| 流程 | 時間 | 做什麼 |
|---|---|---|
| 通知轉寄 | 每分鐘 | 拉待送信件 → 逐封寄出 → 回報成功或失敗（失敗 5 次停止重試） |
| 每日摘要 | 週一至五 09:00 | 請專流把每人的「昨天完成／今天到期／逾期／卡住」寫成待送信件 |
| 週報草稿 | 週五 17:00 | 請專流為每個專案產生週報草稿，寄信通知專案負責人確認 |

週報草稿由專案負責人在專案的「週報」分頁修改、確認後才寄出；收件人是專案負責人與參與此專案的管理角色。

## 啟動展示環境（獨立資料庫，不動平常的 projectflow-formal）

```bash
python deploy/n8n/setup.py --seed-demo
python deploy/n8n/verify.py
```

- 設定檔在 `output/n8n-demo/.env`（不進 git），第一次執行時自動產生資料庫密碼和 `PF_N8N_TOKEN`。
- 網址：專流 http://127.0.0.1:15183、Mailpit http://127.0.0.1:8025、n8n http://127.0.0.1:5678（第一次開啟要建立 n8n 管理者帳號）。
- `--seed-demo` 只用在全新的資料庫；展示帳號的 Email 是 `<帳號>@demo.local`。
- `verify.py` 會指派一個任務、產生每日摘要、產生並寄出一份週報，三封信都在 Mailpit 收到才算通過（exit 0）。

## 接到平常的本機環境

1. 在 `deploy/.env` 加上 `PF_N8N_TOKEN=<至少 24 字元的隨機字串>`。
2. 先備份資料庫，再執行 `python deploy/n8n/setup.py --project projectflow-formal --env-file deploy/.env`（會升級 migration 到 `20261102_0022`，並替沒有 Email 的帳號填 `<帳號>@demo.local`）。

## 離線與安全

- 映像版本寫死：`docker.n8n.io/n8nio/n8n:2.45.7`、`ghcr.io/axllent/mailpit:v1.32.0`；先下載好即可離線使用。
- n8n 已關閉使用統計、版本檢查、範本庫；所有埠只綁 127.0.0.1。
- 不使用 n8n 的雲端 AI 節點；週報的 AI 走專流既有的本地模型設定，模型沒開時改用程式整理的條列。
- 換成公司真正的郵件伺服器時，只要在 n8n 修改「Mailpit SMTP」這組 SMTP 設定。
