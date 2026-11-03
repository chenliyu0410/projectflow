"""Start the local trial or its isolated acceptance stack without resetting data."""

import argparse
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import urllib.error
import urllib.parse
import urllib.request

# Loopback port that deploy/docker-compose.public.yml opens for Tailscale Funnel (nginx port 81).
PUBLIC_WEB_PORT = 15174


def initialize_env(path: Path, web_port: int, api_port: int, acceptance: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open('x', encoding='utf-8', newline='\n') as handle:
            handle.write(f'POSTGRES_PASSWORD={secrets.token_hex(32)}\n'
                         f'WEB_PORT={web_port}\nAPI_PORT={api_port}\n'
                         f'PF_ACCEPTANCE_MODE={str(acceptance).lower()}\n'
                         'PF_ATTACHMENT_ROOT=/var/lib/projectflow-files\n'
                         'PF_ATTACHMENT_QUOTA_BYTES=1000000000\n')
        path.chmod(0o600)
    except FileExistsError:
        return


def n8n_configured(env_file: Path) -> bool:
    """Setting up n8n adds PF_N8N_TOKEN (deploy/n8n/README.md); without it n8n's images may be missing here."""
    token = ''
    # Like Compose: a BOM is ignored and the last assignment wins.
    for line in env_file.read_text(encoding='utf-8-sig', errors='replace').splitlines():
        key, sep, value = line.partition('=')
        if sep and key.strip() == 'PF_N8N_TOKEN':
            token = value.strip()
    return bool(token)


def compose_prefix(root: Path, project: str, env_file: Path, *, public: bool = False, n8n: bool = False) -> list[str]:
    prefix = ['docker', 'compose', '--project-name', project, '--env-file', str(env_file),
              '-f', str(root / 'deploy/docker-compose.yml')]
    if public:
        prefix += ['-f', str(root / 'deploy/docker-compose.public.yml')]
    # Without the profile, a logon restart would leave n8n and Mailpit stopped (Compose sets no restart policy).
    return prefix + ['--profile', 'n8n'] if n8n else prefix


def run(args: list[str], *, acceptance: bool = False, lan: bool = False, public: bool = False) -> str:
    try:
        environment = {**os.environ, 'PF_ACCEPTANCE_MODE': str(acceptance).lower(),
                       'WEB_BIND': '0.0.0.0' if lan else '127.0.0.1',
                       'PF_SHOWCASE_LAN': str(lan or public).lower(),
                       # 只有 --lan 讓 web 80 對區網開放；API 據此不再把 Host 是 loopback 的請求當成本機。
                       'PF_WEB_LAN': str(lan).lower()}
        result = subprocess.run(args, capture_output=True, text=True, encoding='utf-8', errors='replace',
                                check=False, timeout=600, env=environment)
    except (OSError, subprocess.TimeoutExpired):
        raise RuntimeError('Docker is unavailable or the operation timed out.') from None
    if result.returncode:
        raise RuntimeError('Compose operation failed; inspect the local Docker service.')
    return result.stdout.strip()


def check_readiness(url: str, *, acceptance: bool) -> None:
    contracts = [('/api/health/ready', {'ok': True, 'database': 'ready'})]
    if acceptance:
        contracts.append(('/api/health/acceptance', {'acceptance': True}))
    for path, expected in contracts:
        try:
            with urllib.request.urlopen(url + path, timeout=5) as response:
                body = json.loads(response.read())
        except (OSError, ValueError):
            raise RuntimeError('The application did not confirm trial readiness.') from None
        if body != expected:
            raise RuntimeError('The application did not confirm trial readiness.')


def published_port(address: str, host: str) -> int:
    try:
        parsed = urllib.parse.urlsplit('http://' + address)
        valid = (parsed.hostname == host and parsed.port is not None
                 and 0 < parsed.port <= 65535 and not parsed.path and not parsed.query
                 and not parsed.fragment and parsed.username is None and parsed.password is None)
    except ValueError:
        valid = False
    if not valid:
        raise RuntimeError('The trial web port is not bound to the expected address.')
    return parsed.port


def start(root: Path, *, acceptance: bool = False, seed_demo: bool = False, lan: bool = False,
          public: bool = False) -> dict:
    """public=True also opens the loopback port Tailscale Funnel forwards to; deploy/public_trial.py owns Funnel."""
    if acceptance and (lan or public):
        raise RuntimeError('The acceptance stack must stay on loopback.')
    root = root.resolve()
    project = 'projectflow-acceptance' if acceptance else 'projectflow-formal'
    env_file = root / ('.superpowers/p1c/acceptance.env' if acceptance else 'deploy/.env')
    initialize_env(env_file, 15175 if acceptance else 15173, 18002 if acceptance else 18000, acceptance)
    prefix = compose_prefix(root, project, env_file, public=public, n8n=not acceptance and n8n_configured(env_file))
    options = {'acceptance': acceptance, 'lan': lan, 'public': public}
    run(prefix + ['config', '--quiet'], **options)
    run(prefix + ['up', '-d', '--build', '--wait'], **options)
    run(prefix + ['exec', '-T', 'api', 'python', '-m', 'alembic', 'upgrade', 'head'], **options)
    if seed_demo:
        run(prefix + ['exec', '-T', 'api', 'python', '-m', 'app.seed'], **options)
    port = published_port(run(prefix + ['port', 'web', '80'], **options), '0.0.0.0' if lan else '127.0.0.1')
    public_target = None
    if public:
        public_target = f"http://127.0.0.1:{published_port(run(prefix + ['port', 'web', '81'], **options), '127.0.0.1')}"
    url = f'http://127.0.0.1:{port}'
    check_readiness(url, acceptance=acceptance)
    return {'project': project, 'web_url': url, 'env_file': str(env_file), 'lan': lan, 'public_target': public_target}


def lan_address() -> str | None:
    """Best-effort IPv4 of the default route; connecting a UDP socket sends no packet."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(('192.0.2.1', 80))
            return probe.getsockname()[0]
    except OSError:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--acceptance', action='store_true', help='Use a separate test project and database.')
    parser.add_argument('--seed-demo', action='store_true', help='Explicitly initialize local trial accounts and examples.')
    parser.add_argument('--lan', action='store_true', help='Also serve the trial web on this network; restart without it to stop.')
    args = parser.parse_args()
    try:
        result = start(Path(__file__).resolve().parents[1], acceptance=args.acceptance, seed_demo=args.seed_demo, lan=args.lan)
    except (RuntimeError, OSError):
        print('ProjectFlow startup failed. Check Docker, configured loopback ports and local environment permissions.')
        return 1
    print(f"ProjectFlow ready: {result['project']} at {result['web_url']}")
    if result['lan']:
        port = urllib.parse.urlsplit(result['web_url']).port
        print(f"Network access: http://{lan_address() or '<this-computer-ip>'}:{port} "
              f"(allow inbound TCP {port} in Windows Firewall; restart without --lan to stop)")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
