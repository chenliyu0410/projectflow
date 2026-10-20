import { closeProjectDrawer, findProjectMenu } from './test-navigation';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App';
import { api } from './api';

beforeEach(() => { vi.spyOn(api, 'reportFields').mockResolvedValue({ fields: [], version: 0, active: true, can_edit: true }); });
const response = (body: unknown, status = 200) => ({ ok: status < 400, status, json: async () => body });
const identity = { user: { id: 'u', display_name: '成員', role: 'member' }, organization: { id: 'o', name: '公司' } };
const summary = { id: 'p', title: '離開專案', owner_user_id: 'other' };
const second = { id: 'q', title: '另一個專案', owner_user_id: 'other' };
const task = { id: 'n', project_id: 'p', parent_id: null, kind: 'task', title: '原任務', status: 'todo', owner_user_id: 'u', department_id: null, sort_order: 0,
  start_date: '2026-10-08', due_date: '2026-10-12', owner_display_name: '成員', department_name: null, capabilities: { edit_metadata: true, edit_schedule: true, assign: false, create_child: false } };
const detail = { ...summary, nodes: [task], gates: [], capabilities: { create_node: false } };
const overview = { project_count: 2, task_counts: { todo: 1, doing: 0, review: 0, done: 0, skipped: 0 }, completion_percent: 0, projects: [] };
function setup() {
  vi.stubGlobal('fetch', vi.fn(async (path: string) => {
    if (path === '/api/auth/me') return response(identity);
    if (path === '/api/projects') return response({ items: [summary, second] });
    if (path === '/api/workspace/overview') return response(overview);
    if (path === '/api/projects/p') return response(detail);
    if (path === '/api/projects/q') return response({ ...second, nodes: [], gates: [], capabilities: { create_node: false } });
    if (path.includes('/records?')) return response({ items: [], next_cursor: null });
    if (path.endsWith('/collaborators')) return response({ users: [], departments: [], revision: 0 });
    if (path.endsWith('/attachment-quota')) return response({ limit_bytes: 1, charged_bytes: 0, remaining_bytes: 1 });
    if (path.endsWith('/dependencies')) return response({ items: [], nodes: [] });
    if (path.startsWith('/api/workspace/my-tasks')) return response({ items: [] });
    if (path.startsWith('/api/notifications')) return response({ items: [], unread_count: 0, next_offset: null });
    throw Error(`unexpected ${path}`);
  }));
  render(<App />);
}
async function openTask() {
  fireEvent.click(await within(await findProjectMenu()).findByRole('button', { name: summary.title }));
  closeProjectDrawer();
  fireEvent.click(within(await screen.findByLabelText('看板')).getByRole('button', { name: '原任務' }));
}
const nav = (name: RegExp) => within(screen.getByRole('navigation', { name: '工作區導覽' })).getByRole('button', { name });

describe('unsaved form leave guard', () => {
  it('asks before leaving an edited node form for another node, tab or page', async () => {
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false);
    setup(); await openTask();
    fireEvent.click(await screen.findByRole('button', { name: '編輯節點' }));
    fireEvent.change(screen.getByLabelText('節點名稱'), { target: { value: '改到一半' } });
    fireEvent.click(within(screen.getByRole('navigation', { name: '節點路徑' })).getByRole('button', { name: summary.title }));
    fireEvent.click(screen.getByRole('tab', { name: '看板' }));
    fireEvent.click(nav(/我的任務/));
    expect(confirm).toHaveBeenCalledTimes(3);
    expect(confirm.mock.calls[0][0]).toContain('未儲存');
    expect(screen.getByLabelText('節點名稱')).toHaveValue('改到一半');
    confirm.mockReturnValue(true);
    fireEvent.click(nav(/我的任務/));
    expect(await screen.findByRole('heading', { name: '我的任務' })).toBeInTheDocument();
  });

  it('does not ask when the node form is unchanged', async () => {
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false);
    setup(); await openTask();
    fireEvent.click(await screen.findByRole('button', { name: '編輯節點' }));
    fireEvent.click(nav(/我的任務/));
    expect(confirm).not.toHaveBeenCalled();
    expect(await screen.findByRole('heading', { name: '我的任務' })).toBeInTheDocument();
  });

  it('asks before leaving a changed timeline date form', async () => {
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false);
    setup();
    fireEvent.click(await within(await findProjectMenu()).findByRole('button', { name: summary.title }));
    closeProjectDrawer();
    fireEvent.click(await screen.findByRole('tab', { name: '時程' }));
    fireEvent.click(await screen.findByRole('button', { name: '調整日期：原任務' }));
    fireEvent.change(screen.getByLabelText('開始日期'), { target: { value: '2026-10-09' } });
    fireEvent.click(screen.getByRole('tab', { name: '看板' }));
    expect(confirm).toHaveBeenCalledTimes(1);
    expect(screen.getByLabelText('開始日期')).toHaveValue('2026-10-09');
    confirm.mockReturnValue(true);
    fireEvent.click(screen.getByRole('tab', { name: '看板' }));
    await waitFor(() => expect(screen.queryByLabelText('日期表單')).not.toBeInTheDocument());
  });

  it('warns the browser before unload while a node form is changed', async () => {
    setup(); await openTask();
    fireEvent.click(await screen.findByRole('button', { name: '編輯節點' }));
    fireEvent.change(screen.getByLabelText('節點名稱'), { target: { value: '改到一半' } });
    const event = new Event('beforeunload', { cancelable: true });
    window.dispatchEvent(event);
    expect(event.defaultPrevented).toBe(true);
  });
});
