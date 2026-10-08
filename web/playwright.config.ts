import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  workers: 1,
  retries: 0,
  use: {
    baseURL: process.env.PF_BASE_URL || 'http://127.0.0.1:15173',
    browserName: 'chromium',
  },
});
