# TP-D 前置進階：短規格與計畫

日期：2026-10-10。依D70／D65；人類已同意TP-C並指定下一批TP-D。D76已核准：人類簡要確認人工條件與其餘TP-D照計畫後回覆「好」。不表示已實作。

## 目標與差距

補齊SS／FF、延遲天數、軟性前置、條件型前置（不含文件）及相依圖拖線建立。此次先以原始碼對照：Demo的depMet、findBlockers、forecast、前置編輯器、拖線事件；正式版dependency_service、schedule_service、report_service、DependencyPanel／DependencyGraph。尚未做瀏覽器操作驗證，不宣稱畫面已對齊。

| 項目 | Demo依據／行為 | 正式版現況 | 本批建議 |
|---|---|---|---|
| 關係類型 | FS／SS／FF；SS非todo即滿足 | 只有兩個任務端點，視為FS | 新增relation_type；FS完成後開始、SS開始後開始、FF完成後完成 |
| 延遲 | 排程FS為結束+lag+1、SS開始+lag、FF結束+lag；不按實際狀態時間倒數 | FS零延遲 | 整數-365至365日，負數表示提前；只約束計畫日期，不新增工作日曆或實際完成後倒數 |
| 軟性 | 警示但可操作 | 一律阻擋 | enforcement hard／soft；soft不擋狀態、不強制順延、不納入關鍵鏈 |
| 條件 | condMet讀取採購單或營運紀錄指定欄位是否等於need | 尚無正式營運資料模組 | D76需決定：本批人工確認條件，或等營運模組提供真實資料再接入 |
| 拖線 | 圖上拖出FS硬性連線 | 表單新增／刪除 | 拖線後開確認表單，可選類型、延遲、強度；取消不寫入 |
| 編輯 | 可調整類型／延遲／強度 | 僅新增／刪除 | 新增PATCH並記前後值稽核 |
| 阻擋 | FS／SS及条件開始檢查含上層，FF在自身完成檢查 | 開始與送回報共用FS檢查，核准尚未重檢前置 | 分離開始／完成檢查；所有完成入口重檢FF；維持既有Gate與權限 |
| 連動 | 時程、箭頭及預測識別類型 | TP-C只識別FS | 三種端點與lag共用計算、標籤及日期衝突；保留D75原子回滾 |

## D76已核准的產品規則

1. **建議條件採人工確認**：先做「到貨已確認」等有名稱的獨立條件，由系統管理員／該專案負責人確認或撤回，記錄理由、操作者、時間與稽核。介面明示「人工確認」，不假稱ERP同步。條件附屬同公司同專案的目標任務，不用虛構前置任務；可選硬性／軟性，僅限制開始。這是與Demo的刻意差異，需要人類確認。替代方案為本批延後條件型，等UI5／F1有正式資料來源再做；不自動擴大本批為營運模組。
2. **狀態與日期分開**：FS等待done／skipped；SS等待doing／review／done／skipped；FF只擋完成，不擋開始或送待確認回報，但自我確認與審核核准均重檢。保留既有FS／SS在送回報時重檢，避免既有保護消失；開始檢查包含自身及上層FS／SS／條件，FF只針對自身。略過仍沿既有管理者權限，不新增覆寫／申請（TP-F）。已開始任務不因條件撤回自動退回狀態。
3. **日期與權限**：採上述lag公式與範圍；硬性關係才限制日期／順延。FS／SS上層限制延續至子孫；FF限制目標自身結束。新建或編輯連線不自動改日期，只顯示衝突；改期仍走D75服務，任何受影響項目無權、鎖定或不可調整，整筆拒絕。建立／編輯／刪除前置及人工條件沿既有專案管理權限，不放寬為任務負責人。

## 資料與API

