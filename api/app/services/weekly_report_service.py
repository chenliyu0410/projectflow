"""Project weekly report: facts are computed here, the local model only rewrites them as prose (spec §4, D84, D85)."""
import json
import re
import unicodedata
from datetime import datetime, time, timedelta, timezone
from types import SimpleNamespace

from fastapi import HTTPException
from sqlalchemy import select

from app.ai import model, policy, store
from app.audit import log_audit
from app.auth import CurrentUser
from app.models import Node, NodeCollaborator, TaskNote, TaskReport, User, WeeklyReport, now_utc
from app.permissions import can_view_node
from app.services.outbox_service import enqueue
from app.services.record_policy import load_policy_context

TAIPEI = timezone(timedelta(hours=8))
MANAGER_ROLES = {'admin', 'project_owner', 'reviewer', 'readonly'}
CLOSED = {'done', 'skipped'}
SECTIONS = {'summary': '整體摘要', 'highlights': '本週重點', 'risks': '風險與卡關', 'next': '下週重點'}
SCHEMA = {'type': 'object', 'required': list(SECTIONS), 'properties': {
    'summary': {'type': 'string'}, 'highlights': {'type': 'array', 'items': {'type': 'string'}},
    'risks': {'type': 'array', 'items': {'type': 'string'}}, 'next': {'type': 'array', 'items': {'type': 'string'}}}}
SYSTEM = ('你是專案週報助理。只根據使用者提供的 JSON 資料，用繁體中文寫週報。'
          '提到任務時必須用資料中的代號，例如 [T1]，不可提到資料裡沒有的任務，不可自行計算或改動數字。'
          'summary 為一段話；highlights、risks、next 各為 0 到 5 句。')
REF = re.compile(r'\[(T\d+)\]')
NUMBER = re.compile(r'[0-9]{1,3}(?:,[0-9]{3})+(?:\.[0-9]+)?|[0-9]+(?:\.[0-9]+)?')


def numbers(text):
    """Arabic numbers in text, normalized (full-width digits, thousands commas, leading or trailing zeros); [T1] refs are ignored."""
    found = set()
    for raw in NUMBER.findall(REF.sub(' ', unicodedata.normalize('NFKC', text))):
        whole, _, frac = raw.replace(',', '').partition('.')
        frac = frac.rstrip('0')
        found.add((whole.lstrip('0') or '0') + (f'.{frac}' if frac else ''))
    return found


def local_day(now):
    return now.astimezone(TAIPEI).date()


def week_start(day):
    return day - timedelta(days=day.weekday())


def as_user(user, organization):
    return CurrentUser(user=user, organization=organization, token='')


def recipients(db, organization, project):
    """D84: the project owner plus involved users whose role sees every task; members get the daily digest instead."""
    users = {u.id: u for u in db.scalars(select(User).where(User.organization_id == organization.id))}
    owners = set(db.scalars(select(Node.owner_user_id).where(Node.organization_id == organization.id, Node.project_id == project.id)))
    helpers = set(db.scalars(select(NodeCollaborator.user_id).join(Node, (Node.organization_id == NodeCollaborator.organization_id) & (Node.id == NodeCollaborator.node_id))
                             .where(NodeCollaborator.organization_id == organization.id, Node.project_id == project.id)))
    involved = sorted(i for i in owners | helpers if i in users and users[i].role in MANAGER_ROLES)
    picked = dict.fromkeys([project.owner_user_id, *involved])
    return [users[i] for i in picked if i in users and users[i].status == 'active']


def explicit_confidential(organization_key, project_id, nodes):
    """D85: only explicit confidential overrides count; the company-wide default level does not."""
    try:
        overrides = policy.load(organization_key)['overrides']
    except ValueError:
        overrides = {}
    else:
        # policy.load falls back to an empty override list when the file is damaged; for mail that would
        # silently publish tasks someone marked confidential, so stop instead.
        path = policy.path(organization_key)
        try:
            if path.exists():
                json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            raise HTTPException(503, '資料分級設定無法讀取，暫停產生與寄出週報') from None
    if overrides.get(f'project:{project_id}') == 'confidential':
        return set(nodes)
    hidden = set()
    for node_id in nodes:
        cursor, seen = node_id, set()
        while cursor in nodes and cursor not in seen:
            seen.add(cursor)
            if overrides.get(f'node:{cursor}') == 'confidential':
                hidden.add(node_id)
                break
            cursor = nodes[cursor].parent_id
    return hidden


