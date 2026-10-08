# 正式版 MVP 本機試用驗收清單

本清單區分自動化驗證與人類試用。P0至P1c本機MVP已提供API、React、PostgreSQL、隔離啟動／驗收命令；逐Task spec／品質與整體獨立審查均通過。只供本機loopback試用，不是LAN／正式環境部署認證。

## 啟動與驗收

需要Python 3.13、Node 24.15以上且小於25、Docker Desktop Linux容器／Compose。初次clone可依[正式版開發指南](formal-development.md)安裝 `api/requirements.lock`、`web/package-lock.json` 的鎖版依賴與Playwright Chromium。容器啟動需要網路下載映像與套件。

從repo根目錄執行：

```powershell
# 只有明確要初始化示範帳號時加seed
python deploy/start.py --seed-demo
# 已有資料的primary重啟，不重新seed
python deploy/start.py
# 完整隔離驗收，保留服務供查看結果
api/.venv/Scripts/python.exe deploy/verify.py --keep-running
# 完整隔離驗收，結束後停止驗收服務，volume仍保留
api/.venv/Scripts/python.exe deploy/verify.py
```

Primary入口為 `http://127.0.0.1:15173`，驗收入口為 `http://127.0.0.1:15175`（API18002）。驗收使用獨立 `projectflow-acceptance` 專案與volume；已有 `deploy/.env`、`.superpowers/p1c/acceptance.env` 不覆寫、不旋轉密碼、不提交Git。不要刪除volume、既有專案或使用 `down -v`。驗收命令不清理primary。

各測試階段遇錯立即停止並回傳非零exit code。成功啟動後的預設清理只停止驗收服務；keep-running不清理。啟動中斷時可能留下部分驗收服務，請檢查隔離專案。重複驗收會保留新增測試專案、回報與稽核；seed狀態先snapshot並於finally恢復。截圖在 `web/test-results/`。

## 示範帳號

以下帳號只供已明確seed的本機MVP，不適用正式環境：

| 公司 | 帳號／密碼 | 角色與驗收範圍 |
|---|---|---|
| food | yu／demo-yu | admin；建立工作流專案、核准閘門與更新任務 |
| food | chen／demo-chen | reviewer／品保主管；更新部門seed任務，不相關閘門403 |
| food | ming／demo-ming | member；只看本人節點、更新本人任務與送回報 |
| food | lin／demo-lin | readonly；可讀公司節點，不可建立／更新／回報／核准 |
| food | owner／demo-owner | project_owner；沿用現有角色policy |
| electronics | elaine／demo-elaine | admin；驗證公司資料隔離 |
| electronics | kai／demo-kai | member；沿用本人節點可見性 |

權限由真實session cookie與API判斷，前端公司欄位／角色顯示不能擴大資料範圍。回報與稽核目前為API-only，沒有回報／稽核管理畫面；稽核沿用公司範圍。真AI／雲端AI、ERP、AD／LDAP、完整RAG、文件／附件儲存與LAN／TLS正式部署不在本輪交付。

## 自動驗證

- [x] 一鍵啟動順序為Compose設定檢查、build／wait、migration、明確seed、HTTP readiness與acceptance marker。
- [x] verify依序API、Vitest、build、E2E；四個階段失敗均停止後續測試、保留失敗exit，子環境PF_BASE_URL不修改全域環境。
- [x] 清理只對固定acceptance專案down，不帶-v；keep-running不down，orchestration／清理錯誤不輸出原始私密錯誤。
- [x] Playwright預設15175、拒絕共享15173，每個測試寫入前確認marker。
- [x] 1280／375真實yu、chen、ming、lin、elaine流程，閘門阻擋／核准、部門權限、本人任務、唯讀／跨公司邊界、API回報與稽核均實跑。
- [x] Member隱藏節點與gate不回傳，可見孤兒任務可選根節點、麵包屑與看板正常。
- [x] 瀏覽器無額外HTTP／console／pageerror與水平overflow；seed狀態於finally恢復。
- [x] 無seed刷新primary後保持15173、marker404、food專案數12與共享專案／節點snapshot不變。
- [x] 重複acceptance seed啟動保留七個帳號身分／登入憑證、專案詳情／稽核／部門／工作流；兩份已有env內容不變，migration為head。

