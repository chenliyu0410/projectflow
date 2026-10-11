import { fireEvent, render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import PreviewBoundary from './components/PreviewBoundary';

it('keeps version edits and receipt only during the preview; no storage or network writes', () => {
  const fetch = vi.fn(); vi.stubGlobal('fetch', fetch);
  const storage = vi.spyOn(Storage.prototype, 'setItem');
  const view = render(<PreviewBoundary initialPage="documents" food companyName="食品" exit={vi.fn()} />);
  fireEvent.click(screen.getByRole('button', { name: /試產規格書/ }));
  fireEvent.change(screen.getByLabelText('示例版本'), { target: { value: '0' } });
  expect(screen.getByText(/規劃試產 200 罐/)).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('示例版本'), { target: { value: '1' } });
  fireEvent.click(screen.getByRole('button', { name: '編輯文字預覽' }));
  fireEvent.change(screen.getByLabelText('文件文字'), { target: { value: '<script>private</script> 暫存' } });
  fireEvent.click(screen.getByRole('button', { name: '套用至預覽' }));
  expect(screen.getByText('<script>private</script> 暫存')).toBeInTheDocument();
  expect(document.querySelector('script')).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: '關聯資料示例' }));
  fireEvent.click(screen.getByRole('button', { name: '查看採購詳情' }));
  fireEvent.click(screen.getByRole('button', { name: '模擬收貨（僅預覽）' }));
  fireEvent.click(screen.getByRole('button', { name: '查看關聯工單' }));
  expect(screen.getAllByText('原料到位，待包材確認').length).toBeGreaterThan(0);
  fireEvent.click(screen.getByRole('button', { name: '文件示例' }));
  fireEvent.click(screen.getByRole('button', { name: /試產規格書/ }));
  expect(screen.getByText('<script>private</script> 暫存')).toBeInTheDocument();
  view.unmount();
  render(<PreviewBoundary initialPage="documents" food companyName="食品" exit={vi.fn()} />);
  fireEvent.click(screen.getByRole('button', { name: /試產規格書/ }));
  expect(screen.queryByText('<script>private</script> 暫存')).toBeNull();
  expect(fetch).not.toHaveBeenCalled(); expect(storage).not.toHaveBeenCalled();
  storage.mockRestore();
});

it('does not show food fixtures for other companies in any preview', () => {
  render(<PreviewBoundary initialPage="documents" food={false} companyName="電子公司" exit={vi.fn()} />);
  for (const name of ['文件示例', '關聯資料示例', '營運示例', 'AI 政策示例']) {
    fireEvent.click(screen.getByRole('button', { name }));
    expect(screen.getByText(/電子公司尚未建立此類展示示例/)).toBeInTheDocument();
    expect(screen.queryByText(/青禾原料/)).toBeNull();
  }
});
