"""Keep a data question the 16 templates cannot answer useful, without showing anything a template did not compute.

Order: refuse what must never run (commands, overrides, other companies, data we do not hold);
answer usage questions with written help; otherwise name each condition the templates cannot
apply and suggest the nearest analyses, which only run after the user clicks one.
Everything shown here is fixed text, catalog labels or the user's own words. Company names are
read only to recognise a condition and are echoed back only as the user typed them.
"""
import re

from app.ai import store

CONDITION_LABELS = {'time': '時間', 'target': '特定對象', 'status': '狀態', 'ranking': '排序或比較'}

TIME = re.compile(r'上個?月|下個?月|這個月|本月|上[週周]|上禮拜|上星期|下[週周]|下禮拜|下星期|前天|昨天|今天|明天|去年|今年|明年|[上下]半年'
                  r'|第[一二三四1-4]季|Q[1-4]|最近|過去|近\s*\d+\s*天|\d{4}\s*年|\d{1,2}\s*月份?|\d{1,2}/\d{1,2}', re.I)
# "還沒完成的" is the templates' own filter, so only a positive state counts.
STATUS = re.compile(r'(?<![沒未])(?:已經|已)(?:完成|做完|結案|取消|關閉|收貨|到貨)|(?<![沒未])(?:完成|做完|結案)的')
# "比較多" is an adverb; the sorted results already answer "most" and "highest".
RANKING = re.compile(r'前(?:[一二三四五六七八九十兩]|\d+)(?=[名個位家大高低多少])|比較(?![多少高低好快慢大小])|相比|對比|比一比|差多少')
# Words a template already satisfies, keyed by the analysis whose filter they describe.
COVERED = {'q10': ('前五', '前5'), 'q11': ('完成', '做完'), 'q06': ('收貨', '到貨')}

DOMAIN = re.compile(r'部門|專案|案子|廠商|供應商|任務|工作|成本|花費|費用|開銷|支出|預算|超支|不良|瑕疵|品質|品管|檢驗|風險|訂單|採購|下單'
                    r'|工時|時數|進度|交貨|到貨|收貨|逾期|過期|到期|延遲|延誤|負責人|待辦|批次|做完|完成|多少|幾|比例|清單|列出|排名|統計')
HOWTO = re.compile(r'怎麼問|如何問|怎麼用|如何使用|怎麼查|如何查|要怎麼|教我|使用說明|說明一下')
CAPABILITIES = re.compile(r'你是誰|你可以|你能|你會|可以查|能查|會查|什麼功能|功能有|能做什麼|可以做什麼')

COMMAND = re.compile(r'\b(?:delete|drop|update|insert|alter|truncate|create|replace|select|union|pragma|attach|exec)\b|;|--'
                     r'|改成|改為|改掉|修改|刪除|刪掉|移除|新增|更新|設為|設成|標成|標記為|關掉', re.I)
OVERRIDE = re.compile(r'(?:忽略|無視|不要管|別管|跳過).{0,8}(?:規則|指示|限制|設定|前面|以上)|ignore|system\s*prompt|jailbreak'
                      r'|所有資料|全部資料|所有公司|全部公司|所有的資料|全部的資料', re.I)
NO_DATA = re.compile(r'薪水|薪資|薪酬|月薪|年薪|獎金|分紅|考績|績效考核|身分證|電話|手機|地址|住址|生日|密碼|帳號|個資')
COMPANY_SUFFIXES = ('股份有限公司', '有限公司', '公司', '科技', '食品', '電子', '工程', '軟體', '活動', '營造')

REFUSALS = {
    'command': '資料分析只能「查詢」固定的 16 種分析，不能執行指令，也不能修改資料。要更改工作狀態，請到該任務的頁面操作。',
    'override': '這些限制不能關閉：資料分析只會在目前公司與你的權限範圍內，查詢固定的 16 種分析。',
    'no_data': '資料分析沒有這類資料（例如薪資、考績或個人資料），無法回答。可以查的是工作進度、成本、供應商、品質與風險。',
}

