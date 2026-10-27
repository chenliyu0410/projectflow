from contextlib import closing
import os
import sqlite3
from unittest.mock import Mock

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai import formal_index, index_worker
from app.models import DocumentVersion, Node
from test_ai_formal_index import isolated, refresh, ask, upload_doc, upload_attachment
from test_ai_index_auto_history import current_admin
from test_report_lifecycle import setup, switch


def index_path(engine):
    with Session(engine) as db:
        return formal_index.index_path(db, current_admin(db))


def test_new_version_reuses_old_text_and_fts_without_reparsing(client, engine, isolated, monkeypatch):
    nid, _, _ = setup(client, engine, "yu")
    first = upload_doc(client, nid, "新人報到三樓".encode()).json()
    upload_doc(client, nid, "教育訓練帶筆電".encode())
    refresh(client)
    path = index_path(engine)
    with closing(formal_index.connect(path)) as db:
        old_terms = db.execute("SELECT rowid,document_id,words FROM search ORDER BY rowid").fetchall()
        old_terms = [tuple(row) for row in old_terms]
    parser = Mock(wraps=formal_index.extractors.extract_document)
    monkeypatch.setattr(formal_index.extractors, "extract_document", parser)
    assert client.post(f"/documents/{first['document_id']}/text", json={"expected_version": 1, "content": "新人報到五樓"}).status_code == 201
    result = refresh(client)
    assert parser.call_count == 1
    assert result["last_update"] == {"mode": "incremental", "processed": 1, "reused": 2, "removed": 0}
    with closing(formal_index.connect(path)) as db:
        terms = [tuple(row) for row in db.execute("SELECT rowid,document_id,words FROM search ORDER BY rowid")]
    assert terms[:len(old_terms)] == old_terms
    assert {s["version"] for s in ask(client).json()["sources"]} == {2}
    assert {s["version"] for s in ask(client, include_history=True).json()["sources"]} == {1, 2}
    before = path.read_bytes()
    parser.reset_mock()
    refresh(client)
    monkeypatch.setenv("PF_AI_INDEX_AUTO_UPDATE", "true")
    index_worker.tick(engine)
    assert not parser.called and path.read_bytes() == before
    switch(client, "ming")
    assert client.get("/ai/status?dataset=formal-v1").json()["index"]["last_update"] is None


def test_deletion_removes_only_its_index_rows_without_parsing(client, engine, isolated, monkeypatch):
    nid, _, _ = setup(client, engine, "yu")
    upload_doc(client, nid, "新人報到保留文件".encode())
    attachment = upload_attachment(client, nid, "新人報到刪除附件".encode()).json()
    refresh(client)
    parser = Mock(wraps=formal_index.extractors.extract_document)
    monkeypatch.setattr(formal_index.extractors, "extract_document", parser)
    assert client.delete(f"/attachments/{attachment['id']}").status_code == 200
    result = refresh(client)
    assert not parser.called
    assert result["last_update"] == {"mode": "incremental", "processed": 0, "reused": 1, "removed": 1}
    assert "刪除附件" not in ask(client).text
    with closing(formal_index.connect(index_path(engine))) as db:
        assert db.execute("SELECT COUNT(*) FROM chunks").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM search").fetchone()[0] == 1
    with Session(engine) as db:
        from datetime import datetime, timezone
        db.get(Node, nid).deleted_at = datetime.now(timezone.utc)
        db.commit()
    result = refresh(client)
    assert result["last_update"]["removed"] == 1
    assert not parser.called


