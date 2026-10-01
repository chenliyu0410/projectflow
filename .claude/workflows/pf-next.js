export const meta = {
  name: 'pf-next',
  description: 'ProjectFlow：依 docs/PROGRESS.md 推進下一步（Task 實作→雙審查→修正→記錄／整體審查／依 D2 合併）；all＝連續到工作項目完成或阻塞；dry＝只預覽',
  whenToUse: '要推進 ProjectFlow 目前的工作項目時。參數：留空＝推進一步；all＝連續執行到整體審查與合併（或遇到阻塞）；dry＝唯讀預覽下一步。',
  phases: [
    { title: 'Orient', detail: '讀看板、檢查認領與分支、Pre-flight、基準測試、決定下一步' },
    { title: 'Implement', detail: 'TDD 實作一個 Task 並 commit' },
    { title: 'Review', detail: 'spec 符合度與品質，兩位唯讀審查者' },
    { title: 'Fix', detail: '修正 Critical／Important，最多兩輪' },
    { title: 'Final review', detail: '所有 Task 完成後的整體審查與驗收' },
    { title: 'Record', detail: '獨立重跑測試、更新 PROGRESS.md 與 ledger、commit' },
    { title: 'Merge', detail: '依 PROGRESS D2 本地 fast-forward 合併並收尾' },
  ],
}

// ── 參數：字串、陣列或物件都接受 ──
const opt = args && typeof args === 'object' && !Array.isArray(args) ? args : {}
const raw = (Array.isArray(args) ? args.join(' ') : typeof args === 'string' ? args : String(opt.mode || '')).trim().toLowerCase()
const DRY = !!opt.dryRun || /(^|[\s-])(dry|preview)\b|預覽/.test(raw)
const ALL = !DRY && (!!opt.all || /(^|\s)all\b|全部/.test(raw))
const MAX_TASKS = ALL ? 12 : Math.max(1, Number(opt.tasks) || 1)
const MAX_FIX_ROUNDS = 2
log(`參數 ${JSON.stringify(args === undefined ? '' : args)} → ${DRY ? 'dry（唯讀預覽）' : ALL ? `all（最多 ${MAX_TASKS} 個 Task）` : `推進 ${MAX_TASKS} 步`}`)

const BASE = `專案：ProjectFlow，repo 就是目前工作目錄（git）。進度看板 docs/PROGRESS.md 是唯一依據；硬性規則在 AGENTS.md §3；流程在 docs/WORKFLOW.md。
說明文字用繁體中文，識別字、路徑、SHA 照原樣。絕對不要 push、force、reset --hard、checkout -- <檔案>、stash drop，也不要改寫已提交的歷史。
不要整份讀 projectflow-full-demo.html（約 28 萬字元）：先 grep 函式名，再用 offset/limit 讀局部。`

const TRAILER_RULE = `commit 訊息結尾空一行，加上 session attribution 指定的 trailer（例如 \`Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\`），模型名稱寫你實際執行的模型。plan 裡寫死的 trailer 不要照抄，也不要重複。`

// ── Schemas ──
const ISSUE = {
  type: 'object',
  properties: {
    severity: { type: 'string', enum: ['critical', 'important', 'minor'] },
    planMandated: { type: 'boolean', description: 'plan 本身規定了這個有缺陷的做法' },
    file: { type: 'string' },
    line: { type: 'string' },
    desc: { type: 'string' },
    fix: { type: 'string' },
  },
  required: ['severity', 'planMandated', 'file', 'line', 'desc', 'fix'],
}

const ORIENT = {
  type: 'object',
  properties: {
    ok: { type: 'boolean' },
    mode: { type: 'string', enum: ['task', 'review', 'final', 'merge', 'blocked', 'idle'] },
    reason: { type: 'string', description: '下一步摘要；blocked/idle 時寫原因' },
    needsRecord: { type: 'boolean', description: 'mode=blocked 且原因還沒寫進 PROGRESS（需要記錄者寫 ⛔ 與 D 編號）時為 true' },
    workItem: { type: 'string', description: '例如 W1' },
    title: { type: 'string' },
    specPath: { type: 'string' },
    planPath: { type: 'string' },
    branch: { type: 'string' },
    commitPrefix: { type: 'string', description: '修正 commit 的前綴，不含「task N fix:」。取自 PROGRESS 該項目的「commit 前綴」，例如 W1＝Subtask report card、W2＝Departments' },
    allowedFiles: { type: 'array', items: { type: 'string' } },
    taskNumber: { type: 'integer', description: 'mode=task/review 時的 Task 編號，其他模式填 0' },
    taskTitle: { type: 'string' },
    taskSubject: { type: 'string', description: 'plan 指定的該 Task commit 主旨（沒有就空字串）' },
    totalTasks: { type: 'integer' },
    baseSha: { type: 'string', description: 'task：目前 HEAD；review：該 Task 第一個 commit 的 parent；final/merge：目前 HEAD（完整 SHA）' },
    headSha: { type: 'string', description: '目前 HEAD（完整 SHA）' },
    mergeBase: { type: 'string', description: 'git merge-base main HEAD' },
    testBaseline: { type: 'string', description: '實際跑出的 #sum；沒跑就寫原因' },
    executionNotes: { type: 'string', description: 'PROGRESS 該工作項目「執行注意」中與這一步相關的條目（全文）' },
    humanQuestions: { type: 'array', items: { type: 'string' } },
    actionsTaken: { type: 'array', items: { type: 'string' } },
  },
  required: ['ok', 'mode', 'reason', 'needsRecord', 'workItem', 'title', 'specPath', 'planPath', 'branch', 'commitPrefix', 'allowedFiles', 'taskNumber', 'taskTitle', 'taskSubject', 'totalTasks', 'baseSha', 'headSha', 'mergeBase', 'testBaseline', 'executionNotes', 'humanQuestions', 'actionsTaken'],
}

