"""TEXT2SQL-LEARNING：使用者確認過的問法，經管理者審核＋自動檢查後直接答對（驗收情境 1、3–8、確認流程、C1–C5）。"""
import json
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai import fallback, learning, model, service, store
from app.database import sqlalchemy_url
from app.models import AIAnswer, AILearnedPhrase, AuditLog, Organization, User
from test_migrations import ALEMBIC_INI, seed_at_revision

PACK = Path(__file__).resolve().parents[2] / 'deploy' / 'ai-demo-data' / 'pack'
OTHERS = ['峰曜科技', '光點企劃', '雲序軟體', '築衡工程', '禾沐寵物營養股份有限公司']
QUESTION = '哪些供應商常常遲交？'
PHRASE = '哪些供應商常常遲交'


@pytest.fixture()
def demo(tmp_path, monkeypatch):
    monkeypatch.setenv('PF_AI_ROOT', str(tmp_path / 'ai'))
    store.import_pack(PACK, store.root())


def login(client, who='yu', org='food'):
    client.post('/auth/logout')
    assert client.post('/auth/login', json={'organization_key': org, 'username': who, 'password': 'demo-' + who}).status_code == 200


def ask(client, question=QUESTION, **extra):
    response = client.post('/ai/ask', json={'question': question, 'mode': 'sql', **extra})
    assert response.status_code == 200, response.text
    return response.json()


def confirm(client, answer, query_id='q06', question=QUESTION):
    return client.post('/ai/learning/confirm', json={'answer_id': answer['answer_id'], 'query_id': query_id, 'question': question})


def candidates(client):
    return client.get('/ai/learning').json()['items']


def act(client, item_id, action):
    return client.post(f'/ai/learning/{item_id}/{action}')


def add_candidate(engine, phrase, query_id, status='pending'):
    # 直接寫入候選列，模擬「規則改變前就存進來」的候選，用來驗證審核時每一項檢查都會重跑
    with Session(engine) as db:
        org_id = db.scalar(select(Organization.id).where(Organization.key == 'food'))
        user_id = db.scalar(select(User.id).where(User.organization_id == org_id, User.username == 'owner'))
        now = datetime.now(timezone.utc)
        row = AILearnedPhrase(organization_id=org_id, phrase=phrase, query_id=query_id, status=status, confirmed_by=[user_id],
                              first_confirmed_at=now, last_confirmed_at=now)
        db.add(row)
        db.commit()
        return row.id


def test_confirmed_phrase_is_answered_directly_after_review(client, engine, demo):
    # 驗收情境 2：學習前給建議 → 使用者確認 → 管理者審核＋測試 → 同一句直接答對
    login(client)
    before = ask(client)
    assert before['kind'] == 'fallback' and before['fallback']['reason'] == 'topic' and before['analysis'] is None
    offered = {s['query_id']: s for s in before['suggestions']}
    assert {'q06', 'q05'} <= set(offered) and offered['q06']['learnable'] is True
    with Session(engine) as db:
        assert db.get(AIAnswer, before['answer_id']).suggested_ids == [s['query_id'] for s in before['suggestions']]
    clicked = ask(client, offered['q06']['label'], query_id='q06')
    assert clicked['kind'] == 'sql' and clicked['analysis']['query_id'] == 'q06' and clicked['learned'] is False

    saved = confirm(client, before)
    assert saved.status_code == 200, saved.text
    body = saved.json()
    assert (body['phrase'], body['query_id'], body['label'], body['status'], body['confirmations']) == (PHRASE, 'q06', '供應商已收貨延遲率', 'pending', 1)
    assert ask(client)['kind'] == 'fallback'

    listing = client.get('/ai/learning').json()
    assert listing['pending'] == 1
    [item] = listing['items']
    assert (item['id'], item['phrase'], item['label'], item['status'], item['confirmations'], item['checks']) == (body['id'], PHRASE, '供應商已收貨延遲率', 'pending', 1, None)

    reviewed = act(client, item['id'], 'approve')
    assert reviewed.status_code == 200, reviewed.text
    reviewed = reviewed.json()
    assert reviewed['status'] == 'approved' and reviewed['checks']['passed'] is True
    assert [(c['code'], c['ok']) for c in reviewed['checks']['items']] == [(f'C{i}', True) for i in range(1, 6)]
    assert all(c['title'] and c['message'] for c in reviewed['checks']['items'])
    assert client.get('/ai/learning').json()['pending'] == 0

    for wording in (QUESTION, '請問哪些供應商常常遲交', '哪些供應商常常遲交。'):
        after = ask(client, wording)
        assert after['kind'] == 'sql' and after['analysis']['query_id'] == 'q06' and after['learned'] is True
        assert after['gateway']['route'] == 'none'
    # 只認正規化後整句相同，不做相似句
    assert ask(client, '哪些供應商常常遲交貨？')['kind'] == 'fallback'
    login(client, 'owner')
    assert ask(client)['learned'] is True


