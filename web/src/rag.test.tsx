import { act, fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import FormalRagPanel from './components/FormalRagPanel';
import { rag } from './rag';
import type { RagResult, RagStatus } from './rag';
vi.mock('./rag', async importOriginal => ({ ...await importOriginal<typeof import('./rag')>(), rag: { status: vi.fn(), ask: vi.fn(), source: vi.fn(), feedback: vi.fn(), index: vi.fn(), enable: vi.fn(), config: vi.fn(), save: vi.fn(), revalidate: vi.fn() } }));
const status: RagStatus = { project_id: 'uuid1', projects: [{ project_id: 'uuid1', title: '正式甲' }, { project_id: 'uuid2', title: '正式乙' }], can_configure: false, model: { enabled: false, name: '', embedding_model: '' }, counts: {}, documents: [] };
const answer: RagResult = { query_id: 'query1', project_id: 'uuid1', kind: 'retrieval', engine: 'retrieval', answer: '正式回答', warning: '模型未啟用，僅檢索', citations: ['chunk1'], sources: [{ source_id: 'chunk1', chunk_id: 'chunk1', document_id: 'doc1', version: 3, title: '正式規範', project_id: 'uuid1', node_id: 'node1', excerpt: '<script>原文</script>', locator: { page: 2 } }], retrieval_mode: 'bm25', synthetic: false, source_mode: 'formal' };
beforeEach(() => { vi.clearAllMocks(); vi.mocked(rag.status).mockResolvedValue(status); vi.mocked(rag.ask).mockResolvedValue(answer); vi.mocked(rag.feedback).mockResolvedValue({ ok: true }); vi.mocked(rag.source).mockResolvedValue({ document_id: 'doc1', title: '正式規範', version: 3, text: '現行來源文字', locator: { page: 2 }, is_current: true, download_url: '' }); });
async function ask() { await screen.findByRole('option', { name: '正式甲' }); fireEvent.change(screen.getByLabelText('查詢範圍'), { target: { value: 'uuid1' } });  fireEvent.change(screen.getByLabelText('正式文件問題'), { target: { value: '交付要求？' } }); fireEvent.click(screen.getByRole('button', { name: '送出正式文件問題' })); }
it('uses formal IDs, escaped versioned references, source viewer and feedback', async () => {
 render(<FormalRagPanel />); await ask(); await screen.findByText('正式回答'); expect(rag.ask).toHaveBeenCalledWith({ scope: { kind: 'project', project_id: 'uuid1' }, question: '交付要求？', history: [] }, expect.any(AbortSignal));
 expect(screen.getByText(/正式規範・版本 3・第 2 頁/)).toBeInTheDocument(); expect(screen.getByText('<script>原文</script>')).toBeInTheDocument(); expect(document.querySelector('script')).toBeNull();
 fireEvent.click(screen.getByText(/正式規範・版本 3・第 2 頁/)); fireEvent.click(screen.getByRole('button', { name: '查看原文' })); await screen.findByText('現行來源文字'); expect(rag.source).toHaveBeenCalledWith('query1', 'chunk1', expect.any(AbortSignal));
 fireEvent.click(screen.getByRole('button', { name: '有幫助' })); await screen.findByText('已記錄：有幫助'); expect(rag.feedback).toHaveBeenCalledWith('query1', 'helpful', expect.any(AbortSignal));
});
it('aborts on project change and ignores stale answers', async () => {
 let resolve!: (r: RagResult) => void; vi.mocked(rag.ask).mockImplementation(() => new Promise(r => { resolve = r; })); render(<FormalRagPanel />); await ask(); const signal = vi.mocked(rag.ask).mock.calls[0][1]!;
 fireEvent.change(screen.getByLabelText('查詢範圍'), { target: { value: 'uuid2' } }); expect(signal.aborted).toBe(true); await act(async () => resolve(answer)); expect(screen.queryByText('正式回答')).toBeNull(); expect(rag.status).toHaveBeenLastCalledWith({ kind: 'project', project_id: 'uuid2' }, expect.any(AbortSignal));
});
it('shows failures and explicitly cancels', async () => {
 vi.mocked(rag.ask).mockRejectedValue(new Error('來源已變更')); render(<FormalRagPanel />); await ask(); expect(await screen.findByRole('alert')).toHaveTextContent('來源已變更'); vi.mocked(rag.ask).mockImplementation(() => new Promise(() => {})); fireEvent.click(screen.getByRole('button', { name: '重試這一題' })); fireEvent.click(screen.getByRole('button', { name: '停止等待' })); expect(vi.mocked(rag.ask).mock.calls[1][1]!.aborted).toBe(true);
});
it('routes formal requests exclusively through authenticated /rag endpoints', async () => {
 const actual = await vi.importActual<typeof import('./rag')>('./rag');
 const fetchMock = vi.fn().mockImplementation(() => Promise.resolve({ ok: true, status: 200, json: async () => ({ ok: true }) })); vi.stubGlobal('fetch', fetchMock);
 try {
  await actual.rag.status('uuid/1'); await actual.rag.ask({ project_id: 'uuid1', question: '問題' }); await actual.rag.source('query/1', 'chunk/1'); await actual.rag.feedback('query/1', 'unhelpful'); await actual.rag.index('doc/1'); await actual.rag.enable('doc/1', false); await actual.rag.config(); await actual.rag.save({ enabled: false, base_url: 'http://127.0.0.1:11434', model: 'chat', embedding_model: 'embed' });
  expect(fetchMock.mock.calls.map(call => call[0])).toEqual(['/api/rag/status?project_id=uuid%2F1', '/api/rag/ask', '/api/rag/queries/query%2F1/sources/chunk%2F1', '/api/rag/queries/query%2F1/feedback', '/api/rag/documents/doc%2F1/index', '/api/rag/documents/doc%2F1/enabled', '/api/rag/model', '/api/rag/model']);
  expect(fetchMock.mock.calls.every(call => call[1].credentials === 'include')).toBe(true);
 } finally { vi.unstubAllGlobals(); }
});
