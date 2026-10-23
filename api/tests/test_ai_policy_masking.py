import json

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai import formal_index, masking, model, policy
from app.models import AuditLog, OperationsRecord, User
from test_ai_formal_index import isolated, refresh, upload_doc
from test_ai_index_auto_history import current_admin
from test_report_lifecycle import setup, switch

SECRET = "配方：鮪魚 62%、雞肉 18.5%，每公斤成本 NT$185，報價 12,000元，供應商青禾原料行，聯絡 02-2345-6789、buyer@example.com。"
RAW = ["62%", "18.5%", "NT$185", "12,000元", "青禾原料行", "02-2345-6789", "buyer@example.com"]


def test_masking_removes_sensitive_values_and_restores_them():
    masker = masking.Masker(["青禾原料行", "青禾"])
    masked = masker.mask(SECRET + "再次提到青禾原料行。")
    assert not [value for value in RAW if value in masked]
    assert masked.count("{{廠商_1}}") == 2  # Same value, same placeholder.
    assert masker.counts == {"廠商": 1, "Email": 1, "電話": 1, "金額": 2, "比例": 2}
    assert masking.unmask(masked, masker.mapping) == SECRET + "再次提到青禾原料行。"
    assert masking.unmask("{{未知_9}}", masker.mapping) == "{{未知_9}}"


@pytest.mark.parametrize("text, kept, hidden", [
    ("預算185萬，另有1.2億元與NT$30萬", [], ["185萬", "1.2億", "30萬"]),
    ("統編04595257、單號PO-0012345678、3 元件、3千人、2026-10-23、第2版", ["04595257", "PO-0012345678", "3 元件", "3千人", "2026-10-23", "第2版"], []),
    ("手機0912-345-678、市話(02) 2345 6789", [], ["0912-345-678", "2345 6789"]),
])
def test_masking_edge_cases(text, kept, hidden):
    masked = masking.Masker().mask(text)
    assert all(value in masked for value in kept), masked
    assert not [value for value in hidden if value in masked], masked

def test_policy_file_errors_fail_closed(tmp_path, monkeypatch):
    monkeypatch.setenv("PF_AI_ROOT", str(tmp_path))
    assert policy.load("food") == {"mode": "local_only", "company": "confidential", "overrides": {}}
    policy.path("food").parent.mkdir(parents=True)
    policy.path("food").write_text('{"mode":"cloud_allowed","company":"public","overrides":{"node:x":"secret"}}', encoding="utf-8")
    assert policy.load("food")["mode"] == "local_only" and policy.load("food")["company"] == "confidential"


def classify(client, scope, level, item_id=None):
    return client.put("/ai/classification", json=dict(scope=scope, id=item_id, level=level))


def add_partner(engine):
    with Session(engine) as db:
        user = db.scalar(select(User).where(User.username == "yu"))
        db.add(OperationsRecord(organization_id=user.organization_id, category="partners", code="P-RED", title="青禾原料行",
                                status="active", visibility="internal", fields=[], created_by=user.id, updated_by=user.id))
        db.commit()


def preview(client, pid, question="鮪魚配方成本"):
    response = client.post("/ai/preview", json=dict(dataset="formal-v1", question=question, project_id=pid))
    assert response.status_code == 200, response.text
    return response.json()


def test_inheritance_only_allows_stricter_overrides_and_is_audited(client, engine, isolated):
    nid, pid, _ = setup(client, engine, "yu")
    upload_doc(client, nid, "新人報到三樓".encode())
    tree = client.get("/ai/governance").json()
    assert tree["company"] == "confidential" and tree["mode"] == "local_only" and tree["cloud_provider"] is None
    assert classify(client, "company", "internal").status_code == 200
    assert classify(client, "project", "confidential", pid).status_code == 200
    node = next(n for n in client.get("/ai/governance").json()["nodes"] if n["id"] == nid)
    assert node["effective"] == "confidential" and node["inherited"] == "confidential" and node["own"] is None
    assert classify(client, "node", "public", nid).status_code == 422
    assert classify(client, "project", "inherit", pid).status_code == 200
    assert classify(client, "node", "confidential", nid).status_code == 200
    tree = client.get("/ai/governance").json()
    assert next(n for n in tree["nodes"] if n["id"] == nid)["own"] == "confidential"
    assert tree["recent"] and all(r["created_at"].endswith("+00:00") for r in tree["recent"])
    assert all(d["effective"] == "confidential" for d in tree["documents"] if d["node_id"] == nid)
    assert classify(client, "node", "internal", "missing").status_code == 404
    with Session(engine) as db:
        actions = [a.payload for a in db.scalars(select(AuditLog).where(AuditLog.action == "ai.classification.set"))]
    assert {"scope": "node", "from": None, "to": "confidential"} in actions
    switch(client, "ming")
    assert client.get("/ai/governance").status_code == 403
    assert classify(client, "company", "public").status_code == 403


