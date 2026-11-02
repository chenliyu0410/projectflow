from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, Document
from test_ai_formal_index import isolated, ask, refresh, upload_doc
from test_report_lifecycle import setup, switch
from test_projects_nodes import login


def knowledge(client, nid):
    response = client.get("/ai/knowledge", params={"node_id": nid})
    assert response.status_code == 200, response.text
    return response.json()


def original(client, source, history=False):
    return client.get(f"/ai/documents/{source['document_id']}", params={"dataset": "formal-v1", "include_history": history})


def test_switching_off_hides_document_from_answers_but_keeps_old_citations(client, engine, isolated):
    nid, _, _ = setup(client, engine, "yu")
    doc = upload_doc(client, nid, "G2關卡需要品保經理簽核".encode(), "G2檢查表.txt").json()["document_id"]
    assert knowledge(client, nid)["items"][0]["state"] == "pending"
    refresh(client)
    listing = knowledge(client, nid)
    assert listing["can_write"] is True
    assert {k: listing["items"][0][k] for k in ("document_id", "ai_enabled", "state", "indexed_version")} == \
        dict(document_id=doc, ai_enabled=True, state="indexed", indexed_version=1)
    source = ask(client, "G2關卡").json()["sources"][0]
    assert source["document_ref"] == {"kind": "document", "document_id": doc, "version": 1}
    assert source["project_title"] and source["node_title"] and source["page"] is None
    opened = original(client, source).json()
    assert opened["document_ref"] == source["document_ref"] and opened["project_title"] == source["project_title"]

    switched = client.put(f"/ai/knowledge/{doc}", json={"enabled": False})
    assert switched.status_code == 200 and switched.json()["state"] == "disabled"
    assert ask(client, "G2關卡").json()["sources"] == []
    refresh(client)
    # The passage stays indexed, so the earlier answer can still show where it came from.
    assert original(client, source).status_code == 200
    assert client.post(f"/documents/{doc}/text", json={"expected_version": 1, "content": "G2關卡需要廠長簽核"}).status_code == 201
    refresh(client)
    assert knowledge(client, nid)["items"][0]["ai_enabled"] is False
    assert ask(client, "G2關卡").json()["sources"] == []
    assert original(client, source, history=True).json()["is_current"] is False

    assert client.put(f"/ai/knowledge/{doc}", json={"enabled": True}).json()["state"] == "indexed"
    assert ask(client, "G2關卡").json()["sources"][0]["version"] == 2
    with Session(engine) as db:
        audits = [a.payload for a in db.scalars(select(AuditLog).where(AuditLog.action == "ai.knowledge"))]
    assert sorted(audits, key=lambda p: p["enabled"]) == [{"document_id": doc, "enabled": False}, {"document_id": doc, "enabled": True}]


def test_switch_needs_edit_rights_in_the_same_company(client, engine, isolated, monkeypatch):
    nid, pid, _ = setup(client, engine, "yu")
    doc = upload_doc(client, nid, "G2".encode()).json()["document_id"]
    assert client.get("/ai/knowledge").status_code == 422
    assert client.get("/ai/knowledge", params={"node_id": nid, "project_id": pid}).status_code == 422
    assert client.put(f"/ai/knowledge/{doc}", json={"enabled": False, "extra": 1}).status_code == 422
    switch(client, "lin")
    assert knowledge(client, nid)["can_write"] is False
    assert client.put(f"/ai/knowledge/{doc}", json={"enabled": False}).status_code == 403
    switch(client, "ming")
    assert client.put(f"/ai/knowledge/{doc}", json={"enabled": False}).status_code == 200
    client.post("/auth/logout")
    login(client, "electronics", "elaine")
    assert client.put(f"/ai/knowledge/{doc}", json={"enabled": True}).status_code == 404
    assert client.get("/ai/knowledge", params={"node_id": nid}).status_code == 404
    with Session(engine) as db:
        assert db.get(Document, doc).ai_enabled is False
    monkeypatch.delenv("PF_AI_FORMAL_INDEX")
    switch(client, "yu")
    assert client.get("/ai/knowledge", params={"node_id": nid}).status_code == 404
    assert client.put(f"/ai/knowledge/{doc}", json={"enabled": True}).status_code == 404


def test_project_documents_are_listed_by_project(client, engine, isolated):
    nid, pid, _ = setup(client, engine, "yu")
    doc = upload_doc(client, nid, "專案層級文件".encode(), path=f"/projects/{pid}/documents").json()["document_id"]
    upload_doc(client, nid, "節點文件".encode())
    items = client.get("/ai/knowledge", params={"project_id": pid}).json()["items"]
    assert [i["document_id"] for i in items] == [doc]
