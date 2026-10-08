# P2b：回報、審核與協作設計草案

日期：2026-10-08。程式基準：`c0284f6`。依據：[路線圖](../../formal-feature-roadmap.md)、README F6／F11、[PROGRESS D58／D59](../../PROGRESS.md)。

**狀態：G1已定稿（2026-10-08，D64）。** 人類已逐項核准D59–D63的A方案；人類已指示繼續依本規格與[實作計畫](../plans/2026-10-08-p2b-collaboration.md)執行，介面以Demo效果為主要參照；已確認規則不重問，遇到真正阻塞或範圍取捨再詢問。進度見PROGRESS。歷史B方案僅留作決策紀錄。

## 1. 目標與範圍

讓使用者在既有P2a任務工作區留下工作成果、送審、退回重送、確認完成，並透過筆記、附件與協作角色完成多人工作。

對應B1–B6：回報審核服務、回報介面、筆記與協作、主機附件、審核中心與稽核、隔離整合交付。保留既有專案、任務日期、回報、稽核及試用資料；Demo與其測試不改。

不把P2c時程／模板管理／一般相依排程、P2d AI／ERP、LAN／TLS或人類試用簽核納入本次完成宣告。依D63，跳過／覆寫申請不納本期，不沿用Demo子樹操作。

## 2. 已核對的現況

| 項目 | 現有程式行為 | P2b設計影響 |
|---|---|---|
| `POST /nodes/{id}/reports` | 驗can_work_node，新增submitted回報與report.submit稽核；不改Node.status | 不能只加審核按鈕便宣稱已有狀態流程 |
| `PATCH /nodes/{id}/status` | 可操作者能直接改review／done／skipped；有P2a祖先Gate檢查 | 若採正式送審流程，API也須禁止直接完成繞過 |
| TaskReport | result、summary、status、提交者與時間 | 缺版本、審核者／時間／意見、實際完成日及歷史相容標記 |
| 回報查詢與審核 | 尚無清單／確認／退回端點 | 需新API、UI與競態保護，不能只改現有POST |
| 稽核查詢 | 限公司、最新50筆，回傳actor_username與原payload | 必須另核定節點可見範圍、欄位投影與分頁；不可把現有原payload直接展示給所有成員 |
| 協作 | 無Node協作資料；member可見本人負責的節點，我的任務只列本人負責 | 新增協作可見性時须同步詳情、總覽、搜尋、本人入口及附件授權 |
| 附件 | 無正式附件模型、服務或檔案volume | 需獨立持久化、每次下載授權及DB／檔案失敗處理；不能寫到容器暫存層 |

現況來源：`api/app/routes/reports.py`、`projects.py`、`audit_logs.py`、`permissions.py`、`models.py`、`services/node_policy.py`及`deploy/docker-compose.yml`。本次只讀程式，不對15173送業務請求。

## 3. 已確認：回報驅動完成（D59）

### A：回報驅動完成（人類已選，2026-10-08）

1. 執行者填寫成果並送出，任務進入review；此回報內容鎖定。
2. 有審核權限者確認後進入done；退回必填意見，任務回doing。
3. 退回後重送建立新版本，保留前次回報與退回紀錄，不能覆寫歷史。
4. 同一任務同時至多一筆待審版本；兩人並行送出或審核只能成功一次，另一方收到可理解的衝突提示。
5. 一般狀態選單及直接呼叫status API都不能繞過送審進入review／done；已有待審回報時不得以另一條狀態更新使回報與任務脫節。
6. 回報、任務狀態與稽核在同一交易提交；失敗時不得留下部分狀態。沿P2a實體祖先Gate檢查，不依可見樹判定。

代價：改變P2a直接標記完成的操作習慣，需要調整既有API／UI回歸測試；但能讓「確認完成」具有實際約束力。自行確認依D60，重新開啟與跳過依D63及§5矩陣，不從D59單項推定。

### B：回報審核與任務狀態分開（未採用，保留比較紀錄）

新增回報確認／退回及歷史，但保留可操作者直接改done；回報審核結果不強制控制任務狀態。

代價：相容現有操作，但任務可在回報尚未核准時顯示完成。UI須明確區分「任務狀態」與「回報審核結果」，不能宣稱完成必須審核。

### 既有資料的必要相容條件（兩方案皆遵守）

