@AGENTS.md

# Gemini CLI 專用補充

- 你沒有 superpowers skills，也沒有 Claude 的瀏覽器工具。請照 docs/WORKFLOW.md 這兩節做：
  - §11：流程的手動對應做法，以及用 headless Playwright 跑測試。
  - §4.3：審查者提示範本，用來交給另一個 session 審查。
- `.claude/workflows/` 只有 Claude Code 能用，不要執行。
- Commit trailer 寫你實際使用的工具和模型，例如 `AI-Assisted-By: Gemini CLI <模型>`。不要照抄 plan 裡的 Claude trailer。
