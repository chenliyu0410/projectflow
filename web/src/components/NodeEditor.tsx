import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { api, ApiError } from '../api';
import type { AssignmentOptions, DependencyData, NodeItem, NodeMetadata, NodeStatus, NodeUpdate } from '../types';
import { childrenOf, levelOf, subtree, visibleRoots } from './NodeWorkspace';

/** TP-B structure actions run by the App, which closes this form first like the Demo's drawer. */
export type TreeActions = { move: (parentId: string | null) => void; copy: () => void; remove: () => void };
const CLOSED: NodeStatus[] = ['review', 'done', 'skipped'];
const CLOSED_TARGET = '不能移到已完成、待確認或已略過的任務底下';
const TOP = '__top__';
type Target = { target: string | null } | { reason: string };

/** Demo 升級: the grandparent (the project's top level when the parent is a top phase); never past the project. */
export function promoteTarget(nodes: NodeItem[], node: NodeItem): Target {
  const byId = new Map(nodes.map(item => [item.id, item]));
  if (!node.parent_id || byId.get(node.parent_id)?.kind === 'project') return { reason: '已在最上層，無法再升級' };
  const parent = byId.get(node.parent_id);
  if (!parent) return { reason: '看不到上層節點，無法升級' };
  if (!parent.parent_id) return { target: null };
  const grand = byId.get(parent.parent_id);
  if (!grand) return { reason: '看不到上上層節點，無法升級' };
  if (grand.milestone) return { reason: '里程碑不能有子任務，請先取消里程碑' };
  return CLOSED.includes(grand.status) ? { reason: CLOSED_TARGET } : { target: grand.id };
}
/** Demo 降級: into the sibling shown just above it. */
export function demoteTarget(nodes: NodeItem[], node: NodeItem): Target {
  const siblings = nodes.filter(item => item.parent_id === node.parent_id && item.kind !== 'project').sort((a, b) => a.sort_order - b.sort_order);
  const above = siblings[siblings.findIndex(item => item.id === node.id) - 1];
  if (!above) return { reason: '上方沒有同層任務可以放入' };
  if (above.milestone) return { reason: '里程碑不能有子任務，請先取消里程碑' };
  return CLOSED.includes(above.status) ? { reason: CLOSED_TARGET } : { target: above.id };
}
/** Demo 移動到…: every visible node in tree order, minus the node, its subtree and its current parent. */
export function moveOptions(nodes: NodeItem[], node: NodeItem) {
  const family = new Set(subtree(nodes, node.id).map(item => item.id));
  const atTop = !node.parent_id || nodes.find(item => item.id === node.parent_id)?.kind === 'project';
  const out: { value: string; label: string; disabled: boolean }[] = atTop ? [] : [{ value: TOP, label: '（專案最上層）', disabled: false }];
  const walk = (item: NodeItem) => {
    if (family.has(item.id)) return;
    if (item.kind !== 'project' && item.id !== node.parent_id) {
      const closed = CLOSED.includes(item.status) || !!item.milestone;
      // Demo indentation: the project is level 0, so a phase gets one full-width space.
      out.push({ value: item.id, label: `${'　'.repeat(levelOf(nodes, item.id))}${item.title}${item.milestone ? '（里程碑）' : closed ? '（已完成或待確認）' : ''}`, disabled: closed });
    }
    childrenOf(nodes, item.id).forEach(walk);
  };
  visibleRoots(nodes).forEach(walk);
  return out;
}

