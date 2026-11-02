"""Per-person daily digest (no AI): my tasks finished yesterday, due today, overdue or blocked; empty digests are skipped."""
from datetime import timedelta
from types import SimpleNamespace

from sqlalchemy import select

from app.models import Node, Organization, TaskReport, User, now_utc
from app.services.outbox_service import deliverable, enqueue
from app.services.weekly_report_service import CLOSED, local_day

TITLES = {'done_yesterday': '昨天完成', 'due_today': '今天到期', 'overdue': '已逾期', 'blocked': '卡住（前置條件未滿足）'}


def enqueue_all(db, now=None):
    from app.services.notification_service import states
    now = now or now_utc()
    today = local_day(now)
    yesterday = today - timedelta(days=1)
    queued = 0
    for organization in db.scalars(select(Organization)):
        users = [u for u in db.scalars(select(User).where(User.organization_id == organization.id)) if deliverable(u)]
        if not users:
            continue
        tasks = list(db.scalars(select(Node).where(Node.organization_id == organization.id, Node.kind == 'task',
                                                   Node.owner_user_id.in_([u.id for u in users]))))
        finished = set(db.scalars(select(TaskReport.node_id).where(TaskReport.organization_id == organization.id, TaskReport.status == 'approved',
                                                                   TaskReport.finished_on == yesterday, TaskReport.node_id.in_([n.id for n in tasks]))))
        blocked = {}
        for project_id in {n.project_id for n in tasks}:
            blocked.update(states(db, SimpleNamespace(organization=organization), project_id))
        for user in users:
            # Owners always see their own tasks, so no further visibility filter is needed here.
            mine = [n for n in tasks if n.owner_user_id == user.id]
            open_tasks = [n for n in mine if n.status not in CLOSED]
            groups = {
                'done_yesterday': [n for n in mine if n.id in finished],
                'due_today': [n for n in open_tasks if n.due_date == today],
                'overdue': [n for n in open_tasks if n.due_date and n.due_date < today],
                'blocked': [n for n in open_tasks if blocked.get(n.id, (False,))[0]],
            }
            if not any(groups.values()):
                continue
            lines = [f'{user.display_name} 你好，以下是 {today.isoformat()} 的任務摘要。']
            for key, rows in groups.items():
                if rows:
                    lines += ['', f'{TITLES[key]}（{len(rows)}）'] + [f'・{n.title}' + (f'（到期 {n.due_date.isoformat()}）' if n.due_date else '') for n in rows]
            if enqueue(db, organization.id, 'daily_digest', user.id, f'[專流] 今日任務摘要 {today.isoformat()}', '\n'.join(lines),
                       f'daily:{user.id}:{today.isoformat()}'):
                queued += 1
    return queued
