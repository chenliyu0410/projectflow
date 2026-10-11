import { test, expect } from '@playwright/test';
import { randomUUID } from 'node:crypto';

for (const width of [1280, 375]) test(`work order stock ledger ${width}`, async ({ page, request }, info) => {
  test.setTimeout(60000);
  expect(await (await request.get('/api/health/acceptance')).json()).toEqual({ acceptance: true });
  await page.setViewportSize({ width, height: 900 });
  const errors: string[] = []; page.on('pageerror', e => errors.push(String(e)));
  await page.goto('/');
  await page.getByLabel('帳號').fill('yu'); await page.getByLabel('密碼').fill('demo-yu');
  await page.getByRole('button', { name: '登入', exact: true }).click();
  await expect(page.getByRole('heading', { name: '所有專案總覽' })).toBeVisible();
  const stamp = `${width}-${Date.now()}`;
  async function create(category: string, code: string) {
    const result = await page.request.post('/api/operations', { data: { category, code, title: '庫存驗收', status: '待處理', visibility: 'restricted', fields: [] } });
    expect(result.status()).toBe(201); return result.json();
  }
  const material = await create('resources', `MAT-${stamp}`);
  const order = await create('work', `WO-${stamp}`);
  const product = await create('resources', `FG-${stamp}`);
  expect((await page.request.post('/api/inventory/adjustments', { data: { resource_id: material.id, quantity: '12.345', unit: 'kg', reason: 'initial stock', request_id: randomUUID() } })).status()).toBe(200);
  async function enter() {
    if (width === 375 && !await page.getByLabel('工作區導覽').isVisible()) await page.getByRole('button', { name: '切換導覽' }).click();
    await page.getByLabel('工作區導覽').getByRole('button', { name: '營運資料', exact: true }).click();
  }
  async function open(group: string, code: string) {
    await page.getByLabel('營運分類').getByRole('button', { name: group, exact: true }).click();
    await page.getByLabel('搜尋代碼或名稱', { exact: true }).fill(code);
    await page.getByRole('button', { name: '搜尋', exact: true }).click();
    await page.locator('.operations-list').getByRole('button', { name: new RegExp(code) }).click();
  }
  await enter(); await open('試產 / 檢驗', order.code);
  async function pick(code: string) {
    await page.getByLabel('搜尋物料或成品').fill(code);
    await page.getByRole('button', { name: '搜尋物料', exact: true }).click();
    await page.getByLabel('收貨與庫存').getByRole('button', { name: `${code}｜庫存驗收`, exact: true }).click();
  }
  await pick(material.code);
  await expect(page.getByLabel('目前庫存')).toContainText('12.345 kg');
  await page.getByLabel('異動數量').fill('2.005');
  await page.getByLabel('異動原因／收貨說明').fill('工單首批領料');
  page.once('dialog', dialog => dialog.dismiss());
  await page.getByLabel('工單操作').selectOption('completions');
  await expect(page.getByLabel('工單操作')).toHaveValue('issues');
  await expect(page.getByLabel('異動數量')).toHaveValue('2.005');
  page.once('dialog', dialog => dialog.accept());
  await page.getByRole('button', { name: '確認工單領料' }).click();
  await expect(page.getByLabel('目前庫存')).toContainText('10.340 kg');
  await page.getByLabel('工單操作').selectOption('completions');
  await pick(product.code);
  await page.getByLabel('異動數量').fill('5');
  await page.getByLabel('庫存單位', { exact: true }).fill('件');
  await page.getByLabel('異動原因／收貨說明').fill('完成首批成品');
  page.once('dialog', dialog => dialog.accept());
  await page.getByRole('button', { name: '確認完工入庫' }).click();
  await expect(page.getByLabel('目前庫存')).toContainText('5.000 件');
  await expect(page.locator('.inventory-history')).toContainText('工單領料');
  await expect(page.locator('.inventory-history')).toContainText('完工入庫');
  // PostgreSQL concurrent issues cannot overdraw, completion retries never double-post.
  const data = { resource_id: material.id, quantity: '10', unit: 'kg', reason: 'parallel issue', request_id: randomUUID() };
  const issues = await Promise.all([1, 2].map(() => page.request.post(`/api/operations/${order.id}/issues`, { data: { ...data, request_id: randomUUID() } })));
  expect(issues.map(r => r.status()).sort()).toEqual([200, 409]);
  const finish = { ...data, resource_id: product.id, quantity: '1', unit: '件' };
  const completions = await Promise.all([1, 2].map(() => page.request.post(`/api/operations/${order.id}/completions`, { data: finish })));
  expect(completions.map(r => r.status())).toEqual([200, 200]);
  expect((await completions[0].json()).id).toBe((await completions[1].json()).id);
  await page.reload(); await expect(page.getByRole('heading', { name: '所有專案總覽' })).toBeVisible();
  await enter(); await open('試產 / 檢驗', order.code);
  await expect(page.locator('.inventory-history')).toContainText('完成首批成品');
  await expect(page.locator('.inventory-history')).toContainText(order.code);
  expect((await (await page.request.get(`/api/inventory/resources/${material.id}`)).json()).quantity).toBe('0.340');
  expect((await (await page.request.get(`/api/inventory/resources/${product.id}`)).json()).quantity).toBe('6.000');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect(await page.locator('.workspace-content').evaluate(el => el.scrollWidth <= el.clientWidth)).toBe(true);
  await page.screenshot({ path: info.outputPath(`work-stock-${width}.png`), fullPage: true });
  expect(errors).toEqual([]);
});
