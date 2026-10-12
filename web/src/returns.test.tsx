import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import InventoryPanel from './components/InventoryPanel';
import PurchaseOrderPanel from './components/PurchaseOrderPanel';
import WorkOrderPanel from './components/WorkOrderPanel';

const order = { id: 'po', category: 'orders', code: 'PO-1', title: '麵粉採購' };
const line = (over: object) => ({ id: 'l1', line_no: 1, resource_id: 'flour', resource_code: 'MAT', resource_title: '麵粉', unit: 'kg', ordered: '10.000', received: '10.000', remaining: '0.000', returned: '0.000', locked: true, note: '', status: 'received', ...over });
const purchase = (over: object = {}) => ({ order_id: 'po', revision: 2, status: 'partial', status_label: '部分收貨', closed_at: null, closed_by: null, close_reason: null, unlinked_receipts: 0,
  lines: [line({}), line({ id: 'l2', line_no: 2, resource_id: 'sugar', resource_code: 'SUGAR', resource_title: '糖', unit: '包', ordered: '2.000', received: '0.000', remaining: '2.000', locked: false, status: 'pending' })], ...over });
const movement = (over: object) => ({ id: 'm1', kind: 'adjustment', resource_label: 'MAT｜麵粉', order_label: null, work_label: null, quantity: '5.000', unit: 'kg', before: '0.000', after: '5.000',
  reason: '期初', actor_name: '主管', created_at: '2026-10-12T08:00:00+00:00', reversed_by: null, reversed_kind: null, ...over });

type Post = { path: string; body: Record<string, unknown> };
function serve(state: { current: object }, posts: Post[], history: object[] = [], reply: (path: string, count: number) => Response | Error | null = () => null) {
  vi.stubGlobal('fetch', vi.fn(async (path: string, init?: RequestInit) => {
    if (init?.method === 'POST' || init?.method === 'PUT') {
      posts.push({ path, body: JSON.parse(String(init.body)) });
      const custom = reply(path, posts.length);
      if (custom instanceof Error) throw custom;
      if (custom) return custom;
      return new Response(JSON.stringify(path.includes('/purchase') || path.includes('/production') ? state.current : {}), { status: 200 });
    }
    const body = path.endsWith('/purchase') || path.endsWith('/production') ? state.current : path.includes('/inventory/resources/') ? { quantity: '10.000', unit: 'kg' }
      : path.includes('/inventory/movements') ? { items: history, total: history.length, offset: 0, limit: 30 } : { items: [], total: 0, offset: 0 };
    return new Response(JSON.stringify(body), { status: 200 });
  }));
}

it('returns a received purchase line within what was received and shows the returned quantity', async () => {
  vi.spyOn(window, 'confirm').mockReturnValue(true);
  const state = { current: purchase({ status: 'received', status_label: '已收齊' }) as object }; const posts: Post[] = [];
  serve(state, posts);
  render(<PurchaseOrderPanel record={order} expired={vi.fn()} leaveGuard={{ current: null }} />);
  await screen.findByLabelText('收貨狀態');
  fireEvent.change(screen.getByLabelText('採購操作'), { target: { value: 'returns' } });
  expect(screen.getByRole('button', { name: 'SUGAR｜糖 · 尚無可退數量' })).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'MAT｜麵粉 · 可退 10.000 kg' }));
  expect(await screen.findByLabelText('本次可退')).toHaveTextContent('本次最多可退 10.000 kg（已收 10.000，已退 0.000）');
  fireEvent.change(screen.getByLabelText('異動數量'), { target: { value: '10.001' } });
  fireEvent.change(screen.getByLabelText('異動原因／收貨說明'), { target: { value: '受潮退回' } });
  expect(screen.getByRole('alert')).toHaveTextContent('超過已收數量，不能退貨。');
  expect(screen.getByRole('button', { name: '確認採購退貨' })).toBeDisabled();
  fireEvent.change(screen.getByLabelText('異動數量'), { target: { value: '3' } });
  state.current = purchase({ lines: [line({ received: '7.000', remaining: '3.000', returned: '3.000', status: 'partial' }), (purchase() as { lines: object[] }).lines[1]] });
  fireEvent.click(screen.getByRole('button', { name: '確認採購退貨' }));
  await screen.findByText('已入帳，庫存與異動紀錄已保存。');
  expect(posts[0]).toMatchObject({ path: '/api/operations/po/returns', body: { resource_id: 'flour', quantity: '3', unit: 'kg', reason: '受潮退回' } });
  await waitFor(() => expect(screen.getByText('訂購 10.000 kg · 已收 7.000 · 未收 3.000 · 已退 3.000')).toBeInTheDocument());
  // A line with ledger history stays locked even if returns bring it back to zero.
  state.current = purchase({ lines: [line({ received: '0.000', remaining: '10.000', returned: '10.000', status: 'pending' })] });
  fireEvent.click(screen.getByRole('button', { name: '重新載入收貨進度' }));
  fireEvent.click(await screen.findByRole('button', { name: '編輯採購明細' }));
  expect(screen.getByRole('button', { name: '移除 MAT' })).toBeDisabled();
});

