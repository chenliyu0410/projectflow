import { openAccount } from './navigation';
import { test, expect, type Page } from '@playwright/test';

async function login(page: Page, user: string, password: string) {
  await page.goto('/');
  await page.getByLabel('帳號').fill(user); await page.getByLabel('密碼').fill(password);
  await page.getByRole('button', { name: '登入', exact: true }).click();
}
async function logout(page: Page) {
  await (await openAccount(page)).getByRole('button', { name: '登出', exact: true }).click();
  await expect(page.getByRole('heading', { name: '登入專流' })).toBeVisible();
}
async function accountsPage(page: Page, width: number) {
  if (width === 375) await page.getByRole('button', { name: '切換導覽', exact: true }).click();
  await page.getByRole('navigation', { name: '工作區導覽' }).getByRole('button', { name: '帳號與密碼' }).click();
}

for (const width of [1280, 375]) test(`admin adds, user changes temporary password, admin disables ${width}`, async ({ page, request }, info) => {
  expect(await (await request.get('/api/health/acceptance')).json()).toEqual({ acceptance: true });
  await page.setViewportSize({ width, height: 900 });
  const errors: string[] = []; page.on('pageerror', e => errors.push(String(e)));
  const username = `wang${width}${Date.now() % 100000}`;

  await login(page, 'yu', 'demo-yu');
  await expect(page.getByRole('heading', { name: '所有專案總覽' })).toBeVisible();
  await accountsPage(page, width);
  const manager = page.getByRole('region', { name: '帳號管理' });
  await manager.getByLabel('新帳號', { exact: true }).fill(username);
  await manager.getByLabel('新帳號顯示名稱').fill('王小明');
  await manager.getByRole('button', { name: '新增帳號' }).click();
  const temporary = (await manager.locator('.temporary-password').textContent())!.trim();
  expect(temporary.length).toBeGreaterThanOrEqual(10);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: info.outputPath(`accounts-${width}.png`), fullPage: true });
  await manager.getByRole('button', { name: '我已經記下了' }).click();
  await logout(page);

  await login(page, username, temporary);
  const forced = page.getByRole('region', { name: '修改密碼' });
  await expect(forced.getByRole('heading', { name: '請先設定你自己的密碼' })).toBeVisible();
  await forced.getByLabel('臨時密碼').fill(temporary);
  await forced.getByLabel('新密碼', { exact: true }).fill('wang-new-password');
  await forced.getByLabel('再輸入一次新密碼').fill('wang-new-password');
  await forced.getByRole('button', { name: '儲存新密碼' }).click();
  await expect(page.getByRole('heading', { name: '所有專案總覽' })).toBeVisible();
  await logout(page);

  await login(page, 'yu', 'demo-yu');
  await expect(page.getByRole('heading', { name: '所有專案總覽' })).toBeVisible();
  await accountsPage(page, width);
  page.once('dialog', dialog => dialog.accept());
  await manager.getByRole('listitem').filter({ hasText: username }).getByRole('button', { name: '停用' }).click();
  await expect(manager.getByRole('status')).toContainText('已停用「王小明」');
  await logout(page);
  await login(page, username, 'wang-new-password');
  await expect(page.getByRole('alert')).toContainText('帳號或密碼錯誤');
  expect(errors).toEqual([]);
});

test('members only see their own password form', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await login(page, 'lin', 'demo-lin');
  await expect(page.getByRole('heading', { name: '所有專案總覽' })).toBeVisible();
  await accountsPage(page, 1280);
  await expect(page.getByRole('region', { name: '修改密碼' })).toBeVisible();
  await expect(page.getByRole('region', { name: '帳號管理' })).toHaveCount(0);
});
