import pytest
import os
import json
import re
from pathlib import Path
from app.rag import parsing


@pytest.mark.skipif(os.environ.get('PF_RAG_LIVE_TESTS') != '1', reason='Opt-in local Ollama integration')
@pytest.mark.parametrize('variant', ['original', 'renamed', 'no_approval', 'known_absence'])
def test_live_condition_answer_preserves_prerequisites(variant):
    """Catch generated summaries dropping a required sign-off despite complete evidence."""
    from app.rag.provider import answer
    report = Path(__file__).resolve().parents[2] / 'artifacts/rag-demo-data-2026-10-21/evaluation-accepted.json'
    case = next(row for row in json.loads(report.read_text(encoding='utf-8'))['cases'] if row['id'] == 'Q06')
    sources, question = case['sources'], case['question']
    terms = ['批次識別資料', '供應商聲明', '模擬檢驗報告', '陳奕安', '簽核']
    if variant == 'renamed':
        swaps = {'G2': 'K7', '陳奕安': '葉子庭', '批次識別資料': '設備清單', '供應商聲明': '校正紀錄', '模擬檢驗報告': '操作測試報告'}
        for old, new in swaps.items():
            question = question.replace(old, new)
            sources = json.loads(json.dumps(sources, ensure_ascii=False).replace(old, new))
        terms = ['設備清單', '校正紀錄', '操作測試報告', '葉子庭', '簽核']
    elif variant == 'no_approval':
        question = '驗收關卡 Z9 要具備什麼才能通過？是否需要主管簽核？'
        sources = [dict(source_id='z9', title='設備驗收規則', version=1, excerpt='Z9 通過須完成設備清單與操作測試報告。\n兩份文件齊備後，仍須等待觀察期滿七天且無異常，才可通過。\n本關卡不需主管簽核。若觀察期未滿或發現異常，應維持待驗收。')]
        terms = ['設備清單', '操作測試報告', '七天', '異常']
    elif variant == 'known_absence':
        case = next(row for row in json.loads(report.read_text(encoding='utf-8'))['cases'] if row['id'] == 'Q18')
        sources, question = case['sources'], case['question']
        terms = ['備援', '核准']
    result = answer(dict(enabled=True, base_url='http://127.0.0.1:11434', model='qwen2.5-coder:7b'), question, sources)
    print(json.dumps(dict(variant=variant, **result), ensure_ascii=False))
    assert all(term in result['answer'] for term in terms), result
    assert result['citations'] and set(result['citations']) <= {s['source_id'] for s in sources}
    if variant == 'no_approval':
        assert re.search(r'(?:不需|無需|不必)[^。；\n]{0,16}簽核', result['answer']), result
    if variant == 'known_absence':
        assert re.search(r'(?:沒有|無|未|尚未)[^。；\n]{0,12}核准', result['answer']), result
        assert '梧桐' not in result['answer'], result
        supporting_statements = ['目前沒有已核准的備援供應商名稱', '備援供應商仍在評選，本文件沒有提供備援供應商名稱，也不能推定已核准']
        assert any(s['source_id'] in result['citations'] and any(text in s['excerpt'] for text in supporting_statements) for s in sources), result


def test_csv_retains_headers_missing_and_extra_columns(tmp_path):
    p = tmp_path / 'rows.csv'
    p.write_text('日期,,金額,金額\n2030-02-03,樣品,91,27,額外\n2030-02-04\n', encoding='utf-8')
    rows = parsing.parse_file(p, p.name)
    assert rows[1]['text'] == '日期: 2030-02-03 | 第2欄: 樣品 | 金額（第3欄）: 91 | 金額（第4欄）: 27 | 第5欄: 額外'
    assert rows[1]['locator']['section'] == '第 2 列'
    assert rows[2]['text'] == '日期: 2030-02-04'


def grounded_answer(value, sources):
    from app.rag.grounding import grounded_answer as impl
    return impl(value, sources)


SOURCES = [{'source_id': 'a', 'excerpt': '袋：小計 8,125.50 元。箱：小計 274.50 元。'}]


def response(operation='none', operands=None, evidence=None):
    return dict(answer='依文件回答', evidence=evidence or [], calculation=dict(operation=operation, operands=operands or [], unit='元'))


def operand(value, quote, label='小計'):
    return dict(value=value, quote=quote, source_id='a', label=label)


def test_exact_evidence_drives_citations():
    value = response(evidence=[dict(source_id='a', quote='箱：小計 274.50 元。')])
    assert grounded_answer(value, SOURCES)['citations'] == ['a']
    value['evidence'][0]['quote'] = '箱：小計 999 元。'
    with pytest.raises(ValueError):
        grounded_answer(value, SOURCES)


def test_server_owned_evidence_preserves_exact_row_and_rejects_unknown_ids():
    from app.rag.grounding import evidence_catalog, resolve_evidence
    sources = [{'source_id': 'a', 'excerpt': '項目: 紙盒 | 數量: 17 | 小計: 459 | 日期: 2030-01-02'}]
    catalog, mapping = evidence_catalog(sources)
    assert catalog[0]['text'] == sources[0]['excerpt']
    result = grounded_answer(resolve_evidence(response(evidence=['E1']), mapping), sources)
    assert result['citations'] == ['a']
    for wrong in ['E999', {}, None]:
        with pytest.raises(ValueError):
            resolve_evidence(response(evidence=[wrong]), mapping)


