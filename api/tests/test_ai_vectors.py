import json
import zlib
from contextlib import closing

import pytest
from sqlalchemy.orm import Session

from app.ai import formal_index, model, store, starter, vectors
from app.models import Node
from test_ai_formal_index import isolated, refresh, ask, upload_doc
from test_ai_index_auto_history import current_admin
from test_ai_starter import starter_root, login
from test_report_lifecycle import setup, switch

# Words of one concept share a dimension, so a paraphrase is "close" without sharing keywords.
CONCEPTS = [("門禁", "識別證", "通行卡"), ("預算", "經費", "薪酬"), ("報到", "到職", "第一天上班"), ("筆電", "電腦")]


class FakeEmbedder:
    def __init__(self):
        self.calls = []

    def __call__(self, company, texts):
        self.calls.append(list(texts))
        result = []
        for text in texts:
            values = [1.0 if any(word in text for word in group) else 0.0 for group in CONCEPTS]
            values += [0.0] * 64
            # A unique, weak per-text dimension keeps unrelated texts below the similarity floor.
            values[len(CONCEPTS) + zlib.crc32(text.encode()) % 64] = 0.3
            result.append(vectors.normalize(values))
        return result


@pytest.fixture()
def fake(monkeypatch):
    monkeypatch.setenv("PF_ACCEPTANCE_MODE", "true")
    monkeypatch.setenv("PF_AI_VECTOR_MODEL", "fake-embed")
    embedder = FakeEmbedder()
    monkeypatch.setattr(vectors, "embed", embedder)
    monkeypatch.setattr(vectors, "available", lambda company: True)
    monkeypatch.setattr(model, "chat", lambda *args: pytest.fail("No chat model in retrieval tests"))
    return embedder


def ids(db, question, role="admin", **extra):
    return [d["document_id"] for d in starter.search(db, "food", question, role, **extra)[0]]


def test_fuse_anchors_top_keyword_hits_then_adds_semantic_ones():
    keyword = ["k1", "k2", "k3", "k4", "k5", "k6"]
    fused = vectors.fuse(keyword, ["s1", "k6", "s2"])
    assert fused[:3] == ["k1", "k2", "k3"]
    # k6 is found by both rankings; semantic-only s1/s2 outrank weaker keyword-only k4/k5.
    assert fused[3:] == ["k6", "s1", "s2", "k4", "k5"]
    assert vectors.fuse([], ["x", "y"]) == ["x", "y"]


def test_vectors_stay_off_without_isolation_gate(monkeypatch):
    monkeypatch.setenv("PF_AI_VECTOR_MODEL", "fake-embed")
    monkeypatch.setenv("PF_ACCEPTANCE_MODE", "false")
    assert not vectors.enabled()


def test_paraphrase_finds_starter_document_that_keyword_search_misses(starter_root, fake):
    question = "識別證何時拿得到"
    with closing(store.connect("food", "starter-v1")) as db:
        assert "WO-002" not in [d["document_id"] for d in store.search(db, question, "admin")]
        documents, mode = starter.search(db, "food", question, "admin")
        assert mode == "hybrid" and "WO-002" in [d["document_id"] for d in documents]
        corpus_calls = len(fake.calls[0])
        assert corpus_calls == 23 and fake.calls[1] == [question]
        ids(db, question)
        assert [len(c) for c in fake.calls[2:]] == [1]  # Corpus vectors are reused, only the question is embedded.


def test_vectors_never_widen_role_company_or_version_scope(starter_root, fake):
    with closing(store.connect("food", "starter-v1")) as db:
        assert "PDF-006" in ids(db, "人事經費草案", "admin")
        assert "PDF-006" not in ids(db, "人事經費草案", "member")
        assert "MTG-002" not in ids(db, "新人課程", "admin")
        assert "MTG-002" in ids(db, "新人課程", "admin", include_history=True)
        assert not set(ids(db, "第一天上班", "admin", project_id="TRAIN-10")) - {d["document_id"] for d in db.execute(
            "SELECT document_id FROM documents WHERE project_id='TRAIN-10' OR project_id IS NULL")}
    with closing(store.connect("electronics", "starter-v1")) as db:
        found = [d["document_id"] for d in starter.search(db, "electronics", "課程時間", "admin")[0]]
        assert found and all(i == "MAIL-004" for i in found)


def test_vector_failure_falls_back_to_keyword(starter_root, fake, monkeypatch):
    monkeypatch.setattr(vectors, "embed", lambda *args: (_ for _ in ()).throw(OSError("model down")))
    with closing(store.connect("food", "starter-v1")) as db:
        documents, mode = starter.search(db, "food", "新人課程", "admin")
        assert mode == "keyword_fallback"
        assert [d["document_id"] for d in documents] == [d["document_id"] for d in store.search(db, "新人課程", "admin")]


