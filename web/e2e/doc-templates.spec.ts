import { closeProjectDrawer, openProjects } from './navigation';
import { test, expect, type Page } from '@playwright/test';
import { readFile } from 'node:fs/promises';
import { inflateRawSync } from 'node:zlib';

/** Text of word/document.xml from a downloaded .docx (no extra dependency: read the zip entry by hand). */
async function docxText(path: string) {
  const data = await readFile(path);
  for (let offset = 0; offset < data.length - 30;) {
    if (data.readUInt32LE(offset) !== 0x04034b50) break;
    const method = data.readUInt16LE(offset + 8), size = data.readUInt32LE(offset + 18);
    const nameLength = data.readUInt16LE(offset + 26), extra = data.readUInt16LE(offset + 28);
    const name = data.subarray(offset + 30, offset + 30 + nameLength).toString();
    const start = offset + 30 + nameLength + extra, body = data.subarray(start, start + size);
    if (name === 'word/document.xml') return (method === 8 ? inflateRawSync(body) : body).toString('utf8').replace(/<[^>]+>/g, '|').replace(/\|+/g, '|');
    offset = start + size;
  }
  throw new Error('word/document.xml not found');
}

async function login(page: Page, user: string) {
  await page.goto('/');
  await page.getByLabel('帳號').fill(user); await page.getByLabel('密碼').fill(`demo-${user}`);
  await page.getByRole('button', { name: '登入', exact: true }).click();
  await expect(page.getByRole('heading', { name: '所有專案總覽' })).toBeVisible();
}

async function documents(page: Page, width: number) {
  if (width === 375) await page.getByRole('button', { name: '切換導覽' }).click();
  await (await openProjects(page)).locator('.sidebar-projects').getByRole('button').first().click(); await closeProjectDrawer(page);
  await page.getByRole('tab', { name: '文件', exact: true }).click();
}

async function download(page: Page, name: RegExp) {
  const waiting = page.waitForEvent('download'); await page.getByRole('link', { name }).click();
  return docxText((await (await waiting).path())!);
}

test('administrator adds sample templates and sets required fields', async ({ page, request }) => {
  expect(await (await request.get('/api/health/acceptance')).json()).toEqual({ acceptance: true });
  await page.setViewportSize({ width: 1280, height: 900 });
  await login(page, 'yu');
  await page.getByRole('button', { name: '模板庫', exact: true }).click();
  const library = page.getByRole('region', { name: '文件樣板' });
  await library.getByRole('button', { name: '加入三份範例樣板' }).click();
  await expect(library.getByRole('status')).toContainText(/範例/);
  await library.getByRole('listitem').filter({ hasText: '會議紀錄' }).getByRole('button', { name: '設定欄位' }).click();
  for (const name of ['會議名稱', '日期時間', '出席者', '決議']) await library.getByLabel(`${name} 必填`).check();
  await library.getByRole('button', { name: '儲存設定' }).click();
  await expect(library.getByRole('status')).toContainText('已儲存「會議紀錄」');
});

for (const width of [1280, 375]) test(`fill templates into documents ${width}`, async ({ page }, info) => {
  await page.setViewportSize({ width, height: 900 });
  const errors: string[] = []; page.on('pageerror', e => errors.push(String(e)));
  await login(page, 'yu');
  await documents(page, width);
  const panel = page.getByRole('region', { name: '正式文件管理' });

  await panel.getByRole('button', { name: '用樣板建立' }).click();
  const form = page.getByRole('region', { name: '用樣板建立文件' });
  await form.getByLabel('選擇樣板').selectOption({ label: '會議紀錄（會議）' });
  await form.getByLabel('會議名稱').fill('十月新人報到準備會議');
  await form.getByRole('button', { name: '產生文件' }).click();
  await expect(form.getByRole('alert')).toHaveText('請填寫「日期時間」');
  await form.getByLabel('日期時間').fill('2026-10-12 10:00–10:30');
  await form.getByLabel('出席者').fill('林怡安、陳柏宇、王雅婷');
  await form.getByLabel('決議').fill('新人 10/26 09:00 報到 <b>&{{x}}');
  await form.getByLabel('待辦／期限').fill('陳柏宇 10/23 備妥筆電');
  await form.getByRole('button', { name: '產生文件' }).click();
  await expect(panel.getByRole('status')).toContainText(/已產生 會議紀錄-MTG-\d{4}-\d{3}\.docx，版本 v1/);
  const meeting = await download(page, /下載 v1/);
  expect(meeting).toMatch(/MTG-\d{4}-\d{3}/);
  expect(meeting).toContain('新人 10/26 09:00 報到 &lt;b&gt;&amp;{{x}}');

  await panel.getByRole('button', { name: '用樣板建立' }).click();
  await form.getByLabel('選擇樣板').selectOption({ label: '報價單（業務）' });
  await form.getByLabel('客戶名稱').fill('好毛寵物用品（虛構）');
  await form.getByLabel('有效期限').fill('2026-11-22');
  await form.getByLabel('第 1 列品項').fill('成貓主食罐 鮪魚 85g'); await form.getByLabel('第 1 列數量').fill('2000'); await form.getByLabel('第 1 列單價').fill('32');
  await form.getByRole('button', { name: '新增一列' }).click();
  await form.getByLabel('第 2 列品項').fill('成貓主食罐 雞肉 85g'); await form.getByLabel('第 2 列數量').fill('1000'); await form.getByLabel('第 2 列單價').fill('30');
  await expect(form.getByLabel('金額合計')).toContainText('98,700');
  if (width === 375) expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await form.getByRole('button', { name: '產生文件' }).click();
  await expect(panel.getByRole('status')).toContainText(/報價單-Q-\d{4}-\d{4}-\d{2}\.docx/);
  const quote = await download(page, /下載 v1/);
  for (const amount of ['64,000', '30,000', '94,000', '4,700', '98,700']) expect(quote).toContain(amount);

  await panel.getByRole('button', { name: '用樣板建立' }).click();
  await form.getByLabel('選擇樣板').selectOption({ label: '工單（工單）' });
  for (const [label, value] of [['工單名稱', '新人筆電準備'], ['負責人', '陳柏宇'], ['期限', '2026-10-23'], ['需求說明', '準備 2 台筆電'], ['完成條件', '可開機登入']])
    await form.getByLabel(label, { exact: true }).fill(value);
  await form.getByRole('button', { name: '產生文件' }).click();
  await expect(panel.getByRole('status')).toContainText(/工單-WO-\d{3}\.docx，版本 v1/);
  await panel.getByRole('button', { name: '修改內容重新產生' }).click();
  const again = page.getByRole('region', { name: '修改內容重新產生' });
  await again.getByLabel('期限', { exact: true }).fill('2026-10-30');
  await again.getByRole('button', { name: '重新產生新版本' }).click();
  await expect(panel.getByRole('status')).toContainText('版本 v2');
  expect(await download(page, /下載 v2/)).toContain('2026-10-30');
  await panel.getByLabel('版本紀錄').selectOption('1');
  expect(await download(page, /下載 v1/)).toContain('2026-10-23');

  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: info.outputPath(`doc-templates-${width}.png`), fullPage: true });
  expect(errors).toEqual([]);
});

test('readonly user cannot create from templates', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  await login(page, 'lin');
  await documents(page, 1280);
  await expect(page.getByText('目前僅可檢視與下載文件。')).toBeVisible();
  await expect(page.getByRole('button', { name: '用樣板建立' })).toHaveCount(0);
});
