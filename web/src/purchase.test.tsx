import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import PurchaseOrderPanel from './components/PurchaseOrderPanel';

const order = { id: 'po', category: 'orders', code: 'PO-1', title: '麵粉採購' };
const line = (over: object) => ({ id: 'l1', line_no: 1, resource_id: 'flour', resource_code: 'MAT', resource_title: '麵粉', unit: 'kg', ordered: '10.000', received: '4.000', remaining: '6.000', note: '', status: 'partial', ...over });
const purchase = (over: object = {}) => ({ order_id: 'po', revision: 2, status: 'partial', status_label: '部分收貨', closed_at: null, closed_by: null, close_reason: null, unlinked_receipts: 0,
  lines: [line({}), line({ id: 'l2', line_no: 2, resource_id: 'sugar', resource_code: 'SUGAR', resource_title: '糖', unit: '包', ordered: '2.000', received: '0.000', remaining: '2.000', status: 'pending' })], ...over });

function serve(state: { current: object }, posts: { path: string; body: unknown }[], reply: (path: string) => Response | null = () => null) {
  vi.stubGlobal('fetch', vi.fn(async (path: string, init?: RequestInit) => {
    if (init?.method === 'POST' || init?.method === 'PUT') {
      posts.push({ path, body: JSON.parse(String(init.body)) });
      const custom = reply(path);
      if (custom) return custom;
      return new Response(JSON.stringify(path.includes('/purchase') ? state.current : {}), { status: 200 });
    }
    const body = path.endsWith('/purchase') ? state.current : path.includes('/inventory/resources/') ? { quantity: '4.000', unit: 'kg' }
      : path.includes('/inventory/movements') ? { items: [], total: 0, offset: 0, limit: 30 } : { items: [{ id: 'oil', code: 'OIL', title: '油' }], total: 1, offset: 0 };
    return new Response(JSON.stringify(body), { status: 200 });
  }));
}

it('receives against a listed line, blocks over-receipt and refreshes progress', async () => {
  vi.spyOn(window, 'confirm').mockReturnValue(true);
  const state = { current: purchase() as object }; const posts: { path: string; body: unknown }[] = [];
  serve(state, posts);
  const onChanged = vi.fn();
  render(<PurchaseOrderPanel record={order} expired={vi.fn()} leaveGuard={{ current: null }} onChanged={onChanged} />);
  expect(await screen.findByLabelText('收貨狀態')).toHaveTextContent('部分收貨（0/2 列已收齊）');
  expect(screen.queryByLabelText('搜尋收貨物料')).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: 'MAT｜麵粉 · 未收 6.000 kg' }));
  expect(await screen.findByLabelText('本次可收')).toHaveTextContent('本次最多可收 6.000 kg');
  expect(screen.getByLabelText('庫存單位')).toBeDisabled();
  fireEvent.change(screen.getByLabelText('異動數量'), { target: { value: '6.001' } });
  fireEvent.change(screen.getByLabelText('異動原因／收貨說明'), { target: { value: '第二批' } });
  expect(screen.getByRole('alert')).toHaveTextContent('超過未收數量');
  expect(screen.getByRole('button', { name: '確認收貨入庫' })).toBeDisabled();
  fireEvent.change(screen.getByLabelText('異動數量'), { target: { value: '6' } });
  state.current = purchase({ status: 'partial', lines: [line({ received: '10.000', remaining: '0.000', status: 'received' }), (purchase() as { lines: object[] }).lines[1]] });
  await waitFor(() => expect(screen.getByRole('button', { name: '確認收貨入庫' })).toBeEnabled());
  fireEvent.click(screen.getByRole('button', { name: '確認收貨入庫' }));
  await screen.findByText('已入帳，庫存與異動紀錄已保存。');
  expect(posts[0]).toMatchObject({ path: '/api/operations/po/receipts', body: { resource_id: 'flour', quantity: '6', unit: 'kg', reason: '第二批' } });
  await waitFor(() => expect(screen.getByLabelText('收貨狀態')).toHaveTextContent('（1/2 列已收齊）'));
  expect(screen.getByRole('button', { name: 'MAT｜麵粉 · 已收齊' })).toBeDisabled();
  expect(onChanged).toHaveBeenCalled();
});

