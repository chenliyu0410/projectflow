import type { ReviewPage, AuditPage } from './types';
import { useEffect, useRef, useState } from 'react';
import type {
  Attachment,
  Collaborators,
  Note,
  Quota,
  RecordPage,
  Report,
  AssignmentOptions,
  GateItem,
  MyTask,
  NodeCreate,
  NodeItem,
  NodeMetadata,
  NodeStatus,
  ProjectDetail,
  ProjectSummary,
  SessionInfo,
  WorkflowSummary,
  WorkspaceOverviewData,
} from './types';

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

export async function requestJson<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  if (!headers.has('Content-Type'))
    headers.set('Content-Type', 'application/json');
  let response: Response;
  try {
    response = await fetch(`/api${path}`, {
      ...init,
      credentials: 'include',
      headers,
    });
  } catch (error) {
    if (init.signal?.aborted) throw error;
    throw new ApiError(0, '無法連線，請稍後再試');
  }
  // Never display backend details, which may include validation input or secrets.
  if (!response.ok) {
    const message =
      response.status === 401
        ? path === '/auth/login'
          ? '帳號或密碼錯誤'
          : '登入已失效，請重新登入'
        : response.status === 403
          ? '沒有操作權限'
          : response.status === 404
            ? '找不到項目'
            : response.status === 409
              ? '目前狀態已變更或不允許操作，請重新整理確認'
              : response.status === 413
                ? '檔案超過 10 MB 或公司剩餘容量不足'
                : response.status === 415
                  ? '不支援此檔案格式'
                  : response.status === 411
                    ? '無法確認檔案大小，請重新選擇檔案'
                    : response.status === 422 && path !== '/auth/login'
                      ? path.includes('/workspace/reviews') ||
                        path.includes('/audit-logs')
                        ? '篩選或分頁參數已失效，請清除篩選或重新載入'
                        : path.includes('/attachments')
                          ? '請檢查附件內容、檔名與實際長度是否符合格式'
                          : path.includes('/reports')
                            ? '請檢查成果說明、結果、實際完成日或審核意見'
                            : path.includes('/notes')
                              ? '請檢查筆記內容與修訂版本'
                              : path.includes('/collaborators')
                                ? '請檢查協作選擇與修訂版本'
                                : path.includes('/lifecycle')
                                  ? '請填寫有效的操作理由'
                                  : '請檢查欄位內容：名稱、日期或指派不符合規則'
                      : '操作失敗，請稍後再試';
    throw new ApiError(response.status, message);
  }
  if (response.status === 204) return undefined as T;
  try {
    return (await response.json()) as T;
  } catch {
    throw new ApiError(response.status, '無法讀取資料，請稍後再試');
  }
}

