"""TEXT2SQL-LEARNING：使用者確認過的問法，經管理者審核＋自動檢查（C1–C5）後，同一句直接查詢。

只學「問法 → 既有 16 個分析之一」：不新增分析、不讓模型寫 SQL、不學含條件的問句。
問句原文只存在 ai_learned_phrases；ai_answers 與稽核只記 id 和代碼。
"""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.ai import fallback, service, store
from app.audit import log_audit
from app.models import AIAnswer, AILearnedPhrase

MAX_PHRASE = 60
# fallback.suggest 只在「這個分析沒有套用不到的條件」時寫這句。fallback.py 不在這次修改範圍，所以靠它判斷；
# 文字若被改掉，結果是全部不能學（安全的方向），test_ai_learning 會失敗提醒。
NO_CONDITIONS = '不套用問題裡的其他條件'
ORDER = {'pending': 0, 'approved': 1, 'disabled': 2, 'rejected': 3}
HELP_TEXT = '這句是使用說明或和公司資料無關的問題，不能學。'
CHECKS = {
    'C1': ('條件', {
        None: '這個分析能完整回答這句，沒有被略過的條件。',
        'condition': '這句有這個分析套用不到的條件（時間、特定對象、狀態或排序比較），學起來會答錯。',
        'not_suggested': '用規則重算，這句的建議裡沒有這個分析，無法確認是在問它。',
    }),
    'C2': ('危險與說明', {
        None: '不是指令、繞過限制、其他公司、沒有的資料或使用說明。',
        'command': '這句像是要修改資料的指令，不能學。',
        'override': '這句想繞過系統限制，不能學。',
        'other_company': '這句問的是其他公司，不能學。',
        'no_data': '這句問的是系統沒有的資料（例如薪資或個資），不能學。',
        'howto': HELP_TEXT, 'capabilities': HELP_TEXT, 'out_of_scope': HELP_TEXT,
    }),
    'C3': ('衝突', {
        None: '沒有和內建問法或其他已上線問法衝突。',
        'builtin': '這句已經是內建問法，會對到別的分析。',
        'learned': '同一句已經上線為別的分析。',
    }),
    'C4': ('題庫不變', {
        None: '內建檢查題庫每一題的結果都和加入前相同。',
        'bank_changed': '加入後，內建檢查題庫有題目的結果改變了（這句剛好是題庫裡的題目）。',
    }),
    'C5': ('實際執行', {
        None: '用本公司資料實際執行這個分析成功。',
        'too_large': '執行超過上限，這個分析目前無法直接回答。',
        'error': '執行時發生錯誤，請稍後再試。',
    }),
}


def now():
    return datetime.now(timezone.utc)


def bank():
    # 題庫放在 app 套件裡，因為 API 映像檔拿不到 deploy/ 與測試檔
    return json.loads(Path(__file__).with_name('learning_checks.json').read_text(encoding='utf-8'))['questions']


def blocked(phrase, others, names):
    """C2：這句本身就不能學時回原因代碼。"""
    early = fallback.early_reply(phrase, others, names)
    if early:
        return early['fallback']['reason']
    # 學會的問法會直接執行、不再先給建議；「刪除逾期任務」這種指令口吻提問時雖被當成資料問題，仍不學
    return 'command' if fallback.CHANGE.search(phrase) else None


def left_out(phrase, query_id, names):
    """C1：只用規則重算，這個分析在建議裡、而且沒有它套用不到的條件時回 None（決定 9、10）。"""
    # 規則找不到相近分析時，建議會補上固定快捷題；那些不是在回答這句，只認規則真的判定相關的分析
    text = names.sub(' ', phrase) if names else phrase
    if query_id not in fallback.rank(text):
        return 'not_suggested'
    for s in fallback.suggest(phrase, names)['suggestions']:
        if s['query_id'] == query_id:
            return None if s['omits'] == NO_CONDITIONS else 'condition'
    return 'not_suggested'


