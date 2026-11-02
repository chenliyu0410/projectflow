import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { api } from './api';
import WeeklyReportPanel from './components/WeeklyReportPanel';
import type { WeeklyReport } from './types';

const item = (ref: string, title: string) => ({ ref, title, owner: '明成員', due_date: '2026-11-01' });
function report(over: Partial<WeeklyReport> = {}): WeeklyReport {
  return {
    id: 'r1', week_start: '2026-11-02', status: 'draft', excluded_count: 2, model_label: 'AI 未啟用',
    recipients: ['專案負責', '游專案'], generated_by: '專案負責', generated_at: '2026-11-02T09:00:00+00:00', confirmed_by: null, confirmed_at: null,
    sections: { summary: '本週完成 1 項', highlights: ['[T1] 定稿'], risks: ['[T2] 逾期'], next: [] },
    facts: { week_start: '2026-11-02', today: '2026-11-02', project: 'P', completed: [item('T1', '配方定稿')], pending_review: [], doing: [],
      due_next_week: [], overdue: [item('T2', '包材測試')], blocked: [], silent_members: ['明成員'],
      counts: { completed: 1, pending_review: 0, doing: 0, due_next_week: 0, overdue: 1, blocked: 0 } },
    ...over,
  };
}

afterEach(() => vi.restoreAllMocks());

describe('WeeklyReportPanel', () => {
  it('lets the owner edit the AI draft and confirm after a prompt', async () => {
    vi.spyOn(api, 'weeklyReports').mockResolvedValue({ can_manage: true, items: [report()] });
    const save = vi.spyOn(api, 'saveWeeklyReport').mockResolvedValue(report());
    const confirmCall = vi.spyOn(api, 'confirmWeeklyReport').mockResolvedValue({ report: report({ status: 'sent' }), removed: ['游專案'] });
    const prompt = vi.spyOn(window, 'confirm').mockReturnValue(true);
    render(<WeeklyReportPanel projectId="p" />);
    const summary = await screen.findByLabelText('整體摘要');
    expect(screen.getByText('AI 建議')).toBeTruthy();
    expect(screen.getByText('有 2 項因權限或機密等級未列入')).toBeTruthy();
    expect(screen.getByText(/撰寫方式：AI 未啟用/)).toBeTruthy();
    fireEvent.change(summary, { target: { value: '負責人改寫' } });
    fireEvent.click(screen.getByRole('button', { name: '儲存' }));
    await waitFor(() => expect(save).toHaveBeenCalledWith('r1', expect.objectContaining({ summary: '負責人改寫' })));
    fireEvent.click(await screen.findByRole('button', { name: '確認寄出（2 位）' }));
    expect(prompt).toHaveBeenCalled();
    await waitFor(() => expect(confirmCall).toHaveBeenCalledWith('r1', expect.objectContaining({ summary: '負責人改寫' })));
    expect(await screen.findByText(/游專案 已停用或無法查看部分任務/)).toBeTruthy();
  });

  it('does not send when the prompt is cancelled', async () => {
    vi.spyOn(api, 'weeklyReports').mockResolvedValue({ can_manage: true, items: [report()] });
    const confirmCall = vi.spyOn(api, 'confirmWeeklyReport');
    vi.spyOn(window, 'confirm').mockReturnValue(false);
    render(<WeeklyReportPanel projectId="p" />);
    fireEvent.click(await screen.findByRole('button', { name: '確認寄出（2 位）' }));
    expect(confirmCall).not.toHaveBeenCalled();
  });

  it('shows read-only sent reports to managers who cannot manage', async () => {
    vi.spyOn(api, 'weeklyReports').mockResolvedValue({ can_manage: false, items: [report({ status: 'sent', confirmed_by: '專案負責', confirmed_at: '2026-11-02T10:00:00' })] });
    render(<WeeklyReportPanel projectId="p" />);
    expect(await screen.findByText('本週完成 1 項')).toBeTruthy();
    expect(screen.queryByRole('button', { name: '立即產生草稿' })).toBeNull();
    expect(screen.queryByLabelText('整體摘要')).toBeNull();
    expect(screen.getByText(/由 專案負責 於/)).toBeTruthy();
  });

  it('generates a draft and reports backend errors', async () => {
    vi.spyOn(api, 'weeklyReports').mockResolvedValue({ can_manage: true, items: [] });
    const { ApiError } = await import('./api');
    vi.spyOn(api, 'generateWeeklyReport').mockRejectedValue(new ApiError(409, '本週週報已寄出'));
    render(<WeeklyReportPanel projectId="p" />);
    fireEvent.click(await screen.findByRole('button', { name: '立即產生草稿' }));
    expect(await screen.findByRole('alert')).toHaveProperty('textContent', '本週週報已寄出');
  });
});
