import { fireEvent, screen } from '@testing-library/react';

export function projectMenu() { return screen.getByRole('region', { name: '固定專案清單' }); }
export async function findProjectMenu() { return screen.findByRole('region', { name: '固定專案清單' }); }
export function closeProjectDrawer() {
 const close = screen.queryByRole('button', { name: '關閉工作項目' });
 if (close) fireEvent.click(close);
}
export function createProjectButton() {
  projectMenu();
  return screen.getByRole('button', { name: '建立新專案' });
}
export async function findCreateProjectButton() {
  await findProjectMenu();
  return createProjectButton();
}

export function accountMenu() {
  const trigger = screen.getByRole('button', { name:'使用者選單' });
  if (trigger.getAttribute('aria-expanded') !== 'true') fireEvent.click(trigger);
  return screen.getByRole('group', { name:'使用者選單內容' });
}
export function logoutButton() {
  accountMenu();
  return screen.getByRole('button', { name:'登出' });
}
export async function findLogoutButton() {
  await screen.findByRole('button', { name:'使用者選單' });
  return logoutButton();
}
export function projectAction(name: string | RegExp) {
  const trigger = screen.getByRole('button', { name:'專案操作' });
  if (trigger.getAttribute('aria-expanded') !== 'true') fireEvent.click(trigger);
  return screen.getByRole('button', { name });
}