const IMPL = {
  type: 'object',
  properties: {
    status: { type: 'string', enum: ['DONE', 'DONE_WITH_CONCERNS', 'BLOCKED', 'NEEDS_CONTEXT'] },
    commits: { type: 'array', items: { type: 'string', description: '<短 SHA> <主旨>' } },
    headSha: { type: 'string' },
    red: { type: 'string', description: 'RED 證據：#sum 原文與失敗的測試名稱（修正輪填重現測試的 RED）' },
    green: { type: 'string', description: 'GREEN 證據：#sum 原文' },
    uiChecks: { type: 'string', description: '做了哪些 UI 實測；哪些沒驗到' },
    concerns: { type: 'array', items: { type: 'string' } },
    reportPath: { type: 'string' },
  },
  required: ['status', 'commits', 'headSha', 'red', 'green', 'uiChecks', 'concerns', 'reportPath'],
}

const REVIEW = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['approved', 'needs_fixes'] },
    spec: { type: 'string', enum: ['compliant', 'issues', 'cannot_verify', 'n/a'] },
    strengths: { type: 'string' },
    issues: { type: 'array', items: ISSUE },
    report: { type: 'string', description: '完整審查文字（Markdown），會存檔' },
  },
  required: ['verdict', 'spec', 'strengths', 'issues', 'report'],
}

const ACCEPT = {
  type: 'object',
  properties: {
    sum: { type: 'string' },
    allPass: { type: 'boolean' },
    checks: {
      type: 'array',
      items: {
        type: 'object',
        properties: { item: { type: 'string' }, pass: { type: 'boolean' }, evidence: { type: 'string' } },
        required: ['item', 'pass', 'evidence'],
      },
    },
    notes: { type: 'string' },
  },
  required: ['sum', 'allPass', 'checks', 'notes'],
}

const RECORD = {
  type: 'object',
  properties: {
    ok: { type: 'boolean', description: '看板已依指示更新並 commit；獨立重跑測試不符或無法完成時為 false' },
    commit: { type: 'string', description: 'Progress commit 的短 SHA 與主旨' },
    nextAction: { type: 'string', description: '與「▶ 現在」一致的下一步' },
    notes: { type: 'string' },
  },
  required: ['ok', 'commit', 'nextAction', 'notes'],
}

// ── 小工具 ──
const flat = (reviews) => reviews.filter(Boolean).flatMap((r) => r.issues || [])
const uniq = (xs) => xs.filter((x, i) => xs.findIndex((y) => y.file === x.file && y.line === x.line && y.desc === x.desc) === i)
const blocking = (reviews) => reviews.filter(Boolean).flatMap((r) => {
  const hard = (r.issues || []).filter((i) => (i.severity === 'critical' || i.severity === 'important') && !i.planMandated)
  if (!hard.length && r.verdict === 'needs_fixes') {
    return [{ severity: 'important', planMandated: false, file: '(review)', line: '', desc: `審查結論是 needs_fixes 但沒有列出阻塞 issue：${String(r.report || '').slice(0, 400)}`, fix: '依審查報告處理' }]
  }
  return hard
})
const planMandated = (reviews) => uniq(flat(reviews).filter((i) => i.planMandated))
const minors = (reviews) => uniq(flat(reviews).filter((i) => i.severity === 'minor' && !i.planMandated))
const J = (x) => JSON.stringify(x, null, 1)

const itemCtx = (o) => `工作項目：${o.workItem}「${o.title}」
spec：${o.specPath}
plan：${o.planPath}
分支：${o.branch}（先 \`git branch --show-current\` 確認；不是這個分支就停下來，回報 BLOCKED）
允許修改的產品／測試檔：${(o.allowedFiles || []).join('、')}（docs/PROGRESS.md 的 Progress commit 與 .superpowers/ 不受此限，審查時不算越界）
commit 前綴：${o.commitPrefix}
PROGRESS 的執行注意：
${o.executionNotes || '（無）'}`