- 已有done任務不回退，舊回報的ID、文字、提交人與時間及既有稽核不改寫。
- 歷史submitted回報未必對應review，且一個任務可能多筆；migration不能直接把它們全當新待審流程，亦不能先加唯一約束而使升級失敗。
- 完整規格須提供歷史記錄的識別／顯示規則與明確啟用界線，避免舊回報被新審核端點誤操作。具體schema於完整規格與plan列明。
- 不做自動回溯核准、不刪除重複歷史、不重設seed。

### 已確認：審核授權與自行確認（D60，2026-10-08採A）

兩方案的審核人範圍相同：同公司且可見該任務的admin、實際Project.owner_user_id本人、任務負責部門主管，或具既有can_work_node範圍的reviewer。readonly一律拒絕；僅有project_owner角色、一般任務負責人或協作身分不自動取得審核权。reviewer不因角色名稱而取得全公司審核權。部門主管仍須符合可見條件；本決策不暗中扩大節點讀取範圍。

| 方案 | 自己提交的回報 | 取捨 |
|---|---|---|
| A（已採用）管理者可明確自行確認 | admin或該專案實際擁有者，同時有該任務送出權時，可選「送出並確認」；其他審核者不能審自己提交的版本 | 沿README F11的管理者快速完成方向，適合小團隊，不必為每份管理者回報找另一人 |
| B（未採用）一律另一人審核 | 包括admin／專案擁有者，提交者不得確認自己的版本 | 職責分離更嚴格，但只有一位有權者時會無法完成 |

A的自行確認仍須建立完整回報、核准人／時間、self_approved標記與稽核，通過相同Gate／授權／交易檢查；不是恢復直接PATCH done。介面必須讓管理者明確選取，一般送出仍進待審；不能自動核准。權限於審核當下重驗；本項已定案，仍待完整G1／G2通過才實作。

### 已確認：協作可見範圍（D61，2026-10-08採A）

共同規則：僅同公司且具can_manage_project的管理者可新增／移除協作人員與部門。協作只作用於明確指定節點，不自動繼承到父、子或兄弟節點；不可見父節點沿P2a可見根呈現，不補查祖先名稱。管理者只能對可見節點設定協作。

| 方案 | 加入協作部門後取得協作權限的人 | 取捨 |
|---|---|---|
| A（已採用）指定人員與部門主管 | 明確加入的協作人員，以及被加入協作部門的主管；同部門其他成員不自動取得 | 沿README F6最小可見範圍，需參與的其他成員逐一加入 |
| B（未採用）整個協作部門 | 明確加入的協作人員，以及被加入協作部門的所有成員與主管 | 部門共同作業較方便，但會讓更多人讀到任務內容 |

兩方案都只因協作授予該節點與其紀錄的讀取、寫筆記及相關附件操作資格；不因協作授予改狀態、送完成回報、審核、改派或metadata編輯。已因其他身分取得的權限仍適用；readonly即使被加入仍不得寫入。附件的容量、移除與回報附件鎖定依D62，本項不是無限制檔案操作授權。

「我的任務」擴充為本人負責或依本方案取得協作權限的task，去重並標示負責／協作；搜尋與總覽沿更新後的可見集合計算。階段的協作不把其子任務加入列表。移除協作或部門成員／主管變動後，每次API重新計算；若仍有原本讀取權則保留，否則不得再讀取紀錄或下載附件，不依舊前端快取授權。這是正式版對README「必要上層摘要」的明確取捨：維持P2a不補查隱藏祖先。

### 已確認：筆記與附件（D62，2026-10-08採A）

推薦沿README F11保留紀錄，並把正式檔案儲存規則明確化：

