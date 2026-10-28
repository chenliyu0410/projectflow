import { useEffect, useRef, useState } from 'react';
import NavIcon from './NavIcons';
import ModelSettings from './ModelSettings';
import { CATEGORIES } from './copilotScenarios';
import type { CopilotCategory, CopilotQuestion } from './copilotScenarios';
import { ai } from '../ai';
import type { AIPreview, AIResult, AIStatus, GatewayInfo } from '../ai';
import { ApiError } from '../api';

type Message = { id: number; question: string; result: AIResult; history: boolean };
const HEADINGS: Record<string, string> = { project_id: 'AI專案', task_id: '任務', supplier_id: '供應商', department: '部門', name: '姓名', person_id: '人員', status: '狀態', count: '數量', overdue_count: '逾期數', total: '總數', done_count: '完成數', completion_pct: '完成率％', budget_twd: '預算', actual_twd: '已入帳', overrun_twd: '超支', amount_twd: '金額', received_count: '收貨數', late_count: '延遲數', late_pct: '延遲率％', samples: '抽樣數', defects: '不良數', defect_pct: '不良率％', month: '月份', category: '類別', risk_id: '風險', cause: '原因', action: '處理方式', open_tasks: '未完成數', estimated_hours: '預估工時', actual_hours: '實際工時', extra_hours: '超估工時', committed_twd: '承諾金額', due_date: '到期日', rejected_count: '退回數', blocked_count: '受阻數', order_id: '採購單', promised_date: '承諾日', zero_defect_batches: '零不良批次' };
const STATUS_ERROR = '無法載入 AI 資料，請稍後重試。';
const POLICY: Record<string, string> = { local_only: '全本地', mixed: '混合', cloud_allowed: '允許雲端' };
const CLOUD: Record<string, string> = { policy_local_only: '政策為全本地，不送雲端', confidential_local_only: '含機密資料，只能本地', no_cloud_provider: '符合遮罩後送雲端的條件，但未設定雲端供應商，未送出' };
const RETRIEVAL: Record<string, string> = { keyword: '關鍵字', hybrid: '關鍵字＋本地語意向量', keyword_fallback: '關鍵字（語意向量暫時無法使用）' };
const STATUS: Record<string, string> = { done: '完成', doing: '進行中', review: '待審核', rejected: '退回', todo: '未開始', blocked: '受阻' };

function GatewaySummary({ info }: { info: GatewayInfo }) {
  const levels = { public: '公開', internal: '內部', confidential: '機密' };
  const reasons: Record<string, string> = { model_disabled: '模型未啟用', local_only: '僅允許本地／內網模型', invalid_config: '模型設定不符合本地政策，已阻擋', rules_only: '由系統直接查詢，不需要模型', no_sources: '沒有可提供的來源', other_company: '問題詢問其他公司，權限範圍內沒有該公司資料，未送出', context_too_large: '最相關的段落超過本地模型長度上限，未送出' };
  const omitted = info.route === 'local' && info.sent_count !== undefined ? info.source_count - info.sent_count : 0;
  return <p>資料等級：{levels[info.classification]}{info.classification_reason === 'unclassified' ? '（含未分級資料，從嚴處理）' : ''}。{reasons[info.reason] ?? '僅限本地處理'}。{info.outcome === 'completed' ? '本地模型已完成處理' : info.outcome === 'failed' ? '曾嘗試本地模型，未取得有效結果' : '尚未送往模型'}；雲端關閉。{omitted > 0 && `提供模型 ${info.sent_count} 段；另 ${omitted} 段因長度上限未提供，仍列在來源中。`}{info.cloud && `雲端判斷（${POLICY[info.ai_policy ?? ''] ?? '全本地'}）：${CLOUD[info.cloud.reason] ?? info.cloud.reason}。`}</p>;
}

