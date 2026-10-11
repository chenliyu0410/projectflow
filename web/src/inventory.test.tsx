import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import InventoryPanel from './components/InventoryPanel';
import OperationsManager from './components/OperationsManager';

it('retries an uncertain posting with the identical request and blocks draft navigation', async () => {
  const posts: string[] = [];
  vi.spyOn(window, 'confirm').mockReturnValue(true);
  vi.spyOn(window, 'alert').mockImplementation(() => {});
  vi.stubGlobal('fetch', vi.fn(async (path: string, init?: RequestInit) => {
    if (init?.method === 'POST') {
      posts.push(String(init.body));
      if (posts.length === 1) throw new TypeError('network interrupted after posting');
      return new Response('{}', { status: 200 });
    }
    return new Response(JSON.stringify(path.includes('/resources/') ? { quantity: posts.length ? '3.000' : '0.000', unit: 'kg' } : { items: [], total: 0, offset: 0, limit: 30 }), { status: 200 });
  }));
  const guard = { current: null as (() => boolean) | null };
  render(<InventoryPanel record={{ id: 'r', category: 'resources', code: 'MAT', title: '物料' }} expired={vi.fn()} leaveGuard={guard} />);
  await screen.findByLabelText('目前庫存');
  fireEvent.change(screen.getByLabelText('異動數量'), { target: { value: '3' } });
  fireEvent.change(screen.getByLabelText('異動原因／收貨說明'), { target: { value: '期初盤點' } });
  fireEvent.click(screen.getByRole('button', { name: '儲存庫存調整' }));
  await waitFor(() => expect(screen.getByRole('button', { name: '重試相同入帳' })).toBeEnabled());
  expect(guard.current?.()).toBe(false);
  expect(screen.getByLabelText('異動數量')).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: '重試相同入帳' }));
  await screen.findByText('已入帳，庫存與異動紀錄已保存。');
  expect(posts).toHaveLength(2); expect(posts[0]).toBe(posts[1]);
  await waitFor(() => expect(guard.current?.()).toBe(true));
});

it('keeps rejected quantities editable and honors cancellation of unsaved navigation', async () => {
  vi.spyOn(window, 'confirm').mockReturnValue(true);
  vi.stubGlobal('fetch', vi.fn(async (path: string, init?: RequestInit) => new Response(JSON.stringify(init?.method === 'POST' ? {} : path.includes('/resources/') ? { quantity: '1.000', unit: 'kg' } : { items: [], total: 0, offset: 0, limit: 30 }), { status: init?.method === 'POST' ? 409 : 200 })));
  const guard = { current: null as (() => boolean) | null };
  render(<InventoryPanel record={{ id: 'r', category: 'resources', code: 'MAT', title: '物料' }} expired={vi.fn()} leaveGuard={guard} />);
  await screen.findByLabelText('目前庫存');
  fireEvent.change(screen.getByLabelText('異動數量'), { target: { value: '-2' } });
  fireEvent.change(screen.getByLabelText('異動原因／收貨說明'), { target: { value: '盤點' } });
  fireEvent.click(screen.getByRole('button', { name: '儲存庫存調整' }));
  await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('未入帳'));
  expect(screen.getByLabelText('異動數量')).toHaveValue(-2);
  expect(screen.getByLabelText('異動數量')).toBeEnabled();
  vi.mocked(window.confirm).mockReturnValue(false);
  expect(guard.current?.()).toBe(false);
});


it('disables old inventory controls while another operations detail is loading', async () => {
  const row = { id: 'r1', category: 'resources', code: 'MAT1', title: '物料一', status: '正常', visibility: 'internal', fields: [], revision: 1, source: 'native', created_by: '主管', updated_by: '主管', created_at: '2026-10-11', updated_at: '2026-10-11' };
  let resolveDetail: (response: Response) => void = () => {};
  const slow = new Promise<Response>(resolve => { resolveDetail = resolve; });
  const fetcher = vi.fn(async (path: string) => {
    if (path.endsWith('/operations/r2')) return slow;
    const result = path.endsWith('/catalog') ? { can_manage: true, categories: [{ key: 'resources', label: '物料', fields: [] }] }
      : path.includes('/inventory/resources/') ? { quantity: '0.000', unit: 'kg' }
      : path.includes('/inventory/movements') ? { items: [], total: 0, offset: 0, limit: 30 }
      : path.includes('?') ? { items: [row, { ...row, id: 'r2', code: 'MAT2' }], total: 2, offset: 0, limit: 50 } : row;
    return new Response(JSON.stringify(result), { status: 200 });
  });
  vi.stubGlobal('fetch', fetcher);
  render(<OperationsManager expired={vi.fn()} leaveGuard={{ current: null }} preview={vi.fn()} />);
  fireEvent.click(await screen.findByRole('button', { name: /MAT1｜物料一/ }));
  await screen.findByLabelText('目前庫存');
  fireEvent.click(screen.getByRole('button', { name: /MAT2｜物料一/ }));
  expect(screen.getByLabelText('異動數量')).toBeDisabled();
  expect(screen.getByLabelText('異動原因／收貨說明')).toBeDisabled();
  expect(screen.getByRole('button', { name: '儲存庫存調整' })).toBeDisabled();
  resolveDetail(new Response(JSON.stringify({ ...row, id: 'r2', code: 'MAT2' }), { status: 200 }));
  await waitFor(() => expect(screen.getByLabelText('營運資料詳情')).toHaveTextContent('MAT2'));
  await waitFor(() => expect(screen.getByLabelText('異動數量')).toBeEnabled());
});
