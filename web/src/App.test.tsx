import { createProjectButton, findCreateProjectButton, findLogoutButton, findProjectMenu, logoutButton, projectMenu } from './test-navigation';
import { beforeEach as beforeTpF } from 'vitest';
import { api as tpFApi } from './api';
beforeTpF(()=>{
 vi.spyOn(tpFApi,'notifications').mockResolvedValue({items:[],unread_count:0,next_offset:null});
 vi.spyOn(tpFApi,'departments').mockResolvedValue({items:[],users:[],capabilities:{manage:false}});
 vi.spyOn(tpFApi,'collaborationRequests').mockResolvedValue({items:[]});
});
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import App from './App';
import { api } from './api';

const session = { user: { id: 'u1', username: 'yu', display_name: '游專案', role: 'admin' }, organization: { id: 'o1', key: 'food', name: '毛研食品' } };
const projects = { items: [{ id: 'p1', title: '成貓主食罐正式版', organization_key: 'food', owner_user_id: 'u1' }] };
function stubFetch(fetcher: (path: string, init?: RequestInit) => unknown) {
  vi.stubGlobal('fetch', (path: string, init?: RequestInit) => path.includes('/records?') ? Promise.resolve(response({ items: [], next_cursor: null }))
    : path.endsWith('/collaborators') ? Promise.resolve(response({ users: [], departments: [], revision: 0 }))
    : path.endsWith('/attachment-quota') ? Promise.resolve(response({ limit_bytes: 1000000000, charged_bytes: 0, remaining_bytes: 1000000000 })) : path === '/api/workspace/overview'
    ? Promise.resolve(response({ project_count: 0, task_counts: { todo: 0, doing: 0, review: 0, done: 0, skipped: 0 }, completion_percent: null, projects: [] }))
    : path.startsWith('/api/workspace/my-tasks') ? Promise.resolve(response({ items: [] })) : fetcher(path, init));
}
const response = (body: unknown, status = 200) => ({ ok: status < 400, status, json: async () => body });
const detail = { ...projects.items[0], nodes: [
  { id: 'root', project_id: 'p1', parent_id: null, kind: 'project', title: '成貓主食罐正式版', status: 'todo', owner_user_id: 'u1', department_id: null, sort_order: 0 },
  { id: 'phase', project_id: 'p1', parent_id: 'root', kind: 'phase', title: '市場與配方', status: 'todo', owner_user_id: null, department_id: null, sort_order: 10 },
  { id: 'later', project_id: 'p1', parent_id: 'phase', kind: 'task', title: '後續任務', status: 'todo', owner_user_id: null, department_id: null, sort_order: 30, state_actions: ['todo', 'doing'] },
  { id: 'task', project_id: 'p1', parent_id: 'phase', kind: 'task', title: '殺菌條件驗證', status: 'todo', owner_user_id: 'u1', department_id: null, sort_order: 20, state_actions: ['todo', 'doing'] },
], gates: [] };
const secondProject = { ...projects.items[0], id: 'p2', title: '第二專案' };
const secondDetail = { ...secondProject, nodes: [], gates: [] };
function projectButton(title = projects.items[0].title) {
  return within(projectMenu()).getByRole('button', { name: title });
}

const taskNode = detail.nodes.find(node => node.id === 'task')!;
const pendingGate = { id: 'g1', project_id: 'p1', node_id: 'phase', status: 'pending' };
const gateDetail = { ...detail, gates: [pendingGate] };
const workflowList = { items: [{ id: 'w1', name: '食品新品開發' }] };
async function openWorkspace() {
  await screen.findByRole('heading', { name: '所有專案總覽' });
  fireEvent.click(projectButton());
}
// UI4: the main-area node tree is gone; phases are entered from the project-level phase strip.
function selectPhase() {
  fireEvent.click(within(screen.getByLabelText('開發階段與閘門')).getByRole('button', { name: '進入階段：市場與配方' }));
}
function boardButton(name: string) {
  return within(screen.getByLabelText('看板')).getByRole('button', { name });
}
function crumbs() {
  return screen.getByLabelText('節點路徑');
}
async function fillCreation() {
  await screen.findByRole('heading', { name: detail.title });
  fireEvent.click(await findCreateProjectButton());
  await screen.findByRole('option', { name: '食品新品開發' });
  fireEvent.change(screen.getByLabelText('工作流模板'), { target: { value: 'w1' } });
  fireEvent.change(screen.getByLabelText('新專案名稱'), { target: { value: secondProject.title } });
}

