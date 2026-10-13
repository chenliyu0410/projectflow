import CollaborationActions from './CollaborationDialogs';
import MemberPermissions from './MemberPermissions';
import { useEffect, useMemo, useState } from 'react';
import type { DragEvent, FocusEvent, ReactNode } from 'react';
import ReportPanel from './ReportPanel';
import RecordTimeline from './RecordTimeline';
import CollaboratorEditor from './CollaboratorEditor';
import { api } from '../api';
import type { RecordReload } from '../api';
import type { DependencyData, NodeItem, NodeStatus, ProjectDetail } from '../types';
import { percent, progressMap, projectProgress } from '../progress';

export const statuses: { status: NodeStatus; label: string }[] = [
  { status: 'todo', label: '待處理' }, { status: 'doing', label: '進行中' },
  { status: 'review', label: '待確認' }, { status: 'done', label: '完成' }, { status: 'skipped', label: '已略過' },
];
// The Demo board has four columns; skipped work sits in the done column with its own tag.
const columns: { label: string; match: NodeStatus[] }[] = [
  { label: '待處理', match: ['todo'] }, { label: '進行中', match: ['doing'] },
  { label: '待確認', match: ['review'] }, { label: '完成', match: ['done', 'skipped'] },
];
export type NodeTab = 'board' | 'timeline' | 'graph' | 'people' | 'records' | 'documents' | 'data';
const TABS: { tab: NodeTab | null; label: string }[] = [
  { tab: 'board', label: '看板' }, { tab: 'timeline', label: '時程' }, { tab: 'graph', label: '相依圖' },
  { tab: 'documents', label: '文件' }, { tab: 'data', label: '資料' }, { tab: 'people', label: '成員與權限' }, { tab: 'records', label: '紀錄' },
];
const CLOSED: NodeStatus[] = ['done', 'skipped'];
const label = (status: NodeStatus) => statuses.find(item => item.status === status)?.label ?? status;
const shortDate = (value: string | null) => value ? value.slice(5).replace('-', '/') : '?';
export function localToday() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
}

export function nodePath(nodes: NodeItem[], selectedId: string | null) {
  const byId = new Map(nodes.map(node => [node.id, node]));
  const path: NodeItem[] = []; const visited = new Set<string>();
  let node = selectedId ? byId.get(selectedId) : undefined;
  while (node && !visited.has(node.id)) {
    visited.add(node.id); path.unshift(node); node = node.parent_id ? byId.get(node.parent_id) : undefined;
  }
  return path;
}
// Promote visible orphans; retain a selectable entry even for damaged cyclic legacy data.
export function visibleRoots(nodes: NodeItem[]) {
  const ids = new Set(nodes.map(node => node.id));
  const roots = nodes.filter(node => !node.parent_id || !ids.has(node.parent_id));
  const visited = new Set<string>();
  function visit(start: NodeItem) {
    const pending = [start];
    while (pending.length) {
      const item = pending.pop()!;
      if (visited.has(item.id)) continue;
      visited.add(item.id); pending.push(...nodes.filter(node => node.parent_id === item.id));
    }
  }
  roots.forEach(visit);
  for (const node of nodes) if (!visited.has(node.id)) { roots.push(node); visit(node); }
  return roots.sort((a, b) => a.sort_order - b.sort_order);
}
export function childrenOf(nodes: NodeItem[], id: string) {
  return nodes.filter(node => node.parent_id === id && node.id !== id).sort((a, b) => a.sort_order - b.sort_order);
}
export function isLeafTask(nodes: NodeItem[], node: NodeItem | undefined | null) {
  return !!node && node.kind === 'task' && !nodes.some(child => child.parent_id === node.id && child.id !== node.id);
}
/** The node and every visible descendant; cycles in damaged legacy data are visited once. */
export function subtree(nodes: NodeItem[], id: string) {
  const out: NodeItem[] = []; const seen = new Set<string>(); const pending = [id];
  while (pending.length) {
    const current = pending.pop()!;
    if (seen.has(current)) continue;
    seen.add(current);
    const node = nodes.find(item => item.id === current);
    if (node) out.push(node);
    pending.push(...nodes.filter(item => item.parent_id === current).map(item => item.id));
  }
  return out;
}
/** Levels below the project (a phase is 1); a kind=project root does not count. */
export function levelOf(nodes: NodeItem[], id: string) {
  return nodePath(nodes, id).filter(node => node.kind !== 'project').length;
}
/** Visible children that keep a parent from being marked done. */
export function openChildren(nodes: NodeItem[], node: NodeItem) {
  return childrenOf(nodes, node.id).filter(child => !CLOSED.includes(child.status));
}
export const childrenBlockText = (open: NodeItem[]) => `還有 ${open.length} 項子任務未完成：${open.map(node => node.title).join('、')}`;
function period(nodes: NodeItem[]) {
  const starts = nodes.map(node => node.start_date).filter((d): d is string => !!d).sort();
  const dues = nodes.map(node => node.due_date).filter((d): d is string => !!d).sort();
  return { start: starts[0] ?? null, due: dues[dues.length - 1] ?? null };
}
const isLate = (node: NodeItem, today: string) => !!node.due_date && node.due_date < today && !CLOSED.includes(node.status);
const within = (event: DragEvent<HTMLElement> | FocusEvent<HTMLElement>) => event.currentTarget.contains(event.relatedTarget as globalThis.Node | null);

