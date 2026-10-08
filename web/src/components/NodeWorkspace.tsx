import { useEffect, useState } from 'react';
import type { NodeItem, NodeStatus, ProjectDetail } from '../types';

export const statuses: { status: NodeStatus; label: string }[] = [
  { status: 'todo', label: '待處理' }, { status: 'doing', label: '進行中' },
  { status: 'review', label: '待確認' }, { status: 'done', label: '完成' }, { status: 'skipped', label: '已略過' },
];
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
function visibleRoots(nodes: NodeItem[]) {
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

export default function NodeWorkspace({ project, selectedNodeId, select, readonly, canApprove, disabled, mutate }: {
  project: ProjectDetail; selectedNodeId: string | null; select: (id: string | null) => void;
  readonly: boolean; canApprove: boolean; disabled: boolean;
  mutate: (action: 'status' | 'gate', id: string, status?: NodeStatus) => void;
}) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  useEffect(() => {
    setExpanded(value => new Set([...value, ...nodePath(project.nodes, selectedNodeId).map(node => node.id)]));
  }, [project.nodes, selectedNodeId]);
  const selected = project.nodes.find(node => node.id === selectedNodeId);
  const roots = visibleRoots(project.nodes);
  const children = (selectedNodeId === null ? roots : project.nodes.filter(node => node.parent_id === selectedNodeId && node.id !== selectedNodeId))
    .sort((a, b) => a.sort_order - b.sort_order);
  function tree(items: NodeItem[], ancestors = new Set<string>()) {
    return <ul>{items.filter(node => !ancestors.has(node.id)).map(node => {
      const branch = new Set([...ancestors, node.id]);
      const descendants = project.nodes.filter(child => child.parent_id === node.id && !branch.has(child.id)).sort((a, b) => a.sort_order - b.sort_order);
      return <li key={node.id}><div className="tree-row">
        {descendants.length > 0 && <button className="tree-toggle" aria-label={`${expanded.has(node.id) ? '收合' : '展開'}${node.title}`} aria-expanded={expanded.has(node.id)} onClick={() => setExpanded(value => {
          const next = new Set(value); if (next.has(node.id)) next.delete(node.id); else next.add(node.id); return next;
        })}>{expanded.has(node.id) ? '−' : '+'}</button>}
        <button aria-pressed={selectedNodeId === node.id} onClick={() => select(node.id)}>{node.title}</button>
      </div>{expanded.has(node.id) && descendants.length > 0 && tree(descendants, branch)}</li>;
    })}</ul>;
  }
  function statusControl(node: NodeItem) {
    return !readonly && node.kind !== 'project' && <label>狀態<select aria-label={`${node.title}狀態`} value={node.status} disabled={disabled} onChange={event => mutate('status', node.id, event.target.value as NodeStatus)}>
      {statuses.map(option => <option key={option.status} value={option.status}>{option.label}</option>)}
    </select></label>;
  }
  return <>
    <h1>{project.title}</h1>
    <nav aria-label="節點路徑" className="breadcrumbs"><button onClick={() => select(null)}>{project.title}</button>{nodePath(project.nodes, selectedNodeId).map(node => <span key={node.id}> / <button aria-current={node.id === selectedNodeId ? 'location' : undefined} onClick={() => select(node.id)}>{node.title}</button></span>)}</nav>
    <section aria-label="節點樹" className="node-tree"><h2>節點</h2>{project.nodes.length === 0 ? <p>這個專案還沒有節點</p> : tree(roots)}</section>
    <section aria-label="節點詳情" className="node-detail"><h2>節點詳情</h2><strong>{selected?.title ?? project.title}</strong>
      {selected ? <><dl>
        <div><dt>狀態</dt><dd>{statuses.find(item => item.status === selected.status)?.label ?? selected.status}</dd></div>
        <div><dt>負責人</dt><dd>{selected.owner_display_name ?? '未指派'}</dd></div>
        <div><dt>部門</dt><dd>{selected.department_name ?? '未指派'}</dd></div>
        <div><dt>開始日期</dt><dd>{selected.start_date ?? '未設定'}</dd></div>
        <div><dt>截止日期</dt><dd>{selected.due_date ?? '未設定'}</dd></div>
      </dl>{selected.kind !== 'project' && statusControl(selected)}</> : <p>專案工作區</p>}
    </section>
    {project.gates.some(gate => gate.status === 'pending') && <div className="gate-banner"><p>尚有階段閘門待核准，後續階段可能被阻擋</p>
      {canApprove && project.gates.filter(gate => gate.status === 'pending').map(gate => <div className="gate-row" key={gate.id}>
        <span>{project.nodes.find(node => node.id === gate.node_id)?.title ?? '階段閘門'}</span><button disabled={disabled} onClick={() => mutate('gate', gate.id)}>核准閘門</button>
      </div>)}
    </div>}
    <section aria-label="看板"><h2>下一層節點</h2>{children.length === 0 && <p>目前沒有下一層節點</p>}
      <div className="kanban">{statuses.map(column => <div key={column.status} aria-label={column.label} className={`kanban-column ${column.status === 'skipped' ? 'skipped-list' : ''}`}>
        <h2>{column.label}</h2>{children.filter(node => node.status === column.status).map(node => <article key={node.id} className="task-card">
          <button className="task-title" onClick={() => select(node.id)}>{node.title}</button>{statusControl(node)}
        </article>)}
      </div>)}</div>
    </section>
  </>;
}
