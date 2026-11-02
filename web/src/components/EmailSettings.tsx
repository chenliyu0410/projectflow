import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { api, ApiError } from '../api';

/** Each user's own mail address and switch; empty email or switched off means site notifications only. */
export default function EmailSettings({ expired }: { expired?: () => void }) {
  const [email, setEmail] = useState('');
  const [notify, setNotify] = useState(true);
  const [loaded, setLoaded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    api.myEmail(controller.signal).then(data => { setEmail(data.email ?? ''); setNotify(data.email_notify); setLoaded(true); })
      .catch(e => { if (controller.signal.aborted) return; if (e instanceof ApiError && e.status === 401) expired?.(); else setError('無法載入 Email 設定'); });
    return () => controller.abort();
  }, []);

  async function save(event: FormEvent) {
    event.preventDefault();
    setBusy(true); setMessage(''); setError('');
    try {
      const data = await api.saveMyEmail(email.trim() || null, notify);
      setEmail(data.email ?? ''); setNotify(data.email_notify); setMessage('已儲存');
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) expired?.(); else setError(e instanceof ApiError ? e.message : '儲存失敗，請稍後再試');
    } finally { setBusy(false); }
  }

  return <section className="panel" aria-label="Email 通知">
    <h3>Email 通知</h3>
    <p className="small muted">站內通知、每日任務摘要和週報會寄到這個信箱。不填或關閉就只看站內通知。</p>
    <form onSubmit={event => void save(event)} className="email-settings">
      <label>Email<input type="email" value={email} disabled={!loaded || busy} onChange={event => setEmail(event.target.value)} placeholder="name@example.com" /></label>
      <label className="check"><input type="checkbox" checked={notify} disabled={!loaded || busy} onChange={event => setNotify(event.target.checked)} />接收 Email 通知</label>
      <button type="submit" disabled={!loaded || busy}>{busy ? '儲存中…' : '儲存 Email 設定'}</button>
    </form>
    {message && <p role="status">{message}</p>}
    {error && <p role="alert" className="error">{error}</p>}
  </section>;
}
