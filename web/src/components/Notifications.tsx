import { useEffect, useState } from 'react';
import { api, ApiError } from '../api';
import type { NotificationPage } from '../types';
export default function Notifications({openNode,expired}:{openNode:(p:string,n:string)=>void;expired:()=>void}) {
  const [data,setData]=useState<NotificationPage|null>(null),[offset,setOffset]=useState(0),[error,setError]=useState(''),[busy,setBusy]=useState(false),[version,setVersion]=useState(0);
  useEffect(()=>{const c=new AbortController();setError('');api.notifications(offset,c.signal).then(d=>{if(!Array.isArray(d.items))throw Error('invalid response');setData(d);}).catch(e=>{if(c.signal.aborted)return;if(e instanceof ApiError && e.status===401)expired();else setError('無法載入通知');});return()=>c.abort();},[offset,version]);
  async function read(id:string){setBusy(true);try{await api.readNotification(id);setVersion(v=>v+1);}catch{setError('無法標記已讀');}finally{setBusy(false);}}
  return <section className="panel" aria-label="站內通知"><h2>通知{data ? `（${data.unread_count} 未讀）` : ''}</h2>{error && <p role="alert">{error}</p>}<button onClick={()=>setVersion(v=>v+1)}>重新整理通知</button>{data?.items.map(n=><div key={n.id} className="panel"><button className="row-link" onClick={()=>openNode(n.project_id,n.node_id)}>{n.node_title}</button><p>{n.message}</p><small>{new Date(n.created_at).toLocaleString()}</small>{!n.read && <button disabled={busy} onClick={()=>void read(n.id)}>標記已讀</button>}</div>)}{data?.items.length===0 && <p className="empty">目前沒有通知。</p>}{offset>0 && <button onClick={()=>setOffset(Math.max(0,offset-20))}>上一頁通知</button>}{data?.next_offset!=null && <button onClick={()=>setOffset(data.next_offset!)}>下一頁通知</button>}</section>;
}
