"""Content-free deterministic evaluation. A runner may call a model or a fixture."""
import math
from time import perf_counter


def _percentile(values, fraction):
    if not values:
        return None
    values = sorted(values)
    return values[max(0, math.ceil(len(values) * fraction) - 1)]


def evaluate(cases, run, *, mode='actual'):
    if mode not in {'actual', 'fixture'}:
        raise ValueError('invalid evaluation mode')
    metrics = dict(source_leak_count=0, stale_source_count=0, invalid_citation_count=0,
                   no_answer_failure_count=0, kind_failure_count=0, missing_source_count=0)
    rows, times = [], []
    passed = failed = skipped = 0
    for index, case in enumerate(cases):
        started = perf_counter()
        errors = []
        try:
            result = run(case)
            duration = (perf_counter() - started) * 1000
            if result.get('skipped'):
                skipped += 1
                rows.append({'case_id': str(case.get('id', index)), 'status':'skipped'})
                continue
            times.append(duration)
            sources = result.get('sources', [])
            source_ids = {s['source_id'] if isinstance(s, dict) else s for s in sources}
            expected = set(case.get('expected_source_ids', []))
            leaked = len(source_ids - expected)
            stale = sum(s.get('is_current') is False for s in sources if isinstance(s, dict))
            invalid = len(set(result.get('citations', [])) - source_ids)
            missing = len(set(case.get('required_source_ids', [])) - source_ids)
            for name, value in [('source_leak_count', leaked), ('stale_source_count', stale),
                                ('invalid_citation_count', invalid), ('missing_source_count', missing)]:
                metrics[name] += value
                if value: errors.append(name)
            expected_kind = case.get('expected_kind')
            if expected_kind is not None and result.get('kind') != expected_kind:
                metric = 'no_answer_failure_count' if expected_kind in {'no_answer', 'no_sources'} else 'kind_failure_count'
                metrics[metric] += 1
                errors.append(metric)
            expected_failure = case.get('expected_failure')
            if expected_failure and result.get('error_code') != expected_failure:
                errors.append('expected_failure_mismatch')
        except Exception:
            times.append((perf_counter() - started) * 1000)
            errors = ['runner_error']
        status = 'failed' if errors else 'passed'
        failed += bool(errors)
        passed += not errors
        rows.append({'case_id':str(case.get('id', index)), 'status':status, 'failures':errors})
    return dict(mode=mode, actual_model_verified=False, total=len(rows), executed=passed+failed,
                passed=passed, failed=failed, skipped=skipped, metrics=metrics,
                latency_ms={'p50':_percentile(times,.50), 'p95':_percentile(times,.95)},
                token_count=None, cost=None, cases=rows)
