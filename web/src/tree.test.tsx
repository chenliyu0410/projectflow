import { projectMenu } from './test-navigation';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import App from './App';
import NodeEditor, { demoteTarget, moveOptions, promoteTarget } from './components/NodeEditor';
import TimelineView from './components/TimelineView';
import ReportPanel from './components/ReportPanel';
import AuditLogView from './components/AuditLogView';
import type { NodeItem, NodeStatus, ProjectDetail } from './types';

const response = (body: unknown, status = 200) => ({ ok: status < 400, status, json: async () => body });
const caps = { edit_metadata: true, assign: false, create_child: true, submit_report: false, move: true, copy: true, delete: true, lifecycle: true };
function node(id: string, title: string, parent: string | null, kind: string, status: NodeStatus, sort: number, extra: Partial<NodeItem> = {}): NodeItem {
  return { id, project_id: 'p', parent_id: parent, kind, title, status, owner_user_id: null, department_id: null, sort_order: sort,
    start_date: null, due_date: null, owner_display_name: null, department_name: null, capabilities: { ...caps }, state_actions: [], ...extra };
}
// Phase「試作」(top level, like a template project): 上層任務 ─ 子任務一, 子任務二 ─ 孫任務; then 另一個任務, 等待中任務, 待確認任務, 已完成任務.
const nodes = [
  node('ph', '試作', null, 'phase', 'doing', 10),
  node('a', '上層任務', 'ph', 'task', 'todo', 20),
  node('a1', '子任務一', 'a', 'task', 'done', 21),
  node('a2', '子任務二', 'a', 'task', 'todo', 22),
  node('aa', '孫任務', 'a2', 'task', 'todo', 23),
  node('b', '另一個任務', 'ph', 'task', 'todo', 30),
  node('c', '等待中任務', 'ph', 'task', 'todo', 40),
  node('d', '待確認任務', 'ph', 'task', 'review', 50),
  node('e', '已完成任務', 'ph', 'task', 'done', 60, { state_actions: ['reopen'] }),
];
const byId = (id: string) => nodes.find(item => item.id === id)!;
const project: ProjectDetail = { id: 'p', title: '樹狀專案', organization_key: 'food', owner_user_id: 'u1', nodes, gates: [], capabilities: { create_node: true } };
const deps = { items: [{ id: 'e1', project_id: 'p', predecessor_id: 'a1', successor_id: 'b' }, { id: 'e2', project_id: 'p', predecessor_id: 'a2', successor_id: 'aa' }],
  nodes: nodes.filter(n => n.kind === 'task').map(n => ({ id: n.id, title: n.title, status: n.status, blocked: false })), capabilities: { manage: true } };

function editor(target: NodeItem, extra: Partial<Parameters<typeof NodeEditor>[0]> = {}) {
  const tree = { move: vi.fn(), copy: vi.fn(), remove: vi.fn() };
  render(<NodeEditor projectId="p" mode="edit" node={target} parent={null} canAssign={false} nodes={nodes} tree={tree}
    reload={vi.fn()} close={vi.fn()} expired={vi.fn()} {...extra} />);
  return tree;
}

