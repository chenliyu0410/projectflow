import type { Dependency, NodeItem } from './types';

export const dayMs = 86400000;
export const calendarDay = (value: string) => Date.parse(`${value}T00:00:00Z`) / dayMs;
export const calendarDate = (day: number) => new Date(day * dayMs).toISOString().slice(0, 10);
export type Span = { start: number | null; due: number | null };

/** Visible data only. A parent's own planned dates remain part of its envelope. */
export function timelineSpans(nodes: NodeItem[]): Map<string, Span> {
  const result = new Map<string, Span>();
  const children = new Map<string, string[]>();
  const ids = new Set(nodes.map(n => n.id));
  for (const n of nodes) {
    result.set(n.id, { start: n.start_date ? calendarDay(n.start_date) : null, due: n.due_date ? calendarDay(n.due_date) : null });
    if (n.parent_id && ids.has(n.parent_id)) children.set(n.parent_id, [...(children.get(n.parent_id) ?? []), n.id]);
  }
  const order = nodes.filter(n => !n.parent_id || !ids.has(n.parent_id)).map(n => n.id);
  const seen = new Set<string>();
  for (let i = 0; i < order.length; i++) {
    const id = order[i]; if (seen.has(id)) continue; seen.add(id);
    for (const child of children.get(id) ?? []) if (!seen.has(child)) order.push(child);
  }
  for (const id of order.reverse()) {
    const span = result.get(id)!;
    for (const child of children.get(id) ?? []) {
      const s = result.get(child)!;
      if (s.start !== null) span.start = span.start === null ? s.start : Math.min(span.start, s.start);
      if (s.due !== null) span.due = span.due === null ? s.due : Math.max(span.due, s.due);
    }
  }
  return result;
}

export function departmentNodes(nodes: NodeItem[], department: string) {
  if (department === 'all') return nodes;
  const byId = new Map(nodes.map(n => [n.id, n])); const keep = new Set<string>();
  for (const n of nodes) {
    if (n.kind !== 'task' || (n.department_id ?? 'none') !== department) continue;
    let cursor: NodeItem | undefined = n; const seen = new Set<string>();
    while (cursor && !seen.has(cursor.id)) { seen.add(cursor.id); keep.add(cursor.id); cursor = byId.get(cursor.parent_id ?? ''); }
  }
  return nodes.filter(n => keep.has(n.id));
}

/** Demo-style single limiting chain, not CPM/float analysis. Parent edges map to boundary leaves. */
export function criticalChain(nodes: NodeItem[], edges: Dependency[]) {
  const ranges = timelineSpans(nodes); const byId = new Map(nodes.map(n => [n.id, n]));
  const children = new Map<string, NodeItem[]>();
  for (const n of nodes) if (n.parent_id) children.set(n.parent_id, [...(children.get(n.parent_id) ?? []), n]);
  const leaves = nodes.filter(n => !children.has(n.id) && n.kind === 'task' && n.start_date && n.due_date);
  const leafIds = new Set(leaves.map(n => n.id));
  function boundary(id: string, first: boolean): string | undefined {
    const pending = [id], seen = new Set<string>(), candidates: string[] = [];
    for (let i = 0; i < pending.length; i++) {
      const cur = pending[i]; if (seen.has(cur)) continue; seen.add(cur);
      if (leafIds.has(cur)) candidates.push(cur);
      for (const child of children.get(cur) ?? []) pending.push(child.id);
    }
    return candidates.sort((a, b) => (first ? ranges.get(a)!.start! - ranges.get(b)!.start! : ranges.get(b)!.due! - ranges.get(a)!.due!) || a.localeCompare(b))[0];
  }
  const links = edges.flatMap(edge => {
    if (!byId.has(edge.predecessor_id) || !byId.has(edge.successor_id)) return [];
    const from = boundary(edge.predecessor_id, false), to = boundary(edge.successor_id, true);
    return from && to ? [{ from, to, edge }] : [];
  });
  const indegree = new Map(leaves.map(n => [n.id, 0]));
  for (const e of links) indegree.set(e.to, indegree.get(e.to)! + 1);
  const queue = leaves.filter(n => !indegree.get(n.id)).map(n => n.id).sort();
  const end = new Map(leaves.map(n => [n.id, ranges.get(n.id)!.due!]));
  const previous = new Map<string, (typeof links)[number]>();
  for (let i = 0; i < queue.length; i++) {
    const id = queue[i];
    for (const link of links.filter(e => e.from === id).sort((a, b) => a.edge.id.localeCompare(b.edge.id))) {
      const r = ranges.get(link.to)!;
      const predicted = end.get(id)! + 1 + r.due! - r.start!;
      // Keep a predecessor even across planned slack, matching the Demo's limiting-chain display.
      const prev = previous.get(link.to);
      if (!prev || end.get(id)! > end.get(prev.from)!) previous.set(link.to, link);
      end.set(link.to, Math.max(end.get(link.to)!, predicted));
      indegree.set(link.to, indegree.get(link.to)! - 1);
      if (indegree.get(link.to) === 0) queue.push(link.to);
    }
  }
  if (queue.length !== leaves.length) return { nodes: new Set<string>(), edges: new Set<string>(), invalid: true };
  let id = [...leafIds].sort((a, b) => end.get(b)! - end.get(a)! || a.localeCompare(b))[0];
  const marked = new Set<string>(), markedEdges = new Set<string>();
  while (id && !marked.has(id)) {
    marked.add(id); const link = previous.get(id); if (!link) break;
    markedEdges.add(link.edge.id); marked.add(link.edge.predecessor_id); marked.add(link.edge.successor_id);
    // Parent marking must not stop traversal through a leaf predecessor.
    const next = link.from; marked.delete(next); id = next;
  }
  return { nodes: marked, edges: markedEdges, invalid: false };
}

export function visibleEndpoint(id: string, nodes: NodeItem[], rows: Set<string>): string | null {
  const byId = new Map(nodes.map(n => [n.id, n])); const seen = new Set<string>();
  while (byId.has(id) && !seen.has(id)) {
    if (rows.has(id)) return id;
    seen.add(id); id = byId.get(id)!.parent_id ?? '';
  }
  return null;
}
