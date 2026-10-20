import json
from contextlib import closing

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai import model, service, store
from app.models import AuditLog
from test_ai import pack, installed
from test_ai_starter import starter_root, login


def configure():
    model.save("food", dict(enabled=True, base_url="http://127.0.0.1:11434", model="test"))


def test_preview_is_scoped_and_never_calls_model(client, starter_root, monkeypatch):
    configure()
    monkeypatch.setattr(model, "chat", lambda *args: pytest.fail("Preview sent a model request"))
    payload = dict(dataset="starter-v1", question="新人課程", project_id="TRAIN-10")
    assert client.post("/ai/preview", json=payload).status_code == 401
    login(client)
    response = client.post("/ai/preview", json=payload)
    assert response.status_code == 200
    preview = response.json()
    assert preview["gateway"]["classification"] == "internal"
    assert preview["gateway"]["route"] == "local"
    assert preview["gateway"]["outcome"] == "not_sent"
    ids = {d["document_id"] for d in preview["content"]["sources"]}
    assert "MTG-003" in ids and not ids & {"MTG-002", "PDF-006", "MAIL-004"}
    historical = client.post("/ai/preview", json=dict(payload, include_history=True)).json()
    assert "MTG-002" in {d["document_id"] for d in historical["content"]["sources"]}
    assert client.post("/ai/preview", json=dict(payload, company_id="electronics")).status_code == 422
    assert client.post("/ai/preview", json=dict(payload, project_id="HF-TRAIN-10")).status_code == 404
    login(client, "ming")
    assert client.post("/ai/preview", json=dict(payload, project_id="HR-BUDGET")).status_code == 404
    response = client.post("/ai/preview", json=dict(payload, question="預算", project_id=None)).json()
    assert "PDF-006" not in json.dumps(response)
    assert client.post("/ai/preview", json=dict(payload, mode="sql")).status_code == 422
    login(client, "elaine", "electronics")
    other = client.post("/ai/preview", json=dict(payload, project_id=None)).json()
    assert {d["document_id"] for d in other["content"]["sources"]} == {"MAIL-004"}
    assert other["gateway"]["reason"] == "model_disabled"


def test_confidential_query_and_preview_record_only_safe_audit_metadata(client, starter_root, engine, monkeypatch):
    configure()
    login(client)
    captured = []

    def fake(config, system, prompt, schema):
        context = json.loads(prompt)
        captured.append(context)
        return {"answer": "請由人資確認預算草案。", "citations": ["PDF-006"]}

    monkeypatch.setattr(model, "chat", fake)
    payload = dict(dataset="starter-v1", question="預算草案金額", project_id="HR-BUDGET")
    preview = client.post("/ai/preview", json=payload).json()
    assert not captured
    result = client.post("/ai/ask", json=payload).json()
    assert captured == [preview["content"]]
    assert result["engine"] == "model"
    assert result["gateway"]["classification"] == "confidential"
    assert result["gateway"]["outcome"] == "completed"
    assert result["gateway"]["cloud_enabled"] is False
    with Session(engine) as db:
        audits = db.scalars(select(AuditLog).where(AuditLog.action.in_(["ai.preview", "ai.query"]))).all()
        assert {a.action for a in audits} == {"ai.preview", "ai.query"}
        for a in audits:
            assert a.payload["gateway"]["classification"] == "confidential"
            text = json.dumps(a.payload, ensure_ascii=False)
            assert all(value not in text for value in [payload["question"], "12,000", "127.0.0.1", "請由人資"])


@pytest.mark.parametrize("bad_config", [
    dict(enabled=True, base_url="https://8.8.8.8", model="test"),
    dict(enabled=True, base_url="http://127.0.0.1:11434", model="test:cloud"),
    dict(enabled=True, base_url="http://127.0.0.1:11434", model=""),
])
def test_tampered_settings_cannot_send_data(client, starter_root, monkeypatch, bad_config):
    configure()
    (store.root() / "settings/food.json").write_text(json.dumps(bad_config), encoding="utf-8")
    monkeypatch.setattr(model, "chat", lambda *args: pytest.fail("Blocked config reached model"))
    login(client)
    payload = dict(dataset="starter-v1", question="新人課程", project_id="TRAIN-10")
    result = client.post("/ai/ask", json=payload).json()
    assert result["kind"] == "retrieval" and result["sources"]
    assert result["gateway"]["route"] == "blocked"
    assert result["gateway"]["outcome"] == "not_sent"
    assert result["warning"]
    preview = client.post("/ai/preview", json=payload).json()
    assert preview["content"] is None


def test_gateway_fails_closed_for_missing_classification_and_foreign_sources(starter_root, monkeypatch):
    configure()
    from app.ai import gateway
    with closing(store.connect("food", "starter-v1")) as db:
        docs = store.search(db, "新人課程", "admin", "TRAIN-10")
    metadata = json.loads(docs[0]["metadata"])
    metadata.pop("classification")
    docs[0]["metadata"] = json.dumps(metadata)
    prepared = gateway.prepare("food", "admin", "rag", "新人課程", docs)
    assert prepared.info["classification"] == "confidential"
    assert prepared.info["classification_reason"] == "unclassified"
    for mutate in [
        {"metadata": json.dumps(dict(metadata, company_id="electronics"))},
        {"roles": '["member"]'},
        {"metadata": "not-json"},
    ]:
        with pytest.raises(PermissionError):
            gateway.prepare("food", "admin", "rag", "新人課程", [dict(docs[0], **mutate)])


def test_failed_model_reports_attempt_and_rules_and_no_sources_do_not_send(client, starter_root, monkeypatch):
    configure()
    login(client)
    monkeypatch.setattr(model, "chat", lambda *args: (_ for _ in ()).throw(TimeoutError()))
    result = client.post("/ai/ask", json=dict(dataset="starter-v1", question="新人課程")).json()
    assert result["kind"] == "retrieval" and result["gateway"]["outcome"] == "failed"
    monkeypatch.setattr(model, "chat", lambda *args: pytest.fail("Unexpected model request"))
    for payload, reason in [
        (dict(question="火星殖民"), "no_sources"),
        (dict(question="未完成", mode="work_orders"), "rules_only"),
    ]:
        for endpoint in ["ask", "preview"]:
            result = client.post("/ai/" + endpoint, json=dict(dataset="starter-v1", **payload)).json()
            assert result["gateway"]["route"] == "none"
            assert result["gateway"]["reason"] == reason
            assert result["gateway"]["outcome"] == "not_sent"
            if endpoint == "preview":
                assert result["content"] is None


def test_sql_gateway_preview_contains_catalog_not_business_rows(installed, monkeypatch):
    configure()
    monkeypatch.setattr(model, "chat", lambda *args: {"query_id": "q02"})
    with closing(store.connect("food")) as db:
        preview = service.ask(db, "food", "admin", "想看工作情況", "sql", preview=True)
        assert "queries" in preview["content"] and "sources" not in preview["content"]
        assert "rows" not in json.dumps(preview)
        result = service.ask(db, "food", "admin", "想看工作情況", "sql")
        assert result["kind"] == "query_suggestion" and result["gateway"]["outcome"] == "completed"
        deterministic = service.ask(db, "food", "admin", "各部門逾期未完成數", "sql")
        assert deterministic["gateway"]["reason"] == "rules_only"
        with pytest.raises(PermissionError):
            service.ask(db, "food", "member", "想看工作情況", "sql", preview=True)
