import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import OperationsManager from './components/OperationsManager';

const row = { id: 'r', category: 'partners', code: 'S-1', title: '供應商一', status: '評估中', visibility: 'internal', fields: [{ label: '聯絡', value: '<script>hello</script>' }], revision: 1, source: 'native', created_at: '2026-10-11T10:00:00Z', updated_at: '2026-10-11T10:00:00Z', created_by: '主管', updated_by: '主管' };
function mock(canManage = true, conflict = false) {
  let record = { ...row };
  const fetcher = vi.fn(async (path: string, init?: RequestInit) => {
    let result: unknown;
    if (init?.method === 'POST' || init?.method === 'PUT') {
      if (conflict) return new Response('{}', { status: 409 });
      record = { ...record, ...JSON.parse(String(init.body)), revision: record.revision + 1 };
      result = record;
    } else if (path.endsWith('/catalog')) result = { can_manage: canManage, categories: [{ key: 'partners', label: '供應商', fields: ['聯絡'] }, { key: 'orders', label: '採購', fields: ['數量'] }] };
    else if (path.includes('?')) result = { items: [record], total: 1, offset: 0, limit: 50 };
    else result = record;
    return new Response(JSON.stringify(result), { status: 200 });
  });
  vi.stubGlobal('fetch', fetcher); return fetcher;
}
it('creates and edits a durable record through API with expected revision', async () => {
  const fetcher = mock(); render(<OperationsManager expired={vi.fn()} leaveGuard={{ current: null }} preview={vi.fn()} />);
  fireEvent.click(await screen.findByRole('button', { name: '新增供應商' }));
  fireEvent.change(screen.getByLabelText('代碼'), { target: { value: 'NEW-1' } });
  fireEvent.change(screen.getByLabelText('名稱'), { target: { value: '新供應商' } });
  fireEvent.click(screen.getByRole('button', { name: '儲存營運資料' }));
  expect(await screen.findByLabelText('營運資料詳情')).toHaveTextContent('新供應商');
  fireEvent.click(screen.getByRole('button', { name: '編輯營運資料' }));
  fireEvent.change(screen.getByLabelText('狀態'), { target: { value: '合格' } });
  fireEvent.click(screen.getByRole('button', { name: '儲存營運資料' }));
  await waitFor(() => expect(screen.getByLabelText('營運資料詳情')).toHaveTextContent('合格'));
  const write = fetcher.mock.calls.find(([, init]) => init?.method === 'PUT');
  expect(JSON.parse(String(write?.[1]?.body))).toMatchObject({ expected_revision: 2, status: '合格' });
});
it('keeps draft on conflict and declined category or parent navigation', async () => {
  mock(true, true); const leaveGuard: { current: (() => boolean) | null } = { current: null };
  const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false);
  render(<OperationsManager expired={vi.fn()} leaveGuard={leaveGuard} preview={vi.fn()} />);
  fireEvent.click(await screen.findByRole('button', { name: /S-1/ }));
  fireEvent.click(await screen.findByRole('button', { name: '編輯營運資料' }));
  fireEvent.change(screen.getByLabelText('名稱'), { target: { value: '未存草稿' } });
  fireEvent.click(screen.getByRole('button', { name: '儲存營運資料' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('輸入已保留');
  fireEvent.click(screen.getByRole('button', { name: '採購' }));
  expect(screen.getByLabelText('名稱')).toHaveValue('未存草稿');
  expect(leaveGuard.current?.()).toBe(false);
  confirm.mockRestore();
});
it('hides write controls for readonly users and escapes stored text', async () => {
  mock(false); render(<OperationsManager expired={vi.fn()} leaveGuard={{ current: null }} preview={vi.fn()} />);
  fireEvent.click(await screen.findByRole('button', { name: /S-1/ }));
  expect(await screen.findByText('<script>hello</script>')).toBeInTheDocument();
  expect(document.querySelector('script')).toBeNull();
  expect(screen.queryByRole('button', { name: '編輯營運資料' })).toBeNull();
  expect(screen.queryByRole('button', { name: '新增供應商' })).toBeNull();
});
it('can retry initial failure and handles expired login', async () => {
  const expired = vi.fn(); vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(new Response('{}', { status: 503 })).mockResolvedValueOnce(new Response('{}', { status: 401 })));
  render(<OperationsManager expired={expired} leaveGuard={{ current: null }} preview={vi.fn()} />);
  expect(await screen.findByRole('alert')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: '重新載入營運資料' }));
  await waitFor(() => expect(expired).toHaveBeenCalledOnce());
});
