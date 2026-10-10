import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import {it,expect,vi} from 'vitest';
import CollaborationActions from './components/CollaborationDialogs';
import DepartmentManager from './components/DepartmentManager';
import type {NodeItem} from './types';
const node={id:'n',kind:'task',status:'todo',capabilities:{request_exception:true,direct_exception:false}} as NodeItem;
it('request requires reason, preserves failure, and never repeats committed write on refresh retry',async()=>{
 let loads=0;const reload=vi.fn(async()=>{if(++loads===1)throw Error('reload');});
 const fetcher=vi.fn(async(_path:string,_init?:RequestInit)=>({ok:true,status:201,json:async()=>({id:'r'})}));vi.stubGlobal('fetch',fetcher);
 render(<CollaborationActions node={node} reload={reload} expired={vi.fn()}/>);
 fireEvent.click(screen.getByText('跳過／覆寫申請'));
 expect(screen.getByRole('button',{name:'送出申請'})).toBeDisabled();
 fireEvent.change(screen.getByLabelText('申請理由'),{target:{value:'不用執行'}});
 fireEvent.click(screen.getByRole('button',{name:'送出申請'}));
 await screen.findByRole('alert');fireEvent.click(screen.getByRole('button',{name:'已儲存，重新載入'}));
 await waitFor(()=>expect(reload).toHaveBeenCalledTimes(2));expect(fetcher).toHaveBeenCalledTimes(1);
 expect(JSON.parse(fetcher.mock.calls[0][1]!.body as string)).toMatchObject({kind:'skip',reason:'不用執行',direct:false});
});
it('cancel sends no request and readonly has no action',()=>{
 const f=vi.fn();vi.stubGlobal('fetch',f);const {rerender}=render(<CollaborationActions node={node} reload={vi.fn()} expired={vi.fn()}/>);
 fireEvent.click(screen.getByText('跳過／覆寫申請'));fireEvent.click(screen.getByRole('button',{name:'取消'}));expect(f).not.toHaveBeenCalled();
 rerender(<CollaborationActions node={{...node,capabilities:{...node.capabilities,request_exception:false}}} reload={vi.fn()} expired={vi.fn()}/>);expect(screen.queryByText('跳過／覆寫申請')).toBeNull();
});
it('department edit keeps draft on failed write',async()=>{
 const f=vi.fn(async(_p:string,init?:RequestInit)=>init?.method?{ok:false,status:409,json:async()=>({detail:'已有同名部門'})}:{ok:true,status:200,json:async()=>({items:[],users:[],capabilities:{manage:true}})});vi.stubGlobal('fetch',f);
 render(<DepartmentManager expired={vi.fn()}/>);fireEvent.click(await screen.findByText('新增部門'));fireEvent.change(screen.getByLabelText('部門名稱'),{target:{value:'測試部門'}});fireEvent.click(screen.getByText('儲存部門'));await screen.findByRole('alert');expect(screen.getByLabelText('部門名稱')).toHaveValue('測試部門');
});
