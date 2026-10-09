"""Audited fictional scenarios; preview by default, explicit --apply."""
import argparse
from datetime import date, timedelta
import json
import uuid
import secrets
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.audit import log_audit
from app.auth import CurrentUser
from app.security import hash_password
from app.database import get_engine
from app.models import Organization, Project, Node, Gate, TaskReport, TaskNote, AuditLog, User
from app.schemas import ReportCreate, ReportReview, NodeStatusUpdate, GateStatusUpdate
from app.services import report_service
from app.routes.projects import update_node_status
from app.routes.workflows import update_gate
from app.showcase import enabled, catalog
from populate_showcase_projects import actor, stable, TARGETS


class AtomicSession(Session):
    # Reuse business services while the outer maintenance transaction owns commit.
    def commit(self):
        self.flush()


def animate(db):
    if not enabled(): raise RuntimeError('Local showcase mode required')
    output=[]
    for company,title,key in TARGETS:
        org=db.scalar(select(Organization).where(Organization.key==company))
        project=db.scalars(select(Project).where(Project.organization_id==org.id,Project.title==title).with_for_update()).one()
        current=actor(db,org)
        marker=str(uuid.uuid5(uuid.NAMESPACE_URL,'projectflow:live-scenario:v1:'+project.id))
        if db.get(AuditLog,marker):
            output.append({'project':title,'already_applied':True});continue
        if db.get(AuditLog,stable(project.id,'applied')) is None:
            raise RuntimeError('Template application must be completed first')
        nodes=list(db.scalars(select(Node).where(Node.project_id==project.id)))
        ids=[n.id for n in nodes]
        if any(n.status!='todo' for n in nodes) or db.scalar(select(TaskReport.id).where(TaskReport.node_id.in_(ids)).limit(1)) or db.scalar(select(TaskNote.id).where(TaskNote.node_id.in_(ids)).limit(1)):
            raise RuntimeError('Project has user execution content; refusing to overwrite')
        gates=list(db.scalars(select(Gate).where(Gate.project_id==project.id)))
        if any(g.status not in {'pending','approved'} for g in gates): raise RuntimeError('Unexpected Gate state')
        def node(name):
            matches=[n for n in nodes if n.title==name]
            if len(matches)!=1: raise RuntimeError('Ambiguous/missing task '+name)
            return matches[0]
        entry=next(e for e in catalog() if e['key']==key)
        generated={stable(project.id,t['id']) for t in entry['nodes']}
        shift=timedelta(days=5 if company=='food' else 10)
        for n in nodes:
            if n.id in generated:
                before={'start_date':str(n.start_date),'due_date':str(n.due_date)}
                if n.start_date:n.start_date-=shift
                if n.due_date:n.due_date-=shift
                log_audit(db,current,'node.update',node_id=n.id,payload={'reason':'展示情境：排程示例','before':before,'after':{'start_date':str(n.start_date),'due_date':str(n.due_date)}})
        db.flush()
        worker_id=str(uuid.uuid5(uuid.NAMESPACE_URL,'projectflow:showcase-worker:'+org.key))
        worker=db.get(User,worker_id)
        if worker is None:
            worker=User(id=worker_id,organization_id=org.id,username='_showcase_worker',display_name='展示執行者',role='member',password_hash=hash_password(secrets.token_urlsafe(48)))
            db.add(worker);db.flush()
            log_audit(db,current,'showcase.worker_create',payload={'user_id':worker.id})
        if worker.organization_id!=org.id or worker.role!='member' or worker.username!='_showcase_worker':
            raise RuntimeError('Showcase worker identity mismatch')
        submitter=CurrentUser(user=worker,organization=org,token='')
        def report(name,summary,approve=False):
            n=node(name)
            if not approve and n.owner_user_id!=worker.id:
                previous=n.owner_user_id;n.owner_user_id=worker.id
                log_audit(db,current,'node.update',node_id=n.id,payload={'reason':'展示情境：執行者與審核者分工','owner_user_id':{'before':previous,'after':worker.id}})
                db.flush()
            return report_service.submit_report(db,current if approve else submitter,n.id,ReportCreate(result='達成',summary='【展示情境】'+summary,finished_on=min(n.due_date or date(2026,10,9),date(2026,10,9)).isoformat(),self_approve=approve))
        def note(n,body):
            record=TaskNote(organization_id=org.id,node_id=n.id,author_id=current.user.id,body='【展示情境】'+body)
            db.add(record);db.flush()
            log_audit(db,current,'note.create',node_id=n.id,payload={'note_id':record.id,'showcase':True})
        if company=='food':
            report('競品分析與產品定位','已整理三款同類主食罐的容量、價格與訴求，定位為成貓日常主食。此為操作示例，非實際調查結果。',True)
            report('營養標準比對','已建立營養規格檢核表，確認後續配方與送檢項目。本紀錄僅示範完成與審核流程。',True)
            first=report('配方設計','第一版配方提案已送審，示範配方資料待補情境。')
            report_service.review_report(db,current,first['id'],ReportReview(decision='rejected',comment='【展示情境】請補上原料替代方案與成本比較，再重新送審。'))
            report('配方設計','第二版已補原料替代與成本比較，等待管理者確認。可在工作區試用核准或退回。')
            active=node('殺菌條件驗證')
            note(node('配方設計'),'第1版退回補件 → 第2版已送審。供應商評估因前置尚未完成而被擋住。')
            body='正在整理殺菌試驗條件與採樣安排；下一步待確認試驗紀錄。這是進行中展示，不代表已有檢驗結論。'
        else:
            report('市場與競品分析','已整理連接器應用場景及對標規格，形成展示用產品定位。',True)
            report('Business Case 與目標成本','已整理開發投入、預估成本與量產目標，立案資料在展示情境中確認完成。',True)
            phase=node('市場立案')
            update_node_status(phase.id,NodeStatusUpdate(status='done'),current,db)
            gate=next(g for g in gates if g.node_id==phase.id)
            update_gate(gate.id,GateStatusUpdate(status='approved'),current,db)
            report('PRD 規格書','已整理尺寸、公差與電氣需求，作為後續設計依據；此為示範規格完成紀錄。',True)
            report('連接器外觀與介面設計','介面設計提案已送審，等待確認配接方式與防呆方向。法規盤點需待此任務完成。')
            active=node('端子耐久測試')
            note(node('PRD 規格書'),'立案Gate已核准，產品定義階段可開始；後續設計開發仍由下一道Gate保護。')
            body='正在準備插拔耐久測試條件與樣品清單，下一步彙整測試紀錄。此處沒有填入虛構實測數據。'
        update_node_status(node('市場與配方' if company=='food' else '產品定義').id,NodeStatusUpdate(status='doing'),current,db)
        update_node_status(active.id,NodeStatusUpdate(status='doing'),current,db)
        note(active,body)
        audit=log_audit(db,current,'showcase.animate',payload={'project_id':project.id,'fictional':True,'date':'2026-10-09'})
        audit.id=marker;db.flush()
        output.append({'project':title,'statuses':{s:sum(n.kind=='task' and n.status==s for n in nodes) for s in ['done','doing','review','todo']}})
    return output


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    with AtomicSession(get_engine()) as db:
        result=animate(db)
        if args.apply:Session.commit(db)
        else:db.rollback()
        print(json.dumps({'applied':args.apply,'result':result},ensure_ascii=False))
