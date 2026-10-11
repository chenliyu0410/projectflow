import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import CopilotPanel from './components/CopilotPanel';
import { ai } from './ai';
import type { AIResult, AIStatus } from './ai';
vi.mock('./ai', () => ({ ai: { status: vi.fn(), ask: vi.fn(), document: vi.fn(), config: vi.fn(), save: vi.fn(), test: vi.fn() } }));
const status: AIStatus = { ready: true, as_of: '2026-10-11', company_name: '食品', model_enabled: false, model_name: '', can_configure: true, can_sql: true, projects: [{ project_id: 'P1', title: '展示案' }], queries: [{ query_id: 'q02', label: '各部門逾期未完成數' }], counts: { projects: 1, documents: 2 } };
const retrieved: AIResult = { kind: 'retrieval', engine: 'retrieval', answer: '檢索原文', warning: null, sources: [{ document_id: 'D1', title: '交付規範', project_id: 'P1', excerpt: '<script>文字</script> 截圖4張' }], analysis: null };
beforeEach(() => { vi.clearAllMocks(); vi.mocked(ai.status).mockResolvedValue(status); vi.mocked(ai.ask).mockResolvedValue(retrieved); vi.mocked(ai.document).mockResolvedValue({ title: '交付規範', text: '原文截圖4張' }); vi.mocked(ai.config).mockResolvedValue({ enabled: false, base_url: '', model: '' }); });

it('queries actual API, passes selected project and opens escaped original citation', async () => {
  render(<CopilotPanel scope="總覽" open close={vi.fn()} />);
  await screen.findByText(/1 個專案／2 份可見文件/);
  fireEvent.change(screen.getByLabelText('AI展示專案'), { target: { value: 'P1' } });
  fireEvent.click(screen.getByRole('button', { name: '現行交付需要幾張截圖？' }));
  await screen.findByText('檢索原文');
  expect(ai.ask).toHaveBeenCalledWith(expect.objectContaining({ mode: 'rag', project_id: 'P1' }), expect.any(AbortSignal));
  expect(screen.getByText('<script>文字</script> 截圖4張')).toBeInTheDocument();
  expect(document.querySelector('script')).toBeNull();
  fireEvent.click(screen.getByText('D1 · 交付規範'));
  fireEvent.click(screen.getByRole('button', { name: '開啟原文 D1' }));
  expect(await screen.findByLabelText('引用原文')).toHaveTextContent('原文截圖4張');
});

it('renders SQL results and executed query with explicit analysis selection', async () => {
  vi.mocked(ai.ask).mockResolvedValue({ ...retrieved, kind: 'sql', sources: [], analysis: { query_id: 'q02', label: '逾期', sql: 'SELECT COUNT(*) FROM tasks', parameters: { company_id: 'food' }, columns: ['department', 'overdue_count'], rows: [{ department: '研發', overdue_count: 3 }], truncated: false } });
  render(<CopilotPanel scope="總覽" open close={vi.fn()} />);
  await screen.findByText(/1 個專案／2 份可見文件/);
  fireEvent.change(screen.getByLabelText('查詢方式'), { target: { value: 'sql' } });
  fireEvent.change(screen.getByLabelText('分析種類'), { target: { value: 'q02' } });
  fireEvent.click(screen.getByRole('button', { name: '送出 AI 問題' }));
  expect(await screen.findByLabelText('查詢結果')).toHaveTextContent('研發');
  expect(screen.getByText('SELECT COUNT(*) FROM tasks')).toBeInTheDocument();
  expect(ai.ask).toHaveBeenCalledWith(expect.objectContaining({ query_id: 'q02', mode: 'sql' }), expect.any(AbortSignal));
});

it('aborts on scope change and ignores stale results', async () => {
  let resolve!: (r: AIResult) => void;
  vi.mocked(ai.ask).mockImplementation(() => new Promise(r => { resolve = r; }));
  const view = render(<CopilotPanel scope="總覽" open close={vi.fn()} />);
  await screen.findByText(/1 個專案／2 份可見文件/);
  fireEvent.click(screen.getByRole('button', { name: '現行交付需要幾張截圖？' }));
  const signal = vi.mocked(ai.ask).mock.calls[0][1]!;
  fireEvent.change(screen.getByLabelText('AI展示專案'), { target: { value: 'P1' } });
  expect(signal.aborted).toBe(true);
  await act(async () => resolve(retrieved));
  expect(screen.queryByText('檢索原文')).toBeNull();
  view.unmount();
});

it('shows query errors and keeps unsupported members out of SQL and model settings', async () => {
  vi.mocked(ai.status).mockResolvedValue({ ...status, can_configure: false, can_sql: false });
  vi.mocked(ai.ask).mockRejectedValue(new Error('登入已失效'));
  render(<CopilotPanel scope="總覽" open close={vi.fn()} />);
  await screen.findByText(/1 個專案／2 份可見文件/);
  expect(screen.getByRole('option', { name: 'Text-to-SQL 資料分析' })).toBeDisabled();
  expect(screen.queryByText('本地模型連線設定')).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: '現行交付需要幾張截圖？' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('登入已失效');
});

it('lets admin test and save local model settings', async () => {
  vi.mocked(ai.test).mockResolvedValue({ ok: true, models: ['test:1'], message: '連線成功' });
  vi.mocked(ai.save).mockResolvedValue({ ok: true });
  render(<CopilotPanel scope="總覽" open close={vi.fn()} />);
  fireEvent.click(await screen.findByText('本地模型連線設定'));
  await waitFor(() => expect(screen.getByLabelText('Ollama 位址')).not.toBeDisabled());
  fireEvent.change(screen.getByLabelText('Ollama 位址'), { target: { value: 'http://192.168.1.20:11434' } });
  fireEvent.change(screen.getByLabelText('聊天模型名稱'), { target: { value: 'test:1' } });
  fireEvent.click(screen.getByRole('button', { name: '測試連線' }));
  await screen.findByText('連線成功');
  fireEvent.click(screen.getByLabelText('啟用本地模型整理回答'));
  fireEvent.click(screen.getByRole('button', { name: '儲存設定' }));
  await screen.findByText('已儲存本公司模型設定');
  expect(ai.save).toHaveBeenCalledWith({ enabled: true, base_url: 'http://192.168.1.20:11434', model: 'test:1' }, expect.any(AbortSignal));
});

it('makes model-selected SQL scope reviewable before execution', async () => {
  vi.mocked(ai.ask).mockResolvedValue({ ...retrieved, kind: 'query_suggestion', analysis: null, sources: [], answer: '尚未執行', suggestion: { query_id: 'q02', label: '各部門逾期未完成數' } });
  render(<CopilotPanel scope="總覽" open close={vi.fn()} />);
  await screen.findByText(/1 個專案／2 份可見文件/);
  fireEvent.change(screen.getByLabelText('查詢方式'), { target: { value: 'sql' } });
  fireEvent.change(screen.getByLabelText('詢問 AI'), { target: { value: '想知道工作情況' } });
  fireEvent.click(screen.getByRole('button', { name: '送出 AI 問題' }));
  await screen.findByText('尚未執行');
  expect(screen.queryByLabelText('查詢結果')).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: '確認執行：各部門逾期未完成數' }));
  await waitFor(() => expect(ai.ask).toHaveBeenLastCalledWith(expect.objectContaining({ query_id: 'q02' }), expect.any(AbortSignal)));
});
