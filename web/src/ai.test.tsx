import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import CopilotPanel from './components/CopilotPanel';
import { ai } from './ai';
import type { AIResult, AIStatus } from './ai';
import { ApiError } from './api';
vi.mock('./ai', async importOriginal => ({ ...await importOriginal<typeof import('./ai')>(), ai: { status: vi.fn(), ask: vi.fn(), preview: vi.fn(), refreshIndex: vi.fn(), document: vi.fn(), config: vi.fn(), save: vi.fn(), test: vi.fn(), feedback: vi.fn(), feedbackSummary: vi.fn() } }));
const status: AIStatus = { ready: true, as_of: '2026-10-11', company_name: '食品', model_enabled: false, model_name: '', can_configure: true, can_sql: true, projects: [{ project_id: 'P1', title: '展示案' }], queries: [{ query_id: 'q02', label: '各部門逾期未完成數' }], counts: { projects: 1, documents: 2 } };
const retrieved: AIResult = { kind: 'retrieval', engine: 'retrieval', answer: '檢索原文', warning: null, sources: [{ document_id: 'D1', title: '交付規範', project_id: 'P1', excerpt: '<script>文字</script> 截圖4張' }], analysis: null };
beforeEach(() => { vi.clearAllMocks(); vi.mocked(ai.status).mockResolvedValue(status); vi.mocked(ai.ask).mockResolvedValue(retrieved); vi.mocked(ai.document).mockResolvedValue({ title: '交付規範', text: '原文截圖4張' }); vi.mocked(ai.config).mockResolvedValue({ enabled: false, base_url: '', model: '' }); vi.mocked(ai.feedbackSummary).mockRejectedValue(new ApiError(403, '只有管理者可查看回饋統計')); });

const gateway = { policy: 'local_only' as const, cloud_enabled: false as const, function: 'rag', classification: 'confidential' as const, classification_reason: 'source_level', route: 'none' as const, reason: 'model_disabled', outcome: 'not_sent' as const, source_count: 1, model: '' };
const FOOD = '毛研食品';
const ready = () => screen.findByText(/1 個專案／2 份可見文件/);
const category = (name: string) => fireEvent.click(screen.getByRole('button', { name, pressed: false }));
const advanced = () => { const gear = screen.getByRole('button', { name: '進階設定' }); if (gear.getAttribute('aria-expanded') !== 'true') fireEvent.click(gear); };

it('shows only the conversation, category buttons and fixed shortcut questions', async () => {
  render(<CopilotPanel scope="總覽" open close={vi.fn()} companyName={FOOD} />);
  await ready();
  // No setup menus: the category and the shortcut question decide the data.
  expect(screen.queryAllByRole('combobox')).toHaveLength(0);
  expect(screen.queryByLabelText('包含歷史版本')).toBeNull();
  expect(screen.getByRole('button', { name: '文件問答', pressed: true })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: '資料分析', pressed: false })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: '新人報到', pressed: false })).toBeInTheDocument();
  // Advanced details stay folded behind the gear until asked for.
  expect(screen.getByRole('button', { name: '進階設定' })).toHaveAttribute('aria-expanded', 'false');
  expect(screen.getByText('本地模型連線設定')).not.toBeVisible();
  const shortcuts = screen.getByRole('group', { name: '副手快捷動作' });
  expect(shortcuts).toBeVisible();
  fireEvent.click(screen.getByRole('button', { name: '現行交付需要幾張截圖？' }));
  await screen.findByText('檢索原文');
  expect(ai.ask).toHaveBeenCalledWith(expect.objectContaining({ question: '現行交付需要幾張截圖？', mode: 'rag', project_id: null }), expect.any(AbortSignal));
  expect(screen.getByText('現行交付需要幾張截圖？', { selector: '.copilot-question' })).toBeInTheDocument();
  expect(screen.getByText('檢索原文', { selector: '.copilot-answer' })).toBeInTheDocument();
  expect(screen.getByText('來源 1 份')).toBeInTheDocument();
  // The shortcuts stay one click away after a reply.
  expect(screen.getByRole('group', { name: '副手快捷動作' })).toBeVisible();
  advanced();
  expect(screen.getByText('本地模型連線設定')).toBeVisible();
  expect(screen.getByText('模型未啟用・檢索與資料查詢可用')).toBeVisible();
});

