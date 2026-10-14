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

// jsdom does not implement the native dialog methods; browser tests verify modal focus.
if (!HTMLDialogElement.prototype.showModal) HTMLDialogElement.prototype.showModal = function () { this.setAttribute('open', ''); };
if (!HTMLDialogElement.prototype.close) HTMLDialogElement.prototype.close = function () { this.removeAttribute('open'); };
if (!window.matchMedia) window.matchMedia = (query: string) => ({matches:false,media:query,onchange:null,addListener() {},removeListener() {},addEventListener() {},removeEventListener() {},dispatchEvent:()=>true});
