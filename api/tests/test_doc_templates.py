import io
import re
import threading
import zipfile
from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models import AuditLog, DocumentTemplate, DocumentVersion
from app.services import doc_template_service as service
from test_projects_nodes import login
from test_report_lifecycle import setup, switch


@pytest.fixture(autouse=True)
def files(tmp_path, monkeypatch):
    root = tmp_path / 'files'
    root.mkdir()
    monkeypatch.setenv('PF_ATTACHMENT_ROOT', str(root))
    monkeypatch.setenv('PF_ATTACHMENT_QUOTA_BYTES', '1000000000')
    monkeypatch.setattr(service, 'today', lambda: date(2026, 10, 23))
    return root


def text_of(data):
    xml = zipfile.ZipFile(io.BytesIO(data)).read('word/document.xml').decode()
    return re.sub(r'\|+', '|', re.sub(r'<[^>]+>', '|', xml))


def samples(client):
    response = client.post('/document-templates/samples')
    assert response.status_code == 201, response.text
    return {t['name']: t for t in response.json()['items']}


def upload(client, data, name='自訂', filename='自訂.docx'):
    return client.post('/document-templates', params={'filename': filename, 'name': name}, content=data,
                       headers={'Content-Type': 'application/octet-stream'})


def docx_with(*paragraphs, rels=None):
    from docx import Document as Word
    word = Word()
    for text in paragraphs:
        word.add_paragraph(text)
    buffer = io.BytesIO()
    word.save(buffer)
    if rels is None:
        return buffer.getvalue()
    source = zipfile.ZipFile(io.BytesIO(buffer.getvalue()))
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w') as target:
        for item in source.infolist():
            data = source.read(item)
            if item.filename == 'word/_rels/document.xml.rels':
                data = data.replace(b'</Relationships>', rels + b'</Relationships>')
            target.writestr(item, data)
    return output.getvalue()


def generate(client, nid, template, values, lines=None):
    return client.post(f'/nodes/{nid}/documents/from-template', json={'template_id': template['id'], 'values': values, 'lines': lines or []})


MEETING = {'會議名稱': '十月新人報到準備會議', '日期時間': '2026-10-12　10:00–10:30', '出席者': '林怡安、陳柏宇、王雅婷',
           '決議': '新人 10/26 09:00 一樓接待區報到', '待辦': '陳柏宇 10/23 備妥筆電\n王雅婷 10/22 門禁卡'}


def test_meeting_template_scan_settings_generate_and_download(client, engine):
    nid, _, _ = setup(client, engine, 'yu')
    meeting = samples(client)['會議紀錄']
    assert [f['name'] for f in meeting['fields']] == ['會議名稱', '日期時間', '出席者', '決議', '待辦']
    assert meeting['numbering'] == 'MTG-{年}-{序號3位}' and meeting['has_lines'] is False
    fields = [{**f, 'required': f['name'] != '待辦'} for f in meeting['fields']]
    saved = client.put(f'/document-templates/{meeting["id"]}', json={'expected_version': 1, 'name': '會議紀錄', 'category': '會議',
        'fields': fields, 'numbering': meeting['numbering'], 'tax_rate': '5', 'rounding': 'half_up'})
    assert saved.status_code == 200, saved.text
    assert saved.json()['version'] == 2
    missing = generate(client, nid, meeting, {**MEETING, '決議': ' '})
    assert missing.status_code == 422 and '決議' in missing.json()['detail']
    created = generate(client, nid, meeting, MEETING)
    assert created.status_code == 201, created.text
    body = created.json()
    assert body['filename'] == '會議紀錄-MTG-2026-001.docx' and body['version'] == 1 and body['from_template'] is True
    content = client.get(f'/documents/{body["document_id"]}/versions/1/download').content
    text = text_of(content)
    for expected in ['毛研食品　會議紀錄', 'MTG-2026-001', '十月新人報到準備會議', '游專案', '王雅婷 10/22 門禁卡']:
        assert expected in text
    assert '{{' not in text
    listed = client.get(f'/nodes/{nid}/documents').json()['items']
    assert listed[0]['from_template'] is True