// ── 各步驟的 prompt ──
const orientPrompt = (step) => `${BASE}

你是 controller 的「定位」步驟。先讀 AGENTS.md、docs/WORKFLOW.md 的 §0、§2、§5、§8、§9、§12，以及 docs/PROGRESS.md 的「▶ 現在」、§2、§6 和目前工作項目在 §3 的明細。${DRY ? `
**這是 DRY RUN，必須完全唯讀**：不 checkout、不建分支、不 commit、不搬檔、不改任何檔案（包括認領）。
- 把「本來會做的動作」寫進 actionsTaken，每項前面加「(dry) 」。
- 目前分支如果不是「▶ 現在」指向的分支，表示工作目錄的程式碼不是那個分支的版本：**不要跑測試，也不要抽查錨點**。testBaseline 寫「(dry) 未測：需在 <分支> 上」，mode 照看板判斷，不可以因此判 blocked。
- needsRecord 一律填 false。` : ''}

步驟：
1. 執行 \`git status --short\`、\`git branch -a\`、\`git log --oneline -15\`。
   - working tree 必須乾淨（\`.superpowers/\`、\`.claude/settings.local.json\` 已 ignore）。
   - 不乾淨就 mode=blocked。reason 要列出有變動的檔案，並寫「依 WORKFLOW §12 處理（不可丟棄）」。needsRecord=false。
2. 讀 main 上 PROGRESS 的「▶ 現在」。
   - 如果它指向某個 feature 分支，而你目前不在那個分支：${DRY ? '用 `git show <分支>:docs/PROGRESS.md` 讀那個分支的版本' : '執行 `git checkout <分支>`，然後重讀 PROGRESS'}。
   - 分支不存在時，照 WORKFLOW §12：
     - main 的 HEAD 主旨是 \`Progress: start <WID>\`：${DRY ? '寫進 actionsTaken' : '從 HEAD 執行 `git checkout -b <分支>`'}，接著往下做。
     - 看板是 🟢，而且分支的 commit 已經在 main 上：mode=merge（merge 步驟只做 G6）。
     - 其他情況：mode=blocked，needsRecord=${DRY ? 'false' : 'true'}。
3. 認領檢查（WORKFLOW §9），看「▶ 現在」的「認領中」：
   - ${step === 0 ? '不是空的，而且不是過期的認領（超過 4 小時，且分支在這段時間沒有新 commit）→ mode=blocked，reason 寫「已被 <認領人> 認領」，needsRecord=false。過期的認領可以接管，並把「接管 <原認領>」寫進 actionsTaken。' : '本次 /pf-next 稍早寫入的「Claude（/pf-next）」認領可以忽略。其他人的認領照第一輪的規則處理。'}
4. 依目前工作項目的狀態決定 mode：
   - **📋**
     1. 先確認 \`git branch --show-current\` 是 main，不是就 mode=blocked。
     2. **先做第 5 步（Pre-flight，用 Task 1）和第 6 步（基準測試）**，兩者都通過後才開工。
     3. 依 WORKFLOW G3 第 2 步開工：
        - PROGRESS 有三處改成 🔨：「▶ 現在」、§2、§3 標題。
        - 「▶ 現在」的分支填 <分支>；下一個動作寫「切到 <分支>，照該分支的 PROGRESS 執行 Task 1」；認領填「Claude（/pf-next）／<\`date '+%Y-%m-%d %H:%M'\` 的結果>」。
        - \`git add docs/PROGRESS.md\`，commit \`Progress: start <WID>\`（${TRAILER_RULE}）。
     4. 執行 \`git checkout -b <分支>\`，不要用 worktree。
     5. 準備 SDD 工作區（見下方第 7 步），然後 mode=task，taskNumber=1。
   - **🔨**：找出 Task 表中第一個不是 ✅ 的 Task。
     - 這個 Task 是 ⛔，或「阻塞／待人類」有 D 編號而且 §6 仍寫「待人類」→ mode=blocked，reason 寫出 D 編號，needsRecord=false。**不可以重跑。**
     - 執行 \`git log --format='%H %P %s' <mergeBase>..HEAD\`。如果已經有這個 Task 的 commit（主旨等於 plan 指定的主旨，或是 \`<前綴> task N fix:\`），表示上一次在審查或記錄階段中斷了 → mode=review。baseSha 填這個 Task 第一個 commit 的 parent。
     - 否則 mode=task。
     - 同時核對已經 ✅ 的 Task：它們的 commits 都要存在（\`git cat-file -e\`），而且是 HEAD 的祖先。對不上就 mode=blocked，needsRecord=${DRY ? 'false' : 'true'}。
   - **所有 Task 都 ✅，整體審查還沒完成（🔨 或 🔍）**：
     - 整體審查那一列是 ⛔，或有待人類的 D → mode=blocked，needsRecord=false。
     - 否則 mode=final。
   - **🟢**：
     - 「▶ 現在」寫「等待人類合併」→ mode=blocked，needsRecord=false。
     - 否則 mode=merge。
   - **⬜、✏️、⛔、⏸、✖**，或沒有 📋 以上的項目可做 → mode=blocked，needsRecord=false。reason 寫明需要什麼，例如：
     - brainstorming（要人類參與）
     - 先寫 plan（問題清理型可以用 superpowers:writing-plans，依 WORKFLOW G1 例外）
     - 某個 D 編號
     - 可以照 PROGRESS §2 的排程規則建議下一個可做的項目，但**不要自己開工**。
   - **佇列裡全部 ✅** → mode=idle。
5. **Pre-flight**（mode 是 task，或 📋 開工前）：
   - 讀 plan 的 Global Constraints、該 Task 全文，以及 PROGRESS 的執行注意。
   - 抽查該 Task 要搜尋的程式片段（錨點），確認在目前程式碼裡存在。
   - 衝突如果「執行注意」已經裁決過，就照裁決做。其他無法自行解決的衝突 → mode=blocked，問題寫進 humanQuestions，needsRecord=${DRY ? 'false' : 'true'}。
   - executionNotes 填和這個 Task 相關的條目全文。
   - taskSubject 填 plan 指定的 commit 主旨。
6. **基準測試**（mode 是 task、review、final，或 📋 開工前；merge 不用；DRY 規則見上方）：
   - 照 WORKFLOW §5 跑一次，testBaseline 填 \`#sum\` 原文。
   - 要和目前分支 PROGRESS「▶ 現在」的「測試基準」一致。
   - 不一致時，照 §5 第 11 點分診。確定是回歸 → mode=blocked，needsRecord=${DRY ? 'false' : 'true'}。
   - 伺服器只有你自己啟動的才關掉。
7. **SDD 工作區**（非 DRY，mode 是 task、review、final）：
   - \`.superpowers/sdd/progress.md\` 存在，但第一行 \`Plan:\` 不是這份 plan → 整個 \`.superpowers/sdd/\` 移到 \`.superpowers/archive/<那份 plan 的檔名去掉 .md>/\`。
   - 工作區不存在時，建立 \`.superpowers/sdd/\`，寫入 \`.gitignore\`（內容 \`*\`）和 \`progress.md\`（第一行 \`Plan: <plan 路徑>\`）。
8. **認領**（非 DRY，mode 是 task、review、final）：如果「認領中」不是你，改成「Claude（/pf-next）／<日期時間>」。這個修改**先不 commit**，記錄步驟會一起 commit。📋 開工時已經寫過，就不用再寫。
9. 收尾欄位：
   - headSha 和 mergeBase 照 schema 的說明填。task、final、merge 模式下，baseSha 等於 headSha。
   - mode 是 task、review、final、merge 時 ok=true；blocked、idle 時 ok=false。`

