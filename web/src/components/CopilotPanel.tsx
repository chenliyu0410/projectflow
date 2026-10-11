import { useEffect, useRef, useState } from 'react';
import NavIcon from './NavIcons';
import { AI_ACTIONS, answerExample, CASE_TITLE } from '../preview/fixtures';
import type { AiAction } from '../preview/fixtures';

type Message = { id: number; title: string; text: string; user?: boolean; suggestions?: string[]; reference?: string; route?: string; applied?: boolean };
export default function CopilotPanel({ scope, open, close, food = false, companyName = '目前公司' }: { scope: string; open: boolean; close: () => void; food?: boolean; companyName?: string }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [meeting, setMeeting] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const nextId = useRef(0);
  const chat = useRef<HTMLDivElement>(null);
  useEffect(() => { chat.current?.scrollTo?.({ top: chat.current.scrollHeight }); }, [messages, suggestions]);
  function add(message: Omit<Message, 'id'>) { setMessages(value => [...value, { ...message, id: ++nextId.current }]); }
  function run(action: AiAction, text = '') {
    if (!food) { add({ title: action, text: `${companyName}尚未建立此項展示示例；未讀取正式專案，也不套用食品資料。` }); return; }
    if (action === '會議紀錄抽待辦' && !text) { setMeeting('請採購確認原料交期。\n請品保安排成品送驗。'); return; }
    const result = answerExample(action, text);
    add({ title: action, ...result, text: result.text + (action === '會議紀錄抽待辦' && !result.suggestions.length ? '\n未找到含指定關鍵詞的待辦，請修改紀錄後重試。' : '') });
  }
  function ask() {
    const text = input.trim(); if (!text) return;
    add({ title: '你的提問', text, user: true }); setInput('');
    if (!food) { add({ title: '本地展示示例', text: `${companyName}尚無此類示例。請返回既有工作區操作正式任務。` }); return; }
    if (/會議|待辦|紀錄/.test(text)) run('會議紀錄抽待辦', text);
    else if (/成本|配方/.test(text)) run('配方成本比較');
    else if (/風險|延遲/.test(text)) run('延遲風險分析');
    else if (/拆解|下一階段/.test(text)) run('拆解下一階段');
    else if (/模板|部門/.test(text)) run('推薦模板與部門');
    else if (/週報|進度/.test(text)) run('本週進度報告');
    else add({ title: '尚未支援這個問題', text: '這是本地關鍵詞規則，未連接通用模型。可試：「整理進度」、「分析風險」、「比較配方成本」，或使用上方六個快捷。' });
  }
  return <aside id="copilot-panel" className={`copilot ${open ? 'open' : ''}`} aria-label="AI 專案副手">
    <div className="copilot-head"><span className="copilot-avatar"><NavIcon name="ai" /></span><div><strong className="brand-name">AI 專案副手</strong><small>目前位置：{scope}</small></div><button className="copilot-close" aria-label="關閉 AI 副手" onClick={close}>✕</button></div>
    <p className="copilot-policy"><span className="preview-badge">展示預覽</span>本地規則・未連接模型</p>
    <p className="copilot-example-note">{food ? `回答僅使用「${CASE_TITLE}」` : `${companyName}尚無展示資料`}，不讀取正式任務。內容只留在本頁，離開預覽、切公司或登出即清除。</p>
    <div className="copilot-actions" role="group" aria-label="副手快捷動作">{AI_ACTIONS.map(label => <button key={label} onClick={() => run(label)}>{label}</button>)}</div>
    {meeting !== null && <form className="copilot-meeting" onSubmit={e => { e.preventDefault(); run('會議紀錄抽待辦', meeting); setMeeting(null); }}><label>會議紀錄（僅預覽）<textarea maxLength={5000} value={meeting} onChange={e => setMeeting(e.target.value)} /></label><div className="preview-actions"><button disabled={!meeting.trim()} type="submit">預覽待辦</button><button type="button" onClick={() => setMeeting(null)}>取消</button></div></form>}
    <div className="copilot-chat" ref={chat} aria-label="示例對話紀錄" aria-live="polite">{messages.length === 0 && <p>選擇快捷或輸入問題，體驗示例回答、引用與建議操作。</p>}
      {messages.map(message => <article key={message.id} className={`copilot-message ${message.user ? 'user' : ''}`}><strong>{message.title}</strong>{!message.user && <small>本地展示示例・未連接模型</small>}<p>{message.text}</p>
        {!!message.suggestions?.length && <><ul>{message.suggestions.map((text, i) => <li key={i}>{text}</li>)}</ul><button disabled={message.applied} onClick={() => { setSuggestions(value => [...new Set([...value, ...message.suggestions!])]); setMessages(value => value.map(item => item.id === message.id ? { ...item, applied: true } : item)); }}>{message.applied ? '已套用至預覽' : '確認套用至預覽'}</button></>}
        {message.reference && <details><summary>結果詳情／引用與送出內容</summary><p>引用：{message.reference}</p><p>路由示例：{message.route}</p><p>未呼叫任何模型或傳送內容。下列是固定的遮罩格式示意，不是本次輸入的遮罩結果。</p><pre>示例送出內容（未送出）：整理 [供應商_01] 的試產安排。{ '\n' }固定對照：青禾原料 → [供應商_01]</pre></details>}
      </article>)}
      {!!suggestions.length && <section className="preview-suggestions" aria-label="已套用預覽清單"><h3>預覽任務／部門建議</h3><p>未建立正式任務、模板或部門。</p><ul>{suggestions.map(text => <li key={text}>{text}</li>)}</ul></section>}
    </div>
    <form className="copilot-ask" onSubmit={e => { e.preventDefault(); ask(); }}><label className="sr-only" htmlFor="copilot-input">詢問 AI</label><input id="copilot-input" maxLength={2000} value={input} onChange={e => setInput(e.target.value)} placeholder="試問：整理進度、分析風險…" /><button type="submit" disabled={!input.trim()} aria-label="送出預覽問題"><NavIcon name="send" /></button></form>
  </aside>;
}
