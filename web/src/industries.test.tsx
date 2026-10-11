import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import PreviewBoundary from './components/PreviewBoundary';
import data from './preview/industries.json';
afterEach(cleanup);

for (const [key, dataset] of Object.entries(data)) it(`${key}: complete isolated records, valid links and ephemeral editing`, () => {
  const props = { companyKey: key, companyName: dataset.company.name, food: key === 'food', initialPage: 'operations' as const, exit: vi.fn() };
  const { unmount } = render(<PreviewBoundary {...props} />);
  expect(screen.getByRole('heading', { name: dataset.company.name })).toBeInTheDocument();
  const orders = dataset.groups.find(g => g.key === 'orders')!;
  const order = orders.records[0];
  fireEvent.click(screen.getByRole('button', { name: orders.label }));
  fireEvent.click(screen.getByRole('button', { name: new RegExp(order.code) }));
  fireEvent.click(screen.getByRole('button', { name: order.action + '至預覽' }));
  expect(screen.getByRole('status')).toHaveTextContent('未修改正式');
  const link = order.links[0];
  fireEvent.click(screen.getByRole('button', { name: new RegExp('查看' + link.code) }));
  expect(screen.getByRole('heading', { name: new RegExp(link.code) })).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: '文件' }));
  const doc = dataset.groups.find(g => g.key === 'documents')!.records[0];
  fireEvent.click(screen.getByRole('button', { name: new RegExp(doc.code) }));
  fireEvent.change(screen.getByRole('textbox'), { target: { value: '暫存變更' } });
  unmount(); render(<PreviewBoundary {...props} initialPage="documents" />);
  fireEvent.click(screen.getByRole('button', { name: new RegExp(doc.code) }));
  expect(screen.getByRole('textbox')).not.toHaveValue('暫存變更');
  for (const [otherKey, other] of Object.entries(data)) if (otherKey !== key) expect(screen.queryByRole('heading', { name: other.company.name })).not.toBeInTheDocument();
});

it('keeps the original food preview available and does not carry edits across companies', () => {
  const { rerender } = render(<PreviewBoundary companyKey="food" food companyName="毛研食品" initialPage="documents" exit={vi.fn()} />);
  fireEvent.click(screen.getByRole('button', { name: '查看原食品試產示例' }));
  expect(screen.getByRole('button', { name: /試產規格書/ })).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: '返回完整公司展示資料' }));
  fireEvent.click(screen.getByRole('button', { name: /MY-DOC-001/ }));
  fireEvent.change(screen.getByRole('textbox'), { target: { value: '毛研專屬暫存' } });
  rerender(<PreviewBoundary companyKey="software" food={false} companyName="雲序軟體" initialPage="documents" exit={vi.fn()} />);
  fireEvent.click(screen.getByRole('button', { name: /YS-DOC-001/ }));
  expect(screen.getByRole('textbox')).not.toHaveValue('毛研專屬暫存');
});
