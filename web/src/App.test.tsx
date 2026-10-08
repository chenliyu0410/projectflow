import { act, fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import App from './App';

const session = { user: { id: 'u1', username: 'yu', display_name: '游專案', role: 'admin' }, organization: { id: 'o1', key: 'food', name: '毛研食品' } };
const projects = { items: [{ id: 'p1', title: '成貓主食罐正式版', organization_key: 'food', owner_user_id: 'u1' }] };
const response = (body: unknown, status = 200) => ({ ok: status < 400, status, json: async () => body });
async function login() {
  fireEvent.change(await screen.findByLabelText('帳號'), { target: { value: 'yu' } });
  fireEvent.change(screen.getByLabelText('密碼'), { target: { value: 'demo-yu' } });
  fireEvent.click(screen.getByRole('button', { name: '登入' }));
}

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
