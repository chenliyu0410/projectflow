import type { ProjectSummary, SessionInfo } from './types';

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
      : response.status === 403 ? '沒有操作權限' : '操作失敗，請稍後再試';
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
};
