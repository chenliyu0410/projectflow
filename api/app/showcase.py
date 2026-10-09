"""Explicit local showcase provisioning. Never resets existing business data."""
import json
import os
import secrets
import uuid
from functools import lru_cache
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select
from app.models import Organization, User, Workflow, WorkflowNode
from app.security import hash_password

COMPANIES = [
    {'key': 'food', 'name': '毛研食品', 'industry': '寵物食品製造'},
    {'key': 'electronics', 'name': '峰曜科技', 'industry': '電子產品製造'},
    {'key': 'events', 'name': '光點企劃', 'industry': '活動行銷'},
    {'key': 'software', 'name': '雲序軟體', 'industry': 'SaaS 軟體服務'},
    {'key': 'construction', 'name': '築衡工程', 'industry': '營建工程'},
]
USERNAME = '_showcase_demo'


def identifier(value):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, 'projectflow:showcase:v1:' + value))


def enabled():
    return os.environ.get('PF_SHOWCASE_MODE') == 'true'


def dedicated(user, organization):
    return user.username == USERNAME and user.id == identifier('user:' + organization.key)


def local_request(request):
    return request.url.hostname in {'127.0.0.1', 'localhost', '::1'}


def available(user, organization, request):
    return enabled() and local_request(request) and user.role == 'admin' and organization.key in {c['key'] for c in COMPANIES}


def check_switch_request(request):
    if not enabled() or not local_request(request):
        raise HTTPException(404, '找不到項目')
    origin = request.headers.get('origin')
    if origin and origin != str(request.base_url).rstrip('/'):
        raise HTTPException(403, '不允許此來源')
    if request.headers.get('sec-fetch-site') == 'cross-site':
        raise HTTPException(403, '不允許此來源')


@lru_cache
def catalog():
    return json.loads(Path(__file__).with_name('workflow_catalog.json').read_text(encoding='utf-8'))


def provision(db):
    if not enabled():
        raise RuntimeError('Enable PF_SHOWCASE_MODE explicitly before provisioning.')
    from app.auth import CurrentUser
    from app.audit import log_audit
    from app.schemas import WorkflowWrite
    from app.services.workflow_service import validate_graph
    added = {'organizations': 0, 'users': 0, 'workflows': 0}
    for company in COMPANIES:
        org = db.scalar(select(Organization).where(Organization.key == company['key']))
        if org is None:
            org = Organization(key=company['key'], name=company['name']); db.add(org); db.flush(); added['organizations'] += 1
        uid = identifier('user:' + org.key)
        user = db.get(User, uid)
        if user is None:
            if db.scalar(select(User).where(User.organization_id == org.id, User.username == USERNAME)):
                raise RuntimeError('Reserved showcase username already exists; no existing account modified.')
            user = User(id=uid, organization_id=org.id, username=USERNAME, display_name='展示管理者', role='admin', password_hash=hash_password(secrets.token_urlsafe(48)))
            db.add(user); db.flush(); added['users'] += 1
        if user.organization_id != org.id or not dedicated(user, org) or user.role != 'admin':
            raise RuntimeError('Showcase account identity mismatch; no account modified.')
        current = CurrentUser(user=user, organization=org, token='')
        for entry in catalog():
            if entry['industry'] != org.key:
                continue
            wid = identifier('workflow:' + org.key + ':' + entry['key'])
            existing = db.get(Workflow, wid)
            if existing:
                if existing.organization_id != org.id:
                    raise RuntimeError('Catalog identity mismatch')
                continue  # Stable ID survives edits; never overwrite customized templates.
            payload = WorkflowWrite(name=entry['name'], nodes=entry['nodes'], dependencies=entry['dependencies'])
            ordered = validate_graph(payload)
            ids = {n.id: identifier(wid + ':' + n.id) for n in ordered}
            content = {'p2c_version': 1, 'offsets': {ids[n.id]: {'start_offset': n.start_offset, 'due_offset': n.due_offset} for n in ordered}, 'dependencies': [{'predecessor_id': ids[e.predecessor_id], 'successor_id': ids[e.successor_id]} for e in payload.dependencies]}
            name = payload.name
            suffix = 1
            while db.scalar(select(Workflow.id).where(Workflow.organization_id == org.id, Workflow.name == name)):
                name = payload.name[:140] + f'（展示範本 {suffix}）'; suffix += 1
            wf = Workflow(id=wid, organization_id=org.id, name=name, content=content); db.add(wf); db.flush()
            for n in ordered:
                db.add(WorkflowNode(id=ids[n.id], organization_id=org.id, workflow_id=wid, parent_template_id=ids.get(n.parent_id), kind=n.kind, title=n.title, sort_order=n.sort_order, gate_after=n.gate_after)); db.flush()
            log_audit(db, current, 'workflow.create', payload={'workflow_id': wid, 'name': wf.name})
            added['workflows'] += 1
    db.flush()
    return added


if __name__ == '__main__':
    from sqlalchemy.orm import Session
    from app.database import get_engine
    with Session(get_engine()) as db:
        result = provision(db)
        db.commit()
        print(json.dumps(result))