def test_disabled_phrase_goes_back_to_suggestions_and_can_be_approved_again(client, demo):
    # 驗收情境 6
    login(client)
    assert confirm(client, ask(client)).status_code == 200
    [item] = candidates(client)
    assert act(client, item['id'], 'disable').status_code == 409
    assert act(client, item['id'], 'approve').json()['status'] == 'approved'
    assert act(client, item['id'], 'approve').status_code == 409
    disabled = act(client, item['id'], 'disable')
    assert disabled.status_code == 200 and disabled.json()['status'] == 'disabled'
    assert ask(client)['kind'] == 'fallback'
    assert act(client, item['id'], 'reject').status_code == 409
    again = act(client, item['id'], 'approve').json()
    assert again['status'] == 'approved' and again['checks']['passed'] is True
    assert ask(client)['learned'] is True


def test_roles_and_companies_are_enforced(client, engine, demo):
    # 驗收情境 1
    login(client, 'ming')
    assert client.post('/ai/learning/confirm', json={'answer_id': 'x', 'query_id': 'q06', 'question': QUESTION}).status_code == 403
    assert client.get('/ai/learning').status_code == 403
    login(client, 'owner')
    answer = ask(client)
    assert confirm(client, answer).status_code == 200
    assert client.get('/ai/learning').status_code == 403
    login(client)
    [item] = candidates(client)
    login(client, 'owner')
    for action in ('approve', 'reject', 'disable'):
        assert act(client, item['id'], action).status_code == 403
    login(client)
    assert act(client, item['id'], 'approve').json()['status'] == 'approved'

    login(client, 'elaine', 'electronics')
    assert client.get('/ai/learning').json() == {'items': [], 'pending': 0}
    for action in ('approve', 'reject', 'disable'):
        assert act(client, item['id'], action).status_code == 404
    assert confirm(client, answer).status_code == 404
    other = ask(client)
    assert other['kind'] == 'fallback' and other['analysis'] is None
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(AILearnedPhrase)) == 1
        assert db.scalar(select(AILearnedPhrase.status)) == 'approved'


@pytest.mark.parametrize('question', ['上週逾期任務', '刪除逾期任務'])
def test_condition_and_command_like_questions_offer_no_confirm_and_are_refused(client, engine, demo, question):
    # 驗收情境 3：結果沒有套用「上週」，學起來就是錯的；像指令的句子也不學
    login(client)
    answer = ask(client, question)
    assert answer['kind'] == 'fallback' and answer['suggestions']
    assert all(s['learnable'] is False for s in answer['suggestions'])
    for s in answer['suggestions']:
        assert confirm(client, answer, s['query_id'], question).status_code == 422
    with Session(engine) as db:
        assert db.scalars(select(AILearnedPhrase)).all() == []


