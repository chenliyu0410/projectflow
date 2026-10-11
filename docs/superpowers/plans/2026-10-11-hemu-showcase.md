# 禾沐食品公司展示資料

人類已確認食品公司完整資料，並明確要求匯入供操作且保留原資料。此授權涵蓋必要匯入與入口修改，不重問方向。

- 新增獨立公司hemu，保留五家既有公司及所有列值；不改schema、不執行seed或migration。
- 8部門、12名具名人員及1個展示管理帳號、4專案與具名任務、相依、待審／退回／完成回報。真核心資料走既有服務／授權規則與稽核；新增組織與人員由本機專用維護匯入建立，隨機不可猜登入秘密。
- 公司背景、供應商、原料、採購、工單與文件以完整虛構資料集提供可切換瀏覽的展示；尚無後端的營運／文件操作明示預覽、離開即清除。另將資料摘要保存為新增公司專案根節點筆記，重載仍可查閱。不宣稱真AI／ERP或營運CRUD。
- 固定2026-10-11案例，進度以系統實算為準，不強行填入先前概念稿百分比。
- 匯入用單一transaction、穩定標記；公司key或標記碰撞拒絕；重跑不改任何使用者修改。預設dry-run，顯式apply才提交。
- 允許：api/app/showcase.py；deploy/populate_hemu.py；api/tests/test_hemu_showcase.py；web/src/preview/hemu.json；web/src/components/HemuPreview.tsx；web/src/components/PreviewBoundary.tsx；web/src/App.tsx；web/src/hemu.test.tsx；必要既有showcase測試的公司數斷言；README與PROGRESS及本計畫。
- 步驟：資料集／匯入與入口→隔離匯入保值、rollback、冪等與權限測試→build、展示互動測試與獨立唯讀審查→備份現有DB與附件並記hash→匯入／僅更新api、web→逐列比對舊資料與附件、入口驗證→ff-only與D50發布。
- 不修改舊公司任何業務資料，避免登入／切換測試改動舊session；線上驗證使用新公司臨時session並於結束移除。備份存在忽略的.superpowers/hemu中，秘密不入Git。
