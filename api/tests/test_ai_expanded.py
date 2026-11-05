"""擴充題庫：每題保留獨立 pytest ID，規則、權限及正常對照分開計數。"""
import hashlib
import json
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai import model, store
from app.models import AILearnedPhrase
from test_ai import pack, installed, login

caseRoot = Path(__file__).parent / "fixtures"
trapCases = json.loads((caseRoot / "text2sql_traps_100.json").read_text(encoding="utf-8"))
accessCases = json.loads((caseRoot / "text2sql_access_100.json").read_text(encoding="utf-8"))


def dataSnapshot(aiRoot, engine):
  # 允許 API 留下查詢稽核，但拒答或越權不得改動資料集、模型設定或已收錄問法。
  hashes = {
    str(path.relative_to(aiRoot)): hashlib.sha256(path.read_bytes()).hexdigest()
    for path in aiRoot.rglob("*") if path.is_file()
  }
  with Session(engine) as db:
    phrases = [
      (row.id, row.organization_id, row.phrase, row.query_id, row.status,
       tuple(row.confirmed_by), str(row.reviewed_at), str(row.checks))
      for row in db.scalars(select(AILearnedPhrase).order_by(AILearnedPhrase.id))
    ]
  return hashes, phrases


def signIn(client, actor):
  client.base_url = "http://127.0.0.1"
  client.post("/auth/logout")
  if actor == "anonymous":
    return
  if actor == "foreignAdmin":
    response = client.post("/auth/login", json={
      "organization_key": "electronics", "username": "elaine", "password": "demo-elaine"
    })
    assert response.status_code == 200
  else:
    login(client, actor)


@pytest.fixture()
def executionCalls(monkeypatch):
  calls = []
  originalExecute = store.execute_query

  def recordExecution(*args, **kwargs):
    calls.append((args[1], args[2]))
    return originalExecute(*args, **kwargs)

  def forbidModel(*args, **kwargs):
    pytest.fail("規則測試不應連線真實模型")

  monkeypatch.setattr(store, "execute_query", recordExecution)
  monkeypatch.setattr(model, "chat", forbidModel)
  monkeypatch.setattr(model, "request", forbidModel)
  return calls


def test_case_bank_integrity():
  assert len(trapCases) == len(accessCases) == 100
  assert len({case["question"] for case in trapCases}) == 100
  assert len({case["id"] for case in trapCases + accessCases}) == 200
  assert all(case["expected"] == "no_analysis_no_query_execution" for case in trapCases)
  assert len({json.dumps({k: v for k, v in case.items() if k != "id"}, sort_keys=True) for case in accessCases}) == 100
  for case in accessCases:
    if case["category"] == "cross_company":
      reference = case["path"] if case["method"] == "GET" else case["body"]["project_id"]
      assert any(company + "-" in reference for company in store.COMPANIES - {"food"})


@pytest.mark.parametrize("case", trapCases, ids=lambda case: case["id"] + "-" + case["category"])
def test_trap_never_executes_analysis(case, client, installed, engine, executionCalls):
  signIn(client, "yu")
  before = dataSnapshot(installed, engine)
  response = client.post("/ai/ask", json={"question": case["question"], "mode": "sql"})
  assert response.status_code == 200, (case["id"], response.text)
  answer = response.json()
  assert answer["kind"] in {"fallback", "unsupported", "help"}, (case["id"], answer)
  assert answer["analysis"] is None
  assert answer["sources"] == []
  assert answer["engine"] == "rules"
  assert executionCalls == [], case["id"]
  assert dataSnapshot(installed, engine) == before


def prepareLearning(client):
  signIn(client, "yu")
  question = "哪些供應商常常遲交？"
  response = client.post("/ai/ask", json={"question": question, "mode": "sql"})
  assert response.status_code == 200
  answer = response.json()
  assert answer["analysis"] is None
  response = client.post("/ai/learning/confirm", json={
    "answer_id": answer["answer_id"], "query_id": "q06", "question": question
  })
  assert response.status_code == 200, response.text
  return {"answerId": answer["answer_id"], "phraseId": response.json()["id"]}


@pytest.mark.parametrize("case", accessCases, ids=lambda case: case["id"] + "-" + case["category"])
def test_access_boundary(case, client, installed, engine, executionCalls):
  references = prepareLearning(client) if case["setupLearning"] else {}
  signIn(client, case["actor"])
  path = case["path"].format(**references)
  body = {
    key: value.format(**references) if isinstance(value, str) else value
    for key, value in (case["body"] or {}).items()
  }
  before = dataSnapshot(installed, engine)
  executionCalls.clear()
  response = client.request(case["method"], path, **({"json": body} if case["body"] is not None else {}))
  assert response.status_code == case["status"], (case["id"], response.text)
  if case["status"] == 200:
    assert response.json() == {"items": [], "pending": 0}
  else:
    assert set(response.json()) == {"detail"}
  assert executionCalls == [], case["id"]
  assert dataSnapshot(installed, engine) == before