it('returns issued material to stock from a work order', async () => {
  vi.spyOn(window, 'confirm').mockReturnValue(true);
  const production = (issued: object[]) => ({ work_id: 'wo', revision: 2, status: 'in_progress', status_label: '生產中', product: null, unit: null, planned: null, completed: null, remaining: null,
    note: '', closed_at: null, closed_by: null, close_reason: null, unlinked_completions: 0, issued });
  const meat = { resource_id: 'meat', code: 'MEAT', title: '雞肉', unit: 'kg', quantity: '12.500', returned: '0.000' };
  const state = { current: production([meat, { ...meat, resource_id: 'salt', code: 'SALT', title: '鹽', quantity: '0.000', returned: '1.000' }]) as object }; const posts: Post[] = [];
  serve(state, posts);
  render(<WorkOrderPanel record={{ id: 'wo', category: 'work', code: 'WO-1', title: '試產' }} expired={vi.fn()} leaveGuard={{ current: null }} />);
  await screen.findByLabelText('生產狀態');
  expect(within(screen.getByLabelText('累計領料')).getByText('已退料 1.000 kg')).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('工單操作'), { target: { value: 'issue-returns' } });
  expect(screen.queryByLabelText('搜尋物料或成品')).toBeNull();
  expect(screen.getByRole('button', { name: 'SALT｜鹽 · 已全數退回' })).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'MEAT｜雞肉 · 可退 12.500 kg' }));
  expect(await screen.findByLabelText('本次可退')).toHaveTextContent('本次最多可退 12.500 kg（本工單淨領料）');
  fireEvent.change(screen.getByLabelText('異動數量'), { target: { value: '2' } });
  fireEvent.change(screen.getByLabelText('異動原因／收貨說明'), { target: { value: '剩料退回' } });
  state.current = production([{ ...meat, quantity: '10.500', returned: '2.000' }]);
  fireEvent.click(screen.getByRole('button', { name: '確認工單退料' }));
  await screen.findByText('已入帳，庫存與異動紀錄已保存。');
  expect(posts[0]).toMatchObject({ path: '/api/operations/wo/issue-returns', body: { resource_id: 'meat', quantity: '2', unit: 'kg', reason: '剩料退回' } });
  await waitFor(() => expect(within(screen.getByLabelText('累計領料')).getByText('已領 10.500 kg')).toBeInTheDocument());
});

