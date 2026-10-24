import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import CopilotPanel from './components/CopilotPanel';
import { ai } from './ai';
import type { AIResult, AIStatus } from './ai';
vi.mock('./ai', () => ({ ai: { status: vi.fn(), ask: vi.fn(), preview: vi.fn(), refreshIndex: vi.fn(), document: vi.fn(), config: vi.fn(), save: vi.fn(), test: vi.fn() } }));
const status: AIStatus = { ready: true, as_of: '2026-10-11', company_name: '食品', model_enabled: false, model_name: '', can_configure: true, can_sql: true, projects: [{ project_id: 'P1', title: '展示案' }], queries: [{ query_id: 'q02', label: '各部門逾期未完成數' }], counts: { projects: 1, documents: 2 } };
const retrieved: AIResult = { kind: 'retrieval', engine: 'retrieval', answer: '檢索原文', warning: null, sources: [{ document_id: 'D1', title: '交付規範', project_id: 'P1', excerpt: '<script>文字</script> 截圖4張' }], analysis: null };
beforeEach(() => { vi.clearAllMocks(); vi.mocked(ai.status).mockResolvedValue(status); vi.mocked(ai.ask).mockResolvedValue(retrieved); vi.mocked(ai.document).mockResolvedValue({ title: '交付規範', text: '原文截圖4張' }); vi.mocked(ai.config).mockResolvedValue({ enabled: false, base_url: '', model: '' }); });

const gateway = { policy: 'local_only' as const, cloud_enabled: false as const, function: 'rag', classification: 'confidential' as const, classification_reason: 'source_level', route: 'none' as const, reason: 'model_disabled', outcome: 'not_sent' as const, source_count: 1, model: '' };

it('updates isolated formal index and defaults to current sources', async () => {
  const index = { last_update: { mode: 'incremental' as const, processed: 1, reused: 2, removed: 0 }, counts: { indexed: 1, pending: 1, skipped: 1 }, updated_at: '2026-10-20T12:00:00Z', can_refresh: true, items: [{ source_id: 'x', title: '圖片.png', source_type: 'attachment', version: 1, state: 'skipped', reason: '不支援此格式' }] };
  vi.mocked(ai.status).mockResolvedValue({ ...status, formal_available: true });
  vi.mocked(ai.refreshIndex).mockResolvedValue(index);
  render(<CopilotPanel scope="總覽" open close={vi.fn()} />);
  await screen.findByText(/1 個專案／2 份可見文件/);
  vi.mocked(ai.status).mockResolvedValue({ ...status, formal_available: true, index, can_sql: false });
  fireEvent.change(screen.getByLabelText('AI資料集'), { target: { value: 'formal-v1' } });
  await screen.findByText(/已索引 1／待更新 1／略過 1/);
  expect(screen.getByText('最近一次增量更新：處理 1／沿用 2／移除 0 個來源版本。')).toBeInTheDocument();
  expect(screen.getByLabelText('包含歷史版本')).not.toBeChecked();
  expect(screen.getByRole('option', { name: 'Text-to-SQL 資料分析' })).toBeDisabled();
  expect(screen.queryByText(/虛構延伸案/)).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: '更新文件索引' }));
  await waitFor(() => expect(ai.refreshIndex).toHaveBeenCalledOnce());
  await screen.findByRole('button', { name: '更新文件索引' });
  fireEvent.change(screen.getByLabelText('詢問 AI'), { target: { value: '新人報到' } });
  fireEvent.click(screen.getByRole('button', { name: '送出 AI 問題' }));
  await screen.findByText('檢索原文');
  expect(ai.ask).toHaveBeenCalledWith(expect.objectContaining({ dataset: 'formal-v1', include_history: false }), expect.any(AbortSignal));
  fireEvent.click(screen.getByRole('button', { name: '開啟原文 D1' }));
  await screen.findByText('原文截圖4張');
  expect(ai.document).toHaveBeenCalledWith('D1', expect.any(AbortSignal), 'formal-v1', false);
});

