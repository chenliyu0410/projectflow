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
| 收件匣 | 每分鐘 | 請專流掃描收件匣資料夾：專案資料夾裡的檔案存成專案文件並解析（含 OCR），Excel 匯入營運資料 |
| 每日維運 | 每天 02:00 | 完整備份（保留最近 7 份）並寄信給管理者；營運資料 30 天內到期就寄信，並在關聯的任務下建立「更新到期」任務 |

週報草稿由專案負責人在專案的「週報」分頁修改、確認後才寄出；收件人是專案負責人與參與此專案的管理角色。

## 收件匣與備份資料夾

```
deploy/inbox/                      （隔離展示環境在 output/n8n-demo/inbox）
  food/                            ← 公司代碼
    成貓主食罐正式版/                ← 專案名稱（完全相同）
      會議紀錄.pdf                  → 存成專案文件、解析／OCR，寄信通知專案負責人
      已匯入/  失敗/                 ← 處理後自動搬到這裡；失敗會附「.原因.txt」
    _營運資料匯入/
      供應商.xlsx                   → 第一列欄名，必須有「代碼」「名稱」，可有「狀態」；代碼已存在就更新
deploy/backups/                    ← 每日完整備份 projectflow-backup-<時間>.zip
```

- 檔名用營運資料的分類名稱，例如「供應商.xlsx」「原料.xlsx」，或英文代號（partners、resources…）。
- 欄名含「到期」或「有效期限」的欄位會被每日維運檢查。
- 備份檔含帳號密碼雜湊且未加密，備份資料夾請只讓管理者存取，並另外保存到安全的地方。
- 還原備份：在空的資料庫升級 migration 到同一版後，於 api 容器執行 `python -m app.demo_pack import /var/lib/projectflow-backups/<備份.zip>`（帳號密碼維持原樣；目標資料庫有資料時會拒絕覆蓋）。

## 啟動展示環境（獨立資料庫，不動平常的 projectflow-formal）

```bash
python deploy/n8n/setup.py --seed-demo
python deploy/n8n/verify.py
```

- 設定檔在 `output/n8n-demo/.env`（不進 git），第一次執行時自動產生資料庫密碼和 `PF_N8N_TOKEN`。
- 網址：專流 http://127.0.0.1:15183、Mailpit http://127.0.0.1:8025、n8n http://127.0.0.1:5678（第一次開啟要建立 n8n 管理者帳號）。
- `--seed-demo` 只用在全新的資料庫；展示帳號的 Email 是 `<帳號>@demo.local`。
- `verify.py` 依序驗證：指派通知、每日摘要、週報、收件匣文件、Excel 匯入、到期提醒與建任務、備份；每一步的信都在 Mailpit 收到才算通過（exit 0）。

## 接到平常的本機環境

1. 在 `deploy/.env` 加上 `PF_N8N_TOKEN=<至少 24 字元的隨機字串>`。
2. 先備份資料庫，再執行 `python deploy/n8n/setup.py --project projectflow-formal --env-file deploy/.env`（會升級 migration 到 `20261102_0022`，並替沒有 Email 的帳號填 `<帳號>@demo.local`）。

## LINE 廣播（選用）

1. 在 LINE Developers 建立 Messaging API channel（同時會建立 LINE 官方帳號），發行 Channel access token。
2. 在 `deploy/.env` 填 `PF_LINE_CHANNEL_TOKEN=<token>`（不進 git），重新執行 `python deploy/start.py`。
3. 想收通知的人用 LINE 加官方帳號為好友。

「通知轉寄」寄出 Email 後，標記要推 LINE 的事件會再廣播一則：站內通知（指派、待審核等）、週報已寄出、收件匣新文件與匯入完成、到期提醒、備份失敗。每日摘要、週報草稿、備份成功只寄 Email。

- 廣播會送給**所有好友**，訊息只含標題與任務名稱，不含連結（專流只綁 127.0.0.1，手機打不開）、內文或機密欄位。廣播不依權限過濾，所以任務名稱、營運資料名稱本身請不要放機密。
- 需要連外網；LINE 失敗不影響 Email 的寄送結果，也不會重試。免費方案每月有則數上限。
- 收件人沒有 Email 或關閉通知而被略過的事件，不會推 LINE。

## 離線與安全

- 映像版本寫死：`docker.n8n.io/n8nio/n8n:2.45.7`、`ghcr.io/axllent/mailpit:v1.32.0`；先下載好即可離線使用。
- n8n 已關閉使用統計、版本檢查、範本庫；所有埠只綁 127.0.0.1。
- 不使用 n8n 的雲端 AI 節點；週報的 AI 走專流既有的本地模型設定，模型沒開時改用程式整理的條列。
- 換成公司真正的郵件伺服器時，只要在 n8n 修改「Mailpit SMTP」這組 SMTP 設定。
