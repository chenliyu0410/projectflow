"""Run MVP acceptance in its isolated Compose project, preserving database volumes."""

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.parse import urlsplit

from start import compose_prefix, start


def valid_acceptance(result: dict[str, str], root: Path) -> bool:
    try:
        url = urlsplit(result['web_url'])
        return (result['project'] == 'projectflow-acceptance'
                and Path(result['env_file']).resolve() == root / '.superpowers/p1c/acceptance.env'
                and url.scheme == 'http' and url.hostname == '127.0.0.1'
                and url.port is not None and 0 < url.port <= 65535 and url.port != 15173
                and not url.path and not url.query and not url.fragment
                and url.username is None and url.password is None)
    except (KeyError, ValueError, TypeError, OSError):
        return False


def verify(root: Path, *, keep_running: bool = False) -> int:
    root = root.resolve()
    npm = shutil.which('npm.cmd' if os.name == 'nt' else 'npm')
    if npm is None:
        print('Acceptance requires the locked host dependencies and npm. See the development guide.', flush=True)
        return 1
    started = False
    exit_code = 1
    try:
        print('Acceptance: start isolated Compose stack', flush=True)
        result = start(root, acceptance=True, seed_demo=True)
        if not valid_acceptance(result, root):
            raise RuntimeError('Invalid acceptance target')
        started = True
        environment = {**os.environ, 'PF_BASE_URL': result['web_url']}
        stages = [
            ('API', [sys.executable, '-m', 'pytest', '-c', str(root / 'api/pyproject.toml'), str(root / 'api/tests'), '-q']),
            ('Vitest', [npm, '--prefix', str(root / 'web'), 'test']),
            ('build', [npm, '--prefix', str(root / 'web'), 'run', 'build']),
            ('E2E', [npm, '--prefix', str(root / 'web'), 'run', 'e2e']),
        ]
        exit_code = 0
        for name, command in stages:
            print(f'Acceptance: {name}', flush=True)
            completed = subprocess.run(command, cwd=root, env=environment, check=False, timeout=1800)
            if completed.returncode:
                exit_code = completed.returncode if completed.returncode > 0 else 1
                print(f'Acceptance: {name} failed (exit {exit_code}).', flush=True)
                break
    except (RuntimeError, OSError, subprocess.TimeoutExpired):
        print('Acceptance orchestration failed. Check Docker, host dependencies and local configuration.', flush=True)
        exit_code = 1
    finally:
        if started and not keep_running:
            print('Acceptance: stop isolated services; retain database volume', flush=True)
            command = compose_prefix(root, 'projectflow-acceptance', root / '.superpowers/p1c/acceptance.env') + ['down']
            try:
                cleanup = subprocess.run(command, cwd=root, check=False, capture_output=True,
                                         text=True, encoding='utf-8', errors='replace', timeout=600)
                if cleanup.returncode:
                    print('Acceptance cleanup failed. Inspect the isolated Compose project.', flush=True)
                    if exit_code == 0:
                        exit_code = 1
            except (OSError, subprocess.TimeoutExpired):
                print('Acceptance cleanup failed. Inspect the isolated Compose project.', flush=True)
                if exit_code == 0:
                    exit_code = 1
    print(f'Acceptance finished (exit {exit_code}).', flush=True)
    return exit_code


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--keep-running', action='store_true', help='Leave isolated services running after acceptance.')
    args = parser.parse_args()
    return verify(Path(__file__).resolve().parents[1], keep_running=args.keep_running)


if __name__ == '__main__':
    raise SystemExit(main())
