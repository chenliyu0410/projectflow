"""Build the clean demo data for the portable package from an empty database.

Run with the package's Python while its Ollama (bge-m3 loaded) listens on --ollama:

    python deploy/portable/build_seed.py --out <empty dir> --ollama http://127.0.0.1:11437 --ocr-models <dir>

Everything goes through migrations, the demo pack importer and the real API, so the result matches
what a user would get by doing the same steps in the app. The output directory must not exist yet.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
API = REPO / 'api'
DOCS = Path(__file__).resolve().parent / 'demo-docs'
PACK = REPO / 'deploy' / 'demo-data'
STARTER = REPO / 'deploy' / 'rag-starter'
AI_DEMO = REPO / 'deploy' / 'ai-demo-data' / 'pack'  # 原有展示資料 (dataset-v1): Text-to-SQL and its documents
CHAT_MODEL = 'pf-qwen3-rag:latest'
VECTOR_MODEL = 'bge-m3'
STARTER_COMPANIES = ('food', 'electronics')  # the two companies that own AI starter material

# Project titles left behind by automated tests; none may reach the demo data.
TEST_RESIDUE = re.compile(r'\b(1280|1440|375)\b|E2E|\bTP-[A-G]\b|\bP[12][abc]\b|UX 隔離|[0-9a-f]{8}-[0-9a-f]{4}-')
# Projects the demo script (docs/ai-demo-questions.md) opens by title prefix.
REQUIRED_PROJECTS = ('增量索引展示', '隔離索引展示', 'OCR 示範', '遮罩示範')


def alembic(*args):
    subprocess.run([sys.executable, '-m', 'alembic', '-c', str(API / 'alembic.ini'), *args],
                   cwd=API, env=os.environ.copy(), check=True)


def upload(client, url, path, **params):
    response = client.post(url, params={'filename': path.name, **params}, content=path.read_bytes(),
                           headers={'Content-Type': 'application/octet-stream'})
    response.raise_for_status()
    return response.json()


def add_project(client, title):
    response = client.post('/projects', json={'title': title})
    response.raise_for_status()
    return response.json()['id']


def add_documents(client, project_id, folder):
    """`v1/`, `v2/`… hold successive versions of the same file name; `task-attachments/<task>/` become task attachments."""
    ids = {}
    for version in sorted(p for p in folder.iterdir() if p.is_dir() and re.fullmatch(r'v\d+', p.name)):
        for path in sorted(version.iterdir()):
            if path.name in ids:
                upload(client, f"/documents/{ids[path.name]}/versions", path, expected_version=int(version.name[1:]) - 1)
            else:
                ids[path.name] = upload(client, f'/projects/{project_id}/documents', path)['document_id']
    tasks = folder / 'task-attachments'
    for task in sorted(tasks.iterdir()) if tasks.is_dir() else []:
        response = client.post(f'/projects/{project_id}/nodes', json={'title': task.name, 'kind': 'task'})
        response.raise_for_status()
        for path in sorted(task.iterdir()):
            upload(client, f"/nodes/{response.json()['id']}/attachments", path)


def build(out, ollama):
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine, select, delete
    from app import demo_pack
    from app.ai import model, store, vectors
    from app.ai.starter import import_starter
    from app.main import create_app
    from app.database import get_engine
    from app.models import Project, SessionToken

    # The pack is from an older revision and the importer writes with the current tables, so build the current
    # schema, label it with the pack's revision for the import, then label it current again. Later migrations
    # only add tables and defaulted columns, so the rows match a real upgrade.
    alembic('upgrade', 'head')
    alembic('stamp', json.loads((PACK / 'manifest.json').read_text(encoding='utf-8'))['alembic_revision'])
    engine = create_engine(os.environ['DATABASE_URL'], future=True)
    demo_pack.import_pack(engine, lambda name: (PACK / name).read_bytes(), out / 'files')
    engine.dispose()
    alembic('stamp', 'head')
    import_starter(STARTER, out / 'ai')
    store.import_pack(AI_DEMO, out / 'ai')  # the product importer checks checksums and the fixed SQL catalog
    # The model only runs on this computer, so every company gets the full demo, not just the starter companies.
    for company in sorted(store.COMPANIES):
        model.save(company, {'enabled': True, 'base_url': ollama, 'model': CHAT_MODEL})

    with TestClient(create_app()) as client:
        client.post('/auth/login', json={'organization_key': 'food', 'username': 'yu', 'password': 'demo-yu'}).raise_for_status()
        for folder, title in (('增量索引展示', '增量索引展示（虛構）'), ('隔離索引展示', '隔離索引展示（虛構）'),
                              ('OCR 示範（虛構）', 'OCR 示範（虛構）'), ('遮罩示範（虛構）', '遮罩示範（虛構）')):
            project_id = add_project(client, title)
            add_documents(client, project_id, DOCS / folder)
            if folder == '遮罩示範（虛構）':
                partner = client.post('/operations', json={'category': 'partners', 'code': 'P-DEMO-01', 'title': '青禾原料行',
                    'status': '合作中', 'fields': [{'label': '備註', 'value': '全部虛構，遮罩示範用'}]})
                partner.raise_for_status()
                client.post(f'/projects/{project_id}/operation-links', json={'record_id': partner.json()['id']}).raise_for_status()
        client.post('/document-templates/samples').raise_for_status()
        refreshed = client.post('/ai/index/refresh')
        refreshed.raise_for_status()
        client.post('/auth/logout')

    for company in STARTER_COMPANIES:
        with store.connect(company, 'starter-v1') as starter:
            vectors.starter_vectors(starter, company)

    with get_engine().begin() as conn:
        conn.execute(delete(SessionToken))
        titles = list(conn.scalars(select(Project.title)))
    get_engine().dispose()
    return titles, refreshed.json()


def check(out, titles):
    problems = [f'測試殘留專案：{t}' for t in titles if TEST_RESIDUE.search(t)]
    problems += [f'缺少示範專案：{p}' for p in REQUIRED_PROJECTS if not any(t.startswith(p) for t in titles)]
    # Paths are stored relative to the data roots; any absolute path means the seed is tied to this machine.
    markers = [str(REPO).encode(), str(REPO).replace('\\', '/').encode(), os.path.expanduser('~').encode(),
               os.path.expanduser('~').replace('\\', '/').encode()]
    for path in out.rglob('*'):
        if path.is_file():
            data = path.read_bytes()
            problems += [f'含本機路徑：{path.relative_to(out)}' for m in markers if m in data][:1]
    return problems


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--ollama', required=True, help='Package Ollama address, stored in the AI settings')
    parser.add_argument('--ocr-models', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists():
        parser.error(f'{out} 已存在；乾淨資料只建在新的資料夾')
    (out / 'files').mkdir(parents=True)
    os.environ.update({
        'DATABASE_URL': 'sqlite:///' + (out / 'projectflow.sqlite').as_posix(),
        'PF_ATTACHMENT_ROOT': str(out / 'files'), 'PF_AI_ROOT': str(out / 'ai'),
        'PF_ACCEPTANCE_MODE': 'true', 'PF_AI_FORMAL_INDEX': 'true', 'PF_SHOWCASE_MODE': 'false',
        'PF_AI_VECTOR_MODEL': VECTOR_MODEL, 'PF_AI_OCR_MODEL_DIR': str(args.ocr_models.resolve()),
    })
    os.environ.pop('PF_AI_INDEX_AUTO_UPDATE', None)  # one explicit refresh; no background worker while building
    sys.path.insert(0, str(API))
    titles, index = build(out, args.ollama)
    problems = check(out, titles)
    database = out / 'projectflow.sqlite'
    summary = {'projects': len(titles), 'index': index.get('counts'), 'problems': problems,
               'database_sha256': hashlib.sha256(database.read_bytes()).hexdigest()}
    (out / 'seed.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False))
    if problems:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
