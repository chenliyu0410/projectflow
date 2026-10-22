import { ApiError, ApiTimeoutError, requestJson } from './api';
export type Locator = { page?: number; section?: string; start_char?: number; end_char?: number };
export type RagScope = { kind: 'project'; project_id: string } | { kind: 'all_visible' };
export type TurnContext = { question: string; query_id?: string };
export type RagCoverage = { ready: number; queued: number; processing: number; failed: number; unsupported: number; disabled: number; partial: boolean };
export type RagDocument = { document_id: string; version: number; title: string; project_id?: string; project_title?: string; node_id: string | null; can_index: boolean; state: string; indexed_version: number | null; chunk_count: number; error_code: string | null; enabled: boolean };
export type RagStatus = { project_id: string | null; projects: { project_id: string; title: string }[]; can_configure: boolean; model: { enabled: boolean; name: string; embedding_model: string }; documents: RagDocument[]; counts: Record<string, number>; coverage?: RagCoverage };
export type RagConfig = { enabled: boolean; base_url: string; model: string; embedding_model: string };
export type RagSource = { source_id: string; chunk_id: string; document_id: string; version: number; title: string; project_id: string; project_title?: string; node_id: string | null; excerpt: string; locator: Locator };
export type RagResult = { query_id: string; project_id: string | null; kind: string; engine: string; answer: string; warning: string | null; citations: string[]; sources: RagSource[]; blocks?: { text: string; source_ids: string[] }[]; scope?: RagScope; code?: string | null; coverage?: RagCoverage; retrieval_mode: string; synthetic: false; source_mode: 'formal' };
export type RagOriginal = { document_id: string; project_id?: string; project_title?: string; version: number; title: string; text: string; locator: Locator; is_current: boolean; download_url: string };
export const ragMessages: Record<string, string> = {
 no_documents: '這個範圍尚無可查詢文件，請在專案文件區上傳文件。', no_sources: '目前文件沒有找到相關證據，請補充問題或調整範圍。', index_pending: '文件正在準備索引，請稍後再試。', partial_coverage: '部分文件尚未就緒，本次僅查詢可用文件。', embedding_unavailable: '向量模型暫時不可用，本次使用關鍵字檢索。', generation_unavailable: '未產生回答，以下是檢索原文；可稍後重試。', generation_timeout: '模型整理逾時，未產生回答，以下是檢索原文。', scope_limit: '可查詢文件過多，請縮小到單一專案。', source_changed: '來源已有新版，本次追問會重新查詢現行文件。', access_changed: '權限已變更，已移除受限回答；請開始新對話。', clarification_required: '請補充要詢問的對象或階段。',
};
const json = (method: string, body: unknown, signal?: AbortSignal) => ({ method, body: JSON.stringify(body), signal });
// RAG-specific errors accept only machine codes; never expose provider or validation details.
async function askRequest(body: unknown, signal?: AbortSignal): Promise<RagResult> {
 const controller = new AbortController(); let timedOut = false;
 const abort = () => controller.abort(); signal?.addEventListener('abort', abort, { once: true }); if (signal?.aborted) abort();
 const timer = setTimeout(() => { timedOut = true; controller.abort(); }, 180000);
 try {
  const response = await fetch('/api/rag/ask', { ...json('POST', body, controller.signal), credentials: 'include', headers: { 'Content-Type': 'application/json' } });
  if (!response.ok) { let detail: unknown; try { detail = (await response.json())?.detail; } catch { /* safe generic message */ }
   throw new ApiError(response.status, response.status === 401 ? '登入已失效，請重新登入' : response.status === 403 ? '沒有操作權限' : response.status === 404 ? '找不到文件或已無存取權限' : typeof detail === 'string' && ragMessages[detail] ? ragMessages[detail] : '正式文件查詢失敗，請稍後重試。');
  }
  return await response.json() as RagResult;
 } catch (e) { if (timedOut) throw new ApiTimeoutError(); if (controller.signal.aborted || e instanceof ApiError) throw e; throw new ApiError(0, '無法連線，請稍後再試'); }
 finally { clearTimeout(timer); signal?.removeEventListener('abort', abort); }
}
export function sourceDownloadPath(path: string) {
 // The server returns /documents/...; reject foreign origins, queries and traversal.
 if (!/^\/(?:api\/)?documents\/[a-zA-Z0-9-]+\/versions\/\d+\/download$/.test(path)) throw new Error('文件下載位置無效。');
 return path.startsWith('/api/') ? path : '/api' + path;
}
export const rag = {
 status: (scope: RagScope | string, signal?: AbortSignal) => requestJson<RagStatus>('/rag/status' + (typeof scope === 'string' ? (scope ? '?project_id=' + encodeURIComponent(scope) : '?scope_kind=all_visible') : scope.kind === 'project' ? '?project_id=' + encodeURIComponent(scope.project_id) : '?scope_kind=all_visible'), { signal }),
 index: (id: string, signal?: AbortSignal) => requestJson<RagDocument>('/rag/documents/' + encodeURIComponent(id) + '/index', { method: 'POST', signal, timeoutMs: 180_000 }),
 enable: (id: string, enabled: boolean, signal?: AbortSignal) => requestJson<{ ok: boolean }>('/rag/documents/' + encodeURIComponent(id) + '/enabled', json('PUT', { enabled }, signal)),
 ask: (body: { scope: RagScope; question: string; history?: TurnContext[] } | { project_id: string; question: string; previous_question?: string }, signal?: AbortSignal) => askRequest(body, signal),
 revalidate: (query_ids: string[], signal?: AbortSignal) => requestJson<{ queries: { query_id: string; status: 'visible' | 'unavailable' | 'source_changed' }[] }>('/rag/queries/revalidate', json('POST', { query_ids }, signal)),
 source: (query: string, source: string, signal?: AbortSignal) => requestJson<RagOriginal>('/rag/queries/' + encodeURIComponent(query) + '/sources/' + encodeURIComponent(source), { signal }),
 feedback: (query: string, rating: 'helpful' | 'unhelpful', signal?: AbortSignal) => requestJson<{ ok: boolean }>('/rag/queries/' + encodeURIComponent(query) + '/feedback', json('PUT', { rating }, signal)),
 config: (signal?: AbortSignal) => requestJson<RagConfig>('/rag/model', { signal }),
 save: (config: RagConfig, signal?: AbortSignal) => requestJson<unknown>('/rag/model', json('PUT', config, signal)),
};
