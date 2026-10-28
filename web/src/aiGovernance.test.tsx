import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import AIGovernance from './components/AIGovernance';
import { ai } from './ai';
import type { Governance } from './ai';
import { ApiError } from './api';
vi.mock('./ai', () => ({ ai: { governance: vi.fn(), classify: vi.fn(), setPolicy: vi.fn(), maskPreview: vi.fn() } }));

const data: Governance = {
  mode: 'local_only', company: 'internal', cloud_provider: null, can_set_policy: true,
  projects: [{ scope: 'project', id: 'p1', title: '新人報到', own: null, effective: 'internal', inherited: 'internal' }],
  nodes: [{ scope: 'node', id: 'n1', title: '配方階段', own: 'confidential', effective: 'confidential', inherited: 'internal', project_id: 'p1', parent_id: null },
    { scope: 'node', id: 'n2', title: '成本試算', own: null, effective: 'confidential', inherited: 'confidential', project_id: 'p1', parent_id: 'n1' }],
  documents: [{ scope: 'document', id: 'd1', title: '報到說明.txt', own: null, effective: 'internal', inherited: 'internal', project_id: 'p1', node_id: null }],
  recent: [{ action: 'ai.preview', created_at: '2026-10-23T08:00:00Z', classification: 'confidential', cloud: { eligible: false, reason: 'confidential_local_only', masked: false, provider: null, sent: false } }],
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(ai.governance).mockResolvedValue(data);
  vi.mocked(ai.classify).mockResolvedValue({ ok: true });
  vi.mocked(ai.setPolicy).mockResolvedValue({ ok: true });
});

it('shows effective levels and only offers stricter overrides', async () => {
  render(<AIGovernance fallback={<p>示意頁</p>} expired={vi.fn()} />);
  await screen.findByText('配方階段');
  expect(screen.getByText(/雲端供應商/)).toHaveTextContent('未設定');
  const child = screen.getByLabelText('成本試算 的分級');
  expect(child).toHaveValue('inherit');
  expect(screen.getAllByRole('option', { name: '公開' }).filter(o => o.closest('select') === child)[0]).toBeDisabled();
  expect(screen.getByText(/含機密資料，只能本地/)).toBeInTheDocument();
  fireEvent.change(child, { target: { value: 'confidential' } });
  await waitFor(() => expect(ai.classify).toHaveBeenCalledWith({ scope: 'node', id: 'n2', level: 'confidential' }, expect.any(AbortSignal)));
  await waitFor(() => expect(ai.governance).toHaveBeenCalledTimes(2));
});

it('saves policy and masks sample text without showing a mapping', async () => {
  vi.mocked(ai.maskPreview).mockResolvedValue({ masked: '鮪魚 {{比例_1}}', counts: { 比例: 1 } });
  render(<AIGovernance fallback={<p>示意頁</p>} expired={vi.fn()} />);
  await screen.findByText('配方階段');
  fireEvent.change(screen.getByLabelText('公司 AI 政策'), { target: { value: 'mixed' } });
  expect(screen.getByText('遮罩後才可送雲端')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: '儲存政策' }));
  await waitFor(() => expect(ai.setPolicy).toHaveBeenCalledWith('mixed', expect.any(AbortSignal)));
  fireEvent.click(screen.getByRole('button', { name: '測試遮罩' }));
  expect(await screen.findByText('鮪魚 {{比例_1}}')).toBeInTheDocument();
  expect(screen.getByText('比例 1 個')).toBeInTheDocument();
});

it('keeps policy read-only away from the local machine and falls back outside isolated mode', async () => {
  vi.mocked(ai.governance).mockResolvedValueOnce({ ...data, can_set_policy: false });
  const view = render(<AIGovernance fallback={<p>示意頁</p>} expired={vi.fn()} />);
  await screen.findByText('配方階段');
  expect(screen.getByLabelText('公司 AI 政策')).toBeDisabled();
  view.unmount();
  vi.mocked(ai.governance).mockRejectedValueOnce(new ApiError(404, 'not found'));
  render(<AIGovernance fallback={<p>示意頁</p>} expired={vi.fn()} />);
  expect(await screen.findByText('示意頁')).toBeInTheDocument();
});
