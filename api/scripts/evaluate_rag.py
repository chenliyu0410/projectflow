"""Evaluate fixtures or real API behavior using an isolated synthetic database."""
import argparse
import json
from pathlib import Path
import sys
import os
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.rag.evaluation import evaluate


def service_report(work_dir=None):
    """Exercise actual ingestion/retrieval/ACL in a disposable database, with no model calls."""
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.database import Base, get_session
    from app.main import create_app
    from app.seed import seed_demo_data
    with tempfile.TemporaryDirectory(prefix='rag-evaluation-', dir=work_dir) as folder:
        root = Path(folder)
        (root / 'files').mkdir()
        url = 'sqlite:///' + str(root / 'evaluation.db')
        engine = create_engine(url)
        try:
            with patch.dict(os.environ, {'DATABASE_URL': url, 'PF_ATTACHMENT_ROOT': str(root / 'files')}):
                Base.metadata.create_all(engine)
                with Session(engine) as db:
                    seed_demo_data(db)
                    db.commit()
                app = create_app()
                def session():
                    with Session(engine) as db:
                        yield db
                app.dependency_overrides[get_session] = session
                with TestClient(app) as client:
                    def login(org, name):
                        response = client.post('/auth/login', json={'organization_key': org, 'username': name, 'password': 'demo-' + name})
                        response.raise_for_status()
                    login('food', 'yu')
                    project = client.get('/projects').json()['items'][0]['id']
                    uploaded = client.post(f'/projects/{project}/documents', params={'filename': 'evaluation.txt'},
                        content='合成星際驗收需要七次確認。'.encode(), headers={'content-type': 'application/octet-stream'})
                    uploaded.raise_for_status()
                    doc = uploaded.json()['document_id']
                    client.post(f'/rag/documents/{doc}/index').raise_for_status()
                    def ask(question='星際驗收'):
                        response = client.post('/rag/ask', json={'project_id': project, 'question': question})
                        if response.status_code == 404:
                            return {'kind': 'no_sources', 'sources': [], 'citations': [], 'error_code': 'access_denied'}
                        response.raise_for_status()
                        return response.json()
                    first = ask()
                    ids = first['citations']
                    if not ids:
                        raise RuntimeError('Seed document was not retrieved')
                    cases = [dict(id='known', expected_kind='retrieval', expected_source_ids=ids, required_source_ids=ids),
                             dict(id='unknown', expected_kind='no_sources'), dict(id='disabled', expected_kind='no_sources'),
                             dict(id='new_version_pending', expected_kind='no_sources'),
                             dict(id='foreign_company', expected_kind='no_sources', expected_failure='access_denied')]
                    def run(case):
                        if case['id'] == 'unknown':
                            return ask('unrelatedxyz')
                        if case['id'] == 'disabled':
                            client.put(f'/rag/documents/{doc}/enabled', json={'enabled': False}).raise_for_status()
                        if case['id'] == 'new_version_pending':
                            client.put(f'/rag/documents/{doc}/enabled', json={'enabled': True}).raise_for_status()
                            client.post(f'/documents/{doc}/text', json={'expected_version': 1, 'content': '星際驗收改成八次'}).raise_for_status()
                        if case['id'] == 'foreign_company':
                            client.post('/auth/logout')
                            login('electronics', 'elaine')
                        return ask()
                    report = evaluate(cases, run, mode='actual')
                    report['description'] = 'Actual API with isolated synthetic SQLite data; lexical retrieval and access/version policy, no model calls.'
                    return report
        finally:
            engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path)
    parser.add_argument('--service', action='store_true', help='Run actual API over disposable synthetic SQLite data')
    parser.add_argument('--work-dir', type=Path, help='Parent of a temporary test directory')
    args = parser.parse_args()
    if args.service:
        report = service_report(args.work_dir)
    else:
        path = Path(__file__).resolve().parents[1] / 'tests' / 'fixtures' / 'rag_cases.json'
        cases = json.loads(path.read_text(encoding='utf-8-sig'))
        report = evaluate(cases, lambda case: case['fixture_result'], mode='fixture')
        report['description'] = 'Synthetic fixture contract only; no retrieval, permissions, or model quality verified by this run.'
    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.report:
        args.report.write_text(output + '\n', encoding='utf-8')
    print(output)
    return 1 if report['failed'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
