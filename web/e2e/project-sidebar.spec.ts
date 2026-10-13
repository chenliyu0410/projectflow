import { expect, test } from '@playwright/test';
import { openProjects } from './navigation';

for (const [width, height] of [[1280, 720], [375, 667], [844, 390]]) {
  test(`project flyout and connected views at ${width}x${height}`, async ({ page, request }, info) => {
    expect(await (await request.get('/api/health/acceptance')).json()).toEqual({ acceptance: true });
    await page.setViewportSize({ width, height });
    await page.goto('/');
    await page.getByLabel('帳號', { exact: true }).fill('yu');
    await page.getByLabel('密碼', { exact: true }).fill('demo-yu');
    await page.getByRole('button', { name: '登入', exact: true }).click();
    await expect(page.getByLabel('可見任務完成率', { exact: true })).toBeVisible();
    await expect(page.getByLabel('專案清單')).toBeHidden();
    const panel = await openProjects(page);
    if (width > 860) {
      await page.mouse.click(width - 370, 10);
      await expect(panel).toBeHidden();
      await expect(page.getByRole('button', { name:'專案', exact:true })).toBeFocused();
      await openProjects(page);
    }
    const projects = panel.locator('.sidebar-projects');
    const buttons = projects.getByRole('button');
    await expect(buttons).not.toHaveCount(0);
    for (const button of await buttons.all()) {
      await button.scrollIntoViewIfNeeded();
      await button.click({ trial: true });
      const bounds = await button.evaluate(el => {
        const row = el.getBoundingClientRect(), list = el.parentElement!.getBoundingClientRect();
        const title = el.querySelector('.project-name')!;
        return { top: row.top, bottom: row.bottom, min: list.top, max: list.bottom,
          titleWidth: title.clientWidth, contentWidth: title.scrollWidth };
      });
      expect(bounds.top).toBeGreaterThanOrEqual(bounds.min - 1);
      expect(bounds.bottom).toBeLessThanOrEqual(bounds.max + 1);
      expect(bounds.contentWidth).toBeLessThanOrEqual(bounds.titleWidth + 1);
    }
    await panel.getByRole('button', { name: '建立新專案' }).click({ trial: true });
    await page.screenshot({ path: info.outputPath('project-menu.png') });
    await page.keyboard.press('Escape');
    await expect(panel).toBeHidden();
    await expect(page.getByRole('button', { name: '專案', exact: true })).toBeFocused();
    await openProjects(page);
    await projects.getByRole('button', { name: '成貓主食罐正式版', exact: true }).click();
    await expect(panel).toBeHidden();
    await expect(page.getByRole('heading', { level: 1, name: '成貓主食罐正式版', exact: true })).toBeVisible();
    for (const name of ['看板', '時程', '相依圖']) {
      await page.getByRole('tab', { name, exact: true }).click();
      await expect(page.getByRole('tab', { name, exact: true })).toHaveAttribute('aria-selected', 'true');
      const connection = await page.locator('.node-views').evaluate(el => {
        const tab = el.querySelector('[aria-selected=true]')!, content = el.querySelector('.node-view-content')!;
        return { tabColor: getComputedStyle(tab).backgroundColor, contentColor: getComputedStyle(content).backgroundColor,
          gap: content.getBoundingClientRect().top - tab.getBoundingClientRect().bottom };
      });
      await expect.poll(() => page.getByRole('tab', { name, exact: true }).evaluate(el => getComputedStyle(el).backgroundColor)).toBe(connection.contentColor);
      expect(Math.abs(connection.gap)).toBeLessThan(1);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    }
    await page.getByRole('tab', { name:'看板', exact:true }).click();
    await expect(page.getByRole('tab', { name:'看板', exact:true })).toHaveCSS('background-color', 'rgb(255, 255, 255)');
    await page.screenshot({ path: info.outputPath('connected-tabs.png') });
    // Native scroll activity does not change the available layout width.
    const scroller = page.locator('.workspace-content');
    const initialWidth = await scroller.evaluate(el => el.clientWidth);
    await scroller.evaluate(el => { el.scrollTop = el.scrollHeight; });
    await expect(scroller).toHaveAttribute('data-scroll-active','true');
    await expect(scroller).not.toHaveAttribute('data-scroll-active','true');
    expect(await scroller.evaluate(el => el.clientWidth)).toBe(initialWidth);
    await expect.poll(() => scroller.evaluate(el => getComputedStyle(el).scrollbarColor)).toBe('rgba(0, 0, 0, 0) rgba(0, 0, 0, 0)');
  });
}
