import { openProjects } from './navigation';
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

/** Blank project with project root → 階段 → 上層 → 中層 → 底層, plus 另一個 and 待移動 under the phase. */
async function fourLevels(page: Page, title: string) {
  const created = await page.request.post('/api/projects', { data: { title } });
  expect(created.status()).toBe(201);
  const projectId = (await created.json()).id as string;
  const root = (await (await page.request.get(`/api/projects/${projectId}`)).json()).nodes[0].id as string;
  const ids: Record<string, string> = {};
  for (const [name, kind, parent] of [['階段', 'phase', root], ['上層', 'task', '階段'], ['中層', 'task', '上層'], ['底層', 'task', '中層'],
    ['另一個', 'task', '階段'], ['待移動', 'task', '階段']] as const) {
    const response = await page.request.post(`/api/projects/${projectId}/nodes`, { data: { title: name, kind, parent_id: ids[parent] ?? parent } });
    expect(response.status()).toBe(201);
    ids[name] = (await response.json()).id;
  }
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
const column = (page: Page, label: string) => board(page).locator(`[aria-label="${label}"]`);
const headProgress = (page: Page) => page.getByLabel('節點詳情').locator('.progress');
// A task page loads its report card above the board; drag only after that layout has settled.
const settled = (page: Page) => expect(page.getByText('載入回報狀態中')).toHaveCount(0);

test('TP-A drag, weighted progress through four levels, parent rule and move at 1280px', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  const problems = watch(page);
  await login(page, 'yu');
  const title = `TP-A ${randomUUID()}`;
  const { projectId, ids } = await fourLevels(page, title);
  await page.reload();
  await (await openProjects(page)).getByRole('button', { name: title, exact: true }).click();
  await expect(page.getByRole('heading', { name: title, exact: true })).toBeVisible();
  await page.getByRole('button', { name: '進入階段：階段' }).click();
  await expect(card(page, '上層')).toContainText('0/1 子任務');
  await expect(page.getByText('拖曳卡片改狀態；拖到另一張卡片上 = 變成它的子任務')).toBeVisible();

  // Drill down by cards to the deepest level and drag the leaf into 進行中.
  await card(page, '上層').getByRole('button', { name: '上層', exact: true }).click();
  await card(page, '中層').getByRole('button', { name: '中層', exact: true }).click();
  await settled(page);
  await card(page, '底層').dragTo(column(page, '進行中'));
  await expect(column(page, '進行中')).toContainText('底層');
  await expect(headProgress(page)).toHaveAttribute('aria-label', '進度 50%');

  // Parent rule: 中層 cannot be reported while 底層 is open.
  await page.getByRole('navigation', { name: '節點路徑' }).getByRole('button', { name: '上層', exact: true }).click();
  await expect(card(page, '中層')).toContainText('0/1 子任務');
  await expect(card(page, '中層')).toContainText('50%');
  await expect(headProgress(page)).toHaveAttribute('aria-label', '進度 50%');
  await settled(page);
  await card(page, '中層').dragTo(column(page, '完成'));
  await expect(page.getByRole('alert')).toHaveText('還有 1 項子任務未完成：底層');
  await page.getByRole('navigation', { name: '節點路徑' }).getByRole('button', { name: '階段', exact: true }).click();
  // 上層 50, 另一個 0, 待移動 0 → 17.
  await expect(headProgress(page)).toHaveAttribute('aria-label', '進度 17%');
  const blockedDone = page.getByLabel('節點詳情').getByRole('option', { name: '完成（還有 3 項子任務未完成）' });
  expect(await blockedDone.evaluate(option => ({ disabled: (option as HTMLOptionElement).disabled, attr: option.getAttribute('disabled') }))).toEqual({ disabled: true, attr: '' });

  // Quick report on the leaf, then each parent can be reported in turn.
  await card(page, '上層').getByRole('button', { name: '上層', exact: true }).click();
  await card(page, '中層').getByRole('button', { name: '中層', exact: true }).click();
  await card(page, '底層').getByRole('button', { name: '回報完成：底層' }).click();
  await expect(page.getByRole('heading', { name: '底層', exact: true })).toBeVisible();
  const form = page.getByRole('form', { name: '回報表單' });
  await form.getByLabel('成果說明').fill('完成底層');
  await form.getByLabel('實際完成日').fill('2026-10-10');
  await form.getByRole('button', { name: '送出並確認', exact: true }).click();
  await expect(page.getByLabel('完成回報')).toContainText('已完成');
  for (const name of ['中層', '上層']) {
    await page.getByRole('navigation', { name: '節點路徑' }).getByRole('button', { name, exact: true }).click();
    await page.getByLabel('完成回報').getByRole('button', { name: '回報完成', exact: true }).click();
    await page.getByLabel('成果說明').fill(`完成${name}`);
    await page.getByLabel('實際完成日').fill('2026-10-10');
    await page.getByRole('button', { name: '送出並確認', exact: true }).click();
    await expect(page.getByLabel('完成回報')).toContainText('已完成');
    await expect(headProgress(page)).toHaveAttribute('aria-label', '進度 100%');
  }
  await page.getByRole('navigation', { name: '節點路徑' }).getByRole('button', { name: '階段', exact: true }).click();
  // 上層 100, 另一個 0, 待移動 0 → 33.
  await expect(headProgress(page)).toHaveAttribute('aria-label', '進度 33%');

  // Move: drop 待移動 on 另一個, then the moved card appears as its subtask.
  await card(page, '待移動').dragTo(card(page, '另一個'));
  await expect(page.getByText('已將「待移動」移到「另一個」底下')).toBeVisible();
  await expect(card(page, '另一個')).toContainText('0/1 子任務');
  await expect(card(page, '待移動')).toHaveCount(0);
  // 上層 100, 另一個 0 → 50.
  await expect(headProgress(page)).toHaveAttribute('aria-label', '進度 50%');

  // Node-scoped timeline with a way back up.
  await page.getByRole('tab', { name: '時程' }).click();
  await expect(page.getByText('展開圖・子任務（5）')).toBeVisible();
  await page.getByRole('button', { name: `↑ 上一層：${title}` }).click();
  await expect(page.getByText('總覽圖・任務（5）')).toBeVisible();

  // Everything persists after reloading the page.
  await page.reload();
  await (await openProjects(page)).getByRole('button', { name: title, exact: true }).click();
  await expect(page.getByLabel('開發階段與閘門').getByRole('button', { name: '進入階段：階段' })).toHaveAccessibleDescription('50% ● 目前階段');
  const detail = await (await page.request.get(`/api/projects/${projectId}`)).json();
  const byId = Object.fromEntries(detail.nodes.map((n: { id: string; status: string; parent_id: string }) => [n.id, n]));
  expect([byId[ids['底層']].status, byId[ids['中層']].status, byId[ids['上層']].status]).toEqual(['done', 'done', 'done']);
  expect(byId[ids['待移動']].parent_id).toBe(ids['另一個']);
  const audit = await (await page.request.get(`/api/audit-logs?node_id=${ids['待移動']}&action=node.move`)).json();
  expect(audit.items[0].payload).toMatchObject({ from_parent_title: '階段', to_parent_title: '另一個' });
  expect(problems).toEqual([]);
});

