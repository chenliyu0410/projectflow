import { useEffect, useRef, useState } from 'react';
import {
  api,
  ApiError,
  recordError,
  useRequestScope,
  useRecordMutation,
} from '../api';
import type { RecordReload } from '../api';
import type { AssignmentOptions, Collaborators } from '../types';
export default function CollaboratorEditor({
  nodeId,
  projectId,
  manage,
  reload,
  expired,
}: {
  nodeId: string;
  projectId: string;
  manage: boolean;
  reload: RecordReload;
  expired: () => void;
}) {
  const scope = useRequestScope();
  const trigger = useRef<HTMLButtonElement>(null);
  const restoreFocus = useRef(false);
  const [data, setData] = useState<Collaborators | null>(null);
  const [options, setOptions] = useState<AssignmentOptions | null>(null);
  const [error, setError] = useState('');
  const [editing, setEditing] = useState(false);
  const [users, setUsers] = useState<string[]>([]);
  const [departments, setDepartments] = useState<string[]>([]);
  const mutation = useRecordMutation(reload, expired);
  async function load() {
    const r = scope.begin();
    setError('');
    try {
      const value = await api.collaborators(nodeId, r.controller.signal);
      if (!scope.current(r)) return;
      setData(value);
      setUsers(value.users.map((u) => u.id));
      setDepartments(value.departments.map((d) => d.id));
      if (manage) {
        const list = await api.assignmentOptions(
          projectId,
          r.controller.signal,
        );
        if (scope.current(r)) setOptions(list);
      }
    } catch (e) {
      if (scope.current(r)) {
        if (e instanceof ApiError && e.status === 401) expired();
        else setError(recordError(e));
      }
    }
  }
  useEffect(() => {
    void load();
  }, []);
  useEffect(() => {
    if (!editing && restoreFocus.current) trigger.current?.focus();
  }, [editing]);
  function toggle(id: string, values: string[], set: (v: string[]) => void) {
    set(values.includes(id) ? values.filter((v) => v !== id) : [...values, id]);
  }
  return (
    <section className="record-panel" aria-label="協作人員">
      <h3>協作人員與部門</h3>
      {error ? (
        <>
          <p role="alert">{error}</p>
          <button onClick={() => void load()}>重試協作讀取</button>
        </>
      ) : !data ? (
        <p role="status">載入協作設定中</p>
      ) : (
        <p>
          {[
            ...data.users.map((u) => u.display_name),
            ...data.departments.map((d) => d.name),
          ].join('、') || '尚未設定協作'}
        </p>
      )}
      {manage && data && !editing && (
        <button
          ref={trigger}
          disabled={!options || !!error}
          onClick={() => {
            restoreFocus.current = true;
            setEditing(true);
          }}
        >
          協作設定
        </button>
      )}
      {editing && data && options && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void mutation.execute((signal) =>
              api.setCollaborators(
                nodeId,
                users,
                departments,
                data.revision,
                signal,
              ),
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
              重試協作載入
            </button>
          ) : (
            <>
              <fieldset disabled={mutation.busy}>
                <legend>協作人員</legend>
                {options.users.map((u) => (
                  <label className="check-label" key={u.id}>
                    <input
                      type="checkbox"
                      checked={users.includes(u.id)}
                      onChange={() => toggle(u.id, users, setUsers)}
                    />
                    {u.display_name}
                  </label>
                ))}
              </fieldset>
              <fieldset disabled={mutation.busy}>
                <legend>協作部門（僅主管取得權限）</legend>
                {options.departments.map((d) => (
                  <label className="check-label" key={d.id}>
                    <input
                      type="checkbox"
                      checked={departments.includes(d.id)}
                      onChange={() => toggle(d.id, departments, setDepartments)}
                    />
                    {d.name}
                  </label>
                ))}
              </fieldset>
              <button disabled={mutation.busy}>儲存協作</button>
              <button
                type="button"
                disabled={mutation.busy}
                onClick={() => {
                  setUsers(data.users.map((u) => u.id));
                  setDepartments(data.departments.map((d) => d.id));
                  setEditing(false);
                }}
              >
                取消協作
              </button>
            </>
          )}
        </form>
      )}
    </section>
  );
}
