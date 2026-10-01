export const meta = {
  name: 'pf-status',
  description: 'ProjectFlow 唯讀健康檢查：核對 docs/PROGRESS.md 與 git、測試的實際狀態，回報下一步',
  whenToUse: '接手或開工時；懷疑進度看板與實際不一致時。不改 repo；會用 127.0.0.1 跑一次測試頁（會清掉該 origin 的 Demo 資料，不影響 localhost）。',
  phases: [{ title: 'Check', detail: '看板 vs git／ledger，以及實際跑測試' }],
}

const BASE = `專案：ProjectFlow，repo 就是目前工作目錄（git）。
必讀：AGENTS.md、docs/WORKFLOW.md（§0、§5、§8、§9、§12）、docs/PROGRESS.md（進度看板，唯一依據）。
這是唯讀檢查：不可修改、搬移或建立任何檔案；不可 commit、checkout、建立分支；不可 push。
說明文字用繁體中文，識別字、路徑、SHA 照原樣。`

const STATUS = {
  type: 'object',
  properties: {
    consistent: { type: 'boolean', description: '看板與 git／ledger 一致' },
    branch: { type: 'string' },
    head: { type: 'string', description: '短 SHA 與主旨' },
    workingTreeClean: { type: 'boolean' },
    currentItem: { type: 'string', description: '例如「W1 子任務置頂回報卡（📋）」' },
    nextTask: { type: 'string', description: '下一個要做的 Task 或關卡' },
    nextAction: { type: 'string', description: '照 WORKFLOW 和 PROGRESS §2 排程規則，接手者下一步具體要做什麼' },
    discrepancies: { type: 'array', items: { type: 'string' }, description: '看板與實際不符之處，附證據' },
    pendingHuman: { type: 'array', items: { type: 'string' }, description: '目前會擋住進度的 D 編號與問題' },
    notes: { type: 'string' },
  },
  required: ['consistent', 'branch', 'head', 'workingTreeClean', 'currentItem', 'nextTask', 'nextAction', 'discrepancies', 'pendingHuman', 'notes'],
}

const TESTS = {
  type: 'object',
  properties: {
    ran: { type: 'boolean' },
    sum: { type: 'string', description: '#sum 的原文，例如「全部通過 44/44」；沒跑就寫原因' },
    branch: { type: 'string', description: '測試時所在的分支' },
    baseline: { type: 'string', description: '目前分支 PROGRESS 記錄的基準' },
    matchesBaseline: { type: 'boolean' },
    failures: { type: 'array', items: { type: 'string' } },
    consoleErrors: { type: 'array', items: { type: 'string' } },
    notes: { type: 'string' },
  },
  required: ['ran', 'sum', 'branch', 'baseline', 'matchesBaseline', 'failures', 'consoleErrors', 'notes'],
}