- 可見且非readonly的節點可操作者、專案管理者、D60審核者及D61協作者可新增筆記／上傳一般附件；一般可見但無上述資格者只能讀。只有筆記作者且當下仍有寫入資格可編輯，保留修訂稽核，不提供筆記刪除；管理者不能代改他人筆記。
- 檔案可附在節點、筆記或回報。允許PDF、PNG／JPEG、TXT／CSV、DOCX／XLSX／PPTX與ZIP；其他類型拒絕。檔名與類型須驗證，不因副檔名便宣稱內容可信；一律授權下載，不提供瀏覽器內嵌預覽、不在伺服器執行或解壓縮檔案。
- A（已採用）：單檔上限10 MB，沿README F11。B（未採用）：單檔25 MB，適合較大的成果文件；其餘規則相同。實作採十進位MB（10,000,000／25,000,000 bytes），UI和API一致。
- 兩方案均建議每公司初始總容量1 GB（1,000,000,000 bytes），含軟刪除與未關聯的已上傳檔案；上傳時顯示剩餘容量，超額拒絕且不留部分檔案。容量可由主機設定提高，但本期不提供配額管理UI或自動刪檔釋放空間。
- 一般附件可由上傳者或該專案管理者在仍有寫入資格時軟刪除，保留檔案／稽核，停止一般列表顯示與下載；所有已提交回報引用的附件不可刪除，包含退回版本。筆記附件依一般附件規則。已提交回報的文字與附件引用不可編輯。
- 使用主機持久化volume、隨機storage key、SHA-256與DB中繼資料。上傳／關聯失敗不送出不完整回報；磁碟滿、DB失敗與並行配額檢查須有測試。DB和檔案無共同交易，具體暫存、失敗清理與恢復機制在G2列明，不假設兩者天然原子。
- 下載每次檢查公司、節點可見性與軟刪除狀態，不提供公開URL；撤銷權限後禁止新下載，不能宣稱能收回已下載的副本。備份／恢復須同時涵蓋DB與檔案volume。

D62已由人類選A，採用上述筆記與附件整組規則；這是規格決策，不代表已實作或完成驗收。

## 4. 已確認的本期邊界（D63，2026-10-08採A）

人類已明確選A，以下為本期範圍。

### A：聚焦回報與協作（已採用）

| 項目 | 具體規則 |
|---|---|
| 回報對象 | 所有kind=task可回報，含有子任務的task，各自獨立審核，不自動更動父子狀態；phase／舊project根不送完成回報，可在紀錄頁彙總可見後代紀錄，不洩漏隱藏節點或計數 |
| 回報表單 | 結果為達成／部分達成／未達成，加必填成果說明與實際完成日、選填附件。確認代表接受這份結案結果，三種結果均可由有權者確認為done。舊任意result原樣顯示，不回寫；自訂欄位與模板欄位快照延至P2c另訂 |
| 完成後重開 | 只有可見且具can_manage_project的管理者可填必填理由把done重開為doing；保留所有已核准回報，後續送出新增版本。不能透過一般status PATCH重開；有待審回報時禁止重開／另改狀態 |
| 跳過 | 管理者可填必填理由，對可見單一todo／doing任務執行略過；無待審回報、通過P2a祖先Gate才可成功。不連動子樹。一般成員不可直接PATCH skipped；已skipped只由管理者填理由恢复doing，原回報／稽核不刪。跳過申請、Gate覆寫及批次子樹跳過本期不做，另列後續範圍 |
| 階段狀態 | phase保留P2a手動狀態及Gate語義，UI標明其為階段狀態；task的review／done受D59控制。project根維持既有唯讀UI，不新增操作 |
| 審核中心 | 顯示目前有權審的待審回報與有權核准的Gate，分開列示；Gate保持原授權與行為，不因D60擴權。失去權限後不得以舊列表進行審核 |
| 稽核 | 先按公司與節點可見性過濾，再搜尋／分頁；一般使用者只讀可見節點的業務事件，無node_id事件僅admin可讀。回傳安全欄位投影及顯示名稱，不把任意歷史payload或帳號直接放到一般UI；不得因篩選洩漏隱藏節點數量 |

一般狀態API的相容性調整見§5轉換矩陣；上述權限變化須API強制，不能只隱藏按鈕。非readonly管理者與有權執行者的一般todo／doing操作仍需按最終矩陣驗證，不讓其覆寫review／done／skipped流程。

### B：本期一併加入流程擴充（未採用）

採A其餘規則，但把自訂回報欄位／送出快照及成員跳過申請→管理者核准／退回也納入P2b。需追加欄位管理、申請狀態、權限與隔離驗收Task，定稿前再具體確認其規則；不表示已授權Gate覆寫或子樹批次操作。交付範圍與開發量較大。

D63是本期功能邊界選擇；A延後項目必須在最終spec／plan及交付README明列，不能宣稱README F11全部完成。

## 5. 共用授權與狀態契約

