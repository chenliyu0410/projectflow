# UX-CHILD：時程新增與位置保留

使用者要求在協作者本機分支檢查各專案／帳戶的時程子任務新增、拖曳及位置感，完成後提出其餘介面改善建議。

- 分支：`feature/ux-child-modules-navigation`。不合併、不推送、不部署他人的服務；本輪直接指示優先於歷史 D50。
- 權限維持後端既有規則：管理員或該專案負責人可新增；待確認、已完成、已略過、里程碑不可新增子任務。
- 修正：逐項說明新增限制；拖曳前可選擇新增位置；新增表單清楚顯示父層；時程新增以對話框呈現，保留背景；資料更新保留刻度、篩選、收合與捲動；點葉節點維持時程／相依圖分頁；顯示層級與上一層；觸控點時程條有效。
- 不增加帳戶權限、不修改資料結構、不改 Demo、不實作模板拖曳或大幅重構。
- 允許檔案：`web/src/App.tsx`、`web/src/api.ts`（時程不再重建後，成功重載須重設寫入狀態）、`web/src/components/{TimelineView,NodeWorkspace,NodeEditor}.tsx`、`web/src/styles.css`、`web/src/child-creation.ts`；相關前端測試、新增 `web/src/child-navigation.test.tsx`、`web/e2e/child-navigation.spec.ts`、`api/tests/test_child_creation_matrix.py`；本文件、`README.md`、`docs/PROGRESS.md`、`docs/ux-child-review.md`。
- 步驟：重現與資料包權限矩陣 → 補失敗測試 → 修正 → 前端回歸與建置、相關後端測試、隔離瀏覽器桌面／手機驗證 → 一次唯讀獨立審查 → 留本機分支交付。
- 矩陣使用儲存庫去敏資料包的所有帳戶、同公司各專案、可見節點；驗證新增回傳碼且回滾測試寫入，另查跨公司拒絕。實際他人運行中資料不在本機，不宣稱已測。
- 驗收：可用新增按鈕打開正確父層表單；不可用項目有原因；拖曳帶入正確父層／日期；取消零寫入；新增成功仍在原時程；底層時程點選／返回可識別；手機無頁面水平溢出。
