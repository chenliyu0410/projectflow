import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { api, ApiError } from './api';
import type { NodeItem, NodeStatus, ProjectDetail, ProjectSummary, SessionInfo, WorkflowSummary } from './types';

type State = 'checking-session' | 'login' | 'loading' | 'ready' | 'error';
const columns: { status: NodeStatus; label: string }[] = [
  { status: 'todo', label: '待處理' }, { status: 'doing', label: '進行中' },
  { status: 'review', label: '待確認' }, { status: 'done', label: '完成' },
];
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
  const [mutating, setMutating] = useState(false);
  const mutationId = useRef<number | null>(null);
  const [creationOpen, setCreationOpen] = useState(false);
  const [workflows, setWorkflows] = useState<WorkflowSummary[] | null>(null);
  const [workflowLoading, setWorkflowLoading] = useState(false);
  const [workflowId, setWorkflowId] = useState('');
  const [projectTitle, setProjectTitle] = useState('');
  const sequence = useRef(0);
  const controller = useRef<AbortController | null>(null);

  function begin() {
    controller.current?.abort();
    mutationId.current = null; setMutating(false);
    const request = { id: ++sequence.current, controller: new AbortController() };
    controller.current = request.controller;
    return request;
  }
  function current(request: ReturnType<typeof begin>) {
    return request.id === sequence.current && !request.controller.signal.aborted;
  }
  function clearSession() {
    closeCreation(); setWorkflows(null);
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
    closeCreation();
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
    closeCreation();
    setBusy(true); setMessage('');
    try {
      await api.logout(request.controller.signal);
      if (current(request)) clearSession();
    } catch (error) { failed(error, request); }
    finally { if (current(request)) setBusy(false); }
  }

  async function mutate(action: 'status' | 'gate', id: string, status?: NodeStatus) {
    if (!project || !session || busy || mutationId.current !== null || session.user.role === 'readonly') return;
    const projectId = project.id;
    const request = begin();
    mutationId.current = request.id; setMutating(true); setMessage('');
    try {
      if (action === 'status' && status) {
        const result = await api.updateNodeStatus(id, status, request.controller.signal);
        if (!current(request)) return;
        setProject(value => value?.id === projectId ? {
          ...value, nodes: value.nodes.map(node => node.id === id ? { ...node, status: result.status } : node),
        } : value);
      } else if (action === 'gate') {
        await api.approveGate(id, request.controller.signal);
        if (!current(request)) return;
        await loadDetail(projectId, request);
      }
    } catch (error) {
      if (!current(request)) return;
      if (error instanceof ApiError && error.status === 401) {
        clearSession(); setMessage(error.message);
      } else {
        setMessage(error instanceof ApiError && error.status === 403
          ? action === 'gate' ? '沒有核准此閘門的權限' : '沒有操作此節點的權限'
          : error instanceof ApiError && error.status === 409 && action === 'status'
            ? '前一階段閘門尚未通過'
            : error instanceof ApiError ? error.message : '操作失敗，請稍後再試');
      }
    } finally {
      if (current(request)) { mutationId.current = null; setMutating(false); }
    }
  }
  const canApprove = session && project && session.user.role !== 'readonly' && (
    session.user.role === 'admin' || session.user.id === project.owner_user_id || session.user.role === 'reviewer'
  );
  const canCreate = session?.user.role === 'admin' || session?.user.role === 'project_owner';
  function closeCreation() {
    setCreationOpen(false); setWorkflowLoading(false); setWorkflowId(''); setProjectTitle('');
  }
  async function openCreation() {
    if (!canCreate || busy || mutating || state !== 'ready') return;
    setCreationOpen(true); setMessage('');
    if (workflows !== null) return;
    const request = begin();
    setWorkflowLoading(true);
    try {
      const result = await api.workflows(request.controller.signal);
      if (current(request)) setWorkflows(result.items);
    } catch (error) {
      if (current(request)) {
        if (error instanceof ApiError && error.status === 401) clearSession();
        setMessage(error instanceof ApiError ? error.message : '操作失敗，請稍後再試');
      }
    } finally { if (current(request)) setWorkflowLoading(false); }
  }
  async function createProject(event: FormEvent) {
    event.preventDefault();
    if (!canCreate || !workflowId || !projectTitle.trim() || workflowLoading || mutationId.current !== null) return;
    const request = begin();
    mutationId.current = request.id; setMutating(true); setMessage('');
    let created = false;
    try {
      const result = await api.createFromWorkflow({ workflow_id: workflowId, title: projectTitle.trim() }, request.controller.signal);
      if (!current(request)) return;
      created = true; closeCreation(); setProject(null); setSelectedNodeId(null); setSelectedId(result.id); setState('loading');
      setProjects(value => value.some(item => item.id === result.id) ? value : [...value, result]);
      const list = await api.projects(request.controller.signal);
      if (!current(request)) return;
      setProjects(list.items);
      await loadDetail(result.id, request);
    } catch (error) {
      if (!current(request)) return;
      if (created) projectFailed(error, request);
      else if (error instanceof ApiError && error.status === 401) { clearSession(); setMessage(error.message); }
      else setMessage(error instanceof ApiError && error.status === 403 ? '沒有建立專案權限'
        : error instanceof ApiError && error.status === 404 ? '找不到工作流模板'
          : error instanceof ApiError ? error.message : '操作失敗，請稍後再試');
    } finally { if (current(request)) { mutationId.current = null; setMutating(false); } }
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
          {session && canCreate && <div className="project-toolbar"><button disabled={busy || mutating || workflowLoading || state !== 'ready'} onClick={() => void openCreation()}>新增專案</button></div>}
          {creationOpen && <form className="creation-form" onSubmit={event => void createProject(event)}>
            <label>工作流模板<select value={workflowId} disabled={workflowLoading || mutating} onChange={event => setWorkflowId(event.target.value)}>
              <option value="">選擇模板</option>{workflows?.map(workflow => <option key={workflow.id} value={workflow.id}>{workflow.name}</option>)}
            </select></label>
            <label>新專案名稱<input value={projectTitle} disabled={mutating} onChange={event => setProjectTitle(event.target.value)} /></label>
            {workflowLoading && <p role="status">載入模板中</p>}
            {!workflowLoading && workflows === null && <button type="button" onClick={() => void openCreation()}>重試模板</button>}
            {workflows?.length === 0 && <p>目前沒有工作流模板</p>}
            <div className="form-actions"><button type="submit" disabled={!workflowId || !projectTitle.trim() || mutating || workflowLoading}>建立專案</button>
              <button type="button" disabled={mutating} onClick={() => { begin(); closeCreation(); setMessage(''); }}>取消</button></div>
          </form>}
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
            {project.gates.some(gate => gate.status === 'pending') && <div className="gate-banner">
              <p>尚有階段閘門待核准，後續階段可能被阻擋</p>
              {canApprove && project.gates.filter(gate => gate.status === 'pending').map(gate => <div className="gate-row" key={gate.id}>
                <span>{project.nodes.find(node => node.id === gate.node_id)?.title ?? '階段閘門'}</span>
                <button disabled={mutating || creationOpen} onClick={() => void mutate('gate', gate.id)}>核准閘門</button>
              </div>)}
            </div>}
            <section aria-label="看板" className="kanban">
              {columns.map(column => <div key={column.status} aria-label={column.label} className="kanban-column">
                <h2>{column.label}</h2>
                {project.nodes.filter(node => node.kind === 'task' && node.status === column.status).map(node => <article key={node.id} className="task-card">
                  <button className="task-title" aria-pressed={node.id === selectedNodeId} onClick={() => setSelectedNodeId(node.id)}>{node.title}</button>
                  {session?.user.role !== 'readonly' && <label>狀態<select aria-label={`${node.title}狀態`} value={node.status} disabled={mutating || creationOpen} onChange={event => void mutate('status', node.id, event.target.value as NodeStatus)}>
                    {columns.map(option => <option key={option.status} value={option.status}>{option.label}</option>)}
                  </select></label>}
                </article>)}
              </div>)}
            </section>
          </>}
          {state === 'error' && <button disabled={busy} onClick={retry}>重試</button>}
        </section>
      </>}
    </main>
  </>;
}
