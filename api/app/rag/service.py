"""Transactional lifecycle and orchestration for formal, authorized knowledge."""
from datetime import timedelta, timezone
import hashlib
import json
from pathlib import Path
from time import perf_counter, monotonic
import uuid

from fastapi import HTTPException
from sqlalchemy import select, update

from app.audit import log_audit
from app.models import Document, DocumentVersion, Project
from app.permissions import can_view_project
from app.services import document_store
from app.rag.models import RagChunk, RagIndex, RagQuery, RagSettings, now
from app.rag import chunking, governance, parsing, provider, retrieval

PIPELINE = 'formal-rag-v2'
MAX_CANDIDATES = 5000


def settings(db, org):
    row = db.get(RagSettings, org, populate_existing=True)
    return {key: getattr(row, key) if row else default for key, default in
            [('enabled', False), ('base_url', ''), ('model', ''), ('embedding_model', '')]}


def embedding_key(config):
    if not config['enabled'] or not config['embedding_model']:
        return None
    return hashlib.sha256(json.dumps([config['base_url'], config['embedding_model']], ensure_ascii=False).encode()).hexdigest()


def fingerprint(version, config):
    return hashlib.sha256(f'{version.sha256}:{PIPELINE}:{embedding_key(config)}'.encode()).hexdigest()


def index_out(doc, row, title, can_index):
    state = row.state if row and row.version == doc.current_version else 'queued'
    return dict(document_id=doc.id, version=doc.current_version, title=title, node_id=doc.node_id,
                can_index=can_index, state=state, indexed_version=row.indexed_version if row else None,
                chunk_count=row.chunk_count if row and state == 'ready' else 0,
                error_code=row.error_code if row else None, enabled=row.enabled if row else True)


def status(db, current, project_id=None, scope_kind=None):
    projects = [dict(project_id=p.id, title=p.title) for p in db.scalars(select(Project).where(
        Project.organization_id == current.organization.id).order_by(Project.title)) if can_view_project(current, p)]
    config = settings(db, current.organization.id)
    result = dict(source_mode='formal', synthetic=False, projects=projects, project_id=project_id,
                  ready=False, model=dict(enabled=config['enabled'], name=config['model'], embedding_model=config['embedding_model']),
                  documents=[], counts={key: 0 for key in ('queued', 'processing', 'ready', 'failed', 'unsupported')})
    if project_id or scope_kind == 'all_visible':
        for doc in governance.authorized_documents(db, current, project_id):
            version, allowed, _ = document_store.get_version(db, current, doc.id, doc.current_version)
            item = index_out(doc, db.get(RagIndex, doc.id), version.filename, allowed)
            item['project_id'] = doc.project_id
            item['project_title'] = db.get(Project, doc.project_id).title
            result['documents'].append(item)
            result['counts'][item['state']] += 1
        result['ready'] = any(d['state'] == 'ready' and d['enabled'] for d in result['documents'])
    result['scope'] = {'kind':'project', 'project_id':project_id} if project_id else {'kind':'all_visible'}
    result['coverage'] = coverage(result['documents'])
    return result


def coverage(documents):
    counts = {key:0 for key in ('ready','queued','processing','failed','unsupported','disabled')}
    for item in documents:
        counts[item['state'] if item['enabled'] else 'disabled'] += 1
    counts['partial'] = counts['ready'] > 0 and any(counts[k] for k in ('queued','processing','failed','unsupported'))
    return counts


