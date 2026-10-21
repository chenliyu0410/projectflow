import { useEffect, useRef, useState } from 'react';
import { api, ApiError } from '../api';
import type { MyTask } from '../types';
import Notifications from './Notifications';
import { statuses } from './NodeWorkspace';

const monthDay = (value: string | null) => value ? value.slice(5).replace('-', '/') : '';
function period(item: MyTask) {
  if (!item.start_date && !item.due_date) return '未排程';
  return `${monthDay(item.start_date) || '—'}–${monthDay(item.due_date) || '—'}`;
}

export default function MyTasks({ openNode, expired, userName }: { openNode: (projectId: string, nodeId: string) => void; expired: () => void; userName?: string }) {
  // search 是輸入框的即時內容，q 是停手後才送出的查詢，避免每打一個字就打一次 API。
  const [search, setSearch] = useState(''); const [q, setQ] = useState(''); const [status, setStatus] = useState('');
  const [items, setItems] = useState<MyTask[]>([]); const [error, setError] = useState(''); const [loading, setLoading] = useState(true);
  const [loaded, setLoaded] = useState(false);
  useEffect(() => { const timer = setTimeout(() => setQ(search), 300); return () => clearTimeout(timer); }, [search]);
  const sequence = useRef(0); const controller = useRef<AbortController | null>(null);
  async function load() {
    controller.current?.abort(); const request = new AbortController(); controller.current = request;
    const id = ++sequence.current; setLoading(true); setError('');
    try { const result = await api.myTasks(q, status, request.signal); if (id === sequence.current) { setItems(result.items); setLoaded(true); } }
    catch (value) { if (id !== sequence.current) return; if (value instanceof ApiError && value.status === 401) expired(); else setError(value instanceof ApiError ? value.message : '無法載入我的任務'); }
    finally { if (id === sequence.current) setLoading(false); }
  }
  useEffect(() => { void load(); return () => { ++sequence.current; controller.current?.abort(); }; }, [q, status]);
  // Same grouping as the Demo: a task I own is listed once under 我負責的 even if I also collaborate on it.
  const owned = items.filter(item => !item.relations || item.relations.includes('owned'));
  const collaborating = items.filter(item => item.relations && !item.relations.includes('owned') && item.relations.includes('collaborating'));
  const filtered = Boolean(q.trim() || status);
  function group(title: string, list: MyTask[]) {
    return <div className="task-group" key={title}><h2>{title}（{list.length}）</h2>
      {list.length === 0 ? <p className="empty">{filtered ? '沒有符合篩選的任務。' : '沒有項目。'}</p> : <div className="table-wrap"><table className="data-table" aria-label={title}>
        <thead><tr><th>任務</th><th>位置</th><th>狀態</th><th>期間</th></tr></thead>
        <tbody>{list.map(item => <tr key={item.id}>
          <td><span className="cell-title"><span className={`dot ${item.status}`} aria-hidden="true"/><button className="row-link" onClick={() => openNode(item.project_id, item.id)}>{item.title}</button>{item.blocked && <span className="tag warn">🔒 等待前置</span>}</span></td>
          <td className="muted small">{[item.project_title, ...(item.path ?? []).map(entry => entry.title)].join(' / ')}</td>
          <td>{statuses.find(value => value.status === item.status)?.label}</td>
          <td className="nowrap">{period(item)}</td>
        </tr>)}</tbody>
      </table></div>}
    </div>;
  }
  return <section aria-label="我的任務內容"><div className="page-heading"><h1>我的任務</h1><p className="page-description">{userName ? `${userName}・` : ''}跨專案、跨層級（含我負責、我協作）</p></div>
    <div className="task-filters"><label>搜尋任務<input value={search} onChange={event => setSearch(event.target.value)} /></label>
      <label>任務狀態<select aria-label="任務狀態" value={status} onChange={event => setStatus(event.target.value)}><option value="">全部</option>{statuses.map(item => <option key={item.status} value={item.status}>{item.label}</option>)}</select></label>
      <button onClick={() => { setSearch(''); setQ(''); setStatus(''); }}>清除篩選</button>
    </div>
    {loading && loaded && !error && <p role="status" className="small muted">更新我的任務中…</p>}
    {loading && !loaded ? <p role="status">載入我的任務中</p> : error ? <><p role="alert">{error}</p><button onClick={() => void load()}>重試我的任務</button></>
      : items.length === 0 ? <p>{filtered ? '沒有符合篩選的任務' : '目前沒有指派給你的可見任務'}</p>
        : <>{group('待我指派', items.filter(item => item.relations?.includes('awaiting_assignment')))}{group('我負責的', owned)}{group('我協作的', collaborating)}</>}
    <Notifications openNode={openNode} expired={expired}/>
  </section>;
}
