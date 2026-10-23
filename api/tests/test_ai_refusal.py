import pytest

from app.ai import model, service
from test_ai_starter import starter_root, login


@pytest.mark.parametrize("answer", ["資料未提供周子安的身分證字號。", "根據現有資料，文件中沒有記載採購費用。", "資料中未提及李小晴的月薪。"])
def test_absence_only_replies_become_the_fixed_refusal(monkeypatch, answer):
    monkeypatch.setattr(model, "chat", lambda *args: {"answerable": True, "answer": answer, "citations": ["d1"]})
    result = model.answer({}, "問題", [{"document_id": "d1", "body": "來源"}])
    assert result["citations"] == [] and "資料不足" in result["answer"]


def test_partial_answers_that_mention_missing_details_are_kept(monkeypatch):
    answer = "WO-001仍在處理中，已完成1台；採購費用資料未記載。"
    monkeypatch.setattr(model, "chat", lambda *args: {"answerable": True, "answer": answer, "citations": ["d1"]})
    assert model.answer({}, "筆電進度", [{"document_id": "d1", "body": "來源"}])["answer"] == answer


def test_equivalence_rule_is_in_the_prompt():
    assert "十一點＝11:00" in model.ANSWER_SYSTEM and "不要因為說法不同而拒答" in model.ANSWER_SYSTEM


@pytest.mark.parametrize("question, docs, expected", [
    ("峰曜科技的新人課程窗口是誰？", [{"body": "窗口林怡安", "title": "課程說明"}], "峰曜科技"),
    ("峰曜那邊幾點報到？", [{"body": "09:00報到", "title": "報到"}], "峰曜科技"),
    ("我們跟峰曜科技的合作窗口？", [{"body": "峰曜科技窗口為王小明", "title": "合作"}], None),
    ("新人課程窗口是誰？", [{"body": "窗口林怡安", "title": "課程說明"}], None),
])
def test_foreign_company_detection(question, docs, expected):
    assert service.foreign_company(question, docs, ["峰曜科技"]) == expected


def test_questions_about_another_company_are_refused_without_the_model(client, starter_root, monkeypatch):
    model.save("food", dict(enabled=True, base_url="http://127.0.0.1:11434", model="test"))
    monkeypatch.setattr(model, "chat", lambda *args: pytest.fail("Other-company questions must not reach the model"))
    login(client, "ming")
    result = client.post("/ai/ask", json=dict(dataset="starter-v1", question="峰曜科技的新人課程窗口是誰？")).json()
    assert result["kind"] == "other_company" and "林怡安" not in result["answer"] and "峰曜科技" in result["answer"]
    assert result["gateway"]["reason"] == "other_company" and result["gateway"]["outcome"] == "not_sent"
    preview = client.post("/ai/preview", json=dict(dataset="starter-v1", question="峰曜科技的新人課程窗口是誰？")).json()
    assert preview["content"] is None and preview["gateway"]["reason"] == "other_company"
    login(client, "elaine", "electronics")
    # MAIL-004 itself names 毛研食品 ("不適用毛研食品"), so the rule leaves this one to the model.
    model.save("electronics", dict(enabled=True, base_url="http://127.0.0.1:11434", model="test"))
    monkeypatch.setattr(model, "chat", lambda *args: {"answerable": False, "answer": "不足", "citations": []})
    other = client.post("/ai/ask", json=dict(dataset="starter-v1", question="毛研食品的新人哪一天報到？")).json()
    assert other["kind"] == "rag" and other["gateway"]["route"] == "local" and "10月26日" not in other["answer"]
