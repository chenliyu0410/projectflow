import json
import zipfile
import pytest
from app.rag import parsing, chunking, retrieval, provider


def test_text_csv_and_limits(tmp_path):
    p = tmp_path / 'text'
    p.write_text('合約期限\n十月到期', encoding='utf-8')
    assert parsing.parse_file(p, 'x.txt')[0]['text'].startswith('合約')
    p.write_text('名稱,金額\n專案,120', encoding='utf-8')
    assert parsing.parse_file(p, 'x.csv')[1]['text'] == '名稱: 專案 | 金額: 120'
    with pytest.raises(ValueError, match='unsupported_format'):
        parsing.parse_file(p, 'x.exe')
    p.write_text('a' * (parsing.MAX_TEXT + 1))
    with pytest.raises(ValueError, match='text_limit'):
        parsing.parse_file(p, 'x.txt')


def test_docx_and_bomb(tmp_path):
    p = tmp_path / 'x.docx'
    xml = '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>契約</w:t></w:r></w:p></w:body></w:document>'
    with zipfile.ZipFile(p, 'w') as z:
        z.writestr('word/document.xml', xml)
    assert parsing.parse_file(p, p.name)[0]['text'] == '契約'
    with zipfile.ZipFile(p, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr('word/document.xml', 'a' * 100000)
    with pytest.raises(ValueError, match='archive_limit'):
        parsing.parse_file(p, p.name)


def test_chinese_chunks_and_parent_ids():
    chunks = chunking.build_chunks([{'text': '中' * 1500, 'locator': {'page': 1}}, {'text': '中' * 400, 'locator': {'page': 2}}])
    assert all(len(c['text']) <= 400 and len(c['parent_text']) <= 1200 for c in chunks)
    assert chunks[0]['locator']['start_char'] == 0
    assert chunks[1]['locator']['start_char'] == 0
    assert chunks[1]['locator']['end_char'] == len(chunks[1]['parent_text'])
    matched = retrieval.rank('中中', [dict(chunks[1], chunk_id='nonzero-child')], budget=75)[0]
    assert matched['locator']['end_char'] == 75 and len(matched['excerpt']) == 75
    assert chunks[0]['parent_id'] != chunks[-1]['parent_id']
    with pytest.raises(ValueError, match='chunk_limit'):
        chunking.build_chunks([{'text': '中' * 100000}])


def test_retrieval_positive_only_and_budget():
    docs = [dict(chunk_id='a', parent_id='p', text='合約期限十月到期', parent_text='合約期限十月到期', embedding=[1, 0]), dict(chunk_id='b', parent_id='q', text='水果採購', parent_text='水果採購', embedding=[0, 1])]
    assert retrieval.rank('合約', docs)[0]['chunk_id'] == 'a'
    assert retrieval.rank('不存在', docs) == []
    assert retrieval.rank('不存在', docs, [-1, -1]) == []
    assert retrieval.rank('不存在', docs, [1, 0])[0]['chunk_id'] == 'a'
    assert len(retrieval.rank('合約', docs, budget=3)[0]['excerpt']) == 3
    assert '契約' in retrieval.expand_query('合約', '前文')


CONFIG = dict(enabled=True, base_url='http://127.0.0.1:11434', model='local', embedding_model='embed')


def test_embed_batch_validation(monkeypatch):
    sizes = []
    def request(config, path, payload):
        sizes.append(len(payload['input']))
        return {'embeddings': [[1, 0] for _ in payload['input']]}
    monkeypatch.setattr(provider, '_request', request)
    assert len(provider.embed(CONFIG, ['x'] * 17)) == 17
    assert sizes == [8, 8, 1]
    monkeypatch.setattr(provider, '_request', lambda *args: {'embeddings': [[0, 0]]})
    with pytest.raises(ValueError, match='invalid_embeddings'):
        provider.embed(CONFIG, ['x'])


def test_answer_citations_and_refusal(monkeypatch):
    sources = [{'source_id': 'a', 'excerpt': '來源', 'secret': 'excluded'}]
    def request(config, path, payload):
        assert 'secret' not in payload['messages'][1]['content']
        return {'message': {'content': json.dumps({'answer': '來源說明', 'citations': ['unknown']})}}
    monkeypatch.setattr(provider, '_request', request)
    with pytest.raises(ValueError, match='invalid_citations'):
        provider.answer(CONFIG, '問題', sources)
    monkeypatch.setattr(provider, '_request', lambda *args: {'message': {'content': json.dumps({'answer': '資料不足，無法回答', 'evidence': [], 'blocks': [], 'calculation': {'operation': 'none', 'operands': [], 'unit': ''}})}})
    assert provider.answer(CONFIG, '問題', sources)['citations'] == []


def test_model_selects_evidence_ids_and_server_calculates(monkeypatch):
    sources = [{'source_id': 'source-a', 'title': '材料表', 'version': 2, 'excerpt': '甲 小計 321\n乙 小計 79', 'secret': 'excluded'}]
    def request(config, path, payload):
        catalog = json.loads(payload['messages'][1]['content'])['sources']
        assert payload['options']['num_ctx'] == 16384
        assert catalog == [dict(evidence_id='E1', title='材料表', project_title='', version=2, text='甲 小計 321'),
                           dict(evidence_id='E2', title='材料表', project_title='', version=2, text='乙 小計 79')]
        return {'message': {'content': json.dumps(dict(answer='不要採信模型自行計算的 999', evidence=['E1', 'E2'], blocks=[], calculation=dict(
            operation='add', unit='元', operands=[dict(number_id='E1:321', label='甲小計'), dict(number_id='E2:79', label='乙小計')])) )}}
    monkeypatch.setattr(provider, '_request', request)
    result = provider.answer(CONFIG, '兩筆合計？', sources)
    assert '321 + 79 = 400 元' in result['answer']
    assert result['citations'] == ['source-a']


def test_transport_error_is_sanitized(monkeypatch):
    def broken(**kwargs):
        raise RuntimeError('sensitive endpoint')
    monkeypatch.setattr(provider.httpx, 'AsyncClient', broken)
    with pytest.raises(ValueError, match='^model_transport_error$'):
        provider.embed(CONFIG, ['x'])


def test_blank_pdf_no_ocr_and_page_limit(tmp_path, monkeypatch):
    from pypdf import PdfWriter
    p = tmp_path / 'blank.pdf'
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    with p.open('wb') as handle:
        writer.write(handle)
    with pytest.raises(ValueError, match='no_extractable_text'):
        parsing.parse_file(p, p.name)
    monkeypatch.setattr(parsing, 'MAX_PAGES', 0)
    with pytest.raises(ValueError, match='page_limit'):
        parsing.parse_file(p, p.name)


@pytest.mark.parametrize('vector', [[float('nan')], [float('inf')], [True], [], [1] * 4097])
def test_invalid_vectors(monkeypatch, vector):
    monkeypatch.setattr(provider, '_request', lambda *args: {'embeddings': [vector]})
    with pytest.raises(ValueError, match='invalid_embeddings'):
        provider.embed(CONFIG, ['x'])


def test_embed_total_deadline(monkeypatch):
    times = iter([0, 0, 121])
    monkeypatch.setattr(provider.time, 'monotonic', lambda: next(times))
    monkeypatch.setattr(provider, '_request', lambda *args: {'embeddings': [[1]]})
    with pytest.raises(ValueError, match='embedding_timeout'):
        provider.embed(CONFIG, ['x'])


def test_chat_total_deadline(monkeypatch):
    times = iter([0, 61])
    monkeypatch.setattr(provider.time, 'monotonic', lambda: next(times))
    monkeypatch.setattr(provider, '_request', lambda *args: {'message': {'content': '{}'}})
    with pytest.raises(ValueError, match='generation_timeout'):
        provider.answer(CONFIG, '問題', [{'source_id': 'a', 'excerpt': '來源'}])


def _text_pdf(path, text='PDF evidence'):
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=300)
    font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
    page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
    stream = DecodedStreamObject()
    stream.set_data(('BT /F1 12 Tf 20 100 Td (' + text + ') Tj ET').encode('ascii'))
    page[NameObject('/Contents')] = writer._add_object(stream)
    with path.open('wb') as handle:
        writer.write(handle)


