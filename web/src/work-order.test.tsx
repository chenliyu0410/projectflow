import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import WorkOrderPanel from './components/WorkOrderPanel';

const work = { id: 'wo', category: 'work', code: 'WO-1', title: '成貓罐試產' };
const production = (over: object = {}) => ({ work_id: 'wo', revision: 2, status: 'in_progress', status_label: '生產中', product: { id: 'fg', code: 'FG', title: '成貓罐' },
  unit: '罐', planned: '100.000', completed: '40.000', remaining: '60.000', note: '首批', closed_at: null, closed_by: null, close_reason: null, unlinked_completions: 0,
  issued: [{ resource_id: 'meat', code: 'MEAT', title: '雞肉', unit: 'kg', quantity: '12.500' }], ...over });

function serve(state: { current: object }, posts: { path: string; body: unknown }[], stockUnit: string | null = '罐') {
  vi.stubGlobal('fetch', vi.fn(async (path: string, init?: RequestInit) => {
    if (init?.method === 'POST' || init?.method === 'PUT') {
      posts.push({ path, body: JSON.parse(String(init.body)) });
      return new Response(JSON.stringify(path.includes('/production') ? state.current : {}), { status: 200 });
    }
    const body = path.endsWith('/production') ? state.current : path.includes('/inventory/resources/') ? { quantity: '40.000', unit: stockUnit }
      : path.includes('/inventory/movements') ? { items: [], total: 0, offset: 0, limit: 30 } : { items: [{ id: 'fg2', code: 'FG2', title: '成犬罐' }], total: 1, offset: 0 };
    return new Response(JSON.stringify(body), { status: 200 });
  }));
}

it('shows plan progress and issued totals, and completes only the planned product within the plan', async () => {
  vi.spyOn(window, 'confirm').mockReturnValue(true);
  const state = { current: production() as object }; const posts: { path: string; body: unknown }[] = [];
  serve(state, posts);
  const onChanged = vi.fn();
  render(<WorkOrderPanel record={work} expired={vi.fn()} leaveGuard={{ current: null }} onChanged={onChanged} />);
  expect(await screen.findByLabelText('生產狀態')).toHaveTextContent('生產中（已完工 40.000／計畫 100.000 罐）');
  expect(within(screen.getByLabelText('累計領料')).getByText('已領 12.500 kg')).toBeInTheDocument();
  expect(screen.getByLabelText('搜尋物料或成品')).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('工單操作'), { target: { value: 'completions' } });
  expect(screen.queryByLabelText('搜尋物料或成品')).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: 'FG｜成貓罐 · 尚可完工 60.000 罐' }));
  expect(await screen.findByLabelText('本次可完工')).toHaveTextContent('本次最多可完工 60.000 罐（計畫 100.000，已完工 40.000）');
  fireEvent.change(screen.getByLabelText('異動數量'), { target: { value: '61' } });
  fireEvent.change(screen.getByLabelText('異動原因／收貨說明'), { target: { value: '第二批' } });
  expect(screen.getByRole('alert')).toHaveTextContent('超過計畫剩餘產量');
  expect(screen.getByRole('button', { name: '確認完工入庫' })).toBeDisabled();
  fireEvent.change(screen.getByLabelText('異動數量'), { target: { value: '60' } });
  await waitFor(() => expect(screen.getByRole('button', { name: '確認完工入庫' })).toBeEnabled());
  state.current = production({ status: 'completed', status_label: '已達計畫產量', completed: '100.000', remaining: '0.000' });
  fireEvent.click(screen.getByRole('button', { name: '確認完工入庫' }));
  await screen.findByText('已入帳，庫存與異動紀錄已保存。');
  expect(posts[0]).toMatchObject({ path: '/api/operations/wo/completions', body: { resource_id: 'fg', quantity: '60', unit: '罐', reason: '第二批' } });
  await waitFor(() => expect(screen.getByLabelText('生產狀態')).toHaveTextContent('已達計畫產量'));
  expect(screen.getByRole('button', { name: 'FG｜成貓罐 · 已達計畫產量' })).toBeDisabled();
  expect(onChanged).toHaveBeenCalled();
});

