import base64
import hashlib
import importlib.util
from pathlib import Path
import sqlite3
import subprocess
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.ai import store
from app.main import create_app
from app.routes import auth as auth_routes
from app.security import verify_password
from test_ai import pack, installed, login  # noqa: F401  共用 AI 展示資料 fixture

ROOT = Path(__file__).resolve().parents[2]
CREDENTIALS = {'organization_key': 'food', 'username': 'yu', 'password': 'demo-yu'}


# 1. session cookie 的 Secure

def test_login_cookie_is_secure_over_https_only(client):
    client.base_url = 'https://127.0.0.1'
    secure = client.post('/auth/login', json=CREDENTIALS)
    assert secure.status_code == 200
    assert 'secure' in secure.headers['set-cookie'].lower()
    logout = client.post('/auth/logout')
    assert logout.status_code == 204
    assert 'secure' in logout.headers['set-cookie'].lower()
    client.base_url = 'http://127.0.0.1'
    plain = client.post('/auth/login', json=CREDENTIALS)
    assert plain.status_code == 200
    assert 'secure' not in plain.headers['set-cookie'].lower()
    assert client.get('/auth/me').status_code == 200


# 2. 只限本機的 AI 模型設定不能靠 Host 偽造

def test_local_model_config_refused_when_web_is_open_to_lan(client, installed, monkeypatch):
    login(client)
    assert client.get('/ai/status').json()['can_configure'] is True
    assert client.get('/ai/model').status_code == 200
    monkeypatch.setenv('PF_WEB_LAN', 'true')
    # --lan 模式下區網訪客可以送 Host: 127.0.0.1，所以 Host 再像本機也不能放行。
    assert client.get('/ai/status').json()['can_configure'] is False
    assert client.get('/ai/model').status_code == 403
    assert client.put('/ai/model', json={'enabled': False}).status_code == 403
    assert client.get('/ai/model', headers={'Host': 'localhost'}).status_code == 403


def test_forged_loopback_host_from_public_entry_is_not_local(client, installed):
    client.base_url = 'https://pf.example.ts.net:10000'
    assert client.post('/auth/login', json=CREDENTIALS).status_code == 200
    assert client.get('/ai/status').json()['can_configure'] is False
    assert client.get('/ai/model').status_code == 403


