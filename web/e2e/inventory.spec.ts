import { test, expect } from '@playwright/test';
import { randomUUID } from 'node:crypto';

for (const width of [1280, 375]) test(`receipt stock ledger ${width}`, async ({ page, request }, info) => {
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
  const order = await create('orders', `PO-${stamp}`);
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
  await enter(); await open('採購', order.code);
  await page.getByLabel('搜尋收貨物料').fill(material.code);
  await page.getByRole('button', { name: '搜尋物料', exact: true }).click();
  await page.getByLabel('收貨與庫存').getByRole('button', { name: `${material.code}｜庫存驗收`, exact: true }).click();
  await expect(page.getByLabel('目前庫存')).toContainText('0.000');
  await page.getByLabel('異動數量').fill('12.345');
  await page.getByLabel('庫存單位', { exact: true }).fill('kg');
  await page.getByLabel('異動原因／收貨說明').fill('首批到貨');
  page.once('dialog', dialog => dialog.dismiss());
  await page.getByRole('button', { name: '編輯營運資料', exact: true }).click();
  await expect(page.getByLabel('異動數量')).toHaveValue('12.345');
  page.once('dialog', dialog => dialog.accept());
  await page.getByRole('button', { name: '確認收貨入庫' }).click();
  await expect(page.getByText('已入帳，庫存與異動紀錄已保存。', { exact: true })).toBeVisible();
  await expect(page.getByLabel('目前庫存')).toContainText('12.345 kg');
  await page.reload(); await expect(page.getByRole('heading', { name: '所有專案總覽' })).toBeVisible();
  await enter(); await open('原料 / 包材', material.code);
  await expect(page.getByLabel('目前庫存')).toContainText('12.345 kg');
  await expect(page.locator('.inventory-history')).toContainText(order.code);
  await page.getByLabel('異動數量').fill('-2.005');
  await page.getByLabel('異動原因／收貨說明').fill('盤點補正');
  page.once('dialog', dialog => dialog.accept());
  await page.getByRole('button', { name: '儲存庫存調整' }).click();
  await expect(page.getByLabel('目前庫存')).toContainText('10.340 kg');
  // Real PostgreSQL races: retry same request, independent receipts, and competing deductions.
  const data = { resource_id: material.id, quantity: '1.001', unit: 'kg', reason: '重送驗證', request_id: randomUUID() };
  const retry = await Promise.all([1, 2].map(() => page.request.post(`/api/operations/${order.id}/receipts`, { data })));
  expect(retry.map(r => r.status())).toEqual([200, 200]);
  expect((await retry[0].json()).id).toBe((await retry[1].json()).id);
  const parallel = await Promise.all([1, 2].map(() => page.request.post(`/api/operations/${order.id}/receipts`, { data: { ...data, request_id: randomUUID() } })));
  expect(parallel.map(r => r.status())).toEqual([200, 200]);
  const deductions = await Promise.all([1, 2].map(() => page.request.post('/api/inventory/adjustments', { data: { ...data, quantity: '-10', request_id: randomUUID() } })));
  expect(deductions.map(r => r.status()).sort()).toEqual([200, 409]);
  await page.getByRole('button', { name: '重新載入庫存與紀錄' }).click();
  await expect(page.getByLabel('目前庫存')).toContainText('3.343 kg');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect(await page.locator('.workspace-content').evaluate(el => el.scrollWidth <= el.clientWidth)).toBe(true);
  await page.screenshot({ path: info.outputPath(`inventory-${width}.png`), fullPage: true });
  expect(errors).toEqual([]);
});
