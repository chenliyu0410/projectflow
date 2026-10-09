import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import App from './App';
import NodeEditor from './components/NodeEditor';
import type { NodeItem } from './types';

function stubFetch(fetcher: (path: string, init?: RequestInit) => unknown) {
 vi.stubGlobal('fetch', (path: string, init?: RequestInit) => path.includes('/records?') ? Promise.resolve(response({ items: [], next_cursor: null }))
 : path.endsWith('/collaborators') ? Promise.resolve(response({ users: [], departments: [], revision: 0 }))
 : path.endsWith('/attachment-quota') ? Promise.resolve(response({ limit_bytes: 1000000000, charged_bytes: 0, remaining_bytes: 1000000000 })) : fetcher(path, init));
}
const identity = { user: { id: 'u', display_name: '成員', role: 'member' }, organization: { id: 'o', name: '公司' } };
const summary = { id: 'p', title: '編輯專案', owner_user_id: 'other' };
const task = { id: 'n', project_id: 'p', parent_id: null, kind: 'task', title: '原任務', status: 'todo', owner_user_id: 'u', department_id: null, sort_order: 0,
  start_date: '2026-10-08', due_date: '2026-10-12', owner_display_name: '成員', department_name: null, capabilities: { edit_metadata: true, assign: false, create_child: false } };
const detail = { ...summary, nodes: [task], gates: [], capabilities: { create_node: false } };
const overview = { project_count: 1, task_counts: { todo: 1, doing: 0, review: 0, done: 0, skipped: 0 }, completion_percent: 0, projects: [] };
const response = (body: unknown, status = 200) => ({ ok: status < 400, status, json: async () => body });
async function openEditor() {
  fireEvent.click(await within(await screen.findByLabelText('專案清單')).findByRole('button', { name: summary.title }));
  const tree = await screen.findByLabelText('節點樹');
  fireEvent.click(within(tree).getByRole('button', { name: '原任務' }));
  fireEvent.click(screen.getByRole('button', { name: '編輯節點' }));
}
function setup(write: () => Promise<unknown> = async () => response(task), role = 'member') {
  const fetcher = vi.fn(async (path: string, init?: RequestInit) => {
    if (path === '/api/auth/me') return response({ ...identity, user: { ...identity.user, role } });
    if (path === '/api/projects') return response({ items: [summary] });
    if (path === '/api/workspace/overview') return response(overview);
    if (path === '/api/projects/p') return response(detail);
    if (path === '/api/nodes/n' && init?.method === 'PATCH') return write();
    if (path === '/api/auth/logout') return response(undefined, 204);
    throw Error(`unexpected ${path}`);
  });
  stubFetch( fetcher); render(<App />); return fetcher;
}

