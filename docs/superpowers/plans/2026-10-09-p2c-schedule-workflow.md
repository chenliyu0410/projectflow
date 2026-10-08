# P2c 時程、模板與前置 — 精簡規格／計畫

日期：2026-10-09。D65精簡流程；D66人類已選A，以下範圍定稿並開始實作。Demo只作操作參照，不修改。沿用P2a/P2b資料、權限與回報審核。

## 展示目標與範圍

模板建立至少10個任務 → 查看日／週／月時程 → 改期並重載保留 → 前置未完成時拒絕開始／送回報 → 完成或略過前置後解鎖；桌面1280及手機375可走完整流程。

- 時程只列當下可見節點，樹狀展開／收合、今天標線、狀態與點擊任務詳情；無日期另列「未排程」，不捏造日期。依節點原日期畫條，phase手動日期與子任務分開，不自動推導父子日期。
- 日期以日曆日計算。桌面task條可拖曳移動及拉伸截止日（日期完整才可拖曳）；手機及鍵盤可用日期表單。沿用edit_metadata權限、nullable日期與日期順序驗證；單次改期只改該節點，不自動順延或修改子樹；取消不寫，失敗保持原資料、可明確重試，稽核沿用metadata更新。
- 工作流模板同公司可讀，admin／project_owner可新增／編輯／複製；建立專案仍沿既有權限。表單管理名稱、多層phase/task、排序、phase Gate、相對起迄日偏移及FS邊。相對日以新專案開始日為第0天；起迄可空，日偏移非負且起<=迄；節點新建時沿現有建立專案規則指派給建立者，部門不擅自繼承。
- 舊模板無偏移與相依，仍可按既有payload建立無日期專案。父子需同模板、無循環、phase/task種類合法；父節點建立先於子節點，不依資料庫sort_order猜父。模板更新只影響之後建立的專案；複製產生新ID；不提供模板刪除或覆寫既有專案。
- 前置先做**同公司同專案task間硬性FS、延遲0**，可多前置。管理者（同公司admin或實際project owner）新增／移除相依，端點均需可見；不接受跨專案、self、重複、循環。done/skipped滿足。未滿足前置禁止todo→doing／送回報／管理者送出並確認（不讓改status或直接report繞過）；已進行任務若前置重開，後續送回報也被擋，不回退既有狀態。
- Gate保持獨立且仍強制檢查，前置解鎖不能繞過Gate。略過／恢復／重開沿P2b管理者理由機制；不新增前置覆寫或跳過申請。
- 工作區提供前置設定、阻塞提示及可見task的簡單相依圖。隱藏前置不得洩漏標題／ID／日期／統計，僅固定「尚有未完成的前置任務」；API以完整真實相依判斷，UI隱藏不能代替授權。前後端不輸出raw payload。

**延後**：SS/FF、延遲、軟性前置／覆寫、自動順延、工作日／假日、里程碑鎖定、持久undo、關鍵路徑、時程相依連線、子樹另存／套用、拖曳改層級、自訂回報欄位。簡單相依圖不宣稱完整F4或原P2c全部完成。

## 資料、API與實作約束

- migration0004新增node_dependencies及模板相對日期/相依資料（使用Workflow.content合法且驗證版本化內容，或新增受FK保護模板相依表；實作選擇不改上述產品規則）。公司／端點FK與unique；保留0003所有原資料與ID，舊模板/專案不重寫。
- 擴充GET /workflows保持items id/name相容；新增GET /workflows/{id}、POST /workflows、PUT /workflows/{id}、POST /workflows/{id}/copy。schema extra forbid、trim名稱與限長、禁止其他公司參照，完整替換原子交易。既有from-workflow增加optional start_date；有偏移時需開始日，不無聲忽略模板設定。模板建立專案同交易寫節點/Gate/相依/稽核。
- 新增GET /projects/{id}/dependencies、POST /projects/{id}/dependencies、DELETE /dependencies/{id}；read投影只返回兩端可見邊，節點可含安全blocked布林。DELETE僅刪連線、不是刪任務，寫稽核。既有metadata date PATCH重用，不另造重試寫入通道。
- 相依編輯及受影響狀態/報告採一致鎖序（Project→Node）；循環查詢在project鎖內，防止同時加邊繞過驗證；報告先鎖project再node，避免與既有附件quota/node鎖序衝突。若調整交易需在完整現有報告/附件測試回歸，不擴故障矩陣。
- 不新增外部依賴。React/CSS/SVG自行畫基本時程與圖，文字自動跳脫；使用既有401清session與Abort/序列防舊回應。不可改API公司權限、把協作者升成執行者、寫入primary作驗收。

## 允許修改

api/app/models.py、schemas.py、main.py；routes/{workflows,projects,reports,workspace,dependencies}.py；services/{node_policy,record_policy,report_service,dependency_service,workflow_service}.py；alembic/versions/20261009_0004_p2c_schedule_workflow.py。
web/src/{App.tsx,api.ts,types.ts,styles.css}；components/{WorkspaceShell,NodeWorkspace,WorkflowLibrary,TimelineView,DependencyPanel,DependencyGraph}.tsx。
api/tests/{test_health,test_workflows,test_dependencies,test_migrations,test_collaboration_postgresql,test_report_lifecycle,test_node_metadata,test_mvp_acceptance}.py；web/src/{timeline,workflow-library,dependencies,App,workspace}.test.tsx；web/e2e/{schedule,health,mvp,workspace,collaboration,attachments}.spec.ts；deploy/verify.py（只加必要migration/PG驗證相依鎖）；README、PROGRESS、formal-development、mvp-trial-checklist。本文件修正可記錄。需要清單外變更先說明原因。

## 實作步驟與驗收

1. 後端migration／模板schema與CRUD／相依服務及強制阻擋；測核心FS、循環、跨公司/readonly、報告不能繞過、Gate仍生效、舊資料與模板相容。先定介面再UI，不拆成逐Task雙審。
2. 模板庫表單、建立專案開始日、時程（縮放/日期/拖曳）、前置設定及簡單相依圖；一般UI以有意義Vitest及真UI驗證，不強制人為RED。
3. 隔離專案走至少10任務完整旅程，另循環20task案例；驗桌面/手機無overflow非預期console、角色越權、重載保留。PG專用DB驗0003→0004舊值及相依交易，沿verify mandatory PG不允許skip，DSN/temp files隔離。
4. 候選版本一次完整verify；一位獨立審查者合併spec/品質檢查，修正只重驗受影響部分。更新README/PROGRESS及限制，不代勾人類簽核。
5. ff-only到main；不強制再次全量。primary先停止API、備份DB+files及env指紋、保留原值再無seed升級，檢查health/migration與舊資料；隔離cleanup無-v、D50 push並核對remote SHA。

實作commit可按後端／UI／驗收拆分（P2c: …，AI-Assisted-By: Codex GPT-6）；只在階段交付更新一次PROGRESS，阻塞或中斷另留最小紀錄。測試/審查未執行不得寫通過。

實作注意：新增API需同步test_health既有精確route集合，列入測試清單；只更新路由契約斷言，不變更健康端點或擴產品範圍。
