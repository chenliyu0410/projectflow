import { expect, test, type Page, type APIRequestContext } from '@playwright/test';
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
  await expect(page.getByLabel('可見任務完成率', { exact: true })).toBeVisible();
}

for (const width of [1280, 375]) {
  test(`P2a admin four levels and member workspace at ${width}px`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: 900 });
    const errors: string[] = [];
    const httpErrors: { path: string; status: number }[] = [];
    const consoleErrors: { path: string; text: string }[] = [];
    page.on('response', response => { if (response.status() >= 400) httpErrors.push({ path: new URL(response.url()).pathname, status: response.status() }); });
    page.on('console', message => { if (message.type() === 'error') consoleErrors.push({ path: message.location().url ? new URL(message.location().url).pathname : '', text: message.text() }); });
    const navigate = async (name: string) => { if (width === 375) await page.getByRole('button', { name: '切換導覽' }).click(); await page.getByRole('button', { name, exact: true }).click(); };
    page.on('pageerror', error => errors.push(String(error)));
    await login(page, 'yu');
    const title = `P2a ${width} ${randomUUID()}`;
    if (!await page.getByRole('button', { name: '建立新專案' }).isVisible()) await page.getByRole('button', { name: '切換導覽' }).click();
    await page.getByRole('button', { name: '建立新專案' }).click();
    await page.getByRole('button', { name: '空白專案', exact: true }).click();
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
    const departmentId = (await options.json()).departments[0].id;
    for (const [name, kind] of [['階段甲', 'phase'], ['父任務', 'task'], ['子任務', 'task']]) {
      await page.getByRole('button', { name: '新增子節點', exact: true }).click();
      await page.getByLabel('節點名稱').fill(name);
      await page.getByLabel('種類', { exact: true }).selectOption(kind);
      await page.getByLabel('負責人', { exact: true }).selectOption(memberId);
      await page.getByLabel('部門', { exact: true }).selectOption(departmentId);
      await page.getByLabel('開始日期').fill('2026-10-08');
      await page.getByLabel('截止日期').fill('2026-10-12');
      await page.getByRole('button', { name: '儲存', exact: true }).click();
      await expect(page.getByLabel('節點名稱')).toHaveCount(0);
      await expect(page.getByLabel('節點詳情')).toContainText(name);
    }
    await page.getByRole('button', { name: '編輯節點', exact: true }).click();
    await page.getByLabel('節點名稱').fill('子任務更新');
    await page.getByLabel('開始日期').fill('');
    await page.getByRole('button', { name: '儲存', exact: true }).click();
    await expect(page.getByLabel('節點名稱')).toHaveCount(0);
    await expect(page.getByLabel('節點詳情')).toContainText('子任務更新');
    const persisted = await page.request.get(`/api/projects/${projectId}`);
    const child = (await persisted.json()).nodes.find((n: { title: string }) => n.title === '子任務更新');
    expect(child.owner_user_id).toBe(memberId);
    expect(child.department_id).toBe(departmentId);
    expect(child.start_date).toBeNull();
    expect(child.due_date).toBe('2026-10-12');
    if (!await page.getByRole('button', {name:'登出',exact:true}).isVisible()) await page.getByRole('button', {name:'切換導覽'}).click();await page.getByRole('button', { name: '登出', exact: true }).click();await expect(page.getByRole('button',{name:'登入',exact:true})).toBeVisible();
    await login(page, 'ming');
    await navigate('我的任務');
    await page.getByLabel('搜尋任務').fill(title);
    await page.getByRole('button', { name: '子任務更新', exact: true }).click();
    await expect(page.getByLabel('節點詳情')).toContainText('2026-10-12');
    await expect(page.getByRole('button', { name: '新增子節點', exact: true })).toHaveCount(0);
    await page.getByRole('button', { name: '編輯節點', exact: true }).click();
    await expect(page.getByLabel('負責人', { exact: true })).toHaveCount(0);
    await page.getByLabel('節點名稱').fill('成員更新子任務');
    await page.getByLabel('截止日期').fill('2026-10-15');
    await page.getByRole('button', { name: '儲存', exact: true }).click();
    await expect(page.getByLabel('節點名稱')).toHaveCount(0);
    await expect(page.getByLabel('節點詳情')).toContainText('成員更新子任務');
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: info.outputPath(`workspace-${width}.png`), fullPage: true });
    if (!await page.getByRole('button', {name:'登出',exact:true}).isVisible()) await page.getByRole('button', {name:'切換導覽'}).click();await page.getByRole('button', { name: '登出', exact: true }).click();await expect(page.getByRole('button',{name:'登入',exact:true})).toBeVisible();
    await login(page, 'lin');
    if (!await page.getByLabel('專案清單').isVisible()) await page.getByRole('button', {name:'切換導覽'}).click();await page.getByLabel('專案清單').getByRole('button', { name: title, exact: true }).click();
    await expect(page.getByRole('button', { name: '編輯節點', exact: true })).toHaveCount(0);
    expect((await page.request.patch(`/api/nodes/${child.id}`, { data: { title: '拒絕' } })).status()).toBe(403);
    const after = await page.request.get(`/api/projects/${projectId}`);
    expect((await after.json()).nodes.find((n: { id: string }) => n.id === child.id)).toMatchObject({ title: '成員更新子任務', start_date: null, due_date: '2026-10-15', owner_user_id: memberId, department_id: departmentId });
    expect(errors).toEqual([]);
    expect(httpErrors).toEqual(Array.from({ length: 3 }, () => ({ path: '/api/auth/me', status: 401 })));
    expect(consoleErrors).toHaveLength(3);
    for (const error of consoleErrors) { expect(error.path).toBe('/api/auth/me'); expect(error.text).toMatch(/^Failed to load resource:.*status of 401/); }
    console.log(`P2a browser ${width}: pageerror=0 unexpectedHTTP=0 unexpectedConsole=0 expectedMe401=3 noOverflow=true`);
    await info.attach('browser-error-summary', { body: JSON.stringify({ errors, httpErrors, consoleErrors }), contentType: 'application/json' });
  });
}

