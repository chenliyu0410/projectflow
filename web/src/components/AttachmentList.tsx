import { useEffect, useRef, useState } from 'react';
import {
  api,
  formatRecordTime,
  ApiError,
  recordError,
  useRecordMutation,
  useRequestScope,
} from '../api';
import type { RecordReload } from '../api';
import type { Attachment, Quota } from '../types';

export function AttachmentUpload({
  nodeId,
  label,
  changed,
  expired,
  reload,
  disabled = false,
}: {
  nodeId: string;
  label: string;
  changed: (ids: string[], ready: boolean) => void;
  expired: () => void;
  reload?: RecordReload;
  disabled?: boolean;
}) {
  const scope = useRequestScope();
  const [quota, setQuota] = useState<Quota | null>(null);
  const [error, setError] = useState('');
  const [progress, setProgress] = useState('');
  const [uploaded, setUploaded] = useState(false);
  const [busy, setBusy] = useState(false);
  const lock = useRef(false);
  async function loadQuota() {
    const r = scope.begin();
    try {
      const q = await api.quota(nodeId, r.controller.signal);
      if (scope.current(r)) setQuota(q);
    } catch (e) {
      if (scope.current(r)) {
        if (e instanceof ApiError && e.status === 401) expired();
        else setError(recordError(e));
      }
    }
  }
  useEffect(() => {
    void loadQuota();
  }, []);
  async function upload(files: File[]) {
    if (lock.current || !files.length || !quota) return;
    changed([], false);
    setError('');
    setUploaded(false);
    if (
      files.some((f) => f.size === 0 || f.size > 10000000) ||
      files.reduce((n, f) => n + f.size, 0) > quota.remaining_bytes
    ) {
      setError('檔案不得為空，單檔上限 10 MB，且不可超過公司剩餘容量');
      return;
    }
    const r = scope.begin();
    lock.current = true;
    setBusy(true);
    const ids: string[] = [];
    try {
      for (let i = 0; i < files.length; i++) {
        setProgress(`上傳中 ${i + 1} / ${files.length}`);
        const item = await api.upload(nodeId, files[i], r.controller.signal);
        if (!scope.current(r)) return;
        ids.push(item.id);
      }
      changed(ids, true);
      setProgress('上傳完成');
      setUploaded(true);
      if (reload) await reload(r.controller.signal);
    } catch (e) {
      if (!scope.current(r)) return;
      if (e instanceof ApiError && e.status === 401) expired();
      else
        setError(
          ids.length === files.length
            ? '已上傳，資料重新載入失敗'
            : recordError(e),
        );
    } finally {
      if (scope.current(r)) {
        lock.current = false;
        setBusy(false);
      }
    }
  }
  async function retryRead() {
    const r = scope.begin();
    setBusy(true);
    setError('');
    try {
      await reload?.(r.controller.signal);
    } catch (e) {
      if (scope.current(r)) {
        if (e instanceof ApiError && e.status === 401) expired();
        else setError('已上傳，資料重新載入失敗');
      }
    } finally {
      if (scope.current(r)) setBusy(false);
    }
  }
  return (
    <div className="attachment-upload">
      <p>
        單檔上限 10 MB；
        {quota
          ? `公司剩餘容量 ${quota.remaining_bytes.toLocaleString()} bytes`
          : '載入剩餘容量中'}
      </p>
      <label>
        {label}
        <input
          type="file"
          multiple
          accept=".pdf,.png,.jpg,.jpeg,.txt,.csv,.docx,.xlsx,.pptx,.zip"
          disabled={disabled || busy || !quota || (uploaded && !!reload)}
          onChange={(e) => void upload(Array.from(e.target.files ?? []))}
        />
      </label>
      {progress && <p role="status">{progress}</p>}
      {error && <p role="alert">{error}</p>}
      {!quota && error && (
        <button type="button" onClick={() => void loadQuota()}>
          重試容量讀取
        </button>
      )}
      {uploaded && reload && error && (
        <button type="button" disabled={busy} onClick={() => void retryRead()}>
          重試附件載入
        </button>
      )}
      {!reload && (
        <button
          type="button"
          disabled={disabled || busy}
          onClick={() => {
            scope.begin();
            changed([], true);
            setError('');
            setProgress('');
            setUploaded(false);
          }}
        >
          清除待選附件
        </button>
      )}
    </div>
  );
}
export default function AttachmentList({
  items,
  nodeId,
  userId,
  canWrite,
  manage,
  expired,
  reload,
}: {
  items: Attachment[];
  nodeId: string;
  userId: string;
  canWrite: boolean;
  manage: boolean;
  expired: () => void;
  reload: RecordReload;
}) {
  const scope = useRequestScope();
  const mutation = useRecordMutation(reload, expired);
  const [error, setError] = useState('');
  const [downloading, setDownloading] = useState<string | null>(null);
  const objectUrl = useRef<string | null>(null);
  useEffect(
    () => () => {
      if (objectUrl.current) URL.revokeObjectURL(objectUrl.current);
    },
    [],
  );
  async function download(item: Attachment) {
    const r = scope.begin();
    setDownloading(item.id);
    setError('');
    try {
      const blob = await api.download(item.id, r.controller.signal);
      if (!scope.current(r)) return;
      const url = URL.createObjectURL(blob);
      objectUrl.current = url;
      const a = document.createElement('a');
      a.href = url;
      a.download = item.original_name;
      a.click();
      URL.revokeObjectURL(url);
      objectUrl.current = null;
    } catch (e) {
      if (scope.current(r)) {
        if (e instanceof ApiError && e.status === 401) expired();
        else setError(recordError(e));
      }
    } finally {
      if (scope.current(r)) setDownloading(null);
    }
  }
  return (
    <section className="record-panel" aria-label="附件">
      <h3>附件</h3>
      {canWrite && (
        <AttachmentUpload
          nodeId={nodeId}
          label="選擇附件"
          changed={() => {}}
          expired={expired}
          reload={reload}
        />
      )}
      {(error || mutation.error) && (
        <p role="alert">{error || mutation.error}</p>
      )}
      {mutation.saved && mutation.error && (
        <button
          disabled={mutation.busy}
          onClick={() => void mutation.execute()}
        >
          重試附件載入
        </button>
      )}
      {items.length === 0 ? (
        <p>還沒有附件。</p>
      ) : (
        <div className="attachment-table">
          <table>
            <thead>
              <tr>
                <th>檔名</th>
                <th>大小</th>
                <th>上傳者</th>
                <th>時間／所屬</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                  <td data-label="檔名">{item.original_name}</td>
                  <td data-label="大小">
                    {item.size_bytes.toLocaleString()} bytes
                  </td>
                  <td data-label="上傳者">
                    {item.uploaded_by_display_name ?? '未設定'}
                  </td>
                  <td data-label="時間／所屬">
                    {formatRecordTime(item.created_at)}
                    <br />
                    {item.report_id
                      ? '回報附件（鎖定）'
                      : item.note_id
                        ? '筆記附件'
                        : '節點附件'}
                  </td>
                  <td data-label="操作">
                    <button
                      aria-label={`下載 ${item.original_name}`}
                      disabled={!!downloading}
                      onClick={() => void download(item)}
                    >
                      下載
                    </button>
                    {downloading === item.id && <p role="status">下載中</p>}
                    {canWrite &&
                      !item.report_id &&
                      (manage || item.uploaded_by === userId) && (
                        <button
                          aria-label={`移除 ${item.original_name}`}
                          disabled={mutation.busy || mutation.saved}
                          onClick={() =>
                            void mutation.execute((signal) =>
                              api.removeAttachment(item.id, signal),
                            )
                          }
                        >
                          移除
                        </button>
                      )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
