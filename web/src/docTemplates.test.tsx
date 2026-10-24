import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import DocumentManager from './components/DocumentManager';
import DocTemplateLibrary from './components/DocTemplateLibrary';
import { totals } from './components/DocTemplateFill';

const quote = { id: 't1', name: '報價單', category: '業務', status: 'active', version: 1, filename: '報價單範例.docx', auto_fields: ['編號', '今天', '填寫人', '專案名稱', '節點名稱', '公司名稱'],
  fields: [{ name: '客戶名稱', label: '客戶名稱', type: 'text', required: true, unit: '', options: [] }, { name: '有效期限', label: '有效期限', type: 'date', required: true, unit: '', options: [] }],
  numbering: 'Q-{年}-{月}{日}-{序號2位}', tax_rate: '5', rounding: 'half_up', has_lines: true, can_manage: true };
const generated = { document_id: 'd', version: 1, filename: '報價單-Q-2026-1023-01.docx', size_bytes: 9, created_at: '2026-10-23T10:00:00Z', created_by: '游專案', comment: '由樣板產生', editable: false, from_template: true };
const json = (data: unknown, status = 200) => new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } });

function mock({ readonly = false } = {}) {
  let made = false;
  const fetcher = vi.fn(async (url: string, init: RequestInit = {}) => {
    if (url.endsWith('/from-template')) { made = true; return json(generated, 201); }
    if (url.endsWith('/document-templates')) return json({ items: [quote], can_manage: !readonly });
    if (url.endsWith('/documents')) return json({ items: made ? [generated] : [], can_write: !readonly });
    if (url.endsWith('/versions')) return json({ items: [generated], current_version: 1, can_write: !readonly });
    if (url.endsWith('/fill')) return json({ document_id: 'd', current_version: 1, template_name: '報價單', fields: quote.fields, has_lines: true, tax_rate: '5', rounding: 'half_up', number: 'Q-2026-1023-01', values: { 客戶名稱: '好毛', 有效期限: '2026-11-22' }, lines: [{ 品項: '鮪魚罐', 數量: '2000', 單價: '32' }] });
    return json({ error: init.method }, 404);
  });
  vi.stubGlobal('fetch', fetcher); return fetcher;
}

it('computes line amounts, tax and total like the server', () => {
  const sums = totals([{ 品項: 'a', 數量: '2,000', 單價: '32' }, { 品項: 'b', 數量: '1000', 單價: '30' }], '5', 'half_up');
  expect(sums).toEqual({ amounts: [64000, 30000], subtotal: 94000, tax: 4700, total: 98700 });
  expect(totals([{ 品項: 'a', 數量: '1', 單價: '10.5' }], '5', 'down').amounts).toEqual([10]);
  expect(totals([{ 品項: 'a', 數量: '1', 單價: '10.5' }], '5', 'half_up').tax).toBe(1);
});

it('blocks missing required fields, then generates a document from a template', async () => {
  const fetcher = mock();
  render(<DocumentManager scopePath="/nodes/n" expired={vi.fn()} />);
  fireEvent.click(await screen.findByRole('button', { name: '用樣板建立' }));
  fireEvent.change(await screen.findByLabelText('選擇樣板'), { target: { value: 't1' } });
  fireEvent.change(screen.getByLabelText('第 1 列品項'), { target: { value: '成貓主食罐 鮪魚 85g' } });
  fireEvent.change(screen.getByLabelText('第 1 列數量'), { target: { value: '2000' } });
  fireEvent.change(screen.getByLabelText('第 1 列單價'), { target: { value: '32' } });
  fireEvent.click(screen.getByRole('button', { name: '新增一列' }));
  fireEvent.change(screen.getByLabelText('第 2 列品項'), { target: { value: '雞肉' } });
  fireEvent.change(screen.getByLabelText('第 2 列數量'), { target: { value: '1000' } });
  fireEvent.change(screen.getByLabelText('第 2 列單價'), { target: { value: '30' } });
  expect(screen.getByLabelText('金額合計')).toHaveTextContent('98,700');
  fireEvent.click(screen.getByRole('button', { name: '產生文件' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('請填寫「客戶名稱」');
  // The message sits right above the submit button, where the user just clicked, not at the top of a long form.
  expect(screen.getByRole('alert').nextElementSibling).toContainElement(screen.getByRole('button', { name: '產生文件' }));
  expect(fetcher.mock.calls.some(([url]) => String(url).endsWith('/from-template'))).toBe(false);
  fireEvent.change(screen.getByLabelText('客戶名稱'), { target: { value: '好毛 <b>{{x}}</b>' } });
  fireEvent.change(screen.getByLabelText('有效期限'), { target: { value: '2026-11-22' } });
  fireEvent.click(screen.getByRole('button', { name: '產生文件' }));
  expect(await screen.findByRole('status')).toHaveTextContent('已產生 報價單-Q-2026-1023-01.docx，版本 v1');
  const body = JSON.parse(String(fetcher.mock.calls.find(([url]) => String(url).endsWith('/from-template'))?.[1]?.body));
  expect(body).toEqual({ template_id: 't1', values: { 客戶名稱: '好毛 <b>{{x}}</b>', 有效期限: '2026-11-22' },
    lines: [{ 品項: '成貓主食罐 鮪魚 85g', 數量: '2000', 單價: '32' }, { 品項: '雞肉', 數量: '1000', 單價: '30' }] });
  expect(await screen.findByRole('button', { name: '修改內容重新產生' })).toBeInTheDocument();
});

it('hides template creation from readonly users', async () => {
  mock({ readonly: true });
  render(<DocumentManager scopePath="/nodes/n" expired={vi.fn()} />);
  expect(await screen.findByText('目前僅可檢視與下載文件。')).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: '用樣板建立' })).toBeNull();
});

it('lets administrators open field settings and renders nothing for others', async () => {
  mock();
  const { unmount } = render(<DocTemplateLibrary expired={vi.fn()} />);
  fireEvent.click(await screen.findByRole('button', { name: '設定欄位' }));
  expect(screen.getByLabelText('客戶名稱 顯示名稱')).toHaveValue('客戶名稱');
  expect(screen.getByLabelText('有效期限 必填')).toBeChecked();
  expect(screen.getByText(/自動帶入：編號、今天/)).toBeInTheDocument();
  unmount();
  mock({ readonly: true });
  const { container } = render(<DocTemplateLibrary expired={vi.fn()} />);
  await waitFor(() => expect(container).toBeEmptyDOMElement());
});