def test_evidence_catalog_keeps_conditions_decimals_and_bounds():
    from app.rag.grounding import evidence_catalog
    source = dict(source_id='a', title='條件', version=3, excerpt='只在核准後生效；尚未確認。\n小計 1.25 元。')
    catalog, mapping = evidence_catalog([source])
    assert catalog[0]['text'] == '只在核准後生效；尚未確認。'
    assert catalog[1]['text'] == '小計 1.25 元。'
    assert catalog[1]['title'] == '條件' and catalog[1]['version'] == 3
    catalog, _ = evidence_catalog([dict(source_id='a', excerpt='x\n' * 100)])
    assert len(catalog) == 1


def test_numeric_id_binds_value_to_original_evidence():
    from app.rag.grounding import evidence_catalog, numeric_catalog, resolve_evidence
    sources = [dict(source_id='a', excerpt='總數 156'), dict(source_id='b', excerpt='每盒 12')]
    _, mapping = evidence_catalog(sources)
    _, numbers = numeric_catalog(mapping)
    value = response('divide', [dict(number_id='E1:156', label='總數'), dict(number_id='E2:12', label='每盒')])
    result = grounded_answer(resolve_evidence(value, mapping, numbers), sources)
    assert '156 ÷ 12 = 13' in result['answer'] and result['citations'] == ['a', 'b']
    value['calculation']['operands'][1]['number_id'] = 'E1:12'
    with pytest.raises(ValueError):
        resolve_evidence(value, mapping, numbers)


def test_decimal_calculation_replaces_model_arithmetic():
    value = response('add', [operand('8125.50', '袋：小計 8,125.50 元。', '袋'), operand('274.50', '箱：小計 274.50 元。', '箱')])
    value['answer'] = '9999 元'
    result = grounded_answer(value, SOURCES)
    assert '8,400' in result['answer'] and '9999' not in result['answer']
    assert result['citations'] == ['a']


@pytest.mark.parametrize('number', ['125.50', '0', 'nan', 'Infinity', '8e3', '__import__("os")'])
def test_ungrounded_or_unsafe_operand_rejected(number):
    with pytest.raises(ValueError):
        grounded_answer(response('add', [operand(number, SOURCES[0]['excerpt']), operand('274.50', SOURCES[0]['excerpt'])]), SOURCES)


def test_divide_and_zero_rejected():
    sources = [{'source_id': 'a', 'excerpt': '總數 156；每盒 12；剩餘 0'}]
    v = response('divide', [operand('156', sources[0]['excerpt']), operand('12', sources[0]['excerpt'])])
    assert '13' in grounded_answer(v, sources)['answer']
    v['calculation']['operands'][1]['value'] = '0'
    with pytest.raises(ValueError):
        grounded_answer(v, sources)


def test_no_evidence_returns_refusal_not_unsupported_answer():
    assert grounded_answer(response(), SOURCES) == {'answer': '目前來源不足以支持答案。', 'citations': [], 'blocks': []}


@pytest.mark.parametrize('operation', [[], {}, None, True])
def test_malformed_operation_is_safe_failure(operation):
    with pytest.raises(ValueError):
        grounded_answer(response(operation), SOURCES)


def test_small_decimals_and_recurring_quotient_not_rendered_as_zero():
    sources = [{'source_id': 'a', 'excerpt': '甲 0.00001；乙 0.00002；總量 1；份數 30000'}]
    text = sources[0]['excerpt']
    small = grounded_answer(response('add', [operand('0.00001', text), operand('0.00002', text)]), sources)
    assert '0.00001 + 0.00002 = 0.00003' in small['answer']
    recurring = grounded_answer(response('divide', [operand('1', text), operand('30000', text)]), sources)
    assert '≈ 0.0000333333333333' in recurring['answer']

def test_blocks_bind_separately_and_unknown_or_empty_evidence_rejected():
    from app.rag.grounding import evidence_catalog, resolve_evidence
    sources=[{'source_id':'a','excerpt':'甲同意。'},{'source_id':'b','excerpt':'乙不同意。'}]
    _, mapping=evidence_catalog(sources)
    value={'answer':'ignored','evidence':['E1','E2'],'calculation':{'operation':'none','operands':[],'unit':''},'blocks':[{'text':'甲同意。','evidence':['E1']},{'text':'雙方衝突。','evidence':['E1','E2']}]}
    result=grounded_answer(resolve_evidence(value,mapping),sources)
    assert result['blocks']==[{'text':'甲同意。','source_ids':['a']},{'text':'雙方衝突。','source_ids':['a','b']}]
    assert result['citations']==['a','b']
    for ids in ([],['unknown']):
        value['blocks'][0]['evidence']=ids
        with pytest.raises(ValueError): resolve_evidence(value,mapping)


def test_calculation_block_uses_operand_sources():
    value=response('add',[operand('8,125.50','袋：小計 8,125.50 元。'),operand('274.50','箱：小計 274.50 元。')])
    result=grounded_answer(value,SOURCES)
    assert result['blocks']==[{'text':result['answer'],'source_ids':['a']}]
    assert '8,400' in result['answer']