describe('P2a node editor', () => {
  it.each(['create', 'edit'])('preserves a replacement %s editor draft when an older saved-node reload completes', async mode => {
    let reads = 0; let finishReload!: (value: unknown) => void;
    const manageable = { ...detail, nodes: [{ ...task, capabilities: { edit_metadata: true, assign: true, create_child: true } }], capabilities: { create_node: true } };
    const fetcher = vi.fn(async (path: string) => {
      if (path === '/api/auth/me') return response({ ...identity, user: { ...identity.user, role: 'admin' } });
      if (path === '/api/projects') return response({ items: [summary] });
      if (path === '/api/workspace/overview') return response(overview);
      if (path === '/api/projects/p') return ++reads === 1 ? response(manageable) : new Promise(resolve => { finishReload = resolve; });
      if (path.endsWith('/assignment-options')) return response(options);
      if (path === '/api/nodes/n') return response({ ...task, title: '已儲存舊表單' });
      throw Error('unexpected path');
    });
    stubFetch( fetcher); render(<App />); await openEditor();
    await screen.findByRole('option', { name: '成員' });
    fireEvent.change(screen.getByLabelText('節點名稱'), { target: { value: '已儲存舊表單' } });
    fireEvent.click(screen.getByRole('button', { name: '儲存' }));
    await waitFor(() => expect(reads).toBe(2));
    fireEvent.click(screen.getByRole('button', { name: mode === 'create' ? '新增子節點' : '編輯節點' }));
    await screen.findByRole('option', { name: '成員' });
    fireEvent.change(screen.getByLabelText('節點名稱'), { target: { value: '新表單草稿' } });
    await act(async () => { finishReload(response(manageable)); });
    expect(screen.getByLabelText('節點名稱')).toHaveValue('新表單草稿');
    expect(screen.getByRole('button', { name: '儲存' })).not.toBeDisabled();
  });

  it('retries failed project reload after PATCH using only GET', async () => {
    let reads = 0;
    const fetcher = vi.fn(async (path: string) => {
      if (path === '/api/auth/me') return response(identity);
      if (path === '/api/projects') return response({ items: [summary] });
      if (path === '/api/workspace/overview') return response(overview);
      if (path === '/api/projects/p') return ++reads === 2 ? response({}, 500) : response(detail);
      if (path === '/api/nodes/n') return response(task);
      throw Error('unexpected path');
    });
    stubFetch( fetcher); render(<App />); await openEditor();
    fireEvent.change(screen.getByLabelText('節點名稱'), { target: { value: '改名' } }); fireEvent.click(screen.getByRole('button', { name: '儲存' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('已儲存，資料重新載入失敗');
    fireEvent.click(screen.getByRole('button', { name: '重試載入' }));
    await waitFor(() => expect(screen.queryByRole('button', { name: '重試載入' })).not.toBeInTheDocument());
    expect(reads).toBe(3); expect(fetcher.mock.calls.filter(([path]) => path === '/api/nodes/n')).toHaveLength(1);
  });

  it('selects a newly created node and closes the editor after reloading', async () => {
    let created = false;
    const fetcher = vi.fn(async (path: string) => {
      if (path === '/api/auth/me') return response({ ...identity, user: { ...identity.user, role: 'admin' } });
      if (path === '/api/projects') return response({ items: [summary] });
      if (path === '/api/workspace/overview') return response(overview);
      if (path === '/api/projects/p') return response({ ...detail, nodes: created ? [task] : [], capabilities: { create_node: true } });
      if (path.endsWith('/assignment-options')) return response(options);
      if (path === '/api/projects/p/nodes') { created = true; return response(task, 201); }
      throw Error('unexpected path');
    });
    stubFetch( fetcher); render(<App />);
    fireEvent.click(await within(await screen.findByLabelText('專案清單')).findByRole('button', { name: summary.title }));
    fireEvent.click(await screen.findByRole('button', { name: '新增子節點' }));
    await screen.findByRole('option', { name: '成員' });
    fireEvent.change(screen.getByLabelText('節點名稱'), { target: { value: task.title } });
    fireEvent.click(screen.getByRole('button', { name: '儲存' }));
    await waitFor(() => expect(screen.queryByLabelText('節點名稱')).not.toBeInTheDocument());
    expect(screen.getByLabelText('節點詳情')).toHaveTextContent(task.title);
    expect(within(screen.getByLabelText('節點樹')).getByRole('button', { name: task.title })).toHaveAttribute('aria-pressed', 'true');
  });

  it('hides editing and creation even if readonly receives historical editor capabilities', async () => {
    const fetcher = setup(undefined, 'readonly');
    fireEvent.click(await within(await screen.findByLabelText('專案清單')).findByRole('button', { name: summary.title }));
    fireEvent.click(within(await screen.findByLabelText('節點樹')).getByRole('button', { name: '原任務' }));
    expect(screen.queryByRole('button', { name: '編輯節點' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '新增子節點' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '建立新專案' })).not.toBeInTheDocument();
    expect(fetcher.mock.calls.some(([path]) => path.includes('assignment-options'))).toBe(false);
  });

  it('clears drafts on logout and ignores a late write expiry', async () => {
    let finish!: (value: unknown) => void;
    const fetcher = setup(() => new Promise(resolve => { finish = resolve; })); await openEditor();
    fireEvent.change(screen.getByLabelText('節點名稱'), { target: { value: '登出清除' } }); fireEvent.click(screen.getByRole('button', { name: '儲存' }));
    fireEvent.click(screen.getByRole('button', { name: '登出' }));
    await screen.findByRole('heading', { name: '登入專流' });
    await act(async () => { finish(response({}, 401)); });
    expect(screen.queryByLabelText('節點名稱')).not.toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(fetcher.mock.calls.filter(([path]) => path === '/api/projects/p')).toHaveLength(1);
  });

  it('cancels without a write and rejects reversed dates', async () => {
    const fetcher = setup(); await openEditor();
    expect(screen.getByRole('button', { name: '儲存' })).toBeDisabled();
    fireEvent.change(screen.getByLabelText('開始日期'), { target: { value: '2026-10-13' } });
    expect(screen.getByRole('alert')).toHaveTextContent('開始日期不得晚於截止日期');
    expect(screen.getByRole('button', { name: '儲存' })).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: '取消' }));
    expect(screen.queryByLabelText('節點名稱')).not.toBeInTheDocument();
    expect(fetcher.mock.calls.some(([path]) => path === '/api/nodes/n')).toBe(false);
  });

  it('edits only dirty metadata and clears dates with null without requesting assignment options', async () => {
    const fetcher = setup(); await openEditor();
    expect(screen.queryByLabelText('負責人', { exact: true })).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('節點名稱'), { target: { value: '新任務' } });
    fireEvent.change(screen.getByLabelText('開始日期'), { target: { value: '' } });
    fireEvent.click(screen.getByRole('button', { name: '儲存' }));
    await waitFor(() => expect(screen.queryByLabelText('節點名稱')).not.toBeInTheDocument());
    expect(fetcher).toHaveBeenCalledWith('/api/nodes/n', expect.objectContaining({ method: 'PATCH', body: JSON.stringify({ title: '新任務', start_date: null }) }));
    expect(fetcher.mock.calls.some(([path]) => path.includes('assignment-options'))).toBe(false);
  });

  it('keeps input on safe validation errors and does not duplicate a pending write', async () => {
    let finish!: (value: unknown) => void;
    const fetcher = setup(() => new Promise(resolve => { finish = resolve; })); await openEditor();
    fireEvent.change(screen.getByLabelText('節點名稱'), { target: { value: '保留輸入' } });
    const save = screen.getByRole('button', { name: '儲存' }); fireEvent.click(save); fireEvent.click(save);
    expect(save).toBeDisabled(); expect(screen.getByRole('button', { name: '取消' })).toBeDisabled();
    await act(async () => { finish(response({ detail: 'private-secret' }, 422)); });
    expect(await screen.findByRole('alert')).toHaveTextContent('請檢查欄位內容');
    expect(screen.getByLabelText('節點名稱')).toHaveValue('保留輸入');
    expect(document.body).not.toHaveTextContent('private-secret');
    expect(fetcher.mock.calls.filter(([path]) => path === '/api/nodes/n')).toHaveLength(1);
  });

  it('ignores a completed write after navigating away', async () => {
    let finish!: (value: unknown) => void;
    const fetcher = setup(() => new Promise(resolve => { finish = resolve; })); await openEditor();
    fireEvent.change(screen.getByLabelText('節點名稱'), { target: { value: '舊回應' } });
    fireEvent.click(screen.getByRole('button', { name: '儲存' }));
    fireEvent.click(screen.getByRole('button', { name: '所有專案總覽' }));
    await act(async () => { finish(response(task)); });
    expect(screen.getByRole('heading', { name: '所有專案總覽' })).toBeInTheDocument();
    expect(fetcher.mock.calls.filter(([path]) => path === '/api/projects/p')).toHaveLength(1);
    expect(screen.queryByLabelText('節點名稱')).not.toBeInTheDocument();
  });
});

