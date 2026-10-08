import { useEffect, useState } from 'react';

export default function App() {
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<'loading' | 'ready' | 'error'>('loading');

  useEffect(() => {
    const controller = new AbortController();
    setState('loading');
    const timer = window.setTimeout(() => controller.abort(), 5000);
    let active = true;

    (async () => {
      try {
        const response = await fetch('/api/health/ready', { signal: controller.signal });
        if (!response.ok) throw new Error('unavailable');
        const value = await response.json();
        if (value.ok !== true || value.database !== 'ready') throw new Error('invalid');
        if (active) setState('ready');
      } catch {
        if (active) setState('error');
      } finally {
        window.clearTimeout(timer);
      }
    })();

    return () => {
      active = false;
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [attempt]);

  return <>
    <header>
      <img src="/mark.svg" width="32" height="32" alt="" />
      <strong>專流 ProjectFlow</strong>
      <span>系統狀態</span>
    </header>
    <main>
      <h1>服務狀態</h1>
      <section aria-label="連線狀態">
        <h2>API 與資料庫</h2>
        <p role="status" className={state}>
          {state === 'ready' ? '已連線' : state === 'error' ? '無法連線' : '檢查中'}
        </p>
        <button disabled={state === 'loading'} onClick={() => setAttempt(value => value + 1)}>
          重新檢查
        </button>
      </section>
    </main>
  </>;
}
