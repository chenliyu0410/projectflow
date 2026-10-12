"""Every demo-pack account/project/visible parent, using an isolated database."""
import json
import os
from collections import Counter
from pathlib import Path
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session
from app.auth import CurrentUser
from app.database import Base
from app.demo_pack import import_pack
from app.models import Organization, Project, User
from app.routes.projects import create_node, get_project
from app.schemas import NodeCreate

def test_demo_pack_child_creation_matrix(tmp_path):
    pack = Path(__file__).resolve().parents[2] / 'deploy' / 'demo-data'
    manifest = json.loads((pack / 'manifest.json').read_text(encoding='utf-8'))
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'matrix.db'}")
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(text('CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)'))
        conn.execute(text('INSERT INTO alembic_version VALUES (:v)'), {'v': manifest['alembic_revision']})
    files = tmp_path / 'files'; files.mkdir()
    import_pack(engine, lambda name: (pack / name).read_bytes(), files)
    totals = Counter()
    matrix = []
    with Session(engine) as db:
        users = list(db.scalars(select(User)))
        projects = list(db.scalars(select(Project)))
        orgs = {o.id: o for o in db.scalars(select(Organization))}
        for user in users:
            current = CurrentUser(user=user, organization=orgs[user.organization_id], token='matrix')
            for project in projects:
                if project.organization_id != user.organization_id:
                    # Cross-company access is refused even when the account is an admin.
                    with pytest.raises(HTTPException) as denied:
                        get_project(project.id, current, db)
                    assert denied.value.status_code == 404
                    totals['cross_company_denied'] += 1
                    continue
                detail = get_project(project.id, current, db)
                row = dict(company=orgs[user.organization_id].key, account=user.username,
                           role=user.role, project=project.title, visible=len(detail['nodes']),
                           allowed=0, forbidden=0, closed=0, milestone=0)
                manager = user.role != 'readonly' and (user.role == 'admin' or user.id == project.owner_user_id)
                assert detail['capabilities']['create_node'] == manager
                for node in [None, *detail['nodes']]:
                    if node:
                        assert node['capabilities']['create_child'] == (manager and node['kind'] in {'project','phase','task'})
                    expected = 403 if not manager else 409 if node and (node['status'] in {'review','done','skipped'} or node['milestone']) else 201
                    category = 'forbidden' if expected == 403 else 'closed' if node and node['status'] in {'review','done','skipped'} else 'milestone' if node and node['milestone'] else 'allowed'
                    # create_node commits; contain every attempt in its own outer transaction.
                    with engine.connect() as conn:
                        tx = conn.begin()
                        conn.exec_driver_sql('BEGIN')
                        with Session(bind=conn, join_transaction_mode='create_savepoint') as attempt:
                            try:
                                created = create_node(project.id, NodeCreate(title='隔離新增驗證', kind='task', parent_id=node['id'] if node else None), current, attempt)
                                assert expected == 201, (row, node, expected)
                                assert created['parent_id'] == (node['id'] if node else None)
                            except HTTPException as error:
                                assert error.status_code == expected, (row, node, error.status_code, expected)
                        tx.rollback()
                    row[category] += 1
                    totals[category] += 1
                matrix.append(row)
    summary = dict(accounts=len(users), projects=len(projects), companies=len(orgs),
                   account_project_pairs=len(matrix), **dict(totals), matrix=matrix)
    if os.getenv('PF_MATRIX_REPORT'):
        Path(os.environ['PF_MATRIX_REPORT']).write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k != 'matrix'}))
    engine.dispose()
