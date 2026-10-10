import { RequestReviews } from './CollaborationDialogs';
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
  const [notice, setNotice] = useState('');
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
      if (item.type === 'report') {
        const result = await api.reviewReport(
          item.id,
          decision,
          comments[item.id]?.trim() ?? '',
          r.controller.signal,
        );
        if (scope.current(r)) setNotice(result?.dependency_warnings?.length ? `${decision === 'approved' ? '已核准' : '已退回'}。${result.dependency_warnings.join('；')}` : '');
      } else await api.approveGate(item.id, r.controller.signal);
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
  const reports = items.filter((i) => i.type === 'report');
  const gates = items.filter((i) => i.type === 'gate');
  const count = (n: number) =>
    loading || (error && !items.length) ? '' : cursor ? `（已載入 ${n}）` : `（${n}）`;
  const empty = (kind: 'report' | 'gate') =>
    !loading && !error && !items.some((i) => i.type === kind) && (
      <p className="empty">
        {cursor
          ? '目前已載入的清單沒有此類審核'
          : kind === 'report'
            ? '目前沒有待審回報'
            : '目前沒有待核准閘門'}
      </p>
    );
  return (
    <div className="review-center">
      <div className="page-heading">
        <h1>審核中心</h1>
        <p className="page-description">
          完成回報與階段閘門。只列出目前可審核的項目；點任務名稱可開啟完整紀錄。所有決定都寫入稽核紀錄。
        </p>
      </div>
      {loading && <p role="status">載入審核清單中</p>}
      {error && <p role="alert">{error}</p>}
      {notice && <p role="status" className="note warn">{notice}</p>}
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
      <section className="review-section" aria-label="回報審核">
        <h2>待確認的完成回報{count(reports.length)}</h2>
        {reports.map((item) => (
          <article className="panel review-entry" key={`${item.type}:${item.id}`}>
            <div className="record-actions">
              <button
                className="review-node row-link"
                onClick={() => openNode(item.project_id, item.node_id)}
              >
                {item.node_title}
              </button>
              <span className="record-meta">{item.project_title}</span>
            </div>
            <p className="record-meta">
              {formatRecordTime(item.created_at)}
              {` · ${item.submitted_by_display_name ?? '未設定'} · v${item.version}`}
            </p>
            <p className="record-body">
              <span className="record-tag">{item.result}</span>{' '}
              {item.summary}
            </p>
            <p className="small muted">實際完成日：{item.finished_on ?? '未設定'}</p>
            {item.dependency_warnings?.map(w => <p className="note warn" key={w}>{w}</p>)}
            {item.capabilities.review_report && (
              <>
                <label>
                  審核意見（退回時必填）
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
                    className="primary"
                    disabled={busy || saved || loading}
                    onClick={() => void decide(item, 'approved')}
                  >
                    確認回報
                  </button>
                  <button
                    className="danger"
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
          </article>
        ))}
        {empty('report')}
      </section>
      <section className="review-section" aria-label="跳過申請">
        <RequestReviews expired={expired}/>
      </section>
      <section className="review-section" aria-label="閘門審核">
        <h2>待核准的階段閘門{count(gates.length)}</h2>
        {gates.length > 0 && (
          <div className="table-wrap">
            <table className="data-table review-gates">
              <thead>
                <tr><th>專案 / 階段</th><th>送出時間</th><th><span className="sr-only">操作</span></th></tr>
              </thead>
              <tbody>
                {gates.map((item) => (
                  <tr key={`${item.type}:${item.id}`}>
                    <td>
                      <span className="muted">{item.project_title} / </span>
                      <button
                        className="review-node row-link"
                        onClick={() => openNode(item.project_id, item.node_id)}
                      >
                        {item.node_title}
                      </button>
                    </td>
                    <td className="nowrap">{formatRecordTime(item.created_at)}</td>
                    <td>
                      {item.capabilities.approve_gate && (
                        <button
                          disabled={busy || saved || loading}
                          onClick={() => void decide(item, 'approved')}
                        >
                          核准閘門
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {empty('gate')}
      </section>
      {cursor && !saved && (
        <button disabled={loading || busy} onClick={() => void load(true)}>
          載入更多審核
        </button>
      )}
    </div>
  );
}
