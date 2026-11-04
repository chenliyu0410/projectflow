"""Inbox folders (N8N batch 2): files dropped per project become project documents; spreadsheets update operations data.

Layout under PF_INBOX_ROOT (mounted from the host):
  <company key>/<project title>/<file>          -> project document, parsed (OCR when enabled), owner notified by mail
  <company key>/_營運資料匯入/<category>.xlsx      -> operations records added or updated by code
Processed files move to `已匯入/`, rejected ones to `失敗/` with a `.原因.txt` beside them. n8n only triggers the scan.
"""
import asyncio
import os
import re
import threading
import time
import uuid
from datetime import date, timedelta
from pathlib import Path

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select

from app.audit import log_audit
from app.auth import CurrentUser
from app.models import OperationsRecord, Organization, Project, User, now_utc
from app.services import document_store
from app.services.outbox_service import enqueue

IMPORT_DIR = '_營運資料匯入'
DONE, FAILED = '已匯入', '失敗'
SKIP = {DONE, FAILED}
# Files still being copied in are left for the next scan. ctime is checked too: inside the Linux container it
# changes on every write, while Windows copies keep the source file's old mtime.
SETTLE_SECONDS = 5
_scan_lock = threading.Lock()
CELL = re.compile(r'^([A-Z]+)(\d+)=(.*)$')
EXCEL_EPOCH = date(1899, 12, 30)


def inbox_root():
    return Path(os.environ.get('PF_INBOX_ROOT', '/var/lib/projectflow-inbox'))


def stamp():
    return now_utc().strftime('%Y%m%d-%H%M%S')


def move(path, folder, reason=None):
    target_dir = path.parent / folder
    target_dir.mkdir(exist_ok=True)
    target = target_dir / f'{stamp()}-{path.name}'
    os.replace(path, target)
    if reason:
        target.with_name(target.name + '.原因.txt').write_text(str(reason), encoding='utf-8')
    return target


def settled(path):
    info = path.stat()
    return time.time() - max(info.st_mtime, info.st_ctime) >= SETTLE_SECONDS


def ready_files(folder):
    return sorted(p for p in folder.iterdir()
                  if p.is_file() and not p.name.startswith(('.', '~$')) and not p.name.endswith('.原因.txt') and settled(p))


def ensure_layout(db):
    root = inbox_root()
    for key in db.scalars(select(Organization.key)):
        (root / key / IMPORT_DIR).mkdir(parents=True, exist_ok=True)


async def store_document(db, organization, project, owner, path):
    data = path.read_bytes()

    async def chunks():
        yield data

    current = CurrentUser(owner, organization, '')
    db.commit()  # document_store.save starts from a clean transaction
    saved = await document_store.save(db, current, None, chunks(), path.name, '收件匣自動匯入', project_id=project.id)
    try:
        from app.ai import ingest
        note = ingest.ingest(data, path.name).note()
    except Exception as exc:  # parsing problems never undo the stored document
        note = f'無法解析文字（{exc}）'
    enqueue(db, organization.id, 'inbox_document', owner.id, f'[專流] 收件匣新文件：{path.name}',
            f'「{path.name}」已存入專案「{project.title}」的文件。\n解析結果：{note}',
            f"inbox:{saved['document_id']}:{saved['version']}", line=f'[專流] 收件匣新文件：{path.name}\n專案：{project.title}')
    log_audit(db, current, 'inbox.document', payload={'project_id': project.id, 'filename': path.name, 'note': note[:200]})
    db.commit()
    return note


def excel_rows(data, filename):
    """Rows of the first sheet as lists of strings, via the hardened Office parser (zip-bomb and XXE checks)."""
    from app.ai.extractors import extract_document
    text, _ = extract_document(data, filename)
    rows, sheet = {}, 0
    for line in text.splitlines():
        if line.startswith('工作表：'):
            sheet += 1
            continue
        if sheet != 1:
            continue
        for part in line.split(' | '):
            match = CELL.match(part)
            if match:
                column, row, value = match.groups()
                rows.setdefault(int(row), {})[column] = value.strip()
    if not rows:
        return []
    columns = sorted({c for r in rows.values() for c in r}, key=lambda c: (len(c), c))
    return [[rows[n].get(c, '') for c in columns] for n in sorted(rows)]


DATE_LABEL = re.compile(r'日期|到期|期限|日$')


def as_date(label, value):
    """Excel stores dates as day serials; date-like columns are written back as YYYY-MM-DD.

    Only serials between 1954 and 2119 in a date-named column are converted, so counts such as「保存日數」stay numbers.
    """
    if DATE_LABEL.search(label) and re.fullmatch(r'\d{5}(\.0+)?', value) and 20000 <= int(float(value)) <= 80000:
        return (EXCEL_EPOCH + timedelta(days=int(float(value)))).isoformat()
    return value


def category_of(stem):
    from app.routes.operations import CATALOG
    keys = {'partners', 'resources', 'orders', 'work', 'formulas', 'batches'}
    if stem in keys:
        return stem
    # Catalog labels such as 「供應商 / 檢測」: any part of the label names the category.
    for company in CATALOG.values():
        for item in company:
            if item.get('key') in keys and stem in [x.strip() for x in item.get('label', '').split('/')]:
                return item['key']
    return None