it('edits lines keeping received lines and shows a stale revision conflict', async () => {
  vi.spyOn(window, 'confirm').mockReturnValue(true);
  const state = { current: purchase() as object }; const posts: { path: string; body: unknown }[] = [];
  serve(state, posts, path => path.endsWith('/lines') && posts.length === 1 ? new Response(JSON.stringify({ detail: '採購明細已變更，請重新載入' }), { status: 409 }) : null);
  const guard = { current: null as (() => boolean) | null };
  render(<PurchaseOrderPanel record={order} expired={vi.fn()} leaveGuard={guard} />);
  fireEvent.click(await screen.findByRole('button', { name: '編輯採購明細' }));
  expect(screen.queryByLabelText('收貨與庫存')).toBeNull();
  expect(screen.getByRole('button', { name: '移除 MAT' })).toBeDisabled();
  expect(screen.getByLabelText('單位 MAT')).toBeDisabled();
  fireEvent.change(screen.getByLabelText('訂購數量 MAT'), { target: { value: '3.5' } });
  expect(screen.getByRole('button', { name: '儲存採購明細' })).toBeDisabled();
  fireEvent.change(screen.getByLabelText('訂購數量 MAT'), { target: { value: '12' } });
  fireEvent.click(screen.getByRole('button', { name: '移除 SUGAR' }));
  fireEvent.change(screen.getByLabelText('搜尋明細物料'), { target: { value: 'OIL' } });
  fireEvent.click(screen.getByRole('button', { name: '搜尋明細物料' }));
  fireEvent.click(await screen.findByRole('button', { name: '加入 OIL｜油' }));
  fireEvent.change(await screen.findByLabelText('訂購數量 OIL'), { target: { value: '1.25' } });
  expect(screen.getByLabelText('單位 OIL')).toHaveValue('kg');
  fireEvent.click(screen.getByRole('button', { name: '儲存採購明細' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('採購明細已變更，請重新載入');
  expect(screen.getByLabelText('訂購數量 OIL')).toHaveValue(1.25);
  vi.mocked(window.confirm).mockReturnValue(false);
  expect(guard.current?.()).toBe(false);
  fireEvent.click(screen.getByRole('button', { name: '儲存採購明細' }));
  await screen.findByText('已儲存採購明細（2 列）。');
  expect(posts[1].body).toEqual({ expected_revision: 2, lines: [
    { id: 'l1', resource_id: 'flour', quantity: '12', unit: 'kg', note: '' },
    { resource_id: 'oil', quantity: '1.25', unit: 'kg', note: '' }] });
});

it('locks receiving when closed and reopens with a reason', async () => {
  vi.spyOn(window, 'confirm').mockReturnValue(true);
  const state = { current: purchase({ status: 'closed', status_label: '已結案', revision: 3, closed_at: '2026-10-12T08:00:00+00:00', closed_by: '主管', close_reason: '供應商短交' }) as object };
  const posts: { path: string; body: unknown }[] = [];
  serve(state, posts);
  render(<PurchaseOrderPanel record={order} expired={vi.fn()} leaveGuard={{ current: null }} />);
  expect(await screen.findByText(/結案原因：供應商短交 · 主管/)).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: '編輯採購明細' })).toBeNull();
  const receiving = screen.getByLabelText('收貨與庫存');
  expect(within(receiving).getByText('採購單已結案，不能再收貨；如需補收請先重新開啟。')).toBeInTheDocument();
  expect(within(receiving).getByLabelText('異動數量')).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: '重新開啟採購單' }));
  expect(screen.getByRole('button', { name: '確認重新開啟' })).toBeDisabled();
  fireEvent.change(screen.getByLabelText('結案／重開原因'), { target: { value: '供應商補交' } });
  state.current = purchase({ revision: 4 });
  fireEvent.click(screen.getByRole('button', { name: '確認重新開啟' }));
  await screen.findByText('已重新開啟，可繼續收貨。');
  expect(posts[0]).toEqual({ path: '/api/operations/po/purchase/reopen', body: { expected_revision: 3, reason: '供應商補交' } });
  expect(screen.getByLabelText('異動數量')).toBeEnabled();
});

it('keeps free receipts for orders without lines and explains unlinked history', async () => {
  const state = { current: purchase({ status: 'no_lines', status_label: '未建立明細', revision: 0, unlinked_receipts: 2, lines: [] }) as object };
  serve(state, []);
  render(<PurchaseOrderPanel record={order} expired={vi.fn()} leaveGuard={{ current: null }} />);
  expect(await screen.findByText('此單有 2 筆建立明細前的收貨，未計入明細進度，可在下方異動紀錄查看。')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: '建立採購明細' })).toBeEnabled();
  expect(screen.getByLabelText('搜尋收貨物料')).toBeInTheDocument();
  expect(screen.getByText('此單尚未建立採購明細：可分次自由收貨，不檢查訂購數量，也不計入收貨進度。')).toBeInTheDocument();
});
