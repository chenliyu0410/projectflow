import { fireEvent, render, screen, within } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import PreviewBoundary from './components/PreviewBoundary';
import CopilotPanel from './components/CopilotPanel';
import { AI_ACTIONS } from './preview/fixtures';

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

it('six AI shortcuts, input, references and apply operate locally and escape text', () => {
  const fetch = vi.fn(); vi.stubGlobal('fetch', fetch);
  render(<CopilotPanel scope="正式專案（不讀取）" food open close={vi.fn()} />);
  for (const name of AI_ACTIONS) {
    fireEvent.click(screen.getByRole('button', { name }));
    if (name === '會議紀錄抽待辦') {
      fireEvent.change(screen.getByLabelText('會議紀錄（僅預覽）'), { target: { value: '請確認 <img src=x> 交期。其他文字。請安排送驗。' } });
      fireEvent.click(screen.getByRole('button', { name: '預覽待辦' }));
    }
  }
  const chat = within(screen.getByLabelText('示例對話紀錄'));
  for (const name of AI_ACTIONS) expect(chat.getByText(name, { exact: true })).toBeInTheDocument();
  expect(chat.getByText('請確認 <img src=x> 交期')).toBeInTheDocument();
  expect(document.querySelector('img')).toBeNull();
  expect(chat.getAllByText('結果詳情／引用與送出內容')).toHaveLength(6);
  for (const button of chat.getAllByRole('button', { name: '確認套用至預覽' })) fireEvent.click(button);
  expect(screen.getByLabelText('已套用預覽清單')).toHaveTextContent('品保：留樣送驗');
  expect(chat.getAllByRole('button', { name: '已套用至預覽' })).toHaveLength(3);
  fireEvent.change(screen.getByLabelText('詢問 AI'), { target: { value: '請分析風險' } });
  fireEvent.click(screen.getByRole('button', { name: '送出預覽問題' }));
  expect(chat.getAllByText('延遲風險分析', { exact: true })).toHaveLength(2);
  fireEvent.change(screen.getByLabelText('詢問 AI'), { target: { value: '明天天氣如何' } });
  fireEvent.click(screen.getByRole('button', { name: '送出預覽問題' }));
  expect(chat.getByText('尚未支援這個問題')).toBeInTheDocument();
  expect(fetch).not.toHaveBeenCalled();
});

it('other-company AI never returns food cost data', () => {
  render(<CopilotPanel scope="電子" companyName="電子公司" food={false} open close={vi.fn()} />);
  for (const name of AI_ACTIONS) fireEvent.click(screen.getByRole('button', { name }));
  expect(screen.queryByText(/100 元/)).toBeNull();
  expect(within(screen.getByLabelText('示例對話紀錄')).getAllByText(/電子公司尚未建立/)).toHaveLength(6);
});