describe('TP-B targets', () => {
  it('promotes to the grandparent, or to the top level from a top phase', () => {
    expect(promoteTarget(nodes, byId('aa'))).toEqual({ target: 'a' });
    expect(promoteTarget(nodes, byId('a2'))).toEqual({ target: 'ph' });
    expect(promoteTarget(nodes, byId('b'))).toEqual({ target: null });
    expect(promoteTarget(nodes, byId('ph'))).toEqual({ reason: '已在最上層，無法再升級' });
  });

  it('stops at a blank project root and at nodes the user cannot see', () => {
    const blank = [node('r', '專案', null, 'project', 'todo', 0), node('p2', '階段', 'r', 'phase', 'doing', 10),
      node('t', '任務', 'p2', 'task', 'todo', 20), node('top', '頂層任務', 'r', 'task', 'todo', 30)];
    expect(promoteTarget(blank, blank[2])).toEqual({ target: 'r' });
    expect(promoteTarget(blank, blank[3])).toEqual({ reason: '已在最上層，無法再升級' });
    expect(promoteTarget([byId('aa')], byId('aa'))).toEqual({ reason: '看不到上層節點，無法升級' });
    expect(promoteTarget([byId('a2'), byId('aa')], byId('aa'))).toEqual({ reason: '看不到上上層節點，無法升級' });
  });

  it('demotes into the sibling just above and never into a closed one', () => {
    expect(demoteTarget(nodes, byId('b'))).toEqual({ target: 'a' });
    expect(demoteTarget(nodes, byId('a'))).toEqual({ reason: '上方沒有同層任務可以放入' });
    expect(demoteTarget(nodes, byId('e'))).toEqual({ reason: '不能移到已完成、待確認或已略過的任務底下' });
  });

  it('lists move targets in tree order without the node, its subtree or its parent', () => {
    const options = moveOptions(nodes, byId('a2'));
    expect(options.map(option => option.label)).toEqual(['（專案最上層）', '　試作', '　　　子任務一（已完成或待確認）', '　　另一個任務', '　　等待中任務',
      '　　待確認任務（已完成或待確認）', '　　已完成任務（已完成或待確認）']);
    expect(options.filter(option => option.disabled).map(option => option.value)).toEqual(['a1', 'd', 'e']);
    expect(moveOptions(nodes, byId('ph')).some(option => option.label === '（專案最上層）')).toBe(false);
  });
});

describe('TP-B editor', () => {
  it('runs promote, demote, move-to and copy from 層級操作', () => {
    const tree = editor(byId('a2'));
    const ops = screen.getByRole('group', { name: '層級操作' });
    fireEvent.click(within(ops).getByRole('button', { name: '↖ 升級' }));
    expect(tree.move).toHaveBeenLastCalledWith('ph');
    // The sibling above (子任務一) is done, so demoting is not offered.
    expect(within(ops).getByRole('button', { name: '↘ 降級' })).toBeDisabled();
    expect(ops).toHaveTextContent('降級：不能移到已完成、待確認或已略過的任務底下');
    expect(within(ops).getByRole('button', { name: '移動' })).toBeDisabled();
    fireEvent.change(within(ops).getByLabelText('移動到'), { target: { value: 'b' } });
    fireEvent.click(within(ops).getByRole('button', { name: '移動' }));
    expect(tree.move).toHaveBeenLastCalledWith('b');
    fireEvent.change(within(ops).getByLabelText('移動到'), { target: { value: '__top__' } });
    fireEvent.click(within(ops).getByRole('button', { name: '移動' }));
    expect(tree.move).toHaveBeenLastCalledWith(null);
    fireEvent.click(within(ops).getByRole('button', { name: '複製子樹' }));
    expect(tree.copy).toHaveBeenCalledTimes(1);
    document.body.innerHTML = '';
    const other = editor(byId('b'));
    fireEvent.click(within(screen.getByRole('group', { name: '層級操作' })).getByRole('button', { name: '↘ 降級' }));
    expect(other.move).toHaveBeenLastCalledWith('a');
  });

  it('explains unavailable steps and waits for unsaved edits', () => {
    const tree = editor(byId('a'));
    const ops = screen.getByRole('group', { name: '層級操作' });
    expect(within(ops).getByRole('button', { name: '↘ 降級' })).toBeDisabled();
    expect(ops).toHaveTextContent('降級：上方沒有同層任務可以放入');
    fireEvent.change(screen.getByLabelText('節點名稱'), { target: { value: '改過的名稱' } });
    expect(ops).toHaveTextContent('請先儲存或取消目前的變更');
    for (const name of ['↖ 升級', '複製子樹']) expect(within(ops).getByRole('button', { name })).toBeDisabled();
    expect(tree.move).not.toHaveBeenCalled();
  });

  it('shows only what the capabilities allow and nothing on phases', () => {
    editor({ ...byId('b'), capabilities: { ...caps, copy: false, delete: false } });
    const ops = screen.getByRole('group', { name: '層級操作' });
    expect(within(ops).queryByRole('button', { name: '複製子樹' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '刪除' })).not.toBeInTheDocument();
    document.body.innerHTML = '';
    editor({ ...byId('b'), capabilities: { ...caps, move: false, copy: false, delete: false } });
    expect(screen.queryByRole('group', { name: '層級操作' })).not.toBeInTheDocument();
    document.body.innerHTML = '';
    editor(byId('ph'));
    expect(screen.queryByRole('group', { name: '層級操作' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '刪除' })).not.toBeInTheDocument();
  });

  it('confirms a delete with the subtree size and the tasks that wait on it', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(response(deps))));
    const tree = editor(byId('a'));
    fireEvent.click(screen.getByRole('button', { name: '刪除' }));
    const dialog = screen.getByRole('alertdialog', { name: '刪除「上層任務」？' });
    expect(dialog).toHaveTextContent('將一併刪除 3 個子任務。');
    expect(await within(dialog).findByText('以下任務依賴它，前置條件會被移除：另一個任務')).toBeInTheDocument();
    expect(dialog).toHaveTextContent('刪除後可立即按「復原」還原；回報、筆記與附件不會從系統中清除。');
    fireEvent.click(within(dialog).getByRole('button', { name: '取消' }));
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '刪除' }));
    fireEvent.click(await screen.findByRole('button', { name: '確定刪除（可復原）' }));
    await waitFor(() => expect(tree.remove).toHaveBeenCalledTimes(1));
  });
});