def refusal(question, query_id, others, names):
    """不能把這句存成這個分析的原因；確認鈕與確認 API 用同一個判斷，按得下去就不會被拒。"""
    phrase = service.normalize(question)
    if not phrase or len(phrase) > MAX_PHRASE:
        return f'問句太長，無法記住（最多 {MAX_PHRASE} 字）。'
    if service.lookup(phrase):
        return '這句已經能直接查詢，不需要記住。'
    if blocked(phrase, others, names):
        return '這類問句不能記住。'
    if left_out(phrase, query_id, names):
        return '這個分析套用不到問句裡的條件，或規則無法確認是在問它，不能記住。'
    return None


def mark(result, question, data, others):
    """每個建議加 learnable，前端照它決定顯示確認鈕，不從 omits 文字推斷。"""
    fallback_reply = result.get('kind') == 'fallback'
    names = fallback.vocabulary(data) if fallback_reply else None
    for s in result.get('suggestions') or []:
        s['learnable'] = fallback_reply and refusal(question, s['query_id'], others, names) is None


def approved(db, organization_id, exclude=None):
    rows = db.execute(select(AILearnedPhrase.id, AILearnedPhrase.phrase, AILearnedPhrase.query_id)
                      .where(AILearnedPhrase.organization_id == organization_id, AILearnedPhrase.status == 'approved'))
    return {phrase: query_id for row_id, phrase, query_id in rows if row_id != exclude}


def outcome(question, learned, others, names):
    """只用規則（不呼叫模型）時的種類與選定分析，C4 用來比對加入前後。"""
    chosen = service.infer(question, learned)
    if chosen:
        return 'sql', chosen
    early = fallback.early_reply(question, others, names)
    return (early['kind'] if early else 'fallback'), None


def run_checks(db, row, data, company, others):
    """C1–C5 只用這家公司的資料與規則，不呼叫模型；全部都跑，讓管理者一次看到所有原因。"""
    names = fallback.vocabulary(data)
    live = approved(db, row.organization_id, exclude=row.id)
    phrase, query_id = row.phrase, row.query_id
    other = service.lookup(phrase)
    after = {**live, phrase: query_id}
    changed = [q['id'] for q in bank() if outcome(q['question'], live, others, names) != outcome(q['question'], after, others, names)]
    try:
        store.execute_query(data, query_id, company)
        ran = None
    except store.QueryTooLarge:
        ran = 'too_large'
    except (sqlite3.Error, ValueError):
        ran = 'error'
    results = [
        ('C1', left_out(phrase, query_id, names), None),
        ('C2', blocked(phrase, others, names), None),
        ('C3', 'builtin' if other and other != query_id else 'learned' if live.get(phrase, query_id) != query_id else None, None),
        ('C4', 'bank_changed' if changed else None, changed),
        ('C5', ran, None),
    ]
    items = [dict(code=code, ok=reason is None, reason=reason, **({'detail': detail} if detail else {})) for code, reason, detail in results]
    return dict(ran_at=now().isoformat(), passed=all(i['ok'] for i in items), items=items)


def describe(checks):
    # 資料庫只存代碼；白話文字在回應時才加上，改文字不必改資料
    if not checks:
        return None
    return dict(checks, items=[dict(c, title=CHECKS[c['code']][0], message=CHECKS[c['code']][1].get(c['reason'], '沒有通過。'))
                               for c in checks['items']])


def item(row, labels=None):
    labels = labels or fallback.labels()
    iso = lambda value: value.isoformat() if value else None
    return dict(id=row.id, phrase=row.phrase, query_id=row.query_id, label=labels[row.query_id], status=row.status,
                confirmations=len(row.confirmed_by or []), first_confirmed_at=iso(row.first_confirmed_at),
                last_confirmed_at=iso(row.last_confirmed_at), reviewed_at=iso(row.reviewed_at), checks=describe(row.checks))


def require_admin(current):
    if current.user.role != 'admin':
        raise HTTPException(403, '只有管理者可以審核問法')


