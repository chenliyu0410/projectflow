import { childCreationReason } from './child-creation';
import LinkedOperations from './components/LinkedOperations';
import PreviewBoundary from './components/PreviewBoundary';
import AIGovernance from './components/AIGovernance';
import DocumentManager from './components/DocumentManager';
import OperationsManager from './components/OperationsManager';
import TemplateDialogs from './components/TemplateDialogs';
import Dropdown from './components/Dropdown';
import WorkflowLibrary from './components/WorkflowLibrary';
import TimelineView from './components/TimelineView';
import DependencyPanel from './components/DependencyPanel';
import ReviewCenter from './components/ReviewCenter';
import AuditLogView from './components/AuditLogView';
import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { api, ApiError, KNOWN_CONFLICTS } from './api';
import type { NodeStatus, ProjectDetail, ProjectSummary, SessionInfo, WorkflowSummary, WorkspaceRoute } from './types';
import WorkspaceShell, { projectColor } from './components/WorkspaceShell';
import NodeWorkspace, { isLeafTask, levelOf } from './components/NodeWorkspace';
import type { NodeTab } from './components/NodeWorkspace';
import NodeEditor from './components/NodeEditor';
import WorkspaceOverview from './components/WorkspaceOverview';
import MyTasks from './components/MyTasks';
import NavIcon from './components/NavIcons';

