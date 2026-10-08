import type { AssignmentOptions, GateItem, MyTask, NodeCreate, NodeItem, NodeMetadata, NodeStatus, ProjectDetail, ProjectSummary, SessionInfo, WorkflowSummary, WorkspaceOverviewData } from './types';

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

export async function requestJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set('Content-Type', 'application/json');
  let response: Response;
  try {
    response = await fetch(`/api${path}`, { ...init, credentials: 'include', headers });
  } catch (error) {
    if (init.signal?.aborted) throw error;
    throw new ApiError(0, '無法連線，請稍後再試');
  }
  // Never display backend details, which may include validation input or secrets.
  if (!response.ok) {
    const message = response.status === 401
      ? path === '/auth/login' ? '帳號或密碼錯誤' : '登入已失效，請重新登入'
      : response.status === 403 ? '沒有操作權限' : response.status === 404 ? '找不到項目'
        : response.status === 422 && path !== '/auth/login' ? '請檢查欄位內容：名稱、日期或指派不符合規則' : '操作失敗，請稍後再試';
    throw new ApiError(response.status, message);
  }
  if (response.status === 204) return undefined as T;
  try { return await response.json() as T; }
  catch { throw new ApiError(response.status, '無法讀取資料，請稍後再試'); }
}

export const api = {
  me: (signal?: AbortSignal) => requestJson<SessionInfo>('/auth/me', { signal }),
  login: (payload: { organization_key: string; username: string; password: string }, signal?: AbortSignal) =>
    requestJson<SessionInfo>('/auth/login', { method: 'POST', body: JSON.stringify(payload), signal }),
  logout: (signal?: AbortSignal) => requestJson<void>('/auth/logout', { method: 'POST', signal }),
  projects: (signal?: AbortSignal) => requestJson<{ items: ProjectSummary[] }>('/projects', { signal }),
  project: (id: string, signal?: AbortSignal) => requestJson<ProjectDetail>(`/projects/${id}`, { signal }),
  createProject: (title: string, signal?: AbortSignal) => requestJson<ProjectSummary>('/projects', { method: 'POST', body: JSON.stringify({ title }), signal }),
  assignmentOptions: (id: string, signal?: AbortSignal) => requestJson<AssignmentOptions>(`/projects/${id}/assignment-options`, { signal }),
  createNode: (id: string, payload: NodeCreate, signal?: AbortSignal) => requestJson<NodeItem>(`/projects/${id}/nodes`, { method: 'POST', body: JSON.stringify(payload), signal }),
  updateNode: (id: string, payload: Partial<NodeMetadata>, signal?: AbortSignal) => requestJson<NodeItem>(`/nodes/${id}`, { method: 'PATCH', body: JSON.stringify(payload), signal }),
  overview: (signal?: AbortSignal) => requestJson<WorkspaceOverviewData>('/workspace/overview', { signal }),
  myTasks: (q: string, status: string, signal?: AbortSignal) => requestJson<{ items: MyTask[] }>(`/workspace/my-tasks?${new URLSearchParams({ q: q.trim(), status })}`, { signal }),
  updateNodeStatus: (id: string, status: NodeStatus, signal?: AbortSignal) =>
    requestJson<NodeItem>(`/nodes/${id}/status`, { method: 'PATCH', body: JSON.stringify({ status }), signal }),
  workflows: (signal?: AbortSignal) => requestJson<{ items: WorkflowSummary[] }>('/workflows', { signal }),
  createFromWorkflow: (payload: { workflow_id: string; title: string }, signal?: AbortSignal) =>
    requestJson<ProjectSummary>('/projects/from-workflow', { method: 'POST', body: JSON.stringify(payload), signal }),
  approveGate: (id: string, signal?: AbortSignal) =>
    requestJson<GateItem>(`/gates/${id}`, { method: 'PATCH', body: JSON.stringify({ status: 'approved' }), signal }),
};
