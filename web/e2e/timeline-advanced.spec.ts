import { closeProjectDrawer, openProjects } from './navigation';
import { mkdir } from 'node:fs/promises';
import { randomUUID } from 'node:crypto';
import { expect, test, type Page } from '@playwright/test';

test.beforeEach(async ({ request, baseURL }) => {
  expect(new URL(baseURL!).port).not.toBe('15173');
  const marker = await request.get('/api/health/acceptance');
  expect(marker.status()).toBe(200);
  expect(await marker.json()).toEqual({ acceptance: true });
});
async function login(page: Page, username = 'yu') {
  await page.goto('/'); await page.getByLabel('帳號').fill(username); await page.getByLabel('密碼').fill(`demo-${username}`);
  await page.getByRole('button', { name: '登入', exact: true }).click();
  await expect(page.getByLabel('可見任務完成率', { exact: true })).toBeVisible();
}
async function setup(page: Page) {
  const title = `TP-C ${randomUUID()}`;
  const made = await page.request.post('/api/projects', { data: { title } }); expect(made.status()).toBe(201);
  const pid = (await made.json()).id;
  const root = (await (await page.request.get(`/api/projects/${pid}`)).json()).nodes[0].id;
  const ids: Record<string, string> = {};
  const opts = await (await page.request.get(`/api/projects/${pid}/assignment-options`)).json();
  for (const [name, start, due] of [['A', '01', '03'], ['B', '04', '04'], ['C', '05', '07']]) {
    const r = await page.request.post(`/api/projects/${pid}/nodes`, { data: { title: name, kind: 'task', parent_id: root,
      start_date: `2026-10-${start}`, due_date: `2026-10-${due}`, department_id: opts.departments[0]?.id ?? null,
      ...(name === 'B' ? { milestone: true } : {}) } });
    expect(r.status()).toBe(201); ids[name] = (await r.json()).id;
  }
  for (const [a, b] of [['A', 'B'], ['B', 'C']]) expect((await page.request.post(`/api/projects/${pid}/dependencies`, { data: { predecessor_id: ids[a], successor_id: ids[b] } })).status()).toBe(201);
  await page.reload();
  await (await openProjects(page)).getByRole('button', { name: title, exact: true }).click();await closeProjectDrawer(page);
  await page.getByRole('tab', { name: '時程', exact: true }).click();
  await expect(page.getByLabel('專案時程')).toBeVisible();
  return { pid, ids, root, title };
}
const dates = async (page: Page, pid: string) => (await (await page.request.get(`/api/projects/${pid}`)).json()).nodes;
async function editDates(page: Page, name: string, start: string, due: string) {
  await page.getByRole('button', { name: `調整日期：${name}`, exact: true }).click();
  const form = page.getByRole('form', { name: '日期表單' });
  // Fill due first so moving both dates later doesn't leave an invalid max constraint.
  if (!await form.getByLabel('截止日期').isDisabled()) await form.getByLabel('截止日期').fill(due);
  await form.getByLabel('開始日期').fill(start);
  await form.getByRole('button', { name: '儲存日期' }).click();
}

test('TP-C drag cascades, locked successor rejects atomically, arrows and screenshots', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  const errors: string[] = []; page.on('pageerror', e => errors.push(e.message));
  await login(page); const { pid, ids } = await setup(page);
  await expect(page.locator('.timeline-arrows path[data-edge-id]')).toHaveCount(2);
  await page.getByLabel('後續相依自動順延').check();
  const bar = page.getByRole('button', { name: '時程任務：A', exact: true });
  await bar.scrollIntoViewIfNeeded(); const box = (await bar.boundingBox())!;
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await page.mouse.down(); await page.mouse.move(box.x + box.width / 2 + 65, box.y + box.height / 2, { steps: 6 }); await page.mouse.up();
  const form = page.getByRole('form', { name: '日期表單' }); await expect(form).toBeVisible();
  await form.getByRole('button', { name: '儲存日期' }).click();
  await expect(page.getByRole('form', { name: '日期表單' })).toHaveCount(0);
  const changed = await dates(page, pid); const a = changed.find((n: { id: string }) => n.id === ids.A), b = changed.find((n: { id: string }) => n.id === ids.B);
  expect(a.start_date > '2026-10-01').toBe(true); expect(b.start_date > a.due_date).toBe(true);
  const logs = await (await page.request.get(`/api/audit-logs?node_id=${ids.B}`)).json();
  expect(logs.items.some((l: { summary: string }) => l.summary === '自動順延')).toBe(true);
  expect((await page.request.patch(`/api/nodes/${ids.B}`, { data: { schedule_locked: true } })).status()).toBe(200);
  const before = await dates(page, pid);
  await page.getByLabel('後續相依自動順延').check();
  await editDates(page, 'A', '2026-11-01', '2026-11-03');
  await expect(form.getByRole('alert')).toHaveText('後續任務有無法調整的項目，請由專案負責人確認');
  expect(await dates(page, pid)).toEqual(before);
  await form.getByRole('button', { name: '取消改期' }).click();
  expect((await page.request.patch(`/api/nodes/${ids.B}`, { data: { schedule_locked: false } })).status()).toBe(200);
  await editDates(page, 'A', '2026-11-01', '2026-11-03');
  await expect(form).toHaveCount(0);
  await page.getByRole('button', { name: '關鍵路徑', exact: true }).click();
  await expect(page.locator('.timeline-bar.critical')).toHaveCount(3);
  await mkdir('../.superpowers/tpc/e2e', { recursive: true });
  for (const width of [1280, 1440, 375]) {
    await page.setViewportSize({ width, height: 900 });
    await page.getByRole('button', { name: '時程任務：B', exact: true }).scrollIntoViewIfNeeded();
    await page.screenshot({ path: `../.superpowers/tpc/e2e/timeline-${width}.png`, fullPage: true });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  }
  // Mobile uses a real date input instead of a drag gesture.
  await editDates(page, 'C', '2026-11-06', '2026-11-08'); await expect(form).toHaveCount(0);
  await page.reload();
  const saved = await dates(page, pid); expect(saved.find((n: { id: string }) => n.id === ids.C).due_date).toBe('2026-11-08');
  expect(errors).toEqual([]);
});

