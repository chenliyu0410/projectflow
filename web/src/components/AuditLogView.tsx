import { useEffect, useRef, useState } from 'react';
import {
  api,
  ApiError,
  formatRecordTime,
  recordError,
  useRequestScope,
} from '../api';
import type { AuditItem } from '../types';
const actions: Record<string, string> = {
  'project.create': '建立專案',
  'workflow.instantiate': '套用工作流',
  'node.create': '新增節點',
  'node.update': '更新節點資料',
  'node.status': '更新節點狀態',
  'node.reopen': '恢復工作',
  'node.skip': '略過任務',
  'node.restore': '恢復略過任務',
  'gate.approve': '核准閘門',
  'report.submit': '送出回報',
  'report.approve': '確認回報',
  'report.reject': '退回回報',
  'note.create': '新增筆記',
  'note.update': '修訂筆記',
  'collaborators.update': '更新協作設定',
  'attachment.upload': '上傳附件',
  'attachment.delete': '移除附件',
};
const statuses: Record<string, string> = {
  todo: '待處理',
  doing: '進行中',
  review: '待確認',
  done: '完成',
  skipped: '已略過',
  approved: '已核准',
};
function object(v: unknown): Record<string, unknown> {
  return v && typeof v === 'object' && !Array.isArray(v)
    ? (v as Record<string, unknown>)
    : {};
}
function text(v: unknown) {
  return typeof v === 'string' || typeof v === 'number' ? String(v) : '未設定';
}
function names(v: unknown, key: string) {
  return Array.isArray(v)
    ? v
        .map((x) => object(x)[key])
        .filter((x) => typeof x === 'string')
        .join('、') || '未設定'
    : '未設定';
}
function AuditChanges({ item }: { item: AuditItem }) {
  const p = item.payload;
  const lines: [string, string][] = [];
  const add = (label: string, value: unknown) => {
    if (value !== undefined) lines.push([label, text(value)]);
  };
  if (
    ['report.submit', 'report.approve', 'report.reject'].includes(item.action)
  ) {
    add('版本', p.version);
    add('結果', p.result);
    add('審核意見', p.comment);
    if (typeof p.self_approved === 'boolean')
      add('確認方式', p.self_approved ? '自行確認' : '由審核者確認');
  }
  if (item.action === 'note.create') {
    add('筆記', p.body);
    add('修訂', p.revision);
  }
  if (item.action === 'note.update') {
    for (const [side, label] of [
      ['before', '修改前'],
      ['after', '修改後'],
    ]) {
      const v = object(p[side]);
      add(label, v.body);
      add(label + '修訂', v.revision);
    }
  }
  if (['attachment.upload', 'attachment.delete'].includes(item.action)) {
    add('檔名', p.original_name);
    if (typeof p.size_bytes === 'number')
      add('大小', `${p.size_bytes.toLocaleString()} bytes`);
  }
  if (item.action === 'node.status' && typeof p.status === 'string')
    add('狀態', statuses[p.status] ?? '未設定');
  if (['node.reopen', 'node.skip', 'node.restore'].includes(item.action))
    add('理由', p.reason);
  if (
    ['project.create', 'workflow.instantiate', 'node.create'].includes(
      item.action,
    )
  ) {
    add('名稱', p.title);
    add('開始日期', p.start_date);
    add('截止日期', p.due_date);
    if (typeof p.kind === 'string')
      add(
        '種類',
        (
          { project: '專案', phase: '階段', task: '任務' } as Record<
            string,
            string
          >
        )[p.kind],
      );
  }
  if (item.action === 'node.update') {
    for (const [key, label] of [
      ['title', '名稱'],
      ['start_date', '開始日期'],
      ['due_date', '截止日期'],
    ]) {
      const v = object(p[key]);
      add(label + '（修改前）', v.before);
      add(label + '（修改後）', v.after);
    }
    if (p.owner_user_id) add('負責人', '指派已更新');
    if (p.department_id) add('部門', '指派已更新');
  }
  if (item.action === 'collaborators.update') {
    for (const [side, label] of [
      ['before', '修改前'],
      ['after', '修改後'],
    ]) {
      const v = object(p[side]);
      if (v.users) add(label + '協作人員', names(v.users, 'display_name'));
      if (v.departments) add(label + '協作部門', names(v.departments, 'name'));
      add(label + '修訂', v.revision);
    }
  }
  return lines.length ? (
    <dl className="audit-changes">
      {lines.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  ) : null;
}
export default function AuditLogView({
  openNode,
  expired,
}: {
  openNode: (projectId: string, nodeId: string) => void;
  expired: () => void;
}) {
  const scope = useRequestScope();
  const locked = useRef(false);
  const [action, setAction] = useState('');
  const [node, setNode] = useState<{ id: string; title: string } | null>(null);
  const [items, setItems] = useState<AuditItem[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  async function load(append = false) {
    if (append && locked.current) return;
    const r = scope.begin();
    locked.current = true;
    setLoading(true);
    setError('');
    if (!append) {
      setItems([]);
      setCursor(null);
    }
    try {
      const page = await api.audit(
        action,
        node?.id ?? null,
        append ? cursor : null,
        r.controller.signal,
      );
      if (!scope.current(r)) return;
      setItems((old) =>
        append
          ? [
              ...old,
              ...page.items.filter((i) => !old.some((o) => o.id === i.id)),
            ]
          : page.items,
      );
      setCursor(page.next_cursor);
    } catch (e) {
      if (scope.current(r)) {
        if (e instanceof ApiError && e.status === 401) expired();
        else setError(recordError(e));
      }
    } finally {
      if (scope.current(r)) {
        locked.current = false;
        setLoading(false);
      }
    }
  }
  useEffect(() => {
    void load();
  }, [action, node?.id]);
  return (
    <div className="audit-view">
      <h2>稽核紀錄</h2>
      <p>僅顯示目前可見的業務事件。</p>
      <div className="audit-filters">
        <label>
          事件類型
          <select value={action} onChange={(e) => setAction(e.target.value)}>
            <option value="">全部事件</option>
            {Object.entries(actions).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
        </label>
        {node && <p>任務：{node.title}</p>}
        <button
          disabled={!action && !node}
          onClick={() => {
            setAction('');
            setNode(null);
          }}
        >
          清除篩選
        </button>
      </div>
      {loading && <p role="status">載入稽核紀錄中</p>}
      {error && (
        <>
          <p role="alert">{error}</p>
          <button
            disabled={loading}
            onClick={() => void load(items.length > 0)}
          >
            重試稽核讀取
          </button>
        </>
      )}
      {!loading && !error && items.length === 0 && (
        <p>目前沒有符合條件的紀錄</p>
      )}
      <div className="audit-list">
        {items.map((item) => (
          <article className="record-panel" key={item.id}>
            <h3>{actions[item.action] ?? '其他業務事件'}</h3>
            <p className="record-meta">
              {item.actor_display_name ?? '未設定'} ·{' '}
              {formatRecordTime(item.created_at)}
            </p>
            {item.node_id && item.project_id && (
              <div className="record-actions">
                <button
                  onClick={() => openNode(item.project_id!, item.node_id!)}
                >
                  {item.node_title ?? '開啟任務'}
                </button>
                <span>{item.project_title}</span>
                <button
                  aria-label={`只看此任務：${item.node_title ?? '任務'}`}
                  onClick={() =>
                    setNode({
                      id: item.node_id!,
                      title: item.node_title ?? '任務',
                    })
                  }
                >
                  只看此任務
                </button>
              </div>
            )}
            <AuditChanges item={item} />
          </article>
        ))}
      </div>
      {cursor && (
        <button disabled={loading} onClick={() => void load(true)}>
          載入更多稽核
        </button>
      )}
    </div>
  );
}
