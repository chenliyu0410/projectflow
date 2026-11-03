# 正式版開發

P0至P1c為已交付本機MVP，P2a任務工作區已完成獨立審查、main隔離回歸及本機試用部署；人類試用待簽核，發布紀錄見PROGRESS。Demo保持獨立且不得視為正式登入／多租戶安全機制。

## 公司邊界

業務資料以organization_id識別公司。API從已驗證身分取得可用公司，查詢與外鍵須限制公司；不能信任前端傳來的公司參數。稽核、工作流建立同樣受限。目前P0至P1c本機MVP已通過逐Task與整體獨立審查及自動驗收。人類試用簽核見[驗收清單](mvp-trial-checklist.md)，未勾選項目仍待人類完成。

## 環境需求

### P1c 一鍵本機啟動

安裝Python 3.13與Docker Desktop後，可在repo根目錄執行以下單一命令。它建立缺少的本機設定、啟動Compose、執行migration，再確認HTTP就緒；已有 `.env` 不覆寫，volume不刪除。初始化本機示範帳號（含管理員yu）須明確加 `--seed-demo`，只適用本機MVP試用。

```powershell
python deploy/start.py --seed-demo
```

之後重啟用 `python deploy/start.py`，不重新種資料。此入口仍為 http://127.0.0.1:15173 。`deploy/.env`有`PF_N8N_TOKEN`（照`deploy/n8n/README.md`「接到平常的本機環境」設定過n8n）時，會一起啟動n8n與Mailpit（`--profile n8n`）；沒有token就不碰它們。初次Compose會下載Python／Node／PostgreSQL映像與鎖版套件，需要網路。這不是LAN／正式環境部署或人類試用簽核。

### 同網域試用（LAN-TRIAL）

要讓同一個網路的其他電腦試用，改用以下命令重啟。只有web綁定所有網卡，API與DB仍只在本機；資料不重設、不seed。

```powershell
python deploy/start.py --lan
```

成功後會印出 `Network access: http://<這台電腦的IP>:15173`，把這個網址給其他人。有VPN或多張網卡時，這個IP可能不是區網那張，請用 `ipconfig` 核對。這台電腦照舊用 http://127.0.0.1:15173 。要停止對外開放，不加 `--lan` 再執行一次 `python deploy/start.py`，web會回到只綁127.0.0.1。`--lan` 不能和 `--acceptance` 一起用。

- **防火牆要自己開**：Windows預設擋外部連線，網路類型是「公用」時更是如此。用系統管理員身分開PowerShell執行下面這行，只允許同網段連入15173；停止試用時用 `Remove-NetFirewallRule -DisplayName 'ProjectFlow 15173 (LAN trial)'` 移除。如果同事在不同網段，`LocalSubnet` 要換成對方的網段。
  ```powershell
  New-NetFirewallRule -DisplayName 'ProjectFlow 15173 (LAN trial)' -Direction Inbound -Protocol TCP -LocalPort 15173 -RemoteAddress LocalSubnet -Action Allow
  ```
  開了還是連不到時，到「Windows Defender 防火牆→輸入規則」看有沒有封鎖 Docker Desktop Backend 的規則；封鎖規則優先於允許規則。
- **帳號**：登入表單要填公司代碼、帳號、密碼。公司代碼是 `food`、`electronics`、`events`、`software`、`construction`、`hemu`，帳號清單在 `deploy/demo-data/tables/users.json`。資料包還原後密碼都是 `demo-<帳號>`，例如 `food`／`yu`／`demo-yu`。
- **切換公司**：`--lan` 時，管理員從區網登入後也能用左下「切換公司」在六家展示公司之間切換（例如 `food`／`yu`）；切過去的身分是該公司的「展示管理者」。非管理員看不到這個選單。前提是 `deploy/.env` 有 `PF_SHOWCASE_MODE=true`；不加 `--lan` 重啟後，區網的切換和展示身分的登入都會失效。
- **限制**：這些密碼寫在repo裡，同網路的任何人都能用管理員登入，只在信任的網路開放，試用完就關閉。沒有HTTPS。AI模型設定只在本機127.0.0.1的畫面出現；這個限制看的是Host標頭，知道管理員密碼的人可以偽造Host直接呼叫該API。
- **資料**：試用者的修改會直接寫進15173的資料庫。資料包只能匯入空的資料庫，要回到乾淨的展示資料得先清空資料庫再匯入（做法見 `deploy/demo-data/README.md` 與PROGRESS的OPS-RESTORE），清空前先備份。匯入流程會執行不加 `--lan` 的 `start.py`，完成後要再用 `--lan` 啟動一次。

### 網際網路試用（PUBLIC-TRIAL）

測試者如果不在同一個網路，可以用 Tailscale Funnel 把 15173 發布到網際網路，網址是 `https://<這台電腦>.<tailnet>.ts.net:10000`（HTTPS）。

開始前，這台電腦要先準備好：
- 已安裝 Docker Desktop、Python 3.13、Tailscale，而且 Tailscale 已登入。
- 這台電腦在 tailnet 有使用 Funnel 的權限。

- **啟動**：雙擊 repo 根目錄的 `開機自動啟動-公開試用.bat`，或執行 `python deploy/public_trial.py`。它會依序：
  1. 等 Docker 就緒。必要時會自動開 Docker Desktop，最多等 5 分鐘。
  2. 用公開模式啟動 15173。資料保留，不 seed。已設定 n8n 的話，n8n 與 Mailpit 也會一起啟動。
  3. 等 Tailscale 連線，最多等 2 分鐘。
  4. 發布 Funnel 的 10000 埠，然後印出本機和公開網址的健檢結果。

  把「公開」那個網址給測試者。
- **開機自動啟動**：按 Win+R 輸入 `shell:startup`，把 `開機自動啟動-公開試用.bat` 的**捷徑**放進去。不要複製檔案本身，因為它要靠所在位置找到 repo。之後每次登入 Windows，都會開一個視窗跑上面的流程。關掉這個視窗不會停止服務，因為容器是由 Docker 在跑。
- **停止**：雙擊 `停止公開試用.bat`，或執行 `python deploy/public_trial.py --stop`。它只會在 Funnel 10000 埠指向 ProjectFlow 時關閉 Funnel，接著用本機模式重啟。另外要注意：只要沒有經過啟動器就重啟，例如直接執行 `python deploy/start.py`（加不加 `--lan` 都一樣），公開入口就會被拿掉，公開網址會回 502。要恢復公開，再執行一次啟動器。
- **怎麼運作**：
  - Funnel 轉到 127.0.0.1:15174，也就是 web 容器 nginx 的 81 埠。15174 只綁 loopback。
  - 81 埠只接受 `*.ts.net` 的 Host，其他一律回 421。所以從網際網路偽造 `Host: 127.0.0.1`，也不會被當成本機。
  - 81 埠會告訴 API 原本的請求是 HTTPS，切換公司的同源檢查才會通過。
  - 15173、API、DB 照舊只在本機。
  - Funnel 只能用 443、8443、10000 這三個埠，這台的 443 和 8443 已經給其他專案用。10000 如果已經被別的服務占用，啟動器會停下來，不會覆蓋。
