"""Daily maintenance triggered by n8n (N8N batch 3): full backup with mail, and expiry reminders that open tasks."""
import os
import re
import zipfile
from datetime import date, timedelta
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select

from app.audit import log_audit
from app.auth import CurrentUser
from app.models import Node, OperationLink, OperationsRecord, Organization, Project, User, now_utc
from app.services.outbox_service import enqueue
from app.services.weekly_report_service import local_day

KEEP_BACKUPS = 7
EXPIRY_LABEL = re.compile('到期|有效期限')
EXPIRY_WINDOW = timedelta(days=30)


def backup_root():
    return Path(os.environ.get('PF_BACKUP_ROOT', '/var/lib/projectflow-backups'))


def admins(db, organization_id, roles=('admin',)):
    return list(db.scalars(select(User).where(User.organization_id == organization_id, User.role.in_(roles), User.status == 'active')))


def notify_admins(db, kind, subject, text, key):
    for organization in db.scalars(select(Organization)).all():
        for admin in admins(db, organization.id):
            enqueue(db, organization.id, kind, admin.id, subject, text, f'{key}:{admin.id}')


def backup(db):
    """Full logical backup (every table and column plus stored files); restore with `python -m app.demo_pack import`."""
    from app.demo_pack import export_pack
    from app.services.attachment_store import storage_root
    stamp = now_utc().strftime('%Y%m%d-%H%M%S')
    root = backup_root()
    target = root / f'projectflow-backup-{stamp}.zip'
    try:
        root.mkdir(parents=True, exist_ok=True)
        content = export_pack(db.get_bind(), storage_root(), full=True)
        partial = target.with_suffix('.zip.part')
        with zipfile.ZipFile(partial, 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, data in content.items():
                archive.writestr(name, data)
        os.replace(partial, target)
        old = sorted(root.glob('projectflow-backup-*.zip'))[:-KEEP_BACKUPS]
        for path in old:
            path.unlink()
    except Exception as exc:
        db.rollback()
        notify_admins(db, 'backup', '[專流] 每日備份失敗', f'{stamp} 的備份沒有完成：{type(exc).__name__}。請檢查備份資料夾空間與權限。',
                      f'backup-failed:{stamp}')
        db.commit()
        raise HTTPException(500, '備份失敗，已通知管理者') from None
    size = target.stat().st_size
    notify_admins(db, 'backup', '[專流] 每日備份完成', f'備份檔：{target.name}（{size / 1024 / 1024:.1f} MB），保留最近 {KEEP_BACKUPS} 份。',
                  f'backup:{stamp}')
    db.commit()
    return {'file': target.name, 'bytes': size, 'removed': [p.name for p in old]}


def parse_date(value):
    try:
        return date.fromisoformat(str(value).strip().replace('/', '-')[:10])
    except ValueError:
        return None


def expiring(record, today):
    for field in record.fields or []:
        if EXPIRY_LABEL.search(str(field.get('label', ''))):
            day = parse_date(field.get('value', ''))
            if day and day <= today + EXPIRY_WINDOW:
                return field['label'], day
    return None


def open_task(db, organization, admin, link, record, label, day):
    """Create「更新到期」under the linked node (or the project top level) unless the same task already exists."""
    from app.routes.projects import create_node
    from app.schemas import NodeCreate
    title = f'更新到期：{record.title}（{day.isoformat()}）'[:200]
    if db.scalar(select(Node.id).where(Node.organization_id == organization.id, Node.project_id == link.project_id,
                                      Node.parent_id.is_(None) if link.node_id is None else Node.parent_id == link.node_id,
                                      Node.title == title)):
        return False
    parent = db.get(Node, link.node_id) if link.node_id else None
    project = db.get(Project, link.project_id)
    owner = parent.owner_user_id if parent and parent.owner_user_id else project.owner_user_id
    payload = NodeCreate(kind='task', title=title, parent_id=link.node_id, owner_user_id=owner, department_id=None,
                         start_date=None, due_date=max(day - timedelta(days=7), local_day(now_utc())).isoformat())
    try:
        create_node(link.project_id, payload, CurrentUser(admin, organization, ''), db)
    except HTTPException:
        db.rollback()  # e.g. the linked node is already closed; the reminder mail still goes out
        return False
    return True


def expiry(db, now=None):
    today = local_day(now or now_utc())
    reminded = tasks = 0
    for organization in db.scalars(select(Organization)).all():
        managers = admins(db, organization.id, ('admin', 'project_owner'))
        admin = next((u for u in managers if u.role == 'admin'), None)
        for record in db.scalars(select(OperationsRecord).where(OperationsRecord.organization_id == organization.id)).all():
            found = expiring(record, today)
            if not found:
                continue
            label, day = found
            days = (day - today).days
            when = f'已過期 {-days} 天' if days < 0 else '今天到期' if days == 0 else f'{days} 天後到期'
            for user in managers:
                if enqueue(db, organization.id, 'expiry', user.id, f'[專流] 即將到期：{record.title}（{day.isoformat()}）',
                           f'營運資料「{record.code}｜{record.title}」的「{label}」是 {day.isoformat()}，{when}。請安排更新。',
                           f'expiry:{record.id}:{day.isoformat()}:{user.id}'):
                    reminded += 1
            db.commit()
            if admin is None:
                continue
            opened = sum(open_task(db, organization, admin, link, record, label, day)
                         for link in db.scalars(select(OperationLink).where(OperationLink.organization_id == organization.id,
                                                                            OperationLink.record_id == record.id)).all())
            if opened:
                log_audit(db, CurrentUser(admin, organization, ''), 'maintenance.expiry',
                          payload={'record_id': record.id, 'expires_on': day.isoformat(), 'tasks': opened})
                db.commit()
                tasks += opened
    return {'reminded': reminded, 'tasks': tasks}
