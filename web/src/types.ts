export type Role = 'admin' | 'project_owner' | 'reviewer' | 'member' | 'readonly';
export type NodeStatus = 'todo' | 'doing' | 'review' | 'done' | 'skipped';
export interface User { id: string; username: string; display_name: string; role: Role | string; }
export interface Organization { id: string; key: string; name: string; }
export interface SessionInfo { user: User; organization: Organization; }
export interface ProjectSummary { id: string; title: string; organization_key: string; owner_user_id: string | null; }
export interface NodeItem {
  id: string; project_id: string; parent_id: string | null; kind: 'project' | 'phase' | 'task' | string;
  title: string; status: NodeStatus; owner_user_id: string | null; department_id: string | null; sort_order: number;
  start_date: string | null; due_date: string | null;
  owner_display_name: string | null; department_name: string | null;
  capabilities: { edit_metadata: boolean; assign: boolean; create_child: boolean };
}
export interface GateItem { id: string; project_id: string; node_id: string; status: 'pending' | 'approved'; }
export interface ProjectDetail extends ProjectSummary { nodes: NodeItem[]; gates: GateItem[]; capabilities: { create_node: boolean }; }
export type WorkspaceRoute = { page: 'overview' | 'my-tasks' } | { page: 'project'; projectId: string | null; nodeId: string | null };
export interface WorkflowSummary { id: string; name: string; }
export interface AssignmentOptions { users: { id: string; display_name: string }[]; departments: { id: string; name: string }[]; }
export interface NodeMetadata { title: string; owner_user_id: string | null; department_id: string | null; start_date: string | null; due_date: string | null; }
export interface NodeCreate extends NodeMetadata { kind: 'phase' | 'task'; parent_id: string | null; }
export type TaskCounts = Record<NodeStatus, number>;
export interface WorkspaceOverviewData { project_count: number; task_counts: TaskCounts; completion_percent: number | null; projects: { id: string; title: string; task_counts: TaskCounts; completion_percent: number | null }[]; }
export interface MyTask extends NodeItem { project_title: string; }
