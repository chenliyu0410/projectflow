import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import App from './App';
import NodeWorkspace from './components/NodeWorkspace';
import TimelineView from './components/TimelineView';
import DependencyPanel from './components/DependencyPanel';
import RecordTimeline from './components/RecordTimeline';
import ReportPanel from './components/ReportPanel';
import NodeEditor from './components/NodeEditor';
import { percent, progressMap, projectProgress } from './progress';
import type { ProgressNode } from './progress';
import vectors from './progress.vectors.json';
import type { NodeItem, NodeStatus, ProjectDetail } from './types';

const response = (body: unknown, status = 200) => ({ ok: status < 400, status, json: async () => body });
const caps = { edit_metadata: true, assign: false, create_child: false, submit_report: false, move: false };
function node(id: string, title: string, parent: string | null, kind: string, status: NodeStatus, sort: number, extra: Partial<NodeItem> = {}): NodeItem {
  return { id, project_id: 'p', parent_id: parent, kind, title, status, owner_user_id: null, department_id: null, sort_order: sort,
    start_date: null, due_date: null, owner_display_name: null, department_name: null, capabilities: { ...caps }, state_actions: [], ...extra };
}
const reportable = { capabilities: { ...caps, submit_report: true, move: true }, state_actions: ['todo', 'doing', 'submit_report'] };
// Phase「試作」: 上層任務 (1/2 children closed), 另一個任務 (reportable, movable), 等待中任務 (blocked), 待確認任務, 已完成任務 (weight 3).
const nodes = [
  node('ph', '試作', null, 'phase', 'doing', 10, { state_actions: ['todo', 'doing', 'review', 'done', 'skipped'] }),
  node('a', '上層任務', 'ph', 'task', 'todo', 20, { ...reportable, start_date: '2026-10-01', due_date: '2026-10-20' }),
  node('a1', '子任務一', 'a', 'task', 'done', 21),
  node('a2', '子任務二', 'a', 'task', 'todo', 22),
  node('aa', '孫任務', 'a2', 'task', 'todo', 23),
  node('aaa', '曾孫任務', 'aa', 'task', 'todo', 24),
  node('b', '另一個任務', 'ph', 'task', 'todo', 30, reportable),
  node('c', '等待中任務', 'ph', 'task', 'todo', 40, { blocked: true }),
  node('d', '待確認任務', 'ph', 'task', 'review', 50, { state_actions: [] }),
  node('e', '已完成任務', 'ph', 'task', 'done', 60, { weight: 3, state_actions: ['reopen'] }),
];
const project: ProjectDetail = { id: 'p', title: '規劃器專案', organization_key: 'food', owner_user_id: 'u1', nodes, gates: [], capabilities: { create_node: true } };
const deps = (items: { id: string; predecessor_id: string; successor_id: string }[], extra: { id: string; title: string; status: NodeStatus; blocked: boolean }[] = []) => ({
  items: items.map(item => ({ ...item, project_id: 'p' })),
  nodes: [...nodes.filter(n => n.kind === 'task').map(n => ({ id: n.id, title: n.title, status: n.status, blocked: !!n.blocked })), ...extra],
  capabilities: { manage: true },
});

function workspace(props: Partial<Parameters<typeof NodeWorkspace>[0]> = {}) {
  const handlers = { select: vi.fn(), mutate: vi.fn(), move: vi.fn(), openReport: vi.fn(), notify: vi.fn() };
  render(<NodeWorkspace project={project} selectedNodeId="ph" readonly={false} canApprove={false} disabled={false} {...handlers} {...props} />);
  return handlers;
}
const board = () => screen.getByLabelText('看板');
const cardOf = (title: string) => within(board()).getByRole('button', { name: title }).closest('article')!;
const column = (label: string) => board().querySelector(`[aria-label="${label}"]`)!;
function drag(source: Element, target: Element) {
  const dataTransfer = { setData: vi.fn(), getData: vi.fn(), effectAllowed: '', dropEffect: '' };
  fireEvent.dragStart(source, { dataTransfer });
  fireEvent.dragOver(target, { dataTransfer });
  fireEvent.drop(target, { dataTransfer });
  fireEvent.dragEnd(source, { dataTransfer });
}

