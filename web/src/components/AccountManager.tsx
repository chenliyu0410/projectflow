import { useEffect, useRef, useState } from 'react';
import { ApiError, requestJson } from '../api';

type Account = { id: string; username: string; display_name: string; role: string; status: 'active' | 'disabled'; must_change_password: boolean; departments: string[]; last_login_at: string | null };
type Listing = { items: Account[]; roles: string[]; me: string };
export const ROLE_NAMES: Record<string, string> = { admin: '系統管理員', project_owner: '專案負責人', reviewer: '階段審核人', member: '成員', readonly: '唯讀' };

/** Company accounts for system administrators: add, rename, change role, disable and reset passwords. */
export default function AccountManager({ expired }: { expired: () => void }) {
  const [listing, setListing] = useState<Listing | null>(null);
  const [username, setUsername] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [role, setRole] = useState('member');
  const [secret, setSecret] = useState<{ who: string; password: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const inFlight = useRef(false);

  async function run(action: () => Promise<void>) {
    if (inFlight.current) return;
    inFlight.current = true; setBusy(true); setError('');
    try { await action(); }
    catch (e) { if (e instanceof ApiError && e.status === 401) expired(); else setError(e instanceof Error ? e.message : '帳號操作失敗，請稍後再試'); }
    finally { inFlight.current = false; setBusy(false); }
  }
  async function load() { setListing(await requestJson<Listing>('/accounts')); }
  useEffect(() => { void run(load); }, []);

  function create() {
    void run(async () => {
      const made = await requestJson<{ account: Account; temporary_password: string }>('/accounts', { method: 'POST', body: JSON.stringify({ username, display_name: displayName, role }) });
      setUsername(''); setDisplayName(''); setRole('member'); setNotice('');
      setSecret({ who: `${made.account.display_name}（${made.account.username}）`, password: made.temporary_password });
      await load();
    });
  }
  function change(account: Account, body: Partial<Pick<Account, 'role' | 'status'>>, message: string) {
    void run(async () => { await requestJson(`/accounts/${account.id}`, { method: 'PATCH', body: JSON.stringify(body) }); setSecret(null); setNotice(message); await load(); });
  }
  function reset(account: Account) {
    if (!window.confirm(`確定要重設「${account.display_name}」的密碼嗎？對方會被登出，要用新的臨時密碼登入。`)) return;
    void run(async () => {
      const value = await requestJson<{ temporary_password: string }>(`/accounts/${account.id}/reset-password`, { method: 'POST' });
      setNotice(''); setSecret({ who: `${account.display_name}（${account.username}）`, password: value.temporary_password }); await load();
    });
  }

  return <section className="panel account-manager" aria-label="帳號管理">
    <h2>帳號管理</h2>
    <p className="muted">新增同事的帳號後，系統會給一組臨時密碼，只顯示這一次。請交給本人，對方第一次登入時要改成自己的密碼。</p>
    {error && <p role="alert">{error}</p>}{notice && <p role="status">{notice}</p>}
    {secret && <div className="panel" role="status" aria-label="臨時密碼">
      <p><strong>{secret.who} 的臨時密碼：</strong></p>
      <p><code className="temporary-password" style={{ fontSize: '1.6rem', letterSpacing: '0.12em' }}>{secret.password}</code></p>
      <p className="muted">離開這個畫面後就看不到了，請現在抄下或交給本人。</p>
      <button type="button" onClick={() => setSecret(null)}>我已經記下了</button>
    </div>}
    <form className="report-field-editor" aria-label="新增帳號" onSubmit={e => { e.preventDefault(); create(); }}>
      <h3>新增帳號</h3>
      <label>帳號（登入用，英數字）<input aria-label="新帳號" required maxLength={40} value={username} disabled={busy} onChange={e => setUsername(e.target.value)} /></label>
      <label>顯示名稱<input aria-label="新帳號顯示名稱" required maxLength={120} value={displayName} disabled={busy} onChange={e => setDisplayName(e.target.value)} /></label>
      <label>角色<select aria-label="新帳號角色" value={role} disabled={busy} onChange={e => setRole(e.target.value)}>{(listing?.roles ?? Object.keys(ROLE_NAMES)).map(r => <option key={r} value={r}>{ROLE_NAMES[r] ?? r}</option>)}</select></label>
      <button type="submit" disabled={busy}>新增帳號</button>
    </form>
    {!listing ? <p>{busy ? '載入中…' : '尚未載入帳號'}</p> : <ul className="document-list account-list">{listing.items.map(a => {
      const self = a.id === listing.me;
      return <li key={a.id}>
        <strong>{a.display_name}</strong> <span>{a.username} · {ROLE_NAMES[a.role] ?? a.role}{a.departments.length ? ` · ${a.departments.join('、')}` : ''}{a.status === 'disabled' ? ' · 已停用' : ''}{a.must_change_password ? ' · 尚未改臨時密碼' : ''}{self ? ' · 你自己' : ''}</span>
        <p className="small muted">最後登入：{a.last_login_at ? new Date(a.last_login_at).toLocaleString('zh-TW') : '尚未登入'}</p>
        {!self && <div className="record-actions">
          <label>角色<select aria-label={`${a.username} 角色`} value={a.role} disabled={busy} onChange={e => change(a, { role: e.target.value }, `已把「${a.display_name}」改成${ROLE_NAMES[e.target.value] ?? e.target.value}`)}>{listing.roles.map(r => <option key={r} value={r}>{ROLE_NAMES[r] ?? r}</option>)}</select></label>
          {a.status === 'active'
            ? <button disabled={busy} onClick={() => { if (window.confirm(`確定停用「${a.display_name}」？對方會立刻登出，資料與紀錄都會保留。`)) change(a, { status: 'disabled' }, `已停用「${a.display_name}」`); }}>停用</button>
            : <button disabled={busy} onClick={() => change(a, { status: 'active' }, `已重新啟用「${a.display_name}」`)}>重新啟用</button>}
          <button disabled={busy} onClick={() => reset(a)}>重設密碼</button>
        </div>}
      </li>;
    })}</ul>}
  </section>;
}
