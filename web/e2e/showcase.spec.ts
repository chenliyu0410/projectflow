import { test, expect } from '@playwright/test';
import { randomUUID } from 'node:crypto';
import { mkdir } from 'node:fs/promises';
for(const width of [1280,375]) test(`UI2 real catalog and five-company showcase ${width}`,async({page,request,baseURL,playwright})=>{
 test.setTimeout(90000);expect(new URL(baseURL!).port).toBe('15175');expect(await(await request.get('/api/health/acceptance')).json()).toEqual({acceptance:true});
 const errors:string[]=[];page.on('pageerror',e=>errors.push(String(e)));page.on('console',m=>{if(m.type()==='error'&&!m.text().includes('401'))errors.push(m.text());});
 await mkdir('../.superpowers/ui2',{recursive:true});await page.setViewportSize({width,height:900});await page.goto('/');await page.getByLabel('帳號').fill('yu');await page.getByLabel('密碼').fill('demo-yu');await page.getByRole('button',{name:'登入',exact:true}).click();await expect(page.getByLabel('可見任務完成率',{exact:true})).toBeVisible();
 const menu=async()=>{if(width===375&&!await page.getByLabel('工作區導覽').isVisible())await page.getByRole('button',{name:'切換導覽'}).click();};
 const nav=async(name:string)=>{await menu();await page.getByRole('button',{name,exact:true}).click();};
 const capture=async(name:string)=>{expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.screenshot({path:`../.superpowers/ui2/${name}-${width}.png`});};
 await nav('模板庫');await expect(page.getByRole('status')).toHaveCount(0);await capture('company-templates');await page.getByRole('button',{name:'產業範本'}).click();await expect(page.locator('.catalog-card')).toHaveCount(12);await capture('catalog');
 await page.getByLabel('產業分類').selectOption('software');await expect(page.locator('.catalog-card')).toHaveCount(2);await page.getByRole('button',{name:'預覽版本發佈專流'}).click();await expect(page.getByLabel('範本預覽')).toContainText('後端 SSO 整合');await expect(page.getByLabel('範本預覽')).toBeInViewport();await capture('preview');
 const name=`UI2 真模板 ${width} ${randomUUID()}`;await page.getByLabel('匯入模板名稱').fill(name);await page.getByRole('button',{name:'加入公司模板',exact:true}).click();await expect(page.getByLabel('模板內容')).toContainText(name);
 const workflows=await(await page.request.get('/api/workflows')).json();const wid=workflows.items.find((w:{name:string})=>w.name===name).id;
 await menu();await page.getByRole('button',{name:'建立新專案',exact:true}).click();await page.getByLabel('工作流模板').selectOption(wid);await page.getByLabel('新專案名稱').fill(name);await page.getByLabel('專案開始日').fill('2026-10-09');await page.getByRole('button',{name:'建立專案',exact:true}).click();await expect(page.getByRole('heading',{name,exact:true})).toBeVisible();
 const projects=await(await page.request.get('/api/projects')).json();const pid=projects.items.find((p:{title:string})=>p.title===name).id;const before=await(await page.request.get(`/api/projects/${pid}`)).json();expect(before.nodes.filter((n:{kind:string})=>n.kind==='task')).toHaveLength(10);expect(before.gates.length).toBeGreaterThan(0);
 // An open editor requires explicit confirmation, cancellation preserves the form and company.
 await page.getByRole('button',{name:'新增子節點'}).click();await page.getByLabel('節點名稱').fill('尚未儲存');await menu();await page.getByLabel('切換公司（本機展示）').selectOption('events');await page.getByRole('button',{name:'取消切換'}).click();await expect(page.getByLabel('目前公司')).toHaveText('毛研食品');if(width===375)await page.keyboard.press('Escape');await expect(page.getByLabel('節點名稱')).toHaveValue('尚未儲存');
 await nav('所有專案總覽');const oldToken=(await page.context().cookies()).find(c=>c.name==='pf_session')!.value;
 for(const [key,company]of [['electronics','峰曜科技'],['events','光點企劃'],['software','雲序軟體'],['construction','築衡工程'],['food','毛研食品']]){
   await menu();await page.getByLabel('切換公司（本機展示）').selectOption(key);await expect(page.getByLabel('可見任務完成率',{exact:true})).toBeVisible();
   expect((await(await page.request.get('/api/auth/me')).json()).organization.key).toBe(key);
   await menu();await expect(page.getByLabel('目前公司')).toHaveText(company);await expect(page.getByText('展示身分 · 管理者')).toBeVisible();await capture(`switch-${key}`);if(width===375)await page.keyboard.press('Escape');
   if(key!=='food'){expect((await page.request.get(`/api/projects/${pid}`)).status()).toBe(404);await expect(page.getByRole('button',{name,exact:true})).toHaveCount(0);}
 }
 const stale=await playwright.request.newContext({baseURL,extraHTTPHeaders:{cookie:`pf_session=${oldToken}`}});expect((await stale.get('/api/auth/me')).status()).toBe(401);await stale.dispose();
 expect(await(await page.request.get(`/api/projects/${pid}`)).json()).toEqual(before);
 await page.reload();await expect(page.getByLabel('可見任務完成率',{exact:true})).toBeVisible();expect((await(await page.request.get('/api/auth/me')).json()).showcase.active).toBe(true);
 expect(errors).toEqual([]);
});
