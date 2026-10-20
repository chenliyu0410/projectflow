import hashlib
import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, Node, NodeCollaborator, DocumentVersion
from test_report_lifecycle import setup, switch
from test_projects_nodes import login
from test_documents import upload as upload_doc
from test_attachments import upload as upload_attachment


@pytest.fixture()
def isolated(tmp_path, monkeypatch):
    root = tmp_path / "files"
    root.mkdir()
    monkeypatch.setenv("PF_ATTACHMENT_ROOT", str(root))
    monkeypatch.setenv("PF_AI_ROOT", str(tmp_path / "ai"))
    monkeypatch.setenv("PF_AI_FORMAL_INDEX", "true")
    monkeypatch.setenv("PF_ACCEPTANCE_MODE", "true")
    return root


def refresh(client):
    response = client.post("/ai/index/refresh")
    assert response.status_code == 200, response.text
    return response.json()


def ask(client, question="新人報到", **extra):
    return client.post("/ai/ask", json=dict(dataset="formal-v1", question=question, **extra))


def test_index_versions_attachments_and_source_preservation(client, engine, isolated):
    nid, pid, _ = setup(client, engine, "yu")
    doc = upload_doc(client, nid, "新人報到請到三樓人資部".encode()).json()
    attachment = upload_attachment(client, nid, "新人報到記得帶筆電".encode()).json()
    before = {p.name: p.read_bytes() for p in isolated.iterdir()}
    result = refresh(client)
    assert result["counts"]["indexed"] == 2
    assert {p.name: p.read_bytes() for p in isolated.iterdir()} == before
    response = ask(client, project_id=pid).json()
    assert response["synthetic"] is False
    assert response["gateway"]["classification"] == "confidential"
    assert {s["source_type"] for s in response["sources"]} == {"document", "attachment"}
    source = next(s for s in response["sources"] if s["source_type"] == "document")
    original = client.get(f"/ai/documents/{source['document_id']}?dataset=formal-v1").json()
    assert "三樓" in original["text"] and original["version"] == 1
    changed = client.post(f"/documents/{doc['document_id']}/text", json={"expected_version": 1, "content": "新人報到改到五樓"})
    assert changed.status_code == 201
    assert "三樓" not in ask(client).text
    assert client.get(f"/ai/documents/{source['document_id']}?dataset=formal-v1").status_code == 404
    status = client.get("/ai/status?dataset=formal-v1").json()
    assert status["index"]["counts"]["pending"] == 1
    refresh(client)
    assert "五樓" in ask(client).text and "三樓" not in ask(client).text
    assert client.delete(f"/attachments/{attachment['id']}").status_code == 200
    assert "記得帶筆電" not in ask(client).text
    with Session(engine) as db:
        db.get(Node, nid).deleted_at = datetime.now(timezone.utc)
        db.commit()
    assert not ask(client).json()["sources"]
    assert all((isolated / key).read_bytes() == data for key, data in before.items())


def test_live_scope_preview_revocation_and_company_isolation(client, engine, isolated):
    nid, pid, users = setup(client, engine, "yu")
    upload_doc(client, nid, "新人報到，權限限定的節點文件".encode())
    upload_doc(client, nid, "新人報到，公司可見專案文件".encode(), path=f"/projects/{pid}/documents")
    refresh(client)
    switch(client, "ming")
    initial = ask(client).json()
    assert len(initial["sources"]) == 2
    assert client.post("/ai/index/refresh").status_code == 403
    source = next(s for s in initial["sources"] if s["node_id"] == nid)
    with Session(engine) as db:
        db.get(Node, nid).owner_user_id = users["yu"]
        db.commit()
    response = ask(client).json()
    assert len(response["sources"]) == 1
    assert "權限限定" not in json.dumps(response, ensure_ascii=False)
    preview = client.post("/ai/preview", json={"dataset": "formal-v1", "question": "新人報到"}).json()
    assert len(preview["content"]["sources"]) == 1
    assert client.get(f"/ai/documents/{source['document_id']}?dataset=formal-v1").status_code == 404
    assert client.get("/ai/status?dataset=formal-v1").json()["index"]["counts"]["indexed"] == 1
    client.post("/auth/logout")
    login(client, "electronics", "elaine")
    assert client.get(f"/ai/documents/{source['document_id']}?dataset=formal-v1").status_code == 404
    assert not ask(client).json()["sources"]
    assert ask(client, project_id=pid).status_code == 404


