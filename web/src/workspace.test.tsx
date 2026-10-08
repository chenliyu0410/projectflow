import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import App from './App';
import type { NodeItem, ProjectDetail, NodeStatus } from './types';
import NodeWorkspace from './components/NodeWorkspace';
import WorkspaceOverview from './components/WorkspaceOverview';
import MyTasks from './components/MyTasks';

const identity = { user: { id: 'u', display_name: '使用者', role: 'admin' }, organization: { id: 'o', name: '公司' } };
const summary = { id: 'p', title: '四層專案', owner_user_id: 'u', organization_key: 'food' };
const node = (id: string, parent_id: string | null, kind = 'task', status: NodeStatus = 'todo'): NodeItem => ({
  id, project_id: 'p', parent_id, kind, title: id, status, sort_order: 0,
  owner_user_id: null, department_id: null, start_date: null, due_date: null,
  owner_display_name: null, department_name: null,
  state_actions: ['todo', 'doing'], capabilities: { edit_metadata: true, assign: true, create_child: true },
});

describe('P2a query pages', () => {
  const emptyOverview = { project_count: 0, task_counts: { todo: 0, doing: 0, review: 0, done: 0, skipped: 0 }, completion_percent: null, projects: [] };
  it('distinguishes overview read failure from empty data and displays null completion', async () => {
    const fetcher = vi.fn().mockResolvedValueOnce(response({ detail: 'private-secret' }, 500)).mockResolvedValueOnce(response(emptyOverview));
    vi.stubGlobal('fetch', fetcher); render(<WorkspaceOverview openProject={vi.fn()} expired={vi.fn()} />);
    expect(screen.getByRole('status')).toHaveTextContent('載入總覽中');
    await screen.findByRole('alert'); expect(screen.queryByText('目前沒有可見專案')).not.toBeInTheDocument();
    expect(document.body).not.toHaveTextContent('private-secret');
    fireEvent.click(screen.getByRole('button', { name: '重試總覽' }));
    expect(await screen.findByLabelText('可見任務完成率')).toHaveTextContent('—');
    expect(screen.getByText('目前沒有可見專案')).toBeInTheDocument();
  });

  it('supports all five task states and clearing filters without changing overview', async () => {
    const fetcher = vi.fn().mockResolvedValue(response({ items: [] })); vi.stubGlobal('fetch', fetcher);
    render(<MyTasks openNode={vi.fn()} expired={vi.fn()} />);
    expect(await screen.findByText('目前沒有指派給你的可見任務')).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('搜尋任務'), { target: { value: ' 查詢 ' } });
    for (const status of ['todo', 'doing', 'review', 'done', 'skipped']) {
      fireEvent.change(screen.getByLabelText('任務狀態'), { target: { value: status } });
      await waitFor(() => expect(fetcher).toHaveBeenLastCalledWith(`/api/workspace/my-tasks?q=${encodeURIComponent('查詢')}&status=${status}`, expect.anything()));
    }
    expect(await screen.findByText('沒有符合篩選的任務')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '清除篩選' }));
    expect(screen.getByLabelText('搜尋任務')).toHaveValue(''); expect(screen.getByLabelText('任務狀態')).toHaveValue('');
    await screen.findByText('目前沒有指派給你的可見任務');
    expect(fetcher.mock.calls.every(([path]) => path.startsWith('/api/workspace/my-tasks?'))).toBe(true);
  });

  it('retries my-task errors without showing empty results and ignores superseded queries', async () => {
    let finish!: (value: unknown) => void;
    const fetcher = vi.fn().mockResolvedValueOnce(response({}, 500)).mockImplementationOnce(() => new Promise(resolve => { finish = resolve; })).mockResolvedValueOnce(response({ items: [] }));
    const expired = vi.fn(); vi.stubGlobal('fetch', fetcher); render(<MyTasks openNode={vi.fn()} expired={expired} />);
    await screen.findByRole('alert'); expect(screen.queryByText('目前沒有指派給你的可見任務')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '重試我的任務' }));
    fireEvent.change(screen.getByLabelText('搜尋任務'), { target: { value: '最新' } });
    await screen.findByText('沒有符合篩選的任務');
    await act(async () => { finish(response({}, 401)); });
    expect(expired).not.toHaveBeenCalled(); expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it.each(['overview', 'my-tasks'])('clears session on %s expiry', async page => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({}, 401))); const expired = vi.fn();
    render(page === 'overview' ? <WorkspaceOverview openProject={vi.fn()} expired={expired} /> : <MyTasks openNode={vi.fn()} expired={expired} />);
    await waitFor(() => expect(expired).toHaveBeenCalledTimes(1));
  });
});
const nodes = [node('根', null, 'project'), node('階段', '根', 'phase'), node('父任務', '階段'), node('子任務', '父任務'), node('略過任務', '父任務', 'task', 'skipped')];
const detail: ProjectDetail = { ...summary, nodes, gates: [], capabilities: { create_node: true } };
function stubFetch(fetcher: (path: string, init?: RequestInit) => unknown) {
  vi.stubGlobal('fetch', (path: string, init?: RequestInit) => path.includes('/records?') ? Promise.resolve(response({ items: [], next_cursor: null }))
    : path.endsWith('/collaborators') ? Promise.resolve(response({ users: [], departments: [], revision: 0 }))
    : path.endsWith('/attachment-quota') ? Promise.resolve(response({ limit_bytes: 1000000000, charged_bytes: 0, remaining_bytes: 1000000000 })) : path === '/api/workspace/overview'
    ? Promise.resolve(response({ project_count: 0, task_counts: { todo: 0, doing: 0, review: 0, done: 0, skipped: 0 }, completion_percent: null, projects: [] }))
    : path.startsWith('/api/workspace/my-tasks') ? Promise.resolve(response({ items: [] })) : fetcher(path, init));
}
const response = (body: unknown, status = 200) => ({ ok: status < 400, status, json: async () => body });
function setup(value = detail) {
  const fetcher = vi.fn().mockResolvedValueOnce(response(identity)).mockResolvedValueOnce(response({ items: [summary] })).mockResolvedValueOnce(response(value));
  stubFetch(fetcher); render(<App />); return fetcher;
}
async function enter() {
  fireEvent.click(await screen.findByRole('button', { name: '專案工作區' }));
  await screen.findByRole('heading', { name: summary.title });
}
function treeButton(name: string) { return within(screen.getByLabelText('節點樹')).getByRole('button', { name }); }