def visible_to_all(db, organization, users, node_ids, nodes):
    for user in users:
        current = as_user(user, organization)
        context = load_policy_context(db, current)
        node_ids = [i for i in node_ids if can_view_node(current, nodes[i], context=context)]
    return node_ids


def collect_facts(db, organization, project, users, now):
    from app.services.notification_service import states
    today = local_day(now)
    start = week_start(today)
    since = datetime.combine(start, time(), TAIPEI)
    nodes = {n.id: n for n in db.scalars(select(Node).where(Node.organization_id == organization.id, Node.project_id == project.id))}
    tasks = sorted((n for n in nodes.values() if n.kind == 'task'), key=lambda n: (n.sort_order, n.id))
    hidden = explicit_confidential(organization.key, project.id, nodes)
    shown = visible_to_all(db, organization, users, [n.id for n in tasks if n.id not in hidden], nodes)
    tasks = [n for n in tasks if n.id in set(shown)]
    excluded = sum(1 for n in nodes.values() if n.kind == 'task') - len(tasks)
    names = {u.id: u.display_name for u in db.scalars(select(User).where(User.organization_id == organization.id))}
    refs = {n.id: f'T{i}' for i, n in enumerate(tasks, 1)}
    ids = list(refs)
    reports = {}
    for r in db.scalars(select(TaskReport).where(TaskReport.organization_id == organization.id, TaskReport.node_id.in_(ids),
                                                 TaskReport.submitted_at >= since).order_by(TaskReport.submitted_at)):
        reports[r.node_id] = r
    noted = set(db.scalars(select(TaskNote.node_id).where(TaskNote.organization_id == organization.id, TaskNote.node_id.in_(ids),
                                                          TaskNote.created_at >= since)))
    blocked = states(db, SimpleNamespace(organization=organization), project.id)

    def item(n, **extra):
        return {'ref': refs[n.id], 'title': n.title, 'owner': names.get(n.owner_user_id, '未指派'),
                'due_date': n.due_date.isoformat() if n.due_date else None, **extra}

    open_tasks = [n for n in tasks if n.status not in CLOSED]
    overdue = [n for n in open_tasks if n.due_date and n.due_date < today]
    doing = [n for n in tasks if n.status == 'doing']
    silent = sorted({names.get(n.owner_user_id, '未指派') for n in doing + overdue
                     if n.owner_user_id and n.id not in reports and n.id not in noted})
    facts = {
        'week_start': start.isoformat(), 'today': today.isoformat(), 'project': project.title,
        'completed': [item(n, result=reports[n.id].result, summary=reports[n.id].summary[:300]) for n in tasks
                      if n.id in reports and reports[n.id].status == 'approved'],
        'pending_review': [item(n) for n in tasks if n.id in reports and reports[n.id].status == 'submitted'],
        'doing': [item(n, progress=n.progress) for n in doing],
        'due_next_week': [item(n) for n in open_tasks if n.due_date and today <= n.due_date <= today + timedelta(days=7)],
        'overdue': [item(n) for n in overdue],
        'blocked': [item(n) for n in open_tasks if blocked.get(n.id, (False,))[0]],
        'silent_members': silent,
        'node_ids': ids,
    }
    facts['counts'] = {key: len(facts[key]) for key in ('completed', 'pending_review', 'doing', 'due_next_week', 'overdue', 'blocked')}
    return facts, excluded


