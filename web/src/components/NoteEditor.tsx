import { useState } from 'react';
import { api, useRecordMutation } from '../api';
import type { RecordReload } from '../api';
import type { Note } from '../types';
import { AttachmentUpload } from './AttachmentList';
export default function NoteEditor({
  nodeId,
  note,
  reload,
  expired,
  close,
}: {
  nodeId: string;
  note?: Note;
  reload: RecordReload;
  expired: () => void;
  close?: () => void;
}) {
  const [body, setBody] = useState(note?.body ?? '');
  const [ids, setIds] = useState<string[]>([]);
  const [ready, setReady] = useState(true);
  const mutation = useRecordMutation(reload, expired);
  return (
    <form
      className="record-form"
      onSubmit={(e) => {
        e.preventDefault();
        if (body.trim() && ready)
          void mutation.execute((signal) =>
            note
              ? api.editNote(note.id, body.trim(), note.revision, signal)
              : api.note(nodeId, body.trim(), ids, signal),
          );
      }}
    >
      {mutation.error && <p role="alert">{mutation.error}</p>}
      {mutation.saved ? (
        <button
          type="button"
          disabled={mutation.busy}
          onClick={() => void mutation.execute()}
        >
          重試筆記載入
        </button>
      ) : (
        <>
          <label>
            {note ? '編輯筆記' : '新增筆記'}
            <textarea
              autoFocus={!!note}
              maxLength={10000}
              required
              disabled={mutation.busy}
              value={body}
              onChange={(e) => setBody(e.target.value)}
            />
          </label>
          {!note && (
            <AttachmentUpload
              disabled={mutation.busy}
              nodeId={nodeId}
              label="筆記附件"
              expired={expired}
              changed={(v, r) => {
                setIds(v);
                setReady(r);
              }}
            />
          )}
          <div className="record-actions">
            <button disabled={mutation.busy || !ready || !body.trim()}>
              {note ? '儲存筆記' : '新增筆記'}
            </button>
            {close && (
              <button type="button" disabled={mutation.busy} onClick={close}>
                取消編輯筆記
              </button>
            )}
          </div>
        </>
      )}
    </form>
  );
}
