# PUBLIC-TRIAL：用 Tailscale Funnel 開放網際網路試用（短規格／計畫）

> 精簡流程（WORKFLOW §14／§14.1）。人類 2026-10-14 指示「給我本地開伺服器，讓別人能測試 projectflow 的方法」，並附上另外兩個專案的開機自動啟動 .bat（都用 Tailscale Funnel）作參考。被問到開放範圍時選「網際網路（Funnel）」，啟動方式選「開機自動啟動 .bat」。這等於授權本機 15173 透過 Funnel 對網際網路開放試用（D65 §14 第 7 點）。

## 目標

在 repo 根目錄放一個 `開機自動啟動-公開試用.bat`，把它的捷徑放進 `shell:startup`。登入 Windows 後會開一個可見的視窗，依序做這些事：

1. 等 Docker 就緒。
2. 用公開模式啟動 15173（資料保留，不 seed）。
3. 等 Tailscale 連線。
4. 用 Funnel 的 10000 埠發布網址：`https://<本機>.<tailnet>.ts.net:10000`。
5. 印出本機和公開網址的健檢結果。

另外放一個 `停止公開試用.bat`，用來關閉公開。

## 現況與限制

- 這台電腦的 Funnel 已經占用 443（LH，轉到 8000）和 8443（PowerQueryTW，轉到 8766）。Funnel 只允許 443、8443、10000 三個埠，所以 ProjectFlow 用 10000。設定前要先檢查 10000，如果已經被其他目標占用，就拒絕覆蓋。
- 經過 Funnel 的請求，會由本機的 tailscaled 轉發到 127.0.0.1。Docker 在 Windows 上分辨不出這是本機瀏覽器還是 Funnel 轉來的。API 判斷「本機」只看 Host 標頭，所以從網際網路送一個偽造的 `Host: 127.0.0.1`，就能被當成本機，進而取得只限本機的 AI 模型設定。
- 切換公司會比對 `Origin` 和 `request.base_url`。Funnel 那一端是 https，API 收到的卻是 http，兩邊對不上，所以從 Funnel 切換一定會回 403。

## 範圍

- `deploy/nginx.conf`：同一個 server 再監聽 81，作為 Funnel 專用入口：
  - 81 只接受 `<名稱>.<名稱>.ts.net` 的 Host，其他一律回 421。這樣從公開入口進來的請求，永遠不會被當成本機。
  - 81 對 API 帶 `X-Forwarded-Proto: https`，80 帶 `http`，並且覆寫用戶端自己送來的同名標頭。另外也覆寫 `X-Forwarded-For`。
  - `proxy_set_header` 移到 server 層級，讓各個 location 繼承。
- 新增 `deploy/docker-compose.public.yml`，只在公開模式疊加：
  - web 多一個 `127.0.0.1:${WEB_PUBLIC_PORT:-15174}:81`，只綁 loopback。
  - API 加 `FORWARDED_ALLOW_IPS: '*'`，讓 uvicorn 採用 nginx 送來的 https。API 埠本來就只綁 127.0.0.1。
- `deploy/start.py`：
  - `start(..., public=False)` 為 True 時：疊加上面那份 compose；`PF_SHOWCASE_LAN=true`，讓公開的管理員能切換展示公司，比照 LAN-SWITCH；web 仍然綁 127.0.0.1。
  - 核對 `compose port web 81` 必須是 `127.0.0.1:<埠>`，回傳 `public_target`。
  - 不能和 acceptance 一起用，在執行任何命令之前就拒絕。
  - CLI 不新增旗標，入口統一走下面的啟動器。
- 新增 `deploy/public_trial.py`：
  - 啟動：等 Docker。等不到時，如果有 Docker Desktop 就幫忙啟動一次，最多等 5 分鐘。接著 `start(public=True)`，等 Tailscale（最多 2 分鐘），發布 Funnel 10000 → `public_target`，最後做健檢。
  - `--stop`：10000 指向我們的目標時才執行 `funnel off`，然後用 `start()` 預設模式重啟，回到只有本機。
  - 所有 tailscale／docker 呼叫都有逾時。訊息用繁體中文，不輸出 Docker 錯誤原文。
