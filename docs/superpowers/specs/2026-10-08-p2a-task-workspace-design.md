# P2a：完整任務操作與工作區設計

日期：2026-10-08。基準：`9c2fe9e`。依據：[路線圖](../../formal-feature-roadmap.md)、[PROGRESS D55](../../PROGRESS.md)。

**審閱草案**：人類已授權撰寫規格與計畫；下列建議規則待D56確認，尚未通過G1，不得據此開始產品實作。配套[計畫](../plans/2026-10-08-p2a-task-workspace.md)同為草案。

## 1. 問題與目標

正式版目前可登入、選擇專案、查看節點與看板、變更狀態及核准Gate，但無完整任務編輯、日期、總覽與跨專案本人任務入口。本階段將這些能力整合為可日常操作的工作區，保留公司隔離、真實持久化及現有資料。

對應路線圖A1–A6：工作區導覽、metadata API、新增／編輯、多層工作區、總覽／我的任務、整合交付。至少支援專案→階段→任務→子任務四層操作。

不含：回報審核UI、筆記附件、協作授權、時程拖曳、模板CRUD、相依排程、通知、刪除／批次操作、複製或移動子樹、AI、ERP、LAN／TLS。現有狀態與Gate API保留；不代表P2b已完成。Demo與其測試不修改。

## 2. 待確認的產品規則（D56，推薦整組採用）

### 權限矩陣

所有操作先檢查session及公司。角色名稱project_owner不代表擁有公司所有專案；管理權依`Project.owner_user_id`。

| 操作 | admin | 該專案擁有者（非readonly） | 節點負責人／該部門主管（非readonly） | 其他同公司使用者 |
|---|---|---|---|---|
| 讀專案／節點 | 沿既有can_view_project／can_view_node | 同左 | 同左；不擴大member可見範圍 | 同左 |
| 新增phase／task、改派負責人或部門 | 可以 | 可以 | 不可以（除非同時是專案擁有者） | 不可以 |
| 編輯task／phase名稱與日期 | 可以 | 可以 | 必須同時可見且can_work_node | 不可以 |
| 更新status／核准Gate | 沿既有政策 | 沿既有政策 | 沿既有政策 | 沿既有政策 |

readonly一律不可新增、編輯或改派，即使歷史資料把它設為專案／節點負責人或部門主管。選人只列同公司非readonly使用者的id／display_name，部門列同公司id／name；只向具備新增或改派能力者提供選項。不提供帳號、密碼雜湊或session資料。負責人與部門可以獨立指定，不強制負責人屬於選定部門（沿既有模型）。既有readonly指派可讀取，但不可新指派。

`can_manage_project`負責上述新增／改派；`can_edit_node`要求可見且為管理者或can_work_node。新增管理權不擴大status／Gate授權。metadata表單不可傳入status、kind、parent_id、project_id或organization_id。後端回傳capabilities只供UI呈現，每次寫入仍重新授權。

### 層級與舊資料

專案本身作為虛擬容器；既有kind=project根節點保留唯讀，避免與Project.title分歧。新增規則：專案容器或project節點下可建phase／task；phase或task下只能建task。task可有子task；不得新增第二個project根、任意kind、跨專案父節點或循環。parent_id=null表示專案頂層，與既有無project根的工作流資料相容。新節點status固定todo；owner與department預設null，不暗中繼承。

新增只可在可見父節點下；不存在或不可見父節點不洩漏內容。舊有不符新規則的節點仍可讀，不自動搬動或刪除；新規則不回溯重寫歷史結構。project根不提供metadata編輯，專案改名不在本階段。多層樹遍歷需有visited保護。

### 日期與名稱

名稱trim後1–200字元。start_date／due_date為可空的ISO日曆日期YYYY-MM-DD，範圍0001-01-01至9999-12-31；可只填一端，兩端皆有值時start_date <= due_date。無時區換算，可回填過去日期；不限制在父節點日期內，不自動順延或推算父日期。PATCH省略欄位表示不變，明確null清除可空欄位；title=null、空patch與額外欄位拒絕。跨日期PATCH須和DB另一端合併後驗證。

### 統計

依API授權後的可見資料計算，不回傳被隱藏節點的名稱、數量或狀態。任務數計所有可見kind=task（含有子任務的task，各算一次）；完成率=done/(全部task-skipped)，分母0回傳null，畫面顯示「—」。skipped另列，review不算完成，不修改父節點status。介面標「可見任務完成率」，不冒稱全專案進度，不使用隱藏子節點判斷葉節點。專案數沿既有可見Project集合，沒有可見task的專案仍可列出。

我的任務僅列owner_user_id=本人且可見的kind=task；不包含部門主管可操作但未指派本人的任務。依due_date升冪、null最後，再project_id／id排序。搜尋trim後不分大小寫比對任務名稱或可見專案名稱；status可篩全部或五個現有狀態，預設全部。搜尋／篩選不改總覽基礎統計。

## 3. 畫面與互動

登入後進入總覽，主導覽為「總覽」「我的任務」「專案工作區」，持續顯示公司、使用者與登出。保留從工作流建立專案；提供admin既有空白專案建立入口，其他角色沿原API限制。手機用可折疊導覽，主要內容不得水平溢出。

總覽顯示可見專案數、五種task狀態數、完成率及專案入口。我的任務顯示名稱、專案、負責部門、狀態、起迄日，提供搜尋／狀態篩選與清除篩選。點擊以project_id及node_id定位，不依目前樹的選取值。

