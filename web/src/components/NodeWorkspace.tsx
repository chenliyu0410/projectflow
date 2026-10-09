import type { ReactNode } from 'react';
import ReportPanel from './ReportPanel';
import RecordTimeline from './RecordTimeline';
import CollaboratorEditor from './CollaboratorEditor';
import type { RecordReload } from '../api';
import type { NodeItem, NodeStatus, ProjectDetail } from '../types';

export const statuses: { status: NodeStatus; label: string }[] = [
  { status: 'todo', label: '待處理' }, { status: 'doing', label: '進行中' },
  { status: 'review', label: '待確認' }, { status: 'done', label: '完成' }, { status: 'skipped', label: '已略過' },
];
// The Demo board has four columns; skipped work sits in the done column with its own tag.
const columns: { label: string; match: NodeStatus[] }[] = [
  { label: '待處理', match: ['todo'] }, { label: '進行中', match: ['doing'] },
  { label: '待確認', match: ['review'] }, { label: '完成', match: ['done', 'skipped'] },
];
export type NodeTab = 'board' | 'timeline' | 'graph' | 'people' | 'records';
const TABS: { tab: NodeTab | null; label: string }[] = [
  { tab: 'board', label: '看板' }, { tab: 'timeline', label: '時程' }, { tab: 'graph', label: '相依圖' },
  { tab: null, label: '文件' }, { tab: null, label: '資料' }, { tab: 'people', label: '成員與權限' }, { tab: 'records', label: '紀錄' },
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
/** Same rule as the overview API: done tasks ÷ (visible tasks − skipped), half-up; null without tasks. */
export function completion(nodes: NodeItem[]) {
  const tasks = nodes.filter(node => node.kind === 'task');
  const denominator = tasks.length - tasks.filter(node => node.status === 'skipped').length;
  if (denominator === 0) return null;
  return Math.floor((200 * tasks.filter(node => node.status === 'done').length + denominator) / (2 * denominator));
}
function period(nodes: NodeItem[]) {
  const starts = nodes.map(node => node.start_date).filter((d): d is string => !!d).sort();
  const dues = nodes.map(node => node.due_date).filter((d): d is string => !!d).sort();
  return { start: starts[0] ?? null, due: dues[dues.length - 1] ?? null };
}
const isLate = (node: NodeItem, today: string) => !!node.due_date && node.due_date < today && !CLOSED.includes(node.status);

function Progress({ value }: { value: number | null }) {
  return <span className="progress" aria-label={`可見任務完成率 ${value === null ? '—' : `${value}%`}`}>
    <span className="track" aria-hidden="true"><span style={{ width: `${value ?? 0}%` }} /></span><b>{value === null ? '—' : `${value}%`}</b>
  </span>;
}

export default function NodeWorkspace({ project, selectedNodeId, select, readonly, canApprove, disabled, mutate, userId = '', userName = '', roleLabel = '', reloadRecords, expired, recordVersion = 0, recordsEnabled = true, tab = 'board', tabsDisabled = false, changeTab, actions, editor, timeline, graph, color = 'var(--teal)' }: {
  project: ProjectDetail; selectedNodeId: string | null; select: (id: string | null) => void;
  readonly: boolean; canApprove: boolean; disabled: boolean;
  userId?: string; userName?: string; roleLabel?: string; reloadRecords?: RecordReload; expired?: () => void; recordVersion?: number; recordsEnabled?: boolean;
  mutate: (action: 'status' | 'gate', id: string, status?: NodeStatus) => void;
  tab?: NodeTab; tabsDisabled?: boolean; changeTab?: (tab: NodeTab) => void; actions?: ReactNode; editor?: ReactNode; timeline?: ReactNode; graph?: ReactNode; color?: string;
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
  const current = phases.find(phase => !CLOSED.includes(phase.status));
  const gate = selected?.kind === 'phase' ? project.gates.find(item => item.node_id === selected.id) : undefined;
  const tabs = leaf ? [TABS[6], ...TABS.slice(0, 6)] : TABS;
  const active: NodeTab = tab;

  function statusControl(node: NodeItem, compact = false) {
    const allowed = statuses.filter(item => node.state_actions?.includes(item.status));
    return !readonly && node.kind !== 'project' && allowed.length > 0 && <label className={compact ? 'status-select compact' : 'status-select'}>
      <span className={compact ? 'sr-only' : undefined}>{node.kind === 'phase' ? '階段狀態' : '狀態'}</span>
      <select aria-label={`${node.title}狀態`} value={node.status} disabled={disabled} onChange={event => mutate('status', node.id, event.target.value as NodeStatus)}>
        {allowed.map(option => <option key={option.status} value={option.status}>{option.label}</option>)}
      </select></label>;
  }
  function card(node: NodeItem) {
    const phase = phaseOf(node);
    const late = isLate(node, today);
    return <article key={node.id} className={`task-card ${late ? 'late' : ''}`}>
      <div className="tags">{phase && <span className="tag gray">{phase.title}</span>}
        {node.kind !== 'task' && <span className="tag">{node.kind === 'phase' ? '階段' : '專案'}</span>}
        {late && <span className="tag warn">延遲</span>}
        {node.blocked && <span className="tag warn">🔒 等待前置</span>}
        {node.status === 'review' && <span className="tag blue">待確認回報</span>}
        {node.status === 'skipped' && <span className="tag gray">已略過</span>}</div>
      <button className="task-title" onClick={() => select(node.id)}>{node.title}</button>
      <div className="card-foot"><span className="who">{node.owner_display_name && <span className="avatar xs" aria-hidden="true">{node.owner_display_name.slice(0, 1)}</span>}
        <span className="who-name">{node.owner_display_name ?? '未指派'}{node.department_name ? `・${node.department_name}` : ''}</span></span>
        <span className="card-dates">{node.start_date || node.due_date ? `${shortDate(node.start_date)}–${shortDate(node.due_date)}` : '未設定日期'}</span></div>
      {statusControl(node, true)}
    </article>;
  }
  const crumbs = nodePath(nodes, selectedNodeId);
  const owner = selected?.owner_display_name;
  return <>
    <section aria-label="節點詳情" className="node-head">
      <div className="node-head-main">
        <nav aria-label="節點路徑" className="breadcrumbs"><button aria-current={selected ? undefined : 'location'} onClick={() => select(null)}>{project.title}</button>{crumbs.map(node => <span key={node.id}> / <button aria-current={node.id === selectedNodeId ? 'location' : undefined} onClick={() => select(node.id)}>{node.title}</button></span>)}</nav>
        <h1 className="node-title">{selected?.title ?? project.title}</h1>
        <div className="node-meta">
          {selected && <span>{selected.kind === 'task' ? '負責' : '負責人'}：{owner ?? '未指派'}{selected.department_name ? `・${selected.department_name}` : ''}</span>}
          <span>期間：{span.start ?? '未設定'} – {span.due ?? '未設定'}</span>
          {!leaf && <Progress value={completion(scope)} />}
          {selected && (statusControl(selected) || <span className="tag gray">{label(selected.status)}</span>)}
          {selected && isLate(selected, today) && <span className="tag warn">延遲</span>}
          {selected?.blocked && <span className="tag warn">🔒 尚有未完成的前置任務</span>}
        </div>
        {selected?.kind === 'phase' && <p className="small muted">階段狀態為手動設定，不代表子任務完成率。</p>}
      </div>
      <div className="head-actions">
        {owner && <span className="avatar member" title={owner} aria-hidden="true">{owner.slice(0, 1)}</span>}
        {actions}
      </div>
    </section>
    {selected?.kind === 'task' && recordsEnabled && reloadRecords && expired && <ReportPanel key={`report:${selected.id}:${recordVersion}`} node={selected} userId={userId} reload={reloadRecords} expired={expired}/>}
    {!selected && phases.length > 0 && <section className="phases" aria-label="開發階段與閘門">{phases.map(phase => {
      const phaseGate = project.gates.find(item => item.node_id === phase.id);
      const percent = completion(subtree(nodes, phase.id));
      return <button key={phase.id} className={`phase ${current?.id === phase.id ? 'cur' : ''}`} onClick={() => select(phase.id)} aria-label={`進入階段：${phase.title}`}>
        <span className="bar" aria-hidden="true"><span style={{ width: `${percent ?? 0}%`, background: phaseGate?.status === 'approved' ? color : '#E8A77F' }} /></span>
        <span className="phase-row"><span className="phase-name">{phase.title}</span><span className="small muted">{percent === null ? '—' : `${percent}%`}</span></span>
        <span className={`gate-chip ${phaseGate?.status === 'approved' ? 'ok' : ''}`}>{phaseGate?.status === 'approved' ? '✓ 閘門已核准' : current?.id === phase.id ? '● 目前階段' : phaseGate ? '○ 閘門未過' : '無閘門'}</span>
      </button>;
    })}</section>}
    {gate && <section className="panel gate-inline" aria-label="階段閘門">
      <div><b>階段閘門</b>　<span className="tag gray">{gate.status === 'approved' ? '✓ 已核准' : '待核准'}</span>
        {gate.status === 'pending' && <p className="small muted">尚有階段閘門待核准，後續階段可能被阻擋</p>}</div>
      {canApprove && gate.status === 'pending' && <button disabled={disabled} onClick={() => mutate('gate', gate.id)}>核准閘門</button>}
    </section>}
    <div className="node-toolbar"><div role="tablist" aria-label="節點內容">{tabs.map(item => item.tab === null
      ? <button key={item.label} role="tab" aria-selected={false} disabled className="tab-unavailable">{item.label}<span className="nav-badge">尚未提供</span></button>
      : <button key={item.tab} role="tab" aria-selected={active === item.tab} disabled={tabsDisabled} onClick={() => { if (item.tab !== active) changeTab?.(item.tab!); }}>{item.label}</button>)}</div>
      {active === 'board' && <span className="tools-hint">點卡片標題進入下一層；用卡片上的狀態選單改狀態</span>}
    </div>
    {editor}
    {active === 'board' && <section aria-label="看板" className="board-scroll">
      {items.length === 0 && <p className="empty">{nodes.length === 0 ? '這個專案還沒有節點。按「新增子節點」開始拆解。' : '目前沒有下一層節點'}</p>}
      {items.length > 0 && <div className="kanban">{columns.map(column => {
        const list = items.filter(node => column.match.includes(node.status));
        return <div key={column.label} aria-label={column.label} className="kanban-column">
          <h2>{column.label}<span className="column-count">{list.length}</span></h2>
          {list.map(card)}{list.length === 0 && <p className="hint">沒有項目</p>}
        </div>;
      })}</div>}
    </section>}
    {active === 'timeline' && <>{selected && <p className="scope-note">目前顯示整個專案的時程；節點自己的時程排在任務規劃器（TP-A）。</p>}{timeline}</>}
    {active === 'graph' && <>{selected && <p className="scope-note">目前顯示整個專案的相依圖；節點自己的相依圖排在任務規劃器（TP-A）。</p>}{graph}</>}
    {active === 'people' && selected && <div className="people-view">
      <div className="grid2">
        <section className="panel" aria-label="此節點的成員"><h3>此節點的成員</h3>
          <dl className="kv"><dt>負責人</dt><dd>{owner ? <><span className="avatar xs" aria-hidden="true">{owner.slice(0, 1)}</span>{owner}</> : '未指派'}</dd>
            <dt>部門</dt><dd>{selected.department_name ?? '未指派'}</dd></dl>
          <p className="small muted">協作人員與部門在下方設定。角色權限表與部門管理排在任務規劃器（TP-F）。</p>
        </section>
        <section className="panel" aria-label="我在此節點的權限"><h3>你（{userName}{roleLabel ? `・${roleLabel}` : ''}）在此節點可以</h3>
          <ul className="cap-list">{([
            ['檢視', true], ['編輯節點資料', selected.capabilities?.edit_metadata], ['指派負責人與部門', selected.capabilities?.assign],
            ['新增子節點', selected.capabilities?.create_child], ['寫筆記與上傳附件', selected.capabilities?.write_record],
            ['送出完成回報', selected.capabilities?.submit_report], ['確認或退回回報', selected.capabilities?.review_report],
            ['管理協作人員', selected.capabilities?.manage_collaborators], ['略過、重新開啟與恢復', selected.capabilities?.lifecycle],
            ...(selected.kind === 'phase' ? [['核准階段閘門', canApprove]] as const : []),
          ] as const).map(([text, ok]) => <li key={text} className={ok && !readonly || text === '檢視' ? 'yes' : 'no'}><span aria-hidden="true">{ok && !readonly || text === '檢視' ? '✓' : '✗'}</span>{text}<span className="sr-only">{ok && !readonly || text === '檢視' ? '：可以' : '：不可以'}</span></li>)}</ul>
        </section>
      </div>
      {recordsEnabled && reloadRecords && expired && <CollaboratorEditor key={`people:${selected.id}:${recordVersion}`} nodeId={selected.id} projectId={selected.project_id} manage={!!selected.capabilities?.manage_collaborators} reload={reloadRecords} expired={expired} />}
    </div>}
    {active === 'people' && !selected && <p className="empty">專案層的成員與權限頁排在任務規劃器（TP-F）；進入階段或任務可查看該節點的成員與你的權限。</p>}
    {active === 'records' && selected && recordsEnabled && reloadRecords && expired && <RecordTimeline key={`records:${selected.id}:${recordVersion}`} node={selected} userId={userId} reload={reloadRecords} expired={expired} select={select}/>}
    {active === 'records' && !selected && <p className="empty">專案層的紀錄彙總排在任務規劃器；進入階段或任務查看紀錄。</p>}
  </>;
}
