import { useEffect, useRef, useState } from 'react';
import { ApiError, KNOWN_CONFLICTS, newId, requestJson } from '../api';

type Resource = { id: string; code: string; title: string };
/** A purchase line, or a work order's planned product, that postings count toward. */
export type ProgressLine = { id: string; line_no: number; resource_id: string; resource_code: string; resource_title: string; unit: string; ordered: string; received: string; remaining: string; note: string; status: 'pending' | 'partial' | 'received'; returned?: string; locked?: boolean };
/** Net issued material of a work order, which material returns can bring back to stock. */
export type IssuedMaterial = { resource_id: string; code: string; title: string; unit: string; quantity: string; returned?: string };
type Movement = { id: string; kind: string; resource_label: string; order_label: string | null; work_label: string | null; quantity: string; unit: string; before: string; after: string; reason: string; actor_name: string; created_at: string; reversed_by?: string | null; reversed_kind?: string | null };
type History = { items: Movement[]; total: number; offset: number; limit: number };
type Stock = { quantity: string; unit: string | null };
type Payload = { request_id: string; resource_id: string; quantity: string; unit: string; reason: string };
type Mode = 'receipts' | 'returns' | 'issues' | 'issue-returns' | 'completions' | 'adjustments';
/** A source the posting must pick: a purchase line, the planned product or an issued material, with its upper limit. */
type Choice = { key: string; resource: Resource; unit: string; cap: string; text: string; disabled: boolean; hintLabel: string; hint: string };
/** requestId is kept while the outcome is uncertain, so a retry reuses it. */
type Reversal = { id: string; label: string; reason: string; requestId: string | null };

const KIND_LABELS: Record<string, string> = { receipt: '採購收貨', return: '採購退貨', issue: '工單領料', issue_return: '工單退料', completion: '完工入庫', adjustment: '庫存調整', reversal: '沖銷' };
const ACTIONS: Record<Mode, string> = { receipts: '收貨入庫', returns: '採購退貨', issues: '工單領料', 'issue-returns': '工單退料', completions: '完工入庫', adjustments: '庫存調整' };
const OVER: Partial<Record<Mode, string>> = {
  receipts: '超過未收數量；實際多到貨請先修改採購明細的訂購數量。',
  returns: '超過已收數量，不能退貨。',
  completions: '超過計畫剩餘產量；實際多產出請先調高工單計畫產量。',
  'issue-returns': '超過本工單淨領料，不能退料。',
};

function choicesFor(mode: Mode, lines: ProgressLine[] | null, issued: IssuedMaterial[] | null): Choice[] | null {
  const of = (line: ProgressLine) => ({ id: line.resource_id, code: line.resource_code, title: line.resource_title });
  if (lines?.length && mode === 'receipts') return lines.map(line => ({ key: line.id, resource: of(line), unit: line.unit, cap: line.remaining,
    text: line.status === 'received' ? '已收齊' : `未收 ${line.remaining} ${line.unit}`, disabled: line.status === 'received',
    hintLabel: '本次可收', hint: `本次最多可收 ${line.remaining} ${line.unit}（訂購 ${line.ordered}，已收 ${line.received}）` }));
  if (lines?.length && mode === 'returns') return lines.map(line => ({ key: line.id, resource: of(line), unit: line.unit, cap: line.received,
    text: Number(line.received) > 0 ? `可退 ${line.received} ${line.unit}` : '尚無可退數量', disabled: Number(line.received) <= 0,
    hintLabel: '本次可退', hint: `本次最多可退 ${line.received} ${line.unit}（已收 ${line.received}，已退 ${line.returned ?? '0.000'}）` }));
  if (lines?.length && mode === 'completions') return lines.map(line => ({ key: line.id, resource: of(line), unit: line.unit, cap: line.remaining,
    text: line.status === 'received' ? '已達計畫產量' : `尚可完工 ${line.remaining} ${line.unit}`, disabled: line.status === 'received',
    hintLabel: '本次可完工', hint: `本次最多可完工 ${line.remaining} ${line.unit}（計畫 ${line.ordered}，已完工 ${line.received}）` }));
  if (issued && mode === 'issue-returns') return issued.map(item => ({ key: item.resource_id, resource: { id: item.resource_id, code: item.code, title: item.title }, unit: item.unit,
    cap: item.quantity, text: Number(item.quantity) > 0 ? `可退 ${item.quantity} ${item.unit}` : '已全數退回', disabled: Number(item.quantity) <= 0,
    hintLabel: '本次可退', hint: `本次最多可退 ${item.quantity} ${item.unit}（本工單淨領料）` }));
  return null;
}

