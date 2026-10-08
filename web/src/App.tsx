import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { api, ApiError } from './api';
import type { ProjectSummary, SessionInfo } from './types';

type State = 'checking-session' | 'login' | 'loading' | 'ready' | 'error';
export default function App() {
  const [state, setState] = useState<State>('checking-session');
  const [session, setSession] = useState<SessionInfo | null>(null);
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [organization, setOrganization] = useState('food');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const sequence = useRef(0);
  const controller = useRef<AbortController | null>(null);

  function begin() {
    controller.current?.abort();
    const request = { id: ++sequence.current, controller: new AbortController() };
    controller.current = request.controller;
    return request;
  }
  function current(request: ReturnType<typeof begin>) {
    return request.id === sequence.current && !request.controller.signal.aborted;
  }
  function clearSession() {
    setSession(null); setProjects([]); setSelectedId(null); setPassword(''); setState('login');
  }
  function failed(error: unknown, request: ReturnType<typeof begin>, loginFailure = false) {
    if (!current(request)) return;
    if (error instanceof ApiError && error.status === 401) clearSession();
    else setState(loginFailure ? 'login' : 'error');
    setMessage(error instanceof ApiError ? error.message : '操作失敗，請稍後再試');
  }
  async function loadProjects(request: ReturnType<typeof begin>, value: SessionInfo) {
    if (!current(request)) return;
    setSession(value); setState('loading');
    const result = await api.projects(request.controller.signal);
    if (!current(request)) return;
    setProjects(result.items); setSelectedId(result.items[0]?.id ?? null); setState('ready');
  }
  async function restore() {
    const request = begin();
    setMessage(''); setState('checking-session');
    try { await loadProjects(request, await api.me(request.controller.signal)); }
    catch (error) { failed(error, request); }
  }
  useEffect(() => {
    void restore();
    return () => { ++sequence.current; controller.current?.abort(); };
    // Session checking runs once per mount; cleanup invalidates even non-abortable responses.
  }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    const request = begin();
    setBusy(true); setMessage('');
    const payload = { organization_key: organization, username, password };
    setPassword('');
    let authenticated = false;
    try {
      const value = await api.login(payload, request.controller.signal);
      authenticated = true;
      await loadProjects(request, value);
    }
    catch (error) { failed(error, request, !authenticated); }
    finally { if (current(request)) setBusy(false); }
  }
  async function logout() {
    if (busy) return;
    const request = begin();
    setBusy(true); setMessage('');
    try {
      await api.logout(request.controller.signal);
      if (current(request)) clearSession();
    } catch (error) { failed(error, request); }
    finally { if (current(request)) setBusy(false); }
  }

  return <>
    <header>
      <img src="/mark.svg" width="32" height="32" alt="" />
      <strong>專流 ProjectFlow</strong>
      {session && <div className="session"><span aria-label="目前公司">{session.organization.name}</span><span>{session.user.display_name}</span><button disabled={busy} onClick={() => void logout()}>登出</button></div>}
    </header>
    <main className={session ? 'app-shell' : 'login-shell'}>
      {message && <p role="alert">{message}</p>}
      {state === 'login' ? <form onSubmit={event => void submit(event)}>
        <h1>登入專流</h1>
        <label>公司<input value={organization} onChange={event => setOrganization(event.target.value)} required disabled={busy} autoComplete="organization" /></label>
        <label>帳號<input value={username} onChange={event => setUsername(event.target.value)} required disabled={busy} autoComplete="username" /></label>
        <label>密碼<input type="password" value={password} onChange={event => setPassword(event.target.value)} required disabled={busy} autoComplete="current-password" /></label>
        <button type="submit" disabled={busy}>{busy ? '登入中' : '登入'}</button>
      </form> : <>
        {session && <aside aria-label="專案清單"><h1>專案</h1>{projects.map(project => <button key={project.id} aria-pressed={project.id === selectedId} onClick={() => setSelectedId(project.id)}>{project.title}</button>)}</aside>}
        <section aria-label="專案">
          {state === 'checking-session' && <p role="status">確認登入狀態中</p>}
          {state === 'loading' && <p role="status">載入專案中</p>}
          {state === 'ready' && projects.length === 0 && <p>目前沒有專案</p>}
          {state === 'error' && <button disabled={busy} onClick={() => void restore()}>重試</button>}
        </section>
      </>}
    </main>
  </>;
}
