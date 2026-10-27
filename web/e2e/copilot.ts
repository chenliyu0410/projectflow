import type { Locator } from '@playwright/test';

/** The copilot folds its settings into one line after a reply; open them before changing dataset, mode or project. */
export async function openSettings(panel: Locator) {
  const toggle = panel.getByRole('button', { name: /查詢設定/ });
  if (await toggle.getAttribute('aria-expanded') !== 'true') await toggle.click();
}

/** Each reply lists its sources under a folded "來源 N 份"; expand them before opening one. */
export async function openSources(scope: Locator) {
  for (const summary of await scope.locator('.ai-sources-group:not([open]) > summary').all()) await summary.click();
}
