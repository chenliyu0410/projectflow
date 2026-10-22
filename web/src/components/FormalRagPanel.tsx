import { useEffect, useRef, useState } from 'react';
import { ApiError } from '../api';
import { rag } from '../rag';
import type { Locator, RagConfig, RagOriginal, RagResult, RagStatus } from '../rag';
const states: Record<string, string> = { queued: '待索引', indexing: '索引中', processing: '索引中', ready: '可檢索', failed: '索引失敗', unsupported: '格式不支援' };
function location(l: Locator) { return [l.page != null && `第 ${l.page} 頁`, l.section, l.start_char != null && `字元 ${l.start_char}–${l.end_char ?? ''}`].filter(Boolean).join('・') || '文件片段'; }
export default function FormalRagPanel({ expired }: { expired?: () => void }) {
  const [status, setStatus] = useState<RagStatus | null>(null);
  const [project, setProject] = useState('');
  const [question, setQuestion] = useState('');
  const [previous, setPrevious] = useState('');
  const [result, setResult] = useState<RagResult | null>(null);
  const [original, setOriginal] = useState<RagOriginal | null>(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const [config, setConfig] = useState<RagConfig | null>(null);
  const generation = useRef(0);
  const requests = useRef(new Set<AbortController>());
  const sourceRequest = useRef<AbortController | null>(null);
  function invalidate() { generation.current++; requests.current.forEach(r => r.abort()); requests.current.clear(); setBusy(false); }
  useEffect(() => () => { generation.current++; requests.current.forEach(r => r.abort()); }, []);
  async function run<T,>(action: (signal: AbortSignal) => Promise<T>, apply: (value: T) => void) {
    const id = generation.current; const controller = new AbortController(); requests.current.add(controller); setError(''); setBusy(true);
    try { const value = await action(controller.signal); if (!controller.signal.aborted && id === generation.current) apply(value); }
    catch (e) { if (!controller.signal.aborted && id === generation.current) { if (e instanceof ApiError && e.status === 401) expired?.(); setError(e instanceof Error ? e.message : '正式文件操作失敗，請重試。'); } }
    finally { requests.current.delete(controller); if (id === generation.current && !controller.signal.aborted) setBusy(requests.current.size > 0); }
  }
  useEffect(() => {
    const controller = new AbortController(); const id = generation.current; requests.current.add(controller);
    rag.status(project, controller.signal).then(s => { if (!controller.signal.aborted && id === generation.current) setStatus(s); }).catch(e => { if (!controller.signal.aborted && id === generation.current) { if (e instanceof ApiError && e.status === 401) expired?.(); setError('無法載入正式文件，請重新整理。'); } }).finally(() => { requests.current.delete(controller); if (!controller.signal.aborted && id === generation.current) setBusy(requests.current.size > 0); });
    return () => { controller.abort(); requests.current.delete(controller); };
  }, [project, refresh]);
  function selectProject(value: string) { invalidate(); setProject(value); setStatus(null); setResult(null); setOriginal(null); setQuestion(''); setPrevious(''); setError(''); setNotice(''); }
  function showSource(source: string) {
    sourceRequest.current?.abort(); setOriginal(null);
    void run(signal => { const controller = new AbortController(); sourceRequest.current = controller; signal.addEventListener('abort', () => controller.abort(), { once: true }); return rag.source(result!.query_id, source, controller.signal).then(value => { if (controller.signal.aborted) throw new DOMException('取消', 'AbortError'); return value; }); }, setOriginal);
  }
  return <section className="formal-rag" aria-label="正式文件問答">
    <p className="copilot-example-note">正式文件・依目前登入權限檢索。請先在專案的文件區上傳 TXT、CSV、文字 PDF 或 DOCX，再回來重新整理並建立索引。</p>
    <label>正式專案<select aria-label="正式專案" value={project} onChange={e => selectProject(e.target.value)}><option value="">請選擇正式專案</option>{status?.projects.map(p => <option key={p.project_id} value={p.project_id}>{p.title}</option>)}</select></label>
    <button disabled={busy} onClick={() => setRefresh(v => v + 1)}>重新整理正式文件</button>
    <p>{status?.model.enabled ? `本機模型：${status.model.name}` : '模型未啟用；僅提供文件檢索，答案會標示降級。'}</p>
    {project && <div aria-label="正式文件清單">{status?.documents.length === 0 && <p>這個專案尚無可見文件。</p>}{status?.documents.map(d => <article key={d.document_id}><strong>{d.title}</strong><p>版本 {d.version}・{states[d.state] ?? d.state}・{d.chunk_count} 個片段・{d.enabled ? '知識已啟用' : '知識已停用'}</p>{d.error_code && <p>{d.error_code === 'embedding_unavailable' ? '向量模型暫時不可用，目前可用關鍵字檢索；稍後可重試索引。' : '索引未完成，請確認檔案有可擷取的文字、未加密且未超過容量限制，再重試。'}</p>}{d.can_index ? <><button disabled={busy} onClick={() => void run(s => rag.index(d.document_id, s), () => { setRefresh(v => v + 1); setResult(null); setOriginal(null); })}>{d.state === 'failed' ? '重試索引' : '建立／更新索引'}</button><button disabled={busy} onClick={() => void run(s => rag.enable(d.document_id, !d.enabled, s), () => { setRefresh(v => v + 1); setResult(null); setOriginal(null); })}>{d.enabled ? '停用知識' : '啟用知識'}</button></> : <small>唯讀文件；索引由有編輯權限的人管理。</small>}</article>)}</div>}
    <form onSubmit={e => { e.preventDefault(); setOriginal(null); setNotice(''); void run(s => rag.ask({ project_id: project, question: question.trim(), ...(previous.trim() ? { previous_question: previous.trim() } : {}) }, s), setResult); }}>
      <label>正式文件問題<textarea aria-label="正式文件問題" maxLength={2000} disabled={busy} value={question} onChange={e => setQuestion(e.target.value)} /></label>
      <label>前次問題（選填）<input aria-label="前次問題（選填）" maxLength={1000} value={previous} onChange={e => setPrevious(e.target.value)} /></label>
      <button disabled={busy || !project || !question.trim()}>送出正式文件問題</button>
    </form>
    {busy && <p role="status">正在處理… <button onClick={invalidate}>取消正式查詢</button></p>}
    {error && <p role="alert">{error}</p>}{notice && <p role="status">{notice}</p>}
    {result && <article aria-label="正式文件回答"><small>{result.engine === 'model' ? '本機模型・請核對來源' : '文件檢索'}・{result.retrieval_mode === 'hybrid_rrf_rules' ? '混合檢索' : '關鍵字檢索'}</small><p>{result.answer}</p>{result.warning && <p role="status">{result.warning}</p>}{result.sources.map(s => <details key={s.source_id}><summary>{s.title}・版本 {s.version}・{location(s.locator)}{result.citations.includes(s.source_id) ? '（引用）' : ''}</summary><p>{s.excerpt}</p><button disabled={busy} onClick={() => showSource(s.source_id)}>查看原文</button></details>)}<div aria-label="回答回饋"><button disabled={busy} onClick={() => void run(s => rag.feedback(result.query_id, 'helpful', s), () => setNotice('已記錄：有幫助'))}>有幫助</button><button disabled={busy} onClick={() => void run(s => rag.feedback(result.query_id, 'unhelpful', s), () => setNotice('已記錄：沒有幫助'))}>沒有幫助</button></div></article>}
    {original && <section aria-label="正式引用原文"><button onClick={() => setOriginal(null)}>關閉來源</button><h3>{original.title}・版本 {original.version}</h3><p>{location(original.locator)}・{original.is_current ? '現行版本' : '非現行版本'}</p><pre>{original.text}</pre></section>}
    {status?.can_configure && <details><summary onClick={() => { if (!config) void run(s => rag.config(s), setConfig); }}>正式文件本機模型設定</summary>{config && <form onSubmit={e => { e.preventDefault(); void run(s => rag.save(config, s), () => { setNotice('模型設定已儲存'); setRefresh(v => v + 1); }); }}><label><input type="checkbox" checked={config.enabled} onChange={e => setConfig({ ...config, enabled: e.target.checked })} />啟用正式文件模型</label>{(['base_url', 'model', 'embedding_model'] as const).map(key => <label key={key}>{({ base_url: 'Ollama 網址', model: '對話模型', embedding_model: 'Embedding 模型' })[key]}<input required value={config[key]} onChange={e => setConfig({ ...config, [key]: e.target.value })} /></label>)}<button disabled={busy}>儲存正式模型設定</button></form>}</details>}
  </section>;
}
