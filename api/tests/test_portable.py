import importlib.util
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]


def load(name):
    spec = importlib.util.spec_from_file_location(f'portable_{name}', ROOT / 'deploy' / 'portable' / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def web(tmp_path):
    (tmp_path / 'assets').mkdir()
    (tmp_path / 'index.html').write_text('<!doctype html><title>專流</title>', encoding='utf-8')
    (tmp_path / 'assets' / 'app.js').write_text('console.log(1)', encoding='utf-8')
    (tmp_path.parent / 'secret.txt').write_text('outside', encoding='utf-8')
    return tmp_path


def fake_api(events):
    @asynccontextmanager
    async def lifespan(application):
        events.append('start')
        yield
        events.append('stop')

    api = FastAPI(lifespan=lifespan)

    @api.get('/health')
    def health():
        return {'ok': True}
    return api


def test_api_is_served_under_prefix_and_its_lifespan_runs(web):
    events = []
    with TestClient(load('serve').create(fake_api(events), web)) as client:
        # A mounted app's lifespan does not run by default; the index worker and attachment lock depend on it.
        assert events == ['start']
        assert client.get('/api/health').json() == {'ok': True}
    assert events == ['start', 'stop']


def test_frontend_files_and_page_reload_fallback(web):
    with TestClient(load('serve').create(fake_api([]), web)) as client:
        assert '專流' in client.get('/').text
        script = client.get('/assets/app.js')
        assert script.status_code == 200 and 'javascript' in script.headers['content-type']
        # Reloading a client-side route still returns the app shell.
        assert '專流' in client.get('/projects/abc').text
        assert client.get('/assets/missing.js').status_code == 404
        assert client.get('/api/missing').status_code == 404


def test_frontend_never_serves_files_outside_web_root(web):
    with TestClient(load('serve').create(fake_api([]), web)) as client:
        for path in ('/../secret.txt', '/%2e%2e/secret.txt', '/assets/..%2f..%2fsecret.txt'):
            assert 'outside' not in client.get(path).text


def test_server_only_binds_loopback():
    assert load('serve').HOST == '127.0.0.1'


def test_seed_check_flags_test_leftovers_but_not_demo_projects():
    residue = load('build_seed').TEST_RESIDUE
    for leftover in ('TP-A 375 d1df03fe-5c41-4c55-92cd-0083f5667f60', '隔離索引展示 1280 1792506563471',
                     'P2b files facc179a-1726-4fd1-be34-33e930ee5a6b', 'UX 隔離驗證 8d3691ca', 'P1b E2E 1280 x'):
        assert residue.search(leftover), leftover
    for demo in ('成貓主食罐正式版', '增量索引展示（虛構）', 'OCR 示範（虛構）', '十月新人報到', '筆電新機種 2026Q4'):
        assert not residue.search(demo), demo
