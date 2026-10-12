"""Export the running database to the de-identified pack in deploy/demo-data, or restore that pack into an empty database.

  python deploy/demo_data.py export            # local trial stack (projectflow-formal) -> deploy/demo-data
  python deploy/demo_data.py import            # deploy/demo-data -> empty, migrated local trial stack

Use --project-name/--env-file for another Compose project. Sessions, audit logs, notifications and password hashes
are never exported; restored accounts sign in with demo-<username>. Import refuses a database that already has data.
"""
import argparse
import base64
import io
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / 'deploy' / 'demo-data'
SCRIPT = (ROOT / 'api' / 'app' / 'demo_pack.py').read_bytes()


def compose(args, project, env_file, **kwargs):
    command = ['docker', 'compose', '--project-name', project, '--env-file', str(env_file), '-f', str(ROOT / 'deploy' / 'docker-compose.yml'), *args]
    result = subprocess.run(command, capture_output=True, **kwargs)
    if result.returncode:
        raise SystemExit('Compose 指令失敗：' + result.stderr.decode('utf-8', 'replace').strip()[-400:])
    return result.stdout


def export(project, env_file, pack=PACK):
    # The pack module is piped in, so it also works with a container built before the module existed.
    data = base64.b64decode(compose(['exec', '-T', 'api', 'python', '-', 'export'], project, env_file, input=SCRIPT))
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        manifest = json.loads(archive.read('manifest.json'))
        with tempfile.TemporaryDirectory() as scratch:
            archive.extractall(scratch)
            for name in ['tables', 'files']:
                shutil.rmtree(pack / name, ignore_errors=True)
            pack.mkdir(parents=True, exist_ok=True)
            for item in Path(scratch).iterdir():
                shutil.move(str(item), pack / item.name)
    rows = sum(info['rows'] for info in manifest['tables'].values())
    print(json.dumps({'pack': str(pack), 'alembic_revision': manifest['alembic_revision'], 'rows': rows,
        'files': len(manifest['files']), 'excluded_tables': manifest['excluded_tables']}, ensure_ascii=False))


def restore(project, env_file, pack=PACK):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(pack.rglob('*')):
            if path.is_file() and path.name != 'README.md':
                archive.write(path, path.relative_to(pack).as_posix())
    with tempfile.TemporaryDirectory() as scratch:
        local = Path(scratch) / 'demo-pack.zip'
        local.write_bytes(buffer.getvalue())
        compose(['cp', str(local), 'api:/tmp/demo-pack.zip'], project, env_file)
    try:
        print(compose(['exec', '-T', 'api', 'python', '-', 'import', '/tmp/demo-pack.zip'], project, env_file, input=SCRIPT).decode('utf-8'))
    finally:
        compose(['exec', '-T', '-u', 'root', 'api', 'rm', '-f', '/tmp/demo-pack.zip'], project, env_file)  # cp leaves it root-owned


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('action', choices=['export', 'import'])
    parser.add_argument('--project-name', default='projectflow-formal')
    parser.add_argument('--env-file', default=str(ROOT / 'deploy' / '.env'))
    parser.add_argument('--pack', default=str(PACK), help='pack directory (default deploy/demo-data)')
    args = parser.parse_args()
    (export if args.action == 'export' else restore)(args.project_name, Path(args.env_file), Path(args.pack).resolve())
    return 0


if __name__ == '__main__':
    sys.exit(main())