const implementPrompt = (o) => `${BASE}

你是 implementer，只做 plan 的 Task ${o.taskNumber}「${o.taskTitle}」（共 ${o.totalTasks} 個 Task）。
先讀 AGENTS.md §3，以及 docs/WORKFLOW.md 的 §3、§4.1、§5、§6、附錄 C。
${itemCtx(o)}
BASE：${o.baseSha}　目前測試：${o.testBaseline}　plan 指定的 commit 主旨：${o.taskSubject || '（無，用前綴）'}

依 WORKFLOW §3 第 2–7 步：
- **讀需求**：讀 plan 中該 Task 的全文。和程式碼衝突、而且執行注意沒有裁決時，不要猜：status=NEEDS_CONTEXT，寫明衝突點。
- **RED**：照 plan 加入測試，依 WORKFLOW §5 跑測試頁。確認新測試的名稱有出現在 \`#out\`，記下 \`#sum\` 原文和失敗的測試名稱。
- **GREEN**：實作到全部通過。如果 iframe 拿到舊版，照 §5 第 5 點處理。plan 預期的數字和實際不同時，照實寫並說明原因。
- **UI 實測**：有畫面變動時，打開 Demo 實測 plan 指定的流程，console 不能有錯誤。截圖不能用時改用 DOM/JS 檢查，沒驗到的寫進 concerns。改過 viewport 的話，結束前設回桌面。
- **自我檢查**：照 WORKFLOW §4.1。
- **Commit**：\`git add <明確路徑>\`，只加允許清單內你改過的檔案。主旨用 plan 指定的；沒有的話用 \`${o.commitPrefix} task ${o.taskNumber}: …\`。${TRAILER_RULE}
- **報告**：寫到 \`.superpowers/sdd/task-${o.taskNumber}-report.md\`，格式照 WORKFLOW 附錄 C。
- 不要改 docs/PROGRESS.md（記錄步驟會處理）。不要 push。
- 伺服器只關你自己啟動的。之前就在跑的保留。`

const reviewPrompt = (o, kind, base, head, prior) => `${BASE}

你是**唯讀**的${kind === 'spec' ? ' spec 符合度' : '程式品質'}審查者，審查 ${o.workItem} 的 Task ${o.taskNumber}「${o.taskTitle}」。
先讀 AGENTS.md §3 和 docs/WORKFLOW.md §4.1。
不可以修改 working tree、index、HEAD 或分支。**不要使用瀏覽器，也不要啟動伺服器**（另一位審查者同時在跑；需要實測的寫進 issue 的 fix 欄位）。
${itemCtx(o)}
審查範圍：先看 \`git log --oneline ${base}..${head}\` 和 \`git diff --stat ${base}..${head}\`，再讀 \`git diff ${base}..${head}\`。
實作報告：.superpowers/sdd/task-${o.taskNumber}-report.md。**不要相信報告的自述**，以 diff 為準。
${prior ? `上一輪的阻塞問題如下，逐一確認是否修好。仍然存在的要再列一次：\n${prior}\n` : ''}
${kind === 'spec'
    ? `重點：對照 plan 中該 Task 的全文和 spec 的相關章節，找出：
- 漏做（Missing）
- 多做（Extra）
- 做錯（Misunderstood）
另外，測試要照 plan 寫，而且真的有斷言行為。
**從 diff 無法判斷的部分**：spec 填 cannot_verify，並在 issues 加一筆 important，fix 欄寫要怎麼驗證。`
    : `重點有兩類：
- WORKFLOW §4.1 的專案硬性規則：commit()／log()、can()、esc()、繁體中文、不用 CDN、只改允許的檔案、db.v／upgrade()
- 品質：錯誤處理、邊界情況、逐字重複的程式、測試品質、檔案膨脹
只有能說出具體風險時，才去看 diff 以外的程式碼，而且每個風險只做一次聚焦檢查。`}
嚴重度定義照 WORKFLOW §4.1。plan 本身規定了有缺陷的做法時，照實際嚴重度標，並設 planMandated=true。每個 issue 都要附 file:line。
verdict：有任何 critical 或 important，而且不是 planMandated → needs_fixes；否則 approved。
report：完整審查文字，依序寫 Spec Compliance → Strengths → Issues → Assessment。`