describe('P1b workflow creation', () => {
  it('creates via workflow using only workflow/title and selects the new project', async () => {
    const fetcher = kanbanFetch().mockResolvedValueOnce(response(workflowList)).mockResolvedValueOnce(response(secondProject, 201))
      .mockResolvedValueOnce(response({ items: [...projects.items, secondProject] })).mockResolvedValueOnce(response(secondDetail));
    stubFetch(fetcher);
    render(<App />);
    await openWorkspace();
    await fillCreation();
    fireEvent.click(screen.getByRole('button', { name: '建立專案' }));
    expect(await screen.findByRole('heading', { name: secondProject.title })).toBeInTheDocument();
    expect(fetcher).toHaveBeenNthCalledWith(5, '/api/projects/from-workflow', expect.objectContaining({ credentials: 'include', method: 'POST', body: JSON.stringify({ workflow_id: 'w1', title: secondProject.title }) }));
    expect(projectButton(secondProject.title)).toHaveAttribute('aria-pressed', 'true');
    expect(screen.queryByLabelText('新專案名稱')).not.toBeInTheDocument();
  });

  it('requires both fields, cancels cleanly and caches templates', async () => {
    const fetcher = kanbanFetch().mockResolvedValueOnce(response(workflowList));
    stubFetch(fetcher);
    render(<App />);
    await openWorkspace();
    fireEvent.click(await findCreateProjectButton());
    await screen.findByRole('option', { name: '食品新品開發' });
    expect(screen.getByRole('button', { name: '建立專案' })).toBeDisabled();
    fireEvent.change(screen.getByLabelText('工作流模板'), { target: { value: 'w1' } });
    fireEvent.change(screen.getByLabelText('新專案名稱'), { target: { value: '   ' } });
    expect(screen.getByRole('button', { name: '建立專案' })).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: '取消' }));
    expect(screen.queryByLabelText('新專案名稱')).not.toBeInTheDocument();
    fireEvent.click(createProjectButton());
    expect(screen.getByLabelText('新專案名稱')).toHaveValue('');
    expect(fetcher.mock.calls.filter(([path]) => path === '/api/workflows')).toHaveLength(1);
  });

  it.each([403, 404, 500])('maps creation errors safely and permits retry (%s)', async status => {
    const fetcher = kanbanFetch().mockResolvedValueOnce(response(workflowList)).mockResolvedValueOnce(response({ detail: 'private-secret' }, status))
      .mockResolvedValueOnce(response(secondProject, 201)).mockResolvedValueOnce(response({ items: [...projects.items, secondProject] })).mockResolvedValueOnce(response(secondDetail));
    stubFetch(fetcher);
    render(<App />);
    await openWorkspace();
    await fillCreation();
    fireEvent.click(screen.getByRole('button', { name: '建立專案' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(status === 403 ? '沒有建立專案權限' : status === 404 ? '找不到工作流模板' : '操作失敗，請稍後再試');
    expect(document.body).not.toHaveTextContent('private-secret');
    expect(screen.getByLabelText('新專案名稱')).toHaveValue(secondProject.title);
    fireEvent.click(screen.getByRole('button', { name: '建立專案' }));
    expect(await screen.findByRole('heading', { name: secondProject.title })).toBeInTheDocument();
  });

  it('retries template loading after failure', async () => {
    stubFetch(kanbanFetch().mockRejectedValueOnce(new Error('private-secret')).mockResolvedValueOnce(response(workflowList)));
    render(<App />);
    await openWorkspace();
    fireEvent.click(await findCreateProjectButton());
    expect(await screen.findByRole('alert')).toHaveTextContent('無法連線，請稍後再試');
    fireEvent.click(screen.getByRole('button', { name: '重試模板' }));
    expect(await screen.findByRole('option', { name: '食品新品開發' })).toBeInTheDocument();
  });

  it('disables duplicate creation submissions', async () => {
    let resolveCreate!: (value: ReturnType<typeof response>) => void;
    const fetcher = kanbanFetch().mockResolvedValueOnce(response(workflowList)).mockImplementationOnce(() => new Promise(resolve => { resolveCreate = resolve; }))
      .mockResolvedValueOnce(response({ items: [...projects.items, secondProject] })).mockResolvedValueOnce(response(secondDetail));
    stubFetch(fetcher);
    render(<App />);
    await openWorkspace();
    await fillCreation();
    const button = screen.getByRole('button', { name: '建立專案' });
    fireEvent.click(button); fireEvent.click(button);
    expect(button).toBeDisabled();
    expect(fetcher.mock.calls.filter(([path]) => path === '/api/projects/from-workflow')).toHaveLength(1);
    await act(async () => { resolveCreate(response(secondProject, 201)); });
    expect(await screen.findByRole('heading', { name: secondProject.title })).toBeInTheDocument();
  });

  it('hides creation from readonly', async () => {
    stubFetch(kanbanFetch(gateDetail, { ...session, user: { ...session.user, role: 'readonly' } }));
    render(<App />);
    await openWorkspace();
    await screen.findByRole('heading', { name: detail.title });
    selectPhase();
    expect(screen.queryByRole('button', { name: '建立新專案' })).not.toBeInTheDocument();
  });

  it.each(['templates', 'create'])('ignores old %s response after logout', async stage => {
    let resolveOld!: (value: ReturnType<typeof response>) => void;
    const fetcher = kanbanFetch();
    if (stage === 'create') fetcher.mockResolvedValueOnce(response(workflowList));
    fetcher.mockImplementationOnce(() => new Promise(resolve => { resolveOld = resolve; })).mockResolvedValueOnce(response(undefined, 204));
    stubFetch(fetcher);
    render(<App />);
    await openWorkspace();
    if (stage === 'create') { await fillCreation(); fireEvent.click(screen.getByRole('button', { name: '建立專案' })); }
    else fireEvent.click(await findCreateProjectButton());
    fireEvent.click(logoutButton());
    await screen.findByRole('heading', { name: '登入專流' });
    await act(async () => { resolveOld(response(stage === 'create' ? secondProject : workflowList)); });
    expect(screen.getByRole('heading', { name: '登入專流' })).toBeInTheDocument();
    expect(screen.queryByLabelText('新專案名稱')).not.toBeInTheDocument();
  });
});
function statusControl(column = '待處理') {
  return within(screen.getByLabelText(column)).getByRole('combobox', { name: '殺菌條件驗證狀態' });
}
function kanbanFetch(value = gateDetail, identity = session) {
  return vi.fn().mockResolvedValueOnce(response(identity)).mockResolvedValueOnce(response(projects)).mockResolvedValueOnce(response(value));
}

it('renders an owned task with hidden parent as a selectable root and kanban item', async () => {
  stubFetch(kanbanFetch({ ...detail, nodes: [taskNode], gates: [] },
    { ...session, user: { ...session.user, role: 'member' } }));
  render(<App />);
  await openWorkspace();
  await screen.findByRole('heading', { name: detail.title });
  // The orphaned task is promoted to the project-level board as its only selectable card.
  const board = within(screen.getByLabelText('看板'));
  expect(board.getAllByRole('button')).toHaveLength(1);
  expect(board.getByRole('combobox', { name: `${taskNode.title}狀態` })).toBeInTheDocument();
  expect(screen.queryByLabelText('開發階段與閘門')).not.toBeInTheDocument();
  fireEvent.click(board.getByRole('button', { name: taskNode.title }));
  expect(crumbs()).toHaveTextContent(taskNode.title);
  expect(crumbs()).not.toHaveTextContent('市場與配方');
  expect(within(screen.getByLabelText('節點詳情')).getByRole('combobox', { name: `${taskNode.title}狀態` })).toBeInTheDocument();
  // A leaf task opens on its records; its own board has no next level and therefore no controls.
  expect(screen.getByRole('tab', { name: '紀錄' })).toHaveAttribute('aria-selected', 'true');
  fireEvent.click(screen.getByRole('tab', { name: '看板' }));
  expect(within(screen.getByLabelText('看板')).queryByRole('combobox')).not.toBeInTheDocument();
  expect(screen.getByLabelText('看板')).toHaveTextContent('目前沒有下一層節點');
});

describe('P1b kanban and gates', () => {
  it('renders four task-only columns and moves a task after status selection', async () => {
    const fetcher = kanbanFetch().mockResolvedValueOnce(response({ ...taskNode, status: 'doing' }));
    stubFetch(fetcher);
    render(<App />);
    await openWorkspace();
    await screen.findByRole('heading', { name: detail.title });
    selectPhase();
    for (const label of ['待處理', '進行中', '待確認', '完成']) expect(screen.getByLabelText(label)).toBeInTheDocument();
    expect(within(screen.getByLabelText('看板')).queryByText('市場與配方')).not.toBeInTheDocument();
    fireEvent.change(statusControl(), { target: { value: 'doing' } });
    await waitFor(() => expect(statusControl('進行中')).toHaveValue('doing'));
    expect(within(screen.getByLabelText('待處理')).queryByText(taskNode.title)).not.toBeInTheDocument();
    expect(fetcher).toHaveBeenLastCalledWith('/api/nodes/task/status', expect.objectContaining({ method: 'PATCH', credentials: 'include', body: JSON.stringify({ status: 'doing' }) }));
  });

  it.each([409, 403, 500])('keeps old status and maps mutation errors safely (%s)', async status => {
    stubFetch(kanbanFetch().mockResolvedValueOnce(response({ detail: 'private-secret' }, status)));
    render(<App />);
    await openWorkspace();
    await screen.findByRole('heading', { name: detail.title });
    selectPhase();
    fireEvent.change(statusControl(), { target: { value: 'doing' } });
    expect(await screen.findByRole('alert')).toHaveTextContent(status === 409 ? '目前狀態不允許此操作，請檢查閘門與前置任務' : status === 403 ? '沒有操作此節點的權限' : '操作失敗，請稍後再試');
    expect(statusControl()).toHaveValue('todo');
    expect(statusControl()).not.toBeDisabled();
    expect(document.body).not.toHaveTextContent('private-secret');
  });

  it('disables duplicate mutations while pending', async () => {
    let resolveMove!: (value: ReturnType<typeof response>) => void;
    const fetcher = kanbanFetch().mockImplementationOnce(() => new Promise(resolve => { resolveMove = resolve; }));
    stubFetch(fetcher);
    render(<App />);
    await openWorkspace();
    await screen.findByRole('heading', { name: detail.title });
    selectPhase();
    const control = statusControl();
    fireEvent.change(control, { target: { value: 'doing' } });
    expect(control).toBeDisabled();
    expect(screen.getByRole('button', { name: '核准閘門' })).toBeDisabled();
    fireEvent.change(control, { target: { value: 'review' } });
    expect(fetcher.mock.calls.filter(([path]) => path === '/api/nodes/task/status')).toHaveLength(1);
    await act(async () => { resolveMove(response({ ...taskNode, status: 'doing' })); });
    expect(statusControl('進行中')).not.toBeDisabled();
  });

  it('shows pending gate warning and reloads after approval', async () => {
    const approved = { ...pendingGate, status: 'approved' };
    const fetcher = kanbanFetch().mockResolvedValueOnce(response(approved)).mockResolvedValueOnce(response({ ...detail, gates: [approved] }));
    stubFetch(fetcher);
    render(<App />);
    await openWorkspace();
    await screen.findByRole('heading', { name: detail.title });
    // UI4: gates are approved on their phase page, not from a banner repeated on every level.
    expect(screen.queryByRole('button', { name: '核准閘門' })).not.toBeInTheDocument();
    selectPhase();
    const gate = within(screen.getByLabelText('階段閘門'));
    expect(gate.getByText('尚有階段閘門待核准，後續階段可能被阻擋')).toBeInTheDocument();
    expect(gate.getByText('待核准')).toBeInTheDocument();
    fireEvent.click(gate.getByRole('button', { name: '核准閘門' }));
    await waitFor(() => expect(screen.queryByText('尚有階段閘門待核准，後續階段可能被阻擋')).not.toBeInTheDocument());
    expect(within(screen.getByLabelText('階段閘門')).getByText('✓ 已核准')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '核准閘門' })).not.toBeInTheDocument();
    expect(fetcher).toHaveBeenNthCalledWith(4, '/api/gates/g1', expect.objectContaining({ method: 'PATCH', credentials: 'include', body: JSON.stringify({ status: 'approved' }) }));
    expect(fetcher).toHaveBeenLastCalledWith('/api/projects/p1', expect.objectContaining({ credentials: 'include' }));
  });

  it('maps approval denial safely and permits retry without changing pending gate', async () => {
    const fetcher = kanbanFetch().mockResolvedValueOnce(response({ detail: 'private-secret' }, 403)).mockResolvedValueOnce(response({ ...pendingGate, status: 'approved' })).mockResolvedValueOnce(response(detail));
    stubFetch(fetcher);
    render(<App />);
    await openWorkspace();
    fireEvent.click(await screen.findByRole('button', { name: '進入階段：市場與配方' }));
    fireEvent.click(screen.getByRole('button', { name: '核准閘門' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('沒有核准此閘門的權限');
    expect(document.body).not.toHaveTextContent('private-secret');
    expect(screen.getByText('尚有階段閘門待核准，後續階段可能被阻擋')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '核准閘門' }));
    await waitFor(() => expect(screen.queryByRole('button', { name: '核准閘門' })).not.toBeInTheDocument());
  });

  it.each([
    ['readonly', 'u1', false, false], ['member', 'u1', true, true],
    ['member', 'other', true, false], ['reviewer', 'other', true, true], ['admin', 'other', true, true],
  ] as const)('shows controls for role %s owner %s without replacing API authorization', async (role, owner, taskControl, gateControl) => {
    stubFetch(kanbanFetch({ ...gateDetail, owner_user_id: owner }, { ...session, user: { ...session.user, role } }));
    render(<App />);
    await openWorkspace();
    await screen.findByRole('heading', { name: detail.title });
    selectPhase();
    expect(within(screen.getByLabelText('看板')).queryByRole('combobox', { name: '殺菌條件驗證狀態' }) !== null).toBe(taskControl);
    expect(screen.queryByRole('button', { name: '核准閘門' }) !== null).toBe(gateControl);
    expect(screen.getByText('尚有階段閘門待核准，後續階段可能被阻擋')).toBeInTheDocument();
  });

  it.each([200, 401, 500])('ignores stale status mutation after project switch (%s)', async status => {
    let resolveMove!: (value: ReturnType<typeof response>) => void;
    const fetcher = vi.fn().mockResolvedValueOnce(response(session)).mockResolvedValueOnce(response({ items: [...projects.items, secondProject] })).mockResolvedValueOnce(response(gateDetail))
      .mockImplementationOnce(() => new Promise(resolve => { resolveMove = resolve; })).mockResolvedValueOnce(response(secondDetail));
    stubFetch(fetcher);
    render(<App />);
    await openWorkspace();
    await screen.findByRole('heading', { name: detail.title });
    selectPhase();
    fireEvent.change(statusControl(), { target: { value: 'doing' } });
    fireEvent.click(projectButton(secondProject.title));
    await screen.findByRole('heading', { name: secondProject.title });
    await act(async () => { resolveMove(response(status === 200 ? { ...taskNode, status: 'doing' } : {}, status)); });
    expect(screen.getByRole('heading', { name: secondProject.title })).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(within(screen.getByLabelText('看板')).queryByText(taskNode.title)).not.toBeInTheDocument();
  });

  it('ignores old approval after project switch without reloading old project', async () => {
    let resolveGate!: (value: ReturnType<typeof response>) => void;
    const fetcher = vi.fn().mockResolvedValueOnce(response(session)).mockResolvedValueOnce(response({ items: [...projects.items, secondProject] })).mockResolvedValueOnce(response(gateDetail))
      .mockImplementationOnce(() => new Promise(resolve => { resolveGate = resolve; })).mockResolvedValueOnce(response(secondDetail));
    stubFetch(fetcher);
    render(<App />);
    await openWorkspace();
    fireEvent.click(await screen.findByRole('button', { name: '進入階段：市場與配方' }));
    fireEvent.click(screen.getByRole('button', { name: '核准閘門' }));
    fireEvent.click(projectButton(secondProject.title));
    await screen.findByRole('heading', { name: secondProject.title });
    await act(async () => { resolveGate(response({ ...pendingGate, status: 'approved' })); });
    expect(screen.getByRole('heading', { name: secondProject.title })).toBeInTheDocument();
    expect(fetcher.mock.calls.filter(([path]) => path === '/api/projects/p1')).toHaveLength(1);
  });

  it('clears session on mutation expiry', async () => {
    stubFetch(kanbanFetch().mockResolvedValueOnce(response({}, 401)));
    render(<App />);
    await openWorkspace();
    await screen.findByRole('heading', { name: detail.title });
    selectPhase();
    fireEvent.change(statusControl(), { target: { value: 'doing' } });
    expect(await screen.findByRole('heading', { name: '登入專流' })).toBeInTheDocument();
    expect(screen.queryByLabelText('看板')).not.toBeInTheDocument();
  });

  it('ignores a late mutation after logout', async () => {
    let resolveMove!: (value: ReturnType<typeof response>) => void;
    const fetcher = kanbanFetch().mockImplementationOnce(() => new Promise(resolve => { resolveMove = resolve; })).mockResolvedValueOnce(response(undefined, 204));
    stubFetch(fetcher);
    render(<App />);
    await openWorkspace();
    await screen.findByRole('heading', { name: detail.title });
    selectPhase();
    fireEvent.change(statusControl(), { target: { value: 'doing' } });
    fireEvent.click(logoutButton());
    await screen.findByRole('heading', { name: '登入專流' });
    await act(async () => { resolveMove(response({ ...taskNode, status: 'doing' })); });
    expect(screen.getByRole('heading', { name: '登入專流' })).toBeInTheDocument();
    expect(screen.queryByLabelText('看板')).not.toBeInTheDocument();
  });
});

