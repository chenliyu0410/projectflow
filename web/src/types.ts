export type Role = 'admin' | 'project_owner' | 'reviewer' | 'member' | 'readonly';
export type NodeStatus = 'todo' | 'doing' | 'review' | 'done' | 'skipped';
export interface User { id: string; username: string; display_name: string; role: Role | string; }
export interface Organization { id: string; key: string; name: string; }
export interface SessionInfo { user: User; organization: Organization; }
export interface ProjectSummary { id: string; title: string; organization_key: string; owner_user_id: string | null; }
export interface NodeItem {
  id: string; project_id: string; parent_id: string | null; kind: 'project' | 'phase' | 'task' | string;
  title: string; status: NodeStatus; owner_user_id: string | null; department_id: string | null; sort_order: number;
}
export interface GateItem { id: string; project_id: string; node_id: string; status: 'pending' | 'approved'; }
export interface ProjectDetail extends ProjectSummary { nodes: NodeItem[]; gates: GateItem[]; }
export interface WorkflowSummary { id: string; name: string; }
