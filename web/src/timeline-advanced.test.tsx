import { beforeEach as beforeTpG } from 'vitest';
import { api as tpGApi } from './api';
beforeTpG(() => { vi.spyOn(tpGApi, 'reportFields').mockResolvedValue({fields:[],version:0,active:true,can_edit:true}); });
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import TimelineView, { shiftDates } from './components/TimelineView';
import NodeEditor from './components/NodeEditor';
import { calendarDay, criticalChain, departmentNodes, timelineSpans, visibleEndpoint } from './timeline';
import type { Dependency, NodeItem, ProjectDetail } from './types';

const n = (id: string, parent_id: string | null = null, extra: Partial<NodeItem> = {}): NodeItem => ({
  id, parent_id, project_id: 'p', kind: 'task', title: id, status: 'todo', sort_order: 0,
  start_date: '2026-10-01', due_date: '2026-10-03', owner_user_id: null, owner_display_name: null,
  department_id: 'rd', department_name: '研發', capabilities: { edit_metadata: true, edit_schedule: true, assign: false, create_child: true, lock_schedule: true }, ...extra,
});
const edge = (a: string, b: string): Dependency => ({ id: `${a}-${b}`, project_id: 'p', predecessor_id: a, successor_id: b });
const nodes = [n('parent', null, { kind: 'phase', due_date: '2026-10-10' }), n('a', 'parent'), n('b', 'parent', { start_date: '2026-10-05', due_date: '2026-10-12', department_id: 'qa', department_name: '品保' })];
const project: ProjectDetail = { id: 'p', title: '專案', organization_key: 'food', owner_user_id: 'u', gates: [], capabilities: { create_node: true }, nodes };
const response = (body: unknown, status = 200) => ({ ok: status < 400, status, json: async () => body });
afterEach(() => vi.restoreAllMocks());

describe('TP-C calculations', () => {
  it('envelopes own plans and descendants without rewriting nodes', () => {
    const original = JSON.stringify(nodes);
    expect(timelineSpans(nodes).get('parent')).toEqual({ start: calendarDay('2026-10-01'), due: calendarDay('2026-10-12') });
    expect(JSON.stringify(nodes)).toBe(original);
    expect(timelineSpans([n('p', null, { start_date: null, due_date: null }), n('c', 'p')]).get('p')?.due).toBe(calendarDay('2026-10-03'));
  });
  it('filters responsible departments and retains only visible paths', () => {
    expect(departmentNodes([...nodes, n('unrelated', null, { kind: 'phase' })], 'qa').map(n => n.id)).toEqual(['parent', 'b']);
    expect(departmentNodes([n('orphan', 'hidden', { department_id: null })], 'none').map(n => n.id)).toEqual(['orphan']);
    expect(visibleEndpoint('b', nodes, new Set(['parent']))).toBe('parent');
    expect(visibleEndpoint('hidden', nodes, new Set(['parent']))).toBeNull();
  });
  it('supports left resizing, date limits and nonnegative duration', () => {
    expect(shiftDates('2026-10-01', '2026-10-03', 9, 'left')).toEqual({ start_date: '2026-10-03', due_date: '2026-10-03' });
    expect(shiftDates('0001-01-01', '0001-01-03', -9, 'left').start_date).toBe('0001-01-01');
  });
  it('highlights a stable limiting chain through a fork and join', () => {
    const input = [n('a'), n('b', null, { due_date: '2026-10-08' }), n('c'), n('d')];
    const chain = criticalChain(input, [edge('a', 'b'), edge('a', 'c'), edge('b', 'd'), edge('c', 'd')]);
    expect(chain.invalid).toBe(false);
    expect([...chain.nodes].sort()).toEqual(['a', 'b', 'd']);
    expect([...chain.edges].sort()).toEqual(['a-b', 'b-d']);
  });
  it('maps parent links to leaves, handles missing dates and detects cycles', () => {
    const input = [...nodes, n('end', null, { start_date: '2026-10-14', due_date: '2026-10-14' })];
    const chain = criticalChain(input, [edge('parent', 'end')]);
    expect(chain.edges.has('parent-end')).toBe(true);
    expect(chain.nodes.has('b')).toBe(true);
    expect(criticalChain([n('blank', null, { start_date: null, due_date: null })], []).nodes.size).toBe(0);
    expect(criticalChain([n('a'), n('b')], [edge('a', 'b'), edge('b', 'a')]).invalid).toBe(true);
    expect(timelineSpans([n('a', 'b'), n('b', 'a')]).size).toBe(2);
  });
});

