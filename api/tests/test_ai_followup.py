import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai import followup, model
from app.models import AIAnswer, AuditLog
from test_ai_formal_index import isolated, ask, refresh, upload_doc
from test_report_lifecycle import setup


def documents(client, engine):
    nid, _, _ = setup(client, engine, "yu")
    upload_doc(client, nid, "G2關卡要具備試產報告與品保檢驗紀錄".encode(), "G2檢查表.txt")
    upload_doc(client, nid, "G2關卡由品保經理簽核".encode(), "G2簽核.txt")
    upload_doc(client, nid, "新人報到請到三樓人資部".encode(), "報到.txt")
    refresh(client)


def model_on(monkeypatch, reply):
    calls = []
    monkeypatch.setattr(model, "settings", lambda company: dict(enabled=True, base_url="http://127.0.0.1:11434", model="qwen"))

    def chat(config, system, prompt, schema, **options):
        calls.append(dict(system=system, prompt=json.loads(prompt), options=options))
        if system != followup.SYSTEM:
            raise ValueError("answer model unavailable in this test")
        if isinstance(reply, Exception):
            raise reply
        return reply
    monkeypatch.setattr(model, "chat", chat)
    return calls


def test_complete_questions_and_first_questions_are_not_rewritten(monkeypatch):
    calls = model_on(monkeypatch, {"standalone_question": "x", "needs_clarification": False})
    assert followup.resolve("food", "那需要誰簽核？", []) == ("那需要誰簽核？", "none")
    assert followup.resolve("food", "G2需要誰簽核？", ["G2要具備什麼？"]) == ("G2需要誰簽核？", "none")
    assert followup.resolve("food", "這個專案的進度？", ["G2要具備什麼？"]) == ("這個專案的進度？", "none")
    assert calls == []


def test_model_rewrites_follow_up_with_only_earlier_questions(client, engine, isolated, monkeypatch):
    documents(client, engine)
    calls = model_on(monkeypatch, {"standalone_question": "G2需要誰簽核？", "needs_clarification": False})
    response = ask(client, "那需要誰簽核？", history=["G2要具備什麼才能通過？"])
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["followup"] == "model" and body["standalone_question"] == "G2需要誰簽核？"
    assert any(s["title"] == "G2簽核.txt" for s in body["sources"])
    rewrite = calls[0]
    assert rewrite["prompt"] == {"history": ["G2要具備什麼才能通過？"], "question": "那需要誰簽核？"}
    assert rewrite["options"] == {"output_tokens": 500, "timeout": 15}
    with Session(engine) as db:
        assert db.get(AIAnswer, body["answer_id"]).followup == "model"
        payload = db.scalars(select(AuditLog).where(AuditLog.action == "ai.query")).all()[-1].payload
    assert payload["followup"] == "model" and "簽核" not in json.dumps(payload, ensure_ascii=False)


def test_clarification_and_model_failure(client, engine, isolated, monkeypatch):
    documents(client, engine)
    model_on(monkeypatch, {"standalone_question": "", "needs_clarification": True})
    body = ask(client, "那需要誰簽核？", history=["上次開會講了什麼？"]).json()
    assert body["kind"] == "clarification" and body["answer"] == followup.CLARIFY
    assert body["sources"] == [] and "answer_id" not in body
    model_on(monkeypatch, TimeoutError("slow"))
    body = ask(client, "那需要誰簽核？", history=["G2要具備什麼才能通過？"]).json()
    assert body["followup"] == "combined" and body["standalone_question"] == "G2要具備什麼才能通過？ 那需要誰簽核？"
    assert any(s["title"] == "G2簽核.txt" for s in body["sources"])


def test_without_model_follow_up_searches_with_previous_question(client, engine, isolated):
    documents(client, engine)
    body = ask(client, "那需要誰簽核？", history=["G2要具備什麼才能通過？"]).json()
    assert body["followup"] == "combined"
    assert {s["title"] for s in body["sources"]} >= {"G2簽核.txt"}
    assert "報到.txt" not in {s["title"] for s in body["sources"]}
    preview = client.post("/ai/preview", json=dict(dataset="formal-v1", question="那需要誰簽核？", history=["G2要具備什麼才能通過？"])).json()
    assert preview["content"] is None or preview["content"]["question"] == "G2要具備什麼才能通過？ 那需要誰簽核？"


def test_history_limits_and_modes(client, engine, isolated):
    setup(client, engine, "yu")
    assert ask(client, "那呢？", history=["題目"] * 7).status_code == 422
    assert ask(client, "那呢？", history=["長" * 2000] * 3 + ["短"]).status_code == 422
    assert ask(client, "那呢？", history=[""]).status_code == 422
    sql = client.post("/ai/ask", json=dict(dataset="dataset-v1", mode="sql", question="那呢？", history=["題目"]))
    assert sql.status_code == 422
