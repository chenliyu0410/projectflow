import type { NodeItem } from './types';

/** The fields the rollup reads; API nodes and test vectors both fit. */
export type ProgressNode = Pick<NodeItem, 'id' | 'parent_id' | 'kind' | 'status' | 'sort_order'> & { weight?: number | null; progress?: number | null };

// Mirrors api/app/services/progress.py operation by operation so both sides round to the same percent.
const LEAF_TASK: Record<string, number> = { todo: 0, review: 90, done: 100, skipped: 100 };

export function leafProgress(node: ProgressNode) {
  if (node.kind === 'task') return node.status === 'doing' ? node.progress ?? 50 : LEAF_TASK[node.status] ?? 0;
  return node.status === 'done' || node.status === 'skipped' ? 100 : 0;
}
export const weightOf = (node: ProgressNode) => node.weight ?? 1;
/** Half-up; the epsilon absorbs binary rounding of exact .5 averages. */
export const percent = (value: number) => Math.floor(value + 0.5 + 1e-9);

function childrenMap<T extends ProgressNode>(nodes: T[]) {
  const ids = new Set(nodes.map(node => node.id));
  const children = new Map<string, T[]>();
  for (const node of [...nodes].sort((a, b) => a.sort_order - b.sort_order)) {
    if (!node.parent_id || !ids.has(node.parent_id) || node.parent_id === node.id) continue;
    children.set(node.parent_id, [...children.get(node.parent_id) ?? [], node]);
  }
  return children;
}
/** Visible nodes whose parent is hidden or missing; damaged cycles keep one entry. */
export function rollupRoots<T extends ProgressNode>(nodes: T[]) {
  const ids = new Set(nodes.map(node => node.id));
  const children = childrenMap(nodes);
  const roots = nodes.filter(node => !node.parent_id || !ids.has(node.parent_id));
  const visited = new Set<string>();
  const visit = (start: T) => {
    const pending = [start];
    while (pending.length) {
      const item = pending.pop()!;
      if (visited.has(item.id)) continue;
      visited.add(item.id); pending.push(...children.get(item.id) ?? []);
    }
  };
  roots.forEach(visit);
  for (const node of [...nodes].sort((a, b) => a.sort_order - b.sort_order)) if (!visited.has(node.id)) { roots.push(node); visit(node); }
  return roots.sort((a, b) => a.sort_order - b.sort_order);
}
/** Unrounded progress of every visible node: leaf by status, parents weight-average their visible children. */
export function progressMap(nodes: ProgressNode[]) {
  const children = childrenMap(nodes);
  const memo = new Map<string, number>();
  const active = new Set<string>();
  function compute(node: ProgressNode): number {
    const known = memo.get(node.id);
    if (known !== undefined) return known;
    active.add(node.id);
    const kids = (children.get(node.id) ?? []).filter(child => !active.has(child.id));
    let value: number;
    if (kids.length === 0) value = leafProgress(node);
    else {
      let total = 0; let weighted = 0;
      for (const child of kids) { const weight = weightOf(child); total += weight; weighted += compute(child) * weight; }
      value = total ? weighted / total : 0;
    }
    active.delete(node.id); memo.set(node.id, value);
    return value;
  }
  rollupRoots(nodes).forEach(compute);
  nodes.forEach(compute);
  return memo;
}
/** Weight-averaged visible top level; null when nothing is visible. */
export function projectProgress(nodes: ProgressNode[], values = progressMap(nodes)) {
  const roots = rollupRoots(nodes);
  if (roots.length === 0) return null;
  let total = 0; let weighted = 0;
  for (const root of roots) { const weight = weightOf(root); total += weight; weighted += values.get(root.id)! * weight; }
  return percent(total ? weighted / total : 0);
}
