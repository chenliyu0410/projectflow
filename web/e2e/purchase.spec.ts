import { test, expect } from '@playwright/test';
import { randomUUID } from 'node:crypto';

for (const width of [1280, 375]) test(`purchase lines partial receiving ${width}`, async ({ page, request }, info) => {
  test.setTimeout(90000);
  expect(await (await request.get('/api/health/acceptance')).json()).toEqual({ acceptance: true });
  await page.setViewportSize({ width, height: 900 });
  const errors: string[] = []; page.on('pageerror', e => errors.push(String(e)));
  await page.goto('/');
  await page.getByLabel('帳號').fill('yu'); await page.getByLabel('密碼').fill('demo-yu');
  await page.getByRole('button', { name: '登入', exact: true }).click();
  await expect(page.getByRole('heading', { name: '所有專案總覽' })).toBeVisible();
  const stamp = `${width}-${Date.now()}`;
  async function create(category: string, code: string) {
    const result = await page.request.post('/api/operations', { data: { category, code, title: '採購驗收', status: '已下單', visibility: 'restricted', fields: [] } });
    expect(result.status()).toBe(201); return result.json();
  }
  const flour = await create('resources', `FLOUR-${stamp}`);
  const sugar = await create('resources', `SUGAR-${stamp}`);
  const order = await create('orders', `PO-${stamp}`);
  async function enter() {
    if (width === 375 && !await page.getByLabel('工作區導覽').isVisible()) await page.getByRole('button', { name: '切換導覽' }).click();
    await page.getByLabel('工作區導覽').getByRole('button', { name: '營運資料', exact: true }).click();
  }
  async function open() {
    await page.getByLabel('營運分類').getByRole('button', { name: '採購', exact: true }).click();
    await page.getByLabel('搜尋代碼或名稱', { exact: true }).fill(order.code);
    await page.getByRole('button', { name: '搜尋', exact: true }).click();
    await page.locator('.operations-list').getByRole('button', { name: new RegExp(order.code) }).click();
  }
  await enter(); await open();
  const state = page.getByLabel('收貨狀態');
  await expect(state).toContainText('未建立明細');
  // Build two lines; units are set per line because neither material has stock yet.
  await page.getByRole('button', { name: '建立採購明細' }).click();
  for (const [item, quantity, unit] of [[flour, '10', 'kg'], [sugar, '2.5', '包']] as const) {
    await page.getByLabel('搜尋明細物料').fill(item.code);
    await page.getByRole('button', { name: '搜尋明細物料', exact: true }).click();
    await page.getByRole('button', { name: `加入 ${item.code}｜採購驗收` }).click();
    await page.getByLabel(`訂購數量 ${item.code}`).fill(quantity);
    await page.getByLabel(`單位 ${item.code}`).fill(unit);
  }
  await page.getByRole('button', { name: '儲存採購明細' }).click();
  await expect(state).toContainText('待收貨（0/2 列已收齊）');
  // First partial receipt through the UI; over-receipt is blocked before posting.
  await page.getByRole('button', { name: `${flour.code}｜採購驗收 · 未收 10.000 kg` }).click();
  await expect(page.getByLabel('本次可收')).toContainText('10.000 kg');
  await page.getByLabel('異動數量').fill('10.5');
  await expect(page.getByText('超過未收數量；實際多到貨請先修改採購明細的訂購數量。')).toBeVisible();
  await expect(page.getByRole('button', { name: '確認收貨入庫' })).toBeDisabled();
  await page.getByLabel('異動數量').fill('4.25');
  await page.getByLabel('異動原因／收貨說明').fill('首批到貨');
  page.once('dialog', dialog => dialog.accept());
  await page.getByRole('button', { name: '確認收貨入庫' }).click();
  await expect(page.getByText('已入帳，庫存與異動紀錄已保存。', { exact: true })).toBeVisible();
  await expect(state).toContainText('部分收貨（0/2 列已收齊）');
  await expect(page.locator('.purchase-lines')).toContainText('已收 4.250 · 未收 5.750');
  // Real PostgreSQL: concurrent receipts cannot exceed the line, retries never double count.
  const receipt = (resource: { id: string }, quantity: string, unit: string, request_id = randomUUID()) =>
    page.request.post(`/api/operations/${order.id}/receipts`, { data: { resource_id: resource.id, quantity, unit, reason: '併發收貨', request_id } });
  const parallel = await Promise.all([receipt(flour, '3', 'kg'), receipt(flour, '3', 'kg')]);
  expect(parallel.map(r => r.status()).sort()).toEqual([200, 409]);
  const same = randomUUID();
  const retries = await Promise.all([receipt(sugar, '1', '包', same), receipt(sugar, '1', '包', same)]);
  expect(retries.map(r => r.status())).toEqual([200, 200]);
  expect((await retries[0].json()).id).toBe((await retries[1].json()).id);
  expect((await receipt(flour, '2.75', 'kg')).status()).toBe(200);
  await page.getByRole('button', { name: '重新載入收貨進度' }).click();
  await expect(state).toContainText('部分收貨（1/2 列已收齊）');
  await expect(page.getByRole('button', { name: `${flour.code}｜採購驗收 · 已收齊` })).toBeDisabled();
  await expect(page.getByRole('button', { name: `${sugar.code}｜採購驗收 · 未收 1.500 包` })).toBeEnabled();
  // Manual close locks receiving until reopened.
  await page.getByRole('button', { name: '結案採購單' }).click();
  await page.getByLabel('結案／重開原因').fill('供應商短交，剩餘取消');
  page.once('dialog', dialog => dialog.accept());
  await page.getByRole('button', { name: '確認結案' }).click();
  await expect(state).toContainText('已結案');
  await expect(page.getByText('採購單已結案，不能再收貨；如需補收請先重新開啟。')).toBeVisible();
  const blocked = await receipt(sugar, '0.5', '包');
  expect(blocked.status()).toBe(409);
  expect((await blocked.json()).detail).toBe('採購單已結案，不能收貨或修改明細');
  await page.getByRole('button', { name: '重新開啟採購單' }).click();
  await page.getByLabel('結案／重開原因').fill('供應商補交');
  page.once('dialog', dialog => dialog.accept());
  await page.getByRole('button', { name: '確認重新開啟' }).click();
  await expect(state).toContainText('部分收貨（1/2 列已收齊）');
  // Reload keeps progress, ledger and the list badge.
  await page.reload(); await expect(page.getByRole('heading', { name: '所有專案總覽' })).toBeVisible();
  await enter(); await open();
  await expect(state).toContainText('部分收貨（1/2 列已收齊）');
  await expect(page.locator('.operations-list')).toContainText('收貨：部分收貨（1/2 列）');
  await expect(page.locator('.inventory-history')).toContainText('首批到貨');
  expect((await (await page.request.get(`/api/inventory/resources/${flour.id}`)).json()).quantity).toBe('10.000');
  expect((await (await page.request.get(`/api/inventory/resources/${sugar.id}`)).json()).quantity).toBe('1.000');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect(await page.locator('.workspace-content').evaluate(el => el.scrollWidth <= el.clientWidth)).toBe(true);
  await page.screenshot({ path: info.outputPath(`purchase-${width}.png`), fullPage: true });
  expect(errors).toEqual([]);
});
