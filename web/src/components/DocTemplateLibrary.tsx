import { useEffect, useRef, useState } from 'react';
import { ApiError, requestJson } from '../api';
import type { DocTemplate, TemplateField } from './DocTemplateFill';

const TYPES: Record<TemplateField['type'], string> = { text: '文字', textarea: '多行文字', number: '數字', date: '日期', select: '下拉選項' };
const ROUNDING = { half_up: '四捨五入', down: '無條件捨去', up: '無條件進位' };
type Listing = { items: DocTemplate[]; can_manage: boolean };
type Draft = { name: string; category: string; numbering: string; tax_rate: string; rounding: DocTemplate['rounding']; fields: (TemplateField & { optionText: string })[] };

const binary = { 'Content-Type': 'application/octet-stream' };

/** Company document templates; only system administrators manage them (D77). */
export default function DocTemplateLibrary({ expired }: { expired: () => void }) {
  const [listing, setListing] = useState<Listing | null>(null);
  const [editing, setEditing] = useState<DocTemplate | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [name, setName] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const inFlight = useRef(false);

  async function run(action: () => Promise<void>) {
    if (inFlight.current) return;
    inFlight.current = true; setBusy(true); setError('');
    try { await action(); }
    catch (e) { if (e instanceof ApiError && e.status === 401) expired(); else setError(e instanceof ApiError && e.status === 409 ? '樣板已被修改，請重新載入後再編輯' : e instanceof Error ? e.message : '樣板操作失敗，請稍後再試'); }
    finally { inFlight.current = false; setBusy(false); }
  }
  async function load() { setListing(await requestJson<Listing>('/document-templates')); }
  useEffect(() => { void run(load); }, []);

  function edit(template: DocTemplate) {
    setEditing(template); setNotice('');
    setDraft({ name: template.name, category: template.category, numbering: template.numbering, tax_rate: template.tax_rate, rounding: template.rounding,
      fields: template.fields.map(f => ({ ...f, optionText: f.options.join('、') })) });
  }
  function setField(index: number, change: Partial<Draft['fields'][number]>) {
    setDraft(d => d && { ...d, fields: d.fields.map((f, i) => i === index ? { ...f, ...change } : f) });
  }
  function upload(file: File | undefined) {
    if (!file) return;
    if (!name.trim()) { setError('請先輸入樣板名稱'); return; }
    if (!file.name.toLowerCase().endsWith('.docx') || !file.size || file.size > 10_000_000) { setError('請選擇 10 MB 內的 Word（.docx）檔'); return; }
    void run(async () => {
      const saved = await requestJson<DocTemplate>(`/document-templates?${new URLSearchParams({ filename: file.name, name: name.trim() })}`, { method: 'POST', headers: binary, body: file });
      setName(''); await load(); edit(saved);
      setNotice(`已上傳「${saved.name}」，找到 ${saved.fields.length} 個要填的欄位。請設定顯示名稱與必填後儲存。`);
    });
  }
  function replace(file: File | undefined) {
    if (!file || !editing) return;
    void run(async () => {
      const saved = await requestJson<DocTemplate>(`/document-templates/${editing.id}/file?${new URLSearchParams({ filename: file.name, expected_version: String(editing.version) })}`, { method: 'POST', headers: binary, body: file });
      await load(); edit(saved); setNotice(`已換成新版 Word（第 ${saved.version} 版），原本的欄位設定已保留。`);
    });
  }
  function save() {
    if (!editing || !draft) return;
    void run(async () => {
      const fields = draft.fields.map(({ optionText, ...f }) => ({ ...f, unit: f.type === 'number' ? f.unit : '', options: f.type === 'select' ? optionText.split(/[,，、\n]/).map(v => v.trim()).filter(Boolean) : [] }));
      const saved = await requestJson<DocTemplate>(`/document-templates/${editing.id}`, { method: 'PUT', body: JSON.stringify({ expected_version: editing.version, name: draft.name, category: draft.category, numbering: draft.numbering, tax_rate: draft.tax_rate, rounding: draft.rounding, fields }) });
      await load(); setEditing(null); setDraft(null); setNotice(`已儲存「${saved.name}」（第 ${saved.version} 版）`);
    });
  }
  function status(template: DocTemplate, next: 'active' | 'disabled' | 'deleted') {
    if (next === 'deleted' && !window.confirm(`確定刪除樣板「${template.name}」嗎？已產生的文件會保留。`)) return;
    void run(async () => {
      await requestJson(`/document-templates/${template.id}/status`, { method: 'POST', body: JSON.stringify({ status: next }) });
      if (editing?.id === template.id) { setEditing(null); setDraft(null); }
      await load(); setNotice(next === 'active' ? `已啟用「${template.name}」` : next === 'disabled' ? `已停用「${template.name}」` : `已刪除「${template.name}」`);
    });
  }

  if (listing && !listing.can_manage) return null;
  return <section className="panel doc-template-library" aria-label="文件樣板">
    <h2>文件樣板</h2>
    <p className="muted">上傳公司現在用的 Word 表單，把要填的地方寫成 {'{{欄位名稱}}'}。系統會自動帶入 {'{{編號}}'}、{'{{今天}}'}、{'{{填寫人}}'}、{'{{專案名稱}}'}、{'{{節點名稱}}'}、{'{{公司名稱}}'}。報價單明細請用表格列 {'{%tr for 列 in 明細 %}'}…{'{%tr endfor %}'}。</p>
    {error && <p role="alert">{error}</p>}{notice && <p role="status">{notice}</p>}
    <div className="record-actions">
      <button disabled={busy} onClick={() => void run(async () => { const value = await requestJson<Listing & { added: string[] }>('/document-templates/samples', { method: 'POST' }); setListing(value); setNotice(value.added.length ? `已加入範例：${value.added.join('、')}` : '三份範例都已在樣板庫中'); })}>加入三份範例樣板</button>
      <label>樣板名稱<input aria-label="新樣板名稱" maxLength={100} value={name} disabled={busy} onChange={e => setName(e.target.value)} /></label>
      <label>上傳 Word 樣板<input aria-label="上傳 Word 樣板" type="file" accept=".docx" disabled={busy} onChange={e => { const file = e.target.files?.[0]; e.target.value = ''; upload(file); }} /></label>
    </div>
    {!listing ? <p>{busy ? '載入中…' : '尚未載入樣板'}</p> : listing.items.length === 0 ? <p>目前沒有樣板。可以先加入三份範例。</p> :
      <ul className="document-list doc-template-list">{listing.items.map(t => <li key={t.id}>
        <strong>{t.name}</strong> <span>{t.category} · 第 {t.version} 版 · {t.fields.length} 個欄位 · 編號 {t.numbering}{t.status === 'disabled' && ' · 已停用'}</span>
        <div className="record-actions">
          <button disabled={busy} onClick={() => edit(t)}>設定欄位</button>
          <a href={`/api/document-templates/${t.id}/download`}>下載原檔</a>
          <button disabled={busy} onClick={() => status(t, t.status === 'active' ? 'disabled' : 'active')}>{t.status === 'active' ? '停用' : '啟用'}</button>
          <button disabled={busy} onClick={() => status(t, 'deleted')}>刪除</button>
        </div>
      </li>)}</ul>}
    {editing && draft && <form className="report-field-editor doc-template-settings" aria-label={`設定 ${editing.name}`} onSubmit={e => { e.preventDefault(); save(); }}>
      <h3>設定「{editing.name}」</h3>
      <fieldset disabled={busy}>
        <label>樣板名稱<input maxLength={100} value={draft.name} onChange={e => setDraft({ ...draft, name: e.target.value })} /></label>
        <label>類別<input maxLength={50} value={draft.category} onChange={e => setDraft({ ...draft, category: e.target.value })} /></label>
        <label>編號格式<input aria-describedby="numbering-help" maxLength={60} value={draft.numbering} onChange={e => setDraft({ ...draft, numbering: e.target.value })} /></label>
        <p id="numbering-help" className="small muted">可用 {'{年}{月}{日}{序號3位}'}，例如 Q-{'{年}'}-{'{月}{日}'}-{'{序號2位}'}。</p>
        {editing.has_lines && <>
          <label>營業稅率（%）<input inputMode="decimal" maxLength={6} value={draft.tax_rate} onChange={e => setDraft({ ...draft, tax_rate: e.target.value })} /></label>
          <label>金額進位<select value={draft.rounding} onChange={e => setDraft({ ...draft, rounding: e.target.value as Draft['rounding'] })}>{Object.entries(ROUNDING).map(([v, text]) => <option key={v} value={v}>{text}</option>)}</select></label>
        </>}
      </fieldset>
      <fieldset disabled={busy}><legend>要填寫的欄位（來自 Word 裡的代號）</legend>
        <ol>{draft.fields.map((f, index) => <li key={f.name}>
          <p><strong>{`{{${f.name}}}`}</strong></p>
          <label>顯示名稱<input aria-label={`${f.name} 顯示名稱`} maxLength={100} value={f.label} onChange={e => setField(index, { label: e.target.value })} /></label>
          <label>類型<select aria-label={`${f.name} 類型`} value={f.type} onChange={e => setField(index, { type: e.target.value as TemplateField['type'] })}>{Object.entries(TYPES).map(([v, text]) => <option key={v} value={v}>{text}</option>)}</select></label>
          {f.type === 'number' && <label>單位<input aria-label={`${f.name} 單位`} maxLength={30} value={f.unit} onChange={e => setField(index, { unit: e.target.value })} /></label>}
          {f.type === 'select' && <label>選項（以逗號分隔）<input aria-label={`${f.name} 選項`} maxLength={5050} value={f.optionText} onChange={e => setField(index, { optionText: e.target.value })} /></label>}
          <label className="report-field-required"><input type="checkbox" aria-label={`${f.name} 必填`} checked={f.required} onChange={e => setField(index, { required: e.target.checked })} />必填</label>
        </li>)}</ol>
        {!draft.fields.length && <p className="small muted">Word 裡沒有需要手動填寫的代號。</p>}
        <p className="small muted">自動帶入：{editing.auto_fields.join('、')}{editing.has_lines && '；明細表的金額、小計、稅額、總計自動計算'}</p>
      </fieldset>
      <div className="record-actions">
        <button type="submit" disabled={busy}>{busy ? '儲存中…' : '儲存設定'}</button>
        <label>換成新版 Word<input aria-label="換成新版 Word" type="file" accept=".docx" disabled={busy} onChange={e => { const file = e.target.files?.[0]; e.target.value = ''; replace(file); }} /></label>
        <button type="button" disabled={busy} onClick={() => { setEditing(null); setDraft(null); }}>取消</button>
      </div>
    </form>}
  </section>;
}
