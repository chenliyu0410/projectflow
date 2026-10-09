import sys
from pathlib import Path
import pytest
from sqlalchemy import select,func
from sqlalchemy.orm import Session
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'deploy'))
from animate_showcase_projects import AtomicSession,animate
from populate_showcase_projects import populate,actor
from app.models import Organization,Project,Node,TaskReport,TaskNote,Gate,AuditLog
from app.showcase import provision
from app.services.record_policy import load_policy_context
from app.services.node_policy import node_out


def prepare(engine,monkeypatch):
    monkeypatch.setenv('PF_SHOWCASE_MODE','true')
    with Session(engine) as db:
        provision(db)
        for key,title,task in [('food','成貓主食罐正式版','殺菌條件驗證'),('electronics','連接器新產品正式版','端子耐久測試')]:
            org=db.scalar(select(Organization).where(Organization.key==key));user=actor(db,org).user
            p=Project(organization_id=org.id,title=title,owner_user_id=user.id);db.add(p);db.flush()
            parent=None
            if key=='food':
                phase=Node(organization_id=org.id,project_id=p.id,kind='phase',title='市場與配方',sort_order=10);db.add(phase);db.flush();parent=phase.id
            db.add(Node(organization_id=org.id,project_id=p.id,kind='task',title=task,parent_id=parent,sort_order=10))
        db.commit();populate(db);db.commit()


def test_real_status_reports_blocking_and_idempotency(engine,monkeypatch):
    prepare(engine,monkeypatch)
    with AtomicSession(engine) as db:
        result=animate(db);Session.commit(db)
        assert result[0]['statuses']=={'done':2,'doing':1,'review':1,'todo':13}
        assert result[1]['statuses']=={'done':3,'doing':1,'review':1,'todo':9}
        assert db.scalar(select(func.count()).select_from(TaskReport))==8
        assert db.scalar(select(func.count()).select_from(TaskNote))==4
        assert all(r.summary.startswith('【展示情境】') for r in db.scalars(select(TaskReport)))
        food=db.scalar(select(Organization).where(Organization.key=='food'));current=actor(db,food)
        n=db.scalar(select(Node).where(Node.title=='配方設計'));reports=list(db.scalars(select(TaskReport).where(TaskReport.node_id==n.id).order_by(TaskReport.version)))
        assert [(r.version,r.status) for r in reports]==[(1,'rejected'),(2,'submitted')]
        assert reports[0].reviewed_by!=reports[0].submitted_by
        target=db.scalar(select(Node).where(Node.title=='供應商評估'))
        projected=node_out(db,current,db.get(Project,target.project_id),target)
        assert projected['blocked']
        assert db.scalar(select(func.count()).select_from(Gate).where(Gate.status=='approved'))==1
        before=db.scalar(select(func.count()).select_from(AuditLog))
        assert all(x['already_applied'] for x in animate(db));Session.commit(db)
        assert db.scalar(select(func.count()).select_from(AuditLog))==before


def test_preview_and_later_failure_are_atomic(engine,monkeypatch):
    prepare(engine,monkeypatch)
    with AtomicSession(engine) as db:
        animate(db);db.rollback()
        assert not db.scalar(select(TaskReport.id))
        assert all(n.status=='todo' for n in db.scalars(select(Node)))
        electronic=db.scalar(select(Node).where(Node.title=='端子耐久測試'));electronic.status='doing';Session.commit(db)
        with pytest.raises(RuntimeError,match='user execution'):animate(db)
        db.rollback()
        assert not db.scalar(select(TaskReport.id))
        assert db.scalar(select(Node).where(Node.title=='配方設計')).status=='todo'


def test_mode_disabled(engine,monkeypatch):
    monkeypatch.delenv('PF_SHOWCASE_MODE',raising=False)
    with AtomicSession(engine) as db:
        with pytest.raises(RuntimeError,match='mode required'):animate(db)
