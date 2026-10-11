# F1-PO 採購明細、部分收貨進度與單據狀態

使用者2026-10-12指示：以「完成一條真實業務流程」為主線，先開發採購明細＋部分收貨進度＋單據狀態。延續F1-INV／F1-WORK的庫存交易，讓採購單清楚呈現「訂多少、到多少、還差多少」。

**範圍**
- 明細：每張採購單最多50列；每列選既有物料／資源紀錄、訂購數量（正數，最多3位小數）、單位、備註。同一物料在同一張單只列一次。整份明細以版本號保存，他人已修改時拒絕覆蓋。
- 進度：每列顯示訂購／已收／未收與列狀態；單據「收貨狀態」由系統計算：未建立明細／待收貨／部分收貨／已收齊／已結案。原「狀態」欄位維持人工文字，不被覆寫。管理角色在採購列表可看到收貨狀態與已收齊列數。
- 收貨：有明細的採購單只能收明細內物料，單位須與明細一致，累計不得超過訂購數量（超收拒絕；實際多到貨須先修改訂購數量再收）。收貨流水記錄明細ID，並與已收數量、庫存餘額、稽核同交易更新。無明細的舊採購單沿用原自由收貨，不從自由文字推算明細；建立明細前的收貨列出筆數但不計入明細進度。
- 修改限制：已有收貨的明細不可刪除、不可換物料或單位，訂購數量不可低於已收；明細單位須與該物料既有庫存單位一致。
- 結案：管理角色填原因人工結案（例如供應商短交或取消），結案後禁止收貨與修改明細；可填原因重新開啟。全部收齊時狀態自動為「已收齊」，不需另外結案。

**權限與一致性**：明細、進度、結案／重開與收貨限管理者／專案負責人，與F1-INV一致，避免機密物料或數量外洩；一般角色維持原營運唯讀。API每次強制公司、分類與可見性。所有寫入先鎖公司列再鎖單據，與既有庫存記帳同鎖序；收貨UUID冪等規則不變，重送不重複累加。

**延後**：一般角色查看進度（需處理機密物料遮罩）、單價／金額、逐列交期、退貨與沖銷、收貨後自動建立驗收任務、工單產量、ERP。

**資料**：migration 0017新增`purchase_orders`（版本、結案原因／人員／時間）與`purchase_order_lines`（訂購／已收千分量，CHECK已收≤訂購），`inventory_movements`新增nullable `line_id`與公司複合FK（只允許收貨）。舊資料全保留，不自動產生明細、不seed；已有明細、結案或明細流水時拒絕降級。

**允許檔案**：`api/app/models.py`、`api/app/main.py`、`api/app/routes/inventory.py`、`api/app/routes/operations.py`、新`api/app/routes/purchasing.py`、新`api/app/services/purchase_service.py`、0017 migration；`web/src/api.ts`、`InventoryPanel.tsx`、`OperationsManager.tsx`、新`PurchaseOrderPanel.tsx`、`styles.css`；相關測試（新`api/tests/test_purchase_lines.py`、`test_health.py`、`test_migrations.py`、新`web/src/purchase.test.tsx`、`inventory.test.tsx`、新`web/e2e/purchase.spec.ts`）；README／PROGRESS／本計畫。無新依賴。

**驗收**：建立採購→兩列明細→分批收貨（部分收貨→已收齊）→超收拒絕→結案後收貨與修改拒絕→重新開啟→重新整理後進度與流水一致；同UUID重送只入帳一次；真PG併發收貨不超收；跨公司／一般角色拒絕；migration保留舊流水並拒絕有損降級。相關API、全前端Vitest、build、1280／375 E2E（隔離15175）；依WORKFLOW §14一次獨立唯讀審查。備份正式DB／files後遷移部署15173並核對原資料保留；依D50 ff-only合併與push。