def test_help_replies_and_too_long_questions_are_not_learnable(client, engine, demo):
    login(client)
    help_reply = ask(client, '你可以查什麼？')
    assert help_reply['kind'] == 'help' and all(s['learnable'] is False for s in help_reply['suggestions'])
    assert confirm(client, help_reply, help_reply['suggestions'][0]['query_id'], '你可以查什麼？').status_code == 422
    long_question = '我想知道' * 15 + PHRASE
    long_reply = ask(client, long_question)
    assert long_reply['kind'] == 'fallback' and 'q06' in [s['query_id'] for s in long_reply['suggestions']]
    assert all(s['learnable'] is False for s in long_reply['suggestions'])
    assert confirm(client, long_reply, 'q06', long_question).status_code == 422
    with Session(engine) as db:
        assert db.scalars(select(AILearnedPhrase)).all() == []


def test_confirm_checks_the_answer_and_recomputes_the_suggestions(client, engine, demo):
    # 驗收情境 4
    login(client)
    answer = ask(client)
    offered = [s['query_id'] for s in answer['suggestions']]
    assert confirm(client, answer, next(q for q in ('q16', 'q15', 'q01') if q not in offered)).status_code == 422
    assert confirm(client, answer, 'q06', '各專案不良率怎麼樣').status_code == 422
    assert client.post('/ai/learning/confirm', json={'answer_id': str(uuid.uuid4()), 'query_id': 'q06', 'question': QUESTION}).status_code == 404
    assert confirm(client, ask(client, '供應商已收貨延遲率')).status_code == 422
    with Session(engine) as db:
        assert db.scalars(select(AILearnedPhrase)).all() == []

    assert confirm(client, answer).json()['confirmations'] == 1
    assert confirm(client, ask(client)).json()['confirmations'] == 1
    login(client, 'owner')
    assert confirm(client, answer).status_code == 404
    assert confirm(client, ask(client)).json()['confirmations'] == 2
    with Session(engine) as db:
        row = db.scalars(select(AILearnedPhrase)).one()
        assert len(row.confirmed_by) == len(set(row.confirmed_by)) == 2


def test_model_only_suggestion_is_not_learnable(client, demo, monkeypatch):
    # 決定 10：確認時只用規則重算，模型補上、規則算不出的建議學不起來
    model.save('food', dict(enabled=True, base_url='http://127.0.0.1:11434', model='test'))
    monkeypatch.setattr(model, 'chat', lambda *args, **kwargs: {'query_id': 'q16'})
    login(client)
    answer = ask(client)
    flags = {s['query_id']: s['learnable'] for s in answer['suggestions']}
    assert answer['suggestions'][0]['query_id'] == 'q16' and flags['q16'] is False and flags['q06'] is True
    assert confirm(client, answer, 'q16').status_code == 422
    assert confirm(client, answer, 'q06').status_code == 200


def test_rejected_phrase_stays_rejected(client, demo):
    login(client)
    assert confirm(client, ask(client)).status_code == 200
    [item] = candidates(client)
    assert act(client, item['id'], 'reject').json()['status'] == 'rejected'
    login(client, 'owner')
    again = confirm(client, ask(client))
    assert again.status_code == 200 and (again.json()['status'], again.json()['confirmations']) == ('rejected', 1)
    login(client)
    assert act(client, item['id'], 'approve').status_code == 409
    assert ask(client)['kind'] == 'fallback'


@pytest.mark.parametrize('phrase,query_id,code,reason', [
    ('上個月各部門逾期任務有幾件', 'q02', 'C1', 'condition'),
    ('請刪除逾期任務', 'q02', 'C2', 'command'),
    ('刪除逾期任務', 'q02', 'C2', 'command'),
    ('你可以查什麼', 'q02', 'C2', 'capabilities'),
    ('各部門逾期任務數', 'q05', 'C3', 'builtin'),
    ('哪幾家廠商最常晚交貨', 'q06', 'C4', 'bank_changed'),
])
def test_each_failed_check_keeps_the_phrase_pending(client, engine, demo, phrase, query_id, code, reason):
    # 驗收情境 5（C1–C4）
    item_id = add_candidate(engine, phrase, query_id)
    login(client)
    reviewed = act(client, item_id, 'approve')
    assert reviewed.status_code == 200, reviewed.text
    reviewed = reviewed.json()
    assert reviewed['status'] == 'pending' and reviewed['checks']['passed'] is False
    failed = {c['code']: c for c in reviewed['checks']['items'] if not c['ok']}
    assert set(failed) == {code} and failed[code]['reason'] == reason and failed[code]['message']
    assert ask(client, phrase).get('learned') is not True
    [item] = candidates(client)
    assert item['checks'] == reviewed['checks'] and item['status'] == 'pending'


