import { findProjectMenu } from './test-navigation';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import TimelineView from './components/TimelineView';
import App from './App';
import type { NodeItem, ProjectDetail } from './types';
const n = (id: string, extra: Partial<NodeItem> = {}): NodeItem => ({ id, title: id, parent_id: null, project_id: 'p', kind: 'task', status: 'todo', sort_order: 0,
 start_date: '2026-10-12', due_date: '2026-10-15', owner_user_id: null, department_id: null, owner_display_name: null, department_name: null,
 capabilities: { create_child: true, edit_metadata: true, edit_schedule: true, assign: true }, ...extra });
const project: ProjectDetail = { id: 'p', title: '測試專案', organization_key: 'food', owner_user_id: 'u', nodes: [n('parent', { kind: 'phase' }), n('child', { parent_id: 'parent' }), n('closed', { status: 'done' })], gates: [], capabilities: { create_node: true } };
const response = (body: unknown, status = 200) => ({ ok: status < 400, status, json: async () => body });
function stub(detail = project) {
 const fetcher = vi.fn((path: string, _init?: RequestInit) => Promise.resolve(response(
 path === '/api/auth/me' ? { user: { id: 'u', username: 'yu', display_name: '游', role: 'admin' }, organization: { id: 'o', key: 'food', name: '測試公司' } }
 : path === '/api/projects' ? { items: [detail] } : path === '/api/projects/p' ? detail
 : path.includes('assignment-options') ? { users: [], departments: [] }
 : path.includes('overview') ? { project_count: 1, task_counts: { todo: 2, doing: 0, review: 0, done: 1, skipped: 0 }, completion_percent: 33, projects: [] }
 : { items: [], nodes: [], capabilities: {}, next_cursor: null })));
 vi.stubGlobal('fetch', fetcher); return fetcher;
}
describe('child creation and navigation', () => {
 it('describes every blocked row including permission and milestone', () => {
 stub(); render(<TimelineView project={{ ...project, nodes: [n('closed', { status: 'done' }), n('milestone', { milestone: true }), n('denied', { capabilities: { create_child: false, edit_metadata: false, assign: false } })] }} select={vi.fn()} reload={vi.fn()} expired={vi.fn()} />);
 for (const [id, reason] of [['closed', '不能在已完成、待確認或已略過的節點底下新增'], ['milestone', '里程碑不能有子任務，請先取消里程碑'], ['denied', '只有系統管理員或此專案負責人可以新增子任務']]) {
 const button = screen.getByRole('button', { name: `新增子任務：${id}` });
 expect(button).toBeDisabled(); expect(button).toHaveAccessibleDescription(reason);
 }
 });
 it('lets users choose the parent for date dragging and labels the modal destination', async () => {
 const fetcher = stub(); render(<TimelineView project={project} select={vi.fn()} reload={vi.fn()} expired={vi.fn()} />);
 fireEvent.change(screen.getByLabelText('新增位置'), { target: { value: 'parent' } });
 fireEvent.click(screen.getByRole('button', { name: '＋ 新增子任務' }));
 const dialog = screen.getByRole('dialog', { name: '新增子任務' });
 expect(dialog).toHaveTextContent('新增位置：parent');
 await waitFor(() => expect(within(dialog).getByLabelText('負責人')).not.toBeDisabled());
 fireEvent.click(within(dialog).getByRole('button', { name: '取消' }));
 expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
 expect(fetcher.mock.calls.every(call => !call[1]?.method)).toBe(true);
 });
 it('opens an editable timeline bar on a touch click', () => {
 stub(); const select = vi.fn(); render(<TimelineView project={project} select={select} reload={vi.fn()} expired={vi.fn()} />);
 const bar = screen.getByRole('button', { name: '時程任務：child' });
 fireEvent.pointerDown(bar, { pointerType: 'touch' }); fireEvent.pointerUp(bar, { pointerType: 'touch' }); fireEvent.click(bar, { detail: 1 });
 expect(select).toHaveBeenCalledOnce(); expect(select).toHaveBeenCalledWith('child');
 });
 it('keeps the timeline on leaf drill-down and breadcrumbs back up', async () => {
 stub(); render(<App />);
 fireEvent.click(await within(await findProjectMenu()).findByRole('button', { name: '測試專案' }));
 fireEvent.click(await screen.findByRole('tab', { name: '時程' }));
 fireEvent.click(await screen.findByRole('button', { name: 'child' }));
 expect(screen.getByRole('tab', { name: '時程' })).toHaveAttribute('aria-selected', 'true');
 expect(screen.getByLabelText('目前層級')).toHaveTextContent('第 2 層');
 fireEvent.click(within(screen.getByRole('navigation', { name: '節點路徑' })).getByRole('button', { name: 'parent' }));
 expect(screen.getByRole('tab', { name: '時程' })).toHaveAttribute('aria-selected', 'true');
 expect(screen.getByLabelText('目前層級')).toHaveTextContent('第 1 層');
 });
});

describe('persistent timeline state', () => {
 it('falls back to the visible scope if the chosen parent is undone', async () => {
   stub();
   const props = { project, scopeId: 'parent', select: vi.fn(), reload: vi.fn(), expired: vi.fn() };
   const view = render(<TimelineView {...props} />);
   fireEvent.change(screen.getByLabelText('新增位置'), { target: { value: 'child' } });
   view.rerender(<TimelineView {...props} project={{ ...project, nodes: project.nodes.filter(n => n.id !== 'child') }} recordVersion={1} />);
   expect(screen.getByLabelText('新增位置')).toHaveValue('parent');
   fireEvent.click(screen.getByRole('button', { name: '＋ 新增子任務' }));
   expect(screen.getByRole('dialog')).toHaveTextContent('新增位置：parent');
   await waitFor(() => expect(screen.getByLabelText('負責人')).not.toBeDisabled());
 });
 it('allows another date edit after a successful reload without remounting', async () => {
   const fetcher = stub(); const reload = vi.fn().mockResolvedValue(undefined);
   render(<TimelineView project={project} select={vi.fn()} reload={reload} expired={vi.fn()} />);
   for (const day of ['2026-10-20', '2026-10-21']) {
     fireEvent.click(screen.getByRole('button', { name: '調整日期：child' }));
     fireEvent.change(screen.getByLabelText('截止日期'), { target: { value: day } });
     fireEvent.click(screen.getByRole('button', { name: '儲存日期' }));
     await waitFor(() => expect(screen.queryByRole('form', { name: '日期表單' })).not.toBeInTheDocument());
     expect(screen.getByRole('button', { name: '調整日期：child' })).not.toBeDisabled();
   }
   expect(reload).toHaveBeenCalledTimes(2);
   expect(fetcher.mock.calls.filter(call => call[0] === '/api/nodes/child/schedule')).toHaveLength(2);
 });
});
