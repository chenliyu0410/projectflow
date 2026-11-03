"""End-to-end check of the N8N demo stack: assignment mail, daily digest and weekly report all arrive in Mailpit via n8n.

Run after `python deploy/n8n/setup.py --seed-demo`; uses the same env file. Exit 0 only when every mail arrived.
"""
import argparse
import http.cookiejar
import io
import json
import os
import sys
import time
import zipfile
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


def xlsx(rows):
    """Minimal one-sheet workbook with inline strings (no extra packages needed)."""
    def cell(ref, value):
        return f'<c r="{ref}" t="inlineStr"><is><t>{value}</t></is></c>'
    sheet = ''.join(f'<row r="{n}">' + ''.join(cell(f'{chr(65 + i)}{n}', v) for i, v in enumerate(row)) + '</row>' for n, row in enumerate(rows, 1))
    ns = 'http://schemas.openxmlformats.org'
    parts = {
        '[Content_Types].xml': f'<Types xmlns="{ns}/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>',
        '_rels/.rels': f'<Relationships xmlns="{ns}/package/2006/relationships"><Relationship Id="rId1" Type="{ns}/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        'xl/workbook.xml': f'<workbook xmlns="{ns}/spreadsheetml/2006/main" xmlns:r="{ns}/officeDocument/2006/relationships"><sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets></workbook>',
        'xl/_rels/workbook.xml.rels': f'<Relationships xmlns="{ns}/package/2006/relationships"><Relationship Id="rId1" Type="{ns}/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>',
        'xl/worksheets/sheet1.xml': f'<worksheet xmlns="{ns}/spreadsheetml/2006/main"><sheetData>{sheet}</sheetData></worksheet>',
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        for name, body in parts.items():
            archive.writestr(name, body)
    return buffer.getvalue()


def drop(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    old = time.time() - 60
    os.utime(path, (old, old))


def host_folder(env, key, default):
    value = env.get(key) or default
    path = Path(value)
    return path if path.is_absolute() else ROOT / 'deploy' / value


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
    if queued:
        results['daily_digest'] = bool(wait_mail(mailpit, '今日任務摘要', 150))
    else:
        print("   (每人每天只寄一封：今天已寄過，略過這一步)")

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

    inbox = host_folder(env, 'PF_INBOX_HOST', './inbox')
    stamp = time.strftime('%H%M%S')
    drop(inbox / args.org / project['title'] / f'verify-{stamp}.txt', f'n8n 收件匣驗證 {stamp}：殺菌溫度 121 度。'.encode('utf-8'))
    print(f"4. dropped a file into the 「{project['title']}」 inbox folder; waiting for n8n…", flush=True)
    results['inbox_document'] = bool(wait_mail(mailpit, '收件匣新文件', 150))

    code = f'N8N-{stamp}'
    expires = time.strftime('%Y-%m-%d', time.gmtime(time.time() + 8 * 3600 + 10 * 86400))
    drop(inbox / args.org / '_營運資料匯入' / '供應商.xlsx', xlsx([['代碼', '名稱', '證書到期日'], [code, f'驗證供應商 {stamp}', expires]]))
    print('5. dropped 供應商.xlsx into the import folder; waiting for n8n…', flush=True)
    results['excel_import'] = bool(wait_mail(mailpit, '營運資料匯入完成', 150))

    records = web.call('GET', f'/operations?category=partners&q={code}')
    record = next((r for r in records.get('items', []) if r['code'] == code), None)
    if record:
        web.call('POST', f"/nodes/{task['id']}/operation-links", {'record_id': record['id']})
    expiry = api.call('POST', '/integrations/maintenance/expiry', {}, bearer)
    print(f"6. expiry check: {expiry}", flush=True)
    results['expiry'] = bool(record) and expiry['tasks'] >= 1 and bool(wait_mail(mailpit, '即將到期', 150))

    backup = api.call('POST', '/integrations/maintenance/backup', {}, bearer)
    folder = host_folder(env, 'PF_BACKUP_HOST', './backups')
    print(f"7. backup {backup['file']} ({backup['bytes']} bytes) in {folder}", flush=True)
    results['backup'] = (folder / backup['file']).is_file() and bool(wait_mail(mailpit, '每日備份完成', 150))

    for name, ok in results.items():
        print(f"{'PASS' if ok else 'FAIL'} {name}")
    return 0 if all(results.values()) else 1


if __name__ == '__main__':
    sys.exit(main())