test('P2a nested gate, visible statistics and cross-company metadata boundaries', async ({ playwright, baseURL }) => {
  const contexts: APIRequestContext[] = [];
  const role = async (username: string, organization = 'food') => {
    const context = await playwright.request.newContext({ baseURL }); contexts.push(context);
    expect(new URL(baseURL!).port).not.toBe('15173');
    const marker = await context.get('/api/health/acceptance');
    expect(marker.status()).toBe(200); expect(await marker.json()).toEqual({ acceptance: true });
    const response = await context.post('/api/auth/login', { data: { organization_key: organization, username, password: `demo-${username}` } });
    expect(response.status()).toBe(200); return { request: context, user: (await response.json()).user };
  };
  try {
    const admin = await role('yu'); const member = await role('ming'); const reader = await role('lin'); const owner = await role('owner'); const other = await role('elaine', 'electronics');
    const workflows = await admin.request.get('/api/workflows');
    const created = await admin.request.post('/api/projects/from-workflow', { data: { workflow_id: (await workflows.json()).items.find((workflow: { name: string }) => workflow.name === '食品新品開發').id, title: `P2a nested ${randomUUID()}` } });
    expect(created.status()).toBe(201); const projectId = (await created.json()).id;
    const detail = await (await admin.request.get(`/api/projects/${projectId}`)).json();
    const parent = detail.nodes.find((node: { title: string }) => node.title === '試作工單');
    const add = async (title: string, parentId: string, ownerId: string) => {
      const response = await admin.request.post(`/api/projects/${projectId}/nodes`, { data: { title, kind: 'task', parent_id: parentId, owner_user_id: ownerId, start_date: '2026-10-08', due_date: '2026-10-12' } });
      // TP-B: the create response also carries the undo token, which the project detail does not list.
      expect(response.status()).toBe(201); const { undo_id: undoId, ...node } = await response.json(); expect(undoId).toBeTruthy(); return node;
    };
    const visible = await add('可見深層任務', parent.id, member.user.id);
    const hidden = await add(`hidden-${randomUUID()}`, parent.id, admin.user.id);
    const auditBefore = await (await admin.request.get('/api/audit-logs')).json();
    for (const state of ['doing', 'review', 'done', 'skipped']) expect((await member.request.patch(`/api/nodes/${visible.id}/status`, { data: { status: state } })).status()).toBe(409);
    for (const actor of [reader, owner]) expect((await actor.request.patch(`/api/nodes/${visible.id}`, { data: { title: '拒絕' } })).status()).toBe(403);
    expect((await member.request.patch(`/api/nodes/${visible.id}`, { data: { owner_user_id: admin.user.id } })).status()).toBe(403);
    for (const actor of [member, reader, owner]) expect((await actor.request.get(`/api/projects/${projectId}/assignment-options`)).status()).toBe(403);
    expect((await other.request.patch(`/api/nodes/${visible.id}`, { data: { title: '跨公司' } })).status()).toBe(404);
    expect((await other.request.get(`/api/projects/${projectId}/assignment-options`)).status()).toBe(404);
    expect(await (await admin.request.get('/api/audit-logs')).json()).toEqual(auditBefore);
    expect(await (await admin.request.get(`/api/projects/${projectId}`)).json()).toEqual({ ...detail, nodes: [...detail.nodes, visible, hidden] });
    const restricted = await (await member.request.get(`/api/projects/${projectId}`)).json();
    expect(restricted.nodes.map((node: { id: string }) => node.id)).toEqual([visible.id]); expect(restricted.gates).toEqual([]);
    expect((await member.request.get(`/api/workspace/my-tasks?q=${encodeURIComponent(hidden.title)}`)).status()).toBe(200);
    expect((await (await member.request.get(`/api/workspace/my-tasks?q=${encodeURIComponent(hidden.title)}`)).json()).items).toEqual([]);
    expect((await admin.request.patch(`/api/gates/${detail.gates[0].id}`, { data: { status: 'approved' } })).status()).toBe(200);
    const report = await member.request.post(`/api/nodes/${visible.id}/reports`, { data: { result: '達成', summary: '深層工作完成', finished_on: '2026-10-08' } });
    expect(report.status()).toBe(201);
    expect((await admin.request.post(`/api/reports/${(await report.json()).id}/review`, { data: { decision: 'approved' } })).status()).toBe(200);
    expect((await admin.request.post(`/api/nodes/${hidden.id}/lifecycle`, { data: { action: 'skip', reason: '驗收略過' } })).status()).toBe(200);
    const summary = (await (await member.request.get('/api/workspace/overview')).json()).projects.find((project: { id: string }) => project.id === projectId);
    expect(summary.task_counts).toEqual({ todo: 0, doing: 0, review: 0, done: 1, skipped: 0 }); expect(summary.completion_percent).toBe(100);
    const foreign = await (await other.request.get('/api/workspace/overview')).json();
    expect(foreign.projects.some((project: { id: string }) => project.id === projectId)).toBe(false);
    // The project_owner role manages only projects it actually owns.
    const ownProject = await owner.request.post('/api/projects/from-workflow', { data: { workflow_id: (await workflows.json()).items.find((workflow: { name: string }) => workflow.name === '食品新品開發').id, title: `P2a owner ${randomUUID()}` } });
    expect(ownProject.status()).toBe(201); const ownedId = (await ownProject.json()).id;
    const ownTask = await owner.request.post(`/api/projects/${ownedId}/nodes`, { data: { title: '負責人建立', kind: 'task' } }); expect(ownTask.status()).toBe(201);
    expect((await owner.request.patch(`/api/nodes/${(await ownTask.json()).id}`, { data: { owner_user_id: member.user.id } })).status()).toBe(200);
  } finally { for (const context of contexts) await context.dispose(); }
});
