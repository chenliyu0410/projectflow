import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { api, ApiError } from '../api';
import type { AssignmentOptions, NodeItem, NodeMetadata } from '../types';

export default function NodeEditor({ projectId, mode, node, parent, canAssign, reload, close, expired }: {
  projectId: string; mode: 'create' | 'edit'; node: NodeItem | null; parent: NodeItem | null; canAssign: boolean;
  reload: (nodeId: string) => Promise<void>; close: () => void; expired: () => void;
}) {
  const initial: NodeMetadata = { title: node?.title ?? '', start_date: node?.start_date ?? null, due_date: node?.due_date ?? null,
    owner_user_id: node?.owner_user_id ?? null, department_id: node?.department_id ?? null };
  const [title, setTitle] = useState(initial.title); const [start, setStart] = useState(initial.start_date ?? ''); const [due, setDue] = useState(initial.due_date ?? '');
  const [owner, setOwner] = useState(initial.owner_user_id ?? ''); const [department, setDepartment] = useState(initial.department_id ?? '');
  const allowPhase = !parent || parent.kind === 'project'; const [kind, setKind] = useState<'phase' | 'task'>(allowPhase ? 'phase' : 'task');
  const [options, setOptions] = useState<AssignmentOptions | null>(null); const [optionsError, setOptionsError] = useState('');
  const [loading, setLoading] = useState(canAssign); const [saving, setSaving] = useState(false); const [error, setError] = useState('');
  const [savedNodeId, setSavedNodeId] = useState<string | null>(null);
  const controller = useRef<AbortController | null>(null); const sequence = useRef(0); const savingRef = useRef(false);
  function begin() { controller.current?.abort(); const request = new AbortController(); controller.current = request; return { id: ++sequence.current, signal: request.signal }; }
  function current(request: ReturnType<typeof begin>) { return request.id === sequence.current && !request.signal.aborted; }
  async function loadOptions() {
    const request = begin(); setLoading(true); setOptionsError('');
    try { const result = await api.assignmentOptions(projectId, request.signal); if (current(request)) setOptions(result); }
    catch (value) { if (!current(request)) return; if (value instanceof ApiError && value.status === 401) expired(); else setOptionsError(value instanceof ApiError ? value.message : '無法載入指派選項'); }
    finally { if (current(request)) setLoading(false); }
  }
  useEffect(() => { if (canAssign) void loadOptions(); return () => { ++sequence.current; controller.current?.abort(); }; }, []);
  const payload: NodeMetadata = { title: title.trim(), start_date: start || null, due_date: due || null, owner_user_id: owner || null, department_id: department || null };
  const changes: Partial<NodeMetadata> = {};
  for (const key of ['title', 'start_date', 'due_date', ...(canAssign ? ['owner_user_id', 'department_id'] as const : [])] as (keyof NodeMetadata)[]) {
    if (payload[key] !== initial[key]) Object.assign(changes, { [key]: payload[key] });
  }
  const invalidDates = !!start && !!due && start > due;
  async function refresh(id: string, request: ReturnType<typeof begin>) {
    try { await reload(id); if (current(request)) close(); }
    catch (value) { if (!current(request)) return; if (value instanceof ApiError && value.status === 401) expired(); else setError('已儲存，資料重新載入失敗'); }
  }
  async function save(event: FormEvent) {
    event.preventDefault();
    if (savingRef.current || loading || optionsError || savedNodeId || !payload.title || payload.title.length > 200 || invalidDates || (mode === 'edit' && !Object.keys(changes).length)) return;
    const request = begin(); savingRef.current = true; setSaving(true); setError('');
    try {
      const result = mode === 'create' ? await api.createNode(projectId, { ...payload, kind, parent_id: parent?.id ?? null }, request.signal)
        : await api.updateNode(node!.id, changes, request.signal);
      if (!current(request)) return;
      setSavedNodeId(result.id); await refresh(result.id, request);
    } catch (value) {
      if (!current(request)) return;
      if (value instanceof ApiError && value.status === 401) expired();
      else setError(value instanceof ApiError && value.status === 0 ? '連線中斷，請重新整理確認儲存結果；不會自動重送' : value instanceof ApiError ? value.message : '儲存失敗，請重新整理確認結果');
    } finally { if (current(request)) { savingRef.current = false; setSaving(false); } }
  }
  async function retryReload() {
    if (!savedNodeId || savingRef.current) return;
    const request = begin(); savingRef.current = true; setSaving(true); setError('');
    await refresh(savedNodeId, request);
    if (current(request)) { savingRef.current = false; setSaving(false); }
  }
  return <form aria-label={mode === 'create' ? '新增節點表單' : '編輯節點表單'} className="node-editor" onSubmit={event => void save(event)}>
    <h2>{mode === 'create' ? '新增子節點' : '編輯節點'}</h2>
    {error && <p role="alert">{error}</p>}
    {savedNodeId ? <div className="form-actions"><button type="button" disabled={saving} onClick={() => void retryReload()}>重試載入</button><button type="button" disabled={saving} onClick={close}>關閉</button></div> : <>
      <label>節點名稱<input autoFocus required maxLength={200} value={title} disabled={saving} onChange={event => setTitle(event.target.value)} /></label>
      {mode === 'create' && <label>種類<select aria-label="種類" value={kind} disabled={saving} onChange={event => setKind(event.target.value as 'phase' | 'task')}>
        {allowPhase && <option value="phase">階段</option>}<option value="task">任務</option>
      </select></label>}
      {canAssign && <>
        {loading && <p role="status">載入指派選項中</p>}{optionsError && <><p role="alert">{optionsError}</p><button type="button" onClick={() => void loadOptions()}>重試指派選項</button></>}
        <label>負責人<select aria-label="負責人" value={owner} disabled={loading || saving || !options} onChange={event => setOwner(event.target.value)}>
          <option value="">未指派</option>{initial.owner_user_id && !options?.users.some(user => user.id === initial.owner_user_id) && <option disabled value={initial.owner_user_id}>{node?.owner_display_name ?? '既有負責人'}（既有指派）</option>}
          {options?.users.map(user => <option key={user.id} value={user.id}>{user.display_name}</option>)}
        </select></label>
        <label>部門<select aria-label="部門" value={department} disabled={loading || saving || !options} onChange={event => setDepartment(event.target.value)}>
          <option value="">未指派</option>{initial.department_id && !options?.departments.some(item => item.id === initial.department_id) && <option disabled value={initial.department_id}>{node?.department_name ?? '既有部門'}（既有指派）</option>}
          {options?.departments.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}
        </select></label>
      </>}
      <label>開始日期<input type="date" min="0001-01-01" max="9999-12-31" value={start} disabled={saving} onChange={event => setStart(event.target.value)} /></label>
      <label>截止日期<input type="date" min="0001-01-01" max="9999-12-31" value={due} disabled={saving} onChange={event => setDue(event.target.value)} /></label>
      {invalidDates && <p role="alert">開始日期不得晚於截止日期</p>}
      <div className="form-actions"><button type="submit" disabled={saving || loading || !!optionsError || !payload.title || invalidDates || (mode === 'edit' && !Object.keys(changes).length)}>儲存</button><button type="button" disabled={saving} onClick={close}>取消</button></div>
    </>}
  </form>;
}
