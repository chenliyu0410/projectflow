import type { TemplateVersion, TemplateApplyResult, TemplateApplyInput, CatalogEntry, WorkflowDetail, WorkflowWrite, WorkflowList, DependencyData, DependencyInput, Dependency, Undoable, CopyResult, DeleteResult, UndoResult } from './types';
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
  NodeStatus,
  NodeUpdate,
  ProjectDetail,
  ProjectSummary,
  SessionInfo,
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

// Fixed TP-A/TP-B conflict texts may be shown as-is; any other backend detail stays hidden.
export const KNOWN_CONFLICTS = new Set([
  '回報欄位已變更，請重新載入', '回報欄位已變更，請重新載入並確認輸入', '只有未關閉且沒有待確認回報的葉任務可設定欄位',
  '申請已失效結案，請重新申請', '跳過後已有修改，無法整組恢復', '已有待審核申請', '申請已處理，請重新整理', '部門仍有資料引用，請先移轉', '已有同名部門', '部門資料已變更，請重新整理',

  '後續任務有無法調整的項目，請由專案負責人確認',
  '里程碑不能有子任務，請先取消里程碑',
  '日期早於自己或上層的前置任務，請先調整排程',
  '時程相依或階層無法計算，請先檢查連線',
  '順延日期超出允許範圍',
  '子節點尚未全部完成',
  '不能移到自己的子任務底下',
  '不能移到已完成、待確認或已略過的任務底下',
  '移動後會和前置相依衝突，請先移除相依連線',
  '不能在已完成、待確認或已略過的節點底下新增',
  '上層已完成、待確認或已略過，請先重新開啟上層',
  '此節點底下有你看不到的子任務，無法刪除',
  '此節點底下有你看不到的子任務，無法複製',
  '只能復原最近一次的結構操作',
  '之後已有其他變更，無法復原',
  '原本的上層已無法放回，無法復原',
  '相關任務已有變更，無法復原',
  '此節點底下有你看不到的子任務，無法移動',
]);

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
    if (response.status === 409) {
      let detail: unknown;
      try {
        detail = ((await response.json()) as { detail?: unknown } | null)?.detail;
      } catch {
        detail = undefined;
      }
      if (typeof detail === 'string' && KNOWN_CONFLICTS.has(detail))
        throw new ApiError(409, detail);
    }
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
                      ? path.includes('/workflows') ||
                        path.includes('/from-workflow') ||
                        path.includes('/dependencies')
                        ? '請檢查名稱、模板階層、日期與前置設定是否符合規則'
                        : /^\/nodes\/[^/]+\/copy$/.test(path)
                          ? '子樹超過 300 個節點，無法複製'
                          : path.includes('/workspace/reviews') ||
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
  departments: (signal?: AbortSignal) => requestJson<import('./types').DepartmentData>('/departments', {signal}),
  saveDepartment: (id: string | null, payload: Omit<import('./types').DepartmentItem, 'id'>) => requestJson(id ? `/departments/${id}` : '/departments', {method:id ? 'PATCH' : 'POST',body:JSON.stringify(payload)}),
  deleteDepartment: (id: string) => requestJson(`/departments/${id}`, {method:'DELETE'}),
  collaborationRequests: (signal?: AbortSignal) => requestJson<{items: import('./types').CollaborationRequest[]}>('/workspace/requests', {signal}),
  requestException: (id: string, kind: string, reason: string, direct: boolean, signal?: AbortSignal) => requestJson(`/nodes/${id}/requests`, {method:'POST',body:JSON.stringify({kind,reason,direct}),signal}),
  decideException: (id: string, decision: string, comment: string, signal?: AbortSignal) => requestJson(`/requests/${id}/decision`, {method:'POST',body:JSON.stringify({decision,comment}),signal}),
  notifications: (offset=0, signal?: AbortSignal) => requestJson<import('./types').NotificationPage>(`/notifications?offset=${offset}`, {signal}),
  readNotification: (id: string) => requestJson(`/notifications/${id}/read`, {method:'POST'}),

  workflow: (id: string, signal?: AbortSignal) =>
    requestJson<WorkflowDetail>(`/workflows/${id}`, { signal }),
  templateVersions: (id: string, signal?: AbortSignal) => requestJson<{items: TemplateVersion[]}>(`/workflows/${id}/versions`, {signal}),
  templateVersion: (id: string, version: number, signal?: AbortSignal) => requestJson<WorkflowDetail>(`/workflows/${id}/versions/${version}`, {signal}),
  deleteTemplate: (id: string, signal?: AbortSignal) => requestJson<{deleted: boolean}>(`/workflows/${id}`, {method:'DELETE', signal}),
  saveTemplate: (target: string, payload: {name: string; template_id?: string; expected_version?: number}, signal?: AbortSignal) => requestJson<WorkflowDetail>(`${target}/save-template`, {method:'POST', body:JSON.stringify(payload), signal}),
  applyTemplate: (target: string, payload: TemplateApplyInput, signal?: AbortSignal) => requestJson<TemplateApplyResult>(`${target}/apply-template`, {method:'POST', body:JSON.stringify(payload), signal}),
  saveWorkflow: (
    id: string | null,
    payload: WorkflowWrite,
    signal?: AbortSignal,
  ) =>
    requestJson<WorkflowDetail>(id ? `/workflows/${id}` : '/workflows', {
      method: id ? 'PUT' : 'POST',
      body: JSON.stringify(payload),
      signal,
    }),
  copyWorkflow: (id: string, name: string, signal?: AbortSignal) =>
    requestJson<WorkflowDetail>(`/workflows/${id}/copy`, {
      method: 'POST',
      body: JSON.stringify({ name }),
      signal,
    }),
  dependencies: (id: string, signal?: AbortSignal) =>
    requestJson<DependencyData>(`/projects/${id}/dependencies`, { signal }),
  addDependency: (id: string, payload: DependencyInput, signal?: AbortSignal) =>
    requestJson<Dependency>(`/projects/${id}/dependencies`, {
      method: 'POST',
      body: JSON.stringify(payload),
      signal,
    }),
  updateDependency: (id: string, payload: import('./types').DependencySettings, signal?: AbortSignal) => requestJson<import('./types').Dependency>(`/dependencies/${id}`, { method: 'PATCH', body: JSON.stringify(payload), signal }),
  addCondition: (id: string, payload: {node_id: string; label: string; enforcement: 'hard' | 'soft'}, signal?: AbortSignal) => requestJson<import('./types').ManualCondition>(`/projects/${id}/conditions`, {method: 'POST', body: JSON.stringify(payload), signal}),
  updateCondition: (id: string, payload: {label: string; enforcement: 'hard' | 'soft'}, signal?: AbortSignal) => requestJson<import('./types').ManualCondition>(`/conditions/${id}`, {method: 'PATCH', body: JSON.stringify(payload), signal}),
  confirmCondition: (id: string, payload: {is_met: boolean; reason: string}, signal?: AbortSignal) => requestJson<import('./types').ManualCondition>(`/conditions/${id}/confirmation`, {method: 'POST', body: JSON.stringify(payload), signal}),
  removeCondition: (id: string, signal?: AbortSignal) => requestJson(`/conditions/${id}`, {method: 'DELETE', signal}),
  removeDependency: (id: string, signal?: AbortSignal) =>
    requestJson<{ deleted: boolean }>(`/dependencies/${id}`, {
      method: 'DELETE',
      signal,
    }),

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
  projectRecords: (
    id: string,
    cursor: string | null = null,
    limit = 50,
    signal?: AbortSignal,
  ) =>
    requestJson<RecordPage>(
      `/projects/${id}/records?${new URLSearchParams({ limit: String(limit), ...(cursor ? { cursor } : {}) })}`,
      { signal },
    ),
  reportFields: (id: string, signal?: AbortSignal) => requestJson<import('./types').ReportFieldSet>(`/nodes/${id}/report-fields`, {signal}),
  saveReportFields: (id: string, expected_version: number, fields: import('./types').ReportField[], signal?: AbortSignal) => requestJson<import('./types').ReportFieldSet>(`/nodes/${id}/report-fields`, {method: 'PUT', body: JSON.stringify({expected_version, fields}), signal}),
  report: (
    id: string,
    payload: {
      result: string;
      summary: string;
      finished_on: string;
      attachment_ids: string[];
      fields_version?: number; field_values?: Record<string, string>;
      self_approve: boolean; override_reason?: string; request_override?: boolean;
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
    override_reason?: string,
  ) =>
    requestJson<Report>(`/reports/${id}/review`, {
      method: 'POST',
      body: JSON.stringify({ decision, comment, ...(override_reason ? {override_reason} : {}) }),
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
  workflowCatalog: (signal?: AbortSignal) => requestJson<{items: CatalogEntry[]; can_import: boolean}>('/workflow-catalog', {signal}),
  switchCompany: (organization_key: string, signal?: AbortSignal) => requestJson<SessionInfo>('/auth/showcase/switch', {method: 'POST', body: JSON.stringify({organization_key}), signal}),
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
    requestJson<Undoable<NodeItem>>(`/projects/${id}/nodes`, {
      method: 'POST',
      body: JSON.stringify(payload),
      signal,
    }),
  updateSchedule: (id: string, payload: { start_date: string | null; due_date: string | null; cascade: boolean }, signal?: AbortSignal) =>
    requestJson<{ node: NodeItem; shifted_count: number }>(`/nodes/${id}/schedule`, { method: 'POST', body: JSON.stringify(payload), signal }),
  updateNode: (id: string, payload: NodeUpdate, signal?: AbortSignal) =>
    requestJson<NodeItem>(`/nodes/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
      signal,
    }),
  /** `parentId` null moves the task to the project's top level. */
  moveNode: (id: string, parentId: string | null, signal?: AbortSignal) =>
    requestJson<Undoable<NodeItem>>(`/nodes/${id}/move`, {
      method: 'POST',
      body: JSON.stringify({ parent_id: parentId }),
      signal,
    }),
  copyNode: (id: string, signal?: AbortSignal) =>
    requestJson<CopyResult>(`/nodes/${id}/copy`, { method: 'POST', signal }),
  deleteNode: (id: string, signal?: AbortSignal) =>
    requestJson<DeleteResult>(`/nodes/${id}`, { method: 'DELETE', signal }),
  undo: (auditId: string, signal?: AbortSignal) =>
    requestJson<UndoResult>('/undo', {
      method: 'POST',
      body: JSON.stringify({ audit_id: auditId }),
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
    requestJson<WorkflowList>('/workflows', { signal }),
  createFromWorkflow: (
    payload: { workflow_id: string; title: string; start_date?: string },
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
