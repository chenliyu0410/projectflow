from app.rag.evaluation import evaluate


def test_evaluation_checks_leaks_current_citations_and_noanswer():
    cases = [{'id':'a','expected_source_ids':['s1'],'expected_kind':'rag'}]
    report = evaluate(cases, lambda c: {'kind':'rag','sources':[{'source_id':'bad','is_current':False}], 'citations':['unknown']})
    assert report['failed'] == 1
    assert report['metrics']['source_leak_count'] == 1
    assert report['metrics']['stale_source_count'] == 1
    assert report['metrics']['invalid_citation_count'] == 1
    assert report['latency_ms']['p50'] >= 0
    assert report['token_count'] is None


def test_failures_skips_and_fixture_label():
    cases = [{'id':'fail'}, {'id':'skip'}, {'id':'noanswer','expected_kind':'no_sources','expected_source_ids':[]}]
    def run(c):
        if c['id'] == 'fail': raise RuntimeError('private content')
        if c['id'] == 'skip': return {'skipped':True}
        return {'kind':'rag','sources':[], 'citations':[]}
    result = evaluate(cases, run, mode='fixture')
    assert (result['failed'], result['skipped'], result['executed']) == (2,1,2)
    assert result['mode'] == 'fixture'
    assert 'private content' not in str(result)
    assert result['metrics']['no_answer_failure_count'] == 1


def test_fixed_fixture_contract():
    import json
    from pathlib import Path
    cases = json.loads((Path(__file__).parent / 'fixtures' / 'rag_cases.json').read_text(encoding='utf-8-sig'))
    report = evaluate(cases, lambda case: case['fixture_result'], mode='fixture')
    assert report['passed'] == 7 and report['failed'] == 0
    assert report['actual_model_verified'] is False
