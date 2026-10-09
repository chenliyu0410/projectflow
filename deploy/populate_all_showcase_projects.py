"""All current catalog and company flows as real local showcase projects; no existing row edits."""
import argparse
from datetime import date,timedelta
import json,secrets,uuid
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.audit import log_audit
from app.auth import CurrentUser
from app.database import get_engine
from app.models import Organization,Project,Node,Gate,User,TaskNote,AuditLog,Workflow,NodeDependency
from app.schemas import ProjectFromWorkflowCreate,ReportCreate,NodeStatusUpdate,GateStatusUpdate
from app.security import hash_password
from app.showcase import catalog,enabled,identifier
from app.services.workflow_service import instantiate,read_payload,get_workflow
from app.services.report_service import submit_report
from app.routes.projects import update_node_status
from app.routes.workflows import update_gate
from populate_showcase_projects import actor,stable,TARGETS
from animate_showcase_projects import AtomicSession

TITLES={
 'wf-laptop':'輕薄筆電新機種開發', 'wf-event':'秋季品牌體驗展',
 'electronics-1':'連接器材料 ECN 變更', 'events-0':'新品發表會執行',
 'events-1':'秋季整合行銷活動', 'software-0':'客戶入口網站 v2.0 發佈',
 'software-1':'登入服務異常處理', 'construction-0':'辦公室裝修工程',
 'construction-1':'會議室設計變更與查驗', 'food-supplier':'主食罐原料供應商導入'}
TODAY=date(2026,10,9)


def mark(key):
 return str(uuid.uuid5(uuid.NAMESPACE_URL,'projectflow:all-showcase:v1:'+key))


