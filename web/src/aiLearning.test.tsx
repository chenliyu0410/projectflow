import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import LearningReview from './components/LearningReview';
import { ai } from './ai';
import type { LearnedPhrase } from './ai';
import { ApiError } from './api';
vi.mock('./ai', async importOriginal => ({ ...await importOriginal<typeof import('./ai')>(), ai: { status: vi.fn(), learning: vi.fn(), reviewLearning: vi.fn(), confirmLearning: vi.fn() } }));

const checks = { ran_at: '2026-11-05T08:00:00+00:00', passed: false, items: [
  { code: 'C1' as const, ok: false, reason: 'condition', title: '條件', message: '這句有這個分析套用不到的條件（時間、特定對象、狀態或排序比較），學起來會答錯。' },
  { code: 'C2' as const, ok: true, reason: null, title: '危險與說明', message: '不是指令、繞過限制、其他公司、沒有的資料或使用說明。' },
  { code: 'C3' as const, ok: true, reason: null, title: '衝突', message: '沒有和內建問法或其他已上線問法衝突。' },
  { code: 'C4' as const, ok: true, reason: null, title: '題庫不變', message: '內建檢查題庫每一題的結果都和加入前相同。' },
  { code: 'C5' as const, ok: true, reason: null, title: '實際執行', message: '用本公司資料實際執行這個分析成功。' },
] };
const phrase = (id: string, text: string, status: LearnedPhrase['status'], extra: Partial<LearnedPhrase> = {}): LearnedPhrase => ({
  id, phrase: text, query_id: 'q06', label: '供應商已收貨延遲率', status, confirmations: 1,
  first_confirmed_at: '2026-11-05T07:00:00+00:00', last_confirmed_at: '2026-11-05T07:00:00+00:00', reviewed_at: null, checks: null, ...extra,
});
const pending = phrase('L1', '哪些供應商常常遲交', 'pending', { confirmations: 2 });
const failed = phrase('L2', '上週哪些供應商遲交', 'pending', { checks });
const live = phrase('L3', '供應商常遲交嗎', 'approved', { checks: { ...checks, passed: true, items: checks.items.map(c => ({ ...c, ok: true, reason: null })) } });
const stopped = phrase('L4', '誰最常遲交', 'disabled');
const refused = phrase('L5', '供應商遲交排行', 'rejected');
const card = (text: string) => screen.getByRole('article', { name: `問法：${text}` });

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(ai.learning).mockResolvedValue({ items: [pending, failed, live, stopped, refused], pending: 2 });
});

it('lists candidates with the pending count, status, confirmations and the latest checks', async () => {
  render(<LearningReview />);
  expect(await screen.findByText('使用者確認的問法（2 筆待審核）')).toBeInTheDocument();
  expect(within(card('哪些供應商常常遲交')).getByText('「哪些供應商常常遲交」→ 供應商已收貨延遲率')).toBeInTheDocument();
  expect(within(card('哪些供應商常常遲交')).getByText('待審核')).toBeInTheDocument();
  expect(within(card('哪些供應商常常遲交')).getByText(/確認 2 人/)).toBeInTheDocument();
  expect(within(card('供應商常遲交嗎')).getByText('已上線')).toBeInTheDocument();
  expect(within(card('誰最常遲交')).getByText('已停用')).toBeInTheDocument();
  expect(within(card('供應商遲交排行')).getByText('已退回')).toBeInTheDocument();
  // 每項檢查照伺服器給的標題與白話原因顯示 ✓／✕。
  const results = within(card('上週哪些供應商遲交')).getByRole('list', { name: '自動檢查結果' });
  expect(within(results).getByText(/✕ 條件/).closest('li')).toHaveTextContent('這句有這個分析套用不到的條件');
  expect(within(results).getByText(/✓ 實際執行/).closest('li')).toHaveTextContent('用本公司資料實際執行這個分析成功。');
  expect(within(results).getAllByRole('listitem')).toHaveLength(5);
  // 按鈕只出現在可以做的狀態。
  expect(within(card('哪些供應商常常遲交')).getAllByRole('button').map(b => b.textContent)).toEqual(['審核＋測試', '退回']);
  expect(within(card('供應商常遲交嗎')).getAllByRole('button').map(b => b.textContent)).toEqual(['停用']);
  expect(within(card('誰最常遲交')).getAllByRole('button').map(b => b.textContent)).toEqual(['審核＋測試']);
  expect(within(card('供應商遲交排行')).queryAllByRole('button')).toHaveLength(0);
});

