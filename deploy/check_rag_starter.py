"""Import into an isolated directory and measure retrieval, not LLM answer quality."""
import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))
from app.ai import starter, store


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack", type=Path, default=Path(__file__).parent / "rag-starter")
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    os.environ["PF_AI_ROOT"] = str(args.destination.resolve())
    imported = starter.import_starter(args.pack, args.destination)
    cases = []
    questions = [json.loads(line) for line in (args.pack / "evaluation/questions.jsonl").read_text(encoding="utf-8").splitlines()]
    for q in questions:
        role = {"employee": "member", "hr": "admin", "admin": "admin"}[q["role"]]
        with closing(store.connect(q["company_id"], "starter-v1")) as db:
            if q["question_id"] == "Q31":
                rows = starter.pending_orders(db, role)
                mode = "完整工單清單"
            else:
                rows = store.search(db, q["question"], role, include_history=q["include_history"])
                mode = "全文搜尋前六筆"
            ids = {r["document_id"] for r in rows}
            missing = sorted(set(q["required_source_ids"]) - ids)
            forbidden = sorted(set(q["forbidden_source_ids"]) & ids)
            scope_ok = all(role in json.loads(r["roles"]) and json.loads(r["metadata"])["company_id"] == q["company_id"] for r in rows)
            version_ok = q["include_history"] or all(r["current"] for r in rows)
            cases.append(dict(question_id=q["question_id"], mode=mode, retrieved=sorted(ids),
                              required=q["required_source_ids"], missing=missing,
                              forbidden=forbidden, scope_ok=scope_ok, version_ok=version_ok,
                              answer_quality="not_run_no_model"))
    required_cases = [c for c in cases if c["required"]]
    report = dict(
        imported=imported, questions=len(cases),
        all_required_sources_found=sum(not c["missing"] for c in required_cases),
        questions_with_required_sources=len(required_cases),
        scope_and_version_pass=sum(c["scope_ok"] and c["version_ok"] and not c["forbidden"] for c in cases),
        answer_accuracy="not_evaluated", model_called=False,
        note="This evaluates retrieval and scope only. Q31 uses the explicit work-order mode; it does not claim natural-language intent recognition.",
        cases=cases)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in {"cases", "imported"}}, ensure_ascii=False))
    if report["scope_and_version_pass"] != len(cases) or report["all_required_sources_found"] != len(required_cases):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
