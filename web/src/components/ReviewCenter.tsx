import { useEffect, useRef, useState } from 'react';
import {
  api,
  ApiError,
  formatRecordTime,
  recordError,
  useRequestScope,
} from '../api';
import type { ReviewItem } from '../types';
export default function ReviewCenter({
  openNode,
  expired,
}: {
  openNode: (projectId: string, nodeId: string) => void;
  expired: () => void;
}) {
  const scope = useRequestScope();
  const locked = useRef(false);
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [comments, setComments] = useState<Record<string, string>>({});
  function failure(e: unknown) {
    if (e instanceof ApiError && e.status === 401) expired();
    else setError(recordError(e));
  }
  async function load(append = false) {
    if (locked.current) return;
    locked.current = true;
    const r = scope.begin();
    setLoading(true);
    setError('');
    try {
      const page = await api.reviews(
        append ? cursor : null,
        r.controller.signal,
      );
      if (!scope.current(r)) return;
      setItems((old) =>
        append
          ? [
              ...old,
              ...page.items.filter(
                (i) => !old.some((o) => o.type === i.type && o.id === i.id),
              ),
            ]
          : page.items,
      );
      setCursor(page.next_cursor);
      setSaved(false);
    } catch (e) {
      if (scope.current(r)) failure(e);
    } finally {
      if (scope.current(r)) {
        locked.current = false;
        setLoading(false);
      }
    }
  }
  useEffect(() => {
    void load();
  }, []);
  async function decide(item: ReviewItem, decision: 'approved' | 'rejected') {
    if (
      locked.current ||
      saved ||
      (decision === 'rejected' && !comments[item.id]?.trim())
    )
      return;
    locked.current = true;
    const r = scope.begin();
    setBusy(true);
    setError('');
    let committed = false;
    try {
      if (item.type === 'report')
        await api.reviewReport(
          item.id,
          decision,
          comments[item.id]?.trim() ?? '',
          r.controller.signal,
        );
      else await api.approveGate(item.id, r.controller.signal);
      if (!scope.current(r)) return;
      committed = true;
      setSaved(true);
      const page = await api.reviews(null, r.controller.signal);
      if (!scope.current(r)) return;
      setItems(page.items);
      setCursor(page.next_cursor);
      setSaved(false);
      setComments((old) => ({ ...old, [item.id]: '' }));
    } catch (e) {
      if (scope.current(r)) {
        if (e instanceof ApiError && e.status === 401) expired();
        else
          setError(committed ? '已儲存，審核清單重新載入失敗' : recordError(e));
      }
    } finally {
      if (scope.current(r)) {
        locked.current = false;
        setBusy(false);
      }
    }
  }
  return (
    <div className="review-center">
      <h2>審核中心</h2>
      <p>只列出目前可審核的回報與閘門；點選任務名稱可開啟完整紀錄。</p>
      {loading && <p role="status">載入審核清單中</p>}
      {error && <p role="alert">{error}</p>}
      {saved ? (
        <button disabled={busy || loading} onClick={() => void load()}>
          重試審核載入
        </button>
      ) : (
        error &&
        !busy && (
          <button disabled={loading} onClick={() => void load()}>
            重試審核讀取
          </button>
        )
      )}
      {(['report', 'gate'] as const).map((kind) => (
        <section
          className="record-panel"
          aria-label={kind === 'report' ? '回報審核' : '閘門審核'}
          key={kind}
        >
          <h3>{kind === 'report' ? '待確認回報' : '待核准閘門'}</h3>
          {items
            .filter((i) => i.type === kind)
            .map((item) => (
              <article className="review-entry" key={`${item.type}:${item.id}`}>
                <div className="record-actions">
                  <button
                    className="review-node"
                    onClick={() => openNode(item.project_id, item.node_id)}
                  >
                    {item.node_title}
                  </button>
                  <span className="record-meta">{item.project_title}</span>
                </div>
                <p className="record-meta">
                  {formatRecordTime(item.created_at)}
                  {item.type === 'report' &&
                    ` · ${item.submitted_by_display_name ?? '未設定'} · v${item.version}`}
                </p>
                {item.type === 'report' ? (
                  <>
                    <p className="record-body">
                      <span className="record-tag">{item.result}</span>{' '}
                      {item.summary}
                    </p>
                    <p>實際完成日：{item.finished_on ?? '未設定'}</p>
                    {item.capabilities.review_report && (
                      <>
                        <label>
                          審核意見
                          <textarea
                            aria-label={`審核意見：${item.node_title}`}
                            value={comments[item.id] ?? ''}
                            maxLength={2000}
                            disabled={busy || saved || loading}
                            onChange={(e) =>
                              setComments((old) => ({
                                ...old,
                                [item.id]: e.target.value,
                              }))
                            }
                          />
                        </label>
                        <div className="record-actions">
                          <button
                            disabled={busy || saved || loading}
                            onClick={() => void decide(item, 'approved')}
                          >
                            確認回報
                          </button>
                          <button
                            disabled={
                              busy ||
                              saved ||
                              loading ||
                              !comments[item.id]?.trim()
                            }
                            onClick={() => void decide(item, 'rejected')}
                          >
                            退回回報
                          </button>
                        </div>
                      </>
                    )}
                  </>
                ) : (
                  item.capabilities.approve_gate && (
                    <button
                      disabled={busy || saved || loading}
                      onClick={() => void decide(item, 'approved')}
                    >
                      核准閘門
                    </button>
                  )
                )}
              </article>
            ))}
          {!loading && !error && !items.some((i) => i.type === kind) && (
            <p>
              {cursor
                ? '目前已載入的清單沒有此類審核'
                : kind === 'report'
                  ? '目前沒有待審回報'
                  : '目前沒有待核准閘門'}
            </p>
          )}
        </section>
      ))}
      {cursor && !saved && (
        <button disabled={loading || busy} onClick={() => void load(true)}>
          載入更多審核
        </button>
      )}
    </div>
  );
}
