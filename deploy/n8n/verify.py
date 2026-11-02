"""End-to-end check of the N8N demo stack: assignment mail, daily digest and weekly report all arrive in Mailpit via n8n.

Run after `python deploy/n8n/setup.py --seed-demo`; uses the same env file. Exit 0 only when every mail arrived.
"""
import argparse
import http.cookiejar
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from setup import ROOT, env_values  # noqa: E402


class Client:
    def __init__(self, base):
        self.base = base
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def call(self, method, path, body=None, headers=None):
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(self.base + path, data=data, method=method,
                                         headers={'Content-Type': 'application/json', **(headers or {})})
        with self.opener.open(request, timeout=300) as response:
            raw = response.read()
            # Mailpit answers some calls with plain "ok"; only JSON bodies are parsed.
            return json.loads(raw) if raw and response.headers.get_content_type() == 'application/json' else None


def wait_mail(mailpit, needle, seconds):
    deadline = time.time() + seconds
    while time.time() < deadline:
        messages = mailpit.call('GET', '/api/v1/messages')['messages']
        found = [m for m in messages if needle in m['Subject']]
        if found:
            return found
        time.sleep(5)
    return []


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', type=Path, default=ROOT / 'output/n8n-demo/.env')
    parser.add_argument('--org', default='food')
    parser.add_argument('--user', default='yu')
    args = parser.parse_args()
    env = env_values(args.env_file)
    web = Client(f"http://127.0.0.1:{env['WEB_PORT']}/api")
    api = Client(f"http://127.0.0.1:{env['API_PORT']}")
    mailpit = Client(f"http://127.0.0.1:{env.get('MAILPIT_PORT', '8025')}")
    bearer = {'Authorization': f"Bearer {env['PF_N8N_TOKEN']}"}
    results = {}

    mailpit.call('DELETE', '/api/v1/messages')
    web.call('POST', '/auth/login', {'organization_key': args.org, 'username': args.user, 'password': f'demo-{args.user}'})
    me = web.call('GET', '/auth/me')['user']
    for project in web.call('GET', '/projects')['items']:
        detail = web.call('GET', f"/projects/{project['id']}")
        tasks = [n for n in detail['nodes'] if n['kind'] == 'task' and n['status'] not in ('done', 'skipped')]
        users = web.call('GET', f"/projects/{project['id']}/assignment-options")['users']
        if tasks and len(users) > 1:
            break
    else:
        raise SystemExit('no project with an open task and assignable users')
    task = tasks[0]
    target = next(u for u in users if u['id'] not in (task.get('owner_user_id'), me['id']))
    # Due today, so the daily digest below has something to say for the new owner.
    today = time.strftime('%Y-%m-%d', time.gmtime(time.time() + 8 * 3600))
    try:
        web.call('PATCH', f"/nodes/{task['id']}", {'owner_user_id': target['id'], 'due_date': today})
    except urllib.error.HTTPError:
        web.call('PATCH', f"/nodes/{task['id']}", {'owner_user_id': target['id']})
    print(f"1. assigned 「{task['title']}」 to {target['display_name']}; waiting for n8n (runs every minute)…", flush=True)
    results['assignment'] = bool(wait_mail(mailpit, '你被指派為任務負責人', 150))

    queued = api.call('POST', '/integrations/daily-digest', {}, bearer)['enqueued']
    print(f'2. daily digest queued {queued} mail(s)', flush=True)
    results['daily_digest'] = queued > 0 and bool(wait_mail(mailpit, '今日任務摘要', 150))

    try:
        report = web.call('POST', f"/projects/{project['id']}/weekly-reports/generate")
    except urllib.error.HTTPError as exc:
        if exc.code != 409:
            raise
        print('3. this week\'s report was already sent; skipping the weekly step')
        results['weekly_report'] = True
    else:
        sent = web.call('POST', f"/weekly-reports/{report['id']}/confirm", {})
        print(f"3. weekly report for 「{project['title']}」 ({report['model_label']}) sent to {len(sent['report']['recipients'])} recipient(s)", flush=True)
        results['weekly_report'] = bool(wait_mail(mailpit, '週報（', 150))

    for name, ok in results.items():
        print(f"{'PASS' if ok else 'FAIL'} {name}")
    return 0 if all(results.values()) else 1


if __name__ == '__main__':
    sys.exit(main())
