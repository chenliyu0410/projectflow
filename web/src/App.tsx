import WorkflowLibrary from './components/WorkflowLibrary';
import TimelineView from './components/TimelineView';
import DependencyPanel from './components/DependencyPanel';
import ReviewCenter from './components/ReviewCenter';
import AuditLogView from './components/AuditLogView';
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
  const [switchTarget, setSwitchTarget] = useState('');
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
  const [recordVersion, setRecordVersion] = useState(0);
  const [editorGeneration, setEditorGeneration] = useState(0);
  const [workflows, setWorkflows] = useState<WorkflowSummary[] | null>(null);
  const [workflowLoading, setWorkflowLoading] = useState(false);
  const [workflowId, setWorkflowId] = useState('');
  const [projectTitle, setProjectTitle] = useState('');
  const [projectStart, setProjectStart] = useState('');
  const [projectView, setProjectView] = useState<'workspace' | 'timeline' | 'dependencies'>('workspace');
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
    closeCreation(); setWorkflows(null); setSwitchTarget('');
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
    closeCreation(); setProjectView('workspace');
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
    begin(); closeCreation(); setMessage(''); setProjectView('workspace'); setSelectedNodeId(nodeId);
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
  async function switchCompany(target = switchTarget) {
    if (!target || busy || !session?.showcase) return;
    const request = begin();
    closeCreation(); setSwitchTarget(''); setBusy(true); setState('loading'); setMessage('');
    setProject(null); setProjects([]); setWorkflows(null); setRecordVersion(0); setRoute({page:'overview'});
    try {
      const value = await api.switchCompany(target, request.controller.signal);
      if (current(request)) await loadProjects(request, value);
    } catch (error) {
      // A dropped response can still mean the cookie changed. Re-read the real session;
      // never restore previous-company data or automatically repeat the switch mutation.
      if (current(request)) {
        setBusy(false);
        await restore();
        setMessage(error instanceof ApiError ? error.message : '切換失敗，已重新確認登入公司');
      }
    } finally { if (current(request)) setBusy(false); }
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
            ? '目前狀態不允許此操作，請檢查閘門與前置任務'
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
    setEditor(null); setCreationOpen(false); setWorkflowLoading(false); setWorkflowId(''); setProjectTitle(''); setProjectStart('');
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
    if (!canCreate || (creationMode === 'workflow' && !workflowId) || !projectTitle.trim() || (creationMode === 'workflow' && workflows?.find(w => w.id === workflowId)?.requires_start_date && !projectStart) || workflowLoading || mutationId.current !== null) return;
    const request = begin();
    mutationId.current = request.id; setMutating(true); setMessage('');
    let created = false;
    try {
      const result = creationMode === 'blank' ? await api.createProject(projectTitle.trim(), request.controller.signal)
        : await api.createFromWorkflow({ workflow_id: workflowId, title: projectTitle.trim(), ...(projectStart ? {start_date: projectStart} : {}) }, request.controller.signal);
      if (!current(request)) return;
      created = true; closeCreation(); setProjectView('workspace'); setProject(null); setSelectedNodeId(null); setSelectedId(result.id); setState('loading');
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

  async function reloadRecords(signal: AbortSignal) {
    if (!project) return;
    const id = sequence.current;
    try {
      const detail = await api.project(project.id, signal);
      if (signal.aborted || id !== sequence.current) return;
      setProject(detail); setRecordVersion(value => value + 1);
      if (selectedNodeId && !detail.nodes.some(node => node.id === selectedNodeId)) { setSelectedNodeId(null); setMessage('找不到項目或已失去可見權限'); }
    } catch (error) {
      if (!signal.aborted && id === sequence.current && error instanceof ApiError && [403, 404].includes(error.status)) { setProject(null); setState('error'); setMessage(error.message); }
      throw error;
    }
  }

  return <>
    {!session && <header className="login-brand"><img src="/mark.svg" width="32" height="32" alt="" /><strong className="brand-name">專流 ProjectFlow</strong></header>}
    <main className={session ? 'app-shell' : 'login-shell'}>
      {message && !session && <p role="alert">{message}</p>}
      {state === 'login' ? <form onSubmit={event => void submit(event)}>
        <h1>登入專流</h1>
        <label>公司<input value={organization} onChange={event => setOrganization(event.target.value)} required disabled={busy} autoComplete="organization" /></label>
        <label>帳號<input value={username} onChange={event => setUsername(event.target.value)} required disabled={busy} autoComplete="username" /></label>
        <label>密碼<input type="password" value={password} onChange={event => setPassword(event.target.value)} required disabled={busy} autoComplete="current-password" /></label>
        <button type="submit" disabled={busy}>{busy ? '登入中' : '登入'}</button>
      </form> : <>
        {session ? <WorkspaceShell key={session.organization.id} route={route} projects={projects} busy={busy || (state === 'loading' && route.page !== 'project')} navigate={navigate} session={<><span aria-label="目前公司">{session.organization.name}</span>{session.showcase && <><label>切換公司（本機展示）<select aria-label="切換公司（本機展示）" value={switchTarget || session.organization.key} disabled={busy || mutating} onChange={e=>{const key=e.target.value;if(key===session.organization.key){setSwitchTarget('');return;}if(document.querySelector('.workspace-content form')) setSwitchTarget(key);else void switchCompany(key);}}>{session.showcase.companies.map(company=><option key={company.key} value={company.key}>{company.name}｜{company.industry}</option>)}</select></label><span className="showcase-badge">{session.showcase.active ? '展示身分 · 管理者' : '本機展示模式'}</span>{switchTarget && <div className="company-switch-confirm" role="group" aria-label="確認切換公司"><p>將以展示管理者進入所選公司。未儲存的表單內容將離開。</p><button disabled={busy} onClick={()=>void switchCompany()}>確認切換公司</button><button disabled={busy} onClick={()=>setSwitchTarget('')}>取消切換</button></div>}</>}<div className="session-person"><span className="avatar" aria-hidden="true">{session.user.display_name.slice(0, 1)}</span><strong>{session.user.display_name}</strong></div><button disabled={busy} onClick={() => void logout()}>登出</button></>}>
        {message && <p role="alert">{message}</p>}
        <section aria-label={route.page === 'project' ? '專案' : route.page === 'overview' ? '總覽頁面' : route.page === 'my-tasks' ? '我的任務頁面' : route.page === 'reviews' ? '審核中心頁面' : route.page === 'audit' ? '稽核紀錄頁面' : '模板庫頁面'}>
          {session && canCreate && <div className="project-toolbar global-actions">{session.user.role === 'admin' && <button disabled={busy || mutating || state !== 'ready'} onClick={() => { begin(); closeCreation(); setCreationMode('blank'); setCreationOpen(true); setMessage(''); }}>新增空白專案</button>}<button disabled={busy || mutating || workflowLoading || state !== 'ready'} onClick={() => void openCreation()}>新增專案</button></div>}
          {creationOpen && <form className="creation-form" onSubmit={event => void createProject(event)}>
            {creationMode === 'workflow' && <label>工作流模板<select value={workflowId} disabled={workflowLoading || mutating} onChange={event => setWorkflowId(event.target.value)}>
              <option value="">選擇模板</option>{workflows?.map(workflow => <option key={workflow.id} value={workflow.id}>{workflow.name}</option>)}
            </select></label>}
            {creationMode === 'workflow' && <label>專案開始日<input aria-label="專案開始日" type="date" min="0001-01-01" max="9999-12-31" value={projectStart} required={!!workflows?.find(w => w.id === workflowId)?.requires_start_date} disabled={mutating} onChange={e => setProjectStart(e.target.value)} /><small>{workflows?.find(w => w.id === workflowId)?.requires_start_date ? '此模板含相對日期，開始日必填（第 0 天）' : '可留空；無日期設定的模板不會自動排程'}</small></label>}
            <label>新專案名稱<input value={projectTitle} disabled={mutating} onChange={event => setProjectTitle(event.target.value)} /></label>
            {workflowLoading && <p role="status">載入模板中</p>}
            {creationMode === 'workflow' && !workflowLoading && workflows === null && <button type="button" onClick={() => void openCreation()}>重試模板</button>}
            {creationMode === 'workflow' && workflows?.length === 0 && <p>目前沒有工作流模板</p>}
            <div className="form-actions"><button type="submit" disabled={(creationMode === 'workflow' && !workflowId) || !projectTitle.trim() || (creationMode === 'workflow' && !!workflows?.find(w => w.id === workflowId)?.requires_start_date && !projectStart) || mutating || workflowLoading}>建立專案</button>
              <button type="button" disabled={mutating} onClick={() => { begin(); closeCreation(); setMessage(''); }}>取消</button></div>
          </form>}
          {state === 'checking-session' && <p role="status">確認登入狀態中</p>}
          {state === 'loading' && <p role="status">載入專案中</p>}
          {state === 'ready' && projects.length === 0 && <p>目前沒有專案</p>}
          {state === 'ready' && route.page === 'overview' && <WorkspaceOverview openProject={id => navigate({ page: 'project', projectId: id, nodeId: null })} expired={expireSession} />}
          {state === 'ready' && !busy && !creationOpen && route.page === 'workflows' && <WorkflowLibrary expired={expireSession} changed={() => setWorkflows(null)} />}
          {state === 'ready' && !busy && !creationOpen && route.page === 'reviews' && <ReviewCenter openNode={(projectId, nodeId) => navigate({page:'project', projectId, nodeId})} expired={expireSession} />}
          {state === 'ready' && !busy && !creationOpen && route.page === 'audit' && <AuditLogView openNode={(projectId, nodeId) => navigate({page:'project', projectId, nodeId})} expired={expireSession} />}
          {state === 'ready' && route.page === 'my-tasks' && <MyTasks openNode={(projectId, nodeId) => navigate({ page: 'project', projectId, nodeId })} expired={expireSession} />}
          {state === 'ready' && route.page === 'project' && project && <><h1 className="project-heading">{project.title}</h1><div className="workspace-tools"><div className="project-views" role="tablist" aria-label="專案檢視">{([['workspace','工作區'],['timeline','時程'],['dependencies','前置相依']] as const).map(([view,label]) => <button key={view} role="tab" aria-selected={projectView === view} disabled={busy || mutating} onClick={() => { if (view === projectView) return; begin(); closeCreation(); setProjectView(view); }}>{label}</button>)}</div>{projectView === 'workspace' && <div className="project-toolbar">
            {canAddNode && <button disabled={busy || mutating || creationOpen} onClick={() => openNodeEditor('create')}>新增子節點</button>}
            {canEditNode && <button disabled={busy || mutating || creationOpen} onClick={() => openNodeEditor('edit')}>編輯節點</button>}
          </div>}</div>{projectView === 'timeline' && !busy && !creationOpen && <TimelineView key={`${project.id}:${recordVersion}`} project={project} select={selectNode} reload={reloadRecords} expired={expireSession} />}{projectView === 'dependencies' && !busy && !creationOpen && <DependencyPanel key={`${project.id}:${recordVersion}`} projectId={project.id} select={selectNode} reload={reloadRecords} expired={expireSession} />}{projectView === 'workspace' && <>
          {editor && <NodeEditor key={`${project.id}:${selectedNodeId}:${editor}:${editorGeneration}`} projectId={project.id} mode={editor} node={editor === 'edit' ? selectedNode : null} parent={selectedNode}
            canAssign={editor === 'create' || !!selectedNode?.capabilities?.assign} reload={reloadNode} close={() => setEditor(null)} expired={expireSession} />}
          <NodeWorkspace key={project.id} project={project} selectedNodeId={selectedNodeId} select={selectNode}
            userId={session.user.id} reloadRecords={reloadRecords} expired={expireSession} recordVersion={recordVersion} recordsEnabled={!busy && !editor && !creationOpen}
            readonly={session.user.role === 'readonly'} canApprove={!!canApprove} disabled={busy || mutating || creationOpen || !!editor} mutate={(action, id, status) => void mutate(action, id, status)} /></>}</>}
          {state === 'error' && <button disabled={busy} onClick={retry}>重試</button>}
        </section>
        </WorkspaceShell> : <section>{state === 'checking-session' && <p role="status">確認登入狀態中</p>}{state === 'error' && <button onClick={retry}>重試</button>}</section>}
      </>}
    </main>
  </>;
}