def index_document(db, current, document_id, *, automatic=False):
    doc, allowed, _ = document_store.get_document(db, current, document_id, True)
    version, _, _ = document_store.get_version(db, current, doc.id, doc.current_version)
    config = settings(db, current.organization.id)
    wanted, key = fingerprint(version, config), embedding_key(config)
    row = db.get(RagIndex, doc.id)
    if row is None:
        row = RagIndex(document_id=doc.id, organization_id=current.organization.id, version=version.version)
        db.add(row)
        db.flush()
    if not row.enabled:
        raise HTTPException(409, '請先恢復此文件的知識庫使用')
    if row.state == 'ready' and row.fingerprint == wanted and row.indexed_version == version.version and row.embedding_key == key:
        return index_out(doc, row, version.filename, allowed)
    if not automatic:
        from app.rag.indexing import enqueue
        enqueue(row, current.user.id)
        db.flush()
    claim = str(uuid.uuid4())
    cutoff = now() - timedelta(minutes=5)
    claimed = db.execute(update(RagIndex).where(RagIndex.document_id == doc.id,
        ((RagIndex.state != 'processing') | (RagIndex.updated_at < cutoff)),
        RagIndex.enabled.is_(True), RagIndex.version == version.version,
        *([RagIndex.requested_at.is_not(None), RagIndex.requested_by_user_id == current.user.id, RagIndex.attempts < 3,
           (RagIndex.next_attempt_at.is_(None)) | (RagIndex.next_attempt_at <= now())] if automatic else [])).values(
            state='processing', version=version.version, claim=claim, error_code=None, updated_at=now(),
            attempts=RagIndex.attempts + 1, next_attempt_at=None).execution_options(synchronize_session='fetch'))
    if claimed.rowcount != 1:
        raise HTTPException(409, '文件索引處理中，請稍後重新載入')
    org, number, title, sha = current.organization.id, version.version, version.filename, version.sha256
    path = document_store.version_path(version)
    db.commit()  # No business row locks held across parsing or model requests.
    error = None
    try:
        if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
            raise ValueError('source_hash_mismatch')
        pieces = chunking.build_chunks(parsing.parse_file(path, title))
        if not pieces or len(pieces) > 200:
            raise ValueError('chunk_limit')
        vectors = [None] * len(pieces)
        actual_key = None
        if key:
            # Parsing may take time; reauthorize immediately before sending document text.
            governance.recheck(db, current, document_id, number)
            document_store.get_document(db, current, document_id, True)
            active = db.get(RagIndex, document_id, populate_existing=True)
            if active.claim != claim or not active.enabled:
                raise HTTPException(409, '文件索引狀態已改變，請重新載入')
            db.commit()
            try:
                def authorize_index():
                    if not automatic:
                        governance.session_access(db,current)
                    governance.recheck(db,current,document_id,number)
                    document_store.get_document(db,current,document_id,True)
                    active = db.get(RagIndex,document_id,populate_existing=True)
                    if active.claim != claim or not active.enabled:
                        raise HTTPException(409,'文件索引狀態已改變')
                    # Authorization took Project/Node locks; release this read-only
                    # transaction before every network batch. Claim was committed
                    # above and publication rechecks ACL/version/claim under locks.
                    db.rollback()
                vectors = provider.embed(dict(config,_authorize=authorize_index), [p['text'] for p in pieces])
                actual_key = key
            except ValueError:
                error = 'embedding_unavailable'
        db.expire_all()
        # Match document_store.save: Project/Node -> Document -> RagIndex.
        # Locking Document first can deadlock against a concurrent revision.
        doc, allowed, _ = document_store.get_document(db, current, document_id, True)
        doc = db.scalar(select(Document).where(Document.id == document_id,
            Document.organization_id == org).with_for_update().execution_options(populate_existing=True))
        row = db.scalar(select(RagIndex).where(RagIndex.document_id == doc.id).with_for_update().execution_options(populate_existing=True))
        if row.claim != claim or doc.current_version != number or not row.enabled:
            raise HTTPException(409, '文件或知識庫狀態已改變，請重新載入')
        if embedding_key(settings(db, org)) != key:
            row.state, row.claim = 'queued', None
            db.commit()
            raise HTTPException(409, '模型設定已變更，請重新建立索引')
        generation = str(uuid.uuid4())
        for piece, vector in zip(pieces, vectors, strict=True):
            db.add(RagChunk(organization_id=org, document_id=doc.id, version=number, generation=generation,
                sha256=sha, parent_id=f'{doc.id}:{number}:{piece["parent_id"]}', text=piece['text'],
                parent_text=piece['parent_text'], locator=piece['locator'], embedding=vector))
        row.state, row.indexed_version, row.generation = 'ready', number, generation
        row.fingerprint, row.embedding_key, row.chunk_count = wanted, actual_key, len(pieces)
        row.error_code, row.claim, row.updated_at = error, None, now()
        from app.rag.indexing import finish_request
        finish_request(row, transient=error == 'embedding_unavailable')
        log_audit(db, current, 'rag.index', node_id=doc.node_id, payload={'document_id': doc.id, 'version': number})
        db.commit()
        return index_out(doc, row, title, allowed)
    except Exception as exc:
        db.rollback()
        # Do not overwrite a newer version or another worker's claim after a race.
        state = 'unsupported' if Path(title).suffix.lower() not in {'.txt', '.csv', '.pdf', '.docx'} else 'failed'
        safe_errors = {'file_too_large', 'text_limit', 'page_limit', 'encrypted_pdf', 'archive_limit',
                       'unsafe_xml', 'unsupported_format', 'parse_failed', 'no_extractable_text',
                       'chunk_limit', 'parse_timeout', 'source_hash_mismatch'}
        code = str(exc) if isinstance(exc, ValueError) and str(exc) in safe_errors else 'parse_or_index_failed'
        if isinstance(exc, HTTPException) and exc.status_code in (401,403,404):
            code = 'access_changed'
        failed = db.scalar(select(RagIndex).where(RagIndex.document_id == document_id, RagIndex.organization_id == org, RagIndex.claim == claim).with_for_update())
        if failed is not None:
            failed.state, failed.claim, failed.error_code, failed.updated_at = state, None, code, now()
            from app.rag.indexing import finish_request
            finish_request(failed, transient=code == 'parse_timeout')
        db.commit()
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(422, '無法建立索引：請確認格式、文字內容與檔案大小，再重試；原檔仍保留。') from None


