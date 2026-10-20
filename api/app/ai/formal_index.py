"""Derived, isolated file index. Live operational ACLs are always authoritative."""
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import threading

from fastapi import HTTPException
from sqlalchemy import select

from app.ai import extractors, service, store
from app.models import Attachment, Document, DocumentVersion, Node, Project
from app.permissions import can_view_node, can_view_project
from app.services import attachment_store as files
from app.services.record_policy import load_policy_context

DATASET = "formal-v1"
_locks = {}
_locks_guard = threading.Lock()


def enabled():
    return os.environ.get("PF_AI_FORMAL_INDEX") == "true" and os.environ.get("PF_ACCEPTANCE_MODE") == "true"


def require_enabled(db):
    if not enabled() or db.bind.dialect.name != "sqlite":
        raise HTTPException(404, "隔離文件索引未啟用")


def index_path(db, current):
    require_enabled(db)
    # Avoid mixing indexes from different isolated databases, even with identical seed IDs.
    identity = str(db.bind.url) + "|" + current.organization.id
    key = hashlib.sha256(identity.encode()).hexdigest()
    return store.root() / DATASET / (key + ".sqlite")


def inventory(db, current, project_id=None, *, include_history=False):
    require_enabled(db)
    context = load_policy_context(db, current)
    projects = {p.id: p for p in db.scalars(select(Project).where(Project.organization_id == current.organization.id))
                if can_view_project(current, p)}
    if project_id and project_id not in projects:
        raise HTTPException(404, "找不到專案")
    nodes = {n.id: n for n in db.scalars(select(Node).where(Node.organization_id == current.organization.id))
             if n.project_id in projects and can_view_node(current, n, context=context)}
    descriptors = {}

    def add(kind, source_id, node_id, pid, version, filename, key, digest, size, is_current=True):
        if pid not in projects or (project_id and pid != project_id) or (node_id and node_id not in nodes):
            return
        value = dict(source_id=f"{kind}-{source_id}", source_type="document" if kind == "doc" else "attachment",
                     node_id=node_id, project_id=pid, version=version, title=filename,
                     storage_key=key, sha256=digest, size=size)
        value["fingerprint"] = hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
        value["is_current"] = is_current
        descriptors[value["source_id"]] = value

    rows = db.execute(select(Document, DocumentVersion).join(DocumentVersion, DocumentVersion.document_id == Document.id)
                      .where(Document.organization_id == current.organization.id,
                             DocumentVersion.organization_id == current.organization.id))
    for doc, version in rows:
        is_current = version.version == doc.current_version
        if include_history or is_current:
            add("doc", f"{doc.id}-v{version.version}", doc.node_id, doc.project_id, version.version, version.filename,
                version.storage_key, version.sha256, version.size_bytes, is_current)
    for row in db.scalars(select(Attachment).where(Attachment.organization_id == current.organization.id,
                         Attachment.state == "ready", Attachment.deleted_at.is_(None))):
        node = nodes.get(row.node_id)
        if node:
            add("att", row.id, row.node_id, node.project_id, 1, row.original_name,
                row.storage_key, row.sha256, row.size_bytes)
    return descriptors, [{"project_id": p.id, "title": p.title} for p in projects.values()]


def source_path(source):
    return files.storage_path(files.storage_root(), source["storage_key"])


def file_present(source, *, verify_digest=False):
    try:
        path = source_path(source)
        if not path.is_file() or path.stat().st_size != source["size"]:
            return False
        if verify_digest:
            with path.open("rb") as handle:
                data = handle.read(extractors.MAX_BYTES + 1)
            return len(data) <= extractors.MAX_BYTES and hashlib.sha256(data).hexdigest() == source["sha256"]
        return True
    except (OSError, HTTPException):
        return False


def connect(path):
    db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=5)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA query_only=ON")
    return db


