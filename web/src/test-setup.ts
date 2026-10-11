import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach, beforeEach, vi } from 'vitest';
import { ai } from './ai';

// Existing workflow tests own their fetch queues; AI has its own contract tests.
beforeEach(() => {
  vi.spyOn(ai, 'status').mockResolvedValue({ ready: false, as_of: '2026-10-11', company_name: '測試公司', model_enabled: false, model_name: '', can_configure: false, can_sql: false, projects: [], queries: [], counts: {} });
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
