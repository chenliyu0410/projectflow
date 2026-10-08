import { useEffect, useState } from 'react';
import {
  api,
  ApiError,
  recordError,
  useRequestScope,
  useRecordMutation,
} from '../api';
import type { RecordReload } from '../api';
import type { DependencyData } from '../types';
import DependencyGraph from './DependencyGraph';
export default function DependencyPanel({
  projectId,
  select,
  reload,
  expired,
}: {
  projectId: string;
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
  return (
    <section className="dependency-panel" aria-label="前置設定">
      <h2>前置相依</h2>
      <p>
        只管理同專案任務的完成至開始前置，延遲為 0
        天。移除連線不會刪除任務；閘門仍獨立檢查。
      </p>
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
            data.capabilities.manage && (
              <form
                className="record-panel dependency-form"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (pre && post && pre !== post)
                    void mutation.execute((signal) =>
                      api.addDependency(
                        projectId,
                        { predecessor_id: pre, successor_id: post },
                        signal,
                      ),
                    );
                }}
              >
                <label>
                  前置任務
                  <select
                    required
                    disabled={mutation.busy}
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
                    disabled={mutation.busy}
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
                <button
                  disabled={
                    mutation.busy ||
                    !pre ||
                    !post ||
                    pre === post ||
                    data.items.some(
                      (e) =>
                        e.predecessor_id === pre && e.successor_id === post,
                    )
                  }
                >
                  新增前置
                </button>
              </form>
            )
          )}
          <div className="record-panel">
            <h3>可見前置連線</h3>
            {data.items.length === 0 ? (
              <p>目前沒有兩端皆可見的前置連線</p>
            ) : (
              <ul>
                {data.items.map((e) => (
                  <li key={e.id}>
                    <span>
                      {data.nodes.find((n) => n.id === e.predecessor_id)?.title}{' '}
                      → {data.nodes.find((n) => n.id === e.successor_id)?.title}
                    </span>
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
          </div>
          {data.nodes
            .filter((n) => n.blocked)
            .map((n) => (
              <p key={n.id}>
                <button onClick={() => select(n.id)}>{n.title}</button>
                ：尚有未完成的前置任務
              </p>
            ))}
          <DependencyGraph data={data} select={select} />
        </>
      )}
    </section>
  );
}
