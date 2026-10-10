"""Run MVP acceptance in its isolated Compose project, preserving database volumes."""

import argparse
import json
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


# Executed only inside the acceptance API container; DSN never crosses its boundary.
POSTGRES_RUNNER = r"""
import json, os, pathlib, re, subprocess, sys, tempfile, urllib.request, uuid
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from app.database import sqlalchemy_url
try:
    assert os.environ.get('PF_ACCEPTANCE_MODE') == 'true'
    with urllib.request.urlopen('http://127.0.0.1:8000/health/acceptance', timeout=5) as r:
        assert r.status == 200 and json.load(r) == {'acceptance': True}
    sources = json.load(sys.stdin)
    original = make_url(sqlalchemy_url(os.environ['DATABASE_URL']))
    assert original.get_backend_name() == 'postgresql' and original.database == 'projectflow'
    with tempfile.TemporaryDirectory(prefix='p2b-verify-') as directory:
        root = pathlib.Path(directory)
        (root / 'api').symlink_to('/app', target_is_directory=True)
        (root / 'files').mkdir()
        for filename, source in sources.items():
            assert filename in {'test_migrations.py', 'test_collaboration_postgresql.py'}
            (root / filename).write_text(source, encoding='utf-8')
        (root / 'no_skip.py').write_text('def pytest_sessionfinish(session, exitstatus):\n    if session.testscollected == 0 or session.config.pluginmanager.get_plugin("terminalreporter").stats.get("skipped"):\n        session.exitstatus = 1\n', encoding='utf-8')
        environment = {**os.environ, 'PF_ACCEPTANCE_MODE': 'true',
                       'PF_ATTACHMENT_ROOT': str(root / 'files'),
                       'PYTHONPATH': str(root) + ':/app'}
        environment.pop('P2A_MIGRATION_TEST_URL', None)
        stages = [('P2b migration', 'test_migrations.py::test_p2b_postgresql_migration_constraints_and_parallel_pending'),
                  ('P2c migration', 'test_migrations.py::test_p2c_postgresql_migration_and_dependency_constraints'),
                  ('TP-A migration', 'test_migrations.py::test_tp_a_postgresql_migration_preserves_nodes'),
                  ('TP-B migration', 'test_migrations.py::test_tp_b_postgresql_migration_preserves_nodes'),
                  ('API races', 'test_collaboration_postgresql.py')]
        for label, target in stages:
            # Each migration starts on a new database, never an already-upgraded stack.
            name = 'p2b_test_' + uuid.uuid4().hex
            assert re.fullmatch(r'p2b_test_[0-9a-f]{32}', name)
            engine = create_engine(original, isolation_level='AUTOCOMMIT')
            with engine.connect() as db:
                db.execute(text('CREATE DATABASE "' + name + '"'))
            engine.dispose()
            url = original.set(database=name).render_as_string(hide_password=False)
            environment.update(DATABASE_URL=url, P2B_TEST_DATABASE_URL=url)
            result = subprocess.run([sys.executable, '-m', 'pytest', target, '-q', '-p', 'no_skip'],
                                    cwd=root, env=environment, capture_output=True, text=True, timeout=600)
            output = result.stdout + result.stderr
            for secret in [url, str(original.password or '')]:
                if secret: output = output.replace(secret, '[redacted]')
            print('PostgreSQL ' + name + ' ' + label, flush=True)
            print(output, flush=True)
            if result.returncode: raise SystemExit(result.returncode if result.returncode > 0 else 1)
except SystemExit:
    raise
except Exception:
    print('Dedicated PostgreSQL acceptance failed; preserve database and inspect isolated setup.', flush=True)
    raise SystemExit(1)
"""


def postgresql_acceptance(root: Path, result: dict[str, str], environment: dict[str, str]) -> int:
    if not valid_acceptance(result, root):
        return 1
    sources = {name: (root / 'api/tests' / name).read_text(encoding='utf-8')
               for name in ('test_migrations.py', 'test_collaboration_postgresql.py')}
    command = compose_prefix(root, 'projectflow-acceptance', root / '.superpowers/p1c/acceptance.env')
    completed = subprocess.run(command + ['exec', '-T', 'api', 'python', '-c', POSTGRES_RUNNER],
                               cwd=root, env=environment, input=json.dumps(sources), text=True,
                               encoding='utf-8', check=False, timeout=1800)
    return completed.returncode if completed.returncode >= 0 else 1


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
        for name in ('DATABASE_URL', 'P2B_TEST_DATABASE_URL', 'P2A_MIGRATION_TEST_URL', 'PF_ATTACHMENT_ROOT'):
            environment.pop(name, None)
        print('Acceptance: dedicated PostgreSQL migration and API races', flush=True)
        exit_code = postgresql_acceptance(root, result, environment)
        stages = [
            ('API', [sys.executable, '-m', 'pytest', '-c', str(root / 'api/pyproject.toml'), str(root / 'api/tests'), '-q']),
            ('Vitest', [npm, '--prefix', str(root / 'web'), 'test']),
            ('build', [npm, '--prefix', str(root / 'web'), 'run', 'build']),
            ('E2E', [npm, '--prefix', str(root / 'web'), 'run', 'e2e']),
        ]
        for name, command in stages:
            if exit_code:
                break
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