describe('P2a workspace navigation', () => {
  it('loads visible overview statistics and opens a project', async () => {
    const counts = { todo: 2, doing: 1, review: 1, done: 3, skipped: 2 };
    const fetcher = vi.fn(async (path: string) => response(path === '/api/auth/me' ? identity : path === '/api/projects' ? { items: [summary] }
      : path === '/api/workspace/overview' ? { project_count: 1, task_counts: counts, completion_percent: 43, projects: [{ ...summary, task_counts: counts, completion_percent: 43 }] } : detail));
    vi.stubGlobal('fetch', fetcher); render(<App />);
    expect(await screen.findByLabelText('可見任務完成率')).toHaveTextContent('43%');
    expect(screen.getByLabelText('可見專案數')).toHaveTextContent('1');
    fireEvent.click(screen.getByRole('button', { name: summary.title }));
    expect(await screen.findByLabelText('節點樹')).toBeInTheDocument();
  });

  it('searches my tasks and locates the returned project and deep node', async () => {
    const fetcher = vi.fn(async (path: string) => response(path === '/api/auth/me' ? identity : path === '/api/projects' ? { items: [summary] }
      : path.includes('/records?') ? { items: [], next_cursor: null } : path.endsWith('/collaborators') ? { users: [], departments: [], revision: 0 }
      : path.startsWith('/api/workspace/my-tasks') ? { items: [{ ...nodes[3], project_title: summary.title }] }
      : path === '/api/workspace/overview' ? { project_count: 1, task_counts: { todo: 0, doing: 0, review: 0, done: 0, skipped: 0 }, completion_percent: null, projects: [] } : detail));
    vi.stubGlobal('fetch', fetcher); render(<App />);
    fireEvent.click(await screen.findByRole('button', { name: '我的任務' }));
    fireEvent.change(await screen.findByLabelText('搜尋任務'), { target: { value: ' 子任務 ' } });
    fireEvent.change(screen.getByLabelText('任務狀態'), { target: { value: 'skipped' } });
    fireEvent.click(await screen.findByRole('button', { name: '子任務' }));
    expect(await screen.findByLabelText('節點詳情')).toHaveTextContent('子任務');
    await waitFor(() => expect(treeButton('子任務')).toHaveAttribute('aria-pressed', 'true'));
    expect(fetcher.mock.calls.some(([path]) => path.includes('status=skipped'))).toBe(true);
  });

  it.each(['tree', 'project breadcrumb', 'node breadcrumb', 'board card', 'skipped card'])('preserves pending logout when clicking %s', async entry => {
    let resolveLogout!: (value: ReturnType<typeof response>) => void;
    const fetcher = setup().mockImplementationOnce(() => new Promise(done => { resolveLogout = done; }));
    await enter();
    fireEvent.click(treeButton('根')); fireEvent.click(treeButton('階段')); fireEvent.click(treeButton('父任務'));
    const target = entry === 'tree' ? treeButton('子任務')
      : entry === 'project breadcrumb' ? within(screen.getByLabelText('節點路徑')).getByRole('button', { name: summary.title })
      : entry === 'node breadcrumb' ? within(screen.getByLabelText('節點路徑')).getByRole('button', { name: '階段' })
      : within(screen.getByLabelText('看板')).getByRole('button', { name: entry === 'board card' ? '子任務' : '略過任務' });
    fireEvent.click(screen.getByRole('button', { name: '登出' }));
    expect(screen.getByRole('button', { name: '登出' })).toBeDisabled();
    fireEvent.click(target);
    const logoutRequest = fetcher.mock.calls.find(([path]) => path === '/api/auth/logout')!;
    expect(logoutRequest[1].signal.aborted).toBe(false);
    await act(async () => { resolveLogout(response(undefined, 204)); });
    expect(await screen.findByRole('heading', { name: '登入專流' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '登入' })).not.toBeDisabled();
    expect(screen.queryByLabelText('節點樹')).not.toBeInTheDocument();
  });

  it('lands on overview, keeps identity and uses collapsible navigation without loading detail', async () => {
    const fetcher = setup();
    expect(await screen.findByRole('heading', { name: '總覽' })).toBeInTheDocument();
    expect(fetcher).toHaveBeenCalledTimes(2);
    expect(screen.getByLabelText('目前公司')).toHaveTextContent('公司');
    const toggle = screen.getByRole('button', { name: '切換導覽' });
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    fireEvent.click(toggle); expect(toggle).toHaveAttribute('aria-expanded', 'true');
    fireEvent.click(screen.getByRole('button', { name: '我的任務' }));
    expect(screen.getByRole('heading', { name: '我的任務' })).toBeInTheDocument();
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
  });

  it('expands four levels, collapses branches and shows only immediate children including skipped', async () => {
    setup(); await enter();
    expect(screen.getByLabelText('節點詳情')).toHaveTextContent('四層專案');
    expect(within(screen.getByLabelText('看板')).getByRole('button', { name: '根' })).toBeInTheDocument();
    fireEvent.click(treeButton('根'));
    expect(within(screen.getByLabelText('看板')).getByRole('button', { name: '階段' })).toBeInTheDocument();
    expect(screen.getByLabelText('節點詳情')).toHaveTextContent('未指派');
    expect(screen.getByLabelText('節點詳情')).toHaveTextContent('未設定');
    fireEvent.click(treeButton('收合根'));
    fireEvent.click(treeButton('展開根'));
    fireEvent.click(treeButton('展開階段'));
    fireEvent.click(treeButton('父任務'));
    expect(treeButton('子任務')).toBeInTheDocument();
    expect(screen.getByLabelText('節點路徑')).toHaveTextContent('四層專案 / 根 / 階段 / 父任務');
    const board = within(screen.getByLabelText('看板'));
    expect(board.getByRole('button', { name: '子任務' })).toBeInTheDocument();
    expect(board.queryByRole('button', { name: '父任務' })).not.toBeInTheDocument();
    expect(within(screen.getByLabelText('已略過')).getByRole('button', { name: '略過任務' })).toBeInTheDocument();
    fireEvent.click(treeButton('收合階段'));
    expect(within(screen.getByLabelText('節點樹')).queryByRole('button', { name: '父任務' })).not.toBeInTheDocument();
    fireEvent.click(within(screen.getByLabelText('節點路徑')).getByRole('button', { name: '階段' }));
    expect(board.getByRole('button', { name: '父任務' })).toBeInTheDocument();
  });

  it('opens a deep node from an explicit project and node selection and expands its visible ancestors', () => {
    const select = vi.fn();
    render(<NodeWorkspace project={detail} selectedNodeId="子任務" select={select} readonly={false} canApprove={false} disabled={false} mutate={vi.fn()} />);
    expect(treeButton('子任務')).toHaveAttribute('aria-pressed', 'true');
    expect(treeButton('收合根')).toHaveAttribute('aria-expanded', 'true');
    expect(treeButton('收合階段')).toHaveAttribute('aria-expanded', 'true');
    expect(treeButton('收合父任務')).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByLabelText('節點詳情')).toHaveTextContent('子任務');
    fireEvent.click(within(screen.getByLabelText('節點路徑')).getByRole('button', { name: summary.title }));
    expect(select).toHaveBeenCalledWith(null);
  });

  it('bounds cyclic legacy trees and paths without losing visible nodes', () => {
    const cyclic = { ...detail, nodes: [node('循環甲', '循環乙'), node('循環乙', '循環甲'), node('自身', '自身')] };
    render(<NodeWorkspace project={cyclic} selectedNodeId="循環乙" select={vi.fn()} readonly={true} canApprove={false} disabled={false} mutate={vi.fn()} />);
    expect(treeButton('循環甲')).toBeInTheDocument();
    expect(treeButton('循環乙')).toBeInTheDocument();
    expect(treeButton('自身')).toBeInTheDocument();
    expect(within(screen.getByLabelText('節點樹')).getAllByRole('button').filter(button => button.hasAttribute('aria-pressed'))).toHaveLength(3);
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument();
  });

  it.each([403, 404])('shows safe project failure and allows retry (%s)', async status => {
    const fetcher = vi.fn().mockResolvedValueOnce(response(identity)).mockResolvedValueOnce(response({ items: [summary] }))
      .mockResolvedValueOnce(response({ detail: 'private-secret' }, status)).mockResolvedValueOnce(response(detail));
    stubFetch(fetcher); render(<App />);
    await screen.findByRole('heading', { name: '總覽' });
    fireEvent.click(screen.getByRole('button', { name: '專案工作區' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(status === 403 ? '沒有操作權限' : '找不到項目');
    expect(document.body).not.toHaveTextContent('private-secret');
    fireEvent.click(screen.getByRole('button', { name: '重試' }));
    expect(await screen.findByRole('heading', { name: summary.title })).toBeInTheDocument();
  });

  it('promotes visible orphans and displays safe metadata with unconverted dates', async () => {
    setup({ ...detail, nodes: [{ ...node('可見任務', '隱藏父節點'), owner_display_name: '成員', department_name: '研發', start_date: '0001-01-01', due_date: '9999-12-31' }] });
    await enter(); fireEvent.click(treeButton('可見任務'));
    expect(screen.getByLabelText('節點詳情')).toHaveTextContent('成員');
    expect(screen.getByLabelText('節點詳情')).toHaveTextContent('研發');
    expect(screen.getByLabelText('節點詳情')).toHaveTextContent('0001-01-01');
    expect(screen.getByLabelText('節點詳情')).toHaveTextContent('9999-12-31');
    expect(document.body).not.toHaveTextContent('隱藏父節點');
    expect(screen.getByLabelText('看板')).toHaveTextContent('目前沒有下一層節點');
  });

  it('ignores nonabortable detail success or expiry after navigation away', async () => {
    let resolve!: (value: ReturnType<typeof response>) => void;
    const fetcher = vi.fn().mockResolvedValueOnce(response(identity)).mockResolvedValueOnce(response({ items: [summary] })).mockImplementationOnce(() => new Promise(done => { resolve = done; }));
    stubFetch(fetcher); render(<App />);
    fireEvent.click(await screen.findByRole('button', { name: '專案工作區' }));
    await screen.findByText('載入專案中');
    fireEvent.click(screen.getByRole('button', { name: '總覽' }));
    await act(async () => { resolve(response({}, 401)); });
    expect(screen.getByRole('heading', { name: '總覽' })).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('節點樹')).not.toBeInTheDocument();
  });
});
