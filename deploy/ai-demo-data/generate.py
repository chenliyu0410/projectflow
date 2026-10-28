"""Generate the small fictional AI demo pack ("原有展示資料", dataset-v1) used by Text-to-SQL and document Q&A.

    python deploy/ai-demo-data/generate.py --out <new folder>

Deterministic: the same code always writes byte-identical files. Every company follows the same storyline so each
of the 16 fixed analyses (api/app/ai/queries.json) has a clear point, e.g. one overspent project, one supplier
with overdue orders, one project with a high defect rate. The expected answer of every analysis is computed here
in plain Python, independently of the SQL, and written to evaluation/expected.json for verify.py.
"""
import argparse
import collections
import datetime
import decimal
import hashlib
import json
import random
import sqlite3
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCHEMA = HERE.parents[1] / 'api' / 'tests' / 'fixtures' / 'ai_schema.sql'
QUERIES = HERE.parents[1] / 'api' / 'app' / 'ai' / 'queries.json'
AS_OF = datetime.date(2026, 10, 11)
WEEK = (datetime.date(2026, 10, 5), datetime.date(2026, 10, 11))  # q13 has this week hard-coded
ALL_ROLES = ['admin', 'member', 'project_owner', 'readonly', 'reviewer']  # every product role (app/ai/starter.py ROLES)
MANAGERS = ['admin', 'project_owner']
# Delivery spec and quality wording per industry: (screenshot subject, attached record, screenshot must show, quality action).
WORDING = {
    'food': ('產品', '檢驗表', '正面、背面、標籤與包裝', '加嚴進料檢驗'),
    'hemu': ('產品', '檢驗報告', '瓶身、標籤、成分表與外盒', '加嚴原料檢驗'),
    'electronics': ('產品', '測試報告', '正面、背面、銘牌與包裝', '加嚴零件進料檢驗'),
    'events': ('現場', '驗收單', '入口、主舞台、動線與餐檯', '活動前加做彩排檢查'),
    'software': ('系統畫面', '測試紀錄', '登入、主要功能、報表與錯誤訊息', '上線前加做回歸測試'),
    'construction': ('施工', '自主檢查表', '施工前、施工中、完工與安全設施', '加嚴材料進場檢驗'),
}

