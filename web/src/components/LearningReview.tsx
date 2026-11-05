import { useEffect, useState } from 'react';
import { ai } from '../ai';
import type { LearnedPhrase, LearningAction } from '../ai';
import { ApiError } from '../api';

const STATES: Record<LearnedPhrase['status'], string> = { pending: '待審核', approved: '已上線', rejected: '已退回', disabled: '已停用' };

function outcome(item: LearnedPhrase, action: LearningAction) {
  if (action === 'reject') return `已退回「${item.phrase}」。`;
  if (action === 'disable') return `已停用「${item.phrase}」，同一句會回到給建議。`;
  return item.status === 'approved' ? `「${item.phrase}」已上線，之後同一句會直接查詢。` : `自動檢查沒有全過，「${item.phrase}」維持${STATES[item.status]}，原因見下方檢查結果。`;
}

function when(value: string | null) {
  return value ? new Date(value).toLocaleString('zh-TW') : '';
}

/** 使用者確認的問法：管理者在這裡審核＋測試、退回或停用。只有管理者讀得到清單，其他角色被拒（403）時整個區塊不顯示。 */
export default function LearningReview({ version = 0, expired }: { version?: number; expired?: () => void }) {
  const [data, setData] = useState<{ items: LearnedPhrase[]; pending: number } | null>(null);
  const [denied, setDenied] = useState(false);
  const [loadError, setLoadError] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const [reload, setReload] = useState(0);
  const [open, setOpen] = useState(true);
  // 登入失效交給外層回登入頁；沒有權限就整塊不顯示，兩種都不當成一般錯誤。
  function handled(e: unknown) {
    if (!(e instanceof ApiError)) return false;
    if (e.status === 401 && expired) { expired(); return true; }
    if (e.status === 403) { setDenied(true); return true; }
    return false;
  }
  useEffect(() => {
    const request = new AbortController();
    ai.learning(request.signal).then(value => { if (!request.signal.aborted) { setData(value); setLoadError(''); } }, e => {
      if (request.signal.aborted || handled(e)) return;
      setLoadError(e instanceof Error ? e.message : '無法載入使用者確認的問法。');
    });
    return () => request.abort();
  }, [version, reload]);
  async function review(item: LearnedPhrase, action: LearningAction) {
    if (busy) return;
    setBusy(true); setError(''); setNotice('');
    try { setNotice(outcome(await ai.reviewLearning(item.id, action), action)); }
    catch (e) { if (!handled(e)) setError(e instanceof Error ? e.message : '操作失敗，請稍後重試。'); }
    // 不論成功或被拒都重新讀一次，畫面才會和伺服器上的狀態一致。
    finally { setBusy(false); setReload(v => v + 1); }
  }
  if (denied || (!data && !loadError)) return null;
  return <details className="ai-learning" open={open} onToggle={e => setOpen(e.currentTarget.open)}>
    <summary>使用者確認的問法{data && `（${data.pending} 筆待審核）`}</summary>
    {loadError && <p role="alert" className="ai-error">{loadError}<button type="button" onClick={() => setReload(v => v + 1)}>重新載入</button></p>}
    {error && <p role="alert" className="ai-error">{error}</p>}
    {notice && <p role="status" className="copilot-example-note">{notice}</p>}
    {data && !data.items.length && <p className="copilot-example-note">目前沒有候選。使用者點資料分析的建議查詢、按「✓ 結果正確，記住這個問法」後，會出現在這裡。</p>}
    {data?.items.map(item => <article key={item.id} className="ai-learning-item" aria-label={`問法：${item.phrase}`}>
      <p className="ai-learning-head"><span>「{item.phrase}」→ {item.label}</span><span className={`ai-learning-state ${item.status}`}>{STATES[item.status]}</span></p>
      <p className="copilot-example-note">確認 {item.confirmations} 人{item.last_confirmed_at && `・最近確認 ${when(item.last_confirmed_at)}`}{item.checks && `・最近檢查 ${when(item.checks.ran_at)}`}</p>
      {item.checks && <ul className="ai-learning-checks" aria-label="自動檢查結果">{item.checks.items.map(c => <li key={c.code} className={c.ok ? 'ok' : 'failed'}><strong>{c.ok ? '✓' : '✕'} {c.title}</strong>：{c.message}{c.detail?.length ? `（${c.detail.join('、')}）` : ''}</li>)}</ul>}
      {item.status !== 'rejected' && <div className="ai-learning-actions">
        {(item.status === 'pending' || item.status === 'disabled') && <button type="button" disabled={busy} onClick={() => void review(item, 'approve')}>審核＋測試</button>}
        {item.status === 'pending' && <button type="button" disabled={busy} onClick={() => void review(item, 'reject')}>退回</button>}
        {item.status === 'approved' && <button type="button" disabled={busy} onClick={() => void review(item, 'disable')}>停用</button>}
      </div>}
    </article>)}
  </details>;
}