it('opts into formal history for ask, preview and citations and clears on opt-out', async () => {
  vi.mocked(ai.status).mockResolvedValue({ ...status, formal_available: true });
  vi.mocked(ai.ask).mockResolvedValue({ ...retrieved, sources: [{ ...retrieved.sources[0], is_current: false, version: 1 }] });
  vi.mocked(ai.preview).mockResolvedValue({ gateway, content: { question: '原訂', sources: [] } });
  render(<CopilotPanel scope="總覽" open close={vi.fn()} />);
  await screen.findByText(/1 個專案／2 份可見文件/);
  fireEvent.change(screen.getByLabelText('AI資料集'), { target: { value: 'formal-v1' } });
  fireEvent.click(screen.getByLabelText('包含歷史版本'));
  fireEvent.change(screen.getByLabelText('詢問 AI'), { target: { value: '原訂報到地點' } });
  await waitFor(() => expect(screen.getByRole('button', { name: '預覽提供給模型的資料' })).toBeEnabled());
  fireEvent.click(screen.getByRole('button', { name: '預覽提供給模型的資料' }));
  await screen.findByLabelText('模型資料預覽');
  expect(ai.preview).toHaveBeenLastCalledWith(expect.objectContaining({ dataset: 'formal-v1', include_history: true }), expect.any(AbortSignal));
  fireEvent.click(screen.getByRole('button', { name: '送出 AI 問題' }));
  await screen.findByText('D1 · 交付規範（歷史版本）');
  fireEvent.click(screen.getByRole('button', { name: '開啟原文 D1' }));
  await screen.findByLabelText('引用原文');
  expect(ai.document).toHaveBeenLastCalledWith('D1', expect.any(AbortSignal), 'formal-v1', true);
  fireEvent.click(screen.getByLabelText('包含歷史版本'));
  expect(screen.queryByLabelText('引用原文')).toBeNull();
  expect(screen.queryByText('檢索原文')).toBeNull();
});

it('polls formal status while open and cancels polling when closed', async () => {
  vi.mocked(ai.status).mockResolvedValue({ ...status, formal_available: true });
  const view = render(<CopilotPanel scope="總覽" open close={vi.fn()} />);
  await screen.findByText(/1 個專案／2 份可見文件/);
  fireEvent.change(screen.getByLabelText('AI資料集'), { target: { value: 'formal-v1' } });
  await waitFor(() => expect(ai.status).toHaveBeenLastCalledWith(expect.any(AbortSignal), 'formal-v1'));
  vi.useFakeTimers();
  try {
    // Re-enter the effect with fake timers.
    view.rerender(<CopilotPanel scope="總覽" open={false} close={vi.fn()} />);
    view.rerender(<CopilotPanel scope="總覽" open close={vi.fn()} />);
    await act(async () => {});
    const before = vi.mocked(ai.status).mock.calls.length;
    await act(async () => { await vi.advanceTimersByTimeAsync(10000); });
    expect(ai.status).toHaveBeenCalledTimes(before + 1);
    expect(ai.ask).not.toHaveBeenCalled();
    const signal = vi.mocked(ai.status).mock.calls.at(-1)![0]!;
    view.rerender(<CopilotPanel scope="總覽" open={false} close={vi.fn()} />);
    expect(signal.aborted).toBe(true);
    await act(async () => {});
    const closed = vi.mocked(ai.status).mock.calls.length;
    await act(async () => { await vi.advanceTimersByTimeAsync(20000); });
    expect(ai.status).toHaveBeenCalledTimes(closed);
  } finally {
    view.unmount();
    vi.useRealTimers();
  }
});

it('clears a status load error once a later formal poll succeeds', async () => {
  vi.mocked(ai.status).mockResolvedValue({ ...status, formal_available: true });
  const view = render(<CopilotPanel scope="總覽" open close={vi.fn()} />);
  await screen.findByText(/1 個專案／2 份可見文件/);
  vi.mocked(ai.status).mockRejectedValueOnce(new Error('offline'));
  vi.useFakeTimers();
  try {
    fireEvent.change(screen.getByLabelText('AI資料集'), { target: { value: 'formal-v1' } });
    await act(async () => {});
    expect(screen.getByRole('alert')).toHaveTextContent('無法載入 AI 資料');
    await act(async () => { await vi.advanceTimersByTimeAsync(10000); });
    expect(screen.queryByRole('alert')).toBeNull();
  } finally {
    view.unmount();
    vi.useRealTimers();
  }
});

