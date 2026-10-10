import { mkdir } from 'node:fs/promises';
import { expect, test, type Page } from '@playwright/test';
import { randomUUID } from 'node:crypto';

test.beforeEach(async ({ request, baseURL }) => {
  expect(new URL(baseURL!).port).not.toBe('15173');
  const marker = await request.get('/api/health/acceptance');
  expect(marker.status()).toBe(200);
  expect(await marker.json()).toEqual({ acceptance: true });
});

async function login(page: Page, username: string) {
  await page.goto('/');
  await page.getByLabel('帳號').fill(username);
  await page.getByLabel('密碼').fill(`demo-${username}`);
  await page.getByRole('button', { name: '登入', exact: true }).click();
  await expect(page.getByLabel('可見任務完成率', { exact: true })).toBeVisible();
}

/** Blank project: 階段 → 上層 → 子一, 子二 → 孫; 另一個 and 後續 (waits on 子一) under the phase. */
async function seedTree(page: Page, title: string, owner?: string) {
  const created = await page.request.post('/api/projects', { data: { title } });
  expect(created.status()).toBe(201);
  const projectId = (await created.json()).id as string;
  const root = (await (await page.request.get(`/api/projects/${projectId}`)).json()).nodes[0].id as string;
  const ids: Record<string, string> = {};
  for (const [name, kind, parent] of [['階段', 'phase', root], ['上層', 'task', '階段'], ['子一', 'task', '上層'], ['子二', 'task', '上層'],
    ['孫', 'task', '子二'], ['另一個', 'task', '階段'], ['後續', 'task', '階段']] as const) {
    const data = { title: name, kind, parent_id: ids[parent] ?? parent, ...(owner && kind === 'task' ? { owner_user_id: owner } : {}) };
    const response = await page.request.post(`/api/projects/${projectId}/nodes`, { data });
    expect(response.status()).toBe(201);
    ids[name] = (await response.json()).id;
  }
  expect((await page.request.post(`/api/projects/${projectId}/dependencies`, { data: { predecessor_id: ids['子一'], successor_id: ids['後續'] } })).status()).toBe(201);
  return { projectId, ids };
}

function watch(page: Page) {
  const problems: string[] = [];
  page.on('pageerror', error => problems.push(`pageerror ${error}`));
  page.on('response', response => {
    const path = new URL(response.url()).pathname;
    if (response.status() >= 400 && !(response.status() === 401 && path === '/api/auth/me')) problems.push(`${response.status()} ${path}`);
  });
  return problems;
}

const board = (page: Page) => page.getByLabel('看板', { exact: true });
const card = (page: Page, title: string) => board(page).locator('article.task-card').filter({ has: page.getByRole('button', { name: title, exact: true }) });
const crumb = (page: Page, name: string) => page.getByRole('navigation', { name: '節點路徑' }).getByRole('button', { name, exact: true });
const ops = (page: Page) => page.getByRole('group', { name: '層級操作' });
const notice = (page: Page) => page.getByRole('alert');
const dir = '../.superpowers/tpb/e2e';
async function shot(page: Page, name: string, width: number) {
  await mkdir(dir, { recursive: true });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: `${dir}/formal-${name}-${width}.png` });
}
async function nodeOf(page: Page, projectId: string, id: string) {
  const detail = await (await page.request.get(`/api/projects/${projectId}`)).json();
  return detail.nodes.find((n: { id: string }) => n.id === id) as { parent_id: string; title: string } | undefined;
}

