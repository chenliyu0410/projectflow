import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import DocumentManager from './components/DocumentManager';

const v1 = { document_id: 'd', version: 1, filename: '成果.txt', size_bytes: 4, created_at: '2026-10-11T10:00:00Z', created_by: '小明', comment: '初稿', editable: true };
function mock(readonly = false, conflict = false) {
  let version = 1;
  const fetcher = vi.fn(async (url: string, init: RequestInit = {}) => {
    let data: unknown;
    // The AI document index is off here, as in deployments that never switch it on.
    if (url.includes('/ai/knowledge')) return new Response('{"detail":"正式文件索引未啟用"}', { status: 404 });
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

it('shows the AI state of each document and lets editors switch AI use off and on', async () => {
  let enabled = true;
  const calls: string[] = [];
  vi.stubGlobal('fetch', vi.fn(async (url: string, init: RequestInit = {}) => {
    const item = () => ({ document_id: 'd', ai_enabled: enabled, state: enabled ? 'indexed' : 'disabled', reason: '', indexed_version: enabled ? 1 : null });
    let data: unknown;
    if (url.includes('/ai/knowledge/d')) { calls.push(`${init.method} ${init.body}`); enabled = JSON.parse(String(init.body)).enabled; data = item(); }
    else if (url.includes('/ai/knowledge?')) { calls.push(url); data = { items: [item()], can_write: true, automatic: true }; }
    else if (url.endsWith('/documents')) data = { items: [v1], can_write: true };
    else if (url.endsWith('/versions')) data = { items: [v1], current_version: 1, can_write: true };
    else data = { content: '成果' };
    return new Response(JSON.stringify(data), { status: 200, headers: { 'Content-Type': 'application/json' } });
  }));
  render(<DocumentManager scopePath="/nodes/n" expired={vi.fn()} />);
  expect(await screen.findByText('AI：可查詢')).toBeInTheDocument();
  expect(calls[0]).toMatch(/\/ai\/knowledge\?node_id=n$/);
  fireEvent.click(screen.getByRole('button', { name: /成果.txt/ }));
  fireEvent.click(await screen.findByRole('button', { name: '停用 AI 引用' }));
  expect(await screen.findByText(/已停用：AI 助手不會再引用這份文件/)).toBeInTheDocument();
  expect(screen.getByText('AI：已停用')).toBeInTheDocument();
  expect(calls).toContain('PUT {"enabled":false}');
  fireEvent.click(screen.getByRole('button', { name: '恢復 AI 引用' }));
  expect(await screen.findByText('AI 助手可以再引用這份文件。')).toBeInTheDocument();
});

it('hides the AI switch from readers who cannot edit the document', async () => {
  vi.stubGlobal('fetch', vi.fn(async (url: string) => {
    const data = url.includes('/ai/knowledge') ? { items: [{ document_id: 'd', ai_enabled: true, state: 'pending', reason: '新增或已變更，等待索引更新', indexed_version: null }], can_write: false, automatic: true }
      : url.endsWith('/documents') ? { items: [v1], can_write: false } : url.endsWith('/versions') ? { items: [v1], current_version: 1, can_write: false } : { content: '成果' };
    return new Response(JSON.stringify(data), { status: 200, headers: { 'Content-Type': 'application/json' } });
  }));
  render(<DocumentManager scopePath="/nodes/n" expired={vi.fn()} />);
  expect(await screen.findByText('AI：排隊中')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: /成果.txt/ }));
  expect(await screen.findByText('AI 引用：排隊中')).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: '停用 AI 引用' })).toBeNull();
});

it('says an administrator must update the index when automatic updates are off, without polling', async () => {
  const fetcher = vi.fn(async (url: string) => {
    const data = url.includes('/ai/knowledge') ? { items: [{ document_id: 'd', ai_enabled: true, state: 'pending', reason: '新增或已變更，等待索引更新', indexed_version: null }], can_write: true, automatic: false }
      : url.endsWith('/documents') ? { items: [v1], can_write: true } : { content: '成果' };
    return new Response(JSON.stringify(data), { status: 200, headers: { 'Content-Type': 'application/json' } });
  });
  vi.stubGlobal('fetch', fetcher);
  vi.useFakeTimers({ shouldAdvanceTime: true });
  try {
    render(<DocumentManager scopePath="/nodes/n" expired={vi.fn()} />);
    expect(await screen.findByText('AI：待管理者更新')).toBeInTheDocument();
    const calls = fetcher.mock.calls.length;
    await vi.advanceTimersByTimeAsync(12000);
    expect(fetcher.mock.calls.length).toBe(calls);
  } finally { vi.useRealTimers(); }
});
