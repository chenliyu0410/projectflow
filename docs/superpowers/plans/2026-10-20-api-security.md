# API-SECURITY：後端安全強化（短規格／計畫）

> 精簡流程（WORKFLOW §14）。人類 2026-10-20 要求把一次唯讀審查找到的問題全部修掉，可平行的各開分支。本分支 `claude/api-security-15bb48` 只處理後端安全八項；PROGRESS、README 由主 session 合併時更新，本檔記錄計畫與結果。

## 範圍與做法

每項先寫會失敗的測試（`api/tests/test_api_security.py`），再修到通過。

| # | 問題 | 改法 | 檔案 |
|---|---|---|---|
| 1 | session cookie 沒有 `Secure` | 依 `request.url.scheme` 決定：https（含公開模式由 nginx 81 帶 `X-Forwarded-Proto: https`、uvicorn 依 `FORWARDED_ALLOW_IPS` 採信）設 `Secure`，本機 http 不設。登入、切換公司、登出都一致 | `routes/auth.py` |
| 2 | `local_admin` 只看 Host，可偽造 | 「本機」改成同時符合：Host 是 loopback，而且 web 沒有對區網開放（新環境變數 `PF_WEB_LAN`，只有 `start.py --lan` 設為 true）。理由見下方「拓撲」 | `routes/ai.py`、`deploy/start.py`、`deploy/docker-compose.yml` |
| 3 | 寫入路由沒有來源檢查 | `main.py` 加一層 ASGI middleware，擋 POST/PUT/PATCH/DELETE：有 `Sec-Fetch-Site` 時只接受 `same-origin`／`none`；沒有時看 `Origin`，必須等於 API 自己的 origin（`null` 也擋）；兩者都沒有視為非瀏覽器請求，放行 | `main.py` |
| 4 | 公開環境暴露 OpenAPI／docs | 預設關閉 `/openapi.json`、`/docs`、`/redoc`；開發時設 `PF_API_DOCS=true` 才開 | `main.py` |
| 5 | nginx 沒有安全標頭 | server 層加 `X-Frame-Options DENY`、`X-Content-Type-Options nosniff`、`Referrer-Policy same-origin`、`Content-Security-Policy "frame-ancestors 'none'"`，都加 `always`；各 location 沒有自己的 `add_header`，會繼承 | `deploy/nginx.conf` |
| 6 | `verify_password` 忽略雜湊內的 rounds | 用雜湊記錄的 rounds 計算 | `security.py` |
| 7 | 帳號不存在時不跑 PBKDF2 | 帳號不存在時對一組固定的假雜湊跑一次 `verify_password` | `routes/auth.py` |
| 8 | AI SQL 超過步數上限或 sqlite 錯誤時回 500 | `store` 把步數上限中斷轉成 `QueryTooLarge`；路由回 422「查詢過於複雜…」，其他 `sqlite3.Error` 回 503「AI 展示資料暫時無法查詢」 | `ai/store.py`、`routes/ai.py` |

### 拓撲（第 2、3 項的依據）

- API 容器只綁 `127.0.0.1:18000`；瀏覽器都經 web 容器 nginx 轉進來，nginx 用 `proxy_set_header Host $http_host` 原樣轉 Host。
- 預設模式：web 80 只綁 127.0.0.1，能連到的都是本機，Host 無法被外部利用。
- 公開模式：80 仍只綁 127.0.0.1；Funnel 走 81，nginx 只接受 `*.ts.net` Host，並覆寫 `X-Forwarded-Proto`／`X-Forwarded-For`。所以從公開入口來的請求 Host 不會是 loopback。
- `--lan` 模式：80 綁 0.0.0.0，區網任何人都能送 `Host: 127.0.0.1`。Windows 上的 Docker Desktop 轉送已發布埠時，容器看到的來源位址不能可靠分辨本機和區網，所以不能改用 `request.client`／`X-Forwarded-For` 判斷。可靠的資訊只有「這次啟動有沒有對區網開放」，因此由 `start.py` 明確告訴 API（`PF_WEB_LAN`）。代價：`--lan` 模式下連本機管理者也不能在網頁上設定 AI 模型，要設定就先用一般模式（不加 `--lan`）啟動。
- uvicorn 0.54 的 proxy headers 只處理 `X-Forwarded-Proto`／`X-Forwarded-For`，不採信 `X-Forwarded-Host`，所以用戶端無法透過這個標頭改 Host。

### 第 3 項為什麼 `Sec-Fetch-Site` 優先

`Sec-Fetch-Site` 是瀏覽器自己判斷後填的禁用標頭，網頁 JS 改不了；有它就直接採用，不再拿 `Origin` 和 Host 比對。這樣即使代理（例如 Funnel）改寫了 Host 的埠號，也不會誤擋正常操作。舊瀏覽器沒有 `Sec-Fetch-Site` 時，才退回比對 `Origin`。兩者都沒有的請求（curl、Playwright 的 `page.request`、TestClient、部署腳本）不是瀏覽器跨站請求，放行；瀏覽器發出的 POST/PUT/PATCH/DELETE 一定會帶 `Origin`。

## 不在範圍（只記錄）