test('TP-B promote, delete, Ctrl+Z, copy, timeline undo and move-to at 1280px', async ({ page }) => {
  test.setTimeout(90000);
  await page.setViewportSize({ width: 1280, height: 900 });
  const problems = watch(page);
  await login(page, 'yu');
  const title = `TP-B ${randomUUID()}`;
  const { projectId, ids } = await seedTree(page, title);
  await page.reload();
  await page.getByLabel('專案清單').getByRole('button', { name: title, exact: true }).click();
  await page.getByRole('button', { name: '進入階段：階段' }).click();
  await expect(card(page, '後續')).toContainText('等待：子一');

  // 升級 子二 from 上層 to 階段, then undo it from the notice.
  await card(page, '上層').getByRole('button', { name: '上層', exact: true }).click();
  await card(page, '子二').getByRole('button', { name: '子二', exact: true }).click();
  await page.getByRole('button', { name: '編輯節點' }).click();
  await expect(ops(page)).toBeVisible();
  await expect(ops(page).getByRole('button', { name: '↘ 降級' })).toBeEnabled();
  await ops(page).scrollIntoViewIfNeeded();
  await shot(page, 'editor-tree-ops', 1280);
  await ops(page).getByRole('button', { name: '↖ 升級' }).click();
  await expect(notice(page)).toContainText('已將「子二」移到「階段」底下');
  expect((await nodeOf(page, projectId, ids['子二']))!.parent_id).toBe(ids['階段']);
  await notice(page).getByRole('button', { name: '復原' }).click();
  await expect(notice(page)).toHaveText('已復原：移動「子二」');
  expect((await nodeOf(page, projectId, ids['子二']))!.parent_id).toBe(ids['上層']);

  // Delete 上層 with its subtree: the confirmation names the waiting task; the board goes back to the phase.
  await crumb(page, '上層').click();
  await page.getByRole('button', { name: '編輯節點' }).click();
  await page.getByRole('button', { name: '刪除', exact: true }).click();
  const dialog = page.getByRole('alertdialog', { name: '刪除「上層」？' });
  await expect(dialog).toContainText('將一併刪除 3 個子任務。');
  await expect(dialog).toContainText('以下任務依賴它，前置條件會被移除：後續');
  await shot(page, 'delete-confirm', 1280);
  await dialog.getByRole('button', { name: '確定刪除（可復原）' }).click();
  await expect(notice(page)).toContainText('已刪除「上層」');
  await expect(page.getByRole('heading', { name: '階段', exact: true })).toBeVisible();
  await expect(card(page, '上層')).toHaveCount(0);
  await expect(card(page, '後續')).not.toContainText('等待');
  await shot(page, 'after-delete', 1280);
  const deleted = await (await page.request.get(`/api/audit-logs?node_id=${ids['上層']}`)).json();
  expect(deleted.items[0]).toMatchObject({ action: 'node.delete', node_deleted: true, payload: { title: '上層', count: 4 } });

  // Ctrl+Z restores the subtree and the dependency.
  await page.evaluate(() => (document.activeElement as HTMLElement | null)?.blur());
  await page.keyboard.press('Control+z');
  await expect(notice(page)).toHaveText('已復原：刪除「上層」');
  await expect(card(page, '上層')).toContainText('0/2 子任務');
  await expect(card(page, '後續')).toContainText('等待：子一');

  // Copy 另一個, open the copy, and undo it from the timeline toolbar.
  await card(page, '另一個').getByRole('button', { name: '另一個', exact: true }).click();
  await page.getByRole('button', { name: '編輯節點' }).click();
  await ops(page).getByRole('button', { name: '複製子樹' }).click();
  await expect(notice(page)).toContainText('已複製子樹「另一個（複本）」');
  await notice(page).getByRole('button', { name: '開啟' }).click();
  await expect(page.getByRole('heading', { name: '另一個（複本）', exact: true })).toBeVisible();
  await crumb(page, '階段').click();
  await expect(card(page, '另一個（複本）')).toBeVisible();
  await page.getByRole('tab', { name: '時程' }).click();
  await page.getByRole('button', { name: '↶ 復原' }).click();
  await expect(notice(page)).toHaveText('已復原：複製「另一個」');
  await expect(page.getByRole('button', { name: '↶ 復原' })).toBeDisabled();
  await page.getByRole('tab', { name: '看板' }).click();
  await expect(card(page, '另一個（複本）')).toHaveCount(0);

  // 移動到… without dragging.
  await card(page, '後續').getByRole('button', { name: '後續', exact: true }).click();
  await page.getByRole('button', { name: '編輯節點' }).click();
  await ops(page).getByLabel('移動到').selectOption(ids['另一個']);
  await ops(page).getByRole('button', { name: '移動', exact: true }).click();
  await expect(notice(page)).toContainText('已將「後續」移到「另一個」底下');

  // Everything persists after reloading.
  await page.reload();
  await page.getByLabel('專案清單').getByRole('button', { name: title, exact: true }).click();
  await page.getByRole('button', { name: '進入階段：階段' }).click();
  await expect(card(page, '上層')).toContainText('0/2 子任務');
  await expect(card(page, '另一個')).toContainText('0/1 子任務');
  expect((await nodeOf(page, projectId, ids['後續']))!.parent_id).toBe(ids['另一個']);
  const audit = await (await page.request.get(`/api/audit-logs?node_id=${ids['上層']}`)).json();
  expect(audit.items.slice(0, 2).map((item: { action: string }) => item.action)).toEqual(['node.undo', 'node.delete']);
  expect(problems).toEqual([]);
});