export default function CopilotPanel({ scope, open, close, companyName = '目前公司', expired }: { scope: string; open: boolean; close: () => void; food?: boolean; companyName?: string; expired?: () => void }) {
  const [status, setStatus] = useState<AIStatus | null>(null);
  const [error, setError] = useState('');
  const [categoryId, setCategoryId] = useState<CopilotCategory['id']>('docs');
  // Both are fixed per user and company: SQL is a role permission (only reported on the SQL dataset) and the formal
  // index is a deployment switch, so they keep their categories visible while another category's data is shown.
  const [canSql, setCanSql] = useState(false);
  const [formalAvailable, setFormalAvailable] = useState(false);
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [busy, setBusy] = useState(false);
  const [preview, setPreview] = useState<AIPreview | null>(null);
  const [previewBusy, setPreviewBusy] = useState(false);
  const [indexBusy, setIndexBusy] = useState(false);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [document, setDocument] = useState<{ title: string; text: string; version?: number; is_current?: boolean } | null>(null);
  const [loadingDocument, setLoadingDocument] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const controller = useRef<AbortController | null>(null);
  const docController = useRef<AbortController | null>(null);
  const previewController = useRef<AbortController | null>(null);
  const indexController = useRef<AbortController | null>(null);
  const nextId = useRef(0);
  const chat = useRef<HTMLDivElement>(null);
  const previewSection = useRef<HTMLElement>(null);
  const documentVersion = useRef<HTMLParagraphElement>(null);
  const closeButton = useRef<HTMLButtonElement>(null);
  const categories = CATEGORIES.filter(c => (!c.companies || c.companies.includes(companyName)) && (c.id !== 'sql' || canSql) && (c.id !== 'formal' || formalAvailable));
  const category = categories.find(c => c.id === categoryId) ?? CATEGORIES[0];
  const { dataset, mode } = category;
  useEffect(() => { if (open) closeButton.current?.focus(); }, [open]);
  useEffect(() => {
    const request = new AbortController();
    let pending = false;
    async function load() {
      if (pending) return;
      pending = true;
      try {
        const value = await ai.status(request.signal, dataset);
        if (request.signal.aborted) return;
        setStatus(value); setError(current => current === STATUS_ERROR ? '' : current);
        if (dataset === 'dataset-v1') setCanSql(value.can_sql);
        setFormalAvailable(!!value.formal_available);
      }
      catch { if (!request.signal.aborted) setError(STATUS_ERROR); }
      finally { pending = false; }
    }
    void load();
    const timer = open && dataset === 'formal-v1' ? window.setInterval(() => void load(), 10000) : undefined;
    return () => { request.abort(); window.clearInterval(timer); };
  }, [refresh, dataset, open]);
  useEffect(() => () => { controller.current?.abort(); docController.current?.abort(); previewController.current?.abort(); indexController.current?.abort(); }, []);
  useEffect(() => {
    const area = chat.current, section = document ? documentVersion.current : preview ? previewSection.current : null;
    if (area) area.scrollTo?.({ top: section ? area.scrollTop + section.getBoundingClientRect().top - area.getBoundingClientRect().top : area.scrollHeight });
  }, [messages, busy, preview, document]);
  function chooseCategory(id: CopilotCategory['id']) {
    if (id === category.id) return;
    clear(); setInput('');
    if (CATEGORIES.find(c => c.id === id)?.dataset !== dataset) setStatus(null);
    setCategoryId(id);
  }
  // 登入失效時交給外層回登入頁，不在副手裡顯示一般錯誤。
  function sessionExpired(error: unknown) {
    if (!(error instanceof ApiError) || error.status !== 401 || !expired) return false;
    expired();
    return true;
  }
  function clearPreview() { previewController.current?.abort(); setPreview(null); setPreviewBusy(false); }
  function clear() { controller.current?.abort(); docController.current?.abort(); indexController.current?.abort(); setIndexBusy(false); clearPreview(); setBusy(false); setLoadingDocument(false); setMessages([]); setDocument(null); setError(''); }
  async function refreshIndex() {
    if (busy || indexBusy || !status?.index?.can_refresh) return;
    clear();
    const request = new AbortController(); indexController.current = request;
    setIndexBusy(true);
    try {
      await ai.refreshIndex(request.signal);
      if (!request.signal.aborted) { setStatus(null); setRefresh(v => v + 1); }
    } catch (e) { if (!request.signal.aborted && !sessionExpired(e)) setError(e instanceof Error ? e.message : '索引更新失敗，請稍後重試。'); }
    finally { if (!request.signal.aborted) setIndexBusy(false); }
  }
  // A shortcut may bring its own history, work-order mode or project; typed questions search every visible project.
  function payload(question: string, shortcut: CopilotQuestion = { text: question }, selectedQuery?: string) {
    const project = shortcut.project ? status?.projects.find(p => p.title.startsWith(shortcut.project!))?.project_id ?? null : null;
    return { question, mode: shortcut.mode ?? mode, project_id: project, ...(selectedQuery ? { query_id: selectedQuery } : {}), ...(dataset !== 'dataset-v1' ? { dataset, include_history: !!shortcut.history } : {}) };
  }
  async function showPreview() {
    if (busy || indexBusy || previewBusy || !status?.ready || !input.trim()) return;
    clearPreview(); setError(''); setDocument(null);
    const request = new AbortController(); previewController.current = request;
    setPreviewBusy(true);
    try { const value = await ai.preview(payload(input), request.signal); if (!request.signal.aborted) setPreview(value); }
    catch (e) { if (!request.signal.aborted && !sessionExpired(e)) setError(e instanceof Error ? e.message : '無法載入預覽資料。'); }
    finally { if (!request.signal.aborted) setPreviewBusy(false); }
  }
  async function ask(question: string, shortcut?: CopilotQuestion, selectedQuery?: string) {
    if (busy || indexBusy || !status?.ready || !question.trim()) return;
    // 新問題會清掉原文區，舊的原文請求晚到也不該再蓋回來。
    docController.current?.abort(); setLoadingDocument(false);
    const request = new AbortController(); controller.current = request;
    clearPreview(); setBusy(true); setError(''); setDocument(null);
    try {
      const result = await ai.ask(payload(question, shortcut, selectedQuery), request.signal);
      if (!request.signal.aborted) { setMessages(items => [...items.slice(-19), { id: ++nextId.current, question, result, history: dataset !== 'dataset-v1' && !!shortcut?.history }]); setInput(''); }
    } catch (e) {
      if (request.signal.aborted) return;
      if (sessionExpired(e)) return;
      setError(e instanceof Error ? e.message : '查詢失敗，請重試。');
    }
    finally { if (!request.signal.aborted) setBusy(false); }
  }
  async function showDocument(id: string, history: boolean) {
    docController.current?.abort(); const request = new AbortController(); docController.current = request;
    setLoadingDocument(true); setError('');
    try { const value = await ai.document(id, request.signal, dataset, history); if (!request.signal.aborted) setDocument(value); }
    catch (e) {
      if (request.signal.aborted) return;
      if (sessionExpired(e)) return;
      setError('無法讀取引用，可能沒有權限或登入已失效。');
    }
    finally { if (!request.signal.aborted) setLoadingDocument(false); }
  }
  const disabled = busy || indexBusy || !status?.ready;
  return <aside id="copilot-panel" className={`copilot ${open ? 'open' : ''}`} aria-label="AI 專案副手" hidden={!open}>
    <div className="copilot-head"><span className="copilot-avatar"><NavIcon name="ai" /></span><strong className="brand-name">AI 助手</strong>
      <button type="button" className="copilot-gear" aria-label="進階設定" title="進階設定" aria-expanded={advancedOpen} aria-controls="copilot-advanced" onClick={() => setAdvancedOpen(v => !v)}>⚙</button>
      <button ref={closeButton} className="copilot-close" aria-label="關閉 AI 副手" onClick={close}>✕</button></div>
    <div id="copilot-advanced" className="copilot-advanced" hidden={!advancedOpen}>
      <p className="copilot-policy"><span>{status?.model_enabled ? `本地模型：${status.model_name}` : '模型未啟用・檢索與資料查詢可用'}</span>・雲端關閉{status?.vectors?.enabled && `・語意檢索：${status.vectors.model}`}</p>
      <p className="copilot-example-note">目前位置：{scope}・{companyName}・{dataset === 'formal-v1' ? '正式文件與附件（隔離試用），依原權限查詢' : status?.ready ? `${status.counts.projects} 個專案／${status.counts.documents} 份可見文件・基準日 ${status.as_of}` : '資料尚未就緒'}{dataset === 'formal-v1' && status?.index && `・已索引 ${status.index.counts.indexed}／待更新 ${status.index.counts.pending}／略過 ${status.index.counts.skipped}`}</p>
      <button type="button" className="copilot-preview" disabled={busy || indexBusy || previewBusy || !status?.ready || !input.trim()} onClick={() => void showPreview()}>預覽提供給模型的資料</button>
      {dataset === 'formal-v1' && status?.index && <div>{status.index.can_refresh && <button disabled={busy || indexBusy} onClick={() => void refreshIndex()}>{indexBusy ? '正在更新索引…' : '更新文件索引'}</button>}<details><summary>查看索引狀態</summary><div style={{ maxHeight: 180, overflow: 'auto', overflowWrap: 'anywhere' }}><p>{status.index.automatic?.enabled ? `自動更新已開啟：服務運行時每${status.index.automatic.interval_seconds}秒檢查變動。` : '自動更新未開啟，請管理者手動更新。'}最近檢查：{status.index.automatic?.last_checked_at ? new Date(status.index.automatic.last_checked_at).toLocaleString('zh-TW') : '尚無紀錄'}。{status.index.automatic?.last_error}</p>{status.index.last_update && <p>最近一次{status.index.last_update.mode === 'initial' ? '首次建置' : '增量更新'}：處理 {status.index.last_update.processed}／沿用 {status.index.last_update.reused}／移除 {status.index.last_update.removed} 個來源版本。</p>}<p>索引更新：{status.index.updated_at ? new Date(status.index.updated_at).toLocaleString('zh-TW') : '尚未建立'}。新版發布後預設不再查舊版；權限撤回或來源刪除後，各版本都停止提供。</p>{status.index.items.map(item => <p key={item.source_id}>{item.title}（第{item.version}版・{item.is_current === false ? '歷史' : '現行'}）・{({ indexed: '已索引', pending: '待更新', skipped: '略過' } as Record<string, string>)[item.state]}{item.reason && `：${item.reason}`}</p>)}</div></details></div>}
      {status?.can_configure && <details className="ai-model-details" onToggle={e => setSettingsOpen(e.currentTarget.open)}><summary>本地模型連線設定</summary>{settingsOpen && <ModelSettings saved={() => { clearPreview(); setRefresh(v => v + 1); }} />}</details>}
    </div>
    <div className="copilot-categories" role="group" aria-label="AI 分類">{categories.map(c => <button key={c.id} type="button" aria-pressed={c.id === category.id} onClick={() => chooseCategory(c.id)}>{c.title}</button>)}</div>
    {error && <p role="alert" className="ai-error">{error}<button onClick={() => setRefresh(v => v + 1)}>重新載入</button></p>}
    <div className="copilot-chat" ref={chat} aria-label="AI 對話紀錄" aria-live="polite">
      {!messages.length && <p className="copilot-empty">{status && !status.ready ? `${companyName}的${category.title}資料尚未就緒。` : '點下面的問題，或直接輸入。'}</p>}
      {messages.map(({ id, question, result, history }) => <article key={id} className="copilot-message">
        <p className="copilot-question">{question}</p>
        <div className="copilot-reply">
          <p className="copilot-answer" style={result.kind === 'work_orders' || result.engine === 'model' ? { whiteSpace: 'pre-line' } : undefined}>{result.answer}</p>
          {result.warning && <p role="status">{result.warning}</p>}
          {result.suggestion && <button disabled={busy} onClick={() => void ask(result.suggestion!.label, undefined, result.suggestion!.query_id)}>確認執行：{result.suggestion.label}</button>}
          {result.analysis && <><div className="ai-table-scroll" tabIndex={0} aria-label="查詢結果"><table><thead><tr>{result.analysis.columns.map(c => <th key={c}>{HEADINGS[c] ?? c}</th>)}</tr></thead><tbody>{result.analysis.rows.map((row, i) => <tr key={i}>{result.analysis!.columns.map(c => <td key={c}>{c === 'status' ? STATUS[String(row[c])] ?? row[c] : row[c] ?? '—'}</td>)}</tr>)}</tbody></table>{!result.analysis.rows.length && <p>沒有符合條件的資料。</p>}</div><details><summary>查看 SQL 與查詢範圍</summary><pre>{result.analysis.sql}</pre><pre>{JSON.stringify(result.analysis.parameters, null, 2)}</pre></details></>}
          <div className="copilot-meta">
            {!!result.sources.length && <details className="ai-sources-group"><summary>來源 {result.sources.length} 份</summary><div className="ai-sources">{result.sources.map(s => <details key={s.document_id}><summary style={{ overflowWrap: 'anywhere' }}>{s.source_type ? `${s.source_type === 'document' ? '文件' : '附件'}・${s.title}・第${s.version}版／第${s.section}段` : `${s.document_id} · ${s.title}`}{s.is_current === false ? '（歷史版本）' : ''}{result.citations?.includes(s.document_id) ? '（模型引用）' : ''}</summary><p>{s.excerpt}</p><button disabled={loadingDocument} style={{ overflowWrap: 'anywhere' }} onClick={() => void showDocument(s.document_id, history)}>{s.source_type ? `開啟索引段落：${s.title}／${s.section}` : `開啟原文 ${s.document_id}`}</button></details>)}</div></details>}
            {result.gateway && <details><summary>資料處理紀錄</summary><p>{result.engine === 'model' ? '本地模型處理・請核對來源' : result.kind === 'sql' ? '受控SQL・資料庫實算' : result.kind === 'work_orders' ? '完整工單查詢' : result.kind === 'other_company' ? '規則判斷・其他公司' : '本地文件檢索'}</p><GatewaySummary info={result.gateway} />{result.retrieval && <p>檢索方式：{RETRIEVAL[result.retrieval]}</p>}</details>}
          </div>
        </div>
      </article>)}
      {busy && <p role="status">正在查詢… <button onClick={() => { controller.current?.abort(); setBusy(false); }}>取消</button></p>}
      {previewBusy && <p role="status">正在準備預覽… <button onClick={clearPreview}>取消預覽</button></p>}
      {preview && <section ref={previewSection} style={{ overflowWrap: 'anywhere' }} className="ai-document" aria-label="模型資料預覽"><button onClick={clearPreview}>關閉預覽</button><h3>模型資料預覽</h3><GatewaySummary info={preview.gateway} /><p>此預覽不呼叫模型。下方為目前問題與檢索內容，不含固定系統指令；送出查詢時會重新檢查資料與權限。</p>{preview.content ? <><p>問題：{preview.content.question}</p>{preview.content.as_of && <p>資料基準日：{preview.content.as_of}</p>}{preview.content.sources?.map(s => <details key={s.document_id}><summary>{s.document_id}</summary>{s.title && <p>{s.title}・{s.is_current === false ? '歷史版本，請勿當作現行規定' : '現行版本'}{s.version != null && `・第${s.version}版`}{s.project_id && `・專案 ${s.project_id}`}</p>}<pre>{s.text}</pre></details>)}{preview.content.queries && <p>只提供分析選單，不提供業務資料列：{preview.content.queries.map(q => q.label).join('、')}</p>}</> : <p>本次沒有可送往模型的內容。</p>}
        {preview.cloud_content && <details><summary>雲端送出內容（遮罩後，未送出）</summary><p>{Object.entries(preview.gateway.cloud?.masked_counts ?? {}).map(([kind, count]) => `${kind} ${count} 個`).join('、') || '公開內容，未遮罩'}；對照表只留在本機。</p><p>問題：{preview.cloud_content.question}</p>{preview.cloud_content.sources?.map(s => <pre key={s.document_id}>{s.text}</pre>)}</details>}</section>}
      {document && <section className="ai-document" aria-label="引用原文"><button onClick={() => setDocument(null)}>關閉原文</button><h3>{document.title}</h3>{document.version !== undefined && <p ref={documentVersion}>第{document.version}版・{document.is_current === false ? '歷史版本，請勿當作現行規定' : '現行版本'}</p>}<pre>{document.text}</pre></section>}
    </div>
    <div className="copilot-chips" role="group" aria-label="副手快捷動作">{category.questions.map(q => <button disabled={disabled} key={q.text} onClick={() => void ask(q.text, q)}>{q.text}</button>)}</div>
    <form className="copilot-ask" onSubmit={e => { e.preventDefault(); void ask(input); }}><label className="sr-only" htmlFor="copilot-input">詢問 AI</label><input id="copilot-input" maxLength={2000} value={input} disabled={busy || indexBusy} onChange={e => { clearPreview(); setInput(e.target.value); }} placeholder={category.placeholder} /><button type="submit" disabled={disabled || !input.trim()} aria-label="送出 AI 問題"><NavIcon name="send" /></button></form>
  </aside>;
}
