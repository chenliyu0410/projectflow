import { requestJson } from './api';
export type Level = 'public' | 'internal' | 'confidential';
export type CloudPlan = { eligible: boolean; reason: string; masked: boolean; provider: null; sent: false; masked_counts?: Record<string, number> };
export type GatewayInfo = { policy: 'local_only'; cloud_enabled: false; function: string; classification: Level; classification_reason: string; route: 'none' | 'local' | 'blocked'; reason: string; outcome: 'not_sent' | 'completed' | 'failed'; source_count: number; sent_count?: number; model: string; ai_policy?: string; cloud?: CloudPlan };
type PreviewContent = { question: string; as_of?: string; sources?: { document_id: string; text: string; title?: string; project_id?: string | null; is_current?: boolean; version?: number | null }[]; queries?: { query_id: string; label: string }[] };
export type AIPreview = { gateway: GatewayInfo; content: null | PreviewContent; cloud_content?: null | PreviewContent };
type AIRequest = { question: string; mode: string; project_id: string | null; query_id?: string; dataset?: string; include_history?: boolean; history?: string[] };
export type IndexStatus = { last_update?: { mode: 'initial' | 'incremental'; processed: number; reused: number; removed: number } | null; counts: { indexed: number; pending: number; skipped: number; disabled?: number }; updated_at: string | null; can_refresh: boolean; automatic?: { enabled: boolean; interval_seconds: number; last_checked_at: string | null; last_error: string | null }; items: { source_id: string; title: string; source_type: string; version: number; is_current?: boolean; state: string; reason: string }[] };
export type AIStatus = { ready: boolean; as_of: string | null; company_name: string; model_enabled: boolean; model_name: string; can_configure: boolean; can_sql: boolean; projects: { project_id: string; title: string }[]; queries: { query_id: string; label: string }[]; counts: { projects?: number; documents?: number }; gateway?: Pick<GatewayInfo, 'policy' | 'cloud_enabled'>; formal_available?: boolean; index?: IndexStatus; vectors?: { enabled: boolean; model: string } };
export type ModelConfig = { enabled: boolean; base_url: string; model: string };
export type DocumentRef = { kind: 'document'; document_id: string; version: number } | { kind: 'attachment'; attachment_id: string };
/** Where a formal source can be read and downloaded; only formal documents carry it. */
export type SourcePlace = { document_ref?: DocumentRef; project_title?: string; node_title?: string | null; page?: number | null };
export type AISource = SourcePlace & { document_id: string; title: string; project_id: string | null; excerpt: string; is_current?: boolean; source_type?: string; version?: number; section?: number; node_id?: string | null };
export type SourceText = SourcePlace & { title: string; text: string; version?: number; is_current?: boolean; section?: number };
export type Rating = 'helpful' | 'unhelpful';
export type KnowledgeItem = { document_id: string; ai_enabled: boolean; state: 'indexed' | 'pending' | 'skipped' | 'disabled'; reason: string; indexed_version: number | null };
export type Knowledge = { items: KnowledgeItem[]; can_write: boolean; automatic: boolean };
export type AIResult = { kind: string; engine: string; answer: string; answer_id?: string; followup?: 'none' | 'model' | 'combined' | 'clarification'; standalone_question?: string | null; warning: string | null; sources: AISource[]; citations?: string[]; suggestion?: { query_id: string; label: string }; gateway?: GatewayInfo; retrieval?: 'keyword' | 'hybrid' | 'keyword_fallback'; analysis: null | { query_id: string; label: string; sql: string; parameters: Record<string, string | null>; columns: string[]; rows: Record<string, string | number | null>[]; truncated: boolean } };
export type ClassifiedItem = { scope: 'project' | 'node' | 'document'; id: string; title: string; own: Level | null; effective: Level; inherited: Level; project_id?: string; parent_id?: string | null; node_id?: string | null };
export type Governance = { mode: 'local_only' | 'mixed' | 'cloud_allowed'; company: Level; cloud_provider: null; can_set_policy: boolean; projects: ClassifiedItem[]; nodes: ClassifiedItem[]; documents: ClassifiedItem[]; recent: { action: string; created_at: string; dataset?: string; kind?: string; scope?: string; from?: string | null; to?: string; classification?: Level | null; cloud?: CloudPlan | null }[] };
export const ai = {
  status: (signal?: AbortSignal, dataset = 'dataset-v1') => requestJson<AIStatus>('/ai/status?dataset=' + encodeURIComponent(dataset), { signal }),
  // 本地模型回答、遮罩檢索與重建索引都可能超過一般請求的 30 秒上限。
  ask: (body: AIRequest, signal?: AbortSignal) => requestJson<AIResult>('/ai/ask', { method: 'POST', body: JSON.stringify(body), signal, timeoutMs: 180_000 }),
  preview: (body: AIRequest, signal?: AbortSignal) => requestJson<AIPreview>('/ai/preview', { method: 'POST', body: JSON.stringify(body), signal, timeoutMs: 180_000 }),
  refreshIndex: (signal?: AbortSignal) => requestJson<IndexStatus>('/ai/index/refresh', { method: 'POST', signal, timeoutMs: 180_000 }),
  document: (id: string, signal?: AbortSignal, dataset = 'dataset-v1', includeHistory = false) => requestJson<SourceText>('/ai/documents/' + encodeURIComponent(id) + '?dataset=' + encodeURIComponent(dataset) + (includeHistory ? '&include_history=true' : ''), { signal }),
  config: (signal?: AbortSignal) => requestJson<ModelConfig>('/ai/model', { signal }),
  save: (value: ModelConfig, signal?: AbortSignal) => requestJson<{ ok: boolean }>('/ai/model', { method: 'PUT', body: JSON.stringify(value), signal }),
  test: (value: ModelConfig, signal?: AbortSignal) => requestJson<{ ok: boolean; models: string[]; message: string }>('/ai/model/test', { method: 'POST', body: JSON.stringify(value), signal }),
  governance: (signal?: AbortSignal) => requestJson<Governance>('/ai/governance', { signal }),
  classify: (body: { scope: string; id?: string; level: Level | 'inherit' }, signal?: AbortSignal) => requestJson<{ ok: boolean }>('/ai/classification', { method: 'PUT', body: JSON.stringify(body), signal }),
  setPolicy: (mode: Governance['mode'], signal?: AbortSignal) => requestJson<{ ok: boolean }>('/ai/policy', { method: 'PUT', body: JSON.stringify({ mode }), signal }),
  maskPreview: (text: string, signal?: AbortSignal) => requestJson<{ masked: string; counts: Record<string, number> }>('/ai/mask-preview', { method: 'POST', body: JSON.stringify({ text }), signal }),
  feedback: (answerId: string, rating: Rating, signal?: AbortSignal) => requestJson<{ ok: boolean; rating: Rating }>('/ai/answers/' + encodeURIComponent(answerId) + '/feedback', { method: 'PUT', body: JSON.stringify({ rating }), signal }),
  feedbackSummary: (signal?: AbortSignal) => requestJson<{ days: number; helpful: number; unhelpful: number; total_answers: number }>('/ai/feedback/summary', { signal }),
  /** scopePath is the document list's own path: /nodes/<id> or /projects/<id>. */
  knowledge: (scopePath: string, signal?: AbortSignal) => {
    const [, kind, id] = scopePath.split('/');
    return requestJson<Knowledge>('/ai/knowledge?' + new URLSearchParams({ [kind === 'projects' ? 'project_id' : 'node_id']: id }), { signal });
  },
  setKnowledge: (documentId: string, enabled: boolean, signal?: AbortSignal) => requestJson<KnowledgeItem>('/ai/knowledge/' + encodeURIComponent(documentId), { method: 'PUT', body: JSON.stringify({ enabled }), signal }),
};
/** Download links use the documents and attachments routes, which check read permission themselves. */
export function downloadPath(ref: DocumentRef) {
  return ref.kind === 'document' ? `/api/documents/${encodeURIComponent(ref.document_id)}/versions/${ref.version}/download` : `/api/attachments/${encodeURIComponent(ref.attachment_id)}/download`;
}