test('TP-A board stays inside the page at 375px and the status menu still works', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  const problems = watch(page);
  await login(page, 'yu');
  const title = `TP-A 375 ${randomUUID()}`;
  await fourLevels(page, title);
  await page.reload();
  await page.getByRole('button', { name: '切換導覽' }).click();
  await (await openProjects(page)).getByRole('button', { name: title, exact: true }).click();
  await page.getByRole('button', { name: '進入階段：階段' }).click();
  await expect(card(page, '上層')).toContainText('0/1 子任務');
  await card(page, '另一個').getByLabel('另一個狀態').selectOption('doing');
  await expect(column(page, '進行中')).toContainText('另一個');
  await card(page, '上層').getByRole('button', { name: '展開下一層：上層' }).click();
  await expect(card(page, '上層').getByRole('list', { name: '上層的下一層' })).toContainText('中層');
  expect(await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)).toBeLessThanOrEqual(0);
  await page.screenshot({ path: 'test-results/tp-a-board-375.png', fullPage: true });
  expect(problems).toEqual([]);
});

for (const width of [1280, 1440, 375]) test(`TP-A screenshots for Demo comparison at ${width}px`, async ({ page }) => {
  test.setTimeout(60000);
  await page.setViewportSize({ width, height: 900 });
  const problems = watch(page);
  await login(page, 'yu');
  const title = `TP-A 對照 ${width} ${randomUUID()}`;
  const created = await (await page.request.post('/api/projects', { data: { title } })).json();
  const root = (await (await page.request.get(`/api/projects/${created.id}`)).json()).nodes[0].id as string;
  const ids: Record<string, string> = {};
  const rows: [string, string, string, string, string][] = [
    ['市場與配方', 'phase', root, '2026-09-01', '2026-09-20'], ['小量試作', 'phase', root, '2026-09-21', '2026-10-31'],
    ['原料採購（試作用）', 'task', '小量試作', '2026-09-21', '2026-09-28'], ['小量試作與質地調整', 'task', '小量試作', '2026-10-01', '2026-10-30'],
    ['第 1 批試作', 'task', '小量試作與質地調整', '2026-10-01', '2026-10-08'], ['質地與外觀調整', 'task', '小量試作與質地調整', '2026-10-09', '2026-10-20'],
    ['內部品評', 'task', '小量試作與質地調整', '2026-10-21', '2026-10-30'], ['包材確認', 'task', '小量試作', '2026-10-15', '2026-10-25'],
  ];
  for (const [name, kind, parent, start, due] of rows) {
    const response = await page.request.post(`/api/projects/${created.id}/nodes`, { data: { title: name, kind, parent_id: ids[parent] ?? parent, start_date: start, due_date: due } });
    ids[name] = (await response.json()).id;
  }
  for (const name of ['原料採購（試作用）', '第 1 批試作']) {
    await page.request.patch(`/api/nodes/${ids[name]}/status`, { data: { status: 'doing' } });
    await page.request.post(`/api/nodes/${ids[name]}/reports`, { data: { result: '達成', summary: `${name}完成`, finished_on: '2026-10-08', attachment_ids: [], self_approve: true } });
  }
  for (const name of ['小量試作與質地調整', '質地與外觀調整']) await page.request.patch(`/api/nodes/${ids[name]}/status`, { data: { status: 'doing' } });
  await page.request.post(`/api/projects/${created.id}/dependencies`, { data: { predecessor_id: ids['小量試作與質地調整'], successor_id: ids['包材確認'] } });
  await page.request.post(`/api/projects/${created.id}/dependencies`, { data: { predecessor_id: ids['質地與外觀調整'], successor_id: ids['內部品評'] } });
  await page.reload();
  const dir = '../.superpowers/tpa/e2e'; await mkdir(dir, { recursive: true });
  const shot = async (name: string) => {
    await expect(page.getByRole('status').filter({ hasText: '載入' })).toHaveCount(0);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: `${dir}/formal-${name}-${width}.png` });
  };
  if (width === 375) await page.getByRole('button', { name: '切換導覽' }).click();
  await (await openProjects(page)).getByRole('button', { name: title, exact: true }).click();
  await page.getByRole('button', { name: '進入階段：小量試作' }).click();
  const parent = card(page, '小量試作與質地調整');
  await expect(parent).toContainText('1/3 子任務');
  await parent.getByRole('button', { name: '展開下一層：小量試作與質地調整' }).click();
  await expect(card(page, '包材確認')).toContainText('等待：小量試作與質地調整');
  if (width !== 375) {
    await card(page, '包材確認').hover();
    await expect(parent).toHaveClass(/\bhl\b/);
  }
  await shot('phase-board-expanded');
  await page.getByRole('tab', { name: '時程', exact: true }).click(); await expect(page.getByText('展開圖・子任務（6）')).toBeVisible(); await shot('phase-timeline');
  await page.getByRole('tab', { name: '相依圖', exact: true }).click(); await expect(page.getByLabel('可見任務相依圖')).toBeVisible(); await shot('phase-graph');
  await page.getByRole('navigation', { name: '節點路徑' }).getByRole('button', { name: title }).first().click();
  await page.getByRole('tab', { name: '紀錄', exact: true }).click(); await expect(page.getByText(/這是上層節點，以下彙總整棵子樹/)).toBeVisible(); await shot('project-records');
  expect(problems).toEqual([]);
});
