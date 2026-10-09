# UI2 全模板進行情境

人類要求所有模板都有像Demo的進行情境。12套catalog加原2套公司模板及1套複本（共15套）逐一對應五公司專案，沿用食品開發／電子NPI兩既有專案，其餘13套新增明確「展示」專案，不改任何既有業務rows。

新專案經既有instantiate建立完整模板／日期／Gate／FS；完成第一階段並核准Gate，第二階段首項由展示執行者送審，其餘依真FS阻擋；另加獨立「專案協調與風險追蹤」進行中task，避免繞過模板FS硬造平行狀態。原4節點簡版模板補排程，若無剩餘todo則另加待審完成才解鎖的「成果驗收與結案準備」。各新案有成果回報、待審、進行中筆記、已完成階段與進行階段，所有內容標示展示情境。

以第二階段開始日對齊2026-10-09，讓日期涵蓋過去與未來。專案名依產業案例命名；模板數量不變，並非將模板本身改成執行資料。既有兩案不覆寫，包含人類後續進度。

僅本機展示旗標下可跑維護腳本，預設rollback／顯式apply；各公司row lock、穩定audit marker防重複；全部同一transaction。新增3個member展示執行者（其餘兩公司已存在），隨機不可知密碼，只有新案待審任務指派，專用管理者可真審核。

允許deploy/populate_all_showcase_projects.py、api/tests/test_all_showcase_projects.py、本計畫、README／PROGRESS。不改API/UI/schema/Demo。一次相關隔離測試與唯讀獨立審查，primary完整備份、apply、原row逐值／files/env保留核對，五公司畫面抽驗，ff-only與D50push。
