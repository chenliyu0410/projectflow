import { requestJson } from './api';
export type GatewayInfo = { policy: 'local_only'; cloud_enabled: false; function: string; classification: 'public' | 'internal' | 'confidential'; classification_reason: string; route: 'none' | 'local' | 'blocked'; reason: string; outcome: 'not_sent' | 'completed' | 'failed'; source_count: number; sent_count?: number; model: string };
export type AIPreview = { gateway: GatewayInfo; content: null | { question: string; as_of?: string; sources?: { document_id: string; text: string; title?: string; project_id?: string | null; is_current?: boolean; version?: number | null }[]; queries?: { query_id: string; label: string }[] } };
type AIRequest = { question: string; mode: string; project_id: string | null; query_id?: string; dataset?: string; include_history?: boolean };
export type IndexStatus = { last_update?: { mode: 'initial' | 'incremental'; processed: number; reused: number; removed: number } | null; counts: { indexed: number; pending: number; skipped: number }; updated_at: string | null; can_refresh: boolean; automatic?: { enabled: boolean; interval_seconds: number; last_checked_at: string | null; last_error: string | null }; items: { source_id: string; title: string; source_type: string; version: number; is_current?: boolean; state: string; reason: string }[] };
export type AIStatus = { ready: boolean; as_of: string | null; company_name: string; model_enabled: boolean; model_name: string; can_configure: boolean; can_sql: boolean; projects: { project_id: string; title: string }[]; queries: { query_id: string; label: string }[]; counts: { projects?: number; documents?: number }; gateway?: Pick<GatewayInfo, 'policy' | 'cloud_enabled'>; formal_available?: boolean; index?: IndexStatus };
export type ModelConfig = { enabled: boolean; base_url: string; model: string };
export type AISource = { document_id: string; title: string; project_id: string | null; excerpt: string; is_current?: boolean; source_type?: string; version?: number; section?: number; node_id?: string | null };
export type AIResult = { kind: string; engine: string; answer: string; warning: string | null; sources: AISource[]; citations?: string[]; suggestion?: { query_id: string; label: string }; gateway?: GatewayInfo; analysis: null | { query_id: string; label: string; sql: string; parameters: Record<string, string | null>; columns: string[]; rows: Record<string, string | number | null>[]; truncated: boolean } };
export const ai = {
  status: (signal?: AbortSignal, dataset = 'dataset-v1') => requestJson<AIStatus>('/ai/status?dataset=' + encodeURIComponent(dataset), { signal }),
  ask: (body: AIRequest, signal?: AbortSignal) => requestJson<AIResult>('/ai/ask', { method: 'POST', body: JSON.stringify(body), signal }),
  preview: (body: AIRequest, signal?: AbortSignal) => requestJson<AIPreview>('/ai/preview', { method: 'POST', body: JSON.stringify(body), signal }),
  refreshIndex: (signal?: AbortSignal) => requestJson<IndexStatus>('/ai/index/refresh', { method: 'POST', signal }),
  document: (id: string, signal?: AbortSignal, dataset = 'dataset-v1', includeHistory = false) => requestJson<{ title: string; text: string; version?: number; is_current?: boolean }>('/ai/documents/' + encodeURIComponent(id) + '?dataset=' + encodeURIComponent(dataset) + (includeHistory ? '&include_history=true' : ''), { signal }),
  config: (signal?: AbortSignal) => requestJson<ModelConfig>('/ai/model', { signal }),
  save: (value: ModelConfig, signal?: AbortSignal) => requestJson<{ ok: boolean }>('/ai/model', { method: 'PUT', body: JSON.stringify(value), signal }),
  test: (value: ModelConfig, signal?: AbortSignal) => requestJson<{ ok: boolean; models: string[]; message: string }>('/ai/model/test', { method: 'POST', body: JSON.stringify(value), signal }),
};