it('says how many retrieved sections were not sent because of the model length limit', async () => {
  vi.mocked(ai.ask).mockResolvedValue({ ...retrieved, kind: 'rag', engine: 'model', answer: '五樓', citations: ['D1'], retrieval: 'hybrid', gateway: { ...gateway, route: 'local', reason: 'local_only', outcome: 'completed', source_count: 6, sent_count: 4 } });
  render(<CopilotPanel scope="總覽" open close={vi.fn()} />);
  await screen.findByText(/1 個專案／2 份可見文件/);
  fireEvent.change(screen.getByLabelText('詢問 AI'), { target: { value: '報到地點' } });
  fireEvent.click(screen.getByRole('button', { name: '送出 AI 問題' }));
  await screen.findByText('五樓');
  expect(screen.getByText(/提供模型 4 段；另 2 段因長度上限未提供/)).toBeInTheDocument();
  expect(screen.getByText('檢索方式：關鍵字＋本地語意向量')).toBeInTheDocument();
});

it('keeps formal refresh controls out of member view', async () => {
  vi.mocked(ai.status).mockResolvedValue({ ...status, formal_available: true, index: { counts: { indexed: 0, pending: 1, skipped: 0 }, items: [], updated_at: null, can_refresh: false } });
  render(<CopilotPanel scope="總覽" open close={vi.fn()} />);
  await screen.findByText(/1 個專案／2 份可見文件/);
  fireEvent.change(screen.getByLabelText('AI資料集'), { target: { value: 'formal-v1' } });
  await screen.findByText(/已索引 0／待更新 1／略過 0/);
  expect(screen.queryByRole('button', { name: '更新文件索引' })).toBeNull();
});

it('previews scoped data without asking and clears the preview when input changes', async () => {
  vi.mocked(ai.preview).mockResolvedValue({ gateway, content: { question: '預算', sources: [{ document_id: 'PDF-006', text: '<script>機密預算</script>' }] } });
  vi.mocked(ai.ask).mockResolvedValue({ ...retrieved, gateway });
  render(<CopilotPanel scope="總覽" open close={vi.fn()} />);
  await screen.findByText(/1 個專案／2 份可見文件/);
  fireEvent.change(screen.getByLabelText('詢問 AI'), { target: { value: '預算' } });
  fireEvent.click(screen.getByRole('button', { name: '預覽提供給模型的資料' }));
  const preview = await screen.findByLabelText('模型資料預覽');
  expect(preview).toHaveTextContent('機密');
  expect(preview).toHaveTextContent('尚未送往模型');
  expect(preview).toHaveTextContent('<script>機密預算</script>');
  expect(document.querySelector('script')).toBeNull();
  expect(ai.ask).not.toHaveBeenCalled();
  expect(ai.preview).toHaveBeenCalledWith(expect.objectContaining({ question: '預算', mode: 'rag' }), expect.any(AbortSignal));
  fireEvent.change(screen.getByLabelText('詢問 AI'), { target: { value: '課程' } });
  expect(screen.queryByLabelText('模型資料預覽')).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: '送出 AI 問題' }));
  await screen.findByText('檢索原文');
  expect(screen.getByText(/資料等級：機密/)).toBeInTheDocument();
});

it('aborts a pending preview and ignores its late result after scope changes', async () => {
  let resolve!: (value: Awaited<ReturnType<typeof ai.preview>>) => void;
  vi.mocked(ai.preview).mockImplementation(() => new Promise(r => { resolve = r; }));
  render(<CopilotPanel scope="總覽" open close={vi.fn()} />);
  await screen.findByText(/1 個專案／2 份可見文件/);
  fireEvent.change(screen.getByLabelText('詢問 AI'), { target: { value: '預算' } });
  fireEvent.click(screen.getByRole('button', { name: '預覽提供給模型的資料' }));
  const signal = vi.mocked(ai.preview).mock.calls[0][1]!;
  fireEvent.change(screen.getByLabelText('AI資料集'), { target: { value: 'starter-v1' } });
  expect(signal.aborted).toBe(true);
  await act(async () => resolve({ gateway, content: { question: '預算', sources: [] } }));
  expect(screen.queryByLabelText('模型資料預覽')).toBeNull();
});

