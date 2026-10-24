"""Verify the AI demo pack the way the product will use it.

    python deploy/ai-demo-data/verify.py [--pack deploy/ai-demo-data/pack]

Imports the pack with the product importer (app.ai.store.import_pack) into a temporary folder, runs all 16 fixed
analyses for every company with app.ai.store.execute_query, and compares them with evaluation/expected.json
(computed by generate.py without SQL). Also checks the storyline each demo relies on, document permissions,
and that regenerating gives byte-identical files.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import sqlite3
import sys
import tempfile
from contextlib import closing
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'api'))


def generator():
    spec = importlib.util.spec_from_file_location('ai_demo_generate', HERE / 'generate.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def same(a, b):
    """Rows match exactly; percentages may differ only by floating-point noise."""
    if len(a) != len(b):
        return False
    for x, y in zip(a, b):
        if set(x) != set(y):
            return False
        for key in x:
            if isinstance(x[key], float) or isinstance(y[key], float):
                if abs(float(x[key]) - float(y[key])) > 0.005:
                    return False
            elif x[key] != y[key]:
                return False
    return True


def story(cid, results):
    """The point each analysis is supposed to make in a demo."""
    problems = []
    need = lambda ok, text: ok or problems.append(f'{cid}：{text}')
    need(len(results['q04']) == 1 and results['q04'][0]['project_id'].endswith('PRJ2'), '超支專案應只有 PRJ2')
    need([r['supplier_id'] for r in results['q05']] == ['S2'], '逾期未交應只有 S2')
    late = {r['supplier_id']: r['late_pct'] for r in results['q06']}
    need(late.get('S3', 0) == max(late.values()) and late['S3'] >= 50, 'S3 延遲率應最高且至少 50%')
    need(results['q07'][0]['project_id'].endswith('PRJ4'), '不良率最高應是 PRJ4')
    need(3 <= len(results['q13']) <= 5, '本週到期未完成應有 3–5 筆')
    worst = max(results['q14'], key=lambda r: r['rejected_count'] + r['blocked_count'])
    need(worst['project_id'].endswith('PRJ3'), '退回與受阻應集中在 PRJ3')
    need(results['q16'][0]['zero_defect_batches'] >= 2, '零不良批次至少 2 批')
    need(len(results['q09']) >= 2, '尚未結案的高風險至少 2 筆')
    need(len(results['q02']) >= 2 and results['q02'][0]['overdue_count'] > results['q02'][1]['overdue_count'], '逾期最多的部門應明顯領先')
    for query_id, rows in results.items():
        need(bool(rows), f'{query_id} 沒有結果')
    return problems


def verify(pack):
    from app.ai import store
    problems = []
    manifest = json.loads((pack / 'manifest.json').read_text(encoding='utf-8'))
    for relative, digest in manifest['files'].items():
        if hashlib.sha256((pack / relative).read_bytes()).hexdigest() != digest:
            problems.append(f'檔案與 manifest 不符：{relative}')
    expected = json.loads((pack / 'evaluation' / 'expected.json').read_text(encoding='utf-8'))
    with tempfile.TemporaryDirectory() as temp:
        previous = os.environ.get('PF_AI_ROOT')
        os.environ['PF_AI_ROOT'] = temp
        try:
            try:
                store.import_pack(pack, temp)  # rejects a different SQL catalog, bad foreign keys or checksums
            except ValueError as error:
                return problems + [f'匯入器拒絕：{error}']
            for cid in sorted(store.COMPANIES):
                with closing(store.connect(cid)) as db:
                    results = {q['query_id']: store.execute_query(db, q['query_id'], cid)['rows'] for q in store.catalog()}
                    for query_id, rows in results.items():
                        if not same(rows, expected[cid][query_id]):
                            problems.append(f'{cid} {query_id} 與預期不符')
                    problems += story(cid, results)
                    member = {d['document_id'] for d in store.search(db, '成本報告 超支 預算', 'member', include_history=True)}
                    manager = {d['document_id'] for d in store.search(db, '成本報告 超支 預算', 'project_owner')}
                    if any('-COST-' in d for d in member) or not any('-COST-' in d for d in manager):
                        problems.append(f'{cid} 成本報告權限不對')
                    current = [d['document_id'] for d in store.search(db, '現行交付需要幾張截圖', 'member')]
                    if f'{cid}-SPEC-1' in current or f'{cid}-SPEC-2' not in current:
                        problems.append(f'{cid} 交付規範應只找到現行版')
        finally:
            if previous is None:
                os.environ.pop('PF_AI_ROOT', None)
            else:
                os.environ['PF_AI_ROOT'] = previous
        regenerated = Path(temp) / 'regenerated'
        fresh = generator().write(regenerated)['files']
        # The SQLite header records the library version that wrote it, so compare the database by content.
        database = 'projectflow_demo.sqlite'
        if {k: v for k, v in fresh.items() if k != database} != {k: v for k, v in manifest['files'].items() if k != database} \
                or dump(regenerated / database) != dump(pack / database):
            problems.append('重新產生的內容與資料包不同')
    problems += consistency(pack)
    return problems


def dump(path):
    with closing(sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)) as db:
        return list(db.iterdump())


def consistency(pack):
    """Rules the schema cannot express: timelines and who may read which document."""
    from app.ai.starter import ROLES
    problems = []
    with closing(sqlite3.connect((pack / 'projectflow_demo.sqlite').resolve().as_uri() + '?mode=ro', uri=True)) as db:
        checks = {
            '進行中的任務開始日晚於基準日': "SELECT COUNT(*) FROM tasks WHERE status NOT IN ('todo','done') AND start_date>:d",
            '完成或成本或抽查日期晚於基準日': "SELECT (SELECT COUNT(*) FROM tasks WHERE completed_date>:d)+(SELECT COUNT(*) FROM expenses WHERE booked_date>:d)"
                                       "+(SELECT COUNT(*) FROM quality_checks WHERE checked_date>:d)",
            '未開始的任務已有工時': "SELECT COUNT(*) FROM tasks WHERE status='todo' AND actual_hours>0",
            '收貨日早於下單日或晚於基準日': "SELECT COUNT(*) FROM purchase_orders WHERE received_date<ordered_date OR received_date>:d",
            '筆記早於任務開始或晚於基準日': "SELECT COUNT(*) FROM notes n JOIN tasks t USING(company_id,task_id) WHERE n.created_date<t.start_date OR n.created_date>:d",
        }
        for text, sql in checks.items():
            if db.execute(sql, {'d': '2026-10-11'}).fetchone()[0]:
                problems.append(text)
    for line in (pack / 'rag' / 'documents.jsonl').read_text(encoding='utf-8').splitlines():
        d = json.loads(line)
        cost = d['document_type'] == 'cost'
        expected = (['admin', 'project_owner'], 'confidential') if cost else (sorted(ROLES), 'internal')
        if (sorted(d['allowed_roles']), d['classification']) != (sorted(expected[0]), expected[1]):
            problems.append(f'{d["document_id"]} 權限或等級不對')
    return problems


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--pack', type=Path, default=HERE / 'pack')
    args = parser.parse_args()
    problems = verify(args.pack.resolve())
    print(json.dumps(dict(ok=not problems, problems=problems), ensure_ascii=False, indent=1))
    if problems:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
