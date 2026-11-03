"""Run the TEXT2SQL-FALLBACK question bank against the data-analysis copilot and grade every answer.

From the repo root:
  api/.venv/Scripts/python.exe deploy/ai-demo-data/fallback-eval/measure.py
  api/.venv/Scripts/python.exe deploy/ai-demo-data/fallback-eval/measure.py --model http://127.0.0.1:11434 qwen3:4b

The pack is imported into a temporary AI root, so nothing outside it is read or changed.
Grading follows rule 8 of docs/superpowers/plans/2026-11-04-text2sql-fallback.md.
"""
import argparse
import json
import os
import re
import sqlite3
import sys
import tempfile
from collections import Counter
from contextlib import closing
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PACK = REPO / 'deploy/ai-demo-data/pack'
sys.path.insert(0, str(REPO / 'api'))


def data_values(db, company):
    """Names and amounts that may only appear after a template really ran."""
    names = [r[0] for r in db.execute('SELECT name FROM people WHERE company_id=?', (company,))]
    names += [r[0] for r in db.execute('SELECT name FROM suppliers WHERE company_id=?', (company,))]
    names += [re.sub(r'（.*?）', '', r[0]) for r in db.execute('SELECT title FROM projects WHERE company_id=?', (company,))]
    amounts = set()
    for table, column in [('expenses', 'amount_twd'), ('purchase_orders', 'amount_twd'), ('projects', 'budget_twd')]:
        amounts |= {str(int(r[0])) for r in db.execute(f'SELECT {column} FROM {table} WHERE company_id=?', (company,)) if r[0] and r[0] >= 100}
    return names + sorted(amounts)


def shown_text(result):
    parts = [result.get('answer') or '']
    for s in result.get('suggestions') or []:
        parts += [s.get('label', ''), s.get('omits', '')]
    if result.get('suggestion'):
        parts.append(result['suggestion'].get('label', ''))
    return '\n'.join(parts)


def grade(item, result, values):
    expect = item['expect']
    executed = (result.get('analysis') or {}).get('query_id')
    suggestions = [s['query_id'] for s in result.get('suggestions') or []]
    if not suggestions and result.get('suggestion'):
        suggestions = [result['suggestion']['query_id']]
    conditions = {c['type'] for c in result.get('conditions') or []}
    text = shown_text(result)
    leaked = [v for v in values if v in text and v not in item['question']]
    group = item['group']
    if group == 'paraphrase':
        ok = executed in expect['queries'] if executed else any(q in expect['queries'] for q in suggestions[:3])
    elif group == 'condition':
        ok = not executed and expect['condition'] in conditions and any(q in expect['queries'] for q in suggestions[:3])
    elif group == 'help':
        ok = result['kind'] == 'help' and not executed and not leaked
    else:
        ok = result['kind'] in {'unsupported', 'other_company'} and not executed and not suggestions and not leaked
    return dict(id=item['id'], group=group, ok=ok, kind=result['kind'], executed=executed,
                suggestions=suggestions[:3], conditions=sorted(conditions), leaked=leaked)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', nargs=2, metavar=('BASE_URL', 'MODEL'))
    parser.add_argument('--out', type=Path)
    parser.add_argument('--bank', type=Path, default=HERE / 'questions.json', help='questions.json (tuning set) or holdout.json')
    args = parser.parse_args()
    bank = json.loads(args.bank.read_text(encoding='utf-8'))
    company = bank['company']
    with tempfile.TemporaryDirectory() as root:
        os.environ['PF_AI_ROOT'] = root
        from app.ai import model, service, store
        store.import_pack(PACK, store.root())
        if args.model:
            model.save(company, dict(enabled=True, base_url=args.model[0], model=args.model[1]))
        with closing(sqlite3.connect((PACK / 'projectflow_demo.sqlite').resolve().as_uri() + '?mode=ro', uri=True)) as source:
            values = data_values(source, company)
            others = [r[0] for r in source.execute('SELECT name FROM companies WHERE company_id<>?', (company,))]
        rows = []
        with closing(store.connect(company)) as db:
            for item in bank['questions']:
                try:
                    result = service.ask(db, company, 'admin', item['question'], 'sql', other_companies=others)
                except ValueError:
                    result = dict(kind='rejected', analysis=None, answer='')
                rows.append(grade(item, result, values))
    for r in rows:
        print(f"{'O' if r['ok'] else 'X'} {r['id']} {r['kind']:<16} 執行={r['executed'] or '-':<4} 建議={','.join(r['suggestions']) or '-':<12} 條件={','.join(r['conditions']) or '-'}" + (f" 洩漏={r['leaked']}" if r['leaked'] else ''))
    totals = Counter(r['group'] for r in rows)
    passed = Counter(r['group'] for r in rows if r['ok'])
    summary = {g: f'{passed[g]}/{totals[g]}' for g in bank['groups']}
    summary['total'] = f'{sum(passed.values())}/{len(rows)}'
    print(json.dumps(dict(model=args.model[1] if args.model else None, summary=summary), ensure_ascii=False))
    if args.out:
        args.out.write_text(json.dumps(dict(model=args.model[1] if args.model else None, summary=summary, rows=rows), ensure_ascii=False, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
