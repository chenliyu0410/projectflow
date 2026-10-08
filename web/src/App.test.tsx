import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import App from './App';

const good = () => Promise.resolve({ ok: true, json: async () => ({ ok: true, database: 'ready' }) });

describe('health surface', () => {
  it('shows loading until the response arrives', () => {
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {})));
    render(<App />);
    expect(screen.getByRole('status')).toHaveTextContent('檢查中');
    expect(screen.getByRole('button', { name: '重新檢查' })).toBeDisabled();
  });

  it('uses the proxy and displays verified readiness', async () => {
    const fetcher = vi.fn(good);
    vi.stubGlobal('fetch', fetcher);
    render(<App />);
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('已連線'));
    expect(fetcher).toHaveBeenCalledWith('/api/health/ready', expect.objectContaining({ signal: expect.any(AbortSignal) }));
  });

  it('supports retry after network failure', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValueOnce(new Error('private')).mockImplementation(good));
    render(<App />);
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('無法連線'));
    expect(screen.queryByText('private')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: '重新檢查' }));
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('已連線'));
  });

  it.each([
    { ok: false, json: async () => ({ ok: false, database: 'unavailable' }) },
    { ok: true, json: async () => ({ ok: true, database: 'unexpected' }) },
  ])('rejects non-ready responses', async response => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response));
    render(<App />);
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('無法連線'));
  });

  it('aborts the request on unmount', () => {
    const fetcher = vi.fn(() => new Promise(() => {}));
    vi.stubGlobal('fetch', fetcher);
    const { unmount } = render(<App />);
    const signal = (fetcher.mock.calls as unknown as [string, RequestInit][])[0][1].signal;
    unmount();
    expect(signal?.aborted).toBe(true);
  });
});