describe('P1b project navigation', () => {
  it('loads detail, orders the board and selects a leaf with full breadcrumbs', async () => {
    stubFetch(vi.fn().mockResolvedValueOnce(response(session)).mockResolvedValueOnce(response(projects)).mockResolvedValueOnce(response(detail)));
    render(<App />);
    await openWorkspace();
    expect(await screen.findByRole('heading', { name: detail.title })).toBeInTheDocument();
    expect(crumbs()).toHaveTextContent(detail.title);
    // The project-kind root is not a card; its phase is the top level and its tasks are flattened in sort order.
    const cardTitles = () => within(screen.getByLabelText('看板')).getAllByRole('button').map(button => button.textContent);
    expect(within(screen.getByLabelText('開發階段與閘門')).getAllByRole('button').map(button => button.getAttribute('aria-label'))).toEqual(['進入階段：市場與配方']);
    expect(cardTitles()).toEqual(['殺菌條件驗證', '後續任務']);
    expect(within(screen.getByLabelText('待處理')).getAllByText('市場與配方')).toHaveLength(2);
    selectPhase();
    expect(crumbs()).toHaveTextContent('成貓主食罐正式版 / 成貓主食罐正式版 / 市場與配方');
    expect(cardTitles()).toEqual(['殺菌條件驗證', '後續任務']);
    fireEvent.click(boardButton('殺菌條件驗證'));
    expect(crumbs()).toHaveTextContent('成貓主食罐正式版 / 成貓主食罐正式版 / 市場與配方 / 殺菌條件驗證');
    expect(within(crumbs()).getByRole('button', { name: '殺菌條件驗證' })).toHaveAttribute('aria-current', 'location');
    expect(screen.getByRole('heading', { level: 1, name: '殺菌條件驗證' })).toBeInTheDocument();
    fireEvent.click(within(crumbs()).getByRole('button', { name: '市場與配方' }));
    expect(crumbs()).toHaveTextContent('成貓主食罐正式版 / 成貓主食罐正式版 / 市場與配方');
    expect(crumbs()).not.toHaveTextContent('殺菌條件驗證');
    expect(within(crumbs()).getByRole('button', { name: '市場與配方' })).toHaveAttribute('aria-current', 'location');
  });

  it('switches project and resets node selection, including empty trees', async () => {
    const fetcher = vi.fn().mockResolvedValueOnce(response(session)).mockResolvedValueOnce(response({ items: [...projects.items, secondProject] })).mockResolvedValueOnce(response(detail)).mockResolvedValueOnce(response(secondDetail));
    stubFetch(fetcher);
    render(<App />);
    await openWorkspace();
    await screen.findByRole('heading', { name: detail.title });
    selectPhase();
    fireEvent.click(boardButton('殺菌條件驗證'));
    expect(screen.getByRole('heading', { level: 1, name: '殺菌條件驗證' })).toBeInTheDocument();
    fireEvent.click(projectButton(secondProject.title));
    expect(await screen.findByRole('heading', { name: secondProject.title })).toBeInTheDocument();
    expect(crumbs()).toHaveTextContent(secondProject.title);
    expect(crumbs()).not.toHaveTextContent('市場與配方');
    expect(screen.getByRole('tab', { name: '看板' })).toHaveAttribute('aria-selected', 'true');
    expect(within(screen.getByLabelText('看板')).getByText('這個專案還沒有節點。按「新增子節點」開始拆解。')).toBeInTheDocument();
    expect(projectButton(secondProject.title)).toHaveAttribute('aria-pressed', 'true');
    expect(screen.queryByText('殺菌條件驗證')).not.toBeInTheDocument();
    expect(fetcher).toHaveBeenLastCalledWith('/api/projects/p2', expect.objectContaining({ credentials: 'include' }));
  });

  it.each(['500', 'network'])('keeps session and retries selected detail after %s', async failure => {
    const fetcher = vi.fn().mockResolvedValueOnce(response(session)).mockResolvedValueOnce(response(projects));
    if (failure === '500') fetcher.mockResolvedValueOnce(response({ detail: 'private-secret' }, 500));
    else fetcher.mockRejectedValueOnce(new Error('private-secret'));
    fetcher.mockResolvedValueOnce(response(detail));
    stubFetch(fetcher);
    render(<App />);
    await openWorkspace();
    expect(await screen.findByRole('alert')).toHaveTextContent('無法載入專案資料');
    expect(screen.getByLabelText('目前公司')).toHaveTextContent('毛研食品');
    expect(document.body).not.toHaveTextContent('private-secret');
    fireEvent.click(screen.getByRole('button', { name: '重試' }));
    expect(await screen.findByRole('heading', { name: detail.title })).toBeInTheDocument();
    expect(fetcher).toHaveBeenLastCalledWith('/api/projects/p1', expect.objectContaining({ credentials: 'include' }));
  });

  it('clears session on detail expiry', async () => {
    stubFetch(vi.fn().mockResolvedValueOnce(response(session)).mockResolvedValueOnce(response(projects)).mockResolvedValueOnce(response({}, 401)));
    render(<App />);
    await openWorkspace();
    expect(await screen.findByRole('heading', { name: '登入專流' })).toBeInTheDocument();
    expect(screen.queryByLabelText('專案清單')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('目前公司')).not.toBeInTheDocument();
  });

  it.each([200, 401, 500])('ignores stale detail responses after selecting another project (%s)', async status => {
    let resolveDetail!: (value: ReturnType<typeof response>) => void;
    const fetcher = vi.fn().mockResolvedValueOnce(response(session)).mockResolvedValueOnce(response({ items: [...projects.items, secondProject] }))
      .mockImplementationOnce(() => new Promise(resolve => { resolveDetail = resolve; })).mockResolvedValueOnce(response(secondDetail));
    stubFetch(fetcher);
    render(<App />);
    await openWorkspace();
    fireEvent.click(projectButton(secondProject.title));
    expect(await screen.findByRole('heading', { name: secondProject.title })).toBeInTheDocument();
    expect(fetcher.mock.calls[2][1].signal.aborted).toBe(true);
    await act(async () => { resolveDetail(response(status === 200 ? detail : {}, status)); });
    expect(screen.getByRole('heading', { name: secondProject.title })).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: '登入專流' })).not.toBeInTheDocument();
  });

  it('ignores late detail after logout', async () => {
    let resolveDetail!: (value: ReturnType<typeof response>) => void;
    const fetcher = vi.fn().mockResolvedValueOnce(response(session)).mockResolvedValueOnce(response(projects))
      .mockImplementationOnce(() => new Promise(resolve => { resolveDetail = resolve; })).mockResolvedValueOnce(response(undefined, 204));
    stubFetch(fetcher);
    render(<App />);
    await openWorkspace();
    await findProjectMenu();
    fireEvent.click(logoutButton());
    expect(await screen.findByRole('heading', { name: '登入專流' })).toBeInTheDocument();
    await act(async () => { resolveDetail(response(detail)); });
    expect(screen.queryByLabelText('節點詳情')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('看板')).not.toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '登入專流' })).toBeInTheDocument();
  });
});
async function login() {
  fireEvent.change(await screen.findByLabelText('帳號'), { target: { value: 'yu' } });
  fireEvent.change(screen.getByLabelText('密碼'), { target: { value: 'demo-yu' } });
  fireEvent.click(screen.getByRole('button', { name: '登入' }));
}