export default function InventoryPanel({ record, expired, leaveGuard, blocked = false, lines = null, issued = null, closed = false, onPosted }: {
  blocked?: boolean; record: Resource & { category: string }; expired: () => void; leaveGuard: { current: (() => boolean) | null };
  /** Progress lines: receipts, returns, or completions of a planned work order pick a line instead of searching all resources. */
  lines?: ProgressLine[] | null; issued?: IssuedMaterial[] | null; closed?: boolean; onPosted?: () => void;
}) {
  const receipt = record.category === 'orders';
  const work = record.category === 'work';
  const picking = receipt || work;
  const [mode, setMode] = useState<Mode>(work ? 'issues' : receipt ? 'receipts' : 'adjustments');
  const choices = choicesFor(mode, lines, issued);
  const [choiceKey, setChoiceKey] = useState<string | null>(null);
  const choice = choices?.find(item => item.key === choiceKey) ?? null;
  const actionName = ACTIONS[mode];
  const searchLabel = work ? '搜尋物料或成品' : mode === 'returns' ? '搜尋退貨物料' : '搜尋收貨物料';
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
  const [reversal, setReversal] = useState<Reversal | null>(null);
  const inFlight = useRef(false);
  const controller = useRef<AbortController | null>(null);
  const dirty = quantity !== '' || reason !== '' || !!reversal?.reason;
  const overLine = !!choice && quantity !== '' && Number(quantity) > Number(choice.cap);
  useEffect(() => {
    const guard = () => {
      if (inFlight.current) return false;
      if (pending || reversal?.requestId) { window.alert('入帳或沖銷結果待確認，請先重試相同操作；系統會防止重複記帳。'); return false; }
      return !dirty || window.confirm('入帳內容或沖銷原因尚未儲存，確定放棄並離開嗎？');
    };
    leaveGuard.current = guard;
    const unload = (e: BeforeUnloadEvent) => { if (dirty || pending || reversal?.requestId || inFlight.current) { e.preventDefault(); e.returnValue = ''; } };
    window.addEventListener('beforeunload', unload);
    return () => { if (leaveGuard.current === guard) leaveGuard.current = null; window.removeEventListener('beforeunload', unload); };
  }, [dirty, pending, reversal, leaveGuard]);
  async function run(action: (signal: AbortSignal) => Promise<void>, failed = '未入帳') {
    if (inFlight.current) return;
    const current = new AbortController(); controller.current = current; inFlight.current = true;
    setBusy(true); setError('');
    try { await action(current.signal); }
    catch (e) { if (!current.signal.aborted) {
      if (e instanceof ApiError && e.status === 401) expired();
      else setError(e instanceof ApiError && e.status === 409 ? KNOWN_CONFLICTS.has(e.message) ? `${failed}：${e.message}。`
        : failed === '未沖銷' ? '未沖銷：庫存或相關進度已變更，請重新載入後確認。' : '未入帳：庫存不足、單位不符或操作內容衝突。請確認數量及既有單位。'
        : e instanceof Error ? e.message : '操作失敗，請重試');
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
  function pick(item: Choice) {
    setChoiceKey(item.key); setResource(item.resource); setStock(null); setUnit(item.unit);
    // The choice fixes the unit; the server still checks it against the stock unit.
    void run(async signal => { await loadStock(item.resource, signal); if (!signal.aborted) setUnit(item.unit); });
  }
  useEffect(() => { void run(async signal => { await loadHistory(signal); if (!picking) await loadStock(record, signal); });
    return () => { controller.current?.abort(); inFlight.current = false; }; }, []);
  async function search(signal: AbortSignal, offset = 0, q = query) {
    const value = await requestJson<{ items: Resource[]; total: number; offset: number }>(`/operations?${new URLSearchParams({ category: 'resources', q, offset: String(offset), limit: '10' })}`, { signal });
    if (!signal.aborted) { setResources(value); setSearched(q); }
  }
  async function submit() {
    // An uncertain posting is always retried as-is; the server returns the original entry if it was saved.
    if (!resource || blocked || (!pending && (closed || overLine)) || inFlight.current) return;
    const payload = pending ?? { request_id: newId(), resource_id: resource.id, quantity, unit, reason };
    if (!pending && !window.confirm(`確認${actionName}：${resource.code}，${quantity} ${unit}？此筆異動會永久保留。`)) return;
    setPending(payload); setNotice('');
    await run(async signal => {
      try {
        await requestJson<Movement>(picking ? `/operations/${record.id}/${mode}` : '/inventory/adjustments', { method: 'POST', body: JSON.stringify(payload), signal });
      } catch (e) {
        if (e instanceof ApiError && [400, 401, 403, 404, 409, 422].includes(e.status)) setPending(null);
        // A rejection may come from progress or closing done elsewhere; refresh what the parent shows.
        if (e instanceof ApiError && e.status === 409) onPosted?.();
        throw e;
      }
      if (signal.aborted) return;
      setPending(null); setQuantity(''); setReason(''); setNotice('已入帳，庫存與異動紀錄已保存。');
      onPosted?.();
      await loadStock(resource, signal); await loadHistory(signal);
    });
  }
  function startReversal(item: Movement) {
    setError(''); setNotice('');
    setReversal({ id: item.id, label: `${KIND_LABELS[item.kind] ?? '庫存調整'} ${item.resource_label} ${item.quantity} ${item.unit}`, reason: '', requestId: null });
  }
  async function submitReversal() {
    if (!reversal || blocked || inFlight.current || !reversal.reason.trim()) return;
    if (!reversal.requestId && !window.confirm(`確認沖銷「${reversal.label}」？會新增一筆反向流水，原紀錄保留不改。`)) return;
    const target = { ...reversal, requestId: reversal.requestId ?? newId() };
    setReversal(target); setNotice('');
    await run(async signal => {
      try {
        await requestJson<Movement>(`/inventory/movements/${target.id}/reversal`, { method: 'POST', body: JSON.stringify({ request_id: target.requestId, reason: target.reason }), signal });
      } catch (e) {
        if (e instanceof ApiError && [400, 401, 403, 404, 409, 422].includes(e.status)) setReversal({ ...target, requestId: null });
        if (e instanceof ApiError && e.status === 409) onPosted?.();
        throw e;
      }
      if (signal.aborted) return;
      setReversal(null); setNotice('已沖銷，庫存與相關進度已回復；原紀錄保留。');
      onPosted?.();
      if (resource) await loadStock(resource, signal);
      await loadHistory(signal);
    }, '未沖銷');
  }
  return <fieldset className="inventory-shell" disabled={blocked}><section className="inventory-panel" aria-label="收貨與庫存">
    <h3>{work ? '工單領料與完工入庫' : receipt ? '採購收貨' : '庫存與異動'}</h3>
    <p>收貨、退貨、領料、退料、完工入庫、調整及沖銷才會異動庫存；原單據文字不計入庫存。最多三位小數，首次入帳後固定物料單位。</p>
    {receipt && mode === 'receipts' && (lines?.length ? <p>依採購明細收貨：只能收明細內物料，可分次收貨，累計不得超過訂購數量。</p>
      : <p>此單尚未建立採購明細：可分次自由收貨，不檢查訂購數量，也不計入收貨進度。</p>)}
    {receipt && mode === 'returns' && (lines?.length ? <p>採購退貨：只能退明細內物料，數量不超過該列已收；退貨後未收數量恢復，可等待補貨，不補貨請調低訂購數量或結案。建立明細前的自由收貨請在異動紀錄用沖銷更正。</p>
      : <p>此單尚未建立採購明細：可退回本單收過的物料，數量不超過本單淨收貨。</p>)}
    {receipt && closed && <p role="status">採購單已結案，不能再收貨；如需補收請先重新開啟。</p>}
    {work && (mode === 'issue-returns' ? <p>退料只能退回本工單已領的物料，數量不超過淨領料，退料後加回庫存。</p>
      : lines?.length ? <p>領料可選任何物料並分次入帳；完工入庫只能選工單指定成品，累計不得超過計畫產量。不依配方自動扣料。</p>
      : <p>先選領料或完工入庫，再選物料或成品。此工單尚未設定生產計畫：可分批自由入帳，不計入計畫產量，不依配方自動扣料。</p>)}
    {work && closed && <p role="status">工單已結案，不能再領料或完工；如需補登請先重新開啟。</p>}
    {error && <p role="alert">{error}</p>}{notice && <p role="status">{notice}</p>}
    {pending && <p role="alert">{busy ? '入帳處理中…' : '入帳結果待確認，請重試相同入帳，不要另外新增同一筆收貨。'}</p>}
    <fieldset disabled={busy || !!pending || closed}><legend>{work ? actionName : receipt ? mode === 'returns' ? '採購退貨' : '收貨明細' : '盤點／補正調整'}</legend>
      {picking && <label>{work ? '工單操作' : '採購操作'}<select aria-label={work ? '工單操作' : '採購操作'} value={mode} onChange={e => {
        if (dirty && !window.confirm('切換操作會清除尚未保存的輸入，確定切換嗎？')) return;
        setMode(e.target.value as Mode); setResource(null); setChoiceKey(null); setStock(null); setQuantity(''); setReason(''); setUnit(''); setResources(null); setQuery(''); setNotice('');
      }}>{work ? <><option value="issues">領料扣庫存</option><option value="issue-returns">退料回庫存</option><option value="completions">完工入庫</option></>
        : <><option value="receipts">收貨入庫</option><option value="returns">採購退貨</option></>}</select></label>}
      {choices && <><p>{mode === 'completions' ? '工單指定成品' : mode === 'issue-returns' ? '選擇要退回的領料' : mode === 'returns' ? '選擇退貨明細' : '選擇收貨明細'}</p>
        {choices.length === 0 && <p>本工單尚無領料，無法退料。</p>}
        <ul className="receipt-lines">{choices.map(item => <li key={item.key}><button type="button" aria-pressed={choiceKey === item.key}
          disabled={item.disabled} onClick={() => pick(item)}>{item.resource.code}｜{item.resource.title} · {item.text}</button></li>)}</ul></>}
      {picking && !choices && <><label>{searchLabel}<input aria-label={searchLabel} maxLength={100} value={query} onChange={e => setQuery(e.target.value)} /></label>
        <button type="button" onClick={() => void run(signal => search(signal))}>搜尋物料</button>
        {resources && <><p>找到 {resources.total} 筆物料／資源</p><ul>{resources.items.map(item => <li key={item.id}><button type="button" aria-pressed={resource?.id === item.id} onClick={() => { setResource(item); setStock(null); setUnit(''); void run(signal => loadStock(item, signal)); }}>{item.code}｜{item.title}</button></li>)}</ul>
          <button type="button" disabled={resources.offset === 0} onClick={() => void run(signal => search(signal, resources.offset - 10, searched))}>上一批物料</button>
          <button type="button" disabled={resources.offset + 10 >= resources.total} onClick={() => void run(signal => search(signal, resources.offset + 10, searched))}>下一批物料</button></>}
      </>}
      {resource && <p>物料：{resource.code}｜{resource.title}</p>}
      {stock && <p aria-label="目前庫存">目前庫存：{stock.quantity} {stock.unit ?? '（尚未設定單位）'}</p>}
      <label>{work || mode === 'returns' ? `${actionName}數量（請填正數）` : receipt ? '實收數量' : '調整數量（增加為正、減少為負）'}<input aria-label="異動數量" type="number" step="0.001" min={picking ? '0.001' : '-999999999'} max="999999999" value={quantity} onChange={e => setQuantity(e.target.value)} /></label>
      {choice && <p aria-label={choice.hintLabel}>{choice.hint}</p>}
      {overLine && <p role="alert">{OVER[mode]}</p>}
      <label>庫存單位<input aria-label="庫存單位" maxLength={20} disabled={!!stock?.unit || !!choice} value={unit} onChange={e => setUnit(e.target.value)} placeholder="例如 kg、件、箱" /></label>
      <label>異動原因／收貨說明<textarea aria-label="異動原因／收貨說明" maxLength={500} value={reason} onChange={e => setReason(e.target.value)} /></label>
    </fieldset>
    <button type="button" className="primary" disabled={busy || (!pending && (closed || overLine || (!!choices && !choice))) || !resource || !stock || !quantity || !unit.trim() || !reason.trim()} onClick={() => void submit()}>{pending ? '重試相同入帳' : picking && mode !== 'receipts' ? `確認${actionName}` : receipt ? '確認收貨入庫' : '儲存庫存調整'}</button>
    <button type="button" disabled={busy || !!pending} onClick={() => void run(async signal => { await loadHistory(signal); if (resource) await loadStock(resource, signal); })}>重新載入庫存與紀錄</button>
    <h4>異動紀錄{history ? `（${history.total}）` : ''}</h4>
    {reversal && <fieldset className="purchase-editor reversal-editor" disabled={busy}><legend>沖銷異動</legend>
      <p>將新增一筆數量相同、方向相反的沖銷流水抵銷「{reversal.label}」，原紀錄保留不改；同一筆只能沖銷一次，沖銷紀錄不能再沖銷。</p>
      {reversal.requestId && <p role="alert">{busy ? '沖銷處理中…' : '沖銷結果待確認，請重試相同沖銷，不要另外新增沖銷。'}</p>}
      <label>沖銷原因<textarea aria-label="沖銷原因" maxLength={500} disabled={!!reversal.requestId} value={reversal.reason} onChange={e => setReversal({ ...reversal, reason: e.target.value })} /></label>
      <div className="record-actions"><button type="button" className="primary" disabled={!reversal.reason.trim()} onClick={() => void submitReversal()}>{reversal.requestId ? '重試相同沖銷' : '確認沖銷'}</button>
        <button type="button" disabled={!!reversal.requestId} onClick={() => { if (!reversal.reason || window.confirm('放棄尚未送出的沖銷嗎？')) setReversal(null); }}>取消沖銷</button></div>
    </fieldset>}
    {history?.total === 0 && <p>尚無異動紀錄。</p>}
    <ul className="inventory-history">{history?.items.map(item => <li key={item.id}>
      <strong>{KIND_LABELS[item.kind] ?? '庫存調整'}{item.kind === 'reversal' && item.reversed_kind ? `（${KIND_LABELS[item.reversed_kind] ?? '異動'}）` : ''} · {item.resource_label}</strong>
      <p>{item.quantity} {item.unit} · 庫存 {item.before} → {item.after}</p><p>來源：{item.work_label ?? item.order_label ?? '人工調整'} · {item.reason}</p><p>{item.actor_name} · {new Date(item.created_at).toLocaleString('zh-TW')}</p>
      {item.reversed_by && <p className="reversed-tag">已沖銷</p>}
      {item.kind !== 'reversal' && !item.reversed_by && <button type="button" disabled={busy || !!pending || closed || !!reversal} onClick={() => startReversal(item)}>沖銷此筆</button>}
    </li>)}</ul>
    {history && <><button type="button" disabled={busy || !!pending || history.offset === 0} onClick={() => void run(signal => loadHistory(signal, history.offset - history.limit))}>上一頁異動</button><button type="button" disabled={busy || !!pending || history.offset + history.limit >= history.total} onClick={() => void run(signal => loadHistory(signal, history.offset + history.limit))}>下一頁異動</button></>}
  </section></fieldset>;
}
