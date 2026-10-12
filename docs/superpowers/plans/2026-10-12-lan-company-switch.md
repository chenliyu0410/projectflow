# LAN-SWITCH：區網試用也能切換公司（短規格／計畫）

> 精簡流程（WORKFLOW §14／§14.1）。人類2026-10-12問「有辦法一個帳號就切換公司嗎」，選擇方案A：「好，照 A 做」。

## 目標

用 `python deploy/start.py --lan` 開放區網試用時，管理員從 `http://<這台電腦的IP>:15173` 登入後，也能用左下現有的「切換公司」在六家展示公司之間切換。

## 範圍

- 新增 API 環境變數 `PF_SHOWCASE_LAN`。只有它和 `PF_SHOWCASE_MODE` 都是 `true` 時，展示切換才不限 Host 是本機。展示身分的 session 在區網也有效；關閉 `PF_SHOWCASE_LAN` 後，區網的展示 session 會照舊失效。
- `deploy/start.py`：`--lan` 時帶 `PF_SHOWCASE_LAN=true`，否則一律帶 `false`，不沿用 shell 或 `.env` 的殘留值。驗收環境不能加 `--lan`，所以永遠是 `false`。
- `deploy/docker-compose.yml`：API 加 `PF_SHOWCASE_LAN: ${PF_SHOWCASE_LAN:-false}`。
- 文件：`docs/formal-development.md` 的同網域試用段落、README 開頭說明。

## 不變

- 只有管理員能切換；非管理員照舊 403。跨來源 Origin、`sec-fetch-site: cross-site` 照舊拒絕。
- AI 模型設定照舊只限本機（`api/app/routes/ai.py` 不改）。
- 不改前端；切換選單文字「切換公司（本機展示）」維持原樣。
- 不是「一個帳號屬於多家公司」：切換後的身分是該公司的「展示管理者」。

## 資料變更

無 migration、不 seed。API 容器會因環境變數改變而重建，資料 volume 保留。

## 允許修改的檔案

`api/app/showcase.py`、`api/app/auth.py`（若需要）、`api/tests/test_showcase.py`、`deploy/start.py`、`deploy/docker-compose.yml`、`api/tests/test_deployment.py`、`docs/formal-development.md`、`README.md`、`docs/PROGRESS.md`。

## 步驟

1. 先寫測試跑出 RED：
   - 兩個旗標都開時，從區網 Host 登入 `yu`：`/auth/me` 帶 showcase、切換回 200、切換後的 session 在區網仍有效；關掉 `PF_SHOWCASE_LAN` 後該 session 回 401。
   - 只開 `PF_SHOWCASE_LAN` 但沒開 `PF_SHOWCASE_MODE`：照舊 404。
   - 區網開啟時，跨來源仍 403、非管理員仍 403。
   - start.py：`--lan` 帶 `PF_SHOWCASE_LAN=true`，預設強制 `false`；compose 的 API 有 `PF_SHOWCASE_LAN`。
2. 實作到 GREEN，跑 showcase 相關 API 測試、`test_deployment.py`、auth 相關測試。
3. 一次唯讀獨立審查。
4. ff-only 合併 main。
5. `python deploy/start.py --lan` 重啟（不 seed），核對 DB 容器未重建、health ready，並從區網 IP 的 `/api/auth/me`（未登入 401）確認服務正常。
6. 依 D50 push。

## 驗收情境

- 自動測試涵蓋區網切換成功、旗標關閉時拒絕、權限與來源檢查不變。
- 本機 127.0.0.1 照舊能切換。
- 區網實際切換由人類或試用者在瀏覽器確認（AI 不在區網 IP 輸入密碼）。
