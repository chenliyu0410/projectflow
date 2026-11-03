from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AIAnswer, AuditLog
from test_ai_formal_index import isolated, ask, refresh, upload_doc
from test_report_lifecycle import setup, switch
from test_projects_nodes import login


def test_answers_are_recorded_without_text_and_only_the_asker_can_rate(client, engine, isolated):
    nid, _, _ = setup(client, engine, "yu")
    upload_doc(client, nid, "新人報到請到三樓人資部".encode())
    refresh(client)
    answer = ask(client, "新人報到").json()
    answer_id = answer["answer_id"]
    assert answer["followup"] == "none" and answer["standalone_question"] is None
    with Session(engine) as db:
        row = db.get(AIAnswer, answer_id)
        assert (row.dataset, row.mode, row.kind, row.followup, row.rating) == ("formal-v1", "rag", answer["kind"], "none", None)
        assert row.source_ids == [s["document_id"] for s in answer["sources"]]
        stored = str([getattr(row, c.name) for c in AIAnswer.__table__.columns])
        assert "新人報到" not in stored and "三樓" not in stored
    preview = client.post("/ai/preview", json=dict(dataset="formal-v1", question="新人報到"))
    assert preview.status_code == 200 and "answer_id" not in preview.json()

    assert client.put(f"/ai/answers/{answer_id}/feedback", json={"rating": "great"}).status_code == 422
    assert client.put(f"/ai/answers/{answer_id}/feedback", json={"rating": "unhelpful"}).json() == {"ok": True, "rating": "unhelpful"}
    assert client.put(f"/ai/answers/{answer_id}/feedback", json={"rating": "helpful"}).json()["rating"] == "helpful"
    switch(client, "ming")
    assert client.put(f"/ai/answers/{answer_id}/feedback", json={"rating": "unhelpful"}).status_code == 404
    assert client.get("/ai/feedback/summary").status_code == 403
    client.post("/auth/logout")
    login(client, "electronics", "elaine")
    assert client.put(f"/ai/answers/{answer_id}/feedback", json={"rating": "unhelpful"}).status_code == 404
    switch(client, "yu")
    assert client.get("/ai/feedback/summary").json() == {"days": 30, "helpful": 1, "unhelpful": 0, "total_answers": 1}
    with Session(engine) as db:
        assert db.get(AIAnswer, answer_id).rating == "helpful"
        audits = [a.payload for a in db.scalars(select(AuditLog).where(AuditLog.action == "ai.feedback"))]
    assert len(audits) == 2 and all(set(p) == {"answer_id", "rating"} for p in audits)
