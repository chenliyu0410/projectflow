import type { NodeItem } from './types';
/** Explain the existing API rules without granting client-side permissions. */
export function childCreationReason(parent: NodeItem | null, permitted: boolean): string {
  if (!permitted) return '只有系統管理員或此專案負責人可以新增子任務';
  if (parent?.milestone) return '里程碑不能有子任務，請先取消里程碑';
  if (parent && ['review', 'done', 'skipped'].includes(parent.status)) return '不能在已完成、待確認或已略過的節點底下新增';
  return '';
}
