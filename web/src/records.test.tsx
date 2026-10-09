import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import App from './App';
const session = {
  user: { id: 'u', role: 'admin', display_name: '管理者' },
  organization: { id: 'o', name: '公司' },
};
const node = {
  id: 'n',
  project_id: 'p',
  parent_id: null,
  kind: 'task',
  title: '成果任務',
  status: 'doing',
  owner_user_id: 'u',
  department_id: null,
  sort_order: 0,
  start_date: null,
  due_date: null,
  owner_display_name: '管理者',
  department_name: null,
  capabilities: {
    edit_metadata: true,
    assign: true,
    create_child: true,
    write_record: true,
    submit_report: true,
    review_report: true,
    manage_collaborators: true,
    lifecycle: true,
  },
  state_actions: [
    'todo',
    'doing',
    'submit_report',
    'submit_and_approve',
    'skip',
  ],
};
const project = {
  id: 'p',
  title: '紀錄專案',
  owner_user_id: 'u',
  nodes: [node],
  gates: [],
  capabilities: { create_node: true },
};
const report = {
  type: 'report',
  id: 'r',
  node_id: 'n',
  node_title: node.title,
  version: 1,
  legacy: false,
  result: '達成',
  summary: '前版成果',
  finished_on: '2026-10-08',
  status: 'rejected',
  submitted_by: 'u',
  submitted_by_display_name: '管理者',
  submitted_at: '2026-10-08',
  reviewed_by: 'other',
  reviewed_by_display_name: '審核者',
  reviewed_at: '2026-10-08',
  review_comment: '請补充',
  self_approved: false,
  attachments: [],
  created_at: '2026-10-08',
};
const response = (body: unknown, status = 200) => ({
  ok: status < 400,
  status,
  json: async () => body,
});
async function setup(
  items: unknown[] = [],
  override?: (path: string, init?: RequestInit) => unknown,
  value = node,
) {
  const fetcher = vi.fn(async (path: string, init?: RequestInit) => {
    const custom = override?.(path, init);
    if (custom !== undefined) return custom;
    if (path === '/api/auth/me') return response(session);
    if (path === '/api/auth/logout') return response(undefined, 204);
    if (path === '/api/projects') return response({ items: [project] });
    if (path === '/api/projects/p')
      return response({ ...project, nodes: [value] });
    if (path === '/api/workspace/overview')
      return response({
        project_count: 1,
        completion_percent: 0,
        task_counts: { todo: 0, doing: 1, review: 0, done: 0, skipped: 0 },
        projects: [],
      });
    if (path.includes('/records?'))
      return response({ items, next_cursor: null });
    if (path.endsWith('attachment-quota'))
      return response({
        limit_bytes: 1000000000,
        charged_bytes: 0,
        remaining_bytes: 1000000000,
      });
    if (path.endsWith('assignment-options'))
      return response({
        users: [{ id: 'other', display_name: '同事' }],
        departments: [],
      });
    if (path.endsWith('collaborators'))
      return response({ users: [], departments: [], revision: 0 });
    return response(report, 201);
  });
  vi.stubGlobal('fetch', fetcher);
  render(<App />);
  fireEvent.click(await within(await screen.findByLabelText('專案清單')).findByRole('button', { name: '紀錄專案' }));
  // UI4: the node tree is gone; tasks are entered from their project-board card.
  fireEvent.click(
    within(await screen.findByLabelText('看板')).getByRole('button', {
      name: node.title,
    }),
  );
  return fetcher;
}
async function openPeople() {
  // UI4: collaborator editing moved from the records tab to「成員與權限」.
  fireEvent.click(await screen.findByRole('tab', { name: '成員與權限' }));
}
async function fillReport() {
  // UI4: the report form is collapsed until「回報完成」is pressed.
  fireEvent.click(await screen.findByRole('button', { name: '回報完成' }));
  fireEvent.change(await screen.findByLabelText('成果說明'), {
    target: { value: '完成驗證' },
  });
  fireEvent.change(screen.getByLabelText('實際完成日'), {
    target: { value: '2026-10-08' },
  });
}
describe('P2b task records', () => {
  it('defaults tasks to records and restricts direct state changes to API actions', async () => {
    await setup();
    expect(await screen.findByRole('tab', { name: '紀錄' })).toHaveAttribute(
      'aria-selected',
      'true',
    );
    expect(
      within(screen.getByLabelText('節點詳情')).queryByRole('option', {
        name: '完成',
      }),
    ).not.toBeInTheDocument();
  });
  it.each([false, true])(
    'submits a complete new report with explicit self approval %s',
    async (self) => {
      const fetcher = await setup();
      await fillReport();
      fireEvent.click(
        screen.getByRole('button', { name: self ? '送出並確認' : '送出回報' }),
      );
      await waitFor(() =>
        expect(
          fetcher.mock.calls.some(([path]) => path === '/api/nodes/n/reports'),
        ).toBe(true),
      );
      expect(fetcher).toHaveBeenCalledWith(
        '/api/nodes/n/reports',
        expect.objectContaining({
          body: JSON.stringify({
            result: '達成',
            summary: '完成驗證',
            finished_on: '2026-10-08',
            attachment_ids: [],
            self_approve: self,
          }),
        }),
      );
    },
  );
  it('keeps rejected history and clearly creates a new version', async () => {
    await setup([report]);
    expect(await screen.findByText('v1 已退回')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '回報完成' })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '重新回報' }));
    expect(screen.getByLabelText('成果說明')).toHaveValue('前版成果');
    expect(screen.getByText('重新送出將建立新版本')).toBeInTheDocument();
  });
  it('cancels a lifecycle reason without writing', async () => {
    const fetcher = await setup();
    fireEvent.click(await screen.findByRole('button', { name: '略過任務' }));
    expect(screen.getByRole('button', { name: '確認略過' })).toBeDisabled();
    fireEvent.change(screen.getByLabelText('操作理由'), {
      target: { value: '取消測試' },
    });
    fireEvent.click(screen.getByRole('button', { name: '取消操作' }));
    expect(
      fetcher.mock.calls.some(([path]) => path.endsWith('/lifecycle')),
    ).toBe(false);
  });
  it('offers notes and collaborator settings only through capabilities', async () => {
    await setup();
    expect(await screen.findByLabelText('新增筆記')).toBeInTheDocument();
    await openPeople();
    expect(
      await screen.findByRole('button', { name: '協作設定' }),
    ).toBeInTheDocument();
  });
});
function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((r) => {
    resolve = r;
  });
  return { promise, resolve };
}
const note = {
  type: 'note',
  id: 'note1',
  node_id: 'n',
  node_title: node.title,
  body: '原始筆記',
  author_id: 'u',
  author_display_name: '管理者',
  revision: 3,
  created_at: '2026-10-08',
  edited_at: null,
  attachments: [],
};
describe('records asynchronous safety', () => {
  it('does not offer submission until all latest-report pages are loaded', async () => {
    const pending = deferred<unknown>();
    const fetcher = await setup([], (path) =>
      path.includes('limit=100')
        ? path.includes('cursor=')
          ? pending.promise
          : response({ items: [], next_cursor: 'next' })
        : undefined,
    );
    expect(await screen.findByText('正在確認完整回報歷史')).toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: '送出回報' }),
    ).not.toBeInTheDocument();
    for (const name of ['回報完成', '重新回報'])
      expect(screen.queryByRole('button', { name })).not.toBeInTheDocument();
    await act(async () =>
      pending.resolve(response({ items: [report], next_cursor: null })),
    );
    expect(await screen.findByText('v1 已退回')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '重新回報' })).toBeInTheDocument();
    expect(
      fetcher.mock.calls.filter(([p]) => p.includes('limit=50')),
    ).toHaveLength(1);
  });
  it('retries failed history only with GET and keeps empty distinct from failure', async () => {
    let failed = true;
    const fetcher = await setup([], (p) =>
      p.includes('limit=100') && failed ? response({}, 500) : undefined,
    );
    expect(
      await screen.findByRole('button', { name: '重試回報讀取' }),
    ).toBeInTheDocument();
    expect(
      screen.queryByText('需填：結果、成果說明、實際完成日・送出後由有權審核者確認。'),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: '回報完成' }),
    ).not.toBeInTheDocument();
    failed = false;
    fireEvent.click(screen.getByRole('button', { name: '重試回報讀取' }));
    fireEvent.click(await screen.findByRole('button', { name: '回報完成' }));
    expect(
      screen.getByText('需填：結果、成果說明、實際完成日・送出後由有權審核者確認。'),
    ).toBeInTheDocument();
    expect(
      await screen.findByRole('button', { name: '送出回報' }),
    ).toBeInTheDocument();
    expect(fetcher.mock.calls.every(([, i]) => !i?.method)).toBe(true);
  });
  it('never repeats a successful POST when project reload fails', async () => {
    let reloads = 0;
    const fetcher = await setup([], (p) =>
      p === '/api/projects/p' && ++reloads > 1 ? response({}, 500) : undefined,
    );
    await fillReport();
    fireEvent.click(screen.getByRole('button', { name: '送出回報' }));
    fireEvent.click(screen.getByRole('button', { name: '送出回報' }));
    const retry = await screen.findByRole('button', { name: '重試回報載入' });
    await waitFor(() => expect(retry).not.toBeDisabled());
    fireEvent.click(retry);
    await waitFor(() => expect(reloads).toBe(3));
    expect(
      fetcher.mock.calls.filter(([p]) => p.endsWith('/reports')),
    ).toHaveLength(1);
  });
  it('does not submit a report while an attachment upload is pending', async () => {
    const pending = deferred<unknown>();
    const fetcher = await setup([], (p) =>
      p.includes('/attachments?') ? pending.promise : undefined,
    );
    await fillReport();
    const input = screen.getByLabelText('回報附件');
    await waitFor(() => expect(input).not.toBeDisabled());
    const file = new File(['data'], '成果.txt', { type: 'text/plain' });
    fireEvent.change(input, { target: { files: [file] } });
    expect(screen.getByRole('button', { name: '送出回報' })).toBeDisabled();
    await act(async () => pending.resolve(response({ id: 'a' }, 201)));
    fireEvent.click(screen.getByRole('button', { name: '送出回報' }));
    await waitFor(() =>
      expect(
        fetcher.mock.calls.some(
          ([p, i]) =>
            p.endsWith('/reports') &&
            String(i?.body).includes('"attachment_ids":["a"]'),
        ),
      ).toBe(true),
    );
    const upload = fetcher.mock.calls.find(([p]) =>
      p.includes('/attachments?'),
    );
    expect(upload?.[1]?.body).toBe(file);
    expect(new Headers(upload?.[1]?.headers).get('Content-Type')).toBe(
      'application/octet-stream',
    );
  });
  it('drops uploaded and pending attachments when the report form is cancelled', async () => {
    const pending = deferred<unknown>();
    let uploads = 0;
    const fetcher = await setup([], (p) =>
      p.includes('/attachments?')
        ? ++uploads === 1
          ? response({ id: 'a' }, 201)
          : pending.promise
        : undefined,
    );
    await fillReport();
    let input = screen.getByLabelText('回報附件');
    await waitFor(() => expect(input).not.toBeDisabled());
    fireEvent.change(input, { target: { files: [new File(['a'], 'a.txt')] } });
    await waitFor(() => expect(screen.getByRole('button', { name: '送出回報' })).not.toBeDisabled());
    fireEvent.click(screen.getByRole('button', { name: '取消回報' }));
    expect(screen.queryByLabelText('回報表單')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: '回報完成' })).toHaveFocus();
    // An upload still in flight when cancelling must not leave submission blocked.
    await fillReport();
    input = screen.getByLabelText('回報附件');
    await waitFor(() => expect(input).not.toBeDisabled());
    fireEvent.change(input, { target: { files: [new File(['b'], 'b.txt')] } });
    expect(screen.getByRole('button', { name: '送出回報' })).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: '取消回報' }));
    await act(async () => pending.resolve(response({ id: 'b' }, 201)));
    await fillReport();
    expect(screen.getByRole('button', { name: '送出回報' })).not.toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: '送出回報' }));
    await waitFor(() =>
      expect(fetcher.mock.calls.some(([p]) => p.endsWith('/reports'))).toBe(true),
    );
    const posts = fetcher.mock.calls.filter(([p]) => p.endsWith('/reports'));
    expect(posts).toHaveLength(1);
    expect(String(posts[0][1]?.body)).toContain('"attachment_ids":[]');
  });
  it('keeps malformed attachment errors safe and prevents report submission', async () => {
    await setup([], (p) =>
      p.includes('/attachments?')
        ? response({ detail: [{ input: 'PRIVATE' }] }, 422)
        : undefined,
    );
    await fillReport();
    const input = screen.getByLabelText('回報附件');
    await waitFor(() => expect(input).not.toBeDisabled());
    fireEvent.change(input, {
      target: { files: [new File(['bad'], 'bad.pdf')] },
    });
    expect(await screen.findByRole('alert')).toHaveTextContent('附件');
    expect(screen.queryByText('PRIVATE')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: '送出回報' })).toBeDisabled();
  });
  it('requires rejection reason and prevents own report review', async () => {
    await setup([{ ...report, status: 'submitted' }], undefined, {
      ...node,
      status: 'review',
      state_actions: [],
    });
    await screen.findByText('v1 等待確認');
    expect(
      screen.queryByRole('button', { name: '確認回報' }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: '送出並確認' }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: '回報完成' }),
    ).not.toBeInTheDocument();
  });
  it('reviews another author only with an explicit decision', async () => {
    const fetcher = await setup(
      [{ ...report, status: 'submitted', submitted_by: 'other' }],
      undefined,
      { ...node, status: 'review', state_actions: [] },
    );
    expect(
      await screen.findByRole('button', { name: '退回回報' }),
    ).toBeDisabled();
    fireEvent.change(screen.getByLabelText('審核意見'), {
      target: { value: '補充證據' },
    });
    fireEvent.click(screen.getByRole('button', { name: '退回回報' }));
    await waitFor(() =>
      expect(fetcher).toHaveBeenCalledWith(
        '/api/reports/r/review',
        expect.objectContaining({
          body: JSON.stringify({ decision: 'rejected', comment: '補充證據' }),
        }),
      ),
    );
  });
  it('keeps a note conflict draft and sends the expected revision', async () => {
    const fetcher = await setup([note], (p) =>
      p === '/api/notes/note1' ? response({}, 409) : undefined,
    );
    fireEvent.click(await screen.findByRole('button', { name: '修改筆記' }));
    fireEvent.change(screen.getByLabelText('編輯筆記'), {
      target: { value: '保留我的修改' },
    });
    fireEvent.click(screen.getByRole('button', { name: '儲存筆記' }));
    await screen.findByRole('alert');
    expect(screen.getByLabelText('編輯筆記')).toHaveValue('保留我的修改');
    expect(fetcher).toHaveBeenCalledWith(
      '/api/notes/note1',
      expect.objectContaining({
        body: JSON.stringify({ body: '保留我的修改', expected_revision: 3 }),
      }),
    );
  });
  it('appends visible records only on demand independently of latest-report scan', async () => {
    await setup([], (p) =>
      p.includes('limit=50')
        ? response(
            p.includes('cursor=')
              ? {
                  items: [{ ...note, id: 'note2', body: '第二頁可見筆記' }],
                  next_cursor: null,
                }
              : { items: [note], next_cursor: 'page2' },
          )
        : undefined,
    );
    await screen.findByText('原始筆記');
    expect(screen.queryByText('第二頁可見筆記')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '載入更多紀錄' }));
    expect(await screen.findByText('第二頁可見筆記')).toBeInTheDocument();
    expect(screen.getByText('原始筆記')).toBeInTheDocument();
  });
  it('offers no record mutations after capabilities are revoked', async () => {
    await setup([note], undefined, {
      ...node,
      capabilities: {
        ...node.capabilities,
        write_record: false,
        submit_report: false,
        review_report: false,
        manage_collaborators: false,
        lifecycle: false,
      },
      state_actions: [],
    });
    await screen.findByText('原始筆記');
    expect(screen.queryByLabelText('新增筆記')).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: '協作設定' }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: '送出回報' }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: '回報完成' }),
    ).not.toBeInTheDocument();
    expect(screen.queryByLabelText('選擇附件')).not.toBeInTheDocument();
    await openPeople();
    expect(await screen.findByText('尚未設定協作')).toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: '協作設定' }),
    ).not.toBeInTheDocument();
  });
});