- **帳號與切換公司**：和同網域試用一樣，用公司代碼、帳號、`demo-<帳號>` 密碼登入。管理員也能用左下的「切換公司」。AI 模型設定只出現在本機的畫面，從公開網址看不到。
- **限制（重要）**：
  - 任何人拿到網址都能看到登入頁。
  - 密碼是 repo 裡的 `demo-<帳號>`，拿到任何一組帳號的人都能推出管理員密碼，進而修改 15173 的資料。
  - 只把網址和帳號給信任的測試者，試用完就停止。
  - 沒有帳號管理、改密碼、登入次數限制。
  - 要重置資料，照上面同網域試用的「資料」那一點做，完成後再執行一次啟動器。
- **和 `--lan` 的關係**：公開模式下，web 只綁 127.0.0.1，所以區網不開放。兩種模式不能同時用。

自動驗收使用另一個Compose專案、volume與loopback埠，避免寫入使用者試用資料：

```powershell
python deploy/start.py --acceptance --seed-demo
```

驗收入口預設 http://127.0.0.1:15175 ，API18002；私密設定位於gitignored `.superpowers/p1c/acceptance.env`。只有隔離API的 `/health/acceptance` 回200；共享API預設404。所有E2E在業務寫入前強制檢查此marker，並拒絕15173。既有測試專案不會自動刪除。

### 一鍵自動驗收

主機需要API `.venv` 的鎖版依賴、Web `npm ci` 的鎖版依賴與Playwright Chromium。驗收命令使用呼叫它的Python，不會代為安裝依賴：

```powershell
api/.venv/Scripts/python.exe deploy/verify.py --keep-running
```

依序執行隔離啟動（明確seed）、專用PG遷移／並行驗收、pytest、Vitest、build、Playwright。子程序的 `PF_BASE_URL` 來自隔離launcher回傳值，覆蓋傳入的共享網址，不修改呼叫端的環境變數。15175為目前驗收設定；合法的其他loopback驗收埠仍須marker確認。每階段失敗後停止後續測試，保留失敗exit code；orchestration錯誤只顯示固定訊息，不輸出Docker錯誤中的私密設定。

不加 `--keep-running` 時，已成功啟動的驗收stack會在finally以固定 `projectflow-acceptance`／私密env／Compose檔執行 `down`，不帶 `-v`，不停止primary、不刪歷史專案。測試已失敗時，清理失敗不覆蓋原exit code；只有清理失敗也會回非零。若啟動本身失敗，命令不執行down，可能留下部分驗收服務，請檢查該隔離專案後再重試。

測試輸出由各工具直接顯示；失敗依階段名稱定位。每次驗收保留新增測試專案／回報／稽核，並在finally恢復seed節點狀態。Playwright截圖位於 `web/test-results/`，下次執行會覆寫。完整自動結果與人類試用項目見[驗收清單](mvp-trial-checklist.md)。

- 本機開發：Python 3.13、Node 24.15以上且小於25；套件分別使用`api/requirements.lock`及`web/package-lock.json`。
- 完整環境：Docker Desktop的Linux容器引擎與Docker Compose。容器自帶Python／Node，不依賴主機安裝的執行環境。
- 目前為loopback本機MVP，可用 `--lan` 暫時開放同網域試用；部署強化（HTTPS、帳號管理）與人類內部試用簽核尚未完成，不可視為內網正式版發布。

## 本機API

在repo根目錄逐行執行：

```powershell
python -m venv api/.venv
api/.venv/Scripts/python.exe -m pip install -r api/requirements.lock
api/.venv/Scripts/python.exe -m pytest -c api/pyproject.toml api/tests -q
api/.venv/Scripts/python.exe -m uvicorn app.main:app --app-dir api --host 127.0.0.1 --port 18000
```

GET /health檢查API存活；GET /health/ready會實際查詢PostgreSQL，未設定DATABASE_URL或DB不可用時回503。不要把DSN／密碼提交到Git。

## 本機前端

Node 24.15以上、25以下。在repo根目錄逐行執行：

```powershell
npm.cmd --prefix web ci
npm.cmd --prefix web test
npm.cmd --prefix web run build
npm.cmd --prefix web run dev
```

開啟`http://127.0.0.1:15173`。開發代理將`/api`送到`http://127.0.0.1:18000`，不需要放寬跨來源政策。API使用其他埠時，先在同一終端設定`$env:API_PROXY_TARGET = 'http://127.0.0.1:<埠號>'`。目前前端先確認session，未登入時顯示登入表單；公司預設food，種子帳號見下表。登入後僅傳HttpOnly cookie，不接受前端切換公司或推斷完整操作權限；API為權限權威。登入後進總覽；主導覽提供總覽、我的任務與專案工作區，375px手機先按「導覽」展開。專案清單可切換詳情；節點樹依sort_order排列，可展開／收合，選取節點顯示可見路徑，空專案顯示沒有節點。載入錯誤可重試，401會清除session回登入；切換或登出後不套用舊回應。admin／project_owner可開啟「新增專案」的inline表單，選擇工作流模板並填名稱建立；成功後更新清單並選取新專案，403／404使用安全訊息。

看板顯示目前選取節點的下一層節點，保留四種工作狀態及獨立「已略過」清單；狀態選單透過API更新，成功才移欄，失敗保留原狀態。pending閘門顯示警示；admin、專案owner與reviewer顯示核准操作，實際權限由API強制。readonly隱藏狀態、核准與建立操作。403／409使用固定安全訊息；請求期間停用重複寫入，切換專案或登出後忽略舊mutation回應。

## 完整容器環境

以下PowerShell命令均從repo根目錄執行。先確認15173／18000未被其他服務使用：

```powershell
Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -in 15173,18000 }
```

僅在`deploy/.env`不存在時，產生本機專用設定；密碼不顯示、不進Git、不送前端。第一次使用的資料庫volume必須沒有既存的不同密碼。已有設定或volume時不要重產密碼，不要刪除volume。

```powershell
if (-not (Test-Path -LiteralPath deploy/.env)) {
  $bytes = New-Object byte[] 32
  $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
  try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
  $password = ($bytes | ForEach-Object { $_.ToString('x2') }) -join ''
  $config = "POSTGRES_PASSWORD=$password`nWEB_PORT=15173`nAPI_PORT=18000`n"
  [IO.File]::WriteAllText((Join-Path (Get-Location) 'deploy/.env'), $config, (New-Object Text.UTF8Encoding $false))
  Remove-Variable password,config,bytes
}
git check-ignore deploy/.env
docker compose --env-file deploy/.env -f deploy/docker-compose.yml config --quiet
docker compose --env-file deploy/.env -f deploy/docker-compose.yml up -d --build --wait
docker compose --env-file deploy/.env -f deploy/docker-compose.yml ps
```

開啟[專流正式版](http://127.0.0.1:15173)，目前Compose已重建為登入／專案工作流UI。首次啟動還須執行下節migration／seed。API存活檢查位於`http://127.0.0.1:18000/health`；`/health`不依賴DB，`/health/ready`確認真實DB連線，前端代理也提供`/api/health`與`/api/health/ready` HTTP檢查。