def plain_sections(facts):
    c = facts['counts']
    line = lambda i: f"[{i['ref']}] {i['title']}（{i['owner']}）"
    return {
        'summary': f"本週完成 {c['completed']} 項、待確認 {c['pending_review']} 項、進行中 {c['doing']} 項；逾期 {c['overdue']} 項、卡住 {c['blocked']} 項。",
        'highlights': [line(i) + f"：{i['result']}" for i in facts['completed']][:5],
        'risks': ([line(i) + '：已逾期' for i in facts['overdue']] + [line(i) + '：被前置條件擋住' for i in facts['blocked']])[:5],
        'next': [line(i) + f"：{i['due_date']} 到期" for i in facts['due_next_week']][:5],
    }


def write_sections(organization_key, facts):
    """Local model prose with a per-section fallback to the plain listing; returns (sections, model label)."""
    plain = plain_sections(facts)
    config = model.settings(organization_key) if organization_key in store.COMPANIES else {'enabled': False}
    if config.get('enabled') is not True:
        return plain, 'AI 未啟用'
    known = {i['ref'] for key in ('completed', 'pending_review', 'doing', 'due_next_week', 'overdue', 'blocked') for i in facts[key]}
    data = {k: v for k, v in facts.items() if k != 'node_ids'}
    payload = json.dumps(data, ensure_ascii=False)
    allowed = numbers(payload)
    try:
        value = model.chat(config, SYSTEM, payload, SCHEMA)
    except Exception:
        return plain, f"{config.get('model', '本地模型')}（失敗，改用原始整理）"
    sections = {}
    for key in SECTIONS:
        part = value.get(key)
        ok = isinstance(part, str) if key == 'summary' else isinstance(part, list) and all(isinstance(x, str) for x in part)
        text = json.dumps(part, ensure_ascii=False) if ok else ''
        # A section that cites a task outside the facts, or a number the model computed itself
        # (WEEKLY-AI-m1: progress 30 written as "70% 延遲"), is dropped, not trusted.
        ok = ok and numbers(text) <= allowed
        if ok:
            # Capped to what clean_sections accepts, so an unedited draft can always be confirmed.
            part = part[:2000] if key == 'summary' else [x[:500] for x in part[:20]]
        sections[key] = part if ok and set(REF.findall(text)) <= known else plain[key]
    return sections, config.get('model', '本地模型')


def render(project, report):
    s, f = report.sections, report.facts
    bullets = lambda rows: '\n'.join(f'・{x}' for x in rows) or '・無'
    items = lambda key: '\n'.join(f"・[{i['ref']}] {i['title']}（{i['owner']}）" for i in f[key]) or '・無'
    c = f['counts']
    return '\n'.join([
        f"{project.title} 週報（{f['week_start']} 起）", '', '【AI 建議】以下文字由 AI 依專流資料整理，已由專案負責人確認。', '',
        s['summary'], '', '本週重點', bullets(s['highlights']), '', '風險與卡關', bullets(s['risks']), '', '下週重點', bullets(s['next']), '',
        f"數字：完成 {c['completed']}、待確認 {c['pending_review']}、進行中 {c['doing']}、下週到期 {c['due_next_week']}、逾期 {c['overdue']}、卡住 {c['blocked']}",
        '', '逾期任務', items('overdue'), '', '本週未回報成員', bullets(f['silent_members'])])


