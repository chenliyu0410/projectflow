import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import AccountManager from './components/AccountManager';
import ChangePassword from './components/ChangePassword';

const json = (data: unknown, status = 200) => new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } });
const accounts = { me: 'u1', roles: ['admin', 'project_owner', 'reviewer', 'member', 'readonly'], items: [
  { id: 'u1', username: 'yu', display_name: '游專案', role: 'admin', status: 'active', must_change_password: false, departments: ['研發'], last_login_at: '2026-10-24T01:00:00Z' },
  { id: 'u2', username: 'ming', display_name: '明成員', role: 'member', status: 'active', must_change_password: false, departments: [], last_login_at: null }] };

it('creates an account and shows the temporary password once', async () => {
  const fetcher = vi.fn(async (url: string, init: RequestInit = {}) => init.method === 'POST'
    ? json({ account: { ...accounts.items[1], id: 'u3', username: 'wang', display_name: '王小明', must_change_password: true }, temporary_password: 'Tmp-Secret-123' }, 201)
    : json(accounts));
  vi.stubGlobal('fetch', fetcher);
  render(<AccountManager expired={vi.fn()} />);
  expect(await screen.findByText(/游專案/)).toBeInTheDocument();
  expect(screen.getByText(/你自己/)).toBeInTheDocument();
  expect(screen.queryByLabelText('yu 角色')).toBeNull();
  fireEvent.change(screen.getByLabelText('新帳號'), { target: { value: 'wang' } });
  fireEvent.change(screen.getByLabelText('新帳號顯示名稱'), { target: { value: '王小明' } });
  fireEvent.click(screen.getByRole('button', { name: '新增帳號' }));
  expect(await screen.findByText('Tmp-Secret-123')).toBeInTheDocument();
  expect(JSON.parse(String(fetcher.mock.calls.find(([, i]) => i?.method === 'POST')?.[1]?.body))).toEqual({ username: 'wang', display_name: '王小明', role: 'member' });
  fireEvent.click(screen.getByRole('button', { name: '我已經記下了' }));
  expect(screen.queryByText('Tmp-Secret-123')).toBeNull();
});

it('asks before disabling and sends the status change', async () => {
  const fetcher = vi.fn(async (_url: string, _init?: RequestInit) => json(accounts));
  vi.stubGlobal('fetch', fetcher);
  vi.stubGlobal('confirm', vi.fn(() => true));
  render(<AccountManager expired={vi.fn()} />);
  fireEvent.click(await screen.findByRole('button', { name: '停用' }));
  await waitFor(() => expect(fetcher.mock.calls.some(([url, init]) => String(url).endsWith('/accounts/u2') && init?.body === JSON.stringify({ status: 'disabled' }))).toBe(true));
  expect(await screen.findByRole('status')).toHaveTextContent('已停用「明成員」');
});

it('checks the new password locally before sending', async () => {
  const fetcher = vi.fn(async (_url: string, _init?: RequestInit) => json({ ok: true }));
  vi.stubGlobal('fetch', fetcher);
  const done = vi.fn();
  render(<ChangePassword forced done={done} expired={vi.fn()} logout={vi.fn()} />);
  fireEvent.change(screen.getByLabelText('臨時密碼'), { target: { value: 'Tmp-Secret-123' } });
  fireEvent.change(screen.getByLabelText('新密碼'), { target: { value: 'my-new-password' } });
  fireEvent.change(screen.getByLabelText('再輸入一次新密碼'), { target: { value: 'my-new-passwordX' } });
  fireEvent.click(screen.getByRole('button', { name: '儲存新密碼' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('兩次輸入的新密碼不一樣');
  expect(fetcher).not.toHaveBeenCalled();
  fireEvent.change(screen.getByLabelText('再輸入一次新密碼'), { target: { value: 'my-new-password' } });
  fireEvent.click(screen.getByRole('button', { name: '儲存新密碼' }));
  await waitFor(() => expect(done).toHaveBeenCalled());
  expect(fetcher.mock.calls[0][1]?.body).toBe(JSON.stringify({ current_password: 'Tmp-Secret-123', new_password: 'my-new-password' }));
});
