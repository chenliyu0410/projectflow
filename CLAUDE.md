@AGENTS.md

# Claude Code 專用補充

## 開工與推進

- **開工**：先跑 `/pf-status`，或手動照 AGENTS.md §2 讀 `docs/PROGRESS.md` 的「▶ 現在」。
- **推進工作**：用 `/pf-next`，它會照看板推進一步。這一步可能是下面其中一種：
  - 下一個 Task：實作 → 兩位審查者 → 最多兩輪修正 → 記錄並 commit
  - 整體審查與驗收
  - 依 D2 在本地把分支 ff 合併進 main
- `/pf-next` 的參數：
  - `all`：連續推進，直到工作項目完成或遇到阻塞。
  - `dry`：只預覽，不做任何變更。
- 這些流程定義在 `.claude/workflows/`，內容對應 docs/WORKFLOW.md 的 §2–§5 和 §12。

## Skills 怎麼用（WORKFLOW §10）

- **📋 以上的工作項目**：已經有 spec 和 plan，**不要**再跑 brainstorming 或 writing-plans，直接用 `/pf-next`。
  - plan 開頭的「REQUIRED SUB-SKILL」也改用 `/pf-next`。
- **brainstorming**：只在 G1（⬜ → ✏️）用，而且要和人類一起做。
- **手動執行 plan**（`superpowers:subagent-driven-development`）：
  - 開始前，先照 WORKFLOW §7 把舊的 `.superpowers/sdd/` 歸檔。
  - 每個 Task 除了寫 ledger，也要照 WORKFLOW §3 第 9 步 commit `Progress: <WID> task N done`。
- **worktree**：使用者的設定是**不用 worktree**（D2）。`superpowers:using-git-worktrees` 照這個設定，直接在主 checkout 用 `git checkout -b` 開分支。
- **合併**：照 WORKFLOW G5 的步驟做（`--ff-only`，不 `git pull`）。不要用 `superpowers:finishing-a-development-branch` 的合併選項。

## 瀏覽器

- 用內建的 Claude_Browser 工具。可以用 `preview_start` 啟動 `demo`，結束時用 `preview_stop`。
- 如果 8000 埠已經被這個 repo 的伺服器占用（確認方式見 WORKFLOW §5 第 1 點），直接 `navigate` 到 `http://localhost:8000/...`。
- 同一時間只能有一個 agent 使用瀏覽器。

## 其他

- **Commit trailer**：照 session 的 attribution 提示寫，模型名稱寫實際執行的模型。
- **記憶**：進度和決策寫在 `docs/PROGRESS.md`，不要寫進 Claude 的 memory。memory 只記使用者的偏好。
