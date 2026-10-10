import { dependencyMet, dependencyLabel } from '../dependencies';
import { useId, useRef, useState } from 'react';
import type { DependencyData, NodeItem } from '../types';
// Demo layout: 200×58 boxes, left-to-right by predecessor depth, orthogonal arrows that only move right.
const GW = 200, GH = 58, GCOL = 260, GROW = 80;
const shortDate = (value: string | null | undefined) => value ? value.slice(5).replace('-', '/') : '?';
const closed = (status: string | undefined) => status === 'done' || status === 'skipped';
function orthoPath(points: number[][], r = 5) {
  let d = `M${points[0][0]},${points[0][1]}`;
  for (let i = 1; i < points.length - 1; i++) {
    const [px, py] = points[i - 1], [x, y] = points[i], [nx, ny] = points[i + 1];
    const a = Math.min(r, Math.hypot(x - px, y - py) / 2), b = Math.min(r, Math.hypot(nx - x, ny - y) / 2);
    const ux = Math.sign(x - px), uy = Math.sign(y - py), vx = Math.sign(nx - x), vy = Math.sign(ny - y);
    d += ` L${x - ux * a},${y - uy * a} Q${x},${y} ${x + vx * b},${y + vy * b}`;
  }
  const last = points[points.length - 1];
  return `${d} L${last[0]},${last[1]}`;
}
export default function DependencyGraph({
  data,
  select,
  nodes = [],
  connect,
}: {
  data: DependencyData;
  select: (id: string) => void;
  nodes?: NodeItem[];
  connect?: (from: string, to: string) => void;
}) {
  const suppressClick = useRef(false);
  const drag = useRef<string | null>(null);
  const [pointer, setPointer] = useState<{x:number;y:number} | null>(null);
  const [dragging, setDragging] = useState<string | null>(null);
  const marker = useId().replaceAll(':', '');
  const ids = new Set(data.nodes.map((n) => n.id));
  const edges = data.items.filter(
    (e) => ids.has(e.predecessor_id) && ids.has(e.successor_id),
  );
  const levels = new Map(data.nodes.map((n) => [n.id, 0]));
  const incoming = new Map(
    data.nodes.map((n) => [
      n.id,
      edges.filter((e) => e.successor_id === n.id).length,
    ]),
  );
  const queue = data.nodes
    .filter((n) => incoming.get(n.id) === 0)
    .map((n) => n.id);
  const seen = new Set<string>();
  while (queue.length) {
    const id = queue.shift()!;
    if (seen.has(id)) continue;
    seen.add(id);
    for (const e of edges.filter((e) => e.predecessor_id === id)) {
      levels.set(
        e.successor_id,
        Math.max(levels.get(e.successor_id)!, levels.get(id)! + 1),
      );
      incoming.set(e.successor_id, incoming.get(e.successor_id)! - 1);
      if (incoming.get(e.successor_id) === 0) queue.push(e.successor_id);
    }
  }
  const byId = new Map(nodes.map((n) => [n.id, n]));
  const path = (id: string) => {
    const out: string[] = []; const visited = new Set<string>([id]);
    let parent = byId.get(id)?.parent_id ? byId.get(byId.get(id)!.parent_id!) : undefined;
    while (parent && !visited.has(parent.id)) { visited.add(parent.id); out.unshift(parent.title); parent = parent.parent_id ? byId.get(parent.parent_id) : undefined; }
    return out.join(' › ');
  };
  const rows = new Map<number, number>();
  const ordered = [...data.nodes].sort((a, b) => (byId.get(a.id)?.start_date ?? '').localeCompare(byId.get(b.id)?.start_date ?? '') || (byId.get(a.id)?.sort_order ?? 0) - (byId.get(b.id)?.sort_order ?? 0));
  const positions = new Map(
    ordered.map((n) => {
      const level = levels.get(n.id)!;
      const row = rows.get(level) ?? 0;
      rows.set(level, row + 1);
      return [n.id, { x: 24 + level * GCOL, y: 24 + row * GROW, c: level }];
    }),
  );
  const width = Math.max(GCOL + 40, (Math.max(0, ...levels.values()) + 1) * GCOL + 40);
  const height = Math.max(GROW + 40, Math.max(0, ...rows.values()) * GROW + 40);
  const status = new Map(data.nodes.map((n) => [n.id, n.status]));
  return (
    <section aria-label="可見任務相依圖" className="graph-section">
      {data.nodes.length === 0 ? (
        <p className="empty">沒有可顯示的任務。</p>
      ) : (
        <div className="dependency-graph">
          <div className="graph-canvas" style={{ width, height }} onPointerMove={e => {if(drag.current) {const r=e.currentTarget.getBoundingClientRect(); setPointer({x:e.clientX-r.left,y:e.clientY-r.top});}}} onPointerUp={() => {drag.current = null; setDragging(null);}} onPointerCancel={() => {drag.current = null; setDragging(null);}} onPointerLeave={() => {drag.current = null; setDragging(null);}}>
            {dragging && <span role="status">拖到後續任務方塊以設定前置</span>}
            <svg
              role="img"
              aria-label="任務前置連線圖"
              width={width}
              height={height}
              viewBox={`0 0 ${width} ${height}`}
            >
              <defs>
                <marker id={`${marker}-ok`} markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8" fill="#9A958B" /></marker>
                <marker id={`${marker}-wait`} markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8" fill="#D9824F" /></marker>
              </defs>
              {dragging && pointer && positions.has(dragging) && <line x1={positions.get(dragging)!.x+GW} y1={positions.get(dragging)!.y+GH/2} x2={pointer.x} y2={pointer.y} stroke="#1F5F5B" strokeDasharray="4 3"/>}
              {edges.map((e) => {
                const a = positions.get(e.predecessor_id)!, b = positions.get(e.successor_id)!;
                const x1 = a.x + (e.relation_type === 'SS' ? 0 : GW), y1 = a.y + GH / 2, x2 = b.x + (e.relation_type === 'FF' ? GW : 0), y2 = b.y + GH / 2;
                const g1 = x1 + (GCOL - GW) / 2, g2 = x2 - (GCOL - GW) / 2;
                const points = b.c - a.c <= 1
                  ? y1 === y2 ? [[x1, y1], [x2, y2]] : [[x1, y1], [g1, y1], [g1, y2], [x2, y2]]
                  : [[x1, y1], [g1, y1], [g1, b.y - (GROW - GH) / 2], [g2, b.y - (GROW - GH) / 2], [g2, y2], [x2, y2]];
                const met = dependencyMet(e, status.get(e.predecessor_id));
                return (
                  <path
                    key={e.id}
                    d={orthoPath(points)}
                    fill="none"
                    stroke={met ? '#9A958B' : '#D9824F'}
                    strokeWidth="1.6"
                    strokeDasharray={met ? undefined : '5 4'}
                    markerEnd={`url(#${marker}-${met ? 'ok' : 'wait'})`}
                  ><title>{dependencyLabel(e)}：{met ? '已滿足' : '未滿足'}</title></path>
                );
              })}
            </svg>
            {data.nodes.map((n) => {
              const p = positions.get(n.id)!;
              const item = byId.get(n.id);
              const trail = path(n.id);
              return (
                <div key={n.id}>
                <button
                  className={`gnode ${closed(n.status) ? 'done' : ''}`}
                  style={{ left: p.x, top: p.y }}
                  aria-label={`開啟任務：${n.title}`}
                  title={`${trail ? `${trail} › ` : ''}${n.title}${n.blocked ? '：尚有未完成的前置任務' : ''}`}
                  onPointerUp={e => { if(drag.current && connect) {e.preventDefault(); e.stopPropagation(); suppressClick.current = true; const from = drag.current; drag.current = null; setDragging(null); if(from !== n.id) connect(from, n.id); } }}
                  onClick={() => {if(suppressClick.current) {suppressClick.current = false; return;} if(!dragging) select(n.id);}}
                >
                  <span className="gmeta">
                    <span className={`dot ${n.status}`} aria-hidden="true" />
                    <span>{item && (item.start_date || item.due_date) ? `${shortDate(item.start_date)}–${shortDate(item.due_date)}` : '未排程'}</span>
                    {n.blocked && <span className="tag warn">🔒</span>}
                    <span className="gpath">{trail}</span>
                  </span>
                  <b>{n.title}</b>
                </button>
                {connect && <button type="button" className="dependency-handle" style={{left: p.x + GW - 10, top: p.y + GH / 2 - 10}} aria-label={`拖線建立前置：${n.title}`} onPointerDown={e => { if(e.button !== 0) return; e.preventDefault(); drag.current = n.id; setPointer({x:p.x+GW,y:p.y+GH/2}); setDragging(n.id); }} onKeyDown={e => {if(e.key === 'Escape') {drag.current = null; setDragging(null);}}}>＋</button>}
                </div>
              );
            })}
          </div>
        </div>
      )}
      <p className="small muted">由左到右依前後順序排列，箭頭只往右推進。灰色實線＝前置已滿足；橘色虛線＝尚未滿足（軟性僅警示、FF限制完成）。管理者可從＋拖到任務方塊，或用上方表單建立連線。點方塊進入任務。</p>
    </section>
  );
}
