import { useRef, useState } from 'react';
import type { ReactNode } from 'react';
import type { ProjectSummary, WorkspaceRoute } from '../types';

export default function WorkspaceShell({ route, projects, busy, navigate, children, session }: {
  route: WorkspaceRoute; projects: ProjectSummary[]; busy: boolean;
  navigate: (route: WorkspaceRoute) => void; children: ReactNode; session?: ReactNode;
}) {
  const [expanded, setExpanded] = useState(false);
  const toggle = useRef<HTMLButtonElement>(null);
  function go(next: WorkspaceRoute) { if (expanded) toggle.current?.focus(); setExpanded(false); navigate(next); }
  const links = [
    ['overview', '總覽', '▦'], ['my-tasks', '我的任務', '✓'],
    ['project', '專案工作區', '▤'], ['reviews', '審核中心', '◇'],
    ['workflows', '模板庫', '▣'], ['audit', '稽核紀錄', '≡'],
  ] as const;
  return <>
    <div className="mobile-navigation"><span className="brand-name">專流 ProjectFlow</span><button ref={toggle} className="navigation-toggle" aria-label="切換導覽" aria-expanded={expanded} aria-controls="workspace-nav" onClick={() => setExpanded(value => !value)}>☰ 導覽</button></div>
    <div className={`workspace-navigation ${expanded ? 'expanded' : ''}`} onKeyDown={event => { if (event.key === 'Escape') { setExpanded(false); toggle.current?.focus(); } }}>
      <div className="brand"><img src="/mark.svg" width="32" height="32" alt=""/><strong className="brand-name">專流 ProjectFlow</strong></div>
      <nav id="workspace-nav" aria-label="工作區導覽">
        <p className="group-title">工作空間</p>
        {links.map(([page, label, icon]) => <button key={page} disabled={busy} aria-current={route.page === page ? 'page' : undefined} onClick={() => go(page === 'project' ? { page, projectId: route.page === 'project' ? route.projectId : projects[0]?.id ?? null, nodeId: null } : { page })}><span aria-hidden="true" className="nav-icon">{icon}</span>{label}</button>)}
      </nav>
      <aside aria-label="專案清單"><h2 className="group-title">專案 <span>{projects.length}</span></h2><div className="sidebar-projects">{projects.length === 0 && <p className="sidebar-empty">目前沒有專案</p>}{projects.map(item => <button key={item.id} disabled={busy} aria-pressed={route.page === 'project' && item.id === route.projectId} onClick={() => go({ page: 'project', projectId: item.id, nodeId: null })}><span className="project-dot" aria-hidden="true"/><span>{item.title}</span></button>)}</div></aside>
      <div className="sidebar-session">{session}</div>
    </div>
    <div className="workspace-content">{children}</div>
  </>;
}