describe('TP-C interactions', () => {
  function mount(items = nodes, reload = vi.fn()) {
    return render(<TimelineView project={{ ...project, nodes: items }} select={vi.fn()} reload={reload} expired={vi.fn()} />);
  }
  it('draws arrows, removes filtered endpoints and prevents dragging parent bars', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({ items: [edge('a', 'b')] })));
    const { container } = mount();
    await waitFor(() => expect(container.querySelector('[data-edge-id="a-b"]')).toBeInTheDocument());
    expect(screen.queryByRole('button', { name: '調整截止日：parent' })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '品保 1' }));
    expect(screen.queryByRole('button', { name: '時程任務：a' })).not.toBeInTheDocument();
    expect(container.querySelector('[data-edge-id="a-b"]')).not.toBeInTheDocument();
  });
  it('loads project edges even when first mounted at one leaf and then moving up', async () => {
    const fetcher = vi.fn().mockResolvedValue(response({ items: [edge('a', 'b')] })); vi.stubGlobal('fetch', fetcher);
    const props = { project, select: vi.fn(), reload: vi.fn(), expired: vi.fn() };
    const { rerender, container } = render(<TimelineView {...props} scopeId="a" />);
    await waitFor(() => expect(fetcher).toHaveBeenCalledOnce());
    rerender(<TimelineView {...props} scopeId={null} />);
    await waitFor(() => expect(container.querySelector('[data-edge-id="a-b"]')).toBeInTheDocument());
  });
  it('keeps a failed cascade draft and sends the explicit cascade choice', async () => {
    const fetcher = vi.fn().mockResolvedValue(response({ detail: '後續任務有無法調整的項目，請由專案負責人確認' }, 409));
    vi.stubGlobal('fetch', fetcher);
    const reload = vi.fn(); mount([n('a')], reload);
    expect(screen.getByLabelText('後續相依自動順延')).not.toBeChecked();
    fireEvent.click(screen.getByLabelText('後續相依自動順延'));
    fireEvent.click(screen.getByRole('button', { name: '調整日期：a' }));
    fireEvent.change(screen.getByLabelText('截止日期'), { target: { value: '2026-10-07' } });
    fireEvent.click(screen.getByRole('button', { name: '儲存日期' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('後續任務有無法調整的項目');
    expect(screen.getByLabelText('截止日期')).toHaveValue('2026-10-07');
    expect(reload).not.toHaveBeenCalled();
    expect(JSON.parse(fetcher.mock.calls[0][1].body)).toEqual({ start_date: '2026-10-01', due_date: '2026-10-07', cascade: true });
  });
  it('milestones have no resize handles; locked dates and child creation are unavailable', () => {
    mount([n('m', null, { milestone: true, schedule_locked: true, due_date: '2026-10-01', capabilities: { edit_metadata: true, edit_schedule: false, assign: false, create_child: true } })]);
    expect(screen.queryByRole('button', { name: '調整日期：m' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '調整截止日：m' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: '新增子任務：m' })).toBeDisabled();
    expect(screen.getByRole('button', { name: '新增子任務：m' })).toHaveAccessibleDescription('里程碑不能有子任務，請先取消里程碑');
  });
  it('row plus opens the existing task form, cancel makes no business write', async () => {
    const fetcher = vi.fn().mockResolvedValue(response({ users: [], departments: [] })); vi.stubGlobal('fetch', fetcher);
    mount([n('a')]);
    fireEvent.click(screen.getByRole('button', { name: '新增子任務：a' }));
    const form = screen.getByRole('form', { name: '新增節點表單' });
    await waitFor(() => expect(within(form).getByLabelText('負責人')).not.toBeDisabled());
    expect(within(form).getByLabelText('種類')).toHaveValue('task');
    fireEvent.click(within(form).getByRole('button', { name: '取消' }));
    expect(screen.queryByRole('form')).not.toBeInTheDocument();
    expect(fetcher.mock.calls.every(([, init]) => !init.method || init.method === 'GET')).toBe(true);
  });
  it('Escape closes the creation dialog, asking first when it has a draft', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({ users: [], departments: [] })));
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false);
    mount([n('a')]);
    const escape = () => fireEvent(document.querySelector('dialog.timeline-create-dialog')!, new Event('cancel', { cancelable: true }));
    fireEvent.click(screen.getByRole('button', { name: '新增子任務：a' }));
    escape();
    expect(confirm).not.toHaveBeenCalled();
    expect(screen.queryByRole('form', { name: '新增節點表單' })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '新增子任務：a' }));
    fireEvent.change(screen.getByLabelText('節點名稱'), { target: { value: '草稿' } });
    escape();
    expect(confirm).toHaveBeenCalledTimes(1);
    expect(screen.getByLabelText('節點名稱')).toHaveValue('草稿');
    confirm.mockReturnValue(true);
    escape();
    expect(screen.queryByRole('form', { name: '新增節點表單' })).not.toBeInTheDocument();
  });
  it('editor keeps milestone dates equal and sends both flags', async () => {
    const item = n('a', null, { capabilities: { edit_metadata: true, edit_schedule: true, lock_schedule: true, assign: false, create_child: false } });
    const fetcher = vi.fn().mockResolvedValue(response(item)); vi.stubGlobal('fetch', fetcher);
    render(<NodeEditor projectId="p" mode="edit" node={item} parent={null} leaf canAssign={false} reload={vi.fn()} close={vi.fn()} expired={vi.fn()} />);
    fireEvent.click(screen.getByLabelText('里程碑（單日）'));
    fireEvent.change(screen.getByLabelText('開始日期'), { target: { value: '2026-10-08' } });
    expect(screen.getByLabelText('截止日期')).toHaveValue('2026-10-08');
    expect(screen.getByLabelText('截止日期')).toBeDisabled();
    fireEvent.click(screen.getByLabelText('鎖定時程'));
    fireEvent.submit(screen.getByRole('form'));
    await waitFor(() => expect(fetcher).toHaveBeenCalledOnce());
    expect(JSON.parse(fetcher.mock.calls[0][1].body)).toMatchObject({ milestone: true, schedule_locked: true, start_date: '2026-10-08', due_date: '2026-10-08' });
  });
});
