import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { ApiError } from '../api';
import { rag, ragMessages } from '../rag';
import type { RagOriginal, RagScope, RagStatus, TurnContext } from '../rag';
import RagConversation from './RagConversation';
import type { RagTurn } from './RagConversation';
import RagKnowledgeManager from './RagKnowledgeManager';
import RagSourceViewer from './RagSourceViewer';
function scopeFor(id?: string | null): RagScope { return id ? { kind: 'project', project_id: id } : { kind: 'all_visible' }; }
export default function FormalRagPanel({ expired, open = true, routeProjectId, demo }: { expired?: () => void; open?: boolean; routeProjectId?: string | null; demo?: () => void }) {
 const [scopeNotice, setScopeNotice] = useState('');
 const [scope, setScope] = useState<RagScope>(() => scopeFor(routeProjectId));
 const [status, setStatus] = useState<RagStatus | null>(null), [refresh, setRefresh] = useState(0);
 const [turns, setTurns] = useState<RagTurn[]>([]), [draft, setDraft] = useState(''), [elapsed, setElapsed] = useState(0);
 const [management, setManagement] = useState(false), [error, setError] = useState(''), [masked, setMasked] = useState(false);
 const [source, setSource] = useState<{ query: string; original: RagOriginal | null; loading: boolean; error: string } | null>(null);
 const turnRef = useRef(turns); turnRef.current = turns; const sequence = useRef(0), epoch = useRef(0);
 const askRequest = useRef<AbortController | null>(null), sourceRequest = useRef<AbortController | null>(null), validationRequest = useRef<AbortController | null>(null);
 const feedbackRequests = useRef(new Set<AbortController>()); const composing = useRef(false); const previousRoute = useRef(routeProjectId);
 const busy = turns.some(t => t.state === 'waiting');
 function patch(id: number, change: Partial<RagTurn>) { setTurns(items => items.map(t => t.id === id ? { ...t, ...change } : t)); }
 function clear() { epoch.current++; askRequest.current?.abort(); askRequest.current = null; sourceRequest.current?.abort(); validationRequest.current?.abort(); feedbackRequests.current.forEach(c => c.abort()); feedbackRequests.current.clear(); setTurns([]); turnRef.current = []; setDraft(''); setSource(null); setMasked(false); setError(''); setScopeNotice(''); }
 function select(value: string) { clear(); setScopeNotice('範圍已切換，已開始新對話'); setScope(scopeFor(value)); setStatus(v => v ? { ...v, documents: [] } : null); }
 useLayoutEffect(() => { if (previousRoute.current !== routeProjectId) { previousRoute.current = routeProjectId; clear(); setScopeNotice('範圍已切換，已開始新對話'); setScope(scopeFor(routeProjectId)); setStatus(v => v ? { ...v, documents: [] } : null); } }, [routeProjectId]);
 useEffect(() => () => { epoch.current++; askRequest.current?.abort(); sourceRequest.current?.abort(); validationRequest.current?.abort(); feedbackRequests.current.forEach(c => c.abort()); }, []);
 useEffect(() => {
  const c = new AbortController(); rag.status(scope, c.signal).then(v => { if (!c.signal.aborted) { setStatus(v); setError(''); } }).catch(e => { if (!c.signal.aborted) { if (e instanceof ApiError && e.status === 401) expired?.(); setError(e instanceof ApiError ? e.message : '無法載入正式文件，請重新整理。'); } }); return () => c.abort();
 }, [scope, refresh]);
 function revoke(queryIds: Set<string>) {
  sourceRequest.current?.abort(); setSource(null);
  setTurns(items => items.map(t => ({ ...t, history: t.history.filter(h => !h.query_id || !queryIds.has(h.query_id)), ...(t.result && queryIds.has(t.result.query_id) ? { result: undefined, state: 'unavailable' as const, notice: ragMessages.access_changed } : {}) })));
 }
 async function revalidate() {
  validationRequest.current?.abort(); const c = new AbortController(); validationRequest.current = c; const run = epoch.current;
  const ids = [...new Set(turnRef.current.flatMap(t => t.result ? [t.result.query_id] : []))];
  if (!ids.length) { setMasked(false); return; }
  setMasked(true); sourceRequest.current?.abort(); setSource(null);
  try { const results: { query_id: string; status: string }[] = []; for (let i = 0; i < ids.length; i += 100) { const response = await rag.revalidate(ids.slice(i, i + 100), c.signal); results.push(...response.queries); }
   if (c.signal.aborted || run !== epoch.current) return;
   const denied = new Set(ids.filter(id => !results.some(r => r.query_id === id && ['visible', 'source_changed'].includes(r.status)))); revoke(denied);
   setTurns(items => items.map(t => t.result && results.some(r => r.query_id === t.result!.query_id && r.status === 'source_changed') ? { ...t, notice: ragMessages.source_changed } : t)); setMasked(false); setError('');
  } catch(e) { if (c.signal.aborted || run !== epoch.current) return; if (e instanceof ApiError && e.status === 401) { clear(); expired?.(); } else if (e instanceof ApiError && [403,404].includes(e.status)) { revoke(new Set(ids)); setMasked(false); } setError('無法確認來源權限，暫時隱藏舊回答。請重新確認權限。'); }
 }
 useLayoutEffect(() => { if (!open) { setMasked(true); validationRequest.current?.abort(); sourceRequest.current?.abort(); setSource(null); return; } void revalidate(); }, [open]);
 useEffect(() => { if (!open) return; const onFocus = () => { void revalidate(); }; const onVisible = () => { if (document.visibilityState === 'visible') void revalidate(); }; window.addEventListener('focus', onFocus); document.addEventListener('visibilitychange', onVisible); const timer = setInterval(() => { if (document.visibilityState === 'visible') void revalidate(); }, 30000); return () => { clearInterval(timer); window.removeEventListener('focus', onFocus); document.removeEventListener('visibilitychange', onVisible); }; }, [open]);
 useEffect(() => { const pending = turns.find(t => t.state === 'waiting'); if (!pending) return; const tick = () => setElapsed(Math.max(0, Math.floor((Date.now() - pending.started) / 1000))); tick(); const timer = setInterval(tick, 1000); return () => clearInterval(timer); }, [busy, turns.find(t => t.state === 'waiting')?.started]);
 function historyBefore(id?: number) { const result: TurnContext[] = []; let length = 0; const eligible = turnRef.current.filter(t => t.state === 'done' && t.result && (id === undefined || t.id < id)); for (const t of eligible.slice(-6).reverse()) { if (length + t.question.length > 6000) break; length += t.question.length; result.unshift({ question: t.question, query_id: t.result!.query_id }); } return result; }
 async function ask(question: string, retry?: RagTurn) {
  const q = question.trim(); if (!q || askRequest.current || masked) return;
  const c = new AbortController(); askRequest.current = c; const run = epoch.current;
  const item: RagTurn = { id: retry?.id ?? ++sequence.current, question: q, scope: retry?.scope ?? scope, history: historyBefore(retry?.id), state: 'waiting', started: Date.now() };
  sourceRequest.current?.abort(); setSource(null); setElapsed(0); setError('');
  if (retry) setTurns(items => items.map(t => t.id === retry.id ? item : t)); else { setTurns(items => [...items, item]); setDraft(''); }
  const timer = setTimeout(() => { if (run !== epoch.current || askRequest.current !== c) return; c.abort(); askRequest.current = null; patch(item.id, { state: 'failed', error: '查詢逾時，請稍後重試。' }); }, 180000);
  try { const result = await rag.ask({ scope: item.scope, question: q, history: item.history }, c.signal); if (c.signal.aborted || run !== epoch.current) return; if (result.code === 'access_changed') revoke(new Set(turnRef.current.flatMap(t => t.result ? [t.result.query_id] : []))); patch(item.id, { state: 'done', result }); }
  catch(e) { if (c.signal.aborted || run !== epoch.current) return; if (e instanceof ApiError && e.status === 401) { clear(); expired?.(); return; } if (e instanceof ApiError && [403,404].includes(e.status)) revoke(new Set(turnRef.current.flatMap(t => t.result ? [t.result.query_id] : []))); patch(item.id, { state: 'failed', error: e instanceof Error ? e.message : '查詢失敗，請重試。' }); }
  finally { clearTimeout(timer); if (askRequest.current === c) askRequest.current = null; }
 }
 function stop() { askRequest.current?.abort(); askRequest.current = null; setTurns(items => items.map(t => t.state === 'waiting' ? { ...t, state: 'stopped' } : t)); }
 async function showSource(t: RagTurn, id: string) { if (!t.result || masked) return; sourceRequest.current?.abort(); const c = new AbortController(); sourceRequest.current = c; const run = epoch.current; const query = t.result.query_id; setSource({ query, original: null, loading: true, error: '' }); try { const original = await rag.source(query, id, c.signal); if (!c.signal.aborted && run === epoch.current) setSource({ query, original, loading: false, error: '' }); } catch(e) { if (!c.signal.aborted && run === epoch.current) { if (e instanceof ApiError && [401,403,404].includes(e.status)) { revoke(new Set(turnRef.current.flatMap(t => t.result ? [t.result.query_id] : []))); if (e.status === 401) expired?.(); } setSource({ query, original: null, loading: false, error: e instanceof ApiError ? e.message : '無法讀取原文，請重試。' }); } } }
 async function feedback(t: RagTurn, rating: 'helpful' | 'unhelpful') { if (!t.result || masked) return; const c = new AbortController(); feedbackRequests.current.add(c); try { await rag.feedback(t.result.query_id, rating, c.signal); if (!c.signal.aborted) patch(t.id, { notice: rating === 'helpful' ? '已記錄：有幫助' : '已記錄：沒有幫助' }); } catch(e) { if (!c.signal.aborted) { if (e instanceof ApiError && e.status === 401) expired?.(); patch(t.id, { notice: '無法記錄回饋，請稍後重試。' }); } } finally { feedbackRequests.current.delete(c); } }
 return <section className="formal-rag" aria-label="正式文件問答"><div className="rag-toolbar"><label>查詢範圍<select aria-label="查詢範圍" value={scope.kind === 'project' ? scope.project_id : ''} onChange={e => select(e.target.value)}><option value="">所有可見專案</option>{scope.kind === 'project' && !status?.projects.some(p => p.project_id === scope.project_id) && <option value={scope.project_id}>目前專案</option>}{status?.projects.map(p => <option key={p.project_id} value={p.project_id}>{p.title}</option>)}</select></label><button onClick={() => { clear(); setScopeNotice('已開始新對話'); }}>＋ 新對話</button></div>
 {scopeNotice && <p className="rag-scope-notice" role="status">{scopeNotice}</p>}
 {error && <div role="alert">{error}<button onClick={() => { setRefresh(v => v + 1); void revalidate(); }}>重新確認權限</button></div>}
 <RagConversation turns={turns} masked={masked || !open} elapsed={elapsed} ask={q => void ask(q)} retry={t => void ask(t.question, t)} stop={stop} source={(t, id) => void showSource(t, id)} feedback={(t, r) => void feedback(t, r)} />
 <footer className="rag-composer"><form onSubmit={e => { e.preventDefault(); if (!composing.current) void ask(draft); }}><label className="sr-only" htmlFor="rag-question">正式文件問題</label><textarea id="rag-question" aria-label="正式文件問題" rows={2} maxLength={2000} value={draft} placeholder="想了解文件中的什麼？" onChange={e => setDraft(e.target.value)} onCompositionStart={() => { composing.current = true; }} onCompositionEnd={() => { composing.current = false; }} onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing && !composing.current && e.keyCode !== 229) { e.preventDefault(); void ask(draft); } }} /><button disabled={busy || masked || !draft.trim()} aria-label="送出正式文件問題">↑</button></form><div><small>Enter 送出／Shift＋Enter 換行</small><button onClick={() => setManagement(true)}>管理與設定</button></div></footer>
 {management && <RagKnowledgeManager status={status} refresh={() => setRefresh(v => v + 1)} close={() => setManagement(false)} demo={demo} expired={expired} />}
 {source && !masked && open && <RagSourceViewer key={source.query} original={source.original} loading={source.loading} error={source.error} close={() => { sourceRequest.current?.abort(); setSource(null); }} expired={expired} denied={() => revoke(new Set(turnRef.current.flatMap(t => t.result ? [t.result.query_id] : [])))} />}
 </section>;
}