function TreeOperations({ nodes, node, dirty, tree }: { nodes: NodeItem[]; node: NodeItem; dirty: boolean; tree: TreeActions }) {
  const [moveTo, setMoveTo] = useState('');
  const move = !!node.capabilities?.move; const copy = !!node.capabilities?.copy;
  const promote = promoteTarget(nodes, node); const demote = demoteTarget(nodes, node);
  const options = moveOptions(nodes, node);
  const parent = nodes.find(item => item.id === node.parent_id);
  const copyReason = parent && CLOSED.includes(parent.status) ? '不能在已完成、待確認或已略過的節點底下新增' : '';
  const hints = dirty ? ['請先儲存或取消目前的變更'] : [
    ...(move && 'reason' in promote ? [`升級：${promote.reason}`] : []),
    ...(move && 'reason' in demote ? [`降級：${demote.reason}`] : []),
    ...(copy && copyReason ? [`複製：${copyReason}`] : []),
  ];
  const hintId = `tree-hint-${node.id}`;
  return <fieldset className="tree-ops" aria-describedby={hints.length ? hintId : undefined}>
    <legend>層級操作</legend>
    <div className="tree-row">
      {move && <>
        <button type="button" disabled={dirty || 'reason' in promote} onClick={() => { if ('target' in promote) tree.move(promote.target); }}>↖ 升級</button>
        <button type="button" disabled={dirty || 'reason' in demote} onClick={() => { if ('target' in demote) tree.move(demote.target); }}>↘ 降級</button>
        <select aria-label="移動到" value={moveTo} disabled={dirty} onChange={event => setMoveTo(event.target.value)}>
          <option value="">移動到…</option>
          {options.map(option => <option key={option.value} value={option.value} disabled={option.disabled}>{option.label}</option>)}
        </select>
        <button type="button" disabled={dirty || !moveTo} onClick={() => tree.move(moveTo === TOP ? null : moveTo)}>移動</button>
      </>}
      {copy && <button type="button" disabled={dirty || !!copyReason} onClick={tree.copy}>複製子樹</button>}
    </div>
    {hints.length > 0 && <p className="small muted" id={hintId}>{hints.join('；')}</p>}
  </fieldset>;
}

function DeleteConfirm({ projectId, nodes, node, cancel, confirm, expired }: {
  projectId: string; nodes: NodeItem[]; node: NodeItem; cancel: () => void; confirm: () => void; expired: () => void;
}) {
  const [deps, setDeps] = useState<DependencyData | 'error' | null>(null);
  const first = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    const request = new AbortController();
    api.dependencies(projectId, request.signal).then(setDeps, value => {
      if (request.signal.aborted) return;
      if (value instanceof ApiError && value.status === 401) expired(); else setDeps('error');
    });
    first.current?.focus();
    return () => request.abort();
  }, [projectId]);
  const family = new Set(subtree(nodes, node.id).map(item => item.id));
  // Like the Demo, only the tasks outside the subtree that wait on it are listed.
  const affected = deps && deps !== 'error' ? [...new Set(deps.items.filter(edge => family.has(edge.predecessor_id) && !family.has(edge.successor_id))
    .map(edge => deps.nodes.find(item => item.id === edge.successor_id)?.title).filter((title): title is string => !!title))] : [];
  return <section role="alertdialog" aria-labelledby={`delete-title-${node.id}`} className="delete-confirm">
    <h3 id={`delete-title-${node.id}`}>刪除「{node.title}」？</h3>
    {family.size > 1 && <p>將一併刪除 {family.size - 1} 個子任務。</p>}
    {deps === null && <p role="status">載入相依資料中</p>}
    {affected.length > 0 && <p className="note warn">以下任務依賴它，前置條件會被移除：{affected.join('、')}</p>}
    {deps === 'error' && <p className="small muted">無法載入相依資料，受影響的後續任務未列出。</p>}
    <p className="small muted">刪除後可立即按「復原」還原；回報、筆記與附件不會從系統中清除。</p>
    <div className="form-actions"><button ref={first} type="button" onClick={cancel}>取消</button>
      <button type="button" className="danger" disabled={deps === null} onClick={confirm}>確定刪除（可復原）</button></div>
  </section>;
}

