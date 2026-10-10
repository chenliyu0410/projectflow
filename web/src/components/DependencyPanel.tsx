import { useEffect, useState } from 'react';
import {
  api,
  ApiError,
  recordError,
  useRequestScope,
  useRecordMutation,
} from '../api';
import type { RecordReload } from '../api';
import type { DependencyData, ProjectDetail } from '../types';
import { dependencyLabel } from '../dependencies';
import type { DependencySettings, ManualCondition } from '../types';
import DependencyGraph from './DependencyGraph';
import { subtree } from './NodeWorkspace';
export default function DependencyPanel({
  projectId,
  project,
  scopeId = null,
  select,
  reload,
  expired,
}: {
  projectId: string;
  project?: ProjectDetail;
  /** Like the Demo, a node's graph shows only the tasks below it; the list keeps edges touching them. */
  scopeId?: string | null;
  select: (id: string) => void;
  reload: RecordReload;
  expired: () => void;
}) {
  const scope = useRequestScope();
  const [data, setData] = useState<DependencyData | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [pre, setPre] = useState('');
  const [post, setPost] = useState('');
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<string | null>(null);
  const [settings, setSettings] = useState<DependencySettings>({relation_type: 'FS', lag_days: 0, enforcement: 'hard'});
  const [conditionNode, setConditionNode] = useState(scopeId ?? '');
  const [conditionLabel, setConditionLabel] = useState('');
  const [conditionStrength, setConditionStrength] = useState<'hard' | 'soft'>('hard');
  const [conditionEdit, setConditionEdit] = useState<ManualCondition | null>(null);
  const [confirming, setConfirming] = useState<ManualCondition | null>(null);
  const [reason, setReason] = useState('');
  const mutation = useRecordMutation(reload, expired);
  async function load() {
    const r = scope.begin();
    setLoading(true);
    setError('');
    try {
      const value = await api.dependencies(projectId, r.controller.signal);
      if (scope.current(r)) setData(value);
    } catch (e) {
      if (scope.current(r)) {
        if (e instanceof ApiError && e.status === 401) expired();
        else setError(recordError(e));
      }
    } finally {
      if (scope.current(r)) setLoading(false);
    }
  }
  useEffect(() => {
    void load();
  }, []);
  const below =
    scopeId && project && project.nodes.some((n) => n.id === scopeId && n.kind !== 'project')
      ? new Set(
          subtree(project.nodes, scopeId)
            .filter((n) => n.id !== scopeId)
            .map((n) => n.id),
        )
      : null;
  const touches = (id: string) => !below || below.has(id) || id === scopeId;
  const graphData =
    data && below
      ? { ...data, nodes: data.nodes.filter((n) => below.has(n.id)) }
      : data;
  const listed =
    data?.items.filter(
      (e) => touches(e.predecessor_id) || touches(e.successor_id),
    ) ?? [];
  return (
    <section className="dependency-panel" aria-label="前置設定">
      <div className="graph-tools">
        {data?.capabilities.manage && (
          <button
            aria-expanded={formOpen}
            disabled={loading || !!error}
            onClick={() => { setEditing(null); setFormOpen((value) => !value); }}
          >
            <span aria-hidden="true">＋ </span>建立相依連線
          </button>
        )}
        <span>
          FS完成→開始、SS開始→開始、FF完成→完成。延遲只影響計畫日期，負值表示提前；軟性僅警示，閘門獨立檢查。
        </span>
      </div>
      {loading && <p role="status">載入前置設定中</p>}
      {error && (
        <>
          <p role="alert">{error}</p>
          <button onClick={() => void load()}>重試前置讀取</button>
        </>
      )}
      {data && !loading && !error && (
        <>
          {mutation.error && <p role="alert">{mutation.error}</p>}
          {mutation.saved ? (
            <button
              disabled={mutation.busy}
              onClick={() => void mutation.execute()}
            >
              重試前置載入
            </button>
          ) : (
            data.capabilities.manage && formOpen && (
              <form
                className="record-panel dependency-form"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (pre && post && pre !== post)
                    void mutation.execute((signal) =>
                      editing ? api.updateDependency(editing, settings, signal) : api.addDependency(projectId, { predecessor_id: pre, successor_id: post, ...settings }, signal),
                    );
                }}
              >
                <label>
                  前置任務
                  <select
                    required
                    disabled={mutation.busy || !!editing}
                    aria-label="前置任務"
                    value={pre}
                    onChange={(e) => setPre(e.target.value)}
                  >
                    <option value="">選擇前置任務</option>
                    {data.nodes.map((n) => (
                      <option key={n.id} value={n.id}>
                        {n.title}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  後續任務
                  <select
                    required
                    disabled={mutation.busy || !!editing}
                    aria-label="後續任務"
                    value={post}
                    onChange={(e) => setPost(e.target.value)}
                  >
                    <option value="">選擇後續任務</option>
                    {data.nodes
                      .filter((n) => n.id !== pre)
                      .map((n) => (
                        <option key={n.id} value={n.id}>
                          {n.title}
                        </option>
                      ))}
                  </select>
                </label>
                <label>關係類型<select aria-label="關係類型" value={settings.relation_type} disabled={mutation.busy} onChange={e => setSettings({...settings, relation_type: e.target.value as 'FS' | 'SS' | 'FF'})}><option value="FS">FS 完成→開始</option><option value="SS">SS 開始→開始</option><option value="FF">FF 完成→完成</option></select></label>
                <label>延遲天數<input type="number" min={-365} max={365} step={1} required value={settings.lag_days} disabled={mutation.busy} onChange={e => setSettings({...settings, lag_days: Number(e.target.value)})}/></label>
                <label>強度<select aria-label="強度" value={settings.enforcement} disabled={mutation.busy} onChange={e => setSettings({...settings, enforcement: e.target.value as 'hard' | 'soft'})}><option value="hard">硬性</option><option value="soft">軟性</option></select></label>
                <button
                  disabled={
                    mutation.busy ||
                    !pre ||
                    !post ||
                    pre === post ||
                    (!editing && data.items.some(
                      (e) =>
                        e.predecessor_id === pre && e.successor_id === post,
                    ))
                  }
                >
                  {editing ? '儲存前置' : '新增前置'}
                </button>
                <button type="button" disabled={mutation.busy} onClick={() => setFormOpen(false)}>取消</button>
              </form>
            )
          )}
          <DependencyGraph data={graphData!} select={select} nodes={project?.nodes} connect={data.capabilities.manage && !mutation.busy && !mutation.saved ? (a, b) => { setPre(a); setPost(b); setEditing(null); setSettings({relation_type: 'FS', lag_days: 0, enforcement: 'hard'}); setFormOpen(true); } : undefined} />
          <details className="panel dependency-list">
            <summary>連線清單（{listed.length}）</summary>
            <h3>可見前置連線</h3>
            {listed.length === 0 ? (
              <p>目前沒有兩端皆可見的前置連線</p>
            ) : (
              <ul>
                {listed.map((e) => (
                  <li key={e.id}>
                    <span>
                      {data.nodes.find((n) => n.id === e.predecessor_id)?.title}{' '}
                      → {data.nodes.find((n) => n.id === e.successor_id)?.title} · {dependencyLabel(e)}
                    </span>
                    {data.capabilities.manage && <button disabled={mutation.busy || mutation.saved} aria-label={`編輯前置：${data.nodes.find(n => n.id === e.predecessor_id)?.title} → ${data.nodes.find(n => n.id === e.successor_id)?.title}`} onClick={() => { setEditing(e.id); setPre(e.predecessor_id); setPost(e.successor_id); setSettings({relation_type: e.relation_type ?? 'FS', lag_days: e.lag_days ?? 0, enforcement: e.enforcement ?? 'hard'}); setFormOpen(true); }}>編輯</button>}
                    {data.capabilities.manage && (
                      <button
                        disabled={mutation.busy || mutation.saved}
                        aria-label={`移除前置：${data.nodes.find((n) => n.id === e.predecessor_id)?.title} → ${data.nodes.find((n) => n.id === e.successor_id)?.title}`}
                        onClick={() =>
                          void mutation.execute((signal) =>
                            api.removeDependency(e.id, signal),
                          )
                        }
                      >
                        移除連線
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            )}
            {data.nodes
              .filter((n) => n.blocked && touches(n.id))
              .map((n) => (
                <p key={n.id}>
                  <button className="row-link" onClick={() => select(n.id)}>{n.title}</button>
                  ：尚有未完成的前置任務
                </p>
              ))}
          </details>
          <section className="panel" aria-label="人工確認條件">
            <h3>人工確認條件</h3><p>由管理者確認或撤回，僅限制開始；尚未串接ERP。</p>
            {(data.conditions ?? []).filter(c => touches(c.node_id)).map(c => <div className="condition-row" key={c.id}>
              <b>{data.nodes.find(n => n.id === c.node_id)?.title}：{c.label}</b>
              <span>{c.enforcement === 'soft' ? '軟性' : '硬性'} · {c.is_met ? '已確認' : '未確認'}</span>
              {c.reason && <p>最近理由：{c.reason} {c.confirmed_at && new Date(c.confirmed_at).toLocaleString()}</p>}
              {data.capabilities.manage && <><button disabled={mutation.busy || mutation.saved} onClick={() => {setConfirming(c); setReason('');}}>{c.is_met ? '撤回確認' : '確認條件'}</button><button disabled={mutation.busy || mutation.saved} onClick={() => {setConditionEdit(c); setConditionNode(c.node_id); setConditionLabel(c.label); setConditionStrength(c.enforcement);}}>編輯條件</button><button disabled={mutation.busy || mutation.saved} onClick={() => void mutation.execute(signal => api.removeCondition(c.id, signal))}>移除條件</button></>}
            </div>)}
            {data.capabilities.manage && !mutation.saved && <>
              {confirming && <form className="record-panel" onSubmit={e => {e.preventDefault(); if(reason.trim()) void mutation.execute(signal => api.confirmCondition(confirming.id, {is_met: !confirming.is_met, reason}, signal));}}><p>{confirming.is_met ? '撤回' : '確認'}：{confirming.label}</p><label>確認或撤回理由<input required maxLength={1000} value={reason} disabled={mutation.busy} onChange={e => setReason(e.target.value)}/></label><button disabled={mutation.busy || !reason.trim()}>儲存確認結果</button><button type="button" disabled={mutation.busy} onClick={() => setConfirming(null)}>取消確認</button></form>}
              <form className="record-panel dependency-form" onSubmit={e => {e.preventDefault(); if(conditionNode && conditionLabel.trim()) void mutation.execute(signal => conditionEdit ? api.updateCondition(conditionEdit.id, {label: conditionLabel, enforcement: conditionStrength}, signal) : api.addCondition(projectId, {node_id: conditionNode, label: conditionLabel, enforcement: conditionStrength}, signal));}}>
                <label>條件目標任務<select aria-label="條件目標任務" required disabled={mutation.busy || !!conditionEdit} value={conditionNode} onChange={e => setConditionNode(e.target.value)}><option value="">選擇任務</option>{data.nodes.map(n => <option key={n.id} value={n.id}>{n.title}</option>)}</select></label>
                <label>條件名稱<input required maxLength={200} disabled={mutation.busy} value={conditionLabel} onChange={e => setConditionLabel(e.target.value)}/></label>
                <label>條件強度<select aria-label="條件強度" disabled={mutation.busy} value={conditionStrength} onChange={e => setConditionStrength(e.target.value as 'hard' | 'soft')}><option value="hard">硬性</option><option value="soft">軟性</option></select></label>
                <button disabled={mutation.busy || !conditionNode || !conditionLabel.trim()}>{conditionEdit ? '儲存條件' : '新增人工條件'}</button>
                {conditionEdit && <button type="button" disabled={mutation.busy} onClick={() => {setConditionEdit(null); setConditionLabel('');}}>取消編輯條件</button>}
              </form>
            </>}
          </section>
        </>
      )}
    </section>
  );
}
