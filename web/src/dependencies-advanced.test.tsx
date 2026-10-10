import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import DependencyPanel from './components/DependencyPanel';
import DependencyGraph from './components/DependencyGraph';
import { dependencyShift, dependencyMet } from './dependencies';
import { criticalChain } from './timeline';
import type { DependencyData, NodeItem } from './types';
const data: DependencyData = {items: [], nodes: [{id:'a',title:'A',status:'todo',blocked:false},{id:'b',title:'B',status:'todo',blocked:false}], conditions:[], capabilities:{manage:true}};
const response = (body: unknown, status=200) => ({ok:status<400,status,json:async()=>body});
afterEach(()=>vi.restoreAllMocks());
it('calculates calendar constraints and SS satisfaction without soft scheduling',()=>{
  const a={start:1,due:3},b={start:2,due:4};
  expect(dependencyShift({relation_type:'FS',lag_days:-1},a,b)).toBe(1);
  expect(dependencyShift({relation_type:'SS',lag_days:2},a,b)).toBe(1);
  expect(dependencyShift({relation_type:'FF',lag_days:2},a,b)).toBe(1);
  expect(dependencyMet({relation_type:'SS'},'doing')).toBe(true);
  expect(dependencyMet({relation_type:'FF'},'doing')).toBe(false);
  const nodes=['a','b'].map(id=>({id,kind:'task',start_date:'2026-10-01',due_date:'2026-10-03',parent_id:null} as NodeItem));
  expect(criticalChain(nodes,[{id:'ab',project_id:'p',predecessor_id:'a',successor_id:'b',enforcement:'soft'}]).edges.size).toBe(0);
});
it('drag opens a draft only and cancel never sends a write',async()=>{
  const fetch=vi.fn().mockResolvedValue(response(data));vi.stubGlobal('fetch',fetch);
  render(<DependencyPanel projectId="p" select={vi.fn()} reload={vi.fn()} expired={vi.fn()}/>);
  const handle=await screen.findByRole('button',{name:'拖線建立前置：A'});
  fireEvent.pointerDown(handle,{button:0});fireEvent.pointerUp(screen.getByRole('button',{name:'開啟任務：B'}));
  await waitFor(()=>expect(screen.getByLabelText('前置任務')).toHaveValue('a'));
  expect(screen.getByLabelText('後續任務')).toHaveValue('b');
  fireEvent.click(screen.getByRole('button',{name:'取消'}));
  expect(fetch.mock.calls.every(c=>!c[1]?.method)).toBe(true);
});
it('advanced fields submit and failed writes preserve draft',async()=>{
  const fetch=vi.fn().mockResolvedValueOnce(response(data)).mockResolvedValue(response({detail:'前置任務不可循環'},409));vi.stubGlobal('fetch',fetch);
  render(<DependencyPanel projectId="p" select={vi.fn()} reload={vi.fn()} expired={vi.fn()}/>);
  fireEvent.click(await screen.findByRole('button',{name:'建立相依連線'}));
  fireEvent.change(screen.getByLabelText('前置任務'),{target:{value:'a'}});fireEvent.change(screen.getByLabelText('後續任務'),{target:{value:'b'}});
  fireEvent.change(screen.getByLabelText('關係類型'),{target:{value:'SS'}});fireEvent.change(screen.getByLabelText('延遲天數'),{target:{value:'-3'}});fireEvent.change(screen.getByLabelText('強度',{exact:true}),{target:{value:'soft'}});
  fireEvent.click(screen.getByRole('button',{name:'新增前置'}));
  await screen.findByRole('alert');
  expect(JSON.parse(fetch.mock.calls[1][1].body)).toEqual({predecessor_id:'a',successor_id:'b',relation_type:'SS',lag_days:-3,enforcement:'soft'});
  expect(screen.getByLabelText('延遲天數')).toHaveValue(-3);
});
it('readonly graph has no drag handles or manual mutations',()=>{
  render(<DependencyGraph data={{...data,capabilities:{manage:false}}} select={vi.fn()}/>);
  expect(screen.queryByRole('button',{name:/拖線/})).toBeNull();
});