def status(db, current):
    sources, projects = inventory(db, current, include_history=True)
    path = index_path(db, current)
    entries, updated = {}, None
    if path.exists():
        try:
            with closing(connect(path)) as index:
                entries = {r["source_id"]: dict(r) for r in index.execute("SELECT * FROM entries")}
                updated = index.execute("SELECT updated_at FROM info").fetchone()[0]
        except sqlite3.Error:
            raise HTTPException(503, "索引暫時無法讀取，請管理者更新") from None
    counts = dict(indexed=0, pending=0, skipped=0)
    items = []
    for sid, source in sources.items():
        entry = entries.get(sid)
        state, reason = "pending", "新增或已變更，請更新索引"
        if entry and entry["fingerprint"] == source["fingerprint"]:
            state, reason = entry["state"], entry["reason"]
            if state == "indexed" and not file_present(source):
                state, reason = "pending", "來源檔案暫時不可用"
        counts[state] += 1
        items.append(dict(source_id=sid, title=source["title"], source_type=source["source_type"],
                          version=source["version"], is_current=source["is_current"], state=state, reason=reason))
    from app.ai import index_worker
    return dict(counts=counts, items=items, updated_at=updated, projects=projects,
                can_refresh=current.user.role == "admin", automatic=index_worker.status(path))


def snapshot(sources):
    """Metadata plus file state; never stores raw content in the change detector."""
    values = []
    for sid, source in sorted(sources.items()):
        try:
            stat = source_path(source).stat()
            file_state = (stat.st_size, stat.st_mtime_ns)
        except (OSError, HTTPException):
            file_state = None
        values.append((sid, source["fingerprint"], source["is_current"], file_state))
    return hashlib.sha256(json.dumps(["history-v1", values]).encode()).hexdigest()


def refresh(db, current, *, only_if_changed=False):
    path = index_path(db, current)
    if current.user.role != "admin":
        raise HTTPException(403, "只有管理者可更新文件索引")
    with _locks_guard:
        lock = _locks.setdefault(str(path), threading.Lock())
    if not lock.acquire(blocking=False):
        raise HTTPException(409, "文件索引更新中，請稍後")
    temporary = None
    try:
        sources, _ = inventory(db, current, include_history=True)
        signature = snapshot(sources)
        if only_if_changed and path.exists():
            try:
                with closing(connect(path)) as existing:
                    if existing.execute("SELECT snapshot_hash FROM info").fetchone()[0] == signature:
                        return None
            except sqlite3.Error:
                pass  # Older/corrupt derived indexes are rebuilt; sources stay unchanged.
        if len(sources) > 500:
            raise HTTPException(422, "隔離版每公司最多500個來源版本，請另規劃批次索引")
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".index-", suffix=".sqlite", dir=path.parent)
        os.close(fd)
        with closing(sqlite3.connect(temporary)) as index:
            index.executescript("""
                CREATE TABLE entries(source_id TEXT PRIMARY KEY, fingerprint TEXT, state TEXT, reason TEXT);
                CREATE TABLE chunks(document_id TEXT PRIMARY KEY, source_id TEXT, section INTEGER, body TEXT);
                CREATE VIRTUAL TABLE search USING fts5(document_id UNINDEXED, words);
                CREATE TABLE info(updated_at TEXT, snapshot_hash TEXT);
            """)
            for sid, source in sources.items():
                state, reason = "indexed", ""
                try:
                    path_to_source = source_path(source)
                    if source["size"] > extractors.MAX_BYTES:
                        raise extractors.ExtractionError("檔案超過10MB")
                    with path_to_source.open("rb") as handle:
                        data = handle.read(extractors.MAX_BYTES + 1)
                    if len(data) != source["size"] or hashlib.sha256(data).hexdigest() != source["sha256"]:
                        raise extractors.ExtractionError("檔案完整性不符，請確認原始文件")
                    text = extractors.extract(data, source["title"])
                    for section, body in enumerate(extractors.chunks(text), 1):
                        cid = f"{sid}-c{section}"
                        index.execute("INSERT INTO chunks VALUES (?,?,?,?)", (cid, sid, section, body))
                        index.execute("INSERT INTO search VALUES (?,?)", (cid, " ".join(store.tokens(source["title"] + " " + body))))
                except HTTPException as exc:
                    raise OSError("Source storage unavailable") from exc
                except extractors.ExtractionError as exc:
                    state = "skipped"
                    reason = str(exc)
                index.execute("INSERT INTO entries VALUES (?,?,?,?)", (sid, source["fingerprint"], state, reason))
            index.execute("INSERT INTO info VALUES (?,?)", (datetime.now(timezone.utc).isoformat(), signature))
            index.commit()
            if index.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise OSError("Invalid index")
        os.replace(temporary, path)
        return status(db, current)
    except (OSError, sqlite3.Error):
        raise HTTPException(503, "索引更新失敗，原索引與來源檔案保留") from None
    finally:
        if temporary:
            Path(temporary).unlink(missing_ok=True)
        lock.release()


