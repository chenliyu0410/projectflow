import WorkflowCatalog from './WorkflowCatalog';
import { useEffect, useRef, useState } from 'react';
import {
  api,
  ApiError,
  recordError,
  useRequestScope,
  useRecordMutation,
} from '../api';
import type {
  WorkflowDetail,
  WorkflowList,
  WorkflowNode,
  WorkflowWrite,
} from '../types';
function Editor({
  detail,
  mode,
  saved,
  cancel,
  expired,
}: {
  detail: WorkflowDetail | null;
  mode: 'new' | 'edit' | 'copy';
  saved: (value: WorkflowDetail, signal: AbortSignal) => Promise<void>;
  cancel: () => void;
  expired: () => void;
}) {
  const [name, setName] = useState(
    mode === 'copy' ? `${detail?.name ?? ''} 複本` : (detail?.name ?? ''),
  );
  const [nodes, setNodes] = useState<WorkflowNode[]>(detail?.nodes ?? []);
  const [edges, setEdges] = useState(detail?.dependencies ?? []);
  const [pre, setPre] = useState('');
  const [post, setPost] = useState('');
  const savedId = useRef(detail?.id ?? '');
  const mutation = useRecordMutation(async (signal) => {
    const value = await api.workflow(savedId.current, signal);
    if (!signal.aborted) await saved(value, signal);
  }, expired);
  const tasks = nodes.filter((n) => n.kind === 'task');
  function add(kind: 'phase' | 'task') {
    setNodes((old) => [
      ...old,
      {
        id: crypto.randomUUID(),
        parent_id: null,
        kind,
        title: '',
        sort_order: old.length,
        gate_after: false,
        start_offset: null,
        due_offset: null,
      },
    ]);
  }
  function update(id: string, patch: Partial<WorkflowNode>) {
    setNodes((old) => old.map((n) => (n.id === id ? { ...n, ...patch } : n)));
  }
  function remove(id: string) {
    setNodes((old) =>
      old
        .filter((n) => n.id !== id)
        .map((n) => (n.parent_id === id ? { ...n, parent_id: null } : n)),
    );
    setEdges((old) =>
      old.filter((e) => e.predecessor_id !== id && e.successor_id !== id),
    );
  }
  function parents(node: WorkflowNode) {
    const blocked = new Set([node.id]);
    let changed = true;
    while (changed) {
      changed = false;
      for (const n of nodes)
        if (n.parent_id && blocked.has(n.parent_id) && !blocked.has(n.id)) {
          blocked.add(n.id);
          changed = true;
        }
    }
    return nodes.filter((n) => !blocked.has(n.id));
  }
  function submit() {
    if (!name.trim()) return;
    const payload: WorkflowWrite = {
      name: name.trim(),
      nodes: nodes.map((n) => ({ ...n, title: n.title.trim() })),
      dependencies: edges,
    };
    void mutation.execute(async (signal) => {
      const result =
        mode === 'copy'
          ? await api.copyWorkflow(detail!.id, name.trim(), signal)
          : await api.saveWorkflow(
              mode === 'edit' ? detail!.id : null,
              payload,
              signal,
            );
      savedId.current = result.id;
    });
  }
  return (
    <form
      className="workflow-editor record-panel"
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
      aria-label="模板表單"
    >
      <h3>
        {mode === 'new'
          ? '新增模板'
          : mode === 'copy'
            ? '複製模板'
            : '編輯模板'}
      </h3>
      {mutation.error && <p role="alert">{mutation.error}</p>}
      {mutation.saved ? (
        <button
          type="button"
          disabled={mutation.busy}
          onClick={() => void mutation.execute()}
        >
          重試模板載入
        </button>
      ) : (
        <>
          <fieldset disabled={mutation.busy}>
            <label>
              模板名稱
              <input
                required
                maxLength={160}
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </label>
            {mode === 'copy' ? (
              <p>將完整複製節點、日期偏移、閘門與前置設定；原模板保持不變。</p>
            ) : (
              <>
                <p>
                  相對日期以專案開始日為第 0
                  天，可留空。階段只能在頂層；任務可有多層父任務。
                </p>
                <div className="record-actions">
                  <button type="button" onClick={() => add('phase')}>
                    新增階段列
                  </button>
                  <button type="button" onClick={() => add('task')}>
                    新增任務列
                  </button>
                </div>
                {nodes.map((node, index) => (
                  <fieldset className="workflow-node" key={node.id}>
                    <legend>
                      {node.kind === 'phase' ? '階段' : '任務'} {index + 1}
                    </legend>
                    <label>
                      節點名稱
                      <input
                        aria-label={`節點名稱 ${index + 1}`}
                        required
                        maxLength={200}
                        value={node.title}
                        onChange={(e) =>
                          update(node.id, { title: e.target.value })
                        }
                      />
                    </label>
                    {node.kind === 'task' ? (
                      <label>
                        父節點
                        <select
                          aria-label={`父節點 ${index + 1}`}
                          value={node.parent_id ?? ''}
                          onChange={(e) =>
                            update(node.id, {
                              parent_id: e.target.value || null,
                            })
                          }
                        >
                          <option value="">頂層</option>
                          {parents(node).map((n) => (
                            <option key={n.id} value={n.id}>
                              {n.title ||
                                `未命名${n.kind === 'phase' ? '階段' : '任務'} ${nodes.indexOf(n) + 1}`}
                            </option>
                          ))}
                        </select>
                      </label>
                    ) : (
                      <p>頂層階段</p>
                    )}
                    <label>
                      排序
                      <input
                        aria-label={`排序 ${index + 1}`}
                        type="number"
                        min={0}
                        step={1}
                        required
                        value={node.sort_order}
                        onChange={(e) =>
                          update(node.id, {
                            sort_order: Number(e.target.value),
                          })
                        }
                      />
                    </label>
                    <label>
                      開始日偏移
                      <input
                        aria-label={`開始日偏移 ${index + 1}`}
                        type="number"
                        min={0}
                        step={1}
                        value={node.start_offset ?? ''}
                        onChange={(e) =>
                          update(node.id, {
                            start_offset:
                              e.target.value === ''
                                ? null
                                : Number(e.target.value),
                          })
                        }
                      />
                    </label>
                    <label>
                      截止日偏移
                      <input
                        aria-label={`截止日偏移 ${index + 1}`}
                        type="number"
                        min={node.start_offset ?? 0}
                        step={1}
                        value={node.due_offset ?? ''}
                        onChange={(e) =>
                          update(node.id, {
                            due_offset:
                              e.target.value === ''
                                ? null
                                : Number(e.target.value),
                          })
                        }
                      />
                    </label>
                    {node.kind === 'phase' && (
                      <label className="check-label">
                        <input
                          aria-label={`階段閘門 ${index + 1}`}
                          type="checkbox"
                          checked={node.gate_after}
                          onChange={(e) =>
                            update(node.id, { gate_after: e.target.checked })
                          }
                        />
                        階段結束設置閘門
                      </label>
                    )}
                    <button type="button" onClick={() => remove(node.id)}>
                      移除此列 {index + 1}
                    </button>
                  </fieldset>
                ))}
                {nodes.length === 0 && <p>尚未新增節點</p>}
                <fieldset className="workflow-edges">
                  <legend>任務前置（完成至開始，延遲 0 天）</legend>
                  <label>
                    前置任務
                    <select
                      value={pre}
                      onChange={(e) => setPre(e.target.value)}
                    >
                      <option value="">選擇前置任務</option>
                      {tasks.map((n) => (
                        <option key={n.id} value={n.id}>
                          {n.title || '未命名任務'}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    後續任務
                    <select
                      value={post}
                      onChange={(e) => setPost(e.target.value)}
                    >
                      <option value="">選擇後續任務</option>
                      {tasks
                        .filter((n) => n.id !== pre)
                        .map((n) => (
                          <option key={n.id} value={n.id}>
                            {n.title || '未命名任務'}
                          </option>
                        ))}
                    </select>
                  </label>
                  <button
                    type="button"
                    disabled={
                      !pre ||
                      !post ||
                      pre === post ||
                      edges.some(
                        (e) =>
                          e.predecessor_id === pre && e.successor_id === post,
                      )
                    }
                    onClick={() => {
                      setEdges((old) => [
                        ...old,
                        { predecessor_id: pre, successor_id: post },
                      ]);
                      setPre('');
                      setPost('');
                    }}
                  >
                    加入模板前置
                  </button>
                  <ul>
                    {edges.map((e, i) => (
                      <li key={`${e.predecessor_id}:${e.successor_id}`}>
                        {nodes.find((n) => n.id === e.predecessor_id)?.title ||
                          '未命名任務'}{' '}
                        →{' '}
                        {nodes.find((n) => n.id === e.successor_id)?.title ||
                          '未命名任務'}{' '}
                        <button
                          type="button"
                          onClick={() =>
                            setEdges((old) =>
                              old.filter((_, index) => index !== i),
                            )
                          }
                        >
                          移除前置 {i + 1}
                        </button>
                      </li>
                    ))}
                  </ul>
                </fieldset>
              </>
            )}
          </fieldset>
          <div className="record-actions">
            <button disabled={mutation.busy || !name.trim()}>
              {mode === 'copy' ? '建立複本' : '儲存模板'}
            </button>
            <button type="button" onClick={cancel}>
              取消模板編輯
            </button>
          </div>
        </>
      )}
    </form>
  );
}
export default function WorkflowLibrary({
  expired,
  changed,
}: {
  expired: () => void;
  changed: () => void;
}) {
  const [catalogOpen, setCatalogOpen] = useState(false);
  const scope = useRequestScope();
  const [list, setList] = useState<WorkflowList | null>(null);
  const [detail, setDetail] = useState<WorkflowDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState<string | null>(null);
  const [mode, setMode] = useState<'new' | 'edit' | 'copy' | null>(null);
  const [generation, setGeneration] = useState(0);
  async function load(id: string | null = null) {
    const r = scope.begin();
    setLoading(true);
    setError('');
    setSelected(id);
    setDetail(null);
    setMode(null);
    try {
      if (id) {
        const value = await api.workflow(id, r.controller.signal);
        if (scope.current(r)) setDetail(value);
      } else {
        const value = await api.workflows(r.controller.signal);
        if (scope.current(r)) setList(value);
      }
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
  function edit(next: 'new' | 'edit' | 'copy') {
    scope.begin();
    setError('');
    setLoading(false);
    setMode(next);
    setGeneration((v) => v + 1);
  }
  async function saved(value: WorkflowDetail, signal: AbortSignal) {
    const updated = await api.workflows(signal);
    if (signal.aborted) return;
    setList(updated);
    setDetail(value);
    setSelected(value.id);
    setMode(null);
    setCatalogOpen(false);
    changed();
  }
  return (
    <div className="workflow-library">
      <h1>模板庫</h1>
      <p>模板修改只影響之後建立的專案。複製會建立獨立模板。</p>
      <div className="library-tabs"><button aria-pressed={!catalogOpen} onClick={()=>setCatalogOpen(false)}>公司模板</button><button aria-pressed={catalogOpen} onClick={()=>{setMode(null);setCatalogOpen(true);}}>產業範本</button></div>
      {catalogOpen ? <WorkflowCatalog saved={saved} expired={expired}/> : <>
      {list?.capabilities?.create && (
        <button onClick={() => edit('new')}>新增模板</button>
      )}
      <div className="workflow-list" aria-label="模板清單">
        {list?.items.map((w) => (
          <article className="company-template-card" key={w.id}><button
            aria-pressed={selected === w.id}
            onClick={() => void load(w.id)}
          >
            {w.name}
            {w.requires_start_date ? ' · 含相對日期' : ''}
          </button>{w.phase_count !== undefined && <p className="catalog-counts">{w.phase_count} 階段 · {w.task_count} 任務</p>}{w.phase_titles && <p className="record-meta">{w.phase_titles.join(' → ')}</p>}</article>
        ))}
      </div>
      {loading && <p role="status">載入模板中</p>}
      {error && (
        <>
          <p role="alert">{error}</p>
          <button onClick={() => void load(selected)}>重試模板讀取</button>
        </>
      )}
      {list?.items.length === 0 && !loading && !error && <p>目前沒有模板</p>}
      {mode ? (
        <Editor
          key={`${selected}:${mode}:${generation}`}
          detail={mode === 'new' ? null : detail}
          mode={mode}
          expired={expired}
          saved={saved}
          cancel={() => setMode(null)}
        />
      ) : (
        detail &&
        !loading &&
        !error && (
          <section className="record-panel" aria-label="模板內容">
            <h3>{detail.name}</h3>
            <div className="record-actions">
              {detail.capabilities.edit && (
                <button onClick={() => edit('edit')}>編輯模板</button>
              )}
              {detail.capabilities.copy && (
                <button onClick={() => edit('copy')}>複製模板</button>
              )}
            </div>
            <p>
              {detail.requires_start_date
                ? '建立專案時需提供開始日'
                : '此模板沒有排程日期'}
            </p>
            <ol>
              {detail.nodes.map((n) => (
                <li key={n.id}>
                  <strong>{n.title}</strong> ·{' '}
                  {n.kind === 'phase' ? '階段' : '任務'}
                  {n.parent_id &&
                    ` · 父節點：${detail.nodes.find((p) => p.id === n.parent_id)?.title ?? '未設定'}`}{' '}
                  · 排序 {n.sort_order} · 第 {n.start_offset ?? '未設定'} 天至第{' '}
                  {n.due_offset ?? '未設定'} 天
                  {n.gate_after ? ' · 階段閘門' : ''}
                </li>
              ))}
            </ol>
            <h4>前置任務</h4>
            {detail.dependencies.length === 0 ? (
              <p>尚未設定前置</p>
            ) : (
              <ul>
                {detail.dependencies.map((e) => (
                  <li key={`${e.predecessor_id}:${e.successor_id}`}>
                    {detail.nodes.find((n) => n.id === e.predecessor_id)?.title}{' '}
                    → {detail.nodes.find((n) => n.id === e.successor_id)?.title}
                  </li>
                ))}
              </ul>
            )}
          </section>
        )
      )}
      </>}
    </div>
  );
}