describe('TP-A progress', () => {
  it('matches the vectors shared with the API', () => {
    for (const vector of vectors as { name: string; nodes: ProgressNode[]; expected: Record<string, number>; project: number | null }[]) {
      const values = progressMap(vector.nodes);
      expect(Object.fromEntries([...values].map(([id, value]) => [id, percent(value)])), vector.name).toEqual(vector.expected);
      expect(projectProgress(vector.nodes), vector.name).toBe(vector.project);
    }
  });

  it('shows weighted progress in the header and blocks marking a parent done in the status menu', () => {
    workspace();
    const head = screen.getByLabelText('節點詳情');
    // 上層任務 50, 另一個 0, 等待中 0, 待確認 90, 已完成 100×3 → 440 / 7 ≈ 63.
    expect(within(head).getByLabelText('進度 63%')).toBeInTheDocument();
    const done = within(head).getByRole('option', { name: '完成（還有 4 項子任務未完成）' }) as HTMLOptionElement;
    expect(done.disabled).toBe(true);
  });

  it('flags nodes five levels deep', () => {
    workspace({ selectedNodeId: 'aaa' });
    expect(screen.getByText('層數較深，可考慮拆成獨立專案')).toBeInTheDocument();
  });

  it('keeps the phase button name and adds progress and gate state as its description', () => {
    workspace({ selectedNodeId: null });
    const phase = within(screen.getByLabelText('開發階段與閘門')).getByRole('button', { name: '進入階段：試作' });
    expect(phase).toHaveAccessibleDescription('63% ● 目前階段');
  });
});

describe('TP-A cards', () => {
  it('shows subtask count and mini progress, and expands the next level inside the card', () => {
    const { select } = workspace();
    const card = cardOf('上層任務');
    expect(card).toHaveTextContent('1/2 子任務');
    expect(card).toHaveTextContent('50%');
    fireEvent.click(within(card).getByRole('button', { name: '展開下一層：上層任務' }));
    const list = within(card).getByRole('list', { name: '上層任務的下一層' });
    expect(within(list).getAllByRole('button').map(button => button.textContent)).toEqual(['子任務一（0）', '子任務二（1）']);
    fireEvent.click(within(list).getByRole('button', { name: '子任務二（1）' }));
    expect(select).toHaveBeenCalledWith('a2');
    expect(within(card).getByRole('button', { name: '收合下一層：上層任務' })).toHaveAttribute('aria-expanded', 'true');
  });

  it('offers ✓ 回報 only on reportable cards without open children', () => {
    const { openReport } = workspace();
    fireEvent.click(within(cardOf('另一個任務')).getByRole('button', { name: '回報完成：另一個任務' }));
    expect(openReport).toHaveBeenCalledWith('b');
    expect(within(cardOf('上層任務')).queryByRole('button', { name: /回報完成/ })).not.toBeInTheDocument();
    expect(within(cardOf('待確認任務')).queryByRole('button', { name: /回報完成/ })).not.toBeInTheDocument();
  });

  it('hides quick report and dragging for read-only users', () => {
    workspace({ readonly: true });
    expect(within(board()).queryByRole('button', { name: /回報完成/ })).not.toBeInTheDocument();
    expect(board().querySelector('[draggable]')).toBeNull();
    expect(screen.getByText('點卡片標題進入下一層')).toBeInTheDocument();
  });

  it('names visible open predecessors and highlights related cards on hover', async () => {
    const fetch = vi.fn((path: string) => path === '/api/projects/p/dependencies'
      ? Promise.resolve(response(deps([{ id: 'e1', predecessor_id: 'x', successor_id: 'c' }, { id: 'e2', predecessor_id: 'c', successor_id: 'b' }], [{ id: 'x', title: '前置甲', status: 'doing', blocked: false }])))
      : Promise.resolve(response({}, 404)));
    vi.stubGlobal('fetch', fetch);
    workspace();
    expect(await within(cardOf('等待中任務')).findByText('等待：前置甲')).toBeInTheDocument();
    fireEvent.mouseEnter(cardOf('另一個任務'));
    expect(cardOf('等待中任務')).toHaveClass('hl');
    expect(cardOf('另一個任務')).toHaveClass('hl-src');
    expect(cardOf('上層任務')).not.toHaveClass('hl');
    fireEvent.mouseLeave(cardOf('另一個任務'));
    expect(cardOf('等待中任務')).not.toHaveClass('hl');
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it('does not name predecessors the user cannot see', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(response(deps([])))));
    workspace();
    expect(await within(cardOf('等待中任務')).findByText('等待：前置任務')).toBeInTheDocument();
  });
});

