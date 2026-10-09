import sys
from pathlib import Path
import pytest
from sqlalchemy import select,func
from sqlalchemy.orm import Session
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'deploy'))
from populate_all_showcase_projects import populate_all,mark,TITLES
from animate_showcase_projects import AtomicSession,animate
from test_showcase_live_scenarios import prepare as base_prepare
from app.schemas import WorkflowWrite
from app.services.workflow_service import save
from app.models import Project,Node,AuditLog,TaskReport,TaskNote,Organization
from app.services.node_policy import node_out
from populate_showcase_projects import actor
from app.database import Base


def prepare(engine,monkeypatch):
 base_prepare(engine,monkeypatch)
 with Session(engine) as db:
  for key,name in [('food','食品新品開發'),('electronics','電子新品開發'),('food','食品新品開發 複本')]:
   org=db.scalar(select(Organization).where(Organization.key==key))
   save(db,actor(db,org),WorkflowWrite(name=name,nodes=[
    {'id':'p1','kind':'phase','title':'提案','sort_order':0,'gate_after':True},
    {'id':'t1','parent_id':'p1','kind':'task','title':'提案整理','sort_order':1},
    {'id':'p2','kind':'phase','title':'執行','sort_order':2,'gate_after':True},
    {'id':'t2','parent_id':'p2','kind':'task','title':'執行成果','sort_order':3}],dependencies=[]))


def snapshot(db):
 return {t.name:[dict(r) for r in db.execute(select(t)).mappings()] for t in Base.metadata.sorted_tables}


def test_every_catalog_has_active_real_project_and_preserves_existing(engine,monkeypatch):
 prepare(engine,monkeypatch)
 with AtomicSession(engine) as db:
  animate(db);Session.commit(db)
  before=snapshot(db)
  result=populate_all(db);Session.commit(db)
  assert len(result)==15 and sum(r.get('reused',False) for r in result)==2
  assert db.scalar(select(func.count()).select_from(Project))==15
  after=snapshot(db)
  for table,rows in before.items():
   assert all(r in after[table] for r in rows),table
  for row in result:
   if row['reused']:continue
   p=db.get(Project,row['project_id'])
   org=db.get(Organization,p.organization_id);current=actor(db,org)
   nodes=list(db.scalars(select(Node).where(Node.project_id==p.id)))
   assert {'done','doing','review','todo'}<={n.status for n in nodes if n.kind=='task'}
   assert any(node_out(db,current,p,n)['blocked'] for n in nodes if n.kind=='task')
   report=db.scalar(select(TaskReport).join(Node,TaskReport.node_id==Node.id).where(Node.project_id==p.id,TaskReport.status=='submitted'))
   assert report.submitted_by!=current.user.id and report.summary.startswith('【展示情境】')
   assert sum(n.kind=='phase' and n.status=='done' for n in nodes)==1
   assert sum(n.kind=='phase' and n.status=='doing' for n in nodes)==1
  assert all(r['existing'] for r in populate_all(db));Session.commit(db)
  assert snapshot(db)==after


def test_preview_and_late_collision_rollback_all(engine,monkeypatch):
 prepare(engine,monkeypatch)
 with AtomicSession(engine) as db:
  before=snapshot(db);populate_all(db);db.rollback();assert snapshot(db)==before
  org=db.scalar(select(Organization).where(Organization.key=='food'))
  db.add(Project(organization_id=org.id,owner_user_id=actor(db,org).user.id,title='【展示】'+TITLES['food-supplier']));Session.commit(db)
  before=snapshot(db)
  with pytest.raises(RuntimeError,match='Untracked project'):populate_all(db)
  db.rollback();assert snapshot(db)==before


def test_mode_disabled(engine,monkeypatch):
 monkeypatch.delenv('PF_SHOWCASE_MODE',raising=False)
 with AtomicSession(engine) as db:
  with pytest.raises(RuntimeError,match='mode required'):populate_all(db)
