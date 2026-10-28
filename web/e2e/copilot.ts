import type { Locator } from '@playwright/test';

/** The copilot picks its data by category buttons (文件問答、資料分析、新人報到、正式文件) instead of menus. */
export async function chooseCategory(panel: Locator, name: string) {
  await panel.getByRole('group', { name: 'AI 分類' }).getByRole('button', { name, exact: true }).click();
}

/** Model settings, preview and the formal index fold behind the gear; open it before using them. */
export async function openAdvanced(panel: Locator) {
  const gear = panel.getByRole('button', { name: '進階設定' });
  if (await gear.getAttribute('aria-expanded') !== 'true') await gear.click();
}

/** Each reply lists its sources under a folded "來源 N 份"; expand them before opening one. */
export async function openSources(scope: Locator) {
  for (const summary of await scope.locator('.ai-sources-group:not([open]) > summary').all()) await summary.click();
}
