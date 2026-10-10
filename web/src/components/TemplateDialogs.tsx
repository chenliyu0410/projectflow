import { useEffect, useState } from 'react';
import { api, recordError, ApiError, useRequestScope } from '../api';
import type { WorkflowDetail, WorkflowSummary, TemplateVersion, TemplateApplyResult } from '../types';

export function VersionPicker({detail, select, expired, loading}: {loading?:(busy:boolean)=>void; detail: WorkflowDetail; select:(value:WorkflowDetail)=>void; expired:()=>void}) {
  const [versions,setVersions]=useState<TemplateVersion[]>([]); const [error,setError]=useState(''); const scope=useRequestScope();
  useEffect(()=>{const r=scope.begin();void api.templateVersions(detail.id,r.controller.signal).then(v=>{if(scope.current(r))setVersions(v.items);}).catch(e=>{if(scope.current(r)){setError(recordError(e));if(e instanceof ApiError&&e.status===401)expired();}});},[detail.id]);
  async function choose(version:number){const r=scope.begin();setError('');loading?.(true);try{const v=await api.templateVersion(detail.id,version,r.controller.signal);if(scope.current(r))select(v);}catch(e){if(scope.current(r)){setError(recordError(e));if(e instanceof ApiError&&e.status===401)expired();}}finally{if(scope.current(r))loading?.(false);}}
  return <><label>模板版本<select value={detail.version??1} onChange={e=>void choose(Number(e.target.value))}>{versions.length?versions.map(v=><option key={v.version} value={v.version}>v{v.version} · {v.author} · {v.created_at.slice(0,10)}</option>):<option value={detail.version??1}>v{detail.version??1}</option>}</select></label>{error&&<p role="alert">{error}</p>}</>;
}

