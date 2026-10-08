import { useId } from 'react';
import type { DependencyData } from '../types';
export default function DependencyGraph({
  data,
  select,
}: {
  data: DependencyData;
  select: (id: string) => void;
}) {
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
  const rows = new Map<number, number>();
  const positions = new Map(
    data.nodes.map((n) => {
      const level = levels.get(n.id)!;
      const row = rows.get(level) ?? 0;
      rows.set(level, row + 1);
      return [n.id, { x: 20 + level * 240, y: 20 + row * 90 }];
    }),
  );
  const width = Math.max(640, (Math.max(0, ...levels.values()) + 1) * 240);
  const height = Math.max(150, Math.max(0, ...rows.values()) * 90 + 40);
  return (
    <section aria-label="可見任務相依圖">
      <h3>可見任務相依圖</h3>
      <p>僅顯示兩端皆可見的連線；完成或略過前置後，後續任務才可開始。</p>
      {data.nodes.length === 0 ? (
        <p>目前沒有可見任務</p>
      ) : (
        <div className="dependency-graph">
          <svg
            role="img"
            aria-label="任務前置連線圖"
            viewBox={`0 0 ${width} ${height}`}
            style={{ width, height }}
          >
            <defs>
              <marker
                id={marker}
                markerWidth="8"
                markerHeight="8"
                refX="7"
                refY="4"
                orient="auto"
              >
                <path d="M0,0 L8,4 L0,8" fill="#637b7a" />
              </marker>
            </defs>
            {edges.map((e) => {
              const a = positions.get(e.predecessor_id)!,
                b = positions.get(e.successor_id)!;
              return (
                <path
                  key={e.id}
                  d={`M${a.x + 180},${a.y + 25} C${a.x + 210},${a.y + 25} ${b.x - 30},${b.y + 25} ${b.x},${b.y + 25}`}
                  fill="none"
                  stroke="#637b7a"
                  strokeWidth="2"
                  markerEnd={`url(#${marker})`}
                />
              );
            })}
            {data.nodes.map((n) => {
              const p = positions.get(n.id)!;
              return (
                <g
                  key={n.id}
                  role="button"
                  tabIndex={0}
                  aria-label={`開啟任務：${n.title}`}
                  onClick={() => select(n.id)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      select(n.id);
                    }
                  }}
                >
                  <title>
                    {n.title}
                    {n.blocked ? '：尚有未完成的前置任務' : ''}
                  </title>
                  <rect
                    x={p.x}
                    y={p.y}
                    width="180"
                    height="54"
                    rx="9"
                    fill={n.blocked ? '#fff4e5' : '#e7f2ef'}
                    stroke="#638b83"
                  />
                  <text x={p.x + 10} y={p.y + 24}>
                    {n.title.length > 13 ? n.title.slice(0, 12) + '…' : n.title}
                  </text>
                  <text x={p.x + 10} y={p.y + 43} fontSize="11">
                    {n.blocked
                      ? '尚有未完成的前置任務'
                      : n.status === 'done'
                        ? '完成'
                        : n.status === 'skipped'
                          ? '已略過'
                          : '前置條件已滿足'}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>
      )}
    </section>
  );
}
