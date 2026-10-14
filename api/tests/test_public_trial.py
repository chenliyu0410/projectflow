import importlib.util
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

TARGET = 'http://127.0.0.1:15174'
OTHERS = {
    'TCP': {'443': {'HTTPS': True}, '8443': {'HTTPS': True}},
    'Web': {'host.tailnet.ts.net:443': {'Handlers': {'/': {'Proxy': 'http://127.0.0.1:8000'}}},
            'host.tailnet.ts.net:8443': {'Handlers': {'/': {'Proxy': 'http://127.0.0.1:8766'}}}},
}


def with_port_10000(proxy):
    config = json.loads(json.dumps(OTHERS))
    config['TCP']['10000'] = {'HTTPS': True}
    config['Web']['host.tailnet.ts.net:10000'] = {'Handlers': {'/': {'Proxy': proxy}}}
    return config


@pytest.fixture
def launcher(monkeypatch):
    path = Path(__file__).resolve().parents[2] / 'deploy' / 'public_trial.py'
    spec = importlib.util.spec_from_file_location('public_trial', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, 'pause', lambda seconds: None)
    return module


@pytest.fixture
def tailscale(launcher, monkeypatch):
    """Fake tailscale.exe: `funnel` holds the current Funnel config, `calls` every invocation."""
    state = {'funnel': OTHERS, 'calls': [], 'status': {'BackendState': 'Running', 'Self': {'DNSName': 'host.tailnet.ts.net.'}}}

    def command(args, timeout):
        assert timeout
        if args[0] != str(launcher.TAILSCALE):
            return 0, ''
        state['calls'].append(args[1:])
        if args[1:] == ['status', '--json']:
            return 0, json.dumps(state['status'])
        if args[1:] == ['funnel', 'status', '--json']:
            return 0, json.dumps(state['funnel'])
        return 0, ''

    monkeypatch.setattr(launcher, 'command', command)
    return state


def changes(state):
    return [call for call in state['calls'] if call[-1] != '--json']


def test_publish_uses_port_10000_when_free(launcher, tailscale):
    launcher.publish(TARGET)
    assert changes(tailscale) == [['funnel', '--bg', '--https=10000', TARGET]]


def test_publish_again_is_idempotent(launcher, tailscale):
    tailscale['funnel'] = with_port_10000(TARGET)
    launcher.publish(TARGET)
    assert changes(tailscale) == [['funnel', '--bg', '--https=10000', TARGET]]


@pytest.mark.parametrize('config', [with_port_10000('http://127.0.0.1:9999'),
                                    {'TCP': {'10000': {'TCPForward': '127.0.0.1:22'}}}])
def test_publish_never_takes_over_someone_elses_port_10000(launcher, tailscale, config):
    tailscale['funnel'] = config
    with pytest.raises(RuntimeError):
        launcher.publish(TARGET)
    assert changes(tailscale) == []


def test_publish_refuses_when_funnel_status_is_unreadable(launcher, tailscale, monkeypatch):
    monkeypatch.setattr(launcher, 'command', lambda args, timeout: (None, ''))
    with pytest.raises(RuntimeError):
        launcher.publish(TARGET)


def test_unpublish_turns_off_only_our_funnel(launcher, tailscale):
    tailscale['funnel'] = with_port_10000(TARGET)
    assert launcher.unpublish(TARGET) is True
    assert changes(tailscale) == [['funnel', '--https=10000', 'off']]


@pytest.mark.parametrize('config', [OTHERS, with_port_10000('http://127.0.0.1:9999')])
def test_unpublish_leaves_other_funnels_alone(launcher, tailscale, config):
    tailscale['funnel'] = config
    assert launcher.unpublish(TARGET) is False
    assert changes(tailscale) == []


def test_tailnet_name_drops_trailing_dot_and_waits_for_running(launcher, tailscale):
    assert launcher.wait_for_tailscale(timeout_s=0) == 'host.tailnet.ts.net'
    tailscale['status'] = {'BackendState': 'NeedsLogin', 'Self': {'DNSName': 'host.tailnet.ts.net.'}}
    assert launcher.wait_for_tailscale(timeout_s=0) is None


