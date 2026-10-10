# UI5：可展示版本執行計畫

2026-10-11，依D80授權及D81展示優先收斂。本文件是目前唯一UI5執行範圍，已移除被取代的三批交付要求；舊版留Git歷史。下一個AI直接實作，不再規劃或重問方向。

## 目標與停止條件

沿既有Demo布局，補齊文件、資料、營運及AI的可操作預覽，串通一個食品案例。既有任務規劃器、回報審核、附件與權限維持真功能。

以下全部達成即交付並停止：展示主路徑可重複走完；1280桌面與375手機可操作；預覽明確且不寫正式資料；相關測試及一次獨立審查完成；15173更新並附短展示步驟與限制。不接著做F1／F2。

## 必做內容

| 區域 | 最小可展示內容 | 不在本次完成門檻 |
|---|---|---|
| 文件 | 文件卡、詳情、兩個示例版本切換、一個簡單文字編輯預覽 | 正式儲存、文件上傳、核准與Office編輯器 |
| 資料 | 本層關聯卡、子層來源、跳至示例營運詳情及返回 | 正式建立關聯、資料驅動任務狀態 |
| 營運 | 食品七分頁均可瀏覽；供應商→採購→工單串通列表、詳情及一個狀態操作；原料／配方／追溯提供固定示例，ERP顯示未連線說明 | 完整配方編輯、匯入精靈、ERP模擬引擎、七套CRUD |
| AI | 週報與風險兩個固定示例快捷、訊息詳情、政策／路由說明及一筆遮罩稽核示例 | 自由問答、六個快捷全部分支、真模型、真政策設定、建立任務 |

其他四公司保留既有功能與資料；本次預覽顯示符合該公司情境的明確空狀態，不另做四套示例。未支援的動作清楚說明，不能可點卻無反應或回報假成功。

## 實作邊界

- 靜態示例與React記憶體狀態，使用preview識別碼，不綁真實節點ID。預覽入口與內容持續標示「展示預覽」，示例內導航可保留狀態；離開預覽、切公司、登出或刷新即清除。
- 不寫localStorage、IndexedDB或正式DB，不呼叫業務寫入API、不傳到外部。AI僅固定示例，不讀真任務產生回答；文字編輯只用「套用至預覽」。
- 不修改Demo、後端、資料結構或既有業務規則；不新增套件、通用多產業引擎或可配置框架。React沿用文字跳脫；既有API權限、附件與稽核保持原狀。
- Demo參照：viewDocs／openDoc、viewData／linkCard、pagePetfoodOps、pageAIGov、renderChat／aiAction。正式入口在NodeWorkspace、WorkspaceShell及CopilotPanel，目前尚未實作上述頁面。

## 執行順序與檔案

先核對git狀態和PROGRESS，已有進度就續做；無feature時在主checkout開唯一feature/ui5-demo-ready。依序做文件／資料→營運→AI；這是開發順序，不是三次交付。先打通主路徑，再修阻塞。

- 可修改web/src/{App,types,styles}對應tsx／ts／css，以及components/{WorkspaceShell,NodeWorkspace,CopilotPanel,NavIcons}.tsx。
- 可新增web/src/preview/{fixtures,types}.ts與components/{PreviewBoundary,DocumentPreview,LinkedDataPreview,OperationsPreview,AIGovernancePreview}.tsx；只建立用得到的檔案，不為抽象拆檔。
- 測試：web/src/ui5-preview.test.tsx、web/e2e/ui5-preview.spec.ts；直接受影響的web/src/{App,planner}.test.tsx及web/e2e/visual-alignment.spec.ts。
- 交付文件：本計畫、README、PROGRESS、formal-development、mvp-trial-checklist。只更新變更所需段落，不另寫重複規格、報告或新D編號。

## 驗證與交付

1. 展示路徑：進專案→安排任務→回報審核→文件版本→資料關聯→採購／工單詳情→AI週報或風險示例→返回真工作區。業務寫入測試只在隔離環境。
2. 跑build、相關Vitest、1280／375展示E2E及一條既有回報審核冒煙；驗預覽零業務寫入、切公司／登出清除、手機無遮擋。選有代表性的Demo畫面對照，不逐頁三尺寸拍圖，不追像素一致。改共用邏輯時按影響擴測，不機械跑全部API／歷史PG。
3. 整個UI5一次唯讀獨立審查；只擋主路徑失效、資料／權限問題、明顯不可用與真假誤導。修正只驗受影響情境；小間距、少見邊界、歷史minor留後續。
4. ff-only合併，純前端只更新web服務（不啟動相依服務、不seed、不執行migration），保留API／DB／附件／env；驗健康與入口。依D50發布main並核對SHA。若意外需要後端／儲存變更，停止擴張，另定範圍。
5. 一次交付紀錄附入口、短展示步驟、真功能／預覽清單和限制。所有通過只記實跑結果；工程走查不代替人類試用簽核。