def office_bytes(kind, content):
    value = io.BytesIO()
    with zipfile.ZipFile(value, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        if kind == "docx":
            archive.writestr("word/document.xml", f'<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>{content}</w:t></w:r></w:p></w:body></w:document>')
        else:
            archive.writestr("xl/workbook.xml", '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"/>')
            archive.writestr("xl/worksheets/sheet1.xml", f'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>{content}</t></is></c></row></sheetData></worksheet>')
    return value.getvalue()


def test_supported_parsers_skips_and_audit_no_body(client, engine, isolated):
    nid, _, _ = setup(client, engine, "yu")
    for kind in ("docx", "xlsx"):
        assert upload_doc(client, nid, office_bytes(kind, "新人報到教材"), f"教材.{kind}").status_code == 201
    assert upload_doc(client, nid, b"\x89PNG\r\n\x1a\nfake", "圖片.png").status_code == 201
    pdf = next((Path(__file__).resolve().parents[2] / "deploy/rag-starter/corpus").rglob("*.pdf"))
    assert upload_attachment(client, nid, pdf.read_bytes(), "人資教材.pdf").status_code == 201
    result = refresh(client)
    assert result["counts"]["indexed"] == 3 and result["counts"]["skipped"] == 1
    assert "不支援" in result["items"][-1]["reason"] or any("不支援" in i.get("reason", "") for i in result["items"])
    assert {"教材.docx", "教材.xlsx"} <= {s["title"] for s in ask(client).json()["sources"]}
    with Session(engine) as db:
        entries = db.scalars(select(AuditLog).where(AuditLog.action.like("ai.%"))).all()
        assert entries and "新人報到教材" not in json.dumps([a.payload for a in entries], ensure_ascii=False)


def test_default_off_and_failed_refresh_keeps_index(client, engine, isolated, monkeypatch):
    nid, _, _ = setup(client, engine, "yu")
    upload_doc(client, nid, "新人報到原文保留".encode())
    refresh(client)
    from app.ai import formal_index
    original = ask(client).json()["sources"]
    upload_doc(client, nid, "新增文件觸發發布".encode())
    monkeypatch.setattr(formal_index.os, "replace", lambda *args: (_ for _ in ()).throw(OSError("disk failure")))
    assert client.post("/ai/index/refresh").status_code == 503
    assert ask(client).json()["sources"] == original
    monkeypatch.delenv("PF_AI_FORMAL_INDEX")
    assert client.post("/ai/index/refresh").status_code == 404
    assert ask(client).status_code == 404
    monkeypatch.setenv("PF_AI_FORMAL_INDEX", "true")
    monkeypatch.setenv("PF_ACCEPTANCE_MODE", "false")
    assert ask(client).status_code == 404


def test_parser_limits_do_not_expand_untrusted_xml_or_zip():
    from app.ai.extractors import extract, ExtractionError
    bad = io.BytesIO()
    with zipfile.ZipFile(bad, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", b"x" * 13_000_000)
    with pytest.raises(ExtractionError):
        extract(bad.getvalue(), "bomb.docx")
    with pytest.raises(ExtractionError):
        extract(b"\xff", "bad.txt")
    with pytest.raises(ExtractionError):
        extract(office_bytes("docx", "&unknown;"), "bad.docx")


def test_hidden_hits_cannot_crowd_out_allowed_chunk_and_collaboration_is_live(client, engine, isolated):
    nid, pid, users = setup(client, engine, "yu")
    upload_doc(client, nid, ("一般事項。" * 500 + "消防集合請到大門口").encode(), "可見文件.txt")
    hidden = client.post(f"/projects/{pid}/nodes", json={"title": "管理者專用", "kind": "task", "owner_user_id": users["yu"]}).json()["id"]
    for number in range(7):
        upload_doc(client, hidden, "消防集合僅管理者可讀".encode(), f"消防集合{number}.txt")
    refresh(client)
    switch(client, "ming")
    visible = ask(client, "消防集合").json()["sources"]
    assert visible and all(s["node_id"] == nid for s in visible)
    assert any("大門口" in s["excerpt"] for s in visible)
    with Session(engine) as db:
        collaborator = NodeCollaborator(organization_id=db.get(Node, nid).organization_id,
                                       node_id=hidden, user_id=users["ming"], created_by=users["yu"])
        db.add(collaborator)
        db.commit()
        cid = collaborator.id
    assert any(s["node_id"] == hidden for s in ask(client, "消防集合").json()["sources"])
    with Session(engine) as db:
        db.delete(db.get(NodeCollaborator, cid))
        db.commit()
    assert all(s["node_id"] == nid for s in ask(client, "消防集合").json()["sources"])


def test_same_size_file_tamper_is_not_served_from_stale_index(client, engine, isolated):
    nid, _, _ = setup(client, engine, "yu")
    doc = upload_doc(client, nid, "新人報到資料A".encode()).json()
    refresh(client)
    source = ask(client).json()["sources"][0]
    with Session(engine) as db:
        key = db.scalar(select(DocumentVersion.storage_key).where(DocumentVersion.document_id == doc["document_id"]))
    original = (isolated / key).read_bytes()
    (isolated / key).write_bytes(original.replace(b"A", b"B"))
    assert not ask(client).json()["sources"]
    assert client.get(f"/ai/documents/{source['document_id']}?dataset=formal-v1").status_code == 404
    result = refresh(client)
    assert result["counts"]["skipped"] == 1 and "完整性" in result["items"][0]["reason"]


def test_excel_text_budget_stops_before_expanding_later_cells():
    from app.ai.extractors import extract, ExtractionError
    data = io.BytesIO()
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    with zipfile.ZipFile(data, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("xl/sharedStrings.xml", f'<sst xmlns="{ns}"><si><t>{"x" * 40_000}</t></si></sst>')
        cells = "".join(f'<c r="A{i}" t="s"><v>0</v></c>' for i in range(1, 8))
        # This bad reference must never be expanded: earlier cells exhaust the text budget.
        cells += '<c r="A8" t="s"><v>999</v></c>'
        archive.writestr("xl/worksheets/sheet1.xml", f'<worksheet xmlns="{ns}"><sheetData><row>{cells}</row></sheetData></worksheet>')
    with pytest.raises(ExtractionError, match="20萬字"):
        extract(data.getvalue(), "repeated-strings.xlsx")
