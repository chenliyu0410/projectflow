import json
from uuid import uuid4
import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from app.database import Base
from app.demo_pack import EXCLUDED, export_pack, import_pack, tables
from app.models import AuditLog, Node, SessionToken, User
from app.security import verify_password
from test_attachments import upload
from test_purchase_lines import arrange as purchase
from test_report_lifecycle import setup


@pytest.fixture()
def files(tmp_path, monkeypatch):
    root = tmp_path / 'files'; root.mkdir()
    monkeypatch.setenv('PF_ATTACHMENT_ROOT', str(root))
    monkeypatch.setenv('PF_ATTACHMENT_QUOTA_BYTES', '1000000000')
    return root


def counts(engine):
    with engine.connect() as conn:
        return {table.name: conn.execute(select(func.count()).select_from(table)).scalar() for table in tables()}


def test_round_trip_restores_business_data_without_credentials(client, engine, files, tmp_path):
    nid, _, _ = setup(client, engine)
    assert upload(client, nid, '展示附件'.encode()).status_code == 201
    flour, sugar, order, body, path, saved = purchase(client)
    assert client.post(path + '/receipts', json={**body, 'quantity': '4', 'request_id': str(uuid4())}).status_code == 200
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(SessionToken)) and db.scalar(select(func.count()).select_from(AuditLog))
        assert db.scalar(select(func.count()).select_from(Node).where(Node.parent_id.is_not(None)))
    pack = export_pack(engine, files)
    manifest = json.loads(pack['manifest.json'])
    assert not any(name.startswith(f'tables/{excluded}.') for name in pack for excluded in EXCLUDED)
    users = json.loads(pack['tables/users.json'])
    assert users and all('password_hash' not in row for row in users)
    assert b'pbkdf2' not in b''.join(pack.values()) and len(manifest['files']) == 1
    target = create_engine(f"sqlite+pysqlite:///{tmp_path / 'restored.db'}")
    Base.metadata.create_all(target)
    restored_files = tmp_path / 'restored-files'; restored_files.mkdir()
    result = import_pack(target, pack.__getitem__, restored_files)
    assert result == counts(engine) == counts(target)
    assert [p.read_bytes() for p in restored_files.iterdir()] == ['展示附件'.encode()]
    with Session(target) as db:
        yu = db.scalars(select(User).where(User.username == 'yu')).first()
        assert verify_password('demo-yu', yu.password_hash)
        assert db.scalar(select(func.count()).select_from(SessionToken)) == 0
        assert db.scalar(select(func.count()).select_from(AuditLog)) == 0
    with Session(engine) as source, Session(target) as copy:
        assert [(n.id, n.parent_id, n.title, n.status) for n in source.scalars(select(Node).order_by(Node.id))] == \
            [(n.id, n.parent_id, n.title, n.status) for n in copy.scalars(select(Node).order_by(Node.id))]
    # Restoring twice, or into a seeded database, is refused instead of overwriting.
    with pytest.raises(RuntimeError, match='不是空的'):
        import_pack(target, pack.__getitem__, restored_files)


def test_learned_question_text_is_never_exported():
    # D90：候選問法存的是使用者打的原句與確認者 id；展示包會進 git，和 ai_answers 一樣不匯出
    assert {'ai_answers', 'ai_learned_phrases'} <= EXCLUDED
    assert 'ai_learned_phrases' not in {table.name for table in tables()}


def test_import_refuses_tampered_or_mismatched_pack(client, engine, files, tmp_path):
    pack = export_pack(engine, files)
    target = create_engine(f"sqlite+pysqlite:///{tmp_path / 'target.db'}")
    Base.metadata.create_all(target)
    tampered = {**pack, 'tables/projects.json': pack['tables/projects.json'].replace(b'"title"', b'"title" ', 1)}
    with pytest.raises(RuntimeError, match='內容與資料包清單不符'):
        import_pack(target, tampered.__getitem__, tmp_path)
    assert sum(counts(target).values()) == 0
    other = json.loads(pack['manifest.json']); other['alembic_revision'] = '20991231_9999'
    with pytest.raises(RuntimeError, match='資料庫版本須為'):
        import_pack(target, {**pack, 'manifest.json': json.dumps(other).encode()}.__getitem__, tmp_path)