describe('TP-A drag and drop', () => {
  it('changes todo and doing through the status API and opens the report for 待確認／完成', () => {
    const { mutate, openReport } = workspace();
    expect(screen.getByText('拖曳卡片改狀態；拖到另一張卡片上 = 變成它的子任務')).toBeInTheDocument();
    drag(cardOf('另一個任務'), column('進行中'));
    expect(mutate).toHaveBeenCalledWith('status', 'b', 'doing');
    drag(cardOf('另一個任務'), column('待確認'));
    drag(cardOf('另一個任務'), column('完成'));
    expect(openReport.mock.calls).toEqual([['b'], ['b']]);
    expect(mutate).toHaveBeenCalledTimes(1);
  });

  it('explains refused drops without sending anything', () => {
    const { mutate, openReport, notify, move } = workspace();
    drag(cardOf('待確認任務'), column('進行中'));
    drag(cardOf('已完成任務'), column('待處理'));
    drag(cardOf('上層任務'), column('完成'));
    expect(notify.mock.calls).toEqual([['已完成的任務請用「重新開啟」'], ['還有 1 項子任務未完成：子任務二']]);
    expect(cardOf('待確認任務')).not.toHaveAttribute('draggable');
    expect(cardOf('等待中任務')).not.toHaveAttribute('draggable');
    expect(mutate).not.toHaveBeenCalled(); expect(openReport).not.toHaveBeenCalled(); expect(move).not.toHaveBeenCalled();
  });

  it('moves a card under another card for users who can move', () => {
    const { move, notify, mutate } = workspace();
    drag(cardOf('另一個任務'), cardOf('上層任務'));
    expect(move).toHaveBeenCalledWith('b', 'a');
    drag(cardOf('另一個任務'), cardOf('已完成任務'));
    expect(notify).toHaveBeenCalledWith('不能移到已完成、待確認或已略過的任務底下');
    expect(move).toHaveBeenCalledTimes(1);
    expect(mutate).not.toHaveBeenCalled();
  });

  it('refuses a move that would conflict with a dependency once edges are loaded', async () => {
    const fetch = vi.fn(() => Promise.resolve(response(deps([{ id: 'e1', predecessor_id: 'b', successor_id: 'a' }]))));
    vi.stubGlobal('fetch', fetch);
    const { move, notify } = workspace();
    fireEvent.mouseEnter(cardOf('另一個任務'));
    await waitFor(() => expect(fetch).toHaveBeenCalledWith('/api/projects/p/dependencies', expect.anything()));
    await act(async () => { await Promise.resolve(); });
    drag(cardOf('另一個任務'), cardOf('上層任務'));
    expect(notify).toHaveBeenCalledWith('移動後會和前置相依衝突，請先移除相依連線');
    expect(move).not.toHaveBeenCalled();
  });

  it('treats a drop on a card as a drop on its column when the user cannot move', () => {
    const memberNodes = nodes.map(n => n.id === 'b' ? { ...n, capabilities: { ...n.capabilities, move: false } } : n.id === 'a' ? { ...n, capabilities: { ...n.capabilities, move: false } } : n);
    const { move, openReport, mutate } = workspace({ project: { ...project, nodes: memberNodes } });
    expect(screen.getByText('拖曳卡片或用卡片上的狀態選單改狀態；點卡片標題進入下一層')).toBeInTheDocument();
    drag(cardOf('另一個任務'), cardOf('上層任務'));
    expect(mutate).not.toHaveBeenCalled();
    drag(cardOf('另一個任務'), cardOf('待確認任務'));
    expect(openReport).toHaveBeenCalledWith('b');
    expect(move).not.toHaveBeenCalled();
  });
});

