import { useEffect, useRef, useState, type ReactNode } from 'react';
import { ApiError, requestJson } from '../api';

type Item = { id: string; category: string; code: string; title: string; status: string; fields: { label: string; value: string }[]; revision: number };
type Links = { items: Item[]; can_manage: boolean };
type Results = { items: Item[]; total: number; offset: number };

export default function LinkedOperations({ scopePath, expired, preview, leaveGuard }: {
  scopePath: string; expired: () => void; preview: ReactNode; leaveGuard: { current: (() => boolean) | null };
}) {
  const [links, setLinks] = useState<Links | null>(null);
  const [results, setResults] = useState<Results | null>(null);
  const [category, setCategory] = useState('partners');
  const [query, setQuery] = useState('');
  const [searched, setSearched] = useState('');
  const [selected, setSelected] = useState<Item | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [showPreview, setShowPreview] = useState(false);
  const active = useRef<AbortController | null>(null);
  const inFlight = useRef(false);
  const path = `${scopePath}/operation-links`;
  async function run(action: (signal: AbortSignal) => Promise<void>) {
    if (inFlight.current) return;
    inFlight.current = true;
    const controller = new AbortController(); active.current = controller;
    setBusy(true); setError(''); setNotice('');
    try { await action(controller.signal); }
    catch (e) { if (!controller.signal.aborted) {
      if (e instanceof ApiError && e.status === 401) expired();
      else setError(e instanceof Error ? e.message : '操作失敗，請稍後再試');
    } }
    finally { if (!controller.signal.aborted) { inFlight.current = false; setBusy(false); } }
  }
  async function load(signal: AbortSignal) {
    const value = await requestJson<Links>(path, { signal });
    if (!signal.aborted) setLinks(value);
  }
  async function search(signal: AbortSignal, offset = 0, q = query) {
    const value = await requestJson<Results>(`/operations?${new URLSearchParams({ category, q, offset: String(offset), limit: '20' })}`, { signal });
    if (!signal.aborted) { setResults(value); setSearched(q); }
  }
  useEffect(() => { void run(load); return () => { active.current?.abort(); inFlight.current = false; }; }, []);
  useEffect(() => {
    const guard = () => !inFlight.current;
    leaveGuard.current = guard;
    return () => { if (leaveGuard.current === guard) leaveGuard.current = null; };
  }, [leaveGuard]);
  async function mutate(item: Item, remove: boolean, signal: AbortSignal) {
    await requestJson(remove ? `${path}/${item.id}` : path, { method: remove ? 'DELETE' : 'POST', signal,
      ...(remove ? {} : { body: JSON.stringify({ record_id: item.id }) }) });
    if (signal.aborted) return;
    setSelected(null); await load(signal);
    if (!signal.aborted) setNotice(remove ? '已解除關聯，原營運資料保留。' : '關聯已儲存。');
  }
  const labels: Record<string, string> = { partners: '供應商／合作夥伴', orders: '採購／訂單', work: '工單／執行紀錄' };
  if (showPreview) return <><button type="button" onClick={() => setShowPreview(false)}>返回正式關聯</button>{preview}</>;
  return <section className="linked-operations" aria-label="正式資料關聯">
    <header><h2>關聯營運資料</h2><p>本專案或任務的關聯會保存，內容隨營運資料更新。新增或編輯原始紀錄請至左側「營運資料」。</p>
      <button type="button" disabled={busy} onClick={() => setShowPreview(true)}>查看原關聯示例</button>
      <button type="button" disabled={busy} onClick={() => { setSelected(null); setResults(null); void run(load); }}>重新載入</button></header>
    {error && <p role="alert">{error}</p>}{notice && <p role="status">{notice}</p>}
    {!links && <p>{busy ? '載入中…' : '尚未載入資料，請重試。'}</p>}
    {links && <><h3>已關聯資料（{links.items.length}）</h3>
      {!links.items.length && <p>尚無可查看的關聯資料。</p>}
      <ul>{links.items.map(item => <li key={item.id}><span>{labels[item.category]}</span>
        <button type="button" disabled={busy} onClick={() => { setSelected(null); void run(async signal => {
          const value = await requestJson<Item>(`/operations/${item.id}`, { signal }); if (!signal.aborted) setSelected(value);
        }); }}>{item.code} · {item.title}</button><span>{item.status}</span>
        {links.can_manage && <button type="button" disabled={busy} aria-label={`解除關聯 ${item.code}`} onClick={() => {
          if (window.confirm(`解除「${item.title}」的關聯？原營運資料會保留。`)) void run(signal => mutate(item, true, signal));
        }}>解除關聯</button>}</li>)}</ul>
      {!links.can_manage && <p>你可以查看資料；目前沒有編輯此處關聯的權限。</p>}
      {links.can_manage && <fieldset disabled={busy}><legend>新增關聯</legend>
        <label>資料分類<select aria-label="資料分類" value={category} onChange={e => { setCategory(e.target.value); setResults(null); }}>{Object.entries(labels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
        <label>搜尋代碼或名稱<input aria-label="搜尋代碼或名稱" maxLength={100} value={query} onChange={e => setQuery(e.target.value)} /></label>
        <button type="button" onClick={() => void run(signal => search(signal))}>搜尋營運資料</button>
        {results && <><p>找到 {results.total} 筆可查看資料</p><ul>{results.items.map(item => <li key={item.id}><span>{item.code} · {item.title} · {item.status}</span>
          <button type="button" disabled={links.items.some(link => link.id === item.id)} aria-label={`關聯 ${item.code}`} onClick={() => void run(signal => mutate(item, false, signal))}>{links.items.some(link => link.id === item.id) ? '已關聯' : '關聯並儲存'}</button></li>)}</ul>
          <button type="button" disabled={results.offset === 0} onClick={() => void run(signal => search(signal, results.offset - 20, searched))}>上一頁</button>
          <button type="button" disabled={results.offset + 20 >= results.total} onClick={() => void run(signal => search(signal, results.offset + 20, searched))}>下一頁</button></>}
      </fieldset>}
      {selected && <article aria-label="關聯資料內容"><h3>{selected.title}</h3><p>{selected.code} · {selected.status} · 修訂 {selected.revision}</p><dl>{selected.fields.map(field => <div key={field.label}><dt>{field.label}</dt><dd>{field.value || '—'}</dd></div>)}</dl></article>}
    </>}
  </section>;
}
