import { useEffect, useState } from 'react';
import { api, ApiError } from '../api';
import type { WeeklyItem, WeeklyReport, WeeklySections } from '../types';

const LISTS: [keyof Omit<WeeklySections, 'summary'>, string][] = [['highlights', '本週重點'], ['risks', '風險與卡關'], ['next', '下週重點']];
const COUNTS: [keyof WeeklyReport['facts']['counts'], string][] = [['completed', '完成'], ['pending_review', '待確認'], ['doing', '進行中'], ['due_next_week', '下週到期'], ['overdue', '逾期'], ['blocked', '卡住']];
const STATUS: Record<WeeklyReport['status'], string> = { draft: '草稿', sent: '已寄出', unsent: '未寄出' };

function message(error: unknown) {
  return error instanceof ApiError ? error.message : '操作失敗，請稍後再試';
}

function ItemList({ title, items }: { title: string; items: WeeklyItem[] }) {
  return <section aria-label={title}><h4>{title}（{items.length}）</h4>
    {items.length ? <ul>{items.map(item => <li key={item.ref}>[{item.ref}] {item.title}（{item.owner}）{item.due_date ? `・到期 ${item.due_date}` : ''}{item.result ? `・${item.result}` : ''}</li>)}</ul> : <p className="muted small">無</p>}
  </section>;
}

/** Project weekly report: owners/admins generate, edit and confirm; other manager roles read sent reports (D84). */
export default function WeeklyReportPanel({ projectId, expired }: { projectId: string; expired?: () => void }) {
  const [items, setItems] = useState<WeeklyReport[] | null>(null);
  const [canManage, setCanManage] = useState(false);
  const [draft, setDraft] = useState<WeeklySections | null>(null);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [version, setVersion] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setError('');
    api.weeklyReports(projectId, controller.signal).then(data => {
      setItems(data.items); setCanManage(data.can_manage);
      const current = data.items.find(item => item.status === 'draft');
      setDraft(current ? current.sections : null);
    }).catch(e => {
      if (controller.signal.aborted) return;
      if (e instanceof ApiError && e.status === 401) expired?.();
      else { setItems([]); setError(message(e)); }
    });
    return () => controller.abort();
  }, [projectId, version]);

  const current = items?.find(item => item.status === 'draft') ?? null;
  const latest = current ?? items?.[0] ?? null;

  async function run(label: string, action: () => Promise<string | void>) {
    setBusy(label); setError(''); setNotice('');
    try {
      const text = await action();
      if (text) setNotice(text);
      setVersion(value => value + 1);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) expired?.(); else setError(message(e));
    } finally { setBusy(''); }
  }

  const generate = () => run('generate', async () => { await api.generateWeeklyReport(projectId); return '已產生本週週報草稿'; });
  const save = () => current && draft && run('save', async () => { await api.saveWeeklyReport(current.id, draft); return '已儲存草稿'; });
  const confirm = () => {
    if (!current || !draft) return;
    if (!window.confirm(`確認後會寄給 ${current.recipients.length} 位收件人，寄出後不能再修改。要寄出嗎？`)) return;
    void run('confirm', async () => {
      const result = await api.confirmWeeklyReport(current.id, draft);
      return result.removed.length ? `已寄出；${result.removed.join('、')} 已停用或無法查看部分任務，未寄給他們` : '已確認寄出';
    });
  };
  const setList = (key: keyof Omit<WeeklySections, 'summary'>, text: string) => draft && setDraft({ ...draft, [key]: text.split('\n') });

  if (items === null) return <p className="muted">載入週報中…</p>;
  return <section className="weekly-report" aria-label="週報">
    <div className="weekly-head">
      <div><h3>專案週報</h3><p className="small muted">每週五 17:00 自動產生草稿，專案負責人確認後才會寄給管理角色；一般成員改收每日摘要。</p></div>
      {canManage && <button disabled={!!busy || current?.status === 'sent'} onClick={() => void generate()}>{busy === 'generate' ? '產生中…' : '立即產生草稿'}</button>}
    </div>
    {error && <p role="alert" className="error">{error}</p>}
    {notice && <p role="status" className="notice">{notice}</p>}
    {!latest && <p className="empty">本專案還沒有週報{canManage ? '，按「立即產生草稿」開始。' : '。'}</p>}
    {latest && <article className="panel weekly-body" aria-label={`週報 ${latest.week_start}`}>
      <p><span className="tag">AI 建議</span> <b>{latest.week_start} 起</b>　<span className="tag gray">{STATUS[latest.status]}</span>　<span className="small muted">撰寫方式：{latest.model_label}</span></p>
      {latest.excluded_count > 0 && <p className="small muted">有 {latest.excluded_count} 項因權限或機密等級未列入</p>}
      {current && canManage && draft ? <>
        <label>整體摘要<textarea rows={3} value={draft.summary} disabled={!!busy} onChange={event => setDraft({ ...draft, summary: event.target.value })} /></label>
        {LISTS.map(([key, label]) => <label key={key}>{label}（一行一點）<textarea rows={4} value={draft[key].join('\n')} disabled={!!busy} onChange={event => setList(key, event.target.value)} /></label>)}
        <div className="actions"><button disabled={!!busy} onClick={() => void save()}>{busy === 'save' ? '儲存中…' : '儲存'}</button>
          <button className="primary" disabled={!!busy} onClick={confirm}>{busy === 'confirm' ? '寄出中…' : `確認寄出（${current.recipients.length} 位）`}</button></div>
        <p className="small muted">收件人：{current.recipients.join('、') || '無'}</p>
      </> : <>
        <p>{latest.sections.summary}</p>
        {LISTS.map(([key, label]) => <div key={key}><h4>{label}</h4>{latest.sections[key].length ? <ul>{latest.sections[key].map((line, i) => <li key={i}>{line}</li>)}</ul> : <p className="muted small">無</p>}</div>)}
        {latest.confirmed_by && <p className="small muted">由 {latest.confirmed_by} 於 {latest.confirmed_at?.slice(0, 16).replace('T', ' ')} 確認寄出</p>}
      </>}
      <h4>數字（由系統計算，不能修改）</h4>
      <dl className="weekly-counts">{COUNTS.map(([key, label]) => <div key={key}><dt>{label}</dt><dd>{latest.facts.counts[key]}</dd></div>)}</dl>
      <div className="weekly-lists">
        <ItemList title="本週完成" items={latest.facts.completed} />
        <ItemList title="逾期" items={latest.facts.overdue} />
        <ItemList title="卡住" items={latest.facts.blocked} />
        <ItemList title="下週到期" items={latest.facts.due_next_week} />
      </div>
      <p className="small">本週未回報成員：{latest.facts.silent_members.join('、') || '無'}</p>
    </article>}
    {items.length > 1 && <section aria-label="歷史週報"><h4>歷史週報</h4><ul>{items.filter(item => item !== latest).map(item =>
      <li key={item.id}>{item.week_start} 起・{STATUS[item.status]}{item.confirmed_by ? `・${item.confirmed_by} 確認` : ''}</li>)}</ul></section>}
  </section>;
}
