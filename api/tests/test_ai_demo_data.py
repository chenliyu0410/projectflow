import importlib.util
import shutil
from pathlib import Path

PACK = Path(__file__).resolve().parents[2] / 'deploy' / 'ai-demo-data'


def load():
    spec = importlib.util.spec_from_file_location('ai_demo_verify', PACK / 'verify.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_committed_pack_imports_and_every_analysis_matches_its_story():
    # Import with the product importer, run 6 companies x 16 analyses, permissions, and byte-identical regeneration.
    assert load().verify(PACK / 'pack') == []


def test_tampered_pack_is_reported(tmp_path):
    copy = tmp_path / 'pack'
    shutil.copytree(PACK / 'pack', copy)
    documents = copy / 'rag' / 'documents.jsonl'
    documents.write_bytes(documents.read_bytes().replace('截圖4張'.encode(), '截圖5張'.encode(), 1))
    assert any('rag/documents.jsonl' in problem for problem in load().verify(copy))


def test_story_check_catches_a_pack_without_the_demo_point():
    verify = load()
    results = {f'q{n:02d}': [{'x': 1}] for n in range(1, 17)}
    results.update(q04=[], q05=[{'supplier_id': 'S1'}], q06=[{'supplier_id': 'S3', 'late_pct': 10.0}],
                   q07=[{'project_id': 'food-PRJ1'}], q13=[], q14=[{'project_id': 'food-PRJ1', 'rejected_count': 1, 'blocked_count': 0}],
                   q16=[{'zero_defect_batches': 0}], q09=[], q02=[{'overdue_count': 1}, {'overdue_count': 1}])
    assert len(verify.story('food', results)) >= 8
