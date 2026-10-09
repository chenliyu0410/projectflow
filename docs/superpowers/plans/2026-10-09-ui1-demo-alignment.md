# UI1 前端介面對齊 — 精簡規格／計畫

2026-10-09，D67人類指定下一階段改成「前端介面對齊」，排在P2d前。依D65精簡流程；本文件是下一階段的實作範圍，不表示畫面已改版或驗收通過。

## 目標

讓已交付正式版的主要畫面看起來、操作起來接近`projectflow-full-demo.html`。以Demo實際截圖和操作為對照，不能只換配色就宣稱完成；資料、角色、日期、回報、Gate與FS均沿真API。Demo保持原樣，P2d及P2c延後功能不因UI外觀變更而變成已交付。

## 畫面範圍與差異

| 畫面 | 現有差異 | 對齊方向 |
|---|---|---|
| 整體框架 | 正式版頂部header、頁面居中、專案清單偏長 | Demo約252px暖灰側欄、品牌、分組導覽、可捲專案清單、底部真實使用者；主區獨立捲動，手機抽屜／收合導覽 |
| 視覺 | 灰白背景、系統字體、通用按鈕 | Demo米白#F6F4EF、側欄#EFEBE3、深綠#1F5F5B與原狀態色、細邊線、圓角、字級／間距；字體用本機可用中文字體與serif fallback，不新增Google Fonts/CDN |
| 總覽／我的任務 | 偏資料清單 | Demo統計卡、專案卡／進度條、任務列表與篩選層級；僅真實可見資料，沿done/(task-skipped)，不加假指標 |
| 專案工作區 | 樹、詳情與操作縱向堆疊 | Demo麵包屑、標題／操作列、節點導覽、總覽／紀錄／時程／前置切換、下一層任務卡；桌面分區、手機單欄，保持選定節點及動作 |
| 回報／筆記／附件 | 既有功能已齊，視覺較簡單 | Demo完成卡、紀錄卡、狀態標籤及表單布局；權限／鎖定／退回提示清楚，既有內容不截掉 |
| 時程／模板／審核／稽核 | 與主框架樣式尚未統一 | 共用Demo標題、工具列、卡片、空/載入/錯誤狀態；時程保留日週月、拖曳／手機替代，不新增排程規則 |

未實作文件／營運／AI模組如出現在Demo導覽，標示「尚未提供」且不導向假資料；不模仿Demo切換角色／公司、重置資料、假通知／AI連線或ERP同步。登入維持真session；是否收合與畫面選擇是展示狀態，不更改DB。

## 實作與允許檔案

僅web/src/App.tsx、types.ts、styles.css、components既有WorkspaceShell／WorkspaceOverview／MyTasks／NodeWorkspace／NodeEditor／ReportPanel／RecordTimeline／NoteEditor／AttachmentList／CollaboratorEditor／TimelineView／WorkflowLibrary／DependencyPanel／DependencyGraph／ReviewCenter／AuditLogView，以及新共用UI元件（web/src/components/ui/）。保持api.ts介面不變；如缺真資料先說明，不自行造API或假值。

測試可調web/src既有相關*.test.tsx與web/e2e既有*.spec.ts，新增web/e2e/visual-alignment.spec.ts供畫面走查。只適配結構／文案斷言，不能移除原功能、Gate、公司權限與資料保存斷言。README／PROGRESS／formal-development／mvp-trial-checklist同步；不改api、migration、deploy或Demo。

1. 在獨立測試origin讀Demo（不得清使用者Demo資料），截1280／375主要頁；正式版走查只在隔離15175，列主要畫面差異。
2. 先做共用視覺與側欄，再總覽／任務／工作區／紀錄，最後統一時程與管理頁。維持中文accessible labels與鍵盤操作；重整布局不重寫業務邏輯。
3. 驗桌面／手機主流程、長標題／檔名、空／載入／錯誤／readonly、登入失效；無頁面overflow、按鈕遮擋、非預期console。保存Demo/正式版對照截圖並實看，不能只用DOM說「像Demo」。
4. 一次前端完整回歸（Vitest/build/完整E2E，全部業務寫入只在隔離），此次無後端變更不重跑PG/附件故障矩陣；修正只驗相關部分。一位獨立審查者合併視覺符合度與基本功能檢查。
5. 更新文件與真實限制，ff-only合併；只更新15173 web映像，保留API/DB/files/env、不seed；部署健康／靜態產物檢查，D50 push main並核對。人類試用簽核不代勾。

完成標準：主要畫面能以對照圖說明布局／配色／資訊層級已對齊，現有操作仍可用。這一階段是介面對齊，不宣稱尚未實作的Demo全功能一致。
