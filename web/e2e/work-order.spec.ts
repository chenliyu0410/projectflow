import { test, expect } from '@playwright/test';
import { randomUUID } from 'node:crypto';

for (const width of [1280, 375]) test(`work order output plan ${width}`, async ({ page, request }, info) => {
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
    const result = await page.request.post('/api/operations', { data: { category, code, title: '工單驗收', status: '試產中', visibility: 'restricted', fields: [] } });
    expect(result.status()).toBe(201); return result.json();
  }
  const meat = await create('resources', `MEAT-${stamp}`);
  const can = await create('resources', `CAN-${stamp}`);
  const work = await create('work', `WO-${stamp}`);
  expect((await page.request.post('/api/inventory/adjustments', { data: { resource_id: meat.id, quantity: '20', unit: 'kg', reason: 'initial stock', request_id: randomUUID() } })).status()).toBe(200);
  async function enter() {
    if (width === 375 && !await page.getByLabel('工作區導覽').isVisible()) await page.getByRole('button', { name: '切換導覽' }).click();
    await page.getByLabel('工作區導覽').getByRole('button', { name: '營運資料', exact: true }).click();
  }
  async function open() {
    await page.getByLabel('營運分類').getByRole('button', { name: '試產 / 檢驗', exact: true }).click();
    await page.getByLabel('搜尋代碼或名稱', { exact: true }).fill(work.code);
    await page.getByRole('button', { name: '搜尋', exact: true }).click();
    await page.locator('.operations-list').getByRole('button', { name: new RegExp(work.code) }).click();
  }
  await enter(); await open();
  const state = page.getByLabel('生產狀態');
  await expect(state).toContainText('未設定計畫');
  // Plan: finished product, planned output and unit (no stock yet, so the unit is entered here).
  await page.getByRole('button', { name: '設定生產計畫' }).click();
  await page.getByLabel('搜尋成品').fill(can.code);
  await page.getByRole('button', { name: '搜尋成品', exact: true }).click();
  await page.getByRole('button', { name: `選擇 ${can.code}｜工單驗收` }).click();
  await page.getByLabel('計畫產量').fill('10');
  await page.getByLabel('成品單位').fill('罐');
  await page.getByLabel('計畫備註').fill('首批試產');
  await page.getByRole('button', { name: '儲存生產計畫' }).click();
  await expect(state).toContainText('待生產（已完工 0.000／計畫 10.000 罐）');
  // Manual material issue moves the order into production and is totalled per material.
  await page.getByLabel('搜尋物料或成品').fill(meat.code);
  await page.getByRole('button', { name: '搜尋物料', exact: true }).click();
  await page.getByLabel('收貨與庫存').getByRole('button', { name: `${meat.code}｜工單驗收`, exact: true }).click();
  await page.getByLabel('異動數量').fill('5');
  await page.getByLabel('異動原因／收貨說明').fill('首批投料');
  page.once('dialog', dialog => dialog.accept());
  await page.getByRole('button', { name: '確認工單領料' }).click();
  await expect(state).toContainText('生產中');
  await expect(page.getByLabel('累計領料')).toContainText('已領 5.000 kg');
  // Completion is limited to the planned product and the remaining output.
  await page.getByLabel('工單操作').selectOption('completions');
  await page.getByRole('button', { name: `${can.code}｜工單驗收 · 尚可完工 10.000 罐` }).click();
  await expect(page.getByLabel('本次可完工')).toContainText('10.000 罐');
  await page.getByLabel('異動數量').fill('11');
  await expect(page.getByText('超過計畫剩餘產量；實際多產出請先調高工單計畫產量。')).toBeVisible();
  await expect(page.getByRole('button', { name: '確認完工入庫' })).toBeDisabled();
  await page.getByLabel('異動數量').fill('4');
  await page.getByLabel('異動原因／收貨說明').fill('第一批完工');
  page.once('dialog', dialog => dialog.accept());
  await page.getByRole('button', { name: '確認完工入庫' }).click();
  await expect(state).toContainText('生產中（已完工 4.000／計畫 10.000 罐）');
  // Real PostgreSQL: concurrent completions cannot exceed the plan; retries never double count.
  const post = (kind: string, resource: { id: string }, quantity: string, unit: string, request_id = randomUUID()) =>
    page.request.post(`/api/operations/${work.id}/${kind}`, { data: { resource_id: resource.id, quantity, unit, reason: '併發完工', request_id } });
  const parallel = await Promise.all([post('completions', can, '4', '罐'), post('completions', can, '4', '罐')]);
  expect(parallel.map(r => r.status()).sort()).toEqual([200, 409]);
  const same = randomUUID();
  const retries = await Promise.all([post('completions', can, '2', '罐', same), post('completions', can, '2', '罐', same)]);
  expect(retries.map(r => r.status())).toEqual([200, 200]);
  expect((await retries[0].json()).id).toBe((await retries[1].json()).id);
  await page.getByRole('button', { name: '重新載入生產進度' }).click();
  await expect(state).toContainText('已達計畫產量（已完工 10.000／計畫 10.000 罐）');
  await expect(page.getByRole('button', { name: `${can.code}｜工單驗收 · 已達計畫產量` })).toBeDisabled();
  // Manual close locks issues and completions until reopened; a retry still returns the original entry.
  await page.getByRole('button', { name: '結案工單' }).click();
  await page.getByLabel('結案／重開原因').fill('試產完成，轉量產評估');
  page.once('dialog', dialog => dialog.accept());
  await page.getByRole('button', { name: '確認結案' }).click();
  await expect(state).toContainText('已結案');
  await expect(page.getByText('工單已結案，不能再領料或完工；如需補登請先重新開啟。')).toBeVisible();
  const blocked = await post('issues', meat, '1', 'kg');
  expect(blocked.status()).toBe(409);
  expect((await blocked.json()).detail).toBe('工單已結案，不能領料、完工或修改計畫');
  expect((await post('completions', can, '2', '罐', same)).status()).toBe(200);
  await page.getByRole('button', { name: '重新開啟工單' }).click();
  await page.getByLabel('結案／重開原因').fill('補記領料');
  page.once('dialog', dialog => dialog.accept());
  await page.getByRole('button', { name: '確認重新開啟' }).click();
  await expect(state).toContainText('已達計畫產量');
  // Reload keeps plan progress, issued totals, ledger and the list badge.
  await page.reload(); await expect(page.getByRole('heading', { name: '所有專案總覽' })).toBeVisible();
  await enter(); await open();
  await expect(state).toContainText('已達計畫產量（已完工 10.000／計畫 10.000 罐）');
  await expect(page.locator('.operations-list')).toContainText('生產：已達計畫產量（10.000/10.000 罐）');
  await expect(page.getByLabel('累計領料')).toContainText('已領 5.000 kg');
  await expect(page.locator('.inventory-history')).toContainText('第一批完工');
  expect((await (await page.request.get(`/api/inventory/resources/${meat.id}`)).json()).quantity).toBe('15.000');
  expect((await (await page.request.get(`/api/inventory/resources/${can.id}`)).json()).quantity).toBe('10.000');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect(await page.locator('.workspace-content').evaluate(el => el.scrollWidth <= el.clientWidth)).toBe(true);
  await page.screenshot({ path: info.outputPath(`work-order-${width}.png`), fullPage: true });
  expect(errors).toEqual([]);
});
