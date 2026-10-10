import { useRef, useState } from 'react';
import type { PointerEvent as ReactPointerEvent } from 'react';
import { api, useRecordMutation } from '../api';
import type { RecordReload } from '../api';
import type { NodeItem, ProjectDetail } from '../types';
import { subtree } from './NodeWorkspace';
import { percent, progressMap } from '../progress';
const dayMs = 86400000;
export function calendarDay(value: string) {
  return Date.parse(`${value}T00:00:00Z`) / dayMs;
}
export function calendarDate(day: number) {
  return new Date(day * dayMs).toISOString().slice(0, 10);
}
export function shiftDates(
  start: string,
  due: string,
  offset: number,
  resize = false,
) {
  const first = calendarDay(start);
  const last = calendarDay(due);
  const min = calendarDay('0001-01-01'),
    max = calendarDay('9999-12-31');
  const delta = resize
    ? Math.max(first - last, Math.min(max - last, offset))
    : Math.max(min - first, Math.min(max - last, offset));
  return {
    start_date: resize ? start : calendarDate(first + delta),
    due_date: calendarDate(last + delta),
  };
}
export function timelineRows(nodes: NodeItem[], collapsed: Set<string>) {
  const ids = new Set(nodes.map((n) => n.id));
  const visited = new Set<string>();
  const rows: { node: NodeItem; depth: number; children: boolean }[] = [];
  const sorted = [...nodes].sort((a, b) => a.sort_order - b.sort_order);
  function visit(n: NodeItem, depth: number, hidden = false) {
    if (visited.has(n.id)) return;
    visited.add(n.id);
    const children = sorted.filter((c) => c.parent_id === n.id);
    if (!hidden) rows.push({ node: n, depth, children: children.length > 0 });
    for (const child of children)
      visit(child, depth + 1, hidden || collapsed.has(n.id));
  }
  for (const n of sorted.filter((n) => !n.parent_id || !ids.has(n.parent_id)))
    visit(n, 0);
  for (const n of sorted) visit(n, 0);
  return rows;
}
export default function TimelineView({
  project,
  scopeId = null,
  select,
  up,
  reload,
  expired,
  color = 'var(--teal)',
  undo,
}: {
  project: ProjectDetail;
  /** Like the Demo, a node's timeline shows only that node and its descendants. */
  scopeId?: string | null;
  select: (id: string) => void;
  up?: (id: string | null) => void;
  reload: RecordReload;
  expired: () => void;
  color?: string;
  /** Demo toolbar 「↶ 復原」: undoes the user's last structure change (TP-B). */
  undo?: { label: string | null; disabled: boolean; run: () => void };
}) {
  // A blank project's kind=project root is the project level itself.
  const root = scopeId ? project.nodes.find((n) => n.id === scopeId && n.kind !== 'project') : undefined;
  const nodes = root ? subtree(project.nodes, root.id) : project.nodes;
  const parent = root?.parent_id ? project.nodes.find((n) => n.id === root.parent_id) : undefined;
  const values = progressMap(project.nodes);
  const [zoom, setZoom] = useState('week');
  const [collapsed, setCollapsed] = useState(new Set<string>());
  const [draft, setDraft] = useState<{
    node: NodeItem;
    start: string;
    due: string;
  } | null>(null);
  const [preview, setPreview] = useState<{
    id: string;
    start_date: string;
    due_date: string;
  } | null>(null);
  const gesture = useRef<{
    node: NodeItem;
    x: number;
    resize: boolean;
    delta: number;
    scale: number;
  } | null>(null);
  const mutation = useRecordMutation(reload, expired);
  const now = new Date();
  const today = calendarDay(
    `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`,
  );
  const dates = nodes.flatMap((n) =>
    [n.start_date, n.due_date].filter((d): d is string => !!d).map(calendarDay),
  );
  const left = Math.min(today, ...dates) - 2,
    right = Math.max(today, ...dates) + 2;
  const count = right - left + 1;
  const scale = Math.min(
    zoom === 'day' ? 36 : zoom === 'week' ? 12 : 4,
    12000 / count,
  );
  const width = Math.max(600, count * scale);
  const actualScale = width / count;
  // Demo scale: month labels on top, then day numbers (日) or Mondays (週) underneath.
  // Labels are thinned by pixel spacing so very long ranges (e.g. a mistyped year) stay bounded.
  const months: number[] = [];
  const subs: number[] = [];
  const subGap = zoom === 'day' ? 14 : 28;
  let lastMonth = -Infinity, lastSub = -Infinity;
  for (let d = left; d <= right; d++) {
    const date = new Date(d * dayMs);
    const x = (d - left) * actualScale;
    if (d === left || date.getUTCDate() === 1) {
      if (x - lastMonth >= 40) { months.push(d); lastMonth = x; }
      // A real month start wins over the partial leading month it collides with.
      else if (months.length === 1 && months[0] === left) { months[0] = d; lastMonth = x; }
    }
    if ((zoom === 'day' ? actualScale >= 14 : zoom === 'week' && date.getUTCDay() === 1) && x - lastSub >= subGap) { subs.push(d); lastSub = x; }
  }
  const firstMonday = left + ((8 - new Date(left * dayMs).getUTCDay()) % 7);
  const grid = zoom === 'month' ? undefined : {
    backgroundImage: `repeating-linear-gradient(90deg,transparent 0,transparent ${actualScale * 7 - 1}px,#F0EDE6 ${actualScale * 7 - 1}px,#F0EDE6 ${actualScale * 7}px)`,
    backgroundPosition: `${(firstMonday - left) * actualScale}px 0`,
  };
  const short = (day: number) => { const d = new Date(day * dayMs); return `${d.getUTCMonth() + 1}/${d.getUTCDate()}`; };
  const rows = timelineRows(nodes, collapsed);
  const taskCount = (id: string) => {
    const seen = new Set<string>([id]); const pending = [id]; let total = 0;
    while (pending.length) { const current = pending.pop()!; for (const c of project.nodes) if (c.parent_id === current && !seen.has(c.id)) { seen.add(c.id); pending.push(c.id); if (c.kind === 'task') total += 1; } }
    return total;
  };
  function edit(n: NodeItem) {
    if (mutation.busy || mutation.saved) return;
    setDraft({ node: n, start: n.start_date ?? '', due: n.due_date ?? '' });
  }
  function begin(
    e: ReactPointerEvent<HTMLButtonElement>,
    n: NodeItem,
    resize = false,
  ) {
    if (
      !n.capabilities.edit_metadata ||
      n.kind !== 'task' ||
      mutation.busy ||
      mutation.saved ||
      !n.start_date ||
      !n.due_date ||
      e.pointerType === 'touch'
    )
      return;
    e.preventDefault();
    e.currentTarget.setPointerCapture?.(e.pointerId);
    gesture.current = {
      node: n,
      x: e.clientX,
      resize,
      delta: 0,
      scale: actualScale,
    };
  }
  function move(e: ReactPointerEvent<HTMLButtonElement>) {
    const g = gesture.current;
    if (!g) return;
    g.delta = Math.round((e.clientX - g.x) / g.scale);
    setPreview({
      id: g.node.id,
      ...shiftDates(g.node.start_date!, g.node.due_date!, g.delta, g.resize),
    });
  }
  function end() {
    const g = gesture.current;
    gesture.current = null;
    setPreview(null);
    if (!g) return;
    if (g.delta === 0) {
      if (!g.resize) select(g.node.id);
      return;
    }
    const dates = shiftDates(
      g.node.start_date!,
      g.node.due_date!,
      g.delta,
      g.resize,
    );
    setDraft({ node: g.node, start: dates.start_date, due: dates.due_date });
  }
  const statusText = {
    todo: '待處理',
    doing: '進行中',
    review: '待確認',
    done: '完成',
    skipped: '已略過',
  };
  const full = (n: NodeItem) => !!n.start_date && !!n.due_date;
  return (
    <section className="timeline-view" aria-label="專案時程">
      <div className="tl-tools">
        {root ? (
          <button type="button" className="tl-up" onClick={() => up?.(parent && parent.kind !== 'project' ? parent.id : null)}>
            ↑ 上一層：{parent?.title ?? project.title}
          </button>
        ) : (
          <span className="tag">總覽圖</span>
        )}
        <span>點名稱進入節點；拖移任務條改期、拖右端改截止日，或按 ✎ 輸入日期，確認後才儲存。只變更選定節點的日期，不自動順延其他任務。</span>
        <span className="seg" role="group" aria-label="時程刻度">
          {([['day', '日'], ['week', '週'], ['month', '月']] as const).map(([value, text]) => (
            <button key={value} type="button" aria-pressed={zoom === value} onClick={() => setZoom(value)}>{text}</button>
          ))}
        </span>
        <span>今天：{calendarDate(today)}</span>
        {undo && (
          <button type="button" disabled={undo.disabled || !undo.label} title={undo.label ? `復原：${undo.label}` : '沒有可以復原的操作'} onClick={undo.run}>
            ↶ 復原
          </button>
        )}
      </div>
      {draft && (
        <form
          className="record-panel schedule-editor"
          aria-label="日期表單"
          onSubmit={(e) => {
            e.preventDefault();
            if (draft.start && draft.due && draft.start > draft.due) return;
            void mutation.execute((signal) =>
              api.updateNode(
                draft.node.id,
                {
                  start_date: draft.start || null,
                  due_date: draft.due || null,
                },
                signal,
              ),
            );
          }}
        >
          <h3>調整日期：{draft.node.title}</h3>
          {mutation.error && <p role="alert">{mutation.error}</p>}
          {mutation.saved ? (
            <button
              type="button"
              disabled={mutation.busy}
              onClick={() => void mutation.execute()}
            >
              重試時程載入
            </button>
          ) : (
            <>
              <label>
                開始日期
                <input
                  autoFocus
                  type="date"
                  min="0001-01-01"
                  max={draft.due || '9999-12-31'}
                  disabled={mutation.busy}
                  value={draft.start}
                  onChange={(e) =>
                    setDraft({ ...draft, start: e.target.value })
                  }
                />
              </label>
              <label>
                截止日期
                <input
                  type="date"
                  min={draft.start || '0001-01-01'}
                  max="9999-12-31"
                  disabled={mutation.busy}
                  value={draft.due}
                  onChange={(e) => setDraft({ ...draft, due: e.target.value })}
                />
              </label>
              <div className="record-actions">
                <button
                  disabled={
                    mutation.busy ||
                    !!(draft.start && draft.due && draft.start > draft.due)
                  }
                >
                  儲存日期
                </button>
                <button
                  type="button"
                  disabled={mutation.busy}
                  onClick={() => setDraft(null)}
                >
                  取消改期
                </button>
              </div>
            </>
          )}
        </form>
      )}
      <div className="timeline-scroll">
        <div className="timeline-grid" style={{ width: `calc(${width}px + var(--tl-label))`, ['--c' as string]: color }}>
          <div className="timeline-axis">
            <span>{root ? `展開圖・子任務（${nodes.length - 1}）` : `總覽圖・任務（${nodes.filter((n) => n.kind === 'task').length}）`}</span>
            <div style={{ width }}>
              {months.map((t) => (
                <span key={`m${t}`} className="tick-month" style={{ left: (t - left) * actualScale }}>
                  {`${new Date(t * dayMs).getUTCFullYear() % 100}/${new Date(t * dayMs).getUTCMonth() + 1}`}
                </span>
              ))}
              {subs.map((t) => (
                <span key={`s${t}`} className="tick-sub" style={{ left: (t - left) * actualScale }}>
                  {zoom === 'day' ? new Date(t * dayMs).getUTCDate() : short(t)}
                </span>
              ))}
              <b className="today-label" style={{ left: (today - left) * actualScale + 4 }}>今天 {short(today)}</b>
            </div>
          </div>
          {rows.map(({ node: n, depth, children }) => (
            <div className={`timeline-row ${children ? 'parent' : ''}`} key={n.id}>
              <div
                className="timeline-label"
                style={{ paddingLeft: 8 + Math.min(depth, 8) * 14 }}
              >
                {children ? (
                  <button
                    className="tw"
                    aria-label={`${collapsed.has(n.id) ? '展開' : '收合'} ${n.title}`}
                    onClick={() =>
                      setCollapsed((old) => {
                        const next = new Set(old);
                        if (next.has(n.id)) next.delete(n.id);
                        else next.add(n.id);
                        return next;
                      })
                    }
                  >
                    {collapsed.has(n.id) ? '▸' : '▾'}
                  </button>
                ) : (
                  <span className="tw-space" aria-hidden="true" />
                )}
                <span className={`dot ${n.status}`} aria-hidden="true" />
                <button
                  className="nm"
                  title={`進入「${n.title}」・${statusText[n.status]}`}
                  onClick={() => select(n.id)}
                >
                  {n.title}
                </button>
                {n.kind === 'phase' && (
                  <span className="cnt">{taskCount(n.id)} 件</span>
                )}
                {n.capabilities.edit_metadata && n.kind !== 'project' && (
                  <button
                    className="ed"
                    aria-label={`調整日期：${n.title}`}
                    title="調整日期"
                    disabled={mutation.busy || mutation.saved}
                    onClick={() => edit(n)}
                  >
                    ✎
                  </button>
                )}
              </div>
              <div className="timeline-track" style={{ width, ...grid }}>
                <span
                  className="today-line"
                  aria-label="今天標線"
                  style={{ left: (today - left) * actualScale }}
                />
                {full(n) ? (
                  (() => {
                    const d =
                      preview?.id === n.id
                        ? preview
                        : { start_date: n.start_date!, due_date: n.due_date! };
                    const position =
                      (calendarDay(d.start_date) - left) * actualScale;
                    const length =
                      (calendarDay(d.due_date) -
                        calendarDay(d.start_date) +
                        1) *
                      actualScale;
                    const progress = percent(values.get(n.id) ?? 0);
                    return (
                      <div
                        className={`timeline-bar status-${n.status} ${children ? 'parent' : ''}`}
                        style={{ left: position, width: Math.max(length, 8) }}
                        title={`${n.title} ${d.start_date} – ${d.due_date}・${statusText[n.status]}・負責人 ${n.owner_display_name ?? '未指派'}${children ? `・進度 ${progress}%（涵蓋所有子任務）` : ''}`}
                      >
                        {children && <span className="pf" aria-hidden="true" style={{ width: `${progress}%` }} />}
                        <button
                          aria-label={`時程任務：${n.title}`}
                          onPointerDown={(e) => begin(e, n)}
                          onPointerMove={move}
                          onPointerUp={end}
                          onPointerCancel={() => {
                            gesture.current = null;
                            setPreview(null);
                          }}
                          onClick={(e) => {
                            if (
                              e.detail === 0 ||
                              n.kind !== 'task' ||
                              !n.capabilities.edit_metadata
                            )
                              select(n.id);
                          }}
                        >
                          {length > 50 ? (children ? `${n.owner_display_name ?? '未指派'}・${progress}%` : (n.owner_display_name ?? '')) : ''}
                        </button>
                        {n.kind === 'task' && n.capabilities.edit_metadata && (
                          <button
                            className="timeline-resize"
                            aria-label={`調整截止日：${n.title}`}
                            onPointerDown={(e) => begin(e, n, true)}
                            onPointerMove={move}
                            onPointerUp={end}
                            onPointerCancel={() => {
                              gesture.current = null;
                              setPreview(null);
                            }}
                          />
                        )}
                      </div>
                    );
                  })()
                ) : (
                  <span className="timeline-unscheduled">
                    未排程 · {n.start_date ?? '未設定'} ～{' '}
                    {n.due_date ?? '未設定'}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
      {nodes.length === 0 && <p>目前沒有可見節點</p>}
      <section className="unscheduled-list">
        <h3>未排程</h3>
        {nodes
          .filter((n) => !full(n))
          .map((n) => (
            <p key={n.id}>
              {n.title}：{n.start_date ?? '未設定'} ～ {n.due_date ?? '未設定'}
            </p>
          ))}
        {nodes.every(full) && <p>所有可見節點已有完整日期</p>}
      </section>
    </section>
  );
}
