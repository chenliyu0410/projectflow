import { closeProjectDrawer, openAccount, openProjects } from './navigation';
import { test, expect } from '@playwright/test';
import { randomUUID } from 'node:crypto';
import { mkdir } from 'node:fs/promises';

for (const width of [1280,375]) test(`TP-G field lifecycle and template at ${width}`, async ({page,request}) => {
  test.setTimeout(120000); page.setDefaultTimeout(15000);
  expect((await request.get('/api/health/acceptance')).status()).toBe(200);
  const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
  await page.setViewportSize({width,height:900});
  const loginApi=async(user:string)=>{const r=await request.post('/api/auth/login',{data:{organization_key:'food',username:user,password:`demo-${user}`}});expect(r.status()).toBe(200);return (await r.json()).user.id;};
  const member=await loginApi('ming');await loginApi('yu');
  const title=`TP-G ${randomUUID()}`;
  const project=await request.post('/api/projects',{data:{title}});expect(project.status()).toBe(201);const pid=(await project.json()).id;
  const made=await request.post(`/api/projects/${pid}/nodes`,{data:{title:'自訂回報驗證',kind:'task',owner_user_id:member}});expect(made.status()).toBe(201);const nid=(await made.json()).id;
  async function login(user:string){await page.goto('/');await page.getByLabel('帳號',{exact:true}).fill(user);await page.getByLabel('密碼',{exact:true}).fill(`demo-${user}`);await page.getByRole('button',{name:'登入',exact:true}).click();await expect(page.getByLabel('可見任務完成率',{exact:true})).toBeVisible();}
  async function open(){await (await openProjects(page)).getByRole('button',{name:title,exact:true}).click();await closeProjectDrawer(page);await page.getByLabel('看板',{exact:true}).getByRole('button',{name:'自訂回報驗證',exact:true}).click();}
  async function logout(){await (await openAccount(page)).getByRole('button',{name:'登出',exact:true}).click();await expect(page.getByRole('heading',{name:'登入專流',exact:true})).toBeVisible();}
  await login('ming');await open();await page.getByRole('button',{name:'編輯節點',exact:true}).click();
  const editor=page.getByRole('region',{name:'自訂回報欄位設定'});
  await expect(editor.getByRole('button',{name:'新增欄位'})).toBeEnabled();
  for(const [label,type,extra] of [['備註','text',''],['重量','number','kg'],['測試日','date',''],['判定','select','合格、不合格']]){
    await editor.getByLabel('欄位名稱',{exact:true}).fill(label);await editor.getByLabel('欄位類型',{exact:true}).selectOption(type);
    if(extra)await editor.getByLabel(type==='number'?'單位':'選項（以逗號分隔）',{exact:true}).fill(extra);
    await editor.getByRole('checkbox',{name:'必填',exact:true}).check();await editor.getByRole('button',{name:'新增欄位',exact:true}).click();
  }
  await editor.getByRole('button',{name:'上移 判定',exact:true}).click();
  await editor.getByRole('button',{name:'儲存回報欄位',exact:true}).click();await expect(editor.getByText('回報欄位已儲存',{exact:true})).toBeVisible();
  await mkdir('../.superpowers/tpg/e2e',{recursive:true});await page.screenshot({path:`../.superpowers/tpg/e2e/editor-${width}.png`,fullPage:true});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.getByRole('form',{name:'編輯節點表單'}).getByRole('button',{name:'取消',exact:true}).click();
  await page.getByRole('button',{name:'回報完成',exact:true}).click();
  await page.getByRole('textbox',{name:'成果說明',exact:true}).fill('第一版');await page.getByLabel('實際完成日',{exact:true}).fill('2026-10-10');
  await page.getByRole('button',{name:'送出回報',exact:true}).click();await expect(page.getByRole('form',{name:'回報表單'})).toBeVisible();
  await page.getByLabel('備註（必填）',{exact:true}).fill('<文字安全>');await page.getByLabel('重量（kg）（必填）',{exact:true}).fill('0');await page.getByLabel('測試日（必填）',{exact:true}).fill('2026-10-10');await page.getByLabel('判定（必填）',{exact:true}).selectOption('合格');
  await page.screenshot({path:`../.superpowers/tpg/e2e/form-${width}.png`,fullPage:true});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.getByRole('button',{name:'送出回報',exact:true}).click();await expect(page.getByText('v1 等待確認',{exact:true})).toBeVisible();
  await logout();await login('yu');await open();await expect(page.getByLabel('完成回報',{exact:true})).toContainText('0 kg');await page.getByLabel('審核意見',{exact:true}).fill('請補充');await page.getByRole('button',{name:'退回回報',exact:true}).click();await expect(page.getByText('v1 已退回',{exact:true})).toBeVisible();
  await logout();await login('ming');await open();await page.getByRole('button',{name:'重新回報',exact:true}).click();await expect(page.getByLabel('重量（kg）（必填）',{exact:true})).toHaveValue('0');await expect(page.getByLabel('備註（必填）',{exact:true})).toHaveValue('<文字安全>');await page.getByRole('textbox',{name:'成果說明',exact:true}).fill('第二版');await page.getByRole('button',{name:'送出回報',exact:true}).click();await expect(page.getByText('v2 等待確認',{exact:true})).toBeVisible();
  await logout();await login('yu');await open();await page.getByRole('button',{name:'確認回報',exact:true}).click();await expect(page.getByLabel('完成回報',{exact:true})).toContainText('已確認');
  const saved=await page.request.post(`/api/nodes/${nid}/save-template`,{data:{name:`欄位模板 ${randomUUID()}`}});expect(saved.status()).toBe(201);const template=await saved.json();
  const applied=await page.request.post(`/api/projects/${pid}/apply-template`,{data:{template_id:template.id,version:1}});expect(applied.status()).toBe(201);const newId=(await applied.json()).node_ids[0];
  const oldFields=(await(await page.request.get(`/api/nodes/${nid}/report-fields`)).json()).fields;const newFields=(await(await page.request.get(`/api/nodes/${newId}/report-fields`)).json()).fields;
  expect(newFields).toHaveLength(4);expect(newFields[0].id).not.toBe(oldFields[0].id);
  expect(errors).toEqual([]);
});
