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
  await expect(page.getByRole('navigation', { name: '工作區導覽' })).toBeVisible();
}

for (const width of [1280, 375]) {
  test(`P2a admin four levels and member workspace at ${width}px`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: 900 });
    const errors: string[] = [];
    page.on('pageerror', error => errors.push(String(error)));
    await login(page, 'yu');
    const title = `P2a ${width} ${randomUUID()}`;
    await page.getByRole('button', { name: '新增空白專案', exact: true }).click();
    await page.getByLabel('新專案名稱').fill(title);
    await page.getByRole('button', { name: '建立專案', exact: true }).click();
    await expect(page.getByRole('heading', { name: title, exact: true })).toBeVisible();
    const projects = await page.request.get('/api/projects');
    const projectId = (await projects.json()).items.find((p: { title: string }) => p.title === title).id;
    const options = await page.request.get(`/api/projects/${projectId}/assignment-options`);
    expect(options.status()).toBe(200);
    // Resolve the seed member through the real session rather than assuming a display name.
    const memberLogin = await page.request.post('/api/auth/login', { data: { organization_key: 'food', username: 'ming', password: 'demo-ming' } });
    const memberId = (await memberLogin.json()).user.id;
    await page.request.post('/api/auth/login', { data: { organization_key: 'food', username: 'yu', password: 'demo-yu' } });
    for (const [name, kind] of [['階段甲', 'phase'], ['父任務', 'task'], ['子任務', 'task']]) {
      await page.getByRole('button', { name: '新增子節點', exact: true }).click();
      await page.getByLabel('節點名稱').fill(name);
      await page.getByLabel('種類', { exact: true }).selectOption(kind);
      await page.getByLabel('負責人', { exact: true }).selectOption(memberId);
      await page.getByLabel('開始日期').fill('2026-10-08');
      await page.getByLabel('截止日期').fill('2026-10-12');
      await page.getByRole('button', { name: '儲存', exact: true }).click();
      await page.getByLabel('節點樹').getByRole('button', { name, exact: true }).click();
    }
    await page.getByRole('button', { name: '編輯節點', exact: true }).click();
    await page.getByLabel('節點名稱').fill('子任務更新');
    await page.getByLabel('開始日期').fill('');
    await page.getByRole('button', { name: '儲存', exact: true }).click();
    await expect(page.getByLabel('節點詳情')).toContainText('子任務更新');
    const persisted = await page.request.get(`/api/projects/${projectId}`);
    const child = (await persisted.json()).nodes.find((n: { title: string }) => n.title === '子任務更新');
    expect(child.start_date).toBeNull();
    expect(child.due_date).toBe('2026-10-12');
    await page.getByRole('button', { name: '登出', exact: true }).click();
    await login(page, 'ming');
    await page.getByRole('button', { name: '我的任務', exact: true }).click();
    await page.getByLabel('搜尋任務').fill(title);
    await page.getByRole('button', { name: '子任務更新', exact: true }).click();
    await expect(page.getByLabel('節點詳情')).toContainText('2026-10-12');
    await expect(page.getByRole('button', { name: '新增子節點', exact: true })).toHaveCount(0);
    await page.getByRole('button', { name: '編輯節點', exact: true }).click();
    await expect(page.getByLabel('負責人', { exact: true })).toHaveCount(0);
    await page.getByRole('button', { name: '取消', exact: true }).click();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: info.outputPath(`workspace-${width}.png`), fullPage: true });
    await page.getByRole('button', { name: '登出', exact: true }).click();
    await login(page, 'lin');
    await page.getByRole('button', { name: '專案工作區', exact: true }).click();
    await page.getByLabel('專案清單').getByRole('button', { name: title, exact: true }).click();
    await expect(page.getByRole('button', { name: '編輯節點', exact: true })).toHaveCount(0);
    expect((await page.request.patch(`/api/nodes/${child.id}`, { data: { title: '拒絕' } })).status()).toBe(403);
    expect(errors).toEqual([]);
  });
}
