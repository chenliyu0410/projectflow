import { ReportFieldValues } from './ReportFieldEditor';
import { useEffect, useState } from 'react';
import { api, ApiError, useRecordMutation } from '../api';
import type { RecordReload } from '../api';
import type { NodeItem, CollaborationRequest } from '../types';
export default function CollaborationActions({node,reload,expired}:{node:NodeItem;reload:RecordReload;expired:()=>void}) {
  const [open,setOpen]=useState(false),[kind,setKind]=useState('skip'),[reason,setReason]=useState('');
  const mutation=useRecordMutation(reload,expired);
  if(!node.capabilities?.request_exception || ['done','skipped'].includes(node.status))return null;
  const direct=!!node.capabilities?.direct_exception;
  return <div className="panel"><button disabled={mutation.busy} onClick={()=>{setKind(node.kind==='phase'?'gate':'skip');setOpen(!open);}}>跳過／覆寫申請</button>{open && <form onSubmit={e=>{e.preventDefault();if(reason.trim())void mutation.execute(signal=>api.requestException(node.id,kind,reason.trim(),direct,signal));}}><h3>{direct?'附理由直接操作':'送出申請'}</h3><label>操作<select value={kind} disabled={mutation.busy||mutation.saved} onChange={e=>setKind(e.target.value)}>{node.kind==='phase'?<><option value="gate">覆寫此階段閘門</option><option value="phase_complete">覆寫子節點限制，完成階段</option></>:<><option value="skip">跳過任務與未完成子任務</option>{node.status==='todo' && <option value="start">覆寫前置，開始任務</option>}</>}</select></label><p className="note">跳過會連同未完成子任務一起處理；覆寫只放行這次操作，完成仍須交回報。</p><label>申請理由<textarea required maxLength={2000} value={reason} disabled={mutation.busy||mutation.saved} onChange={e=>setReason(e.target.value)}/></label>{mutation.error && <p role="alert">{mutation.error}</p>}{mutation.saved?<button type="button" onClick={()=>void mutation.execute()}>已儲存，重新載入</button>:<button disabled={mutation.busy||!reason.trim()}>{direct?'附理由執行':'送出申請'}</button>}<button type="button" disabled={mutation.busy} onClick={()=>setOpen(false)}>取消</button></form>}</div>;
}
export function RequestReviews({expired}:{expired:()=>void}) {
 const [version,setVersion]=useState(0);
 return <RequestReviewsList key={version} expired={expired} refreshed={()=>setVersion(v=>v+1)}/>;
}
function RequestReviewsList({expired,refreshed}:{expired:()=>void;refreshed:()=>void}) {
 const [items,setItems]=useState<CollaborationRequest[]>([]),[comments,setComments]=useState<Record<string,string>>({}),[error,setError]=useState('');
 const load:RecordReload=async signal=>{const d=await api.collaborationRequests(signal);if(!Array.isArray(d.items))throw Error('invalid response');setItems(d.items);};
 const mutation=useRecordMutation(async signal=>{await load(signal);refreshed();},expired);
 useEffect(()=>{const c=new AbortController();load(c.signal).catch(e=>{if(c.signal.aborted)return;if(e instanceof ApiError&&e.status===401)expired();else setError('無法載入申請');});return()=>c.abort();},[]);
 return <><h2>跳過／覆寫申請（{items.length}）</h2><button disabled={mutation.busy} onClick={refreshed}>重新整理申請</button>{(error||mutation.error)&&<p role="alert">{error||mutation.error}</p>}{mutation.saved && <button onClick={()=>void mutation.execute()}>已儲存，重新載入申請</button>}{items.map(r=><article className="panel" key={r.id}><h3>{r.node_title}</h3><p>{r.kind==='skip'?'跳過子樹':r.kind==='gate'?'覆寫閘門':r.kind==='report_submit'?'覆寫並送出完成回報':r.kind==='phase_complete'?'覆寫並完成階段':'覆寫前置'}：{r.reason}</p>{r.report && <p>回報：{r.report.result}／{r.report.summary}／{r.report.finished_on}</p>}<ReportFieldValues fields={r.fields} />{r.can_review?<><label>退回理由<input value={comments[r.id]??''} onChange={e=>setComments({...comments,[r.id]:e.target.value})}/></label><button disabled={mutation.busy||mutation.saved} onClick={()=>void mutation.execute(signal=>api.decideException(r.id,'approved','',signal))}>核准申請</button><button disabled={mutation.busy||mutation.saved||!comments[r.id]?.trim()} onClick={()=>void mutation.execute(signal=>api.decideException(r.id,'rejected',comments[r.id].trim(),signal))}>退回申請</button></>:<p>等待主管核准</p>}</article>)}{!items.length && !error && <p className="empty">目前沒有待處理申請。</p>}</>;
}