it('reverses one entry with a reason and retries an uncertain reversal with the same request', async () => {
  vi.spyOn(window, 'confirm').mockReturnValue(true);
  vi.spyOn(window, 'alert').mockImplementation(() => {});
  const posts: Post[] = [];
  const history = [movement({}), movement({ id: 'm2', kind: 'receipt', order_label: 'PO｜採購', reversed_by: 'm3' }), movement({ id: 'm3', kind: 'reversal', reversed_kind: 'receipt', quantity: '-5.000', reason: '錯收' })];
  serve({ current: {} }, posts, history, (_, count) => count === 1 ? new TypeError('network interrupted') : null);
  const guard = { current: null as (() => boolean) | null };
  render(<InventoryPanel record={{ id: 'r', category: 'resources', code: 'MAT', title: '麵粉' }} expired={vi.fn()} leaveGuard={guard} />);
  const items = await screen.findAllByRole('listitem');
  expect(items).toHaveLength(3);
  expect(within(items[1]).getByText('已沖銷')).toBeInTheDocument();
  expect(within(items[1]).queryByRole('button', { name: '沖銷此筆' })).toBeNull();
  expect(within(items[2]).getByText('沖銷（採購收貨） · MAT｜麵粉')).toBeInTheDocument();
  expect(within(items[2]).queryByRole('button', { name: '沖銷此筆' })).toBeNull();
  fireEvent.click(within(items[0]).getByRole('button', { name: '沖銷此筆' }));
  expect(screen.getByRole('button', { name: '確認沖銷' })).toBeDisabled();
  fireEvent.change(screen.getByLabelText('沖銷原因'), { target: { value: '期初數量填錯' } });
  fireEvent.click(screen.getByRole('button', { name: '確認沖銷' }));
  await waitFor(() => expect(screen.getByRole('button', { name: '重試相同沖銷' })).toBeEnabled());
  expect(screen.getByLabelText('沖銷原因')).toBeDisabled();
  expect(guard.current?.()).toBe(false);
  fireEvent.click(screen.getByRole('button', { name: '重試相同沖銷' }));
  await screen.findByText('已沖銷，庫存與相關進度已回復；原紀錄保留。');
  expect(posts.map(post => post.path)).toEqual(['/api/inventory/movements/m1/reversal', '/api/inventory/movements/m1/reversal']);
  expect(posts[0].body).toEqual(posts[1].body);
  expect(posts[0].body.reason).toBe('期初數量填錯');
  await waitFor(() => expect(guard.current?.()).toBe(true));
});

it('keeps a rejected reversal editable and disables reversals on a closed order', async () => {
  vi.spyOn(window, 'confirm').mockReturnValue(true);
  const posts: Post[] = [];
  serve({ current: {} }, posts, [movement({})], () => new Response(JSON.stringify({ detail: '庫存不足，無法沖銷' }), { status: 409 }));
  const { unmount } = render(<InventoryPanel record={{ id: 'r', category: 'resources', code: 'MAT', title: '麵粉' }} expired={vi.fn()} leaveGuard={{ current: null }} />);
  fireEvent.click(await screen.findByRole('button', { name: '沖銷此筆' }));
  fireEvent.change(screen.getByLabelText('沖銷原因'), { target: { value: '錯帳' } });
  fireEvent.click(screen.getByRole('button', { name: '確認沖銷' }));
  expect(await screen.findByText('未沖銷：庫存不足，無法沖銷。')).toHaveAttribute('role', 'alert');
  expect(screen.getByLabelText('沖銷原因')).toBeEnabled();
  expect(screen.getByRole('button', { name: '確認沖銷' })).toBeEnabled();
  unmount();
  serve({ current: purchase({ status: 'closed', status_label: '已結案', closed_at: '2026-10-12T08:00:00+00:00', closed_by: '主管', close_reason: '短交' }) }, [], [movement({ kind: 'receipt', order_label: 'PO｜採購' })]);
  render(<PurchaseOrderPanel record={order} expired={vi.fn()} leaveGuard={{ current: null }} />);
  expect(await screen.findByRole('button', { name: '沖銷此筆' })).toBeDisabled();
  expect(screen.getByLabelText('採購操作')).toBeDisabled();
});
