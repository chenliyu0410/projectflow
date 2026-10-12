import importlib.util
import json
import os
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


def test_lan_start_binds_all_interfaces_but_checks_loopback(tmp_path, start_module, monkeypatch):
    calls = []
    def run(args, **kwargs):
        calls.append(kwargs['env'])
        return subprocess.CompletedProcess(args, 0, '0.0.0.0:15173\n' if 'port' in args else '', '')
    monkeypatch.setattr(start_module.subprocess, 'run', run)
    monkeypatch.setattr(start_module, 'check_readiness', MagicMock())
    result = start_module.start(tmp_path, lan=True)
    assert result['web_url'] == 'http://127.0.0.1:15173'
    assert result['lan'] is True
    assert calls and all(env['WEB_BIND'] == '0.0.0.0' for env in calls)
    start_module.check_readiness.assert_called_once_with('http://127.0.0.1:15173', acceptance=False)


def test_default_start_forces_loopback_bind(tmp_path, start_module, monkeypatch):
    monkeypatch.setenv('WEB_BIND', '0.0.0.0')
    calls = []
    def run(args, **kwargs):
        calls.append(kwargs['env'])
        return subprocess.CompletedProcess(args, 0, '127.0.0.1:15173' if 'port' in args else '', '')
    monkeypatch.setattr(start_module.subprocess, 'run', run)
    monkeypatch.setattr(start_module, 'check_readiness', MagicMock())
    result = start_module.start(tmp_path)
    assert result['lan'] is False
    assert calls and all(env['WEB_BIND'] == '127.0.0.1' for env in calls)


@pytest.mark.parametrize('address', ['127.0.0.1:15173', 'example.com:15173', '0.0.0.0:0'])
def test_lan_start_rejects_unexpected_binding(tmp_path, start_module, monkeypatch, address):
    monkeypatch.setattr(start_module.subprocess, 'run', lambda args, **kwargs: subprocess.CompletedProcess(args, 0, address, ''))
    monkeypatch.setattr(start_module, 'check_readiness', MagicMock())
    with pytest.raises(RuntimeError):
        start_module.start(tmp_path, lan=True)
    start_module.check_readiness.assert_not_called()


def test_lan_is_refused_for_acceptance_before_any_command(tmp_path, start_module, monkeypatch):
    runner = MagicMock()
    monkeypatch.setattr(start_module.subprocess, 'run', runner)
    with pytest.raises(RuntimeError):
        start_module.start(tmp_path, acceptance=True, lan=True)
    runner.assert_not_called()
    assert not (tmp_path / '.superpowers').exists()


def test_compose_web_bind_defaults_to_loopback_and_api_stays_loopback():
    compose = (Path(__file__).resolve().parents[2] / 'deploy/docker-compose.yml').read_text()
    assert "'${WEB_BIND:-127.0.0.1}:${WEB_PORT:-15173}:80'" in compose
    assert "'127.0.0.1:${API_PORT:-18000}:8000'" in compose
    assert compose.count('WEB_BIND') == 1


def test_docker_output_is_decoded_as_utf8(start_module, monkeypatch):
    runner = MagicMock(return_value=subprocess.CompletedProcess([], 0, 'output', ''))
    monkeypatch.setattr(start_module.subprocess, 'run', runner)
    assert start_module.run(['docker', 'version']) == 'output'
    assert runner.call_args.kwargs['encoding'] == 'utf-8'
    assert runner.call_args.kwargs['errors'] == 'replace'


