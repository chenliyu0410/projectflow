import { act, fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import App from './App';
import { api } from './api';

const session = { user: { id: 'u1', username: 'yu', display_name: '游專案', role: 'admin' }, organization: { id: 'o1', key: 'food', name: '毛研食品' } };
const projects = { items: [{ id: 'p1', title: '成貓主食罐正式版', organization_key: 'food', owner_user_id: 'u1' }] };
const response = (body: unknown, status = 200) => ({ ok: status < 400, status, json: async () => body });
async function login() {
  fireEvent.change(await screen.findByLabelText('帳號'), { target: { value: 'yu' } });
  fireEvent.change(screen.getByLabelText('密碼'), { target: { value: 'demo-yu' } });
  fireEvent.click(screen.getByRole('button', { name: '登入' }));
}

describe('P1b typed API client', () => {
  it('loads project detail using cookies without organization context', async () => {
    const detail = { ...projects.items[0], nodes: [], gates: [] };
    const fetcher = vi.fn().mockResolvedValue(response(detail));
    vi.stubGlobal('fetch', fetcher);
    const signal = new AbortController().signal;
    expect(await api.project('p1', signal)).toEqual(detail);
    expect(fetcher).toHaveBeenCalledWith('/api/projects/p1', expect.objectContaining({ credentials: 'include', signal }));
    expect(fetcher.mock.calls[0][1].body).toBeUndefined();
  });

  it('updates node status with only the status payload', async () => {
    const node = { id: 'n1', status: 'doing' };
    const fetcher = vi.fn().mockResolvedValue(response(node));
    vi.stubGlobal('fetch', fetcher);
    const signal = new AbortController().signal;
    expect(await api.updateNodeStatus('n1', 'doing', signal)).toEqual(node);
    expect(fetcher).toHaveBeenCalledWith('/api/nodes/n1/status', expect.objectContaining({ method: 'PATCH', credentials: 'include', signal }));
    expect(JSON.parse(fetcher.mock.calls[0][1].body)).toEqual({ status: 'doing' });
  });

  it('loads workflow templates using cookies without organization context', async () => {
    const workflows = { items: [{ id: 'w1', name: '食品新品開發' }] };
    const fetcher = vi.fn().mockResolvedValue(response(workflows));
    vi.stubGlobal('fetch', fetcher);
    const signal = new AbortController().signal;
    expect(await api.workflows(signal)).toEqual(workflows);
    expect(fetcher).toHaveBeenCalledWith('/api/workflows', expect.objectContaining({ credentials: 'include', signal }));
    expect(fetcher.mock.calls[0][1].body).toBeUndefined();
  });

  it('creates a project with only workflow and title payload', async () => {
    const fetcher = vi.fn().mockResolvedValue(response(projects.items[0], 201));
    vi.stubGlobal('fetch', fetcher);
    const payload = { workflow_id: 'w1', title: '成貓主食罐正式版' };
    const signal = new AbortController().signal;
    expect(await api.createFromWorkflow(payload, signal)).toEqual(projects.items[0]);
    expect(fetcher).toHaveBeenCalledWith('/api/projects/from-workflow', expect.objectContaining({ method: 'POST', credentials: 'include', signal }));
    expect(JSON.parse(fetcher.mock.calls[0][1].body)).toEqual(payload);
  });

  it('approves a gate with only approved status payload', async () => {
    const gate = { id: 'g1', project_id: 'p1', node_id: 'n1', status: 'approved' };
    const fetcher = vi.fn().mockResolvedValue(response(gate));
    vi.stubGlobal('fetch', fetcher);
    const signal = new AbortController().signal;
    expect(await api.approveGate('g1', signal)).toEqual(gate);
    expect(fetcher).toHaveBeenCalledWith('/api/gates/g1', expect.objectContaining({ method: 'PATCH', credentials: 'include', signal }));
    expect(JSON.parse(fetcher.mock.calls[0][1].body)).toEqual({ status: 'approved' });
  });
});

describe('P1b session UI', () => {
  it('shows login without an active session', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({}, 401)));
    render(<App />);
    expect(await screen.findByRole('heading', { name: '登入專流' })).toBeInTheDocument();
    expect(screen.getByLabelText('公司')).toHaveValue('food');
  });

  it('logs in and loads projects using cookies only', async () => {
    const fetcher = vi.fn().mockResolvedValueOnce(response({}, 401)).mockResolvedValueOnce(response(session)).mockResolvedValueOnce(response(projects));
    vi.stubGlobal('fetch', fetcher);
    render(<App />);
    await login();
    expect(await screen.findByText('成貓主食罐正式版')).toBeInTheDocument();
    expect(fetcher).toHaveBeenCalledWith('/api/auth/login', expect.objectContaining({ credentials: 'include', method: 'POST', body: JSON.stringify({ organization_key: 'food', username: 'yu', password: 'demo-yu' }) }));
    expect(fetcher).toHaveBeenLastCalledWith('/api/projects', expect.objectContaining({ credentials: 'include' }));
    expect(fetcher.mock.calls[2][1].body).toBeUndefined();
    expect(screen.getByRole('button', { name: '成貓主食罐正式版' })).toHaveAttribute('aria-pressed', 'true');
  });

  it('restores a session and handles an empty project list', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(response(session)).mockResolvedValueOnce(response({ items: [] })));
    render(<App />);
    expect(await screen.findByText('目前沒有專案')).toBeInTheDocument();
    expect(screen.getByLabelText('目前公司')).toHaveTextContent('毛研食品');
  });

  it.each([401, 422, 500])('maps login errors safely (%s)', async status => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(response({}, 401)).mockResolvedValueOnce(response({ detail: 'private-secret' }, status)));
    render(<App />);
    await login();
    expect(await screen.findByRole('alert')).toHaveTextContent(status === 401 ? '帳號或密碼錯誤' : '操作失敗，請稍後再試');
    expect(document.body).not.toHaveTextContent('private-secret');
    expect(screen.getByLabelText('密碼')).toHaveValue('');
  });

  it('returns to login on expired project session', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(response(session)).mockResolvedValueOnce(response({}, 401)));
    render(<App />);
    expect(await screen.findByRole('heading', { name: '登入專流' })).toBeInTheDocument();
    expect(screen.queryByLabelText('目前公司')).not.toBeInTheDocument();
  });

  it.each(['500', 'network'])('keeps the authenticated session and retries failed projects (%s)', async failure => {
    const fetcher = vi.fn().mockResolvedValueOnce(response({}, 401)).mockResolvedValueOnce(response(session));
    if (failure === '500') fetcher.mockResolvedValueOnce(response({ detail: 'private-secret' }, 500));
    else fetcher.mockRejectedValueOnce(new Error('private-secret'));
    fetcher.mockResolvedValueOnce(response(session)).mockResolvedValueOnce(response(projects));
    vi.stubGlobal('fetch', fetcher);
    render(<App />);
    await login();
    expect(await screen.findByRole('alert')).toHaveTextContent(failure === '500' ? '操作失敗，請稍後再試' : '無法連線，請稍後再試');
    expect(screen.getByLabelText('目前公司')).toHaveTextContent('毛研食品');
    expect(screen.queryByRole('heading', { name: '登入專流' })).not.toBeInTheDocument();
    expect(document.body).not.toHaveTextContent('private-secret');
    fireEvent.click(screen.getByRole('button', { name: '重試' }));
    expect(await screen.findByText('成貓主食罐正式版')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(fetcher.mock.calls.filter(([path]) => path === '/api/auth/login')).toHaveLength(1);
  });

  it('retries after a safe network error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValueOnce(new Error('private-secret')).mockResolvedValueOnce(response(session)).mockResolvedValueOnce(response(projects)));
    render(<App />);
    expect(await screen.findByRole('alert')).toHaveTextContent('無法連線，請稍後再試');
    expect(document.body).not.toHaveTextContent('private-secret');
    fireEvent.click(screen.getByRole('button', { name: '重試' }));
    expect(await screen.findByText('成貓主食罐正式版')).toBeInTheDocument();
  });

  it('logs out and ignores late projects even when fetch ignores abort', async () => {
    let resolveProjects!: (value: ReturnType<typeof response>) => void;
    const fetcher = vi.fn().mockResolvedValueOnce(response(session)).mockImplementationOnce(() => new Promise(resolve => { resolveProjects = resolve; })).mockResolvedValueOnce(response(undefined, 204));
    vi.stubGlobal('fetch', fetcher);
    render(<App />);
    fireEvent.click(await screen.findByRole('button', { name: '登出' }));
    expect(await screen.findByRole('heading', { name: '登入專流' })).toBeInTheDocument();
    expect(fetcher).toHaveBeenLastCalledWith('/api/auth/logout', expect.objectContaining({ credentials: 'include', method: 'POST' }));
    expect(fetcher.mock.calls[1][1].signal.aborted).toBe(true);
    await act(async () => { resolveProjects(response(projects)); });
    expect(screen.queryByText('成貓主食罐正式版')).not.toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '登入專流' })).toBeInTheDocument();
  });

  it('permits retry when logout fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(response(session)).mockResolvedValueOnce(response(projects)).mockResolvedValueOnce(response({ detail: 'private-secret' }, 500)).mockResolvedValueOnce(response(undefined, 204)));
    render(<App />);
    await screen.findByText('成貓主食罐正式版');
    fireEvent.click(screen.getByRole('button', { name: '登出' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('操作失敗，請稍後再試');
    expect(document.body).not.toHaveTextContent('private-secret');
    fireEvent.click(screen.getByRole('button', { name: '登出' }));
    expect(await screen.findByRole('heading', { name: '登入專流' })).toBeInTheDocument();
  });

  it('aborts the request on unmount', () => {
    const fetcher = vi.fn(() => new Promise(() => {}));
    vi.stubGlobal('fetch', fetcher);
    const { unmount } = render(<App />);
    const signal = (fetcher.mock.calls as unknown as [string, RequestInit][])[0][1].signal;
    unmount();
    expect(signal?.aborted).toBe(true);
  });
});