def test_quote_totals_numbering_and_regenerate(client, engine):
    nid, _, _ = setup(client, engine, 'yu')
    quote = samples(client)['報價單']
    lines = [{'品項': '成貓主食罐 鮪魚 85g', '數量': '2000', '單價': '32'}, {'品項': '成貓主食罐 雞肉 85g', '數量': 1000, '單價': 30}]
    values = {'客戶名稱': '好毛寵物用品（虛構）', '有效期限': '2026-11-22'}
    assert generate(client, nid, quote, values, []).status_code == 422
    first = generate(client, nid, quote, values, lines)
    assert first.status_code == 201, first.text
    text = text_of(client.get(f'/documents/{first.json()["document_id"]}/versions/1/download').content)
    for expected in ['Q-2026-1023-01', '64,000', '30,000', '94,000', '4,700', '98,700']:
        assert expected in text
    second = generate(client, nid, quote, values, lines).json()
    assert second['filename'] == '報價單-Q-2026-1023-02.docx'
    doc = second['document_id']
    detail = client.get(f'/documents/{doc}/fill').json()
    assert detail['number'] == 'Q-2026-1023-02' and detail['values'] == values and len(detail['lines']) == 2
    again = client.post(f'/documents/{doc}/regenerate', json={'expected_version': 1, 'values': {**values, '有效期限': '2026-12-01'}, 'lines': lines[:1]})
    assert again.status_code == 201, again.text
    assert again.json()['version'] == 2 and again.json()['filename'] == second['filename']
    newer = text_of(client.get(f'/documents/{doc}/versions/2/download').content)
    assert '2026-12-01' in newer and 'Q-2026-1023-02' in newer and '67,200' in newer
    assert '2026-11-22' in text_of(client.get(f'/documents/{doc}/versions/1/download').content)
    stale = client.post(f'/documents/{doc}/regenerate', json={'expected_version': 1, 'values': values, 'lines': lines})
    assert stale.status_code == 409


