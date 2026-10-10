# TP-E 模板進階：短規格與計畫

日期：2026-10-10。依D70／D65；人類指定下一批TP-E。人類回覆「照建議做」，D77已核准，依本計畫實作。

## 目標與原始碼差距

從既有節點保存可重用結構，選定版本加入其他節點，並管理模板。對照Demo的pageTemplates、nodeToTemplate、openApplyTpl、applyTemplate、submitSaveTpl、deleteWorkflow，以及正式版WorkflowLibrary、App標題列、workflow_service、WorkflowWrite與tree_service。本輪完成原始碼對照；瀏覽器同尺寸對照尚未執行，不宣稱視覺驗收。

| 項目 | Demo實際行為 | 正式版現況 | 本批提案 |
|---|---|---|---|
| 另存 | 保存根與子孫、相對日期、里程碑、人員／部門；葉節點入口停用 | 入口停用；只能手動編輯工作流 | 任務及階段可另存，含葉任務；專案保存為工作流 |
| 套用 | 模板根新增成目標子任務，原有內容保留；可選結構／前置／人員／日期及填變數 | 只能從工作流建立新專案 | 任務模板追加子樹；工作流追加到既有專案頂層 |
| 版本 | 同名任務模板遞增；history只存版號／日期／備註 | content格式版號不是使用者版本 | 保存完整不可變快照，可查看及選版套用 |
| 刪除 | 自訂工作流可刪、內建不可刪；任務模板無刪除入口 | 沒有刪除API | 公司模板軟刪除，保留歷史及已套用任務 |
| 進階欄位 | 保存type／lag但漏soft；條件不保存 | 只有FS與相對日期 | 保留FS／SS／FF、lag、hard／soft、里程碑、權重；人工條件重新確認 |
| 模板庫 | 工作流／任務兩區、版本、統計、預覽、套用 | 工作流可用；任務區尚未提供 | 接通真實模板、版本及刪除，沿既有卡片與對話框布局 |

## D77已核准的產品規則

1. **追加，不覆蓋**：套用只新增結構，不改既有任務或日期。任務模板含根，新增一個根任務及子孫；階段另存為任務模板時根轉普通任務，不帶階段閘門，預覽明示。專案另存工作流不建立虛構專案根，保留頂層階段及閘門；工作流只能套到專案。目標及上層沿D74檢查，待確認／完成／已略過時拒絕新增。
2. **公司模板與權限**：本批先用同公司共用模板，不新增個人發布流程。模板管理限admin／project_owner，沿現有工作流規則；另存另須來源專案管理權與完整子樹可見，套用須目標專案管理權。跨公司引用404，不可透過模板發布看不到的任務；公司內瀏覽沿既有權限，由API強制。
3. **完整版本**：新模板v1，修改或另存到明確選定的既有模板才新增版本。同名時提示「建立新版」或改名，不默默覆蓋。版本可看作者、時間及結構，可選舊版套用；已建立任務不連動。複製新模板從v1起。本批不做版本差異比較／回退編輯。刪除是軟刪除並隱藏，不影響既有任務；無垃圾桶還原介面，名稱仍保留。產業範本來源唯讀，匯入的公司副本可刪。
4. **帶入內容**：預設帶完整結構、前置與相對日期；負責人／協作部門另行勾選，預設不帶、新任務未指派。保存標題、說明、部門、權重、里程碑；鎖定重設false，狀態待處理，完成進度及閘門核准重設。保留子樹內任務前置與強度，外部前置不帶且預覽明示，不洩漏隱藏端點。人工條件只保存名稱／強度，套用重設未確認，不帶確認證據。回報、筆記、附件、稽核、文件不複製；自訂回報欄位留TP-G。
5. **選項與日期**：任務模板可取消結構、前置、人員、日期；不帶結構只建根，不帶前置同時不帶人工條件；工作流保持完整結構。日期以所有已排程端點最早日為基準保存偏移，空日期保持空；選帶日期且模板有日期時必填開始日，不帶日期全部未排程。里程碑須單日、超界整筆拒絕，不自動改既有任務日期。標題中{變數}純文字替換，预览並驗證長度，不執行運算式。
6. **復原與延後**：套用可用既有「復原上一步」撤回整組新增，限原操作者，後續有活動即拒絕，沿TP-B保留資料。模板編輯／刪除不納入結構復原。保存／套用每次最多300節點。直接搜尋過去任務套用、個人發布、AI推薦、文件／檢查清單延後；TP-B複製仍可用，不宣稱完成README F2全部功能。

## 資料與API

