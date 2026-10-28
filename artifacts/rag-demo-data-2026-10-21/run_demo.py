"""Evaluate only in temporary SQLite; --import-local adds a new dedicated local demo project.

Requires the repository's Python API dependencies. No passwords or tokens are saved in reports.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from time import perf_counter
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / 'api'))


def checked(client, method, path, **kwargs):
    response = client.request(method, path, **kwargs)
    response.raise_for_status()
    return response.json() if response.content else None


def populate(client, *, check_version=False, progress=None):
    manifest = json.loads((HERE / 'manifest.json').read_text(encoding='utf-8'))
    assert manifest['synthetic'] is True
    for item in manifest['documents']:
        assert hashlib.sha256((HERE / item['path']).read_bytes()).hexdigest() == item['sha256']
        if item.get('history_path'):
            assert hashlib.sha256((HERE / item['history_path']).read_bytes()).hexdigest() == item['history_sha256']
    project = checked(client, 'POST', '/projects', json={'title': manifest['project_title']})
    documents = {}
    if progress:
        progress(project, documents, 'created')
    version_checks = {}
    # Index and supersede the old version before adding other documents.
    for item in sorted(manifest['documents'], key=lambda d: (d['key'] != '05', d['key'])):
        raw = HERE / item.get('history_path', item['path'])
        doc = checked(client, 'POST', f"/projects/{project['id']}/documents",
                      params={'filename': item['filename'], 'comment': '完全虛構：RAG 資料驗證'},
                      headers={'Content-Type': 'application/octet-stream'}, content=raw.read_bytes())
        docid = doc['document_id']
        documents[docid] = {'key': item['key'], 'version': 1, 'filename': item['filename'], 'state': 'uploaded'}
        if progress:
            progress(project, documents, 'partial')
        if item.get('history_path'):
            old = checked(client, 'POST', f'/rag/documents/{docid}/index')
            assert old['state'] == 'ready'
            checked(client, 'POST', f'/documents/{docid}/versions',
                    params={'filename': item['filename'], 'expected_version': 1, 'comment': '現行規格：版本 2'},
                    headers={'Content-Type': 'application/octet-stream'}, content=(HERE / item['path']).read_bytes())
            if check_version:
                pending = checked(client, 'POST', '/rag/ask', json={'project_id': project['id'], 'question': '每箱幾包？'})
                version_checks['old_version_excluded_before_reindex'] = pending['sources'] == []
                assert version_checks['old_version_excluded_before_reindex']
        index = checked(client, 'POST', f'/rag/documents/{docid}/index')
        assert index['state'] == 'ready', index
        assert not index.get('error_code'), index
        documents[docid] = {'key': item['key'], 'version': item['version'], 'filename': item['filename'], 'state': 'ready'}
        if progress:
            progress(project, documents, 'partial')
        print(json.dumps({'indexed': item['key'], 'version': item['version']}), flush=True)
    return project, documents, version_checks


def grade(case, result, documents):
    sources = {s['source_id']: s for s in result['sources']}
    citations = result['citations']
    cited = {documents[sources[c]['document_id']]['key'] for c in citations if c in sources and sources[c]['document_id'] in documents}
    text = result['answer']
    checks = {
        'valid_citations': all(c in sources for c in citations),
        'current_sources_only': all(s['document_id'] in documents and s['version'] == documents[s['document_id']]['version'] for s in sources.values()),
        'actual_model': result['engine'] == 'model',
    }
    if case['expect_refusal']:
        checks['refusal_signal'] = any(t in text for t in ('不足', '未提供', '沒有提供', '無法', '未記錄', '沒有記錄', '沒有已核准', '尚未', '未有', '仍在評選'))
    else:
        checks['answer_term_signals'] = all(any(term in text for term in group) for group in case['term_groups'])
        checks['required_documents_cited'] = set(case['required_document_keys']) <= cited
        checks['has_citation'] = bool(citations)
    return {'automatic_pass': all(checks.values()), 'checks': checks, 'cited_document_keys': sorted(cited)}


def evaluate(report_path, case_ids=None, generation_model='qwen2.5:3b-instruct-q4_K_M'):
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.database import Base, get_session
    from app.main import create_app
    from app.seed import seed_demo_data
    cases = json.loads((HERE / 'questions.json').read_text(encoding='utf-8'))
    if case_ids:
        cases = [c for c in cases if c['id'] in case_ids]
        assert len(cases) == len(case_ids), 'Unknown or duplicate case ID'
    if report_path.exists():
        raise SystemExit('Report already exists; choose a new path to preserve previous evidence.')
    with tempfile.TemporaryDirectory(prefix='rag-fictional-') as folder:
        root = Path(folder); (root / 'files').mkdir()
        url = 'sqlite:///' + (root / 'evaluation.db').as_posix()
        engine = create_engine(url)
        try:
            with patch.dict(os.environ, {'DATABASE_URL': url, 'PF_ATTACHMENT_ROOT': str(root / 'files'), 'PF_WEB_LAN': 'false'}):
                Base.metadata.create_all(engine)
                with Session(engine) as db:
                    seed_demo_data(db); db.commit()
                app = create_app()
                def sessions():
                    with Session(engine) as db:
                        yield db
                app.dependency_overrides[get_session] = sessions
                with TestClient(app, base_url='http://127.0.0.1') as client:
                    checked(client, 'POST', '/auth/login', json={'organization_key': 'food', 'username': 'yu', 'password': 'demo-yu'})
                    checked(client, 'PUT', '/rag/model', json={'enabled': True, 'base_url': 'http://127.0.0.1:11434', 'model': generation_model, 'embedding_model': 'bge-m3:latest'})
                    project, documents, version_checks = populate(client, check_version=True)
                    rows = []
                    for case in cases:
                        started = perf_counter()
                        result = checked(client, 'POST', '/rag/ask', json={'project_id': project['id'], 'question': case['question']})
                        row = {'id': case['id'], 'question': case['question'], 'expected_answer': case['expected_answer'],
                               'answer': result['answer'], 'engine': result['engine'], 'kind': result['kind'],
                               'retrieval_mode': result['retrieval_mode'], 'warning': result.get('warning'),
                               'latency_ms': round((perf_counter()-started)*1000),
                               'sources': result['sources'], 'citations': result['citations'],
                               **grade(case, result, documents)}
                        rows.append(row)
                        print(json.dumps({'case': case['id'], 'automatic_pass': row['automatic_pass'], 'checks': row['checks'] if not row['automatic_pass'] else {}}), flush=True)
                    report = {'mode': 'isolated_actual_model', 'synthetic': True, 'generation_model': generation_model,
                              'embedding_model': 'bge-m3:latest', 'total': len(rows),
                              'automatic_passed': sum(r['automatic_pass'] for r in rows),
                              'version_checks': version_checks, 'cases': rows,
                              'limitation': 'Automatic term/citation/refusal checks are screening signals, not complete semantic or domain-quality validation. No production DB is used.'}
                    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
                    print(json.dumps({k: report[k] for k in ('total', 'automatic_passed', 'version_checks')}), flush=True)
        finally:
            engine.dispose()


def import_local():
    import httpx
    state = REPO / '.superpowers/rag-demo-data-20261021'
    state.mkdir(exist_ok=True)
    receipt = state / 'import-receipt.json'
    if receipt.exists():
        raise SystemExit('Existing import receipt: refusing to create a duplicate project. Inspect it before re-running.')
    with httpx.Client(base_url='http://127.0.0.1:15173/api', timeout=150, trust_env=False) as client:
        checked(client, 'POST', '/auth/login', json={'organization_key': 'food', 'username': 'yu', 'password': 'demo-yu'})
        # Use the already configured local model; do not overwrite existing settings.
        settings = checked(client, 'GET', '/rag/model')
        assert settings['enabled'] and settings['embedding_model'], 'Configure the existing local RAG model first.'
        def progress(project, documents, state):
            receipt.write_text(json.dumps({'project': project, 'documents': documents, 'state': state}, ensure_ascii=False, indent=2), encoding='utf-8')
        project, documents, _ = populate(client, progress=progress)
        progress(project, documents, 'complete')
        checked(client, 'POST', '/auth/logout')
    print(json.dumps({'imported_documents': len(documents), 'project_id': project['id']}, ensure_ascii=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--import-local', action='store_true', help='Explicitly create one new fictional demo project on the local trial service.')
    parser.add_argument('--report', type=Path, default=HERE / 'evaluation-after.json', help='New report path; refuses to overwrite existing reports.')
    parser.add_argument('--cases', nargs='+', help='Optional case IDs for diagnosis; omit for full 20-question acceptance.')
    parser.add_argument('--model', default='qwen2.5:3b-instruct-q4_K_M', help='Installed local generation model; report records the exact choice.')
    args = parser.parse_args()
    import_local() if args.import_local else evaluate(args.report, args.cases, args.model)