三個服務屬於`projectflow-formal`專案；PostgreSQL只在容器網路內開放，資料保留在`projectflow-formal_pgdata`。對外埠僅綁127.0.0.1。若埠被占用，只改本機`deploy/.env`的`WEB_PORT`／`API_PORT`，不要停掉其他人的服務；開發Vite可用`npm.cmd --prefix web run dev -- --port <空閒埠>`並同步設定API_PROXY_TARGET。本機API與Compose API不能同時占用18000。

## 整合驗收與恢復

E2E保留API存活／就緒與未知路由檢查，1280px／375px測試登入、指定seed專案、建立唯一測試專案、gate阻擋／核准／狀態更新及readonly。每次重跑只在隔離資料庫另建專案；角色測試暫時修改seed節點狀態，於finally恢復。測試專案與回報／稽核會留在隔離資料庫，沒有刪除API。

先啟動隔離Compose，再逐行執行（也可直接使用一鍵verify）：

```powershell
api/.venv/Scripts/python.exe deploy/start.py --acceptance --seed-demo
api/.venv/Scripts/python.exe -m pytest -c api/pyproject.toml api/tests -q
npm.cmd --prefix web ci
npm.cmd --prefix web test
npm.cmd --prefix web run build
Push-Location web
try { npm.cmd exec -- playwright install chromium } finally { Pop-Location }
npm.cmd --prefix web run e2e
```

E2E預設15175；若隔離環境WEB_PORT不同，先設定`$env:PF_BASE_URL = 'http://127.0.0.1:<隔離實際WEB_PORT>'`。共享15173一律拒絕，每項測試寫入前確認acceptance marker。登入、建立、gate阻擋／核准、readonly截圖位於被忽略的`web/test-results/`。每階段檢查水平溢出；pageerror必須0，HTTP及Chrome resource console錯誤僅精確允許初始`/api/auth/me` 401與測試task的預期409各一次，其他錯誤必須0，不宣稱console全空。

只對隔離驗收資料庫中斷（先確認acceptance服務已啟動）：

```powershell
try {
  docker compose --project-name projectflow-acceptance --env-file .superpowers/p1c/acceptance.env -f deploy/docker-compose.yml stop db
  if ($LASTEXITCODE -ne 0) { throw 'Cannot stop database' }
  curl.exe -s -o NUL -w '%{http_code}' http://127.0.0.1:15175/api/health
  curl.exe -s -o NUL -w '%{http_code}' http://127.0.0.1:15175/api/health/ready
  # 預期存活200、就緒503；登入UI的資料載入會顯示安全錯誤。
  Read-Host '確認HTTP狀態後按Enter恢復資料庫'
} finally {
  docker compose --project-name projectflow-acceptance --env-file .superpowers/p1c/acceptance.env -f deploy/docker-compose.yml up -d --wait db
  if ($LASTEXITCODE -ne 0) { throw 'Database recovery failed' }
}
```

恢復後`/api/health/ready`應回200；登入UI載入失敗時按「重試」，或重新登入後選取專案。此操作不改密碼、不刪volume。上述中斷步驟是手動驗收流程，本輪Task 4未中斷DB。完整停機可執行以下命令，保留資料；**不可加`-v`，不可使用prune清理資料**：

```powershell
docker compose --project-name projectflow-acceptance --env-file .superpowers/p1c/acceptance.env -f deploy/docker-compose.yml down
```

Docker基礎映像使用開發方便用的版本tag，本次實測image ID／digest見PROGRESS；不是離線或正式環境可重現部署保證。

## P1a 後端資料庫

P1a 使用 Alembic migration 管理正式業務 schema。啟動完整 Compose 後，從 repo 根目錄執行：

```powershell
api/.venv/Scripts/python.exe -m alembic -c api/alembic.ini upgrade head
```

Compose容器內工作目錄為`/app`，設定檔是`alembic.ini`，不可套用主機的`api/alembic.ini`路徑：

```powershell
docker compose --env-file deploy/.env -f deploy/docker-compose.yml exec api python -m alembic upgrade head
docker compose --env-file deploy/.env -f deploy/docker-compose.yml exec api python -m app.seed
```

本機測試會使用 SQLite 暫存資料庫檢查路由與權限；完整 PostgreSQL migration 仍必須在 Compose DB 上實跑。登入使用本地種子帳號與 HttpOnly session cookie，只供 P1a/P1b MVP 驗證，不代表 AD/LDAP 已完成。

### P1a 種子帳號與核心 API

P1a 種子資料包含兩家公司：

| 公司 | 帳號 | 密碼 | 角色 |
|---|---|---|---|
| food / 毛研食品 | yu | demo-yu | admin |
| food / 毛研食品 | chen | demo-chen | reviewer |
| food / 毛研食品 | ming | demo-ming | member |
| food / 毛研食品 | lin | demo-lin | readonly |
| electronics / 峰曜科技 | elaine | demo-elaine | admin |
| electronics / 峰曜科技 | kai | demo-kai | member |

以下範例只顯示HTTP狀態與回應形狀；不要記錄或轉貼`Set-Cookie`值：

```powershell
$apiPort = ((Get-Content deploy/.env | Where-Object { $_ -match '^API_PORT=' }) -split '=',2)[1]
if (-not $apiPort) { $apiPort = '18000' }
$base = "http://127.0.0.1:$apiPort"
Invoke-WebRequest -Uri "$base/auth/login" -Method Post -ContentType 'application/json' -Body '{"organization_key":"food","username":"yu","password":"demo-yu"}' -SessionVariable pf
Invoke-WebRequest -Uri "$base/projects" -WebSession $pf
Invoke-WebRequest -Uri "$base/departments" -WebSession $pf
Invoke-WebRequest -Uri "$base/audit-logs" -WebSession $pf
```

目前後端已提供 `/departments`、`/projects`、`/projects/{project_id}`、`/projects/{project_id}/nodes`、`/nodes/{node_id}/status`、`/nodes/{node_id}/reports` 與 `/audit-logs`。所有業務查詢都以 session 內的公司為準；query string 或 JSON payload 的公司欄位不能切換公司。

工作流與閘門 API：

```powershell
Invoke-WebRequest -Uri "$base/workflows" -WebSession $pf
Invoke-WebRequest -Uri "$base/projects/from-workflow" -Method Post -ContentType 'application/json' -Body '{"workflow_id":"<workflow id>","title":"測試專案"}' -WebSession $pf
Invoke-WebRequest -Uri "$base/gates/<gate id>" -Method Patch -ContentType 'application/json' -Body '{"status":"approved"}' -WebSession $pf
```

`/projects/from-workflow` 會依目前 session 公司建立專案、節點與 pending gate；猜測其他公司的 workflow id 會回 404。後續階段任務在前一階段 gate pending 時，直接打 `/nodes/{node_id}/status` 也會回 409，不能用 `override` payload 繞過。

完成回報 API：

```powershell
Invoke-WebRequest -Uri "$base/nodes/<node id>/reports" -Method Post -ContentType 'application/json' -Body '{"result":"達成","summary":"已完成測試","finished_on":"2026-10-08"}' -WebSession $pf
Invoke-WebRequest -Uri "$base/audit-logs" -WebSession $pf
```

回報會建立 `submitted` 狀態的 task report，並在同一家公司寫入 `report.submit` 稽核紀錄。唯讀角色與跨公司 node id 不能送出回報。

