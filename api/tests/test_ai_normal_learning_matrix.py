"""64 個正常查詢矩陣與 8 個完整回訓流程，僅修改隔離測試資料。"""
import hashlib
import json
import shutil
import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai import store
from app.models import AILearnedPhrase
from test_ai import pack
from test_ai_expanded import dataSnapshot, executionCalls, signIn

caseRoot = Path(__file__).parent / "fixtures"
normalCases = json.loads((caseRoot / "text2sql_normal_64.json").read_text(encoding="utf-8"))
learningCases = json.loads((caseRoot / "text2sql_learning_8.json").read_text(encoding="utf-8"))


def refreshManifest(packPath):
  manifestPath = packPath / "manifest.json"
  manifest = json.loads(manifestPath.read_text(encoding="utf-8"))
  manifest["files"] = {
    path.relative_to(packPath).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
    for path in packPath.rglob("*") if path.is_file() and path != manifestPath
  }
  manifestPath.write_text(json.dumps(manifest), encoding="utf-8")


@pytest.fixture(scope="module")
def normalPack(pack, tmp_path_factory):
  packPath = tmp_path_factory.mktemp("normal-query-pack")
  shutil.copytree(pack, packPath, dirs_exist_ok=True)
  # 讓每種分析都有可算結果，避免空資料讓錯誤模板看起來也通過。
  with sqlite3.connect(packPath / "projectflow_demo.sqlite") as db:
    for company in sorted(store.COMPANIES):
      for number in (1, 2):
        project = f"{company}-P{number}"
        for taskId, status in [("T3", "rejected"), ("T4", "blocked")]:
          db.execute("INSERT INTO tasks VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (
            company, f"{project}-{taskId}", project, "p1", "補充測試任務", "研發", status,
            "2026-10-01", "2026-10-10", None, 5, 3
          ))
        for suffix, price, promised, received, status in [
          ("PO2", 20, "2026-10-05", "2026-10-08", "received"),
          ("PO3", 30, "2026-10-09", "2026-10-08", "received"),
          ("PO4", 40, "2026-10-20", None, "pending"),
          ("PO5", 50, "2026-10-05", None, "cancelled"),
        ]:
          db.execute("INSERT INTO purchase_orders VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (
            company, f"{project}-{suffix}", project, "s1", "測試", 2, price, price * 2,
            "2026-09-01", promised, received, status
          ))
        db.execute("INSERT INTO quality_checks VALUES (?,?,?,?,?,?,?)", (
          company, f"{project}-Q2", project, "2026-10-08", 20, 0, "test"
        ))
    assert db.execute("PRAGMA foreign_key_check").fetchall() == []
  refreshManifest(packPath)
  return packPath


@pytest.fixture(scope="module")
def emptyPack(normalPack, tmp_path_factory):
  packPath = tmp_path_factory.mktemp("empty-query-pack")
  shutil.copytree(normalPack, packPath, dirs_exist_ok=True)
  # 保留合法公司與專案，驗的是沒有業務明細，不是用不存在的專案換來拒答。
  with sqlite3.connect(packPath / "projectflow_demo.sqlite") as db:
    for table in ("notes", "tasks", "expenses", "purchase_orders", "quality_checks", "risks"):
      db.execute(f"DELETE FROM {table} WHERE company_id=?", ("food",))
    assert db.execute("PRAGMA foreign_key_check").fetchall() == []
  refreshManifest(packPath)
  return packPath


@pytest.fixture()
def normalDataset(case, normalPack, emptyPack, tmp_path, monkeypatch):
  monkeypatch.setenv("PF_AI_ROOT", str(tmp_path / "ai"))
  source = emptyPack if case.get("variant") == "empty" else normalPack
  store.import_pack(source, store.root())
  return store.root()


def test_normal_and_learning_case_matrix():
  expectedIds = {f"q{number:02}" for number in range(1, 17)}
  assert len(normalCases) == 64
  for variant in ("standard", "polite", "project", "empty"):
    group = [case for case in normalCases if case["variant"] == variant]
    assert len(group) == 16 and {case["queryId"] for case in group} == expectedIds
  assert len(learningCases) == 8
  assert len({case["id"] for case in normalCases + learningCases}) == 72
  assert len({case["question"] for case in learningCases}) == 8
  for case in normalCases:
    if case["variant"] != "empty":
      assert case["expectedRows"]
    elif case["queryId"] == "q16":
      assert case["expectedRows"] == [{"zero_defect_batches": 0}]
    else:
      assert case["expectedRows"] == []


