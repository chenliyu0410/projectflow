import { useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { api } from '../api';
import type { ProjectSummary, WorkspaceRoute } from '../types';
import CopilotPanel from './CopilotPanel';
import Dropdown from './Dropdown';
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

export default function WorkspaceShell({ route, projects, busy, navigate, children, session, createAction, copilotScope, food = false, companyName = '目前公司', accountName = '使用者', previewKey }: {
  route: WorkspaceRoute; projects: ProjectSummary[]; busy: boolean;
  navigate: (route: WorkspaceRoute) => void; children: ReactNode; session?: ReactNode;
  createAction?: ReactNode; copilotScope: string; food?: boolean; companyName?: string; accountName?: string; previewKey?: string;
}) {
  const [expanded, setExpanded] = useState(false);
  const [projectsOpen, setProjectsOpen] = useState(false);
  const [copilotOpen, setCopilotOpen] = useState(false);
  const [progress, setProgress] = useState<Record<string, number | null>>({});
  const toggle = useRef<HTMLButtonElement>(null);
  const copilotToggle = useRef<HTMLButtonElement>(null);
  const restoreCopilotFocus = useRef(false);
  const projectToggle = useRef<HTMLButtonElement>(null);
  const projectPanel = useRef<HTMLElement>(null);
  const location = route.page === 'project' ? `project:${route.projectId}` : route.page;
  useEffect(() => {
    // Sidebar progress is decoration; pages own error and expiry handling for the same endpoint.
    const request = new AbortController();
    api.overview(request.signal).then(data => setProgress(Object.fromEntries(data.projects.map(item => [item.id, item.progress_percent ?? null]))), () => undefined);
    return () => request.abort();
  }, [projects, location]);
  function go(next: WorkspaceRoute) { if (expanded) toggle.current?.focus(); else if (projectsOpen) projectToggle.current?.focus(); setProjectsOpen(false); setExpanded(false); navigate(next); }
  function closeProjects() { setProjectsOpen(false); projectToggle.current?.focus(); }
  function closeNavigation() { setExpanded(false); toggle.current?.focus(); }
  function closeCopilot() { restoreCopilotFocus.current = true; setCopilotOpen(false); }
  useEffect(() => {
    // The launcher is hidden while open; focus it only after its visible state is committed.
    if (!copilotOpen && restoreCopilotFocus.current) {
      restoreCopilotFocus.current = false;
      copilotToggle.current?.focus();
    }
  }, [copilotOpen]);
  useEffect(() => {
    // Focus may stay on the toggle after opening, so Escape is handled page-wide while a drawer is open.
    if (!expanded && !copilotOpen && !projectsOpen) return;
    function onKey(event: KeyboardEvent) {
      if (event.key !== 'Escape') return;
      if (projectsOpen) { closeProjects(); return; }
      if (expanded) closeNavigation();
      if (copilotOpen) closeCopilot();
    }
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [expanded, copilotOpen, projectsOpen]);
  useEffect(() => {
    if (!projectsOpen) return;
    const panel = projectPanel.current;
    const first = panel?.querySelector<HTMLButtonElement>('.sidebar-projects button[aria-pressed=true]')
      ?? panel?.querySelector<HTMLButtonElement>('.sidebar-projects button:not(:disabled)')
      ?? panel?.querySelector<HTMLButtonElement>('.project-menu-close');
    first?.focus();
    function outside(event: Event) {
      if (!(event.target instanceof Node) || projectPanel.current?.contains(event.target) || projectToggle.current?.contains(event.target)) return;
      if (event.type === 'pointerdown' && projectPanel.current?.contains(document.activeElement)
        && event.target instanceof Element && !event.target.closest('button, a[href], input, select, textarea, [tabindex], [contenteditable=true]')) {
        // Let the browser finish its pointer focus change before restoring blank-space clicks.
        setTimeout(() => {
          if (document.activeElement === document.body || projectPanel.current?.contains(document.activeElement)) projectToggle.current?.focus();
        }, 0);
      }
      setProjectsOpen(false);
    }
    document.addEventListener('pointerdown', outside);
    document.addEventListener('focusin', outside);
    return () => { document.removeEventListener('pointerdown', outside); document.removeEventListener('focusin', outside); };
  }, [projectsOpen]);
  return <>
    <div id="workspace-navigation" className={`workspace-navigation ${expanded ? 'expanded' : ''}`}>
      <div className="brand"><img src="/mark.svg" width="32" height="32" alt=""/><strong className="brand-name">專流 ProjectFlow</strong></div>
      <nav id="workspace-nav" aria-label="工作區導覽">
        {LINKS.map(item => item.page === null
          ? <button key={item.label} disabled className="nav-unavailable"><NavIcon name={item.icon}/>{item.label}<span className="nav-badge">尚未提供</span></button>
          : <button key={item.page} disabled={busy} aria-current={route.page === item.page ? 'page' : undefined} onClick={() => go({ page: item.page! })}><NavIcon name={item.icon}/>{item.label}</button>)}
      </nav>
      <button ref={projectToggle} className="project-menu-toggle" disabled={busy} aria-label="專案" aria-expanded={projectsOpen} aria-controls="project-menu" onClick={() => setProjectsOpen(value => !value)}><NavIcon name="projects"/><span>專案</span><span className="project-menu-count">{projects.length}</span><span aria-hidden="true">›</span></button>


    </div>
      <aside ref={projectPanel} id="project-menu" className="project-menu" aria-label="專案清單" hidden={!projectsOpen}>
        <div className="project-menu-heading"><h2>專案 <span>{projects.length}</span></h2><button className="project-menu-close" aria-label="關閉專案選單" onClick={closeProjects}>×</button></div>
        <div className="sidebar-projects">{projects.length === 0 && <p className="sidebar-empty">目前沒有專案</p>}{projects.map((item, index) => {
        const percent = progress[item.id];
        return <button key={item.id} disabled={busy} aria-label={item.title} aria-describedby={`project-progress-${item.id}`} aria-pressed={route.page === 'project' && item.id === route.projectId} onClick={() => go({ page: 'project', projectId: item.id, nodeId: null })}>
          <span className="project-dot" aria-hidden="true" style={{ background: projectColor(index) }}/>
          <span className="project-info"><span className="project-name">{item.title}</span><span className="project-track" aria-hidden="true"><span style={{ width: `${percent ?? 0}%`, background: projectColor(index) }}/></span></span>
          <span className="project-percent" id={`project-progress-${item.id}`}>{percent === undefined ? '' : percent === null ? '—' : `${percent}%`}</span>
        </button>;
      })}</div>{createAction && <div className="sidebar-create" onClick={() => { setProjectsOpen(false); setExpanded(false); }}>{createAction}</div>}</aside>
    <div className="workspace-main">
      <div className="workspace-topbar">
        <button ref={toggle} className="navigation-toggle" aria-label="切換導覽" aria-expanded={expanded} aria-controls="workspace-navigation" onClick={() => setExpanded(value => !value)}>☰ 選單</button>
        <Dropdown className="account-menu" name="使用者選單" label={<><span className="avatar" aria-hidden="true">{accountName.slice(0, 1)}</span><span className="account-name">{accountName}</span></>}><div className="sidebar-session">{session}</div></Dropdown>
      </div>
      <div className="workspace-content">{children}</div>
    </div>
    <button ref={copilotToggle} className="copilot-launcher" aria-label="切換 AI 副手" title="AI 專案副手" aria-expanded={copilotOpen} aria-controls="copilot-panel" onClick={() => setCopilotOpen(value => !value)}><NavIcon name="ai" size={26}/><span className="sr-only">AI 專案副手</span></button>
    <CopilotPanel key={previewKey ?? location} food={food} companyName={companyName} scope={copilotScope} open={copilotOpen} close={closeCopilot} />
    {(expanded || copilotOpen) && <div className="drawer-backdrop" aria-hidden="true" onClick={() => { if (expanded) closeNavigation(); if (copilotOpen) closeCopilot(); }} />}
  </>;
}
