import { openProjects } from './navigation';
import {test,expect} from '@playwright/test';
import {randomUUID} from 'node:crypto';
import {mkdir} from 'node:fs/promises';
test('TP-F application, approval, restore, departments and notification desktop/mobile',async({page,browser})=>{
 test.setTimeout(120000);
 expect((await page.request.get('/api/health/acceptance')).status()).toBe(200);
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/');await page.getByLabel('帳號').fill('yu');await page.getByLabel('密碼').fill('demo-yu');await page.getByRole('button',{name:'登入',exact:true}).click();await expect(page.getByLabel('可見任務完成率',{exact:true})).toBeVisible();
 const title='TP-F '+randomUUID();const taskTitle=title+'待處理任務';const made=await page.request.post('/api/projects',{data:{title}});expect(made.status()).toBe(201);const pid=(await made.json()).id;
 const root=(await(await page.request.get(`/api/projects/${pid}`)).json()).nodes[0].id;
 const opts=await(await page.request.get(`/api/projects/${pid}/assignment-options`)).json();const member=opts.users.find((u:{display_name:string})=>u.display_name==='明成員');
 const madeNode=await page.request.post(`/api/projects/${pid}/nodes`,{data:{title:taskTitle,kind:'task',parent_id:root,owner_user_id:member.id}});expect(madeNode.status()).toBe(201);const nid=(await madeNode.json()).id;
 const ctx=await browser.newContext({baseURL:new URL(page.url()).origin});const memberPage=await ctx.newPage();await memberPage.goto('/');await memberPage.getByLabel('帳號').fill('ming');await memberPage.getByLabel('密碼').fill('demo-ming');await memberPage.getByRole('button',{name:'登入',exact:true}).click();await expect(memberPage.getByLabel('可見任務完成率',{exact:true})).toBeVisible();
 await memberPage.getByRole('button',{name:'我的任務',exact:true}).click();await expect(memberPage.getByLabel('站內通知')).toContainText('你被指派為任務負責人');
 await memberPage.getByRole('table',{name:'我負責的'}).getByRole('button',{name:taskTitle,exact:true}).click();
 await memberPage.getByRole('button',{name:'跳過／覆寫申請',exact:true}).click();await memberPage.getByLabel('申請理由').fill('範圍調整');await memberPage.getByRole('button',{name:'送出申請',exact:true}).click();
 await expect.poll(async()=> (await(await memberPage.request.get('/api/workspace/requests')).json()).items.some((r:{node_id:string})=>r.node_id===nid)).toBe(true);
 await page.getByRole('button',{name:'審核中心',exact:true}).click();const card=page.locator('article').filter({has:page.getByRole('heading',{name:taskTitle,exact:true})});await card.getByRole('button',{name:'核准申請'}).click();await expect(card).toHaveCount(0);
 await page.reload();await (await openProjects(page)).getByRole('button',{name:title,exact:true}).click();await page.getByRole('button',{name:taskTitle,exact:true}).click();await page.getByRole('button',{name:'恢復任務',exact:true}).click();await page.getByLabel('操作理由').fill('恢復工作');await page.getByRole('button',{name:'確認恢復',exact:true}).click();
 await expect.poll(async()=> (await(await page.request.get(`/api/projects/${pid}`)).json()).nodes.find((n:{id:string})=>n.id===nid).status).toBe('todo');
 await page.getByRole('tab',{name:'成員與權限',exact:true}).click();await expect(page.getByRole('heading',{name:'專案成員與權限'})).toBeVisible();
 await page.getByRole('button',{name:'新增部門',exact:true}).click();await page.getByLabel('部門名稱').fill('TP-F '+randomUUID());await page.getByRole('button',{name:'儲存部門',exact:true}).click();await expect(page.getByLabel('部門名稱')).toHaveCount(0);
 await mkdir('../.superpowers/tpf/e2e',{recursive:true});for(const width of [1280,1440,375]){await page.setViewportSize({width,height:900});await page.screenshot({path:`../.superpowers/tpf/e2e/members-${width}.png`,fullPage:true});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);}
 expect(errors).toEqual([]);await ctx.close();
});
