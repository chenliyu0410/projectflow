import importlib.util
import json
from pathlib import Path
import subprocess
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def start_module():
    path = Path(__file__).resolve().parents[2] / 'deploy' / 'start.py'
    spec = importlib.util.spec_from_file_location('trial_start', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def fake_commands(start_module, monkeypatch):
    calls = []

    def run(args, **kwargs):
        calls.append(args)
        output = '127.0.0.1:15175\n' if 'port' in args else ''
        return subprocess.CompletedProcess(args, 0, output, '')

    monkeypatch.setattr(start_module.subprocess, 'run', run)
    monkeypatch.setattr(start_module, 'check_readiness', MagicMock())
    return calls


def test_existing_env_is_preserved(tmp_path, start_module):
    path = tmp_path / '.env'
    path.write_bytes(b'EXISTING=unchanged\n')
    start_module.initialize_env(path, 15175, 18002, True)
    assert path.read_bytes() == b'EXISTING=unchanged\n'


def test_new_acceptance_env_is_private_and_unique(tmp_path, start_module):
    first, second = tmp_path / 'one' / '.env', tmp_path / 'two' / '.env'
    start_module.initialize_env(first, 15175, 18002, True)
    start_module.initialize_env(second, 15175, 18002, True)
    values = dict(line.split('=', 1) for line in first.read_text().splitlines())
    assert values['WEB_PORT'] == '15175'
    assert values['API_PORT'] == '18002'
    assert values['PF_ACCEPTANCE_MODE'] == 'true'
    assert len(bytes.fromhex(values['POSTGRES_PASSWORD'])) == 32
    assert first.read_bytes() != second.read_bytes()


def test_acceptance_commands_are_ordered_and_isolated(tmp_path, start_module, fake_commands):
    result = start_module.start(tmp_path, acceptance=True, seed_demo=True)
    assert result['project'] == 'projectflow-acceptance'
    assert result['web_url'] == 'http://127.0.0.1:15175'
    assert result['env_file'] == str(tmp_path / '.superpowers/p1c/acceptance.env')
    assert all('projectflow-acceptance' in args for args in fake_commands)
    tails = [args[8:] for args in fake_commands]
    assert tails == [
        ['config', '--quiet'], ['up', '-d', '--build', '--wait'],
        ['exec', '-T', 'api', 'python', '-m', 'alembic', 'upgrade', 'head'],
        ['exec', '-T', 'api', 'python', '-m', 'app.seed'], ['port', 'web', '80'],
    ]
    start_module.check_readiness.assert_called_once_with('http://127.0.0.1:15175', acceptance=True)
    assert not any('down' in args or '-v' in args for args in fake_commands)


def test_regular_start_does_not_seed_and_preserves_env(tmp_path, start_module, fake_commands):
    env = tmp_path / 'deploy/.env'
    env.parent.mkdir()
    env.write_bytes(b'POSTGRES_PASSWORD=preserve\nWEB_PORT=15175\n')
    result = start_module.start(tmp_path)
    assert result['project'] == 'projectflow-formal'
    assert env.read_bytes() == b'POSTGRES_PASSWORD=preserve\nWEB_PORT=15175\n'
    assert all('projectflow-formal' in args for args in fake_commands)
    assert not any('app.seed' in args for args in fake_commands)


def test_failed_command_stops_and_hides_secrets(tmp_path, start_module, monkeypatch):
    runner = MagicMock(return_value=subprocess.CompletedProcess([], 1, '', 'secret-password'))
    monkeypatch.setattr(start_module.subprocess, 'run', runner)
    with pytest.raises(RuntimeError) as error:
        start_module.start(tmp_path)
    assert 'secret-password' not in str(error.value)
    assert runner.call_count == 1


def test_missing_docker_is_safe(tmp_path, start_module, monkeypatch):
    monkeypatch.setattr(start_module.subprocess, 'run', MagicMock(side_effect=FileNotFoundError('secret-path')))
    with pytest.raises(RuntimeError) as error:
        start_module.start(tmp_path)
    assert 'secret-path' not in str(error.value)


@pytest.mark.parametrize('address', ['0.0.0.0:15175', 'example.com:15175', '127.0.0.1:0', '127.0.0.1:70000', 'garbage', '127.0.0.1:15175/path'])
def test_invalid_public_port_is_rejected(tmp_path, start_module, fake_commands, monkeypatch, address):
    monkeypatch.setattr(start_module.subprocess, 'run', lambda args, **kwargs: subprocess.CompletedProcess(args, 0, address, ''))
    with pytest.raises(RuntimeError):
        start_module.start(tmp_path)
    start_module.check_readiness.assert_not_called()


def test_readiness_and_marker_contract(start_module, monkeypatch):
    calls = []

    def open_url(url, **kwargs):
        calls.append((url, kwargs['timeout']))
        body = {'acceptance': True} if url.endswith('/acceptance') else {'ok': True, 'database': 'ready'}
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(body).encode()
        return response

    monkeypatch.setattr(start_module.urllib.request, 'urlopen', open_url)
    start_module.check_readiness('http://127.0.0.1:15175', acceptance=True)
    assert calls == [('http://127.0.0.1:15175/api/health/ready', 5), ('http://127.0.0.1:15175/api/health/acceptance', 5)]


def test_invalid_readiness_rejected(start_module, monkeypatch):
    response = MagicMock()
    response.__enter__.return_value.read.return_value = b'{"ok": true, "database": "unexpected"}'
    monkeypatch.setattr(start_module.urllib.request, 'urlopen', lambda *args, **kwargs: response)
    with pytest.raises(RuntimeError):
        start_module.check_readiness('http://127.0.0.1:15175', acceptance=False)


def test_shared_start_cannot_inherit_acceptance_marker(tmp_path, start_module, monkeypatch):
    monkeypatch.setenv('PF_ACCEPTANCE_MODE', 'true')
    calls = []
    def run(args, **kwargs):
        calls.append(kwargs)
        return subprocess.CompletedProcess(args, 0, '127.0.0.1:15173' if 'port' in args else '', '')
    monkeypatch.setattr(start_module.subprocess, 'run', run)
    monkeypatch.setattr(start_module, 'check_readiness', lambda *args, **kwargs: None)
    start_module.start(tmp_path)
    assert all(call['env']['PF_ACCEPTANCE_MODE'] == 'false' for call in calls)


def test_docker_output_is_decoded_as_utf8(start_module, monkeypatch):
    runner = MagicMock(return_value=subprocess.CompletedProcess([], 0, 'output', ''))
    monkeypatch.setattr(start_module.subprocess, 'run', runner)
    assert start_module.run(['docker', 'version']) == 'output'
    assert runner.call_args.kwargs['encoding'] == 'utf-8'
    assert runner.call_args.kwargs['errors'] == 'replace'
