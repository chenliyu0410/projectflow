# TP-F 權限與協作：短規格與計畫

日期：2026-10-10。人類要求「下一步是 TP-F，開始開發」。依D70啟動；人類回覆「照建議做」，D78及本計畫已核准。

## 原始碼對照與差距

| 項目 | Demo | 正式版現況／本批 |
|---|---|---|
| 跳過申請 | skipTask／decideOverride：理由、主管核准、子樹跳過、恢復 | 僅管理者生命週期操作；新增申請、核准／退回與子樹恢復 |
| 覆寫 | submitBlock將前置永久overridden；閘門獨立覆寫 | 硬性前置、人工條件、子節點與閘門均會阻擋；新增具範圍與理由的例外證據 |
| 部門 | addDept／updateDept／deleteDept；限admin，主管須是成員，使用中不可刪 | GET /departments唯讀；新增管理介面與寫入API |
| 成員權限 | deptPanelHTML與角色權限表 | NodeWorkspace只有節點協作與capabilities；補專案層、部門管理與權限說明 |
| 待我指派 | 部門主管名下未指派任務 | my-tasks只有owned／collaborating；補主管可見與指派權限 |
| 負載 | 未完成任務數 | overview已有可見人員／部門open_count；沿用並提供任務清單篩選 |
| 通知 | 我的任務顯示audit.notes最近八筆，並非個人收件匣 | 新增同公司個人站內通知與已讀狀態 |

已閱讀上述Demo函式及正式版permissions、node_policy、record_policy、workspace、departments；尚未做瀏覽器同尺寸對照，實作前補齊。正式版用詞沿D72。

## D78已核准規則

1. **申請與核准**：任務負責人、所屬部門主管、該專案管理者可附理由申請跳過；唯讀與僅協作者不可。admin或該專案負責人可直接附理由跳過／覆寫；部門主管可審核自己部門的他人申請，跨部門子樹交專案管理者。不因擁有project_owner或reviewer角色便取得所有專案核准權。申請者不能核准自己的申請，管理者直接操作另記為直接核准。每節點同類只能有一筆待審；退回必填理由，核准時重驗權限與目前狀態，過期申請結案不執行。
2. **子樹跳過與恢復**：跳過任務及未完成子孫，已完成／已略過不動；待確認回報退回並保留證據，恢復時回進行中。保存本次實際改動的狀態快照；整組恢復只允許管理者，若其後有相關業務修改或上層已關閉，409並說明，不覆蓋新資料。仍保留舊版無快照的單節點恢復。這是生命週期操作，與TP-B結構復原分開。
3. **覆寫是當次例外**：前置／人工條件／子節點未完成可附理由例外放行指定動作，保留被略過的規則及當時狀態，不永久停用前置、不將人工條件假標已確認。申請核准後只執行所申請動作，阻擋集合有新增或變更則409要求重送。完成任務仍須完成回報；不能由覆寫直接把任務改完成。回報送出與核准分別重驗，必要時各附理由。閘門使用獨立覆寫入口並留理由，一般前置覆寫不得繞過閘門。公司隔離、可見性、唯讀、資料結構與已關閉上層等限制不可覆寫。不自動改變上層狀態。
4. **部門與指派**：僅admin管理同公司部門名稱、成員及主管；主管須為有效且非唯讀的部門成員。名稱去頭尾空白且同公司不可重名。移除現任主管的成員資格須同時更換／清空主管。仍被任務（含軟刪）、協作、成員或模板版本引用時不可刪，不默默清空引用。一般成員擔任主管時可看自己主管部門任務並指派同公司有效非唯讀人員，不因此取得其他部門或隱藏祖先資料。唯讀帳號不因歷史主管設定取得寫入權。
5. **成員、權限與負載**：專案頁顯示專案負責人及可見任務的負責人／協作人員，節點頁沿用既有協作設定；角色表說明範圍，實際按鈕依API capabilities。不新增帳號、角色編輯或自訂ACL。待我指派只列自己主管部門、未指派且未完成的任務。負載只統計可見未完成任務數，含未指派，非工時／產能估算。
6. **站內通知**：指派新負責人、申請送審、核准／退回及原本受阻任務解鎖時建立收件人通知；排除操作者自己。通知收件人須同公司且有查看來源權限；讀取時再次檢查，失去權限或來源刪除後不回傳內容或計數。支援分頁、未讀數與標記已讀；不提供Email／推播／ERP、逾期排程或歷史通知補發。通知與業務操作同交易，解鎖只在blocked→unblocked時發送並避免同次交易重複。

