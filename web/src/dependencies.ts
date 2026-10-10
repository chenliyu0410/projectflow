import type { DependencySettings } from './types';
export const dependencyLabel = (e: DependencySettings) => `${e.relation_type ?? 'FS'} · ${(e.lag_days ?? 0) >= 0 ? '+' : ''}${e.lag_days ?? 0} 天 · ${e.enforcement === 'soft' ? '軟性' : '硬性'}`;
export const dependencyMet = (e: DependencySettings, status?: string) => e.relation_type === 'SS' ? ['doing', 'review', 'done', 'skipped'].includes(status ?? '') : ['done', 'skipped'].includes(status ?? '');
export function dependencyShift(e: DependencySettings, a: {start: number; due: number}, b: {start: number; due: number}) {
  return (e.relation_type === 'SS' ? a.start - b.start : e.relation_type === 'FF' ? a.due - b.due : a.due + 1 - b.start) + (e.lag_days ?? 0);
}
