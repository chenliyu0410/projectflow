import { openActions, openProjects } from './navigation';
import {test,expect} from '@playwright/test';
import {randomUUID} from 'node:crypto';
import {mkdir} from 'node:fs/promises';

test('TP-E save, historical version, additive apply, undo and delete on desktop/mobile',async({page})=>{
  const marker=await page.request.get('/api/health/acceptance');expect(marker.status()).toBe(200);expect(await marker.json()).toEqual({acceptance:true});
  const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
  await page.setViewportSize({width:1280,height:900});await page.goto('/');
  await page.getByLabel('帳號').fill('yu');await page.getByLabel('密碼').fill('demo-yu');await page.getByRole('button',{name:'登入',exact:true}).click();
  await expect(page.getByLabel('可見任務完成率',{exact:true})).toBeVisible();
  const title=`TP-E ${randomUUID()}`;const made=await page.request.post('/api/projects',{data:{title}});expect(made.status()).toBe(201);const pid=(await made.json()).id;
  const root=(await(await page.request.get(`/api/projects/${pid}`)).json()).nodes[0].id;
  const created=await page.request.post(`/api/projects/${pid}/nodes`,{data:{title:'模板來源',kind:'task',parent_id:root}});expect(created.status()).toBe(201);const nid=(await created.json()).id;
  await page.reload();await (await openProjects(page)).getByRole('button',{name:title,exact:true}).click();
  await page.getByRole('button',{name:'模板來源',exact:true}).click();
  await (await openActions(page)).getByRole('button',{name:'另存為模板',exact:true}).click();
  let dialog=page.getByRole('dialog',{name:'另存為模板',exact:true});const templateName=`模板 ${randomUUID()}`;
  await expect(dialog.getByRole('button',{name:'儲存模板',exact:true})).toBeEnabled();
  await mkdir('../.superpowers/tpe/e2e',{recursive:true});
  for(const width of [1280,1440,375]){await page.setViewportSize({width,height:900});await page.screenshot({path:`../.superpowers/tpe/e2e/save-${width}.png`,fullPage:true});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);}
  await page.setViewportSize({width:1280,height:900});
  await dialog.getByLabel('模板名稱').fill(templateName);await dialog.getByRole('button',{name:'儲存模板',exact:true}).click();await expect(dialog).toHaveCount(0);
  const template=(await(await page.request.get('/api/workflows')).json()).items.find((w:{name:string})=>w.name===templateName);expect(template.kind).toBe('task');
  expect((await page.request.patch(`/api/nodes/${nid}`,{data:{title:'新版來源'}})).status()).toBe(200);
  const v2=await page.request.post(`/api/nodes/${nid}/save-template`,{data:{name:templateName,template_id:template.id,expected_version:1}});expect(v2.status()).toBe(201);
  await (await openActions(page)).getByRole('button',{name:'套用模板',exact:true}).click();dialog=page.getByRole('dialog',{name:'套用模板',exact:true});
  await dialog.getByLabel('選擇模板').selectOption(template.id);await expect(dialog.getByLabel('模板版本')).toHaveValue('2');await dialog.getByLabel('模板版本').selectOption('1');await expect(dialog.getByLabel('模板版本')).toHaveValue('1');
  await mkdir('../.superpowers/tpe/e2e',{recursive:true});
  for(const width of [1280,1440,375]){await page.setViewportSize({width,height:900});await page.screenshot({path:`../.superpowers/tpe/e2e/apply-${width}.png`,fullPage:true});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);}
  await dialog.getByRole('button',{name:'取消',exact:true}).click();expect((await(await page.request.get(`/api/projects/${pid}`)).json()).nodes).toHaveLength(2);
  await (await openActions(page)).getByRole('button',{name:'套用模板',exact:true}).click();dialog=page.getByRole('dialog',{name:'套用模板',exact:true});await dialog.getByLabel('選擇模板').selectOption(template.id);await dialog.getByLabel('模板版本').selectOption('1');await expect(dialog.getByLabel('模板版本')).toHaveValue('1');await dialog.getByRole('button',{name:'套用',exact:true}).click();await expect(dialog).toHaveCount(0);
  expect((await(await page.request.get(`/api/projects/${pid}`)).json()).nodes).toHaveLength(3);
  await page.getByRole('button',{name:'復原',exact:true}).click();await expect(page.getByText('已復原：套用模板',{exact:true})).toBeVisible();expect((await(await page.request.get(`/api/projects/${pid}`)).json()).nodes).toHaveLength(2);
  await page.setViewportSize({width:1280,height:900});await page.getByRole('button',{name:'模板庫',exact:true}).click();await page.getByRole('button',{name:`查看與管理「${templateName}」`}).click();
  await expect(page.getByRole('region',{name:'模板內容'})).toBeVisible();await expect(page.getByLabel('模板版本')).toHaveValue('2');
  for(const width of [1280,1440,375]){await page.setViewportSize({width,height:900});await page.getByRole('region',{name:'模板內容'}).scrollIntoViewIfNeeded();await page.screenshot({path:`../.superpowers/tpe/e2e/library-${width}.png`,fullPage:true});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);}
  await page.getByRole('button',{name:'刪除模板',exact:true}).click();await page.getByRole('button',{name:'確認刪除模板',exact:true}).click();await expect(page.getByRole('button',{name:`查看與管理「${templateName}」`})).toHaveCount(0);
  expect((await page.request.get(`/api/workflows/${template.id}`)).status()).toBe(404);expect(errors).toEqual([]);
});
