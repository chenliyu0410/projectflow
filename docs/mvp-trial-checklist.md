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

權限由真實session cookie與API判斷，前端公司欄位／角色顯示不能擴大資料範圍。P2b已實作回報／審核／筆記／協作／持久附件與稽核介面，整合驗收及發布狀態見PROGRESS；稽核依可見節點及安全欄位投影。真AI／雲端AI、ERP、AD／LDAP、完整RAG、文件版本與LAN／TLS正式部署不在本輪交付。

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
- [ ] 試用者理解目前回報／稽核介面與仍未提供的功能，接受本機MVP試用範圍。
- [ ] 管理者確認正式帳號、密碼、備份／還原、LAN／TLS與安全部署另行規劃，不沿用示範憑證發布。
- [ ] 試用負責人記錄意見、簽核日期與下一步；自動化通過不代替此項。

## P2a 工程驗收與人類試用

P2a工程驗收、雙獨立G4審查、ff-only合併與本機試用部署已完成；人類試用仍待簽核。前移旅程RED已於Task1前取得（1280／375共2 failed，缺工作區導覽）；功能完成後新增的整合案例屬回歸，不破壞產品製造RED。

P2a實跑記錄：隔離Playwright 9 passed (16.8s)，涵蓋四層建立、日期清除／指派／成員編輯／readonly，以及真實兩公司、多角色、深層Gate與可見完成率。真PostgreSQL專用DB `p2a_migration_b12b66168c4c`：1 passed, 4 deselected, 2 warnings (0.41s)，舊資料／稽核保留、日期null、新日期保存與反序CHECK皆通過。隔離Compose正常stop/start --wait，未seed，完整專案detail前後一致（包括start_date=null、due_date=2026-10-15、owner及department）；各階段exit0。完整`deploy/verify.py`：API 182 passed／1 skipped（專用PG另驗）／3 warnings (131.31s)、Vitest 96 passed、build exit0、E2E 9 passed (17.6s)，預設cleanup成功，最終exit0。隔離容器清單為空、`projectflow-acceptance_pgdata`保留。G6 main完整回歸另通過：API182 passed／1 skipped／125.26s、Vitest96／3.33s、build0、E2E9／16.8s及cleanup0。15173已啟動，首頁／health／ready為200、acceptance marker為404，migration為20261008_0002 head；此入口未跑自動業務測試。發布紀錄见PROGRESS。

以下維持人類待辦，不由自動化代勾：

- [ ] 管理者實際建立專案→階段→任務→子任務，指派負責人及部門，設定／清除日期後重新登入確認。
- [ ] 成員從「我的任務」搜尋／篩選並進入任務，編輯名稱／日期，確認沒有改派控制。
- [ ] 唯讀者確認不能新增／編輯／改派；試用者確認公司及可見範圍符合工作安排。
- [ ] 桌面及手機試用總覽、折疊導覽、樹、麵包屑與下一層看板，確認操作體驗。
- [ ] 確認「可見任務完成率」只算可見task，略過不進分母；日期不代表已有時程拖曳或自動排程。
- [ ] 試用負責人記錄P2a意見、日期與簽核；理解剩餘未交付項目與LAN／TLS限制。

## P2b 工程驗收與人類試用

P2b工程交付完成：八Task與G4雙獨立審查通過、ff-only合併main、G6完整隔離回歸及15173保留資料升級通過；人類試用仍未簽核。Task1前移旅程已取得真RED（a76bdb1；1280／375缺成果說明），Task8沿同旅程驗送出→退回→新版本→他人確認。新增驗收案例屬回歸，不破壞產品製造RED；verify新增強制PG階段另有真RED／GREEN。

Task8實跑：verify新增強制PG階段先取得真RED（2 failed、35 deselected，exit1），實作後部署測試39 passed。完整`deploy/verify.py`最終exit0：唯一`p2b_test_326c1ff802db42519aeb33f368efee17`先migration 1 passed（0.56s）、再真API競態3 passed（1.94s），兩階段不允許skip；主機API 337 passed／5 conditional skipped／5 warnings（265.53s）、Vitest148、build0、E2E13 passed（34.1s）。PG skip故障注入另確認整體非零、不執行後續API race。初次完整E2E稽核selector逾時為11 passed／2 failed，改用語意combobox定位後定點與完整重跑通過，保留失敗證據。

1280／375涵蓋前移回報旅程GREEN、管理者自核、協作增撤、筆記修訂、下載SHA、附件軟刪／回報鎖定、跨公司及唯讀拒絕、稽核安全投影／事件篩選／來源返回；精確允許初始auth/me401，非預期HTTP／console／pageerror皆0、無水平溢出。唯一資料的project／note／report／attachment及SHA於正常stop/start（不seed）前後一致；隔離offline pending修復後failed、partial檔移除、quota返還且ready綁定附件及SHA保留。最終cleanup容器清單空，`projectflow-acceptance_pgdata`與`projectflow-acceptance_files`保留；本Task未寫primary。詳細log、snapshot與截圖在ignored `.superpowers/p2b/task8-*`，人類項目仍未簽核。

G6 main再次完整驗收exit0：強制PG migration1／競態3、API337passed5conditional skip（265.91s）、Vitest150、build0、E2E13passed（34.0s）。admin／readonly×1280／375實看階段狀態說明，無overflow／非預期console；acceptance与Task4隔離容器已停止，DB／files雙volume保留。15173升級前停止API、保存DB備份與env指紋；原P2a無附件volume，升級新增files10001:10001/0700。migration0003、health／ready200、原有表全部欄位及row值完全相同、env指紋不變，未seed或跑primary業務測試。ignored證據見`.superpowers/p2b/g6-*`。

