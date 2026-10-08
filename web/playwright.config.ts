import { defineConfig } from '@playwright/test';

const baseURL = process.env.PF_BASE_URL || 'http://127.0.0.1:15175';
const target = new URL(baseURL);
if (target.protocol !== 'http:' || !['127.0.0.1', 'localhost', '[::1]'].includes(target.hostname)
  || target.port === '15173' || target.username || target.password || target.pathname !== '/') {
  throw new Error('E2E requires a loopback acceptance URL and refuses shared port 15173');
}

export default defineConfig({
  testDir: './e2e',
  workers: 1,
  retries: 0,
  use: {
    baseURL,
    browserName: 'chromium',
  },
});
