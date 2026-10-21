# API-CORRECTNESS：後端正確性與效能修正（短規格／計畫）

> 精簡流程（WORKFLOW §14／§14.1）。人類 2026-10-20 指示「把唯讀審查找到的問題全部修掉，可平行的各開分支」。本分支 `claude/api-correctness-814517`（從 main @3c1294e 切出）；平行分支另有 api-security、web-fixes、ci-tests。為避免衝突，本分支不改 `docs/PROGRESS.md` 與 `README.md`，進度與結果寫在本檔。

## 範圍（允許修改的檔案）

- `api/app/database.py`、`api/app/routes/projects.py`、`api/app/services/*`
- `api/app/routes/audit_logs.py`、`documents.py`、`attachments.py`、`report_fields.py`
- 新增 `api/tests/test_api_correctness.py`；既有測試必要時才調整（不動 `conftest.py`、`test_migrations.py`、`test_health.py`）

## 項目與做法

1. **engine 快取**：`get_session` 每個請求都 `create_engine`（每次新建連線池）。改成依 URL 快取 engine；快取鍵含 URL，測試 monkeypatch `DATABASE_URL` 時會拿到對應的 engine。
2. **PATCH /nodes/{id}/status 的非 task 節點**：階段負責人或 admin 可直接把階段／專案根節點改成 skipped／review，底下未完成任務會被凍結。UI（階段狀態下拉）與既有測試依賴階段直接變更狀態，且申請／核准流程沒有階段略過，所以照人類裁示的規則 A 實作（見下方「決定」）。
3. **授權資料全量重算**：先用展示資料規模實測送出跳過申請等路徑的耗時，有實際問題才最佳化；行為不可改變。
4. **唯讀 GET 不再拿 `FOR UPDATE`**：report_fields、documents、attachments 的 GET 改用不加鎖的讀取；寫入路徑維持原樣。
5. **稽核分頁**：把篩選與分頁移到 SQL（可見節點、node_id、action、游標、limit+1），回應與游標格式不變。

每項先寫會失敗的測試再修（TDD）；效能項以量測數字為準。最後跑 API 全量 `python -m pytest api/tests -q`。

## 決定

- 第 2 項：人類 2026-10-20 選規則 A，原話：「階段狀態機用 A：階段可直接改 review／skipped，但子節點必須全部 done／skipped，否則 409；專案根節點不能用 PATCH 改 skipped／review。」
  - 其他提出的選項：B（非 task 一律不得經 PATCH 改 skipped／review，階段從此無法略過）、C（不改）。
  - `test_tp_a_planner.py` 的 `test_phase_cannot_be_done_while_any_child_is_open_even_hidden` 最後一段原本斷言「子節點未完成時階段仍可改 review」，正好是規則 A 要擋的行為；改成斷言 review 回 409、doing 仍可。

## 結果

### 改法

1. `database.py`：`get_engine()` 以轉換後的 URL 為鍵，把 engine 快取在模組層字典（加鎖）；`get_session()` 沿用。
2. `routes/projects.py` 的 `update_node_status`：專案根節點改 review／skipped 一律 409（`conflict()`）；改 done／review／skipped 且狀態有變時都套 `require_children_finished`（子節點含看不到的，全部 done／skipped 才放行，訊息不透露子節點）。task 原本就只能 todo／doing，行為不變。
3. `services/record_policy.py`：把 `load_policy_context` 中與使用者無關的公司層資料（使用者、部門、協作設定、回報、前置阻擋）拆成 `company_policy_data()`；新增 `shared_policy_data(db)` 區塊，區塊內同公司只算一次，離開區塊即丟棄，每個 context 拿自己的容器副本。只套用在兩個「迴圈內只新增通知」的地方：`collaboration_service.create` 通知所有審核者的迴圈，以及 `notification_service.finish_notifications`。
4. 新增 `dependency_service.read_project`、`report_service.read_node`（同樣的授權與 404，不加 `FOR UPDATE`、不登記通知比對）。GET 改用它們：`report-fields`、文件列表／版本／文字／下載、專案文件列表、附件下載、附件配額。`document_store.permission` 只在 `write=True` 時加鎖，寫入路徑（上傳、新版本、文字編輯、刪除附件）照舊加鎖。
5. `routes/audit_logs.py`：可見範圍（可見節點；admin 另含無節點的公司事件）、`node_id`、`action`、游標條件都放進 SQL，`ORDER BY created_at DESC, id DESC LIMIT limit+1`；PostgreSQL 上 id 用 `COLLATE "C"` 以符合原本 Python 字串排序。回報／筆記／附件／閘門參照只載入本頁用到的節點。游標編解碼抽成 `record_policy.decode_page_cursor／encode_page_cursor`，`authorized_page` 改呼叫它們，格式不變。