it('offers only the categories the company has data and permission for', async () => {
  const view = render(<CopilotPanel scope="總覽" open close={vi.fn()} companyName="雲序軟體" />);
  await ready();
  expect(screen.getByRole('button', { name: '文件問答' })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: '資料分析' })).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: '新人報到' })).toBeNull();
  expect(screen.queryByRole('button', { name: '正式文件' })).toBeNull();
  view.unmount();
  vi.mocked(ai.status).mockResolvedValue({ ...status, formal_available: true });
  render(<CopilotPanel scope="總覽" open close={vi.fn()} companyName={FOOD} />);
  await ready();
  expect(screen.getByRole('button', { name: '正式文件' })).toBeInTheDocument();
});

it('switches the shortcut questions and dataset with the category', async () => {
  render(<CopilotPanel scope="總覽" open close={vi.fn()} companyName={FOOD} />);
  await ready();
  category('資料分析');
  expect(screen.getByRole('button', { name: '供應商已收貨延遲率' })).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: '現行交付需要幾張截圖？' })).toBeNull();
  expect(screen.getByLabelText('詢問 AI')).toHaveAttribute('placeholder', '例如：各部門逾期未完成數');
  category('新人報到');
  await waitFor(() => expect(ai.status).toHaveBeenLastCalledWith(expect.any(AbortSignal), 'starter-v1'));
  expect(screen.getByRole('button', { name: '列出全部未完成工單' })).toBeInTheDocument();
});

it('updates isolated formal index and defaults to current sources', async () => {
  const index = { last_update: { mode: 'incremental' as const, processed: 1, reused: 2, removed: 0 }, counts: { indexed: 1, pending: 1, skipped: 1 }, updated_at: '2026-10-20T12:00:00Z', can_refresh: true, items: [{ source_id: 'x', title: '圖片.png', source_type: 'attachment', version: 1, state: 'skipped', reason: '不支援此格式' }] };
  vi.mocked(ai.status).mockResolvedValue({ ...status, formal_available: true });
  vi.mocked(ai.refreshIndex).mockResolvedValue(index);
  render(<CopilotPanel scope="總覽" open close={vi.fn()} companyName={FOOD} />);
  await ready();
  vi.mocked(ai.status).mockResolvedValue({ ...status, formal_available: true, index, can_sql: false });
  category('正式文件');
  advanced();
  await screen.findByText(/已索引 1／待更新 1／略過 1/);
  expect(screen.getByText('最近一次增量更新：處理 1／沿用 2／移除 0 個來源版本。')).toBeInTheDocument();
  // The SQL category is a role permission, so it stays while browsing a dataset without SQL.
  expect(screen.getByRole('button', { name: '資料分析' })).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: '更新文件索引' }));
  await waitFor(() => expect(ai.refreshIndex).toHaveBeenCalledOnce());
  await screen.findByRole('button', { name: '更新文件索引' });
  fireEvent.change(screen.getByLabelText('詢問 AI'), { target: { value: '新人報到' } });
  fireEvent.click(screen.getByRole('button', { name: '送出 AI 問題' }));
  await screen.findByText('檢索原文');
  expect(ai.ask).toHaveBeenCalledWith(expect.objectContaining({ dataset: 'formal-v1', include_history: false, mode: 'rag', project_id: null }), expect.any(AbortSignal));
  fireEvent.click(screen.getByRole('button', { name: '開啟原文 D1' }));
  await screen.findByText('原文截圖4張');
  // A cited formal version stays readable after a newer upload, so sources always open with history allowed.
  expect(ai.document).toHaveBeenCalledWith('D1', expect.any(AbortSignal), 'formal-v1', true);
});