def set_enabled(db, current, document_id, enabled):
    doc, _, _ = document_store.get_document(db, current, document_id, True)
    row = db.get(RagIndex, doc.id)
    if row is None:
        row = RagIndex(document_id=doc.id, organization_id=current.organization.id, version=doc.current_version)
        db.add(row)
    row.enabled = enabled
    row.claim = None
    if row.state == 'processing':
        row.state = 'queued'
    if enabled and (row.state != 'ready' or row.indexed_version != doc.current_version or row.error_code):
        from app.rag.indexing import enqueue
        enqueue(row, current.user.id)
    row.updated_at = now()
    log_audit(db, current, 'rag.enabled', node_id=doc.node_id, payload={'document_id': doc.id, 'enabled': enabled})
    db.commit()
    return {'ok': True}


def valid_source(db, current, source, require_current=True):
    version = governance.recheck(db, current, source['document_id'], source['version'], require_current=require_current)
    index = db.get(RagIndex, source['document_id'], populate_existing=True)
    if require_current and (index is None or not index.enabled):
        raise HTTPException(404, '來源已停用或無法存取')
    if require_current and (index.state != 'ready' or index.indexed_version != source['version'] or
                            index.generation != source['generation']):
        raise HTTPException(409, '來源已有變更，請重新提問')
    if version.sha256 != source['sha256']:
        raise HTTPException(409, '來源內容不一致，請重新建立索引')
    return version


def candidates(db, current, project_id, config):
    documents = governance.authorized_documents(db, current, project_id)
    if not documents:
        return []
    docs = {d.id: d for d in documents}
    rows = db.execute(select(RagChunk, RagIndex, DocumentVersion).join(RagIndex,
        (RagChunk.document_id == RagIndex.document_id) & (RagChunk.generation == RagIndex.generation)).join(Document,
        Document.id == RagChunk.document_id).join(DocumentVersion,
        (DocumentVersion.document_id == RagChunk.document_id) & (DocumentVersion.version == RagChunk.version)).where(
        RagChunk.organization_id == current.organization.id, RagChunk.document_id.in_(docs),
        RagIndex.enabled.is_(True), RagIndex.state == 'ready', RagChunk.version == Document.current_version,
        RagIndex.indexed_version == Document.current_version).limit(MAX_CANDIDATES + 1)).all()
    if len(rows) > MAX_CANDIDATES:
        raise HTTPException(422, 'scope_limit')
    key = embedding_key(config)
    return [dict(source_id=c.id, chunk_id=c.id, document_id=c.document_id, version=c.version,
        title=v.filename, project_id=docs[c.document_id].project_id, project_title=db.get(Project, docs[c.document_id].project_id).title, node_id=docs[c.document_id].node_id, text=c.text,
        parent_text=c.parent_text, parent_id=c.parent_id, locator=c.locator, generation=c.generation,
        sha256=c.sha256, embedding=c.embedding if key and index.embedding_key == key else None)
        for c, index, v in rows]