## 工作流程

### P1c Task2 隔離角色驗收

Playwright 預設使用 `http://127.0.0.1:15175`；`PF_BASE_URL` 只接受 loopback HTTP，拒絕共享埠 15173。每個 E2E 在任何業務寫入前必須取得 `/api/health/acceptance` 的 200 與 `{ "acceptance": true }`。請先執行 `api/.venv/Scripts/python.exe deploy/start.py --acceptance --seed-demo`，再執行 `npm.cmd --prefix web run e2e`。不得將共享環境當測試資料庫。

| 角色 | 專案 detail | 狀態／回報 | 閘門 |
|---|---|---|---|
| yu / admin | 公司內節點與閘門 | 公司內可操作 | 可核准 |
| chen / reviewer | 公司內節點與閘門 | 沿用負責人／部門主管權限；可操作 seed 品保任務 | 需專案操作權限或該節點部門權限；不相關閘門 403 |
| ming / member | 僅本人負責節點；隱藏節點的 gate 不回傳 | 本人任務可操作；不相關節點 403 | 沿用原有 API 權限 |
| lin / readonly | 公司內節點與閘門 | 狀態、回報、建立皆 403 | 403 |
| 跨公司 ID | 專案 404 | 節點狀態／回報 404 | 閘門 404 |

前端將父節點不在回應內的可見任務顯示為可選根節點，麵包屑在缺少父節點處停止。P1c當時回報與稽核為 **API-only**，測試使用各角色真實登入的同 context cookie 呼叫，當時尚無回報／稽核畫面與新增節點範圍規則；P2b介面與安全投影見文末。

瀏覽器驗收於 1280 與 375 寬度分別以 yu、chen、ming、lin、elaine 獨立 context 登入，檢查節點樹／看板、部門與本人狀態更新、report.submit 稽核、閘門 409→核准→更新、唯讀與跨公司邊界，並保存截圖、檢查水平 overflow 與瀏覽器錯誤。Seed 節點狀態先 snapshot，finally 由 yu 恢復並比對完整節點回應；隔離環境的新增專案／回報／稽核保留。共享 15173 僅做登入與唯讀檢查。

2026-10-08 Task2 實跑摘要（BASE `b76606e8b3be3521af3a2b5882927c27d676712b`）：

- pytest RED：`1 failed, 14 passed, 1 warning in 11.60s`，exit 1，`test_member_detail_filters_nodes_and_hidden_gate_metadata` 收到額外 yu 節點 ID。
- Vitest RED：`Tests  1 failed | 55 passed (56)`，exit 1，孤兒任務在節點樹找不到 button。
- E2E RED（舊驗收容器）：`2 failed`，exit 1，1280／375 的 ming 回應含隱藏階段 ID。
- full API GREEN：`63 passed, 1 warning in 31.98s`，exit 0；既有 Starlette TestClient deprecation warning 未新增依賴處理。
- full Vitest GREEN：`Tests  56 passed (56)`，exit 0；build：`tsc --noEmit && vite build`，exit 0。
- acceptance launcher：`ProjectFlow ready: projectflow-acceptance at http://127.0.0.1:15175`，exit 0。
- full E2E GREEN：`6 passed (10.4s)`，保留截圖的最後一次為 `6 passed (11.0s)`，均 exit 0。Health 每個 workflow 精確一個 me401 與一個 task409；各角色 context 精確一個初始 me401；無其他 console／HTTP／pageerror、無水平 overflow。
- 防護：`PF_BASE_URL=http://127.0.0.1:15173` 的 `--list` 在 config 拒絕，exit 1；指向共享 API 18000 的唯讀 health 測試在 marker 404 的 beforeEach 拒絕，`1 failed`／exit 1，未執行業務寫入。
- 共享 15173 保持 projectcount 12、marker 404；Task2 未重建 primary。截圖位於 `web/test-results/`，下一次 Playwright 執行會覆寫該目錄。

主checkout一次一個feature分支，TDD、每Task獨立審查、PROGRESS唯一進度來源。每階段完成更新README、驗收後ff-only到main並依D50推送，不force。正式資料庫未導入migration前，不可建立業務表或宣稱P1a完成。

## P2a 任務工作區與保留資料升級

管理者（admin或該專案非readonly擁有者）可新增phase／task及改派負責人／部門；可見且有操作權的非readonly執行者可編輯名稱與日期，不能改派。readonly即使歷史上是owner也不能新增、編輯或改派。實際授權以API及session公司為準；project_owner角色不等於所有專案的管理者。新增管理權不擴大原本status／Gate權限。

專案容器／既有project根下可新增階段或任務，階段及任務下可新增子任務；舊project根唯讀。新增不繼承指派，日期皆可空；起迄均填時開始日不得晚於截止日。日期採YYYY-MM-DD日曆日期，沒有時區轉換。編輯時省略欄位保持原值、null清除；名稱trim後1–200字元。取消不寫入，寫入成功但重新載入失敗時只重試GET，不重送mutation。

總覽統計所有可見task（含有子任務的task，各算一次），完成率為done／(task−skipped)，分母0顯示「—」。我的任務只列本人負責且可見的task，支援名稱／專案搜尋、五狀態篩選與清除；按到期日排序、未設定排最後。點擊項目定位到正確專案及節點，隱藏父節點不補查或顯示。多層Gate沿真實祖先判定，不能從子任務繞過。

新增API為PATCH `/nodes/{id}`、GET `/projects/{id}/assignment-options`、GET `/workspace/overview`及GET `/workspace/my-tasks`；瀏覽器經代理時前綴為`/api`。節點回應含日期、安全顯示名稱與capabilities，後端每次寫入仍重新檢查權限。

Alembic `20261008_0002`新增nullable DATE `start_date`／`due_date`及日期順序CHECK，升級不改舊ID、status、關聯或稽核，舊日期皆null。已有環境用`python deploy/start.py`升級，不加seed、不重建env或刪volume。不要在primary或已保存日期的驗收DB降版；migration保留資料測試使用全新的`p2a_migration_*`專用資料庫，從0001填fixture後升head，另驗日期CHECK與保存。主機API測試預設只跑SQLite，未設定`P2A_MIGRATION_TEST_URL`時PG案例會skip；完整PG證據另記PROGRESS，不能把skip當通過。

P2a隔離E2E覆蓋1280／375建立四層、日期清除／保存、指派、重新登入、成員編輯與唯讀拒絕；另驗真實兩公司、多角色、深層Gate與可見完成率。任何寫入前拒絕15173並檢查acceptance marker。瀏覽器只精確允許每次頁面初始me401及刻意觸發的Gate409，其他HTTP／console／pageerror須0。正常stop/start隔離服務不seed，完整專案detail需與停機前一致。人類試用項目仍由人類簽核。

## P2b 回報、協作與持久附件

P2b八Task、G4雙獨立審查、main完整隔離回歸與15173保留資料升級已完成；人類試用簽核仍待完成，證據見PROGRESS。任務預設開啟紀錄，提供完成回報卡、歷史版本、筆記、附件及協作設定；主導覽新增審核中心與稽核紀錄。紀錄／審核／稽核分頁游標讀取，先授權再篩選，點擊來源回正確節點；不補查隱藏祖先。

