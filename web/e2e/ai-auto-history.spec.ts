import { expect, test } from '@playwright/test';
import { openSettings, openSources } from './copilot';

test.use(process.platform === 'win32' ? { channel: 'msedge' } : {});

for (const width of [1280, 375]) test(`automatic index and historical citations ${width}`, async ({ page }, info) => {
  test.setTimeout(90000);
  expect(await (await page.request.get('/api/health/acceptance')).json()).toEqual({ acceptance: true });
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(String(error)));
  await page.setViewportSize({ width, height: 900 });
  await page.goto('/');
  await page.getByLabel('帳號').fill('yu');
  await page.getByLabel('密碼').fill('demo-yu');
  await page.getByRole('button', { name: '登入', exact: true }).click();
  await expect(page.getByRole('heading', { name: '所有專案總覽' })).toBeVisible();
  const initial = await (await page.request.get('/api/ai/status?dataset=formal-v1')).json();
  expect(initial.index.automatic.enabled).toBe(true);
  const created = await page.request.post('/api/projects', { data: { title: `自動索引與版本展示 ${width} ${Date.now()}` } });
  expect(created.status()).toBe(201);
  const project = await created.json();
  const uploaded = await page.request.post(`/api/projects/${project.id}/documents?filename=${encodeURIComponent('報到地點版本說明.txt')}`, {
    data: Buffer.from('全部虛構。新人報到原訂在三樓人資部，請帶識別證。'), headers: { 'Content-Type': 'application/octet-stream' },
  });
  expect(uploaded.status()).toBe(201);
  const doc = await uploaded.json();
  async function sources(include_history = false) {
    const response = await page.request.post('/api/ai/ask', { data: { dataset: 'formal-v1', question: '新人報到', project_id: project.id, include_history } });
    expect(response.status()).toBe(200);
    return (await response.json()).sources as { version: number; is_current: boolean; document_id: string; excerpt: string }[];
  }
  // No manual-refresh API/button is used anywhere in this scenario.
  await expect.poll(async () => (await sources()).some(s => s.version === 1), { timeout: 30000, intervals: [500, 1000] }).toBe(true);
  const updated = await page.request.post(`/api/documents/${doc.document_id}/text`, { data: { expected_version: 1, content: '全部虛構。新人報到改在五樓人資部，請帶識別證。' } });
  expect(updated.status()).toBe(201);
  await expect.poll(async () => (await sources()).some(s => s.version === 2), { timeout: 30000, intervals: [500, 1000] }).toBe(true);
  expect((await sources()).every(s => s.is_current && s.version === 2)).toBe(true);
  const historical = await sources(true);
  expect(historical.some(s => s.version === 1 && !s.is_current)).toBe(true);
  const old = historical.find(s => !s.is_current)!;
  expect((await page.request.get(`/api/ai/documents/${old.document_id}?dataset=formal-v1`)).status()).toBe(404);
  await page.getByRole('button', { name: '切換 AI 副手' }).click();
  const panel = page.getByLabel('AI 專案副手', { exact: true });
  await openSettings(panel);
  await panel.getByLabel('AI資料集').selectOption('formal-v1');
  await openSettings(panel);
  await panel.getByLabel('查詢專案').selectOption(project.id);
  await openSettings(panel);
  await expect(panel.getByLabel('包含歷史版本')).not.toBeChecked();
  await openSettings(panel);
  await panel.getByLabel('包含歷史版本').check();
  await panel.getByLabel('詢問 AI').fill('新人報到');
  await panel.getByRole('button', { name: '預覽提供給模型的資料' }).click();
  await expect(panel.getByLabel('模型資料預覽', { exact: true })).toContainText('歷史版本');
  await panel.getByRole('button', { name: '送出 AI 問題' }).click();
  const oldSource = panel.locator('.ai-sources details').filter({ has: page.locator('summary', { hasText: '第1版／第1段（歷史版本）' }) });
  await openSources(panel);
  await oldSource.locator('summary').click();
  await oldSource.getByRole('button', { name: '開啟索引段落：報到地點版本說明.txt／1' }).click();
  await expect(panel.getByLabel('引用原文')).toContainText('三樓');
  await expect(panel.getByLabel('引用原文')).toContainText('歷史版本，請勿當作現行規定');
  // Allow subpixel rounding at the scroll boundary (Edge reports ~0.999 on 375px).
  await expect(panel.getByLabel('引用原文').getByText('第1版・歷史版本，請勿當作現行規定')).toBeInViewport({ ratio: 0.99 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect(await panel.evaluate(element => element.scrollWidth <= element.clientWidth)).toBe(true);
  await page.screenshot({ path: info.outputPath(`auto-history-${width}.png`), fullPage: true });
  await openSettings(panel);
  await panel.getByLabel('包含歷史版本').uncheck();
  await expect(panel.locator('.copilot-message')).toHaveCount(0);
  await expect(panel.getByLabel('引用原文')).toHaveCount(0);
  await panel.getByLabel('詢問 AI').fill('新人報到');
  await panel.getByRole('button', { name: '送出 AI 問題' }).click();
  await expect(panel.locator('.ai-sources')).toContainText('第2版');
  await expect(panel.locator('.ai-sources')).not.toContainText('歷史版本');
  await openSettings(panel);
  await panel.getByLabel('AI資料集').selectOption('starter-v1');
  await expect(panel.locator('.copilot-message')).toHaveCount(0);
  await expect(panel).toContainText('23 份可見文件');
  expect(errors).toEqual([]);
});
