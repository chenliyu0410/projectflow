import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import FormalRagPanel from './components/FormalRagPanel';
import { rag, sourceDownloadPath } from './rag';
import CopilotPanel from './components/CopilotPanel';
vi.mock('./ai', () => ({ ai: { status: vi.fn().mockResolvedValue({ ready: false, projects: [], queries: [], counts: {}, can_configure: false }) } }));
vi.mock('./rag', async importOriginal => ({ ...await importOriginal<typeof import('./rag')>(), rag: { status: vi.fn(), ask: vi.fn(), source: vi.fn(), feedback: vi.fn(), index: vi.fn(), enable: vi.fn(), config: vi.fn(), save: vi.fn(), revalidate: vi.fn() } }));
const status = { project_id: null, projects: [{ project_id: 'p1', title: '甲專案' }, { project_id: 'p2', title: '乙專案' }], documents: [], counts: {}, can_configure: false, model: { enabled: true, name: 'local', embedding_model: 'embed' } };
const answer = { query_id: 'q1', project_id: 'p1', kind: 'answer', engine: 'model', answer: '需要簽核', blocks: [{ text: '需要簽核', source_ids: ['s1'] }], code: null, warning: null, citations: ['s1'], sources: [{ source_id: 's1', chunk_id: 's1', document_id: 'd1', version: 1, title: '規範', project_id: 'p1', project_title: '甲專案', node_id: null, excerpt: '指定人員簽核', locator: {} }], retrieval_mode: 'bm25', synthetic: false as const, source_mode: 'formal' as const };
beforeEach(() => { vi.clearAllMocks(); vi.mocked(rag.status).mockResolvedValue(status); vi.mocked(rag.ask).mockResolvedValue(answer); vi.mocked(rag.revalidate).mockResolvedValue({ queries: [{ query_id: 'q1', status: 'visible' }] }); });
afterEach(() => vi.useRealTimers());
function send(text = 'G2條件？') { fireEvent.change(screen.getByLabelText('正式文件問題'), { target: { value: text } }); fireEvent.click(screen.getByRole('button', { name: '送出正式文件問題' })); }
it('sends automatic history and keeps citations bound to their turn', async () => {
 render(<FormalRagPanel />); await screen.findByRole('option', { name: '甲專案' }); send(); await screen.findByText('需要簽核'); expect(rag.ask).toHaveBeenCalledWith({ scope: { kind: 'all_visible' }, question: 'G2條件？', history: [] }, expect.any(AbortSignal));
 vi.mocked(rag.ask).mockResolvedValue({ ...answer, query_id: 'q2', answer: '另一答案', blocks: [{ text: '另一答案', source_ids: [] }], sources: [] }); send('誰簽核？'); await screen.findByText('另一答案'); expect(rag.ask).toHaveBeenLastCalledWith(expect.objectContaining({ history: [{ question: 'G2條件？', query_id: 'q1' }] }), expect.any(AbortSignal));
 vi.mocked(rag.source).mockResolvedValue({ document_id: 'd1', version: 1, title: '規範', text: '原文', locator: {}, is_current: true, download_url: '' }); fireEvent.click(screen.getByRole('button', { name: '引用 1：規範' })); await screen.findByText('原文'); expect(rag.source).toHaveBeenCalledWith('q1', 's1', expect.any(AbortSignal));
});
it('waits with real elapsed time, stops and retries without duplicates or stale answers', async () => {
 vi.useFakeTimers(); let resolve!: (v: typeof answer) => void; vi.mocked(rag.ask).mockImplementation(() => new Promise(r => { resolve = r; })); render(<FormalRagPanel />); await act(async () => {}); send(); expect(screen.getByText('G2條件？')).toBeInTheDocument(); await act(async () => vi.advanceTimersByTime(31000)); expect(screen.getByText(/仍在處理/)).toBeInTheDocument();
 fireEvent.change(screen.getByLabelText('正式文件問題'), { target: { value: '下一題草稿' } }); fireEvent.click(screen.getByRole('button', { name: '停止等待' })); expect(vi.mocked(rag.ask).mock.calls[0][1]?.aborted).toBe(true); await act(async () => resolve(answer)); expect(screen.queryByText('需要簽核')).toBeNull(); expect(screen.getByLabelText('正式文件問題')).toHaveValue('下一題草稿'); fireEvent.click(screen.getByRole('button', { name: '重試這一題' })); expect(screen.getAllByText('G2條件？')).toHaveLength(1); await act(async () => vi.advanceTimersByTime(180000)); expect(screen.getByRole('alert')).toHaveTextContent('逾時');
});
it('guards IME and Shift+Enter and clears history on scope change', async () => {
 render(<FormalRagPanel />); await screen.findByRole('option', { name: '甲專案' }); const input = screen.getByLabelText('正式文件問題'); fireEvent.change(input, { target: { value: '測試' } }); fireEvent.compositionStart(input); fireEvent.keyDown(input, { key: 'Enter', keyCode: 229 }); expect(rag.ask).not.toHaveBeenCalled(); fireEvent.compositionEnd(input); fireEvent.keyDown(input, { key: 'Enter', shiftKey: true }); expect(rag.ask).not.toHaveBeenCalled(); fireEvent.keyDown(input, { key: 'Enter' }); await screen.findByText('需要簽核'); fireEvent.change(screen.getByLabelText('查詢範圍'), { target: { value: 'p2' } }); expect(screen.queryByText('需要簽核')).toBeNull(); send('新問題'); await screen.findByText('需要簽核'); expect(rag.ask).toHaveBeenLastCalledWith({ scope: { kind: 'project', project_id: 'p2' }, question: '新問題', history: [] }, expect.any(AbortSignal));
});
it('masks and removes revoked answers on reopen', async () => {
 const view = render(<FormalRagPanel open routeProjectId="p1" />); await screen.findByRole('option', { name: '甲專案' }); send(); await screen.findByText('需要簽核'); view.rerender(<FormalRagPanel open={false} routeProjectId="p1" />); vi.mocked(rag.revalidate).mockResolvedValue({ queries: [{ query_id: 'q1', status: 'unavailable' }] }); view.rerender(<FormalRagPanel open routeProjectId="p1" />); expect(screen.queryByText('需要簽核')).toBeNull(); await screen.findByText(/已移除受限回答/); expect(screen.queryByText('指定人員簽核')).toBeNull();
});
it('hides management and restricts model configuration', async () => {
 render(<FormalRagPanel />); await screen.findByRole('option', { name: '甲專案' }); expect(screen.queryByLabelText('正式文件清單')).toBeNull(); fireEvent.click(screen.getByRole('button', { name: '管理與設定' })); expect(screen.getByLabelText('正式文件清單')).toBeInTheDocument(); expect(screen.queryByText('正式文件本機模型設定')).toBeNull();
});