describe('record session and replacement races', () => {
  it('ignores a late successful mutation after navigation', async () => {
    const pending = deferred<unknown>();
    let reads = 0;
    const fetcher = await setup([], (p) => {
      if (p === '/api/projects/p') reads++;
      if (p.endsWith('/reports')) return pending.promise;
    });
    await fillReport();
    fireEvent.click(screen.getByRole('button', { name: '送出回報' }));
    fireEvent.click(screen.getByRole('button', { name: '所有專案總覽' }));
    await act(async () => pending.resolve(response(report, 201)));
    expect(reads).toBe(1);
    expect(screen.queryByLabelText('成果說明')).not.toBeInTheDocument();
    expect(
      fetcher.mock.calls.filter(([p]) => p.endsWith('/reports')),
    ).toHaveLength(1);
  });
  it('clears drafts and files when a record mutation returns 401', async () => {
    await setup([], (p) =>
      p.endsWith('/reports') ? response({}, 401) : undefined,
    );
    await fillReport();
    fireEvent.click(screen.getByRole('button', { name: '送出回報' }));
    expect(
      await screen.findByRole('button', { name: '登入' }),
    ).toBeInTheDocument();
    expect(screen.queryByLabelText('成果說明')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('回報附件')).not.toBeInTheDocument();
  });
  it('does not automatically repeat uncertain network writes', async () => {
    const fetcher = await setup([], (p) =>
      p.endsWith('/reports')
        ? Promise.reject(new TypeError('network'))
        : undefined,
    );
    await fillReport();
    fireEvent.click(screen.getByRole('button', { name: '送出回報' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('重新整理確認');
    expect(
      fetcher.mock.calls.filter(([p]) => p.endsWith('/reports')),
    ).toHaveLength(1);
    expect(screen.getByLabelText('成果說明')).toHaveValue('完成驗證');
  });
  it('ignores a late 401 after logout and a fresh login screen', async () => {
    const pending = deferred<unknown>();
    await setup([], (p) =>
      p.endsWith('/reports') ? pending.promise : undefined,
    );
    await fillReport();
    fireEvent.click(screen.getByRole('button', { name: '送出回報' }));
    fireEvent.click(screen.getByRole('button', { name: '登出' }));
    await screen.findByRole('button', { name: '登入' });
    await act(async () => pending.resolve(response({}, 401)));
    expect(screen.getByRole('button', { name: '登入' })).toBeInTheDocument();
    expect(
      screen.queryByText('登入已失效，請重新登入'),
    ).not.toBeInTheDocument();
  });
  it('does not let an old note reload discard a replacement note draft', async () => {
    const pending = deferred<unknown>();
    let reads = 0;
    await setup([note, { ...note, id: 'note2', body: '另一則' }], (p) =>
      p === '/api/projects/p' && ++reads > 1 ? pending.promise : undefined,
    );
    const edits = await screen.findAllByRole('button', { name: '修改筆記' });
    fireEvent.click(edits[0]);
    fireEvent.change(screen.getByLabelText('編輯筆記'), {
      target: { value: '已保存' },
    });
    fireEvent.click(screen.getByRole('button', { name: '儲存筆記' }));
    await waitFor(() => expect(reads).toBe(2));
    fireEvent.click(edits[1]);
    fireEvent.change(screen.getByLabelText('編輯筆記'), {
      target: { value: '新的草稿' },
    });
    await act(async () => pending.resolve(response(project)));
    expect(screen.getByLabelText('編輯筆記')).toHaveValue('新的草稿');
  });
  it('retains collaboration selections after stale-revision conflict without resending', async () => {
    const fetcher = await setup([], (p, i) =>
      p.endsWith('/collaborators') && i?.method === 'PUT'
        ? response({}, 409)
        : undefined,
    );
    await openPeople();
    fireEvent.click(await screen.findByRole('button', { name: '協作設定' }));
    fireEvent.click(screen.getByRole('checkbox', { name: '同事' }));
    fireEvent.click(screen.getByRole('button', { name: '儲存協作' }));
    expect(await screen.findByRole('alert')).toBeInTheDocument();
    expect(screen.getByRole('checkbox', { name: '同事' })).toBeChecked();
    expect(
      fetcher.mock.calls.filter(([, i]) => i?.method === 'PUT'),
    ).toHaveLength(1);
  });
});
it('returns keyboard focus to collaboration trigger on cancel', async () => {
  await setup();
  await openPeople();
  const trigger = await screen.findByRole('button', { name: '協作設定' });
  fireEvent.click(trigger);
  fireEvent.click(screen.getByRole('button', { name: '取消協作' }));
  expect(screen.getByRole('button', { name: '協作設定' })).toHaveFocus();
});
it('downloads an authorized Blob, releases its URL and never previews attachments', async () => {
  const create = vi.fn(() => 'blob:authorized');
  const revoke = vi.fn();
  vi.stubGlobal(
    'URL',
    class extends URL {
      static createObjectURL = create;
      static revokeObjectURL = revoke;
    },
  );
  const click = vi
    .spyOn(HTMLAnchorElement.prototype, 'click')
    .mockImplementation(() => {});
  const attachment = {
    type: 'attachment',
    id: 'a',
    node_id: 'n',
    node_title: node.title,
    original_name: '安全.txt',
    size_bytes: 4,
    uploaded_by: 'u',
    uploaded_by_display_name: '管理者',
    created_at: '2026-10-08',
    report_id: 'r',
    note_id: null,
  };
  await setup([attachment], (p) =>
    p.endsWith('/download')
      ? { ok: true, status: 200, blob: async () => new Blob(['safe']) }
      : undefined,
  );
  fireEvent.click(await screen.findByRole('button', { name: '下載 安全.txt' }));
  await waitFor(() => expect(revoke).toHaveBeenCalledWith('blob:authorized'));
  expect(create).toHaveBeenCalledTimes(1);
  expect(click).toHaveBeenCalledTimes(1);
  expect(
    screen.queryByRole('button', { name: '移除 安全.txt' }),
  ).not.toBeInTheDocument();
  expect(document.querySelector('iframe,object,embed')).toBeNull();
  click.mockRestore();
});
it('shows safe revoked-download failure without creating a URL', async () => {
  const create = vi.fn();
  vi.stubGlobal(
    'URL',
    class extends URL {
      static createObjectURL = create;
    },
  );
  const attachment = {
    type: 'attachment',
    id: 'a',
    node_id: 'n',
    node_title: node.title,
    original_name: '撤銷.txt',
    size_bytes: 4,
    uploaded_by: 'u',
    uploaded_by_display_name: '管理者',
    created_at: '2026-10-08',
    report_id: null,
    note_id: null,
  };
  await setup([attachment], (p) =>
    p.endsWith('/download')
      ? response({ detail: 'secret hidden node' }, 404)
      : undefined,
  );
  fireEvent.click(await screen.findByRole('button', { name: '下載 撤銷.txt' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('找不到附件');
  expect(create).not.toHaveBeenCalled();
  expect(screen.queryByText('secret hidden node')).not.toBeInTheDocument();
});
it('does not request hidden ancestors or show unseen records from a pagination error', async () => {
  const fetcher = await setup([], (p) =>
    p.includes('limit=50')
      ? response(
          p.includes('cursor=')
            ? { detail: 'hidden ancestor' }
            : { items: [note], next_cursor: 'visible-only' },
          p.includes('cursor=') ? 422 : 200,
        )
      : undefined,
  );
  fireEvent.click(await screen.findByRole('button', { name: '載入更多紀錄' }));
  expect(
    await screen.findByRole('button', { name: '重試紀錄讀取' }),
  ).toBeInTheDocument();
  expect(screen.queryByText('hidden ancestor')).not.toBeInTheDocument();
  expect(
    fetcher.mock.calls
      .filter(([p]) => p.includes('/nodes/'))
      .every(([p]) => p.includes('/nodes/n/')),
  ).toBe(true);
});
describe('legacy and incomplete attachment reads', () => {
  it('labels legacy submitted reports outside the new review workflow', async () => {
    await setup(
      [{ ...report, legacy: true, status: 'submitted', version: 0 }],
      undefined,
      { ...node, status: 'review', state_actions: ['submit_report'] },
    );
    expect(
      await screen.findAllByText('歷史回報（未納入新審核流程）'),
    ).toHaveLength(2);
    expect(screen.queryByText(/等待確認/)).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: '確認回報' }),
    ).not.toBeInTheDocument();
  });
  it('does not claim no attachments while the first records GET is pending', async () => {
    const pending = deferred<unknown>();
    await setup([], (p) =>
      p.includes('limit=50') ? pending.promise : undefined,
    );
    expect(
      within(await screen.findByRole('region', { name: '附件' })).queryByText(
        '還沒有附件。',
      ),
    ).not.toBeInTheDocument();
    await act(async () =>
      pending.resolve(response({ items: [], next_cursor: null })),
    );
    expect(await screen.findByText('還沒有附件。')).toBeInTheDocument();
  });
  it('does not claim no attachments after a records GET failure and exposes retry', async () => {
    await setup([], (p) =>
      p.includes('limit=50') ? response({}, 500) : undefined,
    );
    await screen.findByRole('button', { name: '重試紀錄讀取' });
    expect(
      within(screen.getByRole('region', { name: '附件' })).queryByText(
        '還沒有附件。',
      ),
    ).not.toBeInTheDocument();
  });
  it('qualifies incomplete attachment pages and appends the later attachment', async () => {
    const attachment = {
      type: 'attachment',
      id: 'a',
      node_id: 'n',
      node_title: node.title,
      original_name: '後頁.txt',
      size_bytes: 4,
      uploaded_by: 'u',
      uploaded_by_display_name: '管理者',
      created_at: '2026-10-08',
      report_id: null,
      note_id: null,
    };
    await setup([], (p) =>
      p.includes('limit=50')
        ? response(
            p.includes('cursor=')
              ? { items: [attachment], next_cursor: null }
              : { items: [note], next_cursor: 'next' },
          )
        : undefined,
    );
    expect(
      await screen.findByText('目前已載入的紀錄沒有附件。'),
    ).toBeInTheDocument();
    expect(screen.queryByText('還沒有附件。')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '載入更多紀錄' }));
    expect(
      await screen.findByRole('button', { name: '下載 後頁.txt' }),
    ).toBeInTheDocument();
    expect(
      screen.queryByText('目前已載入的紀錄沒有附件。'),
    ).not.toBeInTheDocument();
  });
});
