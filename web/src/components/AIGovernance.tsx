import { useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { ai } from '../ai';
import type { ClassifiedItem, Governance, Level } from '../ai';
import { ApiError } from '../api';

export const LEVEL_LABEL: Record<Level, string> = { public: '公開', internal: '內部', confidential: '機密' };
const LEVELS: Level[] = ['public', 'internal', 'confidential'];
const RANK: Record<Level, number> = { public: 0, internal: 1, confidential: 2 };
const MODE_LABEL: Record<Governance['mode'], string> = { local_only: '全本地', mixed: '混合', cloud_allowed: '允許雲端' };
const ACTION_LABEL: Record<string, string> = { 'ai.query': 'AI 查詢', 'ai.preview': '模型資料預覽', 'ai.index.refresh': '更新文件索引', 'ai.classification.set': '調整分級', 'ai.policy.set': '變更 AI 政策' };
const CLOUD_REASON: Record<string, string> = { policy_local_only: '政策為全本地', confidential_local_only: '含機密資料，只能本地', no_cloud_provider: '可遮罩後送雲端，但未設定雲端供應商，未送出' };

function route(mode: Governance['mode'], level: Level) {
  if (mode === 'local_only') return '只用本地模型';
  if (level === 'confidential') return '只用本地模型（機密整份不送雲端）';
  return level === 'public' ? '可直接送雲端' : '遮罩後才可送雲端';
}

function LevelSelect({ item, change, busy }: { item: ClassifiedItem; change: (item: ClassifiedItem, level: Level | 'inherit') => void; busy: boolean }) {
  return <select aria-label={`${item.title} 的分級`} value={item.own ?? 'inherit'} disabled={busy} onChange={e => change(item, e.target.value as Level | 'inherit')}>
    <option value="inherit">繼承（{LEVEL_LABEL[item.inherited]}）</option>
    {LEVELS.map(level => <option key={level} value={level} disabled={RANK[level] < RANK[item.inherited]}>{LEVEL_LABEL[level]}</option>)}
  </select>;
}

export default function AIGovernance({ fallback, expired }: { fallback: ReactNode; expired: () => void }) {
  const [data, setData] = useState<Governance | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [mode, setMode] = useState<Governance['mode']>('local_only');
  const [project, setProject] = useState('');
  const [sample, setSample] = useState('鮪魚 62%、雞肉 18%，每公斤成本 NT$185，供應商聯絡 02-2345-6789。');
  const [masked, setMasked] = useState<{ masked: string; counts: Record<string, number> } | null>(null);
  const [reload, setReload] = useState(0);
  const controller = useRef<AbortController | null>(null);
  const expiredRef = useRef(expired);
  expiredRef.current = expired;

  useEffect(() => {
    const request = new AbortController();
    ai.governance(request.signal).then(value => {
      if (request.signal.aborted) return;
      setData(value); setMode(value.mode); setProject(current => current || value.projects[0]?.id || '');
    }).catch(e => {
      if (request.signal.aborted) return;
      if (e instanceof ApiError && e.status === 401) expiredRef.current();
      else if (e instanceof ApiError && (e.status === 403 || e.status === 404)) setUnavailable(true);
      else setError(e instanceof Error ? e.message : '無法載入 AI 政策');
    });
    return () => request.abort();
  }, [reload]);
  useEffect(() => () => controller.current?.abort(), []);

  async function run(action: (signal: AbortSignal) => Promise<unknown>) {
    controller.current?.abort();
    const request = new AbortController(); controller.current = request;
    setBusy(true); setError('');
    try { await action(request.signal); if (!request.signal.aborted) setReload(v => v + 1); }
    catch (e) { if (!request.signal.aborted) setError(e instanceof Error ? e.message : '儲存失敗，請重試。'); }
    finally { if (!request.signal.aborted) setBusy(false); }
  }
  const change = (item: ClassifiedItem, level: Level | 'inherit') => void run(signal => ai.classify({ scope: item.scope, id: item.id, level }, signal));

  if (unavailable) return <>{fallback}</>;
  if (!data) return error ? <p role="alert">{error}<button onClick={() => setReload(v => v + 1)}>重新載入</button></p> : <p role="status">載入 AI 政策中</p>;
  const nodes = data.nodes.filter(n => n.project_id === project);
  const depth = (node: ClassifiedItem) => { let level = 0, parent = node.parent_id; const byId = new Map(nodes.map(n => [n.id, n])); while (parent && byId.has(parent) && level < 10) { level += 1; parent = byId.get(parent)!.parent_id; } return level; };
  const documents = data.documents.filter(d => d.project_id === project);
  const selected = data.projects.find(p => p.id === project);

  return <section aria-label="AI 政策與稽核" className="ai-governance">
    <h2>AI 政策與稽核</h2>
    <p>隔離試用環境的真實設定。雲端供應商：<strong>未設定</strong>，任何政策下都不會送出雲端請求；機密資料一律只用本地模型。</p>
    {error && <p role="alert" className="ai-error">{error}</p>}
    <div className="preview-grid">
      <article className="preview-detail"><h3>公司 AI 政策</h3>
        <label>政策<select aria-label="公司 AI 政策" value={mode} disabled={busy || !data.can_set_policy} onChange={e => setMode(e.target.value as Governance['mode'])}>{(Object.keys(MODE_LABEL) as Governance['mode'][]).map(m => <option key={m} value={m}>{MODE_LABEL[m]}</option>)}</select></label>
        <button disabled={busy || !data.can_set_policy || mode === data.mode} onClick={() => void run(signal => ai.setPolicy(mode, signal))}>儲存政策</button>
        {!data.can_set_policy && <p>只有在本機登入的管理者可以變更政策。</p>}
        <dl>{LEVELS.map(level => <div key={level}><dt>{LEVEL_LABEL[level]}</dt><dd>{route(mode, level)}</dd></div>)}</dl>
      </article>
      <article className="preview-detail"><h3>公司預設等級</h3>
        <p>正式文件與附件從公司、專案、節點一路繼承，下層只能比上層更嚴格。</p>
        <label>公司預設<select aria-label="公司預設等級" value={data.company} disabled={busy} onChange={e => void run(signal => ai.classify({ scope: 'company', level: e.target.value as Level }, signal))}>{LEVELS.map(level => <option key={level} value={level}>{LEVEL_LABEL[level]}</option>)}</select></label>
      </article>
    </div>
    <article className="preview-detail"><h3>專案、節點與文件分級</h3>
      <label>專案<select aria-label="分級專案" value={project} onChange={e => setProject(e.target.value)}>{data.projects.map(p => <option key={p.id} value={p.id}>{p.title}</option>)}</select></label>
      {selected && <div className="ai-table-scroll" tabIndex={0} aria-label="分級清單"><table><thead><tr><th>項目</th><th>自身設定</th><th>實際等級</th></tr></thead><tbody>
        <tr><td><strong>{selected.title}</strong>（專案）</td><td><LevelSelect item={selected} change={change} busy={busy} /></td><td>{LEVEL_LABEL[selected.effective]}</td></tr>
        {nodes.map(n => <tr key={n.id}><td style={{ paddingLeft: 8 + depth(n) * 14 }}>{n.title}</td><td><LevelSelect item={n} change={change} busy={busy} /></td><td>{LEVEL_LABEL[n.effective]}</td></tr>)}
        {documents.map(d => <tr key={d.id}><td>📄 {d.title}</td><td><LevelSelect item={d} change={change} busy={busy} /></td><td>{LEVEL_LABEL[d.effective]}</td></tr>)}
      </tbody></table></div>}
      <p>附件跟隨所在節點的等級。調整等級不會重建索引，下一次查詢就會套用。</p>
    </article>
    <article className="preview-detail"><h3>遮罩測試</h3>
      <p>只在本機做規則遮罩，不呼叫模型、不保存；對照表不會顯示或送出。</p>
      <label className="sr-only" htmlFor="mask-sample">要遮罩的文字</label>
      <textarea id="mask-sample" maxLength={4000} rows={3} value={sample} onChange={e => { setSample(e.target.value); setMasked(null); }} />
      <button disabled={busy || !sample.trim()} onClick={() => void run(async signal => { const value = await ai.maskPreview(sample, signal); if (!signal.aborted) setMasked(value); })}>測試遮罩</button>
      {masked && <><pre style={{ whiteSpace: 'pre-wrap' }}>{masked.masked}</pre><p>{Object.entries(masked.counts).map(([kind, count]) => `${kind} ${count} 個`).join('、') || '沒有偵測到需遮罩的內容'}</p></>}
    </article>
    <article className="preview-detail"><h3>最近 AI 稽核紀錄</h3>
      <p>只記錄處理方式與等級，不記錄問題原文、文件內容或遮罩對照表。</p>
      {data.recent.length ? <ul>{data.recent.map((r, i) => <li key={i}>{new Date(r.created_at).toLocaleString('zh-TW')}・{ACTION_LABEL[r.action] ?? r.action}
        {r.classification && `・資料等級 ${LEVEL_LABEL[r.classification]}`}{r.cloud && `・${CLOUD_REASON[r.cloud.reason] ?? r.cloud.reason}`}
        {r.action === 'ai.classification.set' && `・${r.scope}：${r.from ? LEVEL_LABEL[r.from as Level] ?? r.from : '繼承'} → ${r.to === 'inherit' ? '繼承' : LEVEL_LABEL[r.to as Level] ?? r.to}`}
        {r.action === 'ai.policy.set' && `・${MODE_LABEL[r.from as Governance['mode']] ?? r.from} → ${MODE_LABEL[r.to as Governance['mode']] ?? r.to}`}</li>)}</ul> : <p>尚無紀錄。</p>}
    </article>
  </section>;
}