def test_conflict_with_another_live_phrase_fails_c3(client, engine, demo):
    add_candidate(engine, PHRASE, 'q05', status='approved')
    item_id = add_candidate(engine, PHRASE, 'q06')
    login(client)
    reviewed = act(client, item_id, 'approve').json()
    failed = {c['code']: c['reason'] for c in reviewed['checks']['items'] if not c['ok']}
    assert reviewed['status'] == 'pending' and failed == {'C3': 'learned'}
    assert ask(client)['analysis']['query_id'] == 'q05'


def test_query_over_the_execution_limit_fails_c5(client, engine, demo, monkeypatch):
    item_id = add_candidate(engine, PHRASE, 'q06')
    monkeypatch.setattr(store, 'PROGRESS_INTERVAL', 1)
    monkeypatch.setattr(store, 'PROGRESS_BUDGET', 1)
    login(client)
    reviewed = act(client, item_id, 'approve').json()
    failed = {c['code']: c['reason'] for c in reviewed['checks']['items'] if not c['ok']}
    assert reviewed['status'] == 'pending' and failed == {'C5': 'too_large'}


def test_bank_question_check_reports_which_questions_changed(client, engine, demo):
    item_id = add_candidate(engine, '哪幾家廠商最常晚交貨', 'q06')
    login(client)
    [c4] = [c for c in act(client, item_id, 'approve').json()['checks']['items'] if c['code'] == 'C4']
    assert c4['detail'] == ['A04']


def test_check_bank_matches_current_behaviour(demo):
    bank = learning.bank()
    assert len(bank) == 57 and len({q['id'] for q in bank}) == 57
    with closing(store.connect('food')) as db:
        names = fallback.vocabulary(db)
        for item in bank:
            result = service.ask(db, 'food', 'admin', item['question'], 'sql', other_companies=OTHERS)
            expected = (item['kind'], item['query_id'])
            assert (result['kind'], (result['analysis'] or {}).get('query_id')) == expected, item['id']
            assert learning.outcome(item['question'], {}, OTHERS, names) == expected, item['id']


def test_question_text_stays_only_in_the_candidates_table(client, engine, demo):
    # 驗收情境 7
    login(client)
    assert confirm(client, ask(client)).status_code == 200
    [item] = candidates(client)
    act(client, item['id'], 'approve')
    ask(client)
    act(client, item['id'], 'disable')
    other = add_candidate(engine, '各部門延誤的工作有幾件', 'q02')
    act(client, other, 'reject')
    with Session(engine) as db:
        answers = [str([getattr(r, c.name) for c in AIAnswer.__table__.columns]) for r in db.scalars(select(AIAnswer))]
        audits = [(a.action, a.payload) for a in db.scalars(select(AuditLog).where(AuditLog.action.like('ai.%')))]
        stored = db.scalars(select(AILearnedPhrase.phrase)).all()
    assert len(answers) == 2 and sorted(stored) == sorted([PHRASE, '各部門延誤的工作有幾件'])
    for text in answers + [json.dumps(p, ensure_ascii=False) for _, p in audits]:
        assert '供應商' not in text and '遲交' not in text and '延誤' not in text
    learned = {action: payload for action, payload in audits if action.startswith('ai.learning.')}
    assert set(learned) == {'ai.learning.confirm', 'ai.learning.approve', 'ai.learning.disable', 'ai.learning.reject'}
    assert set(learned['ai.learning.confirm']) == {'phrase_id', 'query_id', 'answer_id', 'counted'}
    assert learned['ai.learning.approve'] == {'phrase_id': item['id'], 'query_id': 'q06', 'passed': True, 'failed': []}
    assert learned['ai.learning.disable'] == {'phrase_id': item['id'], 'query_id': 'q06'}
    assert learned['ai.learning.reject'] == {'phrase_id': other, 'query_id': 'q02'}


