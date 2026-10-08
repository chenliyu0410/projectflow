# 正式版開發

正式版目標為P0至P1c的可內部試用MVP，Demo保持獨立且不得視為正式登入／多租戶安全機制。

## 公司邊界

後續業務資料以organization_id識別公司。API從已驗證身分取得可用公司，查詢與外鍵須限制公司；不能信任前端傳來的公司參數。稽核、檔案讀寫與工作流建立同樣受限。P0只有健康檢查，尚無業務API或登入功能。

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

開啟`http://127.0.0.1:15173`。開發代理將`/api`送到`http://127.0.0.1:18000`，不需要放寬跨來源政策。API使用其他埠時，先在同一終端設定`$env:API_PROXY_TARGET = 'http://127.0.0.1:<埠號>'`。真實資料庫尚待Task3設定，未設定時顯示「無法連線」是預期結果。Docker整合與桌面／手機畫面將在Task3验收。

## 工作流程

主checkout一次一個feature分支，TDD、每Task獨立審查、PROGRESS唯一進度來源。每階段完成更新README、驗收後ff-only到main並依D50推送，不force。正式資料庫未導入migration前，不可建立業務表或宣稱P1a完成。
