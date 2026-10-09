import { useEffect, useRef, useState } from 'react';
import { api, ApiError, recordError, useRequestScope, useRecordMutation } from '../api';
import type { CatalogEntry, WorkflowDetail } from '../types';
const industries: Record<string, string> = {food:'食品研發',electronics:'電子製造',events:'活動行銷',software:'軟體服務',construction:'營建工程'};

function Preview({ entry, canImport, saved, expired, close }: {entry: CatalogEntry; canImport: boolean; saved: (value: WorkflowDetail, signal: AbortSignal) => Promise<void>; expired: () => void; close: () => void}) {
  const [name,setName] = useState(`${entry.name} 複本`);
  const savedId = useRef('');
  const panel = useRef<HTMLElement>(null);
  useEffect(()=>{panel.current?.scrollIntoView?.({block:'start',behavior:'instant'});},[]);
  const mutation = useRecordMutation(async signal => { const value = await api.workflow(savedId.current, signal); await saved(value, signal); }, expired);
  return <section ref={panel} className="catalog-preview record-panel" aria-label="範本預覽"><div className="record-actions"><h2>{entry.name}</h2><button onClick={close} disabled={mutation.busy}>關閉預覽</button></div><p>{entry.description}</p><p className="record-meta">{entry.source}。只包含階段、任務、建議日期、閘門與前置；建立後可調整。</p>
    <div className="catalog-stages">{entry.nodes.filter(n=>n.kind==='phase').map(phase=><article key={phase.id}><h3>{phase.title}</h3><span className="record-tag">第 {phase.start_offset}–{phase.due_offset} 天{phase.gate_after?' · 階段閘門':''}</span><ol>{entry.nodes.filter(n=>n.parent_id===phase.id).map(n=><li key={n.id}>{n.title}</li>)}</ol></article>)}</div>
    <p className="record-meta">{entry.dependencies.length} 條完成至開始（FS）前置。建立模板不會變更既有專案。</p>
    {mutation.error && <p role="alert">{mutation.error}</p>}
    {canImport ? <form onSubmit={e=>{e.preventDefault(); void mutation.execute(async signal=>{const value=await api.saveWorkflow(null,{name:name.trim(),nodes:entry.nodes,dependencies:entry.dependencies},signal);savedId.current=value.id;});}}><label>匯入模板名稱<input value={name} maxLength={160} required disabled={mutation.busy||mutation.saved} onChange={e=>setName(e.target.value)}/></label>{mutation.saved?<button type="button" disabled={mutation.busy} onClick={()=>void mutation.execute()}>重試模板載入</button>:<button disabled={mutation.busy||!name.trim()}>{mutation.busy?'加入中':'加入公司模板'}</button>}</form>:<p>目前身分可預覽，需由管理者或專案負責人加入公司模板。</p>}
  </section>;
}

export default function WorkflowCatalog({saved,expired}: {saved:(value:WorkflowDetail,signal:AbortSignal)=>Promise<void>;expired:()=>void}) {
 const scope=useRequestScope(); const [items,setItems]=useState<CatalogEntry[]>([]);const [canImport,setCanImport]=useState(false);const [loading,setLoading]=useState(true);const [error,setError]=useState('');const [industry,setIndustry]=useState('');const [query,setQuery]=useState('');const [selected,setSelected]=useState<CatalogEntry|null>(null);
 async function load(){const r=scope.begin();setLoading(true);setError('');try{const value=await api.workflowCatalog(r.controller.signal);if(scope.current(r)){setItems(value.items);setCanImport(value.can_import);}}catch(e){if(scope.current(r)){if(e instanceof ApiError&&e.status===401)expired();else setError(recordError(e));}}finally{if(scope.current(r))setLoading(false);}}
 useEffect(()=>{void load();},[]);
 const visible=items.filter(e=>(!industry||e.industry===industry)&&`${e.name} ${e.description}`.includes(query.trim()));
 return <section aria-label="產業範本"><div className="page-heading"><h2>從成熟流程開始</h2><p className="page-description">五種產業的完整流程，可預覽、複製並調整成你的公司模板。</p></div><div className="task-filters"><label>搜尋範本<input value={query} onChange={e=>setQuery(e.target.value)}/></label><label>產業分類<select value={industry} onChange={e=>setIndustry(e.target.value)}><option value="">全部產業</option>{Object.entries(industries).map(([key,name])=><option key={key} value={key}>{name}</option>)}</select></label><button onClick={()=>{setQuery('');setIndustry('');}}>清除範本篩選</button></div>
 {loading?<p role="status">載入產業範本中</p>:error?<><p role="alert">{error}</p><button onClick={()=>void load()}>重試產業範本</button></>:<><p className="record-meta">共 {visible.length} 套範本</p>{visible.length===0&&<p>沒有符合條件的範本</p>}<div className="catalog-grid">{visible.map(entry=><article className={`catalog-card industry-${entry.industry}`} key={entry.key}><span className="record-tag">{industries[entry.industry]}</span><h3>{entry.name}</h3><p>{entry.description}</p><div className="catalog-counts"><span>{entry.nodes.filter(n=>n.kind==='phase').length} 階段</span><span>{entry.nodes.filter(n=>n.kind==='task').length} 任務</span><span>{entry.dependencies.length} 前置</span></div><button aria-label={`預覽${entry.name}`} onClick={()=>setSelected(entry)}>預覽流程 →</button></article>)}</div></>}
 {selected&&<Preview key={selected.key} entry={selected} canImport={canImport} saved={saved} expired={expired} close={()=>setSelected(null)}/>}
 </section>;
}