### 5.1 授權

新增policy由API統一執行：公司→project／node關聯→可見性→動作授權→交易內重驗。不可見／其他公司／不存在均404，可見但不能寫403；readonly任何新增或編輯能力為false。

- `can_view_node`保留P2a既有讀權，另加D61直接協作人員／協作部門主管；同部門其他人不自動加入。不把「專案管理者」默默轉成可讀隱藏節點的新規則。
- `can_submit_report`：kind=task、可見、非readonly且既有`can_work_node`。D60管理者自核仍須同時可送回報；Project.owner不因管理權自動成為任務執行者。
- `can_review_report`：可見、非readonly，且admin／實際Project.owner／負責部門主管／role=reviewer且既有can_work_node；只能處理新流程的最新submitted版本。一般核准或退回端點一律拒絕審自己的版本；自核只走明確的submit-and-approve動作，限D60管理者。
- `can_write_record`：可見、非readonly，且can_work_node／can_manage_project／上述審核身分／D61協作任一資格。筆記編輯還須作者本人。一般附件移除還須上傳者本人或can_manage_project。
- 協作管理沿can_manage_project且節點可見，僅同公司users／departments；不提供跨公司選項、帳號或密碼。可沿既有assignment-options取得非readonly使用者與部門。歷史readonly關聯不提供寫入能力。
- 批次讀取公司內必要資料建policy context；詳情／capabilities／overview／my-tasks／records／reviews／audit及下載一致使用，不逐節點查詢協作表。Gate API授權不變，D60僅適用回報。

### 5.2 task狀態矩陣

| 動作 | 來源 | 目標 | 額外限制 |
|---|---|---|---|
| 一般status PATCH | todo／doing | todo／doing | 沿can_work_node，無新流程待審；任何狀態寫入都驗祖先鏈，開始工作沿P2a pending Gate |
| 送出回報 | todo／doing，或歷史review但無新流程待審 | review | can_submit_report，固定欄位有效、附件完整可關聯、Gate允許、無待審版本 |
| 送出並確認 | 同上 | done | 同時滿足送出權、D60自核資格；建立approved版本與兩個動作的稽核 |
| 確認他人回報 | review＋目前新流程submitted版本 | done | can_review_report，提交者非本人；不接受過時版本 |
| 退回他人回報 | 同上 | doing | 同上、必填意見；原回報改rejected，内容仍不可改 |
| 重開 | done，或歷史review且沒有新流程待審 | doing | 可見管理者、必填理由；歷史review列為「恢復工作」；保留回報，不撤銷歷史核准 |
| 略過 | todo／doing | skipped | 可見管理者、必填理由、無待審、Gate允許 |
| 恢復略過 | skipped | doing | 可見管理者、必填理由；重新查Gate，不遞迴改子樹 |

task直接PATCH review／done／skipped一律409；從review／done／skipped以一般PATCH繞回todo／doing亦409。phase保持P2a狀態契約、project根UI不新增操作。metadata維持D56，可編輯不等於回報或完成；已送回報本身與附件引用不可變。新建子任務不自動重開父任務。

P2a Gate helper依來源status只擋todo開始工作；P2b送回報／自核／重新開啟／恢復略過須另查所屬phase之前的pending Gate，不得把helper直接拿來假裝涵蓋doing等來源。抽出共用祖先／pending查詢，保留P2a原status語義；確認回報亦重查Gate，退回只驗鏈完整性。损毀鏈409。此為避免新完成入口繞過Gate，不新增Gate覆寫。

鎖定Node列後讀取目前報告，再進行狀態交易；相同節點所有新status／lifecycle／submit／review路徑使用同一鎖順序。PostgreSQL真並行驗證不可只靠SQLite。兩次送出／審核只有一次成功，另一個409；網路不確定時UI不自動重送，而重新讀取確認。

## 6. 資料與保留資料migration

新增單一revision `20261008_0003_p2b_collaboration`（Alembic revision id可用`20261008_0003`）接0002；不改既有revision、不重設seed、Demo v6不變。