it('lets a shortcut ask for history and one project, and opens citations with that history', async () => {
  vi.mocked(ai.status).mockResolvedValue({ ...status, formal_available: true });
  vi.mocked(ai.ask).mockResolvedValue({ ...retrieved, sources: [{ ...retrieved.sources[0], is_current: false, version: 1 }] });
  render(<CopilotPanel scope="總覽" open close={vi.fn()} companyName={FOOD} />);
  await ready();
  vi.mocked(ai.status).mockResolvedValue({ ...status, formal_available: true, can_sql: false, projects: [{ project_id: 'X1', title: '增量索引展示（虛構）' }, { project_id: 'OCR1', title: 'OCR 示範（虛構）' }] });
  category('正式文件');
  await waitFor(() => expect(ai.status).toHaveBeenLastCalledWith(expect.any(AbortSignal), 'formal-v1'));
  await waitFor(() => expect(screen.getByRole('button', { name: '新人報到地點原本和現在分別在哪一樓？' })).toBeEnabled());
  fireEvent.click(screen.getByRole('button', { name: '新人報到地點原本和現在分別在哪一樓？' }));
  await screen.findByText('D1 · 交付規範（歷史版本）');
  expect(ai.ask).toHaveBeenLastCalledWith(expect.objectContaining({ dataset: 'formal-v1', include_history: true, project_id: 'X1' }), expect.any(AbortSignal));
  fireEvent.click(screen.getByRole('button', { name: '開啟原文 D1' }));
  await screen.findByLabelText('引用原文');
  expect(ai.document).toHaveBeenLastCalledWith('D1', expect.any(AbortSignal), 'formal-v1', true);
  fireEvent.click(screen.getByRole('button', { name: '新人報到要先去哪裡換證？' }));
  await waitFor(() => expect(ai.ask).toHaveBeenLastCalledWith(expect.objectContaining({ include_history: false, project_id: 'OCR1' }), expect.any(AbortSignal)));
});