@pytest.mark.parametrize("case", normalCases, ids=lambda case: case["id"] + "-" + case["variant"] + "-" + case["queryId"])
def test_normal_query_result(case, client, normalDataset, engine, executionCalls):
  signIn(client, "yu")
  before = dataSnapshot(normalDataset, engine)
  payload = {"question": case["question"], "mode": "sql"}
  if case["projectId"]:
    payload["project_id"] = case["projectId"]
  response = client.post("/ai/ask", json=payload)
  assert response.status_code == 200, response.text
  answer = response.json()
  assert answer["kind"] == "sql" and answer["learned"] is False
  assert answer["engine"] == "rules"
  analysis = answer["analysis"]
  assert analysis["query_id"] == case["queryId"]
  assert analysis["rows"] == case["expectedRows"]
  assert analysis["parameters"] == {
    "company_id": "food", "as_of": "2026-10-11", "project_id": case["projectId"]
  }
  assert analysis["truncated"] is False
  assert executionCalls == [(case["queryId"], "food")]
  assert dataSnapshot(normalDataset, engine) == before


def askQuestion(client, question, **extra):
  response = client.post("/ai/ask", json={"question": question, "mode": "sql", **extra})
  assert response.status_code == 200, response.text
  return response.json()


@pytest.mark.parametrize("case", learningCases, ids=lambda case: case["id"] + "-" + case["queryId"])
def test_learning_complete_flow(case, client, normalDataset, engine, executionCalls):
  signIn(client, "owner")
  originalFiles = dataSnapshot(normalDataset, engine)[0]
  before = askQuestion(client, case["question"])
  assert before["kind"] == "fallback" and before["analysis"] is None
  offered = {item["query_id"]: item for item in before["suggestions"]}
  assert case["queryId"] in offered
  chosen = offered[case["queryId"]]
  assert chosen["learnable"] is True
  assert executionCalls == []

  clicked = askQuestion(client, chosen["label"], query_id=case["queryId"])
  assert clicked["kind"] == "sql" and clicked["learned"] is False
  assert clicked["analysis"]["query_id"] == case["queryId"]
  assert clicked["analysis"]["rows"] == case["expectedRows"]
  assert executionCalls == [(case["queryId"], "food")]
  executionCalls.clear()

  confirmed = client.post("/ai/learning/confirm", json={
    "answer_id": before["answer_id"], "query_id": case["queryId"], "question": case["question"]
  })
  assert confirmed.status_code == 200, confirmed.text
  item = confirmed.json()
  assert item["status"] == "pending"
  assert askQuestion(client, case["question"])["kind"] == "fallback"
  assert executionCalls == []

  signIn(client, "yu")
  reviewed = client.post(f"/ai/learning/{item['id']}/approve")
  assert reviewed.status_code == 200, reviewed.text
  checked = reviewed.json()
  assert checked["status"] == "approved"
  assert checked["checks"]["passed"] is True
  assert [(check["code"], check["ok"]) for check in checked["checks"]["items"]] == [
    (f"C{number}", True) for number in range(1, 6)
  ]
  assert executionCalls == [(case["queryId"], "food")]
  executionCalls.clear()

  signIn(client, "owner")
  after = askQuestion(client, case["question"])
  assert after["kind"] == "sql" and after["learned"] is True
  assert after["analysis"]["query_id"] == case["queryId"]
  assert after["analysis"]["rows"] == case["expectedRows"]
  assert after["gateway"]["route"] == "none"
  assert executionCalls == [(case["queryId"], "food")]
  executionCalls.clear()

  signIn(client, "foreignAdmin")
  foreign = askQuestion(client, case["question"])
  assert foreign["kind"] == "fallback" and foreign["analysis"] is None
  assert client.get("/ai/learning").json() == {"items": [], "pending": 0}
  assert executionCalls == []
  with Session(engine) as db:
    [row] = list(db.scalars(select(AILearnedPhrase)))
    assert row.id == item["id"] and row.status == "approved"
    assert row.phrase == case["question"] and row.query_id == case["queryId"]
  assert dataSnapshot(normalDataset, engine)[0] == originalFiles