- demo 密碼與帳號管理（路線圖）。
- repo 外 8443 的本地共用版。
- 展示公司跨公司切換政策（待人類決定）。
- `app/showcase.py` 的 `local_request` 同樣只看 Host，但 `--lan` 與公開模式下 `PF_SHOWCASE_LAN` 本來就是 true，一般模式 web 只綁 loopback，目前沒有可利用的路徑；檔案不在本分支範圍，沒有改。
- PROGRESS、README 不在本分支更新。

## 驗證

- 新增測試：`python -m pytest api/tests/test_api_security.py -q`
- 全量：`python -m pytest api/tests -q`（含 `test_deployment.py`）

## 結果

### 測試

- RED（在 main @3c1294e 的原始碼上跑同一份新測試）：`19 failed, 9 passed`。通過的 9 個是本來就該成立的防護（同源與非瀏覽器寫入、GET 不受影響、公開入口不算本機、開發時可開文件頁、正確密碼只驗一次）。
- GREEN：`api/tests/test_api_security.py` `28 passed`。
- 相關既有測試（auth、ai、showcase、hemu／industry showcase、deployment、health、public_trial）：`126 passed`。
- nginx：用本機現有的 `nginx:1.30.4` 開暫時容器（不碰正在執行的 stack）跑 `nginx -t` 通過；實際請求 80 的 200、81 偽造 Host 的 421、`/api` 的 502 都帶四個標頭。容器已移除。
- 全量 `python -m pytest api/tests -q`（含 test_deployment）：`692 passed, 14 skipped`，exit code 0，約 17 分鐘。14 個 skip 都是需要專用 PostgreSQL 的測試（test_migrations、test_collaboration_postgresql），這台沒有設定對應的測試資料庫 URL。

### 未完全解決的限制

- **Cookie 不分埠號**：瀏覽器的 cookie 只看主機名稱，不看埠號，所以 `<機器>.ts.net:443`／`:8443` 上的其他服務仍會在每次請求收到 `pf_session`，也能用同名 cookie 覆寫它。評估過的做法：
  - `__Host-` 前綴：只能防止子網域用 `Domain` 屬性塞 cookie，同主機其他埠一樣能設定，對埠號沒有幫助；還要改 `app/auth.py`（不在本分支範圍）並在 http 本機模式用另一個名字。沒有做。
  - `Path=/api`：可以讓其他服務只有 `/api/*` 路徑收到 cookie，但 API 看到的路徑已被 nginx 去掉 `/api`，要另外加設定，而且其他服務仍能用 `Path=/api` 覆寫。收益有限，沒有做。
  - 真正的解法是讓 ProjectFlow 用獨立的主機名稱（例如另一個 tailnet 節點名稱），這會動到 Tailscale 設定，不在本次範圍。
  - 已經降低的部分：cookie 是 `HttpOnly`，其他服務的網頁 JS 讀不到；新的來源檢查讓其他埠的網頁無法用這顆 cookie 送出寫入請求（`Sec-Fetch-Site: same-site` 會被擋）。剩下的風險是其他服務的伺服器端程式本身能看到 cookie。
- **`--lan` 模式不能在網頁設定 AI 模型**：連本機管理者也不行，要設定就用一般模式（不加 `--lan`）或公開模式從本機 `http://127.0.0.1:15173` 進入。
- **沒有 `Sec-Fetch-Site` 也沒有 `Origin` 的寫入請求放行**：這是為了 curl、Playwright `page.request`、TestClient 與部署腳本。現代瀏覽器的寫入請求都帶 `Origin`，所以不影響 CSRF 防護。
- **公開模式的 `Origin` 備援比對**：只在舊瀏覽器（沒有 `Sec-Fetch-Site`）才用到；如果 Funnel 轉送時改掉 Host 的埠號，這類舊瀏覽器會被誤擋。沒有實際連 Funnel 驗證（本次不碰正在執行的部署）。
- **沒有用真瀏覽器跑 web**：前端是否正常靠測試與規格推論（瀏覽器同源 fetch 一定帶 `Sec-Fetch-Site: same-origin`）。部署前建議跑一次 web e2e。
- `app/showcase.py` 的 `local_request`：見上方「不在範圍」。

### 怎麼驗證

1. `python -m pytest api/tests/test_api_security.py -q`，應該 `28 passed`。
2. 重新部署後（`python deploy/start.py` 或公開試用啟動器），用瀏覽器登入、建立／修改一筆資料，應該都正常。
3. 開發者工具 → Network：
   - 公開網址的 `/api/auth/login` 回應，`Set-Cookie` 有 `Secure`；本機 `http://127.0.0.1:15173` 沒有。
   - 任一頁面回應都有 `X-Frame-Options: DENY`、`X-Content-Type-Options: nosniff`、`Referrer-Policy: same-origin`、`Content-Security-Policy: frame-ancestors 'none'`。
4. `curl.exe -s -o NUL -w "%{http_code}" http://127.0.0.1:15173/api/openapi.json` 應該是 `404`。
5. `curl.exe -s -X POST -H "Origin: http://evil.example" -H "Content-Type: application/json" -d "{}" http://127.0.0.1:15173/api/auth/login` 應該回 `{"detail":"不允許此來源"}`（403）。
