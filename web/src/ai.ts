import { requestJson } from './api';
export type AIStatus = { ready: boolean; as_of: string; company_name: string; model_enabled: boolean; model_name: string; can_configure: boolean; can_sql: boolean; projects: { project_id: string; title: string }[]; queries: { query_id: string; label: string }[]; counts: { projects?: number; documents?: number } };
export type ModelConfig = { enabled: boolean; base_url: string; model: string };
export type AISource = { document_id: string; title: string; project_id: string | null; excerpt: string; is_current?: boolean };
export type AIResult = { kind: string; engine: string; answer: string; warning: string | null; sources: AISource[]; citations?: string[]; suggestion?: { query_id: string; label: string }; analysis: null | { query_id: string; label: string; sql: string; parameters: Record<string, string | null>; columns: string[]; rows: Record<string, string | number | null>[]; truncated: boolean } };
export const ai = {
  status: (signal?: AbortSignal, dataset = 'dataset-v1') => requestJson<AIStatus>('/ai/status?dataset=' + encodeURIComponent(dataset), { signal }),
  ask: (body: { question: string; mode: string; project_id: string | null; query_id?: string; dataset?: string; include_history?: boolean }, signal?: AbortSignal) => requestJson<AIResult>('/ai/ask', { method: 'POST', body: JSON.stringify(body), signal }),
  document: (id: string, signal?: AbortSignal, dataset = 'dataset-v1') => requestJson<{ title: string; text: string }>('/ai/documents/' + encodeURIComponent(id) + '?dataset=' + encodeURIComponent(dataset), { signal }),
  config: (signal?: AbortSignal) => requestJson<ModelConfig>('/ai/model', { signal }),
  save: (value: ModelConfig, signal?: AbortSignal) => requestJson<{ ok: boolean }>('/ai/model', { method: 'PUT', body: JSON.stringify(value), signal }),
  test: (value: ModelConfig, signal?: AbortSignal) => requestJson<{ ok: boolean; models: string[]; message: string }>('/ai/model/test', { method: 'POST', body: JSON.stringify(value), signal }),
};
