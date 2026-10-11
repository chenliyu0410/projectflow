import hashlib
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import AttachmentQuota, AuditLog, Document, DocumentVersion, Node
from test_report_lifecycle import setup, switch
from test_projects_nodes import login


@pytest.fixture(autouse=True)
def files(tmp_path, monkeypatch):
    root = tmp_path / 'files'
    root.mkdir()
    monkeypatch.setenv('PF_ATTACHMENT_ROOT', str(root))
    monkeypatch.setenv('PF_ATTACHMENT_QUOTA_BYTES', '1000000000')
    return root


def upload(client, nid, data=b'original', name='文件.txt', path=None):
    return client.post(path or f'/nodes/{nid}/documents', params={'filename': name, 'expected_version': 1, 'comment': '初稿'},
        content=data, headers={'Content-Type': 'application/octet-stream'})


def test_document_versions_persist_with_history_and_audit(client, engine):
    nid, _, _ = setup(client, engine)
    first = upload(client, nid)
    assert first.status_code == 201, first.text
    doc = first.json()['document_id']
    edited = client.post(f'/documents/{doc}/text', json={'expected_version': 1, 'content': '新版內容', 'comment': '修正'})
    assert edited.status_code == 201, edited.text
    assert edited.json()['version'] == 2
    assert client.get(f'/documents/{doc}/versions/1/download').content == b'original'
    assert client.get(f'/documents/{doc}/versions/2/text').json() == {'content': '新版內容'}
    switch(client, 'ming')
    versions = client.get(f'/documents/{doc}/versions').json()
    assert [v['version'] for v in versions['items']] == [2, 1]
    assert versions['items'][0]['comment'] == '修正'
    assert versions['items'][0]['sha256'] == hashlib.sha256('新版內容'.encode()).hexdigest()
    assert 'storage_key' not in str(versions)
    assert client.get(f'/nodes/{nid}/documents').json()['items'][0]['version'] == 2
    with Session(engine) as db:
        assert db.scalar(select(AttachmentQuota.charged_bytes)) == len(b'original') + len('新版內容'.encode())
        assert len(db.scalars(select(AuditLog).where(AuditLog.action == 'document.version')).all()) == 2


def test_conflict_preserves_history_and_rejects_stale_upload(client, engine, files):
    nid, _, _ = setup(client, engine)
    doc = upload(client, nid).json()['document_id']
    path = f'/documents/{doc}/text'
    assert client.post(path, json={'expected_version': 1, 'content': 'new'}).status_code == 201
    assert client.post(path, json={'expected_version': 1, 'content': 'stale'}).status_code == 409
    assert upload(client, nid, path=f'/documents/{doc}/versions').status_code == 409
    assert len(client.get(f'/documents/{doc}/versions').json()['items']) == 2
    assert len([p for p in files.iterdir() if not p.name.startswith(".")]) == 2


def test_readonly_foreign_and_revoked_node_access(client, engine):
    nid, _, users = setup(client, engine)
    doc = upload(client, nid).json()['document_id']
    switch(client, 'lin')
    assert client.get(f'/nodes/{nid}/documents').json()['can_write'] is False
    assert client.get(f'/documents/{doc}/versions/1/download').status_code == 200
    assert upload(client, nid).status_code == 403
    assert client.post(f'/documents/{doc}/text', json={'expected_version': 1, 'content': 'no'}).status_code == 403
    client.post('/auth/logout')
    login(client, 'electronics', 'elaine')
    for path in [f'/nodes/{nid}/documents', f'/documents/{doc}/versions', f'/documents/{doc}/versions/1/text', f'/documents/{doc}/versions/1/download']:
        assert client.get(path).status_code == 404
    assert upload(client, nid, path=f'/documents/{doc}/versions').status_code == 404
    switch(client, 'ming')
    with Session(engine) as db:
        db.get(Node, nid).owner_user_id = users['yu']
        db.commit()
    assert client.get(f'/documents/{doc}/versions').status_code == 404


@pytest.mark.parametrize('data,name,status', [(b'', 'empty.txt', 422), (b'bad', 'a.pdf', 422), (b'x', '../x.txt', 422),
    (b'x', 'x.exe', 415), (b'\xff', 'x.csv', 422), (b'a\x00b', 'x.txt', 422), (b'x'*10000001, 'large.txt', 413)], ids=['empty','signature','path','extension','encoding','null','size'])
def test_invalid_upload_has_no_visible_version(client, engine, files, data, name, status):
    nid, _, _ = setup(client, engine)
    assert upload(client, nid, data, name).status_code == status
    assert client.get(f'/nodes/{nid}/documents').json()['items'] == []
    assert [p for p in files.iterdir() if not p.name.startswith(".")] == []


def test_binary_replacement_and_quota(client, engine, monkeypatch):
    nid, _, _ = setup(client, engine)
    doc = upload(client, nid, b'%PDF-1.4\nold', 'spec.pdf').json()['document_id']
    assert client.get(f'/documents/{doc}/versions/1/text').status_code == 415
    assert client.post(f'/documents/{doc}/text', json={'expected_version': 1, 'content': 'no'}).status_code == 415
    replacement = upload(client, nid, b'%PDF-1.4\nnew', 'spec.pdf', f'/documents/{doc}/versions')
    assert replacement.status_code == 201 and replacement.json()['version'] == 2
    monkeypatch.setenv('PF_ATTACHMENT_QUOTA_BYTES', '1')
    assert upload(client, nid).status_code == 413
    assert len(client.get(f'/nodes/{nid}/documents').json()['items']) == 1


def test_storage_failure_does_not_advance_version(client, engine, monkeypatch):
    from app.services import document_store
    nid, _, _ = setup(client, engine)
    doc = upload(client, nid).json()['document_id']
    monkeypatch.setattr(document_store.os, 'replace', lambda *args: (_ for _ in ()).throw(OSError('disk failed')))
    assert client.post(f'/documents/{doc}/text', json={'expected_version': 1, 'content': 'new'}).status_code == 503
    assert client.get(f'/documents/{doc}/versions').json()['current_version'] == 1
    assert client.get(f'/documents/{doc}/versions/1/download').content == b'original'


def test_project_root_and_soft_deleted_node(client, engine):
    nid, pid, _ = setup(client, engine, 'yu')
    first = upload(client, nid, path=f'/projects/{pid}/documents')
    assert first.status_code == 201
    assert client.get(f'/projects/{pid}/documents').json()['items'][0]['document_id'] == first.json()['document_id']
    doc = upload(client, nid).json()['document_id']
    assert client.delete(f'/nodes/{nid}').status_code == 200
    assert client.get(f'/documents/{doc}/versions').status_code == 404
