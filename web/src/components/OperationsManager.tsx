import InventoryPanel from './InventoryPanel';
import PurchaseOrderPanel from './PurchaseOrderPanel';
import { useEffect, useRef, useState } from 'react';
import { ApiError, requestJson } from '../api';

type Field = { label: string; value: string };
type Write = { category: string; code: string; title: string; status: string; visibility: 'internal' | 'restricted'; fields: Field[] };
type Receiving = { status: string; label: string; lines: number; received_lines: number };
type RecordItem = Write & { id: string; revision: number; source: string; created_at: string; updated_at: string; created_by: string; updated_by: string; receiving?: Receiving };
type Catalog = { categories: { key: string; label: string; fields: string[] }[]; can_manage: boolean };
type Listing = { items: RecordItem[]; total: number; offset: number; limit: number };

export default function OperationsManager({ expired, leaveGuard, preview }: {
  expired: () => void; leaveGuard: { current: (() => boolean) | null }; preview: () => void;
}) {
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [category, setCategory] = useState('partners');
  const [query, setQuery] = useState('');
  const [listing, setListing] = useState<Listing | null>(null);
  const [selected, setSelected] = useState<RecordItem | null>(null);
  const [draft, setDraft] = useState<Write | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const inFlight = useRef(false);
  const request = useRef<AbortController | null>(null);
  const inventoryGuard = useRef<(() => boolean) | null>(null);
  const guard = () => (inventoryGuard.current?.() ?? true) && !busy && (draft === null || window.confirm('營運資料有未儲存的修改，確定放棄並離開嗎？'));
  useEffect(() => {
    leaveGuard.current = guard;
    const unload = (event: BeforeUnloadEvent) => { if (draft || busy) { event.preventDefault(); event.returnValue = ''; } };
    window.addEventListener('beforeunload', unload);
    return () => { if (leaveGuard.current === guard) leaveGuard.current = null; window.removeEventListener('beforeunload', unload); };
  }, [draft, busy, leaveGuard]);
  async function run(action: (signal: AbortSignal) => Promise<void>) {
    if (inFlight.current) return;
    const current = new AbortController(); request.current = current; inFlight.current = true;
    setBusy(true); setError(''); setNotice('');
    try { await action(current.signal); }
    catch (e) { if (!current.signal.aborted) {
      if (e instanceof ApiError && e.status === 401) expired();
      else setError(e instanceof ApiError && e.status === 409 ? '代碼重複，或這筆資料已由他人修改。輸入已保留；請檢查代碼，或複製內容後重新載入最新資料。' : e instanceof Error ? e.message : '操作失敗，請稍後再試');
    } }
    finally { if (!current.signal.aborted) { setBusy(false); inFlight.current = false; } }
  }
  async function load(signal: AbortSignal, group = category, q = query, offset = 0) {
    const result = await requestJson<Listing>(`/operations?${new URLSearchParams({ category: group, q, offset: String(offset) })}`, { signal });
    if (!signal.aborted) setListing(result);
  }
  async function initialize(signal: AbortSignal) {
    const result = await requestJson<Catalog>('/operations/catalog', { signal });
    if (signal.aborted) return;
    setCatalog(result); await load(signal);
  }
  useEffect(() => { void run(initialize); return () => { request.current?.abort(); inFlight.current = false; }; }, []);
  async function open(id: string, signal: AbortSignal) {
    const result = await requestJson<RecordItem>(`/operations/${id}`, { signal });
    if (!signal.aborted) { setSelected(result); setDraft(null); }
  }
  function changeCategory(key: string) {
    if (!guard()) return;
    setCategory(key); setQuery(''); setSelected(null); setDraft(null); setListing(null);
    void run(signal => load(signal, key, ''));
  }
  const group = catalog?.categories.find(item => item.key === category);
  const edit = (item: RecordItem) => setDraft({ category: item.category, code: item.code, title: item.title, status: item.status, visibility: item.visibility, fields: item.fields.map(field => ({ ...field })) });
  function create() {
    if (!guard()) return;
    setSelected(null); setNotice(''); setError('');
    setDraft({ category, code: '', title: '', status: '草稿', visibility: category === 'formulas' ? 'restricted' : 'internal', fields: (group?.fields ?? []).map(label => ({ label, value: '' })) });
  }
  async function save() {
    if (!draft) return;
    const editing = selected;
    await run(async signal => {
      const saved = await requestJson<RecordItem>(editing ? `/operations/${editing.id}` : '/operations', {
        method: editing ? 'PUT' : 'POST', signal, body: JSON.stringify(editing ? { ...draft, expected_revision: editing.revision } : draft),
      });
      if (signal.aborted) return;
      setSelected(saved); setDraft(null); setNotice(`已儲存 ${saved.code}｜${saved.title}（第 ${saved.revision} 版）`);
      await load(signal);
    });
  }
  return <section className="operations-manager" aria-label="正式營運資料">
    <div className="page-heading"><h2>營運資料</h2><p>維護公司的供應商、資源與單據。資料會正式保存；採購可建立明細、分批收貨並追蹤未收數量與結案，工單可領料與完工入庫，物料詳情可查看與調整庫存。「狀態」欄位仍為人工紀錄，採購收貨狀態由系統計算。</p></div>
    <div className="record-actions"><button disabled={busy} onClick={() => { if (guard()) { setDraft(null); void run(async signal => { if (!catalog) await initialize(signal); else { await load(signal); if (selected) await open(selected.id, signal); } }); } }}>重新載入營運資料</button><button disabled={busy} onClick={() => { if (guard()) preview(); }}>查看原展示示例</button></div>
    {error && <p role="alert">{error}</p>}{notice && <p role="status">{notice}</p>}{busy && <p role="status">處理中…</p>}
    {catalog && <>
      <nav className="preview-tabs" aria-label="營運分類">{catalog.categories.map(item => <button key={item.key} disabled={busy} aria-current={category === item.key ? 'page' : undefined} onClick={() => changeCategory(item.key)}>{item.label}</button>)}</nav>
      {!catalog.can_manage && <p>目前可查看公司內部紀錄；新增、編輯與機密資料由管理者或專案負責人維護。</p>}
      <div className="record-actions"><label>搜尋代碼或名稱<input maxLength={100} disabled={busy} value={query} onChange={e => setQuery(e.target.value)} /></label><button disabled={busy} onClick={() => { if (guard()) { setDraft(null); setSelected(null); void run(signal => load(signal)); } }}>搜尋</button>{catalog.can_manage && <button className="primary" disabled={busy} onClick={create}>新增{group?.label ?? '紀錄'}</button>}</div>
    </>}
    {listing && <><p>共 {listing.total} 筆符合條件的資料</p><div className="operations-list">{listing.items.map(item => <button key={item.id} disabled={busy} aria-pressed={selected?.id === item.id} onClick={() => { if (guard()) void run(signal => open(item.id, signal)); }}><strong>{item.code}｜{item.title}</strong><span>{item.status} · {item.visibility === 'restricted' ? '機密' : '公司內部'}{item.source === 'showcase' ? ' · 展示資料' : ''}</span>
        {item.receiving && <span className={`purchase-state is-${item.receiving.status}`}>收貨：{item.receiving.label}{item.receiving.lines ? `（${item.receiving.received_lines}/${item.receiving.lines} 列）` : ''}</span>}</button>)}</div>{listing.items.length === 0 && <p>目前沒有符合條件的紀錄。</p>}
      <div className="record-actions"><button disabled={busy || listing.offset === 0} onClick={() => { if (guard()) { setDraft(null); setSelected(null); void run(signal => load(signal, category, query, Math.max(0, listing.offset - listing.limit))); } }}>上一頁</button><button disabled={busy || listing.offset + listing.limit >= listing.total} onClick={() => { if (guard()) { setDraft(null); setSelected(null); void run(signal => load(signal, category, query, listing.offset + listing.limit)); } }}>下一頁</button></div></>}
    {draft ? <form className="panel operations-editor" aria-label="營運資料編輯" onSubmit={e => { e.preventDefault(); void save(); }}>
      <h3>{selected ? '編輯紀錄' : '新增紀錄'} · {group?.label}</h3>
      <label>代碼<input required maxLength={80} disabled={busy} value={draft.code} onChange={e => setDraft({ ...draft, code: e.target.value })} /></label>
      <label>名稱<input required maxLength={200} disabled={busy} value={draft.title} onChange={e => setDraft({ ...draft, title: e.target.value })} /></label>
      <label>狀態<input required maxLength={80} disabled={busy} value={draft.status} onChange={e => setDraft({ ...draft, status: e.target.value })} /></label>
      <label>可見範圍<select disabled={busy} value={draft.visibility} onChange={e => setDraft({ ...draft, visibility: e.target.value as Write['visibility'] })}><option value="internal">公司內部</option><option value="restricted">機密：僅管理者／專案負責人</option></select></label>
      <p className="muted">含價格、成本、配方比例等敏感內容時，請將整筆紀錄設為機密。</p>
      <h4>詳細欄位</h4>{draft.fields.map((field, index) => <div className="operations-field" key={index}>
        <label>欄位名稱 {index + 1}<input required maxLength={80} disabled={busy} value={field.label} onChange={e => setDraft({ ...draft, fields: draft.fields.map((f, i) => i === index ? { ...f, label: e.target.value } : f) })} /></label>
        <label>欄位內容 {index + 1}<textarea aria-label={`欄位內容 ${index + 1}`} rows={2} maxLength={4000} disabled={busy} value={field.value} onChange={e => setDraft({ ...draft, fields: draft.fields.map((f, i) => i === index ? { ...f, value: e.target.value } : f) })} /></label>
        <button type="button" disabled={busy} aria-label={`移除欄位 ${index + 1}`} onClick={() => setDraft({ ...draft, fields: draft.fields.filter((_, i) => i !== index) })}>移除欄位</button>
      </div>)}
      <button type="button" disabled={busy || draft.fields.length >= 40} onClick={() => setDraft({ ...draft, fields: [...draft.fields, { label: '', value: '' }] })}>新增欄位</button>
      <div className="record-actions"><button className="primary" disabled={busy} type="submit">{busy ? '儲存中…' : '儲存營運資料'}</button><button type="button" disabled={busy} onClick={() => { if (guard()) setDraft(null); }}>取消編輯</button></div>
    </form> : selected && <article className="panel operations-detail" aria-label="營運資料詳情">
      <h3>{selected.code}｜{selected.title}</h3><p>{selected.status} · {selected.visibility === 'restricted' ? '機密' : '公司內部'} · 第 {selected.revision} 版</p>
      {selected.source === 'showcase' && <p>來源：虛構展示資料，已保存至營運資料庫。</p>}
      <dl>{selected.fields.map(field => <div key={field.label}><dt>{field.label}</dt><dd>{field.value || '未填寫'}</dd></div>)}</dl>
      <p>建立：{selected.created_by} · {new Date(selected.created_at).toLocaleString('zh-TW')}</p><p>最後修改：{selected.updated_by} · {new Date(selected.updated_at).toLocaleString('zh-TW')}</p>
      {catalog?.can_manage && <button disabled={busy} onClick={() => { if (guard()) edit(selected); }}>編輯營運資料</button>}
      {catalog?.can_manage && selected.category === 'orders' && <PurchaseOrderPanel blocked={busy} key={selected.id} record={selected} expired={expired} leaveGuard={inventoryGuard} onChanged={() => void run(signal => load(signal))} />}
      {catalog?.can_manage && ['resources', 'work'].includes(selected.category) && <InventoryPanel blocked={busy} key={selected.id} record={selected} expired={expired} leaveGuard={inventoryGuard} />}
    </article>}
  </section>;
}
