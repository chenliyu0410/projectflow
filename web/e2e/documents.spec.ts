import { test, expect } from '@playwright/test';
import { readFile } from 'node:fs/promises';

for (const width of [1280, 375]) test(`persistent documents ${width}`, async ({ page, request }, info) => {
  expect(await (await request.get('/api/health/acceptance')).json()).toEqual({ acceptance: true });
  await page.setViewportSize({ width, height: 900 });
  const errors: string[] = []; page.on('pageerror', e => errors.push(String(e)));
  await page.goto('/');
  await page.getByLabel('帳號').fill('yu'); await page.getByLabel('密碼').fill('demo-yu');
  await page.getByRole('button', { name: '登入', exact: true }).click();
  await expect(page.getByRole('heading', { name: '所有專案總覽' })).toBeVisible();
  async function enter() {
    if (width === 375) await page.getByRole('button', { name: '切換導覽' }).click();
    await page.getByLabel('專案清單').getByRole('button').first().click();
    await page.getByRole('tab', { name: '文件', exact: true }).click();
  }
  await enter();
  const filename = `文件驗收-${width}-${Date.now()}.txt`;
  await page.getByLabel('上傳新文件', { exact: true }).setInputFiles({ name: filename, mimeType: 'text/plain', buffer: Buffer.from('原始版本') });
  await expect(page.getByRole('link', { name: '下載 v1' })).toBeVisible();
  await page.getByRole('button', { name: '編輯文字', exact: true }).click();
  await page.getByLabel('編輯文件內容').fill('正式儲存的新版本');
  page.once('dialog', dialog => dialog.dismiss());
  await page.getByRole('tab', { name: '看板', exact: true }).click();
  await expect(page.getByLabel('編輯文件內容')).toHaveValue('正式儲存的新版本');
  await page.getByLabel('新版本說明').fill('修正內容');
  await page.getByRole('button', { name: '儲存新版本' }).click();
  await expect(page.getByRole('link', { name: '下載 v2' })).toBeVisible();
  await page.reload(); await expect(page.getByRole('heading', { name: '所有專案總覽' })).toBeVisible(); await enter();
  await page.getByRole('button', { name: new RegExp(filename) }).click();
  await expect(page.locator('.document-text')).toHaveText('正式儲存的新版本');
  await page.getByLabel('版本紀錄').selectOption('1');
  await expect(page.locator('.document-text')).toHaveText('原始版本');
  const downloading = page.waitForEvent('download'); await page.getByRole('link', { name: '下載 v1' }).click();
  const downloaded = await downloading; expect(await readFile((await downloaded.path())!, 'utf8')).toBe('原始版本');
  await page.getByLabel('版本紀錄').selectOption('2');
  await page.getByLabel('上傳新版本', { exact: true }).setInputFiles({ name: filename, mimeType: 'text/plain', buffer: Buffer.from('外部修改的第三版') });
  await expect(page.getByRole('link', { name: '下載 v3' })).toBeVisible();
  const link = await page.getByRole('link', { name: '下載 v3' }).getAttribute('href');
  const documentId = link!.split('/')[3];
  const results = await Promise.all(['race A', 'race B'].map(content => page.request.post(`/api/documents/${documentId}/text`, { data: { expected_version: 3, content } })));
  expect(results.map(result => result.status()).sort()).toEqual([201, 409]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  expect(await page.locator('.workspace-content').evaluate(el => el.scrollWidth <= el.clientWidth)).toBe(true);
  await page.screenshot({ path: info.outputPath(`documents-${width}.png`), fullPage: true });
  expect(errors).toEqual([]);
});
