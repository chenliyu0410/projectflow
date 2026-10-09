import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import App from './App';
const response = (body: unknown, status = 200) => ({
  ok: status < 400,
  status,
  json: async () => body,
});
const report = {
  type: 'report',
  id: 'r',
  node_id: 'n',
  node_title: '待確認成果',
  project_id: 'p',
  project_title: '示範專案',
  created_at: '2026-10-08T12:00:00Z',
  status: 'submitted',
  version: 2,
  result: '達成',
  summary: '成果內容',
  finished_on: '2026-10-08',
  submitted_by: 'other',
  submitted_by_display_name: '同事',
  capabilities: { review_report: true },
};
const gate = {
  type: 'gate',
  id: 'g',
  node_id: 'phase',
  node_title: '階段查核',
  project_id: 'p',
  project_title: '示範專案',
  created_at: '2026-10-08T12:00:00Z',
  status: 'pending',
  capabilities: { approve_gate: true },
};
const audit = {
  id: 'a',
  action: 'note.update',
  summary: '修訂筆記',
  node_id: 'n',
  node_title: '待確認成果',
  project_id: 'p',
  project_title: '示範專案',
  actor_display_name: '同事',
  actor_user_id: 'internal-user',
  created_at: '2026-10-08T12:00:00Z',
  payload: {
    note_id: 'internal-note',
    before: { body: '舊文字', revision: 1 },
    after: { body: '<script>安全新文字</script>', revision: 2 },
  },
};
async function setup(
  route = '審核中心',
  override?: (p: string, i?: RequestInit) => unknown,
) {
  const fetcher = vi.fn(async (p: string, i?: RequestInit) => {
    const custom = override?.(p, i);
    if (custom !== undefined) return custom;
    if (p === '/api/auth/me')
      return response({
        user: { id: 'u', role: 'admin', display_name: '管理者' },
        organization: { id: 'o', name: '公司' },
      });
    if (p === '/api/projects') return response({ items: [] });
    if (p.startsWith('/api/workspace/reviews'))
      return response({ items: [report, gate], next_cursor: null });
    if (p.startsWith('/api/audit-logs'))
      return response({ items: [audit], next_cursor: null });
    if (p === '/api/workspace/overview')
      return response({
        project_count: 0,
        task_counts: { todo: 0, doing: 0, review: 0, done: 0, skipped: 0 },
        completion_percent: null,
        projects: [],
      });
    return response({}, 200);
  });
  vi.stubGlobal('fetch', fetcher);
  render(<App />);
  fireEvent.click(await screen.findByRole('button', { name: route }));
  return fetcher;
}
function deferred() {
  let resolve!: (v: unknown) => void;
  const promise = new Promise((r) => (resolve = r));
  return { promise, resolve };
}
describe('review and audit entry points', () => {
  it('separates API-authorized report and gate queues', async () => {
    await setup();
    expect(
      await within(screen.getByRole('region', { name: '回報審核' })).findByText(
        '成果內容',
      ),
    ).toBeInTheDocument();
    expect(
      within(screen.getByRole('region', { name: '閘門審核' })).getByText(
        '階段查核',
      ),
    ).toBeInTheDocument();
  });
  it('requires rejection text and posts the report decision only', async () => {
    const f = await setup();
    const reject = await screen.findByRole('button', { name: '退回回報' });
    expect(reject).toBeDisabled();
    fireEvent.change(screen.getByLabelText('審核意見：待確認成果'), {
      target: { value: '請補充' },
    });
    fireEvent.click(reject);
    await waitFor(() =>
      expect(f).toHaveBeenCalledWith(
        '/api/reports/r/review',
        expect.objectContaining({
          body: JSON.stringify({ decision: 'rejected', comment: '請補充' }),
        }),
      ),
    );
    expect(f.mock.calls.some(([p]) => p === '/api/gates/g')).toBe(false);
  });
  it('approves gate through its dedicated endpoint', async () => {
    const f = await setup();
    fireEvent.click(await screen.findByRole('button', { name: '核准閘門' }));
    await waitFor(() =>
      expect(f).toHaveBeenCalledWith(
        '/api/gates/g',
        expect.objectContaining({
          method: 'PATCH',
          body: JSON.stringify({ status: 'approved' }),
        }),
      ),
    );
  });
  it('keeps a conflict draft and safe 409 feedback', async () => {
    await setup('審核中心', (p) =>
      p === '/api/reports/r/review'
        ? response({ detail: 'PRIVATE' }, 409)
        : undefined,
    );
    fireEvent.change(await screen.findByLabelText('審核意見：待確認成果'), {
      target: { value: '保留意見' },
    });
    fireEvent.click(screen.getByRole('button', { name: '退回回報' }));
    expect(await screen.findByRole('alert')).not.toHaveTextContent('PRIVATE');
    expect(screen.getByLabelText('審核意見：待確認成果')).toHaveValue(
      '保留意見',
    );
  });
  it('never repeats a committed decision on reload retry', async () => {
    let reads = 0;
    const f = await setup('審核中心', (p) =>
      p.startsWith('/api/workspace/reviews') && ++reads > 1
        ? response({}, 500)
        : undefined,
    );
    fireEvent.click(await screen.findByRole('button', { name: '確認回報' }));
    const retry = await screen.findByRole('button', { name: '重試審核載入' });
    await waitFor(() => expect(retry).not.toBeDisabled());
    fireEvent.click(retry);
    await waitFor(() => expect(reads).toBe(3));
    expect(
      f.mock.calls.filter(([p]) => p === '/api/reports/r/review'),
    ).toHaveLength(1);
  });
  it('distinguishes an empty queue from failed read', async () => {
    await setup('審核中心', (p) =>
      p.startsWith('/api/workspace/reviews') ? response({}, 503) : undefined,
    );
    expect(
      await screen.findByRole('button', { name: '重試審核讀取' }),
    ).toBeInTheDocument();
    expect(screen.queryByText('目前沒有待審回報')).not.toBeInTheDocument();
  });
  it('renders safe readable audit changes with title-based filtering', async () => {
    const f = await setup('活動與稽核紀錄');
    expect(await screen.findByText('舊文字')).toBeInTheDocument();
    expect(screen.getByText('<script>安全新文字</script>')).toBeInTheDocument();
    expect(screen.queryByText('internal-note')).not.toBeInTheDocument();
    fireEvent.click(
      screen.getByRole('button', { name: '只看此任務：待確認成果' }),
    );
    await waitFor(() =>
      expect(f.mock.calls.some(([p]) => p.includes('node_id=n'))).toBe(true),
    );
    fireEvent.change(screen.getByLabelText('事件類型'), {
      target: { value: 'note.update' },
    });
    await waitFor(() =>
      expect(f.mock.calls.some(([p]) => p.includes('action=note.update'))).toBe(
        true,
      ),
    );
  });
  it('ignores late unauthorized responses after navigation', async () => {
    const pending = deferred();
    await setup('審核中心', (p) =>
      p.startsWith('/api/workspace/reviews') ? pending.promise : undefined,
    );
    fireEvent.click(screen.getByRole('button', { name: '活動與稽核紀錄' }));
    await screen.findByText('舊文字');
    await act(async () => pending.resolve(response({}, 401)));
    expect(
      screen.queryByRole('button', { name: '登入' }),
    ).not.toBeInTheDocument();
    expect(screen.getByText('舊文字')).toBeInTheDocument();
  });
});

