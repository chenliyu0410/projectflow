import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { api, ApiError } from './api';
import type { NodeStatus, ProjectDetail, ProjectSummary, SessionInfo, WorkflowSummary, WorkspaceRoute } from './types';
import WorkspaceShell from './components/WorkspaceShell';
import NodeWorkspace from './components/NodeWorkspace';
import NodeEditor from './components/NodeEditor';
import WorkspaceOverview from './components/WorkspaceOverview';
import MyTasks from './components/MyTasks';

type State = 'checking-session' | 'login' | 'loading' | 'ready' | 'error';
export default function App() {
  const [state, setState] = useState<State>('checking-session');
  const [session, setSession] = useState<SessionInfo | null>(null);
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [route, setRoute] = useState<WorkspaceRoute>({ page: 'overview' });
  const selectedId = route.page === 'project' ? route.projectId : null;
  const selectedNodeId = route.page === 'project' ? route.nodeId : null;
  function setSelectedId(projectId: string | null) { setRoute({ page: 'project', projectId, nodeId: null }); }
  function setSelectedNodeId(nodeId: string | null) { setRoute(value => value.page === 'project' ? { ...value, nodeId } : value); }
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [organization, setOrganization] = useState('food');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [mutating, setMutating] = useState(false);
  const mutationId = useRef<number | null>(null);
  const [creationOpen, setCreationOpen] = useState(false);
  const [creationMode, setCreationMode] = useState<'workflow' | 'blank'>('workflow');
  const [editor, setEditor] = useState<'create' | 'edit' | null>(null);
  const [editorGeneration, setEditorGeneration] = useState(0);
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
    setSession(null); setProjects([]); setRoute({ page: 'overview' }); setProject(null); setPassword(''); setState('login');
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
    setProject(null); setRoute({ page: 'overview' });
    try {
      const result = await api.projects(request.controller.signal);
      if (!current(request)) return;
      setProjects(result.items);
      setState('ready');
    } catch (error) { projectFailed(error, request); }
  }
  function projectFailed(error: unknown, request: ReturnType<typeof begin>) {
    if (!current(request)) return;
    failed(error, request);
    if (!(error instanceof ApiError && error.status === 401)) setMessage(error instanceof ApiError && error.status === 403 ? '沒有操作權限' : error instanceof ApiError && error.status === 404 ? '找不到項目' : '無法載入專案資料');
  }
  async function loadDetail(id: string, request: ReturnType<typeof begin>, nodeId: string | null = null) {
    try {
      const detail = await api.project(id, request.controller.signal);
      if (!current(request)) return;
      setProject(detail);
      setSelectedNodeId(detail.nodes.some(node => node.id === nodeId) ? nodeId : null);
      if (nodeId && !detail.nodes.some(node => node.id === nodeId)) setMessage('找不到項目');
      setState('ready');
    } catch (error) { projectFailed(error, request); }
  }
  async function selectProject(id: string, nodeId: string | null = null) {
    if (busy) return;
    const request = begin();
    closeCreation();
    setRoute({ page: 'project', projectId: id, nodeId }); setProject(null); setMessage(''); setState('loading');
    await loadDetail(id, request, nodeId);
  }
  function navigate(next: WorkspaceRoute) {
    if (busy) return;
    if (next.page === 'project' && next.projectId) { void selectProject(next.projectId, next.nodeId); return; }
    begin(); closeCreation(); setProject(null); setMessage(''); setRoute(next); setState('ready');
  }
  function selectNode(nodeId: string | null) {
    if (busy) return;
    begin(); closeCreation(); setMessage(''); setSelectedNodeId(nodeId);
  }
  function retry() {
    if (session && selectedId) void selectProject(selectedId, selectedNodeId);
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
        await loadDetail(projectId, request, selectedNodeId);
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
    setEditor(null); setCreationOpen(false); setWorkflowLoading(false); setWorkflowId(''); setProjectTitle('');
  }
  async function openCreation() {
    if (!canCreate || busy || mutating || state !== 'ready') return;
    setCreationMode('workflow'); setEditor(null); setCreationOpen(true); setMessage('');
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
    if (!canCreate || (creationMode === 'workflow' && !workflowId) || !projectTitle.trim() || workflowLoading || mutationId.current !== null) return;
    const request = begin();
    mutationId.current = request.id; setMutating(true); setMessage('');
    let created = false;
    try {
      const result = creationMode === 'blank' ? await api.createProject(projectTitle.trim(), request.controller.signal)
        : await api.createFromWorkflow({ workflow_id: workflowId, title: projectTitle.trim() }, request.controller.signal);
      if (!current(request)) return;
      created = true; closeCreation(); setProject(null); setSelectedNodeId(null); setSelectedId(result.id); setState('loading');
      setProjects(value => value.some(item => item.id === result.id) ? value : [...value, result]);
      const list = await api.projects(request.controller.signal);
      if (!current(request)) return;
      setProjects(list.items);
      const detail = await api.project(result.id, request.controller.signal);
      if (!current(request)) return;
      setProject(detail); setState('ready');
    } catch (error) {
      if (!current(request)) return;
      if (created) { projectFailed(error, request); if (!(error instanceof ApiError && error.status === 401)) setMessage('已儲存，資料重新載入失敗'); }
      else if (error instanceof ApiError && error.status === 401) { clearSession(); setMessage(error.message); }
      else setMessage(error instanceof ApiError && error.status === 403 ? '沒有建立專案權限'
        : error instanceof ApiError && error.status === 404 ? '找不到工作流模板'
          : error instanceof ApiError && error.status === 0 ? '連線中斷，請重新整理確認建立結果；不會自動重送'
            : error instanceof ApiError ? error.message : '操作失敗，請稍後再試');
    } finally { if (current(request)) { mutationId.current = null; setMutating(false); } }
  }

  const selectedNode = project?.nodes.find(node => node.id === selectedNodeId) ?? null;
  const canAddNode = session?.user.role !== 'readonly' && (selectedNode ? selectedNode.capabilities?.create_child : project?.capabilities?.create_node);
  const canEditNode = session?.user.role !== 'readonly' && selectedNode?.kind !== 'project' && selectedNode?.capabilities?.edit_metadata;
  function openNodeEditor(mode: 'create' | 'edit') {
    if (busy || mutating || creationOpen) return;
    begin(); setEditorGeneration(value => value + 1); setEditor(mode);
  }
  function expireSession() { begin(); clearSession(); setBusy(false); setMessage('登入已失效，請重新登入'); }
  async function reloadNode(nodeId: string) {
    if (!project) return;
    const request = begin();
    const detail = await api.project(project.id, request.controller.signal);
    if (!current(request)) return;
    setEditor(null); setProject(detail); setSelectedNodeId(detail.nodes.some(node => node.id === nodeId) ? nodeId : null);
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
        {session ? <WorkspaceShell route={route} projects={projects} busy={busy || (state === 'loading' && route.page !== 'project')} navigate={navigate}>
        <section aria-label={route.page === 'project' ? '專案' : route.page === 'overview' ? '總覽頁面' : '我的任務頁面'}>
          {session && canCreate && <div className="project-toolbar">{session.user.role === 'admin' && <button disabled={busy || mutating || state !== 'ready'} onClick={() => { begin(); closeCreation(); setCreationMode('blank'); setCreationOpen(true); setMessage(''); }}>新增空白專案</button>}<button disabled={busy || mutating || workflowLoading || state !== 'ready'} onClick={() => void openCreation()}>新增專案</button></div>}
          {creationOpen && <form className="creation-form" onSubmit={event => void createProject(event)}>
            {creationMode === 'workflow' && <label>工作流模板<select value={workflowId} disabled={workflowLoading || mutating} onChange={event => setWorkflowId(event.target.value)}>
              <option value="">選擇模板</option>{workflows?.map(workflow => <option key={workflow.id} value={workflow.id}>{workflow.name}</option>)}
            </select></label>}
            <label>新專案名稱<input value={projectTitle} disabled={mutating} onChange={event => setProjectTitle(event.target.value)} /></label>
            {workflowLoading && <p role="status">載入模板中</p>}
            {creationMode === 'workflow' && !workflowLoading && workflows === null && <button type="button" onClick={() => void openCreation()}>重試模板</button>}
            {creationMode === 'workflow' && workflows?.length === 0 && <p>目前沒有工作流模板</p>}
            <div className="form-actions"><button type="submit" disabled={(creationMode === 'workflow' && !workflowId) || !projectTitle.trim() || mutating || workflowLoading}>建立專案</button>
              <button type="button" disabled={mutating} onClick={() => { begin(); closeCreation(); setMessage(''); }}>取消</button></div>
          </form>}
          {state === 'checking-session' && <p role="status">確認登入狀態中</p>}
          {state === 'loading' && <p role="status">載入專案中</p>}
          {state === 'ready' && projects.length === 0 && <p>目前沒有專案</p>}
          {state === 'ready' && route.page === 'overview' && <WorkspaceOverview openProject={id => navigate({ page: 'project', projectId: id, nodeId: null })} expired={expireSession} />}
          {state === 'ready' && route.page === 'my-tasks' && <MyTasks openNode={(projectId, nodeId) => navigate({ page: 'project', projectId, nodeId })} expired={expireSession} />}
          {state === 'ready' && route.page === 'project' && project && <><div className="project-toolbar">
            {canAddNode && <button disabled={busy || mutating || creationOpen} onClick={() => openNodeEditor('create')}>新增子節點</button>}
            {canEditNode && <button disabled={busy || mutating || creationOpen} onClick={() => openNodeEditor('edit')}>編輯節點</button>}
          </div>
          {editor && <NodeEditor key={`${project.id}:${selectedNodeId}:${editor}:${editorGeneration}`} projectId={project.id} mode={editor} node={editor === 'edit' ? selectedNode : null} parent={selectedNode}
            canAssign={editor === 'create' || !!selectedNode?.capabilities?.assign} reload={reloadNode} close={() => setEditor(null)} expired={expireSession} />}
          <NodeWorkspace key={project.id} project={project} selectedNodeId={selectedNodeId} select={selectNode}
            readonly={session.user.role === 'readonly'} canApprove={!!canApprove} disabled={busy || mutating || creationOpen || !!editor} mutate={(action, id, status) => void mutate(action, id, status)} /></>}
          {state === 'error' && <button disabled={busy} onClick={retry}>重試</button>}
        </section>
        </WorkspaceShell> : <section>{state === 'checking-session' && <p role="status">確認登入狀態中</p>}{state === 'error' && <button onClick={retry}>重試</button>}</section>}
      </>}
    </main>
  </>;
}
