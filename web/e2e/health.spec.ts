import { expect, test } from '@playwright/test';

test('proxy verifies actual database readiness', async ({ request }) => {
  const live = await request.get('/api/health');
  expect(live.status()).toBe(200);
  expect(await live.json()).toEqual({ ok: true });
  const ready = await request.get('/api/health/ready');
  expect(ready.status()).toBe(200);
  expect(await ready.json()).toEqual({ ok: true, database: 'ready' });
});

for (const width of [1280, 375]) {
  test(`usable health surface at ${width}px`, async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', error => errors.push(String(error)));
    page.on('console', message => {
      if (message.type() === 'error') errors.push(message.text());
    });
    await page.setViewportSize({ width, height: 900 });
    await page.goto('/');
    await expect(page.getByRole('heading', { name: '服務狀態' })).toBeVisible();
    await expect(page.getByRole('status')).toHaveText('已連線');
    await page.getByRole('button', { name: '重新檢查' }).click();
    await expect(page.getByRole('status')).toHaveText('已連線');
    expect(await page.locator('header img').evaluate((img: HTMLImageElement) => img.complete && img.naturalWidth > 0)).toBe(true);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: `test-results/p0-${width}.png`, fullPage: true });
    expect(errors).toEqual([]);
  });
}

test('unknown API path is not served as frontend HTML', async ({ request }) => {
  const response = await request.get('/api/missing');
  expect(response.status()).toBe(404);
  expect(response.headers()['content-type']).toContain('application/json');
});