COMPANIES = {
    'food': dict(name='毛研食品', business='寵物食品研發與製造', departments=['研發', '品保', '採購', '行銷'],
                 projects=['成貓主食罐口味擴充', '犬用凍乾零食', '低敏配方試作', '電商禮盒組'],
                 suppliers=['青禾原料行', '海鮮冷鏈', '鐵罐包材', '印刷標籤'], item='原料'),
    'hemu': dict(name='禾沐寵物營養股份有限公司', business='寵物保健品', departments=['研發', '法規', '生產', '業務'],
                 projects=['關節保健粉', '益生菌滴劑', '魚油膠囊改版', '寵物醫院通路'],
                 suppliers=['膠原原料', '菌種供應', '膠囊代工', '紙盒包材'], item='原料'),
    'electronics': dict(name='峰曜科技', business='消費性電子', departments=['硬體', '韌體', '測試', '採購'],
                        projects=['藍牙耳機新機種', '充電座量產導入', '智慧插座認證', '電源板二供'],
                        suppliers=['被動元件', '機構件', 'PCB 板廠', '包裝材料'], item='零件'),
    'events': dict(name='光點企劃', business='活動企劃', departments=['企劃', '設計', '執行', '業務'],
                   projects=['年終尾牙', '品牌快閃店', '產品發表會', '員工旅遊'],
                   suppliers=['舞台燈光', '印刷輸出', '餐飲外燴', '遊覽車'], item='服務'),
    'software': dict(name='雲序軟體', business='軟體開發', departments=['產品', '開發', '測試', '客服'],
                     projects=['會員系統改版', 'App 推播', '報表模組', '資安稽核'],
                     suppliers=['雲端主機', '外包開發', '測試裝置', '資安顧問'], item='服務'),
    'construction': dict(name='築衡工程', business='營建工程', departments=['工務', '設計', '採購', '安衛'],
                         projects=['辦公室裝修', '廠房屋頂改善', '停車場鋪面', '機電改善'],
                         suppliers=['鋼構材料', '水泥砂石', '機具租賃', '水電包商'], item='材料'),
}
SURNAMES = '陳林黃張李王吳劉蔡楊許鄭謝郭洪曾周賴徐葉'
GIVEN = ['怡君', '冠宇', '雅婷', '家豪', '詩涵', '建宏', '佩珊', '志明', '欣怡', '俊傑', '宜蓁', '承翰', '思妤', '柏宇', '品妍']
PHASES = ['規劃', '執行', '驗證', '結案']
CATEGORIES = ['人力', '材料', '委外', '差旅']
# Per project: P3 concentrates rejected/blocked work (q14).
STATUSES = [
    ['done'] * 9 + ['doing'] * 3 + ['review'] + ['todo'] * 2,
    ['done'] * 8 + ['doing'] * 3 + ['review'] * 2 + ['todo'] * 2,
    ['done'] * 6 + ['doing'] * 2 + ['rejected'] * 3 + ['blocked'] * 2 + ['todo'] * 2,
    ['done'] * 7 + ['doing'] * 3 + ['review'] + ['rejected'] + ['todo'] * 3,
]
TASK_WORK = ['需求確認', '時程排定', '樣品準備', '供應商報價', '試作', '內部測試', '問題修正', '文件整理', '主管審核',
             '客戶確認', '量產準備', '教育訓練', '上線檢查', '成本結算', '結案報告']


def day(value):
    return value.isoformat()


def people(rng, spec):
    names = rng.sample([s + g for s in SURNAMES for g in GIVEN], 10)
    departments = [d for d, n in zip(spec['departments'], (3, 3, 2, 2)) for _ in range(n)]
    return [dict(person_id=f'P{i + 1:02d}', name=names[i], department=departments[i]) for i in range(10)]


