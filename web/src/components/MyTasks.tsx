import { useEffect, useRef, useState } from 'react';
import { api, ApiError } from '../api';
import type { MyTask } from '../types';
import { statuses } from './NodeWorkspace';

export default function MyTasks({ openNode, expired }: { openNode: (projectId: string, nodeId: string) => void; expired: () => void }) {
  const [q, setQ] = useState(''); const [status, setStatus] = useState('');
  const [items, setItems] = useState<MyTask[]>([]); const [error, setError] = useState(''); const [loading, setLoading] = useState(true);
  const sequence = useRef(0); const controller = useRef<AbortController | null>(null);
  async function load() {
    controller.current?.abort(); const request = new AbortController(); controller.current = request;
    const id = ++sequence.current; setLoading(true); setError('');
    try { const result = await api.myTasks(q, status, request.signal); if (id === sequence.current) setItems(result.items); }
    catch (value) { if (id !== sequence.current) return; if (value instanceof ApiError && value.status === 401) expired(); else setError(value instanceof ApiError ? value.message : '無法載入我的任務'); }
    finally { if (id === sequence.current) setLoading(false); }
  }
  useEffect(() => { void load(); return () => { ++sequence.current; controller.current?.abort(); }; }, [q, status]);
  return <section aria-label="我的任務內容"><div className="page-heading"><p className="eyebrow">工作空間</p><h1>我的任務</h1><p className="page-description">追蹤你負責與協作的任務</p></div>
    <div className="task-filters"><label>搜尋任務<input value={q} onChange={event => setQ(event.target.value)} /></label>
      <label>任務狀態<select aria-label="任務狀態" value={status} onChange={event => setStatus(event.target.value)}><option value="">全部</option>{statuses.map(item => <option key={item.status} value={item.status}>{item.label}</option>)}</select></label>
      <button onClick={() => { setQ(''); setStatus(''); }}>清除篩選</button>
    </div>
    {loading ? <p role="status">載入我的任務中</p> : error ? <><p role="alert">{error}</p><button onClick={() => void load()}>重試我的任務</button></>
      : items.length === 0 ? <p>{q.trim() || status ? '沒有符合篩選的任務' : '目前沒有指派給你的可見任務'}</p>
        : <ul className="my-task-list">{items.map(item => <li key={item.id} className={`status-${item.status}`}>
          <button onClick={() => openNode(item.project_id, item.id)}>{item.title}</button><p>{item.relations?.map(value => value === 'owned' ? '負責' : '協作').join(' · ')}</p><dl>
            <div><dt>專案</dt><dd>{item.project_title}</dd></div><div><dt>部門</dt><dd>{item.department_name ?? '未指派'}</dd></div>
            <div><dt>狀態</dt><dd>{statuses.find(value => value.status === item.status)?.label}</dd></div>
            <div><dt>開始日期</dt><dd>{item.start_date ?? '未設定'}</dd></div><div><dt>截止日期</dt><dd>{item.due_date ?? '未設定'}</dd></div>
          </dl></li>)}</ul>}
  </section>;
}