describe('TP-B other entries', () => {
  it('offers ↶ 復原 on the timeline only when there is a step to undo', () => {
    const run = vi.fn();
    const { rerender } = render(<TimelineView project={project} select={vi.fn()} reload={vi.fn()} expired={vi.fn()} undo={{ label: null, disabled: false, run }} />);
    expect(screen.getByRole('button', { name: '↶ 復原' })).toBeDisabled();
    rerender(<TimelineView project={project} select={vi.fn()} reload={vi.fn()} expired={vi.fn()} undo={{ label: '移動「另一個任務」', disabled: false, run }} />);
    fireEvent.click(screen.getByRole('button', { name: '↶ 復原' }));
    expect(run).toHaveBeenCalledTimes(1);
  });

  it('keeps reopen unavailable while the parent is closed', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(response({ items: [], next_cursor: null }))));
    render(<ReportPanel node={byId('e')} userId="u1" reload={vi.fn()} expired={vi.fn()} parentClosed />);
    expect(await screen.findByRole('button', { name: '重新開啟' })).toBeDisabled();
    expect(screen.getByText('上層已完成、待確認或已略過，請先重新開啟上層')).toBeInTheDocument();
  });

  it('keeps a deleted node in the audit history without a link', async () => {
    const item = { id: 'l1', action: 'node.delete', summary: '刪除節點', node_id: 'a', node_title: '上層任務', node_deleted: true, project_id: 'p',
      project_title: '樹狀專案', actor_display_name: '專案負責', created_at: '2026-10-10T01:00:00+00:00', payload: { title: '上層任務', count: 4, parent_title: '試作' } };
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(response({ items: [item], next_cursor: null }))));
    render(<AuditLogView openNode={vi.fn()} expired={vi.fn()} />);
    expect(await screen.findByText('上層任務（已刪除）')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '上層任務' })).not.toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '刪除節點' })).toBeInTheDocument();
    expect(screen.getByText('刪除節點數').nextSibling).toHaveTextContent('4');
  });
});

