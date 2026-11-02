import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { api, ApiError } from './api';
import EmailSettings from './components/EmailSettings';
import MailFailures from './components/MailFailures';
import WeeklyReportPanel, { thisMonday } from './components/WeeklyReportPanel';

afterEach(() => vi.restoreAllMocks());

describe('EmailSettings', () => {
  it('loads, saves and shows backend validation errors', async () => {
    vi.spyOn(api, 'myEmail').mockResolvedValue({ email: 'ming@demo.local', email_notify: true });
    const save = vi.spyOn(api, 'saveMyEmail').mockRejectedValueOnce(new ApiError(422, 'Email 格式不正確')).mockResolvedValueOnce({ email: null, email_notify: false });
    render(<EmailSettings />);
    const input = await screen.findByDisplayValue('ming@demo.local');
    fireEvent.change(input, { target: { value: 'a@b' } });  // passes the browser's check, rejected by the API
    fireEvent.click(screen.getByRole('button', { name: '儲存 Email 設定' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Email 格式不正確');
    fireEvent.change(input, { target: { value: '' } });
    fireEvent.click(screen.getByLabelText('接收 Email 通知'));
    await waitFor(() => expect(screen.getByRole('button', { name: '儲存 Email 設定' })).toBeEnabled());
    fireEvent.click(screen.getByRole('button', { name: '儲存 Email 設定' }));
    await waitFor(() => expect(save).toHaveBeenLastCalledWith(null, false));
    expect(await screen.findByRole('status')).toHaveTextContent('已儲存');
  });
});

describe('MailFailures', () => {
  it('lists failed mail and resends it', async () => {
    const list = vi.spyOn(api, 'failedMail')
      .mockResolvedValueOnce({ items: [{ id: 'e1', subject: '[專流] 週報', recipient: '陳主管', attempts: 5, last_error: 'SMTP 550', created_at: '2026-11-02T01:00:00' }] })
      .mockResolvedValueOnce({ items: [] });
    const retry = vi.spyOn(api, 'retryMail').mockResolvedValue({ status: 'pending' });
    render(<MailFailures />);
    expect(await screen.findByText('原因：SMTP 550')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '重寄' }));
    await waitFor(() => expect(retry).toHaveBeenCalledWith('e1'));
    expect(await screen.findByText('目前沒有寄送失敗的信。')).toBeInTheDocument();
    expect(list).toHaveBeenCalledTimes(2);
  });
});

describe('WeeklyReportPanel safeguards', () => {
  it('explains the daily digest to members instead of showing an error', async () => {
    vi.spyOn(api, 'weeklyReports').mockRejectedValue(new ApiError(403, '一般成員請看每日摘要'));
    render(<WeeklyReportPanel projectId="p" />);
    expect(await screen.findByText(/今日任務摘要/)).toBeInTheDocument();
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('disables generating once this week has been sent', async () => {
    const counts = { completed: 0, pending_review: 0, doing: 0, due_next_week: 0, overdue: 0, blocked: 0 };
    vi.spyOn(api, 'weeklyReports').mockResolvedValue({ can_manage: true, items: [{
      id: 'r', week_start: thisMonday(), status: 'sent', excluded_count: 0, model_label: 'AI 未啟用', recipients: ['游專案'], generated_by: '游專案',
      generated_at: '2026-11-02T01:00:00', confirmed_by: '游專案', confirmed_at: '2026-11-02T02:00:00',
      sections: { summary: '摘要', highlights: [], risks: [], next: [] },
      facts: { week_start: thisMonday(), today: thisMonday(), project: 'P', completed: [], pending_review: [], doing: [], due_next_week: [], overdue: [], blocked: [], silent_members: [], counts } }] });
    render(<WeeklyReportPanel projectId="p" />);
    expect(await screen.findByRole('button', { name: '本週已寄出' })).toBeDisabled();
  });

  it('computes Monday of the current week', () => {
    expect(thisMonday(new Date(2026, 10, 5))).toBe('2026-11-02');
    expect(thisMonday(new Date(2026, 10, 2))).toBe('2026-11-02');
    expect(thisMonday(new Date(2026, 10, 8))).toBe('2026-11-02');
  });
});