def test_red_team_cloud_content_never_carries_raw_secrets(client, engine, isolated, monkeypatch):
    monkeypatch.setattr(model, "chat", lambda *args: pytest.fail("Preview must not call a model"))
    nid, pid, _ = setup(client, engine, "yu")
    add_partner(engine)
    upload_doc(client, nid, SECRET.encode())
    refresh(client)
    # Default policy is local only: nothing would leave.
    result = preview(client, pid)
    assert result["cloud_content"] is None and result["gateway"]["cloud"]["reason"] == "policy_local_only"
    classify(client, "company", "internal")
    policy.save("food", dict(policy.load("food"), mode="mixed"))
    result = preview(client, pid)
    cloud, local = result["gateway"]["cloud"], json.dumps(result["content"], ensure_ascii=False)
    assert cloud["eligible"] and cloud["masked"] and cloud["sent"] is False and cloud["provider"] is None
    assert cloud["masked_counts"]["廠商"] == 1 and cloud["masked_counts"]["金額"] == 2
    payload = json.dumps(result["cloud_content"], ensure_ascii=False)
    assert not [value for value in RAW if value in payload]
    assert all(value in local for value in RAW)  # The local model still gets real values.
    with Session(engine) as db:
        audits = json.dumps([a.payload for a in db.scalars(select(AuditLog).where(AuditLog.action.like("ai.%")))], ensure_ascii=False)
    assert not [value for value in RAW if value in audits] and "{{" not in audits
    # Confidential sources keep the whole request local, with no cloud content at all.
    classify(client, "node", "confidential", nid)
    result = preview(client, pid)
    assert result["cloud_content"] is None and result["gateway"]["cloud"]["reason"] == "confidential_local_only"
    assert result["gateway"]["classification"] == "confidential"


def test_changing_a_level_does_not_rebuild_the_index(client, engine, isolated):
    nid, pid, _ = setup(client, engine, "yu")
    upload_doc(client, nid, "新人報到三樓".encode())
    refresh(client)
    with Session(engine) as db:
        path = formal_index.index_path(db, current_admin(db))
    before = path.read_bytes()
    classify(client, "company", "internal")
    classify(client, "node", "confidential", nid)
    refresh(client)
    assert path.read_bytes() == before


def test_mask_preview_is_local_admin_only_and_hides_mapping(client, engine, isolated):
    setup(client, engine, "yu")
    add_partner(engine)
    result = client.post("/ai/mask-preview", json={"text": SECRET}).json()
    assert set(result) == {"masked", "counts"} and "青禾原料行" not in result["masked"]
    assert client.put("/ai/policy", json={"mode": "mixed"}).status_code == 403  # Test client is not a loopback host.
    switch(client, "ming")
    assert client.post("/ai/mask-preview", json={"text": SECRET}).status_code == 403


def test_governance_is_hidden_outside_isolated_mode(client, engine, isolated, monkeypatch):
    setup(client, engine, "yu")
    monkeypatch.setenv("PF_AI_FORMAL_INDEX", "false")
    assert client.get("/ai/governance").status_code == 404


def test_failed_audit_restores_the_policy_file(client, engine, isolated, monkeypatch):
    setup(client, engine, "yu")
    from app.routes import ai as routes
    def broken(*args, **kwargs):
        raise RuntimeError("audit unavailable")
    monkeypatch.setattr(routes, "log_audit", broken)
    with pytest.raises(RuntimeError):
        classify(client, "company", "public")
    assert policy.load("food")["company"] == "confidential"
