import json

import pytest

from app.ai import model, service


def test_citation_schema_only_allows_supplied_documents(monkeypatch):
    def chat(config, system, prompt, schema):
        assert schema['properties']['citations']['items']['enum'] == ['d1']
        return {'answerable': True, 'answer': '帶筆電', 'citations': ['d1']}
    monkeypatch.setattr(model, 'chat', chat)
    model.answer({}, '要準備什麼', [{'document_id': 'd1', 'body': '帶筆電，另見未提供的d2'}])


def test_source_context_carries_version_and_current_flag():
    content = model.answer_content('新人報到', [dict(document_id='d1', body='三樓', current=0, title='報到指南', metadata='{"version":1}')])
    assert content['sources'][0]['is_current'] is False
    assert content['sources'][0]['version'] == 1
    assert content['sources'][0]['title'] == '報到指南'


def test_insufficient_evidence_can_abstain_without_fabricated_citation(monkeypatch):
    monkeypatch.setattr(model, 'chat', lambda *args: {'answerable': False, 'answer': '猜測薪資八萬元', 'citations': []})
    result = model.answer({}, '薪資多少', [{'document_id': 'd1', 'body': '新人報到'}])
    assert result['citations'] == []
    assert '資料不足' in result['answer'] and '八萬' not in result['answer']


@pytest.mark.parametrize('value', [
    {'answer': '未聲明能否回答', 'citations': ['d1']},
    {'answerable': True, 'answer': '猜測', 'citations': []},
    {'answerable': 'false', 'answer': '猜測', 'citations': ['d1']},
    {'answerable': False, 'answer': '不足', 'citations': ['other-company']},
])
def test_invalid_or_foreign_citations_are_rejected(monkeypatch, value):
    monkeypatch.setattr(model, 'chat', lambda *args: value)
    with pytest.raises(ValueError):
        model.answer({}, '問題', [{'document_id': 'd1', 'body': '來源'}])


def test_local_chat_bounded_context_no_thinking_and_truncation_rejected(monkeypatch):
    captured = []
    def request(config, path, payload):
        captured.append(payload)
        return {'done': True, 'done_reason': 'length', 'message': {'content': '{"answer":"部分答案"}'}}
    monkeypatch.setattr(model, 'request', request)
    with pytest.raises(ValueError, match='Incomplete'):
        model.chat({'model': 'local'}, '指示', '問題', {'type': 'object'})
    assert captured[0]['think'] is False
    assert captured[0]['options']['num_ctx'] == 16384


@pytest.mark.parametrize('extra', [{}, {'done': 'true'}, {'done': 1}, {'done': True}, {'done': True, 'done_reason': 'error'}])
def test_incomplete_completion_metadata_is_rejected(monkeypatch, extra):
    monkeypatch.setattr(model, 'request', lambda *args: dict(extra, message={'content': '{"answer":"不完整"}'}))
    with pytest.raises(ValueError, match='Incomplete'):
        model.chat({'model': 'local'}, '指示', '問題', {'type': 'object'})


def test_oversized_context_fails_before_model_can_silently_drop_sources(monkeypatch):
    monkeypatch.setattr(model, 'request', lambda *args: pytest.fail('oversized prompt sent'))
    with pytest.raises(ValueError, match='context'):
        model.chat({'model': 'local'}, '指示', '字' * 10000, {'type': 'object'})


def test_six_full_cjk_chunks_fit_the_context_budget():
    # Formal-document search returns up to six 1200-character sections.
    documents = [dict(document_id=f'd{i}', body='新人報到地點' * 200, title='報到說明') for i in range(6)]
    assert model.fit_documents('新人報到地點在哪裡？', documents, '2026-10-23') == documents


def test_sources_that_do_not_fit_are_dropped_from_the_lowest_rank_whole():
    documents = [dict(document_id=f'd{i}', body='字' * 3000) for i in range(6)]
    sent = model.fit_documents('問題', documents)
    assert sent == documents[:len(sent)] and 0 < len(sent) < 6
    assert model.fit_documents('問題', [dict(document_id='big', body='字' * 20000)]) == []


def test_answer_content_carries_as_of_for_planned_dates(monkeypatch):
    captured = []
    def chat(config, system, prompt, schema):
        captured.append((system, json.loads(prompt)))
        return {'answerable': True, 'answer': '預計10月26日發卡', 'citations': ['d1']}
    monkeypatch.setattr(model, 'chat', chat)
    model.answer({}, '門禁卡發了嗎', [{'document_id': 'd1', 'body': '10月26日發卡'}], '2026-10-20')
    system, content = captured[0]
    assert content['as_of'] == '2026-10-20'
    assert 'as_of' in system and '預計' in system and '核准人' in system


def test_gateway_records_sent_count_and_refuses_when_top_source_is_too_large(monkeypatch):
    from app.ai import gateway
    monkeypatch.setattr(model, 'settings', lambda company: dict(enabled=True, base_url='http://127.0.0.1:11434', model='local'))
    def doc(i, size):
        return dict(document_id=f'd{i}', body='字' * size, roles='["admin"]', metadata=json.dumps(dict(company_id='food', classification='internal')))
    prepared = gateway.prepare('food', 'admin', 'rag', '問題', [doc(i, 3000) for i in range(6)], as_of='2026-10-23')
    assert prepared.info['route'] == 'local' and prepared.info['source_count'] == 6
    assert 0 < prepared.info['sent_count'] < 6
    assert [d['document_id'] for d in prepared.content['sources']] == [d['document_id'] for d in prepared.documents]
    blocked = gateway.prepare('food', 'admin', 'rag', '問題', [doc(0, 20000)])
    assert blocked.info['route'] == 'none' and blocked.info['reason'] == 'context_too_large' and blocked.content is None
    monkeypatch.setattr(model, 'settings', lambda company: dict(enabled=False, base_url='', model=''))
    assert gateway.prepare('food', 'admin', 'rag', '問題', [doc(0, 20000)]).info['reason'] == 'model_disabled'
