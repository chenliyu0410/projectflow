import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import App from './App';
import type { NodeItem, ProjectDetail, NodeStatus } from './types';
import NodeWorkspace from './components/NodeWorkspace';

const identity = { user: { id: 'u', display_name: '使用者', role: 'admin' }, organization: { id: 'o', name: '公司' } };
const summary = { id: 'p', title: '四層專案', owner_user_id: 'u', organization_key: 'food' };
const node = (id: string, parent_id: string | null, kind = 'task', status: NodeStatus = 'todo'): NodeItem => ({
  id, project_id: 'p', parent_id, kind, title: id, status, sort_order: 0,
  owner_user_id: null, department_id: null, start_date: null, due_date: null,
  owner_display_name: null, department_name: null,
  capabilities: { edit_metadata: true, assign: true, create_child: true },
});
const nodes = [node('根', null, 'project'), node('階段', '根', 'phase'), node('父任務', '階段'), node('子任務', '父任務'), node('略過任務', '父任務', 'task', 'skipped')];
const detail: ProjectDetail = { ...summary, nodes, gates: [], capabilities: { create_node: true } };
const response = (body: unknown, status = 200) => ({ ok: status < 400, status, json: async () => body });
function setup(value = detail) {
  const fetcher = vi.fn().mockResolvedValueOnce(response(identity)).mockResolvedValueOnce(response({ items: [summary] })).mockResolvedValueOnce(response(value));
  vi.stubGlobal('fetch', fetcher); render(<App />); return fetcher;
}
async function enter() {
  fireEvent.click(await screen.findByRole('button', { name: '專案工作區' }));
  await screen.findByRole('heading', { name: summary.title });
}
function treeButton(name: string) { return within(screen.getByLabelText('節點樹')).getByRole('button', { name }); }

describe('P2a workspace navigation', () => {
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
    vi.stubGlobal('fetch', fetcher); render(<App />);
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
    vi.stubGlobal('fetch', fetcher); render(<App />);
    fireEvent.click(await screen.findByRole('button', { name: '專案工作區' }));
    await screen.findByText('載入專案中');
    fireEvent.click(screen.getByRole('button', { name: '總覽' }));
    await act(async () => { resolve(response({}, 401)); });
    expect(screen.getByRole('heading', { name: '總覽' })).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('節點樹')).not.toBeInTheDocument();
  });
});