describe('TP-A node-scoped tabs', () => {
  const dated = { ...project, nodes: nodes.map(n => ({ ...n, start_date: n.start_date ?? '2026-10-02', due_date: n.due_date ?? '2026-10-10' })) };
  it('limits the timeline to the node and its descendants with a way up', () => {
    const select = vi.fn(); const up = vi.fn();
    render(<TimelineView project={dated} scopeId="a" select={select} up={up} reload={vi.fn()} expired={vi.fn()} />);
    expect(screen.getAllByRole('button', { name: /^時程任務：/ }).map(b => b.getAttribute('aria-label'))).toEqual(
      ['時程任務：上層任務', '時程任務：子任務一', '時程任務：子任務二', '時程任務：孫任務', '時程任務：曾孫任務']);
    expect(screen.getByText('展開圖・子任務（4）')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '時程任務：上層任務' }).parentElement).toHaveAttribute('title', expect.stringContaining('進度 50%（涵蓋所有子任務）'));
    fireEvent.click(screen.getByRole('button', { name: '↑ 上一層：試作' }));
    expect(up).toHaveBeenCalledWith('ph');
  });

  it('shows the whole project with the overview header at project level', () => {
    render(<TimelineView project={dated} select={vi.fn()} reload={vi.fn()} expired={vi.fn()} />);
    expect(screen.getByText('總覽圖')).toBeInTheDocument();
    expect(screen.getByText('總覽圖・任務（9）')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /上一層/ })).not.toBeInTheDocument();
  });

  it('limits the dependency graph to tasks below the node and keeps touching edges in the list', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(response(deps([
      { id: 'e1', predecessor_id: 'a1', successor_id: 'a2' }, { id: 'e2', predecessor_id: 'b', successor_id: 'a1' }, { id: 'e3', predecessor_id: 'b', successor_id: 'c' }])))));
    const { unmount } = render(<DependencyPanel projectId="p" project={project} scopeId="a" select={vi.fn()} reload={vi.fn()} expired={vi.fn()} />);
    const graph = await screen.findByLabelText('可見任務相依圖');
    expect(within(graph).getAllByRole('button').map(b => b.getAttribute('aria-label'))).toEqual(
      expect.arrayContaining(['開啟任務：子任務一', '開啟任務：子任務二', '開啟任務：孫任務', '開啟任務：曾孫任務']));
    expect(within(graph).queryByRole('button', { name: '開啟任務：另一個任務' })).not.toBeInTheDocument();
    expect(within(graph).queryByRole('button', { name: '開啟任務：上層任務' })).not.toBeInTheDocument();
    expect(screen.getByText('連線清單（2）')).toBeInTheDocument();
    unmount();
    render(<DependencyPanel projectId="p" project={project} scopeId="c" select={vi.fn()} reload={vi.fn()} expired={vi.fn()} />);
    expect(await screen.findByText('沒有可顯示的任務。')).toBeInTheDocument();
    expect(screen.getByText('連線清單（1）')).toBeInTheDocument();
  });

  it('rolls up the whole project in the project-level records', async () => {
    const fetch = vi.fn(() => Promise.resolve(response({ items: [], next_cursor: null })));
    vi.stubGlobal('fetch', fetch);
    render(<RecordTimeline node={null} projectId="p" leaf={false} descendantTasks={9} userId="u1" reload={vi.fn()} expired={vi.fn()} select={vi.fn()} />);
    expect(await screen.findByText(/這是上層節點，以下彙總整棵子樹（9 個子任務）的紀錄，只能檢視/)).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledWith('/api/projects/p/records?limit=50', expect.anything());
    expect(screen.queryByLabelText('紀錄範圍')).not.toBeInTheDocument();
  });

  it('opens an upper task on its read-only subtree roll-up', async () => {
    const fetch = vi.fn(() => Promise.resolve(response({ items: [], next_cursor: null })));
    vi.stubGlobal('fetch', fetch);
    render(<RecordTimeline node={nodes[1]} projectId="p" leaf={false} descendantTasks={4} userId="u1" reload={vi.fn()} expired={vi.fn()} select={vi.fn()} />);
    expect(await screen.findByText(/（4 個子任務）/)).toBeInTheDocument();
    expect(screen.getByLabelText('紀錄範圍')).toHaveValue('subtree');
    expect(fetch).toHaveBeenCalledWith('/api/nodes/a/records?scope=subtree&limit=50', expect.anything());
  });
});

