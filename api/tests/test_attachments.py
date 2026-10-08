import hashlib
import io
import zipfile
from pathlib import Path
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import Attachment, AttachmentQuota, AuditLog, Node, TaskNote, TaskReport, User
from test_report_lifecycle import setup, switch, PAYLOAD


@pytest.fixture(autouse=True)
def files(tmp_path,monkeypatch):
    root=tmp_path/'files';root.mkdir()
    monkeypatch.setenv('PF_ATTACHMENT_ROOT',str(root))
    monkeypatch.setenv('PF_ATTACHMENT_QUOTA_BYTES','1000000000')
    return root


def upload(client,nid,data=b'hello',name='成果.txt',headers=None):
    return client.post(f'/nodes/{nid}/attachments',params={'filename':name},content=data,
                       headers={'Content-Type':'application/octet-stream',**(headers or {})})


def rows(engine):
    with Session(engine) as db:
        return [(a.id,a.state,a.size_bytes,a.report_id,a.note_id,a.deleted_at) for a in db.scalars(select(Attachment))]


def test_upload_download_hash_safe_projection_and_quota(client,engine,files):
    nid,_,_=setup(client,engine)
    r=upload(client,nid,'內容'.encode());assert r.status_code==201
    a=r.json();assert a['sha256']==hashlib.sha256('內容'.encode()).hexdigest()
    assert 'storage_key' not in r.text and str(files) not in r.text
    downloaded=client.get(f"/attachments/{a['id']}/download")
    assert downloaded.status_code==200 and downloaded.content=='內容'.encode()
    assert downloaded.headers['x-content-type-options']=='nosniff'
    assert downloaded.headers['content-disposition'].startswith('attachment;')
    quota=client.get(f'/nodes/{nid}/attachment-quota').json()
    assert quota=={'limit_bytes':1000000000,'charged_bytes':6,'remaining_bytes':999999994}
    records=client.get(f'/nodes/{nid}/records').json()['items']
    assert len(records)==1 and records[0]['type']=='attachment'
    assert records[0]['id']==a['id']


@pytest.mark.parametrize('data,name,code',[(b'','empty.txt',422),(b'x','a.exe',415),(b'x','../a.txt',422),
    (b'x','a\\b.txt',422),(b'x','a\x01.txt',422),(b'x','x'*201+'.txt',422),(b'\xff','a.txt',422),
    (b'a\x00b','a.csv',422),(b'notpdf','a.pdf',422),(b'bad','a.png',422),(b'bad','a.jpg',422),(b'bad','a.zip',422)])
def test_upload_rejects_invalid_metadata_and_content(client,engine,data,name,code):
    nid,_,_=setup(client,engine)
    r=upload(client,nid,data,name);assert r.status_code==code
    assert all(row[1]=='failed' for row in rows(engine))
    with Session(engine) as db:
        assert db.scalar(select(AttachmentQuota.charged_bytes).where(AttachmentQuota.organization_id==db.get(Node,nid).organization_id)) in (None,0)
        assert list(db.scalars(select(AuditLog).where(AuditLog.action=='attachment.upload')))==[]


def test_limits_actual_length_and_required_headers(client,engine):
    nid,_,_=setup(client,engine)
    request=client.build_request('POST',f'/nodes/{nid}/attachments?filename=a.txt',content=b'x',headers={'Content-Type':'application/octet-stream'})
    del request.headers['content-length']
    assert client.send(request).status_code==411
    assert upload(client,nid,b'x',headers={'Content-Type':'text/plain'}).status_code==415
    assert upload(client,nid,b'abc',headers={'Content-Length':'2'}).status_code==422
    assert upload(client,nid,b'abc',headers={'Content-Length':'4'}).status_code==422
    assert upload(client,nid,b'x'*10000001,headers={'Content-Length':'1'}).status_code==413
    ok=upload(client,nid,b'x'*10000000);assert ok.status_code==201
    assert upload(client,nid,b'x'*10000001).status_code==413


