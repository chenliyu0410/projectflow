# UI2 既有展示專案補齊（資料操作）

人類要求將模板套入目前專案，另明確要求移除waa。本次不是新增套用模板的UI功能，不改API／前端／schema。

- 成貓主食罐正式版：套食品開發流程，沿用同名既有頂層階段，保留原task與一切內容。
- 連接器新產品正式版：電子NPI五階段，筆電專屬task調整為連接器結構／模具／端子／接觸電阻測試；原task保留。
- 新任務使用2026-10-09起算模板相對日，todo與pending Gate，不偽造完成進度；指派既有專案owner。
- waa：備份後只刪該專案及其單一project root；若多出其他內容即中止，不級聯刪未知資料。
- 維護腳本以精確公司／專案名稱範圍、預覽預設、明確apply、單一交易、project鎖、稽核及穩定ID防重複；先隔離測試與唯讀獨立審查，再備份primary及執行。保留其餘rows／files／env。
- 允許檔：deploy/populate_showcase_projects.py、api/tests/test_showcase_project_fill.py、本計畫及README／PROGRESS。資料腳本相關測試完整跑一次，不重跑未改動UI/API全套。D50 ff-only與push。
