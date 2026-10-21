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
        model.chat({'model': 'local'}, '指示', '字' * 9000, {'type': 'object'})
