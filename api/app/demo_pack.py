"""De-identified demo data pack: export business tables to JSON and restore them into an empty database.

Login sessions, audit logs and notifications are left out, and password hashes are never written; restored
accounts get the local demo password `demo-<username>`. Run inside the API container (`python -m app.demo_pack`),
or pipe this file to `python -` there; `deploy/demo_data.py` does that from the host.
"""
import base64
import hashlib
import io
import json
import os
import sys
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path

from sqlalchemy import Boolean, Date, DateTime, func, inspect, select, text
from sqlalchemy.types import TypeDecorator

from app.database import Base, get_engine
import app.models  # noqa: F401  (registers every table)
from app.security import hash_password

FORMAT = 1
EXCLUDED = {'sessions', 'audit_logs', 'notifications'}
SCRUBBED = {'users': {'password_hash'}}
FILE_TABLES = {'attachments': 'storage_key', 'document_versions': 'storage_key'}
# A backup also carries the uploaded Word template files.
BACKUP_FILE_TABLES = {**FILE_TABLES, 'document_template_versions': 'storage_key'}


# Backups keep audit logs and notifications but never live login sessions.
BACKUP_EXCLUDED = {'sessions'}


def tables(excluded=EXCLUDED):
    return [table for table in Base.metadata.sorted_tables if table.name not in excluded]


def revision(conn):
    if not inspect(conn).has_table('alembic_version'):
        return None
    return conn.execute(text('SELECT version_num FROM alembic_version')).scalar()


def encode(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value


def decode(column, value):
    if value is None:
        return None
    kind = column.type.impl if isinstance(column.type, TypeDecorator) else column.type
    if isinstance(kind, DateTime):
        parsed = datetime.fromisoformat(value)
        return parsed if parsed.tzinfo or not kind.timezone else parsed.replace(tzinfo=timezone.utc)
    if isinstance(kind, Date):
        return date.fromisoformat(value)
    if isinstance(kind, Boolean):
        return bool(value)
    return value


def parents_first(table, rows):
    """Order rows of a self-referencing table so every parent is inserted before its children."""
    links = [(tuple(column.name for column in fk.columns), tuple(element.column.name for element in fk.elements))
        for fk in table.foreign_key_constraints if fk.referred_table is table]
    if not links:
        return rows
    seen = {remote: set() for _, remote in links}
    pending, ordered = list(rows), []
    while pending:
        ready = [row for row in pending if all(any(row[name] is None for name in local) or tuple(row[name] for name in local) in seen[remote]
            for local, remote in links)]
        if not ready:
            raise RuntimeError(f'{table.name} 含有無法排序的上下層關聯')
        for row in ready:
            for _, remote in links:
                seen[remote].add(tuple(row[name] for name in remote))
        placed = {id(row) for row in ready}
        ordered += ready
        pending = [row for row in pending if id(row) not in placed]
    return ordered

def export_pack(engine, files_root, full=False):
    """Return {relative path: bytes} for the pack; full=True is a backup (every table, password hashes kept)."""
    excluded, scrubbed, file_tables = (BACKUP_EXCLUDED, {}, BACKUP_FILE_TABLES) if full else (EXCLUDED, SCRUBBED, FILE_TABLES)
    out, manifest = {}, {'format': FORMAT, 'exported_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'excluded_tables': sorted(excluded), 'scrubbed_columns': {k: sorted(v) for k, v in scrubbed.items()},
        'tables': {}, 'files': {}}
    if full:
        manifest['full'] = True
    else:
        manifest['restored_password'] = 'demo-<username>'
    keys = set()
    with engine.connect() as conn:
        manifest['alembic_revision'] = revision(conn)
        for table in tables(excluded):
            order = [table.c[column.name] for column in table.primary_key.columns]
            rows = [{column.name: encode(value) for column, value in zip(table.columns, row)
                if column.name not in scrubbed.get(table.name, ())} for row in conn.execute(select(*table.columns).order_by(*order))]
            body = json.dumps(rows, ensure_ascii=False, indent=1, sort_keys=True).encode('utf-8')
            out[f'tables/{table.name}.json'] = body
            manifest['tables'][table.name] = {'rows': len(rows), 'sha256': hashlib.sha256(body).hexdigest()}
            if table.name in file_tables:
                keys.update(row[file_tables[table.name]] for row in rows if row.get(file_tables[table.name]))
    root = Path(files_root)
    for key in sorted(keys):
        path = root / key
        if path.is_file() and path.resolve().parent == root.resolve():
            data = path.read_bytes()
            out[f'files/{key}'] = data
            manifest['files'][key] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    out['manifest.json'] = json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True).encode('utf-8')
    return out


def import_pack(engine, read, files_root):
    """Restore a pack into an empty database at the same migration. `read(path)` returns the pack file bytes."""
    manifest = json.loads(read('manifest.json'))
    if manifest.get('format') != FORMAT:
        raise RuntimeError('不支援的資料包格式')
    root = Path(files_root)
    with engine.begin() as conn:
        if revision(conn) != manifest['alembic_revision']:
            raise RuntimeError(f"資料庫版本須為 {manifest['alembic_revision']}，請先執行 migration")
        # A pack only lists the tables that existed at its revision; tables added later stay untouched.
        packed = [table for table in tables(BACKUP_EXCLUDED) if table.name in manifest['tables']]
        for table in packed:
            if conn.execute(select(func.count()).select_from(table)).scalar():
                raise RuntimeError(f'目標資料庫不是空的（{table.name} 已有資料），拒絕覆蓋')
        for table in packed:
            body = read(f'tables/{table.name}.json')
            info = manifest['tables'][table.name]
            if hashlib.sha256(body).hexdigest() != info['sha256']:
                raise RuntimeError(f'{table.name} 內容與資料包清單不符')
            rows = [{column.name: decode(column, row.get(column.name)) for column in table.columns if column.name in row}
                for row in json.loads(body)]
            if table.name == 'users' and not manifest.get('full'):  # a backup keeps the real password hashes
                for row in rows:
                    row['password_hash'] = hash_password(f"demo-{row['username']}")
            if rows:
                conn.execute(table.insert(), parents_first(table, rows))
        for key, info in manifest['files'].items():
            data = read(f'files/{key}')
            if hashlib.sha256(data).hexdigest() != info['sha256']:
                raise RuntimeError(f'附件 {key} 內容與資料包清單不符')
            target = root / key
            if target.resolve().parent != root.resolve():
                raise RuntimeError('附件路徑無效')
            if target.exists() and target.read_bytes() != data:
                raise RuntimeError(f'附件 {key} 已存在且內容不同，拒絕覆蓋')
            target.write_bytes(data)
    return {name: info['rows'] for name, info in manifest['tables'].items()}


def main(argv):
    engine = get_engine()
    files_root = os.environ.get('PF_ATTACHMENT_ROOT', '/var/lib/projectflow-files')
    if argv[:1] == ['export']:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, data in sorted(export_pack(engine, files_root).items()):
                archive.writestr(name, data)
        sys.stdout.buffer.write(base64.b64encode(buffer.getvalue()))
    elif argv[:1] == ['import'] and len(argv) == 2:
        with zipfile.ZipFile(argv[1]) as archive:
            print(json.dumps(import_pack(engine, archive.read, files_root), ensure_ascii=False))
    else:
        raise SystemExit('usage: python -m app.demo_pack export | import PACK.zip')


if __name__ == '__main__':
    main(sys.argv[1:])