export const api = {
  reviews: (cursor: string | null = null, signal?: AbortSignal) =>
    requestJson<ReviewPage>(
      `/workspace/reviews?${new URLSearchParams({ kind: 'all', limit: '50', ...(cursor ? { cursor } : {}) })}`,
      { signal },
    ),
  audit: (
    action: string,
    nodeId: string | null,
    cursor: string | null = null,
    signal?: AbortSignal,
  ) =>
    requestJson<AuditPage>(
      `/audit-logs?${new URLSearchParams({ action, limit: '50', ...(nodeId ? { node_id: nodeId } : {}), ...(cursor ? { cursor } : {}) })}`,
      { signal },
    ),
  records: (
    id: string,
    scope = 'self',
    cursor: string | null = null,
    limit = 50,
    signal?: AbortSignal,
  ) =>
    requestJson<RecordPage>(
      `/nodes/${id}/records?${new URLSearchParams({ scope, limit: String(limit), ...(cursor ? { cursor } : {}) })}`,
      { signal },
    ),
  report: (
    id: string,
    payload: {
      result: string;
      summary: string;
      finished_on: string;
      attachment_ids: string[];
      self_approve: boolean;
    },
    signal?: AbortSignal,
  ) =>
    requestJson<Report>(`/nodes/${id}/reports`, {
      method: 'POST',
      body: JSON.stringify(payload),
      signal,
    }),
  reviewReport: (
    id: string,
    decision: string,
    comment: string,
    signal?: AbortSignal,
  ) =>
    requestJson<Report>(`/reports/${id}/review`, {
      method: 'POST',
      body: JSON.stringify({ decision, comment }),
      signal,
    }),
  lifecycle: (
    id: string,
    action: string,
    reason: string,
    signal?: AbortSignal,
  ) =>
    requestJson<NodeItem>(`/nodes/${id}/lifecycle`, {
      method: 'POST',
      body: JSON.stringify({ action, reason }),
      signal,
    }),
  note: (
    id: string,
    body: string,
    attachment_ids: string[],
    signal?: AbortSignal,
  ) =>
    requestJson<Note>(`/nodes/${id}/notes`, {
      method: 'POST',
      body: JSON.stringify({ body, attachment_ids }),
      signal,
    }),
  editNote: (
    id: string,
    body: string,
    expected_revision: number,
    signal?: AbortSignal,
  ) =>
    requestJson<Note>(`/notes/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ body, expected_revision }),
      signal,
    }),
  collaborators: (id: string, signal?: AbortSignal) =>
    requestJson<Collaborators>(`/nodes/${id}/collaborators`, { signal }),
  setCollaborators: (
    id: string,
    user_ids: string[],
    department_ids: string[],
    expected_revision: number,
    signal?: AbortSignal,
  ) =>
    requestJson<Collaborators>(`/nodes/${id}/collaborators`, {
      method: 'PUT',
      body: JSON.stringify({ user_ids, department_ids, expected_revision }),
      signal,
    }),
  quota: (id: string, signal?: AbortSignal) =>
    requestJson<Quota>(`/nodes/${id}/attachment-quota`, { signal }),
  upload: (id: string, file: File, signal?: AbortSignal) =>
    requestJson<Attachment>(
      `/nodes/${id}/attachments?${new URLSearchParams({ filename: file.name })}`,
      {
        method: 'POST',
        body: file,
        headers: { 'Content-Type': 'application/octet-stream' },
        signal,
      },
    ),
  removeAttachment: (id: string, signal?: AbortSignal) =>
    requestJson<{ deleted: boolean }>(`/attachments/${id}`, {
      method: 'DELETE',
      signal,
    }),
  download: async (id: string, signal?: AbortSignal) => {
    const response = await fetch(`/api/attachments/${id}/download`, {
      credentials: 'include',
      signal,
    });
    if (!response.ok)
      throw new ApiError(
        response.status,
        response.status === 401
          ? '登入已失效，請重新登入'
          : response.status === 404
            ? '找不到附件'
            : response.status === 403
              ? '沒有操作權限'
              : '附件下載失敗，請稍後重試',
      );
    return response.blob();
  },
  me: (signal?: AbortSignal) =>
    requestJson<SessionInfo>('/auth/me', { signal }),
  login: (
    payload: { organization_key: string; username: string; password: string },
    signal?: AbortSignal,
  ) =>
    requestJson<SessionInfo>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(payload),
      signal,
    }),
  logout: (signal?: AbortSignal) =>
    requestJson<void>('/auth/logout', { method: 'POST', signal }),
  projects: (signal?: AbortSignal) =>
    requestJson<{ items: ProjectSummary[] }>('/projects', { signal }),
  project: (id: string, signal?: AbortSignal) =>
    requestJson<ProjectDetail>(`/projects/${id}`, { signal }),
  createProject: (title: string, signal?: AbortSignal) =>
    requestJson<ProjectSummary>('/projects', {
      method: 'POST',
      body: JSON.stringify({ title }),
      signal,
    }),
  assignmentOptions: (id: string, signal?: AbortSignal) =>
    requestJson<AssignmentOptions>(`/projects/${id}/assignment-options`, {
      signal,
    }),
  createNode: (id: string, payload: NodeCreate, signal?: AbortSignal) =>
    requestJson<NodeItem>(`/projects/${id}/nodes`, {
      method: 'POST',
      body: JSON.stringify(payload),
      signal,
    }),
  updateNode: (
    id: string,
    payload: Partial<NodeMetadata>,
    signal?: AbortSignal,
  ) =>
    requestJson<NodeItem>(`/nodes/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
      signal,
    }),
  overview: (signal?: AbortSignal) =>
    requestJson<WorkspaceOverviewData>('/workspace/overview', { signal }),
  myTasks: (q: string, status: string, signal?: AbortSignal) =>
    requestJson<{ items: MyTask[] }>(
      `/workspace/my-tasks?${new URLSearchParams({ q: q.trim(), status })}`,
      { signal },
    ),
  updateNodeStatus: (id: string, status: NodeStatus, signal?: AbortSignal) =>
    requestJson<NodeItem>(`/nodes/${id}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
      signal,
    }),
  workflows: (signal?: AbortSignal) =>
    requestJson<{ items: WorkflowSummary[] }>('/workflows', { signal }),
  createFromWorkflow: (
    payload: { workflow_id: string; title: string },
    signal?: AbortSignal,
  ) =>
    requestJson<ProjectSummary>('/projects/from-workflow', {
      method: 'POST',
      body: JSON.stringify(payload),
      signal,
    }),
  approveGate: (id: string, signal?: AbortSignal) =>
    requestJson<GateItem>(`/gates/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ status: 'approved' }),
      signal,
    }),
};

export function useRequestScope() {
  const sequence = useRef(0);
  const controller = useRef<AbortController | null>(null);
  useEffect(
    () => () => {
      ++sequence.current;
      controller.current?.abort();
    },
    [],
  );
  function begin() {
    controller.current?.abort();
    const value = { id: ++sequence.current, controller: new AbortController() };
    controller.current = value.controller;
    return value;
  }
  function current(value: ReturnType<typeof begin>) {
    return value.id === sequence.current && !value.controller.signal.aborted;
  }
  return { begin, current };
}
export type RecordReload = (signal: AbortSignal) => Promise<void>;
export function recordError(error: unknown) {
  return error instanceof ApiError
    ? error.status === 0
      ? '連線中斷，請重新整理確認結果；不會自動重送'
      : error.message
    : '操作失敗，請重新整理確認結果';
}
export function useRecordMutation(reload: RecordReload, expired: () => void) {
  const scope = useRequestScope();
  const lock = useRef(false);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');
  async function execute(write?: (signal: AbortSignal) => Promise<unknown>) {
    if (lock.current || (saved && write)) return;
    const request = scope.begin();
    lock.current = true;
    setBusy(true);
    setError('');
    let committed = saved;
    try {
      if (write) {
        await write(request.controller.signal);
        if (!scope.current(request)) return;
        committed = true;
        setSaved(true);
      }
      await reload(request.controller.signal);
    } catch (value) {
      if (!scope.current(request)) return;
      if (value instanceof ApiError && value.status === 401) expired();
      else
        setError(committed ? '已儲存，資料重新載入失敗' : recordError(value));
    } finally {
      if (scope.current(request)) {
        lock.current = false;
        setBusy(false);
      }
    }
  }
  return { busy, saved, error, execute };
}
export function formatRecordTime(value: string | null | undefined) {
  if (!value) return '未設定';
  const date = new Date(value);
  return Number.isNaN(date.valueOf())
    ? '未設定'
    : new Intl.DateTimeFormat('zh-TW', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
      }).format(date);
}