| 資料 | 欄位與約束 |
|---|---|
| TaskReport擴充 | nullable workflow_version、version、finished_on、reviewed_by／reviewed_at／review_comment，self_approved default false。新資料workflow_version=2，version為節點下新流程的連續正整數；新status限submitted／approved／rejected，result限達成／部分達成／未達成。新增欄位只對新流程要求完整；同公司FK至審核者 |
| 回報唯一性 | 同公司node／version唯一（歷史version null不衝突）；部分唯一索引保證同node至多一筆workflow_version=2且submitted。SQLite單元與PG皆具等價約束 |
| NodeCollaborator | id、organization_id、node_id、user_id或department_id二擇一、created_by／created_at；同公司複合FK，node/user與node/department分別唯一。不改樹結構 |
| TaskNote | id、organization_id、node_id、body、author_id、revision default 1、created_at／edited_at；同公司FK。編輯傳expected_revision，過時409；no-op不增版或追加稽核 |
| Attachment | id、organization_id、node_id、uploaded_by、original_name、storage_key、size_bytes、sha256、state(pending／ready／failed)、created_at、deleted_at／deleted_by；nullable report_id或note_id至多一個。同公司同node關聯以複合FK約束，不容跨node綁定。storage_key唯一，不使用檔名當路徑 |
| AttachmentQuota | organization_id唯一FK、charged_bytes非負。包含ready／軟刪與未清理pending預留量；每公司鎖定此列檢查並扣抵配額 |

舊TaskReport所有新流程識別欄位保持null，既有status／result／summary／ID／user／時間不變；以「歷史回報（未納入新審核流程）」展示，不加入待審、不允許新review端點改它。不改舊Node.status或AuditLog。新version從1起算，不拿歷史筆數冒充版本。歷史review依§5送新回報或管理者填理由恢復；舊done僅明確重開才變更。

migration測試先在0002插入多筆submitted、任意result、done/review任務、日期、owner/dept與audit，升head後逐值與counts比較。新表初始空、配額按公司初始化0（本期此前無附件）；沒有migration附件檔案搬移。只在全新專用測試DB測downgrade，正式回退不自動drop新資料。

## 7. API契約

以下為API內部路徑；前端經`/api`。JSON schemas extra=forbid、文字trim並拒空；summary／note body上限10000字元、理由／審核意見上限2000字元；日期沿P2a YYYY-MM-DD範圍，可過去或未來，不轉時區。新回報finished_on必填。未知欄位／非法日期422。

### 7.1 紀錄、回報與協作

| 介面 | 請求／回應 |
|---|---|
| GET /nodes/{id}/records | scope=self（預設）或subtree；可見節點逐一過濾後，回報／筆記／ready未刪附件依created_at、id穩定排序並分頁。回傳items(type,id,node_id,node_title,安全欄位)、next_cursor，不回隱藏counts。scope=subtree唯讀彙總、visited與同project/company保護 |
| POST /nodes/{id}/reports | {result,summary,finished_on,attachment_ids:[],self_approve:false}；201 report＋node.status。新提交版本鎖定，附件只可同node、本人上傳、ready未刪且尚未綁定；整批檢查再交易關聯 |
| POST /reports/{id}/review | {decision:approved或rejected,comment}；200安全report。退回comment必填，確認可空；已審／過時／舊流程／本人審自己409，無權403 |
| POST /nodes/{id}/lifecycle | {action:reopen或skip或restore,reason}；200 node，依§5矩陣，原因入稽核 |
| POST /nodes/{id}/notes | {body,attachment_ids:[]}；201 note。附件同送回報的上傳者／node／狀態規則 |
| PATCH /notes/{id} | {body,expected_revision}；200 note；僅改內容，不改作者／node／附件引用；稽核保留before／after，無DELETE筆記 |
| GET /nodes/{id}/collaborators | 可見者取得安全users(id,display_name)、departments(id,name)與revision |
| PUT /nodes/{id}/collaborators | {user_ids:[],department_ids:[],expected_revision}；管理者整組替換，去重、查公司；Node加collaborators_revision default 0用於衝突檢查，同Node列鎖內更新與稽核。no-op不增版 |

紀錄中的report回傳版本、legacy旗標、result／summary／finished_on、提交者／審核者display_name、時間／意見、self_approved及安全附件清單；不得傳storage_key或檔案系統路徑。TaskNote及Attachment同樣只投影安全欄位。未綁定一般附件保留在節點，不在送出失敗時任意刪除。

### 7.2 附件與失敗恢復

