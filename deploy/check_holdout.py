"""Score the frozen holdout question bank against the isolated preview API (read-only queries).

The bank (rag-starter/evaluation/holdout.jsonl) was frozen in git before its first run and is never
edited to fit results. Scores are automatic checks, not a substitute for human semantic review.
"""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import time
from urllib.parse import urlsplit

import httpx

FIXED_REFUSAL = '資料不足'
FREE_REFUSAL = re.compile(r'未記載|沒有記載|未提供|沒有提供|無法得知|無法確認|不能取得|無法提供|沒有相關')


def score(case, result):
    problems = []
    answer = result['answer']
    sources = result['sources']
    source_ids = [s['document_id'] for s in sources]
    cited = result.get('citations') or []
    for pattern in case.get('must_not', []):
        if re.search(pattern, answer):
            problems.append(f'不得出現：{pattern}')
    for sid in case.get('forbidden_sources', []):
        if sid in source_ids:
            problems.append(f'越權或舊版來源：{sid}')
    if 'sources_only' in case and set(source_ids) - set(case['sources_only']):
        problems.append('出現範圍外來源：' + ','.join(sorted(set(source_ids) - set(case['sources_only']))))
    if any(c not in source_ids for c in cited):
        problems.append('引用不在本次來源內')
    style = None
    if case.get('refuse'):
        if result['kind'] == 'no_sources' or FIXED_REFUSAL in answer:
            style = 'fixed'
        elif FREE_REFUSAL.search(answer):
            style = 'free'
        else:
            problems.append('應拒答卻作答')
        return problems, style
    if result['engine'] != 'model':
        problems.append(f'未由模型回答（{result["kind"]}）')
        return problems, style
    for pattern in case.get('must', []):
        if not re.search(pattern, answer):
            problems.append(f'缺少：{pattern}')
    titles = {s['document_id']: s.get('title', '') for s in sources}
    if case.get('cite_any') and not set(cited) & set(case['cite_any']):
        problems.append('未引用關鍵來源：' + '/'.join(case['cite_any']))
    if case.get('cite_titles') and not any(t in titles.get(c, '') for c in cited for t in case['cite_titles']):
        problems.append('未引用關鍵來源：' + '/'.join(case['cite_titles']))
    return problems, style


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:18006')
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    url = urlsplit(args.url)
    if url.scheme != 'http' or url.hostname != '127.0.0.1' or url.port != 18006 or url.path:
        parser.error('Only the dedicated loopback acceptance API on port 18006 is allowed')
    bank = Path(__file__).parent / 'rag-starter/evaluation/holdout.jsonl'
    cases = [json.loads(line) for line in bank.read_text(encoding='utf-8').splitlines() if line.strip()]
    rows = []
    with httpx.Client(base_url=args.url, timeout=210, trust_env=False, follow_redirects=False) as client:
        assert client.get('/health/acceptance').json() == {'acceptance': True}
        active, projects = None, {}
        for case in cases:
            who = (case.get('company', 'food'), case['login'])
            if active != who:
                client.cookies.clear()
                client.post('/auth/login', json=dict(organization_key=who[0], username=who[1], password='demo-' + who[1])).raise_for_status()
                active, projects = who, {}
            payload = dict(question=case['question'], dataset=case['dataset'], mode='rag', include_history=case.get('include_history', False))
            if 'project_title' in case:
                if case['dataset'] not in projects:
                    projects[case['dataset']] = client.get('/ai/status', params={'dataset': case['dataset']}).json()['projects']
                payload['project_id'] = next(p['project_id'] for p in projects[case['dataset']] if p['title'].startswith(case['project_title']))
            start = time.monotonic()
            response = client.post('/ai/ask', json=payload)
            response.raise_for_status()
            result = response.json()
            problems, style = score(case, result)
            rows.append(dict(case, seconds=round(time.monotonic() - start, 3), passed=not problems, problems=problems, refusal_style=style,
                             engine=result['engine'], kind=result['kind'], retrieval=result.get('retrieval'), answer=result['answer'],
                             citations=result.get('citations') or [], sources=[s['document_id'] for s in result['sources']]))
            print(case['id'], 'pass' if not problems else problems, flush=True)
    by_category = defaultdict(lambda: [0, 0])
    for row in rows:
        by_category[row['category']][0] += row['passed']
        by_category[row['category']][1] += 1
    summary = dict(cases=len(rows), passed=sum(r['passed'] for r in rows),
                   by_category={k: f'{v[0]}/{v[1]}' for k, v in by_category.items()},
                   free_style_refusals=[r['id'] for r in rows if r['refusal_style'] == 'free'],
                   failed=[r['id'] for r in rows if not r['passed']])
    report = dict(created_at=datetime.now(timezone.utc).isoformat(), bank=str(bank.name), independent_of_prompt_tuning=True,
                  third_party_blind=False, summary=summary, cases=rows)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main()
