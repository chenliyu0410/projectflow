import { useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { api } from '../api';
import type { ProjectSummary, WorkspaceRoute } from '../types';
import CopilotPanel from './CopilotPanel';
import NavIcon from './NavIcons';
import type { IconName } from './NavIcons';

// Fixed palette in list order, matching the Demo's per-project colour dots and progress tracks.
export const PROJECT_COLORS = ['#1F5F5B', '#B4541F', '#4A5A8C', '#6B7A3A', '#914667', '#216677', '#A9692E', '#3D6F4E'];
export const projectColor = (index: number) => PROJECT_COLORS[index % PROJECT_COLORS.length];

type NavItem = { page: 'overview' | 'my-tasks' | 'reviews' | 'workflows' | 'audit' | 'operations' | 'governance' | null; label: string; icon: IconName };
const LINKS: NavItem[] = [
  { page: 'overview', label: '所有專案總覽', icon: 'overview' }, { page: 'my-tasks', label: '我的任務', icon: 'tasks' },
  { page: 'reviews', label: '審核中心', icon: 'review' }, { page: 'operations', label: '營運資料', icon: 'ops' },
  { page: 'workflows', label: '模板庫', icon: 'templates' }, { page: 'governance', label: 'AI 政策與稽核', icon: 'ai' },
  { page: 'audit', label: '活動與稽核紀錄', icon: 'audit' },
];

export default function WorkspaceShell({ route, projects, busy, navigate, children, session, createAction, copilotScope, food = false, companyName = '目前公司', previewKey }: {
  route: WorkspaceRoute; projects: ProjectSummary[]; busy: boolean;
  navigate: (route: WorkspaceRoute) => void; children: ReactNode; session?: ReactNode;
  createAction?: ReactNode; copilotScope: string; food?: boolean; companyName?: string; previewKey?: string;
}) {
  const [expanded, setExpanded] = useState(false);
  const [copilotOpen, setCopilotOpen] = useState(false);
  const [progress, setProgress] = useState<Record<string, number | null>>({});
  const toggle = useRef<HTMLButtonElement>(null);
  const copilotToggle = useRef<HTMLButtonElement>(null);
  const location = route.page === 'project' ? `project:${route.projectId}` : route.page;
  useEffect(() => {
    // Sidebar progress is decoration; pages own error and expiry handling for the same endpoint.
    const request = new AbortController();
    api.overview(request.signal).then(data => setProgress(Object.fromEntries(data.projects.map(item => [item.id, item.progress_percent ?? null]))), () => undefined);
    return () => request.abort();
  }, [projects, location]);
  function go(next: WorkspaceRoute) { if (expanded) toggle.current?.focus(); setExpanded(false); navigate(next); }
  function closeNavigation() { setExpanded(false); toggle.current?.focus(); }
  function closeCopilot() { setCopilotOpen(false); copilotToggle.current?.focus(); }
  useEffect(() => {
    // Focus may stay on the toggle after opening, so Escape is handled page-wide while a drawer is open.
    if (!expanded && !copilotOpen) return;
    function onKey(event: KeyboardEvent) {
      if (event.key !== 'Escape') return;
      if (expanded) closeNavigation();
      if (copilotOpen) closeCopilot();
    }
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [expanded, copilotOpen]);
  return <>
    <div id="workspace-navigation" className={`workspace-navigation ${expanded ? 'expanded' : ''}`}>
      <div className="brand"><img src="/mark.svg" width="32" height="32" alt=""/><strong className="brand-name">專流 ProjectFlow</strong></div>
      <nav id="workspace-nav" aria-label="工作區導覽">
        {LINKS.map(item => item.page === null
          ? <button key={item.label} disabled className="nav-unavailable"><NavIcon name={item.icon}/>{item.label}<span className="nav-badge">尚未提供</span></button>
          : <button key={item.page} disabled={busy} aria-current={route.page === item.page ? 'page' : undefined} onClick={() => go({ page: item.page! })}><NavIcon name={item.icon}/>{item.label}</button>)}
      </nav>
      <aside aria-label="專案清單"><h2 className="group-title">專案 <span>{projects.length}</span></h2><div className="sidebar-projects">{projects.length === 0 && <p className="sidebar-empty">目前沒有專案</p>}{projects.map((item, index) => {
        const percent = progress[item.id];
        return <button key={item.id} disabled={busy} aria-label={item.title} aria-describedby={`project-progress-${item.id}`} aria-pressed={route.page === 'project' && item.id === route.projectId} onClick={() => go({ page: 'project', projectId: item.id, nodeId: null })}>
          <span className="project-dot" aria-hidden="true" style={{ background: projectColor(index) }}/>
          <span className="project-info"><span className="project-name">{item.title}</span><span className="project-track" aria-hidden="true"><span style={{ width: `${percent ?? 0}%`, background: projectColor(index) }}/></span></span>
          <span className="project-percent" id={`project-progress-${item.id}`}>{percent === undefined ? '' : percent === null ? '—' : `${percent}%`}</span>
        </button>;
      })}</div>{createAction && <div className="sidebar-create" onClick={() => setExpanded(false)}>{createAction}</div>}</aside>
      <div className="sidebar-session">{session}</div>
    </div>
    <div className="workspace-main">
      <div className="mobile-navigation">
        <button ref={toggle} className="navigation-toggle" aria-label="切換導覽" aria-expanded={expanded} aria-controls="workspace-navigation" onClick={() => setExpanded(value => !value)}>☰ 選單</button>
        <button ref={copilotToggle} className="copilot-toggle" aria-label="切換 AI 副手" aria-expanded={copilotOpen} aria-controls="copilot-panel" onClick={() => setCopilotOpen(value => !value)}>✦ AI 副手</button>
      </div>
      <div className="workspace-content">{children}</div>
    </div>
    <CopilotPanel key={previewKey ?? location} food={food} companyName={companyName} scope={copilotScope} open={copilotOpen} close={closeCopilot} />
    {(expanded || copilotOpen) && <div className="drawer-backdrop" aria-hidden="true" onClick={() => { if (expanded) closeNavigation(); if (copilotOpen) closeCopilot(); }} />}
  </>;
}
