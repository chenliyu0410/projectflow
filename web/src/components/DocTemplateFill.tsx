import { useEffect, useRef, useState } from 'react';
import { ApiError, requestJson } from '../api';

export type TemplateField = { name: string; label: string; type: 'text' | 'textarea' | 'number' | 'date' | 'select'; required: boolean; unit: string; options: string[] };
export type DocTemplate = { id: string; name: string; category: string; status: 'active' | 'disabled'; version: number; filename: string; fields: TemplateField[]; auto_fields: string[]; numbering: string; tax_rate: string; rounding: 'half_up' | 'down' | 'up'; has_lines: boolean; can_manage: boolean };
type Line = { 品項: string; 數量: string; 單價: string };
type FillDetail = { document_id: string; current_version: number; template_name: string; fields: TemplateField[]; has_lines: boolean; tax_rate: string; rounding: DocTemplate['rounding']; number: string; values: Record<string, string>; lines: Line[] };
export type SavedVersion = { document_id: string; version: number; filename: string };

const AUTO_HINTS: Record<string, string> = { 編號: '產生時自動編號', 今天: '今天日期', 填寫人: '登入者姓名', 專案名稱: '所屬專案', 節點名稱: '目前任務', 公司名稱: '公司名稱' };
const EMPTY_LINE: Line = { 品項: '', 數量: '', 單價: '' };

function round(value: number, rule: DocTemplate['rounding']) {
  const nudged = value + (value >= 0 ? 1e-9 : -1e-9);
  return rule === 'down' ? Math.trunc(value + 1e-9) : rule === 'up' ? Math.ceil(value - 1e-9) : Math.round(nudged);
}
const money = (value: number) => value.toLocaleString('zh-TW');
const asNumber = (text: string) => { const value = Number(text.replace(/,/g, '').trim()); return text.trim() && Number.isFinite(value) ? value : null; };

export function totals(lines: Line[], taxRate: string, rule: DocTemplate['rounding']) {
  const amounts = lines.map(line => { const q = asNumber(line.數量), p = asNumber(line.單價); return q === null || p === null ? null : round(q * p, rule); });
  const subtotal = amounts.reduce<number>((sum, value) => sum + (value ?? 0), 0);
  const tax = round(subtotal * Number(taxRate) / 100, rule);
  return { amounts, subtotal, tax, total: subtotal + tax };
}