const ROLE_LABELS: Record<string, string> = { admin: '系統管理員', project_owner: '專案負責人', reviewer: '階段審核人', member: '成員', readonly: '唯讀' };
const PAGE_SCOPES: Record<string, string> = { overview: '所有可見專案', 'my-tasks': '我的任務', reviews: '審核中心', workflows: '模板庫', audit: '活動與稽核紀錄', operations: '公司營運資料', governance: 'AI 政策展示預覽' };

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
  // TP-B: the user's latest structure change (kept in memory like the Demo) and the notice that offers 復原／開啟.
  const [lastUndo, setLastUndo] = useState<{ id: string; label: string } | null>(null);
  const [templateDialog,setTemplateDialog] = useState<'save'|'apply'|null>(null);
  const [notice, setNotice] = useState<{ text: string; undo: boolean; open?: string } | null>(null);
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
  const [projectView, setProjectView] = useState<NodeTab>('board');
  // A card's ✓ 回報 opens that task with its report form already expanded.
  const [reportIntent, setReportIntent] = useState<string | null>(null);
  // Like the Demo: a leaf task opens on its records, anything else on its board.
  const defaultTab = (nodes: ProjectDetail['nodes'], nodeId: string | null): NodeTab => isLeafTask(nodes, nodes.find(node => node.id === nodeId)) ? 'records' : 'board';
  const sequence = useRef(0);
  const creationForm = useRef<HTMLFormElement>(null);
  const documentLeaveGuard = useRef<(() => boolean) | null>(null);
  const [operationsPreview, setOperationsPreview] = useState(false);
  const canLeaveDocument = () => documentLeaveGuard.current?.() ?? true;
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
    closeCreation(); setWorkflows(null); setSwitchTarget(''); setLastUndo(null); setNotice(null);
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
    setLastUndo(null); setNotice(null);
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
      return detail;
    } catch (error) { projectFailed(error, request); }
  }
  async function selectProject(id: string, nodeId: string | null = null) {
    if (busy) return;
    const request = begin();
    closeCreation(); setProjectView('board');
    setRoute({ page: 'project', projectId: id, nodeId }); setProject(null); setMessage(''); setState('loading');
    const detail = await loadDetail(id, request, nodeId);
    if (detail && current(request)) setProjectView(defaultTab(detail.nodes, nodeId));
  }
  function navigate(next: WorkspaceRoute) {
    if (busy) return;
    if (!canLeaveDocument()) return;
    setOperationsPreview(false);
    if (next.page === 'project' && next.projectId) { void selectProject(next.projectId, next.nodeId); return; }
    begin(); closeCreation(); setProject(null); setMessage(''); setRoute(next); setState('ready');
  }
  /** Keep the user's timeline/graph context, including leaf tasks and breadcrumbs. */
  function selectNode(nodeId: string | null, preferTab?: NodeTab) {
    if (busy) return;
    if (!canLeaveDocument()) return;
    const nodes = project?.nodes ?? [];
    begin(); closeCreation(); setMessage(''); setReportIntent(null);
    setProjectView(preferTab ?? (projectView === 'timeline' || projectView === 'graph' ? projectView : defaultTab(nodes, nodeId)));
    setSelectedNodeId(nodeId);
  }
  function openReport(nodeId: string) {
    if (busy || mutationId.current !== null) return;
    selectNode(nodeId, 'records'); setReportIntent(nodeId);
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
    if (!canLeaveDocument()) { setSwitchTarget(''); return; }
    setOperationsPreview(false);
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
    if (!canLeaveDocument()) return;
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
            ? KNOWN_CONFLICTS.has(error.message) ? error.message : '目前狀態不允許此操作，請檢查閘門與前置任務'
            : error instanceof ApiError ? error.message : '操作失敗，請稍後再試');
      }
    } finally {
      if (current(request)) { mutationId.current = null; setMutating(false); }
    }
  }
  function announce(text: string, undo: boolean, open?: string) { setMessage(text); setNotice({ text, undo, open }); }
  /** TP-B structure changes: move (drag, 升級, 降級, 移動到…), copy and delete; each can be undone once. */
  async function structure(kind: 'move' | 'copy' | 'delete', id: string, parentId: string | null = null) {
    if (!project || !session || busy || mutationId.current !== null || session.user.role === 'readonly') return;
    if (!canLeaveDocument()) return;
    const projectId = project.id;
    const title = project.nodes.find(node => node.id === id)?.title ?? '';
    const target = parentId ? project.nodes.find(node => node.id === parentId) : undefined;
    const request = begin();
    setEditor(null); mutationId.current = request.id; setMutating(true); setMessage('');
    let saved = false;
    try {
      const signal = request.controller.signal;
      let text = ''; let open: string | undefined; let undoId: string | null; let parentAfter: string | null = null;
      if (kind === 'move') {
        undoId = (await api.moveNode(id, parentId, signal)).undo_id;
        if (undoId) setLastUndo({ id: undoId, label: `移動「${title}」` });
      } else if (kind === 'copy') {
        const result = await api.copyNode(id, signal);
        undoId = result.undo_id; open = result.id; text = `已複製子樹「${result.title}」`;
        setLastUndo({ id: undoId, label: `複製「${title}」` });
      } else {
        const result = await api.deleteNode(id, signal);
        undoId = result.undo_id; parentAfter = result.parent_id; text = `已刪除「${title}」`;
        setLastUndo({ id: undoId, label: `刪除「${title}」` });
      }
      saved = true;
      if (!current(request)) return;
      const detail = await api.project(projectId, signal);
      if (!current(request)) return;
      setProject(detail); setRecordVersion(value => value + 1);
      if (kind === 'delete' && selectedNodeId && !detail.nodes.some(node => node.id === selectedNodeId)) {
        // Like the Demo, leaving a deleted node goes back to its parent.
        const keep = parentAfter && detail.nodes.some(node => node.id === parentAfter) ? parentAfter : null;
        setProjectView(defaultTab(detail.nodes, keep)); setSelectedNodeId(keep);
      }
      if (kind === 'move') {
        const where = !target || target.kind === 'project' ? '專案最上層' : `「${target.title}」底下`;
        text = `已將「${title}」移到${where}${levelOf(detail.nodes, id) >= 5 ? '；層數超過 5 層，建議考慮拆成獨立專案' : ''}`;
      }
      announce(text, !!undoId, open);
    } catch (error) {
      if (!current(request)) return;
      const verb = kind === 'move' ? '移動' : kind === 'copy' ? '複製' : '刪除';
      if (error instanceof ApiError && error.status === 401) { clearSession(); setMessage(error.message); }
      else if (saved) setMessage(`已${verb}，資料重新載入失敗，請重新整理`);
      else setMessage(error instanceof ApiError && error.status === 403 ? `你的角色無權${verb}此任務`
        : error instanceof ApiError && error.status === 0 ? `連線中斷，請重新整理確認${verb}結果；不會自動重送`
          : error instanceof ApiError ? error.message : '操作失敗，請稍後再試');
    } finally { if (current(request)) { mutationId.current = null; setMutating(false); } }
  }
  const moveNode = (id: string, parentId: string | null) => structure('move', id, parentId);
  async function undoLast() {
    if (!session || busy || mutationId.current !== null || session.user.role === 'readonly') return;
    if (!canLeaveDocument()) return;
    if (!lastUndo) { setNotice(null); setMessage('沒有可以復原的操作'); return; }
    const step = lastUndo; const projectId = project?.id;
    const request = begin();
    setEditor(null); mutationId.current = request.id; setMutating(true); setMessage('');
    let saved = false;
    try {
      const result = await api.undo(step.id, request.controller.signal);
      saved = true; setLastUndo(null);
      if (!current(request)) return;
      if (projectId) {
        const detail = await api.project(projectId, request.controller.signal);
        if (!current(request)) return;
        setProject(detail); setRecordVersion(value => value + 1);
        if (selectedNodeId && !detail.nodes.some(node => node.id === selectedNodeId)) {
          const keep = result.parent_id && detail.nodes.some(node => node.id === result.parent_id) ? result.parent_id : null;
          setProjectView(defaultTab(detail.nodes, keep)); setSelectedNodeId(keep);
        }
      }
      setMessage(`已復原：${step.label}`);
    } catch (error) {
      if (!current(request)) return;
      if (error instanceof ApiError && error.status === 401) { clearSession(); setMessage(error.message); }
      else if (saved) setMessage('已復原，資料重新載入失敗，請重新整理');
      else {
        // A step that is no longer the latest (or is gone) can never be undone; other refusals may clear up later.
        if (error instanceof ApiError && (error.status === 404 || error.message === '只能復原最近一次的結構操作')) setLastUndo(null);
        setMessage(error instanceof ApiError && error.status === 0 ? '連線中斷，請重新整理確認復原結果；不會自動重送'
          : error instanceof ApiError && error.status === 404 ? '沒有可以復原的操作'
            : error instanceof ApiError ? error.message : '操作失敗，請稍後再試');
      }
    } finally { if (current(request)) { mutationId.current = null; setMutating(false); } }
  }
  function nodeCreated(title: string, undoId: string | null) {
    if (!undoId) return;
    setLastUndo({ id: undoId, label: `新增「${title}」` });
    announce(`已新增「${title}」`, true);
  }
  // Demo: Ctrl+Z / ⌘Z undoes the last step when focus is not in a field and no form is open.
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (!(event.ctrlKey || event.metaKey) || event.shiftKey || event.altKey || event.key.toLowerCase() !== 'z') return;
      const active = document.activeElement as HTMLElement | null;
      if (active && (/^(INPUT|TEXTAREA|SELECT)$/.test(active.tagName) || active.isContentEditable)) return;
      if (route.page !== 'project' || editor || creationOpen) return;
      event.preventDefault();
      // Undo reloads the project and remounts record forms, so an open draft would be lost.
      const content = document.querySelector('.workspace-content');
      if (content && (content.querySelector('.node-editor, .schedule-editor, form[aria-label="回報表單"]')
        || [...content.querySelectorAll('textarea')].some(area => area.value.trim() !== ''))) {
        setNotice(null); setMessage('請先送出或取消開著的表單，再按 Ctrl+Z 復原'); return;
      }
      void undoLast();
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  });
  const canApprove = session && project && session.user.role !== 'readonly' && (
    session.user.role === 'admin' || session.user.id === project.owner_user_id || session.user.role === 'reviewer'
  );
  const canCreate = session?.user.role === 'admin' || session?.user.role === 'project_owner';
  function closeCreation() {
    setEditor(null); setCreationOpen(false); setWorkflowLoading(false); setWorkflowId(''); setProjectTitle(''); setProjectStart('');
  }
  useEffect(() => {
    if (!creationOpen) return;
    creationForm.current?.scrollIntoView?.({ block: 'start' });
    creationForm.current?.focus();
  }, [creationOpen]);
  async function openCreation(presetWorkflow = '') {
    if (!canCreate || busy || mutating || state !== 'ready') return;
    if (!canLeaveDocument()) return;
    setCreationMode('workflow'); setEditor(null); setCreationOpen(true); setMessage('');
    if (presetWorkflow) setWorkflowId(presetWorkflow);
    if (workflows !== null) return;
    const request = begin();
    setWorkflowLoading(true);
    try {
      const result = await api.workflows(request.controller.signal);
      if (current(request)) setWorkflows(result.items.filter(w=>w.kind!=='task'));
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
      created = true; closeCreation(); setProjectView('board'); setProject(null); setSelectedNodeId(null); setSelectedId(result.id); setState('loading');
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
  const copilotScope = route.page === 'project' ? project?.title ?? '專案' : PAGE_SCOPES[route.page];
  useEffect(()=>{setTemplateDialog(null);},[project?.id,selectedNodeId,session?.user.id,route.page]);
  const canAddNode = session?.user.role !== 'readonly' && (selectedNode ? selectedNode.capabilities?.create_child : project?.capabilities?.create_node);
  // D74: a review/done/skipped node cannot gain new children.
  const closedParent = !!selectedNode && !!childCreationReason(selectedNode, true);
  const canEditNode = session?.user.role !== 'readonly' && selectedNode?.kind !== 'project' && selectedNode?.capabilities?.edit_metadata;
  function openNodeEditor(mode: 'create' | 'edit') {
    if (busy || mutating || creationOpen) return;
    if (!canLeaveDocument()) return;
    begin(); setEditorGeneration(value => value + 1); setEditor(mode);
  }
  function expireSession() { begin(); clearSession(); setBusy(false); setMessage('登入已失效，請重新登入'); }
  async function reloadNode(nodeId: string) {
    if (!project) return;
    const request = begin();
    const detail = await api.project(project.id, request.controller.signal);
    if (!current(request)) return;
    const kept = detail.nodes.some(node => node.id === nodeId) ? nodeId : null;
    // Creating a child keeps the parent and current tab; users can explicitly open it.
    if (editor === 'create') {
      const made = detail.nodes.find(node => node.id === kept);
      if (made) announce(`已新增「${made.title}」，目前仍在原位置`, true, made.id);
      setEditor(null); setProject(detail);
    } else { setEditor(null); setProject(detail); setSelectedNodeId(kept); }
  }

  async function reloadRecords(signal: AbortSignal) {
    if (!project) return;
    const id = sequence.current;
    try {
      const detail = await api.project(project.id, signal);
      if (signal.aborted || id !== sequence.current) return;
      setProject(detail); setRecordVersion(value => value + 1); setReportIntent(null);
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
        {session ? <WorkspaceShell key={session.organization.id} route={route} projects={projects} busy={busy || (state === 'loading' && route.page !== 'project')} navigate={navigate} copilotScope={copilotScope} food={session.organization.key === 'food'} companyName={session.organization.name} accountName={session.user.display_name}
          headerActions={state === 'ready' && route.page === 'project' && project && canAddNode && <Dropdown key={`${project.id}:${selectedNodeId}`} className="project-actions-menu" name="專案操作" closeOnAction label="新增子節點">
              {canAddNode && <button className="primary" disabled={busy || mutating || creationOpen || closedParent} title={selectedNode?.milestone ? '里程碑不能有子任務，請先取消里程碑' : closedParent ? '不能在已完成、待確認或已略過的節點底下新增' : undefined} onClick={() => openNodeEditor('create')}><span aria-hidden="true">＋ </span>新增子節點</button>}
              {['admin','project_owner'].includes(session.user.role) && <>
                <button disabled={busy||mutating} onClick={()=>setTemplateDialog('save')}>另存為模板</button>
                <button disabled={busy||mutating||closedParent} onClick={()=>setTemplateDialog('apply')}>套用模板</button>
              </>}

              </Dropdown>}
          previewKey={state !== 'ready' ? state : route.page === 'operations' || route.page === 'governance' || (route.page === 'project' && ['documents', 'data'].includes(projectView)) ? 'preview' : `${route.page}:${selectedId}:${selectedNodeId}:${projectView}`}
          createAction={canCreate && <button className="new-project" disabled={busy || mutating || workflowLoading || state !== 'ready'} onClick={() => { if (creationOpen) { creationForm.current?.scrollIntoView?.({ block: 'start' }); creationForm.current?.focus(); } else void openCreation(); }}><NavIcon name="plus" size={16} />建立新專案</button>} session={<><span aria-label="目前公司">{session.organization.name}</span>{session.showcase && <><label>切換公司（本機展示）<select aria-label="切換公司（本機展示）" value={switchTarget || session.organization.key} disabled={busy || mutating} onChange={e=>{const key=e.target.value;if(key===session.organization.key){setSwitchTarget('');return;}if(document.querySelector('.workspace-content form')) setSwitchTarget(key);else void switchCompany(key);}}>{session.showcase.companies.map(company=><option key={company.key} value={company.key}>{company.name}｜{company.industry}</option>)}</select></label><span className="showcase-badge">{session.showcase.active ? '展示身分 · 管理者' : '本機展示模式'}</span>{switchTarget && <div className="company-switch-confirm" role="group" aria-label="確認切換公司"><p>將以展示管理者進入所選公司。未儲存的表單內容將離開。</p><button disabled={busy} onClick={()=>void switchCompany()}>確認切換公司</button><button disabled={busy} onClick={()=>setSwitchTarget('')}>取消切換</button></div>}</>}<div className="session-person"><span className="avatar" aria-hidden="true">{session.user.display_name.slice(0, 1)}</span><div><strong>{session.user.display_name}</strong><small>{ROLE_LABELS[session.user.role] ?? session.user.role}</small></div></div><button disabled={busy} onClick={() => void logout()}>登出</button></>}>
        {message && <p role="alert" className={notice?.text === message ? 'notice' : undefined}>{message}
          {notice?.text === message && notice.open && <button type="button" disabled={busy || mutating} onClick={() => { const id = notice.open!; selectNode(id); }}>開啟</button>}
          {notice?.text === message && notice.undo && lastUndo && <button type="button" disabled={busy || mutating} onClick={() => void undoLast()}>復原</button>}</p>}
        <section aria-label={route.page === 'project' ? '專案' : route.page === 'overview' ? '總覽頁面' : route.page === 'my-tasks' ? '我的任務頁面' : route.page === 'reviews' ? '審核中心頁面' : route.page === 'audit' ? '稽核紀錄頁面' : '模板庫頁面'}>
          {creationOpen && <form ref={creationForm} tabIndex={-1} className="creation-form" aria-label="建立新專案" onSubmit={event => void createProject(event)}>
            <h2>建立新專案</h2>
            {session?.user.role === 'admin' && <div className="creation-modes" role="group" aria-label="建立方式"><button type="button" aria-pressed={creationMode === 'workflow'} disabled={mutating} onClick={() => void openCreation()}>從模板建立</button><button type="button" aria-pressed={creationMode === 'blank'} disabled={mutating} onClick={() => { setCreationMode('blank'); setMessage(''); }}>空白專案</button></div>}
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
          {state === 'ready' && !creationOpen && route.page === 'operations' && !operationsPreview && <OperationsManager key={session.organization.id} expired={expireSession} leaveGuard={documentLeaveGuard} preview={() => setOperationsPreview(true)} />}
          {state === 'ready' && route.page === 'operations' && operationsPreview && <PreviewBoundary initialPage="operations" companyKey={session.organization.key} food={session.organization.key === 'food'} companyName={session.organization.name} exit={() => setOperationsPreview(false)} />}
          {state === 'ready' && route.page === 'governance' && <AIGovernance key={session.organization.id} expired={expireSession} fallback={<PreviewBoundary initialPage="governance" companyKey={session.organization.key} food={session.organization.key === 'food'} companyName={session.organization.name} exit={() => navigate({ page: 'overview' })} />} />}
          {state === 'ready' && route.page === 'overview' && <WorkspaceOverview showAssignHint={canCreate} openProject={id => navigate({ page: 'project', projectId: id, nodeId: null })} expired={expireSession} />}
          {state === 'ready' && !busy && !creationOpen && route.page === 'workflows' && <WorkflowLibrary expired={expireSession} changed={() => setWorkflows(null)} createProject={canCreate ? id => void openCreation(id) : undefined} />}
          {state === 'ready' && !busy && !creationOpen && route.page === 'reviews' && <ReviewCenter openNode={(projectId, nodeId) => navigate({page:'project', projectId, nodeId})} expired={expireSession} />}
          {state === 'ready' && !busy && !creationOpen && route.page === 'audit' && <AuditLogView openNode={(projectId, nodeId) => navigate({page:'project', projectId, nodeId})} expired={expireSession} />}
          {state === 'ready' && route.page === 'my-tasks' && <MyTasks userName={session.user.display_name} openNode={(projectId, nodeId) => navigate({ page: 'project', projectId, nodeId })} expired={expireSession} />}
          {state==='ready'&&route.page==='project'&&project&&templateDialog&&<TemplateDialogs key={`${project.id}:${selectedNodeId}:${templateDialog}`} mode={templateDialog}
            target={selectedNode&&selectedNode.kind!=='project'?`/nodes/${selectedNode.id}`:`/projects/${project.id}`} title={selectedNode?.title??project.title} projectTarget={!selectedNode||selectedNode.kind==='project'}
            close={()=>setTemplateDialog(null)} expired={expireSession} saved={()=>{setWorkflows(null);setMessage('已儲存模板，可至模板庫查看版本');}}
            applied={async (result,signal)=>{setLastUndo({id:result.undo_id,label:'套用模板'});await reloadRecords(signal);if(signal.aborted)return;announce(`已套用模板，新增 ${result.created_count} 個節點`,true);}}/>}
          {state === 'ready' && route.page === 'project' && project && <NodeWorkspace key={project.id} project={project} selectedNodeId={selectedNodeId} select={(id, preserveTab) => selectNode(id, preserveTab ? projectView : undefined)}
            userId={session.user.id} userName={session.user.display_name} roleLabel={ROLE_LABELS[session.user.role] ?? session.user.role}
            reloadRecords={reloadRecords} expired={expireSession} recordVersion={recordVersion} recordsEnabled={!busy && !editor && !creationOpen}
            readonly={session.user.role === 'readonly'} canApprove={!!canApprove} disabled={busy || mutating || creationOpen || !!editor} mutate={(action, id, status) => void mutate(action, id, status)}
            move={(id, parentId) => void moveNode(id, parentId)} openReport={openReport} reportIntent={reportIntent} notify={setMessage}
            color={projectColor(Math.max(0, projects.findIndex(item => item.id === project.id)))}
            preview={projectView === 'documents' ? <DocumentManager key={`${session.organization.id}:${selectedNodeId ?? project.id}`} scopePath={selectedNodeId && selectedNode?.kind !== 'project' ? `/nodes/${selectedNodeId}` : `/projects/${project.id}`} expired={expireSession} leaveGuard={documentLeaveGuard} /> : projectView === 'data' && <LinkedOperations key={`${session.organization.id}:${selectedNodeId ?? project.id}`} scopePath={selectedNodeId && selectedNode?.kind !== 'project' ? `/nodes/${selectedNodeId}` : `/projects/${project.id}`} expired={expireSession} leaveGuard={documentLeaveGuard} preview={<PreviewBoundary key={selectedNodeId ?? 'project-preview'} initialPage="data" companyKey={session.organization.key} food={session.organization.key === 'food'} companyName={session.organization.name} exit={() => setProjectView(defaultTab(project.nodes, selectedNodeId))} />} />}
            tab={projectView} tabsDisabled={busy || mutating} changeTab={view => { if (!canLeaveDocument()) return; begin(); closeCreation(); setProjectView(view); }}
            actions={canEditNode && <button disabled={busy || mutating || creationOpen} onClick={() => openNodeEditor('edit')}>編輯節點</button>}
            editor={editor && <NodeEditor key={`${project.id}:${selectedNodeId}:${editor}:${editorGeneration}`} projectId={project.id} mode={editor} node={editor === 'edit' ? selectedNode : null} parent={selectedNode}
              canAssign={editor === 'create' || !!selectedNode?.capabilities?.assign} leaf={isLeafTask(project.nodes, selectedNode)} reload={reloadNode} close={() => setEditor(null)} expired={expireSession}
              nodes={project.nodes} created={nodeCreated} tree={selectedNode ? { move: parentId => void moveNode(selectedNode.id, parentId), copy: () => void structure('copy', selectedNode.id), remove: () => void structure('delete', selectedNode.id) } : undefined} />}
            timeline={!busy && !creationOpen && <TimelineView key={project.id} recordVersion={recordVersion} project={project} scopeId={selectedNodeId} created={nodeCreated} notice={setMessage} color={projectColor(Math.max(0, projects.findIndex(item => item.id === project.id)))} select={id => selectNode(id, 'timeline')} up={id => selectNode(id, 'timeline')} reload={reloadRecords} expired={expireSession}
              undo={session.user.role === 'readonly' ? undefined : { label: lastUndo?.label ?? null, disabled: busy || mutating, run: () => void undoLast() }} />}
            graph={!busy && !creationOpen && <DependencyPanel key={`${project.id}:${recordVersion}`} projectId={project.id} project={project} scopeId={selectedNodeId} select={id => selectNode(id, 'graph')} reload={reloadRecords} expired={expireSession} />} />}
          {state === 'error' && <button disabled={busy} onClick={retry}>重試</button>}
        </section>
        </WorkspaceShell> : <section>{state === 'checking-session' && <p role="status">確認登入狀態中</p>}{state === 'error' && <button onClick={retry}>重試</button>}</section>}
      </>}
    </main>
  </>;
}