function Progress({ value, color }: { value: number | null; color?: string }) {
  return <span className="progress" aria-label={`進度 ${value === null ? '—' : `${value}%`}`}>
    <span className="track" aria-hidden="true"><span style={{ width: `${value ?? 0}%`, ...(color ? { background: color } : {}) }} /></span><b>{value === null ? '—' : `${value}%`}</b>
  </span>;
}

export default function NodeWorkspace({ project, selectedNodeId, select, readonly, canApprove, disabled, mutate, move, openReport, reportIntent = null, notify, userId = '', userName = '', roleLabel = '', reloadRecords, expired, recordVersion = 0, recordsEnabled = true, tab = 'board', tabsDisabled = false, changeTab, actions, editor, timeline, graph, preview, color = 'var(--teal)' }: {
  project: ProjectDetail; selectedNodeId: string | null; select: (id: string | null) => void;
  readonly: boolean; canApprove: boolean; disabled: boolean;
  userId?: string; userName?: string; roleLabel?: string; reloadRecords?: RecordReload; expired?: () => void; recordVersion?: number; recordsEnabled?: boolean;
  mutate: (action: 'status' | 'gate', id: string, status?: NodeStatus) => void;
  move?: (id: string, parentId: string) => void; openReport?: (id: string) => void; reportIntent?: string | null; notify?: (text: string) => void;
  tab?: NodeTab; tabsDisabled?: boolean; changeTab?: (tab: NodeTab) => void; actions?: ReactNode; editor?: ReactNode; timeline?: ReactNode; graph?: ReactNode; preview?: ReactNode; color?: string;
}) {
  const nodes = project.nodes;
  const today = localToday();
  const selected = nodes.find(node => node.id === selectedNodeId);
  // Blank projects keep a project-kind root node; its children are the project's top level.
  const top = visibleRoots(nodes).flatMap(node => node.kind === 'project' ? [node, ...childrenOf(nodes, node.id)] : [node]).filter(node => node.kind !== 'project');
  const phases = top.filter(node => node.kind === 'phase');
  const leaf = isLeafTask(nodes, selected);
  const scope = selected ? subtree(nodes, selected.id) : nodes;
  const span = period(scope);
  // Project board flattens phases like the Demo: each phase's work appears with a phase tag.
  const items = selected ? childrenOf(nodes, selected.id)
    : top.flatMap(node => node.kind === 'phase' ? childrenOf(nodes, node.id) : [node]);
  const phaseOf = (node: NodeItem) => !selected && node.parent_id ? phases.find(phase => phase.id === node.parent_id) : undefined;
  const gate = selected?.kind === 'phase' ? project.gates.find(item => item.node_id === selected.id) : undefined;
  const tabs = leaf ? [TABS[6], ...TABS.slice(0, 6)] : TABS;
  const active: NodeTab = tab;
  const values = useMemo(() => progressMap(nodes), [nodes]);
  const nodePercent = (node: NodeItem) => percent(values.get(node.id) ?? 0);
  const headPercent = selected ? nodePercent(selected) : projectProgress(nodes, values);

  const [expanded, setExpanded] = useState(new Set<string>());
  const [deps, setDeps] = useState<DependencyData | null>(null);
  const [hover, setHover] = useState<string | null>(null);
  const [drag, setDrag] = useState<string | null>(null);
  const [over, setOver] = useState<string | null>(null);
  const [nest, setNest] = useState<string | null>(null);
  // Load edges only when a card waits on predecessors or the user first points at, focuses or drags a card.
  const [wantDeps, setWantDeps] = useState(false);
  const needDeps = active === 'board' && items.length > 0 && (wantDeps || items.some(node => node.blocked));
  useEffect(() => {
    if (!needDeps) return;
    const request = new AbortController();
    // Waiting names and highlights are decoration: on failure the 🔒 tag stays the only hint.
    api.dependencies(project.id, request.signal).then(setDeps, () => undefined);
    return () => request.abort();
  }, [project.id, recordVersion, needDeps]);
  const point = (id: string) => { setHover(id); setWantDeps(true); };
  const related = useMemo(() => {
    const out = new Set<string>();
    if (!hover || !deps) return out;
    const chain = new Set(nodePath(nodes, hover).map(node => node.id));
    for (const edge of deps.items) {
      if (chain.has(edge.successor_id)) out.add(edge.predecessor_id);
      if (edge.predecessor_id === hover) out.add(edge.successor_id);
    }
    out.delete(hover);
    return out;
  }, [hover, deps, nodes]);
  const dragged = drag ? nodes.find(node => node.id === drag) : undefined;
  const say = (text: string) => notify?.(text);
  // A task still waiting on predecessors would be refused by the API, so the shortcut is not offered.
  const canReport = (node: NodeItem) => !readonly && node.kind === 'task' && !!node.capabilities?.submit_report && !node.blocked
    && !!node.state_actions?.includes('submit_report') && (node.status === 'todo' || node.status === 'doing') && openChildren(nodes, node).length === 0;
  const canDrag = (node: NodeItem) => !readonly && !disabled && (!!node.capabilities?.move || (node.state_actions?.length ?? 0) > 0);
  const canMoveAny = !readonly && items.some(node => node.capabilities?.move);
  const anyDraggable = items.some(canDrag);
  function clearDrag() { setDrag(null); setOver(null); setNest(null); }
  function waiting(node: NodeItem) {
    if (node.status !== 'todo' || !node.blocked || !deps) return null;
    const titles = deps.items.filter(edge => edge.successor_id === node.id)
      .map(edge => deps.nodes.find(item => item.id === edge.predecessor_id))
      .filter((item): item is DependencyData['nodes'][number] => !!item && !CLOSED.includes(item.status)).map(item => item.title);
    return `等待：${titles.length ? titles.join('、') : '前置任務'}`;
  }
  // Dragging is another entry to the same rules: review and done still go through a completion report.
  function statusDrop(node: NodeItem, target: NodeStatus) {
    if (node.status === target || (target === 'done' && node.status === 'skipped')) return;
    if (node.kind === 'task') {
      if (node.status === 'review') return say('此任務有待確認的完成回報，請到「紀錄」分頁確認或退回');
      if (node.status === 'done') return say('已完成的任務請用「重新開啟」');
      if (node.status === 'skipped') return say('已略過的任務請用「恢復任務」還原');
      if (target === 'review' || target === 'done') {
        const open = openChildren(nodes, node);
        if (open.length) return say(childrenBlockText(open));
        if (node.blocked) return say('尚有未完成的前置任務，完成前置後才能回報');
        if (canReport(node)) return openReport?.(node.id);
        return say('你的角色無權回報此任務');
      }
    }
    if (!node.state_actions?.includes(target)) return say('你的角色無權變更此任務');
    if (target === 'done' && openChildren(nodes, node).length) return say(childrenBlockText(openChildren(nodes, node)));
    mutate('status', node.id, target);
  }
  function moveDrop(node: NodeItem, target: NodeItem) {
    if (target.id === node.id || target.id === node.parent_id) return;
    const family = new Set(subtree(nodes, node.id).map(item => item.id));
    if (family.has(target.id)) return say('不能移到自己的子任務底下');
    if (['review', 'done', 'skipped'].includes(target.status)) return say('不能移到已完成、待確認或已略過的任務底下');
    const chain = new Set(nodePath(nodes, target.id).map(item => item.id));
    if (deps?.items.some(edge => (family.has(edge.predecessor_id) && chain.has(edge.successor_id)) || (chain.has(edge.predecessor_id) && family.has(edge.successor_id))))
      return say('移動後會和前置相依衝突，請先移除相依連線');
    move?.(node.id, target.id);
  }
  const nestable = (target: NodeItem) => !!dragged && dragged.id !== target.id && !!dragged.capabilities?.move;

  function statusControl(node: NodeItem, compact = false) {
    const allowed = statuses.filter(item => node.state_actions?.includes(item.status));
    const open = node.kind === 'task' ? [] : openChildren(nodes, node);
    return !readonly && node.kind !== 'project' && allowed.length > 0 && <label className={compact ? 'status-select compact' : 'status-select'}>
      <span className={compact ? 'sr-only' : undefined}>{node.kind === 'phase' ? '階段狀態' : '狀態'}</span>
      <select aria-label={`${node.title}狀態`} value={node.status} disabled={disabled} onChange={event => mutate('status', node.id, event.target.value as NodeStatus)}>
        {allowed.map(option => {
          const blocked = option.status === 'done' && node.status !== 'done' && open.length > 0;
          return <option key={option.status} value={option.status} disabled={blocked}>{option.label}{blocked ? `（還有 ${open.length} 項子任務未完成）` : ''}</option>;
        })}
      </select></label>;
  }
  function card(node: NodeItem) {
    const phase = phaseOf(node);
    const late = isLate(node, today);
    const kids = childrenOf(nodes, node.id);
    const open = expanded.has(node.id);
    const wait = waiting(node);
    const draggable = canDrag(node);
    const lit = related.has(node.id) ? 'hl' : hover === node.id && related.size > 0 ? 'hl-src' : '';
    return <article key={node.id} data-id={node.id} draggable={draggable || undefined}
      className={['task-card', late && 'late', drag === node.id && 'dragging', nest === node.id && 'nest', lit].filter(Boolean).join(' ')}
      onDragStart={event => { if (!draggable) return; event.dataTransfer?.setData('text/plain', node.id); if (event.dataTransfer) event.dataTransfer.effectAllowed = 'move'; setDrag(node.id); setWantDeps(true); }}
      onDragEnd={clearDrag}
      onDragOver={event => { if (!nestable(node)) return; event.preventDefault(); event.stopPropagation(); if (nest !== node.id) setNest(node.id); setOver(null); }}
      onDragLeave={event => { if (nest === node.id && !within(event)) setNest(null); }}
      onDrop={event => { if (!nestable(node)) return; event.preventDefault(); event.stopPropagation(); const source = dragged!; clearDrag(); moveDrop(source, node); }}
      onMouseEnter={() => point(node.id)} onMouseLeave={() => setHover(value => value === node.id ? null : value)}
      onFocus={() => point(node.id)} onBlur={event => { if (!within(event)) setHover(value => value === node.id ? null : value); }}>
      <div className="tags">{phase && <span className="tag gray">{phase.title}</span>}
        {node.kind !== 'task' && <span className="tag">{node.kind === 'phase' ? '階段' : '專案'}</span>}
        {late && <span className="tag warn">延遲</span>}
        {node.blocked && <span className="tag warn">🔒 等待前置</span>}
        {node.status === 'review' && <span className="tag blue">待確認回報</span>}
        {node.status === 'skipped' && <span className="tag gray">已略過</span>}</div>
      <button className="task-title" onClick={() => select(node.id)}>{node.title}</button>
      {wait && <p className="card-waiting small muted">{wait}</p>}
      {kids.length > 0 && <div className="mini">
        <span>{kids.filter(kid => CLOSED.includes(kid.status)).length}/{kids.length} 子任務</span>
        <span className="track" aria-hidden="true"><span style={{ width: `${nodePercent(node)}%` }} /></span>
        <span>{nodePercent(node)}%</span>
        <button type="button" className="iconbtn" aria-expanded={open} aria-label={`${open ? '收合' : '展開'}下一層：${node.title}`}
          onClick={() => setExpanded(value => { const next = new Set(value); if (next.has(node.id)) next.delete(node.id); else next.add(node.id); return next; })}>{open ? '收合' : '展開'}</button>
      </div>}
      {open && kids.length > 0 && <ul className="sublist" aria-label={`${node.title}的下一層`}>{kids.map(kid => <li key={kid.id}>
        <button type="button" onClick={() => select(kid.id)}><span className={`dot ${kid.status}`} aria-hidden="true" /><span>{kid.title}</span>{childrenOf(nodes, kid.id).length > 0 && <span className="muted small">（{childrenOf(nodes, kid.id).length}）</span>}</button>
      </li>)}</ul>}
      <div className="card-foot"><span className="who">{node.owner_display_name && <span className="avatar xs" aria-hidden="true">{node.owner_display_name.slice(0, 1)}</span>}
        <span className="who-name">{node.owner_display_name ?? '未指派'}{node.department_name ? `・${node.department_name}` : ''}</span></span>
        <span className="card-dates">{node.start_date || node.due_date ? `${shortDate(node.start_date)}–${shortDate(node.due_date)}` : '未設定日期'}</span>
        {canReport(node) && <button type="button" className="iconbtn report-quick" aria-label={`回報完成：${node.title}`} title="回報完成" disabled={disabled} onClick={() => openReport?.(node.id)}>✓ 回報</button>}</div>
      {statusControl(node, true)}
    </article>;
  }
  const crumbs = nodePath(nodes, selectedNodeId);
  const owner = selected?.owner_display_name;
  const level = selected ? levelOf(nodes, selected.id) : 0;
  const descendantTasks = (selected ? subtree(nodes, selected.id).filter(node => node.id !== selected.id) : nodes).filter(node => node.kind === 'task').length;
  return <>
    <section aria-label="節點詳情" className="node-head">
      <div className="node-head-main">
        {selected && <nav aria-label="節點路徑" className="breadcrumbs"><button aria-current={selected ? undefined : 'location'} onClick={() => select(null)}>{project.title}</button>{crumbs.map(node => <span key={node.id}> / <button aria-current={node.id === selectedNodeId ? 'location' : undefined} onClick={() => select(node.id)}>{node.title}</button></span>)}</nav>}
        <div className="node-title-row"><div className="location-context"><span aria-label="目前層級">{level ? `第 ${level} 層 · ${selected?.kind === 'phase' ? '階段' : '任務'}` : '專案總覽'}</span>{selected && <button type="button" onClick={() => select(crumbs.length > 1 ? crumbs[crumbs.length - 2].id : null)}>↑ 返回上一層</button>}</div>
        <h1 className="node-title">{selected?.title ?? project.title}</h1></div>
        <div className="node-meta">
          {selected && <span>{selected.kind === 'task' ? '負責' : '負責人'}：{owner ?? '未指派'}{selected.department_name ? `・${selected.department_name}` : ''}</span>}
          <span>期間：{span.start ?? '未設定'} – {span.due ?? '未設定'}</span>
          <Progress value={headPercent} color={color} />
          {selected && (statusControl(selected) || <span className="tag gray">{label(selected.status)}</span>)}
          {selected && isLate(selected, today) && <span className="tag warn">延遲</span>}
          {selected?.dependency_warnings?.map(w => <p className="note warn" key={w}>{w}</p>)}
          {selected?.blocked && <span className="tag warn">🔒 尚有未完成的前置任務</span>}
          {level >= 5 && <span className="tag warn">層數較深，可考慮拆成獨立專案</span>}
        </div>
        {selected?.kind === 'phase' && <p className="small muted">階段狀態為手動設定；子節點全部完成或略過後才能標為完成。</p>}
      </div>
      {(owner || actions) && <div className="head-actions">
        {owner && <span className="avatar member" title={owner} aria-hidden="true">{owner.slice(0, 1)}</span>}
        {actions}
      </div>}
    </section>
    {selected && reloadRecords && expired && <CollaborationActions key={`collaboration:${selected.id}:${recordVersion}`} node={selected} reload={reloadRecords} expired={expired}/>}
    {selected?.kind === 'task' && recordsEnabled && reloadRecords && expired && <ReportPanel key={`report:${selected.id}:${recordVersion}`} node={selected} userId={userId} reload={reloadRecords} expired={expired}
      autoOpen={reportIntent === selected.id} openChildren={openChildren(nodes, selected)}
      parentClosed={['review', 'done', 'skipped'].includes(nodes.find(node => node.id === selected.parent_id)?.status ?? '')} />}
    {!selected && phases.length > 0 && <section className="phases" aria-label="開發階段與閘門">{phases.map(phase => {
      const phaseGate = project.gates.find(item => item.node_id === phase.id);
      const value = nodePercent(phase);
      const complete = CLOSED.includes(phase.status);
      const started = !complete && subtree(nodes, phase.id).some(node => node.status !== 'todo');
      const state = complete ? 'done' : started ? 'doing' : 'todo';
      const stateText = complete ? '已完成' : started ? '進行中' : '尚未開始';
      const unavailable = !started;
      const reason = complete ? '已完成階段不開放此入口' : !started ? '尚未開始，暫不開放此入口' : '';
      return <button key={phase.id} className={`phase phase-${state}`} disabled={disabled || unavailable} title={reason || undefined}
        onClick={() => select(phase.id)} aria-label={`進入階段：${phase.title}`} aria-describedby={`phase-state-${phase.id} phase-progress-${phase.id} phase-gate-${phase.id}`}>
        <span className="phase-row"><span className="phase-state" id={`phase-state-${phase.id}`}>{complete ? '✓ ' : ''}{stateText}</span>{started && <span className="phase-arrow" aria-label="進行中階段">→</span>}</span>
        <span className="phase-name">{phase.title}</span>
        <span className="phase-progress-label" id={`phase-progress-${phase.id}`}><span>完成度</span><strong>{value}%</strong></span>
        <span className="phase-progress-track" aria-hidden="true"><span style={{ width: `${value}%` }} /></span>
        <span className="phase-gate" id={`phase-gate-${phase.id}`}>{phase.status === 'skipped' ? '此階段已略過' : reason || (phaseGate?.status === 'pending' ? '本階段閘門待核准' : phaseGate ? '閘門已核准' : '無閘門')}</span>
      </button>;
    })}</section>}
    {gate && <section className="panel gate-inline" aria-label="階段閘門">
      <div><b>階段閘門</b>　<span className="tag gray">{gate.status === 'approved' ? '✓ 已核准' : '待核准'}</span>
        {gate.status === 'pending' && <p className="small muted">尚有階段閘門待核准，後續階段可能被阻擋</p>}</div>
      {canApprove && gate.status === 'pending' && <button disabled={disabled} onClick={() => mutate('gate', gate.id)}>核准閘門</button>}
    </section>}
    <div className="node-views">
    <div className="node-toolbar"><div role="tablist" aria-label="節點內容">{tabs.map(item => item.tab === null
      ? <button key={item.label} role="tab" aria-selected={false} disabled className="tab-unavailable">{item.label}<span className="nav-badge">尚未提供</span></button>
      : <button key={item.tab} role="tab" aria-selected={active === item.tab} disabled={tabsDisabled} onClick={() => { if (item.tab !== active) changeTab?.(item.tab!); }}>{item.label}</button>)}</div>

    </div>
    <div className="node-view-content">
      {active === 'board' && <p className="tools-hint">{canMoveAny ? '拖曳卡片改狀態；拖到另一張卡片上 = 變成它的子任務' : anyDraggable ? '拖曳卡片或用卡片上的狀態選單改狀態；點卡片標題進入下一層' : '點卡片標題進入下一層'}</p>}
    {editor}
    {active === 'board' && <section aria-label="看板" className="board-scroll">
      {items.length === 0 && <p className="empty">{nodes.length === 0 ? '這個專案還沒有節點。按「新增子節點」開始拆解。' : '目前沒有下一層節點'}</p>}
      {items.length > 0 && <div className="kanban">{columns.map(column => {
        const list = items.filter(node => column.match.includes(node.status));
        return <div key={column.label} aria-label={column.label} className={`kanban-column ${over === column.label ? 'over' : ''}`}
          onDragOver={event => { if (!drag) return; event.preventDefault(); if (over !== column.label) setOver(column.label); if (nest) setNest(null); }}
          onDragLeave={event => { if (over === column.label && !within(event)) setOver(null); }}
          onDrop={event => { if (!drag) return; event.preventDefault(); const source = dragged; clearDrag(); if (source) statusDrop(source, column.match[0]); }}>
          <h2>{column.label}<span className="column-count">{list.length}</span></h2>
          {list.map(card)}{list.length === 0 && <p className="hint">{anyDraggable ? '把任務拖到這裡' : '沒有項目'}</p>}
        </div>;
      })}</div>}
    </section>}
    {(active === 'documents' || active === 'data') && preview}
    {active === 'timeline' && timeline}
    {active === 'graph' && graph}
    {active === 'people' && selected && <div className="people-view">
      <div className="grid2">
        <section className="panel" aria-label="此節點的成員"><h3>此節點的成員</h3>
          <dl className="kv"><dt>負責人</dt><dd>{owner ? <><span className="avatar xs" aria-hidden="true">{owner.slice(0, 1)}</span>{owner}</> : '未指派'}</dd>
            <dt>部門</dt><dd>{selected.department_name ?? '未指派'}</dd></dl>
          <p className="small muted">協作人員與部門在下方設定。實際可操作範圍依你的任務角色決定。</p>
        </section>
        <section className="panel" aria-label="我在此節點的權限"><h3>你（{userName}{roleLabel ? `・${roleLabel}` : ''}）在此節點可以</h3>
          <ul className="cap-list">{([
            ['檢視', true], ['編輯節點資料', selected.capabilities?.edit_metadata], ['指派負責人與部門', selected.capabilities?.assign],
            ['新增子節點', selected.capabilities?.create_child], ['移動到其他任務底下', selected.capabilities?.move],
            ['複製子樹', selected.capabilities?.copy], ['刪除任務', selected.capabilities?.delete], ['寫筆記與上傳附件', selected.capabilities?.write_record],
            ['送出完成回報', selected.capabilities?.submit_report], ['確認或退回回報', selected.capabilities?.review_report],
            ['管理協作人員', selected.capabilities?.manage_collaborators], ['略過、重新開啟與恢復', selected.capabilities?.lifecycle],
            ...(selected.kind === 'phase' ? [['核准階段閘門', canApprove]] as const : []),
          ] as const).map(([text, ok]) => <li key={text} className={ok && !readonly || text === '檢視' ? 'yes' : 'no'}><span aria-hidden="true">{ok && !readonly || text === '檢視' ? '✓' : '✗'}</span>{text}<span className="sr-only">{ok && !readonly || text === '檢視' ? '：可以' : '：不可以'}</span></li>)}</ul>
        </section>
      </div>
      {recordsEnabled && reloadRecords && expired && <CollaboratorEditor key={`people:${selected.id}:${recordVersion}`} nodeId={selected.id} projectId={selected.project_id} manage={!!selected.capabilities?.manage_collaborators} reload={reloadRecords} expired={expired} />}
    </div>}
    {active === 'people' && expired && <MemberPermissions project={project} expired={expired}/>}
    {active === 'records' && recordsEnabled && reloadRecords && expired && <RecordTimeline key={`records:${selected?.id ?? project.id}:${recordVersion}`} node={selected ?? null} projectId={project.id}
      leaf={leaf} descendantTasks={descendantTasks} userId={userId} reload={reloadRecords} expired={expired} select={select} />}
    </div>
    </div>
  </>;
}