describe('P2a blank project creation', () => {
  it('creates once then retries only reads after successful POST and failed reload', async () => {
    let lists = 0; let details = 0;
    const fetcher = vi.fn(async (path: string, init?: RequestInit) => {
      if (path === '/api/auth/me') return response({ ...identity, user: { ...identity.user, role: 'admin' } });
      if (path === '/api/workspace/overview') return response(overview);
      if (path === '/api/workflows') return response({ items: [] });
      if (path === '/api/projects' && init?.method === 'POST') return response(summary, 201);
      if (path === '/api/projects') { lists++; return response({ items: lists === 1 ? [] : [summary] }); }
      if (path === '/api/projects/p') { details++; return details === 1 ? response({}, 500) : response(detail); }
      throw Error('unexpected path');
    });
    stubFetch( fetcher); render(<App />);
    fireEvent.click(await screen.findByRole('button', { name: '建立新專案' }));
    fireEvent.click(await screen.findByRole('button', { name: '空白專案' }));
    fireEvent.change(screen.getByLabelText('新專案名稱'), { target: { value: ' 新空白專案 ' } });
    fireEvent.click(screen.getByRole('button', { name: '建立專案' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('已儲存，資料重新載入失敗');
    expect(screen.queryByRole('button', { name: '建立專案' })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '重試' }));
    expect(await screen.findByLabelText('節點樹')).toBeInTheDocument();
    expect(fetcher.mock.calls.filter(([, init]) => init?.method === 'POST')).toHaveLength(1);
    expect(fetcher).toHaveBeenCalledWith('/api/projects', expect.objectContaining({ method: 'POST', body: JSON.stringify({ title: '新空白專案' }) }));
    expect(details).toBe(2);
  });
});

const options = { users: [{ id: 'u', display_name: '成員' }], departments: [{ id: 'd', name: '研發' }] };
function editorProps(overrides = {}) {
  return { projectId: 'p', mode: 'edit' as const, node: task as NodeItem, parent: null, canAssign: false, reload: vi.fn().mockResolvedValue(undefined), close: vi.fn(), expired: vi.fn(), ...overrides };
}
describe('P2a editor mutation lifecycle', () => {
  it('creates a child with complete metadata and independent assignments', async () => {
    const fetcher = vi.fn().mockResolvedValueOnce(response(options)).mockResolvedValueOnce(response({ ...task, id: 'new' }, 201));
    stubFetch( fetcher); const props = editorProps();
    render(<NodeEditor {...props} mode="create" node={null} parent={task as NodeItem} canAssign />);
    await screen.findByRole('option', { name: '成員' });
    expect(screen.queryByRole('option', { name: '階段' })).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('節點名稱'), { target: { value: ' 子任務 ' } });
    fireEvent.change(screen.getByLabelText('部門'), { target: { value: 'd' } });
    fireEvent.change(screen.getByLabelText('截止日期'), { target: { value: '2026-11-01' } });
    fireEvent.click(screen.getByRole('button', { name: '儲存' }));
    await waitFor(() => expect(props.close).toHaveBeenCalled());
    expect(fetcher).toHaveBeenLastCalledWith('/api/projects/p/nodes', expect.objectContaining({ method: 'POST', body: JSON.stringify({ title: '子任務', start_date: null, due_date: '2026-11-01', owner_user_id: null, department_id: 'd', kind: 'task', parent_id: 'n' }) }));
    expect(props.reload).toHaveBeenCalledWith('new');
  });

  it('retains a legacy readonly owner without submitting an unchanged assignment', async () => {
    const fetcher = vi.fn().mockResolvedValueOnce(response(options)).mockResolvedValueOnce(response(task)); stubFetch( fetcher);
    const props = editorProps(); render(<NodeEditor {...props} node={{ ...task, owner_user_id: 'legacy', owner_display_name: '唯讀成員' } as NodeItem} canAssign />);
    await screen.findByRole('option', { name: '成員' });
    expect(screen.getByLabelText('負責人')).toHaveValue('legacy');
    expect(screen.getByRole('option', { name: '唯讀成員（既有指派）' })).toBeDisabled();
    fireEvent.change(screen.getByLabelText('節點名稱'), { target: { value: '改名' } }); fireEvent.click(screen.getByRole('button', { name: '儲存' }));
    await waitFor(() => expect(props.close).toHaveBeenCalled());
    expect(fetcher).toHaveBeenLastCalledWith('/api/nodes/n', expect.objectContaining({ body: JSON.stringify({ title: '改名' }) }));
  });

  it('blocks save when assignment options fail and retries only the read', async () => {
    const fetcher = vi.fn().mockResolvedValueOnce(response({}, 403)).mockResolvedValueOnce(response(options)); stubFetch( fetcher);
    render(<NodeEditor {...editorProps()} canAssign />);
    expect(await screen.findByRole('alert')).toHaveTextContent('沒有操作權限');
    fireEvent.change(screen.getByLabelText('節點名稱'), { target: { value: '改名' } });
    expect(screen.getByRole('button', { name: '儲存' })).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: '重試指派選項' }));
    await screen.findByRole('option', { name: '成員' });
    expect(screen.getByRole('button', { name: '儲存' })).not.toBeDisabled();
    expect(fetcher.mock.calls.every(([path]) => path === '/api/projects/p/assignment-options')).toBe(true);
  });

  it('retries only reload after a successful write and never offers another save', async () => {
    const fetcher = vi.fn().mockResolvedValue(response(task)); stubFetch( fetcher);
    const props = editorProps({ reload: vi.fn().mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce(undefined) });
    render(<NodeEditor {...props} />);
    fireEvent.change(screen.getByLabelText('節點名稱'), { target: { value: '改名' } }); fireEvent.click(screen.getByRole('button', { name: '儲存' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('已儲存，資料重新載入失敗');
    expect(screen.queryByRole('button', { name: '儲存' })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '重試載入' }));
    await waitFor(() => expect(props.close).toHaveBeenCalled());
    expect(props.reload).toHaveBeenCalledTimes(2); expect(fetcher).toHaveBeenCalledTimes(1);
  });

  it('warns to refresh after network uncertainty without automatically resending', async () => {
    const fetcher = vi.fn().mockRejectedValue(new Error('private-secret')); stubFetch( fetcher);
    render(<NodeEditor {...editorProps()} />);
    fireEvent.change(screen.getByLabelText('節點名稱'), { target: { value: '保留' } }); fireEvent.click(screen.getByRole('button', { name: '儲存' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('請重新整理確認儲存結果');
    expect(screen.getByLabelText('節點名稱')).toHaveValue('保留'); expect(fetcher).toHaveBeenCalledTimes(1);
    expect(document.body).not.toHaveTextContent('private-secret');
  });

  it.each([401, 404, 422])('maps mutation error %s safely', async status => {
    stubFetch( vi.fn().mockResolvedValue(response({ detail: 'private-secret' }, status)));
    const props = editorProps(); render(<NodeEditor {...props} />);
    fireEvent.change(screen.getByLabelText('節點名稱'), { target: { value: '保留' } }); fireEvent.click(screen.getByRole('button', { name: '儲存' }));
    if (status === 401) await waitFor(() => expect(props.expired).toHaveBeenCalled());
    else expect(await screen.findByRole('alert')).toHaveTextContent(status === 404 ? '找不到項目' : '請檢查欄位內容');
    expect(document.body).not.toHaveTextContent('private-secret');
  });

  it('ignores stale option failure on unmount', async () => {
    let finish!: (value: unknown) => void;
    stubFetch( vi.fn(() => new Promise(resolve => { finish = resolve; })));
    const props = editorProps(); const view = render(<NodeEditor {...props} canAssign />); view.unmount();
    await act(async () => { finish(response({}, 401)); }); expect(props.expired).not.toHaveBeenCalled();
  });
});
