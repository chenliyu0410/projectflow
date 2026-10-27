import { useState } from 'react';
import { ApiError, requestJson } from '../api';

/** Change one's own password; `forced` is the full-screen step after signing in with a temporary password. */
export default function ChangePassword({ forced = false, done, expired, logout }: { forced?: boolean; done: () => void; expired: () => void; logout?: () => void }) {
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [again, setAgain] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  async function submit() {
    setNotice('');
    if (next.length < 10) { setError('新密碼至少要 10 個字元'); return; }
    if (next !== again) { setError('兩次輸入的新密碼不一樣'); return; }
    setBusy(true); setError('');
    try {
      await requestJson('/auth/password', { method: 'POST', body: JSON.stringify({ current_password: current, new_password: next }) });
      setCurrent(''); setNext(''); setAgain('');
      if (forced) done(); else { setNotice('密碼已更新。其他裝置上的登入已經登出。'); done(); }
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) expired();
      else setError(e instanceof Error ? e.message : '修改密碼失敗，請稍後再試');
    } finally { setBusy(false); }
  }

  return <section className="panel change-password" aria-label="修改密碼">
    <h2>{forced ? '請先設定你自己的密碼' : '修改密碼'}</h2>
    {forced && <p>你現在用的是管理者給的臨時密碼。設定新密碼後才能開始使用。</p>}
    <p className="muted">新密碼至少 10 個字元，不能和帳號一樣，也不能用 demo- 開頭。</p>
    {error && <p role="alert">{error}</p>}{notice && <p role="status">{notice}</p>}
    <form onSubmit={e => { e.preventDefault(); void submit(); }}>
      <label>{forced ? '臨時密碼' : '目前密碼'}<input type="password" autoComplete="current-password" required maxLength={200} value={current} disabled={busy} onChange={e => setCurrent(e.target.value)} /></label>
      <label>新密碼<input type="password" autoComplete="new-password" required minLength={10} maxLength={200} value={next} disabled={busy} onChange={e => setNext(e.target.value)} /></label>
      <label>再輸入一次新密碼<input type="password" autoComplete="new-password" required maxLength={200} value={again} disabled={busy} onChange={e => setAgain(e.target.value)} /></label>
      <div className="record-actions">
        <button type="submit" disabled={busy}>{busy ? '儲存中…' : '儲存新密碼'}</button>
        {forced && logout && <button type="button" disabled={busy} onClick={logout}>登出</button>}
      </div>
    </form>
  </section>;
}