- migration `20261010_0009`：workflows新增模板種類、目前版本、deleted_at；新增workflow_versions，含organization_id、workflow_id、version、完整JSON快照、created_by、created_at，複合公司外鍵與版號唯一约束。既有模板保留原列／欄位值，補v1快照；舊格式向後相容，不重建專案。遇新版本／刪除／新格式資料拒絕有損降級。
- 使用workflow_service統一驗證及展開。快照採模板內部鍵，人員／部門套用前重驗同公司及有效性；選擇帶入但引用失效時整筆拒絕，提示取消該選項，不默默部分成功。
- 既有GET／POST／PUT／copy／from-workflow相容舊請求，擴充kind、version與capabilities；新版編輯帶expected_version避免覆蓋併發更新。新增GET /workflows/{id}/versions、GET /workflows/{id}/versions/{version}、DELETE /workflows/{id}。from-workflow限工作流模板，可指定版號。
- 新增POST /nodes/{id}/save-template、POST /projects/{id}/save-template；POST /nodes/{id}/apply-template、POST /projects/{id}/apply-template。保存新版必填template_id及expected_version；套用指定已預覽版號，回傳新增數與undo_id。沿既有樹／前置服務檢查位置、深度、循環與授權。
- 保存鎖來源專案及模板；套用鎖目標專案及模板，固定鎖順序。快照、節點、前置、條件、閘門與稽核同交易，失敗全部回滾。刪除與套用併發須序列化。新節點使用新ID，稽核記模板／版本及新增ID。
- 所有列表、版本讀取、複製、套用與建立專案排除軟刪模板。編輯器須保留未顯示的進階欄位，不得儲存後消失。預覽呈現根轉換、數量、日期、重設與不帶入項目，提交時重新驗證。

## 允許檔案與實作步驟

核准後於主checkout開唯一`feature/tp-e-advanced-templates`；無新依賴，不改Demo。

1. API：api/app/models.py、schemas.py、routes/workflows.py、routes/projects.py、routes/audit_logs.py、services/workflow_service.py、tree_service.py、node_policy.py；必要時新增services/template_service.py分離快照／展開；新增api/alembic/versions/20261010_0009_tp_e_templates.py。先migration／版本，再另存／套用／刪除及undo。
2. 前端：web/src/types.ts、api.ts、App.tsx、components/WorkflowLibrary.tsx、WorkflowCatalog.tsx、NodeWorkspace.tsx、AuditLogView.tsx、styles.css；新增components/TemplateDialogs.tsx。啟用入口、任務模板卡、選版／預覽／選項、同名處理、刪除確認；錯誤保留草稿，手機與鍵盤可操作。
3. 測試：新增api/tests/test_tp_e_templates.py、web/src/templates-advanced.test.tsx、web/e2e/templates-advanced.spec.ts；更新api/tests/test_migrations.py、test_workflows.py、test_workflows_gates.py、test_tree_editing.py、test_health.py、web/src/workflow-library.test.tsx及deploy/verify.py的PG驗證階段。只調整本批實際改變的既有契約。
4. 文件：本計畫、docs/PROGRESS.md、README.md、docs/formal-development.md、docs/mvp-trial-checklist.md。產品commit主旨TP-E並記實際工具／模型。

## 驗收與交付

- 葉任務／子樹／階段／專案另存→重載模板庫→預覽→套用；位置正確、原任務逐值不變、300節點／深度／循環限制有效。
- v1→v2完整保留，舊版可查看／套用；併發409、重名明確處理；軟刪阻擋所有使用入口，歷史及既有任務保留；複本v1。
- SS／FF／正負lag／soft／里程碑／未排程／條件重設；人員失效、日期超界、變數長度與跳脫、取消及失敗零部分寫入。
- 一般成員／readonly／非該專案管理者／跨公司／隱藏子樹／刪除來源拒絕；錯誤不洩漏隱藏資料。復原整組新增含階段與閘門，已有活動拒絕。
- 實作前補Demo與正式版模板庫／另存／套用同尺寸對照；隔離E2E驗證1280／1440與375手機主流程、錯誤、取消、長名稱，pageerror 0、無頁面水平溢出。
- D65一次唯讀獨立審查及一次完整隔離回歸（PG migration、API、Vitest、build、E2E），修正後定向驗證。規劃階段僅文件核對，不跑產品測試。
- 交付ff-only合併；15173更新前備份DB／files／env與原值、附件SHA，migration不seed／重設；健康與唯讀確認後依D50 push main。LAN未授權、人類試用不代簽。