2026-10-08 Task3實跑（BASE `61c197dfc54eee1852886b2dc216c435eee563fc`）：

| 命令／階段 | 真實摘要 | exit code |
|---|---|---|
| `api/.venv/Scripts/python.exe -m pytest -c api/pyproject.toml api/tests/test_deployment.py -q` RED | `16 passed, 1 warning, 17 errors in 0.54s`；新verify.py尚不存在，非依賴缺少 | 1 |
| 同一targeted命令 GREEN | `33 passed, 1 warning in 0.18s` | 0 |
| `api/.venv/Scripts/python.exe deploy/verify.py --keep-running` | 隔離啟動→API→Vitest→build→E2E；`Acceptance finished (exit 0).` | 0 |
| verify內full API | `80 passed, 1 warning in 31.65s` | 0 |
| verify內full Vitest | `Tests  56 passed (56)` | 0 |
| verify內build | `tsc --noEmit && vite build`；`✓ built in 103ms` | 0 |
| verify內E2E | `6 passed (10.0s)`，1280／375 | 0 |
| `api/.venv/Scripts/python.exe deploy/start.py` | `ProjectFlow ready: projectflow-formal at http://127.0.0.1:15173`；未加seed | 0 |
| `api/.venv/Scripts/python.exe deploy/start.py --acceptance --seed-demo` 重複啟動 | 隔離snapshot及七個帳號登入驗證前後一致；primary／acceptance env內容不變 | 0 |
| 隔離Compose `exec -T api python -m alembic current` | `20261008_0001 (head)` | 0 |

共享snapshot只透過food／yu真實登入讀取 `/projects` 與清單順序的各專案detail。格式為 `{"list": <完整清單回應>, "details": <detail陣列>}`，保留JSON插入順序、UTF-8、`ensure_ascii=False`、compact separators。SHA256精確符合controller提供的 `79500e1f2db0f54d311e99b7921499a3b155b28d011da8dcea62a3912b073ed7`；另以sorted-key canonical details計算的執行前後hash均為 `5828a55a5b100dfb15e076ef47f55f7667fab4eb95f1c366cb47e4439072e3b0`。共享marker404，隔離marker200／`{"acceptance":true}`。未停止primary、未刪任何volume或歷史專案；keep-running保留兩個stack供controller審查。

G4預設verify另實跑：API `80 passed,1 warning in 38.36s`、Vitest56、build0、E2E `6 passed (11.3s)`、最終exit0；預設down成功，acceptance容器清單空，`projectflow-acceptance_pgdata`保留，shared count12／snapshot hash不變、marker404。目前實機驗證使用既有持久volume；新的設定建立與重複啟動保留由launcher單元測試涵蓋，沒有為測試刪除既有volume或偽稱已完成新機器試用。既有Starlette TestClient deprecation warning與Node顏色環境warning不影響exit，未因此新增依賴。

## 人類試用簽核

- [ ] 新機器clone後依文件安裝／啟動並執行驗收，記錄環境與結果。
- [ ] 試用者自行登入yu、chen、ming與lin，確認工作流程符合團隊日常需求。
- [ ] 試用者於桌面與手機查看樹、看板與閘門提示，確認閱讀與操作體驗。
- [ ] 試用者理解回報／稽核為API-only及本輪未提供的功能，接受本機MVP試用範圍。
- [ ] 管理者確認正式帳號、密碼、備份／還原、LAN／TLS與安全部署另行規劃，不沿用示範憑證發布。
- [ ] 試用負責人記錄意見、簽核日期與下一步；自動化通過不代替此項。