describe('TP-B app flows', () => {
  const projects = { items: [{ id: 'p', title: '樹狀專案', organization_key: 'food', owner_user_id: 'u1' }] };
  const overview = { project_count: 0, task_counts: { todo: 0, doing: 0, review: 0, done: 0, skipped: 0 }, completion_percent: null, projects: [] };
  function app(extra: (path: string, init?: RequestInit) => unknown = () => undefined, detail: () => ProjectDetail = () => project) {
    const session = { user: { id: 'u1', username: 'yu', display_name: '游專案', role: 'admin' }, organization: { id: 'o1', key: 'food', name: '毛研食品' } };
    const fetch = vi.fn((path: string, init?: RequestInit) => {
      const custom = extra(path, init);
      if (custom !== undefined) return Promise.resolve(custom);
      return Promise.resolve(path === '/api/auth/me' ? response(session) : path === '/api/projects' ? response(projects)
        : path === '/api/workspace/overview' ? response(overview) : path.startsWith('/api/workspace/my-tasks') ? response({ items: [] })
          : path === '/api/projects/p' ? response(detail()) : path === '/api/projects/p/dependencies' ? response(deps)
            : path.includes('/records?') ? response({ items: [], next_cursor: null }) : response({}, 404));
    });
    vi.stubGlobal('fetch', fetch);
    render(<App />);
    return fetch;
  }
  async function openNode(...titles: string[]) {
    await screen.findByRole('heading', { name: '所有專案總覽' });
    fireEvent.click(within(projectMenu()).getByRole('button', { name: '樹狀專案' }));
    await screen.findByRole('heading', { name: '樹狀專案' });
    fireEvent.click(within(screen.getByLabelText('開發階段與閘門')).getByRole('button', { name: '進入階段：試作' }));
    for (const title of titles) {
      fireEvent.click(within(screen.getByLabelText('看板')).getByRole('button', { name: title }));
      await screen.findByRole('heading', { name: title });
    }
  }
  const notice = () => screen.getByRole('alert');

  it('deletes a task, returns to its parent and undoes the delete', async () => {
    let gone = false;
    const fetch = app((path, init) => path === '/api/nodes/a' && init?.method === 'DELETE' ? (gone = true, response({ undo_id: 'u-del', project_id: 'p', parent_id: 'ph', deleted_count: 4 }))
      : path === '/api/undo' ? (gone = false, response({ action: 'node.delete', project_id: 'p', node_id: 'a', parent_id: 'ph' })) : undefined,
    () => gone ? { ...project, nodes: nodes.filter(n => !['a', 'a1', 'a2', 'aa'].includes(n.id)) } : project);
    await openNode('上層任務');
    fireEvent.click(screen.getByRole('button', { name: '編輯節點' }));
    fireEvent.click(screen.getByRole('button', { name: '刪除' }));
    fireEvent.click(await screen.findByRole('button', { name: '確定刪除（可復原）' }));
    expect(await screen.findByText('已刪除「上層任務」')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '試作' })).toBeInTheDocument();
    expect(within(screen.getByLabelText('看板')).queryByRole('button', { name: '上層任務' })).not.toBeInTheDocument();
    fireEvent.click(within(notice()).getByRole('button', { name: '復原' }));
    expect(await screen.findByText('已復原：刪除「上層任務」')).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledWith('/api/undo', expect.objectContaining({ method: 'POST', body: JSON.stringify({ audit_id: 'u-del' }) }));
    expect(within(screen.getByLabelText('看板')).getByRole('button', { name: '上層任務' })).toBeInTheDocument();
  });

  it('copies a subtree and opens the copy', async () => {
    const copy = node('b2', '另一個任務（複本）', 'ph', 'task', 'todo', 30);
    let copied = false;
    const fetch = app(path => path === '/api/nodes/b/copy' ? (copied = true, response({ ...copy, undo_id: 'u-copy', copied_count: 1 }, 201)) : undefined,
      () => copied ? { ...project, nodes: [...nodes, copy] } : project);
    await openNode('另一個任務');
    fireEvent.click(screen.getByRole('button', { name: '編輯節點' }));
    fireEvent.click(screen.getByRole('button', { name: '複製子樹' }));
    expect(await screen.findByText('已複製子樹「另一個任務（複本）」')).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledWith('/api/nodes/b/copy', expect.objectContaining({ method: 'POST' }));
    expect(within(notice()).getByRole('button', { name: '復原' })).toBeEnabled();
    fireEvent.click(within(notice()).getByRole('button', { name: '開啟' }));
    expect(await screen.findByRole('heading', { name: '另一個任務（複本）' })).toBeInTheDocument();
  });

  it('promotes a task and undoes it with Ctrl+Z, once', async () => {
    let moved = false;
    const fetch = app(path => path === '/api/nodes/a2/move' ? (moved = true, response({ ...byId('a2'), parent_id: 'ph', undo_id: 'u-move' }))
      : path === '/api/undo' ? (moved = false, response({ action: 'node.move', project_id: 'p', node_id: 'a2', parent_id: 'a' })) : undefined,
    () => moved ? { ...project, nodes: nodes.map(n => n.id === 'a2' ? { ...n, parent_id: 'ph' } : n) } : project);
    await openNode('上層任務', '子任務二');
    fireEvent.click(screen.getByRole('button', { name: '編輯節點' }));
    fireEvent.click(screen.getByRole('button', { name: '↖ 升級' }));
    expect(await screen.findByText('已將「子任務二」移到「試作」底下')).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledWith('/api/nodes/a2/move', expect.objectContaining({ body: JSON.stringify({ parent_id: 'ph' }) }));
    fireEvent.keyDown(window, { key: 'z', ctrlKey: true });
    expect(await screen.findByText('已復原：移動「子任務二」')).toBeInTheDocument();
    fireEvent.keyDown(window, { key: 'z', ctrlKey: true });
    expect(await screen.findByText('沒有可以復原的操作')).toBeInTheDocument();
    expect(fetch.mock.calls.filter(([path]) => path === '/api/undo')).toHaveLength(1);
  });

  it('keeps the undo step when the API refuses for now, and drops it once it is stale', async () => {
    let attempts = 0;
    const fetch = app(path => path === '/api/nodes/b/move' ? response({ ...byId('b'), parent_id: 'a', undo_id: 'u-move' })
      : path === '/api/undo' ? (attempts += 1, attempts === 1 ? response({ detail: '原本的上層已無法放回，無法復原' }, 409)
        : response({ detail: '只能復原最近一次的結構操作' }, 409)) : undefined);
    await openNode('另一個任務');
    fireEvent.click(screen.getByRole('button', { name: '編輯節點' }));
    fireEvent.click(screen.getByRole('button', { name: '↘ 降級' }));
    expect(await screen.findByText('已將「另一個任務」移到「上層任務」底下')).toBeInTheDocument();
    fireEvent.click(within(notice()).getByRole('button', { name: '復原' }));
    expect(await screen.findByText('原本的上層已無法放回，無法復原')).toBeInTheDocument();
    fireEvent.keyDown(window, { key: 'z', ctrlKey: true });
    expect(await screen.findByText('只能復原最近一次的結構操作')).toBeInTheDocument();
    fireEvent.keyDown(window, { key: 'z', ctrlKey: true });
    expect(await screen.findByText('沒有可以復原的操作')).toBeInTheDocument();
    expect(fetch.mock.calls.filter(([path]) => path === '/api/undo')).toHaveLength(2);
  });

  it('does not offer a new child under a closed node', async () => {
    app();
    await openNode('已完成任務');
    const add = screen.getByRole('button', { name: /新增子節點/ });
    expect(add).toBeDisabled();
    expect(add).toHaveAttribute('title', '不能在已完成、待確認或已略過的節點底下新增');
  });
});
