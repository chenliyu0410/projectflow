import { useEffect, useRef, useState } from 'react';
import {
  api,
  formatRecordTime,
  ApiError,
  recordError,
  useRequestScope,
  useRecordMutation,
} from '../api';
import type { RecordReload } from '../api';
import type { NodeItem, Report } from '../types';
import { AttachmentUpload } from './AttachmentList';
export function ReportSummary({ report, compact = false }: { report: Report; compact?: boolean }) {
  return (
    <article className={compact ? 'report-history compact' : 'report-history'}>
      <h4 className={compact ? 'sr-only' : undefined}>
        {report.legacy
          ? '歷史回報（未納入新審核流程）'
          : `v${report.version} · ${report.status === 'submitted' ? '等待確認' : report.status === 'approved' ? '已確認' : '已退回'}`}
      </h4>
      <p className="record-body">
        <span className="record-tag">{report.result}</span> {report.summary}
      </p>
      <p className="record-meta">
        實際完成日：{report.finished_on ?? '未設定'} ·{' '}
        {report.submitted_by_display_name ?? '未設定'} 送出 ·{' '}
        {formatRecordTime(report.submitted_at)}
      </p>
      {report.reviewed_at && (
        <p className="record-meta">
          {report.self_approved ? '自行確認' : '審核'}：
          {report.reviewed_by_display_name ?? '未設定'} ·{' '}
          {formatRecordTime(report.reviewed_at)}
        </p>
      )}
      {report.review_comment && (
        <p className="record-comment">審核意見：{report.review_comment}</p>
      )}
    </article>
  );
}
export default function ReportPanel({
  node,
  userId,
  reload,
  expired,
}: {
  node: NodeItem;
  userId: string;
  reload: RecordReload;
  expired: () => void;
}) {
  const scope = useRequestScope();
  const mutation = useRecordMutation(reload, expired);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [latest, setLatest] = useState<Report | null>(null);
  const [summary, setSummary] = useState('');
  const [result, setResult] = useState('達成');
  const [date, setDate] = useState('');
  const [ids, setIds] = useState<string[]>([]);
  const [ready, setReady] = useState(true);
  const [comment, setComment] = useState('');
  const [action, setAction] = useState('');
  const [reason, setReason] = useState('');
  const [formOpen, setFormOpen] = useState(false);
  const trigger = useRef<HTMLButtonElement | null>(null);
  const reopen = useRef(false);
  async function load() {
    const request = scope.begin();
    setLoading(true);
    setError('');
    let candidate: Report | null = null;
    let legacy: Report | null = null;
    let cursor: string | null = null;
    const seen = new Set<string>();
    try {
      do {
        const page = await api.records(
          node.id,
          'self',
          cursor,
          100,
          request.controller.signal,
        );
        if (!scope.current(request)) return;
        for (const item of page.items) {
          if (item.type !== 'report') continue;
          if (item.legacy) legacy = item;
          else if (!candidate || item.version > candidate.version)
            candidate = item;
        }
        cursor = page.next_cursor;
        if (cursor) {
          if (seen.has(cursor)) throw Error('cursor');
          seen.add(cursor);
        }
      } while (cursor);
      setLatest(candidate ?? legacy);
      if (candidate?.status === 'rejected') {
        setSummary(candidate.summary);
        setDate(candidate.finished_on ?? '');
        setResult(
          ['達成', '部分達成', '未達成'].includes(candidate.result)
            ? candidate.result
            : '達成',
        );
      }
    } catch (e) {
      if (scope.current(request)) {
        if (e instanceof ApiError && e.status === 401) expired();
        else setError(recordError(e));
      }
    } finally {
      if (scope.current(request)) setLoading(false);
    }
  }
  useEffect(() => {
    void load();
  }, []);
  const actions = node.state_actions ?? [];
  const canSubmit =
    !!node.capabilities?.submit_report && actions.includes('submit_report');
  const canReview =
    !!node.capabilities?.review_report &&
    latest &&
    !latest.legacy &&
    latest.status === 'submitted' &&
    node.status === 'review' &&
    latest.submitted_by !== userId;
  const pending = !!latest && !latest.legacy && latest.status === 'submitted';
  const rejected = !!latest && !latest.legacy && latest.status === 'rejected';
  const tone = node.status === 'skipped' ? 'skip' : pending ? 'pending' : rejected ? 'rejected' : '';
  const title = loading ? '載入回報狀態中' : error ? '無法載入回報狀態'
    : pending ? `v${latest?.version} 等待確認` : rejected ? `v${latest?.version} 已退回`
      : node.status === 'done' ? '已完成' : node.status === 'skipped' ? '已略過' : '完成回報';
  const mark = !loading && !error && !pending && !rejected ? (node.status === 'done' ? '✓ ' : node.status === 'skipped' ? '⤳ ' : '') : '';
  function submit(self: boolean) {
    if (!summary.trim() || !date || !ready) return;
    void mutation.execute((signal) =>
      api.report(
        node.id,
        {
          result,
          summary: summary.trim(),
          finished_on: date,
          attachment_ids: ids,
          self_approve: self,
        },
        signal,
      ),
    );
  }
  const showForm = canSubmit && formOpen && !mutation.saved;
  return (
    <section className={`record-panel report-card ${tone}`} aria-label="完成回報">
      <div className="rc-row">
        <div className="rc-main">
          <h3>{mark && <span aria-hidden="true">{mark}</span>}{title}</h3>
          {loading ? (
            <p role="status">正在確認完整回報歷史</p>
          ) : error ? (
            <p role="alert">{error}</p>
          ) : latest && (pending || rejected || node.status === 'done' || latest.legacy) ? (
            <ReportSummary report={latest} compact />
          ) : (
            <p className="small muted">
              {node.status === 'done'
                ? '已完成，未附回報'
                : node.status === 'skipped'
                  ? '這個任務已略過；有權限的人可以恢復。'
                  : '需填：結果、成果說明、實際完成日・送出後由有權審核者確認。'}
            </p>
          )}
        </div>
        <div className="rc-acts">
          {error && !loading && <button onClick={() => void load()}>重試回報讀取</button>}
          {!loading && !error && canSubmit && !formOpen && !mutation.saved && (
            <button
              className="primary"
              ref={(el) => {
                if (el && reopen.current) {
                  reopen.current = false;
                  el.focus();
                }
              }}
              onClick={() => setFormOpen(true)}
            >
              {rejected ? '重新回報' : '回報完成'}
            </button>
          )}
          {!loading && !error && pending && !canReview && <span className="small muted">等待有權審核者確認</span>}
        </div>
      </div>
      {!loading && !error && (
        <>
          {mutation.error && <p role="alert">{mutation.error}</p>}
          {mutation.saved ? (
            <button
              disabled={mutation.busy}
              onClick={() => void mutation.execute()}
            >
              重試回報載入
            </button>
          ) : (
            <>
              {showForm && (
                <form
                  className="record-form"
                  aria-label="回報表單"
                  onSubmit={(e) => {
                    e.preventDefault();
                    submit(false);
                  }}
                >
                  {rejected && <p>重新送出將建立新版本</p>}
                  <fieldset disabled={mutation.busy}>
                    <label>
                      結果
                      <select
                        aria-label="結果"
                        value={result}
                        onChange={(e) => setResult(e.target.value)}
                      >
                        {['達成', '部分達成', '未達成'].map((v) => (
                          <option key={v}>{v}</option>
                        ))}
                      </select>
                    </label>
                    <label>
                      成果說明
                      <textarea
                        autoFocus
                        required
                        maxLength={10000}
                        placeholder="做了什麼、結果如何、有沒有需要後續處理的事"
                        value={summary}
                        onChange={(e) => setSummary(e.target.value)}
                      />
                    </label>
                    <label>
                      實際完成日
                      <input
                        required
                        type="date"
                        min="0001-01-01"
                        max="9999-12-31"
                        value={date}
                        onChange={(e) => setDate(e.target.value)}
                      />
                    </label>
                  </fieldset>
                  <AttachmentUpload
                    disabled={mutation.busy}
                    nodeId={node.id}
                    label="回報附件"
                    expired={expired}
                    changed={(v, r) => {
                      setIds(v);
                      setReady(r);
                    }}
                  />
                  <p className="small muted">送出後任務會移到「待確認」，回報內容會鎖定；由有權審核者確認完成。</p>
                  <div className="record-actions">
                    <button
                      type="button"
                      disabled={mutation.busy}
                      onClick={() => {
                        // The upload list unmounts with the form, so drop its selection too.
                        setIds([]);
                        setReady(true);
                        reopen.current = true;
                        setFormOpen(false);
                      }}
                    >
                      取消回報
                    </button>
                    {actions.includes('submit_and_approve') && (
                      <button
                        type="button"
                        disabled={
                          mutation.busy || !ready || !summary.trim() || !date
                        }
                        onClick={() => submit(true)}
                      >
                        送出並確認
                      </button>
                    )}
                    <button
                      disabled={
                        mutation.busy || !ready || !summary.trim() || !date
                      }
                    >
                      送出回報
                    </button>
                  </div>
                </form>
              )}
              {canReview && latest && (
                <div className="record-form">
                  <label>
                    審核意見（退回時必填）
                    <textarea
                      aria-label="審核意見"
                      maxLength={2000}
                      disabled={mutation.busy}
                      value={comment}
                      onChange={(e) => setComment(e.target.value)}
                    />
                  </label>
                  <div className="record-actions">
                    <button
                      className="primary"
                      disabled={mutation.busy}
                      onClick={() =>
                        void mutation.execute((signal) =>
                          api.reviewReport(
                            latest.id,
                            'approved',
                            comment.trim(),
                            signal,
                          ),
                        )
                      }
                    >
                      確認回報
                    </button>
                    <button
                      className="danger"
                      disabled={mutation.busy || !comment.trim()}
                      onClick={() =>
                        void mutation.execute((signal) =>
                          api.reviewReport(
                            latest.id,
                            'rejected',
                            comment.trim(),
                            signal,
                          ),
                        )
                      }
                    >
                      退回回報
                    </button>
                  </div>
                </div>
              )}
              {node.capabilities?.lifecycle && (
                <div className="record-actions lifecycle-actions">
                  {[
                    ['skip', '略過任務'],
                    [
                      'reopen',
                      node.status === 'review' ? '恢復工作' : '重新開啟',
                    ],
                    ['restore', '恢復任務'],
                  ]
                    .filter(([key]) => actions.includes(key))
                    .map(([key, text]) => (
                      <button
                        key={key}
                        disabled={mutation.busy}
                        onClick={(e) => {
                          trigger.current = e.currentTarget;
                          setAction(key);
                          setReason('');
                        }}
                      >
                        {text}
                      </button>
                    ))}
                </div>
              )}
              {action && (
                <form
                  className="record-form"
                  onSubmit={(e) => {
                    e.preventDefault();
                    if (reason.trim())
                      void mutation.execute((signal) =>
                        api.lifecycle(node.id, action, reason.trim(), signal),
                      );
                  }}
                >
                  <label>
                    操作理由
                    <textarea
                      autoFocus
                      required
                      maxLength={2000}
                      disabled={mutation.busy}
                      value={reason}
                      onChange={(e) => setReason(e.target.value)}
                    />
                  </label>
                  <button disabled={mutation.busy || !reason.trim()}>
                    {action === 'skip'
                      ? '確認略過'
                      : action === 'reopen'
                        ? '確認重新開啟'
                        : '確認恢復'}
                  </button>
                  <button
                    type="button"
                    disabled={mutation.busy}
                    onClick={() => {
                      setAction('');
                      trigger.current?.focus();
                    }}
                  >
                    取消操作
                  </button>
                </form>
              )}
            </>
          )}
        </>
      )}
    </section>
  );
}