- [ ] 試用者在桌面／手機送出成果、閱讀退回意見、重送新版本，由另一位有權者確認完成。
- [ ] 管理者試用明確「送出並確認」、附理由重開／略過／恢復，確認不會繞過Gate。
- [ ] 指定協作者新增紀錄／筆記、作者修改筆記；撤銷協作後確認不可繼續讀取或下載，理解不擴張狀態與子樹權限。
- [ ] 上傳、下載並核對附件；確認回報附件鎖定、非回報附件軟刪與容量不自動釋放的規則。
- [ ] 查看審核中心、稽核篩選與游標載入，確認僅見授權範圍、來源導航正確。
- [ ] 管理者確認DB＋files一致備份、公司quota、停止API後pending修復流程；理解沒有預覽／病毒掃描或公開下載連結。
- [ ] 試用負責人記錄日期、意見與簽核，理解自訂欄位、跳過申請、Gate覆寫及P2c以後仍未交付。


## P2c 精簡範圍工程驗收與人類試用

依D65／D66A，只交付時程／模板／硬性FS的精簡範圍，非完整Demo移植。工程結果及部署狀態見PROGRESS；以下由人類試用簽核，自動化不代勾。

2026-10-09候選整合實跑：mandatoryPG分三個全新專用DB，P2b migration1 passed（0.53s）、P2c0003→0004保留值／約束1 passed（0.78s）、真雙連線race4 passed（2.21s），無skip。唯一完整verify在API階段為344 passed／7 skipped／2 failed（273.09s），exit1且finally cleanup成功；兩個失敗為舊query cap7，P2c新增單次批次前置查詢後仍成長前後8==8。依計畫窄適配cap8並加恰好一次dependency查詢斷言，兩target重新2 passed（2.05s）。7條件skip中的P2b／P2c migration及四race共6項已在mandatoryPG實跑；另1項P2a舊migration沿歷史證據，不本輪重跑。

繼續未執行stage：Vitest167 passed、build exit0；完整E2E15 passed／1 failed（46.5s），失敗是舊workspace將模板清單首項視為食品seed。改精確選「食品新品開發」後只重驗nested Gate案例1 passed，exit0；保留原Gate／可見完成率／跨公司斷言。依D65不重跑完整API或main全量，沒有宣稱原verify exit0。早期schedule定點2 failed為舊UI錯誤文案預期，API固定FS／Gate錯誤另精確驗證；適配後schedule＋health共7 passed（17.2s）。上述均為既有完成行為回歸，不冒稱產品RED。

10任務模板真UI涵蓋新增／複製、日週月、desktop拖移／拉伸後確認、mobile鍵盤日期表單及重載、FSdone／skipped解鎖與Gate独立、readonly真UI／跨公司／隱藏前置安全投影；另20task閉環原子拒絕。1280／375頁面無水平overflow，僅精確允許初始auth/me401與刻意FS/Gate409，其他HTTP／console／pageerror為0，截圖已實看。相依圖手機使用內部橫捲。兩個唯一專案正常stop/start、不seed，完整project（含日期／ID／狀態）、workflow及dependencies snapshot前後一致。證據保存在ignored `.superpowers/p2c/`，含full-verify、query-targeted、vitest、build、e2e-full、workspace-targeted、persistence及schedule／dependencies截圖。primary未執行業務測試，附件故障矩陣未重做。


- [ ] 建立含至少10任務的模板，試相對日、階段Gate、FS及複製，確認修改不影響已有專案。
- [ ] 以開始日建立專案，查看日／週／月、樹狀收合及未排程；理解phase日期不由子任務自動推導。
- [ ] 桌面拖移／拉伸及手機／鍵盤表單改期，確認儲存前可取消、重載保留且不自動順延其他節點。
- [ ] 確認前置未完成時禁止開始／送回報，done及skipped解鎖後Gate仍獨立生效。
- [ ] 以執行者／唯讀者實際查看時程與前置，確認隱藏節點不洩漏、協作不提升執行權限。
- [ ] 試用者接受本輪未提供關鍵路徑、SS／FF、延遲／覆寫、自動順延與其他列明延後功能，記錄意見／日期／簽核。

P2c交付：一次獨立審查Ready to merge: Yes，ff-only合併main；依D65不重跑main全量。15173停止API後成套DB+files備份，再無seed升至20261009_0004。全部原表欄位/row值、既有檔案SHA及env指紋相同，web/health/ready200，files10001:10001/0700。證據ignored `.superpowers/p2c/primary-*`；自動業務測試僅隔離環境，人類勾選仍未代勾。

## UI1 介面對齊驗收

工程驗收已完成一次獨立審查、完整前端回歸與失敗定點修正。完整Vitest165pass2fail→受影響78/78pass，build0；完整E2E15pass3fail→相關11/11pass，視覺與空／載入／503重試／session失效2/2pass。失敗均為舊結構定位與手機導覽步驟，業務及權限斷言保留；詳細證據與部署狀態見PROGRESS。Demo／正式1280與375PNG已保存並實看；不將隔離測試資料帶入15173。

- [ ] 桌面側欄、配色、字級與卡片接近Demo，長專案／任務名稱可閱讀。
- [ ] 手機開關導覽、總覽、我的任務、節點工作區與時程日期表單可操作。
- [ ] 完成回報、紀錄／筆記／附件、審核、模板與稽核頁面符合試用需求。
- [ ] 原有15173專案、日期與檔案仍在，理解UI1不代表P2d或完整Demo功能已交付。
- [ ] 試用者填寫日期、意見與簽核（自動化不得代勾）。
