import { useEffect, useRef, useState } from 'react';
import { api, ApiError } from '../api';
import type { WorkspaceOverviewData } from '../types';
import { statuses } from './NodeWorkspace';

export default function WorkspaceOverview({ openProject, expired }: { openProject: (id: string) => void; expired: () => void }) {
  const [data, setData] = useState<WorkspaceOverviewData | null>(null);
  const [error, setError] = useState(''); const [loading, setLoading] = useState(true);
  const sequence = useRef(0); const controller = useRef<AbortController | null>(null);
  async function load() {
    controller.current?.abort(); const request = new AbortController(); controller.current = request;
    const id = ++sequence.current; setLoading(true); setError('');
    try { const result = await api.overview(request.signal); if (id === sequence.current) setData(result); }
    catch (value) { if (id !== sequence.current) return; if (value instanceof ApiError && value.status === 401) expired(); else setError(value instanceof ApiError ? value.message : '無法載入總覽'); }
    finally { if (id === sequence.current) setLoading(false); }
  }
  useEffect(() => { void load(); return () => { ++sequence.current; controller.current?.abort(); }; }, []);
  return <section aria-label="總覽內容"><div className="page-heading"><p className="eyebrow">工作空間</p><h1>總覽</h1><p className="page-description">掌握可見專案進度與任務狀態</p></div>
    {loading ? <p role="status">載入總覽中</p> : error ? <><p role="alert">{error}</p><button onClick={() => void load()}>重試總覽</button></> : data && <>
      <div className="overview-statistics"><div aria-label="可見專案數"><span>可見專案數：</span><strong>{data.project_count}</strong></div><div aria-label="可見任務完成率"><span>可見任務完成率：</span><strong>{data.completion_percent === null ? '—' : `${data.completion_percent}%`}</strong></div>
        {statuses.map(item => <div key={item.status} className={`stat-${item.status}`}><span>{item.label}：</span><strong>{data.task_counts[item.status]}</strong></div>)}
      </div>
      <h2>所有專案</h2>{data.projects.length === 0 ? <p>目前沒有可見專案</p> : <ul className="overview-projects">{data.projects.map(project => <li key={project.id}>
        <span className="eyebrow">專案</span><button onClick={() => openProject(project.id)}>{project.title}</button><span>可見任務完成率：{project.completion_percent === null ? '—' : `${project.completion_percent}%`}</span>{project.completion_percent !== null && <progress aria-label={`${project.title}完成率`} max={100} value={project.completion_percent} />}
      </li>)}</ul>}
    </>}
  </section>;
}
