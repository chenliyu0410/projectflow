import { openProjects } from './navigation';
import { expect, test, type Page } from '@playwright/test';
import { randomUUID } from 'node:crypto';

for (const width of [1280, 375]) {
  test(`P2b submit reject resubmit approve journey at ${width}px`, async ({ page, request, baseURL }, info) => {
    test.setTimeout(90000);
    const errors: string[] = [];
    const httpErrors: {path:string;status:number}[] = [];
    const consoleErrors: {path:string;text:string}[] = [];
    page.on('pageerror', error => errors.push(String(error)));
    page.on('response', r => { if(r.status()>=400) httpErrors.push({path:new URL(r.url()).pathname,status:r.status()}); });
    page.on('console', m => { if(m.type()==='error') consoleErrors.push({path:m.location().url ? new URL(m.location().url).pathname : '',text:m.text()}); });
    expect(new URL(baseURL!).port).not.toBe('15173');
    const marker = await request.get('/api/health/acceptance');
    expect(marker.status()).toBe(200);
    expect(await marker.json()).toEqual({ acceptance: true });
    await page.setViewportSize({ width, height: 900 });
    const member = await request.post('/api/auth/login', { data: { organization_key: 'food', username: 'ming', password: 'demo-ming' } });
    expect(member.status()).toBe(200);
    const memberId = (await member.json()).user.id;
    expect((await request.post('/api/auth/login', { data: { organization_key: 'food', username: 'yu', password: 'demo-yu' } })).status()).toBe(200);
    const title = `P2b journey ${randomUUID()}`;
    const project = await request.post('/api/projects', { data: { title } });
    expect(project.status()).toBe(201);
    const pid = (await project.json()).id;
    const created = await request.post(`/api/projects/${pid}/nodes`, { data: { title: '送審成果任務', kind: 'task', owner_user_id: memberId } });
    expect(created.status()).toBe(201);
    const nid = (await created.json()).id;
    const login = async (username: string) => {
      await page.goto('/');
      await page.getByLabel('帳號').fill(username);
      await page.getByLabel('密碼').fill(`demo-${username}`);
      await page.getByRole('button', { name: '登入', exact: true }).click();
      await expect(page.getByLabel('可見任務完成率', { exact: true })).toBeVisible();
    };
    const navigate = async (label: string) => {
      if (width === 375) await page.getByRole('button', { name: '切換導覽' }).click();
      await page.getByRole('button', { name: label, exact: true }).click();
    };
    const openTask = async () => {
      await (await openProjects(page)).getByRole('button', { name: title, exact: true }).click();
      await page.getByLabel('看板').getByRole('button', { name: '送審成果任務', exact: true }).click();
    };
    const submit = async (summary: string) => {
      await page.getByLabel('完成回報', { exact: true }).getByRole('button', { name: /^(回報完成|重新回報)$/ }).click();
      await page.getByRole('textbox', { name: '成果說明', exact: true }).fill(summary);
      await page.getByLabel('結果', { exact: true }).selectOption('達成');
      await page.getByLabel('實際完成日', { exact: true }).fill('2026-10-08');
      await page.getByRole('button', { name: '送出回報', exact: true }).click();
      await expect(page.getByLabel('節點詳情')).toContainText('待確認');
    };
    await login('ming'); await openTask();
    await submit('第一版成果');
    if (!await page.getByRole('button', {name:'登出',exact:true}).isVisible()) await page.getByRole('button', {name:'切換導覽'}).click();await page.getByRole('button', { name: '登出', exact: true }).click();
    await expect(page.getByRole('heading', { name: '登入專流', exact: true })).toBeVisible();
    await login('yu'); await openTask();
    await page.getByLabel('審核意見', { exact: true }).fill('請補充驗證資料');
    await page.getByRole('button', { name: '退回回報', exact: true }).click();
    await expect(page.getByLabel('節點詳情')).toContainText('進行中');
    if (!await page.getByRole('button', {name:'登出',exact:true}).isVisible()) await page.getByRole('button', {name:'切換導覽'}).click();await page.getByRole('button', { name: '登出', exact: true }).click();
    await expect(page.getByRole('heading', { name: '登入專流', exact: true })).toBeVisible();
    await login('ming'); await openTask();
    await expect(page.getByLabel('完成回報', { exact: true })).toContainText('請補充驗證資料');
    await submit('第二版補齊驗證資料');
    if (!await page.getByRole('button', {name:'登出',exact:true}).isVisible()) await page.getByRole('button', {name:'切換導覽'}).click();await page.getByRole('button', { name: '登出', exact: true }).click();
    await expect(page.getByRole('heading', { name: '登入專流', exact: true })).toBeVisible();
    await login('yu'); await openTask();
    await page.getByRole('button', { name: '確認回報', exact: true }).click();
    await expect(page.getByLabel('完成回報', { exact: true }).getByRole('heading', { name: '已完成', exact: true })).toBeVisible();
    const detail = await request.get(`/api/projects/${pid}`);
    expect((await detail.json()).nodes.find((node: { id: string }) => node.id === nid).status).toBe('done');
    const records = await request.get(`/api/nodes/${nid}/records`);
    expect(records.status()).toBe(200);
    const reports = (await records.json()).items.filter((item: { type: string }) => item.type === 'report');
    expect(reports).toEqual(expect.arrayContaining([
      expect.objectContaining({ version: 1, status: 'rejected', summary: '第一版成果' }),
      expect.objectContaining({ version: 2, status: 'approved', summary: '第二版補齊驗證資料' }),
    ]));
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    expect(errors).toEqual([]);
    expect(httpErrors).toEqual(Array.from({length:4},()=>({path:'/api/auth/me',status:401})));
    expect(consoleErrors).toHaveLength(4);
    for(const error of consoleErrors){expect(error.path).toBe('/api/auth/me');expect(error.text).toMatch(/^Failed to load resource:.*status of 401/);}
    await page.screenshot({path:info.outputPath(`collaboration-${width}.png`),fullPage:true});
    await page.getByLabel('節點詳情').screenshot({path:info.outputPath(`collaboration-detail-${width}.png`)});
    console.log(`P2b collaboration ${width}: pageerror=0 unexpectedHTTP=0 unexpectedConsole=0 expectedMe401=4 noOverflow=true`);
  });
}