const fixPrompt = (o, issues, round, label) => `${BASE}

你是修正者（${label === 'final' ? '整體審查' : `Task ${o.taskNumber}`}，第 ${round} 輪）。先讀 docs/WORKFLOW.md §3、§5、§6。
${itemCtx(o)}
請修正以下阻塞問題（critical／important，不含 plan-mandated）：
${J(issues)}

做法：
- 能寫測試重現的問題，先寫測試跑出 RED，再修到 GREEN（WORKFLOW §5）。
- 最後跑完整測試頁，必須全部通過。
- 不要順手改清單以外的東西。認為某項是誤判就不要改，把理由寫進 concerns。
- commit：\`git add <明確路徑>\`，訊息用 \`${label === 'final' ? `${o.commitPrefix} final review fixes: …` : `${o.commitPrefix} task ${o.taskNumber} fix: …`}\`。${TRAILER_RULE}
- 在 \`${label === 'final' ? '.superpowers/sdd/final-fix-report.md' : `.superpowers/sdd/task-${o.taskNumber}-report.md`}\` 後面附加 \`## Fix round ${round}\`，內容包含 RED/GREEN 證據、改動的檔案和 concerns。
- 不要改 docs/PROGRESS.md，不要 push。伺服器只關你自己啟動的。`

const recordPrompt = (o, data) => `${BASE}

你是記錄者。先讀 docs/WORKFLOW.md 的 §3 第 9 步、§5、§7、§8、附錄 A、附錄 B。
${itemCtx(o)}
本輪資料（JSON）：
${J(data)}

依序執行：
1. **確認分支**：確認目前在 ${o.branch}。如果這個分支還不存在（\`git rev-parse --verify ${o.branch}\` 失敗，例如開工前就被擋下），改在 main 上記錄。
2. **獨立重跑測試**（只在 outcome 是 done 或 final_ready 時做；你是循序執行的，可以安全使用瀏覽器）：
   - 照 WORKFLOW §5 跑測試頁。\`#sum\` 必須是「全部通過 N/N」，而且和最後一次 GREEN（或驗收結果）一致。
   - 不一致時，**不要標 ✅ 或 🟢**：改照 outcome=blocked 記錄，新增 D 編號（「測試結果和實作回報不符」，附上 \`#sum\` 原文），最後回傳 ok=false。
   - 伺服器只關你自己啟動的。
3. **存審查報告**：把每份審查的 report 全文存成 \`.superpowers/sdd/review-<base7>..<head7>-<spec|quality|final>[-r<輪次>].md\`。
4. **寫 ledger**：在 \`.superpowers/sdd/progress.md\` 加一行：
   - 完成：\`Task N: complete (commits <base7>..<head7>, review clean[ after fix round k])\`
   - 阻塞：\`Task N: BLOCKED — <原因>\`
   - 整體審查：\`Final review: <ready|blocked> (<base7>..<head7>)\`
5. **更新 docs/PROGRESS.md**：
   - **outcome=done**
     - 該 Task 改成 ✅。commits 填 \`<base7>..<head7>\`（A..B 的語意，不含 A）。
     - 測試欄保留預期值，後面接實際結果，例如 \`→ 實際 RED 失敗 x/N → GREEN 全部通過 N/N\`。
     - minor 問題加進 §5 OPEN。ID 用 \`${o.workItem}-T${o.taskNumber}-m<k>\`，格式照附錄 B。
     - plan-mandated 問題加進 §6：新的 D 編號，狀態寫「待人類」，並註明嚴重度。
     - 「▶ 現在」：下一個動作改成下一個 Task，最新程式 commit 填 head 的短 SHA，測試基準填這次的實際數字；資料版本有變就一起更新。
     - 如果這是最後一個 Task：該項目改成 🔍（三處：「▶ 現在」、§2、§3 標題），下一個動作寫「整體審查（/pf-next）」。
   - **outcome=blocked**
     - 該 Task（或工作項目，如果還沒開始任何 Task）改成 ⛔。
     - §6 新增 D 編號，寫明問題和選項。
     - 「▶ 現在」：目前工作項目後面加 ⛔，「阻塞／待人類」填 D 編號，下一個動作寫「等待人類回答 Dn」。
   - **outcome=final_ready**
     - 整體審查那一列填 commits 和結論。
     - 驗收清單依 acceptance 的結果打勾。
     - 整體審查的 minor 用 ID \`${o.workItem}-F-m<k>\`。
     - §6 如果還有本工作項目產生、仍寫「待人類」的 D（包括這次新增的 plan-mandated D）→ 維持 🔍 並標 ⛔，「阻塞／待人類」填那些 D 編號。
     - 否則改成 🟢（三處），下一個動作寫「合併（/pf-next，依 D2）」。
   - **outcome=final_blocked**：維持 🔍 並標 ⛔，§6 新增 D 編號，「阻塞／待人類」填這個 D 編號。
   - **交接紀錄**：在 §7 最上方加一筆，格式照附錄 A。日期用 \`date\` 取得，AI 欄寫你實際執行的模型，審查方式寫「獨立（/pf-next）」。§7 只保留最近 5 筆，更舊的刪掉。
   - **認領**：只有 continuing=true **而且** outcome=done 時才保留「認領中」，其他情況一律清空。
6. **commit**：\`git add docs/PROGRESS.md\`，只加這個檔案。訊息依 outcome：
   - done：\`Progress: ${o.workItem} task N done\`
   - blocked：\`Progress: ${o.workItem} blocked\`
   - final：\`Progress: ${o.workItem} final review\`
   - ${TRAILER_RULE}
7. 回傳下一步，必須和「▶ 現在」一致。
   - ok=true 的條件：看板已更新並 commit，而且第 2 步（如果有做）一致。
   - outcome 本身是 blocked 但記錄成功，也算 ok=true。`