**相容性變更**：task的一般status PATCH只處理todo／doing；review必須送出回報、done必須確認回報，不能直接PATCH繞過。POST `/nodes/{id}/reports`必填result（達成／部分達成／未達成）、summary及finished_on，可附attachment_ids；送出建立不可變新版本並進review。POST `/reports/{id}/review`使用approved／rejected，退回必填comment並回doing，新送出另建版本。管理者明確選「送出並確認」才自核；一般任務owner不能自行審核。POST `/nodes/{id}/lifecycle`為skip／reopen／restore且必填reason；不遞迴改子樹，不覆寫Gate。

新增GET `/nodes/{id}/records`、POST `/nodes/{id}/notes`、PATCH `/notes/{id}`、GET／PUT `/nodes/{id}/collaborators`、GET `/workspace/reviews`與安全分頁GET `/audit-logs`。筆記只由作者修改，expected_revision防覆寫；協作替換也須expected_revision。指定協作者／指定部門主管的協作資格僅提供本節點紀錄讀取及筆記／附件操作資格；協作本身不授予送完成回報、審核、狀態、metadata或Gate操作權，也不自動取得子樹權限。送完成回報仍須符合原有can_work_node；同一使用者若另具負責人、管理者等既有角色身分，其權限依原規則另行判定。我的任務列出本人負責或協作task。移除協作後每次讀取／下載重新授權；readonly仍不可寫。舊版本所述report／audit API-only與公司全範圍稽核為歷史紀錄，P2b改以當下可見節點與安全欄位投影為準。

附件使用raw bytes POST `/nodes/{id}/attachments?filename=...`，不使用multipart。GET `/attachments/{id}/download`每次驗權，強制attachment及nosniff、不提供公開URL或內嵌預覽；DELETE同路徑只軟刪，已提交回報附件一律鎖定不可刪。允許pdf/png/jpg/jpeg/txt/csv/docx/xlsx/pptx/zip，單檔10,000,000 bytes，API驗內容與檔名；不提供病毒掃描。公司quota預設1,000,000,000 bytes（PF_ATTACHMENT_QUOTA_BYTES）；pending也預留容量，軟刪不釋放容量或刪實體。GET `/nodes/{id}/attachment-quota`供當下可上傳者看公司剩餘容量。上傳失敗請先讀取確認，不自動重送。

migration `20261008_0003`接0002，保留既有ID、status、日期、關聯及稽核；舊回報新流程欄位保持null，顯示「歷史回報（未納入新審核流程）」，不入新待審隊列、不重寫舊回報。新版回報從v1起。升級前停止API，保存同一時間點DB與files備份及既有env指紋，之後用`python deploy/start.py`升級，不seed、不覆寫env、不降版補救。新增files volume，固定UID/GID10001與0700目錄由映像首次copy-up設定；已有volume不遞迴改ownership，錯誤需保留資料處理。

**完整驗收**：`api/.venv/Scripts/python.exe deploy/verify.py`先啟動隔離環境，強制在acceptance API容器內建立唯一`p2b_test_<uuid>`資料庫，先跑0002→0003保留資料／約束，再跑真PG雙連線回報、審核、筆記、協作與附件配額競態。DSN只在容器子程序，檔案使用獨立temp root；任何skip、無案例、連線／建立DB或測試失敗均使整體非零。接著跑主機API／Vitest／build／E2E，主機測試移除繼承的DATABASE_URL、P2A／P2B測試URL及附件root，避免連到既存資料。主機套件中的PG條件skip由前述強制實跑補足；專用資料庫保留作證據。結束down不加-v，保留acceptance_pgdata與acceptance_files；不清primary。

### 備份與pending離線恢復

DB與files是同一份業務資料，必須成套備份及還原。先停止對應stack API以凍結寫入，再由資料庫工具pg_dump備份DB並完整複製該stack的files volume，保留時間、migration版本、env指紋與附件SHA清單；既有檔案含軟刪內容，不可prune。還原時停止API、核對相同備份組與檔案ownership，DB＋files都恢復後檢查ready及SHA再開放。不要單獨恢復DB或只複製附件目錄，也不要在恢復中重新seed或自動downgrade。備份／還原不是本階段提供的一鍵產品介面。

只有已查明的pending／failed、未綁定且未軟刪附件可執行恢復；停止該stack API後，傳明確公司與附件id。以下是隔離stack範例，運維處理primary時需先備份並改用正確stack設定，不能拿primary跑測試：

```powershell
docker compose --project-name projectflow-acceptance --env-file .superpowers/p1c/acceptance.env -f deploy/docker-compose.yml stop api
docker compose --project-name projectflow-acceptance --env-file .superpowers/p1c/acceptance.env -f deploy/docker-compose.yml run --rm --no-deps api python -m app.services.attachment_recovery --organization-id <公司ID> --attachment-id <附件ID> --api-stopped
docker compose --project-name projectflow-acceptance --env-file .superpowers/p1c/acceptance.env -f deploy/docker-compose.yml start --wait api
```

命令取獨占runtime鎖，不會清ready／綁定／歷史附件；修復指定未完成檔案、標failed並返還該筆預留容量。失敗保留資料並回非零，不手動刪未知檔案。恢復後重新登入比對既有note/report/附件中繼資料與下載SHA；下載過的副本無法撤回。

仍未交付：自訂回報欄位（延後）、跳過申請、Gate覆寫、子樹批次操作、AI／ERP、LAN／TLS與正式備份排程；人類試用簽核不得由自動化代勾。


## P2c 時程、模板與硬性前置（D65／D66A精簡範圍）

本輪移植日／週／月時程、工作流模板管理及同專案task間硬性FS（完成至開始、延遲0）；尚非完整Demo或原P2c全部功能。工程驗收與一次獨立審查已完成，15173已保留資料升級migration0004；詳細結果以PROGRESS為準。時程只畫可見節點原日期，缺日期列未排程；phase手動日期不由子任務推導。桌面拖移任務條／右端拉伸後，日期表單確認才寫入；手機與鍵盤可使用調整日期按鈕及表單。可取消、日期可空，單次只改選定節點，沒有自動順延或持久undo。操作沿edit_metadata，失敗保留原值，已保存但載入失敗只重讀。

「模板庫」同公司可讀，admin／project_owner可新增、編輯與複製；表單包括phase／多層task、排序、階段Gate、起迄相對日及FS。開始日為第0天，偏移非負且起<=迄；有偏移的模板建立專案必填開始日，無偏移舊模板仍可不填日期。新節點指派給建立者，不繼承部門。修改只影響之後建立專案，複製建立新模板及節點ID，不刪除模板或覆寫既有專案。

API擴充GET／POST `/workflows`、GET／PUT `/workflows/{id}`、POST `/workflows/{id}/copy`；from-workflow可傳start_date。完整模板儲存與建立專案採原子交易，不輸出raw payload。migration `20261009_0004`新增node_dependencies，模板設定存經schema驗證的版本化Workflow.content，保留0003既有值／ID、舊模板、日期、回報、筆記、附件與稽核。