def test_pdf_text_and_decoded_stream_limits(tmp_path, monkeypatch):
    path = tmp_path / 'text.pdf'
    _text_pdf(path)
    assert parsing.parse_file(path, path.name) == [{'text': 'PDF evidence', 'locator': {'page': 1}}]
    monkeypatch.setattr(parsing, 'MAX_PDF_PAGE_STREAM', 10)
    with pytest.raises(ValueError, match='text_limit'):
        parsing.parse_file(path, path.name)
    monkeypatch.setattr(parsing, 'MAX_PDF_PAGE_STREAM', 1000)
    monkeypatch.setattr(parsing, 'MAX_PDF_TOTAL_STREAM', 10)
    with pytest.raises(ValueError, match='text_limit'):
        parsing.parse_file(path, path.name)


def test_pdf_wall_timeout(tmp_path, monkeypatch):
    path = tmp_path / 'text.pdf'
    _text_pdf(path)
    monkeypatch.setattr(parsing, 'PDF_TIMEOUT', 0)
    with pytest.raises(ValueError, match='parse_timeout'):
        parsing.parse_file(path, path.name)


def test_request_total_deadline_cancels_slow_headers_and_body():
    import time, threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    class Slow(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def do_POST(self):
            self.rfile.read(int(self.headers['Content-Length']))
            time.sleep(.18)
            self.send_response(200);self.send_header('Content-Length','20');self.end_headers()
            self.wfile.write(b'{');self.wfile.flush()
            time.sleep(.5)
    server=ThreadingHTTPServer(('127.0.0.1',0),Slow)
    server.daemon_threads=True
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        # Warm up the async runtime/client creation before measuring the deadline.
        started=time.monotonic()
        config=dict(CONFIG,base_url=f'http://127.0.0.1:{server.server_port}',_remaining_timeout=.3,_deadline=started+.3,_timeout_code='generation_timeout')
        with pytest.raises(ValueError,match='generation_timeout'):
            provider._request(config,'/api/chat',{})
        assert time.monotonic()-started < .40
    finally:
        server.shutdown();server.server_close();thread.join()


def test_authorization_exception_is_not_converted_to_model_failure(monkeypatch):
    from fastapi import HTTPException
    def deny(): raise HTTPException(401,'login expired')
    with pytest.raises(HTTPException) as error:
        provider._request(dict(CONFIG,_authorize=deny),'/api/chat',{})
    assert error.value.status_code==401
    def denied_request(*args): raise HTTPException(404,'source revoked')
    monkeypatch.setattr(provider,'_request',denied_request)
    with pytest.raises(HTTPException):
        provider.answer(CONFIG,'問題',[{'source_id':'a','excerpt':'文字'}])


def test_known_negative_keeps_grounded_block_and_prompt_distinguishes_absence(monkeypatch):
    def request(config,path,payload):
        assert '否定與未定同樣是可回答的事實' in payload['messages'][0]['content']
        return {'message':{'content':json.dumps({'answer':'目前沒有已核准的替代設備。','evidence':['E1'],'blocks':[{'text':'目前沒有已核准的替代設備。','evidence':['E1']}],'calculation':{'operation':'none','operands':[],'unit':''}})}}
    monkeypatch.setattr(provider,'_request',request)
    result=provider.answer(CONFIG,'核准的替代設備是什麼？',[{'source_id':'a','excerpt':'替代設備尚在評選，沒有已核准的型號。'}])
    assert result['blocks'][0]['source_ids']==['a'] and result['citations']==['a']