- repo 根目錄新增兩個 .bat：內容只用 ASCII 和 CRLF，訊息全部來自 Python。這是照 LH 的經驗：cmd 會用 cp950 解讀 .bat，裡面有中文會解析錯位。`.gitattributes` 把 `*.bat` 固定為 CRLF。
- 文件：`docs/formal-development.md` 新增「網際網路試用」段落，README 開頭加一則說明，PROGRESS 也要更新。

## 不變

- 不改 API 程式。`PF_SHOWCASE_LAN` 的語意沿用「允許非本機 Host 使用展示切換」。
- AI 模型設定照舊只限本機。從公開入口進來的 Host 永遠是 ts.net，所以不能設定。
- 不加 `--lan` 時，web 照舊只綁 127.0.0.1。公開模式和 `--lan` 是兩件事：啟動器用公開模式時，`lan=False`。
- 預設的 `python deploy/start.py` 不疊加 public compose。所以任何不帶公開模式的重啟，都會拿掉 15174，公開網址隨之失效（Funnel 會回 502）。

## 已知風險（人類選擇 Funnel 時已提醒）

- 密碼是 repo 裡的 `demo-<帳號>`，拿到任何一組帳號的人都能推出管理員密碼，並寫入 15173 的資料。只把網址給信任的測試者，試用完就停止。改密碼、帳號管理、登入次數限制都不在本次範圍。
- 試用者的修改會直接寫進 15173 的資料庫，和 LAN 試用相同。

## 資料變更

沒有 migration，不 seed。web 映像重建（nginx.conf 有改），API 和 web 容器會因為環境變數和埠改變而重建；DB 容器與 volume 保留。部署前先 pg_dump。

## 允許修改的檔案

`deploy/nginx.conf`、`deploy/docker-compose.public.yml`（新）、`deploy/start.py`、`deploy/public_trial.py`（新）、`api/tests/test_deployment.py`、`api/tests/test_public_trial.py`（新）、`開機自動啟動-公開試用.bat`（新）、`停止公開試用.bat`（新）、`.gitattributes`、`docs/formal-development.md`、`README.md`、`docs/PROGRESS.md`。

## 步驟

1. 先寫測試，跑出 RED：
   - start.py：public 會疊加 compose、`PF_SHOWCASE_LAN=true`、`WEB_BIND=127.0.0.1`，核對 81 綁 loopback 並回傳 `public_target`；81 綁錯時拒絕；和 acceptance 一起用時，在任何命令之前拒絕；預設模式不疊加。
   - compose overlay、nginx 的契約字串。
   - public_trial.py：Funnel 10000 空著才發布，已經是我們的目標時重發不出錯，被別的目標占用時拒絕；stop 只關掉我們的目標；啟動順序正確；start 失敗時不碰 Funnel；tailscale 沒裝或逾時時，不拋出例外。
2. 實作到 GREEN，跑 `test_deployment.py`、`test_public_trial.py`、showcase 相關測試。
3. 一次唯讀獨立審查。
4. ff-only 合併 main。
5. 部署：
   - pg_dump 後執行 `python deploy/public_trial.py`。
   - 核對 DB 容器沒有重建、`compose port`（web 80→127.0.0.1:15173、81→127.0.0.1:15174）。
   - 本機 15174：用 ts.net Host 回 200，用 `Host: 127.0.0.1` 回 421。
   - 公開網址的 `/api/health/ready` 回 ready。透過公開網址偽造 `Host: 127.0.0.1` 時回 421。
   - 在本機 15174 帶 ts.net Host 和 https Origin 登入 yu，`/auth/me` 要有切換清單；不實際切換，避免寫入稽核。
6. 依 D50 push。

## 驗收情境

- 自動測試涵蓋公開模式的 compose／環境變數／埠核對、Funnel 不覆蓋別人的設定、停止流程。
- 部署後公開網址可用；偽造本機 Host 被擋下；本機 127.0.0.1:15173 照舊可用；區網不開放。
- 從外部網路用瀏覽器實際登入與切換，由人類或試用者確認（AI 不在公開網址輸入密碼）。
- 開機捷徑放進 `shell:startup` 這件事，由人類決定、人類執行。