it('keeps the copilot mounted across close, and a new identity discards conversation', async () => {
 const view = render(<CopilotPanel key="company1:user1" scope="總覽" open close={vi.fn()} />); await screen.findByRole('option', { name: '甲專案' }); send(); await screen.findByText('需要簽核');
 view.rerender(<CopilotPanel key="company1:user1" scope="總覽" open={false} close={vi.fn()} />); view.rerender(<CopilotPanel key="company1:user1" scope="總覽" open close={vi.fn()} />); await screen.findByText('需要簽核'); expect(rag.revalidate).toHaveBeenCalledWith(['q1'], expect.any(AbortSignal));
 view.rerender(<CopilotPanel key="company2:user1" scope="總覽" open close={vi.fn()} />); expect(screen.queryByText('需要簽核')).toBeNull(); send('公司2問題'); await screen.findByText('需要簽核'); expect(rag.ask).toHaveBeenLastCalledWith(expect.objectContaining({ history: [] }), expect.any(AbortSignal));
 view.unmount(); render(<CopilotPanel key="company2:user2" scope="總覽" open close={vi.fn()} />); expect(screen.queryByText('需要簽核')).toBeNull();
});
it('preserves manual scope at the same project and resets when route project changes', async () => {
 const view = render(<FormalRagPanel routeProjectId="p1" />); await screen.findByRole('option', { name: '甲專案' }); fireEvent.change(screen.getByLabelText('查詢範圍'), { target: { value: '' } }); send(); await screen.findByText('需要簽核');
 view.rerender(<FormalRagPanel routeProjectId="p1" />); expect(screen.getByLabelText('查詢範圍')).toHaveValue(''); expect(screen.getByText('需要簽核')).toBeInTheDocument(); view.rerender(<FormalRagPanel routeProjectId="p2" />); expect(screen.getByLabelText('查詢範圍')).toHaveValue('p2'); expect(screen.queryByText('需要簽核')).toBeNull();
});
it('bounds history by six turns and 6000 characters without deleting displayed turns', async () => {
 render(<FormalRagPanel />); await screen.findByRole('option', { name: '甲專案' }); for (let i = 0; i < 8; i++) { send(String(i) + '問'.repeat(999)); await act(async () => {}); } const body = vi.mocked(rag.ask).mock.calls[7][0]; expect('history' in body && body.history).toHaveLength(6); expect(screen.getAllByText('需要簽核')).toHaveLength(8);
});
it('maps downloads to the API and rejects foreign or traversing paths', () => {
 expect(sourceDownloadPath('/documents/doc-1/versions/3/download')).toBe('/api/documents/doc-1/versions/3/download'); expect(() => sourceDownloadPath('https://bad.test/documents/d/versions/1/download')).toThrow(); expect(() => sourceDownloadPath('/documents/../versions/1/download')).toThrow();
});
it('keeps answers hidden when reauthorization fails and recovers only after a successful check', async () => {
 const view = render(<FormalRagPanel open />); await screen.findByRole('option', { name: '甲專案' }); send(); await screen.findByText('需要簽核'); view.rerender(<FormalRagPanel open={false} />); vi.mocked(rag.revalidate).mockRejectedValueOnce(new Error('offline')); view.rerender(<FormalRagPanel open />); await screen.findByRole('alert'); expect(screen.queryByText('需要簽核')).toBeNull(); fireEvent.click(screen.getByRole('button', { name: '重新確認權限' })); await screen.findByText('需要簽核');
});
it.each(['generation_timeout', 'generation_unavailable'])('retries a completed %s degradation with the same question and scope', async code => {
 vi.mocked(rag.ask).mockResolvedValueOnce({ ...answer, code, engine: 'retrieval' });
 render(<FormalRagPanel routeProjectId="p1" />); await screen.findByRole('option', { name: '甲專案' }); send(); await screen.findByText('需要簽核');
 expect(screen.getByText(/未產生回答/)).toBeInTheDocument();
 fireEvent.change(screen.getByLabelText('正式文件問題'), { target: { value: '下一題草稿' } });
 fireEvent.click(screen.getByRole('button', { name: '重試這一題' })); await act(async () => {});
 expect(rag.ask).toHaveBeenLastCalledWith({ scope: { kind: 'project', project_id: 'p1' }, question: 'G2條件？', history: [] }, expect.any(AbortSignal));
 expect(screen.getAllByText('G2條件？')).toHaveLength(1); expect(screen.getByLabelText('正式文件問題')).toHaveValue('下一題草稿');
 expect(screen.queryByRole('button', { name: '重試這一題' })).toBeNull();
});