const mergePrompt = (o) => `${BASE}

你是合併者，依 WORKFLOW §2 的 G5、G6 收尾 ${o.workItem}「${o.title}」（分支 ${o.branch}）。先讀 docs/WORKFLOW.md §2 的 G4–G6、§5、§6。
**不要使用 superpowers:finishing-a-development-branch**，直接照下面的步驟做。

1. **檢查能不能合併。** 下列任一項成立就**不要合併**：
   - D2 不允許 AI 在本地 fast-forward 合併。
   - PROGRESS 的 Task 列或整體審查列註明「自我審查」。
   - §6 還有本工作項目產生、仍寫「待人類」的 D。
   - 該項目不是 🟢。

   處理方式：在「▶ 現在」寫「⛔ 等待人類合併 ${o.branch}（原因）」，commit \`Progress: ${o.workItem} awaiting merge\`，然後回傳 ok=false。
2. **確認分支狀態。** 如果 ${o.branch} 已經不存在，而且它的 commit 都在 main 上，表示上次中斷在 G5 和 G6 之間，直接跳到第 4 步。
   否則：
   - 確認分支上的 working tree 是乾淨的。
   - 照 WORKFLOW §5 再跑一次測試，必須全部通過。
3. **合併。** 分開執行 \`git checkout main\` 和 \`git merge --ff-only ${o.branch}\`，**不要 \`git pull\`**。
   - 如果無法 fast-forward：先執行 \`git checkout ${o.branch}\` 回到分支，在 PROGRESS 標 ⛔，新增一個 D 編號（需要人類處理），commit，回傳 ok=false。
4. **在 main 上做 G6 收尾。**
   1. 確認 README 已經照 plan 更新。
   2. 該項目改成 ✅，摘要移到 §4。
   3. 「▶ 現在」**每一列都要更新**：
      - 目前工作項目、下一個動作：換成 §2 的下一個項目
      - 分支：改成 \`main\`
      - 最新程式 commit：填合併後的 HEAD
      - 測試基準、資料版本
      - 遠端：執行 \`git log --oneline origin/main..main\` 重算
      - 認領中：清空
      - 阻塞／待人類
   4. 寫一筆交接紀錄。
   5. \`git add docs/PROGRESS.md\`，commit \`Progress: ${o.workItem} done\`（${TRAILER_RULE}）。
5. **刪除分支與歸檔。** commit 完成後才執行 \`git branch -d ${o.branch}\`。然後把 \`.superpowers/sdd/\` 移到 \`.superpowers/archive/<plan 檔名去掉 .md>/\`。
6. **不要 push。** 在 notes 提醒人類：要不要 push 由人類決定（D3）。`

// ── 單一 Task（mode=task 或 review）──
async function runTask(o, continuing, resume) {
  let impl
  if (resume) {
    impl = { status: 'DONE', commits: [], headSha: o.headSha, red: '（中斷復原：沿用既有 commit，未重新實作）', green: o.testBaseline, uiChecks: '（中斷復原，未重新實測）', concerns: ['中斷復原：從審查步驟接續（WORKFLOW §12）'], reportPath: `.superpowers/sdd/task-${o.taskNumber}-report.md` }
    log(`${o.workItem} Task ${o.taskNumber}：偵測到既有 commit，從審查步驟接續`)
  } else {
    phase('Implement')
    impl = await agent(implementPrompt(o), { label: `implement ${o.workItem} T${o.taskNumber}`, phase: 'Implement', schema: IMPL })
  }

  let head = impl ? impl.headSha : o.headSha
  const fixes = []
  const allReviews = []
  let outcome = 'done'
  let reason = ''
  let prior = ''
  let lastBlock = []

  if (!impl) {
    outcome = 'blocked'
    reason = 'implementer 沒有回應（可能已部分修改，請依 WORKFLOW §12 檢查）'
  } else if (impl.status === 'BLOCKED' || impl.status === 'NEEDS_CONTEXT') {
    outcome = 'blocked'
    reason = `implementer 回報 ${impl.status}：${(impl.concerns || []).join('；')}`
  } else {
    for (let round = 0; ; round++) {
      phase('Review')
      const reviews = await parallel([
        () => agent(reviewPrompt(o, 'spec', o.baseSha, head, prior), { label: `review:spec ${o.workItem} T${o.taskNumber}${round ? ` r${round}` : ''}`, phase: 'Review', schema: REVIEW }),
        () => agent(reviewPrompt(o, 'quality', o.baseSha, head, prior), { label: `review:quality ${o.workItem} T${o.taskNumber}${round ? ` r${round}` : ''}`, phase: 'Review', schema: REVIEW }),
      ])
      allReviews.push(...reviews.filter(Boolean))
      const missing = ['spec', 'quality'].filter((_, i) => !reviews[i])
      if (missing.length) { outcome = 'blocked'; reason = `審查者沒有回應：${missing.join('、')}（不可視為通過）`; break }
      const pmCritical = planMandated(reviews).filter((i) => i.severity === 'critical')
      if (pmCritical.length) { outcome = 'blocked'; reason = `plan-mandated critical ${pmCritical.length} 項，需要人類決定（WORKFLOW §4.1、§8）`; break }
      const block = blocking(reviews)
      lastBlock = block
      if (!block.length) break
      if (round >= MAX_FIX_ROUNDS) { outcome = 'blocked'; reason = `修正 ${MAX_FIX_ROUNDS} 輪後仍有 ${block.length} 個阻塞問題`; break }
      phase('Fix')
      const fx = await agent(fixPrompt(o, block, round + 1, 'task'), { label: `fix ${o.workItem} T${o.taskNumber} r${round + 1}`, phase: 'Fix', schema: IMPL })
      if (!fx || fx.status === 'BLOCKED' || fx.status === 'NEEDS_CONTEXT') {
        outcome = 'blocked'
        reason = `修正者無法完成：${fx ? (fx.concerns || []).join('；') : '沒有回應'}`
        break
      }
      fixes.push(fx)
      head = fx.headSha
      prior = J(block)
    }
  }

  phase('Record')
  const rec = await agent(recordPrompt(o, {
    outcome, reason, continuing: continuing && outcome === 'done', resumed: !!resume,
    task: o.taskNumber, taskTitle: o.taskTitle, totalTasks: o.totalTasks,
    base: o.baseSha, head, implementer: impl, fixes,
    reviews: allReviews.map((r) => ({ verdict: r.verdict, spec: r.spec, issues: r.issues, report: r.report })),
    minorIssues: minors(allReviews), planMandatedIssues: planMandated(allReviews),
    unresolvedBlocking: outcome === 'blocked' ? lastBlock : [],
  }), { label: `record ${o.workItem} T${o.taskNumber}`, phase: 'Record', schema: RECORD })

  return {
    outcome, reason, task: o.taskNumber, head, fixRounds: fixes.length,
    planMandatedCount: planMandated(allReviews).length,
    impl: impl ? { status: impl.status, commits: impl.commits, green: impl.green, concerns: impl.concerns } : null,
    record: rec,
  }
}

