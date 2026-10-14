import { useEffect, useRef, useState } from 'react';
import NavIcon from './NavIcons';
import ModelSettings from './ModelSettings';
import { ai } from '../ai';
import type { AIResult, AIStatus } from '../ai';

type Message = { id: number; question: string; result: AIResult };
const HEADINGS: Record<string, string> = { project_id: 'AI專案', task_id: '任務', supplier_id: '供應商', department: '部門', name: '姓名', person_id: '人員', status: '狀態', count: '數量', overdue_count: '逾期數', total: '總數', done_count: '完成數', completion_pct: '完成率％', budget_twd: '預算', actual_twd: '已入帳', overrun_twd: '超支', amount_twd: '金額', received_count: '收貨數', late_count: '延遲數', late_pct: '延遲率％', samples: '抽樣數', defects: '不良數', defect_pct: '不良率％', month: '月份', category: '類別', risk_id: '風險', cause: '原因', action: '處理方式', open_tasks: '未完成數', estimated_hours: '預估工時', actual_hours: '實際工時', extra_hours: '超估工時', committed_twd: '承諾金額', due_date: '到期日', rejected_count: '退回數', blocked_count: '受阻數', order_id: '採購單', promised_date: '承諾日', zero_defect_batches: '零不良批次' };
const STATUS: Record<string, string> = { done: '完成', doing: '進行中', review: '待審核', rejected: '退回', todo: '未開始', blocked: '受阻' };

