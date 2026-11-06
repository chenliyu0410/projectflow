// Runs the Demo browser test page (tests/records.html) headless and fails on any failed test or console error.
// Usage: node .github/scripts/run_demo_tests.mjs [base URL]   (the repo must be served over HTTP, e.g. python -m http.server)
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const require = createRequire(fileURLToPath(new URL('../../web/package.json', import.meta.url)));
const { chromium } = require('playwright');
const base = process.argv[2] || 'http://127.0.0.1:8000';
const browser = await chromium.launch();
const page = await (await browser.newContext()).newPage();
const fonts = /fonts\.(googleapis|gstatic)\.com/; // fonts are blocked below; only their load errors are ignored
const errors = [];
page.on('console', (m) => m.type() === 'error' && !fonts.test(m.text()) && !fonts.test(m.location()?.url || '') && errors.push(m.text()));
page.on('pageerror', (e) => errors.push(String(e)));
await page.route(fonts, (r) => r.abort());
await page.goto(`${base}/tests/records.html?t=${Date.now()}`, { timeout: 60000 });
let timedOut = false;
try {
  await page.waitForSelector('#sum', { timeout: 30000 });
  await page.waitForFunction(() => !document.getElementById('sum').textContent.startsWith('執行中'), null, { timeout: 180000 });
} catch { timedOut = true; }
const summary = (await page.textContent('#sum')).trim();
const results = await page.evaluate(() => window.__results || []);
const failed = results.filter((x) => !x.ok);
console.log(summary);
for (const f of failed) console.log(`✗ ${f.name}\n${f.err}`);
console.log(`tests: ${results.length}, failed: ${failed.length}, console errors: ${errors.length}`);
for (const e of errors) console.log(`console: ${e}`);
await browser.close();
const ok = !timedOut && results.length > 0 && failed.length === 0 && errors.length === 0 && summary.startsWith('全部通過');
process.exit(ok ? 0 : 1);