// ── 整體審查 ──
async function runFinal(o) {
  let head = o.headSha
  let prior = ''
  let acc = null
  const allFinals = []
  const fixes = []
  let outcome = 'final_ready'
  let reason = ''
  for (let round = 0; ; round++) {
    phase('Final review')
    const [final, a] = await parallel([
      () => agent(`${BASE}

你是**唯讀**的整體審查者，負責 ${o.workItem}「${o.title}」的完整分支。先讀 AGENTS.md §3 和 docs/WORKFLOW.md §4。
不可以修改 working tree 或 HEAD。**不要使用瀏覽器，也不要啟動伺服器**，驗收者正在同時使用。舊版 localStorage 升級這類需要實測的項目，從程式碼判斷；判斷不了的，寫進 issue 的 fix 欄位。
${itemCtx(o)}
審查範圍：先看 \`git log --oneline ${o.mergeBase}..${head}\` 和 \`git diff --stat ${o.mergeBase}..${head}\`，再讀 diff。
依 WORKFLOW §4.2，對照 plan 和 spec 檢查：
- 功能是否齊全、偏離 plan 的地方是否合理
- 架構與整合
- 上線準備：舊資料能否升級、README 是否照 plan 更新
- PROGRESS §5 中本工作項目新增的 minor，有沒有應該在合併前修掉的
${prior ? `上一輪的阻塞問題如下，逐一確認是否已修好，仍然存在的要再列一次：\n${prior}\n` : ''}
嚴重度照 WORKFLOW §4.1。
verdict：有任何 critical 或 important，而且不是 planMandated，就填 needs_fixes；否則填 approved（等於 Ready to merge: Yes）。
spec 欄填 n/a 或 compliant。
report 要寫完整文字，結尾加上 \`Ready to merge: Yes | No | With fixes\`。`, { label: `final-review ${o.workItem}${round ? ` r${round}` : ''}`, phase: 'Final review', schema: REVIEW }),
      () => agent(`${BASE}

你是驗收者，負責 ${o.workItem}「${o.title}」。不要修改任何檔案。先讀 docs/WORKFLOW.md §5。
${itemCtx(o)}
1. 照 WORKFLOW §5 跑完整測試頁，記下 \`#sum\`。這也算一個檢查項目，item 寫「測試頁全部通過」。
2. 逐項執行 docs/PROGRESS.md 中本工作項目的「驗收」清單，以及 plan、spec 指定的瀏覽器實測：
   - 切換身分、點擊流程
   - 375px 寬度（用 WORKFLOW §5 第 7 點的檢查式）
   - console 錯誤

   每一項都要附證據：DOM 或 JS 讀到的值、console 輸出，或截圖說明。結束前把 viewport 設回桌面，伺服器只關你自己啟動的。
3. allPass 只有在所有檢查項目（包括測試頁）都 pass 時才填 true。`, { label: `acceptance ${o.workItem}${round ? ` r${round}` : ''}`, phase: 'Final review', schema: ACCEPT }),
    ])
    acc = a
    if (final) allFinals.push(final)
    if (!final || !acc) { outcome = 'final_blocked'; reason = `${!final ? '整體審查者' : '驗收者'}沒有回應，不可視為通過`; break }
    const pmCritical = planMandated([final]).filter((i) => i.severity === 'critical')
    if (pmCritical.length) { outcome = 'final_blocked'; reason = `plan-mandated critical ${pmCritical.length} 項，需要人類決定`; break }
    const accFails = (acc.checks || []).filter((c) => !c.pass).map((c) => ({ severity: 'important', planMandated: false, file: '(acceptance)', line: '', desc: `驗收未通過：${c.item}`, fix: c.evidence }))
    if (!acc.allPass && !accFails.length) accFails.push({ severity: 'important', planMandated: false, file: '(acceptance)', line: '', desc: `驗收 allPass=false（#sum：${acc.sum}）`, fix: acc.notes })
    const all = [...blocking([final]), ...accFails]
    if (!all.length) break
    if (round >= MAX_FIX_ROUNDS) { outcome = 'final_blocked'; reason = `整體審查或驗收在修正 ${round} 輪後仍未通過（${all.length} 項）`; break }
    phase('Fix')
    const fx = await agent(fixPrompt(o, all, round + 1, 'final'), { label: `final-fix ${o.workItem} r${round + 1}`, phase: 'Fix', schema: IMPL })
    if (!fx || fx.status === 'BLOCKED' || fx.status === 'NEEDS_CONTEXT') {
      outcome = 'final_blocked'
      reason = `整體修正無法完成：${fx ? (fx.concerns || []).join('；') : '沒有回應'}`
      break
    }
    fixes.push(fx)
    head = fx.headSha
    prior = J(all)
  }
  phase('Record')
  const rec = await agent(recordPrompt(o, {
    outcome, reason, continuing: false, base: o.mergeBase, head, fixes,
    reviews: allFinals.map((r) => ({ verdict: r.verdict, issues: r.issues, report: r.report })),
    acceptance: acc,
    minorIssues: minors(allFinals), planMandatedIssues: planMandated(allFinals),
  }), { label: `record ${o.workItem} final`, phase: 'Record', schema: RECORD })
  return { outcome, reason, head, fixRounds: fixes.length, planMandatedCount: planMandated(allFinals).length, acceptance: acc && { sum: acc.sum, allPass: acc.allPass }, record: rec }
}