## 資料、API與允許檔案

- 新migration `20261010_0010`：申請／決策與跳過快照、當次覆寫證據、個人通知；同公司複合外鍵、待審唯一性及必要索引。舊資料保持原值，不seed、不重建；有新業務資料時拒絕有損降級。既有Gate是否需擴充狀態由實作沿其約束處理，覆寫證據另存。
- 新增申請、直接覆寫、決策與恢復API，整合workspace/reviews；departments新增POST／PATCH／DELETE及成員設定；workspace/my-tasks新增awaiting_assignment關係，新增通知查詢／已讀API。錯誤不揭露隱藏節點名稱、數量或人員。
- 鎖定專案後再鎖申請／節點，以一致順序完成核准、子樹狀態、回報、通知及稽核；重送與併發核准不得重複執行。沿用既有服務，不新增依賴。
- API允許：api/app/models.py、schemas.py、permissions.py、main.py；routes/{departments,projects,reports,workspace,workflows,audit_logs}.py；services/{node_policy,record_policy,report_service,dependency_service,condition_service,tree_service,workflow_service,template_service}.py；新增routes/{collaboration,notifications}.py、services/{collaboration_service,notification_service}.py及上述migration。
- 前端允許：web/src/{App,api,types,styles}對應tsx／ts／css；components/{NodeWorkspace,NodeEditor,ReviewCenter,ReportPanel,MyTasks,WorkspaceOverview,WorkspaceShell,AuditLogView}.tsx；新增components/{CollaborationDialogs,DepartmentManager,MemberPermissions,Notifications}.tsx。
- 測試允許：新增api/tests/test_tp_f_collaboration.py、test_tp_f_notifications.py、test_tp_f_departments.py；更新test_migrations.py、test_health.py及與上述API直接相關的既有權限／回報／工作區測試；新增web/src/collaboration-advanced.test.tsx與web/e2e/collaboration-advanced.spec.ts，更新既有workspace／review／planner／records測試中改變的契約；deploy/verify.py新增PG驗證。
- 文件允許：本文件、docs/PROGRESS.md、README.md、docs/formal-development.md、docs/mvp-trial-checklist.md。Demo產品與測試不修改。

## 實作順序與驗收

1. 核准D78後主checkout開唯一feature/tp-f-permissions-collaboration；補Demo與正式版1280／1440／375畫面對照。
2. migration、權限及部門／指派；測試一般主管的可見範圍、readonly、跨公司、成員／主管一致性、引用中刪除及稽核。
3. 申請／核准／直接覆寫／子樹恢復；測試必填理由、隱藏子樹、自己核准、狀態變動、回報結案、FF與人工條件、獨立閘門、同時核准一次及失敗零部分寫入。
4. 通知與前端；完整走指派→回報／跳過申請→主管核准→通知已讀→恢復，及負載篩選。驗證取消、失敗保留輸入、重載失敗不重複寫入、手機／鍵盤與長文字。
5. 一位唯讀獨立審查者及一次隔離完整回歸：PG migration／併發、API、Vitest、build、E2E；修正後只重跑受影響案例，保留真實摘要及exit code。
6. ff-only合併；15173更新前備份DB／附件／env，migration後原列／原值與附件SHA比對、健康與唯讀操作確認；依D50發布main並核對遠端SHA。人類試用不代簽、LAN未授權。
