import { useEffect, useRef, useState } from 'react';
import { ApiError, requestJson } from '../api';
import InventoryPanel, { type ProgressLine } from './InventoryPanel';

type Resource = { id: string; code: string; title: string };
type Purchase = {
  order_id: string; revision: number; status: 'no_lines' | 'pending' | 'partial' | 'received' | 'closed'; status_label: string;
  closed_at: string | null; closed_by: string | null; close_reason: string | null; unlinked_receipts: number; lines: ProgressLine[];
};
type Draft = { id?: string; resource_id: string; code: string; title: string; quantity: string; unit: string; note: string; received: string; locked: boolean; fixedUnit: boolean };
const LINE_LABELS = { pending: '待收貨', partial: '部分收貨', received: '已收齊' };

export default function PurchaseOrderPanel({ record, expired, leaveGuard, blocked = false, onChanged }: {
  record: Resource & { category: string }; expired: () => void; leaveGuard: { current: (() => boolean) | null };
  blocked?: boolean; onChanged?: () => void;
}) {
  const [purchase, setPurchase] = useState<Purchase | null>(null);
  const [draft, setDraft] = useState<Draft[] | null>(null);
  const [changing, setChanging] = useState(false);
  const [reason, setReason] = useState('');
  const [query, setQuery] = useState('');
  const [searched, setSearched] = useState('');
  const [found, setFound] = useState<{ items: Resource[]; total: number; offset: number } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const inFlight = useRef(false);
  const controller = useRef<AbortController | null>(null);
  const inventoryGuard = useRef<(() => boolean) | null>(null);
  const editing = draft !== null || changing;
  const dirty = draft !== null || reason !== '';
  useEffect(() => {
    const guard = () => {
      if (inFlight.current || !(inventoryGuard.current?.() ?? true)) return false;
      return !dirty || window.confirm('採購明細或結案原因尚未儲存，確定放棄並離開嗎？');
    };
    leaveGuard.current = guard;
    const unload = (e: BeforeUnloadEvent) => { if (dirty || inFlight.current) { e.preventDefault(); e.returnValue = ''; } };
    window.addEventListener('beforeunload', unload);
    return () => { if (leaveGuard.current === guard) leaveGuard.current = null; window.removeEventListener('beforeunload', unload); };
  }, [dirty, leaveGuard]);
  async function run(action: (signal: AbortSignal) => Promise<void>) {
    if (inFlight.current) return;
    const current = new AbortController(); controller.current = current; inFlight.current = true;
    setBusy(true); setError('');
    try { await action(current.signal); }
    catch (e) { if (!current.signal.aborted) {
      if (e instanceof ApiError && e.status === 401) expired();
      else setError(e instanceof Error ? e.message : '操作失敗，請重試');
    } }
    finally { if (!current.signal.aborted) { inFlight.current = false; setBusy(false); } }
  }
  async function load(signal: AbortSignal) {
    const value = await requestJson<Purchase>(`/operations/${record.id}/purchase`, { signal });
    if (!signal.aborted) setPurchase(value);
  }
  useEffect(() => { void run(load); return () => { controller.current?.abort(); inFlight.current = false; }; }, []);
  function refresh() { void run(async signal => { await load(signal); if (!signal.aborted) onChanged?.(); }); }
  // The receipt form is hidden while editing, so its unsaved input must be released first.
  function open(start: () => void) {
    if (!purchase || !(inventoryGuard.current?.() ?? true)) return;
    setNotice(''); setError(''); start();
  }
  function startEdit() {
    open(() => {
      setFound(null); setQuery('');
      setDraft(purchase!.lines.map(line => ({ id: line.id, resource_id: line.resource_id, code: line.resource_code, title: line.resource_title,
        // Lines with any receipt or return history keep their material and unit, even when returns bring them to zero.
        quantity: line.ordered, unit: line.unit, note: line.note, received: line.received, locked: line.locked ?? Number(line.received) > 0, fixedUnit: line.locked ?? Number(line.received) > 0 })));
    });
  }
  function update(index: number, change: Partial<Draft>) { setDraft(current => current && current.map((line, i) => i === index ? { ...line, ...change } : line)); }
  async function search(signal: AbortSignal, offset = 0, q = query) {
    const value = await requestJson<{ items: Resource[]; total: number; offset: number }>(`/operations?${new URLSearchParams({ category: 'resources', q, offset: String(offset), limit: '10' })}`, { signal });
    if (!signal.aborted) { setFound(value); setSearched(q); }
  }
  function add(item: Resource) {
    void run(async signal => {
      // An existing stock unit is fixed, so the line must use it.
      const stock = await requestJson<{ unit: string | null }>(`/inventory/resources/${item.id}`, { signal });
      if (signal.aborted) return;
      setDraft(current => current && !current.some(line => line.resource_id === item.id) ? [...current, { resource_id: item.id, code: item.code, title: item.title,
        quantity: '', unit: stock.unit ?? '', note: '', received: '0.000', locked: false, fixedUnit: !!stock.unit }] : current);
    });
  }
  async function save() {
    if (!draft || !purchase) return;
    const lines = draft.map(line => ({ ...(line.id ? { id: line.id } : {}), resource_id: line.resource_id, quantity: line.quantity, unit: line.unit, note: line.note }));
    await run(async signal => {
      const value = await requestJson<Purchase>(`/operations/${record.id}/purchase/lines`, { method: 'PUT', signal, body: JSON.stringify({ expected_revision: purchase.revision, lines }) });
      if (signal.aborted) return;
      setPurchase(value); setDraft(null); setNotice(`已儲存採購明細（${value.lines.length} 列）。`);
      onChanged?.();
    });
  }
  async function changeState() {
    if (!purchase) return;
    const closing = purchase.status !== 'closed';
    if (!window.confirm(closing ? '確認結案？結案後不能再收貨或修改明細，可再重新開啟。' : '確認重新開啟採購單？')) return;
    await run(async signal => {
      const value = await requestJson<Purchase>(`/operations/${record.id}/purchase/${closing ? 'close' : 'reopen'}`, { method: 'POST', signal, body: JSON.stringify({ expected_revision: purchase.revision, reason }) });
      if (signal.aborted) return;
      setPurchase(value); setReason(''); setChanging(false); setNotice(closing ? '已結案，收貨與明細修改已鎖定。' : '已重新開啟，可繼續收貨。');
      onChanged?.();
    });
  }
  const closed = purchase?.status === 'closed';
  const done = purchase?.lines.filter(line => line.status === 'received').length ?? 0;
  const invalid = !draft || draft.some(line => !line.quantity || Number(line.quantity) <= 0 || !line.unit.trim() || (line.locked && Number(line.quantity) < Number(line.received)));
  return <section className="purchase-panel" aria-label="採購明細與收貨進度">
    <h3>採購明細與收貨進度</h3>
    {error && <p role="alert">{error}</p>}{notice && <p role="status">{notice}</p>}{busy && !purchase && <p role="status">載入中…</p>}
    {purchase && <>
      <p className={`purchase-state is-${purchase.status}`} aria-label="收貨狀態">收貨狀態：<strong>{purchase.status_label}</strong>{purchase.lines.length > 0 && `（${done}/${purchase.lines.length} 列已收齊）`}</p>
      {closed && <p>結案原因：{purchase.close_reason} · {purchase.closed_by} · {new Date(purchase.closed_at!).toLocaleString('zh-TW')}</p>}
      {purchase.status === 'no_lines' && <p>尚未建立明細。原單據欄位的文字不會自動轉成明細，請逐列選擇物料並填寫訂購數量。</p>}
      {purchase.unlinked_receipts > 0 && <p>此單有 {purchase.unlinked_receipts} 筆建立明細前的收貨，未計入明細進度，可在下方異動紀錄查看。</p>}
      {draft === null && purchase.lines.length > 0 && <ul className="purchase-lines">{purchase.lines.map(line => <li key={line.id}>
        <strong>{line.line_no}. {line.resource_code}｜{line.resource_title}</strong>
        <span>訂購 {line.ordered} {line.unit} · 已收 {line.received} · 未收 {line.remaining}{Number(line.returned ?? 0) > 0 && ` · 已退 ${line.returned}`}</span>
        <span className={`line-state is-${line.status}`}>{LINE_LABELS[line.status]}</span>
        {line.note && <span>備註：{line.note}</span>}
      </li>)}</ul>}
      {!editing && <div className="record-actions">
        {!closed && <button type="button" disabled={busy || blocked} onClick={startEdit}>{purchase.lines.length ? '編輯採購明細' : '建立採購明細'}</button>}
        <button type="button" disabled={busy || blocked} onClick={() => open(() => setChanging(true))}>{closed ? '重新開啟採購單' : '結案採購單'}</button>
        <button type="button" disabled={busy || blocked} onClick={refresh}>重新載入收貨進度</button>
      </div>}
      {draft && <fieldset className="purchase-editor" disabled={busy || blocked}><legend>編輯採購明細</legend>
        <p>每列一種物料；已有收貨或退貨紀錄的明細不能移除或改單位，訂購數量不可低於已收。實際多到貨時，先調高訂購數量再收貨；退貨後不補貨時，調低訂購數量或結案。</p>
        {draft.length === 0 && <p>尚無明細列，請搜尋物料加入。</p>}
        {draft.map((line, index) => <div className="purchase-draft" key={line.resource_id}>
          <strong>{index + 1}. {line.code}｜{line.title}</strong>
          {line.locked && <span>已收 {line.received} {line.unit}</span>}
          <label>訂購數量<input aria-label={`訂購數量 ${line.code}`} type="number" step="0.001" min={line.locked ? line.received : '0.001'} max="999999999" value={line.quantity} onChange={e => update(index, { quantity: e.target.value })} /></label>
          <label>單位<input aria-label={`單位 ${line.code}`} maxLength={20} disabled={line.fixedUnit} value={line.unit} onChange={e => update(index, { unit: e.target.value })} placeholder="例如 kg、件、箱" /></label>
          <label>備註<input aria-label={`備註 ${line.code}`} maxLength={500} value={line.note} onChange={e => update(index, { note: e.target.value })} /></label>
          <button type="button" disabled={line.locked} onClick={() => setDraft(draft.filter((_, i) => i !== index))}>移除 {line.code}</button>
        </div>)}
        <label>搜尋要加入的物料<input aria-label="搜尋明細物料" maxLength={100} value={query} onChange={e => setQuery(e.target.value)} /></label>
        <button type="button" onClick={() => void run(signal => search(signal))}>搜尋明細物料</button>
        {found && <><p>找到 {found.total} 筆物料／資源</p><ul className="purchase-found">{found.items.map(item => <li key={item.id}>
          <button type="button" disabled={draft.length >= 50 || draft.some(line => line.resource_id === item.id)} onClick={() => add(item)}>加入 {item.code}｜{item.title}</button></li>)}</ul>
          <button type="button" disabled={found.offset === 0} onClick={() => void run(signal => search(signal, found.offset - 10, searched))}>上一批明細物料</button>
          <button type="button" disabled={found.offset + 10 >= found.total} onClick={() => void run(signal => search(signal, found.offset + 10, searched))}>下一批明細物料</button></>}
        <div className="record-actions"><button type="button" className="primary" disabled={invalid} onClick={() => void save()}>儲存採購明細</button>
          <button type="button" onClick={() => { if (window.confirm('放棄尚未儲存的明細修改嗎？')) setDraft(null); }}>取消編輯明細</button></div>
      </fieldset>}
      {changing && <fieldset className="purchase-editor" disabled={busy || blocked}><legend>{closed ? '重新開啟採購單' : '結案採購單'}</legend>
        {!closed && <p>結案表示未收數量不再交貨；結案後不能收貨或修改明細，必要時可重新開啟。</p>}
        <label>{closed ? '重新開啟原因' : '結案原因'}<textarea aria-label="結案／重開原因" maxLength={500} value={reason} onChange={e => setReason(e.target.value)} /></label>
        <div className="record-actions"><button type="button" className="primary" disabled={!reason.trim()} onClick={() => void changeState()}>{closed ? '確認重新開啟' : '確認結案'}</button>
          <button type="button" onClick={() => { if (!reason || window.confirm('放棄尚未儲存的原因嗎？')) { setReason(''); setChanging(false); } }}>取消</button></div>
      </fieldset>}
      {!editing && <InventoryPanel blocked={blocked || busy} record={record} lines={purchase.lines} closed={closed} onPosted={refresh} expired={expired} leaveGuard={inventoryGuard} />}
    </>}
  </section>;
}
