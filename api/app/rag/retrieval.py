import math
import re
from collections import Counter


def _tokens(text):
    result = re.findall(r'[a-z0-9_]+', text.lower())
    for run in re.findall(r'[\u3400-\u9fff]+', text):
        result.extend(run[i:i + 2] for i in range(len(run) - 1))
        if len(run) == 1:
            result.append(run)
    return result


def expand_query(question, previous_question=None):
    result = str(question)[:2000]
    if previous_question:
        result += '\n前次問題：' + str(previous_question)[:1000]
    for word, synonyms in {'費用': '成本 支出', '期限': '截止 到期', '客戶': '顧客', '文件': '文檔', '合約': '契約'}.items():
        if word in result:
            result += ' ' + synonyms
    return result


def _vector(value):
    if not isinstance(value, (list, tuple)) or not value or len(value) > 4096:
        return None
    if any(isinstance(x, bool) or not isinstance(x, (float, int)) or not math.isfinite(x) for x in value):
        return None
    norm = math.hypot(*value)
    return [x / norm for x in value] if math.isfinite(norm) and norm else None


def rank(question, candidates, query_vector=None, limit=6, budget=8000):
    if len(candidates) > 5000:
        raise ValueError('candidate_limit')
    budget = max(0, min(8000, budget))
    limit = max(0, min(200, limit))
    query = Counter(_tokens(question))
    docs = [Counter(_tokens(c.get('text', ''))) for c in candidates]
    average = sum(sum(d.values()) for d in docs) / max(1, len(docs)) or 1
    frequency = Counter(t for d in docs for t in d)
    lexical, vector = [], []
    qvec = _vector(query_vector)
    for i, terms in enumerate(docs):
        score = 0
        length = sum(terms.values())
        for term in query:
            tf = terms[term]
            if tf:
                idf = math.log(1 + (len(docs) - frequency[term] + .5) / (frequency[term] + .5))
                score += idf * tf * 2.2 / (tf + 1.2 * (.25 + .75 * length / average))
        if score > 0:
            lexical.append((i, score))
        vec = _vector(candidates[i].get('embedding'))
        if qvec and vec and len(qvec) == len(vec):
            similarity = sum(a * b for a, b in zip(qvec, vec))
            if similarity > 0:
                vector.append((i, similarity))
    scores = Counter()
    for ranking in (lexical, vector):
        for position, (i, _) in enumerate(sorted(ranking, key=lambda pair: (-pair[1], pair[0])), 1):
            scores[i] += 1 / (60 + position)
    # Transparent rule reranking: exact question phrase receives a small tie-breaking boost.
    phrase = question.strip().lower()
    for i in scores:
        if phrase and phrase in candidates[i].get('text', '').lower():
            scores[i] += .001
    selected, parents = [], set()
    for i in sorted(scores, key=lambda i: (-scores[i], i)):
        candidate = candidates[i]
        parent = (candidate.get('document_id'), candidate.get('version'), candidate.get('parent_id', candidate.get('chunk_id', i)))
        if parent in parents:
            continue
        excerpt = candidate.get('parent_text') or candidate.get('text', '')
        excerpt = excerpt[:budget]
        if not excerpt or len(selected) >= limit:
            break
        locator = dict(candidate.get('locator') or {})
        if 'start_char' in locator:
            locator['end_char'] = locator['start_char'] + len(excerpt)
        selected.append(dict(candidate, excerpt=excerpt, locator=locator))
        budget -= len(excerpt)
        parents.add(parent)
    return selected