// ── 主迴圈 ──
const history = []
const seen = new Set()
let taskSteps = 0
for (let step = 0; step < MAX_TASKS + 4; step++) {
  phase('Orient')
  const o = await agent(orientPrompt(step), { label: `orient${step ? ` #${step + 1}` : ''}`, phase: 'Orient', schema: ORIENT })
  if (!o) { history.push({ step: 'orient', outcome: 'error', reason: 'orient agent 沒有回應' }); break }
  history.push({ step: 'orient', mode: o.mode, workItem: o.workItem, task: o.taskNumber, reason: o.reason, testBaseline: o.testBaseline, actions: o.actionsTaken, humanQuestions: o.humanQuestions })
  log(`${o.workItem || '?'}｜mode=${o.mode}${o.taskNumber ? `｜Task ${o.taskNumber}/${o.totalTasks}` : ''}｜${o.reason}`)

  if (o.mode === 'blocked' && o.needsRecord && !DRY) {
    phase('Record')
    const rec = await agent(recordPrompt(o, { outcome: 'blocked', reason: o.reason, continuing: false, task: o.taskNumber, humanQuestions: o.humanQuestions, source: 'orient' }), { label: `record ${o.workItem} blocked`, phase: 'Record', schema: RECORD })
    history.push({ step: 'record-blocked', record: rec })
  }
  if (DRY || !o.ok || o.mode === 'blocked' || o.mode === 'idle') break

  const key = `${o.workItem}#${o.mode}#${o.taskNumber}`
  if (seen.has(key)) { history.push({ step: 'guard', outcome: 'error', reason: `orient 再次回傳 ${key}，看板沒有前進，停止以免重做` }); break }
  seen.add(key)

  if (o.mode === 'task' || o.mode === 'review') {
    const continuing = ALL || (taskSteps + 1 < MAX_TASKS && o.taskNumber < o.totalTasks)
    const r = await runTask(o, continuing, o.mode === 'review')
    history.push({ step: `task ${o.taskNumber}`, ...r })
    taskSteps++
    if (r.outcome !== 'done') break
    if (!r.record || !r.record.ok) { history.push({ step: 'record', outcome: 'error', reason: '記錄者沒有回應或 ok=false（看板可能沒前進），停止' }); break }
    if (ALL && r.planMandatedCount) { log('有 plan-mandated 問題待人類決定，all 模式停止'); break }
    if (taskSteps >= MAX_TASKS) { if (ALL) log(`已達 ${MAX_TASKS} 個 Task 的上限，停止`); break }
    if (!ALL && o.taskNumber >= o.totalTasks) break
    continue
  }
  if (o.mode === 'final') {
    const r = await runFinal(o)
    history.push({ step: 'final', ...r })
    if (r.outcome !== 'final_ready' || !ALL || !(r.record && r.record.ok) || r.planMandatedCount) break
    continue
  }
  if (o.mode === 'merge') {
    phase('Merge')
    const m = await agent(mergePrompt(o), { label: `merge ${o.workItem}`, phase: 'Merge', schema: RECORD })
    history.push({ step: 'merge', record: m })
    break
  }
  break
}

const last = history[history.length - 1] || {}
return {
  mode: DRY ? 'dry-run' : ALL ? 'all' : `steps:${MAX_TASKS}`,
  tasksCompleted: history.filter((h) => /^task /.test(h.step || '') && h.outcome === 'done').length,
  stoppedAt: last.step,
  stopReason: last.reason || (last.record && last.record.notes) || '',
  nextAction: (last.record && last.record.nextAction) || last.reason || '',
  history,
}
