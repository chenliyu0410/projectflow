# FORMAL-INDEX：正式文件與附件索引（隔離交付）

依使用者明確要求接續正式文件與附件索引，仍只用隔離測試版、不得影響原資料。套用 WORKFLOW §14 短規格／計畫，由本 session 執行，一次獨立唯讀審查。

## 範圍與資料保護

- 索引來源是目前環境的 Document 最新版本，以及 ready 且未刪除的 Attachment；保留原始二進位檔、文件版本與業務表，不新增 migration，不修改上傳／刪除流程。
- 新增 `formal-v1` 資料集及獨立 SQLite FTS5 衍生索引；按資料庫身分與公司分檔，管理者手動「更新文件索引」，暫存完整建立後原子替換。更新失敗保留舊索引；相同公司同時更新拒絕重複執行。
- 本階段功能同時要求 `PF_ACCEPTANCE_MODE=true`、`PF_AI_FORMAL_INDEX=true`，預設關閉。服務啟動器只在既有隔離 DB／獨立檔案區明確設定；不接原本正式 DB 或 Docker。
- 每次 status／檢索／預覽／開啟引用都即時查業務來源及原有 can_view_project、can_view_node、協作者／部門主管政策。索引中舊權限不當作授權。新版已上傳、節點已刪、附件已刪／不可用或索引 fingerprint 與來源不符時停止回傳舊資料；更新索引後才查新版。尚未實作歷史文件索引。
- 語意分級尚無正式欄位：全部正式來源保守按機密，沿用全本地閘道。API 不接受任意 company_id；不把正式資料標成 synthetic。
- 解析 UTF-8 TXT／CSV、有文字層 PDF、DOCX 本文與表格、XLSX 儲存格值（不計算公式），不追外部連結、不執行 Office 程式。圖片／掃描PDF、ZIP／PPTX 等列為略過並說明；有檔案大小、頁數、解壓後 XML 及字數限制，不靜默截斷整份文件。
- 分段索引，引用含來源類型／版本／段落編號，可開啟索引段落。檢索及模型預覽只用當下可見有效來源；無權限時連檔名、計數與錯誤理由都不洩漏。
- UI 提供正式資料集、可見索引狀態（已索引／待更新／略過）、管理者更新按鈕、來源／版本標記。保留舊教材、舊SQL、工單清單及預覽清理行為；正式資料只提供文件問答。

## 允許檔案

- 新增 `api/app/ai/formal_index.py`、`api/app/ai/extractors.py`、`api/tests/test_ai_formal_index.py`
- 修改 `api/app/ai/service.py`（抽出共用RAG回答）、`api/app/routes/ai.py`
- 修改 `web/src/ai.ts`、`web/src/components/CopilotPanel.tsx`、`web/src/ai.test.tsx`
- 新增 `web/e2e/ai-formal-index.spec.ts`
- 修改本文件、`docs/PROGRESS.md`、`docs/ai-assistant.md`、`README.md`
- repo外 `output/rag-starter-acceptance/`：隔離備份、測試檔案區、啟動器、操作說明及驗證證據；可透過原有上傳API新增明確標記的虛構測試文件，不覆寫原資料。

## 實作與驗收

1. 寫核心測試並確認失敗：開關預設拒絕、TXT/PDF/DOCX/XLSX、附件、增版後舊內容失效、撤回權限／跨公司／刪除、top-k不被無權資料占據、失敗保留舊索引、正文不入稽核。
2. 實作來源盤點、解析／段落索引、原子發布與即時權限；沿用RAG閘道及引用API。
3. 新增UI入口與更新操作。只在已驗證的隔離環境加入虛構範例，保留原資料與教材hash，展示文件上傳→索引→預覽／檢索→原文段落。
4. 一次適用完整回歸：AI及文件／附件API、前端全量、tsc/build、桌面1280／手機375；獨立唯讀審查。小修只驗受影響部分。
5. 更新文件／待辦與本機commit；不merge／push／正式部署。真模型、pgvector、OCR、歷史索引、排程自動更新另階段處理。