TOPICS = {
    'q01': [(r'狀態|分布', 2), (r'進行中|待辦', 1)],
    'q02': [(r'逾期|過期|延誤|超過期限|拖延|拖', 2), (r'部門', 2), (r'沒做完|未完成|還沒完成|沒完成', 1)],
    'q03': [(r'完成率|完成比例|完成度|進度|幾成|百分之|做到哪', 2), (r'專案|案子', 1)],
    'q04': [(r'超支|超出預算|超過預算|預算', 2), (r'專案|案子', 1), (r'多少錢|金額', 1)],
    'q05': [(r'還沒送來|沒送來|還沒交|未交|沒交貨|沒到貨|答應的貨', 2), (r'廠商|供應商', 1), (r'逾期|過期|超過', 1), (r'訂單|金額', 1)],
    'q06': [(r'晚交|晚到|遲交|延遲|延誤交貨|準時', 2), (r'廠商|供應商', 1), (r'比例|率|幾次|最常|常常', 1)],
    'q07': [(r'不良|瑕疵|品質|品管|檢驗', 2), (r'率|比例|最高', 1), (r'專案|案子', 1)],
    'q08': [(r'成本|花費|費用|開銷|花了|支出', 2), (r'每個月|各月|月份|每月', 1), (r'類別|各類|分類', 1)],
    'q09': [(r'風險', 2), (r'嚴重|高|還沒處理|未處理|沒解決|尚未結案|還沒結案', 1)],
    'q10': [(r'誰|哪些人|負責人|手上|最忙', 2), (r'最多|前五|前5', 1), (r'沒做完|未完成|還沒完成|待辦', 1)],
    'q11': [(r'工時|時數|花的時間|比預估|超估', 2), (r'完成|做完', 1)],
    'q12': [(r'採購|下單|訂了|訂購', 2), (r'金額|多少錢|總額', 1), (r'專案|案子', 1)],
    'q13': [(r'本週|這週|這禮拜|本星期|這星期|這個禮拜', 2), (r'到期', 2), (r'沒做完|未完成|還沒完成|沒完成', 1)],
    'q14': [(r'退回|被退|受阻|卡住|阻塞|擋住', 2), (r'專案|案子', 1)],
    'q15': [(r'還在等|尚未收貨|還沒收貨|沒收到|在途', 2), (r'沒逾期|未逾期|還沒到期|還沒過期', 2)],
    'q16': [(r'零不良|沒有不良|零缺點|完全沒有不良|全部合格|零瑕疵', 3), (r'批次|批', 1)],
}
# One per group of the plain-language table: progress, money, suppliers, quality, risk.
STARTERS = ('q02', 'q04', 'q06', 'q07', 'q09')

HELP = {
    'capabilities': (
        '我是資料分析小幫手，只會查固定的 16 種公司資料，分成五類：\n'
        '・工作進度：逾期、完成率、誰的事最多、本週到期\n'
        '・錢：超支、每月成本、採購金額\n'
        '・供應商：還沒交貨、常晚交、還在等的貨\n'
        '・品質：不良率、零不良批次\n'
        '・風險：還沒解決的高風險\n'
        '點下面的問題就能直接查。', STARTERS),
    'howto': (
        '這樣問最準：\n'
        '1. 直接說要查什麼，例如「各部門逾期未完成數」。\n'
        f'2. 日期固定在 {store.AS_OF}，還不能指定「上週」「9 月」這類時間。\n'
        '3. 結果會列出全部的部門、專案或人員，不能只查其中一個，請在結果表格裡找。\n'
        '4. 問到我不會的，我會說明原因並建議最接近的查詢，按下才會查。', ('q02', 'q13')),
    'out_of_scope': (
        '這個問題我沒辦法回答。我只會查公司的工作進度、成本、供應商、品質和風險資料。'
        '請點下方快捷題試試看，或問「你可以查什麼？」。', STARTERS),
}


def labels():
    return {q['query_id']: q['label'] for q in store.catalog()}


def suggestion(query_id, omits=''):
    return dict(query_id=query_id, label=labels()[query_id], omits=omits)


def help_reply(topic):
    """Written help; it never reads company data, so every company gets the same text."""
    answer, shortcuts = HELP[topic]
    return dict(kind='help', answer=answer, fallback=dict(reason=topic, conditions=[]), conditions=[],
                suggestions=[suggestion(q) for q in shortcuts])