def test_missing_or_hung_cli_is_reported_not_raised(launcher, monkeypatch):
    def hang(*args, **kwargs):
        raise launcher.subprocess.TimeoutExpired('tailscale', 15)
    monkeypatch.setattr(launcher.subprocess, 'run', hang)
    assert launcher.command(['tailscale', 'status'], 15) == (None, '')
    monkeypatch.setattr(launcher.subprocess, 'run', MagicMock(side_effect=FileNotFoundError()))
    assert launcher.command(['docker', 'info'], 15) == (None, '')


def test_docker_desktop_is_launched_once_while_waiting(launcher, monkeypatch, tmp_path):
    answers = iter([False, False, True])
    monkeypatch.setattr(launcher, 'docker_ready', lambda: next(answers))
    desktop = tmp_path / 'Docker Desktop.exe'
    desktop.write_bytes(b'')
    monkeypatch.setattr(launcher, 'DOCKER_DESKTOP', desktop)
    popen = MagicMock()
    monkeypatch.setattr(launcher.subprocess, 'Popen', popen)
    assert launcher.wait_for_docker(timeout_s=60) is True
    popen.assert_called_once_with([str(desktop)])


def test_up_starts_public_stack_then_publishes_and_checks_both_urls(launcher, tailscale, monkeypatch, capsys):
    order = []
    monkeypatch.setattr(launcher, 'wait_for_docker', lambda: order.append('docker') or True)
    stack = MagicMock(side_effect=lambda root, **kwargs: order.append(('start', kwargs)) or
                      {'web_url': 'http://127.0.0.1:15173', 'public_target': TARGET})
    monkeypatch.setattr(launcher.trial, 'start', stack)
    checked = []
    monkeypatch.setattr(launcher, 'http_status', lambda url, timeout=10: checked.append(url) or 200)
    assert launcher.main([]) == 0
    assert order == ['docker', ('start', {'public': True})]
    assert changes(tailscale) == [['funnel', '--bg', '--https=10000', TARGET]]
    assert checked == ['http://127.0.0.1:15173/api/health/ready', 'https://host.tailnet.ts.net:10000/api/health/ready']
    assert 'https://host.tailnet.ts.net:10000' in capsys.readouterr().out


def test_up_does_not_touch_funnel_when_the_stack_fails(launcher, tailscale, monkeypatch):
    monkeypatch.setattr(launcher, 'wait_for_docker', lambda: True)
    monkeypatch.setattr(launcher.trial, 'start', MagicMock(side_effect=RuntimeError('secret')))
    assert launcher.main([]) == 1
    assert tailscale['calls'] == []


def test_up_stops_when_docker_never_becomes_ready(launcher, tailscale, monkeypatch):
    monkeypatch.setattr(launcher, 'wait_for_docker', lambda: False)
    stack = MagicMock()
    monkeypatch.setattr(launcher.trial, 'start', stack)
    assert launcher.main([]) == 1
    stack.assert_not_called()
    assert tailscale['calls'] == []


def test_up_reports_failure_when_public_url_is_not_ready(launcher, tailscale, monkeypatch):
    monkeypatch.setattr(launcher, 'wait_for_docker', lambda: True)
    monkeypatch.setattr(launcher.trial, 'start', MagicMock(return_value={'web_url': 'http://127.0.0.1:15173', 'public_target': TARGET}))
    monkeypatch.setattr(launcher, 'http_status', lambda url, timeout=10: 200 if '127.0.0.1' in url else 502)
    assert launcher.main([]) == 1


def test_stop_unpublishes_then_restarts_loopback_only(launcher, tailscale, monkeypatch):
    tailscale['funnel'] = with_port_10000(TARGET)
    monkeypatch.setattr(launcher, 'docker_ready', lambda: True)
    stack = MagicMock(return_value={'web_url': 'http://127.0.0.1:15173', 'public_target': None})
    monkeypatch.setattr(launcher.trial, 'start', stack)
    assert launcher.main(['--stop']) == 0
    assert changes(tailscale) == [['funnel', '--https=10000', 'off']]
    stack.assert_called_once_with(launcher.ROOT)


def test_stop_target_matches_the_public_overlay(launcher):
    assert launcher.PUBLIC_TARGET == f'http://127.0.0.1:{launcher.trial.PUBLIC_WEB_PORT}'