def test_quota_soft_delete_and_live_access(client,engine,monkeypatch):
    nid,_,users=setup(client,engine)
    monkeypatch.setenv('PF_ATTACHMENT_QUOTA_BYTES','5')
    a=upload(client,nid).json();assert 'id' in a
    assert upload(client,nid,b'x').status_code==413
    switch(client,'lin')
    assert client.get(f"/attachments/{a['id']}/download").status_code==200
    assert client.delete(f"/attachments/{a['id']}").status_code==403
    assert client.get(f'/nodes/{nid}/attachment-quota').status_code==403
    switch(client,'ming')
    with Session(engine) as db:db.get(Node,nid).owner_user_id=users['yu'];db.commit()
    assert client.get(f"/attachments/{a['id']}/download").status_code==404
    switch(client,'yu')
    assert client.delete(f"/attachments/{a['id']}").status_code==200
    assert client.get(f"/attachments/{a['id']}/download").status_code==404
    assert client.get(f'/nodes/{nid}/attachment-quota').json()['charged_bytes']==5
    assert upload(client,nid,b'x').status_code==413


def test_binding_batch_atomic_history_and_note_attachments(client,engine):
    nid,_,_=setup(client,engine)
    a=upload(client,nid).json();assert 'id' in a
    failed=client.post(f'/nodes/{nid}/reports',json={**PAYLOAD,'attachment_ids':[a['id'],'missing']})
    assert failed.status_code==422 and rows(engine)[0][3] is None
    report=client.post(f'/nodes/{nid}/reports',json={**PAYLOAD,'attachment_ids':[a['id']]})
    assert report.status_code==201 and report.json()['attachments'][0]['id']==a['id']
    assert client.delete(f"/attachments/{a['id']}").status_code==409
    switch(client,'yu')
    assert client.post(f"/reports/{report.json()['id']}/review",json={'decision':'rejected','comment':'retry'}).status_code==200
    assert client.delete(f"/attachments/{a['id']}").status_code==409
    switch(client,'ming')
    b=upload(client,nid,b'note').json()
    note=client.post(f'/nodes/{nid}/notes',json={'body':'note','attachment_ids':[b['id']]}).json()
    assert note['attachments'][0]['id']==b['id']
    assert client.post(f'/nodes/{nid}/notes',json={'body':'reuse','attachment_ids':[b['id']]}).status_code==422
    items=client.get(f'/nodes/{nid}/records').json()['items']
    assert next(x for x in items if x['type']=='report')['attachments'][0]['id']==a['id']
    assert next(x for x in items if x['type']=='note')['attachments'][0]['id']==b['id']
    assert client.delete(f"/attachments/{b['id']}").status_code==200


@pytest.mark.parametrize('fault',['before_commit','after_commit','disk_full','rename_crash','unknown_db'])
def test_upload_failure_reconciles_durable_state(client,engine,files,monkeypatch,fault):
    nid,_,_=setup(client,engine)
    from app.services import attachment_store as store
    original=Session.commit
    triggered=False
    def commit(db):
        nonlocal triggered
        ready=any(isinstance(x,Attachment) and x.state=='ready' for x in db.identity_map.values())
        if ready and not triggered and fault in {'before_commit','after_commit','unknown_db'}:
            triggered=True
            if fault=='after_commit':original(db)
            raise RuntimeError('internal database detail')
        return original(db)
    monkeypatch.setattr(Session,'commit',commit)
    if fault=='disk_full':monkeypatch.setattr(store,'write_chunk',lambda *args: (_ for _ in ()).throw(OSError('disk secret')))
    if fault=='rename_crash':monkeypatch.setattr(store,'mark_ready',lambda *args: (_ for _ in ()).throw(RuntimeError('crash secret')))
    if fault=='unknown_db':monkeypatch.setattr(store,'reconcile_upload',lambda *args,**kwargs: (_ for _ in ()).throw(RuntimeError('unavailable')))
    r=upload(client,nid)
    assert r.status_code==(201 if fault=='after_commit' else 503)
    assert 'secret' not in r.text and 'internal' not in r.text
    with Session(engine) as db:
        a=db.scalars(select(Attachment)).one();q=db.get(AttachmentQuota,a.organization_id)
        if fault=='after_commit':
            assert a.state=='ready' and q.charged_bytes==5
            assert (files/a.storage_key).read_bytes()==b'hello'
            assert len(list(db.scalars(select(AuditLog).where(AuditLog.action=='attachment.upload'))))==1
        elif fault=='unknown_db':
            assert a.state=='pending' and q.charged_bytes==5 and (files/a.storage_key).exists()
        else:
            assert a.state=='failed' and q.charged_bytes==0
            assert not (files/a.storage_key).exists() and not (files/(a.storage_key+'.part')).exists()