### 效能量測（第 3 項）

方法：把 `deploy/demo-data` 還原到 SQLite（6 家公司、80 帳號、500 節點、39 專案），取節點最多的 electronics（128 節點、14 帳號），用 TestClient 量單一請求耗時；同一台機器、同時段，舊版（HEAD 的 `api/app`）與新版交替各跑 3 次，每次每路徑 4–5 筆取中位數。量測腳本放在 session 暫存區，不進 repo。

| 路徑 | 公司層資料計算次數 舊 → 新 | 中位數耗時 舊（3 次） | 中位數耗時 新（3 次） |
|---|---|---|---|
| POST 跳過申請（member） | 21–25 → 2 | 410／482／342 ms | 117／105／89 ms |
| POST 核准申請（admin） | 4 → 4 | 103／138／109 ms | 118／167／119 ms |
| PATCH 狀態（member） | 1 → 1 | 63／92／68 ms | 71／113／70 ms |
| GET 專案（admin） | 1 → 1 | 35／107／32 ms | 38／41／40 ms |

跳過申請的成本原本和公司帳號數成正比（每位帳號約 20 ms），改後固定約 2 次計算；其他路徑沒有改動，差異在量測雜訊範圍內（同時有其他 session 在跑）。

### 測試

新增 `api/tests/test_api_correctness.py`（13 個案例）。各項 RED → GREEN（pytest，`-c api/pyproject.toml`）：

| 項目 | RED | GREEN |
|---|---|---|
| 1 engine 快取 | `2 failed`，exit 1 | `2 passed`，exit 0 |
| 4 GET 不加鎖 | `1 failed, 4 passed`，exit 1（report-fields GET 出現 FOR UPDATE） | `5 passed`，exit 0；相關既有 `test_documents`／`test_attachments`／`test_tp_g_report_fields` `66 passed`，exit 0 |
| 5 稽核 SQL 分頁 | `1 failed, 2 passed`，exit 1（一頁 5 筆卻載入 78 筆稽核；排序／篩選／游標鏈的特徵測試在舊版即通過） | `3 passed`，exit 0；含 `/audit-logs` 的 12 個既有測試檔 exit 0 |
| 3 授權資料共用 | `2 failed`，exit 1（`company_policy_data` 不存在；審核者通知名單在舊版為 chen、yu，據此釘住） | 新測試檔 `10 passed`，exit 0 |
| 2 階段規則 A | `2 failed, 1 passed`，exit 1 | 新測試檔＋`test_tp_a_planner.py` `37 passed`，exit 0 |

API 全量：`python -m pytest -c api/pyproject.toml api/tests -q` → `677 passed, 14 skipped, 78 warnings in 1151.85s`，exit 0。14 個 skip 都是需要專用 PostgreSQL 的測試（本次沒有碰 Docker／PG），所以 PostgreSQL 上的 `FOR UPDATE` 與 `COLLATE "C"` 排序只有程式審閱、沒有實跑；warnings 是既有的 starlette／sqlite3／alembic 棄用提示。

### 後續（不在本分支允許範圍）

- `routes/operation_links.py` 的 GET（`scope()`）仍用 `lock_node`／`lock_project`，可改用 `read_node`／`read_project`。
- `audit_logs` 目前只有 `organization_id` 單欄索引；資料量再大時可加 `(organization_id, created_at, id)` 複合索引（需要 migration）。