def test_changed_file_state_and_unsupported_sources_are_handled_individually(client, engine, isolated, monkeypatch):
    nid, _, _ = setup(client, engine, "yu")
    doc = upload_doc(client, nid, "新人報到原始文字".encode()).json()
    assert upload_doc(client, nid, b"\x89PNG\r\n\x1a\nfake", name="image.png").status_code == 201
    refresh(client)
    parser = Mock(wraps=formal_index.extractors.extract_document)
    monkeypatch.setattr(formal_index.extractors, "extract_document", parser)
    with Session(engine) as db:
        key = db.scalar(select(DocumentVersion.storage_key).where(DocumentVersion.document_id == doc["document_id"]))
    file = isolated / key
    state = file.stat()
    os.utime(file, ns=(state.st_atime_ns, state.st_mtime_ns + 1_000_000_000))
    result = refresh(client)
    assert parser.call_count == 1
    assert result["last_update"]["processed"] == 1 and result["last_update"]["reused"] == 1
    assert result["counts"]["skipped"] == 1
    parser.reset_mock()
    file.write_bytes(b"x" * file.stat().st_size)
    result = refresh(client)
    assert not parser.called  # Digest failure is rejected before parsing.
    assert result["counts"]["skipped"] == 2
    assert not ask(client).json()["sources"]


def test_failed_incremental_build_preserves_old_index_and_retries(client, engine, isolated, monkeypatch):
    nid, _, _ = setup(client, engine, "yu")
    upload_doc(client, nid, "新人報到保留".encode())
    refresh(client)
    path = index_path(engine)
    before = path.read_bytes()
    upload_doc(client, nid, "新人報到新增甲".encode())
    upload_doc(client, nid, "新人報到新增乙".encode())
    original = formal_index.extractors.extract_document
    calls = []

    def fail_second(data, filename):
        calls.append(data)
        if len(calls) == 2:
            raise OSError("transient")
        return original(data, filename)

    monkeypatch.setattr(formal_index.extractors, "extract_document", fail_second)
    assert client.post("/ai/index/refresh").status_code == 503
    assert path.read_bytes() == before
    assert not list(path.parent.glob(".index-*.sqlite"))
    parser = Mock(wraps=original)
    monkeypatch.setattr(formal_index.extractors, "extract_document", parser)
    result = refresh(client)
    assert parser.call_count == 2 and result["last_update"]["reused"] == 1


def test_legacy_index_is_built_once_without_modifying_sources(client, engine, isolated, monkeypatch):
    nid, _, _ = setup(client, engine, "yu")
    upload_doc(client, nid, "新人報到舊索引升級".encode())
    source_bytes = {p.name: p.read_bytes() for p in isolated.iterdir()}
    path = index_path(engine)
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as db:
        db.executescript("""
            CREATE TABLE entries(source_id TEXT PRIMARY KEY, fingerprint TEXT, state TEXT, reason TEXT);
            CREATE TABLE chunks(document_id TEXT PRIMARY KEY, source_id TEXT, section INTEGER, body TEXT);
            CREATE VIRTUAL TABLE search USING fts5(document_id UNINDEXED, words);
            CREATE TABLE info(updated_at TEXT,snapshot_hash TEXT);
            INSERT INTO info VALUES ('old','old');
        """)
        db.commit()
    parser = Mock(wraps=formal_index.extractors.extract_document)
    monkeypatch.setattr(formal_index.extractors, "extract_document", parser)
    result = refresh(client)
    assert result["last_update"] == {"mode": "initial", "processed": 1, "reused": 0, "removed": 0}
    assert parser.call_count == 1
    refresh(client)
    assert parser.call_count == 1
    assert {p.name: p.read_bytes() for p in isolated.iterdir()} == source_bytes


def test_missing_source_file_is_skipped_without_blocking_other_sources(client, engine, isolated):
    nid, _, _ = setup(client, engine, "yu")
    missing = upload_doc(client, nid, "新人報到遺失檔案".encode()).json()
    with Session(engine) as db:
        key = db.scalar(select(DocumentVersion.storage_key).where(DocumentVersion.document_id == missing["document_id"]))
    file = isolated / key
    saved = file.read_bytes()
    file.unlink()
    upload_doc(client, nid, "新人報到保留檔案".encode())
    result = refresh(client)
    assert result["counts"] == {"indexed": 1, "pending": 0, "skipped": 1}
    assert any("不存在" in item["reason"] for item in result["items"])
    assert "保留檔案" in ask(client).text and "遺失檔案" not in ask(client).text
    file.write_bytes(saved)
    result = refresh(client)
    assert result["counts"]["indexed"] == 2 and result["last_update"]["processed"] == 1
