import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App';
import { ai } from './ai';
import type { AIResult, AIStatus } from './ai';
import { ApiError } from './api';

const response = (body: unknown, status = 200) => ({ ok: status < 400, status, json: async () => body });
const identity = { user: { id: 'u', display_name: '成員', role: 'member' }, organization: { id: 'o', key: 'electronics', name: '公司' } };
const status: AIStatus = { ready: true, as_of: '2026-10-11', company_name: '公司', model_enabled: false, model_name: '', can_configure: false, can_sql: false, projects: [], queries: [], counts: { projects: 1, documents: 1 } };
const answer: AIResult = { kind: 'retrieval', engine: 'retrieval', answer: '保留的回答', warning: null, sources: [], analysis: null };
const overview = { project_count: 0, task_counts: { todo: 0, doing: 0, review: 0, done: 0, skipped: 0 }, completion_percent: null, projects: [] };
beforeEach(() => {
  vi.spyOn(ai, 'status').mockResolvedValue(status);
  vi.stubGlobal('fetch', vi.fn(async (path: string) => path === '/api/auth/me' ? response(identity) : path === '/api/projects' ? response({ items: [] })
    : path === '/api/workspace/overview' ? response(overview) : path.startsWith('/api/workspace/my-tasks') ? response({ items: [] })
      : path.startsWith('/api/notifications') ? response({ items: [], unread_count: 0, next_offset: null }) : path.startsWith('/api/workspace/reviews') ? response({ items: [], next_cursor: null })
        : path.startsWith('/api/workspace/requests') ? response({ items: [] }) : response({}, 404)));
});
const nav = (name: RegExp) => within(screen.getByRole('navigation', { name: '工作區導覽' })).getByRole('button', { name });
async function openCopilot() {
  render(<App />);
  fireEvent.click(await screen.findByRole('button', { name: '切換 AI 副手' }));
  const copilot = within(screen.getByRole('complementary', { name: 'AI 專案副手' }));
  await copilot.findByText(/1 個專案／1 份可見文件/);
  return copilot;
}

describe('copilot across navigation', () => {
  it('keeps the conversation and a running question when the user moves to another page', async () => {
    let finish!: (value: AIResult) => void;
    vi.spyOn(ai, 'ask').mockResolvedValueOnce(answer).mockImplementationOnce(() => new Promise(resolve => { finish = resolve; }));
    const copilot = await openCopilot();
    fireEvent.click(copilot.getByRole('button', { name: '風險原因與處理方式' }));
    await copilot.findByText('保留的回答');
    fireEvent.click(copilot.getByRole('button', { name: '採購追蹤紀錄' }));
    const signal = vi.mocked(ai.ask).mock.calls[1][1]!;
    fireEvent.click(nav(/我的任務/));
    await screen.findByRole('heading', { name: '我的任務' });
    expect(signal.aborted).toBe(false);
    await act(async () => finish({ ...answer, answer: '導覽後完成的回答' }));
    const after = within(screen.getByRole('complementary', { name: 'AI 專案副手' }));
    expect(after.getByText('保留的回答')).toBeInTheDocument();
    expect(after.getByText('導覽後完成的回答')).toBeInTheDocument();
  });

  it('still clears the conversation when entering the preview area', async () => {
    vi.spyOn(ai, 'ask').mockResolvedValue(answer);
    const copilot = await openCopilot();
    fireEvent.click(copilot.getByRole('button', { name: '風險原因與處理方式' }));
    await copilot.findByText('保留的回答');
    fireEvent.click(nav(/AI 政策與稽核/));
    await screen.findByLabelText('展示預覽工作區');
    expect(within(screen.getByRole('complementary', { name: 'AI 專案副手', hidden: true })).queryByText('保留的回答')).not.toBeInTheDocument();
  });


  it('expires the session when a question returns 401', async () => {
    vi.spyOn(ai, 'ask').mockRejectedValue(new ApiError(401, '登入已失效，請重新登入'));
    const copilot = await openCopilot();
    fireEvent.click(copilot.getByRole('button', { name: '風險原因與處理方式' }));
    expect(await screen.findByRole('heading', { name: '登入專流' })).toBeInTheDocument();
  });
});