for (const width of [1440, 375]) test(`TP-B editor and delete confirmation fit at ${width}px`, async ({ page }) => {
  await page.setViewportSize({ width, height: 900 });
  const problems = watch(page);
  await login(page, 'yu');
  const title = `TP-B ${width} ${randomUUID()}`;
  await seedTree(page, title);
  await page.reload();
  if (width === 375) await page.getByRole('button', { name: '切換導覽' }).click();
  await page.getByLabel('專案清單').getByRole('button', { name: title, exact: true }).click();
  await page.getByRole('button', { name: '進入階段：階段' }).click();
  await card(page, '上層').getByRole('button', { name: '上層', exact: true }).click();
  await page.getByRole('button', { name: '編輯節點' }).click();
  await expect(ops(page).getByRole('button', { name: '↖ 升級' })).toBeEnabled();
  await ops(page).scrollIntoViewIfNeeded();
  await shot(page, 'editor-tree-ops', width);
  await page.getByRole('button', { name: '刪除', exact: true }).click();
  await expect(page.getByRole('alertdialog')).toContainText('以下任務依賴它，前置條件會被移除：後續');
  await shot(page, 'delete-confirm', width);
  await page.getByRole('alertdialog').getByRole('button', { name: '取消' }).click();
  await expect(ops(page)).toBeVisible();
  expect(problems).toEqual([]);
});

test('TP-B a task owner may promote and demote but not copy or delete (D74)', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await login(page, 'yu');
  const title = `TP-B 成員 ${randomUUID()}`;
  const created = await (await page.request.post('/api/projects', { data: { title } })).json();
  const options = await (await page.request.get(`/api/projects/${created.id}/assignment-options`)).json();
  const ming = options.users.find((user: { display_name: string }) => user.display_name === '明成員').id as string;
  await seedTree(page, `${title} 樹`, ming);
  await page.getByRole('button', { name: '登出' }).click();
  const problems = watch(page);
  await login(page, 'ming');
  await page.getByLabel('工作區導覽').getByRole('button', { name: '我的任務' }).click();
  // The search also matches the project title, so only this run's tasks remain.
  await page.getByLabel('搜尋任務').fill(title);
  await expect(page.getByRole('button', { name: '另一個', exact: true })).toHaveCount(1);
  await page.getByRole('button', { name: '另一個', exact: true }).click();
  await expect(page.getByRole('heading', { name: '另一個', exact: true })).toBeVisible();
  await page.getByRole('button', { name: '編輯節點' }).click();
  await expect(ops(page).getByRole('button', { name: '↘ 降級' })).toBeEnabled();
  await expect(ops(page).getByRole('button', { name: '複製子樹' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: '刪除', exact: true })).toHaveCount(0);
  await ops(page).getByRole('button', { name: '↘ 降級' }).click();
  await expect(notice(page)).toContainText('已將「另一個」移到「上層」底下');
  await notice(page).getByRole('button', { name: '復原' }).click();
  await expect(notice(page)).toHaveText('已復原：移動「另一個」');
  expect(problems).toEqual([]);
});
