import {expect,test} from '@playwright/test';
import {openProjects,closeProjectDrawer} from './navigation';
for(const [width,height] of [[1440,900],[1280,720],[1024,600],[768,600],[375,720]])test(`fixed project list and connected tabs ${width}`,async({page,request},info)=>{
 expect(await (await request.get('/api/health/acceptance')).json()).toEqual({acceptance:true});
 await page.setViewportSize({width,height});await page.goto('/');await page.getByLabel('帳號',{exact:true}).fill('yu');await page.getByLabel('密碼',{exact:true}).fill('demo-yu');await page.getByRole('button',{name:'登入',exact:true}).click();
 const panel=await openProjects(page),list=panel.locator('.sidebar-projects');
 for(const button of await list.getByRole('button').all()){
  await button.scrollIntoViewIfNeeded();await button.click({trial:true});
  const r=await button.evaluate(el=>{const a=el.getBoundingClientRect(),b=el.parentElement!.getBoundingClientRect(),t=el.querySelector('.project-name')!;return{top:a.top,bottom:a.bottom,min:b.top,max:b.bottom,text:t.scrollWidth,width:t.clientWidth}});
  expect(r.top).toBeGreaterThanOrEqual(r.min-1);expect(r.bottom).toBeLessThanOrEqual(r.max+1);expect(r.text).toBeLessThanOrEqual(r.width+1);
 }
 await page.screenshot({path:info.outputPath('fixed-projects.png')});
 const trigger=panel.getByRole('button',{name:'成貓主食罐正式版',exact:true});await trigger.click();await expect(page.getByRole('dialog',{name:'專案我的待辦'})).toBeVisible();await closeProjectDrawer(page);
 if(width>860){await expect(panel).toBeVisible();await expect(trigger).toBeFocused();}else await expect(page.getByRole('button',{name:'切換導覽'})).toBeFocused();
 for(const name of ['看板','時程','相依圖']){
  await page.getByRole('tab',{name,exact:true}).click();await expect(page.getByRole('tab',{name,exact:true})).toHaveAttribute('aria-selected','true');
  const connection=await page.locator('.node-views').evaluate(el=>{const tab=el.querySelector('[aria-selected=true]')!,content=el.querySelector('.node-view-content')!;return{color:getComputedStyle(content).backgroundColor,gap:content.getBoundingClientRect().top-tab.getBoundingClientRect().bottom}});
  await expect.poll(()=>page.getByRole('tab',{name,exact:true}).evaluate(el=>getComputedStyle(el).backgroundColor)).toBe(connection.color);expect(Math.abs(connection.gap)).toBeLessThan(1);
 }
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});