def vocabulary(db):
    """Names in this company's data that make a question about one person, department, supplier or project."""
    names = {r[0] for r in db.execute('SELECT name FROM people')}
    names |= {r[0] for r in db.execute('SELECT name FROM suppliers')}
    names |= {r[0] for r in db.execute('SELECT supplier_id FROM suppliers')}
    for project_id, title in db.execute('SELECT project_id, title FROM projects'):
        names |= {re.sub(r'（.*?）', '', title).strip(), project_id.split('-')[-1]}
    departments = {r[0] for r in db.execute('SELECT DISTINCT department FROM people')}
    parts = [re.escape(n) for n in sorted(names, key=len, reverse=True) if n]
    parts += [re.escape(d) + r'(?:部門|部|組|課|處|單位)' for d in sorted(departments, key=len, reverse=True) if d]
    return re.compile('|'.join(parts)) if parts else None


def mentioned_company(question, others):
    for name in others:
        core = name
        for suffix in COMPANY_SUFFIXES:
            if core.endswith(suffix) and len(core) - len(suffix) >= 2:
                core = core[:-len(suffix)]
        if name in question or core in question:
            return name
    return None


def early_reply(question, others, names):
    """A refusal or written help, decided before any model sees the question."""
    if COMMAND.search(question):
        return refusal('command')
    if OVERRIDE.search(question):
        return refusal('override')
    other = mentioned_company(question, others)
    if other:
        return refusal('other_company', f'這個問題詢問的是{other}，目前公司與權限範圍內沒有{other}的資料，無法回答，也不會用本公司的資料代替。')
    if NO_DATA.search(question):
        return refusal('no_data')
    if DOMAIN.search(question) or (names and names.search(question)):
        return None
    return help_reply('howto' if HOWTO.search(question) else 'capabilities' if CAPABILITIES.search(question) else 'out_of_scope')


def refusal(reason, answer=None):
    return dict(kind='unsupported', answer=answer or REFUSALS[reason], fallback=dict(reason=reason, conditions=[]),
                conditions=[], suggestions=[])


def rank(text):
    scores = {}
    for query_id, keywords in TOPICS.items():
        score = sum(weight for pattern, weight in keywords if re.search(pattern, text))
        if score:
            scores[query_id] = score
    return sorted(scores, key=lambda q: (-scores[q], q))


def suggest(question, names, proposed=None):
    """Name the conditions no template applies and offer up to three nearest analyses; nothing runs."""
    conditions = [dict(type='target', text=m.group(0)) for m in names.finditer(question)] if names else []
    text = names.sub(' ', question) if names else question
    ranked = rank(text)
    if proposed in labels():
        ranked = [proposed] + [q for q in ranked if q != proposed]
    found = [('time', m.group(0)) for m in TIME.finditer(question)]
    found += [('status', m.group(0)) for m in STATUS.finditer(question)]
    found += [('ranking', m.group(0)) for m in RANKING.finditer(question)]
    covered = COVERED.get(ranked[0], ()) if ranked else ()
    conditions += [dict(type=kind, text=word) for kind, word in found if not any(c in word for c in covered)]
    seen = set()
    conditions = [c for c in conditions if (c['type'], c['text']) not in seen and not seen.add((c['type'], c['text']))]
    for c in conditions:
        c['label'] = CONDITION_LABELS[c['type']]
    scope = f'結果是目前公司的全部範圍、基準日 {store.AS_OF}'
    if conditions:
        words = '、'.join(f'「{c["text"]}」' for c in conditions)
        reason, omits = 'condition', f'不含{words}條件'
        answer = f'目前的分析還不能套用{words}這個條件。下面是最接近的分析，尚未執行，按下才會查詢；{scope}，{omits}。'
    else:
        reason, omits = 'topic', '不套用問題裡的其他條件'
        answer = f'沒有完全符合的分析。下面是最接近的分析，尚未執行，按下才會查詢；{scope}，{omits}。'
    if not ranked:
        reason, ranked = ('condition' if conditions else 'no_match'), list(STARTERS)
        answer = (f'目前的分析還不能套用{words}這個條件，也找不到相近的分析。' if conditions else '找不到相近的分析。') + \
            '請點下方快捷題，或問「你可以查什麼？」看能查哪些資料。'
    return dict(kind='fallback', answer=answer, conditions=conditions,
                fallback=dict(reason=reason, conditions=sorted({c['type'] for c in conditions})),
                suggestions=[suggestion(q, omits) for q in ranked[:3]])