phase('Check')
const [status, tests] = await parallel([
  () => agent(`${BASE}

任務：核對進度看板與實際狀態是否一致。
1. 執行以下指令：
   - \`git status --short\`
   - \`git branch -a -vv\`
   - \`git log --oneline -20\`
   - \`git log --oneline origin/main..HEAD\`
2. 讀 docs/PROGRESS.md 的「▶ 現在」、§2 佇列、目前工作項目的 Task 表，以及 §6。
   - 如果「▶ 現在」指向某個 feature 分支，用 \`git show <分支>:docs/PROGRESS.md\` 讀那個分支上的版本，不要 checkout。
3. 逐項核對：
   - 標成 ✅ 的 Task：它的 commits 要存在（\`git cat-file -e <sha>\`），而且是祖先（\`git merge-base --is-ancestor\`）。
   - 「分支」欄寫的分支要存在。如果不存在，對照 WORKFLOW §12 判斷是哪一種中斷。
   - 「最新程式 commit」之後，是否還有沒記錄的程式 commit：執行 \`git log --oneline <最新程式 commit>..HEAD -- projectflow-full-demo.html tests\`。
   - 「認領中」是否有殘留。過期規則見 WORKFLOW §9。
   - Task 已經有 commit，但看板還沒打 ✅：這屬於中斷，照 WORKFLOW §12 處理。
   - working tree 有未提交的改動，或有 untracked 檔案（\`.superpowers/\` 除外）。
   - 本機 ledger \`.superpowers/sdd/progress.md\` 如果存在：看它第一行 \`Plan:\`，屬於哪一份 plan？是否和目前工作項目一致？不一致的話，依 WORKFLOW §7 應該先歸檔。
4. 依 WORKFLOW §0、§8、§12 和 PROGRESS §2 的排程規則，寫出接手者下一步具體要做什麼。被人類決定卡住的項目列在 pendingHuman。

回傳結構化結果。每個 discrepancy 都要附證據（指令輸出或 file:line）。`, { label: 'progress-vs-git', phase: 'Check', schema: STATUS }),

  () => agent(`${BASE}

任務：照 docs/WORKFLOW.md §5 實際跑一次瀏覽器測試，並回報結果。
- 先執行 \`git branch --show-current\`，填進 branch 欄位。
- **伺服器**：
  - 已經有伺服器在跑：先 \`curl.exe -s http://127.0.0.1:8000/AGENTS.md\`（PowerShell 必須寫 curl.exe），第一行要以 \`# AGENTS.md\` 開頭。確認是這個 repo 才沿用；不是的話就不要動它，ran=false，並在 notes 說明。
  - 沒有伺服器：用 Bash 在背景啟動 \`python -m http.server 8000 --bind 127.0.0.1 >/dev/null 2>&1 & echo $!\`，記下 PID。
- **瀏覽器工具**：如果是 deferred，用 ToolSearch 載入 \`select:mcp__Claude_Browser__navigate,mcp__Claude_Browser__javascript_tool,mcp__Claude_Browser__read_console_messages\`。
- **跑測試**：
  - 打開 \`http://127.0.0.1:8000/tests/records.html?t=<目前時間戳>\`，輪詢 \`#sum\`，直到它不再以「執行中」開頭（最多 60 秒）。
  - 讀 \`#sum\` 和 \`#out\` 裡的失敗行。
  - 測試數和 \`tests/*.test.js\` 裡的 \`await T(\` 數量對不上，或新測試一直失敗時，照 §5 第 5 點 reload iframe，再讀一次。
- **檢查 Demo**：打開 \`http://127.0.0.1:8000/projectflow-full-demo.html\`，讀 console 的錯誤（onlyErrors）。
- **比較基準**：讀**工作目錄裡**的 docs/PROGRESS.md「▶ 現在」的「測試基準」來比較，因為這才對應目前 checkout 的程式碼。
  - 如果目前不在「▶ 現在」指向的 feature 分支上，在 notes 註明「未在 <分支> 上測試」。這種情況不要算成回歸。
- **收尾**：只有伺服器是你啟動的才關掉，用你記下的 PID，在啟動它的同一個 shell 關。不要修改任何檔案。`, { label: 'run-tests', phase: 'Check', schema: TESTS }),
])

const s = status || {}
const t = tests || {}
const failedAgents = [!status && 'progress-vs-git', !tests && 'run-tests'].filter(Boolean)
log(`看板一致：${!status ? '未知（檢查 agent 沒有回應）' : s.consistent ? '是' : '否'}｜測試：${!tests ? '未知（測試 agent 沒有回應）' : `${t.sum || '未執行'}${t.matchesBaseline ? '（符合基準）' : '（與基準不符或未執行）'}`}`)
return {
  summary: {
    branch: s.branch,
    head: s.head,
    currentItem: s.currentItem,
    nextTask: s.nextTask,
    nextAction: s.nextAction,
    tests: t.sum,
    testsMatchBaseline: t.matchesBaseline,
    consistent: s.consistent,
    workingTreeClean: s.workingTreeClean,
  },
  failedAgents,
  discrepancies: s.discrepancies || [],
  pendingHuman: s.pendingHuman || [],
  testFailures: t.failures || [],
  consoleErrors: t.consoleErrors || [],
  notes: [s.notes, t.notes].filter(Boolean),
}
