# 五家公司完整展示資料追加

人類已明確授權生成、匯入並保留原資料。目標為food/electronics/events/software/construction五既有公司，每家四個產業專案、部門／具名人員、待審退回與前置阻擋，以及公司／合作單位／資源／單據／執行紀錄／文件展示。禾沐與所有既有資料不改。

- 只追加，不變更任何舊列值。新增部門使用獨立明確名稱，遇同名／同username／專案title碰撞拒絕整批；不強行修改或重新指派舊資料。
- 復用禾沐業務服務匯入邏輯，五公司同一交易；穩定匯入標記、mode檢查、PG鎖、dry-run／apply。重跑只讀標記，不覆蓋使用者修改。部署前完整DB／附件備份與env hash，提交前舊列比對、提交後再驗。
- 真專案、任務、相依、回報／審核、筆記與稽核可操作保存。營運單據與文件保持明示預覽；關聯用明確ID，不假稱ERP或AI已連接。公司快照存入新專案根筆記。
- 食品原UI5示例保留返回入口，不修改舊fixtures；其餘產業有自身分類、金額與日期，所有內容虛構。六家公司切換清除暫存。維持既有AI功能範圍。
- 允許檔案：deploy/populate_hemu.py、deploy/populate_industries.py；web/src/preview/industries.json、web/src/components/IndustryPreview.tsx、web/src/components/PreviewBoundary.tsx；api/tests/test_industry_showcases.py及必要hemu測試；web/src/industries.test.tsx及web/e2e/ui5-preview.spec.ts必要舊入口更新；README、PROGRESS、本計畫。
- 驗證：資料一致性與跨連結、產業獨立性、舊列保值、回報審核、阻擋、冪等、晚期錯誤rollback及公司API隔離；build與相關前端測試；真PG隔離驗證；五家公司1280／375唯讀瀏覽與預覽操作，零業務寫入、切換清除。一次独立唯讀審查。只部署web；維護匯入在既有api容器執行，不seed／migration／重建DB。
- Git：主checkout唯一feature、ff-only、D50發布，秘密與備份留忽略目錄。人類試用不代簽。
