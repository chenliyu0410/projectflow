import { useEffect, useRef, useState } from 'react';
import { api, ApiError } from '../api';
import type { ReportField, ReportFieldSet } from '../types';

export const fieldTypes = { text: '文字', number: '數字', date: '日期', select: '單選' };

export function FieldDefinitions({ fields, changed, disabled = false }: { fields: ReportField[]; changed: (fields: ReportField[]) => void; disabled?: boolean }) {
  const [label, setLabel] = useState('');
  const [type, setType] = useState<ReportField['type']>('text');
  const [extra, setExtra] = useState('');
  const [required, setRequired] = useState(false);
  const [error, setError] = useState('');
  function add() {
    const options = type === 'select' ? extra.split(/[,，、\n]/).map(v => v.trim()).filter(Boolean) : [];
    if (!label.trim() || fields.length >= 30 || (type === 'select' && (options.length < 2 || options.length > 50 || new Set(options).size !== options.length || options.some(v => v.length > 100)))) {
      setError('請填寫欄位名稱；單選需2至50個不重複選項，每項最多100字。'); return;
    }
    changed([...fields, { id: null, label: label.trim(), type, required, unit: type === 'number' ? extra.trim() : '', options }]);
    setLabel(''); setExtra(''); setRequired(false); setError('');
  }
  function move(index: number, delta: number) {
    const next = [...fields]; [next[index], next[index + delta]] = [next[index + delta], next[index]]; changed(next);
  }
  return <fieldset className="report-field-editor" disabled={disabled}>
    <legend>回報欄位</legend>
    <ol>{fields.map((f, index) => <li key={f.id ?? `new-${index}`}>
      <span>{f.label} · {fieldTypes[f.type]}{f.unit && `（${f.unit}）`}{f.required && ' · 必填'}{f.type === 'select' && ` · ${f.options.join('、')}`}</span>
      <div className="record-actions"><button type="button" aria-label={`上移 ${f.label}`} disabled={disabled || index === 0} onClick={() => move(index, -1)}>上移</button><button type="button" aria-label={`下移 ${f.label}`} disabled={disabled || index === fields.length - 1} onClick={() => move(index, 1)}>下移</button><button type="button" aria-label={`移除 ${f.label}`} onClick={() => changed(fields.filter((_, i) => i !== index))}>移除</button></div>
    </li>)}</ol>
    {!fields.length && <p className="small muted">尚無自訂欄位</p>}
    {error && <p role="alert">{error}</p>}
    <label>欄位名稱<input maxLength={100} value={label} onChange={e => setLabel(e.target.value)} /></label>
    <label>欄位類型<select aria-label="欄位類型" value={type} onChange={e => { setType(e.target.value as ReportField['type']); setExtra(''); }}>{Object.entries(fieldTypes).map(([v, text]) => <option key={v} value={v}>{text}</option>)}</select></label>
    {(type === 'number' || type === 'select') && <label>{type === 'number' ? '單位' : '選項（以逗號分隔）'}<input maxLength={type === 'number' ? 30 : 5050} value={extra} onChange={e => setExtra(e.target.value)} /></label>}
    <label className="report-field-required"><input type="checkbox" checked={required} onChange={e => setRequired(e.target.checked)} />必填</label>
    <button type="button" disabled={disabled || fields.length >= 30} onClick={add}>新增欄位</button>
  </fieldset>;
}

export default function ReportFieldEditor({ nodeId, expired, disabled = false }: { nodeId: string; expired: () => void; disabled?: boolean }) {
  const [data, setData] = useState<ReportFieldSet | null>(null);
  const [fields, setFields] = useState<ReportField[]>([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const controller = useRef<AbortController | null>(null);
  const inFlight = useRef(false);
  function failure(e: unknown) { if (e instanceof ApiError && e.status === 401) expired(); else setError(e instanceof Error ? e.message : '無法讀取回報欄位'); }
  async function load() {
    controller.current?.abort(); const request = new AbortController(); controller.current = request;
    setBusy(true); setError('');
    try { const result = await api.reportFields(nodeId, request.signal); if (!request.signal.aborted) { setData(result); setFields(result.fields); } }
    catch (e) { if (!request.signal.aborted) failure(e); }
    finally { if (!request.signal.aborted) setBusy(false); }
  }
  useEffect(() => { void load(); return () => controller.current?.abort(); }, [nodeId]);
  async function save() {
    if (!data || inFlight.current) return;
    inFlight.current = true; setBusy(true); setError(''); setSaved(false);
    const request = new AbortController(); controller.current = request;
    try { const result = await api.saveReportFields(nodeId, data.version, fields, request.signal); if (!request.signal.aborted) { setData(result); setFields(result.fields); setSaved(true); } }
    catch (e) { if (!request.signal.aborted) failure(e); }
    finally { inFlight.current = false; if (!request.signal.aborted) setBusy(false); }
  }
  const dirty = data && JSON.stringify(fields) !== JSON.stringify(data.fields);
  return <section aria-label="自訂回報欄位設定">
    {error && <p role="alert">{error}（輸入已保留）</p>}
    {busy && <p role="status">處理回報欄位中</p>}
    {data && <><FieldDefinitions fields={fields} changed={v => { setFields(v); setSaved(false); }} disabled={disabled || busy || !data.can_edit} />
      {!data.can_edit && <p>只有可編輯、未關閉且沒有待確認回報的葉任務可設定欄位。</p>}
      {data.can_edit && <button type="button" disabled={disabled || busy || !dirty} onClick={() => void save()}>儲存回報欄位</button>}
      {dirty && <button type="button" disabled={busy} onClick={() => { setFields(data.fields); setError(''); }}>取消欄位變更</button>}
      {saved && <p role="status">回報欄位已儲存</p>}</>}
    {error && <button type="button" disabled={busy} onClick={() => { if (!dirty || window.confirm('重新載入會捨棄尚未儲存的欄位設定，是否繼續？')) void load(); }}>重新載入欄位設定</button>}
    <p className="small muted">欄位設定分開儲存；移除欄位不影響歷史回報。</p>
  </section>;
}

export function ReportFieldInputs({ fields, values, changed }: { fields: ReportField[]; values: Record<string, string>; changed: (values: Record<string, string>) => void }) {
  return <>{fields.map(field => <label key={field.id}>{field.label}{field.unit && `（${field.unit}）`}{field.required && '（必填）'}
    {field.type === 'select' ? <select aria-label={`${field.label}${field.unit ? `（${field.unit}）` : ""}${field.required ? "（必填）" : ""}`} required={field.required} value={values[field.id!] ?? ''} onChange={e => changed({ ...values, [field.id!]: e.target.value })}><option value="">請選擇</option>{field.options.map(v => <option key={v}>{v}</option>)}</select> : <input required={field.required} type={field.type === 'text' ? 'text' : field.type} step={field.type === 'number' ? 'any' : undefined} maxLength={4000} min={field.type === 'date' ? '0001-01-01' : undefined} max={field.type === 'date' ? '9999-12-31' : undefined} value={values[field.id!] ?? ''} onChange={e => changed({ ...values, [field.id!]: e.target.value })} />}
  </label>)}</>;
}

export function ReportFieldValues({fields}: {fields?: import("../types").Report["fields"]}) { return fields?.length ? <dl className="report-field-values">{fields.map(f => <div key={f.id}><dt>{f.label}</dt><dd>{f.value === null ? "—" : String(f.value)}{f.unit && ` ${f.unit}`}</dd></div>)}</dl> : null; }
