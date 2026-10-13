import { fireEvent, render, screen, within, act, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import WorkspaceShell from './components/WorkspaceShell';
import useScrollActivity from './useScrollActivity';
import { api } from './api';

function setup() {
  vi.spyOn(api, 'overview').mockResolvedValue({ projects: [] } as never);
  const navigate = vi.fn();
  render(<WorkspaceShell route={{page: 'overview'}} projects={[{id:'p', title:'長名稱專案', organization_key:'food', owner_user_id:null}]} busy={false} navigate={navigate} copilotScope="總覽"><button>內容操作</button></WorkspaceShell>);
  return navigate;
}
describe('project secondary navigation', () => {
  it('opens on demand, selects the project and returns focus to its trigger', () => {
    const navigate = setup();
    const trigger = screen.getByRole('button', {name:'專案'});
    expect(screen.getByLabelText('專案清單')).not.toBeVisible();
    fireEvent.click(trigger);
    const project = within(screen.getByLabelText('專案清單')).getByRole('button', {name:'長名稱專案'});
    expect(project).toHaveFocus();
    fireEvent.click(project);
    expect(navigate).toHaveBeenCalledWith({page:'project', projectId:'p', nodeId:null});
    expect(trigger).toHaveFocus();
    expect(trigger).toHaveAttribute('aria-expanded', 'false');
  });
  it('Escape closes the second level before the mobile navigation', () => {
    setup();
    const navigation = screen.getByRole('button', {name:'切換導覽'});
    fireEvent.click(navigation);
    const trigger = screen.getByRole('button', {name:'專案'});
    fireEvent.click(trigger);
    fireEvent.keyDown(document, {key:'Escape'});
    expect(trigger).toHaveFocus();
    expect(trigger).toHaveAttribute('aria-expanded', 'false');
    expect(navigation).toHaveAttribute('aria-expanded', 'true');
    fireEvent.keyDown(document, {key:'Escape'});
    expect(navigation).toHaveAttribute('aria-expanded', 'false');
  });
  it('returns focus to the trigger when closing from outside blank space', async () => {
    setup();
    const trigger = screen.getByRole('button', {name:'專案'});
    fireEvent.click(trigger);
    fireEvent.pointerDown(document.body);
    await waitFor(() => expect(trigger).toHaveFocus());
    expect(screen.getByLabelText('專案清單')).not.toBeVisible();
  });
  it('closes on outside pointer interaction without stealing focus', () => {
    setup();
    fireEvent.click(screen.getByRole('button', {name:'專案'}));
    fireEvent.pointerDown(screen.getByRole('button', {name:'內容操作'}));
    expect(screen.getByLabelText('專案清單')).not.toBeVisible();
  });
});
it('reveals each active scroller independently, hides it after idle and cleans up', () => {
  vi.useFakeTimers();
  function Scrollers() { useScrollActivity(); return <><div data-testid="one"/><div data-testid="two"/></>; }
  const view=render(<Scrollers/>);
  try {
    const one=screen.getByTestId('one'), two=screen.getByTestId('two');
    fireEvent.scroll(one);
    expect(one).toHaveAttribute('data-scroll-active','true');
    expect(two).not.toHaveAttribute('data-scroll-active');
    act(()=>vi.advanceTimersByTime(500));
    fireEvent.scroll(two);
    act(()=>vi.advanceTimersByTime(400));
    expect(one).not.toHaveAttribute('data-scroll-active');
    expect(two).toHaveAttribute('data-scroll-active','true');
    view.unmount();
    expect(two).not.toHaveAttribute('data-scroll-active');
    expect(vi.getTimerCount()).toBe(0);
  } finally { vi.useRealTimers(); }
});
