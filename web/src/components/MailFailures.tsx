import { useEffect, useState } from 'react';
import { api, ApiError } from '../api';

type Failure = { id: string; subject: string; recipient: string; attempts: number; last_error: string | null; created_at: string };

/** Admin view of mail that n8n gave up on after five attempts, with a resend button. */
export default function MailFailures({ expired }: { expired?: () => void }) {
  const [items, setItems] = useState<Failure[] | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState('');
  const [version, setVersion] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    api.failedMail(controller.signal).then(data => setItems(data.items))
      .catch(e => { if (controller.signal.aborted) return; if (e instanceof ApiError && e.status === 401) expired?.(); else { setItems([]); setError('無法載入寄送狀態'); } });
    return () => controller.abort();
  }, [version]);

  async function retry(id: string) {
    setBusy(id); setError('');
    try { await api.retryMail(id); setVersion(value => value + 1); }
    catch (e) { if (e instanceof ApiError && e.status === 401) expired?.(); else setError(e instanceof ApiError ? e.message : '重寄失敗'); }
    finally { setBusy(''); }
  }

  return <section className="panel" aria-label="寄送失敗的通知">
    <h3>寄送失敗的通知</h3>
    <p className="small muted">n8n 連續 5 次寄不出去的信會停在這裡；排除郵件伺服器問題後可以重寄。</p>
    {error && <p role="alert" className="error">{error}</p>}
    {items === null ? <p className="muted">載入中…</p> : items.length === 0 ? <p className="empty">目前沒有寄送失敗的信。</p>
      : <ul className="mail-failures">{items.map(item => <li key={item.id}>
        <div><b>{item.subject}</b><span className="small muted">　收件人：{item.recipient}・嘗試 {item.attempts} 次・{item.created_at.slice(0, 16).replace('T', ' ')}</span></div>
        {item.last_error && <div className="small muted">原因：{item.last_error}</div>}
        <button disabled={!!busy} onClick={() => void retry(item.id)}>{busy === item.id ? '處理中…' : '重寄'}</button>
      </li>)}</ul>}
  </section>;
}