def import_records(db, organization, path):
    from app.routes.operations import RecordUpdate, RecordWrite, save
    category = category_of(path.stem)
    if category is None:
        raise ValueError(f'不認得的分類「{path.stem}」，檔名請用分類名稱，例如 供應商.xlsx')
    admin = db.scalar(select(User).where(User.organization_id == organization.id, User.role == 'admin', User.status == 'active').order_by(User.created_at))
    if admin is None:
        raise ValueError('公司沒有啟用中的管理者，無法匯入')
    rows = excel_rows(path.read_bytes(), path.name)
    if len(rows) < 2:
        raise ValueError('沒有資料列（第一列是欄名）')
    header = rows[0]
    if '代碼' not in header or '名稱' not in header:
        raise ValueError('第一列必須有「代碼」與「名稱」欄')
    current = CurrentUser(admin, organization, '')
    created = updated = 0
    for number, values in enumerate(rows[1:], 2):
        record = dict(zip(header, values))
        if not record.get('代碼') or not record.get('名稱'):
            continue
        incoming = {label: as_date(label, value) for label, value in record.items() if label and label not in {'代碼', '名稱', '狀態'} and value}
        existing = db.scalar(select(OperationsRecord).where(OperationsRecord.organization_id == organization.id,
                                                            OperationsRecord.category == category, OperationsRecord.code == record['代碼'].strip().upper()))
        body = {'category': category, 'code': record['代碼'], 'title': record['名稱'],
                'fields': [{'label': k, 'value': v} for k, v in incoming.items()], 'status': record.get('狀態') or '啟用'}
        if existing is not None:
            # An update only changes what the sheet contains: other fields, the status and who may see the record stay.
            merged = {f['label']: f['value'] for f in existing.fields or []}
            merged.update(incoming)
            body.update(fields=[{'label': k, 'value': v} for k, v in merged.items()], visibility=existing.visibility,
                        status=record.get('狀態') or existing.status)
        try:
            if existing is None:
                save(db, current, RecordWrite(**body), source='import')
                created += 1
            else:
                save(db, current, RecordUpdate(**body, expected_revision=existing.revision), existing.id, source='import')
                updated += 1
        except (ValidationError, HTTPException) as exc:
            detail = exc.detail if isinstance(exc, HTTPException) else exc.errors()[0]['msg']
            done = f'（前面 {created + updated} 筆已匯入）' if created + updated else ''
            raise ValueError(f'第 {number} 列無法匯入：{detail}{done}') from None
    return created, updated, admin


def scan_sync(db):
    """Entry point for the API: one scan at a time, run off the event loop so OCR does not block other requests."""
    if not _scan_lock.acquire(blocking=False):
        return {'documents': 0, 'imports': 0, 'failed': 0, 'note': '上一輪掃描尚未結束'}
    try:
        return asyncio.run(scan(db))
    finally:
        _scan_lock.release()


async def scan(db):
    root = inbox_root()
    if not root.is_dir():
        return {'documents': 0, 'imports': 0, 'failed': 0, 'note': '收件匣資料夾不存在'}
    ensure_layout(db)
    summary = {'documents': 0, 'imports': 0, 'failed': 0}
    for organization in db.scalars(select(Organization)).all():
        company = root / organization.key
        if not company.is_dir():
            continue
        projects = {p.title: (p, owner) for p, owner in db.execute(
            select(Project, User).join(User, (User.organization_id == Project.organization_id) & (User.id == Project.owner_user_id))
            .where(Project.organization_id == organization.id)).all()}
        for folder in sorted(p for p in company.iterdir() if p.is_dir() and p.name not in SKIP):
            for path in ready_files(folder):
                try:
                    if folder.name == IMPORT_DIR:
                        created, updated, admin = import_records(db, organization, path)
                        enqueue(db, organization.id, 'inbox_import', admin.id, f'[專流] 營運資料匯入完成：{path.name}',
                                f'「{path.name}」新增 {created} 筆、更新 {updated} 筆營運資料。', f'import:{uuid.uuid4()}',
                                line=f'[專流] 營運資料匯入完成：{path.name}（新增 {created}、更新 {updated}）')
                        db.commit()
                        summary['imports'] += 1
                    elif folder.name in projects:
                        project, owner = projects[folder.name]
                        await store_document(db, organization, project, owner, path)
                        summary['documents'] += 1
                    else:
                        continue
                    move(path, DONE)
                except (ValueError, HTTPException) as exc:
                    db.rollback()
                    try:
                        move(path, FAILED, exc.detail if isinstance(exc, HTTPException) else exc)
                    except OSError:
                        pass  # left in place; the next scan reports it again
                    summary['failed'] += 1
                except OSError:
                    # A locked or vanished file only skips this file; the rest of the inbox is still processed.
                    db.rollback()
                    summary['failed'] += 1
    return summary