it('approves, rejects and disables the chosen phrase and reloads the list after each action', async () => {
  render(<LearningReview />);
  await screen.findByText('使用者確認的問法（2 筆待審核）');
  vi.mocked(ai.reviewLearning).mockResolvedValueOnce({ ...pending, status: 'approved', checks: live.checks });
  vi.mocked(ai.learning).mockResolvedValueOnce({ items: [failed, { ...pending, status: 'approved', checks: live.checks }, live, stopped, refused], pending: 1 });
  fireEvent.click(within(card('哪些供應商常常遲交')).getByRole('button', { name: '審核＋測試' }));
  expect(await screen.findByText('使用者確認的問法（1 筆待審核）')).toBeInTheDocument();
  expect(ai.reviewLearning).toHaveBeenLastCalledWith('L1', 'approve');
  expect(ai.learning).toHaveBeenCalledTimes(2);
  expect(within(card('哪些供應商常常遲交')).getByText('已上線')).toBeInTheDocument();
  expect(within(card('哪些供應商常常遲交')).getAllByText(/^✓/)).toHaveLength(5);
  expect(screen.getByRole('status')).toHaveTextContent('「哪些供應商常常遲交」已上線');

  vi.mocked(ai.reviewLearning).mockResolvedValueOnce({ ...failed, status: 'rejected' });
  vi.mocked(ai.learning).mockResolvedValueOnce({ items: [{ ...pending, status: 'approved' }, live, stopped, refused, { ...failed, status: 'rejected' }], pending: 0 });
  fireEvent.click(within(card('上週哪些供應商遲交')).getByRole('button', { name: '退回' }));
  expect(await screen.findByText('使用者確認的問法（0 筆待審核）')).toBeInTheDocument();
  expect(ai.reviewLearning).toHaveBeenLastCalledWith('L2', 'reject');

  vi.mocked(ai.reviewLearning).mockResolvedValueOnce({ ...live, status: 'disabled' });
  vi.mocked(ai.learning).mockResolvedValueOnce({ items: [{ ...pending, status: 'approved' }, { ...live, status: 'disabled' }, stopped, refused, { ...failed, status: 'rejected' }], pending: 0 });
  fireEvent.click(within(card('供應商常遲交嗎')).getByRole('button', { name: '停用' }));
  await waitFor(() => expect(within(card('供應商常遲交嗎')).getByText('已停用')).toBeInTheDocument());
  expect(ai.reviewLearning).toHaveBeenLastCalledWith('L3', 'disable');
  expect(ai.learning).toHaveBeenCalledTimes(4);
});

it('keeps a phrase pending and says so when the automatic checks do not all pass', async () => {
  render(<LearningReview />);
  await screen.findByText('使用者確認的問法（2 筆待審核）');
  vi.mocked(ai.reviewLearning).mockResolvedValueOnce(failed);
  fireEvent.click(within(card('上週哪些供應商遲交')).getByRole('button', { name: '審核＋測試' }));
  expect(await screen.findByRole('status')).toHaveTextContent('自動檢查沒有全過');
  expect(within(card('上週哪些供應商遲交')).getByText('待審核')).toBeInTheDocument();
});