- migration 0008為node_dependencies新增relation_type（FS）、lag_days（0）、enforcement（hard），有enum／範圍DB約束；保留每個既有欄位值。舊請求仍預設FS／0／hard，同方向任務對保留唯一連線，不允許自環／循環，soft也檢查循環。降級有非預設資料則拒絕。
- 若採人工條件：獨立node_conditions表，含organization_id、project_id、node_id、label、enforcement、is_met、確認資訊及建立者；複合外鍵保障公司／專案隔離。新增／編輯／刪除／確認均鎖專案並在同交易稽核。条件撤回保留稽核；不存在、軟刪除、跨公司或不可見目標不洩漏內容。降級有條件資料則拒絕。
- POST／PATCH dependencies及conditions由嚴格schema驗證。警示只提供可見端點詳細內容，隱藏前置使用泛稱，不回傳名稱、日期、數量。清单、節點capabilities、送回報／核准與時程使用同一套判斷。
- TP-B複製保留內部連線類型／lag／強度；人工條件複製標為未確認，不沿用他人確認證據。刪除／復原保存條件與邊完整快照，復原檢查權限與有效關係。既有工作流模板使用獨立schema或顯式默认，避免直接擴充DependencyCreate意外引入未支援模板行為；TP-E再補模板進階保存。
- 時程與圖形標示FS／SS／FF及正負lag、硬／軟、滿足與否；預測依可見硬性任務邊估算，條件無日期不虛構工期。不可見資料不進前端推算，仍明示非完整CPM。

## 允許檔案與步驟

核准後於主checkout開唯一feature/tp-d-advanced-dependencies，無新外部依賴、不改Demo。

1. API：models.py、schemas.py、routes/dependencies.py、routes/projects.py、routes/reports.py、routes/audit_logs.py；services/dependency_service.py、schedule_service.py、record_policy.py、node_policy.py、report_service.py、tree_service.py、workflow_service.py；新增services/condition_service.py及routes/conditions.py（採人工條件時）、main.py註冊；migration 0008。
2. 前端：types.ts、api.ts、timeline.ts；components/DependencyPanel.tsx、DependencyGraph.tsx、TimelineView.tsx、NodeEditor.tsx、NodeWorkspace.tsx、AuditLogView.tsx、ReportPanel.tsx、ReviewCenter.tsx；styles.css。新增web/src/dependencies.ts共用判斷／標籤工具。指標拖線取消、錯誤保留草稿、鍵盤／手機用等效表單。
3. 測試：新增api/tests/test_tp_d_dependencies.py、web/src/dependencies-advanced.test.tsx、web/e2e/dependencies-advanced.spec.ts；test_migrations.py與既有dependency、schedule、report、tree測試，deploy/verify.py加入PG 0008保留資料階段。既有測試允許test_tp_c_schedule.py、test_tree_editing.py、test_dependencies.py、test_reports.py、test_health.py及web/src/timeline-advanced.test.tsx、timeline.test.tsx、dependencies.test.tsx（僅調整本批新增欄位與語意斷言）。
4. 文件：本計畫、README、PROGRESS、formal-development、mvp-trial-checklist。commit主旨TP-D，實際工具／模型trailer。

## 驗收與交付

- FS／SS／FF開始、送回報、自我確認、核准矩陣；硬性拒絕、軟性成功且有警示；上層繼承、前置重新開啟、hidden／readonly／跨公司拒絕；失敗交易不寫日期或稽核。
- 正／零／負lag與FS翌日、SS開始、FF結束；混合鏈／分叉匯合／父層／鎖定回滾；日期超界及循環有限終止；圖與時程一致。
- 條件未確認／確認／撤回、權限、複製重置及刪除復原；不把條件當假任務。若D76選延後，本節明列取消而非宣稱完成。
- 隔離Chromium E2E驗证拖線→表單→儲存→重載、取消零寫入、軟性提示、FF核准阻擋、人工條件（若核准）；1280／1440／375與Demo對照，頁面無水平溢出、pageerror 0。
- 依WORKFLOW §5／§14一次完整隔離回歸（PG、API、Vitest、build、E2E）及一次唯讀獨立審查，修正後定向驗證。只文件階段不跑產品測試。
- 交付才ff-only main；15173更新前備份DB／files／env並記原有值及附件SHA，migration保留所有舊值，不seed；健康／唯讀確認與D50 push main。LAN未授權。
