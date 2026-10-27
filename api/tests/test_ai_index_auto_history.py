from contextlib import closing
from datetime import datetime, timezone
import threading

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.models import Node, Organization, User
from test_ai_formal_index import isolated, ask, refresh, upload_doc, upload_attachment
from test_report_lifecycle import setup, switch
from test_projects_nodes import login


def current_admin(db):
    user = db.scalar(select(User).where(User.username == "yu"))
    return CurrentUser(user, db.get(Organization, user.organization_id), "")


def test_history_is_opt_in_and_live_permissions_apply(client, engine, isolated):
    nid, _, users = setup(client, engine, "yu")
    doc = upload_doc(client, nid, "新人報到三樓（原訂）".encode()).json()
    assert client.post(f"/documents/{doc['document_id']}/text",
                       json={"expected_version": 1, "content": "新人報到五樓（現行）"}).status_code == 201
    refresh(client)
    assert {s["version"] for s in ask(client).json()["sources"]} == {2}
    history = ask(client, include_history=True)
    assert history.status_code == 200, history.text
    sources = history.json()["sources"]
    assert {s["version"] for s in sources} == {1, 2}
    old = next(s for s in sources if s["version"] == 1)
    assert old["is_current"] is False
    url = f"/ai/documents/{old['document_id']}?dataset=formal-v1"
    assert client.get(url).status_code == 404
    assert client.get(url + "&include_history=true").json()["is_current"] is False
    preview = client.post("/ai/preview", json={"dataset": "formal-v1", "question": "新人報到", "include_history": True}).json()
    assert any("歷史版本" in s["text"] and "第1版" in s["text"] for s in preview["content"]["sources"])
    switch(client, "ming")
    with Session(engine) as db:
        db.get(Node, nid).owner_user_id = users["yu"]
        db.commit()
    assert not ask(client, include_history=True).json()["sources"]
    assert client.get(url + "&include_history=true").status_code == 404
    assert client.get("/ai/status?dataset=formal-v1").json()["index"]["items"] == []
    client.post("/auth/logout")
    login(client, "electronics", "elaine")
    assert client.get(url + "&include_history=true").status_code == 404


def test_auto_tick_tracks_changes_noop_and_deleted_sources(client, engine, isolated, monkeypatch):
    from app.ai import index_worker, formal_index
    monkeypatch.setenv("PF_AI_INDEX_AUTO_UPDATE", "true")
    nid, _, _ = setup(client, engine, "yu")
    doc = upload_doc(client, nid, "新人報到三樓".encode()).json()
    att = upload_attachment(client, nid, "新人報到攜帶筆電".encode()).json()
    index_worker.tick(engine)
    assert len(ask(client).json()["sources"]) == 2
    with Session(engine) as db:
        path = formal_index.index_path(db, current_admin(db))
    before = path.read_bytes()
    index_worker.tick(engine)
    assert path.read_bytes() == before
    assert client.post(f"/documents/{doc['document_id']}/text",
                       json={"expected_version": 1, "content": "新人報到五樓"}).status_code == 201
    # Reads never return obsolete content while waiting for the next background tick.
    assert "三樓" not in ask(client).text
    index_worker.tick(engine)
    assert "五樓" in ask(client).text
    assert {s["version"] for s in ask(client, include_history=True).json()["sources"]} == {1, 2}
    assert client.delete(f"/attachments/{att['id']}").status_code == 200
    with Session(engine) as db:
        db.get(Node, nid).deleted_at = datetime.now(timezone.utc)
        db.commit()
    index_worker.tick(engine)
    assert not ask(client, include_history=True).json()["sources"]
    with closing(formal_index.connect(path)) as index:
        assert index.execute("SELECT COUNT(*) FROM entries").fetchone()[0] == 0


def test_auto_failure_preserves_index_and_retries(client, engine, isolated, monkeypatch):
    from app.ai import index_worker, formal_index
    monkeypatch.setenv("PF_AI_INDEX_AUTO_UPDATE", "true")
    nid, _, _ = setup(client, engine, "yu")
    upload_doc(client, nid, "新人報到初稿".encode())
    index_worker.tick(engine)
    with Session(engine) as db:
        path = formal_index.index_path(db, current_admin(db))
    before = path.read_bytes()
    upload_doc(client, nid, "新人報到追加文件".encode())
    real_replace = formal_index.os.replace
    monkeypatch.setattr(formal_index.os, "replace", lambda *_: (_ for _ in ()).throw(OSError("private path")))
    index_worker.tick(engine)
    assert path.read_bytes() == before
    state = client.get("/ai/status?dataset=formal-v1").json()["index"]["automatic"]
    assert state["last_error"] and "private path" not in state["last_error"]
    monkeypatch.setattr(formal_index.os, "replace", real_replace)
    index_worker.tick(engine)
    assert len(ask(client).json()["sources"]) == 2
    assert not client.get("/ai/status?dataset=formal-v1").json()["index"]["automatic"]["last_error"]


def test_worker_requires_all_isolation_gates_and_stops(engine, isolated, monkeypatch):
    from app.ai import index_worker
    visited = threading.Event()
    monkeypatch.setattr(index_worker, "tick", lambda _engine: visited.set())
    with index_worker.running(engine):
        assert not visited.is_set()
    monkeypatch.setenv("PF_AI_INDEX_AUTO_UPDATE", "true")
    with index_worker.running(engine) as worker:
        assert visited.wait(2)
        assert worker.is_alive()
    assert not worker.is_alive()
    visited.clear()
    monkeypatch.setenv("PF_ACCEPTANCE_MODE", "false")
    with index_worker.running(engine):
        assert not visited.is_set()
    monkeypatch.setenv("PF_ACCEPTANCE_MODE", "true")
    from types import SimpleNamespace
    with index_worker.running(SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))):
        assert not visited.is_set()


def test_temporary_file_read_failure_keeps_index_and_recovers_without_source_change(client, engine, isolated, monkeypatch):
    from pathlib import Path
    from app.ai import index_worker, formal_index
    monkeypatch.setenv("PF_AI_INDEX_AUTO_UPDATE", "true")
    nid, _, _ = setup(client, engine, "yu")
    upload_doc(client, nid, "新人報到原文件".encode())
    index_worker.tick(engine)
    with Session(engine) as db:
        path = formal_index.index_path(db, current_admin(db))
    before = path.read_bytes()
    upload_doc(client, nid, "新人報到新增文件".encode())
    original_open = Path.open

    def unavailable(file, *args, **kwargs):
        if file.parent == isolated and args and args[0] == "rb":
            raise PermissionError("temporary file lock")
        return original_open(file, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "open", unavailable)
        index_worker.tick(engine)
    assert path.read_bytes() == before
    index_worker.tick(engine)
    assert len(ask(client).json()["sources"]) == 2