專案「前置相依」提供設定與簡單可見相依圖。GET／POST `/projects/{id}/dependencies`、DELETE `/dependencies/{id}`；只有同公司admin或實際專案owner可管理，端點需同專案且可見，拒self／重複／循環／跨專案。只刪連線不刪任務。前置done或skipped才滿足；否則禁止開始、送回報及管理者送出並確認。已開始任務若前置重開，不回退既有狀態，但再次回報會被擋。Gate獨立生效，不因前置滿足而繞過。隱藏前置只顯示固定阻塞訊息，不揭露標題／ID／日期；協作不提升執行權限。Project→Node一致鎖序序列化加邊與狀態／回報，循環檢查在Project鎖內。

完整verify保留P2bPG migration與四項真PG競態，另加入0003→0004保留資料／相依約束測試；每個PG階段建立各自全新p2b_test_*專用DB，避免已到head的DB假驗升級，不downgrade既有環境。命名沿原護欄相容，DSN僅子程序、檔案temp隔離、skip仍使驗收非零。候選版本完成一次完整verify，修正只重驗受影響部分，合併main不重複全量；附件既有故障矩陣不擴充。升級仍先備份DB＋files與env指紋、不seed、不刪volume。

本輪延後：SS／FF、延遲、軟性前置／覆寫、自動順延、工作日／假日、里程碑鎖定、持久undo、關鍵路徑、時程相依連線、子樹另存／套用、拖曳改層級與自訂回報欄位；既有P2b的跳過申請／Gate覆寫及AI／ERP／LAN正式部署限制仍在。

## UI1 Demo介面對齊

UI1只改React介面，API契約與migration0004維持。桌面252px側欄與主區各自捲動；手機「導覽」開關切换導覽／主內容，Escape或選頁返回開關焦點。真實公司／使用者及登出放在側欄底部；沒有模擬公司／角色切換。背景#F6F4EF、側欄#EFEBE3、主色#1F5F5B，本機中文字體與serif fallback，不新增字體CDN。

總覽使用原可見統計與done/(task-skipped)進度；我的任務保留查詢／狀態；節點樹、详情與下一層卡片分區，回報／筆記／附件保留完整內容及操作。時程日週月、桌面拖拉與手機日期表單、FS／Gate與真API權限不變。未提供的Demo模組不加入可操作入口。

驗收使用15175 acceptance marker；`npm.cmd --prefix web run e2e -- visual-alignment.spec.ts`保存桌面／手機PNG至ignored `.superpowers/ui1/`，涵蓋主要頁面、長名稱、空／載入／錯誤重試與登入失效。完整回歸首次結構selector失敗及修正定點結果如實記在PROGRESS。發布只build/up `web --no-deps`，不重啟API/DB、不seed；部署前後核對原row、files SHA、env與API/DB容器身分。


## UI2 產業範本與本機展示公司切換

模板庫分「公司模板」與「產業範本」。12套涵蓋食品2、電子3、活動3、軟體2、工程2；包括Demo筆電與活動完整流程及各產業精簡流程，食品內容另補開發／供應商導入。卡片顯示階段／任務數，範本可搜尋、分類與預覽。相對日為可編輯建議；Gate與硬性FS接既有模板契約，沒有移植Demo未支援的部門、自訂欄位等資料。admin／project_owner可將範本另存公司模板；其他角色可預覽。建立專案仍選公司模板並指定開始日。

`PF_SHOWCASE_MODE`預設false。僅明確啟用的loopback部署、五個指定公司的已登入admin能使用左下公司選單。選擇後換發真實HttpOnly session並撤銷舊token，使用目標公司的專用「展示管理者」，清除原公司畫面並回總覽。有開啟表單時先確認／可取消，其他頁直接切換；手機先展開導覽。模式關閉後專用展示session失效，原有登入帳號／密碼不變。

本機展示初始化（先備份，既有Compose啟動後執行）：

```powershell
docker compose --project-name projectflow-formal --env-file deploy/.env -f deploy/docker-compose.yml exec -T api python -m app.showcase
```

須先在本機`deploy/.env`加入`PF_SHOWCASE_MODE=true`並重建API；勿用seed代替。初始化僅補缺公司／隨機不可知密碼的專用帳號／模板，穩定ID保留使用者已改模板，重跑不覆寫。15173本次新增3家公司、5個專用身分、12模板／219節點與12稽核；既有全部rows、欄位、附件及原環境設定逐值保留，migration仍0004。DB容器未重建，僅API/web更新；旗標只增加在ignored本機env。公司新建時沒有假專案，請用模板建立真實專案。這不是LAN部署授權。

UI2完整回歸與定向修正見PROGRESS，七項專用PG條件測試本輪未跑；本次沒有schema、migration與附件邏輯變更。獨立審查Ready to merge，1280／375畫面已實看；人類試用另簽核。

## UI3 Demo框架與首頁

寬度大於1180為Demo三區：側欄252｜主區｜右側AI副手350。861–1180副手改右側抽屜，860以下導覽也改左側抽屜；頂部列左「☰ 選單」、右「✦ AI 副手」，Escape關閉並把焦點還給開關，抽屜關閉時不可聚焦。導覽名稱照Demo，「營運資料」「AI 政策與稽核」停用並標「尚未提供」；「專案工作區」改由側欄專案清單進入。建立入口在側欄「＋ 建立新專案」，管理者在表單內選空白或從模板。AI副手只是標示「展示預覽」的位置，快捷動作與提問框停用，不產生任何回答。

`GET /workspace/overview`新增唯讀欄位`today`（台灣日曆日）、`overdue_count`、各專案`current_phase_title`／`due_date`／`overdue_count`、`people`、`departments`；`GET /workspace/my-tasks`新增可見祖先`path`。全部從既有可見節點計算，不改schema、不新增查詢；看不到的節點不進統計、負載與位置欄。

對照截圖用的乾淨隔離環境`projectflow-ui3cmp`（15179，acceptance marker）只存在本機，seed後依序套用三個展示腳本；不要拿15175累積的E2E資料比較畫面。若本機沒有Playwright內建Chromium，可用不提交的暫時設定`{...base, use: {...base.use, channel: 'msedge'}}`改以系統Edge跑同一套E2E；結果與環境如實記在PROGRESS。

## UI4 專案工作區與操作

專案節點頁照Demo由上而下：麵包屑 → h1目前節點 → meta列（負責、期間、完成率、狀態、🔒等待前置）→ 右側操作（狀態下拉、編輯節點、另存為模板／套用模板停用並標「尚未提供」、＋新增子節點）→ 任務的完成回報卡 → 專案層階段條／階段層閘門列 → 分頁「看板・時程・相依圖・文件・資料・成員與權限・紀錄」。主區不再有節點樹：往下點看板卡片或階段條，往上點麵包屑，整棵樹在時程分頁。看不到上層的可見節點與循環資料照`visibleRoots`規則放在專案層看板。

看板4欄「待處理／進行中／待確認／完成」，已略過放在完成欄並標「已略過」；專案層有階段時，卡片是各階段底下的子節點並加階段標籤。860以下每欄240px，在看板框內橫捲。子任務（沒有可見子節點的任務）預設打開「紀錄」；回報表單收合，按「回報完成」／「重新回報」才展開，「取消回報」會清掉這次選的附件並把焦點還給按鈕。協作人員編輯移到「成員與權限」，並依節點capabilities列出你在此節點可以做的事。閘門只在該階段頁或審核中心核准。

