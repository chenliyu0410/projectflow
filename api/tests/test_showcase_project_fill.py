import importlib.util
from pathlib import Path
import pytest
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models import Organization, Project, Node, AuditLog, TaskNote
from app.showcase import provision

spec=importlib.util.spec_from_file_location('project_fill',Path(__file__).resolve().parents[2]/'deploy/populate_showcase_projects.py')
fill=importlib.util.module_from_spec(spec); spec.loader.exec_module(fill)


def prepare(engine, monkeypatch):
    monkeypatch.setenv('PF_SHOWCASE_MODE','true')
    with Session(engine) as db:
        provision(db)
        for company,title,_ in fill.TARGETS:
            org=db.scalar(select(Organization).where(Organization.key==company))
            user=fill.actor(db,org).user
            project=Project(organization_id=org.id,title=title,owner_user_id=user.id);db.add(project);db.flush()
            node=Node(organization_id=org.id,project_id=project.id,kind='phase' if company=='food' else 'task',title='市場與配方' if company=='food' else '端子耐久測試',status='doing',sort_order=10)
            db.add(node)
        food=db.scalar(select(Organization).where(Organization.key=='food'))
        p=Project(organization_id=food.id,title='waa',owner_user_id=fill.actor(db,food).user.id);db.add(p);db.flush()
        db.add(Node(organization_id=food.id,project_id=p.id,kind='project',title='waa'));db.commit()


def test_additive_apply_preserves_originals_dates_links_and_is_idempotent(engine,monkeypatch):
    prepare(engine,monkeypatch)
    with Session(engine) as db:
        old={n.id:{c.name:getattr(n,c.name) for c in Node.__table__.columns} for n in db.scalars(select(Node).where(Node.title!='waa'))}
        result=fill.populate(db);db.commit()
        assert [x.get('nodes_added') for x in result[:2]]==[20,18]
        for nid,values in old.items():
            assert {c.name:getattr(db.get(Node,nid),c.name) for c in Node.__table__.columns}==values
        assert not db.scalar(select(Project.id).where(Project.title=='waa'))
        nodes=list(db.scalars(select(Node).where(Node.id.not_in(old))))
        assert all(n.status=='todo' and n.start_date>=fill.START and n.due_date>=n.start_date for n in nodes)
        assert any(n.title=='連接器結構與端子設計' for n in nodes)
        count=db.scalar(select(func.count()).select_from(Node)); audits=db.scalar(select(func.count()).select_from(AuditLog))
        assert all(x['already_applied'] for x in fill.populate(db));db.commit()
        assert db.scalar(select(func.count()).select_from(Node))==count
        assert db.scalar(select(func.count()).select_from(AuditLog))==audits


def test_preview_rolls_back_everything(engine,monkeypatch):
    prepare(engine,monkeypatch)
    with Session(engine) as db:
        count=db.scalar(select(func.count()).select_from(Node))
        fill.populate(db);db.rollback()
        assert db.scalar(select(func.count()).select_from(Node))==count
        assert db.scalar(select(Project.id).where(Project.title=='waa'))


def test_unexpected_waa_content_aborts_whole_transaction(engine,monkeypatch):
    prepare(engine,monkeypatch)
    with Session(engine) as db:
        n=db.scalar(select(Node).where(Node.title=='waa'));n.status='doing';db.commit()
        count=db.scalar(select(func.count()).select_from(Node))
        with pytest.raises(RuntimeError,match='waa changed'):fill.populate(db)
        db.rollback()
        assert db.scalar(select(func.count()).select_from(Node))==count


def test_mode_off_rejects_without_writes(engine,monkeypatch):
    monkeypatch.delenv('PF_SHOWCASE_MODE',raising=False)
    with Session(engine) as db:
        with pytest.raises(RuntimeError,match='mode required'):fill.populate(db)
