import { useEffect, useRef, useState } from 'react';
import {
  api,
  formatRecordTime,
  ApiError,
  recordError,
  useRequestScope,
} from '../api';
import type { RecordReload } from '../api';
import type { NodeItem, Note, RecordItem, Attachment } from '../types';
import { ReportSummary } from './ReportPanel';
import NoteEditor from './NoteEditor';
import AttachmentList from './AttachmentList';
import CollaboratorEditor from './CollaboratorEditor';
function Timeline({
  node,
  userId,
  reload,
  expired,
  select,
  readScope,
}: {
  node: NodeItem;
  userId: string;
  reload: RecordReload;
  expired: () => void;
  select: (id: string) => void;
  readScope: string;
}) {
  const scope = useRequestScope();
  const [items, setItems] = useState<RecordItem[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [editing, setEditing] = useState<Note | null>(null);
  const trigger = useRef<HTMLButtonElement | null>(null);
  const lock = useRef(false);
  async function load(append = false) {
    if (lock.current) return;
    const r = scope.begin();
    lock.current = true;
    setLoading(true);
    setError('');
    try {
      const page = await api.records(
        node.id,
        readScope,
        append ? cursor : null,
        50,
        r.controller.signal,
      );
      if (scope.current(r)) {
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
      }
    } catch (e) {
      if (scope.current(r)) {
        if (e instanceof ApiError && e.status === 401) expired();
        else setError(recordError(e));
      }
    } finally {
      if (scope.current(r)) {
        lock.current = false;
        setLoading(false);
      }
    }
  }
  useEffect(() => {
    void load();
  }, []);
  const canWrite = !!node.capabilities?.write_record;
  const attachments = new Map<string, Attachment>();
  for (const item of items) {
    if (item.type === 'attachment') attachments.set(item.id, item);
    else
      for (const attachment of item.attachments)
        attachments.set(attachment.id, attachment);
  }
  function source(item: RecordItem) {
    return (
      readScope === 'subtree' && (
        <button className="record-source" onClick={() => select(item.node_id)}>
          {item.node_title}
        </button>
      )
    );
  }
  return (
    <div className="records" aria-label="任務紀錄">
      {readScope === 'subtree' && (
        <p>以下為可見後代紀錄彙總；不包含不可見節點。</p>
      )}
      {loading && <p role="status">載入紀錄中</p>}
      {error && (
        <>
          <p role="alert">{error}</p>
          <button onClick={() => void load(items.length > 0)}>
            重試紀錄讀取
          </button>
        </>
      )}
      <section className="record-panel" aria-label="回報歷史">
        <h3>回報歷史</h3>
        {items
          .filter((i) => i.type === 'report')
          .map((item) => (
            <div key={item.id}>
              {source(item)}
              <ReportSummary report={item} />
            </div>
          ))}
        {!loading && !error && !items.some((i) => i.type === 'report') && (
          <p>目前已載入的紀錄沒有回報。</p>
        )}
      </section>
      <section className="record-panel" aria-label="筆記">
        <h3>筆記</h3>
        {canWrite && readScope === 'self' && (
          <NoteEditor nodeId={node.id} reload={reload} expired={expired} />
        )}
        {items
          .filter((i) => i.type === 'note')
          .map((note) => (
            <article key={note.id} className="note-entry">
              <div className="record-actions">
                <strong>{note.author_display_name ?? '未設定'}</strong>
                <span className="record-meta">
                  {formatRecordTime(note.created_at)}
                  {note.edited_at &&
                    ` · 已編輯 ${formatRecordTime(note.edited_at)}`}{' '}
                  · 修訂 {note.revision}
                </span>
                {source(note)}
                {readScope === 'self' &&
                  canWrite &&
                  note.author_id === userId && (
                    <button
                      onClick={(e) => {
                        trigger.current = e.currentTarget;
                        setEditing(note);
                      }}
                    >
                      修改筆記
                    </button>
                  )}
              </div>
              {editing?.id === note.id ? (
                <NoteEditor
                  key={note.id}
                  nodeId={node.id}
                  note={note}
                  reload={reload}
                  expired={expired}
                  close={() => {
                    setEditing(null);
                    trigger.current?.focus();
                  }}
                />
              ) : (
                <p className="record-body">{note.body}</p>
              )}
            </article>
          ))}
        {!loading && !error && !items.some((i) => i.type === 'note') && (
          <p>目前已載入的紀錄沒有筆記。</p>
        )}
      </section>
      <AttachmentList
        items={[...attachments.values()]}
        nodeId={node.id}
        userId={userId}
        canWrite={canWrite && readScope === 'self'}
        manage={!!node.capabilities?.manage_collaborators}
        reload={reload}
        expired={expired}
      />
      {cursor && (
        <button disabled={loading} onClick={() => void load(true)}>
          載入更多紀錄
        </button>
      )}
      <CollaboratorEditor
        nodeId={node.id}
        projectId={node.project_id}
        manage={!!node.capabilities?.manage_collaborators}
        reload={reload}
        expired={expired}
      />
    </div>
  );
}

export default function RecordTimeline(props: {
  node: NodeItem;
  userId: string;
  reload: RecordReload;
  expired: () => void;
  select: (id: string) => void;
}) {
  const [scope, setScope] = useState(
    props.node.kind === 'task' ? 'self' : 'subtree',
  );
  return (
    <>
      {props.node.kind !== 'task' && (
        <label>
          紀錄範圍
          <select
            aria-label="紀錄範圍"
            value={scope}
            onChange={(e) => setScope(e.target.value)}
          >
            <option value="self">此節點</option>
            <option value="subtree">可見後代彙總（唯讀）</option>
          </select>
        </label>
      )}
      <Timeline key={scope} {...props} readScope={scope} />
    </>
  );
}
