import { useEffect, useRef } from 'react';
import type { RagResult, RagScope, TurnContext, Locator } from '../rag';
import { ragMessages } from '../rag';
export type RagTurn = { id: number; question: string; scope: RagScope; history: TurnContext[]; state: 'waiting' | 'done' | 'failed' | 'stopped' | 'unavailable'; started: number; result?: RagResult; error?: string; notice?: string };
export function location(l: Locator) { return [l.page != null && `第 ${l.page} 頁`, l.section, l.start_char != null && `字元 ${l.start_char}–${l.end_char ?? ''}`].filter(Boolean).join('・') || '文件片段'; }
export default function RagConversation({ turns, masked, elapsed, ask, retry, stop, source, feedback }: { turns: RagTurn[]; masked: boolean; elapsed: number; ask: (q: string) => void; retry: (t: RagTurn) => void; stop: () => void; source: (t: RagTurn, id: string) => void; feedback: (t: RagTurn, rating: 'helpful' | 'unhelpful') => void }) {
 const chat = useRef<HTMLDivElement>(null); useEffect(() => { chat.current?.scrollTo?.({ top: chat.current.scrollHeight }); }, [turns]);
 const busy = turns.some(t => t.state === 'waiting');
 return <div ref={chat} className="rag-chat" aria-label="正式對話紀錄" aria-live="polite">
 {!turns.length && <div className="rag-welcome"><small>從文件找到答案</small><h3>想了解專案的哪一件事？</h3><p>直接提問，回答會附上文件來源。<br />你也可以接著追問。</p><div className="rag-suggestions">{['G2 要具備什麼才能通過？', '包裝規格有哪些要求？', '目前有哪些已核准的備援供應商？'].map(q => <button key={q} onClick={() => ask(q)}>{q} ↗</button>)}</div></div>}
 {masked && turns.some(t => t.result) && <p role="status">正在重新確認來源權限…</p>}
 {turns.map(t => { const r = t.result; const ids = r ? [...new Set((r.blocks ?? []).flatMap(b => b.source_ids).concat(r.citations))] : [];
 return <div key={t.id} className="rag-turn"><p className="rag-user">{t.question}</p>
 {t.state === 'waiting' && <div role="status">查詢文件並整理回答・已等待 {elapsed} 秒{elapsed >= 30 && <p>仍在處理，較長文件可能需要更多時間。</p>}<button onClick={stop}>停止等待</button></div>}
 {t.state === 'stopped' && <p role="status">已停止等待；伺服器可能仍在處理。</p>}
 {t.error && <p role="alert">{t.error}</p>}
 {(t.state === 'stopped' || t.state === 'failed' || (t.state === 'done' && ['generation_timeout', 'generation_unavailable'].includes(r?.code ?? ''))) && <button disabled={busy || masked} onClick={() => retry(t)}>重試這一題</button>}
 {!masked && r && <article aria-label="正式文件回答" className="rag-answer"><small>{r.engine === 'model' ? '本機模型・請核對來源' : '文件檢索'}</small>
 {r.code && ragMessages[r.code] && <p role="status" className="rag-notice">{ragMessages[r.code]}</p>}
 {r.coverage?.partial && r.code !== 'partial_coverage' && <p role="status">{ragMessages.partial_coverage}</p>}
 {(r.blocks?.length ? r.blocks : [{ text: r.answer, source_ids: [] }]).map((b, i) => <p key={i}><span>{b.text}</span>{b.source_ids.map(id => { const s = r.sources.find(s => s.source_id === id); return s ? <button key={id} className="rag-citation" aria-label={`引用 ${ids.indexOf(id) + 1}：${s.title}`} onClick={() => source(t, id)}>[{ids.indexOf(id) + 1}]</button> : null; })}</p>)}
 {r.warning && !r.code && <p role="status">{r.warning}</p>}
 <div className="rag-sources">{r.sources.map(s => <details key={s.source_id}><summary>{ids.includes(s.source_id) ? `[${ids.indexOf(s.source_id) + 1}] ` : ''}{s.title}・版本 {s.version}・{location(s.locator)}</summary><p>{s.project_title ?? s.project_id}</p><blockquote>{s.excerpt}</blockquote><button onClick={() => source(t, s.source_id)}>查看原文</button></details>)}</div>
 <div aria-label="回答回饋"><button onClick={() => feedback(t, 'helpful')}>有幫助</button><button onClick={() => feedback(t, 'unhelpful')}>沒有幫助</button></div></article>}
 {t.notice && <p role="status">{t.notice}</p>}
 </div>; })}</div>;
}