it('selects the starter corpus, requests history explicitly and opens its own citations', async () => {
  render(<CopilotPanel scope="總覽" open close={vi.fn()} />);
  await screen.findByText(/1 個專案／2 份可見文件/);
  vi.mocked(ai.status).mockResolvedValue({ ...status, as_of: '2026-10-20', can_sql: false, projects: [], counts: { projects: 4, documents: 23 } });
  fireEvent.change(screen.getByLabelText('AI資料集'), { target: { value: 'starter-v1' } });
  await screen.findByText(/基準日 2026-10-20/);
  expect(screen.getByRole('option', { name: 'Text-to-SQL 資料分析' })).toBeDisabled();
  fireEvent.click(screen.getByLabelText('包含歷史版本'));
  fireEvent.change(screen.getByLabelText('詢問 AI'), { target: { value: '課程原本哪天？' } });
  fireEvent.click(screen.getByRole('button', { name: '送出 AI 問題' }));
  await screen.findByText('檢索原文');
  expect(ai.ask).toHaveBeenLastCalledWith(expect.objectContaining({ dataset: 'starter-v1', include_history: true }), expect.any(AbortSignal));
  fireEvent.click(screen.getByRole('button', { name: '開啟原文 D1' }));
  await screen.findByText('原文截圖4張');
  expect(ai.document).toHaveBeenLastCalledWith('D1', expect.any(AbortSignal), 'starter-v1', true);
});

it('cancels old queries and clears their replies when the dataset changes', async () => {
  let resolve!: (value: AIResult) => void;
  vi.mocked(ai.ask).mockImplementation(() => new Promise(r => { resolve = r; }));
  render(<CopilotPanel scope="總覽" open close={vi.fn()} />);
  await screen.findByText(/1 個專案／2 份可見文件/);
  fireEvent.click(screen.getByRole('button', { name: '現行交付需要幾張截圖？' }));
  const signal = vi.mocked(ai.ask).mock.calls[0][1]!;
  fireEvent.change(screen.getByLabelText('AI資料集'), { target: { value: 'starter-v1' } });
  expect(signal.aborted).toBe(true);
  await act(async () => resolve(retrieved));
  expect(screen.queryByText('檢索原文')).toBeNull();
});

it('uses explicit complete work-order mode without silently accepting extra text filters', async () => {
  render(<CopilotPanel scope="總覽" open close={vi.fn()} />);
  await screen.findByText(/1 個專案／2 份可見文件/);
  fireEvent.change(screen.getByLabelText('AI資料集'), { target: { value: 'starter-v1' } });
  await screen.findByText(/1 個專案／2 份可見文件/);
  fireEvent.change(screen.getByLabelText('查詢方式'), { target: { value: 'work_orders' } });
  expect(screen.getByLabelText('詢問 AI')).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: '送出 AI 問題' }));
  await screen.findByText('檢索原文');
  expect(ai.ask).toHaveBeenLastCalledWith(expect.objectContaining({
    dataset: 'starter-v1', mode: 'work_orders', question: '列出全部未完成工單',
  }), expect.any(AbortSignal));
});

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

it('gives the conversation the space: settings fold into one line once a reply arrives', async () => {
  render(<CopilotPanel scope="總覽" open close={vi.fn()} />);
  await screen.findByText(/1 個專案／2 份可見文件/);
  const toggle = screen.getByRole('button', { name: /查詢設定/ });
  // Before the first question the settings are open, so the user can choose the data first.
  expect(toggle).toHaveAttribute('aria-expanded', 'true');
  expect(screen.getByLabelText('AI資料集')).toBeVisible();
  expect(toggle).toHaveTextContent('原有展示資料・文件問答・全部專案');
  fireEvent.click(screen.getByRole('button', { name: '現行交付需要幾張截圖？' }));
  await screen.findByText('檢索原文');
  // After the reply the settings fold away; question and answer are separate blocks.
  expect(toggle).toHaveAttribute('aria-expanded', 'false');
  expect(screen.getByLabelText('AI資料集')).not.toBeVisible();
  expect(screen.getByText('現行交付需要幾張截圖？', { selector: '.copilot-question' })).toBeInTheDocument();
  expect(screen.getByText('檢索原文', { selector: '.copilot-answer' })).toBeInTheDocument();
  expect(screen.getByText('來源 1 份')).toBeInTheDocument();
  // Suggested questions stay one click away, and the settings reopen on demand.
  expect(screen.getByRole('group', { name: '副手快捷動作' })).toBeVisible();
  fireEvent.click(toggle);
  expect(toggle).toHaveAttribute('aria-expanded', 'true');
  expect(screen.getByLabelText('AI資料集')).toBeVisible();
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
