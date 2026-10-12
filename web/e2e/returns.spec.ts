import { test, expect } from '@playwright/test';
import { randomUUID } from 'node:crypto';

for (const width of [1280, 375]) test(`purchase returns, material returns and reversals ${width}`, async ({ page, request }, info) => {
  test.setTimeout(120000);
  expect(await (await request.get('/api/health/acceptance')).json()).toEqual({ acceptance: true });
  await page.setViewportSize({ width, height: 900 });
  const errors: string[] = []; page.on('pageerror', e => errors.push(String(e)));
  await page.goto('/');
  await page.getByLabel('帳號').fill('yu'); await page.getByLabel('密碼').fill('demo-yu');
  await page.getByRole('button', { name: '登入', exact: true }).click();
  await expect(page.getByRole('heading', { name: '所有專案總覽' })).toBeVisible();
  const stamp = `${width}-${Date.now()}`;
  async function create(category: string, code: string) {
    const result = await page.request.post('/api/operations', { data: { category, code, title: '退貨驗收', status: '進行中', visibility: 'restricted', fields: [] } });
    expect(result.status()).toBe(201); return result.json();
  }
  const flour = await create('resources', `FLOUR-${stamp}`);
  const meat = await create('resources', `MEAT-${stamp}`);
  const order = await create('orders', `PO-${stamp}`);
  const work = await create('work', `WO-${stamp}`);
  const api = (path: string, data: object) => page.request.post(`/api${path}`, { data });
  expect((await page.request.put(`/api/operations/${order.id}/purchase/lines`, { data: { expected_revision: 0, lines: [{ resource_id: flour.id, quantity: '10', unit: 'kg' }] } })).status()).toBe(200);
  expect((await api(`/operations/${order.id}/receipts`, { resource_id: flour.id, quantity: '10', unit: 'kg', reason: '到貨', request_id: randomUUID() })).status()).toBe(200);
  expect((await api('/inventory/adjustments', { resource_id: meat.id, quantity: '20', unit: 'kg', reason: 'initial stock', request_id: randomUUID() })).status()).toBe(200);
  expect((await api(`/operations/${work.id}/issues`, { resource_id: meat.id, quantity: '5', unit: 'kg', reason: '投料', request_id: randomUUID() })).status()).toBe(200);
  async function enter() {
    if (width === 375 && !await page.getByLabel('工作區導覽').isVisible()) await page.getByRole('button', { name: '切換導覽' }).click();
    await page.getByLabel('工作區導覽').getByRole('button', { name: '營運資料', exact: true }).click();
  }
  async function open(category: string, code: string) {
    await page.getByLabel('營運分類').getByRole('button', { name: category, exact: true }).click();
    await page.getByLabel('搜尋代碼或名稱', { exact: true }).fill(code);
    await page.getByRole('button', { name: '搜尋', exact: true }).click();
    await page.locator('.operations-list').getByRole('button', { name: new RegExp(code) }).click();
  }
  await enter(); await open('採購', order.code);
  const state = page.getByLabel('收貨狀態');
  await expect(state).toContainText('已收齊（1/1 列已收齊）');
  // Return part of a received line: the returned quantity becomes outstanding again.
  await page.getByLabel('採購操作').selectOption('returns');
  await page.getByRole('button', { name: `${flour.code}｜退貨驗收 · 可退 10.000 kg` }).click();
  await expect(page.getByLabel('本次可退')).toContainText('本次最多可退 10.000 kg');
  await page.getByLabel('異動數量').fill('10.5');
  await expect(page.getByText('超過已收數量，不能退貨。')).toBeVisible();
  await expect(page.getByRole('button', { name: '確認採購退貨' })).toBeDisabled();
  await page.getByLabel('異動數量').fill('3');
  await page.getByLabel('異動原因／收貨說明').fill('受潮退回');
  page.once('dialog', dialog => dialog.accept());
  await page.getByRole('button', { name: '確認採購退貨' }).click();
  await expect(page.getByText('已入帳，庫存與異動紀錄已保存。', { exact: true })).toBeVisible();
  await expect(state).toContainText('部分收貨（0/1 列已收齊）');
  await expect(page.locator('.purchase-lines')).toContainText('已收 7.000 · 未收 3.000 · 已退 3.000');
  // Real PostgreSQL: concurrent returns cannot take back more than was received.
  const giveBack = (quantity: string) => api(`/operations/${order.id}/returns`, { resource_id: flour.id, quantity, unit: 'kg', reason: '併發退貨', request_id: randomUUID() });
  const parallel = await Promise.all([giveBack('4'), giveBack('4')]);
  expect(parallel.map(r => r.status()).sort()).toEqual([200, 409]);
  const accepted = await parallel.find(r => r.status() === 200)!.json();
  // Reverse the UI return from its history entry; the original stays and is marked.
  await page.getByRole('button', { name: '重新載入收貨進度' }).click();
  await expect(page.locator('.purchase-lines')).toContainText('已收 3.000');
  const entry = page.locator('.inventory-history li', { hasText: '受潮退回' });
  await entry.getByRole('button', { name: '沖銷此筆' }).click();
  await page.getByLabel('沖銷原因').fill('退貨數量登錄錯誤');
  page.once('dialog', dialog => dialog.accept());
  await page.getByRole('button', { name: '確認沖銷' }).click();
  await expect(page.getByText('已沖銷，庫存與相關進度已回復；原紀錄保留。')).toBeVisible();
  await expect(entry).toContainText('已沖銷');
  await expect(page.locator('.purchase-lines')).toContainText('已收 6.000 · 未收 4.000');
  // Real PostgreSQL: one entry is reversed at most once, even under concurrent requests.
  const reverse = () => api(`/inventory/movements/${accepted.id}/reversal`, { reason: '併發沖銷', request_id: randomUUID() });
  const reversals = await Promise.all([reverse(), reverse()]);
  expect(reversals.map(r => r.status()).sort()).toEqual([200, 409]);
  await page.getByRole('button', { name: '重新載入收貨進度' }).click();
  await expect(state).toContainText('已收齊（1/1 列已收齊）');
  // Material return on the work order brings issued material back to stock.
  await open('試產 / 檢驗', work.code);
  await page.getByLabel('工單操作').selectOption('issue-returns');
  await page.getByRole('button', { name: `${meat.code}｜退貨驗收 · 可退 5.000 kg` }).click();
  await page.getByLabel('異動數量').fill('2');
  await page.getByLabel('異動原因／收貨說明').fill('剩料退回');
  page.once('dialog', dialog => dialog.accept());
  await page.getByRole('button', { name: '確認工單退料' }).click();
  await expect(page.getByLabel('累計領料')).toContainText('已領 3.000 kg');
  await expect(page.getByLabel('累計領料')).toContainText('已退料 2.000 kg');
  // Reload keeps the line progress, reversal marks and stock.
  await page.reload(); await expect(page.getByRole('heading', { name: '所有專案總覽' })).toBeVisible();
  await enter(); await open('採購', order.code);
  await expect(state).toContainText('已收齊（1/1 列已收齊）');
  await expect(page.locator('.inventory-history li', { hasText: '受潮退回' })).toContainText('已沖銷');
  await expect(page.locator('.inventory-history')).toContainText('沖銷（採購退貨）');
  expect((await (await page.request.get(`/api/inventory/resources/${flour.id}`)).json()).quantity).toBe('10.000');
  expect((await (await page.request.get(`/api/inventory/resources/${meat.id}`)).json()).quantity).toBe('17.000');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect(await page.locator('.workspace-content').evaluate(el => el.scrollWidth <= el.clientWidth)).toBe(true);
  await page.screenshot({ path: info.outputPath(`returns-${width}.png`), fullPage: true });
  expect(errors).toEqual([]);
});
