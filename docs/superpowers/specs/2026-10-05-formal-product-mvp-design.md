# Formal Product MVP Design

> 2026-10-08 恢復規劃：本文件從 `paused/p0-formal-product-plan` 保留的 `5ced30f` 帶回，依 D49 在最新 main 基礎上續修。這是正式版範圍草稿，文件合併不代表批准 P0/P1 實作；AGENTS／WORKFLOW 的 Demo 規則尚未切換。

## 1. 背景

ProjectFlow Demo 驗證軌已完成主要功能架構：F1–F11、W1、W2、W3、W5、W6 都已在 Demo 層級完成，且 `tests/records.html` 基準為 `全部通過 174/174`（2026-10-08 實測）。W6 的 v6 容器有五個固定展示公司，localStorage key 仍為 `projectflow-demo-v2`；這不是正式後端多租戶。

人類在 2026-10-05 指定正式產品版的初步標準：

- P0 技術骨架與規則：約 1–2 天。
- React 前端 + FastAPI + PostgreSQL 基礎版：約 1–2 週。

本 spec 的目的，是把「正式版第一個可內部試用的 MVP」切成清楚階段，作為後續 PR 與 implementation plan 的依據。

## 2. 目標

正式產品 MVP 要把單檔 Demo 轉成可維護、可部署、可多人使用的內網 Web 系統，但第一版不追求完整 AI、完整 ERP、完整 RAG。

MVP 完成時，應能做到：

- 使用 React + TypeScript 前端取代單檔 Demo UI 架構。
- 使用 FastAPI 提供後端 API。
- 使用 PostgreSQL 保存專案、節點、部門、工作流、關卡、回報與稽核資料。
- 使用 Docker Compose 在本機或內網主機啟動 Web、API、DB。
- 保留 Demo 已驗證的核心產品能力：Project、Node、Workflow、Gate、Dept/RBAC、Reports/Logs。
- 提供基本登入與角色切換，足以驗證權限規則。
- 提供測試與種子資料，讓團隊能穩定迭代。

## 3. 非目標

以下不在 P0/P1 MVP 第一輪範圍內：

- 真正串接公司 ERP。
- 真正串接 AD / LDAP。
- 真正部署 Ollama / vLLM。
- 真正啟用雲端 LLM。
- 完整 RAG 文件問答。
- 完整附件版本管理與文件線上編輯。
- 取代 ERP 或處理財會／稽核正式流程。

這些保留到 P2 之後。

## 4. 分期

### P0：正式版技術骨架與規則，1–2 天

目的：建立可執行、可測、可部署的正式版骨架，不實作完整業務功能。

交付：

- `web/`：Vite + React + TypeScript。
- `api/`：FastAPI。
- `deploy/`：Docker Compose 啟動 web、api、postgres。
- `docs/`：正式版開發規則、環境變數、測試方式。
- CI 或本地測試命令雛形。
- Demo 到正式版的資料模組切分決策。
- 依已批准的 W6 spec §13 保留公司邊界要求：業務模型需有 `organization_id`／公司邊界，後續 API、資料庫查詢、檔案儲存與權限檢查必須強制隔離。不得把 Demo 的前端切換或角色選單當成正式授權。P0 先記錄邊界，P1a 的業務 API 出現時就要實作並驗證隔離。

### P1a：資料模型與後端核心，2–4 天

目的：把 Demo 的核心資料搬成 PostgreSQL schema 與 API。

交付：

- PostgreSQL migration。
- SQLAlchemy 或 SQLModel models。
- Project、Node、Department、Workflow、Gate、Report、AuditLog 的基本 CRUD API。
- 種子資料，至少能重現 Demo 中的核心示例。
- 後端權限檢查雛形：`can_view`、`can_work`。
- 公司邊界測試：已驗證身分不能透過另一公司的記錄 ID、工作流、關聯節點或稽核 API 取得／修改他公司資料；檔案功能實作時採同一邊界。識別值及外鍵的具體設計須在可執行計畫中定案，不能直接假設 Demo ID 全域唯一。

### P1b：React 核心 UI，3–5 天

目的：讓使用者能在正式前端跑通主要工作流。

交付：

- 登入／角色切換雛形。
- 專案清單與專案頁。
- 節點樹與麵包屑。
- 看板四欄與狀態更新。
- 工作流模板列表、從工作流建立專案。
- 階段 Gate 阻擋提示。

### P1c：部署、測試、MVP 驗收，2–3 天

目的：把 P1a/P1b 整合成可內部試用版本。

交付：

- Docker Compose 一鍵啟動。
- API 測試、前端 smoke test、權限測試。
- README 快速開始更新。
- 管理員初始化種子資料。
- MVP 驗收腳本：以 yu、chen、ming 三種角色走完主要流程。

## 5. 驗收標準

P0/P1 MVP 通過時，需滿足：

- 新機器 clone repo 後，可以用文件指令啟動 Web + API + DB。
- 可以登入或切換角色。
- 可以建立專案、查看節點、更新任務狀態。
- 可以從工作流模板建立專案。
- Gate 未通過時，後續階段任務不能被一般操作繞過。
- 不同角色看到的任務範圍符合 Demo 的核心規則。
- 在伺服器執行公司與角色授權；更換前端公司參數或猜測他公司 ID 不得繞過隔離。
- 測試命令有明確輸出，失敗時能定位到 API、UI 或權限層。

## 6. 風險

- Demo 是單檔全域狀態，正式版拆前後端時最容易遺失隱含行為。
- 權限規則複雜，不能只靠前端隱藏按鈕，API 必須重做檢查。
- 工作流 Gate 和 generic 前置覆寫曾有繞過風險，正式版必須把這個案例寫入測試。
- 若一開始就做完整 AI/RAG/ERP，會讓 1–2 週基礎版失焦。

## 7. 建議 PR 範圍

本次依 D49 只恢復 spec、計畫草稿、README 入口及進度看板，檢查後 ff-only 合併回 main；依後續 D50 授權完成一段就推送 GitHub main。不開 PR、不啟動 P0 實作。舊暫停分支只作歷史備查，main 中的規劃文件為後續修訂來源。

下一階段先確認此範圍，再把 P0 拆成符合現行流程的可執行計畫，包含正式軌規則切換、依賴／啟動檔、測試與公司邊界決策；P1a–P1c 仍是後續規劃。原時程是估算，不是本次完成承諾。
