import pytest
from app.rag import parsing


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
    assert grounded_answer(response(), SOURCES) == {'answer': '目前來源不足以支持答案。', 'citations': []}


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