describe('TP-A report and editor', () => {
  it('opens the report form directly when coming from ✓ 回報', async () => {
    vi.stubGlobal('fetch', vi.fn((path: string) => Promise.resolve(path.endsWith('/attachment-quota')
      ? response({ limit_bytes: 1000000, charged_bytes: 0, remaining_bytes: 1000000 }) : response({ items: [], next_cursor: null }))));
    render(<ReportPanel node={nodes[6]} userId="u1" reload={vi.fn()} expired={vi.fn()} autoOpen />);
    expect(await screen.findByRole('form', { name: '回報表單' })).toBeInTheDocument();
  });

  it('explains open children instead of offering the report', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(response({ items: [], next_cursor: null }))));
    render(<ReportPanel node={nodes[1]} userId="u1" reload={vi.fn()} expired={vi.fn()} autoOpen openChildren={[nodes[3]]} />);
    expect(await screen.findByText('還有 1 項子任務未完成：子任務二；全部完成或略過後才能回報完成。')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '回報完成' })).not.toBeInTheDocument();
    expect(screen.queryByRole('form', { name: '回報表單' })).not.toBeInTheDocument();
  });

  it('edits weight and manual progress of a doing leaf task', async () => {
    const fetch = vi.fn((_path: string, _init?: RequestInit) => Promise.resolve(response({ ...nodes[6], weight: 3, progress: 30 })));
    vi.stubGlobal('fetch', fetch);
    const reload = vi.fn(async () => undefined);
    const doing = { ...nodes[6], status: 'doing' as NodeStatus };
    render(<NodeEditor projectId="p" mode="edit" node={doing} parent={null} canAssign={false} leaf reload={reload} close={vi.fn()} expired={vi.fn()} />);
    fireEvent.change(screen.getByLabelText('權重（彙總進度用）'), { target: { value: '1.5' } });
    expect(screen.getByRole('alert')).toHaveTextContent('權重需為 0–100 的整數');
    expect(screen.getByRole('button', { name: '儲存' })).toBeDisabled();
    fireEvent.change(screen.getByLabelText('權重（彙總進度用）'), { target: { value: '3' } });
    fireEvent.change(screen.getByLabelText(/進度 %/), { target: { value: '30' } });
    fireEvent.click(screen.getByRole('button', { name: '儲存' }));
    await waitFor(() => expect(reload).toHaveBeenCalledWith('b'));
    expect(fetch).toHaveBeenCalledWith('/api/nodes/b', expect.objectContaining({ method: 'PATCH', body: JSON.stringify({ weight: 3, progress: 30 }) }));
  });

  it('offers manual progress only for doing leaf tasks', () => {
    render(<NodeEditor projectId="p" mode="edit" node={nodes[1]} parent={null} canAssign={false} leaf={false} reload={vi.fn()} close={vi.fn()} expired={vi.fn()} />);
    expect(screen.getByLabelText('權重（彙總進度用）')).toHaveValue(1);
    expect(screen.queryByLabelText(/進度 %/)).not.toBeInTheDocument();
  });
});