時程用日／週／月分段鈕，270px標籤欄（860以下150px）、36px列、專案色條、月份與日／週兩層刻度；刻度依像素間距抽稀。手機也用同一張圖並在框內橫捲，改期用✎。相依圖在前、HTML方塊由左到右依前置層級排列，已滿足灰實線、未滿足橘虛線；「＋ 建立相依連線」切換既有表單，連線清單收在「連線清單（N）」。模板庫卡片有「用這套工作流建立專案」（可建立專案的角色），打開側欄同一張建立表單並預選模板。審核中心分「待確認的完成回報（N）」「待審核的跳過申請」（尚未提供）「待核准的階段閘門（N）」表格。

UI4只改React介面，沒有新API、欄位或migration；拖曳改狀態、節點自己的時程／相依圖、加權進度等歸TP-A至TP-G。對照截圖在ignored `.superpowers/ui4/`（baseline為Demo與改版前，round1為改版後）。

TP-A新增`POST /nodes/{id}/move`（body `{parent_id}`，只限`can_manage_project`；目標要是同專案的專案根節點、階段或任務，狀態不能是待確認／完成／已略過，被移動子樹和新上層路徑之間不能有前置連線）與`GET /projects/{id}/records`（專案內所有可見節點的回報、筆記、附件，唯讀，游標綁定專案）。`PATCH /nodes/{id}`另收`weight`（0–100整數）與`progress`（0–100整數或null，只限任務）；`GET /workspace/overview`的專案多`progress_percent`（只用可見節點的加權進度）。階段改完成、送出回報（含送出並確認）、確認回報時，若有任何子節點不是完成或已略過，回409「子節點尚未全部完成」。前端只顯示這幾句固定的409文字，其他後端訊息仍不顯示。進度公式前後端各一份（`api/app/services/progress.py`、`web/src/progress.ts`），共用測試向量`web/src/progress.vectors.json`。migration `20261010_0005`的PG保留資料測試已加入`deploy/verify.py`；舊階段的migration測試改用`seed_at_revision`，先用目前ORM在暫存SQLite建資料，再只複製目標版本已有的欄位。E2E `web/e2e/planner.spec.ts`用真Chromium拖曳，對照截圖存在ignored `.superpowers/tpa/e2e/`。

TP-B新增`DELETE /nodes/{id}`（軟刪除任務與整棵子樹，只限`can_manage_project`；子樹含看不到的節點、或是階段時拒絕；兩端任一在子樹內的前置連線實際移除並寫進稽核payload）、`POST /nodes/{id}/copy`（只限`can_manage_project`與任務，最多300個節點；複製名稱加「（複本）」、負責人、部門、日期、權重、協作與子樹內前置，狀態歸待處理）與`POST /undo`（body `{audit_id}`）。`POST /nodes/{id}/move`的`parent_id`可為null（移到專案最上層；有專案根節點時換成根節點），權限放寬為`can_manage_project`或`can_work_node`（D74）。新增節點、移動、複製、刪除的回應多`undo_id`；復原只接受目前使用者本公司最近一次「新增／刪除／移動／複製／復原」稽核，只限原操作者，之後有其他稽核、子節點或連線就回409。已刪除節點由ORM全域條件排除（`app/models.py`的`do_orm_execute`＋`with_loader_criteria`），需要讀到它們的地方（刪除、復原、稽核頁）明確加`execution_options(include_deleted=True)`；Core層級查詢不受這個條件影響，新寫的Core查詢要自行過濾`deleted_at`。新增子節點、重新開啟、恢復任務在上層是待確認／完成／已略過時回409。migration `20261010_0006`有降級保護：資料庫裡有已刪除節點時拒絕降級。PG保留資料測試已加入`deploy/verify.py`。E2E `web/e2e/tree.spec.ts`的對照截圖存在ignored `.superpowers/tpb/e2e/`。

## TP-C 時程進階（D75）

時程父條顯示自己與可見子孫計畫期間的聯集，不改資料庫日期；負責部門篩選保留上層路徑。每列「＋」及最下方空白軌拖曳開啟新增表單，手機／鍵盤用按鈕和日期欄位。葉任務可以拖移與左右拉伸，父條只供導覽，里程碑只移動。

`POST /nodes/{id}/schedule`接受`{start_date, due_date, cascade}`，回傳`{node, shifted_count}`。`cascade`預設false；true時沿既有FS（完成→開始，翌日、零延遲）向後順延，保持工期與子樹相對日期。每個實際變更節點須可見、可編輯；後續鎖定、日期未排完整或已待確認／完成／略過時整次409，沒有部分日期或稽核寫入。前端保留失敗草稿。日期PATCH與建立也共用前置及里程碑檢查，不能繞過；不因前置提早而提前其他任務。

migration `20261010_0007`新增`nodes.milestone`、`schedule_locked`，既有列預設false。里程碑只能是有完整同日起訖的葉任務，鎖定必須為里程碑；新增、移動、複製與復原不能把子任務放在里程碑下面。只有系統管理員或該專案負責人可以鎖定／解鎖或直接修改已鎖定日期。自動順延一律不能越過鎖定，管理者也要先明確解除。

API `capabilities.edit_schedule`控制日期入口，`lock_schedule`控制鎖定入口；metadata編輯權限不變。時程改期使用`node.update`稽核，逐節點保留前後日期，摘要為「調整時程」或「自動順延」。複製子樹保留里程碑及鎖定值。D74的復原仍只涵蓋結構操作，日期不加入復原。

箭頭只用目前範圍內可見的前置，灰實線表示前置已完成／略過，橘虛線表示等待；日期衝突另有說明。關鍵路徑沿Demo的最晚結束單條限制鏈估算，明示是可見範圍FS估算，非完整CPM或浮時分析。SS／FF、延遲、軟性及條件前置留TP-D；模板里程碑保存留TP-E；覆寫申請與通知留TP-F。ERP交期與首頁延後天數預測仍未提供。


## TP-D 前置進階（D76）

migration `20261010_0008`新增連線relation_type（FS／SS／FF）、lag_days（整數-365至365）、enforcement（hard／soft）及node_conditions表。舊連線預設FS／0／hard，舊值不變；存在進階設定或人工條件時拒絕降級。

- `POST /projects/{id}/dependencies`接受三個新增設定；`PATCH /dependencies/{id}`只改提交的設定，端點不可改；自環、重複與循環仍拒絕。管理權限不變。
- `GET /projects/{id}/dependencies`新增可見目標的conditions；不可見前置只有通用阻擋／軟性警示。
- `POST /projects/{id}/conditions`：node_id、label、enforcement。`PATCH /conditions/{id}`：label、enforcement；改名稱清除先前確認。
- `POST /conditions/{id}/confirmation`：is_met及非空reason，管理者確認／撤回；`DELETE /conditions/{id}`移除。所有寫入均鎖專案、同交易稽核。條件只有人工確認，尚未接ERP／文件。條件撤回不回退已開始任務。
- FS日期為前置截止+1+lag；SS為前置開始+lag；FF為前置截止+lag限制後項截止。lag不表示實際狀態完成後倒數，也不排除假日。soft不強制日期或順延、不加入關鍵鏈。
- FS／SS開始阻擋含上層，回報保留重檢；FF允許開始與送待確認回報，在自我確認和核准重檢。Gate與略過權限保持獨立。審核清單及核准回應提供軟性警示。
- 複製子樹保留內部邊全部設定；人工條件複製為未確認。軟刪除保留條件原列，恢復保留原確認證據；刪除及復原邊保存完整設定。所有條件讀寫排除已刪除任務。

