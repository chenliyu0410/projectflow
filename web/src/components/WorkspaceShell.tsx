import { useState } from 'react';
import type { ReactNode } from 'react';
import type { ProjectSummary, WorkspaceRoute } from '../types';

export default function WorkspaceShell({ route, projects, busy, navigate, children }: {
  route: WorkspaceRoute; projects: ProjectSummary[]; busy: boolean;
  navigate: (route: WorkspaceRoute) => void; children: ReactNode;
}) {
  const [expanded, setExpanded] = useState(false);
  function go(next: WorkspaceRoute) { setExpanded(false); navigate(next); }
  return <>
    <div className="workspace-navigation">
      <button className="navigation-toggle" aria-label="切換導覽" aria-expanded={expanded} aria-controls="workspace-nav" onClick={() => setExpanded(value => !value)}>導覽</button>
      <nav id="workspace-nav" aria-label="工作區導覽" className={expanded ? 'expanded' : ''}>
        <button disabled={busy} aria-current={route.page === 'overview' ? 'page' : undefined} onClick={() => go({ page: 'overview' })}>總覽</button>
        <button disabled={busy} aria-current={route.page === 'my-tasks' ? 'page' : undefined} onClick={() => go({ page: 'my-tasks' })}>我的任務</button>
        <button disabled={busy} aria-current={route.page === 'project' ? 'page' : undefined} onClick={() => go({ page: 'project', projectId: route.page === 'project' ? route.projectId : projects[0]?.id ?? null, nodeId: null })}>專案工作區</button>
      </nav>
      {route.page === 'project' && <aside aria-label="專案清單"><h2>專案</h2>{projects.map(item => <button key={item.id} disabled={busy} aria-pressed={item.id === route.projectId} onClick={() => go({ page: 'project', projectId: item.id, nodeId: null })}>{item.title}</button>)}</aside>}
    </div>
    <div className="workspace-content">{children}</div>
  </>;
}
