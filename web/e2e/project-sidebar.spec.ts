import { expect, test } from '@playwright/test';
import { randomUUID } from 'node:crypto';

for (const [width, height] of [[1920, 1080], [1280, 720], [1024, 600], [375, 667], [844, 390]]) {
  test(`all sidebar projects remain readable and selectable at ${width}x${height}`, async ({ page, request }, info) => {
    expect(await (await request.get('/api/health/acceptance')).json()).toEqual({ acceptance: true });
    await page.setViewportSize({ width, height });
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto('/');
    await page.getByLabel('帳號', { exact: true }).fill('yu');
    await page.getByLabel('密碼', { exact: true }).fill('demo-yu');
    await page.getByRole('button', { name: '登入', exact: true }).click();
    await expect(page.getByLabel('可見任務完成率', { exact: true })).toBeVisible();
    const title = '側欄完整名稱驗證：跨部門產品開發與上市時程專案 ' + randomUUID().slice(0, 8);
    const created = await page.request.post('/api/projects', { data: { title } });
    expect(created.status()).toBe(201);
    await page.reload();
    if (width <= 860) await page.getByRole('button', { name: '切換導覽' }).click();
    const navigation = page.locator('#workspace-navigation');
    const projects = page.locator('.sidebar-projects');
    const buttons = projects.getByRole('button');
    await expect(buttons).not.toHaveCount(0);
    // A complete row must fit in the list before attempting to scroll/click it.
    const sizes = await projects.evaluate(el => ({ list: el.clientHeight, row: el.querySelector('button')!.getBoundingClientRect().height }));
    expect(sizes.list).toBeGreaterThanOrEqual(sizes.row);
    for (const button of await buttons.all()) {
      await button.scrollIntoViewIfNeeded();
      await button.click({ trial: true });
      const bounds = await button.evaluate(el => {
        const row = el.getBoundingClientRect();
        const nav = el.closest('#workspace-navigation')!.getBoundingClientRect();
        const list = el.parentElement!;
        const listBox = list.getBoundingClientRect();
        const clips = ['auto', 'scroll', 'hidden', 'clip'].includes(getComputedStyle(list).overflowY);
        const title = el.querySelector('.project-name')!;
        return { top: row.top, bottom: row.bottom, visibleTop: Math.max(0, nav.top, clips ? listBox.top : 0),
          visibleBottom: Math.min(innerHeight, nav.bottom, clips ? listBox.bottom : innerHeight),
          titleWidth: title.clientWidth, titleContentWidth: title.scrollWidth, rowWidth: el.clientWidth, rowContentWidth: el.scrollWidth };
      });
      expect(bounds.top).toBeGreaterThanOrEqual(bounds.visibleTop - 1);
      expect(bounds.bottom).toBeLessThanOrEqual(bounds.visibleBottom + 1);
      expect(bounds.titleContentWidth).toBeLessThanOrEqual(bounds.titleWidth + 1);
      expect(bounds.rowContentWidth).toBeLessThanOrEqual(bounds.rowWidth + 1);
    }
    await navigation.getByRole('button', { name: /建立新專案/ }).click({ trial: true });
    await navigation.getByRole('button', { name: '登出', exact: true }).click({ trial: true });
    expect(await navigation.evaluate(el => el.scrollWidth <= el.clientWidth)).toBe(true);
    const target = projects.getByRole('button', { name: title, exact: true });
    await target.scrollIntoViewIfNeeded();
    await page.screenshot({ path: info.outputPath('sidebar-projects.png') });
    await target.click();
    await expect(page.getByRole('heading', { level: 1, name: title, exact: true })).toBeVisible();
    if (width <= 860) await expect(navigation).toBeHidden();
    else await expect(target).toHaveAttribute('aria-pressed', 'true');
  });
}
