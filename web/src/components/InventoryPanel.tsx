import { useEffect, useRef, useState } from 'react';
import { ApiError, requestJson } from '../api';

type Resource = { id: string; code: string; title: string };
type Movement = { id: string; kind: string; resource_label: string; order_label: string | null; work_label: string | null; quantity: string; unit: string; before: string; after: string; reason: string; actor_name: string; created_at: string };
type History = { items: Movement[]; total: number; offset: number; limit: number };
type Stock = { quantity: string; unit: string | null };
type Payload = { request_id: string; resource_id: string; quantity: string; unit: string; reason: string };

export default function InventoryPanel({ record, expired, leaveGuard, blocked = false }: {
  blocked?: boolean; record: Resource & { category: string }; expired: () => void; leaveGuard: { current: (() => boolean) | null };
}) {
  const receipt = record.category === 'orders';
  const work = record.category === 'work';
  const picking = receipt || work;
  const [workMode, setWorkMode] = useState<'issues' | 'completions'>('issues');
  const actionName = work ? workMode === 'issues' ? '工單領料' : '完工入庫' : receipt ? '收貨入庫' : '庫存調整';
  const [history, setHistory] = useState<History | null>(null);
  const [stock, setStock] = useState<Stock | null>(null);
  const [resources, setResources] = useState<{ items: Resource[]; total: number; offset: number } | null>(null);
  const [query, setQuery] = useState('');
  const [searched, setSearched] = useState('');
  const [resource, setResource] = useState<Resource | null>(picking ? null : record);
  const [quantity, setQuantity] = useState('');
  const [unit, setUnit] = useState('');
  const [reason, setReason] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [pending, setPending] = useState<Payload | null>(null);
  const inFlight = useRef(false);
  const controller = useRef<AbortController | null>(null);
  const dirty = quantity !== '' || reason !== '';
  useEffect(() => {
    const guard = () => {
      if (inFlight.current) return false;
      if (pending) { window.alert('入帳結果待確認，請先重試相同入帳；系統會防止重複記帳。'); return false; }
      return !dirty || window.confirm('收貨／庫存調整尚未儲存，確定放棄並離開嗎？');
    };
    leaveGuard.current = guard;
    const unload = (e: BeforeUnloadEvent) => { if (dirty || pending || inFlight.current) { e.preventDefault(); e.returnValue = ''; } };
    window.addEventListener('beforeunload', unload);
    return () => { if (leaveGuard.current === guard) leaveGuard.current = null; window.removeEventListener('beforeunload', unload); };
  }, [dirty, pending, leaveGuard]);
  async function run(action: (signal: AbortSignal) => Promise<void>) {
    if (inFlight.current) return;
    const current = new AbortController(); controller.current = current; inFlight.current = true;
    setBusy(true); setError('');
    try { await action(current.signal); }
    catch (e) { if (!current.signal.aborted) {
      if (e instanceof ApiError && e.status === 401) expired();
      else setError(e instanceof ApiError && e.status === 409 ? '未入帳：庫存不足、單位不符或操作內容衝突。請確認數量及既有單位。' : e instanceof Error ? e.message : '操作失敗，請重試');
    } }
    finally { if (!current.signal.aborted) { inFlight.current = false; setBusy(false); } }
  }
  async function loadHistory(signal: AbortSignal, offset = 0) {
    const value = await requestJson<History>(`/inventory/movements?${work ? 'work_id' : receipt ? 'order_id' : 'resource_id'}=${record.id}&offset=${offset}`, { signal });
    if (!signal.aborted) setHistory(value);
  }
  async function loadStock(item: Resource, signal: AbortSignal) {
    const value = await requestJson<Stock>(`/inventory/resources/${item.id}`, { signal });
    if (!signal.aborted) { setStock(value); setUnit(value.unit ?? ''); }
  }
  useEffect(() => { void run(async signal => { await loadHistory(signal); if (!picking) await loadStock(record, signal); });
    return () => { controller.current?.abort(); inFlight.current = false; }; }, []);
  async function search(signal: AbortSignal, offset = 0, q = query) {
    const value = await requestJson<{ items: Resource[]; total: number; offset: number }>(`/operations?${new URLSearchParams({ category: 'resources', q, offset: String(offset), limit: '10' })}`, { signal });
    if (!signal.aborted) { setResources(value); setSearched(q); }
  }
  async function submit() {
    if (!resource || blocked || inFlight.current) return;
    const payload = pending ?? { request_id: crypto.randomUUID(), resource_id: resource.id, quantity, unit, reason };
    if (!pending && !window.confirm(`確認${actionName}：${resource.code}，${quantity} ${unit}？此筆異動會永久保留。`)) return;
    setPending(payload); setNotice('');
    await run(async signal => {
      try {
        await requestJson<Movement>(work ? `/operations/${record.id}/${workMode}` : receipt ? `/operations/${record.id}/receipts` : '/inventory/adjustments', { method: 'POST', body: JSON.stringify(payload), signal });
      } catch (e) {
        if (e instanceof ApiError && [400, 401, 403, 404, 409, 422].includes(e.status)) setPending(null);
        throw e;
      }
      if (signal.aborted) return;
      setPending(null); setQuantity(''); setReason(''); setNotice('已入帳，庫存與異動紀錄已保存。');
      await loadStock(resource, signal); await loadHistory(signal);
    });
  }
  return <fieldset className="inventory-shell" disabled={blocked}><section className="inventory-panel" aria-label="收貨與庫存">
    <h3>{work ? '工單領料與完工入庫' : receipt ? '採購收貨' : '庫存與異動'}</h3>
    <p>收貨、領料、完工入庫及調整才會異動庫存；原單據文字不計入庫存。最多三位小數，首次入帳後固定物料單位。</p>
    {receipt && <p>可分次收貨；尚未檢查訂購數量上限，不自動改單據狀態。</p>}
    {work && <p>先選領料或完工入庫，再選物料或成品。成品請先在物料／資源分類建立；可分批入帳，不自動結案，不依配方自動扣料。</p>}
    {error && <p role="alert">{error}</p>}{notice && <p role="status">{notice}</p>}
    {pending && <p role="alert">{busy ? '入帳處理中…' : '入帳結果待確認，請重試相同入帳，不要另外新增同一筆收貨。'}</p>}
    <fieldset disabled={busy || !!pending}><legend>{work ? actionName : receipt ? '收貨明細' : '盤點／補正調整'}</legend>
      {work && <label>工單操作<select aria-label="工單操作" value={workMode} onChange={e => {
        if (dirty && !window.confirm('切換操作會清除尚未保存的輸入，確定切換嗎？')) return;
        setWorkMode(e.target.value as 'issues' | 'completions'); setResource(null); setStock(null); setQuantity(''); setReason(''); setUnit(''); setResources(null); setQuery(''); setNotice('');
      }}><option value="issues">領料扣庫存</option><option value="completions">完工入庫</option></select></label>}
      {picking && <><label>{work ? '搜尋物料或成品' : '搜尋收貨物料'}<input aria-label={work ? '搜尋物料或成品' : '搜尋收貨物料'} maxLength={100} value={query} onChange={e => setQuery(e.target.value)} /></label>
        <button type="button" onClick={() => void run(signal => search(signal))}>搜尋物料</button>
        {resources && <><p>找到 {resources.total} 筆物料／資源</p><ul>{resources.items.map(item => <li key={item.id}><button type="button" aria-pressed={resource?.id === item.id} onClick={() => { setResource(item); setStock(null); setUnit(''); void run(signal => loadStock(item, signal)); }}>{item.code}｜{item.title}</button></li>)}</ul>
          <button type="button" disabled={resources.offset === 0} onClick={() => void run(signal => search(signal, resources.offset - 10, searched))}>上一批物料</button>
          <button type="button" disabled={resources.offset + 10 >= resources.total} onClick={() => void run(signal => search(signal, resources.offset + 10, searched))}>下一批物料</button></>}
      </>}
      {resource && <p>物料：{resource.code}｜{resource.title}</p>}
      {stock && <p aria-label="目前庫存">目前庫存：{stock.quantity} {stock.unit ?? '（尚未設定單位）'}</p>}
      <label>{work ? `${actionName}數量（請填正數）` : receipt ? '實收數量' : '調整數量（增加為正、減少為負）'}<input aria-label="異動數量" type="number" step="0.001" min={picking ? '0.001' : '-999999999'} max="999999999" value={quantity} onChange={e => setQuantity(e.target.value)} /></label>
      <label>庫存單位<input aria-label="庫存單位" maxLength={20} disabled={!!stock?.unit} value={unit} onChange={e => setUnit(e.target.value)} placeholder="例如 kg、件、箱" /></label>
      <label>異動原因／收貨說明<textarea aria-label="異動原因／收貨說明" maxLength={500} value={reason} onChange={e => setReason(e.target.value)} /></label>
    </fieldset>
    <button type="button" className="primary" disabled={busy || !resource || !stock || !quantity || !unit.trim() || !reason.trim()} onClick={() => void submit()}>{pending ? '重試相同入帳' : work ? `確認${actionName}` : receipt ? '確認收貨入庫' : '儲存庫存調整'}</button>
    <button type="button" disabled={busy || !!pending} onClick={() => void run(async signal => { await loadHistory(signal); if (resource) await loadStock(resource, signal); })}>重新載入庫存與紀錄</button>
    <h4>異動紀錄{history ? `（${history.total}）` : ''}</h4>
    {history?.total === 0 && <p>尚無異動紀錄。</p>}
    <ul className="inventory-history">{history?.items.map(item => <li key={item.id}><strong>{item.kind === 'issue' ? '工單領料' : item.kind === 'completion' ? '完工入庫' : item.kind === 'receipt' ? '採購收貨' : '庫存調整'} · {item.resource_label}</strong><p>{item.quantity} {item.unit} · 庫存 {item.before} → {item.after}</p><p>來源：{item.work_label ?? item.order_label ?? '人工調整'} · {item.reason}</p><p>{item.actor_name} · {new Date(item.created_at).toLocaleString('zh-TW')}</p></li>)}</ul>
    {history && <><button type="button" disabled={busy || !!pending || history.offset === 0} onClick={() => void run(signal => loadHistory(signal, history.offset - history.limit))}>上一頁異動</button><button type="button" disabled={busy || !!pending || history.offset + history.limit >= history.total} onClick={() => void run(signal => loadHistory(signal, history.offset + history.limit))}>下一頁異動</button></>}
  </section></fieldset>;
}