describe('TP-A app flows', () => {
  const projects = { items: [{ id: 'p', title: '規劃器專案', organization_key: 'food', owner_user_id: 'u1' }] };
  const overview = { project_count: 0, task_counts: { todo: 0, doing: 0, review: 0, done: 0, skipped: 0 }, completion_percent: null, projects: [] };
  function app(role: string, extra: (path: string, init?: RequestInit) => unknown = () => undefined, detail: ProjectDetail = project) {
    const session = { user: { id: 'u1', username: 'yu', display_name: '游專案', role }, organization: { id: 'o1', key: 'food', name: '毛研食品' } };
    const fetch = vi.fn((path: string, init?: RequestInit) => {
      const custom = extra(path, init);
      if (custom !== undefined) return Promise.resolve(custom);
      return Promise.resolve(path === '/api/auth/me' ? response(session) : path === '/api/projects' ? response(projects)
        : path === '/api/workspace/overview' ? response(overview) : path.startsWith('/api/workspace/my-tasks') ? response({ items: [] })
          : path === '/api/projects/p' ? response(detail) : path.includes('/records?') ? response({ items: [], next_cursor: null })
            : response({}, 404));
    });
    vi.stubGlobal('fetch', fetch);
    render(<App />);
    return fetch;
  }
  async function openProject() {
    await screen.findByRole('heading', { name: '所有專案總覽' });
    fireEvent.click(within(screen.getByLabelText('專案清單')).getByRole('button', { name: '規劃器專案' }));
    await screen.findByRole('heading', { name: '規劃器專案' });
  }

  it('hides the unavailable template actions from read-only users', async () => {
    app('readonly');
    await openProject();
    expect(screen.queryByRole('button', { name: /另存為模板/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /套用模板/ })).not.toBeInTheDocument();
  });

  it('still shows them disabled to users who can edit', async () => {
    app('admin');
    await openProject();
    expect(screen.getByRole('button', { name: /另存為模板/ })).toBeDisabled();
  });

  it('opens the task with its report form from a card ✓ 回報', async () => {
    app('admin');
    await openProject();
    fireEvent.click(within(screen.getByLabelText('開發階段與閘門')).getByRole('button', { name: '進入階段：試作' }));
    fireEvent.click(await screen.findByRole('button', { name: '回報完成：另一個任務' }));
    expect(await screen.findByRole('heading', { name: '另一個任務' })).toBeInTheDocument();
    expect(await screen.findByRole('form', { name: '回報表單' })).toBeInTheDocument();
  });

  it('moves a card and reloads the project with a confirmation', async () => {
    let moved = false;
    const fetch = app('admin', path => path === '/api/nodes/b/move' ? (moved = true, response({ ...nodes[6], parent_id: 'a' }))
      : path === '/api/projects/p' && moved ? response({ ...project, nodes: project.nodes.map(n => n.id === 'b' ? { ...n, parent_id: 'a' } : n) }) : undefined);
    await openProject();
    fireEvent.click(within(screen.getByLabelText('開發階段與閘門')).getByRole('button', { name: '進入階段：試作' }));
    drag(cardOf('另一個任務'), cardOf('上層任務'));
    expect(await screen.findByText('已將「另一個任務」移到「上層任務」底下')).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledWith('/api/nodes/b/move', expect.objectContaining({ method: 'POST', body: JSON.stringify({ parent_id: 'a' }) }));
    expect(cardOf('上層任務')).toHaveTextContent('1/3 子任務');
  });

  it('shows the fixed parent-completion conflict when only hidden children are open', async () => {
    const visibleDone = { ...project, nodes: [nodes[0], nodes[9]] };
    const fetch = app('admin', path => path === '/api/nodes/ph/status' ? response({ detail: '子節點尚未全部完成' }, 409) : undefined, visibleDone);
    await openProject();
    fireEvent.click(within(screen.getByLabelText('開發階段與閘門')).getByRole('button', { name: '進入階段：試作' }));
    fireEvent.change(within(screen.getByLabelText('節點詳情')).getByRole('combobox', { name: '試作狀態' }), { target: { value: 'done' } });
    expect(await screen.findByText('子節點尚未全部完成')).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledWith('/api/nodes/ph/status', expect.objectContaining({ method: 'PATCH', body: JSON.stringify({ status: 'done' }) }));
    // Any other conflict text from the API stays hidden behind the generic message.
  });

  it('creates a project from a template card in the library', async () => {
    const workflows = { items: [{ id: 'w1', name: '食品新品開發', phase_count: 2, task_count: 5, capabilities: { edit: true, copy: true } }], capabilities: { create: true } };
    const created = { id: 'p2', title: '新罐頭', organization_key: 'food', owner_user_id: 'u1' };
    const fetch = app('admin', path => path === '/api/workflows' ? response(workflows) : path === '/api/projects/from-workflow' ? response(created, 201)
      : path === '/api/projects/p2' ? response({ ...created, nodes: [], gates: [], capabilities: { create_node: true } }) : undefined);
    await screen.findByRole('heading', { name: '所有專案總覽' });
    fireEvent.click(within(screen.getByLabelText('工作區導覽')).getByRole('button', { name: '模板庫' }));
    fireEvent.click(await screen.findByRole('button', { name: '用這套工作流建立專案' }));
    const form = await screen.findByRole('form', { name: '建立新專案' });
    await waitFor(() => expect(within(form).getByLabelText('工作流模板')).toHaveValue('w1'));
    fireEvent.change(within(form).getByLabelText('新專案名稱'), { target: { value: '新罐頭' } });
    fireEvent.click(within(form).getByRole('button', { name: '建立專案' }));
    await waitFor(() => expect(fetch).toHaveBeenCalledWith('/api/projects/from-workflow', expect.objectContaining({ method: 'POST', body: JSON.stringify({ workflow_id: 'w1', title: '新罐頭' }) })));
    expect(await screen.findByRole('heading', { name: '新罐頭' })).toBeInTheDocument();
  });
});