def test_api_reports_retrieval_mode(client, starter_root, fake):
    model.save("food", dict(enabled=False, base_url="", model=""))
    login(client)
    result = client.post("/ai/ask", json=dict(dataset="starter-v1", question="識別證")).json()
    assert result["retrieval"] == "hybrid" and "WO-002" in {s["document_id"] for s in result["sources"]}
    assert client.get("/ai/status?dataset=starter-v1").json()["vectors"] == {"enabled": True, "model": "fake-embed"}
    assert client.get("/ai/status").json()["vectors"]["enabled"] is False


def index_rows(engine, sql):
    with Session(engine) as db:
        path = formal_index.index_path(db, current_admin(db))
    with closing(formal_index.connect(path)) as index:
        return index.execute(sql).fetchall()


def test_formal_index_embeds_only_changed_chunks_and_finds_paraphrase(client, engine, isolated, fake):
    nid, _, _ = setup(client, engine, "yu")
    first = upload_doc(client, nid, "門禁卡於報到當天由人資發放".encode()).json()
    upload_doc(client, nid, "教育訓練請攜帶公司筆電".encode())
    fake.calls.clear()
    result = refresh(client)
    chunks = index_rows(engine, "SELECT COUNT(*) FROM chunks")[0][0]
    assert result["last_update"]["vectors"] == chunks and result["last_update"]["vector_state"] == "complete"
    assert index_rows(engine, "SELECT COUNT(*) FROM vectors")[0][0] == chunks
    response = ask(client, question="識別證何時拿到").json()
    assert response["retrieval"] == "hybrid"
    assert any("門禁卡" in s["excerpt"] for s in response["sources"])
    fake.calls.clear()
    assert client.post(f"/documents/{first['document_id']}/text", json={"expected_version": 1, "content": "門禁卡改由行政發放"}).status_code == 201
    result = refresh(client)
    assert result["last_update"]["processed"] == 1 and len(fake.calls) == 1 and len(fake.calls[0]) == 1
    assert index_rows(engine, "SELECT COUNT(*) FROM vectors")[0][0] == index_rows(engine, "SELECT COUNT(*) FROM chunks")[0][0] == chunks + 1  # New version added; history kept.
    assert index_rows(engine, "SELECT COUNT(*) FROM vectors LEFT JOIN chunks USING(document_id) WHERE chunks.document_id IS NULL")[0][0] == 0


def test_formal_vectors_respect_live_permissions(client, engine, isolated, fake):
    nid, _, users = setup(client, engine, "yu")
    upload_doc(client, nid, "門禁卡於報到當天由人資發放".encode())
    refresh(client)
    switch(client, "ming")
    with Session(engine) as db:
        db.get(Node, nid).owner_user_id = users["yu"]
        db.commit()
    assert not ask(client, question="識別證何時拿到").json()["sources"]


def test_formal_vector_outage_keeps_keyword_index_and_backfills(client, engine, isolated, fake, monkeypatch):
    nid, _, _ = setup(client, engine, "yu")
    upload_doc(client, nid, "門禁卡於報到當天由人資發放".encode())
    working = vectors.embed
    monkeypatch.setattr(vectors, "embed", lambda *args: (_ for _ in ()).throw(OSError("model down")))
    result = refresh(client)
    assert result["counts"]["indexed"] == 1 and result["last_update"]["vector_state"] == "pending"
    assert ask(client, question="門禁卡").json()["sources"]  # Keyword search still works.
    assert client.post("/ai/index/refresh").status_code == 503  # Nothing else changed: no republish.
    monkeypatch.setattr(vectors, "embed", working)
    result = refresh(client)
    assert result["last_update"]["vectors"] == 1 and result["last_update"]["processed"] == 0
    assert refresh(client)["last_update"]["vectors"] == 1  # Already complete: no rebuild.
    monkeypatch.setenv("PF_AI_VECTOR_MODEL", "other-embed")
    fake.calls.clear()
    assert refresh(client)["last_update"]["vectors"] == 1 and len(fake.calls[0]) == 1


def test_vectors_unavailable_when_company_model_is_switched_off(starter_root, monkeypatch):
    monkeypatch.setenv("PF_ACCEPTANCE_MODE", "true")
    monkeypatch.setenv("PF_AI_VECTOR_MODEL", "fake-embed")
    monkeypatch.setattr(vectors, "embed", lambda *args: pytest.fail("Embedded with the model switched off"))
    model.save("food", dict(enabled=False, base_url="", model=""))
    assert not vectors.available("food")
    with closing(store.connect("food", "starter-v1")) as db:
        assert starter.search(db, "food", "新人課程", "admin")[1] == "keyword"
    model.save("food", dict(enabled=True, base_url="http://127.0.0.1:11434", model="test"))
    assert vectors.available("food")