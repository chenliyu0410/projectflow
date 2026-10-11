import { useEffect, useRef, useState } from 'react';
import { ApiError, requestJson } from '../api';

type Version = { document_id: string; version: number; filename: string; size_bytes: number; created_at: string; created_by: string; comment: string; editable: boolean };
type Listing = { items: Version[]; can_write: boolean };
type History = Listing & { current_version: number };
const ACCEPT = '.txt,.csv,.pdf,.png,.jpg,.jpeg,.docx,.xlsx,.pptx,.zip';

export default function DocumentManager({ scopePath, expired, leaveGuard }: { scopePath: string; expired: () => void; leaveGuard?: { current: (() => boolean) | null } }) {
  const [listing, setListing] = useState<Listing | null>(null);
  const [history, setHistory] = useState<History | null>(null);
  const [selected, setSelected] = useState<Version | null>(null);
  const [content, setContent] = useState<string | null>(null);
  const [draft, setDraft] = useState<string | null>(null);
  const [comment, setComment] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const controller = useRef<AbortController | null>(null);
  const inFlight = useRef(false);
  useEffect(() => {
    const guard = () => {
      if (busy) { window.alert('文件正在處理中，請稍候再離開。'); return false; }
      return draft === null || window.confirm('文件有未儲存的編輯，確定放棄並離開嗎？');
    };
    if (leaveGuard) leaveGuard.current = guard;
    const unload = (event: BeforeUnloadEvent) => { if (draft !== null || busy) { event.preventDefault(); event.returnValue = ''; } };
    window.addEventListener('beforeunload', unload);
    return () => { if (leaveGuard?.current === guard) leaveGuard.current = null; window.removeEventListener('beforeunload', unload); };
  }, [draft, busy, leaveGuard]);

  async function run(action: (signal: AbortSignal) => Promise<void>) {
    if (inFlight.current) return;
    inFlight.current = true;
    const request = new AbortController(); controller.current = request;
    setBusy(true); setError('');
    try { await action(request.signal); }
    catch (e) { if (!request.signal.aborted) {
      if (e instanceof ApiError && e.status === 401) expired();
      else setError(e instanceof ApiError && e.status === 409 ? '文件已有新版本。你的編輯仍保留，請先複製內容，再重新載入最新版本。' : e instanceof Error ? e.message : '文件操作失敗，請稍後再試');
    } }
    finally { if (!request.signal.aborted) { inFlight.current = false; setBusy(false); } }
  }
  async function load(signal: AbortSignal) {
    const value = await requestJson<Listing>(`${scopePath}/documents`, { signal });
    if (!signal.aborted) setListing(value);
  }
  useEffect(() => { void run(load); return () => { controller.current?.abort(); inFlight.current = false; }; }, [scopePath]);
  async function open(version: Version, signal: AbortSignal) {
    const value = await requestJson<History>(`/documents/${version.document_id}/versions`, { signal });
    const body = version.editable ? await requestJson<{ content: string }>(`/documents/${version.document_id}/versions/${version.version}/text`, { signal }) : null;
    if (signal.aborted) return;
    setHistory(value); setSelected(version); setContent(body?.content ?? null); setDraft(null); setComment('');
  }
  const discard = () => draft === null || window.confirm('尚有未儲存的編輯，確定放棄嗎？');
  async function upload(file: File | undefined, update: boolean) {
    if (!file) return;
    if (!file.size || file.size > 10_000_000) { setError('請選擇非空且不超過 10 MB 的檔案'); return; }
    if (!discard()) return;
    await run(async signal => {
      const query = new URLSearchParams({ filename: file.name, comment });
      if (update && history) query.set('expected_version', String(history.current_version));
      const path = update && selected ? `/documents/${selected.document_id}/versions` : `${scopePath}/documents`;
      const saved = await requestJson<Version>(`${path}?${query}`, { method: 'POST', headers: { 'Content-Type': 'application/octet-stream' }, body: file, signal });
      if (signal.aborted) return;
      setNotice(`已儲存 ${saved.filename}，版本 v${saved.version}`); setDraft(null);
      await load(signal); await open(saved, signal);
    });
  }
  async function saveText() {
    if (!selected || !history || draft === null) return;
    if (new TextEncoder().encode(draft).length > 1_000_000) { setError('文字編輯上限為 1 MB'); return; }
    await run(async signal => {
      const saved = await requestJson<Version>(`/documents/${selected.document_id}/text`, { method: 'POST', body: JSON.stringify({ expected_version: history.current_version, content: draft, comment }), signal });
      if (signal.aborted) return;
      setDraft(null); setNotice(`已儲存新版本 v${saved.version}，舊版本已保留`);
      await load(signal); await open(saved, signal);
    });
  }
  return <section className="panel document-manager" aria-label="正式文件管理">
    <h2>文件管理</h2><p className="muted">此專案或任務的文件會正式保存。TXT／CSV（1 MB 內）可直接編輯；其他格式請下載修改後上傳新版本。單檔上限 10 MB。</p>
    {error && <p role="alert">{error}</p>}{notice && <p role="status">{notice}</p>}
    <div className="record-actions"><button disabled={busy} onClick={() => { if (discard()) void run(async signal => { await load(signal); if (selected) { const latest = await requestJson<History>(`/documents/${selected.document_id}/versions`, { signal }); if (latest.items[0]) await open(latest.items[0], signal); } }); }}>重新載入文件</button>
      {listing?.can_write && <label>上傳新文件<input aria-label="上傳新文件" type="file" accept={ACCEPT} disabled={busy} onChange={e => { const file = e.target.files?.[0]; e.target.value = ''; void upload(file, false); }} /></label>}
    </div>
    {!listing ? <p>{busy ? '載入文件中…' : '尚未載入文件，請重試。'}</p> : <>
      {!listing.can_write && <p>目前僅可檢視與下載文件。</p>}
      {listing.items.length === 0 && <p>目前沒有文件。有編輯權限的人員可上傳第一份文件。</p>}
      <div className="document-list">{listing.items.map(v => <button key={v.document_id} disabled={busy} aria-pressed={selected?.document_id === v.document_id} onClick={() => { if (discard()) void run(signal => open(v, signal)); }}><strong>{v.filename}</strong><span>v{v.version} · {v.created_by} · {new Date(v.created_at).toLocaleString('zh-TW')}</span></button>)}</div>
    </>}
    {selected && history && <article className="document-detail"><h3>{selected.filename}</h3>
      <label>版本紀錄<select aria-label="版本紀錄" disabled={busy} value={selected.version} onChange={e => { const v = history.items.find(row => row.version === Number(e.target.value)); if (v && discard()) void run(signal => open(v, signal)); }}>{history.items.map(v => <option key={v.version} value={v.version}>v{v.version} · {v.created_by} · {new Date(v.created_at).toLocaleString('zh-TW')}</option>)}</select></label>
      <p>{selected.version === history.current_version ? '目前版本' : '歷史版本（唯讀）'} · {selected.size_bytes.toLocaleString()} bytes</p>
      <p>版本說明：{selected.comment || '未填寫'}</p>
      <a href={`/api/documents/${selected.document_id}/versions/${selected.version}/download`}>下載 v{selected.version}</a>
      {content !== null && draft === null && <pre className="document-text">{content}</pre>}
      {content === null && <p>此檔案請下載查看；原始檔案與歷史版本均已保存。</p>}
      {history.can_write && selected.version === history.current_version && <>
        {draft !== null ? <><label>編輯文件內容<textarea aria-label="編輯文件內容" rows={14} value={draft} disabled={busy} onChange={e => setDraft(e.target.value)} /></label></> : selected.editable && content !== null && <button disabled={busy} onClick={() => setDraft(content)}>編輯文字</button>}
        <label>新版本說明<input maxLength={500} value={comment} disabled={busy} onChange={e => setComment(e.target.value)} /></label>
        {draft !== null ? <div className="record-actions"><button disabled={busy || !draft.length} onClick={() => void saveText()}>{busy ? '儲存中…' : '儲存新版本'}</button><button disabled={busy} onClick={() => { if (discard()) setDraft(null); }}>取消編輯</button></div> : <label>上傳新版本<input type="file" aria-label="上傳新版本" accept={ACCEPT} disabled={busy} onChange={e => { const file = e.target.files?.[0]; e.target.value = ''; void upload(file, true); }} /></label>}
      </>}
    </article>}
  </section>;
}