def test_work_order_number_and_concurrent_numbers_do_not_repeat(client, engine):
    nid, _, _ = setup(client, engine, 'yu')
    order = samples(client)['工單']
    made = generate(client, nid, order, {'工單名稱': '新人筆電準備', '負責人': '陳柏宇', '期限': '2026-10-23',
        '需求說明': '準備 2 台筆電', '完成條件': '可開機登入'})
    assert made.status_code == 201, made.text
    assert made.json()['filename'] == '工單-WO-001.docx'
    with Session(engine) as db:
        org = db.get(DocumentTemplate, order['id']).organization_id
    factory = sessionmaker(bind=engine)
    results, errors = [], []

    def worker():
        try:
            with factory() as db:
                results.append(service.next_number(db, org, order['id'], 'WO-{序號3位}', date(2026, 10, 23)))
        except Exception as error:  # pragma: no cover - surfaced by the assertion below
            errors.append(error)
    threads = [threading.Thread(target=worker) for _ in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert not errors and len(set(results)) == 6 and 'WO-001' not in results


def test_permissions_and_company_isolation(client, engine):
    nid, _, _ = setup(client, engine, 'yu')
    meeting = samples(client)['會議紀錄']
    doc = generate(client, nid, meeting, MEETING).json()['document_id']
    switch(client, 'lin')
    assert client.post('/document-templates/samples').status_code == 403
    assert upload(client, service.sample_docx(service.SAMPLES[0])).status_code == 403
    assert client.get(f'/nodes/{nid}/documents').json()['can_write'] is False
    assert generate(client, nid, meeting, MEETING).status_code == 403
    assert client.get('/document-templates').json()['can_manage'] is False
    switch(client, 'ming')
    assert client.put(f'/document-templates/{meeting["id"]}', json={'expected_version': 1, 'name': 'x', 'category': '', 'fields': [],
        'numbering': 'A-{序號3位}', 'tax_rate': '5', 'rounding': 'half_up'}).status_code == 403
    client.post('/auth/logout')
    login(client, 'electronics', 'elaine')
    assert client.get('/document-templates').json()['items'] == []
    assert client.get(f'/documents/{doc}/fill').status_code == 404
    assert client.post(f'/document-templates/{meeting["id"]}/status', json={'status': 'disabled'}).status_code in {403, 404}
    assert generate(client, nid, meeting, MEETING).status_code == 404


def test_disable_and_delete_keep_generated_documents(client, engine):
    nid, _, _ = setup(client, engine, 'yu')
    meeting = samples(client)['會議紀錄']
    doc = generate(client, nid, meeting, MEETING).json()['document_id']
    assert client.post(f'/document-templates/{meeting["id"]}/status', json={'status': 'disabled'}).status_code == 200
    assert generate(client, nid, meeting, MEETING).status_code == 409
    switch(client, 'ming')
    assert all(t['id'] != meeting['id'] for t in client.get('/document-templates').json()['items'])
    switch(client, 'yu')
    assert client.post(f'/document-templates/{meeting["id"]}/status', json={'status': 'deleted'}).status_code == 200
    assert all(t['id'] != meeting['id'] for t in client.get('/document-templates').json()['items'])
    assert client.get(f'/documents/{doc}/versions/1/download').status_code == 200


@pytest.mark.parametrize('paragraphs,rels,reason', [
    (['{% if x %}秘密{% endif %}'], None, '只能使用'),
    (['{{ 名稱|upper }}'], None, '只能使用'),
    (['{{ __class__ }}'], None, '無效'),
    (['{{ 沒關'], None, '未關閉'),
    (['{{ 小計 }}'], None, '明細表'),
    (['正常 {{ 名稱 }}'], b'<Relationship Id="rIdX" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" Target="https://example.com" TargetMode="External"/>', '外部連結'),
], ids=['logic', 'filter', 'dunder', 'unclosed', 'totals', 'external'])
def test_unsafe_templates_are_rejected_with_reason(client, engine, paragraphs, rels, reason):
    setup(client, engine, 'yu')
    response = upload(client, docx_with(*paragraphs, rels=rels))
    assert response.status_code == 422 and reason in response.json()['detail'], response.text
    with Session(engine) as db:
        assert db.scalar(select(DocumentTemplate.id)) is None


def rewrite(data, changes):
    """Copy a .docx, applying {name: fn(bytes)->bytes} and adding parts whose name is new."""
    source = zipfile.ZipFile(io.BytesIO(data))
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w') as target:
        for item in source.infolist():
            content = source.read(item)
            target.writestr(item, changes.pop(item.filename, lambda x: x)(content))
        for name, change in changes.items():
            target.writestr(name, change(b''))
    return output.getvalue()


ATTRIBUTE = b'<w:bookmarkStart w:id="9" w:name="X{{ range(99999)|length }}"/>'
ORPHAN_HEADER = (b'<w:hdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:p><w:r><w:t>'
                 b'{% for a in range(99999) %}{% endfor %}</w:t></w:r></w:p></w:hdr>')


@pytest.mark.parametrize('changes', [
    {'word/document.xml': lambda x: x.replace(b'<w:body>', b'<w:body><w:p>' + ATTRIBUTE + b'</w:p>', 1)},
    {'word/header9.xml': lambda _: ORPHAN_HEADER},
    {'docProps/core.xml': lambda x: x.replace(b'</cp:coreProperties>', '<dc:title>{{ 名稱 }}</dc:title></cp:coreProperties>'.encode())},
    {'word/document.xml': lambda x: x.replace(b'<w:body>', b'<w:body><w:p><w:r><w:t>&#123;&#123; 7*7 }}</w:t></w:r></w:p>', 1)},
    {'word/document.xml': lambda x: x.replace(b'<w:body>', b'<w:body><w:p><w:bookmarkStart w:id="8" w:name="&#x7B;&#123; 7*7 }}"/></w:p>', 1)},
], ids=['attribute', 'orphan-header', 'properties', 'char-ref-text', 'char-ref-attribute'])
def test_tags_outside_visible_text_are_rejected(client, engine, changes):
    setup(client, engine, 'yu')
    response = upload(client, rewrite(docx_with('正常 {{ 名稱 }}'), changes))
    assert response.status_code == 422, response.text
    assert any(word in response.json()['detail'] for word in ('代號', '只能使用', '無效'))


def test_oversized_unpacked_and_non_docx_are_rejected(client, engine):
    setup(client, engine, 'yu')
    bomb = io.BytesIO()
    with zipfile.ZipFile(bomb, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('[Content_Types].xml', '<Types/>')
        archive.writestr('word/document.xml', b'<a/>' + b' ' * 31_000_000)
    assert '過大' in upload(client, bomb.getvalue()).json()['detail']
    assert upload(client, b'not a zip').status_code == 422
    assert upload(client, b'x', filename='a.txt').status_code == 415


def test_values_with_markup_stay_literal_and_audit_has_no_content(client, engine):
    nid, _, _ = setup(client, engine, 'yu')
    meeting = samples(client)['會議紀錄']
    tricky = {**MEETING, '決議': '{{編號}} <w:t>&amp; {% for x in y %}'}
    made = generate(client, nid, meeting, tricky)
    assert made.status_code == 201, made.text
    content = client.get(f'/documents/{made.json()["document_id"]}/versions/1/download').content
    from docx import Document as Word
    word = Word(io.BytesIO(content))
    cells = [c.text for t in word.tables for r in t.rows for c in r.cells]
    assert '{{編號}} <w:t>&amp; {% for x in y %}' in cells
    with Session(engine) as db:
        logs = db.scalars(select(AuditLog).where(AuditLog.action.like('doc_template.%'))).all()
        assert {a.action for a in logs} == {'doc_template.create', 'doc_template.generate'}
        assert '新人' not in str([a.payload for a in logs])
        assert db.scalar(select(DocumentVersion.fill_values))['values']['決議'] == tricky['決議']


def test_replace_file_keeps_settings_and_versions(client, engine):
    setup(client, engine, 'yu')
    created = upload(client, docx_with('{{ 客戶 }} {{ 日期 }} {{編號}}'))
    assert created.status_code == 201, created.text
    template = created.json()
    assert [f['name'] for f in template['fields']] == ['客戶', '日期']
    fields = [{**template['fields'][0], 'label': '客戶名稱', 'required': True}, {**template['fields'][1], 'type': 'date'}]
    bad = client.put(f'/document-templates/{template["id"]}', json={'expected_version': 1, 'name': '自訂', 'category': '',
        'fields': fields[:1], 'numbering': 'C-{序號3位}', 'tax_rate': '5', 'rounding': 'half_up'})
    assert bad.status_code == 422
    assert client.put(f'/document-templates/{template["id"]}', json={'expected_version': 1, 'name': '自訂', 'category': '',
        'fields': fields, 'numbering': 'C/{序號3位}', 'tax_rate': '5', 'rounding': 'half_up'}).status_code == 422
    assert client.put(f'/document-templates/{template["id"]}', json={'expected_version': 1, 'name': '自訂', 'category': '',
        'fields': fields, 'numbering': 'C-{序號3位}', 'tax_rate': '5', 'rounding': 'half_up'}).status_code == 200
    replaced = client.post(f'/document-templates/{template["id"]}/file', params={'filename': '新版.docx', 'expected_version': 2},
        content=docx_with('{{ 客戶 }} {{ 備註 }}'), headers={'Content-Type': 'application/octet-stream'})
    assert replaced.status_code == 201, replaced.text
    body = replaced.json()
    assert body['version'] == 3 and body['numbering'] == 'C-{序號3位}'
    assert body['fields'][0]['label'] == '客戶名稱' and body['fields'][0]['required'] is True
    assert body['fields'][1] == service.default_field('備註')
