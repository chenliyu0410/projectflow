import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App';
import NoteEditor from './components/NoteEditor';
import { api, ApiError, requestJson, REQUEST_TIMEOUT_MS } from './api';

// 模擬卡住的後端：只有 signal 被中止時才結束。
function hanging(_path: string, init?: RequestInit) {
  return new Promise<Response>((_, reject) => {
    init?.signal?.addEventListener('abort', () => reject(init.signal!.reason ?? new DOMException('aborted', 'AbortError')));
  });
}
const response = (body: unknown, status = 200) => ({ ok: status < 400, status, json: async () => body });

beforeEach(() => { vi.useFakeTimers(); });
afterEach(() => { vi.useRealTimers(); });

describe('request timeout', () => {
  it('turns a stalled request into a readable status-0 error without aborting the caller', async () => {
    vi.stubGlobal('fetch', vi.fn(hanging));
    const caller = new AbortController();
    const result = requestJson('/projects', { signal: caller.signal });
    const settled = expect(result).rejects.toMatchObject({ status: 0, message: '伺服器回應逾時，請稍後再試' });
    await act(async () => { await vi.advanceTimersByTimeAsync(REQUEST_TIMEOUT_MS); });
    await settled;
    expect(caller.signal.aborted).toBe(false);
  });

  it('still reports a caller abort as an abort, not a timeout', async () => {
    vi.stubGlobal('fetch', vi.fn(hanging));
    const caller = new AbortController();
    const result = requestJson('/projects', { signal: caller.signal });
    caller.abort();
    await expect(result).rejects.not.toBeInstanceOf(ApiError);
  });

  it('times out attachment downloads too', async () => {
    vi.stubGlobal('fetch', vi.fn(hanging));
    const result = api.download('a1');
    const settled = expect(result).rejects.toMatchObject({ status: 0 });
    await act(async () => { await vi.advanceTimersByTimeAsync(120_000); });
    await settled;
  });

  it('releases the login busy state after a stalled login', async () => {
    vi.stubGlobal('fetch', vi.fn(async (path: string, init?: RequestInit) => path === '/api/auth/me' ? response({ detail: 'x' }, 401) : hanging(path, init)));
    render(<App />);
    await act(async () => { await vi.advanceTimersByTimeAsync(0); });
    fireEvent.change(screen.getByLabelText('帳號'), { target: { value: 'yu' } });
    fireEvent.change(screen.getByLabelText('密碼'), { target: { value: 'pw' } });
    fireEvent.click(screen.getByRole('button', { name: '登入' }));
    expect(screen.getByRole('button', { name: '登入中' })).toBeDisabled();
    await act(async () => { await vi.advanceTimersByTimeAsync(REQUEST_TIMEOUT_MS); });
    expect(screen.getByRole('button', { name: '登入' })).toBeEnabled();
    expect(screen.getByRole('alert')).toHaveTextContent('逾時');
  });

  it('releases the record mutation lock after a stalled write', async () => {
    vi.spyOn(api, 'quota').mockResolvedValue({ limit_bytes: 1, charged_bytes: 0, remaining_bytes: 1 });
    vi.stubGlobal('fetch', vi.fn(hanging));
    render(<NoteEditor nodeId="n" reload={async () => undefined} expired={vi.fn()} />);
    fireEvent.change(screen.getByLabelText('新增筆記'), { target: { value: '卡住的筆記' } });
    fireEvent.click(screen.getByRole('button', { name: '新增筆記' }));
    expect(screen.getByRole('button', { name: '新增筆記' })).toBeDisabled();
    await act(async () => { await vi.advanceTimersByTimeAsync(REQUEST_TIMEOUT_MS); });
    expect(screen.getByRole('alert')).toHaveTextContent('逾時');
    expect(screen.getByRole('button', { name: '新增筆記' })).toBeEnabled();
    expect(screen.getByLabelText('新增筆記')).toHaveValue('卡住的筆記');
  });
});