不用新增multipart依賴：前端以File原始bytes及query `filename`送`POST /nodes/{id}/attachments`，Content-Type為application/octet-stream、Content-Length必填且可信度只作預檢（實際逐chunk計數）；缺長度411，超10,000,000 bytes或公司配額413，不支援格式415，內容／長度不符422。禁止空檔案。正常201安全Attachment。

流程：先授權並鎖Quota預留宣告bytes，新增pending記錄與隨機key→stream到專用暫存（硬性大小上限）並計SHA→檢查實際大小、格式及重新授權→在同volume原子rename後將DB記錄置ready並寫稽核。交易回滾不能假設檔案一起回滾。失敗先區分commit結果：若ready commit可能已成功但回覆遺失，須以新交易鎖定並重讀持久Attachment；讀到ready或已綁定回報／筆記即保留檔案和配額，回讀結果供使用者確認。只有確認仍pending且本次upload已結束，才嘗試清除其temp/final；確定檔案不存在後才釋放預留並標failed。無法確定DB狀態或清理結果時保留檔案與charged_bytes，不把連線例外等同rollback，避免刪掉已成功附件。

只允許§3 D62副檔名，拒路徑分隔符、控制字元及超200字元檔名；PDF／PNG／JPEG查檔頭、Office／ZIP檢查容器結構但不解壓縮內容（防巨型metadata、entry數限制）；文字類要求有效UTF-8且無NUL。檢查不是防毒承諾，所有下載Content-Disposition: attachment與nosniff，不提供預覽。使用標準庫完成，不新增套件。

GET /attachments/{id}/download：每次查session、company/node可見、ready且未刪，串流檔案；缺檔503安全提示並記運維錯誤，不曝光路徑。DELETE /attachments/{id}：依D62軟刪200，已綁report一律409；不減配額、不刪實體。GET /nodes/{id}/attachment-quota回公司limit_bytes／charged_bytes／remaining_bytes，僅當下有上傳資格者可讀，不列其他節點檔名。

補一個只處理pending的運維恢復命令：需明確公司/id且停止該stack API後執行，逐項檢查及移除pending對應的專用檔案、更新failed與配額；可重跑，不掃除ready或軟刪檔，不回收歷史附件。無預設自動清理，不對primary跑測試。G2需寫具體安全步驟和恢復測試。

並行上傳、綁定回報與軟刪需鎖Attachment，所有關聯處理按id排序；先Quota再Node再Attachment的全域鎖順序，普通回報／刪除不需要Quota時從Node開始。不要在長stream期间持有DB交易鎖。pending不可讀／綁定；崩潰時不產生可用但未計價的檔案。

### 7.3 審核中心／稽核／現有API

GET /workspace/reviews?kind=report或gate或all&cursor=&limit=：只回當下可審別人的submitted新回報及按原政策可核的pending Gate，分開type，附可見project/node安全標題與capabilities；不列自送待審回報為可自行確認。Gate讀取同時須節點可見，不藉新增中心擴張舊讀權。

GET /audit-logs增加node_id、action、cursor、limit；先授權再篩選分頁。node事件可見者可讀，node null僅admin；未知action用安全摘要不暴露原payload。已知action按白名單映射before/after，筆記修訂可顯示文字但其關聯ID必須安全投影，未知或不可見引用遮蔽；actor只顯display_name／id，不回actor_username。舊契約更動須在文件與測試明列。

新分頁端點limit預設50、1–100，按(created_at,id,type)穩定cursor，invalid cursor422，不依hidden資料生成總數；拒絕以跨公司cursor取資料。overview公式不變，my-tasks納本人負責或D61協作task，新增relations陣列(owned／collaborating)、去重，維持日期null-last排序。不任意新增本人任務分頁。

新capabilities與state_actions由API回傳，前端只用於呈現；Node投影增加record/submit/review/manage-collaborators/lifecycle能力並保留P2a欄位。401清session，403固定無權訊息，404固定找不到，409提示刷新／目前狀態不允許，413／415／422顯示可理解原因，500／503不傳內部例外。

## 8. UI與資料生命週期

