import { useRef, useState } from 'react';
import type { PointerEvent as ReactPointerEvent } from 'react';
import { api, useRecordMutation } from '../api';
import type { RecordReload } from '../api';
import type { NodeItem, ProjectDetail } from '../types';
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
  select,
  reload,
  expired,
}: {
  project: ProjectDetail;
  select: (id: string) => void;
  reload: RecordReload;
  expired: () => void;
}) {
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
  const dates = project.nodes.flatMap((n) =>
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
  const step = Math.max(
    zoom === 'day' ? 1 : zoom === 'week' ? 7 : 30,
    Math.ceil(count / 80),
  );
  const ticks = Array.from(
    { length: Math.ceil(count / step) },
    (_, i) => left + i * step,
  );
  const rows = timelineRows(project.nodes, collapsed);
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
      <h2>{project.title} · 時程</h2>
      <p>
        只變更選定節點的日期，不自動順延其他任務。階段日期與子任務分開設定。
      </p>
      <div className="record-actions">
        <label>
          時程刻度
          <select value={zoom} onChange={(e) => setZoom(e.target.value)}>
            <option value="day">日</option>
            <option value="week">週</option>
            <option value="month">月</option>
          </select>
        </label>
        <span>今天：{calendarDate(today)}</span>
      </div>
      <p className="timeline-desktop-hint">
        拖移任務條可改期，拖曳右端可調整截止日；確認日期後才儲存。
      </p>
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
        <div className="timeline-grid" style={{ width: width + 220 }}>
          <div className="timeline-axis">
            <span>節點</span>
            <div style={{ width }}>
              {ticks.map((t) => (
                <span key={t} style={{ left: (t - left) * actualScale }}>
                  {calendarDate(t)}
                </span>
              ))}
            </div>
          </div>
          {rows.map(({ node: n, depth, children }) => (
            <div className="timeline-row" key={n.id}>
              <div
                className="timeline-label"
                style={{ paddingLeft: 8 + Math.min(depth, 8) * 10 }}
              >
                {children && (
                  <button
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
                    {collapsed.has(n.id) ? '＋' : '−'}
                  </button>
                )}
                <button onClick={() => select(n.id)}>{n.title}</button>
                {n.capabilities.edit_metadata && n.kind !== 'project' && (
                  <button
                    aria-label={`調整日期：${n.title}`}
                    disabled={mutation.busy || mutation.saved}
                    onClick={() => edit(n)}
                  >
                    改期
                  </button>
                )}
              </div>
              <div className="timeline-track" style={{ width }}>
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
                    return (
                      <div
                        className={`timeline-bar status-${n.status}`}
                        style={{ left: position, width: Math.max(length, 8) }}
                      >
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
                          {n.title} · {statusText[n.status]}
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
                          >
                            ↔
                          </button>
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
      <div className="timeline-mobile">
        {rows.map(({ node: n, depth, children }) => (
          <article className="record-panel" key={n.id}>
            <div className="record-actions">
              {children && (
                <button
                  aria-label={`手機${collapsed.has(n.id) ? '展開' : '收合'} ${n.title}`}
                  onClick={() =>
                    setCollapsed((old) => {
                      const next = new Set(old);
                      if (next.has(n.id)) next.delete(n.id);
                      else next.add(n.id);
                      return next;
                    })
                  }
                >
                  {collapsed.has(n.id) ? '展開' : '收合'}
                </button>
              )}
              <button onClick={() => select(n.id)}>
                {'› '.repeat(Math.min(depth, 5))}
                {n.title}
              </button>
            </div>
            <p>狀態：{statusText[n.status]}</p>
            <p>
              {full(n) ? '已排程' : '未排程'}：{n.start_date ?? '未設定'} ～{' '}
              {n.due_date ?? '未設定'}
            </p>
            {n.capabilities.edit_metadata && n.kind !== 'project' && (
              <button
                aria-label={`手機調整日期：${n.title}`}
                disabled={mutation.busy || mutation.saved}
                onClick={() => edit(n)}
              >
                調整日期
              </button>
            )}
          </article>
        ))}
      </div>
      {project.nodes.length === 0 && <p>目前沒有可見節點</p>}
      <section className="unscheduled-list">
        <h3>未排程</h3>
        {project.nodes
          .filter((n) => !full(n))
          .map((n) => (
            <p key={n.id}>
              {n.title}：{n.start_date ?? '未設定'} ～ {n.due_date ?? '未設定'}
            </p>
          ))}
        {project.nodes.every(full) && <p>所有可見節點已有完整日期</p>}
      </section>
    </section>
  );
}