def check_learning_migration(url, monkeypatch):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import MetaData, create_engine, text
    from sqlalchemy.exc import IntegrityError
    from app.seed import seed_demo_data
    monkeypatch.setenv('DATABASE_URL', url)
    seed_at_revision(url, '20261104_0025', seed_demo_data)
    config = Config(ALEMBIC_INI)
    engine = create_engine(sqlalchemy_url(url))
    with engine.begin() as c:
        org, user = c.execute(text("SELECT organization_id,id FROM users WHERE username='yu'")).one()
        c.execute(text("INSERT INTO ai_answers (id,organization_id,user_id,dataset,mode,kind,followup,source_ids,rating,created_at) "
                       "VALUES ('keep',:org,:user,'dataset-v1','sql','fallback','none','[]','helpful','2026-11-04')"), dict(org=org, user=user))
    meta = MetaData()
    meta.reflect(engine)

    def snapshot():
        with engine.connect() as db:
            return {t.name: sorted([dict(r) for r in db.execute(select(t)).mappings()], key=lambda r: str(r.get('id'))) for t in meta.sorted_tables if t.name != 'alembic_version'}
    before = snapshot()
    command.upgrade(config, 'head')
    assert snapshot() == before
    with engine.connect() as c:
        assert json.loads(c.scalar(text("SELECT CAST(suggested_ids AS TEXT) FROM ai_answers WHERE id='keep'"))) == []
        assert c.scalar(text('SELECT count(*) FROM ai_learned_phrases')) == 0
    command.downgrade(config, '20261104_0025')
    assert snapshot() == before
    command.upgrade(config, 'head')
    insert = text("INSERT INTO ai_learned_phrases (id,organization_id,phrase,query_id,status,confirmed_by,first_confirmed_at,last_confirmed_at) "
                  "VALUES (:id,:org,'哪些供應商常常遲交',:query,:status,'[]','2026-11-05','2026-11-05')")
    with engine.begin() as c:
        c.execute(insert, dict(id='p1', org=org, query='q06', status='pending'))
    for values in (dict(id='p2', org=org, query='q06', status='pending'), dict(id='p3', org=org, query='q99', status='pending'),
                   dict(id='p4', org=org, query='q05', status='live')):
        with pytest.raises(IntegrityError):
            with engine.begin() as c:
                c.execute(insert, values)
    with pytest.raises(RuntimeError, match='拒絕有損降級'):
        command.downgrade(config, '20261104_0025')
    with engine.connect() as c:
        assert c.scalar(text('SELECT count(*) FROM ai_learned_phrases')) == 1
        assert c.scalar(text("SELECT rating FROM ai_answers WHERE id='keep'")) == 'helpful'
    engine.dispose()


def test_learning_migration_preserves_answers_and_refuses_loss(tmp_path, monkeypatch):
    # 驗收情境 8
    check_learning_migration(f"sqlite:///{tmp_path / 'learning.db'}", monkeypatch)


def test_learning_postgresql_migration_preserves_answers_and_refuses_loss(monkeypatch):
    import os
    from sqlalchemy.engine import make_url
    url = os.environ.get('P2B_TEST_DATABASE_URL')
    if not url:
        pytest.skip('Dedicated PostgreSQL required')
    assert make_url(url).database.startswith('p2b_test_') and os.environ.get('PF_ACCEPTANCE_MODE') == 'true'
    check_learning_migration(url, monkeypatch)