def test_pending_missing_root_and_file_are_safe(client,engine,files,monkeypatch):
    nid,_,_=setup(client,engine)
    a=upload(client,nid).json();assert 'id' in a
    with Session(engine) as db:
        row=db.get(Attachment,a['id']);key=row.storage_key;row.state='pending';db.commit()
    assert client.get(f"/attachments/{a['id']}/download").status_code==404
    with Session(engine) as db:db.get(Attachment,a['id']).state='ready';db.commit()
    (files/key).unlink()
    r=client.get(f"/attachments/{a['id']}/download");assert r.status_code==503 and str(files) not in r.text
    monkeypatch.setenv('PF_ATTACHMENT_ROOT',str(files/'missing'))
    assert upload(client,nid).status_code==503


def test_zip_metadata_and_office_validation(client,engine):
    nid,_,_=setup(client,engine)
    def zipped(names):
        result=io.BytesIO()
        with zipfile.ZipFile(result,'w') as z:
            for name in names:z.writestr(name,'x')
        return result.getvalue()
    assert upload(client,nid,zipped(['doc.txt']),'a.zip').status_code==201
    assert upload(client,nid,zipped(['doc.txt']),'a.docx').status_code==422
    assert upload(client,nid,zipped(['[Content_Types].xml','word/document.xml']),'a.docx').status_code==201
    assert upload(client,nid,zipped(['../bad']),'a.zip').status_code==422
    assert upload(client,nid,zipped([f'{i}.txt' for i in range(1001)]),'a.zip').status_code==422


def test_recovery_requires_stopped_api_and_cleans_only_pending(engine,files):
    from app.seed import seed_demo_data
    from app.services import attachment_recovery as recovery, attachment_store as store
    with Session(engine) as db:
        seed_demo_data(db);db.commit()
        user=db.scalars(select(User).where(User.username=='ming')).one()
        node=db.scalars(select(Node).where(Node.owner_user_id==user.id,Node.kind=='task')).one()
        a=Attachment(organization_id=user.organization_id,node_id=node.id,uploaded_by=user.id,
                     original_name='pending.txt',storage_key='a'*32,size_bytes=5,state='pending')
        db.add(a);db.flush();aid=a.id;org=user.organization_id
        quota=db.get(AttachmentQuota,org)
        if quota is None:db.add(AttachmentQuota(organization_id=org,charged_bytes=5))
        else:quota.charged_bytes=5
        db.commit()
    (files/('a'*32)).write_bytes(b'hello')
    with pytest.raises(ValueError):recovery.recover(engine,org,aid,files,api_stopped=False)
    with store.runtime_lock(files):
        with pytest.raises(Exception):recovery.recover(engine,org,aid,files,api_stopped=True)
    recovery.recover(engine,org,aid,files,api_stopped=True)
    recovery.recover(engine,org,aid,files,api_stopped=True)
    with Session(engine) as db:
        assert db.get(Attachment,aid).state=='failed' and db.get(AttachmentQuota,org).charged_bytes==0
        db.get(Attachment,aid).state='ready';db.get(Attachment,aid).sha256='0'*64;db.commit()
    with pytest.raises(Exception):recovery.recover(engine,org,aid,files,api_stopped=True)


def test_cleanup_failure_and_unsafe_key_preserve_pending_charge(client,engine,files,monkeypatch):
    nid,_,_=setup(client,engine)
    from app.services import attachment_store as store
    original=store.mark_ready
    monkeypatch.setattr(store,'mark_ready',lambda *args: (_ for _ in ()).throw(RuntimeError('crash')))
    original_unlink=Path.unlink
    def unlink(path,*args,**kwargs):
        if path.parent==files:raise OSError('cannot remove')
        return original_unlink(path,*args,**kwargs)
    monkeypatch.setattr(Path,'unlink',unlink)
    assert upload(client,nid).status_code==503
    with Session(engine) as db:
        a=db.scalars(select(Attachment)).one();org=a.organization_id;aid=a.id
        assert a.state=='pending' and db.get(AttachmentQuota,org).charged_bytes==5
    monkeypatch.setattr(Path,'unlink',original_unlink)
    store.reconcile_upload(engine,org,aid,files)
    with Session(engine) as db:
        a=db.get(Attachment,aid);a.state='pending';a.storage_key='../escape';db.get(AttachmentQuota,org).charged_bytes=5;db.commit()
    with pytest.raises(Exception):store.reconcile_upload(engine,org,aid,files)
    with Session(engine) as db:assert db.get(AttachmentQuota,org).charged_bytes==5


