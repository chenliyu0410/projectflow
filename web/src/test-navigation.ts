import { fireEvent, screen } from '@testing-library/react';

export function projectMenu() {
  const trigger = screen.getByRole('button', { name: '專案' });
  if (trigger.getAttribute('aria-expanded') !== 'true') fireEvent.click(trigger);
  return screen.getByLabelText('專案清單');
}
export async function findProjectMenu() {
  await screen.findByRole('button', { name: '專案' });
  return projectMenu();
}
export function createProjectButton() {
  projectMenu();
  return screen.getByRole('button', { name: '建立新專案' });
}
export async function findCreateProjectButton() {
  await findProjectMenu();
  return createProjectButton();
}
