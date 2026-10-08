# 正式版開發

正式版目標為P0至P1c的可內部試用MVP，Demo保持獨立且不得視為正式登入／多租戶安全機制。

## 公司邊界

業務資料以organization_id識別公司。API從已驗證身分取得可用公司，查詢與外鍵須限制公司；不能信任前端傳來的公司參數。稽核、檔案讀寫與工作流建立同樣受限。目前P1a業務API、P1b Task 1–3已通過獨立審查；Task 4工作流建立與瀏覽器測試已實作、待獨立審查。P1c部署／測試／內部試用驗收仍未完成。

## 環境需求

- 本機開發：Python 3.13、Node 24.15以上且小於25；套件分別使用`api/requirements.lock`及`web/package-lock.json`。
- 完整環境：Docker Desktop的Linux容器引擎與Docker Compose。容器自帶Python／Node，不依賴主機安裝的執行環境。
- 目前為本機MVP開發環境；P1c正式部署強化與內部試用驗收尚未完成，不可直接視為內網正式版發布。

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

開啟`http://127.0.0.1:15173`。開發代理將`/api`送到`http://127.0.0.1:18000`，不需要放寬跨來源政策。API使用其他埠時，先在同一終端設定`$env:API_PROXY_TARGET = 'http://127.0.0.1:<埠號>'`。目前前端先確認session，未登入時顯示登入表單；公司預設food，種子帳號見下表。登入後僅傳HttpOnly cookie，不接受前端切換公司或推斷完整操作權限；API為權限權威。專案清單可切換詳情；節點樹依sort_order排列，選取節點顯示完整路徑，空專案顯示沒有節點。載入錯誤可重試，401會清除session回登入；切換或登出後不套用舊回應。admin／project_owner可開啟「新增專案」的inline表單，選擇工作流模板並填名稱建立；成功後更新清單並選取新專案，403／404使用安全訊息。

四欄看板只顯示task節點；狀態選單透過API更新，成功才移欄，失敗保留原狀態。pending閘門顯示警示；admin、專案owner與reviewer顯示核准操作，實際權限由API強制。readonly隱藏狀態、核准與建立操作。403／409使用固定安全訊息；請求期間停用重複寫入，切換專案或登出後忽略舊mutation回應。

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

E2E保留API存活／就緒與未知路由檢查，1280px／375px測試登入、指定seed專案、建立唯一測試專案、gate阻擋／核准／狀態更新及readonly。每次重跑另建專案，不修改seed節點狀態；測試專案會留在本機資料庫，沒有刪除API。

先啟動完整Compose，再逐行執行：

```powershell
api/.venv/Scripts/python.exe -m pytest -c api/pyproject.toml api/tests -q
npm.cmd --prefix web ci
npm.cmd --prefix web test
npm.cmd --prefix web run build
Push-Location web
try { npm.cmd exec -- playwright install chromium } finally { Pop-Location }
npm.cmd --prefix web run e2e
```

如果WEB_PORT不是15173，在E2E之前設定`$env:PF_BASE_URL = 'http://127.0.0.1:<實際WEB_PORT>'`。登入、建立、gate阻擋／核准、readonly截圖位於被忽略的`web/test-results/`。每階段檢查水平溢出；pageerror必須0，HTTP及Chrome resource console錯誤僅按URL+status排除初始`/api/auth/me` 401與測試task的預期409，其他錯誤必須0，不宣稱console全空。

只對本專案測試資料庫中斷：

```powershell
try {
  docker compose --env-file deploy/.env -f deploy/docker-compose.yml stop db
  if ($LASTEXITCODE -ne 0) { throw 'Cannot stop database' }
  curl.exe -s -o NUL -w '%{http_code}' http://127.0.0.1:15173/api/health
  curl.exe -s -o NUL -w '%{http_code}' http://127.0.0.1:15173/api/health/ready
  # 預期存活200、就緒503；登入UI的資料載入會顯示安全錯誤。
  Read-Host '確認HTTP狀態後按Enter恢復資料庫'
} finally {
  docker compose --env-file deploy/.env -f deploy/docker-compose.yml up -d --wait db
  if ($LASTEXITCODE -ne 0) { throw 'Database recovery failed' }
}
```

恢復後`/api/health/ready`應回200；登入UI載入失敗時按「重試」，或重新登入後選取專案。此操作不改密碼、不刪volume。上述中斷步驟是手動驗收流程，本輪Task 4未中斷DB。完整停機可執行以下命令，保留資料；**不可加`-v`，不可使用prune清理資料**：

```powershell
docker compose --env-file deploy/.env -f deploy/docker-compose.yml down
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
Invoke-WebRequest -Uri "$base/nodes/<node id>/reports" -Method Post -ContentType 'application/json' -Body '{"result":"達成","summary":"已完成測試"}' -WebSession $pf
Invoke-WebRequest -Uri "$base/audit-logs" -WebSession $pf
```

回報會建立 `submitted` 狀態的 task report，並在同一家公司寫入 `report.submit` 稽核紀錄。唯讀角色與跨公司 node id 不能送出回報。

## 工作流程

主checkout一次一個feature分支，TDD、每Task獨立審查、PROGRESS唯一進度來源。每階段完成更新README、驗收後ff-only到main並依D50推送，不force。正式資料庫未導入migration前，不可建立業務表或宣稱P1a完成。
