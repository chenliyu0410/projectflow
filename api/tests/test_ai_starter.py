import hashlib
import json
import shutil
from contextlib import closing
from pathlib import Path

import pytest
from app.ai import store

PACK = Path(__file__).resolve().parents[2] / "deploy/rag-starter"


@pytest.fixture()
def starter_root(tmp_path, monkeypatch):
    monkeypatch.setenv("PF_AI_ROOT", str(tmp_path / "ai"))
    from app.ai.starter import import_starter
    import_starter(PACK, store.root())
    return store.root()


def login(client, username="yu", company="food"):
    client.base_url = "http://127.0.0.1"
    assert client.post("/auth/login", json={
        "organization_key": company, "username": username,
        "password": "demo-" + username,
    }).status_code == 200


def test_starter_import_preserves_old_dataset_and_is_idempotent(tmp_path, monkeypatch):
    from app.ai.starter import import_starter
    root = tmp_path / "ai"
    old = root / "dataset-v1"
    old.mkdir(parents=True)
    (old / "sentinel").write_bytes(b"keep old data")
    monkeypatch.setenv("PF_AI_ROOT", str(root))
    result = import_starter(PACK, root)
    assert result["documents"] == 24
    before = {p.name: p.read_bytes() for p in (root / "starter-v1").glob("*.sqlite")}
    assert import_starter(PACK, root)["already_imported"]
    assert before == {p.name: p.read_bytes() for p in (root / "starter-v1").glob("*.sqlite")}
    assert (old / "sentinel").read_bytes() == b"keep old data"
    with closing(store.connect("food", "starter-v1")) as db:
        assert db.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 23
        assert "請假" in db.execute("SELECT body FROM documents WHERE document_id='PDF-002'").fetchone()[0]
        with pytest.raises(Exception):
            db.execute("DELETE FROM documents")
    with closing(store.connect("electronics", "starter-v1")) as db:
        assert db.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 1


@pytest.mark.parametrize("change", ["hash", "escape", "role"])
def test_bad_import_never_publishes(tmp_path, change):
    from app.ai.starter import import_starter
    pack = tmp_path / "pack"
    shutil.copytree(PACK, pack)
    manifest = json.loads((pack / "manifest.json").read_text(encoding="utf-8"))
    if change == "escape":
        manifest["files"]["../outside.txt"] = "0" * 64
    else:
        path = pack / "machine/documents.jsonl"
        docs = [json.loads(s) for s in path.read_text(encoding="utf-8").splitlines()]
        docs[0]["allowed_roles"] = ["unknown"]
        path.write_text("".join(json.dumps(d, ensure_ascii=False) + "\n" for d in docs), encoding="utf-8")
        if change == "role":
            manifest["files"]["machine/documents.jsonl"] = hashlib.sha256(path.read_bytes()).hexdigest()
    (pack / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError):
        import_starter(pack, tmp_path / "out")
    assert not (tmp_path / "out/starter-v1").exists()


def test_starter_api_scope_history_and_complete_orders(client, starter_root):
    assert client.get("/ai/status?dataset=starter-v1").status_code == 401
    login(client)
    status = client.get("/ai/status?dataset=starter-v1").json()
    assert status["ready"] and status["as_of"] == "2026-10-20"
    assert status["counts"]["documents"] == 23 and not status["can_sql"]
    assert client.get("/ai/status?dataset=../x").status_code == 422
    response = client.post("/ai/ask", json={
        "dataset": "starter-v1", "question": "新人課程改期",
        "project_id": "TRAIN-10",
    }).json()
    ids = {s["document_id"] for s in response["sources"]}
    assert "MTG-003" in ids and "MTG-002" not in ids and "MAIL-004" not in ids
    historical = client.post("/ai/ask", json={
        "dataset": "starter-v1", "question": "新人課程原訂", "include_history": True,
        "project_id": "TRAIN-10",
    }).json()
    assert "MTG-002" in {s["document_id"] for s in historical["sources"]}
    assert client.get("/ai/documents/PDF-001?dataset=starter-v1").status_code == 200
    assert client.get("/ai/documents/MTG-002?dataset=starter-v1").status_code == 404
    old = client.get("/ai/documents/MTG-002?dataset=starter-v1&include_history=true")
    assert old.status_code == 200 and old.json()["is_current"] is False
    assert client.get("/ai/documents/MAIL-004?dataset=starter-v1").status_code == 404
    assert client.post("/ai/ask", json={"dataset": "starter-v1", "question": "x", "mode": "sql"}).status_code == 422
    orders = client.post("/ai/ask", json={"dataset": "starter-v1", "question": "列出工單", "mode": "work_orders"}).json()
    assert len(orders["sources"]) == 6 and "WO-006" in orders["answer"]
    assert "逾期1天" in orders["answer"]
    login(client, "ming")
    assert client.get("/ai/documents/PDF-006?dataset=starter-v1").status_code == 404
    status = client.get("/ai/status?dataset=starter-v1").json()
    assert status["counts"]["documents"] == 22
    assert "HR-BUDGET" not in {p["project_id"] for p in status["projects"]}
    assert client.post("/ai/ask", json={"dataset": "starter-v1", "question": "預算", "project_id": "HR-BUDGET"}).status_code == 404
    data = client.post("/ai/ask", json={"dataset": "starter-v1", "question": "預算草案金額"}).json()
    assert "PDF-006" not in {s["document_id"] for s in data["sources"]}
    assert "12,000" not in json.dumps(data, ensure_ascii=False)
    login(client, "elaine", "electronics")
    assert client.get("/ai/status?dataset=starter-v1").json()["counts"]["documents"] == 1
    assert client.get("/ai/documents/MAIL-004?dataset=starter-v1").status_code == 200
    assert client.get("/ai/documents/PDF-001?dataset=starter-v1").status_code == 404
    other = client.post("/ai/ask", json={"dataset": "starter-v1", "question": "新人課程"}).json()
    assert {s["document_id"] for s in other["sources"]} == {"MAIL-004"}


def test_starter_dataset_rejects_unknown_company_or_dataset(starter_root):
    with pytest.raises(FileNotFoundError):
        store.connect("../food", "starter-v1")
    with pytest.raises(ValueError):
        store.connect("food", "../starter-v1")


def test_simultaneous_identical_imports_publish_once(tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from app.ai.starter import import_starter
    barrier = Barrier(2)
    rename = Path.rename

    def synchronized_rename(path, target):
        if path.name == "starter-v1":
            barrier.wait(timeout=10)
        return rename(path, target)

    monkeypatch.setattr(Path, "rename", synchronized_rename)
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: import_starter(PACK, tmp_path / "ai"), range(2)))
    assert sum(bool(r.get("already_imported")) for r in results) == 1
    assert all(r["documents"] == 24 for r in results)