it('polls formal status while open and cancels polling when closed', async () => {
  vi.mocked(ai.status).mockResolvedValue({ ...status, formal_available: true });
  const view = render(<CopilotPanel scope="總覽" open close={vi.fn()} companyName={FOOD} />);
  await ready();
  category('正式文件');
  await waitFor(() => expect(ai.status).toHaveBeenLastCalledWith(expect.any(AbortSignal), 'formal-v1'));
  vi.useFakeTimers();
  try {
    // Re-enter the effect with fake timers.
    view.rerender(<CopilotPanel scope="總覽" open={false} close={vi.fn()} companyName={FOOD} />);
    view.rerender(<CopilotPanel scope="總覽" open close={vi.fn()} companyName={FOOD} />);
    await act(async () => {});
    const before = vi.mocked(ai.status).mock.calls.length;
    await act(async () => { await vi.advanceTimersByTimeAsync(10000); });
    expect(ai.status).toHaveBeenCalledTimes(before + 1);
    expect(ai.ask).not.toHaveBeenCalled();
    const signal = vi.mocked(ai.status).mock.calls.at(-1)![0]!;
    view.rerender(<CopilotPanel scope="總覽" open={false} close={vi.fn()} companyName={FOOD} />);
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
  const view = render(<CopilotPanel scope="總覽" open close={vi.fn()} companyName={FOOD} />);
  await ready();
  vi.mocked(ai.status).mockRejectedValueOnce(new Error('offline'));
  vi.useFakeTimers();
  try {
    category('正式文件');
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
  await ready();
  fireEvent.change(screen.getByLabelText('詢問 AI'), { target: { value: '報到地點' } });
  fireEvent.click(screen.getByRole('button', { name: '送出 AI 問題' }));
  await screen.findByText('五樓');
  expect(screen.getByText(/提供模型 4 段；另 2 段因長度上限未提供/)).toBeInTheDocument();
  expect(screen.getByText('檢索方式：關鍵字＋本地語意向量')).toBeInTheDocument();
});

it('keeps formal refresh controls out of member view', async () => {
  vi.mocked(ai.status).mockResolvedValue({ ...status, formal_available: true, index: { counts: { indexed: 0, pending: 1, skipped: 0 }, items: [], updated_at: null, can_refresh: false } });
  render(<CopilotPanel scope="總覽" open close={vi.fn()} companyName={FOOD} />);
  await ready();
  category('正式文件');
  advanced();
  await screen.findByText(/已索引 0／待更新 1／略過 0/);
  expect(screen.queryByRole('button', { name: '更新文件索引' })).toBeNull();
});

it('previews scoped data without asking and clears the preview when input changes', async () => {
  vi.mocked(ai.preview).mockResolvedValue({ gateway, content: { question: '預算', sources: [{ document_id: 'PDF-006', text: '<script>機密預算</script>' }] } });
  vi.mocked(ai.ask).mockResolvedValue({ ...retrieved, gateway });
  render(<CopilotPanel scope="總覽" open close={vi.fn()} />);
  await ready();
  fireEvent.change(screen.getByLabelText('詢問 AI'), { target: { value: '預算' } });
  advanced();
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

it('aborts a pending preview and ignores its late result after the category changes', async () => {
  let resolve!: (value: Awaited<ReturnType<typeof ai.preview>>) => void;
  vi.mocked(ai.preview).mockImplementation(() => new Promise(r => { resolve = r; }));
  render(<CopilotPanel scope="總覽" open close={vi.fn()} companyName={FOOD} />);
  await ready();
  fireEvent.change(screen.getByLabelText('詢問 AI'), { target: { value: '預算' } });
  advanced();
  fireEvent.click(screen.getByRole('button', { name: '預覽提供給模型的資料' }));
  const signal = vi.mocked(ai.preview).mock.calls[0][1]!;
  category('新人報到');
  expect(signal.aborted).toBe(true);
  await act(async () => resolve({ gateway, content: { question: '預算', sources: [] } }));
  expect(screen.queryByLabelText('模型資料預覽')).toBeNull();
});

it('asks the starter corpus with history from its shortcut and opens its own citations', async () => {
  render(<CopilotPanel scope="總覽" open close={vi.fn()} companyName={FOOD} />);
  await ready();
  vi.mocked(ai.status).mockResolvedValue({ ...status, as_of: '2026-10-20', can_sql: false, projects: [], counts: { projects: 4, documents: 23 } });
  category('新人報到');
  await screen.findByText(/基準日 2026-10-20/);
  fireEvent.click(screen.getByRole('button', { name: '新人課程原本哪天？為什麼改期？' }));
  await screen.findByText('檢索原文');
  expect(ai.ask).toHaveBeenLastCalledWith(expect.objectContaining({ dataset: 'starter-v1', include_history: true }), expect.any(AbortSignal));
  fireEvent.click(screen.getByRole('button', { name: '開啟原文 D1' }));
  await screen.findByText('原文截圖4張');
  expect(ai.document).toHaveBeenLastCalledWith('D1', expect.any(AbortSignal), 'starter-v1', true);
});

it('cancels old queries and clears their replies when the category changes', async () => {
  let resolve!: (value: AIResult) => void;
  vi.mocked(ai.ask).mockImplementation(() => new Promise(r => { resolve = r; }));
  render(<CopilotPanel scope="總覽" open close={vi.fn()} companyName={FOOD} />);
  await ready();
  fireEvent.click(screen.getByRole('button', { name: '現行交付需要幾張截圖？' }));
  const signal = vi.mocked(ai.ask).mock.calls[0][1]!;
  category('新人報到');
  expect(signal.aborted).toBe(true);
  await act(async () => resolve(retrieved));
  expect(screen.queryByText('檢索原文')).toBeNull();
});

it('lists complete work orders from its shortcut', async () => {
  render(<CopilotPanel scope="總覽" open close={vi.fn()} companyName={FOOD} />);
  await ready();
  category('新人報到');
  await waitFor(() => expect(screen.getByRole('button', { name: '列出全部未完成工單' })).toBeEnabled());
  fireEvent.click(screen.getByRole('button', { name: '列出全部未完成工單' }));
  await screen.findByText('檢索原文');
  expect(ai.ask).toHaveBeenLastCalledWith(expect.objectContaining({
    dataset: 'starter-v1', mode: 'work_orders', question: '列出全部未完成工單',
  }), expect.any(AbortSignal));
});

it('queries the actual API across all visible projects and opens an escaped original citation', async () => {
  render(<CopilotPanel scope="總覽" open close={vi.fn()} />);
  await ready();
  fireEvent.click(screen.getByRole('button', { name: '現行交付需要幾張截圖？' }));
  await screen.findByText('檢索原文');
  expect(ai.ask).toHaveBeenCalledWith(expect.objectContaining({ mode: 'rag', project_id: null }), expect.any(AbortSignal));
  expect(screen.getByText('<script>文字</script> 截圖4張')).toBeInTheDocument();
  expect(document.querySelector('script')).toBeNull();
  fireEvent.click(screen.getByText('D1 · 交付規範'));
  fireEvent.click(screen.getByRole('button', { name: '開啟原文 D1' }));
  expect(await screen.findByLabelText('引用原文')).toHaveTextContent('原文截圖4張');
});

it('renders SQL results and the executed query from an analysis shortcut', async () => {
  vi.mocked(ai.ask).mockResolvedValue({ ...retrieved, kind: 'sql', sources: [], analysis: { query_id: 'q02', label: '逾期', sql: 'SELECT COUNT(*) FROM tasks', parameters: { company_id: 'food' }, columns: ['department', 'overdue_count'], rows: [{ department: '研發', overdue_count: 3 }], truncated: false } });
  render(<CopilotPanel scope="總覽" open close={vi.fn()} />);
  await ready();
  category('資料分析');
  fireEvent.click(screen.getByRole('button', { name: '各部門逾期未完成數' }));
  expect(await screen.findByLabelText('查詢結果')).toHaveTextContent('研發');
  expect(screen.getByText('SELECT COUNT(*) FROM tasks')).toBeInTheDocument();
  expect(ai.ask).toHaveBeenCalledWith(expect.objectContaining({ question: '各部門逾期未完成數', mode: 'sql' }), expect.any(AbortSignal));
});

it('shows query errors and keeps unsupported members out of SQL and model settings', async () => {
  vi.mocked(ai.status).mockResolvedValue({ ...status, can_configure: false, can_sql: false });
  vi.mocked(ai.ask).mockRejectedValue(new Error('登入已失效'));
  render(<CopilotPanel scope="總覽" open close={vi.fn()} />);
  await ready();
  expect(screen.queryByRole('button', { name: '資料分析' })).toBeNull();
  expect(screen.queryByText('本地模型連線設定')).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: '現行交付需要幾張截圖？' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('登入已失效');
});

it('lets admin test and save local model settings', async () => {
  vi.mocked(ai.test).mockResolvedValue({ ok: true, models: ['test:1'], message: '連線成功' });
  vi.mocked(ai.save).mockResolvedValue({ ok: true });
  render(<CopilotPanel scope="總覽" open close={vi.fn()} />);
  await ready();
  advanced();
  fireEvent.click(screen.getByText('本地模型連線設定'));
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

it('names a dropped condition and runs a suggested analysis only when clicked', async () => {
  vi.mocked(ai.ask).mockResolvedValue({ ...retrieved, kind: 'fallback', engine: 'rules', analysis: null, sources: [], answer: '目前的分析還不能套用「上週」這個條件。尚未執行',
    conditions: [{ type: 'time', label: '時間', text: '上週' }],
    suggestions: [{ query_id: 'q02', label: '各部門逾期未完成數', omits: '不含「上週」條件' }, { query_id: 'q13', label: '本週到期未完成任務', omits: '不含「上週」條件' }] });
  render(<CopilotPanel scope="總覽" open close={vi.fn()} />);
  await ready();
  category('資料分析');
  fireEvent.change(screen.getByLabelText('詢問 AI'), { target: { value: '上週有多少工作逾期？' } });
  fireEvent.click(screen.getByRole('button', { name: '送出 AI 問題' }));
  await screen.findByText(/還不能套用「上週」/);
  expect(screen.queryByLabelText('查詢結果')).toBeNull();
  expect(ai.ask).toHaveBeenCalledTimes(1);
  fireEvent.click(screen.getByRole('button', { name: '查詢：各部門逾期未完成數（不含「上週」條件）' }));
  await waitFor(() => expect(ai.ask).toHaveBeenLastCalledWith(expect.objectContaining({ query_id: 'q02', mode: 'sql' }), expect.any(AbortSignal)));
});

it('shows written help on separate lines with shortcut analyses', async () => {
  vi.mocked(ai.ask).mockResolvedValue({ ...retrieved, kind: 'help', engine: 'rules', analysis: null, sources: [], answer: '我是資料分析小幫手\n・工作進度',
    suggestions: [{ query_id: 'q02', label: '各部門逾期未完成數', omits: '' }] });
  render(<CopilotPanel scope="總覽" open close={vi.fn()} />);
  await ready();
  category('資料分析');
  fireEvent.change(screen.getByLabelText('詢問 AI'), { target: { value: '你可以幫我查什麼？' } });
  fireEvent.click(screen.getByRole('button', { name: '送出 AI 問題' }));
  const answer = await screen.findByText(/我是資料分析小幫手/);
  expect(answer).toHaveStyle({ whiteSpace: 'pre-line' });
  expect(screen.getByRole('group', { name: '「你可以幫我查什麼？」的建議查詢' })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: '查詢：各部門逾期未完成數' })).toBeInTheDocument();
});

it('cancels a pending citation request when a new question starts', async () => {
  vi.mocked(ai.document).mockImplementation(() => new Promise(() => undefined));
  render(<CopilotPanel scope="總覽" open close={vi.fn()} />);
  await ready();
  fireEvent.click(screen.getByRole('button', { name: '現行交付需要幾張截圖？' }));
  await screen.findByText('檢索原文');
  fireEvent.click(screen.getByText('D1 · 交付規範'));
  fireEvent.click(screen.getByRole('button', { name: '開啟原文 D1' }));
  const signal = vi.mocked(ai.document).mock.calls[0][1]!;
  fireEvent.click(screen.getByRole('button', { name: '風險原因與處理方式' }));
  expect(signal.aborted).toBe(true);
  await waitFor(() => expect(screen.getAllByRole('button', { name: '開啟原文 D1' }).every(button => !(button as HTMLButtonElement).disabled)).toBe(true));
});

it('expires the session when a question or citation returns 401', async () => {
  const expired = vi.fn();
  vi.mocked(ai.ask).mockRejectedValueOnce(new ApiError(401, '登入已失效，請重新登入'));
  render(<CopilotPanel scope="總覽" open close={vi.fn()} expired={expired} />);
  await ready();
  fireEvent.click(screen.getByRole('button', { name: '現行交付需要幾張截圖？' }));
  await waitFor(() => expect(expired).toHaveBeenCalledTimes(1));
  vi.mocked(ai.document).mockRejectedValueOnce(new ApiError(401, '登入已失效，請重新登入'));
  fireEvent.click(screen.getByRole('button', { name: '現行交付需要幾張截圖？' }));
  await screen.findByText('檢索原文');
  fireEvent.click(screen.getByText('D1 · 交付規範'));
  fireEvent.click(screen.getByRole('button', { name: '開啟原文 D1' }));
  await waitFor(() => expect(expired).toHaveBeenCalledTimes(2));
});

const send = async (text: string) => {
  fireEvent.change(screen.getByLabelText('詢問 AI'), { target: { value: text } });
  // After a category change the button waits for that category's data to load.
  await waitFor(() => expect(screen.getByRole('button', { name: '送出 AI 問題' })).toBeEnabled());
  fireEvent.click(screen.getByRole('button', { name: '送出 AI 問題' }));
  await screen.findByText(text, { selector: '.copilot-question' });
};
const lastAsk = () => vi.mocked(ai.ask).mock.calls.at(-1)![0];

it('sends earlier questions as follow-up history and a new conversation starts over', async () => {
  render(<CopilotPanel scope="總覽" open close={vi.fn()} companyName={FOOD} />);
  await ready();
  await send('G2 要具備什麼？');
  expect(lastAsk()).not.toHaveProperty('history');
  vi.mocked(ai.ask).mockResolvedValueOnce({ ...retrieved, followup: 'model', standalone_question: 'G2 需要誰簽核？' });
  await send('那需要誰簽核？');
  expect(lastAsk().history).toEqual(['G2 要具備什麼？']);
  expect(await screen.findByText('已理解為：G2 需要誰簽核？')).toBeInTheDocument();
  vi.mocked(ai.ask).mockResolvedValueOnce({ ...retrieved, followup: 'combined', standalone_question: 'G2 需要誰簽核？ 還缺哪些？' });
  await send('還缺哪些？');
  expect(await screen.findByText('已合併上一題一起查詢')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: '新對話' }));
  expect(screen.queryByText('G2 要具備什麼？', { selector: '.copilot-question' })).toBeNull();
  await send('新的問題');
  expect(lastAsk()).not.toHaveProperty('history');
  // Switching category also starts over; data analysis never carries history.
  category('資料分析');
  await send('各部門逾期未完成數');
  await send('那哪個部門最多？');
  expect(lastAsk()).not.toHaveProperty('history');
});

it('bounds follow-up history to six questions and 6000 characters', async () => {
  render(<CopilotPanel scope="總覽" open close={vi.fn()} companyName={FOOD} />);
  await ready();
  for (const text of ['一', '二', '三', '四', '五', '六', '七']) await send(text);
  await send('那呢？');
  expect(lastAsk().history).toEqual(['二', '三', '四', '五', '六', '七']);
  fireEvent.click(screen.getByRole('button', { name: '新對話' }));
  const long = ['a'.repeat(1500), 'b'.repeat(2000), 'c'.repeat(2000), 'd'.repeat(1500)];
  for (const text of long) await send(text);
  await send('那呢？');
  expect(lastAsk().history).toEqual(long.slice(1));
});

it('records helpful or not for each answer and shows the counts to administrators', async () => {
  vi.mocked(ai.ask).mockResolvedValue({ ...retrieved, answer_id: 'A1' });
  vi.mocked(ai.feedback).mockResolvedValue({ ok: true, rating: 'helpful' });
  vi.mocked(ai.feedbackSummary).mockResolvedValue({ days: 30, helpful: 3, unhelpful: 1, total_answers: 5 });
  render(<CopilotPanel scope="總覽" open close={vi.fn()} companyName={FOOD} />);
  await ready();
  await send('現行交付需要幾張截圖？');
  fireEvent.click(screen.getByRole('button', { name: '有幫助' }));
  expect(await screen.findByText('已記錄：有幫助')).toBeInTheDocument();
  expect(ai.feedback).toHaveBeenCalledWith('A1', 'helpful');
  expect(screen.getByRole('button', { name: '有幫助' })).toHaveAttribute('aria-pressed', 'true');
  advanced();
  expect(await screen.findByText('回饋（近30天）：有幫助 3／沒有幫助 1／回答 5')).toBeInTheDocument();
});

it('shows where a formal source comes from, links its download and reports a source that can no longer be read', async () => {
  vi.mocked(ai.status).mockResolvedValue({ ...status, formal_available: true });
  const source = { document_id: 'doc-X-v1-c3', title: 'G2檢查表.pdf', project_id: 'P1', excerpt: 'G2 由品保經理簽核', is_current: true, source_type: 'document', version: 1, section: 3,
    document_ref: { kind: 'document' as const, document_id: 'X', version: 1 }, project_title: '展示案', node_title: '試產', page: 2 };
  vi.mocked(ai.ask).mockResolvedValue({ ...retrieved, sources: [source] });
  vi.mocked(ai.document).mockResolvedValue({ title: 'G2檢查表.pdf', text: '第2頁\nG2 由品保經理簽核', version: 1, is_current: true, section: 3,
    document_ref: source.document_ref, project_title: '展示案', node_title: '試產', page: 2 });
  render(<CopilotPanel scope="總覽" open close={vi.fn()} companyName="峰曜科技" />);
  await ready();
  // Every company may ask its own formal documents; only 毛研食品 has written shortcut questions.
  vi.mocked(ai.status).mockResolvedValue({ ...status, formal_available: true, can_sql: false });
  category('正式文件');
  expect(screen.getByRole('group', { name: '副手快捷動作' })).toBeEmptyDOMElement();
  await send('G2 誰簽核？');
  expect(screen.getByText('文件・G2檢查表.pdf・第1版／第3段・第2頁')).toBeInTheDocument();
  expect(screen.getByText('展示案／試產')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: '開啟索引段落：G2檢查表.pdf／3' }));
  expect(await screen.findByRole('link', { name: '下載原檔（第1版）' })).toHaveAttribute('href', '/api/documents/X/versions/1/download');
  expect(screen.getByText('第1版・現行版本・第2頁')).toBeInTheDocument();
  vi.mocked(ai.document).mockRejectedValueOnce(new ApiError(404, '找不到'));
  fireEvent.click(screen.getByRole('button', { name: '開啟索引段落：G2檢查表.pdf／3' }));
  expect(await screen.findByText('你目前無法查看這個來源。')).toBeInTheDocument();
  expect(screen.queryByRole('alert')).toBeNull();
});
