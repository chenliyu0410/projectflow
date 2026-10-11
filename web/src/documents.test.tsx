import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import DocumentManager from './components/DocumentManager';

const v1 = { document_id: 'd', version: 1, filename: '成果.txt', size_bytes: 4, created_at: '2026-10-11T10:00:00Z', created_by: '小明', comment: '初稿', editable: true };
function mock(readonly = false, conflict = false) {
  let version = 1;
  const fetcher = vi.fn(async (url: string, init: RequestInit = {}) => {
    let data: unknown;
    if (init?.method === 'POST') {
      if (conflict) return new Response('{}', { status: 409 });
      version = 2; data = { ...v1, version: 2 };
    } else if (url.endsWith('/documents')) data = { items: [{ ...v1, version }], can_write: !readonly };
    else if (url.endsWith('/versions')) data = { items: version === 1 ? [v1] : [{ ...v1, version: 2 }, v1], current_version: version, can_write: !readonly };
    else data = { content: url.includes('/1/') ? '<script>原稿</script>' : '新版' };
    return new Response(JSON.stringify(data), { status: 200, headers: { 'Content-Type': 'application/json' } });
  });
  vi.stubGlobal('fetch', fetcher); return fetcher;
}
it('saves edits as a new version and shows immutable historical content safely', async () => {
  const fetcher = mock();
  render(<DocumentManager scopePath="/nodes/n" expired={vi.fn()} />);
  fireEvent.click(await screen.findByRole('button', { name: /成果.txt/ }));
  fireEvent.click(await screen.findByRole('button', { name: '編輯文字' }));
  fireEvent.change(screen.getByLabelText('編輯文件內容'), { target: { value: '新版' } });
  fireEvent.click(screen.getByRole('button', { name: '儲存新版本' }));
  await waitFor(() => expect(screen.getByRole('link', { name: '下載 v2' })).toBeInTheDocument());
  expect(fetcher.mock.calls.find(([, init]) => init?.method === 'POST')?.[1]?.body).toBe(JSON.stringify({ expected_version: 1, content: '新版', comment: '' }));
  fireEvent.change(screen.getByLabelText('版本紀錄'), { target: { value: '1' } });
  expect(await screen.findByText('<script>原稿</script>')).toBeInTheDocument();
  expect(document.querySelector('script')).toBeNull();
  expect(screen.queryByRole('button', { name: '編輯文字' })).toBeNull();
});
it('preserves a draft on version conflict', async () => {
  mock(false, true); render(<DocumentManager scopePath="/nodes/n" expired={vi.fn()} />);
  fireEvent.click(await screen.findByRole('button', { name: /成果.txt/ }));
  fireEvent.click(await screen.findByRole('button', { name: '編輯文字' }));
  fireEvent.change(screen.getByLabelText('編輯文件內容'), { target: { value: '我的未存內容' } });
  fireEvent.click(screen.getByRole('button', { name: '儲存新版本' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('文件已有新版本');
  expect(screen.getByLabelText('編輯文件內容')).toHaveValue('我的未存內容');
});
it('offers only viewing and downloads to readonly users', async () => {
  mock(true); render(<DocumentManager scopePath="/projects/p" expired={vi.fn()} />);
  fireEvent.click(await screen.findByRole('button', { name: /成果.txt/ }));
  expect(await screen.findByRole('link', { name: '下載 v1' })).toHaveAttribute('href', '/api/documents/d/versions/1/download');
  expect(screen.queryByLabelText('上傳新文件')).toBeNull();
  expect(screen.queryByRole('button', { name: '編輯文字' })).toBeNull();
});
it('supports retry after a failed list request and expires invalid sessions', async () => {
  const expired = vi.fn(); const fetcher = vi.fn().mockResolvedValueOnce(new Response('{}', { status: 503 })).mockResolvedValueOnce(new Response('{}', { status: 401 }));
  vi.stubGlobal('fetch', fetcher); render(<DocumentManager scopePath="/nodes/n" expired={expired} />);
  expect(await screen.findByRole('alert')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: '重新載入文件' }));
  await waitFor(() => expect(expired).toHaveBeenCalledOnce());
});