export default function NodeEditor({ projectId, mode, node, parent, canAssign, leaf = false, nodes = [], tree, created, reload, close, expired, initialDates }: {
  projectId: string; mode: 'create' | 'edit'; node: NodeItem | null; parent: NodeItem | null; canAssign: boolean; leaf?: boolean;
  initialDates?: { start_date?: string; due_date?: string };
  nodes?: NodeItem[]; tree?: TreeActions; created?: (title: string, undoId: string | null) => void;
  reload: (nodeId: string) => Promise<void>; close: () => void; expired: () => void;
}) {
  const initial: NodeMetadata = { title: node?.title ?? '', start_date: node?.start_date ?? initialDates?.start_date ?? null, due_date: node?.due_date ?? initialDates?.due_date ?? null,
    owner_user_id: node?.owner_user_id ?? null, department_id: node?.department_id ?? null };
  const [title, setTitle] = useState(initial.title); const [start, setStart] = useState(initial.start_date ?? ''); const [due, setDue] = useState(initial.due_date ?? '');
  const [owner, setOwner] = useState(initial.owner_user_id ?? ''); const [department, setDepartment] = useState(initial.department_id ?? '');
  // TP-A rollup fields: the weight counts toward the parent; manual progress only applies to a doing leaf task.
  const initialWeight = String(node?.weight ?? 1); const initialProgress = node?.progress == null ? '' : String(node.progress);
  const [weight, setWeight] = useState(initialWeight); const [progress, setProgress] = useState(initialProgress);
  const showProgress = mode === 'edit' && node?.kind === 'task' && node.status === 'doing' && leaf;
  const allowPhase = !parent || parent.kind === 'project'; const [kind, setKind] = useState<'phase' | 'task'>(allowPhase && !initialDates ? 'phase' : 'task');
  const [milestone, setMilestone] = useState(!!node?.milestone); const [locked, setLocked] = useState(!!node?.schedule_locked);
  const scheduleDisabled = !!node?.schedule_locked && !node.capabilities.lock_schedule;
  const [options, setOptions] = useState<AssignmentOptions | null>(null); const [optionsError, setOptionsError] = useState('');
  const [loading, setLoading] = useState(canAssign); const [saving, setSaving] = useState(false); const [error, setError] = useState('');
  const [savedNodeId, setSavedNodeId] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
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
  const changes: NodeUpdate = {};
  for (const key of ['title', 'start_date', 'due_date', ...(canAssign ? ['owner_user_id', 'department_id'] as const : [])] as (keyof NodeMetadata)[]) {
    if (payload[key] !== initial[key]) Object.assign(changes, { [key]: payload[key] });
  }
  const percentField = (value: string) => /^\d{1,3}$/.test(value) && Number(value) <= 100;
  const invalidWeight = mode === 'edit' && !percentField(weight);
  const invalidProgress = showProgress && progress !== '' && !percentField(progress);
  if (mode === 'edit' && !invalidWeight && weight !== initialWeight) changes.weight = Number(weight);
  if (showProgress && !invalidProgress && progress !== initialProgress) changes.progress = progress === '' ? null : Number(progress);
  if (milestone !== !!node?.milestone) changes.milestone = milestone;
  if (locked !== !!node?.schedule_locked) changes.schedule_locked = locked;
  const invalidMilestone = milestone && (!start || start !== due || (mode === 'create' ? kind !== 'task' : !leaf));
  const invalidDates = !!start && !!due && start > due;
  // Unsaved edits would be lost by a structure action, so those wait until the form is saved or cancelled.
  const dirty = Object.keys(changes).length > 0 || weight !== initialWeight || progress !== initialProgress;
  async function refresh(id: string, request: ReturnType<typeof begin>) {
    try { await reload(id); if (current(request)) close(); }
    catch (value) { if (!current(request)) return; if (value instanceof ApiError && value.status === 401) expired(); else setError('已儲存，資料重新載入失敗'); }
  }
  async function save(event: FormEvent) {
    event.preventDefault();
    if (savingRef.current || loading || optionsError || savedNodeId || !payload.title || payload.title.length > 200 || invalidDates || invalidMilestone || invalidWeight || invalidProgress || (mode === 'edit' && !Object.keys(changes).length)) return;
    const request = begin(); savingRef.current = true; setSaving(true); setError('');
    try {
      let result: NodeItem;
      if (mode === 'create') {
        const made = await api.createNode(projectId, { ...payload, kind, parent_id: parent?.id ?? null, ...(milestone ? { milestone, schedule_locked: locked } : {}) }, request.signal);
        if (!current(request)) return;
        created?.(made.title, made.undo_id);
        result = made;
      } else result = await api.updateNode(node!.id, changes, request.signal);
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
  const treeNode = mode === 'edit' && node?.kind === 'task' && tree ? node : null;
  return <form aria-label={mode === 'create' ? '新增節點表單' : '編輯節點表單'} className="node-editor" onSubmit={event => void save(event)}>
    <h2>{mode === 'create' ? '新增子節點' : '編輯節點'}</h2>
    {error && <p role="alert">{error}</p>}
    {confirmDelete && treeNode && tree ? <DeleteConfirm projectId={projectId} nodes={nodes} node={treeNode} cancel={() => setConfirmDelete(false)} confirm={tree.remove} expired={expired} />
    : savedNodeId ? <div className="form-actions"><button type="button" disabled={saving} onClick={() => void retryReload()}>重試載入</button><button type="button" disabled={saving} onClick={close}>關閉</button></div> : <>
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
      <label>開始日期<input type="date" min="0001-01-01" max="9999-12-31" value={start} disabled={saving || scheduleDisabled} onChange={event => { setStart(event.target.value); if (milestone) setDue(event.target.value); }} /></label>
      <label>截止日期<input type="date" min="0001-01-01" max="9999-12-31" value={due} disabled={saving || scheduleDisabled || milestone} onChange={event => setDue(event.target.value)} /></label>
      {(mode === 'create' ? kind === 'task' : node?.kind === 'task') && <div className="milestone-options">
        <label><input type="checkbox" checked={milestone} disabled={saving || scheduleDisabled || (mode === 'edit' && !leaf)} onChange={e => { setMilestone(e.target.checked); if (e.target.checked) setDue(start); else setLocked(false); }} />里程碑（單日）</label>
        {(mode === 'create' || node?.capabilities.lock_schedule) && <label><input type="checkbox" checked={locked} disabled={saving || !milestone} onChange={e => setLocked(e.target.checked)} />鎖定時程</label>}
        {scheduleDisabled && <p>已鎖定，請由專案負責人或系統管理員調整日期。</p>}
        {invalidMilestone && <p role="alert">里程碑必須是有完整單日日期的葉任務</p>}
      </div>}
      {invalidDates && <p role="alert">開始日期不得晚於截止日期</p>}
      {mode === 'edit' && <label>權重（彙總進度用）<input type="number" inputMode="numeric" min={0} max={100} step={1} value={weight} disabled={saving} onChange={event => setWeight(event.target.value)} /></label>}
      {invalidWeight && <p role="alert">權重需為 0–100 的整數</p>}
      {showProgress && <label>進度 %<input type="number" inputMode="numeric" min={0} max={100} step={1} placeholder="50" value={progress} disabled={saving} onChange={event => setProgress(event.target.value)} /><small>留空時依狀態計算（進行中 50%）</small></label>}
      {invalidProgress && <p role="alert">進度需為 0–100 的整數</p>}
      {treeNode && tree && (treeNode.capabilities?.move || treeNode.capabilities?.copy) && <TreeOperations nodes={nodes} node={treeNode} dirty={dirty} tree={tree} />}
      <div className="form-actions">
        {treeNode && treeNode.capabilities?.delete && <button type="button" className="danger form-left" disabled={saving} onClick={() => setConfirmDelete(true)}>刪除</button>}
        <button type="submit" disabled={saving || loading || !!optionsError || !payload.title || invalidDates || invalidMilestone || invalidWeight || invalidProgress || (mode === 'edit' && !Object.keys(changes).length)}>儲存</button><button type="button" disabled={saving} onClick={close}>取消</button></div>
    </>}
  </form>;
}