def populate_all(db):
 if not enabled():raise RuntimeError('Local showcase mode required')
 output=[];titles=dict(TITLES)
 # Serialize repeat invocations, including project creation before marker insertion.
 for org in db.scalars(select(Organization).order_by(Organization.key).with_for_update()):pass
 entries=[dict(e) for e in catalog()]
 known={identifier('workflow:'+e['industry']+':'+e['key']) for e in entries}
 for workflow,org in db.execute(select(Workflow,Organization).join(Organization,Organization.id==Workflow.organization_id).order_by(Organization.key,Workflow.name)):
  if org.key in {'food','electronics','events','software','construction'} and workflow.id not in known:
   key='company-'+workflow.id
   entries.append({'key':key,'industry':org.key,'workflow_id':workflow.id})
   titles[key]=workflow.name
 for entry in entries:
  old=db.get(AuditLog,mark(entry['key']))
  if old:
   p=db.get(Project,old.payload['project_id'])
   if p is None or p.organization_id!=old.organization_id:raise RuntimeError('Recorded showcase project is missing')
   output.append({'catalog':entry['key'],'project_id':p.id,'existing':True});continue
  org=db.scalars(select(Organization).where(Organization.key==entry['industry'])).one()
  current=actor(db,org)
  existing=next((t for t in TARGETS if t[2]==entry['key']),None)
  if existing:
   p=db.scalars(select(Project).where(Project.organization_id==org.id,Project.title==existing[1])).one()
   if not db.get(AuditLog,stable(p.id,'applied')):raise RuntimeError('Existing project template provenance missing')
  else:
   title='【展示】'+titles[entry['key']]
   if db.scalar(select(Project.id).where(Project.organization_id==org.id,Project.title==title)):
    raise RuntimeError('Untracked project with showcase title exists; refusing duplicate')
   workflow=get_workflow(db,current,entry.get('workflow_id') or identifier('workflow:'+org.key+':'+entry['key']),lock=True)
   payload=read_payload(db,workflow)
   phases=sorted([n for n in payload.nodes if n.kind=='phase'],key=lambda n:(n.sort_order,n.id))
   if len(phases)<2:raise RuntimeError('Two phases required')
   start=TODAY-timedelta(days=phases[1].start_offset if phases[1].start_offset is not None else 7)
   result=instantiate(db,current,ProjectFromWorkflowCreate(workflow_id=workflow.id,title=title,start_date=start.isoformat()))
   p=db.get(Project,result['id'])
   nodes=list(db.scalars(select(Node).where(Node.project_id==p.id)))
   actual_phases=sorted([n for n in nodes if n.kind=='phase'],key=lambda n:(n.sort_order,n.id))
   first,second=actual_phases[:2]
   for index,phase in enumerate(actual_phases):
    phase_start=start+timedelta(days=index*7)
    if phase.start_date is None:phase.start_date=phase_start
    if phase.due_date is None:phase.due_date=phase_start+timedelta(days=6)
    for task in nodes:
     if task.parent_id==phase.id:
      if task.start_date is None:task.start_date=phase.start_date
      if task.due_date is None:task.due_date=phase.due_date
   db.flush()
   tasks=sorted([n for n in nodes if n.kind=='task' and n.parent_id==first.id],key=lambda n:(n.sort_order,n.id))
   pending=sorted([n for n in nodes if n.kind=='task' and n.parent_id==second.id],key=lambda n:(n.sort_order,n.id))
   if not tasks or not pending:raise RuntimeError('Phase task structure unsupported')
   for n in tasks:
    submit_report(db,current,n.id,ReportCreate(result='達成',summary=f'【展示情境】{titles[entry["key"]]}：已整理「{n.title}」的工作成果與檢核重點，管理者已確認，可進入下一階段。此為操作範例，非實際執行結論。',finished_on=min(n.due_date or TODAY,TODAY).isoformat(),self_approve=True))
   update_node_status(first.id,NodeStatusUpdate(status='done'),current,db)
   for gate in db.scalars(select(Gate).where(Gate.project_id==p.id,Gate.node_id==first.id)):
    update_gate(gate.id,GateStatusUpdate(status='approved'),current,db)
   update_node_status(second.id,NodeStatusUpdate(status='doing'),current,db)
   uid=str(uuid.uuid5(uuid.NAMESPACE_URL,'projectflow:showcase-worker:'+org.key))
   worker=db.get(User,uid)
   if worker is None:
    worker=User(id=uid,organization_id=org.id,username='_showcase_worker',display_name='展示執行者',role='member',password_hash=hash_password(secrets.token_urlsafe(48)))
    db.add(worker);db.flush();log_audit(db,current,'showcase.worker_create',payload={'user_id':uid})
   if worker.organization_id!=org.id or worker.username!='_showcase_worker' or worker.role!='member':raise RuntimeError('Worker identity mismatch')
   n=pending[0];n.owner_user_id=worker.id;db.flush()
   log_audit(db,current,'node.update',node_id=n.id,payload={'owner_user_id':worker.id,'reason':'展示情境執行與審核分工'})
   submit_report(db,CurrentUser(user=worker,organization=org,token=''),n.id,ReportCreate(result='達成',summary=f'【展示情境】「{n.title}」的初版成果已整理，等待管理者確認內容及下一步。可試用核准／退回，後續任務依原模板前置條件解鎖。',finished_on=TODAY.isoformat()))
   if not any(t.kind=='task' and t.status=='todo' for t in nodes):
    followup=Node(organization_id=org.id,project_id=p.id,kind='task',title='成果驗收與結案準備',owner_user_id=current.user.id,start_date=TODAY+timedelta(days=7),due_date=TODAY+timedelta(days=10),sort_order=max(t.sort_order for t in nodes)+5)
    db.add(followup);db.flush()
    db.add(NodeDependency(organization_id=org.id,project_id=p.id,predecessor_id=n.id,successor_id=followup.id,created_by=current.user.id))
    log_audit(db,current,'node.create',node_id=followup.id,payload={'project_id':p.id,'showcase':True,'reason':'展示待審通過後解鎖驗收'})
    db.flush()
   parallel=Node(organization_id=org.id,project_id=p.id,kind='task',title='專案協調與風險追蹤',owner_user_id=current.user.id,start_date=TODAY-timedelta(days=2),due_date=TODAY+timedelta(days=5),sort_order=max(n.sort_order for n in nodes)+10)
   db.add(parallel);db.flush()
   log_audit(db,current,'node.create',node_id=parallel.id,payload={'project_id':p.id,'showcase':True,'reason':'獨立平行協調工作，不繞過模板前置'})
   update_node_status(parallel.id,NodeStatusUpdate(status='doing'),current,db)
   for target,body in [(parallel,f'{titles[entry["key"]]}：正在確認跨階段交接、待決事項與時程風險；下次檢查重點是待審成果與後續資源安排。'),(n,'成果已送審，可由展示管理者進行核准或退回；尚未完成的前置會繼續保護後續工作。'),(second,'前階段已完成，現在進入本階段。日期、回報與Gate皆為可操作的展示資料。')]:
    note=TaskNote(organization_id=org.id,node_id=target.id,author_id=current.user.id,body='【展示情境】'+body);db.add(note);db.flush()
    log_audit(db,current,'note.create',node_id=target.id,payload={'note_id':note.id,'showcase':True})
  audit=log_audit(db,current,'showcase.catalog_project',payload={'catalog_key':entry['key'],'project_id':p.id,'reused':bool(existing),'fictional':True})
  audit.id=mark(entry['key']);db.flush()
  output.append({'catalog':entry['key'],'project_id':p.id,'reused':bool(existing)})
 return output


if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');args=parser.parse_args()
 with AtomicSession(get_engine()) as db:
  result=populate_all(db)
  if args.apply:Session.commit(db)
  else:db.rollback()
  print(json.dumps({'applied':args.apply,'projects':result},ensure_ascii=False))