def public_source(source):
    return {key: source[key] for key in ('source_id', 'chunk_id', 'document_id', 'version', 'title',
        'project_id', 'project_title', 'node_id', 'excerpt', 'locator')}


def ask(db, current, project_id, question, previous_question=None, *, scope=None, history=None):
    from app.rag import conversation
    governance.session_access(db,current)
    started, deadline = perf_counter(), monotonic() + 170
    scope = scope or {'kind':'project', 'project_id':project_id}
    config = settings(db, current.organization.id)
    summary = status(db, current, project_id, scope['kind'])
    cov = summary['coverage']
    history = history or ([] if not previous_question else [{'question':previous_question}])
    code, clarification, query = None, None, question
    try:
        query, clarification = conversation.resolve(db, current, scope, question, history, config, deadline)
    except HTTPException as error:
        if error.status_code not in (403,404,409):
            raise
        code, query = 'access_changed', None
    def authorize(sources=()):
        governance.session_access(db,current)
        conversation.validate_history(db,current,scope,history)
        for source in sources:
            valid_source(db,current,source)
    retrieval_start = perf_counter()
    embedding_ms, generation_ms = 0, 0
    pool = []
    if query is not None:
        try:
            pool = candidates(db, current, project_id, config)
        except HTTPException as error:
            if error.detail != 'scope_limit':
                raise
            code = 'scope_limit'
    vector, warning, mode = None, None, 'bm25_rules'
    if pool and embedding_key(config) and any(c['embedding'] is not None for c in pool):
        embedding_start = perf_counter()
        try:
            authorize(pool)
            vector = provider.embed(dict(config, _authorize=lambda:authorize(pool), _deadline=min(deadline,monotonic()+90)), [query])[0]
            dimensions = {len(c['embedding']) for c in pool if c['embedding'] is not None}
            if dimensions != {len(vector)}:
                raise ValueError('embedding_dimension_changed')
            mode = 'hybrid_rrf_rules'
        except ValueError:
            vector, code = None, 'embedding_unavailable'
            warning = '向量服務無法使用，目前採關鍵字檢索。'
        embedding_ms = round((perf_counter()-embedding_start)*1000,2)
    elif pool:
        warning = '目前採關鍵字檢索；設定向量模型並重建索引後可啟用混合檢索。'
        if embedding_key(config):
            code = 'embedding_unavailable'
    selected = retrieval.rank(retrieval.expand_query(query or question), pool, query_vector=vector, limit=6, budget=8000)
    for source in selected:
        valid_source(db, current, source)
    retrieval_ms = round((perf_counter()-retrieval_start)*1000,2)
    answer, kind, engine, citations, blocks = '目前資料不足，找不到可供回答的現行授權來源。', 'no_sources', 'retrieval', [], []
    if clarification:
        answer, kind, code = clarification, 'clarification', 'clarification_required'
    elif code in ('access_changed','scope_limit'):
        answer = '存取權限已變更，請開始新對話。' if code == 'access_changed' else '可查詢資料過多，請縮小到單一專案。'
    elif not selected:
        code = 'index_pending' if cov['queued'] or cov['processing'] else ('no_sources' if cov['ready'] else 'no_documents')
    if selected:
        answer = '未產生回答，以下是檢索原文：\n\n' + '\n\n'.join(s['excerpt'] for s in selected)
        kind, citations = 'retrieval', [s['source_id'] for s in selected]
        blocks = [dict(text=s['excerpt'], source_ids=[s['source_id']]) for s in selected]
        if config['enabled'] and config['model']:
            generation_start = perf_counter()
            try:
                if monotonic() >= deadline:
                    raise ValueError('generation_timeout')
                authorize(selected)
                generated = provider.answer(dict(config,_authorize=lambda:authorize(selected),_deadline=deadline), query, selected)
                answer, citations, kind, engine = generated['answer'], generated['citations'], 'rag', 'model'
                blocks = generated.get('blocks', [dict(text=answer,source_ids=citations)] if citations else [])
                if not citations:
                    kind, blocks = 'insufficient_evidence', []
                    answer = '目前來源不足以支持答案，請補充文件或縮小問題範圍。'
            except ValueError as error:
                code = 'generation_timeout' if str(error) == 'generation_timeout' else 'generation_unavailable'
                warning = '生成模型未產生回答，以下是檢索原文。'
            generation_ms = round((perf_counter()-generation_start)*1000,2)
        else:
            code = 'generation_unavailable'
            warning = '尚未啟用生成模型，以下顯示原文。'
    for source in selected:
        valid_source(db, current, source)
    governance.session_access(db,current)
    if code != 'access_changed':
        conversation.validate_history(db,current,scope,history)
    if cov['partial'] and code is None:
        code = 'partial_coverage'
    trace = governance.trace_summary(kind=kind, engine=engine, retrieval_mode=mode, stage='query',
        outcome='degraded' if warning or code else 'success', duration_ms=round((perf_counter() - started) * 1000, 2),
        candidate_count=len(pool), source_count=len(selected), pipeline_version=PIPELINE, prompt_version='blocks-v4',
        scope_kind=scope['kind'], contract_version='ask-v1', error_code=code,
        retrieval_ms=retrieval_ms, embedding_ms=embedding_ms, generation_ms=generation_ms,
        model=config['model'] if engine == 'model' else '', input_tokens=None, output_tokens=None, cost=None)
    row = RagQuery(organization_id=current.organization.id, actor_user_id=current.user.id, project_id=project_id,
                   source_ids=[s['source_id'] for s in selected], trace=trace)
    db.add(row)
    db.commit()
    governance.session_access(db,current)
    for source in selected:
        valid_source(db,current,source)
    if code != 'access_changed':
        conversation.validate_history(db,current,scope,history)
    return dict(query_id=row.id, project_id=project_id, scope=scope, source_mode='formal', synthetic=False, kind=kind,
                engine=engine, answer=answer, warning=warning, citations=citations, blocks=blocks, code=code, coverage=cov,
                sources=[public_source(s) for s in selected], retrieval_mode=mode)


