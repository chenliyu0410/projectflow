"""Run the document intake pipeline over a folder and write an HTML + JSON report.

    api/.venv/Scripts/python.exe deploy/ocr_pipeline.py deploy/ocr-eval/samples --models ../ocr-models --compare-preprocess

Files with a <name>.gt.txt beside them are scored by 1-CER. Only reads the folder; writes to --out.
"""
import argparse
from html import escape
import json
import os
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'api'))
from app.ai import extractors, ingest, ocr, ocr_metrics  # noqa: E402

SUPPORTED = {'.pdf', '.png', '.jpg', '.jpeg', '.docx', '.xlsx', '.txt', '.csv'}
ROUTE_NAMES = {'text_pdf': '文字層PDF', 'ocr': '掃描→OCR', 'office': 'Word／Excel', 'plain': '純文字', 'skipped': '略過'}


def run(path):
    started = time.perf_counter()
    try:
        result = ingest.ingest(path.read_bytes(), path.name)
    except extractors.ExtractionError as exc:
        return {'filename': path.name, 'error': str(exc), 'pages': [], 'chunks': [], 'seconds': 0, '_pages': []}
    item = result.as_dict()
    item['seconds'] = round(time.perf_counter() - started, 3)
    truth = path.with_name(path.name + '.gt.txt')
    if truth.is_file():
        item['accuracy'] = round(ocr_metrics.accuracy(truth.read_text(encoding='utf-8'), result.text()), 4)
    item['text'] = result.text()
    item['_pages'] = result.pages
    return item


def badge(route):
    return f'<span class="b {route}">{ROUTE_NAMES.get(route, route)}</span>'


def pct(item):
    return f"{item['accuracy']:.1%}" if 'accuracy' in item else '—'


def html_report(items, stats, comparison):
    scored = [i['accuracy'] for i in items if 'accuracy' in i]
    rows = ''.join(
        f"<tr><td>{escape(i['filename'])}</td><td>{''.join(badge(p['route']) for p in i['pages']) or escape(i.get('error', ''))}</td>"
        f"<td>{len(i['pages'])}</td><td>{', '.join(str(p['confidence']) for p in i['pages'] if p['confidence'] is not None) or '—'}</td>"
        f"<td>{i['seconds']}</td><td>{pct(i)}</td><td>{len(i['chunks'])}</td></tr>"
        for i in items)
    route_rows = ''.join(f"<tr><td>{badge(r)}</td><td>{s['pages']}</td><td>{s['seconds']}</td><td>{s['per_page']}</td></tr>" for r, s in stats.items())
    ab = ''.join(f"<tr><td>{escape(n)}</td><td>{off:.1%}</td><td>{on:.1%}</td><td>{on - off:+.1%}</td></tr>" for n, off, on in comparison)
    details = ''.join(
        f"<details><summary>{escape(i['filename'])}</summary><pre>{escape(i.get('text') or i.get('error', ''))}</pre>"
        f"<p class='m'>前 3 段 RAG chunk（含 metadata）</p><pre>{escape(json.dumps([{k: c[k] for k in ('filename', 'page', 'route')} | {'text': c['text'][:60]} for c in i['chunks'][:3]], ensure_ascii=False, indent=1))}</pre></details>"
        for i in items)
    average = f'{sum(scored) / len(scored):.1%}' if scored else '—'
    return f"""<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>OCR 管線報告</title><style>
body{{font-family:system-ui,'Microsoft JhengHei',sans-serif;margin:24px auto;max-width:1000px;padding:0 16px;color:#222;background:#fff}}
table{{border-collapse:collapse;width:100%;margin:8px 0 24px}}td,th{{border-bottom:1px solid #ddd;padding:6px 8px;text-align:left}}
.cards{{display:flex;gap:12px;flex-wrap:wrap}}.card{{border:1px solid #ddd;border-radius:8px;padding:12px 16px;min-width:150px}}.card b{{font-size:24px;display:block}}
.b{{display:inline-block;border-radius:4px;padding:1px 6px;margin-right:4px;font-size:12px;color:#fff}}.text_pdf{{background:#2e7d5b}}.ocr{{background:#5b4bb7}}
.office{{background:#2f6f9f}}.plain{{background:#666}}.skipped{{background:#b55}}pre{{white-space:pre-wrap;background:#f6f6f6;padding:8px}}.m{{color:#666}}
</style><h1>OCR 管線報告</h1>
<div class="cards"><div class="card">檔案<b>{len(items)}</b></div><div class="card">頁數<b>{sum(len(i['pages']) for i in items)}</b></div>
<div class="card">平均辨識正確率（1−CER）<b>{average}</b></div><div class="card">RAG 段落<b>{sum(len(i['chunks']) for i in items)}</b></div></div>
<h2>逐檔結果</h2><table><tr><th>檔案</th><th>逐頁路徑</th><th>頁</th><th>OCR 信心</th><th>秒</th><th>1−CER</th><th>段落</th></tr>{rows}</table>
<h2>處理時間（分路統計）</h2><table><tr><th>路徑</th><th>頁數</th><th>總秒數</th><th>每頁秒數</th></tr>{route_rows}</table>
{'<h2>前處理 A/B（1−CER）</h2><table><tr><th>檔案</th><th>關閉</th><th>開啟</th><th>差異</th></tr>' + ab + '</table>' if comparison else ''}
<h2>清理後全文與 RAG 段落</h2>{details}</html>"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('folder', type=Path)
    parser.add_argument('--models', type=Path, help='Folder with the Traditional Chinese OCR model')
    parser.add_argument('--out', type=Path, default=Path('output/ocr-report'))
    parser.add_argument('--compare-preprocess', action='store_true')
    args = parser.parse_args()
    if args.models:
        os.environ['PF_ACCEPTANCE_MODE'] = 'true'  # The OCR switch is only honoured in isolated runs.
        os.environ['PF_AI_OCR_MODEL_DIR'] = str(args.models.resolve())
    print('OCR', 'on' if ocr.enabled() else 'off (images and scanned pages are skipped)')
    files = sorted(p for p in args.folder.iterdir()
                   if p.suffix.lower() in SUPPORTED and not p.name.endswith('.gt.txt'))  # Labels are answers, not inputs.
    image = next((p for p in files if p.suffix.lower() in extractors.IMAGES), None)
    if ocr.enabled() and image:
        run(image)  # Warm-up so model loading is not counted in the per-page seconds.
    items = [run(path) for path in files]
    stats = ocr_metrics.route_stats([page for item in items for page in item['_pages']])
    comparison = []
    if args.compare_preprocess and ocr.enabled():
        for item, path in zip(items, files):
            if 'accuracy' in item and any(p['route'] == 'ocr' for p in item['pages']):
                ocr.PREPROCESS = False
                off = run(path).get('accuracy', 0.0)
                ocr.PREPROCESS = True
                comparison.append((item['filename'], off, item['accuracy']))
    for item in items:
        del item['_pages']
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / 'result.json').write_text(json.dumps({'items': items, 'routes': stats, 'preprocess_ab': comparison}, ensure_ascii=False, indent=1), encoding='utf-8')
    (args.out / 'report.html').write_text(html_report(items, stats, comparison), encoding='utf-8')
    for item in items:
        print(f"{item['filename']}: {[p['route'] for p in item['pages']]} {item.get('accuracy', item.get('error', ''))}")
    print(f"report: {(args.out / 'report.html').resolve()}")


if __name__ == '__main__':
    main()