export default function TemplateDialogs({mode,target,title,projectTarget,close,expired,applied,saved}: {
  mode:'save'|'apply'; target:string; title:string; projectTarget:boolean; close:()=>void; expired:()=>void;
  applied:(result:TemplateApplyResult,signal:AbortSignal)=>Promise<void>; saved:()=>void;
}) {
  const scope=useRequestScope(); const [list,setList]=useState<WorkflowSummary[]>([]);const [name,setName]=useState(title.slice(0,160));
  const [selected,setSelected]=useState('');const [detail,setDetail]=useState<WorkflowDetail|null>(null);const [busy,setBusy]=useState(true);const [error,setError]=useState('');
  const [start,setStart]=useState('');const [structure,setStructure]=useState(true);const [dependencies,setDependencies]=useState(true);const [owners,setOwners]=useState(false);const [dates,setDates]=useState(true);const [variables,setVariables]=useState<Record<string,string>>({});
  const [result,setResult]=useState<TemplateApplyResult|null>(null);
  const fail=(e:unknown)=>{setError(recordError(e));if(e instanceof ApiError&&e.status===401)expired();};
  useEffect(()=>{const r=scope.begin();void api.workflows(r.controller.signal).then(v=>{if(scope.current(r))setList(v.items.filter(w=>mode==='save'?(w.kind??'workflow')===(projectTarget?'workflow':'task'):projectTarget||w.kind==='task'));}).catch(e=>{if(scope.current(r))fail(e);}).finally(()=>{if(scope.current(r))setBusy(false);});},[]);
  async function choose(id:string){setSelected(id);setDetail(null);if(!id)return;const r=scope.begin();setBusy(true);setError('');try{const v=await api.workflow(id,r.controller.signal);if(scope.current(r))setDetail(v);}catch(e){if(scope.current(r))fail(e);}finally{if(scope.current(r))setBusy(false);}}
  async function submit(){const r=scope.begin();setBusy(true);setError('');try{
    if(mode==='save') {await api.saveTemplate(target,{name:name.trim(),...(detail?{template_id:detail.id,expected_version:detail.version}: {})},r.controller.signal);if(scope.current(r)){saved();close();}}
    else {const value=result??await api.applyTemplate(target,{template_id:detail!.id,version:detail!.version??1,...(dates&&start?{start_date:start}:{}),structure:detail!.kind==='workflow'||structure,dependencies,owners,dates,variables},r.controller.signal);if(scope.current(r)){setResult(value);await applied(value,r.controller.signal);if(scope.current(r))close();}}
  }catch(e){if(scope.current(r))fail(e);}finally{if(scope.current(r))setBusy(false);}}
  const vars=[...new Set((detail?.nodes??[]).flatMap(n=>Array.from(n.title.matchAll(/\{([^{}]+)\}/g),m=>m[1])))];
  const renderTitle=(title:string)=>title.replace(/\{([^{}]+)\}/g,(m,key)=>variables[key]??m);
  return <div className="template-overlay"><section role="dialog" aria-modal="true" aria-label={mode==='save'?'另存為模板':'套用模板'} className="template-dialog"><form onSubmit={e=>{e.preventDefault();void submit();}}>
    <h2>{mode==='save'?'另存為模板':'套用模板'}</h2><p>{mode==='save'?'保存來源':'建立在'}：{title}</p>
    {error&&<p role="alert">{error}</p>}
    {result?<p>任務已建立；重新載入失敗時請重試載入，不會重複套用。</p>:<fieldset disabled={busy}>
      {mode==='save'&&<label>模板名稱<input required maxLength={160} value={name} onChange={e=>setName(e.target.value)}/></label>}
      <label>{mode==='save'?'儲存方式':'選擇模板'}<select value={selected} required={mode==='apply'} onChange={e=>void choose(e.target.value)}><option value="">{mode==='save'?'建立新模板':'請選擇模板'}</option>{list.map(w=><option key={w.id} value={w.id}>{mode==='save'?'建立新版：':''}{w.name} · v{w.version??1}</option>)}</select></label>
      {mode==='save'?<p className="note">保存整棵子樹及內部前置；外部前置不帶入。階段另存會轉為普通根任務，不帶閘門。同名請明確選擇建立新版。既有任務不會隨模板更新。</p>:<>
      {detail&&<VersionPicker detail={detail} select={setDetail} expired={expired} loading={setBusy}/>}
      <label>開始日<input type="date" value={start} required={dates&&!!detail?.requires_start_date} disabled={!dates} onChange={e=>setStart(e.target.value)}/></label>
      <div className="template-options">{detail?.kind!=='workflow'&&<label><input type="checkbox" checked={structure} onChange={e=>setStructure(e.target.checked)}/>子任務結構</label>}
      <label><input type="checkbox" checked={dependencies} onChange={e=>setDependencies(e.target.checked)}/>前置與人工條件</label>
      <label><input type="checkbox" checked={owners} onChange={e=>setOwners(e.target.checked)}/>預設負責人／協作部門</label>
      <label><input type="checkbox" checked={dates} onChange={e=>setDates(e.target.checked)}/>工期與相對日期</label></div>
      {vars.map(v=><label key={v}>{`{${v}}`}<input maxLength={200} value={variables[v]??''} onChange={e=>setVariables(old=>({...old,[v]:e.target.value}))}/></label>)}
      <p className="note">只追加，不覆蓋既有任務。新任務為待處理、未鎖定，人工條件需重新確認；不帶回報、筆記或附件。不勾人員則未指派。含里程碑時必須帶入日期。</p>
      {detail&&<details open><summary>預覽：{detail.name} v{detail.version} · {detail.kind==='workflow'||structure?detail.nodes.length:1} 個節點</summary><ol>{detail.nodes.filter(n=>detail.kind==='workflow'||structure||!n.parent_id).map(n=><li key={n.id}>{renderTitle(n.title)}{(n.report_fields?.length ?? 0) > 0 && <span> · 回報欄位：{n.report_fields!.map(f => `${f.label}${f.required ? '（必填）' : ''}`).join('、')}</span>}{n.milestone?' · 里程碑':''}{dates?` · 第 ${n.start_offset??'未排程'} 至 ${n.due_offset??'未排程'} 天`:''}</li>)}</ol><p>{dependencies?`${detail.dependencies.length} 條內部前置・${detail.conditions?.length??0} 個人工條件`:'不帶前置與條件'}；外部前置不帶入。</p></details>}
      </>}
    </fieldset>}
    <div className="record-actions"><button type="button" disabled={busy} onClick={close}>取消</button><button className="primary" disabled={busy||(mode==='apply'&&!detail)||(!result&&!!selected&&!detail)}>{busy?'處理中…':result?'重試載入':mode==='save'?'儲存模板':'套用'}</button></div>
  </form></section></div>;
}
