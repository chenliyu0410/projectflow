import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { api, ApiError } from './api';
import type { NodeItem, ProjectDetail, ProjectSummary, SessionInfo } from './types';

type State = 'checking-session' | 'login' | 'loading' | 'ready' | 'error';
function childrenOf(nodes: NodeItem[], parentId: string | null) {
  return nodes.filter(node => node.parent_id === parentId).sort((a, b) => a.sort_order - b.sort_order);
}
function pathFor(nodes: NodeItem[], selectedId: string | null) {
  const byId = new Map(nodes.map(node => [node.id, node]));
  const path: NodeItem[] = [];
  const seen = new Set<string>();
  let node = selectedId ? byId.get(selectedId) : undefined;
  while (node && !seen.has(node.id)) {
    seen.add(node.id); path.unshift(node);
    node = node.parent_id ? byId.get(node.parent_id) : undefined;
  }
  return path;
}
function NodeTree({ nodes, parentId, selectedId, select }: {
  nodes: NodeItem[]; parentId: string | null; selectedId: string | null; select: (id: string) => void;
}) {
  const children = childrenOf(nodes, parentId);
  if (children.length === 0) return null;
  return <ul>{children.map(node => <li key={node.id}>
    <button aria-pressed={selectedId === node.id} onClick={() => select(node.id)}>{node.title}</button>
    <NodeTree nodes={nodes} parentId={node.id} selectedId={selectedId} select={select} />
  </li>)}</ul>;
}
export default function App() {
  const [state, setState] = useState<State>('checking-session');
  const [session, setSession] = useState<SessionInfo | null>(null);
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [organization, setOrganization] = useState('food');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const sequence = useRef(0);
  const controller = useRef<AbortController | null>(null);

  function begin() {
    controller.current?.abort();
    const request = { id: ++sequence.current, controller: new AbortController() };
    controller.current = request.controller;
    return request;
  }
  function current(request: ReturnType<typeof begin>) {
    return request.id === sequence.current && !request.controller.signal.aborted;
  }
  function clearSession() {
    setSession(null); setProjects([]); setSelectedId(null); setProject(null); setSelectedNodeId(null); setPassword(''); setState('login');
  }
  function failed(error: unknown, request: ReturnType<typeof begin>, loginFailure = false) {
    if (!current(request)) return;
    if (error instanceof ApiError && error.status === 401) clearSession();
    else setState(loginFailure ? 'login' : 'error');
    setMessage(error instanceof ApiError ? error.message : '操作失敗，請稍後再試');
  }
  async function loadProjects(request: ReturnType<typeof begin>, value: SessionInfo) {
    if (!current(request)) return;
    setSession(value); setState('loading');
    setProject(null); setSelectedNodeId(null); setSelectedId(null);
    try {
      const result = await api.projects(request.controller.signal);
      if (!current(request)) return;
      setProjects(result.items);
      const first = result.items[0]?.id ?? null;
      setSelectedId(first);
      if (first) await loadDetail(first, request);
      else setState('ready');
    } catch (error) { projectFailed(error, request); }
  }
  function projectFailed(error: unknown, request: ReturnType<typeof begin>) {
    if (!current(request)) return;
    failed(error, request);
    if (!(error instanceof ApiError && error.status === 401)) setMessage('無法載入專案資料');
  }
  async function loadDetail(id: string, request: ReturnType<typeof begin>) {
    try {
      const detail = await api.project(id, request.controller.signal);
      if (!current(request)) return;
      setProject(detail);
      setSelectedNodeId(childrenOf(detail.nodes, null)[0]?.id ?? null);
      setState('ready');
    } catch (error) { projectFailed(error, request); }
  }
  async function selectProject(id: string) {
    if (busy) return;
    const request = begin();
    setSelectedId(id); setProject(null); setSelectedNodeId(null); setMessage(''); setState('loading');
    await loadDetail(id, request);
  }
  function retry() {
    if (session && selectedId) void selectProject(selectedId);
    else void restore();
  }
  async function restore() {
    const request = begin();
    setMessage(''); setState('checking-session');
    try { await loadProjects(request, await api.me(request.controller.signal)); }
    catch (error) { failed(error, request); }
  }
  useEffect(() => {
    void restore();
    return () => { ++sequence.current; controller.current?.abort(); };
    // Session checking runs once per mount; cleanup invalidates even non-abortable responses.
  }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    const request = begin();
    setBusy(true); setMessage('');
    const payload = { organization_key: organization, username, password };
    setPassword('');
    let authenticated = false;
    try {
      const value = await api.login(payload, request.controller.signal);
      authenticated = true;
      await loadProjects(request, value);
    }
    catch (error) { failed(error, request, !authenticated); }
    finally { if (current(request)) setBusy(false); }
  }
  async function logout() {
    if (busy) return;
    const request = begin();
    setBusy(true); setMessage('');
    try {
      await api.logout(request.controller.signal);
      if (current(request)) clearSession();
    } catch (error) { failed(error, request); }
    finally { if (current(request)) setBusy(false); }
  }

  return <>
    <header>
      <img src="/mark.svg" width="32" height="32" alt="" />
      <strong>專流 ProjectFlow</strong>
      {session && <div className="session"><span aria-label="目前公司">{session.organization.name}</span><span>{session.user.display_name}</span><button disabled={busy} onClick={() => void logout()}>登出</button></div>}
    </header>
    <main className={session ? 'app-shell' : 'login-shell'}>
      {message && <p role="alert">{message}</p>}
      {state === 'login' ? <form onSubmit={event => void submit(event)}>
        <h1>登入專流</h1>
        <label>公司<input value={organization} onChange={event => setOrganization(event.target.value)} required disabled={busy} autoComplete="organization" /></label>
        <label>帳號<input value={username} onChange={event => setUsername(event.target.value)} required disabled={busy} autoComplete="username" /></label>
        <label>密碼<input type="password" value={password} onChange={event => setPassword(event.target.value)} required disabled={busy} autoComplete="current-password" /></label>
        <button type="submit" disabled={busy}>{busy ? '登入中' : '登入'}</button>
      </form> : <>
        {session && <aside aria-label="專案清單"><h2>專案</h2>{projects.map(item => <button key={item.id} disabled={busy} aria-pressed={item.id === selectedId} onClick={() => void selectProject(item.id)}>{item.title}</button>)}</aside>}
        <section aria-label="專案">
          {state === 'checking-session' && <p role="status">確認登入狀態中</p>}
          {state === 'loading' && <p role="status">載入專案中</p>}
          {state === 'ready' && projects.length === 0 && <p>目前沒有專案</p>}
          {state === 'ready' && project && <>
            <h1>{project.title}</h1>
            <nav aria-label="節點路徑">{pathFor(project.nodes, selectedNodeId).map(node => node.title).join(' / ') || project.title}</nav>
            <section aria-label="節點樹" className="node-tree">
              <h2>節點</h2>
              {project.nodes.length === 0 ? <p>這個專案還沒有節點</p> : <NodeTree nodes={project.nodes} parentId={null} selectedId={selectedNodeId} select={setSelectedNodeId} />}
            </section>
          </>}
          {state === 'error' && <button disabled={busy} onClick={retry}>重試</button>}
        </section>
      </>}
    </main>
  </>;
}