def test_upload_authorization_rechecked_after_stream(client,engine,monkeypatch):
    nid,_,users=setup(client,engine)
    from app.services import attachment_store as store
    original=store.write_chunk
    changed=False
    def write(handle,chunk):
        nonlocal changed
        original(handle,chunk)
        if not changed:
            changed=True
            with Session(engine) as db:db.get(Node,nid).owner_user_id=users['yu'];db.commit()
    monkeypatch.setattr(store,'write_chunk',write)
    assert upload(client,nid).status_code==404
    with Session(engine) as db:
        a=db.scalars(select(Attachment)).one()
        assert a.state=='failed' and db.get(AttachmentQuota,a.organization_id).charged_bytes==0
        assert list(db.scalars(select(AuditLog).where(AuditLog.action=='attachment.upload')))==[]


@pytest.mark.parametrize('invalid',['other_node','other_uploader','pending','deleted','foreign_company'])
def test_attachment_binding_rejects_wrong_target_or_state(client,engine,invalid):
    nid,pid,users=setup(client,engine)
    a=upload(client,nid).json();assert 'id' in a
    with Session(engine) as db:
        row=db.get(Attachment,a['id'])
        if invalid=='other_node':
            node=Node(organization_id=row.organization_id,project_id=pid,kind='task',title='other',owner_user_id=users['ming'])
            db.add(node);db.flush();row.node_id=node.id
        elif invalid=='other_uploader':row.uploaded_by=users['yu']
        elif invalid=='pending':row.state='pending'
        elif invalid=='deleted':
            from app.models import now_utc
            row.deleted_at=now_utc()
        else:
            other=db.scalars(select(User).where(User.organization_id!=row.organization_id)).first()
            row.organization_id=other.organization_id
        db.commit()
    assert client.post(f'/nodes/{nid}/reports',json={**PAYLOAD,'attachment_ids':[a['id']]}).status_code==422
    assert client.post(f'/nodes/{nid}/notes',json={'body':'not created','attachment_ids':[a['id']]}).status_code==422
    with Session(engine) as db:
        assert list(db.scalars(select(TaskReport)))==[] and list(db.scalars(select(TaskNote)))==[]
        assert db.get(Node,nid).status=='todo'


def test_extremely_long_content_length_is_safe(client,engine):
    nid,_,_=setup(client,engine)
    client._transport.raise_server_exceptions=False
    response=upload(client,nid,b'x',headers={'Content-Length':'9'*5000})
    assert response.status_code in {413,422}
    assert 'Internal' not in response.text


def test_zip_missing_local_file_header_is_rejected(client,engine):
    nid,_,_=setup(client,engine)
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w') as archive:archive.writestr('file.txt','x')
    content=b'FAIL'+buffer.getvalue()[4:]
    assert upload(client,nid,content,'bad.zip').status_code==422


def test_committed_upload_is_recovered_even_if_old_session_rollback_fails(client,engine,monkeypatch):
    nid,_,_=setup(client,engine)
    original_commit,original_rollback=Session.commit,Session.rollback
    committed=False;rollback_failed=False
    def commit(db):
        nonlocal committed
        ready=any(isinstance(x,Attachment) and x.state=='ready' for x in db.identity_map.values())
        original_commit(db)
        if ready and not committed:
            committed=True
            raise RuntimeError('lost commit response')
    def rollback(db):
        nonlocal rollback_failed
        if committed and not rollback_failed:
            rollback_failed=True
            raise RuntimeError('old connection unavailable')
        return original_rollback(db)
    monkeypatch.setattr(Session,'commit',commit)
    monkeypatch.setattr(Session,'rollback',rollback)
    response=upload(client,nid)
    assert response.status_code==201
    assert client.get(f"/attachments/{response.json()['id']}/download").content==b'hello'
