import { useEffect, useRef, useState } from 'react';
import { ApiError, requestJson } from '../api';
import InventoryPanel, { type ProgressLine } from './InventoryPanel';

type Resource = { id: string; code: string; title: string };
type Production = {
  work_id: string; revision: number; status: 'no_plan' | 'planned' | 'in_progress' | 'completed' | 'closed'; status_label: string;
  product: Resource | null; unit: string | null; planned: string | null; completed: string | null; remaining: string | null; note: string;
  closed_at: string | null; closed_by: string | null; close_reason: string | null; unlinked_completions: number;
  issued: { resource_id: string; code: string; title: string; unit: string; quantity: string }[];
};
type Draft = { product: Resource | null; quantity: string; unit: string; note: string; fixedUnit: boolean; locked: boolean };

export default function WorkOrderPanel({ record, expired, leaveGuard, blocked = false, onChanged }: {
  record: Resource & { category: string }; expired: () => void; leaveGuard: { current: (() => boolean) | null };
  blocked?: boolean; onChanged?: () => void;
}) {
  const [production, setProduction] = useState<Production | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
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
      return !dirty || window.confirm('生產計畫或結案原因尚未儲存，確定放棄並離開嗎？');
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
    const value = await requestJson<Production>(`/operations/${record.id}/production`, { signal });
    if (!signal.aborted) setProduction(value);
  }
  useEffect(() => { void run(load); return () => { controller.current?.abort(); inFlight.current = false; }; }, []);
  function refresh() { void run(async signal => { await load(signal); if (!signal.aborted) onChanged?.(); }); }
  // The posting form is hidden while editing, so its unsaved input must be released first.
  function open(start: () => void) {
    if (!production || !(inventoryGuard.current?.() ?? true)) return;
    setNotice(''); setError(''); start();
  }
  function startEdit() {
    open(() => {
      const locked = Number(production!.completed ?? 0) > 0;
      setFound(null); setQuery('');
      setDraft({ product: production!.product, quantity: production!.planned ?? '', unit: production!.unit ?? '', note: production!.note, fixedUnit: locked, locked });
    });
  }
  async function search(signal: AbortSignal, offset = 0, q = query) {
    const value = await requestJson<{ items: Resource[]; total: number; offset: number }>(`/operations?${new URLSearchParams({ category: 'resources', q, offset: String(offset), limit: '10' })}`, { signal });
    if (!signal.aborted) { setFound(value); setSearched(q); }
  }
  function choose(item: Resource) {
    void run(async signal => {
      // An existing stock unit is fixed, so the plan must use it.
      const stock = await requestJson<{ unit: string | null }>(`/inventory/resources/${item.id}`, { signal });
      if (signal.aborted) return;
      setDraft(current => current && { ...current, product: item, unit: stock.unit ?? (current.product?.id === item.id ? current.unit : ''), fixedUnit: !!stock.unit });
    });
  }
  async function save() {
    if (!draft?.product || !production) return;
    const payload = { expected_revision: production.revision, product_id: draft.product.id, quantity: draft.quantity, unit: draft.unit, note: draft.note };
    await run(async signal => {
      const value = await requestJson<Production>(`/operations/${record.id}/production/plan`, { method: 'PUT', signal, body: JSON.stringify(payload) });
      if (signal.aborted) return;
      setProduction(value); setDraft(null); setNotice('已儲存生產計畫。');
      onChanged?.();
    });
  }
  async function changeState() {
    if (!production) return;
    const closing = production.status !== 'closed';
    if (!window.confirm(closing ? '確認結案？結案後不能再領料、完工或修改計畫，可再重新開啟。' : '確認重新開啟工單？')) return;
    await run(async signal => {
      const value = await requestJson<Production>(`/operations/${record.id}/production/${closing ? 'close' : 'reopen'}`, { method: 'POST', signal, body: JSON.stringify({ expected_revision: production.revision, reason }) });
      if (signal.aborted) return;
      setProduction(value); setReason(''); setChanging(false); setNotice(closing ? '已結案，領料、完工與計畫修改已鎖定。' : '已重新開啟，可繼續生產。');
      onChanged?.();
    });
  }
  const closed = production?.status === 'closed';
  const plan: ProgressLine[] = production?.product ? [{ id: 'plan', line_no: 1, resource_id: production.product.id, resource_code: production.product.code,
    resource_title: production.product.title, unit: production.unit!, ordered: production.planned!, received: production.completed!, remaining: production.remaining!, note: production.note,
    status: Number(production.remaining) <= 0 ? 'received' : Number(production.completed) > 0 ? 'partial' : 'pending' }] : [];
  const invalid = !draft?.product || !draft.quantity || Number(draft.quantity) <= 0 || !draft.unit.trim()
    || (draft.locked && Number(draft.quantity) < Number(production?.completed ?? 0));
  return <section className="purchase-panel" aria-label="工單計畫與產量">
    <h3>工單計畫與產量</h3>
    {error && <p role="alert">{error}</p>}{notice && <p role="status">{notice}</p>}{busy && !production && <p role="status">載入中…</p>}
    {production && <>
      <p className={`purchase-state is-${production.status}`} aria-label="生產狀態">生產狀態：<strong>{production.status_label}</strong>{production.product && `（已完工 ${production.completed}／計畫 ${production.planned} ${production.unit}）`}</p>
      {closed && <p>結案原因：{production.close_reason} · {production.closed_by} · {new Date(production.closed_at!).toLocaleString('zh-TW')}</p>}
      {production.product ? <dl className="production-plan">
        <div><dt>成品</dt><dd>{production.product.code}｜{production.product.title}</dd></div>
        <div><dt>計畫／已完工／尚差</dt><dd>{production.planned} / {production.completed} / {production.remaining} {production.unit}</dd></div>
        {production.note && <div><dt>備註</dt><dd>{production.note}</dd></div>}
      </dl> : <p>尚未設定生產計畫。原工單欄位的文字不會自動轉成計畫，請指定成品與計畫產量。</p>}
      {production.unlinked_completions > 0 && <p>此工單有 {production.unlinked_completions} 筆設定計畫前的完工入庫，未計入計畫進度，可在下方異動紀錄查看。</p>}
      <h4>累計領料</h4>
      {production.issued.length ? <ul className="purchase-lines" aria-label="累計領料">{production.issued.map(item => <li key={`${item.resource_id}-${item.unit}`}>
        <strong>{item.code}｜{item.title}</strong><span>已領 {item.quantity} {item.unit}</span></li>)}</ul> : <p>尚無領料紀錄。</p>}
      {!editing && <div className="record-actions">
        {!closed && <button type="button" disabled={busy || blocked} onClick={startEdit}>{production.product ? '編輯生產計畫' : '設定生產計畫'}</button>}
        <button type="button" disabled={busy || blocked} onClick={() => open(() => setChanging(true))}>{closed ? '重新開啟工單' : '結案工單'}</button>
        <button type="button" disabled={busy || blocked} onClick={refresh}>重新載入生產進度</button>
      </div>}
      {draft && <fieldset className="purchase-editor" disabled={busy || blocked}><legend>編輯生產計畫</legend>
        <p>已有完工入庫時不能更換成品或單位，計畫產量不可低於已完工。實際多產出時，先調高計畫產量再完工入庫。</p>
        <p aria-label="計畫成品">成品：{draft.product ? `${draft.product.code}｜${draft.product.title}` : '尚未選擇'}</p>
        {!draft.locked && <>
          <label>搜尋成品<input aria-label="搜尋成品" maxLength={100} value={query} onChange={e => setQuery(e.target.value)} /></label>
          <button type="button" onClick={() => void run(signal => search(signal))}>搜尋成品</button>
          {found && <><p>找到 {found.total} 筆物料／資源</p><ul className="purchase-found">{found.items.map(item => <li key={item.id}>
            <button type="button" aria-pressed={draft.product?.id === item.id} onClick={() => choose(item)}>選擇 {item.code}｜{item.title}</button></li>)}</ul>
            <button type="button" disabled={found.offset === 0} onClick={() => void run(signal => search(signal, found.offset - 10, searched))}>上一批成品</button>
            <button type="button" disabled={found.offset + 10 >= found.total} onClick={() => void run(signal => search(signal, found.offset + 10, searched))}>下一批成品</button></>}
        </>}
        <label>計畫產量<input aria-label="計畫產量" type="number" step="0.001" min={draft.locked ? production.completed ?? '0.001' : '0.001'} max="999999999" value={draft.quantity} onChange={e => setDraft({ ...draft, quantity: e.target.value })} /></label>
        <label>成品單位<input aria-label="成品單位" maxLength={20} disabled={draft.fixedUnit} value={draft.unit} onChange={e => setDraft({ ...draft, unit: e.target.value })} placeholder="例如 罐、件、箱" /></label>
        <label>計畫備註<input aria-label="計畫備註" maxLength={500} value={draft.note} onChange={e => setDraft({ ...draft, note: e.target.value })} /></label>
        <div className="record-actions"><button type="button" className="primary" disabled={invalid} onClick={() => void save()}>儲存生產計畫</button>
          <button type="button" onClick={() => { if (window.confirm('放棄尚未儲存的計畫修改嗎？')) setDraft(null); }}>取消編輯計畫</button></div>
      </fieldset>}
      {changing && <fieldset className="purchase-editor" disabled={busy || blocked}><legend>{closed ? '重新開啟工單' : '結案工單'}</legend>
        {!closed && <p>結案表示此工單不再生產；結案後不能領料、完工或修改計畫，必要時可重新開啟。</p>}
        <label>{closed ? '重新開啟原因' : '結案原因'}<textarea aria-label="結案／重開原因" maxLength={500} value={reason} onChange={e => setReason(e.target.value)} /></label>
        <div className="record-actions"><button type="button" className="primary" disabled={!reason.trim()} onClick={() => void changeState()}>{closed ? '確認重新開啟' : '確認結案'}</button>
          <button type="button" onClick={() => { if (!reason || window.confirm('放棄尚未儲存的原因嗎？')) { setReason(''); setChanging(false); } }}>取消</button></div>
      </fieldset>}
      {!editing && <InventoryPanel blocked={blocked || busy} record={record} lines={plan} closed={closed} onPosted={refresh} expired={expired} leaveGuard={inventoryGuard} />}
    </>}
  </section>;
}
