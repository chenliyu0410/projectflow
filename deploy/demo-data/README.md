# 展示資料包（去敏）

從本機試用環境（15173）匯出的業務資料，用來在另一台電腦還原同一套展示內容。資料皆為虛構展示資料。

- **包含**：公司、部門、成員帳號（帳號、顯示名稱、角色）、工作流模板、專案、任務、前置、關卡、回報、筆記、營運資料、採購明細、工單計畫、庫存與流水、文件與附件（有引用的檔案放在 `files/`）。
- **不包含**：登入 session（token）、稽核紀錄、通知、密碼雜湊。還原後所有帳號的密碼為 `demo-<帳號>`，例如 `yu` 為 `demo-yu`。
- 因為沒有稽核紀錄，還原後「活動與稽核紀錄」為空，也無法復原匯出前的結構操作。
- `manifest.json` 記錄 migration 版本、各表筆數與 SHA-256；還原時逐表核對，內容被改過就拒絕。

## 還原到另一台電腦

在 repo 根目錄逐行執行。第一行建立空的本機環境並執行 migration，**不要加 `--seed-demo`**；還原只接受完全空的資料庫，已有資料會拒絕覆蓋。

```powershell
python deploy/start.py
python deploy/demo_data.py import
```

完成後開啟 http://127.0.0.1:15173 ，以 `yu`／`demo-yu` 登入。資料包的 migration 版本須與程式版本相同；程式較新時先用相同版本還原，再執行 `python deploy/start.py` 升級。

## 重新匯出

```powershell
python deploy/demo_data.py export
```

會以目前 15173 的資料覆寫本目錄的 `manifest.json`、`tables/`、`files/`（本說明檔保留）。提交前請確認內容仍只有展示資料。
