import { test, expect } from '@playwright/test';

for (const width of [1280, 375]) test(`persistent operation links ${width}`, async ({ page, request }, info) => {
  test.setTimeout(60000);
  expect(await (await request.get('/api/health/acceptance')).json()).toEqual({ acceptance: true });
  await page.setViewportSize({ width, height: 900 });
  const errors: string[] = []; page.on('pageerror', e => errors.push(String(e)));
  await page.goto('/');
  await page.getByLabel('帳號').fill('yu'); await page.getByLabel('密碼').fill('demo-yu');
  await page.getByRole('button', { name: '登入', exact: true }).click();
  await expect(page.getByRole('heading', { name: '所有專案總覽' })).toBeVisible();
  async function enter() {
    if (width === 375) await page.getByRole('button', { name: '切換導覽' }).click();
    await page.getByLabel('專案清單').getByRole('button').first().click();
    await page.getByRole('tab', { name: '資料', exact: true }).click();
    await expect(page.getByRole('heading', { name: '關聯營運資料' })).toBeVisible();
  }
  await enter();
  const records = [];
  for (const category of ['partners', 'orders', 'work']) {
    const payload = { category, code: `LINK-${category}-${width}-${Date.now()}`, title: `關聯驗收${category}`, status: '進行中', visibility: 'internal', fields: [{ label: '說明', value: '原始內容' }] };
    const created = await page.request.post('/api/operations', { data: payload }); expect(created.status()).toBe(201);
    const row = await created.json(); records.push({ ...row, payload });
    await page.getByLabel('資料分類', { exact: true }).selectOption(category);
    await page.getByLabel('搜尋代碼或名稱').fill(row.code);
    await page.getByRole('button', { name: '搜尋營運資料' }).click();
    await page.getByRole('button', { name: `關聯 ${row.code}`, exact: true }).click();
    await expect(page.getByRole('status')).toHaveText('關聯已儲存。');
  }
  const row = records[0];
  expect((await page.request.put(`/api/operations/${row.id}`, { data: { ...row.payload, fields: [{ label: '說明', value: '最新內容' }], expected_revision: 1 } })).status()).toBe(200);
  await page.reload(); await expect(page.getByRole('heading', { name: '所有專案總覽' })).toBeVisible(); await enter();
  for (const record of records) await expect(page.getByRole('button', { name: `${record.code} · ${record.title}`, exact: true })).toBeVisible();
  await page.getByRole('button', { name: `${row.code} · ${row.title}`, exact: true }).click();
  await expect(page.getByLabel('關聯資料內容')).toContainText('最新內容');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect(await page.locator('.workspace-content').evaluate(el => el.scrollWidth <= el.clientWidth)).toBe(true);
  await page.screenshot({ path: info.outputPath(`links-${width}.png`), fullPage: true });
  page.once('dialog', dialog => dialog.accept());
  await page.getByRole('button', { name: `解除關聯 ${row.code}`, exact: true }).click();
  await expect(page.getByRole('status')).toContainText('原營運資料保留');
  expect((await page.request.get(`/api/operations/${row.id}`)).status()).toBe(200);
  expect(errors).toEqual([]);
});
