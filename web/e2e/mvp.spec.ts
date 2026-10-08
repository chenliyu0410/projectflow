import { expect, test, type BrowserContext, type Page } from '@playwright/test';
import { randomUUID } from 'node:crypto';

test.beforeEach(async ({ request, baseURL }) => {
  expect(new URL(baseURL!).port).not.toBe('15173');
  const marker = await request.get('/api/health/acceptance');
  expect(marker.status(), 'Acceptance requires the isolated test stack').toBe(200);
  expect(await marker.json()).toEqual({ acceptance: true });
});

for (const width of [1280, 375]) {
  test(`real role boundaries and restored seed at ${width}px`, async ({ browser, baseURL }, testInfo) => {
    const contexts: BrowserContext[] = [];
    const checks: (() => Promise<void>)[] = [];
    const role = async (username: string, organization = 'food') => {
      const context = await browser.newContext({ baseURL, viewport: { width, height: 900 } });
      contexts.push(context);
      const page = await context.newPage();
      const pageErrors: string[] = [];
      const httpErrors: { path: string; status: number }[] = [];
      const consoleErrors: { path: string; text: string }[] = [];
      page.on('pageerror', error => pageErrors.push(String(error)));
      page.on('response', response => {
        if (response.status() >= 400) httpErrors.push({ path: new URL(response.url()).pathname, status: response.status() });
      });
      page.on('console', message => {
        if (message.type() === 'error') consoleErrors.push({ path: message.location().url ? new URL(message.location().url).pathname : '', text: message.text() });
      });
      checks.push(async () => {
        expect(pageErrors).toEqual([]);
        expect(httpErrors).toEqual([{ path: '/api/auth/me', status: 401 }]);
        expect(consoleErrors).toHaveLength(1);
        expect(consoleErrors[0].path).toBe('/api/auth/me');
        expect(consoleErrors[0].text).toMatch(/^Failed to load resource:.*status of 401/);
      });
      await page.goto('/');
      await page.getByLabel('公司', { exact: true }).fill(organization);
      await page.getByLabel('帳號').fill(username);
      await page.getByLabel('密碼').fill(`demo-${username}`);
      await page.getByRole('button', { name: '登入', exact: true }).click();
      if (width === 375) await page.getByRole('button', { name: '切換導覽' }).click();
      await page.getByRole('button', { name: '專案工作區', exact: true }).click();
      await expect(page.getByLabel('專案清單')).toBeVisible();
      return page;
    };
    const snapshot = async (page: Page, name: string) => {
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      await page.screenshot({ path: testInfo.outputPath(`p1c-${width}-${name}.png`), fullPage: true });
    };
    const openSeed = async (page: Page) => {
      await page.getByLabel('專案清單').getByRole('button', { name: '成貓主食罐正式版', exact: true }).click();
      await expect(page.getByRole('heading', { name: '成貓主食罐正式版', exact: true })).toBeVisible();
    };
    let yu: Page | undefined;
    let seedId: string | undefined;
    let seedNodes: { id: string; status: string; kind: string; title: string; owner_user_id: string; parent_id: string | null }[] = [];
    try {
      yu = await role('yu');
      const projects = await yu.request.get('/api/projects');
      expect(projects.status()).toBe(200);
      seedId = (await projects.json()).items.find((p: { title: string }) => p.title === '成貓主食罐正式版').id;
      const before = await yu.request.get(`/api/projects/${seedId}`);
      expect(before.status()).toBe(200);
      seedNodes = (await before.json()).nodes;
      const own = seedNodes.find(n => n.kind === 'task')!;
      const hidden = seedNodes.find(n => n.kind === 'phase')!;
      const chen = await role('chen');
      await openSeed(chen);
      const ownParent = seedNodes.find(n => n.id === own.parent_id)!;
      await chen.getByLabel('節點樹').getByRole('button', { name: ownParent.title, exact: true }).click();
      await chen.getByRole('combobox', { name: `${own.title}狀態` }).selectOption('doing');
      await expect(chen.getByLabel('進行中').getByRole('combobox', { name: `${own.title}狀態` })).toHaveValue('doing');
      await snapshot(chen, 'chen');
      const ming = await role('ming');
      const me = await ming.request.get('/api/auth/me');
      expect(me.status()).toBe(200);
      const memberId = (await me.json()).user.id;
      const restricted = await ming.request.get(`/api/projects/${seedId}`);
      expect(restricted.status()).toBe(200);
      expect((await restricted.json()).nodes.map((n: { id: string }) => n.id).sort())
        .toEqual(seedNodes.filter(n => n.owner_user_id === memberId).map(n => n.id).sort());
      await openSeed(ming);
      await ming.getByLabel('節點樹').getByRole('button', { name: own.title }).click();
      await expect(ming.getByLabel('節點路徑')).toHaveText(`成貓主食罐正式版 / ${own.title}`);
      await expect(ming.getByLabel('節點樹')).not.toContainText(hidden.title);
      await ming.getByRole('combobox', { name: `${own.title}狀態` }).selectOption('todo');
      await expect(ming.getByLabel('節點詳情').getByRole('combobox', { name: `${own.title}狀態` })).toHaveValue('todo');
      const reportProject = await yu.request.post('/api/projects', { data: { title: `P2b role report ${randomUUID()}` } });
      expect(reportProject.status()).toBe(201);
      const reportTask = await yu.request.post(`/api/projects/${(await reportProject.json()).id}/nodes`, { data: { title: '角色回報任務', kind: 'task', owner_user_id: memberId } });
      expect(reportTask.status()).toBe(201);
      const reportNodeId = (await reportTask.json()).id;
      const report = await ming.request.post(`/api/nodes/${reportNodeId}/reports`, { data: { result: '達成', summary: `P2b ${randomUUID()}`, finished_on: '2026-10-08' } });
      expect(report.status()).toBe(201);
      const reportId = (await report.json()).id;
      const audit = await ming.request.get(`/api/audit-logs?node_id=${reportNodeId}&action=report.submit`);
      expect(audit.status()).toBe(200);
      expect((await audit.json()).items.some((log: { action: string; node_id: string; organization_key: string; actor_display_name: string; payload: { report_id?: string } }) =>
        log.action === 'report.submit' && log.node_id === reportNodeId && log.organization_key === 'food' && log.actor_display_name === '明成員' && log.payload.report_id === reportId)).toBe(true);
      expect((await ming.request.patch(`/api/nodes/${hidden.id}/status`, { data: { status: 'doing' } })).status()).toBe(403);
      expect((await ming.request.post(`/api/nodes/${hidden.id}/reports`, { data: { result: '達成', summary: '越權', finished_on: '2026-10-08' } })).status()).toBe(404);
      await snapshot(ming, 'ming');

      const title = `P1c E2E ${width} ${randomUUID()}`;
      await yu.getByRole('button', { name: '新增專案' }).click();
      await yu.getByLabel('工作流模板').selectOption({ label: '食品新品開發' });
      await yu.getByLabel('新專案名稱').fill(title);
      const createdPromise = yu.waitForResponse(r => new URL(r.url()).pathname === '/api/projects/from-workflow' && r.request().method() === 'POST');
      await yu.getByRole('button', { name: '建立專案' }).click();
      const created = await createdPromise;
      expect(created.status()).toBe(201);
      const projectId = (await created.json()).id;
      await expect(yu.getByRole('heading', { name: title, exact: true })).toBeVisible();
      const detailResponse = await yu.request.get(`/api/projects/${projectId}`);
      expect(detailResponse.status()).toBe(200);
      const detail = await detailResponse.json();
      const task = detail.nodes.find((n: { title: string }) => n.title === '試作工單');
      const gate = detail.gates[0];
      expect((await yu.request.patch(`/api/nodes/${task.id}/status`, { data: { status: 'doing' } })).status()).toBe(409);
      expect((await chen.request.patch(`/api/gates/${gate.id}`, { data: { status: 'approved' } })).status()).toBe(403);
      expect((await ming.request.patch(`/api/nodes/${task.id}/status`, { data: { status: 'doing' } })).status()).toBe(403);
      const hiddenProject = await ming.request.get(`/api/projects/${projectId}`);
      expect(hiddenProject.status()).toBe(200);
      expect((await hiddenProject.json()).gates).toEqual([]);
      await yu.getByRole('button', { name: '核准閘門' }).click();
      await expect(yu.getByRole('button', { name: '核准閘門' })).toHaveCount(0);
      await yu.getByLabel('節點樹').getByRole('button', { name: detail.nodes.find((n: { id: string }) => n.id === task.parent_id).title, exact: true }).click();
      await yu.getByRole('combobox', { name: '試作工單狀態' }).selectOption('doing');
      await expect(yu.getByLabel('進行中').getByRole('combobox', { name: '試作工單狀態' })).toHaveValue('doing');
      await snapshot(yu, 'yu');
      const readonly = await role('lin');
      await readonly.getByLabel('專案清單').getByRole('button', { name: title, exact: true }).click();
      await expect(readonly.getByRole('heading', { name: title, exact: true })).toBeVisible();
      await expect(readonly.getByLabel('看板').getByRole('combobox')).toHaveCount(0);
      await expect(readonly.getByRole('button', { name: '新增專案' })).toHaveCount(0);
      await expect(readonly.getByRole('button', { name: '核准閘門' })).toHaveCount(0);
      expect((await readonly.request.post('/api/projects', { data: { title: '唯讀' } })).status()).toBe(403);
      expect((await readonly.request.patch(`/api/nodes/${task.id}/status`, { data: { status: 'done' } })).status()).toBe(403);
      expect((await readonly.request.post(`/api/nodes/${task.id}/reports`, { data: { result: '達成', summary: '唯讀', finished_on: '2026-10-08' } })).status()).toBe(403);
      expect((await readonly.request.patch(`/api/gates/${gate.id}`, { data: { status: 'approved' } })).status()).toBe(403);
      await snapshot(readonly, 'readonly');

      const electronics = await role('elaine', 'electronics');
      const otherProjects = await electronics.request.get('/api/projects');
      expect(otherProjects.status()).toBe(200);
      const otherId = (await otherProjects.json()).items.find((p: { title: string }) => p.title === '連接器新產品正式版').id;
      const otherDetail = await electronics.request.get(`/api/projects/${otherId}`);
      expect(otherDetail.status()).toBe(200);
      const otherNode = (await otherDetail.json()).nodes[0];
      const workflows = await electronics.request.get('/api/workflows');
      expect(workflows.status()).toBe(200);
      const otherCreated = await electronics.request.post('/api/projects/from-workflow', { data: { workflow_id: (await workflows.json()).items[0].id, title: `跨公司 ${randomUUID()}` } });
      expect(otherCreated.status()).toBe(201);
      const otherWorkflow = await electronics.request.get(`/api/projects/${(await otherCreated.json()).id}`);
      expect(otherWorkflow.status()).toBe(200);
      const otherGate = (await otherWorkflow.json()).gates[0];
      const otherTask = await electronics.request.post(`/api/projects/${otherId}/nodes`, { data: { title: `電子回報 ${randomUUID()}`, kind: 'task' } });
      expect(otherTask.status()).toBe(201);
      const otherReport = await electronics.request.post(`/api/nodes/${(await otherTask.json()).id}/reports`, { data: { result: '達成', summary: '電子公司', finished_on: '2026-10-08' } });
      expect(otherReport.status()).toBe(201);
      const otherReportId = (await otherReport.json()).id;
      for (const page of [yu, chen, ming, readonly]) {
        expect((await page.request.get(`/api/projects/${otherId}?organization_key=electronics`)).status()).toBe(404);
        expect((await page.request.patch(`/api/nodes/${otherNode.id}/status`, { data: { status: 'doing' } })).status()).toBe(404);
        expect((await page.request.post(`/api/nodes/${otherNode.id}/reports`, { data: { result: '達成', summary: '跨公司', finished_on: '2026-10-08' } })).status()).toBe(404);
        expect((await page.request.patch(`/api/gates/${otherGate.id}`, { data: { status: 'approved' } })).status()).toBe(404);
        const scoped = await page.request.get('/api/audit-logs?organization_key=electronics');
        expect(scoped.status()).toBe(200);
        expect((await scoped.json()).items.every((log: { organization_key: string; payload: { report_id?: string } }) => log.organization_key === 'food' && log.payload.report_id !== otherReportId)).toBe(true);
      }
      await snapshot(electronics, 'electronics');
      for (const check of checks) await check();
    } finally {
      try {
        if (yu && seedId) {
          for (const node of seedNodes) {
            expect((await yu.request.patch(`/api/nodes/${node.id}/status`, { data: { status: node.status } })).status()).toBe(200);
          }
          const restored = await yu.request.get(`/api/projects/${seedId}`);
          expect(restored.status()).toBe(200);
          expect((await restored.json()).nodes).toEqual(seedNodes);
        }
      } finally {
        for (const context of contexts) await context.close();
      }
    }
  });
}
