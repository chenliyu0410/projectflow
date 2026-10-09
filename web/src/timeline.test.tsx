import {
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import TimelineView, {
  calendarDay,
  shiftDates,
  timelineRows,
} from './components/TimelineView';
import type { NodeItem, ProjectDetail } from './types';
const node: NodeItem = {
  id: 'n',
  project_id: 'p',
  parent_id: null,
  kind: 'task',
  title: '排程任務',
  status: 'doing',
  owner_user_id: null,
  department_id: null,
  sort_order: 0,
  start_date: '2026-03-07',
  due_date: '2026-03-10',
  owner_display_name: null,
  department_name: null,
  capabilities: { edit_metadata: true, assign: false, create_child: false },
};
const project: ProjectDetail = {
  id: 'p',
  title: '排程專案',
  organization_key: 'food',
  owner_user_id: 'u',
  nodes: [node],
  gates: [],
  capabilities: { create_node: true },
};
const response = (body: unknown, status = 200) => ({
  ok: status < 400,
  status,
  json: async () => body,
});
describe('calendar schedule', () => {
  it('moves calendar days across DST and leap dates without changing duration', () => {
    expect(calendarDay('2026-03-09') - calendarDay('2026-03-08')).toBe(1);
    expect(shiftDates('2024-02-28', '2024-02-29', 1)).toEqual({
      start_date: '2024-02-29',
      due_date: '2024-03-01',
    });
    expect(shiftDates('2026-03-07', '2026-03-10', -99, true).due_date).toBe(
      '2026-03-07',
    );
    expect(shiftDates('9999-12-29', '9999-12-31', 4).due_date).toBe(
      '9999-12-31',
    );
  });
  it('promotes visible orphans and terminates even on damaged cyclic trees', () => {
    const nodes = [
      { ...node, id: 'a', parent_id: 'hidden' },
      { ...node, id: 'b', parent_id: 'a' },
      { ...node, id: 'c', parent_id: 'd' },
      { ...node, id: 'd', parent_id: 'c' },
    ];
    expect(timelineRows(nodes, new Set(['a'])).map((x) => x.node.id)).toEqual([
      'a',
      'c',
      'd',
    ]);
  });
  it('shows unscheduled null dates and supports accessible day/week/month controls', () => {
    render(
      <TimelineView
        project={{
          ...project,
          nodes: [{ ...node, start_date: null, due_date: null }],
        }}
        select={vi.fn()}
        reload={vi.fn()}
        expired={vi.fn()}
      />,
    );
    expect(screen.getByRole('heading', { name: '未排程' })).toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: '時程任務：排程任務' }),
    ).not.toBeInTheDocument();
    const scale = screen.getByRole('group', { name: '時程刻度' });
    const day = within(scale).getByRole('button', { name: '日' });
    const week = within(scale).getByRole('button', { name: '週' });
    const month = within(scale).getByRole('button', { name: '月' });
    expect(week).toHaveAttribute('aria-pressed', 'true');
    fireEvent.click(month);
    expect(month).toHaveAttribute('aria-pressed', 'true');
    expect(week).toHaveAttribute('aria-pressed', 'false');
    expect(day).toHaveAttribute('aria-pressed', 'false');
    fireEvent.click(day);
    expect(day).toHaveAttribute('aria-pressed', 'true');
    expect(month).toHaveAttribute('aria-pressed', 'false');
    expect(screen.getByText(/^今天：/)).toBeInTheDocument();
  });
  it('saves only the selected dates, supports null and never repeats PATCH on read retry', async () => {
    const f = vi.fn().mockResolvedValue(response(node));
    vi.stubGlobal('fetch', f);
    const reload = vi.fn().mockRejectedValue(new Error('read'));
    render(
      <TimelineView
        project={project}
        select={vi.fn()}
        reload={reload}
        expired={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByRole('button', { name: '調整日期：排程任務' }));
    fireEvent.change(screen.getByLabelText('開始日期'), {
      target: { value: '' },
    });
    fireEvent.click(screen.getByRole('button', { name: '儲存日期' }));
    const retry = await screen.findByRole('button', { name: '重試時程載入' });
    await waitFor(() => expect(retry).not.toBeDisabled());
    fireEvent.click(retry);
    await waitFor(() => expect(reload).toHaveBeenCalledTimes(2));
    expect(f).toHaveBeenCalledTimes(1);
    expect(f).toHaveBeenCalledWith(
      '/api/nodes/n',
      expect.objectContaining({
        method: 'PATCH',
        body: JSON.stringify({ start_date: null, due_date: '2026-03-10' }),
      }),
    );
  });
  it('cancel does not write and readonly nodes offer no date editor', () => {
    const f = vi.fn();
    vi.stubGlobal('fetch', f);
    const props = {
      project,
      select: vi.fn(),
      reload: vi.fn(),
      expired: vi.fn(),
    };
    const { rerender } = render(<TimelineView {...props} />);
    fireEvent.click(screen.getByRole('button', { name: '調整日期：排程任務' }));
    fireEvent.click(screen.getByRole('button', { name: '取消改期' }));
    expect(f).not.toHaveBeenCalled();
    rerender(
      <TimelineView
        {...props}
        project={{
          ...project,
          nodes: [
            {
              ...node,
              capabilities: { ...node.capabilities, edit_metadata: false },
            },
          ],
        }}
      />,
    );
    expect(
      screen.queryByRole('button', { name: '調整日期：排程任務' }),
    ).not.toBeInTheDocument();
  });
  it('pointer resize previews dates without a write until confirmation', () => {
    vi.stubGlobal('PointerEvent', MouseEvent);
    const f = vi.fn();
    vi.stubGlobal('fetch', f);
    render(
      <TimelineView
        project={project}
        select={vi.fn()}
        reload={vi.fn()}
        expired={vi.fn()}
      />,
    );
    const resize = screen.getByRole('button', { name: '調整截止日：排程任務' });
    fireEvent.pointerDown(resize, { clientX: 100, button: 0 });
    fireEvent.pointerMove(resize, { clientX: 124 });
    fireEvent.pointerUp(resize, { clientX: 124 });
    expect(screen.getByLabelText('開始日期')).toHaveValue('2026-03-07');
    expect(screen.getByLabelText('截止日期')).toHaveValue('2026-03-12');
    expect(f).not.toHaveBeenCalled();
  });
});
