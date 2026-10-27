import { useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { api } from '../api';
import type { MyTask, ProjectSummary, WorkspaceRoute } from '../types';
import CopilotPanel from './CopilotPanel';
import Dropdown from './Dropdown';
import NavIcon from './NavIcons';
import type { IconName } from './NavIcons';
export const PROJECT_COLORS = ['#1F5F5B','#B4541F','#4A5A8C','#6B7A3A','#914667','#216677','#A9692E','#3D6F4E'];
export const projectColor = (index: number) => PROJECT_COLORS[index % PROJECT_COLORS.length];
type NavItem = {page:'overview'|'my-tasks'|'reviews'|'workflows'|'audit'|'operations'|'governance'|'accounts';label:string;icon:IconName};
const LINKS:NavItem[]=[{page:'overview',label:'所有專案總覽',icon:'overview'},{page:'my-tasks',label:'我的任務',icon:'tasks'},{page:'reviews',label:'審核中心',icon:'review'},{page:'operations',label:'營運資料',icon:'ops'},{page:'workflows',label:'模板庫',icon:'templates'},{page:'governance',label:'AI 政策與稽核',icon:'ai'},{page:'audit',label:'活動與稽核紀錄',icon:'audit'},{page:'accounts',label:'帳號與密碼',icon:'account'}];
const STATUS:Record<string,string>={todo:'待處理',doing:'進行中',review:'待確認'};
export default function WorkspaceShell({route,projects,busy,navigate,children,session,createAction,headerActions,copilotScope,food=false,companyName='目前公司',accountName='使用者',previewKey,expired}:{
 route:WorkspaceRoute;projects:ProjectSummary[];busy:boolean;navigate:(route:WorkspaceRoute)=>boolean|void;children:ReactNode;session?:ReactNode;createAction?:ReactNode;headerActions?:ReactNode;copilotScope:string;food?:boolean;companyName?:string;accountName?:string;previewKey?:string;expired?:()=>void;
}){
 const [expanded,setExpanded]=useState(false),[copilotOpen,setCopilotOpen]=useState(false);
 const [drawerProject,setDrawerProject]=useState<ProjectSummary|null>(null),[tasks,setTasks]=useState<MyTask[]>([]);
 const [loading,setLoading]=useState(false),[error,setError]=useState(''),[attempt,setAttempt]=useState(0);
 const [progress,setProgress]=useState<Record<string,number|null>>({});
 const toggle=useRef<HTMLButtonElement>(null),copilotToggle=useRef<HTMLButtonElement>(null);
 const restoreCopilotFocus=useRef(false),dialog=useRef<HTMLDialogElement>(null);
 const projectButtons=useRef(new Map<string,HTMLButtonElement>());
 const focusDestination=useRef(false);
 const drawerId=drawerProject?.id,location=route.page==='project'?`project:${route.projectId}`:route.page;
 useEffect(()=>{const request=new AbortController();api.overview(request.signal).then(data=>setProgress(Object.fromEntries(data.projects.map(item=>[item.id,item.progress_percent??null]))),()=>undefined);return ()=>request.abort();},[projects,location]);
 useEffect(()=>{
  if(!drawerId)return;const request=new AbortController();setLoading(true);setError('');setTasks([]);
  api.myTasks('','',request.signal).then(data=>{if(!request.signal.aborted)setTasks(data.items.filter(task=>task.project_id===drawerId&&task.kind==='task'&&!['done','skipped'].includes(task.status)&&task.relations?.some(relation=>relation==='owned'||relation==='collaborating')));}).catch(()=>{if(!request.signal.aborted)setError('無法載入你的待辦，請重試。');}).finally(()=>{if(!request.signal.aborted)setLoading(false);});return ()=>request.abort();
 },[drawerId,attempt]);
 useEffect(()=>{if(drawerProject&&!dialog.current?.open)dialog.current?.showModal();if(!drawerProject&&dialog.current?.open)dialog.current.close();},[drawerProject]);
 function closeDrawer(restore=true){const id=drawerProject?.id;dialog.current?.close();setDrawerProject(null);if(restore){if(window.matchMedia('(max-width:860px)').matches)toggle.current?.focus();else if(id)projectButtons.current.get(id)?.focus();}}
 function go(next:WorkspaceRoute){focusDestination.current=true;closeDrawer(false);setExpanded(false);navigate(next);}
 useEffect(()=>{if(!focusDestination.current||busy)return;const target=document.querySelector<HTMLElement>('.workspace-content .level-back, .workspace-content .node-title, .workspace-content h1');if(target){if(!target.matches('button'))target.tabIndex=-1;target.focus({preventScroll:true});focusDestination.current=false;}},[route,children,busy]);
 function openProject(item:ProjectSummary){setExpanded(false);if(navigate({page:'project',projectId:item.id,nodeId:null})===false)return;setDrawerProject(item);}
 function closeNavigation(){setExpanded(false);toggle.current?.focus();}
 function closeCopilot(){restoreCopilotFocus.current=true;setCopilotOpen(false);}
 useEffect(()=>{if(!copilotOpen&&restoreCopilotFocus.current){restoreCopilotFocus.current=false;copilotToggle.current?.focus();}},[copilotOpen]);
 useEffect(()=>{function key(event:KeyboardEvent){if(event.key!=='Escape'||drawerProject)return;if(expanded)closeNavigation();if(copilotOpen)closeCopilot();}document.addEventListener('keydown',key);return ()=>document.removeEventListener('keydown',key);},[expanded,copilotOpen,drawerProject]);
 return <>
 <aside id="workspace-navigation" className={`workspace-navigation ${expanded?'expanded':''}`} aria-label="側邊導覽">
  <div className="brand"><img src="/mark.svg" width="32" height="32" alt=""/><strong className="brand-name">專流 ProjectFlow</strong></div>
  <nav id="workspace-nav" aria-label="工作區導覽">{LINKS.map(item=><button key={item.page} disabled={busy} aria-current={route.page===item.page?'page':undefined} onClick={()=>go({page:item.page})}><NavIcon name={item.icon}/>{item.label}</button>)}</nav>
  <section className="fixed-projects" aria-label="固定專案清單">
   <div className="fixed-project-heading"><h2><NavIcon name="projects"/>專案</h2><span>{projects.length}</span></div><p className="project-list-hint">選擇專案，查看我的待辦</p>
   <div className="sidebar-projects" tabIndex={0} aria-label="捲動專案清單">{!projects.length&&<p className="sidebar-empty">目前沒有專案</p>}{projects.map((item,index)=><button key={item.id} ref={el=>{if(el)projectButtons.current.set(item.id,el);else projectButtons.current.delete(item.id);}} disabled={busy} aria-label={item.title} aria-haspopup="dialog" aria-expanded={drawerId===item.id} aria-pressed={route.page==='project'&&route.projectId===item.id} onClick={()=>openProject(item)}>
   <span className="project-dot" aria-hidden="true" style={{background:projectColor(index)}}/><span className="project-info"><span className="project-name">{item.title}</span><span className="project-track" aria-hidden="true"><span style={{width:`${progress[item.id]??0}%`,background:projectColor(index)}}/></span></span><span className="project-percent">{progress[item.id]==null?'—':`${progress[item.id]}%`}</span></button>)}</div>
   {createAction&&<div className="sidebar-create" onClick={()=>setExpanded(false)}>{createAction}</div>}
  </section>
 </aside>
 <dialog ref={dialog} className="project-task-drawer" aria-label="專案我的待辦" onCancel={event=>{event.preventDefault();closeDrawer();}} onClick={event=>{if(event.target!==event.currentTarget)return;const r=event.currentTarget.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)closeDrawer();}}>
  <div className="task-drawer-head"><span className="drawer-eyebrow">我的待辦</span><button autoFocus aria-label="關閉工作項目" onClick={()=>closeDrawer()}>×</button></div><h2>{drawerProject?.title}</h2><p className="task-drawer-scope">{accountName}・僅列出指派給我或我參與協作的未完成任務</p>
  <div className="task-drawer-count"><strong>{loading?'…':tasks.length}</strong><span>項待辦</span></div>
  <div className="task-drawer-list" aria-busy={loading}>{loading?<p role="status">載入我的待辦…</p>:error?<div role="alert"><p>{error}</p><button onClick={()=>setAttempt(v=>v+1)}>重試</button></div>:tasks.length?tasks.map(task=><button className="project-task-item" key={task.id} onClick={()=>go({page:'project',projectId:task.project_id,nodeId:task.id})}>
   <span className="task-drawer-row"><span className={`task-state task-state-${task.status}`}>{STATUS[task.status]}</span><span className="task-relation">{task.relations?.includes('owned')?'我負責':'我協作'}</span></span><strong>{task.title}</strong><span className="task-drawer-path">{task.path?.map(p=>p.title).join(' › ')||'專案最上層'}</span><span className="task-drawer-row"><span>{task.due_date?`截止 ${task.due_date.replaceAll('-','/')}`:'尚未設定截止日'}</span><span aria-hidden="true">開啟 →</span></span>
  </button>):<div className="task-drawer-empty"><span aria-hidden="true">✓</span><h3>這個專案目前沒有你的待辦。</h3><p>完成、已略過，以及未指派給你或未邀請你協作的任務，不會列在這裡。</p></div>}</div>
  <button className="task-drawer-overview" disabled={busy||!drawerProject} onClick={()=>drawerProject&&go({page:'project',projectId:drawerProject.id,nodeId:null})}>開啟專案總覽 →</button>
 </dialog>
 <div className="workspace-main"><div className="workspace-topbar"><button ref={toggle} className="navigation-toggle" aria-label="切換導覽" aria-expanded={expanded} aria-controls="workspace-navigation" onClick={()=>setExpanded(v=>!v)}>☰ 選單</button><div className="workspace-account-actions">{headerActions}<Dropdown className="account-menu" name="使用者選單" label={<><span className="avatar" aria-hidden="true">{accountName.slice(0,1)}</span><span className="account-name">{accountName}</span></>}><div className="sidebar-session">{session}</div></Dropdown></div></div><div className="workspace-content">{children}</div></div>
 <button ref={copilotToggle} className="copilot-launcher" aria-label="切換 AI 副手" title="AI 專案副手" aria-expanded={copilotOpen} aria-controls="copilot-panel" onClick={()=>setCopilotOpen(v=>!v)}><NavIcon name="ai" size={26}/><span className="sr-only">AI 專案副手</span></button>
 {/* 只在進出展示預覽區時重建（照 formal-development.md 清除對話）；一般導覽保留對話與進行中查詢。 */}
 <CopilotPanel key={previewKey??'workspace'} food={food} companyName={companyName} scope={copilotScope} open={copilotOpen} close={closeCopilot} expired={expired}/>
 {(expanded||copilotOpen)&&<div className="drawer-backdrop" aria-hidden="true" onClick={()=>{if(expanded)closeNavigation();if(copilotOpen)closeCopilot();}}/>}
 </>;
}
