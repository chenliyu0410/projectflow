# P2a Task Workspace Implementation Plan

**狀態：配套審閱草案。** 2026-10-08；spec及D56未定稿，尚不可執行G3。進度只記PROGRESS，不在本檔打勾。

**Goal:** 依[spec](../specs/2026-10-08-p2a-task-workspace-design.md)交付工作區、任務metadata編輯、多層Gate、可見總覽與本人任務。

**Architecture:** React沿既有session／request sequence，拆出工作區組件；FastAPI以共用policy投影與驗證，SQLAlchemy DATE加Alembic migration保存日期。API是唯一授權與彙總來源；不新增套件。API內部路徑無/api前綴，外部由Nginx提供/api。

## Global Constraints

- D55授權撰寫文件；D56及spec審閱通過才把PROGRESS改📋，依WORKFLOW G3跑基準並在主checkout開`feature/p2a-task-workspace`。只有一位寫入者，不用worktree。
- 只修改以下File Structure；正式DB唯一變更是spec日期migration，Demo v6及tests/維持。不得重設DB、覆寫.env、刪volume或歷史專案。
- 新增can_manage_project、can_edit_node；讀取沿can_view_project／can_view_node；status沿can_work_node。readonly管理權必須明確拒絕。新能力不得默默擴大Gate授權。
- 業務寫入與稽核同交易。日期／指派／權限拒絕後資料及稽核不變。React預設跳脫，繁體中文，session退出清除資料。
- 不新增依賴；不修改lockfile。公司來源只能是session。
- 自動驗收只用隔離Compose／marker，15173供人類試用。G4及合併後回歸通过才依D50發布；本草案不構成發布完成。
- 每Task記錄BASE、真實RED失敗名稱／摘要／exit code、GREEN摘要／exit code，commit後交另一agent/session做獨立spec及quality審查，按WORKFLOW最多兩輪修正。不能把工具缺失算RED。

## File Structure（允許清單）

```text
api/app/models.py
api/app/schemas.py
api/app/permissions.py
api/app/main.py
api/app/routes/projects.py
api/app/routes/workspace.py                 # 新增：總覽／本人任務
api/app/services/__init__.py                # 新增
api/app/services/node_policy.py             # 新增：metadata驗證、投影、祖先Gate
api/alembic/versions/20261008_0002_p2a_node_dates.py
api/tests/test_migrations.py
api/tests/test_projects_nodes.py
api/tests/test_workflows_gates.py
api/tests/test_node_metadata.py             # 新增
api/tests/test_workspace.py                 # 新增
web/src/App.tsx
web/src/App.test.tsx
web/src/api.ts
web/src/types.ts
web/src/styles.css
web/src/components/WorkspaceShell.tsx       # 新增
web/src/components/NodeEditor.tsx           # 新增
web/src/components/NodeWorkspace.tsx        # 新增
web/src/components/WorkspaceOverview.tsx    # 新增
web/src/components/MyTasks.tsx              # 新增
web/src/workspace.test.tsx                  # 新增
web/src/node-editor.test.tsx                # 新增
web/e2e/workspace.spec.ts                   # 新增
web/e2e/mvp.spec.ts
web/e2e/health.spec.ts
README.md
docs/formal-development.md
docs/mvp-trial-checklist.md
docs/PROGRESS.md
```

spec／plan的修訂依AGENTS例外記錄；不需為拆分檔案重寫現有未相關功能。若實作確需清單外檔案先更新plan，依WORKFLOW處理。

## 測試方式：見 WORKFLOW §5

正式軌命令在repo根目錄執行，沿正式開發指南先備好鎖版環境。以下均為待執行命令，不是本次測試結果。

```powershell
api/.venv/Scripts/python.exe -m pytest -c api/pyproject.toml api/tests -q
npm.cmd --prefix web test
npm.cmd --prefix web run build
api/.venv/Scripts/python.exe deploy/verify.py
```

最後命令自動選隔離PF_BASE_URL並跑API／Vitest／build／E2E，完成後停止隔離服務但保留volume。需要檢視截圖用`--keep-running`，收工只停止本次啟動的隔離服務，不加-v。現有P1c記錄基準API80、Vitest56、E2E6、build exit0；G3需實跑核對。每Task是基準加新案例，不硬寫總測試數。

## Task 1 — 日期migration與metadata服務（A2）

**Files:** models.py、schemas.py、permissions.py、routes/projects.py、新services兩檔、新migration、test_migrations.py、test_node_metadata.py、test_projects_nodes.py。

**Interfaces:** spec §2／§4；NodeCreate限phase/task；NodeUpdate以model_fields_set区分未傳與null；assignment-options及node安全投影。暫時保留Gate原函式到Task2。