export default function CopilotPanel({ scope, open, close, companyName = '目前公司' }: { scope: string; open: boolean; close: () => void; food?: boolean; companyName?: string }) {
  const [status, setStatus] = useState<AIStatus | null>(null);
  const [error, setError] = useState('');
  const [mode, setMode] = useState<'rag' | 'sql'>('rag');
  const [project, setProject] = useState('');
  const [query, setQuery] = useState('');
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [busy, setBusy] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [document, setDocument] = useState<{ title: string; text: string } | null>(null);
  const [loadingDocument, setLoadingDocument] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const controller = useRef<AbortController | null>(null);
  const docController = useRef<AbortController | null>(null);
  const nextId = useRef(0);
  const chat = useRef<HTMLDivElement>(null);
  const closeButton = useRef<HTMLButtonElement>(null);
  useEffect(() => { if (open) closeButton.current?.focus(); }, [open]);
  useEffect(() => {
    const request = new AbortController();
    ai.status(request.signal).then(value => { if (!request.signal.aborted) { setStatus(value); setError(''); } }).catch(() => { if (!request.signal.aborted) setError('無法載入 AI 資料，請稍後重試。'); });
    return () => request.abort();
  }, [refresh]);
  useEffect(() => () => { controller.current?.abort(); docController.current?.abort(); }, []);
  useEffect(() => { chat.current?.scrollTo?.({ top: chat.current.scrollHeight }); }, [messages, busy]);
  function clear() { controller.current?.abort(); docController.current?.abort(); setBusy(false); setLoadingDocument(false); setMessages([]); setDocument(null); setError(''); }
  async function ask(question: string, selectedQuery?: string, selectedMode = mode) {
    if (busy || !status?.ready || !question.trim()) return;
    const request = new AbortController(); controller.current = request;
    setBusy(true); setError(''); setDocument(null);
    try {
      const result = await ai.ask({ question, mode: selectedMode, project_id: project || null, ...(selectedQuery ? { query_id: selectedQuery } : {}) }, request.signal);
      if (!request.signal.aborted) { setMessages(items => [...items.slice(-19), { id: ++nextId.current, question, result }]); setInput(''); }
    } catch (e) { if (!request.signal.aborted) setError(e instanceof Error ? e.message : '查詢失敗，請重試。'); }
    finally { if (!request.signal.aborted) setBusy(false); }
  }
  async function showDocument(id: string) {
    docController.current?.abort(); const request = new AbortController(); docController.current = request;
    setLoadingDocument(true); setError('');
    try { const value = await ai.document(id, request.signal); if (!request.signal.aborted) setDocument(value); }
    catch { if (!request.signal.aborted) setError('無法讀取引用，可能沒有權限或登入已失效。'); }
    finally { if (!request.signal.aborted) setLoadingDocument(false); }
  }
  const quick = mode === 'rag' ? ['現行交付需要幾張截圖？', '風險原因與處理方式', '採購追蹤紀錄'] : ['各部門逾期未完成數', '超支專案及金額', '各專案加權不良率'];
  return <aside id="copilot-panel" className={`copilot ${open ? 'open' : ''}`} aria-label="AI 專案副手" hidden={!open}>
    <div className="copilot-head"><span className="copilot-avatar"><NavIcon name="ai" /></span><div><strong className="brand-name">AI 專案副手</strong><small>目前位置：{scope}</small></div><button ref={closeButton} className="copilot-close" aria-label="關閉 AI 副手" onClick={close}>✕</button></div>
    <p className="copilot-policy">{status?.model_enabled ? `本地模型：${status.model_name}` : '模型未啟用・檢索與資料查詢可用'}</p>
    <p className="copilot-example-note">{companyName}・AI展示資料區<br />{status?.ready ? `${status.counts.projects} 個專案／${status.counts.documents} 份可見文件・基準日 ${status.as_of}` : '資料尚未就緒'}。虛構延伸案，與目前正式任務分開；查詢不修改任務。</p>
    <div className="ai-controls">
      <label>查詢方式<select aria-label="查詢方式" value={mode} onChange={e => { clear(); setMode(e.target.value as 'rag' | 'sql'); setQuery(''); }}><option value="rag">RAG 文件問答</option><option value="sql" disabled={!status?.can_sql}>Text-to-SQL 資料分析</option></select></label>
      <label>AI展示專案<select aria-label="AI展示專案" value={project} onChange={e => { clear(); setProject(e.target.value); }}><option value="">目前公司全部AI專案</option>{status?.projects.map(p => <option key={p.project_id} value={p.project_id}>{p.project_id}｜{p.title}</option>)}</select></label>
      {mode === 'sql' && <label>分析種類<select aria-label="分析種類" value={query} onChange={e => setQuery(e.target.value)}><option value="">依輸入問題辨識</option>{status?.queries.map(q => <option key={q.query_id} value={q.query_id}>{q.label}</option>)}</select></label>}
    </div>
    <div className="copilot-actions" role="group" aria-label="副手快捷動作">{quick.map(text => <button disabled={busy || !status?.ready} key={text} onClick={() => void ask(text)}>{text}</button>)}</div>
    {error && <p role="alert" className="ai-error">{error}<button onClick={() => setRefresh(v => v + 1)}>重新載入</button></p>}
    <div className="copilot-chat" ref={chat} aria-label="AI 對話紀錄" aria-live="polite">
      {!messages.length && <p>選擇AI專案後提問，或使用快捷分析。RAG提供可開啟的原文引用；資料分析顯示實際SQL與結果。</p>}
      {messages.map(({ id, question, result }) => <article key={id} className="copilot-message"><strong>{question}</strong><small>{result.engine === 'model' ? '本地模型處理・請核對來源' : result.kind === 'sql' ? '受控SQL・資料庫實算' : '本地文件檢索'}</small><p>{result.answer}</p>{result.warning && <p role="status">{result.warning}</p>}
        {result.suggestion && <button disabled={busy} onClick={() => void ask(result.suggestion!.label, result.suggestion!.query_id, 'sql')}>確認執行：{result.suggestion.label}</button>}
        {result.analysis && <><div className="ai-table-scroll" tabIndex={0} aria-label="查詢結果"><table><thead><tr>{result.analysis.columns.map(c => <th key={c}>{HEADINGS[c] ?? c}</th>)}</tr></thead><tbody>{result.analysis.rows.map((row, i) => <tr key={i}>{result.analysis!.columns.map(c => <td key={c}>{c === 'status' ? STATUS[String(row[c])] ?? row[c] : row[c] ?? '—'}</td>)}</tr>)}</tbody></table>{!result.analysis.rows.length && <p>沒有符合條件的資料。</p>}</div><details><summary>查看 SQL 與查詢範圍</summary><pre>{result.analysis.sql}</pre><pre>{JSON.stringify(result.analysis.parameters, null, 2)}</pre></details></>}
        {!!result.sources.length && <div className="ai-sources">{result.sources.map(s => <details key={s.document_id}><summary>{s.document_id} · {s.title}{result.citations?.includes(s.document_id) ? '（模型引用）' : ''}</summary><p>{s.excerpt}</p><button disabled={loadingDocument} onClick={() => void showDocument(s.document_id)}>開啟原文 {s.document_id}</button></details>)}</div>}
      </article>)}
      {busy && <p role="status">正在查詢… <button onClick={() => { controller.current?.abort(); setBusy(false); }}>取消</button></p>}
      {document && <section className="ai-document" aria-label="引用原文"><button onClick={() => setDocument(null)}>關閉原文</button><h3>{document.title}</h3><pre>{document.text}</pre></section>}
    </div>
    <form className="copilot-ask" onSubmit={e => { e.preventDefault(); const selected = status?.queries.find(q => q.query_id === query); void ask(selected ? selected.label : input, query || undefined); }}><label className="sr-only" htmlFor="copilot-input">詢問 AI</label><input id="copilot-input" maxLength={2000} value={input} disabled={busy} onChange={e => setInput(e.target.value)} placeholder={mode === 'rag' ? '查交付規範、風險或會議紀錄…' : query ? '將執行上方選定分析' : '例如：各部門逾期未完成數'} /><button type="submit" disabled={busy || !status?.ready || (!input.trim() && !query)} aria-label="送出 AI 問題"><NavIcon name="send" /></button></form>
    {status?.can_configure && <details className="ai-model-details" onToggle={e => setSettingsOpen(e.currentTarget.open)}><summary>本地模型連線設定</summary>{settingsOpen && <ModelSettings saved={() => setRefresh(v => v + 1)} />}</details>}
  </aside>;
}