describe('P1b typed API client', () => {
  it('loads project detail using cookies without organization context', async () => {
    const detail = { ...projects.items[0], nodes: [], gates: [] };
    const fetcher = vi.fn().mockResolvedValue(response(detail));
    stubFetch(fetcher);
    const signal = new AbortController().signal;
    expect(await api.project('p1', signal)).toEqual(detail);
    expect(fetcher).toHaveBeenCalledWith('/api/projects/p1', expect.objectContaining({ credentials: 'include', signal }));
    expect(fetcher.mock.calls[0][1].body).toBeUndefined();
  });

  it('updates node status with only the status payload', async () => {
    const node = { id: 'n1', status: 'doing' };
    const fetcher = vi.fn().mockResolvedValue(response(node));
    stubFetch(fetcher);
    const signal = new AbortController().signal;
    expect(await api.updateNodeStatus('n1', 'doing', signal)).toEqual(node);
    expect(fetcher).toHaveBeenCalledWith('/api/nodes/n1/status', expect.objectContaining({ method: 'PATCH', credentials: 'include', signal }));
    expect(JSON.parse(fetcher.mock.calls[0][1].body)).toEqual({ status: 'doing' });
  });

  it('loads workflow templates using cookies without organization context', async () => {
    const workflows = { items: [{ id: 'w1', name: '食品新品開發' }] };
    const fetcher = vi.fn().mockResolvedValue(response(workflows));
    stubFetch(fetcher);
    const signal = new AbortController().signal;
    expect(await api.workflows(signal)).toEqual(workflows);
    expect(fetcher).toHaveBeenCalledWith('/api/workflows', expect.objectContaining({ credentials: 'include', signal }));
    expect(fetcher.mock.calls[0][1].body).toBeUndefined();
  });

  it('creates a project with only workflow and title payload', async () => {
    const fetcher = vi.fn().mockResolvedValue(response(projects.items[0], 201));
    stubFetch(fetcher);
    const payload = { workflow_id: 'w1', title: '成貓主食罐正式版' };
    const signal = new AbortController().signal;
    expect(await api.createFromWorkflow(payload, signal)).toEqual(projects.items[0]);
    expect(fetcher).toHaveBeenCalledWith('/api/projects/from-workflow', expect.objectContaining({ method: 'POST', credentials: 'include', signal }));
    expect(JSON.parse(fetcher.mock.calls[0][1].body)).toEqual(payload);
  });

  it('approves a gate with only approved status payload', async () => {
    const gate = { id: 'g1', project_id: 'p1', node_id: 'n1', status: 'approved' };
    const fetcher = vi.fn().mockResolvedValue(response(gate));
    stubFetch(fetcher);
    const signal = new AbortController().signal;
    expect(await api.approveGate('g1', signal)).toEqual(gate);
    expect(fetcher).toHaveBeenCalledWith('/api/gates/g1', expect.objectContaining({ method: 'PATCH', credentials: 'include', signal }));
    expect(JSON.parse(fetcher.mock.calls[0][1].body)).toEqual({ status: 'approved' });
  });
});