**Steps:**
1. 寫日期可空、單邊、反序、閏日、非法格式、PATCH合併另一端／清除、名稱trim與空白、不可改parent/kind/status及空patch測試。寫admin／專案owner／節點owner／部門主管／不相關／readonly-owner／跨公司權限矩陣，斷言失敗DB與audit不變。
2. RED：`api/.venv/Scripts/python.exe -m pytest -c api/pyproject.toml api/tests/test_node_metadata.py api/tests/test_migrations.py api/tests/test_projects_nodes.py -q`。新增案例必須因缺少欄位／介面／規則失敗。
3. migration增加兩nullable DATE及順序CHECK；先在舊revision插入專案／節點，再升級，斷言原ID／title／status／關聯不變且日期null。SQLite單元測試外，真PostgreSQL也須執行相同保留資料案例。
4. 實作授權、欄位白名單、同公司關聯查核、指派選項與capabilities。metadata變更先完整驗證再flush／audit／commit，no-op不寫audit；不可把can_manage_project套到status／Gate擴權。
5. 既有test_projects_nodes.py以POST指派readonly並期待201的測試，改用DB fixture建立歷史readonly指派，保留status拒絕與資料不變斷言，另測新POST拒絕readonly指派；不刪除原權限回歸。新增節點按父種類與可見性驗證；parent=null保留頂層兼容。舊project根不可PATCH。node.create包含完整metadata稽核。
6. GREEN跑同組及完整API；檢查日期CHECK、拒絕副作用與安全序列化。commit後獨立審查並更新PROGRESS。

**Commit:** `P2a task 1: add authorized node metadata and date migration`

## Task 2 — 多層樹與Gate防繞過（A4服務）

**Files:** services/node_policy.py、routes/projects.py、test_workflows_gates.py、test_projects_nodes.py。

**Interfaces:** 將blocked_by_pending_gate委派共用祖先遍歷；只查同公司同project，visited保護，損毀鏈回409。現有Report API不改status，不納入此Task修改。

**Steps:**
1. 建立project→phase→task→task；前phase pending時，深層todo改doing/review/done/skipped皆409且無audit；核准後成功。補phase本身、頂層task、無project根工作流、無Gate、其他公司Gate、循環父鏈案例。
2. RED／GREEN：`api/.venv/Scripts/python.exe -m pytest -c api/pyproject.toml api/tests/test_workflows_gates.py api/tests/test_projects_nodes.py -q`。
3. 從本人node向上找phase，復用既有sort_order／pending Gate語義；不得依前端可見集合判斷是否阻擋。錯誤內容不洩漏隱藏phase。
4. 完整API回歸包含既有Report／Gate授權；獨立審查核對新kind限制未破壞原seed／workflow。

**Commit:** `P2a task 2: enforce gates for nested tasks`

## Task 3 — 可見總覽與本人任務API（A5服務）

**Files:** routes/workspace.py、main.py、services/node_policy.py、test_workspace.py。

**Interfaces:** GET /workspace/overview、/workspace/my-tasks，依spec §4 JSON；沿用Task1 node投影。不要逐專案HTTP抓取或N+1查詢；可用批次取公司專案／節點／部門後套policy。

**Steps:**
1. 測兩公司、member隱藏父兄弟、readonly、project_owner非本人任務；只在可見資料上統計／搜尋；skipped分母、空集合null、四捨五入、本人且task限制、日期null-last穩定排序、非法status。
2. RED／GREEN：`api/.venv/Scripts/python.exe -m pytest -c api/pyproject.toml api/tests/test_workspace.py -q`。
3. 把可見判斷與投影共用；以status counts推完成率，不檢查隱藏子節點是否存在。先授權再套搜尋，回傳專案名亦使用可見Project。
4. 全API回歸及獨立安全審查，檢查回應沒有password_hash／session／別公司資料。

**Commit:** `P2a task 3: add permission-scoped workspace queries`

## Task 4 — 導覽與多層節點工作區（A1、A4 UI）

**Files:** App.tsx、App.test.tsx、api.ts、types.ts、styles.css、WorkspaceShell.tsx、NodeWorkspace.tsx、workspace.test.tsx。

**Interfaces:** route state為overview/my-tasks/project加projectId/nodeId；NodeItem增加日期、顯示名稱、capabilities。Task5填入總覽與本人任務內容，此Task先完成導覽、工作區與真實載入狀態。

