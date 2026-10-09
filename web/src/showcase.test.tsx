import { fireEvent, render, screen, within, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import WorkflowCatalog from './components/WorkflowCatalog';
import App from './App';
const response=(body:unknown,status=200)=>({ok:status<400,status,json:async()=>body});
const entry={key:'test',industry:'food',name:'食品範本',description:'需求到量產',source:'Demo',nodes:[{id:'p',kind:'phase',title:'開發',parent_id:null,sort_order:0,gate_after:true,start_offset:0,due_offset:4},{id:'t',kind:'task',title:'配方驗證',parent_id:'p',sort_order:1,gate_after:false,start_offset:0,due_offset:4}],dependencies:[]};
describe('UI2 catalog',()=>{
 it('filters and previews without writing, then imports a real independent template',async()=>{
  const saved=vi.fn().mockResolvedValue(undefined);
  const fetcher=vi.fn(async(path:string,init?:RequestInit)=>response(path==='/api/workflow-catalog'?{items:[entry],can_import:true}:path==='/api/workflows'&&init?.method==='POST'?{id:'new'}:{...entry,id:'new',capabilities:{edit:true,copy:true}}));
  vi.stubGlobal('fetch',fetcher);render(<WorkflowCatalog saved={saved} expired={vi.fn()}/>);
  fireEvent.click(await screen.findByRole('button',{name:'預覽食品範本'}));
  expect(screen.getByLabelText('範本預覽')).toHaveTextContent('配方驗證');expect(fetcher).toHaveBeenCalledTimes(1);
  fireEvent.change(screen.getByLabelText('匯入模板名稱'),{target:{value:'我的新流程'}});fireEvent.click(screen.getByRole('button',{name:'加入公司模板'}));
  await waitFor(()=>expect(saved).toHaveBeenCalled());
  const write=fetcher.mock.calls.find(([,init])=>init?.method==='POST')!;
  expect(JSON.parse(write[1]!.body as string)).toEqual({name:'我的新流程',nodes:entry.nodes,dependencies:[]});
 });
 it('allows readonly preview and empty search but no import',async()=>{
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue(response({items:[entry],can_import:false})));
  render(<WorkflowCatalog saved={vi.fn()} expired={vi.fn()}/>);fireEvent.click(await screen.findByRole('button',{name:'預覽食品範本'}));expect(screen.queryByRole('button',{name:'加入公司模板'})).not.toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('搜尋範本'),{target:{value:'不存在'}});expect(screen.getByText('沒有符合條件的範本')).toBeInTheDocument();
 });
 it('cancels switching, then clears old-company data after real session switch',async()=>{
  const companies=[{key:'food',name:'食品公司',industry:'食品'},{key:'events',name:'活動公司',industry:'活動'}];
  const session=(key:string)=>({user:{id:key,display_name:key==='food'?'原管理者':'展示管理者',role:'admin'},organization:{id:key,key,name:key==='food'?'食品公司':'活動公司'},showcase:{active:key==='events',companies}});
  let company='food';const fetcher=vi.fn(async(path:string)=>{
   if(path==='/api/auth/showcase/switch'){company='events';return response(session(company));}
   if(path==='/api/auth/me')return response(session(company));
   if(path==='/api/projects')return response({items:[{id:company,title:company==='food'?'原公司機密專案':'活動專案'}]});
   return response({project_count:1,task_counts:{todo:0,doing:0,review:0,done:0,skipped:0},completion_percent:null,projects:[]});
  });vi.stubGlobal('fetch',fetcher);render(<App/>);
  const select=await screen.findByLabelText('切換公司（本機展示）');
  fireEvent.click(screen.getByRole('button',{name:'新增空白專案'}));
  fireEvent.change(select,{target:{value:'events'}});fireEvent.click(screen.getByRole('button',{name:'取消切換'}));
  expect(fetcher.mock.calls.some(([p])=>p==='/api/auth/showcase/switch')).toBe(false);
  fireEvent.change(select,{target:{value:'events'}});fireEvent.click(screen.getByRole('button',{name:'確認切換公司'}));
  await waitFor(()=>expect(screen.getByLabelText('目前公司')).toHaveTextContent('活動公司'));
  expect(screen.queryByText('原公司機密專案')).not.toBeInTheDocument();expect(await within(screen.getByLabelText('專案清單')).findByText('活動專案')).toBeInTheDocument();expect(screen.getByText('展示身分 · 管理者')).toBeInTheDocument();
 });
});
