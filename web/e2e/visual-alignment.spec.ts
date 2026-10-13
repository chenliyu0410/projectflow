import { openProjects } from './navigation';
import { expect, test } from '@playwright/test';
import { randomUUID } from 'node:crypto';
import { mkdir } from 'node:fs/promises';

for (const width of [1280, 375]) test(`UI1 visual alignment and navigation at ${width}px`, async ({ page, request, baseURL }) => {
  test.setTimeout(60000);
  expect(new URL(baseURL!).port).toBe('15175');
  expect(await (await request.get('/api/health/acceptance')).json()).toEqual({ acceptance: true });
  const login = await request.post('/api/auth/login', { data: { organization_key: 'food', username: 'yu', password: 'demo-yu' } });
  expect(login.status()).toBe(200);
  const user = (await login.json()).user;
  const title = `UI1 介面驗收 ${width} ${randomUUID()}`;
  const project = await request.post('/api/projects', { data: { title } });
  expect(project.status()).toBe(201);
  const pid = (await project.json()).id;
  for (const [i, name] of ['需求確認與規格整理', '產品設計與驗證', '長標題任務：確認所有跨部門協作內容與交付文件皆能完整閱讀'].entries()) {
    const node = await request.post(`/api/projects/${pid}/nodes`, { data: { title: name, kind: 'task', owner_user_id: user.id, start_date: `2026-10-${10+i}`, due_date: `2026-10-${15+i}` } });
    expect(node.status()).toBe(201);
  }
  const errors: string[] = [];
  page.on('pageerror', e => errors.push(String(e)));
  page.on('console', m => { if (m.type() === 'error' && !m.text().includes('401')) errors.push(m.text()); });
  await page.setViewportSize({ width, height: 900 });
  await page.goto('/');
  await page.getByLabel('帳號').fill('yu'); await page.getByLabel('密碼').fill('demo-yu');
  await page.getByRole('button', { name: '登入', exact: true }).click();
  await expect(page.getByLabel('可見任務完成率', { exact: true })).toBeVisible();
  const dir = '../.superpowers/ui4/e2e'; await mkdir(dir, { recursive: true });
  const capture = async (name: string) => {
    if (name !== 'loading') await expect(page.getByRole('status').filter({ hasText: '載入' })).toHaveCount(0);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    expect(await page.locator('.workspace-content').evaluate(el => el.scrollWidth <= el.clientWidth)).toBe(true);
    await page.screenshot({ path: `${dir}/formal-${name}-${width}.png` });
  };
  const menu = async () => { if (width === 375) await page.getByRole('button', { name: '切換導覽' }).click(); };
  const nav = async (name: string) => { await menu(); await page.getByRole('button', { name, exact: true }).click(); };
  await capture('overview');
  if (width === 1280) {
    expect(await page.locator('.workspace-navigation').evaluate(el => el.getBoundingClientRect().width)).toBe(252);
    // Collapsed assistant leaves the full area beside the 252px navigation.
    expect(await page.locator('.workspace-main').evaluate(el => el.getBoundingClientRect().width)).toBe(1028);
    await expect(page.getByRole('complementary', { name: 'AI 專案副手' })).toBeHidden();
    await openProjects(page);
    // Long project names must not overlap their next sibling in the scrolling sidebar.
    expect(await page.locator('.sidebar-projects').evaluate(el => [...el.children].every((a, i, list) => i === 0 || a.getBoundingClientRect().top >= list[i-1].getBoundingClientRect().bottom))).toBe(true);
    await page.getByRole('button', { name: '關閉專案選單' }).click();
  } else {
    await openProjects(page); await expect(page.getByLabel('專案清單')).toBeVisible(); await page.screenshot({ path: `${dir}/formal-navigation-${width}.png` });
    // Escape works from sidebar content and returns focus to its trigger.
    await page.getByRole('button', { name: '所有專案總覽', exact: true }).focus(); await page.keyboard.press('Escape');
    await expect(page.getByRole('button', { name: '切換導覽' })).toBeFocused();
  }
  await nav('我的任務'); await expect(page.getByRole('heading', { name: '我的任務', exact: true })).toBeVisible();
  await page.getByLabel('搜尋任務').fill(title); await expect(page.locator('.task-group tbody tr')).toHaveCount(3); await capture('tasks');
  await menu(); await (await openProjects(page)).getByRole('button', { name: title, exact: true }).click();
  await expect(page.getByRole('heading', { name: title, exact: true })).toBeVisible(); await capture('workspace');
  // UI4: Demo board is four columns (148px each at 1280 with the copilot open, 240px scrolling inside the board on phones).
  expect(await page.locator('.kanban-column').evaluateAll(cols => cols.map(c => Math.round(c.getBoundingClientRect().width)))).toEqual(Array(4).fill(width === 1280 ? 227 : 240));
  await page.getByRole('tab', { name: '時程', exact: true }).click(); await expect(page.getByLabel('專案時程')).toBeVisible(); await capture('timeline');
  await page.getByRole('tab', { name: '相依圖', exact: true }).click(); await expect(page.getByLabel('前置設定')).toBeVisible(); await capture('dependencies');
  await page.getByRole('tab', { name: '看板', exact: true }).click();
  await page.getByLabel('看板').getByRole('button', { name: '需求確認與規格整理', exact: true }).click();
  await expect(page.getByRole('tab', { name: '紀錄', exact: true })).toHaveAttribute('aria-selected', 'true');
  await expect(page.getByRole('textbox', { name: '成果說明', exact: true })).toHaveCount(0);
  await page.getByLabel('完成回報', { exact: true }).getByRole('button', { name: '回報完成', exact: true }).click();
  await expect(page.getByRole('textbox', { name: '成果說明', exact: true })).toBeVisible(); await capture('records');
  await page.getByRole('button', { name: '取消回報', exact: true }).click();
  await page.getByRole('tab', { name: '成員與權限', exact: true }).click(); await expect(page.getByLabel('此節點的成員')).toContainText('負責人'); await capture('people');
  for (const [label, heading, name] of [['模板庫','模板庫','templates'],['審核中心','審核中心','reviews'],['活動與稽核紀錄','稽核紀錄','audit']]) {
    await nav(label); await expect(page.getByRole('heading', { name: heading, exact: true })).toBeVisible(); await capture(name);
  }
  expect(errors).toEqual([]);
  await nav('我的任務');
  await page.getByLabel('搜尋任務').fill(`不存在-${randomUUID()}`);
  await expect(page.getByText('沒有符合篩選的任務')).toBeVisible(); await capture('empty');
  let release!: () => void;
  const held = new Promise<void>(resolve => { release = resolve; });
  await page.route('**/api/workspace/overview', async route => { await held; await route.continue(); }, { times: 1 });
  await nav('所有專案總覽'); await expect(page.getByText('載入總覽中')).toBeVisible(); await capture('loading');
  release(); await expect(page.getByLabel('可見任務完成率', { exact: true })).toBeVisible();
  await nav('我的任務');
  await page.route('**/api/workspace/overview', route => route.fulfill({ status: 503, contentType: 'application/json', body: '{}' }), { times: 1 });
  await nav('所有專案總覽'); await expect(page.getByRole('alert')).toBeVisible(); await capture('error');
  await page.getByRole('button', { name: '重試總覽' }).click(); await expect(page.getByLabel('可見任務完成率', { exact: true })).toBeVisible();
  expect((await page.request.post('/api/auth/logout')).status()).toBe(204);
  await nav('我的任務'); await expect(page.getByRole('heading', { name: '登入專流' })).toBeVisible();
  await expect(page.getByRole('alert')).toHaveText('登入已失效，請重新登入');
  await page.screenshot({ path: `${dir}/formal-expired-${width}.png` });
  expect(errors).toHaveLength(1); expect(errors[0]).toMatch(/503/);
});