test('TP-C drag-to-create and row plus use existing create and one-step undo', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 }); await login(page); const { pid, ids } = await setup(page);
  const track = page.getByLabel('拖曳日期新增子任務'); await track.scrollIntoViewIfNeeded(); const box = (await track.boundingBox())!;
  // The sticky name column can cover the track's left edge after horizontal scrolling.
  const label = (await page.locator('.timeline-add .timeline-label').boundingBox())!;
  const dragX = Math.max(box.x, label.x + label.width) + 20;
  await page.mouse.move(dragX, box.y + 18); await page.mouse.down(); await page.mouse.move(dragX + 70, box.y + 18, { steps: 5 }); await page.mouse.up();
  let form = page.getByRole('form', { name: '新增節點表單' }); await expect(form).toBeVisible();
  expect(await form.getByLabel('開始日期').inputValue()).not.toBe('');
  await form.getByLabel('節點名稱').fill('拖出新任務'); await form.getByRole('button', { name: '儲存', exact: true }).click();
  await expect(form).toHaveCount(0);
  expect((await dates(page, pid)).some((n: { title: string }) => n.title === '拖出新任務')).toBe(true);
  await page.getByRole('button', { name: '↶ 復原', exact: true }).click();
  await expect(page.getByRole('button', { name: '時程任務：拖出新任務', exact: true })).toHaveCount(0);
  await page.getByRole('button', { name: '新增子任務：A', exact: true }).click();
  form = page.getByRole('form', { name: '新增節點表單' }); await form.getByLabel('節點名稱').fill('列上新增');
  await form.getByRole('button', { name: '儲存', exact: true }).click(); await expect(form).toHaveCount(0);
  expect((await dates(page, pid)).find((n: { title: string }) => n.title === '列上新增').parent_id).toBe(ids.A);
  await expect(page.getByRole('button', { name: '調整截止日：A', exact: true })).toHaveCount(0);
  await expect(page.getByRole('button', { name: '新增子任務：B', exact: true })).toBeDisabled();
});

test('TP-C member cannot cascade into another owner and cannot unlock milestone', async ({ page }) => {
  await login(page); const { pid, ids } = await setup(page);
  // Read the member's own session identity from a separate authenticated context.
  const member = await page.context().browser()!.newContext({ baseURL: test.info().project.use.baseURL as string });
  try {
    const signed = await member.request.post('/api/auth/login', { data: { organization_key: 'food', username: 'ming', password: 'demo-ming' } });
    expect(signed.status()).toBe(200); const uid = (await signed.json()).user.id;
    expect((await page.request.patch(`/api/nodes/${ids.A}`, { data: { owner_user_id: uid } })).status()).toBe(200);
    const before = await dates(page, pid);
    const denied = await member.request.post(`/api/nodes/${ids.A}/schedule`, { data: { start_date: '2026-10-04', due_date: '2026-10-06', cascade: true } });
    expect(denied.status()).toBe(409); expect(await dates(page, pid)).toEqual(before);
    expect((await page.request.patch(`/api/nodes/${ids.B}`, { data: { owner_user_id: uid, schedule_locked: true } })).status()).toBe(200);
    expect((await member.request.patch(`/api/nodes/${ids.B}`, { data: { schedule_locked: false } })).status()).toBe(403);
  } finally { await member.close(); }
});