def own_query(db, current, query_id):
    row = db.scalar(select(RagQuery).where(RagQuery.id == query_id, RagQuery.organization_id == current.organization.id,
        RagQuery.actor_user_id == current.user.id))
    if row is None:
        raise HTTPException(404, '找不到問答紀錄')
    return row


def source_text(db, current, query_id, source_id):
    query = own_query(db, current, query_id)
    if source_id not in query.source_ids:
        raise HTTPException(404, '找不到引用來源')
    chunk = db.scalar(select(RagChunk).where(RagChunk.id == source_id, RagChunk.organization_id == current.organization.id))
    if chunk is None:
        raise HTTPException(404, '找不到引用來源')
    version = valid_source(db, current, dict(document_id=chunk.document_id, version=chunk.version, sha256=chunk.sha256), False)
    doc, _, _ = document_store.get_document(db, current, chunk.document_id)
    return dict(document_id=doc.id, version=chunk.version, title=version.filename, text=chunk.parent_text,
                project_id=doc.project_id, project_title=db.get(Project,doc.project_id).title,
                locator=chunk.locator, is_current=doc.current_version == chunk.version,
                download_url=f'/documents/{doc.id}/versions/{chunk.version}/download')


def revalidate(db, current, query_ids):
    results = []
    for query_id in query_ids:
        state = 'visible'
        try:
            row = own_query(db, current, query_id)
            for sid in row.source_ids:
                source = source_text(db, current, row.id, sid)
                if not source['is_current']:
                    state = 'source_changed'
        except HTTPException:
            state = 'unavailable'
        results.append(dict(query_id=query_id, status=state))
    return {'queries':results}