工作區包含專案選擇、展開／收合樹、麵包屑、節點詳情與下一層看板。深連結進入時展開可見祖先；不可見父節點下的可見任務作可見根呈現，不補查或顯示祖先名稱。看板只列下一層，不重複扁平列全樹；skipped有獨立清單，既有四欄保留。節點詳情顯示名稱、狀態、負責人、部門與日期，null顯示「未指派／未設定」。既有關聯的顯示名称由API以同公司安全投影提供。

新增／編輯用具label的表單：名稱、種類（僅新增）、負責人、部門、起迄日。普通編輯者不顯示指派選單。取消不寫入；保存中禁用重送與取消，導航仍可離開且忽略舊回應。成功重新載入相關資料；若寫入成功但reload失敗，明示「已儲存，資料重新載入失敗」只重試讀取，不能再次POST。網路失敗時不自動重送寫入，提醒重新整理確認結果；表單保留輸入。切換專案／公司或登出清掉表單與快取，使用既有sequence／AbortController避免舊回應污染新頁面。

每頁有載入、無資料、篩選無結果、讀取失敗重試；401清session回登入，403顯示無權限、404顯示找不到項目，422欄位錯誤保留輸入。Gate 409維持原狀態，提示阻擋；不揭露不可見前階段名稱。

## 4. API與資料契約

新增Node.start_date、due_date（SQL DATE nullable），以migration `20261008_0002_p2a_node_dates`接續`20261008_0001_p1a_core`，既有列皆null。加日期順序CHECK；upgrade不得改ID／status／關聯／業務稽核或重設seed。只在隔離DB測downgrade；實際資料回退不自動drop日期欄位。無新套件。

| 介面（均在/api下） | 契約 |
|---|---|
| GET /projects/{id} | 保留既有欄位；nodes增加日期、owner_display_name／department_name（nullable）、capabilities={edit_metadata,assign,create_child}；project增加capabilities={create_node} |
| POST /projects/{id}/nodes | 沿既有路徑，新增日期、限制kind為phase/task、驗證父與角色；回傳201 node；新增project.kind不開放 |
| PATCH /nodes/{id} | metadata局部更新，200 node；整筆原子驗證；node.update稽核只記實際更動欄位的before/after，同交易commit；相同值回200但不追加業務稽核 |
| GET /projects/{id}/assignment-options | 管理者且可見專案才200；{users:[{id,display_name}],departments:[{id,name}]}；其他403，跨公司404 |
| GET /workspace/overview | {project_count,task_counts:{todo,doing,review,done,skipped},completion_percent,projects:[{id,title,task_counts,completion_percent}]}；完成率四捨五入整數或null |
| GET /workspace/my-tasks?q=&status= | {items:[node加project_title]}；空q／空status不篩；非法status 422；完整授權集合才篩選與排序，本階段不分頁，不截斷 |

路由以靜態workspace前綴避免與既有動態id衝突。新metadata端點的節點404用於不存在／其他公司／不可見；既有status端點仍沿can_work_node與原錯誤契約（部門主管可能可操作但不可見），不在此默改；同公司可見但不准寫403；同公司不合法關聯400（不指出其他公司的名稱），schema／日期422。所有失敗不產生部分變更或業務稽核。新增節點稽核沿node.create，含日期與指派內容。

## 5. 多層Gate相容性

現況`blocked_by_pending_gate`只看直接父phase；P2a允許task下新增task後必須修正。沿父鏈找所屬phase（同公司同專案，visited防循環），比較現有sort_order及前階段pending Gate；phase本身亦視為所屬phase。維持現有todo→doing/review/done/skipped阻擋語義，其他轉換不另改制度；Gate核准權限不變。

狀態API使用此判斷，不能從深層子任務繞過。現有Report submit只新增TaskReport與稽核、不更動Node.status，本階段保持原契約；P2b若加入狀態轉換須重用此判斷。metadata編輯本身不啟動任務，不受Gate阻擋。遇到循環或損毀父链以409拒絕工作狀態變更；專案頂層task無phase則沿既有無Gate行為。不加入一般前置或Gate覆寫。

## 6. 驗收與文件

- admin建立空白專案與四層節點，設定／清除日期及指派，重新登入和重啟服務仍一致。
- 專案擁有者可新增／改派；成員只編輯可見且可操作的節點名稱／日期；非擁有者、readonly（含被設為owner情況）、他公司拒絕越權且DB／稽核不變。
- 兩公司、多角色和隱藏父節點案例；總覽、搜尋、本人任務不洩漏hidden節點；done/skipped/空集合符合公式。
- 舊migration含既有專案資料升級後原值與數量不變，日期null；非法日期由schema及DB防線拒絕。
- 深層Gate狀態阻擋→有權者核准→可開始；既有工作流無project根仍可新增子節點。
- 1280／375、鍵盤表單、長名称、空資料、500重試、401、403、404、422、mutation重複點擊與舊回應；console無非預期錯誤。
- API／Vitest／build／隔離Playwright與真PostgreSQL migration驗收；更新README、正式開發指南、試用清單及PROGRESS。P1c人類簽核仍由人類完成。

## 7. 功能對照及審閱重點

Demo pageOverview／pageMyTasks／openEditor只作互動參照。父子聚合改用上述可見task口徑；不移植Demo假通知／ERP狀態或前端授權。拖曳改層、複製子樹、批次刪除留待獨立規格；本階段的日期欄位不代表已有時程功能。

D56主要取捨：推薦「管理者新增／改派，執行者編輯名稱日期」保留責任分工；更嚴方案為所有metadata僅管理者可改，代價是成員無法自行改期。日期可空與可見task完成率是推薦配套；未同意前不升級DB或改產品。
