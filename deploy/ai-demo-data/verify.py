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
        if generator().write(regenerated)['files'] != manifest['files']:
            problems.append('重新產生的內容與資料包不同')
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