describe('P1b session UI', () => {
  it('shows login without an active session', async () => {
    stubFetch(vi.fn().mockResolvedValue(response({}, 401)));
    render(<App />);
    expect(await screen.findByRole('heading', { name: '登入專流' })).toBeInTheDocument();
    expect(screen.getByLabelText('公司')).toHaveValue('food');
  });

  it('logs in and loads projects using cookies only', async () => {
    const fetcher = vi.fn().mockResolvedValueOnce(response({}, 401)).mockResolvedValueOnce(response(session)).mockResolvedValueOnce(response(projects)).mockResolvedValueOnce(response(detail));
    stubFetch(fetcher);
    render(<App />);
    await login();
    await openWorkspace();
    expect(await screen.findByRole('heading', { name: detail.title })).toBeInTheDocument();
    expect(fetcher).toHaveBeenCalledWith('/api/auth/login', expect.objectContaining({ credentials: 'include', method: 'POST', body: JSON.stringify({ organization_key: 'food', username: 'yu', password: 'demo-yu' }) }));
    expect(fetcher).toHaveBeenCalledWith('/api/projects', expect.objectContaining({ credentials: 'include' }));
    expect(fetcher.mock.calls[2][1].body).toBeUndefined();
    expect(projectButton()).toHaveAttribute('aria-pressed', 'true');
  });

  it('restores a session and handles an empty project list', async () => {
    stubFetch(vi.fn().mockResolvedValueOnce(response(session)).mockResolvedValueOnce(response({ items: [] })));
    render(<App />);
    expect(await within(await findProjectMenu()).findByText('目前沒有專案')).toBeInTheDocument();
    expect(screen.getByLabelText('目前公司')).toHaveTextContent('毛研食品');
  });

  it.each([401, 422, 500])('maps login errors safely (%s)', async status => {
    stubFetch(vi.fn().mockResolvedValueOnce(response({}, 401)).mockResolvedValueOnce(response({ detail: 'private-secret' }, status)));
    render(<App />);
    await login();
    expect(await screen.findByRole('alert')).toHaveTextContent(status === 401 ? '帳號或密碼錯誤' : '操作失敗，請稍後再試');
    expect(document.body).not.toHaveTextContent('private-secret');
    expect(screen.getByLabelText('密碼')).toHaveValue('');
  });

  it('returns to login on expired project session', async () => {
    stubFetch(vi.fn().mockResolvedValueOnce(response(session)).mockResolvedValueOnce(response({}, 401)));
    render(<App />);
    expect(await screen.findByRole('heading', { name: '登入專流' })).toBeInTheDocument();
    expect(screen.queryByLabelText('目前公司')).not.toBeInTheDocument();
  });

  it.each(['500', 'network'])('keeps the authenticated session and retries failed projects (%s)', async failure => {
    const fetcher = vi.fn().mockResolvedValueOnce(response({}, 401)).mockResolvedValueOnce(response(session));
    if (failure === '500') fetcher.mockResolvedValueOnce(response({ detail: 'private-secret' }, 500));
    else fetcher.mockRejectedValueOnce(new Error('private-secret'));
    fetcher.mockResolvedValueOnce(response(session)).mockResolvedValueOnce(response(projects)).mockResolvedValueOnce(response(detail));
    stubFetch(fetcher);
    render(<App />);
    await login();
    expect(await screen.findByRole('alert')).toHaveTextContent('無法載入專案資料');
    expect(screen.getByLabelText('目前公司')).toHaveTextContent('毛研食品');
    expect(screen.queryByRole('heading', { name: '登入專流' })).not.toBeInTheDocument();
    expect(document.body).not.toHaveTextContent('private-secret');
    fireEvent.click(screen.getByRole('button', { name: '重試' }));
    await openWorkspace();
    expect(await screen.findByRole('heading', { name: detail.title })).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(fetcher.mock.calls.filter(([path]) => path === '/api/auth/login')).toHaveLength(1);
  });

  it('retries after a safe network error', async () => {
    stubFetch(vi.fn().mockRejectedValueOnce(new Error('private-secret')).mockResolvedValueOnce(response(session)).mockResolvedValueOnce(response(projects)).mockResolvedValueOnce(response(detail)));
    render(<App />);
    expect(await screen.findByRole('alert')).toHaveTextContent('無法連線，請稍後再試');
    expect(document.body).not.toHaveTextContent('private-secret');
    fireEvent.click(screen.getByRole('button', { name: '重試' }));
    await openWorkspace();
    expect(await screen.findByRole('heading', { name: detail.title })).toBeInTheDocument();
  });

  it('logs out and ignores late projects even when fetch ignores abort', async () => {
    let resolveProjects!: (value: ReturnType<typeof response>) => void;
    const fetcher = vi.fn().mockResolvedValueOnce(response(session)).mockImplementationOnce(() => new Promise(resolve => { resolveProjects = resolve; })).mockResolvedValueOnce(response(undefined, 204));
    stubFetch(fetcher);
    render(<App />);
    fireEvent.click(await findLogoutButton());
    expect(await screen.findByRole('heading', { name: '登入專流' })).toBeInTheDocument();
    expect(fetcher).toHaveBeenLastCalledWith('/api/auth/logout', expect.objectContaining({ credentials: 'include', method: 'POST' }));
    expect(fetcher.mock.calls[1][1].signal.aborted).toBe(true);
    await act(async () => { resolveProjects(response(projects)); });
    expect(screen.queryByText('成貓主食罐正式版')).not.toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '登入專流' })).toBeInTheDocument();
  });

  it('permits retry when logout fails', async () => {
    stubFetch(vi.fn().mockResolvedValueOnce(response(session)).mockResolvedValueOnce(response(projects)).mockResolvedValueOnce(response(detail)).mockResolvedValueOnce(response({ detail: 'private-secret' }, 500)).mockResolvedValueOnce(response(undefined, 204)));
    render(<App />);
    await openWorkspace();
    await screen.findByRole('heading', { name: detail.title });
    selectPhase();
    fireEvent.click(logoutButton());
    expect(await screen.findByRole('alert')).toHaveTextContent('操作失敗，請稍後再試');
    expect(document.body).not.toHaveTextContent('private-secret');
    fireEvent.click(logoutButton());
    expect(await screen.findByRole('heading', { name: '登入專流' })).toBeInTheDocument();
  });

  it('aborts the request on unmount', () => {
    const fetcher = vi.fn(() => new Promise(() => {}));
    stubFetch(fetcher);
    const { unmount } = render(<App />);
    const signal = (fetcher.mock.calls as unknown as [string, RequestInit][])[0][1].signal;
    unmount();
    expect(signal?.aborted).toBe(true);
  });
});
