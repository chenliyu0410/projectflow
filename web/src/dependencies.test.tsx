import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import DependencyPanel from './components/DependencyPanel';
const data = {
  items: [{ id: 'e', project_id: 'p', predecessor_id: 'a', successor_id: 'b' }],
  nodes: [
    { id: 'a', title: '前項', status: 'todo', blocked: false },
    { id: 'b', title: '後項', status: 'todo', blocked: true },
  ],
  capabilities: { manage: true },
};
const response = (body: unknown, status = 200) => ({
  ok: status < 400,
  status,
  json: async () => body,
});
describe('visible dependency editing', () => {
  it('shows only safe blockage and visible edges with keyboard node navigation', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(data)));
    const select = vi.fn();
    render(
      <DependencyPanel
        projectId="p"
        select={select}
        reload={vi.fn()}
        expired={vi.fn()}
      />,
    );
    const entry = await screen.findByRole('button', { name: '追蹤相依：後項' });
    expect(screen.getAllByText(/尚有未完成的前置任務/).length).toBeGreaterThan(
      0,
    );
    expect(entry).toHaveAttribute(
      'title',
      expect.stringContaining('：尚有未完成的前置任務'),
    );
    expect(
      screen.getByRole('button', { name: '追蹤相依：前項' }),
    ).not.toHaveAttribute('title', expect.stringContaining('尚有未完成'));
    // UI4：方塊改為原生 HTML button，可用 Tab 聚焦、Enter／Space 由瀏覽器觸發 click。
    // jsdom 不會把 keyDown 轉成 click，因此驗證它是可聚焦的原生按鈕後以 click 代表啟用。
    expect(entry.tagName).toBe('BUTTON');
    expect(entry).not.toBeDisabled();
    expect(entry).not.toHaveAttribute('tabindex', '-1');
    entry.focus();
    expect(entry).toHaveFocus();
    fireEvent.click(entry);
    expect(select).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: '開啟任務 →' }));
    expect(select).toHaveBeenCalledTimes(1);
    expect(select).toHaveBeenCalledWith('b');
    expect(screen.queryByText('hidden')).not.toBeInTheDocument();
  });
  it('keeps a rejected cyclic edge selection and displays a safe message', async () => {
    const f = vi.fn(async (_p: string, i?: RequestInit) =>
      response(
        i?.method ? { detail: 'INTERNAL' } : data,
        i?.method ? 422 : 200,
      ),
    );
    vi.stubGlobal('fetch', f);
    render(
      <DependencyPanel
        projectId="p"
        select={vi.fn()}
        reload={vi.fn()}
        expired={vi.fn()}
      />,
    );
    const open = await screen.findByRole('button', { name: '建立相依連線' });
    expect(open).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByLabelText('前置任務')).not.toBeInTheDocument();
    fireEvent.click(open);
    expect(open).toHaveAttribute('aria-expanded', 'true');
    fireEvent.change(await screen.findByLabelText('前置任務'), {
      target: { value: 'b' },
    });
    fireEvent.change(screen.getByLabelText('後續任務'), {
      target: { value: 'a' },
    });
    fireEvent.click(screen.getByRole('button', { name: '新增前置' }));
    expect(await screen.findByRole('alert')).not.toHaveTextContent('INTERNAL');
    expect(screen.getByLabelText('前置任務')).toHaveValue('b');
    expect(screen.getByLabelText('後續任務')).toHaveValue('a');
    expect(f.mock.calls.filter(([, i]) => i?.method === 'POST')).toHaveLength(
      1,
    );
    expect(f).toHaveBeenCalledWith(
      '/api/projects/p/dependencies',
      expect.objectContaining({
        body: JSON.stringify({ predecessor_id: 'b', successor_id: 'a', relation_type: 'FS', lag_days: 0, enforcement: 'hard' }),
      }),
    );
  });
  it('deletes the edge only and retries only GET after write success', async () => {
    const f = vi.fn(async (_p: string, i?: RequestInit) =>
      response(i?.method ? { deleted: true } : data),
    );
    vi.stubGlobal('fetch', f);
    const reload = vi.fn().mockRejectedValue(new Error('read'));
    render(
      <DependencyPanel
        projectId="p"
        select={vi.fn()}
        reload={reload}
        expired={vi.fn()}
      />,
    );
    fireEvent.click(
      await screen.findByRole('button', { name: '移除前置：前項 → 後項' }),
    );
    const retry = await screen.findByRole('button', { name: '重試前置載入' });
    await waitFor(() => expect(retry).not.toBeDisabled());
    fireEvent.click(retry);
    await waitFor(() => expect(reload).toHaveBeenCalledTimes(2));
    expect(f.mock.calls.filter(([, i]) => i?.method === 'DELETE')).toHaveLength(
      1,
    );
    expect(f).toHaveBeenCalledWith(
      '/api/dependencies/e',
      expect.objectContaining({ method: 'DELETE' }),
    );
  });
  it('hides mutations without API management capability', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValue(
          response({ ...data, capabilities: { manage: false } }),
        ),
    );
    render(
      <DependencyPanel
        projectId="p"
        select={vi.fn()}
        reload={vi.fn()}
        expired={vi.fn()}
      />,
    );
    await screen.findByRole('heading', { name: '可見前置連線' });
    // UI4：新增表單要先按「建立相依連線」才出現；無權限時連開啟按鈕都不應存在。
    expect(
      screen.queryByRole('button', { name: '建立相依連線' }),
    ).not.toBeInTheDocument();
    expect(screen.queryByLabelText('前置任務')).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: /移除前置/ }),
    ).not.toBeInTheDocument();
  });
  it('does not expire a new view after an old request is unmounted', async () => {
    let resolve!: (v: unknown) => void;
    vi.stubGlobal(
      'fetch',
      vi.fn(() => new Promise((r) => (resolve = r))),
    );
    const expired = vi.fn();
    const { unmount } = render(
      <DependencyPanel
        projectId="p"
        select={vi.fn()}
        reload={vi.fn()}
        expired={expired}
      />,
    );
    unmount();
    await act(async () => resolve(response({}, 401)));
    expect(expired).not.toHaveBeenCalled();
  });
});