範圍限制：模板進階保存留TP-E；覆寫申請／通知留TP-F；人工條件沒有推估日期，不宣稱完整CPM或ERP交期預測。


## TP-E 模板進階（D77）

工作區標題列的「另存為模板」保存任務根及子孫；階段保存為普通根任務，閘門不帶入。專案另存為工作流，保留階段／閘門。「套用模板」先選模板及版本，預覽後在目前節點下追加；工作流只套專案頂層。模板庫分工作流與任務，可看完整版本、修改成新版、複製及刪除；查看舊版時停用編輯／複製，避免把最新版誤當舊版。

公司模板管理限admin／project_owner；來源另存及目標套用還必須有該專案管理權，且來源子樹完整可見。套用預設帶結構、內部前置與日期，人員／協作預設不帶；保存負責部門、權重、里程碑及FS／SS／FF、lag、hard／soft。人工條件重新確認，狀態回待處理、鎖定清除；不複製回報、筆記、附件與確認證據。空日期維持空；有里程碑時不允許取消日期，避免產生不符合單日規則的節點。現有節點無獨立說明欄位，不把筆記當說明複製。

migration `20261010_0009`新增模板種類／版本／軟刪時間及workflow_versions快照表；既有每個模板補v1，原值保留，遇進階資料拒絕有損降級。版本修改與整組套用為原子交易，套用稽核可復原上一步；後續有活動即拒絕。每次最多300節點、檢查循環。軟刪模板阻擋所有使用入口，名稱、版本與既有任務仍保留，尚無垃圾桶還原UI。

新增 `/nodes/{id}/save-template`、`/projects/{id}/save-template`、對應`apply-template`、`/workflows/{id}/versions`與`/versions/{version}`及DELETE工作流。保存新版帶template_id／expected_version；套用指定版號。選版載入中禁用提交，操作完成但重載失敗只重試重載；公司／路由切換取消失效回呼。

個人模板發布、搜尋過去任務直接套用、版本差異比較／回退編輯、文件／檢查清單／AI推薦延後，自訂回報欄位歸TP-G。TP-E不宣稱README F2全功能完成。測試只用隔離環境，更新15173前備份並逐值核對既有資料／附件／env，不seed。


## TP-F 權限與協作（D78）

節點的「跳過／覆寫申請」可提交跳過子樹、覆寫前置開始；階段另有獨立閘門覆寫及例外完成入口。管理者直接操作，其他負責人送主管核准，理由必填。審核中心可核准、附理由退回與重新整理；申請者不能核准自己。已失效申請結案不執行。

完成回報提供當次覆寫理由；非管理者填寫覆寫理由並送出會建立送出回報的申請，核准後仍進待確認，完成核准另重驗規則。覆寫不永久停用前置，也不假造人工條件已完成。公司隔離、唯讀及上層已關閉不能覆寫。

跳過保存实际異動快照，保留已完成子孫；待確認回報退回並保存。整組恢復限專案管理者且異動後無相關稽核，否則409；原待確認任務恢復為進行中。與結構復原分開。

成員與權限頁提供角色範圍及可見成員。部門由admin維護名稱、成員、主管，主管須是同公司非唯讀成員；使用中的部門不能刪除。主管可見並指派本部門任務，未指派開放任務出現在「待我指派」。負載是可見未完成任務數，含未指派，不代表工時。

站內通知涵蓋指派、申請、決策與前置／閘門解除；排除操作者本人，讀取再次檢查來源權限。支援分頁及已讀，無Email、推播、ERP或歷史補發。核心新API：`POST /nodes/{id}/requests`、`GET /workspace/requests`、`POST /requests/{id}/decision`、`GET /notifications`、`POST /notifications/{id}/read`，以及部門POST／PATCH／DELETE。migration `20261010_0010`新增collaboration_requests及notifications，保留旧表原值；存在新資料時拒絕有損降級。

## TP-G 自訂回報欄位

編輯葉任務時可設定文字／數字／日期／單選欄位、必填、數字單位及排序，最多30欄。欄位設定有獨立的「儲存回報欄位」按鈕；取消節點資料不會撤銷已儲存的欄位。只有原本可編輯任務的人可設定，待確認、完成、略過或上層關閉時停用。名稱或類型需移除後新增；歷史回報保留送出時的完整快照。

填寫途中欄位改版，送出回409；按重新載入保留相同欄位輸入，再確認新欄位。退回重報依目前欄位定義帶回相同識別碼的值；覆寫申請不能略過必填或型別，過期申請結案後可重送。模板／完整版本／建立專案／套用與複製子樹帶入定義、產生新識別碼，不複製回報值。父任務保留原欄位但暫停使用，回到葉任務後沿用。

migration 20261010_0011僅新增nodes定義／版本及task_reports快照欄位，舊列保持原值。沿隔離驗收流程，不seed更新使用者的15173資料。無公式、多選、條件顯示、共用欄位庫、統計或欄位編輯復原。


## UI5 展示操作（2026-10-11）

本機入口：http://127.0.0.1:15173 。選食品公司，使用既有帳號登入。既有任務、回報／審核、附件、模板與權限仍是真功能；以下新增頁面均有「展示預覽」標示，使用獨立食品案例，不讀正式任務產生回答。

1. 開啟既有專案，展示看板／時程及回報審核。若只需介紹介面，不必新增正式資料；寫入驗收仍限15175隔離環境。
2. 點「文件」→「試產規格書」，切換v1／v2，編輯文字並「套用至預覽」。
3. 在「關聯資料示例」查看供應商，依「查看關聯採購」→「模擬收貨」→「查看關聯工單」展示流向；七個營運分頁可瀏覽，ERP明示未連線。
4. 右側AI副手（手機上方開啟）依序試六個快捷。會議紀錄輸入「請採購確認交期。請品保安排送驗。」可擷取待辦；拆解／推薦／待辦確認後只加入預覽清單。輸入「請拆解下一階段」，查看詳情、引用與固定遮罩示意。
5. 點「AI政策示例」切換政策查看路由說明；再「離開預覽，返回工作區」。重進後文字及收貨狀態清除；切公司、登出、重新整理也不保留。其他公司顯示空狀態，不借用食品數據。

限制：文件無正式儲存／上傳；關聯與營運不寫資料庫；AI為本地關鍵詞規則與固定示例，沒有模型、ERP、真遮罩引擎或真政策設定。示例內導航保留文件／採購狀態，離開該預覽區域即清除；AI對話於離開預覽或切換真工作區時清除。F1／F2不自動開始。

純前端更新命令：`docker compose --project-name projectflow-formal --env-file deploy/.env -f deploy/docker-compose.yml up -d --build --no-deps web`。保留既有API、DB及附件容器／volume，不seed、不執行migration。若服務原本停止，可用`docker start`恢復既有DB、API容器，勿重建或重設資料。
