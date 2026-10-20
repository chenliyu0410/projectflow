import { useEffect } from 'react';

/** Forms that are open at the same time each register here; App asks all of them before navigating away. */
export type LeaveGuards = { current: Set<() => boolean> };

export function useLeaveGuard(guards: LeaveGuards | undefined, dirty: boolean, message: string) {
  useEffect(() => {
    if (!guards || !dirty) return;
    const guard = () => window.confirm(message);
    const unload = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ''; };
    guards.current.add(guard);
    window.addEventListener('beforeunload', unload);
    return () => { guards.current.delete(guard); window.removeEventListener('beforeunload', unload); };
  }, [guards, dirty, message]);
}

export function canLeaveAll(guards: LeaveGuards) {
  // 逐一詢問，任何一個表單選擇留下就停止，不再多跳後面的確認框。
  for (const guard of guards.current) if (!guard()) return false;
  return true;
}