it('shows the server reason when an action is refused and still reloads the list', async () => {
  render(<LearningReview />);
  await screen.findByText('使用者確認的問法（2 筆待審核）');
  vi.mocked(ai.reviewLearning).mockRejectedValueOnce(new ApiError(409, '只有待審核的問法可以退回'));
  fireEvent.click(within(card('哪些供應商常常遲交')).getByRole('button', { name: '退回' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('只有待審核的問法可以退回');
  await waitFor(() => expect(ai.learning).toHaveBeenCalledTimes(2));
});

it('renders nothing for non-administrators and hands an expired session back', async () => {
  vi.mocked(ai.learning).mockRejectedValueOnce(new ApiError(403, '只有管理者可以審核問法'));
  const view = render(<LearningReview />);
  await waitFor(() => expect(ai.learning).toHaveBeenCalledTimes(1));
  await act(async () => {});
  expect(view.container).toBeEmptyDOMElement();
  view.unmount();
  const expired = vi.fn();
  vi.mocked(ai.learning).mockRejectedValueOnce(new ApiError(401, '登入已失效，請重新登入'));
  render(<LearningReview expired={expired} />);
  await waitFor(() => expect(expired).toHaveBeenCalledTimes(1));
});

it('reloads when the panel reports a new confirmation', async () => {
  const view = render(<LearningReview version={0} />);
  await screen.findByText('使用者確認的問法（2 筆待審核）');
  vi.mocked(ai.learning).mockResolvedValueOnce({ items: [phrase('L9', '新問法', 'pending'), pending, failed], pending: 3 });
  view.rerender(<LearningReview version={1} />);
  expect(await screen.findByText('使用者確認的問法（3 筆待審核）')).toBeInTheDocument();
});

it('calls the learning endpoints and passes the server reason through on refusal', async () => {
  const { ai: client } = await vi.importActual<typeof import('./ai')>('./ai');
  const fetch = vi.fn()
    .mockResolvedValueOnce(new Response(JSON.stringify({ id: 'L1', phrase: '哪些供應商常常遲交', query_id: 'q06', label: '供應商已收貨延遲率', status: 'pending', confirmations: 1 }), { status: 200 }))
    .mockResolvedValueOnce(new Response(JSON.stringify({ items: [], pending: 0 }), { status: 200 }))
    .mockResolvedValueOnce(new Response(JSON.stringify({ detail: '只有待審核的問法可以退回' }), { status: 409 }))
    .mockResolvedValueOnce(new Response(JSON.stringify({ detail: [{ loc: ['body', 'question'], input: '秘密' }] }), { status: 422 }));
  vi.stubGlobal('fetch', fetch);
  await expect(client.confirmLearning({ answer_id: 'A1', query_id: 'q06', question: '哪些供應商常常遲交？' })).resolves.toMatchObject({ status: 'pending' });
  expect(fetch).toHaveBeenLastCalledWith('/api/ai/learning/confirm', expect.objectContaining({ method: 'POST', credentials: 'include', body: JSON.stringify({ answer_id: 'A1', query_id: 'q06', question: '哪些供應商常常遲交？' }) }));
  await expect(client.learning()).resolves.toEqual({ items: [], pending: 0 });
  expect(fetch).toHaveBeenLastCalledWith('/api/ai/learning', expect.objectContaining({ credentials: 'include' }));
  await expect(client.reviewLearning('L1', 'reject')).rejects.toMatchObject({ status: 409, message: '只有待審核的問法可以退回' });
  expect(fetch).toHaveBeenLastCalledWith('/api/ai/learning/L1/reject', expect.objectContaining({ method: 'POST' }));
  // 驗證錯誤的細節（可能含輸入內容）不顯示，改用通用文字。
  const refusal = await client.reviewLearning('L1', 'approve').then(() => null, (e: unknown) => e);
  expect(refusal).toBeInstanceOf(ApiError);
  expect((refusal as ApiError).message).toBe('問法學習操作失敗，請重新整理後再試。');
});
