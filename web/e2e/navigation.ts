import { expect, type Page } from '@playwright/test';

export async function openProjects(page: Page) {
  const trigger = page.getByRole('button', { name: '專案', exact: true });
  if (!await trigger.isVisible()) await page.getByRole('button', { name: '切換導覽', exact: true }).click();
  await expect(trigger).toBeVisible();
  if (await trigger.getAttribute('aria-expanded') !== 'true') await trigger.click();
  const panel = page.getByLabel('專案清單', { exact: true });
  await expect(panel).toBeVisible();
  return panel;
}