def build_company(cid, spec):
    rng = random.Random(f'projectflow-ai-demo-v1-{cid}')
    staff = people(rng, spec)
    focus = [p['person_id'] for p in staff if p['department'] == spec['departments'][2]]  # the department with most overdue work
    data = collections.defaultdict(list)
    data['companies'].append(dict(company_id=cid, name=spec['name'], business=spec['business']))
    data['people'] = [dict(company_id=cid, **p) for p in staff]

    budgets = [round(base * rng.uniform(0.7, 1.4), -4) for base in (1_200_000, 800_000, 1_500_000, 600_000)]
    projects = [dict(company_id=cid, project_id=f'{cid}-PRJ{k + 1}', title=f'{title}（AI 延伸案）', owner_id=staff[k]['person_id'],
                     budget_twd=int(budgets[k])) for k, title in enumerate(spec['projects'])]
    data['projects'] = projects

    # Open work gets a due-date bucket: 8 overdue, 4 due this week (also overdue by q02's rule), the rest later.
    buckets = ['past'] * 8 + ['week'] * 4 + ['future'] * 18
    rng.shuffle(buckets)
    week_days = [datetime.date(2026, 10, d) for d in (6, 7, 8, 10)]
    for k, project in enumerate(projects):
        for j, status in enumerate(STATUSES[k]):
            duration = rng.randint(5, 18)
            estimated = rng.choice([8, 12, 16, 24, 32])
            if status == 'done':
                start = datetime.date(2026, 8, 3) + datetime.timedelta(days=k * 6 + j * 4)
                due = start + datetime.timedelta(days=duration)
                completed = min(max(due + datetime.timedelta(days=rng.choice([-2, -1, 0, 0, 1, 3])), start), AS_OF - datetime.timedelta(days=1))
                actual = max(1, estimated + rng.choice([-4, -2, 0, 0, 2, 6, 10]))
                owner = rng.choice(staff)['person_id']
            else:
                bucket = buckets.pop()
                if bucket == 'past':
                    due = datetime.date(2026, 9, 15) + datetime.timedelta(days=rng.randint(0, 18))
                elif bucket == 'week':
                    due = week_days.pop()
                else:
                    due = datetime.date(2026, 10, 14) + datetime.timedelta(days=rng.randint(0, 45))
                start = due - datetime.timedelta(days=duration)
                completed, actual = None, max(0, estimated - rng.randint(2, 10))
                if status == 'todo':
                    actual = 0  # not started yet; it may also start after the as-of date
                else:
                    start = min(start, AS_OF)  # work in progress has already started
                owner = rng.choice(focus) if bucket != 'future' and rng.random() < 0.7 else rng.choice(staff)['person_id']
            data['tasks'].append(dict(company_id=cid, task_id=f'{project["project_id"]}-T{j + 1:02d}', project_id=project['project_id'],
                owner_id=owner, title=f'{TASK_WORK[j]}', phase=PHASES[min(j // 4, 3)], status=status, start_date=day(start),
                due_date=day(due), completed_date=day(completed) if completed else None, estimated_hours=estimated, actual_hours=actual))

    # Costs: PRJ2 ends 15–25% over budget (q04); the others stay well under.
    for k, project in enumerate(projects):
        ratio = rng.uniform(1.15, 1.25) if k == 1 else rng.uniform(0.45, 0.8)
        total = int(round(project['budget_twd'] * ratio, -3))
        cuts = sorted(rng.sample(range(1, total // 1000), 4))
        parts = [b - a for a, b in zip([0, *cuts], [*cuts, total // 1000])]
        for n, part in enumerate(parts):
            month = 8 + n * 3 // 5  # the five parts fall in Aug, Aug, Sep, Sep, Oct; October stays before the as-of date
            booked = datetime.date(2026, month, rng.randint(1, 10 if month == 10 else 28))
            data['expenses'].append(dict(company_id=cid, expense_id=f'{project["project_id"]}-E{n + 1}', project_id=project['project_id'],
                                         category=CATEGORIES[(k + n) % 4], booked_date=day(booked), amount_twd=part * 1000))

    suppliers = [dict(company_id=cid, supplier_id=f'S{n + 1}', name=name, category=spec['item']) for n, name in enumerate(spec['suppliers'])]
    data['suppliers'] = suppliers
    # S1 on time; S2 has overdue undelivered orders (q05); S3 is usually late (q06); S4 has orders still to come (q15).
    plans = {'S1': ['on_time'] * 5 + ['cancelled'], 'S2': ['overdue'] * 3 + ['on_time'] * 2 + ['cancelled'],
             'S3': ['late'] * 4 + ['on_time'] + ['future'], 'S4': ['future'] * 3 + ['on_time'] * 2 + ['late']}
    n = 0
    for supplier, kinds in plans.items():
        for kind in kinds:
            n += 1
            ordered = datetime.date(2026, 8, 5) + datetime.timedelta(days=rng.randint(0, 50))
            promised = ordered + datetime.timedelta(days=rng.randint(10, 25))
            received, status = None, 'received'
            if kind == 'future':
                promised = AS_OF + datetime.timedelta(days=rng.randint(3, 30)); status = 'pending'
            elif kind == 'overdue':
                promised = AS_OF - datetime.timedelta(days=rng.randint(4, 20)); ordered = promised - datetime.timedelta(days=20); status = 'pending'
            elif kind == 'cancelled':
                status = 'cancelled'
            else:
                promised = min(promised, AS_OF - datetime.timedelta(days=12))
                ordered = min(ordered, promised - datetime.timedelta(days=10))
                received = promised + datetime.timedelta(days=rng.randint(3, 9) if kind == 'late' else -rng.randint(0, 3))
            quantity, price = rng.randint(2, 40) * 10, rng.randint(15, 400) * 10
            data['purchase_orders'].append(dict(company_id=cid, order_id=f'{cid}-PO{n:02d}', project_id=projects[n % 4]['project_id'],
                supplier_id=supplier, item=f'{spec["item"]}批次{n:02d}', quantity=quantity, unit_price_twd=price, amount_twd=quantity * price,
                ordered_date=day(ordered), promised_date=day(promised), received_date=day(received) if received else None, status=status))

    # Quality: PRJ4 has a clearly higher defect rate (q07); at least two clean batches (q16).
    for k, project in enumerate(projects):
        for b in range(3):
            samples = rng.randint(3, 8) * 10
            defects = rng.randint(5, 9) if k == 3 else (0 if (k, b) in ((0, 0), (2, 1)) else rng.randint(0, 2))
            data['quality_checks'].append(dict(company_id=cid, check_id=f'{project["project_id"]}-Q{b + 1}', project_id=project['project_id'],
                checked_date=day(datetime.date(2026, 9, 1) + datetime.timedelta(days=k * 7 + b * 9)), sample_count=samples,
                defect_count=defects, criterion='外觀與規格抽查'))

    risks = [('high', 'open', 1, '成本超出預算', '專案費用已超過核定預算', '凍結非必要支出並提報追加預算'),
             ('high', 'open', 0, f'{spec["suppliers"][1]}交期延遲', '後續驗證時程延後', '每週追蹤交期並啟動替代供應商'),
             ('medium', 'open', 3, '抽查不良率偏高', '可能需要重工', f'{WORDING[cid][3]}並與供應商檢討'),
             ('low', 'closed', 2, '文件版本不一致', '溝通成本增加', '統一由專案負責人發布'),
             ('high', 'closed', 2, '關鍵人力請假', '進度可能延後', '已安排代理人'),
             ('medium', 'open', 2, '需求變更頻繁', '任務退回增加', '變更需經週會核准')]
    for r, (severity, state, k, cause, impact, action) in enumerate(risks):
        data['risks'].append(dict(company_id=cid, risk_id=f'{cid}-R{r + 1}', project_id=projects[k]['project_id'], severity=severity,
            status=state, cause=cause, impact=impact, action=action, owner_id=projects[k]['owner_id'],
            next_review_date=day(AS_OF + datetime.timedelta(days=7 + r))))

    # Notes only on work that has started, so no note predates its task.
    notes = rng.sample([t for t in data['tasks'] if t['start_date'] <= day(AS_OF)], 30)
    for m, task in enumerate(sorted(notes, key=lambda t: t['task_id'])):
        written = min(datetime.date.fromisoformat(task['start_date']) + datetime.timedelta(days=2), AS_OF)
        data['notes'].append(dict(company_id=cid, note_id=f'{cid}-N{m + 1:02d}', task_id=task['task_id'], created_date=day(written),
                                  body=f'{task["title"]}進度更新：目前狀態{task["status"]}，下次週會再確認。'))

    data['documents'] = documents(cid, spec, projects, data)
    return data


def documents(cid, spec, projects, data):
    shots, record, parts, quality = WORDING[cid]
    p1, p2, p3, p4 = (p['project_id'] for p in projects)
    over = summary(data)['q04'][0]  # PRJ2 is the only overspent project
    s2_late = [o for o in data['purchase_orders'] if o['supplier_id'] == 'S2' and o['status'] == 'pending' and o['promised_date'] < day(AS_OF)]
    high = max((q for q in data['quality_checks'] if q['project_id'] == p4), key=lambda q: q['defect_count'])
    rows = [
        ('SPEC-1', p1, '交付規範', 'spec', False, 1, ALL_ROLES, 'internal',
         f'舊版交付規範：{projects[0]["title"]}交付時需附{shots}截圖2張與{record}1份。此版本已於2026-09-20停用。'),
        ('SPEC-2', p1, '交付規範', 'spec', True, 2, ALL_ROLES, 'internal',
         f'現行交付規範（第2版，2026-09-20起適用）：{projects[0]["title"]}交付時需附{shots}截圖4張與{record}1份，截圖需含{parts}。'),
        ('MEET-1', p1, '專案週會紀錄', 'meeting', True, 1, ALL_ROLES, 'internal',
         f'2026-10-07週會：{projects[0]["title"]}樣品準備完成，客戶確認排在下週。決議依現行交付規範準備截圖。'),
        ('MEET-2', p2, '專案週會紀錄', 'meeting', True, 1, ALL_ROLES, 'internal',
         f'2026-10-08週會：{projects[1]["title"]}費用偏高，請專案負責人提出追加預算或刪減項目。'),
        ('MEET-3', p3, '專案週會紀錄', 'meeting', True, 1, ALL_ROLES, 'internal',
         f'2026-10-09週會：{projects[2]["title"]}有多項任務被退回或受阻，主因是需求變更，之後變更需經週會核准。'),
        ('RISK-1', p2, '風險處理紀錄', 'risk', True, 1, ALL_ROLES, 'internal',
         f'風險：成本超出預算。原因：{projects[1]["title"]}追加了委外與材料費用。處理方式：凍結非必要支出並提報追加預算，每週檢視。'),
        ('RISK-2', p1, '風險處理紀錄', 'risk', True, 1, ALL_ROLES, 'internal',
         f'風險：{spec["suppliers"][1]}交期延遲。原因：供應商產能不足。處理方式：每週追蹤交期，並啟動替代供應商詢價。'),
        ('PO-1', None, '採購追蹤紀錄', 'purchase', True, 1, ALL_ROLES, 'internal',
         f'採購追蹤：{spec["suppliers"][1]}有{len(s2_late)}張訂單已過承諾交期仍未交貨（' + '、'.join(o['order_id'] for o in s2_late) + '），已發函催貨。'),
        ('PO-2', None, '採購追蹤紀錄', 'purchase', True, 1, ALL_ROLES, 'internal',
         f'採購追蹤：{spec["suppliers"][2]}近期多次晚於承諾日交貨，下季評選將列入考量。'),
        ('COST-1', p2, '成本報告', 'cost', True, 1, MANAGERS, 'confidential',
         f'機密：{projects[1]["title"]}預算{over["budget_twd"]:,}元，實際{over["actual_twd"]:,}元，超支{over["overrun_twd"]:,}元。'),
        ('COST-2', p1, '成本報告', 'cost', True, 1, MANAGERS, 'confidential',
         f'機密：{projects[0]["title"]}目前在預算內，預算{projects[0]["budget_twd"]:,}元。'),
        ('QC-1', p4, '品質抽查報告', 'quality', True, 1, ALL_ROLES, 'internal',
         f'品質抽查：{projects[3]["title"]}批次{high["check_id"]}抽查{high["sample_count"]}件，不良{high["defect_count"]}件，已要求{quality}。'),
        ('GUIDE-1', None, '專案管理通則', 'guide', True, 1, ALL_ROLES, 'internal',
         f'{spec["name"]}專案管理通則：任務逾期需在週會說明原因；需求變更需經週會核准；成本報告僅限管理者與專案負責人查閱。'),
    ]
    return [dict(document_id=f'{cid}-{key}', company_id=cid, project_id=project, title=title, document_type=kind, is_current=current,
                 version=version, allowed_roles=roles, classification=level, text=text)
            for key, project, title, kind, current, version, roles, level, text in rows]


def summary(data):
    """Expected answer of every analysis, computed without SQL (verify.py compares it with the real queries)."""
    as_of = day(AS_OF)
    tasks, staff = data['tasks'], {p['person_id']: p for p in data['people']}
    orders, checks = data['purchase_orders'], data['quality_checks']
    # SQLite ROUND() rounds halves away from zero (5/160 → 3.13); Python round() would give 3.12.
    pct = lambda a, b: float((decimal.Decimal(100 * a) / decimal.Decimal(b)).quantize(decimal.Decimal('0.01'), decimal.ROUND_HALF_UP))
    count = collections.Counter
    by_project = lambda rows: sorted({r['project_id'] for r in rows})
    result = {}
    result['q01'] = [dict(status=s, count=n) for s, n in sorted(count(t['status'] for t in tasks).items())]
    overdue = count(staff[t['owner_id']]['department'] for t in tasks if t['due_date'] < as_of and t['status'] != 'done')
    result['q02'] = [dict(department=d, overdue_count=n) for d, n in sorted(overdue.items(), key=lambda x: (-x[1], x[0]))]
    result['q03'] = [dict(project_id=p, total=len(rows), done_count=sum(t['status'] == 'done' for t in rows),
                          completion_pct=pct(sum(t['status'] == 'done' for t in rows), len(rows)))
                     for p in by_project(tasks) for rows in [[t for t in tasks if t['project_id'] == p]]]
    spent = collections.defaultdict(int)
    for e in data['expenses']:
        spent[e['project_id']] += e['amount_twd']
    result['q04'] = sorted([dict(project_id=p['project_id'], budget_twd=p['budget_twd'], actual_twd=spent[p['project_id']],
                                 overrun_twd=spent[p['project_id']] - p['budget_twd'])
                            for p in data['projects'] if spent[p['project_id']] > p['budget_twd']], key=lambda r: (-r['overrun_twd'], r['project_id']))
    late = [o for o in orders if o['status'] == 'pending' and o['promised_date'] < as_of]
    result['q05'] = sorted([dict(supplier_id=s, overdue_count=sum(o['supplier_id'] == s for o in late),
                                 amount_twd=sum(o['amount_twd'] for o in late if o['supplier_id'] == s))
                            for s in sorted({o['supplier_id'] for o in late})], key=lambda r: (-r['overdue_count'], r['supplier_id']))
    received = [o for o in orders if o['status'] == 'received']
    result['q06'] = [dict(supplier_id=s, received_count=len(rows), late_count=sum(o['received_date'] > o['promised_date'] for o in rows),
                          late_pct=pct(sum(o['received_date'] > o['promised_date'] for o in rows), len(rows)))
                     for s in sorted({o['supplier_id'] for o in received}) for rows in [[o for o in received if o['supplier_id'] == s]]]
    result['q07'] = sorted([dict(project_id=p, samples=sum(q['sample_count'] for q in rows), defects=sum(q['defect_count'] for q in rows),
                                 defect_pct=pct(sum(q['defect_count'] for q in rows), sum(q['sample_count'] for q in rows)))
                            for p in by_project(checks) for rows in [[q for q in checks if q['project_id'] == p]]],
                           key=lambda r: (-r['defect_pct'], r['project_id']))
    months = collections.defaultdict(int)
    for e in data['expenses']:
        months[(e['booked_date'][:7], e['category'])] += e['amount_twd']
    result['q08'] = [dict(month=m, category=c, amount_twd=a) for (m, c), a in sorted(months.items())]
    result['q09'] = [dict(risk_id=r['risk_id'], project_id=r['project_id'], cause=r['cause'], action=r['action'])
                     for r in sorted(data['risks'], key=lambda r: r['risk_id']) if r['severity'] == 'high' and r['status'] == 'open']
    open_work = count(t['owner_id'] for t in tasks if t['status'] != 'done')
    result['q10'] = [dict(person_id=p, name=staff[p]['name'], open_tasks=n) for p, n in sorted(open_work.items(), key=lambda x: (-x[1], x[0]))[:5]]
    result['q11'] = sorted([dict(task_id=t['task_id'], estimated_hours=t['estimated_hours'], actual_hours=t['actual_hours'],
                                 extra_hours=t['actual_hours'] - t['estimated_hours'])
                            for t in tasks if t['status'] == 'done' and t['actual_hours'] > t['estimated_hours']],
                           key=lambda r: (-r['extra_hours'], r['task_id']))
    result['q12'] = [dict(project_id=p, committed_twd=sum(o['amount_twd'] for o in orders if o['project_id'] == p and o['status'] != 'cancelled'))
                     for p in sorted({o['project_id'] for o in orders if o['status'] != 'cancelled'})]
    result['q13'] = sorted([dict(task_id=t['task_id'], due_date=t['due_date'], status=t['status']) for t in tasks
                            if day(WEEK[0]) <= t['due_date'] <= day(WEEK[1]) and t['status'] != 'done'], key=lambda r: (r['due_date'], r['task_id']))
    result['q14'] = [dict(project_id=p, rejected_count=sum(t['status'] == 'rejected' for t in rows), blocked_count=sum(t['status'] == 'blocked' for t in rows))
                     for p in by_project(tasks) for rows in [[t for t in tasks if t['project_id'] == p]]]
    result['q15'] = sorted([dict(order_id=o['order_id'], promised_date=o['promised_date'], amount_twd=o['amount_twd'])
                            for o in orders if o['status'] == 'pending' and o['promised_date'] >= as_of], key=lambda r: (r['promised_date'], r['order_id']))
    result['q16'] = [dict(zero_defect_batches=sum(q['defect_count'] == 0 for q in checks))]
    return result


def write(out):
    catalog = json.loads(QUERIES.read_text(encoding='utf-8'))
    out.mkdir(parents=True)
    (out / 'rag').mkdir()
    (out / 'evaluation').mkdir()
    db = sqlite3.connect(out / 'projectflow_demo.sqlite')
    db.executescript(SCHEMA.read_text(encoding='utf-8'))
    docs, expected, counts = [], {}, collections.Counter()
    tables = ('companies', 'people', 'projects', 'tasks', 'suppliers', 'purchase_orders', 'expenses', 'quality_checks', 'risks', 'notes')
    for cid in sorted(COMPANIES):  # the first company's SQL lines must equal the catalog, in order
        data = build_company(cid, COMPANIES[cid])
        for table in tables:
            for row in data[table]:
                db.execute(f'INSERT INTO {table} ({",".join(row)}) VALUES ({",".join("?" * len(row))})', list(row.values()))
            counts[table] += len(data[table])
        docs += data['documents']
        expected[cid] = summary(data)
    db.commit()
    db.execute('VACUUM')
    db.close()
    counts['documents'] = len(docs)
    # newline='\n': the same bytes on every operating system, so verify.py can compare a regeneration anywhere.
    (out / 'rag' / 'documents.jsonl').write_text(''.join(json.dumps(d, ensure_ascii=False, sort_keys=True) + '\n' for d in docs),
                                                 encoding='utf-8', newline='\n')
    (out / 'evaluation' / 'sql_questions.jsonl').write_text(''.join(
        json.dumps(dict(company_id=cid, query_id=q['query_id'], question=q['label'], sql=q['sql']), ensure_ascii=False) + '\n'
        for cid in sorted(COMPANIES) for q in catalog), encoding='utf-8', newline='\n')
    (out / 'evaluation' / 'expected.json').write_text(json.dumps(expected, ensure_ascii=False, indent=1, sort_keys=True),
                                                      encoding='utf-8', newline='\n')
    files = {p.relative_to(out).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.rglob('*')) if p.is_file()}
    manifest = dict(dataset='dataset-v1', generator='deploy/ai-demo-data/generate.py', as_of=day(AS_OF), synthetic=True,
                    counts=dict(counts=dict(sorted(counts.items()))), files=files)
    (out / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True), encoding='utf-8', newline='\n')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error(f'{args.out} 已存在；請指定新的資料夾')
    print(json.dumps(write(args.out)['counts'], ensure_ascii=False))


if __name__ == '__main__':
    main()
