export type Role = 'admin' | 'project_owner' | 'reviewer' | 'member' | 'readonly';
export type NodeStatus = 'todo' | 'doing' | 'review' | 'done' | 'skipped';
export interface User { id: string; username: string; display_name: string; role: Role | string; }
export interface Organization { id: string; key: string; name: string; }
export interface SessionInfo { user: User; organization: Organization; showcase?: { active: boolean; companies: { key: string; name: string; industry: string }[] }; }
export interface ProjectSummary { id: string; title: string; organization_key: string; owner_user_id: string | null; }
export interface NodeItem {
  id: string; project_id: string; parent_id: string | null; kind: 'project' | 'phase' | 'task' | string;
  title: string; status: NodeStatus; owner_user_id: string | null; department_id: string | null; sort_order: number;
  start_date: string | null; due_date: string | null;
  milestone?: boolean; schedule_locked?: boolean;
  weight?: number; progress?: number | null;
  owner_display_name: string | null; department_name: string | null;
  capabilities: { edit_schedule?: boolean; lock_schedule?: boolean; edit_metadata: boolean; assign: boolean; create_child: boolean; write_record?: boolean; submit_report?: boolean; review_report?: boolean; manage_collaborators?: boolean; lifecycle?: boolean; move?: boolean; copy?: boolean; delete?: boolean };
  state_actions?: string[];
  blocked?: boolean;
}
/** TP-B structure changes answer with the audit id that `POST /undo` accepts (null when nothing changed). */
export type Undoable<T> = T & { undo_id: string | null };
export interface CopyResult extends NodeItem { undo_id: string; copied_count: number; }
export interface DeleteResult { undo_id: string; project_id: string; parent_id: string | null; deleted_count: number; }
export interface UndoResult { action: 'node.create' | 'node.delete' | 'node.move' | 'node.copy'; project_id: string; node_id: string; parent_id: string | null; }
export interface GateItem { id: string; project_id: string; node_id: string; status: 'pending' | 'approved'; }
export interface ProjectDetail extends ProjectSummary { nodes: NodeItem[]; gates: GateItem[]; capabilities: { create_node: boolean }; }
export type WorkspaceRoute = { page: 'overview' | 'my-tasks' | 'reviews' | 'audit' | 'workflows' } | { page: 'project'; projectId: string | null; nodeId: string | null };
export interface WorkflowSummary { phase_count?: number; task_count?: number; phase_titles?: string[]; id: string; name: string; requires_start_date?: boolean; capabilities?: { edit: boolean; copy: boolean }; }
export interface AssignmentOptions { users: { id: string; display_name: string }[]; departments: { id: string; name: string }[]; }
export interface NodeMetadata { title: string; owner_user_id: string | null; department_id: string | null; start_date: string | null; due_date: string | null; }
export interface NodeCreate extends NodeMetadata { milestone?: boolean; schedule_locked?: boolean; kind: 'phase' | 'task'; parent_id: string | null; }
export type NodeUpdate = Partial<NodeMetadata> & { milestone?: boolean; schedule_locked?: boolean; weight?: number; progress?: number | null };
export type TaskCounts = Record<NodeStatus, number>;
export interface OverviewProject { id: string; title: string; task_counts: TaskCounts; completion_percent: number | null; progress_percent?: number | null; current_phase_title?: string | null; due_date?: string | null; overdue_count?: number; }
export interface WorkloadPerson { user_id: string; display_name: string; department_name: string | null; open_count: number; overdue_count: number; }
export interface WorkspaceOverviewData { project_count: number; task_counts: TaskCounts; completion_percent: number | null; projects: OverviewProject[]; today?: string; overdue_count?: number; people?: WorkloadPerson[]; departments?: { id: string; name: string; open_count: number }[]; }
export interface MyTask extends NodeItem { project_title: string; relations?: ('owned' | 'collaborating')[]; path?: { id: string; title: string }[]; }

export interface Attachment { id: string; node_id: string; original_name: string; size_bytes: number; sha256: string; uploaded_by: string; uploaded_by_display_name: string | null; created_at: string; report_id: string | null; note_id: string | null; }
export interface Report { type: 'report'; id: string; node_id: string; node_title: string; version: number; legacy: boolean; result: string; summary: string; finished_on: string | null; status: string; submitted_by: string; submitted_by_display_name: string | null; submitted_at: string; reviewed_by_display_name: string | null; reviewed_at: string | null; review_comment: string | null; self_approved: boolean; attachments: Attachment[]; created_at: string; }
export interface Note { type: 'note'; id: string; node_id: string; node_title: string; body: string; author_id: string; author_display_name: string | null; revision: number; created_at: string; edited_at: string | null; attachments: Attachment[]; }
export type RecordItem = Report | Note | (Attachment & { type: 'attachment'; node_title: string });
export interface RecordPage { items: RecordItem[]; next_cursor: string | null; }
export interface Collaborators extends AssignmentOptions { revision: number; }
export interface Quota { limit_bytes: number; charged_bytes: number; remaining_bytes: number; }
export interface ReviewItem { type: 'report' | 'gate'; id: string; node_id: string; node_title: string; project_id: string; project_title: string; created_at: string; status: string; version?: number; result?: string; summary?: string; finished_on?: string | null; submitted_by?: string; submitted_by_display_name?: string | null; capabilities: { review_report?: boolean; approve_gate?: boolean }; }
export interface ReviewPage { items: ReviewItem[]; next_cursor: string | null; }
export interface AuditItem { id: string; action: string; summary: string; node_id: string | null; node_title: string | null; node_deleted?: boolean; project_id: string | null; project_title: string | null; actor_display_name: string | null; created_at: string; payload: Record<string, unknown>; }
export interface AuditPage { items: AuditItem[]; next_cursor: string | null; }
export interface WorkflowNode { id: string; parent_id: string | null; kind: 'phase' | 'task'; title: string; sort_order: number; gate_after: boolean; start_offset: number | null; due_offset: number | null; }
export interface DependencyInput { predecessor_id: string; successor_id: string; }
export interface WorkflowWrite { name: string; nodes: WorkflowNode[]; dependencies: DependencyInput[]; }
export interface WorkflowDetail extends WorkflowWrite { id: string; requires_start_date: boolean; capabilities: { edit: boolean; copy: boolean }; }
export interface WorkflowList { items: WorkflowSummary[]; capabilities?: { create: boolean }; }
export interface Dependency extends DependencyInput { id: string; project_id: string; }
export interface DependencyData { items: Dependency[]; nodes: { id: string; title: string; status: NodeStatus; blocked: boolean }[]; capabilities: { manage: boolean }; }

export interface CatalogEntry extends WorkflowWrite { key: string; industry: string; description: string; source: string; }
