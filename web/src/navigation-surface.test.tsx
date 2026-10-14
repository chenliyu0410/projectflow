import { fireEvent, render, screen, within, act, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import WorkspaceShell from './components/WorkspaceShell';
import useScrollActivity from './useScrollActivity';
import { api } from './api';

function setup(items: unknown[] = []) {
 vi.spyOn(api, 'overview').mockResolvedValue({projects:[]} as never);
 vi.spyOn(api, 'myTasks').mockResolvedValue({items} as never);
 const navigate=vi.fn();
 render(<WorkspaceShell route={{page:'overview'}} projects={[{id:'p',title:'長名稱專案',organization_key:'food',owner_user_id:null}]} busy={false} navigate={navigate} copilotScope="總覽"><button>內容操作</button></WorkspaceShell>);
 return navigate;
}
const task=(id:string,status:string,relations:string[],project_id='p')=>({id,title:id,kind:'task',project_id,status,relations,path:[],due_date:null});
describe('fixed project navigation and personal drawer',()=>{
 it('keeps projects visible and opens an honest empty state',async()=>{
  const navigate=setup();const trigger=within(screen.getByRole('region',{name:'固定專案清單'})).getByRole('button',{name:'長名稱專案'});
  expect(trigger).toBeVisible();fireEvent.click(trigger);
  expect(navigate).toHaveBeenCalledWith({page:'project',projectId:'p',nodeId:null});
  expect(await screen.findByText('這個專案目前沒有你的待辦。')).toBeVisible();
  fireEvent.click(screen.getByRole('button',{name:'關閉工作項目'}));
  expect(trigger).toHaveFocus();expect(screen.getByLabelText('專案我的待辦')).not.toBeVisible();
 });
 it('includes owned and collaborating tasks only, excluding completed and other projects',async()=>{
  const navigate=setup([task('我負責','doing',['owned']),task('協作項','todo',['collaborating']),task('完成項','done',['owned']),task('略過項','skipped',['collaborating']),task('未指派','todo',['awaiting_assignment']),task('他人項','todo',[]),task('別專案','doing',['owned'],'other')]);
  fireEvent.click(screen.getByRole('button',{name:'長名稱專案'}));
  const drawer=screen.getByRole('dialog',{name:'專案我的待辦'});
  await waitFor(()=>expect(drawer.querySelectorAll('.project-task-item')).toHaveLength(2));
  expect(within(drawer).queryByText('完成項')).not.toBeInTheDocument();expect(within(drawer).queryByText('別專案')).not.toBeInTheDocument();
  fireEvent.click(within(drawer).getByRole('button',{name:/協作項/}));
  expect(navigate).toHaveBeenLastCalledWith({page:'project',projectId:'p',nodeId:'協作項'});
 });
 it('native cancel closes the drawer and restores focus',async()=>{
  setup();const trigger=screen.getByRole('button',{name:'長名稱專案'});fireEvent.click(trigger);
  await screen.findByText('這個專案目前沒有你的待辦。');
  fireEvent(screen.getByRole('dialog',{name:'專案我的待辦'}),new Event('cancel',{bubbles:false,cancelable:true}));
  expect(trigger).toHaveFocus();expect(trigger).toHaveAttribute('aria-expanded','false');
 });
 it('shows a failed request as an error rather than an empty task list',async()=>{
  setup();vi.mocked(api.myTasks).mockRejectedValueOnce(new Error('failed'));
  fireEvent.click(screen.getByRole('button',{name:'長名稱專案'}));
  expect(await screen.findByText('無法載入你的待辦，請重試。')).toBeVisible();
  expect(screen.queryByText('這個專案目前沒有你的待辦。')).not.toBeInTheDocument();
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
