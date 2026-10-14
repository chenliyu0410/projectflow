# PROJECT-DRAWER — 固定專案清單、我的待辦與相依追蹤

2026-10-14 使用者確認獨立 HTML 後要求「開 PR 推上去」；將已確認互動整合至正式前端並更新 PR #3，不合併或部署。

## 範圍

- 專案清單固定在側欄獨立可捲動區，捲軸閒置隱藏。點專案開啟我的待辦抽屜，只有指派給目前帳號／參與協作且未完成、未略過的 task，資料使用既有已授權的 my-tasks API，無新增後端權限。
- 相依圖 hover 追蹤所有前置／後續路徑，click 固定，空白或 Escape 取消；獨立開啟任務按鈕，切換層級清除固定。保留既有前置編輯與拖線。
- 藍色返回按鈕固定於內容頂端，麵包屑同列；返回保持分頁。移除時程重複返回入口。
- 保留正式登入、公司隔離、文件與業務操作。離線資料、mock fetch、展示 AI 回覆及展示標示不納入正式版。無資料庫變更。

## 允許檔案與步驟

1. web/src/App.tsx、components/WorkspaceShell.tsx、DependencyGraph.tsx、DependencyPanel.tsx、NodeWorkspace.tsx、TimelineView.tsx、styles.css：整合並移除離線頁首位移。
2. web/src/*test*、web/e2e/：更新受影響的導覽測試與必要模擬環境，補待辦篩選、相依高亮、返回定位與正式登入驗收。
3. 一次獨立唯讀審查；正式型別、build、前端完整單元與桌面／手機展示路徑。更新 README、PROGRESS，明確路徑提交及推送 PR。

## 驗收

管理者也不擴張為全部待辦；own／collaborator 包含，done／skipped／其他人／僅待指派排除。空狀態、關閉／焦點、手機、返回分頁、前後多跳高亮與不相干支線、固定後 hover 其他節點、切層重設皆驗證。後端功能與資料未更動，不重跑歷史全量 API。