/** Pick a template (or reopen a generated document), fill only the needed fields, and save a new document version. */
export default function DocTemplateFill({ scopePath, documentId, expectedVersion, done, cancel, expired }: {
  scopePath: string; documentId?: string; expectedVersion?: number; done: (saved: SavedVersion) => void; cancel: () => void; expired: () => void;
}) {
  const [templates, setTemplates] = useState<DocTemplate[] | null>(null);
  const [detail, setDetail] = useState<FillDetail | null>(null);
  const [chosen, setChosen] = useState('');
  const [values, setValues] = useState<Record<string, string>>({});
  const [lines, setLines] = useState<Line[]>([{ ...EMPTY_LINE }]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const controller = useRef<AbortController | null>(null);

  useEffect(() => {
    const request = new AbortController(); controller.current = request;
    setBusy(true);
    (async () => {
      try {
        if (documentId) {
          const value = await requestJson<FillDetail>(`/documents/${documentId}/fill`, { signal: request.signal });
          if (request.signal.aborted) return;
          setDetail(value); setValues(value.values); setLines(value.lines.length ? value.lines : [{ ...EMPTY_LINE }]);
        } else {
          const value = await requestJson<{ items: DocTemplate[] }>('/document-templates', { signal: request.signal });
          if (!request.signal.aborted) setTemplates(value.items.filter(t => t.status === 'active'));
        }
      } catch (e) {
        if (request.signal.aborted) return;
        if (e instanceof ApiError && e.status === 401) expired(); else setError(e instanceof Error ? e.message : '無法載入樣板');
      } finally { if (!request.signal.aborted) setBusy(false); }
    })();
    return () => request.abort();
  }, [documentId]);

  const template = templates?.find(t => t.id === chosen);
  const fields = detail?.fields ?? template?.fields ?? [];
  const hasLines = detail?.has_lines ?? template?.has_lines ?? false;
  const taxRate = detail?.tax_rate ?? template?.tax_rate ?? '5';
  const rule = detail?.rounding ?? template?.rounding ?? 'half_up';
  const sums = totals(lines, taxRate, rule);
  const ready = Boolean(detail || template);

  function pick(id: string) { setChosen(id); setValues({}); setLines([{ ...EMPTY_LINE }]); setError(''); }
  function setLine(index: number, key: keyof Line, value: string) { setLines(rows => rows.map((row, i) => i === index ? { ...row, [key]: value } : row)); }

  async function submit() {
    const missing = fields.find(f => f.required && !(values[f.name] ?? '').trim());
    if (missing) { setError(`請填寫「${missing.label}」`); return; }
    const filled = lines.filter(l => l.品項.trim() || l.數量.trim() || l.單價.trim());
    if (hasLines && !filled.length) { setError('請至少填一列品項、數量與單價'); return; }
    const bad = filled.findIndex(l => !l.品項.trim() || asNumber(l.數量) === null || asNumber(l.單價) === null);
    if (hasLines && bad >= 0) { setError(`第 ${bad + 1} 列請填品項，數量與單價要填數字`); return; }
    const request = new AbortController(); controller.current = request;
    setBusy(true); setError('');
    try {
      const body = { values, lines: hasLines ? filled : [] };
      const saved = documentId
        ? await requestJson<SavedVersion>(`/documents/${documentId}/regenerate`, { method: 'POST', body: JSON.stringify({ ...body, expected_version: expectedVersion }), signal: request.signal })
        : await requestJson<SavedVersion>(`${scopePath}/documents/from-template`, { method: 'POST', body: JSON.stringify({ ...body, template_id: chosen }), signal: request.signal });
      if (!request.signal.aborted) done(saved);
    } catch (e) {
      if (request.signal.aborted) return;
      if (e instanceof ApiError && e.status === 401) expired();
      else setError(e instanceof ApiError && e.status === 409 && documentId ? '文件已有新版本，請關閉後重新載入再修改。' : e instanceof Error ? e.message : '產生文件失敗，請稍後再試');
    } finally { if (!request.signal.aborted) setBusy(false); }
  }

  return <section className="panel doc-template-fill" aria-label={documentId ? '修改內容重新產生' : '用樣板建立文件'}>
    <h3>{documentId ? `修改內容重新產生：${detail?.template_name ?? ''}` : '用樣板建立文件'}</h3>
    {error && !ready && <p role="alert">{error}</p>}
    {!documentId && templates && (templates.length
      ? <label>選擇樣板<select aria-label="選擇樣板" value={chosen} disabled={busy} onChange={e => pick(e.target.value)}>
          <option value="">請選擇</option>{templates.map(t => <option key={t.id} value={t.id}>{t.name}（{t.category}）</option>)}
        </select></label>
      : <p>公司還沒有可用的文件樣板，請系統管理員到「模板庫」加入。</p>)}
    {busy && !ready && <p>載入中…</p>}
    {ready && <form onSubmit={e => { e.preventDefault(); void submit(); }}>
      <p className="muted">只要填有 ★ 的欄位，其他由系統自動帶入。{detail && `編號維持 ${detail.number}，會存成新版本，舊版本保留。`}</p>
      <fieldset className="report-field-editor" disabled={busy}><legend>要填寫的欄位</legend>
        {fields.map(f => {
          const label = <>{f.required && <span aria-hidden="true">★ </span>}{f.label}{f.unit && `（${f.unit}）`}</>;
          const value = values[f.name] ?? '';
          const change = (next: string) => setValues(old => ({ ...old, [f.name]: next }));
          return <label key={f.name}>{label}
            {f.type === 'textarea' ? <textarea aria-label={f.label} aria-required={f.required} rows={3} maxLength={4000} value={value} onChange={e => change(e.target.value)} />
              : f.type === 'select' ? <select aria-label={f.label} aria-required={f.required} value={value} onChange={e => change(e.target.value)}><option value="">請選擇</option>{f.options.map(o => <option key={o}>{o}</option>)}</select>
              : <input aria-label={f.label} aria-required={f.required} type={f.type === 'date' ? 'date' : 'text'} inputMode={f.type === 'number' ? 'decimal' : undefined} maxLength={4000} value={value} onChange={e => change(e.target.value)} />}
          </label>;
        })}
        {!fields.length && <p className="small muted">此樣板沒有需要手動填寫的欄位。</p>}
      </fieldset>
      {hasLines && <fieldset className="report-field-editor doc-template-lines" disabled={busy}><legend>★ 品項明細（金額自動計算）</legend>
        <table><thead><tr><th>品項</th><th>數量</th><th>單價</th><th>金額</th><th><span className="sr-only">操作</span></th></tr></thead>
          <tbody>{lines.map((line, index) => <tr key={index}>
            <td><input aria-label={`第 ${index + 1} 列品項`} maxLength={200} value={line.品項} onChange={e => setLine(index, '品項', e.target.value)} /></td>
            <td><input aria-label={`第 ${index + 1} 列數量`} inputMode="decimal" value={line.數量} onChange={e => setLine(index, '數量', e.target.value)} /></td>
            <td><input aria-label={`第 ${index + 1} 列單價`} inputMode="decimal" value={line.單價} onChange={e => setLine(index, '單價', e.target.value)} /></td>
            <td>{sums.amounts[index] === null ? '—' : money(sums.amounts[index] as number)}</td>
            <td><button type="button" aria-label={`刪除第 ${index + 1} 列`} disabled={lines.length === 1} onClick={() => setLines(rows => rows.filter((_, i) => i !== index))}>刪除</button></td>
          </tr>)}</tbody></table>
        <button type="button" disabled={lines.length >= 100} onClick={() => setLines(rows => [...rows, { ...EMPTY_LINE }])}>新增一列</button>
        <dl className="report-field-values" aria-label="金額合計">
          <div><dt>小計</dt><dd>{money(sums.subtotal)}</dd></div>
          <div><dt>營業稅 {taxRate}%</dt><dd>{money(sums.tax)}</dd></div>
          <div><dt>總計</dt><dd>{money(sums.total)}</dd></div>
        </dl>
      </fieldset>}
      <dl className="report-field-values" aria-label="自動帶入">
        {(template?.auto_fields ?? Object.keys(AUTO_HINTS)).map(name => <div key={name}><dt>自動　{name}</dt><dd>{name === '編號' && detail ? detail.number : AUTO_HINTS[name]}</dd></div>)}
      </dl>
      {/* Next to the submit button: the form is long, so a message at the top would be off screen. */}
      {error && <p role="alert">{error}</p>}
      <div className="record-actions">
        <button type="submit" disabled={busy}>{busy ? '產生中…' : documentId ? '重新產生新版本' : '產生文件'}</button>
        <button type="button" disabled={busy} onClick={cancel}>取消</button>
      </div>
    </form>}
    {!ready && <div className="record-actions"><button type="button" onClick={cancel}>取消</button></div>}
  </section>;
}
