"""Start an isolated N8N demo stack (own Compose project, database and env file) and load the n8n workflows.

Default target: project `projectflow-n8n`, env file `output/n8n-demo/.env` (outside git), web 15183, API 18010,
Mailpit 8025, n8n 5678. The everyday `projectflow-formal` stack and its data are not touched.
"""
import argparse
import secrets
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = {'notify': 'pfNotify0000001', 'daily-digest': 'pfDailyDigest01', 'weekly-draft': 'pfWeeklyDraft01',
             'inbox': 'pfInbox00000001', 'maintenance': 'pfMaintenance01'}


def env_values(path):
    values = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        if '=' in line and not line.lstrip().startswith('#'):
            key, value = line.split('=', 1)
            values[key.strip()] = value.strip()
    return values


def ensure_env(path):
    if path.exists():
        return env_values(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    values = {'POSTGRES_PASSWORD': secrets.token_urlsafe(24), 'PF_N8N_TOKEN': secrets.token_urlsafe(32),
              'WEB_PORT': '15183', 'API_PORT': '18010', 'MAILPIT_PORT': '8025', 'N8N_PORT': '5678',
              'PF_PUBLIC_URL': 'http://127.0.0.1:15183', 'PF_AI_OCR': 'false',
              'PF_INBOX_HOST': str(path.parent / 'inbox'), 'PF_BACKUP_HOST': str(path.parent / 'backups')}
    path.write_text(''.join(f'{k}={v}\n' for k, v in values.items()), encoding='utf-8')
    return values


def compose(project, env_file, *args, check=True):
    command = ['docker', 'compose', '--project-name', project, '--env-file', str(env_file),
               '-f', str(ROOT / 'deploy/docker-compose.yml'), '--profile', 'n8n', *args]
    print('>', ' '.join(command[6:]) if len(command) > 6 else ' '.join(command), flush=True)
    return subprocess.run(command, check=check, text=True, encoding='utf-8', errors='replace')


def wait_for(url, seconds=120):
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5):
                return
        except OSError:
            time.sleep(2)
    raise SystemExit(f'not ready: {url}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', default='projectflow-n8n')
    parser.add_argument('--env-file', type=Path, default=ROOT / 'output/n8n-demo/.env')
    parser.add_argument('--seed-demo', action='store_true', help='seed demo accounts (use only on a new, empty database)')
    args = parser.parse_args()
    values = ensure_env(args.env_file)
    for key, default in (('PF_INBOX_HOST', 'inbox'), ('PF_BACKUP_HOST', 'backups')):
        if key not in values and args.env_file.resolve() != (ROOT / 'deploy/.env').resolve():
            # Isolated stacks keep their folders beside their env file instead of sharing deploy/inbox.
            values[key] = str(args.env_file.parent / default)
            with args.env_file.open('a', encoding='utf-8') as handle:
                handle.write(f'{key}={values[key]}\n')
        folder = Path(values.get(key, ''))
        folder = folder if folder.is_absolute() else ROOT / 'deploy' / default
        folder.mkdir(parents=True, exist_ok=True)
    if len(values.get('PF_N8N_TOKEN', '')) < 24:
        raise SystemExit('PF_N8N_TOKEN must be at least 24 characters')
    compose(args.project, args.env_file, 'up', '-d', '--build', '--wait')
    compose(args.project, args.env_file, 'exec', '-T', 'api', 'python', '-m', 'alembic', 'upgrade', 'head')
    if args.seed_demo:
        compose(args.project, args.env_file, 'exec', '-T', 'api', 'python', '-m', 'app.seed')
    # Databases created before this feature have no emails; only empty ones are filled.
    compose(args.project, args.env_file, 'exec', '-T', 'api', 'python', '-m', 'app.integrations_cli', 'demo-emails')
    wait_for(f"http://127.0.0.1:{values.get('N8N_PORT', '5678')}/healthz")
    compose(args.project, args.env_file, 'exec', '-T', 'n8n', 'n8n', 'import:credentials',
            '--input=/opt/projectflow-n8n/credentials/mailpit-smtp.json')
    for name in WORKFLOWS:
        compose(args.project, args.env_file, 'exec', '-T', 'n8n', 'n8n', 'import:workflow', f'--input=/opt/projectflow-n8n/workflows/{name}.json')
    for workflow_id in WORKFLOWS.values():
        compose(args.project, args.env_file, 'exec', '-T', 'n8n', 'n8n', 'publish:workflow', f'--id={workflow_id}')
    # Schedules are registered at start-up, so n8n restarts once after the workflows are published.
    compose(args.project, args.env_file, 'restart', 'n8n')
    wait_for(f"http://127.0.0.1:{values.get('N8N_PORT', '5678')}/healthz")
    print(f"ready: web http://127.0.0.1:{values.get('WEB_PORT', '15173')}  mailpit http://127.0.0.1:{values.get('MAILPIT_PORT', '8025')}  "
          f"n8n http://127.0.0.1:{values.get('N8N_PORT', '5678')}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
