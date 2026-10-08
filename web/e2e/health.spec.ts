import { expect, test } from '@playwright/test';
import { randomUUID } from 'node:crypto';

test('proxy verifies actual database readiness', async ({ request }) => {
  const live = await request.get('/api/health');
  expect(live.status()).toBe(200);
  expect(await live.json()).toEqual({ ok: true });
  const ready = await request.get('/api/health/ready');
  expect(ready.status()).toBe(200);
  expect(await ready.json()).toEqual({ ok: true, database: 'ready' });
});

for (const width of [1280, 375]) {
  test(`login workflow creation gate and readonly at ${width}px`, async ({ page }, testInfo) => {
    const pageErrors: string[] = [];
    const consoleErrors: { text: string; path: string }[] = [];
    const httpErrors: { status: number; path: string }[] = [];
    const expected = new Map<string, number>([['/api/auth/me', 401]]);
    page.on('pageerror', error => pageErrors.push(String(error)));
    page.on('response', response => {
      if (response.status() >= 400) httpErrors.push({ status: response.status(), path: new URL(response.url()).pathname });
    });
    page.on('console', message => {
      if (message.type() === 'error') {
        const url = message.location().url;
        consoleErrors.push({ text: message.text(), path: url ? new URL(url).pathname : '' });
      }
    });
    const noOverflow = async () => expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    const screenshot = async (stage: string) => {
      await noOverflow();
      await page.screenshot({ path: testInfo.outputPath(`p1b-${width}-${stage}.png`), fullPage: true });
    };
    const login = async (username: string) => {
      await page.getByLabel('帳號').fill(username);
      await page.getByLabel('密碼').fill(`demo-${username}`);
      await page.getByRole('button', { name: '登入', exact: true }).click();
      await expect(page.getByLabel('專案清單')).toBeVisible();
      await expect(page.getByRole('status')).toHaveCount(0);
    };
    await page.setViewportSize({ width, height: 900 });
    await page.goto('/');
    await expect(page.getByRole('heading', { name: '登入專流' })).toBeVisible();
    await screenshot('login');
    await login('yu');
    await page.getByLabel('專案清單').getByRole('button', { name: '成貓主食罐正式版', exact: true }).click();
    await expect(page.getByRole('heading', { name: '成貓主食罐正式版', exact: true })).toBeVisible();
    await expect(page.getByLabel('節點樹')).toContainText('殺菌條件驗證');
    const projectList = await page.request.get('/api/projects');
    expect(projectList.status()).toBe(200);
    const seedProject = (await projectList.json()).items.find((item: { title: string }) => item.title === '成貓主食罐正式版');
    const seedBefore = await page.request.get(`/api/projects/${seedProject.id}`);
    expect(seedBefore.status()).toBe(200);
    const seedNodes = (await seedBefore.json()).nodes;
    const title = `P1b E2E ${width} ${randomUUID()}`;
    await page.getByRole('button', { name: '新增專案' }).click();
    await page.getByLabel('工作流模板').selectOption({ label: '食品新品開發' });
    await page.getByLabel('新專案名稱').fill(title);
    await screenshot('create');
    const createdResponse = page.waitForResponse(response => new URL(response.url()).pathname === '/api/projects/from-workflow' && response.request().method() === 'POST');
    await page.getByRole('button', { name: '建立專案' }).click();
    const created = await createdResponse;
    expect(created.status()).toBe(201);
    const project = await created.json();
    await expect(page.getByRole('heading', { name: title, exact: true })).toBeVisible();
    const detailResponse = await page.request.get(`/api/projects/${project.id}`);
    expect(detailResponse.status()).toBe(200);
    const detail = await detailResponse.json();
    const task = detail.nodes.find((node: { title: string }) => node.title === '試作工單');
    expect(task).toBeTruthy();
    const statusPath = `/api/nodes/${task.id}/status`;
    expected.set(statusPath, 409);
    const blockedResponse = page.waitForResponse(response => new URL(response.url()).pathname === statusPath);
    await page.getByLabel('待處理').getByRole('combobox', { name: '試作工單狀態' }).selectOption('doing');
    expect((await blockedResponse).status()).toBe(409);
    await expect(page.getByRole('alert')).toHaveText('前一階段閘門尚未通過');
    await expect(page.getByLabel('待處理').getByRole('combobox', { name: '試作工單狀態' })).toHaveValue('todo');
    await screenshot('gate-blocked');
    await page.getByRole('button', { name: '核准閘門' }).click();
    await expect(page.getByText('尚有階段閘門待核准，後續階段可能被阻擋')).toHaveCount(0);
    await page.getByLabel('待處理').getByRole('combobox', { name: '試作工單狀態' }).selectOption('doing');
    await expect(page.getByLabel('進行中').getByRole('combobox', { name: '試作工單狀態' })).toHaveValue('doing');
    await screenshot('gate-approved');
    await page.getByRole('button', { name: '登出' }).click();
    await expect(page.getByRole('heading', { name: '登入專流' })).toBeVisible();
    await login('lin');
    await page.getByLabel('專案清單').getByRole('button', { name: title, exact: true }).click();
    await expect(page.getByRole('heading', { name: title, exact: true })).toBeVisible();
    await expect(page.getByLabel('進行中')).toContainText('試作工單');
    await expect(page.getByLabel('看板').getByRole('combobox')).toHaveCount(0);
    await expect(page.getByRole('button', { name: '新增專案' })).toHaveCount(0);
    await expect(page.getByRole('button', { name: '核准閘門' })).toHaveCount(0);
    await screenshot('readonly');
    expect(await page.locator('header img').evaluate((img: HTMLImageElement) => img.complete && img.naturalWidth > 0)).toBe(true);
    expect(pageErrors).toEqual([]);
    expect(httpErrors).toContainEqual({ path: '/api/auth/me', status: 401 });
    expect(httpErrors).toContainEqual({ path: statusPath, status: 409 });
    expect(httpErrors.filter(error => expected.get(error.path) !== error.status)).toEqual([]);
    expect(consoleErrors.filter(error => {
      const status = expected.get(error.path);
      return !status || !error.text.startsWith('Failed to load resource:') || !error.text.includes(`status of ${status}`);
    })).toEqual([]);
    const seedAfter = await page.request.get(`/api/projects/${seedProject.id}`);
    expect(seedAfter.status()).toBe(200);
    expect((await seedAfter.json()).nodes).toEqual(seedNodes);
    console.log(`Browser ${width}: pageerror=0 unexpectedHTTP=0 unexpectedConsole=0 expectedHTTP=${httpErrors.length} expectedConsole=${consoleErrors.length}`);
    await testInfo.attach('browser-error-summary', { body: JSON.stringify({ pageErrors, expectedHttp: httpErrors, expectedConsole: consoleErrors }), contentType: 'application/json' });
  });
}

test('unknown API path is not served as frontend HTML', async ({ request }) => {
  const response = await request.get('/api/missing');
  expect(response.status()).toBe(404);
  expect(response.headers()['content-type']).toContain('application/json');
});
