import { expect, type Page } from '@playwright/test';

export async function openProjects(page: Page) {
  await page.locator('.project-menu-toggle').waitFor({state:'attached'});
  const trigger = page.getByRole('button', { name: '專案', exact: true });
  if (!await trigger.isVisible()) await page.getByRole('button', { name: '切換導覽', exact: true }).click();
  await expect(trigger).toBeVisible();
  if (await trigger.getAttribute('aria-expanded') !== 'true') await trigger.click();
  const panel = page.getByLabel('專案清單', { exact: true });
  await expect(panel).toBeVisible();
  return panel;
}

export async function openAccount(page: Page) {
  if (await page.getByLabel('專案清單',{exact:true}).isVisible()) await page.keyboard.press('Escape');
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
