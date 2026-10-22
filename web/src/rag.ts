import { requestJson } from './api';
export type Locator = { page?: number; section?: string; start_char?: number; end_char?: number };
export type RagDocument = { document_id: string; version: number; title: string; node_id: string | null; can_index: boolean; state: string; indexed_version: number | null; chunk_count: number; error_code: string | null; enabled: boolean };
export type RagStatus = { project_id: string | null; projects: { project_id: string; title: string }[]; can_configure: boolean; model: { enabled: boolean; name: string; embedding_model: string }; documents: RagDocument[]; counts: Record<string, number> };
export type RagConfig = { enabled: boolean; base_url: string; model: string; embedding_model: string };
export type RagSource = { source_id: string; chunk_id: string; document_id: string; version: number; title: string; project_id: string; node_id: string | null; excerpt: string; locator: Locator };
export type RagResult = { query_id: string; project_id: string; kind: string; engine: string; answer: string; warning: string | null; citations: string[]; sources: RagSource[]; retrieval_mode: string; synthetic: false; source_mode: 'formal' };
export type RagOriginal = { document_id: string; version: number; title: string; text: string; locator: Locator; is_current: boolean; download_url: string };
const json = (method: string, body: unknown, signal?: AbortSignal) => ({ method, body: JSON.stringify(body), signal });
export const rag = {
  status: (project: string, signal?: AbortSignal) => requestJson<RagStatus>('/rag/status' + (project ? '?project_id=' + encodeURIComponent(project) : ''), { signal }),
  index: (id: string, signal?: AbortSignal) => requestJson<RagDocument>('/rag/documents/' + encodeURIComponent(id) + '/index', { method: 'POST', signal, timeoutMs: 180_000 }),
  enable: (id: string, enabled: boolean, signal?: AbortSignal) => requestJson<{ ok: boolean }>('/rag/documents/' + encodeURIComponent(id) + '/enabled', json('PUT', { enabled }, signal)),
  ask: (body: { project_id: string; question: string; previous_question?: string }, signal?: AbortSignal) => requestJson<RagResult>('/rag/ask', { ...json('POST', body, signal), timeoutMs: 180_000 }),
  source: (query: string, source: string, signal?: AbortSignal) => requestJson<RagOriginal>('/rag/queries/' + encodeURIComponent(query) + '/sources/' + encodeURIComponent(source), { signal }),
  feedback: (query: string, rating: 'helpful' | 'unhelpful', signal?: AbortSignal) => requestJson<{ ok: boolean }>('/rag/queries/' + encodeURIComponent(query) + '/feedback', json('PUT', { rating }, signal)),
  config: (signal?: AbortSignal) => requestJson<RagConfig>('/rag/model', { signal }),
  save: (config: RagConfig, signal?: AbortSignal) => requestJson<unknown>('/rag/model', json('PUT', config, signal)),
};
