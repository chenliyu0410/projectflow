# UI2 產業模板與本機展示公司切換 — 精簡規格／計畫

2026-10-09，承接UI1。人類要求模板像Demo豐富、公司切換在左下，並明確選擇「展示模式一鍵切換公司（僅本機開啟，明確標示展示身分）」。依D65，不啟動P2d。

## 交付範圍

- 增加食品、電子、活動、軟體、工程五種產業的完整可用範本（至少12套），含階段／任務、相對日、Gate與硬性FS；以Demo既有流程名稱／內容為主要來源。日期為可編輯的建議，不表示法規或工期承諾。
- 模板庫提供產業分類、名稱搜尋、階段與任務數、說明及流程預覽。保留公司模板與原有新增／編輯／複製；選用範本可建立真實公司模板，再用既有流程建立專案。不把Demo不支援的欄位冒稱已保存。
- 初始化時僅新增缺少的展示公司、專用展示使用者與各產業範本；不覆寫舊公司、帳號、專案、模板或附件。可重複執行且不重複新增／恢復使用者改過的模板。
- 左下公司選單顯示公司／產業與展示身分；真後端換發HttpOnly session並撤銷舊session，切換後回總覽、清除上一公司的前端資料／表單。一般頁面選公司立即切換；有開啟表單時先提示內容將離開，取消不切換。角色／公司隔離沿既有API。
- 本機展示設定預設false；僅loopback URL可用且需已登入的指定展示公司管理者或专用展示帳號。一般member/reviewer/readonly拒絕，沒有匿名登入／通用密碼／任意使用者指定。專用展示session在關閉模式後失效。部署只開目前loopback stack，不開LAN。

## 允許檔案

api/app新增showcase服務／catalog資料、routes/auth.py、routes/workflows.py、auth.py、schemas.py與相應api/tests；web/src/App.tsx、api.ts、types.ts、styles.css、components/WorkspaceShell.tsx、WorkflowLibrary.tsx與新增WorkflowCatalog.tsx、相關既有/新增unit與e2e；deploy/docker-compose.yml、nginx.conf、README、PROGRESS、formal-development與mvp-trial-checklist。不改Demo、不改既有seed行為、不改migration或DB schema、不新增依賴。

## 執行與驗收

1. 抽取／整理Demo產業流程，新增可驗證catalog、冪等新增命令；只增缺項，schema沿P2c。
2. 先測本機／關閉模式／角色拒絕／舊token撤銷／公司隔離，再實作展示session切換；檢查關閉模式使展示token失效。
3. 完成卡片分類／預覽／選用與左下公司切換；完整真功能、錯誤／取消與跨公司快取清理，桌面1280與手機375截圖實看。
4. 一次完整API/Vitest/build/E2E；失敗只重驗相關部分，無migration與附件邏輯變更不重跑PG/附件故障矩陣。一位唯讀獨立審查。
5. 備份並比對既有DB rows/files/env；只新增明列展示資料與環境旗標，發布API/web，健康與保留資料驗證，ff-only、D50 push main。人類試用不代勾。
