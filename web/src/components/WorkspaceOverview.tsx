import { useEffect, useRef, useState } from 'react';
import { api, ApiError } from '../api';
import type { WorkspaceOverviewData } from '../types';
import { projectColor } from './WorkspaceShell';

const OPEN = ['todo', 'doing', 'review'] as const;
export const slashDate = (value: string | null | undefined) => value ? value.split('-').join('/') : '—';

export default function WorkspaceOverview({ openProject, expired, showAssignHint = false }: { openProject: (id: string) => void; expired: () => void; showAssignHint?: boolean }) {
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
  const open = data ? OPEN.reduce((sum, status) => sum + data.task_counts[status], 0) : 0;
  const active = data ? data.projects.filter(project => OPEN.some(status => project.task_counts[status] > 0)).length : 0;
  const people = data?.people ?? [];
  const heaviest = Math.max(1, ...people.map(person => person.open_count));
  return <section aria-label="總覽內容"><div className="page-heading"><h1>所有專案總覽</h1><p className="page-description">跨專案進度、預估完成與人員負載（今天 {slashDate(data?.today)}）</p></div>
    {loading ? <p role="status">載入總覽中</p> : error ? <><p role="alert">{error}</p><button onClick={() => void load()}>重試總覽</button></> : data && <>
      <div className="overview-statistics">
        <div aria-label="進行中專案"><strong>{active}</strong><span>進行中專案</span></div>
        <div aria-label="未完成任務"><strong>{open}</strong><span>未完成任務（含子任務）</span></div>
        <div aria-label="已延遲任務" className="stat-late"><strong>{data.overdue_count ?? 0}</strong><span>已延遲任務</span></div>
        <div aria-label="可見任務完成率"><strong>{data.completion_percent === null ? '—' : `${data.completion_percent}%`}</strong><span>可見任務完成率</span></div>
      </div>
      {data.projects.length === 0 ? <p>目前沒有可見專案</p> : <div className="table-wrap"><table className="data-table overview-table" aria-label="專案進度">
        <thead><tr><th>專案</th><th>目前階段</th><th>完成度</th><th>預計完成</th><th>時程</th><th>待確認</th></tr></thead>
        <tbody>{data.projects.map((project, index) => <tr key={project.id}>
          <td><span className="cell-title"><span className="project-dot" aria-hidden="true" style={{ background: projectColor(index) }}/><button className="row-link" onClick={() => openProject(project.id)}>{project.title}</button></span></td>
          <td>{project.current_phase_title ?? '—'}</td>
          <td className="progress-cell">{project.completion_percent === null ? <span className="muted">—</span> : <>
            <span className="bar-track" role="progressbar" aria-label={`${project.title}完成率`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={project.completion_percent}><span style={{ width: `${project.completion_percent}%`, background: projectColor(index) }}/></span>
            <span className="muted">{project.completion_percent}%</span></>}</td>
          <td>{slashDate(project.due_date)}</td>
          <td>{project.overdue_count ? <span className="tag warn">延遲 {project.overdue_count} 項</span> : project.due_date ? <span className="tag">如期</span> : <span className="muted">—</span>}</td>
          <td>{project.task_counts.review || ''}</td>
        </tr>)}</tbody>
      </table></div>}
      <div className="overview-panels">
        <div className="panel"><h3>人員負載（未完成任務數）</h3>
          {people.length === 0 ? <p className="muted">目前沒有指派給人員的未完成任務。</p> : people.map(person => <div className="load-row" key={person.user_id}>
            <div className="load-head"><span className="load-name"><span className="avatar small" aria-hidden="true">{person.display_name.slice(0, 1)}</span>{person.display_name}{person.department_name && <span className="muted">{person.department_name}</span>}</span>
              <span>{person.open_count} 項{person.overdue_count > 0 && <span className="late">，{person.overdue_count} 項延遲</span>}</span></div>
            <span className="bar-track" aria-hidden="true"><span className={person.open_count === heaviest ? 'hot' : ''} style={{ width: `${person.open_count / heaviest * 100}%` }}/></span>
          </div>)}
          <p className="muted small">工作量最重的人以橘色標示{showAssignHint ? '，可在任務編輯中改派負責人' : ''}。</p></div>
        <div className="panel"><h3>部門負載</h3>
          {(data.departments ?? []).length === 0 ? <p className="muted">尚未設定部門。</p> : data.departments!.map(department => <div className="dept-row" key={department.id}><span>{department.name}</span><span>{department.open_count} 項</span></div>)}
        </div>
      </div>
    </>}
  </section>;
}