it('sets a first plan with the product stock unit and protects a plan with completions', async () => {
  vi.spyOn(window, 'confirm').mockReturnValue(true);
  const state = { current: production({ status: 'no_plan', status_label: '未設定計畫', revision: 0, product: null, unit: null, planned: null, completed: null, remaining: null, note: '', issued: [] }) as object };
  const posts: { path: string; body: unknown }[] = [];
  serve(state, posts, '箱');
  const guard = { current: null as (() => boolean) | null };
  render(<WorkOrderPanel record={work} expired={vi.fn()} leaveGuard={guard} />);
  expect(await screen.findByText(/^尚未設定生產計畫。/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: '設定生產計畫' }));
  expect(screen.queryByLabelText('收貨與庫存')).toBeNull();
  expect(screen.getByRole('button', { name: '儲存生產計畫' })).toBeDisabled();
  fireEvent.change(screen.getByLabelText('搜尋成品'), { target: { value: 'FG2' } });
  fireEvent.click(screen.getByRole('button', { name: '搜尋成品' }));
  fireEvent.click(await screen.findByRole('button', { name: '選擇 FG2｜成犬罐' }));
  await waitFor(() => expect(screen.getByLabelText('成品單位')).toHaveValue('箱'));
  expect(screen.getByLabelText('成品單位')).toBeDisabled();
  fireEvent.change(screen.getByLabelText('計畫產量'), { target: { value: '24' } });
  vi.mocked(window.confirm).mockReturnValue(false);
  expect(guard.current?.()).toBe(false);
  vi.mocked(window.confirm).mockReturnValue(true);
  state.current = production({ revision: 1, status: 'planned', product: { id: 'fg2', code: 'FG2', title: '成犬罐' }, unit: '箱', planned: '24.000', completed: '0.000', remaining: '24.000', note: '' });
  fireEvent.click(screen.getByRole('button', { name: '儲存生產計畫' }));
  await screen.findByText('已儲存生產計畫。');
  expect(posts[0]).toEqual({ path: '/api/operations/wo/production/plan', body: { expected_revision: 0, product_id: 'fg2', quantity: '24', unit: '箱', note: '' } });
  state.current = production();
  fireEvent.click(screen.getByRole('button', { name: '重新載入生產進度' }));
  fireEvent.click(await screen.findByRole('button', { name: '編輯生產計畫' }));
  expect(screen.queryByLabelText('搜尋成品')).toBeNull();
  expect(screen.getByLabelText('成品單位')).toBeDisabled();
  fireEvent.change(screen.getByLabelText('計畫產量'), { target: { value: '39' } });
  expect(screen.getByRole('button', { name: '儲存生產計畫' })).toBeDisabled();
});

it('locks issues and completions when closed and reopens with a reason', async () => {
  vi.spyOn(window, 'confirm').mockReturnValue(true);
  const state = { current: production({ status: 'closed', status_label: '已結案', revision: 3, closed_at: '2026-10-12T08:00:00+00:00', closed_by: '主管', close_reason: '原料品質異常' }) as object };
  const posts: { path: string; body: unknown }[] = [];
  serve(state, posts);
  render(<WorkOrderPanel record={work} expired={vi.fn()} leaveGuard={{ current: null }} />);
  expect(await screen.findByText(/結案原因：原料品質異常 · 主管/)).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: '編輯生產計畫' })).toBeNull();
  const posting = screen.getByLabelText('收貨與庫存');
  expect(within(posting).getByText('工單已結案，不能再領料或完工；如需補登請先重新開啟。')).toBeInTheDocument();
  expect(within(posting).getByLabelText('工單操作')).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: '重新開啟工單' }));
  fireEvent.change(screen.getByLabelText('結案／重開原因'), { target: { value: '更換原料後續產' } });
  state.current = production({ revision: 4 });
  fireEvent.click(screen.getByRole('button', { name: '確認重新開啟' }));
  await screen.findByText('已重新開啟，可繼續生產。');
  expect(posts[0]).toEqual({ path: '/api/operations/wo/production/reopen', body: { expected_revision: 3, reason: '更換原料後續產' } });
  expect(screen.getByLabelText('工單操作')).toBeEnabled();
});

it('keeps free completions for work orders without a plan and explains unlinked history', async () => {
  serve({ current: production({ status: 'no_plan', status_label: '未設定計畫', revision: 0, product: null, unit: null, planned: null, completed: null, remaining: null, note: '', unlinked_completions: 2 }) }, []);
  render(<WorkOrderPanel record={work} expired={vi.fn()} leaveGuard={{ current: null }} />);
  expect(await screen.findByText('此工單有 2 筆設定計畫前的完工入庫，未計入計畫進度，可在下方異動紀錄查看。')).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('工單操作'), { target: { value: 'completions' } });
  expect(screen.getByLabelText('搜尋物料或成品')).toBeInTheDocument();
  expect(screen.getByText(/此工單尚未設定生產計畫：可分批自由入帳/)).toBeInTheDocument();
});