def valid_sources(index, sources):
    entries = {r["source_id"]: dict(r) for r in index.execute("SELECT * FROM entries WHERE state='indexed'")}
    return {sid: source for sid, source in sources.items()
            if sid in entries and entries[sid]["fingerprint"] == source["fingerprint"] and file_present(source)}


def as_document(row, source, current):
    metadata = dict(company_id=current.organization.key, classification="confidential",
                    version=source["version"], is_current=source["is_current"])
    label = "現行版本" if source["is_current"] else "歷史版本，請勿當作現行規定"
    row = dict(row, body=f"來源：{source['title']}／第{source['version']}版（{label}）\n{row['body']}")
    # The role assertion is produced only after checking current operational ACLs.
    return dict(row, title=source["title"], project_id=source["project_id"],
                node_id=source["node_id"], source_type=source["source_type"], version=source["version"],
                current=int(source["is_current"]), roles=json.dumps([current.user.role]), metadata=json.dumps(metadata))


def search(db, current, question, project_id=None, *, include_history=False):
    sources, _ = inventory(db, current, project_id, include_history=include_history)
    path = index_path(db, current)
    if not path.exists():
        return []
    words = list(dict.fromkeys(store.tokens(question)))[:60]
    if not words:
        return []
    match = " OR ".join('"' + word + '"' for word in words)
    try:
        with closing(connect(path)) as index:
            allowed = valid_sources(index, sources)
            if not allowed:
                return []
            # Apply ACLs before top-k; hidden hits cannot crowd out accessible documents.
            slots = ",".join("?" for _ in allowed)
            rows = index.execute(f"""SELECT c.* FROM search JOIN chunks c USING(document_id)
                WHERE search MATCH ? AND c.source_id IN ({slots})
                ORDER BY bm25(search),c.document_id""", (match, *allowed))
            verified, results = {}, []
            for row in rows:
                sid = row["source_id"]
                if sid not in verified:
                    verified[sid] = file_present(allowed[sid], verify_digest=True)
                if verified[sid]:
                    results.append(as_document(dict(row), allowed[sid], current))
                if len(results) == 6:
                    break
            return results
    except sqlite3.Error:
        raise HTTPException(503, "索引暫時無法讀取，請管理者更新") from None


def document(db, current, document_id, *, include_history=False):
    sources, _ = inventory(db, current, include_history=include_history)
    path = index_path(db, current)
    if path.exists():
        with closing(connect(path)) as index:
            row = index.execute("SELECT * FROM chunks WHERE document_id=?", (document_id,)).fetchone()
            if row:
                source = valid_sources(index, sources).get(row["source_id"])
                if source and file_present(source, verify_digest=True):
                    return dict(document_id=document_id, title=source["title"], text=row["body"],
                                version=source["version"], is_current=source["is_current"], section=row["section"])
    raise HTTPException(404, "找不到符合版本選項與權限的索引段落，請確認索引狀態")


def ask(db, current, payload, *, preview=False):
    if payload.mode != "rag" or payload.query_id:
        raise HTTPException(422, "正式文件索引僅支援文件問答")
    documents = search(db, current, payload.question, payload.project_id, include_history=payload.include_history)
    base = dict(as_of=datetime.now(timezone.utc).date().isoformat(), synthetic=False,
                project_id=payload.project_id, sources=[], analysis=None, warning=None)
    return service.answer_documents(current.organization.key, current.user.role, payload.question,
                                    documents, base, include_history=payload.include_history, preview=preview)