- 保留P2a三入口，新增「審核中心」「稽核紀錄」。task詳情頂端有回報卡與「概覽／紀錄」分頁，開task預設紀錄；phase／project根保留工作區並提供可見後代紀錄彙總。不重查不可見祖先。紀錄以分頁追加，區分空結果／錯誤／載入。
- 回報卡顯示目前狀態、最新回報、待審／退回意見與可用操作；上傳全部成功後才能送出。退回後可帶入上一版本內容作新草稿，但明確標示新版本。一般送出與「送出並確認」分開，不能預設自核。
- 所有可寫角色可用筆記及一般附件，作者編輯筆記有衝突提示。協作設定只給管理者；撤銷後刷新詳情／能力與後續overview/my-tasks讀取，失去可見性回安全頁。
- 一般task狀態選單只提供允許todo／doing；完成／審核／略過／重開走對應明確操作，管理者理由表單取消不寫。phase狀態清楚標記不代表子任務完成率。
- 子組件拆ReportPanel、RecordTimeline、NoteEditor、AttachmentList、CollaboratorEditor、ReviewCenter、AuditLogView；共用請求序號及取消保護，不讓App膨脹成單一檔案。替換表單也使舊reload失效，保留P2a兩項race回歸。
- 送出期間防連點，允許導航離開並忽略舊回應；成功但reload失敗只重試GET。網路失敗提示確認结果，不自動重送POST；登入失效清草稿／檔案參照。下載中及上傳進度有可見提示，錯誤不以空列表冒充成功。
- 繁體中文、明確label、鍵盤可提交／取消、焦點回到觸發控制；1280／375無水平溢出，長檔名／長筆記換行，React預設跳脫，不用dangerouslySetInnerHTML。

## 9. 部署、稽核與验收

Dockerfile在USER appuser前以固定UID/GID 10001建立appuser及`/var/lib/projectflow-files`（owner appuser、mode0700），API仍以非root執行。Compose將新files named volume掛到此預先建好的目錄、保留預設copy-up（不可nocopy），使全新volume沿用目錄ownership；需實跑全新volume上傳才算驗證。既有volume重啟不得重置owner或遞迴chmod/chown，UID保持10001；非預期ownership明確報錯，保留資料交由運維處理。測試全新volume與已有檔案volume重啟均可寫且舊SHA不變。files與project名稱分離primary／acceptance；不改既有pgdata／.env，不把檔案提交Git。設定PF_ATTACHMENT_ROOT與PF_ATTACHMENT_QUOTA_BYTES（預設1 GB），缺目錄／不可寫時安全拒絕上傳，不退回其他不持久路徑。Nginx最大body設10,000,000 bytes以上足以通過邊界，API仍執行精確上限；調整上傳相關timeout，測試11 MB拒絕。既有一般讀取逾時契約不得無意放寬。

業務稽核含report.submit／approve／reject、node.reopen／skip／restore、note.create／update、collaborators.update、attachment.upload／delete；同DB交易。未完成的檔案預留屬技術記錄，不當業務成功；失敗無部分回報／狀態／成功稽核。不得記password／session／storage path。

验收必须包括：
1. 兩公司、admin／實際owner／非擁有者project_owner／reviewer範圍／部門主管／member／協作／readonly；D59–D63每項允許與拒絕及DB／audit副作用。
2. todo→送審→退回→新版本→他人確認；管理者明確自核；新／舊review、done重開、略過與恢復；深層Gate和損毀鏈不繞過。
3. 真PG兩連線並行送審／審核／quota／協作替換；不以單執行緒mock當並行證據。
4. 協作撤銷、部門主管更換、隱藏父節點、可見統計、本人／協作去重；所有紀錄／下載／稽核均不洩漏。
5. 10 MB／超限、公司滿額、格式／路徑、未授權、軟刪、回報附件鎖定、寫檔／DB失敗、pending恢復；sha下載一致。
6. 專用PG由0002舊資料升head保留；正常停止／再啟動驗收服務（不seed、不刪volume）核對DB業務值與附件SHA；primary只在G6通過後保留資料升級與健康檢查。
7. API／Vitest／build／隔離Playwright及桌面／手機／鍵盤／console證據，逐Task雙獨立審查及G4完整diff審查。

README／正式開發指南／試用清單／PROGRESS更新，明列自訂欄位、跳過申請、Gate覆寫等未交付。文件draft與schema設計不是GREEN；G3需重跑P2a歷史基準182 API（專用PG另驗）、96 Vitest、9 E2E，再取得各Task真RED。全程不代勾人類試用。
