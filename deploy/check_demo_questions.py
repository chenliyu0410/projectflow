"""Run the demo questions against the isolated preview API before a live demo (read-only queries)."""
import argparse
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

import httpx

REFUSAL = '資料不足'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:18006')
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    url = urlsplit(args.url)
    if url.scheme != 'http' or url.hostname != '127.0.0.1' or url.port != 18006 or url.path:
        parser.error('Only the dedicated loopback acceptance API on port 18006 is allowed')
    cases = json.loads((Path(__file__).parent / 'rag-starter/evaluation/demo-questions.json').read_text(encoding='utf-8'))
    results = []
    with httpx.Client(base_url=args.url, timeout=210, trust_env=False, follow_redirects=False) as client:
        assert client.get('/health/acceptance').json() == {'acceptance': True}
        active = None
        for case in cases:
            who = (case.get('company', 'food'), case['login'])
            if active != who:
                client.cookies.clear()
                client.post('/auth/login', json=dict(organization_key=who[0], username=who[1], password='demo-' + who[1])).raise_for_status()
                active = who
            payload = dict(question=case['question'], dataset=case['dataset'], mode=case.get('mode', 'rag'),
                           include_history=case.get('include_history', False))
            if 'project_title' in case:
                projects = client.get('/ai/status', params={'dataset': case['dataset']}).json()['projects']
                payload['project_id'] = next(p['project_id'] for p in projects if p['title'].startswith(case['project_title']))
            response = client.post('/ai/ask', json=payload)
            response.raise_for_status()
            result = response.json()
            answer, sources = result['answer'], [s['document_id'] for s in result['sources']]
            problems = []
            if case.get('kind') == 'refuse' and REFUSAL not in answer and result['kind'] != 'no_sources':
                problems.append('expected refusal')
            problems += [f'missing {p}' for p in case.get('must_contain', []) if not re.search(p, answer)]
            problems += [f'should not say {p}' for p in case.get('must_not_contain', []) if re.search(p, answer)]
            problems += [f'missing source {s}' for s in case.get('sources_include', []) if s not in sources]
            problems += [f'leaked source {s}' for s in case.get('sources_exclude', []) if s in sources]
            if 'sources_only' in case and set(sources) - set(case['sources_only']):
                problems.append('sources outside ' + ','.join(case['sources_only']))
            if 'source_type' in case and case['source_type'] not in {s.get('source_type') for s in result['sources']}:
                problems.append('missing ' + case['source_type'] + ' source')
            results.append(dict(case, engine=result['engine'], retrieval=result.get('retrieval'), answer=answer,
                                citations=result.get('citations', []), sources=sources, problems=problems))
            print(case['id'], 'ok' if not problems else problems, flush=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    failed = [r['id'] for r in results if r['problems']]
    print(json.dumps(dict(cases=len(results), failed=failed), ensure_ascii=False))
    if failed:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
