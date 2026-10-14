import { expect, type Page } from '@playwright/test';

export async function closeProjectDrawer(page: Page) {
 const drawer=page.getByRole('dialog',{name:'專案我的待辦'});
 if(await drawer.isVisible())await drawer.getByRole('button',{name:'關閉工作項目'}).click();
}
export async function openProjects(page: Page) {
 await closeProjectDrawer(page);
 const panel=page.locator('.fixed-projects');
 await panel.waitFor({state:'attached'});
 if(!await panel.isVisible())await page.getByRole('button',{name:'切換導覽',exact:true}).click();
 await expect(panel).toBeVisible();return panel;
}

export async function openAccount(page: Page) {
  await closeProjectDrawer(page);
  if (await page.locator('.navigation-toggle').getAttribute('aria-expanded') === 'true') await page.keyboard.press('Escape');
  const assistant = page.getByRole('complementary',{name:'AI 專案副手'});
  if (await assistant.isVisible()) await assistant.getByRole('button',{name:'關閉 AI 副手'}).click();
  const trigger = page.getByRole('button',{name:'使用者選單',exact:true});
  if (await trigger.getAttribute('aria-expanded') !== 'true') await trigger.click();
  return page.getByRole('group',{name:'使用者選單內容',exact:true});
}
export async function openActions(page: Page) {
  const trigger = page.getByRole('button',{name:'專案操作',exact:true});
  if (await trigger.getAttribute('aria-expanded') !== 'true') await trigger.click();
  return page.getByRole('group',{name:'專案操作內容',exact:true});
}