**Steps:**
1. 寫登入後總覽導覽、切換專案、四層expand/collapse、麵包屑、隱藏父節點提升可見根、下一層看板、skipped顯示、Gate409／核准刷新，以及切換後舊回應不覆蓋新畫面測試。
2. RED／GREEN：`npm.cmd --prefix web test -- src/App.test.tsx src/workspace.test.tsx`。
3. 拆組件保留現有session／mutation序號機制。樹顯示採visited防循環；詳情初始選取支援跨頁定位。資料刷新以API為準，不自己遞迴推算權限或進度。
4. 測401清狀態、500重試、登出race、鍵盤與375長名稱；跑完整Vitest及build。UI走查使用隔離環境，記錄console與版面證據後獨立審查。

**Commit:** `P2a task 4: build navigable task workspace`

## Task 5 — 表單、總覽與我的任務（A3、A5 UI）

**Files:** App.tsx、App.test.tsx、api.ts、types.ts、styles.css、NodeEditor.tsx、WorkspaceOverview.tsx、MyTasks.tsx、node-editor.test.tsx、workspace.test.tsx。

**Interfaces:** NodeEditor mode=create/edit，收到projectId、parent/node、capabilities與成功刷新callback；普通編輯者不請求assignment-options。API沿spec §4。

**Steps:**
1. 表单新增／取消／局部編輯／null清除、兩端日期驗證、readonly無按鈕、普通編輯無指派控制、選項403、儲存中防重送、422保留輸入、成功後reload失敗僅重試GET、切換／logout忽略舊POST回應測試。
2. 總覽統計與空值顯示、我的任務搜尋／五狀態篩選／清除／空結果，點擊正確project/node；明確區別讀取失敗與空資料。admin空白專案入口與既有workflow入口皆可用。
3. RED／GREEN：`npm.cmd --prefix web test -- src/node-editor.test.tsx src/workspace.test.tsx src/App.test.tsx`。
4. 實作label／焦點／日期欄位及API错误映射，不加入假資料。登入失效清草稿；保存成功更新project、overview、my-tasks的下一次讀取，不重送mutation。
5. 全Vitest及build；1280／375表單操作、鍵盤提交／取消、長名稱走查。獨立spec及quality審查後PROGRESS記錄。

**Commit:** `P2a task 5: add task forms overview and my tasks`

## Task 6 — 整合驗收與文件交付（A6）

**Files:** web/e2e/workspace.spec.ts、mvp.spec.ts、health.spec.ts、api/tests/test_migrations.py、README.md、formal-development.md、mvp-trial-checklist.md、PROGRESS.md。

**Interfaces:** 原acceptance marker及verify入口保持，E2E在任何寫入前拒絕15173並驗marker。以唯一名稱建立測試資料，不刪既有資料，不改密碼。

**Steps:**
1. TDD採前移：Task1開始前先在本Task允許的workspace.spec.ts寫關鍵使用者旅程（admin四層建立與編輯、member本人入口、readonly拒絕）並實跑RED，記BASE與失敗原因；該檔由主寫入者持續維護，到Task6完成。功能已完成後不可用破壞產品制造RED；新增已通過的驗收案例如實記錄為回歸。
2. 各Task GREEN後，隔離Compose以真實登入完成兩公司／角色矩陣、日期／指派保存、登出再登入、多層Gate。1280與375斷言document無水平溢出、導航可用與console非預期錯誤為0。
3. 真PostgreSQL升級保留資料：隔離測試DB從0001建立fixture，記錄ID/status/關聯與counts，再upgrade head驗null及新日期持久化；downgrade僅於專用測試DB。不得在primary或已保存日期的驗收DB降版。
4. 正常停止再啟動隔離服務（保留volume、不seed），確認Task6專案日期仍存在；記錄前後業務值。使用`api/.venv/Scripts/python.exe deploy/verify.py`做完整回歸，失敗不能宣稱交付。
5. 更新README已完成／仍未完成對照、正式指南日期／權限／migration說明、試用清單P2a人類未勾選項目。獨立G4審查完整diff，修完所有Important／Critical。
6. G5 ff-only、G6 main完整隔離回歸；通過後依D50更新本機15173程式與migration（保留資料／env，不跑自動業務測試到15173），驗健康並提供人類試用；推origin main。若migration或環境不符保留現況並記錄，不重設資料補救。

**Commit:** `P2a task 6: verify task workspace and document delivery`

## Review Focus與完成條件

對照spec逐條審核：readonly-owner不繞過、一般editor不可改派、跨公司不能藉選單／聚合／錯誤訊息洩漏；PATCH驗證合併日期而非單獨payload；多層Gate沿實體祖先而非可見樹；隱藏task不影響完成率；網路超時不重送POST；舊project根／workflow／資料全部相容。

文件審阅不等於GREEN；真正完成需六Task與獨立審查、完整隔離測試、升級保留與重啟證據、1280／375實测、README／看板更新。P2a可試用不等於P2b–P2d完成，P1c及P2a人類簽核不得代勾。