@pytest.fixture
def start_module():
    spec = importlib.util.spec_from_file_location('trial_start_security', ROOT / 'deploy' / 'start.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('options,expected', [({}, 'false'), ({'lan': True}, 'true'), ({'public': True}, 'false')])
def test_start_tells_api_whether_web_is_open_to_lan(tmp_path, start_module, monkeypatch, options, expected):
    monkeypatch.setenv('PF_WEB_LAN', 'true' if expected == 'false' else 'false')
    calls = []

    def run(args, **kwargs):
        calls.append(kwargs['env'])
        bind = '0.0.0.0' if options.get('lan') else '127.0.0.1'
        output = {'80': f'{bind}:15173', '81': '127.0.0.1:15174'}.get(args[-1], '') if 'port' in args else ''
        return subprocess.CompletedProcess(args, 0, output, '')

    monkeypatch.setattr(start_module.subprocess, 'run', run)
    monkeypatch.setattr(start_module, 'check_readiness', MagicMock())
    start_module.start(tmp_path, **options)
    assert calls and all(env['PF_WEB_LAN'] == expected for env in calls)


def test_compose_passes_lan_flag_to_api_with_safe_default():
    compose = (ROOT / 'deploy/docker-compose.yml').read_text()
    api = compose[compose.index('  api:'):compose.index('  web:')]
    assert 'PF_WEB_LAN: ${PF_WEB_LAN:-false}' in api


# 3. 寫入請求的來源檢查

@pytest.mark.parametrize('headers', [
    {'Origin': 'http://evil.example'},
    {'Origin': 'http://127.0.0.1:8443'},
    {'Origin': 'null'},
    {'Sec-Fetch-Site': 'cross-site'},
    {'Sec-Fetch-Site': 'same-site'},
    {'Sec-Fetch-Site': 'same-site', 'Origin': 'http://127.0.0.1'},
])
def test_cross_origin_writes_are_refused(client, headers):
    client.base_url = 'http://127.0.0.1'
    response = client.post('/auth/login', json=CREDENTIALS, headers=headers)
    assert response.status_code == 403
    assert response.json() == {'detail': '不允許此來源'}
    assert 'set-cookie' not in response.headers
    for method in ('PUT', 'PATCH', 'DELETE'):
        assert client.request(method, '/projects/any', headers=headers).status_code == 403


@pytest.mark.parametrize('headers', [
    {},
    {'Origin': 'http://127.0.0.1'},
    {'Sec-Fetch-Site': 'same-origin', 'Origin': 'http://127.0.0.1'},
    {'Sec-Fetch-Site': 'none'},
    # 代理改寫 Host 的埠號時，瀏覽器自己判定的 same-origin 仍然可信。
    {'Sec-Fetch-Site': 'same-origin', 'Origin': 'https://pf.example.ts.net:10000'},
])
def test_same_origin_and_non_browser_writes_pass(client, headers):
    client.base_url = 'http://127.0.0.1'
    assert client.post('/auth/login', json=CREDENTIALS, headers=headers).status_code == 200


def test_reads_are_not_blocked_by_origin_check(client):
    client.base_url = 'http://127.0.0.1'
    assert client.get('/auth/me', headers={'Sec-Fetch-Site': 'cross-site', 'Origin': 'http://evil.example'}).status_code == 401


# 4. OpenAPI 與文件頁預設關閉

def test_api_docs_are_off_by_default(monkeypatch):
    monkeypatch.delenv('PF_API_DOCS', raising=False)
    with TestClient(create_app(checker=lambda: True)) as client:
        for path in ('/openapi.json', '/docs', '/redoc'):
            assert client.get(path).status_code == 404


def test_api_docs_can_be_enabled_for_development(monkeypatch):
    monkeypatch.setenv('PF_API_DOCS', 'true')
    with TestClient(create_app(checker=lambda: True)) as client:
        assert client.get('/openapi.json').status_code == 200
        assert client.get('/docs').status_code == 200


# 5. nginx 安全標頭

def test_nginx_sends_security_headers_on_every_response():
    nginx = (ROOT / 'deploy/nginx.conf').read_text()
    server = nginx[nginx.index('server {'):]
    head = server[:server.index('\n  location ')]
    for line in ['add_header X-Frame-Options "DENY" always;',
                 'add_header X-Content-Type-Options "nosniff" always;',
                 'add_header Referrer-Policy "same-origin" always;',
                 'add_header Content-Security-Policy "frame-ancestors \'none\'" always;']:
        assert line in head
    # location 一旦有自己的 add_header，就不再繼承 server 層的標頭。
    assert server.count('add_header') == 4


# 6. verify_password 依雜湊記錄的 rounds

def test_verify_password_uses_recorded_rounds():
    salt = b'0123456789abcdef'
    digest = hashlib.pbkdf2_hmac('sha256', b'secret', salt, 1000)
    encoded = 'pbkdf2_sha256$1000${}${}'.format(base64.b64encode(salt).decode(), base64.b64encode(digest).decode())
    assert verify_password('secret', encoded) is True
    assert verify_password('wrong', encoded) is False
    assert verify_password('secret', encoded.replace('$1000$', '$0$')) is False


# 7. 帳號不存在時也跑一次 PBKDF2

@pytest.mark.parametrize('payload', [
    {'organization_key': 'food', 'username': 'nobody', 'password': 'x'},
    {'organization_key': 'missing', 'username': 'yu', 'password': 'x'},
    {'organization_key': 'food', 'username': 'yu', 'password': 'x'},
])
def test_login_always_runs_one_password_check(client, monkeypatch, payload):
    calls = []
    original = auth_routes.verify_password

    def counting(password, encoded):
        calls.append(encoded)
        return original(password, encoded)

    monkeypatch.setattr(auth_routes, 'verify_password', counting)
    assert client.post('/auth/login', json=payload).status_code == 401
    assert len(calls) == 1
    assert calls[0].startswith('pbkdf2_sha256$')


# 8. AI SQL 錯誤轉成看得懂的回應

def test_ai_query_over_step_limit_is_a_clear_client_error(client, installed, monkeypatch):
    login(client)
    monkeypatch.setattr(store, 'PROGRESS_INTERVAL', 1)
    monkeypatch.setattr(store, 'PROGRESS_BUDGET', 1)
    response = client.post('/ai/ask', json={'question': '逾期', 'mode': 'sql', 'query_id': 'q02'})
    assert response.status_code == 422
    assert '查詢過於複雜' in response.json()['detail']


def test_ai_sqlite_failure_is_service_unavailable(client, installed, monkeypatch):
    login(client)

    def broken(*args, **kwargs):
        raise sqlite3.OperationalError('disk I/O error')

    monkeypatch.setattr(store, 'execute_query', broken)
    response = client.post('/ai/ask', json={'question': '逾期', 'mode': 'sql', 'query_id': 'q02'})
    assert response.status_code == 503
    assert response.json() == {'detail': 'AI展示資料暫時無法查詢，請稍後再試'}