def listing(db, current):
    require_admin(current)
    rows = list(db.scalars(select(AILearnedPhrase).where(AILearnedPhrase.organization_id == current.organization.id)))
    rows.sort(key=lambda r: (ORDER[r.status], -r.last_confirmed_at.timestamp()))
    labels = fallback.labels()
    return dict(items=[item(r, labels) for r in rows], pending=sum(r.status == 'pending' for r in rows))


def find(db, current, phrase_id):
    require_admin(current)
    row = db.get(AILearnedPhrase, phrase_id, with_for_update=True)
    if row is None or row.organization_id != current.organization.id:
        raise HTTPException(404, '找不到這個問法')
    return row


def confirm(db, current, payload, data, others):
    answer = db.get(AIAnswer, payload.answer_id)
    # 只有提問的本人能確認；其他人連這則回答存不存在都看不出來
    if answer is None or answer.organization_id != current.organization.id or answer.user_id != current.user.id:
        raise HTTPException(404, '找不到這則回答')
    if (answer.dataset, answer.mode, answer.kind) != ('dataset-v1', 'sql', 'fallback'):
        raise HTTPException(422, '這則回答不是資料分析的建議回覆')
    if payload.query_id not in (answer.suggested_ids or []):
        raise HTTPException(422, '這個分析不在那次的建議裡')
    # 回答紀錄不存問句，所以用規則重算送來的問句：拿別次的 answer_id 配一句不相干的問句，重算會對不上
    problem = refusal(payload.question, payload.query_id, others, fallback.vocabulary(data))
    if problem:
        raise HTTPException(422, problem)
    phrase, user_id, stamp = service.normalize(payload.question), current.user.id, now()
    row = db.scalar(select(AILearnedPhrase).where(AILearnedPhrase.organization_id == current.organization.id, AILearnedPhrase.phrase == phrase,
                                                  AILearnedPhrase.query_id == payload.query_id).with_for_update())
    counted = row is None or (row.status != 'rejected' and user_id not in row.confirmed_by)
    if row is None:
        row = AILearnedPhrase(organization_id=current.organization.id, phrase=phrase, query_id=payload.query_id, status='pending',
                              confirmed_by=[user_id], first_confirmed_at=stamp, last_confirmed_at=stamp)
        db.add(row)
    elif row.status != 'rejected':
        # 退回的維持不動，避免同一句反覆送審；其他狀態把確認人併進去，同一人重複確認不累加
        if counted:
            row.confirmed_by = [*row.confirmed_by, user_id]
        row.last_confirmed_at = stamp
    try:
        db.flush()
        log_audit(db, current, 'ai.learning.confirm', payload={'phrase_id': row.id, 'query_id': row.query_id, 'answer_id': answer.id, 'counted': counted})
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, '同時有其他人確認這個問法，請再按一次') from None
    return dict(id=row.id, phrase=row.phrase, query_id=row.query_id, label=fallback.labels()[row.query_id], status=row.status,
                confirmations=len(row.confirmed_by))


def finish(db, current, row, action, **extra):
    row.reviewed_by, row.reviewed_at = current.user.id, now()
    log_audit(db, current, action, payload={'phrase_id': row.id, 'query_id': row.query_id, **extra})
    db.commit()
    return item(row)


def approve(db, current, row, data, others):
    if row.status not in ('pending', 'disabled'):
        raise HTTPException(409, '只有待審核或已停用的問法可以審核')
    row.checks = run_checks(db, row, data, current.organization.key, others)
    # 自動檢查沒全過就維持原狀態，不能上線
    if row.checks['passed']:
        row.status = 'approved'
    return finish(db, current, row, 'ai.learning.approve', passed=row.checks['passed'], failed=[c['code'] for c in row.checks['items'] if not c['ok']])


def reject(db, current, row):
    if row.status != 'pending':
        raise HTTPException(409, '只有待審核的問法可以退回')
    row.status = 'rejected'
    return finish(db, current, row, 'ai.learning.reject')


def disable(db, current, row):
    if row.status != 'approved':
        raise HTTPException(409, '只有已上線的問法可以停用')
    row.status = 'disabled'
    return finish(db, current, row, 'ai.learning.disable')
