"""Compare keyword and hybrid retrieval on the isolated starter copy (no chat model, no answers).

Run from the repo root with the isolated AI area, e.g.:
  PF_AI_ROOT=../output/rag-starter-acceptance/local-model/ai python deploy/check_retrieval.py --report out.json
It only reads documents; the first run adds a vector side file under PF_AI_ROOT/vectors.
"""
import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'api'))
from app.ai import starter, store, vectors  # noqa: E402

ROLES = {'employee': 'member', 'hr': 'admin', 'admin': 'admin'}


def load(name):
    path = Path(__file__).parent / 'rag-starter/evaluation' / name
    return [json.loads(s) for s in path.read_text(encoding='utf-8').splitlines() if s.strip()]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--model', default='bge-m3')
    args = parser.parse_args()
    if 'output' not in Path(store.root()).resolve().parts:
        parser.error('PF_AI_ROOT must point at an isolated copy under output/')
    os.environ.update(PF_ACCEPTANCE_MODE='true', PF_AI_VECTOR_MODEL=args.model)
    cases = [dict(q, bank='original', acceptable=q['required_source_ids']) for q in load('questions.jsonl') if q['question_id'] != 'Q31']
    cases += [dict(q, bank='paraphrase', acceptable=q['acceptable_source_ids']) for q in load('paraphrases.jsonl')]
    rows = []
    for case in cases:
        company = case['company_id']
        role = 'admin' if company == 'electronics' else ROLES[case['role']]
        with closing(store.connect(company, 'starter-v1')) as db:
            keyword = [d['document_id'] for d in store.search(db, case['question'], role, None, case['include_history'])]
            documents, mode = starter.search(db, company, case['question'], role, None, case['include_history'])
            hybrid = [d['document_id'] for d in documents]
            stored = vectors.starter_vectors(db, company)
            query = vectors.embed(company, [case['question']])[0]
            scores = sorted(((round(vectors.similarity(query, v), 3), i) for i, v in stored.items()), reverse=True)
        expected = set(case['acceptable'])
        forbidden = set(case.get('forbidden_source_ids', []))

        def recall(found):
            # Questions that must be refused have no required source; only the forbidden check applies.
            return len(expected & set(found)) / len(expected) if expected else 1.0

        rows.append(dict(question_id=case['question_id'], bank=case['bank'], question=case['question'], mode=mode,
                         keyword=keyword, hybrid=hybrid,
                         keyword_hit=bool(expected & set(keyword)) or not expected, hybrid_hit=bool(expected & set(hybrid)) or not expected,
                         keyword_recall=recall(keyword), hybrid_recall=recall(hybrid),
                         forbidden_in_hybrid=sorted(forbidden & set(hybrid)),
                         best_relevant=max((s for s, i in scores if i in expected), default=None),
                         best_other=max((s for s, i in scores if i not in expected), default=None)))
        print(case['question_id'], mode, 'keyword', rows[-1]['keyword_hit'], 'hybrid', rows[-1]['hybrid_hit'], flush=True)
    summary = {}
    for bank in ('original', 'paraphrase'):
        part = [r for r in rows if r['bank'] == bank]
        summary[bank] = dict(cases=len(part),
                             keyword_hit=sum(r['keyword_hit'] for r in part), hybrid_hit=sum(r['hybrid_hit'] for r in part),
                             keyword_recall=round(sum(r['keyword_recall'] for r in part) / len(part), 3),
                             hybrid_recall=round(sum(r['hybrid_recall'] for r in part) / len(part), 3),
                             hybrid_regressions=[r['question_id'] for r in part if r['keyword_recall'] > r['hybrid_recall']],
                             forbidden_leaks=[r['question_id'] for r in part if r['forbidden_in_hybrid']])
    report = dict(model=args.model, min_similarity=vectors.MIN_SIMILARITY, summary=summary, cases=rows)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False))
    if any(s['hybrid_regressions'] or s['forbidden_leaks'] for s in summary.values()):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