def generate(db, organization, project, actor, now=None, via='web'):
    now = now or now_utc()
    start = week_start(local_day(now))
    report = db.scalar(select(WeeklyReport).where(WeeklyReport.organization_id == organization.id, WeeklyReport.project_id == project.id,
                                                  WeeklyReport.week_start == start))
    if report is not None and report.status == 'sent':
        raise HTTPException(409, '本週週報已寄出')
    if report is not None and via == 'n8n':
        return None  # the schedule never overwrites a draft the owner may already have edited
    for old in db.scalars(select(WeeklyReport).where(WeeklyReport.organization_id == organization.id, WeeklyReport.project_id == project.id,
                                                     WeeklyReport.status == 'draft', WeeklyReport.week_start < start)):
        old.status = 'unsent'
    users = recipients(db, organization, project)
    facts, excluded = collect_facts(db, organization, project, users, now)
    sections, label = write_sections(organization.key, facts)
    if report is None:
        report = WeeklyReport(organization_id=organization.id, project_id=project.id, week_start=start)
        db.add(report)
    report.status, report.facts, report.ai_sections, report.sections = 'draft', facts, sections, sections
    report.recipient_ids, report.excluded_count, report.model_label = [u.id for u in users], excluded, label
    report.generated_by, report.generated_at, report.confirmed_by, report.confirmed_at = actor.user.id, now, None, None
    db.flush()
    enqueue(db, organization.id, 'weekly_draft', project.owner_user_id, f'[專流] 週報草稿待確認：{project.title}',
            f"{project.title} 本週（{start.isoformat()} 起）週報草稿已產生，請到專案的「週報」分頁確認後寄出。\n撰寫方式：{label}",
            f'weekly_draft:{report.id}:{now.isoformat()}')
    log_audit(db, actor, 'weekly_report.generate', payload={'project_id': project.id, 'report_id': report.id, 'model': label,
                                                            'excluded_count': excluded, 'via': via})
    if label != 'AI 未啟用':
        log_audit(db, actor, 'ai.weekly_report', payload={'project_id': project.id, 'model': label, 'route': 'local'})
    return report


def clean_sections(value):
    if not isinstance(value, dict) or set(value) != set(SECTIONS):
        raise HTTPException(422, '週報段落格式不正確')
    out = {}
    for key in SECTIONS:
        part = value[key]
        if key == 'summary':
            if not isinstance(part, str) or len(part) > 2000:
                raise HTTPException(422, '整體摘要格式不正確')
            out[key] = part.strip()
        else:
            if not isinstance(part, list) or len(part) > 20 or not all(isinstance(x, str) and len(x) <= 500 for x in part):
                raise HTTPException(422, f'{SECTIONS[key]}格式不正確')
            out[key] = [x.strip() for x in part if x.strip()]
    return out


def confirm(db, current, project, report, sections=None):
    if report.status != 'draft':
        raise HTTPException(409, '只有草稿可以確認寄出')
    if sections is not None:
        report.sections = clean_sections(sections)
    organization = current.organization
    users = {u.id: u for u in db.scalars(select(User).where(User.organization_id == organization.id, User.id.in_(report.recipient_ids)))}
    nodes = {n.id: n for n in db.scalars(select(Node).where(Node.organization_id == organization.id, Node.id.in_(report.facts['node_ids'])))}
    project_nodes = {n.id: n for n in db.scalars(select(Node).where(Node.organization_id == organization.id, Node.project_id == project.id))}
    if explicit_confidential(organization.key, project.id, project_nodes) & set(nodes):
        raise HTTPException(409, '有任務在草稿產生後被標為機密，請重新產生草稿')
    kept, removed = [], []
    for user_id in report.recipient_ids:
        user = users.get(user_id)
        # Tasks deleted since the draft are ignored; only tasks that still exist must stay visible.
        ok = user is not None and user.status == 'active' and \
            len(visible_to_all(db, organization, [user], list(nodes), nodes)) == len(nodes)
        (kept if ok else removed).append(user)
    text = render(project, report)
    for index, user in enumerate(kept):
        # One LINE broadcast per report, carried by the first recipient's mail; the content itself stays in mail.
        line = f"[專流] {project.title} 週報已寄出（{report.facts['week_start']} 起），請查看信箱" if index == 0 else None
        enqueue(db, organization.id, 'weekly_report', user.id, f"[專流] {project.title} 週報（{report.facts['week_start']} 起）",
                text, f'weekly_report:{report.id}:{user.id}', line=line)
    report.status, report.confirmed_by, report.confirmed_at = 'sent', current.user.id, now_utc()
    edited = [k for k in SECTIONS if report.sections.get(k) != report.ai_sections.get(k)]
    log_audit(db, current, 'weekly_report.confirm', payload={'project_id': project.id, 'report_id': report.id,
                                                            'recipients': len(kept), 'removed': len(removed), 'edited': edited})
    return [u.display_name if u else '已刪除帳號' for u in removed]
