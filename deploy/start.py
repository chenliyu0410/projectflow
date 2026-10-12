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


def compose_prefix(root: Path, project: str, env_file: Path) -> list[str]:
    return ['docker', 'compose', '--project-name', project, '--env-file', str(env_file),
            '-f', str(root / 'deploy/docker-compose.yml')]


def run(args: list[str], *, acceptance: bool = False, lan: bool = False) -> str:
    try:
        environment = {**os.environ, 'PF_ACCEPTANCE_MODE': str(acceptance).lower(),
                       'WEB_BIND': '0.0.0.0' if lan else '127.0.0.1'}
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


def start(root: Path, *, acceptance: bool = False, seed_demo: bool = False, lan: bool = False) -> dict:
    if lan and acceptance:
        raise RuntimeError('The acceptance stack must stay on loopback.')
    root = root.resolve()
    project = 'projectflow-acceptance' if acceptance else 'projectflow-formal'
    env_file = root / ('.superpowers/p1c/acceptance.env' if acceptance else 'deploy/.env')
    initialize_env(env_file, 15175 if acceptance else 15173, 18002 if acceptance else 18000, acceptance)
    prefix = compose_prefix(root, project, env_file)
    run(prefix + ['config', '--quiet'], acceptance=acceptance, lan=lan)
    run(prefix + ['up', '-d', '--build', '--wait'], acceptance=acceptance, lan=lan)
    run(prefix + ['exec', '-T', 'api', 'python', '-m', 'alembic', 'upgrade', 'head'], acceptance=acceptance, lan=lan)
    if seed_demo:
        run(prefix + ['exec', '-T', 'api', 'python', '-m', 'app.seed'], acceptance=acceptance, lan=lan)
    address = run(prefix + ['port', 'web', '80'], acceptance=acceptance, lan=lan)
    try:
        parsed = urllib.parse.urlsplit('http://' + address)
        valid = (parsed.hostname == ('0.0.0.0' if lan else '127.0.0.1') and parsed.port is not None
                 and 0 < parsed.port <= 65535 and not parsed.path and not parsed.query
                 and not parsed.fragment and parsed.username is None and parsed.password is None)
    except ValueError:
        valid = False
    if not valid:
        raise RuntimeError('The trial web port must be a valid loopback address.')
    url = f'http://127.0.0.1:{parsed.port}'
    check_readiness(url, acceptance=acceptance)
    return {'project': project, 'web_url': url, 'env_file': str(env_file), 'lan': lan}


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