describe('queue and audit read boundaries', () => {
  it.each([403, 404])(
    'shows a safe %s queue error with no fabricated empty state',
    async (status) => {
      await setup('審核中心', (p) =>
        p.startsWith('/api/workspace/reviews')
          ? response({ detail: 'HIDDEN' }, status)
          : undefined,
      );
      expect(await screen.findByRole('alert')).toHaveTextContent(
        status === 403 ? '沒有操作權限' : '找不到',
      );
      expect(screen.queryByText('HIDDEN')).not.toBeInTheDocument();
      expect(screen.queryByText('目前沒有待審回報')).not.toBeInTheDocument();
    },
  );
  it('expires the session after a current queue 401', async () => {
    await setup('審核中心', (p) =>
      p.startsWith('/api/workspace/reviews') ? response({}, 401) : undefined,
    );
    expect(
      await screen.findByRole('button', { name: '登入' }),
    ).toBeInTheDocument();
  });
  it('shows an actual empty queue and hides unauthorized write controls', async () => {
    await setup('審核中心', (p) =>
      p.startsWith('/api/workspace/reviews')
        ? response({
            items: [{ ...report, capabilities: { review_report: false } }],
            next_cursor: null,
          })
        : undefined,
    );
    await screen.findByText('成果內容');
    expect(
      screen.queryByRole('button', { name: '確認回報' }),
    ).not.toBeInTheDocument();
    expect(screen.getByText('目前沒有待核准閘門')).toBeInTheDocument();
  });
  it('locks duplicate decisions and ignores their late responses after leaving', async () => {
    const pending = deferred();
    const f = await setup('審核中心', (p) =>
      p === '/api/reports/r/review' ? pending.promise : undefined,
    );
    const button = await screen.findByRole('button', { name: '確認回報' });
    fireEvent.click(button);
    fireEvent.click(button);
    fireEvent.click(screen.getByRole('button', { name: '活動與稽核紀錄' }));
    await screen.findByText('舊文字');
    await act(async () => pending.resolve(response({}, 401)));
    expect(
      screen.queryByRole('button', { name: '登入' }),
    ).not.toBeInTheDocument();
    expect(
      f.mock.calls.filter(([p]) => p === '/api/reports/r/review'),
    ).toHaveLength(1);
  });
  it('appends queues without exposing counts from unreturned rows', async () => {
    await setup('審核中心', (p) =>
      p.startsWith('/api/workspace/reviews')
        ? response(
            p.includes('cursor=')
              ? { items: [gate], next_cursor: null }
              : { items: [report], next_cursor: 'more' },
          )
        : undefined,
    );
    await screen.findByText('成果內容');
    expect(screen.queryByText('階段查核')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '載入更多審核' }));
    expect(await screen.findByText('階段查核')).toBeInTheDocument();
    expect(screen.getByText('成果內容')).toBeInTheDocument();
  });
  it('cancels stale audit filters and does not render unknown payloads or internal ids', async () => {
    const pending = deferred();
    await setup('活動與稽核紀錄', (p) =>
      p.startsWith('/api/audit-logs')
        ? p.includes('action=note.update')
          ? response({
              items: [
                {
                  ...audit,
                  id: 'b',
                  action: 'unknown',
                  summary: 'UNSAFE',
                  payload: { secret: 'HIDDEN' },
                  node_id: null,
                },
              ],
              next_cursor: null,
            })
          : pending.promise
        : undefined,
    );
    fireEvent.change(screen.getByLabelText('事件類型'), {
      target: { value: 'note.update' },
    });
    await screen.findByText('其他業務事件');
    await act(async () => pending.resolve(response({}, 401)));
    expect(screen.queryByText('HIDDEN')).not.toBeInTheDocument();
    expect(screen.queryByText('UNSAFE')).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: '登入' }),
    ).not.toBeInTheDocument();
  });
  it.each([401, 403, 404])(
    'handles current audit %s without false empty content',
    async (status) => {
      await setup('活動與稽核紀錄', (p) =>
        p.startsWith('/api/audit-logs')
          ? response({ detail: 'PRIVATE' }, status)
          : undefined,
      );
      if (status === 401)
        expect(
          await screen.findByRole('button', { name: '登入' }),
        ).toBeInTheDocument();
      else
        expect(
          await screen.findByRole('button', { name: '重試稽核讀取' }),
        ).toBeInTheDocument();
      expect(
        screen.queryByText('目前沒有符合條件的紀錄'),
      ).not.toBeInTheDocument();
      expect(screen.queryByText('PRIVATE')).not.toBeInTheDocument();
    },
  );
  it('appends audit pages and clears filters by readable controls', async () => {
    const f = await setup('活動與稽核紀錄', (p) =>
      p.startsWith('/api/audit-logs')
        ? response(
            p.includes('cursor=')
              ? {
                  items: [
                    {
                      ...audit,
                      id: 'b',
                      action: 'attachment.upload',
                      payload: { original_name: '成果.txt', size_bytes: 4 },
                    },
                  ],
                  next_cursor: null,
                }
              : { items: [audit], next_cursor: 'more' },
          )
        : undefined,
    );
    fireEvent.click(
      await screen.findByRole('button', { name: '載入更多稽核' }),
    );
    expect(await screen.findByText('成果.txt')).toBeInTheDocument();
    expect(screen.getByText('舊文字')).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('事件類型'), {
      target: { value: 'attachment.upload' },
    });
    fireEvent.click(screen.getByRole('button', { name: '清除篩選' }));
    await waitFor(() =>
      expect(
        f.mock.calls
          .filter(([p]) => p.startsWith('/api/audit-logs'))
          .at(-1)?.[0],
      ).not.toContain('attachment.upload'),
    );
  });
});
it.each(['__proto__', 'constructor', 'toString'])(
  'safely labels unknown prototype action %s',
  async (action) => {
    await setup('活動與稽核紀錄', (p) =>
      p.startsWith('/api/audit-logs')
        ? response({
            items: [{ ...audit, action, payload: { secret: 'PRIVATE' } }],
            next_cursor: null,
          })
        : undefined,
    );
    expect(
      await screen.findByRole('heading', { name: '其他業務事件' }),
    ).toBeInTheDocument();
    expect(screen.getByText('同事', { exact: false })).toBeInTheDocument();
    expect(screen.queryByText('PRIVATE')).not.toBeInTheDocument();
  },
);