@pytest.fixture
def verify_module(monkeypatch):
    directory = Path(__file__).resolve().parents[2] / 'deploy'
    monkeypatch.syspath_prepend(str(directory))
    spec = importlib.util.spec_from_file_location('trial_verify', directory / 'verify.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def verification_commands(tmp_path, verify_module, monkeypatch):
    calls = []
    def start(root, **kwargs):
        calls.append(('start', root, kwargs))
        return {'project': 'projectflow-acceptance', 'web_url': 'http://127.0.0.1:15175',
                'env_file': str(tmp_path / '.superpowers/p1c/acceptance.env')}
    def run(args, **kwargs):
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(args, 0)
    monkeypatch.setattr(verify_module, 'start', start)
    monkeypatch.setattr(verify_module, 'postgresql_acceptance', lambda *args: 0)
    monkeypatch.setattr(verify_module.subprocess, 'run', run)
    monkeypatch.setattr(verify_module.shutil, 'which', lambda name: name)
    return calls


def test_verify_command_order_and_child_env(tmp_path, verify_module, verification_commands, monkeypatch):
    monkeypatch.setenv('PF_BASE_URL', 'http://127.0.0.1:15173')
    before = dict(os.environ)
    assert verify_module.verify(tmp_path) == 0
    calls = verification_commands
    assert calls[0] == ('start', tmp_path, {'acceptance': True, 'seed_demo': True})
    npm = 'npm.cmd' if os.name == 'nt' else 'npm'
    assert [call[0] for call in calls[1:5]] == [
        [verify_module.sys.executable, '-m', 'pytest', '-c', str(tmp_path / 'api/pyproject.toml'), str(tmp_path / 'api/tests'), '-q'],
        [npm, '--prefix', str(tmp_path / 'web'), 'test'],
        [npm, '--prefix', str(tmp_path / 'web'), 'run', 'build'],
        [npm, '--prefix', str(tmp_path / 'web'), 'run', 'e2e'],
    ]
    assert all(call[1]['cwd'] == tmp_path for call in calls[1:5])
    assert all(call[1]['env']['PF_BASE_URL'] == 'http://127.0.0.1:15175' for call in calls[1:5])
    assert dict(os.environ) == before
    cleanup, options = calls[-1]
    assert cleanup == ['docker', 'compose', '--project-name', 'projectflow-acceptance',
                       '--env-file', str(tmp_path / '.superpowers/p1c/acceptance.env'),
                       '-f', str(tmp_path / 'deploy/docker-compose.yml'), 'down']
    assert options['capture_output'] is True
    assert '-v' not in cleanup and 'projectflow-formal' not in cleanup


@pytest.mark.parametrize('failed_stage', [0, 1, 2, 3])
def test_verify_failure_stops_later_stages_and_preserves_exit(tmp_path, verify_module, verification_commands, monkeypatch, failed_stage):
    stages = []
    def run(args, **kwargs):
        if 'down' in args:
            verification_commands.append((args, kwargs))
            return subprocess.CompletedProcess(args, 9, '', 'private-cleanup-secret')
        stages.append(args)
        return subprocess.CompletedProcess(args, 7 if len(stages) - 1 == failed_stage else 0)
    monkeypatch.setattr(verify_module.subprocess, 'run', run)
    assert verify_module.verify(tmp_path) == 7
    assert len(stages) == failed_stage + 1
    assert verification_commands[-1][0][-1] == 'down'


def test_verify_keep_running_avoids_down(tmp_path, verify_module, verification_commands):
    assert verify_module.verify(tmp_path, keep_running=True) == 0
    assert len(verification_commands) == 5
    assert not any('down' in call[0] for call in verification_commands)


def test_verify_cleanup_failure_is_nonzero_and_sanitized(tmp_path, verify_module, verification_commands, monkeypatch, capsys):
    original = verify_module.subprocess.run
    def run(args, **kwargs):
        if 'down' in args:
            return subprocess.CompletedProcess(args, 3, 'private-secret', 'private-secret')
        return original(args, **kwargs)
    monkeypatch.setattr(verify_module.subprocess, 'run', run)
    assert verify_module.verify(tmp_path) != 0
    assert 'private-secret' not in capsys.readouterr().out


@pytest.mark.parametrize('failure', [RuntimeError('private-secret'), OSError('private-secret')])
def test_verify_start_failure_does_not_stop_any_project(tmp_path, verify_module, verification_commands, monkeypatch, capsys, failure):
    def fail(*args, **kwargs):
        raise failure
    monkeypatch.setattr(verify_module, 'start', fail)
    assert verify_module.verify(tmp_path) != 0
    assert verification_commands == []
    assert 'private-secret' not in capsys.readouterr().out


@pytest.mark.parametrize('failure', [OSError('private-secret'), subprocess.TimeoutExpired(['private-secret'], 1)])
def test_verify_subprocess_exception_is_sanitized_and_cleanup_runs(tmp_path, verify_module, verification_commands, monkeypatch, capsys, failure):
    def run(args, **kwargs):
        verification_commands.append((args, kwargs))
        if 'down' not in args:
            raise failure
        return subprocess.CompletedProcess(args, 0)
    monkeypatch.setattr(verify_module.subprocess, 'run', run)
    assert verify_module.verify(tmp_path) != 0
    assert verification_commands[-1][0][-1] == 'down'
    assert 'private-secret' not in capsys.readouterr().out


def test_verify_missing_npm_fails_safely_before_start(tmp_path, verify_module, verification_commands, monkeypatch, capsys):
    monkeypatch.setattr(verify_module.shutil, 'which', lambda name: None)
    assert verify_module.verify(tmp_path) != 0
    assert verification_commands == []
    assert 'npm' in capsys.readouterr().out.lower()


@pytest.mark.parametrize('field,value', [
    ('project', 'projectflow-formal'), ('web_url', 'http://127.0.0.1:15173'),
    ('web_url', 'http://example.com:15175'), ('env_file', 'deploy/.env'),
])
def test_verify_rejects_non_acceptance_start_result(tmp_path, verify_module, verification_commands, monkeypatch, field, value):
    result = {'project': 'projectflow-acceptance', 'web_url': 'http://127.0.0.1:15175',
              'env_file': str(tmp_path / '.superpowers/p1c/acceptance.env')}
    result[field] = value
    monkeypatch.setattr(verify_module, 'start', lambda *args, **kwargs: result)
    assert verify_module.verify(tmp_path) != 0
    assert verification_commands == []


def test_verify_uses_returned_loopback_acceptance_port(tmp_path, verify_module, verification_commands, monkeypatch):
    monkeypatch.setattr(verify_module, 'start', lambda *args, **kwargs: {
        'project': 'projectflow-acceptance', 'web_url': 'http://127.0.0.1:15177',
        'env_file': str(tmp_path / '.superpowers/p1c/acceptance.env')})
    assert verify_module.verify(tmp_path, keep_running=True) == 0
    assert all(call[1]['env']['PF_BASE_URL'] == 'http://127.0.0.1:15177' for call in verification_commands)


def test_attachment_volume_runtime_and_proxy_contracts():
    root=Path(__file__).resolve().parents[2]
    docker=(root/'deploy/api.Dockerfile').read_text()
    compose=(root/'deploy/docker-compose.yml').read_text()
    nginx=(root/'deploy/nginx.conf').read_text()
    assert '10001' in docker and '0700' in docker
    assert docker.index('/var/lib/projectflow-files') < docker.index('USER appuser')
    assert 'files:/var/lib/projectflow-files' in compose and 'nocopy' not in compose
    assert 'PF_ATTACHMENT_ROOT:' in compose and 'PF_ATTACHMENT_QUOTA_BYTES:' in compose
    assert 'client_max_body_size 10000000;' in nginx
    assert 'proxy_read_timeout 8s;' in nginx
    assert 'proxy_read_timeout 120s;' in nginx


def test_new_env_includes_attachment_configuration(tmp_path,start_module):
    path=tmp_path/'attachment.env'
    start_module.initialize_env(path,15177,18004,True)
    values=dict(line.split('=',1) for line in path.read_text().splitlines())
    assert values['PF_ATTACHMENT_ROOT']=='/var/lib/projectflow-files'
    assert values['PF_ATTACHMENT_QUOTA_BYTES']=='1000000000'


def test_verify_requires_postgresql_before_host_tests(tmp_path, verify_module, verification_commands, monkeypatch):
    seen=[]
    monkeypatch.setattr(verify_module,'postgresql_acceptance',lambda *args: seen.append(args) or 0,raising=False)
    assert verify_module.verify(tmp_path)==0
    assert len(seen)==1
    assert seen[0][1]['project']=='projectflow-acceptance'


def test_verify_postgresql_failure_stops_host_tests(tmp_path, verify_module, verification_commands, monkeypatch):
    monkeypatch.setattr(verify_module,'postgresql_acceptance',lambda *args: 6,raising=False)
    assert verify_module.verify(tmp_path)==6
    assert len(verification_commands)==2
    assert verification_commands[-1][0][-1]=='down'


def test_verify_clears_inherited_database_and_attachment_targets(tmp_path, verify_module, verification_commands, monkeypatch):
    for key in ('DATABASE_URL','P2B_TEST_DATABASE_URL','P2A_MIGRATION_TEST_URL','PF_ATTACHMENT_ROOT'):
        monkeypatch.setenv(key,'private-primary-setting')
    before=dict(os.environ)
    assert verify_module.verify(tmp_path)==0
    for command, options in verification_commands[1:-1]:
        assert not any(key in options['env'] for key in ('DATABASE_URL','P2B_TEST_DATABASE_URL','P2A_MIGRATION_TEST_URL','PF_ATTACHMENT_ROOT'))
    assert dict(os.environ)==before


def test_postgresql_stage_uses_acceptance_container_stdin_and_propagates_failure(tmp_path,verify_module,monkeypatch):
    folder=tmp_path/'api/tests';folder.mkdir(parents=True)
    for name in ('test_migrations.py','test_collaboration_postgresql.py'):
        (folder/name).write_text('# test fixture')
    result={'project':'projectflow-acceptance','web_url':'http://127.0.0.1:15175','env_file':str(tmp_path/'.superpowers/p1c/acceptance.env')}
    runner=MagicMock(return_value=subprocess.CompletedProcess([],6))
    monkeypatch.setattr(verify_module.subprocess,'run',runner)
    assert verify_module.postgresql_acceptance(tmp_path,result,{'PF_BASE_URL':result['web_url']})==6
    command=runner.call_args.args[0];options=runner.call_args.kwargs
    assert command[:4]==['docker','compose','--project-name','projectflow-acceptance']
    assert command[-6:-1]==['exec','-T','api','python','-c']
    assert 'DATABASE_URL' not in options['env']
    assert set(json.loads(options['input']))=={'test_migrations.py','test_collaboration_postgresql.py'}
    runner.reset_mock()
    assert verify_module.postgresql_acceptance(tmp_path,{**result,'project':'projectflow-formal'}, {})==1
    runner.assert_not_called()
