import { findCreateProjectButton } from './test-navigation';
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import WorkflowLibrary from './components/WorkflowLibrary';
import App from './App';
const detail = {
  id: 'w',
  name: '既有模板',
  requires_start_date: true,
  capabilities: { edit: true, copy: true },
  nodes: [
    {
      id: 'phase',
      kind: 'phase',
      parent_id: null,
      title: '階段',
      sort_order: 0,
      gate_after: true,
      start_offset: 0,
      due_offset: 9,
    },
    {
      id: 't',
      kind: 'task',
      parent_id: 'phase',
      title: '任務',
      sort_order: 1,
      gate_after: false,
      start_offset: 1,
      due_offset: 3,
    },
  ],
  dependencies: [],
};
const list = {
  items: [{ id: 'w', name: '既有模板', requires_start_date: true }],
  capabilities: { create: true },
};
// UI4：卡片標題按鈕的「 · 含相對日期」改放在 sr-only span 裡；
// jsdom 的名稱計算會修掉 span 開頭的空白（得到「既有模板· 含相對日期」），故容許該空白差異。
const cardTitle = /^既有模板\s?· 含相對日期$/;
const response = (body: unknown, status = 200) => ({
  ok: status < 400,
  status,
  json: async () => body,
});
function setup(override?: (p: string, i?: RequestInit) => unknown) {
  const fetcher = vi.fn(async (p: string, i?: RequestInit) => {
    if (p.endsWith('/versions')) return response({items:[{version:1,author:'測試',created_at:'2026-10-10'}]});
    const custom = override?.(p, i);
    return custom ?? response(p === '/api/workflows' ? list : detail);
  });
  vi.stubGlobal('fetch', fetcher);
  const expired = vi.fn();
  render(<WorkflowLibrary expired={expired} changed={vi.fn()} />);
  return { fetcher, expired };
}
describe('workflow library', () => {
  it('creates a ten-task template with offsets, hierarchy, phase gate and FS edge', async () => {
    const { fetcher } = setup();
    fireEvent.click(await screen.findByRole('button', { name: '新增模板' }));
    fireEvent.change(screen.getByLabelText('模板名稱'), {
      target: { value: '十任務模板' },
    });
    fireEvent.click(screen.getByRole('button', { name: '新增階段列' }));
    fireEvent.change(screen.getByLabelText('節點名稱 1'), {
      target: { value: '首階段' },
    });
    fireEvent.click(screen.getByLabelText('階段閘門 1'));
    for (let i = 0; i < 10; i++) {
      fireEvent.click(screen.getByRole('button', { name: '新增任務列' }));
      fireEvent.change(screen.getByLabelText(`節點名稱 ${i + 2}`), {
        target: { value: `任務${i + 1}` },
      });
      fireEvent.change(screen.getByLabelText(`開始日偏移 ${i + 2}`), {
        target: { value: String(i) },
      });
      fireEvent.change(screen.getByLabelText(`截止日偏移 ${i + 2}`), {
        target: { value: String(i + 1) },
      });
    }
    const parent = screen.getByLabelText('父節點 2') as HTMLSelectElement;
    fireEvent.change(parent, { target: { value: parent.options[1].value } });
    const pre = screen.getByLabelText('前置任務') as HTMLSelectElement;
    fireEvent.change(pre, { target: { value: pre.options[1].value } });
    const post = screen.getByLabelText('後續任務') as HTMLSelectElement;
    fireEvent.change(post, { target: { value: post.options[1].value } });
    fireEvent.click(screen.getByRole('button', { name: '加入模板前置' }));
    fireEvent.click(screen.getByRole('button', { name: '儲存模板' }));
    await waitFor(() =>
      expect(fetcher.mock.calls.some(([, i]) => i?.method === 'POST')).toBe(
        true,
      ),
    );
    const payload = JSON.parse(
      String(
        fetcher.mock.calls.find(([, i]) => i?.method === 'POST')?.[1]?.body,
      ),
    );
    expect(
      payload.nodes.filter((n: { kind: string }) => n.kind === 'task'),
    ).toHaveLength(10);
    expect(payload.nodes[0].gate_after).toBe(true);
    expect(payload.nodes[1].parent_id).toBe(payload.nodes[0].id);
    expect(payload.nodes[10].due_offset).toBe(10);
    expect(payload.dependencies).toEqual([
      {
        predecessor_id: payload.nodes[1].id,
        successor_id: payload.nodes[2].id,
      },
    ]);
  });
  it('uses the copy endpoint with only the new name and never repeats it on read failure', async () => {
    let writes = 0;
    const { fetcher } = setup((p, i) => {
      if (i?.method === 'POST') {
        writes++;
        return response({ ...detail, id: 'copy' }, 201);
      }
      if (p === '/api/workflows/copy') return response({}, 500);
    });
    fireEvent.click(
      await screen.findByRole('button', { name: cardTitle }),
    );
    fireEvent.click(await screen.findByRole('button', { name: '複製模板' }));
    fireEvent.change(screen.getByLabelText('模板名稱'), {
      target: { value: '獨立複本' },
    });
    fireEvent.click(screen.getByRole('button', { name: '建立複本' }));
    const retry = await screen.findByRole('button', { name: '重試模板載入' });
    await waitFor(() => expect(retry).not.toBeDisabled());
    fireEvent.click(retry);
    await waitFor(() =>
      expect(
        fetcher.mock.calls.filter(([p]) => p === '/api/workflows/copy'),
      ).toHaveLength(2),
    );
    expect(writes).toBe(1);
    expect(fetcher).toHaveBeenCalledWith(
      '/api/workflows/w/copy',
      expect.objectContaining({ body: JSON.stringify({ name: '獨立複本' }) }),
    );
  });
  it('updates existing templates without allowing nested phases', async () => {
    const { fetcher } = setup();
    fireEvent.click(
      await screen.findByRole('button', { name: cardTitle }),
    );
    fireEvent.click(await screen.findByRole('button', { name: '編輯模板' }));
    expect(screen.queryByLabelText('父節點 1')).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('節點名稱 2'), {
      target: { value: '更新任務' },
    });
    fireEvent.click(screen.getByRole('button', { name: '儲存模板' }));
    await waitFor(() =>
      expect(fetcher.mock.calls.some(([, i]) => i?.method === 'PUT')).toBe(
        true,
      ),
    );
  });
  it('shows readonly templates without authoring actions', async () => {
    setup((p) =>
      response(
        p === '/api/workflows'
          ? { ...list, capabilities: { create: false } }
          : { ...detail, capabilities: { edit: false, copy: false } },
      ),
    );
    fireEvent.click(
      await screen.findByRole('button', { name: cardTitle }),
    );
    await screen.findByRole('region', { name: '模板內容' });
    expect(
      screen.queryByRole('button', { name: '新增模板' }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: '編輯模板' }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: '複製模板' }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: '用這套工作流建立專案' }),
    ).not.toBeInTheDocument();
  });
  it('ignores late detail expiry when replaced by a new form', async () => {
    let resolve!: (v: unknown) => void;
    const { expired } = setup((p) =>
      p === '/api/workflows/w' ? new Promise((r) => (resolve = r)) : undefined,
    );
    fireEvent.click(
      await screen.findByRole('button', { name: cardTitle }),
    );
    fireEvent.click(screen.getByRole('button', { name: '新增模板' }));
    fireEvent.change(screen.getByLabelText('模板名稱'), {
      target: { value: '新草稿' },
    });
    await act(async () => resolve(response({}, 401)));
    expect(expired).not.toHaveBeenCalled();
    expect(screen.getByLabelText('模板名稱')).toHaveValue('新草稿');
  });
  it('requires an anchor date for offset templates and includes it in project creation', async () => {
    const fetcher = vi.fn(async (p: string, i?: RequestInit) =>
      response(
        p === '/api/auth/me'
          ? {
              user: { id: 'u', role: 'admin', display_name: '管理者' },
              organization: { id: 'o', name: '公司' },
            }
          : p === '/api/projects'
            ? { items: [] }
            : p === '/api/workflows'
              ? list
              : p === '/api/projects/from-workflow'
                ? { id: 'p', title: '新專案' }
                : p === '/api/projects/p'
                  ? {
                      id: 'p',
                      title: '新專案',
                      nodes: [],
                      gates: [],
                      capabilities: { create_node: true },
                    }
                  : {
                      project_count: 0,
                      task_counts: {
                        todo: 0,
                        doing: 0,
                        review: 0,
                        done: 0,
                        skipped: 0,
                      },
                      completion_percent: null,
                      projects: [],
                    },
      ),
    );
    vi.stubGlobal('fetch', fetcher);
    render(<App />);
    fireEvent.click(await findCreateProjectButton());
    fireEvent.change(await screen.findByLabelText('工作流模板'), {
      target: { value: 'w' },
    });
    fireEvent.change(screen.getByLabelText('新專案名稱'), {
      target: { value: '新專案' },
    });
    expect(screen.getByRole('button', { name: '建立專案' })).toBeDisabled();
    fireEvent.change(screen.getByLabelText('專案開始日'), {
      target: { value: '2026-10-09' },
    });
    fireEvent.click(screen.getByRole('button', { name: '建立專案' }));
    await waitFor(() =>
      expect(fetcher).toHaveBeenCalledWith(
        '/api/projects/from-workflow',
        expect.objectContaining({
          body: JSON.stringify({
            workflow_id: 'w',
            title: '新專案',
            start_date: '2026-10-09',
          }),
        }),
      ),
    );
  });
});
