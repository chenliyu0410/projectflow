"""OCR-FORMS evaluation: current OCR vs coordinate-based reading vs OvisOCR2 on handwritten forms, with an HTML report.

    <eval-python> deploy/ocr_forms_eval.py --samples ../output/ocr-forms/samples --out ../output/ocr-forms/results \
        --models ../output/rag-starter-acceptance/local-model/ocr-models \
        --ovis-python ../output/ocr-forms/.venv-ovis/Scripts/python.exe --ovis-model ../output/ocr-forms/models/OvisOCR2

Methods (see docs/superpowers/plans/2026-11-10-ocr-handwriting-forms.md):
  P0        current pipeline (ocr.preprocess + RapidOCR on the whole page), values paired to labels by position; no checkbox reading
  P1-free   no template: lines removed, light evened, whole-page RapidOCR, label pairing; checkboxes found as small squares
  P1        template: page aligned to the form, each field cropped, cleaned and read by RapidOCR; checkbox ink measured
  P2-page   OvisOCR2 on the whole page (end to end); values paired from its table output
  P2        template crops (same as P1) read by OvisOCR2; checkbox crops asked "is it marked?"
  P3        combination of measured parts, no new parameters: P2 field reading + P1 checkbox ink
Only reads the samples; writes to --out. Pages named tune-* may be used to choose thresholds; report the test-* pages.
"""
import argparse
from html import escape
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))
from app.ai import form_ocr, ocr, ocr_metrics  # noqa: E402

TEMPLATES = Path(__file__).resolve().parent / "ocr-eval/forms/templates"
CHECK_SYMBOLS = {"☑": True, "✓": True, "✔": True, "■": True, "☒": True, "√": True, "☐": False, "□": False}
METHODS = ["P0", "P1-free", "P1", "P2-page", "P2", "P3"]

try:
    import opencc
    _s2t = opencc.OpenCC("s2t")
    to_traditional = _s2t.convert
except ImportError:  # scoring still works; Simplified output would just count as wrong characters
    def to_traditional(text):
        return text


def score_text(truth, predicted):
    """Both sides go through s2t, so a Simplified answer (XFUND) and Simplified output compare as the same characters.
    "mapped" (1-CER >= 50%) is a loose "read roughly right" share, not a measure of field mapping."""
    t, p = form_ocr.normalize(to_traditional(truth)), form_ocr.normalize(to_traditional(predicted))
    return {"acc": round(ocr_metrics.accuracy(t, p), 4), "exact": t == p, "mapped": ocr_metrics.accuracy(t, p) >= 0.5}

# ---------------------------------------------------------------- RapidOCR


def rapid(image, detect=True):
    """[(text, [x0, y0, x1, y1])] in the image's coordinates."""
    result, _ = ocr.engine()(image, use_det=detect, use_cls=False, use_rec=True)
    out = []
    for item in result or []:
        if detect:
            points, text, _ = item
            xs, ys = [p[0] for p in points], [p[1] for p in points]
            out.append((ocr.normalize(text), [min(xs), min(ys), max(xs), max(ys)]))
        else:
            out.append((ocr.normalize(item[0]), [0, 0, image.shape[1], image.shape[0]]))
    return out


def reading_order(boxes):
    if not boxes:
        return ""
    height = np.median([b[1][3] - b[1][1] for b in boxes]) or 1
    return "".join(t for t, _ in sorted(boxes, key=lambda b: (round(((b[1][1] + b[1][3]) / 2) / height), b[1][0])))


def read_field(image):
    """P1: split the field into tight lines and let the recognizer read each one (no text detector on small crops)."""
    return "".join(t for line in form_ocr.text_lines(image) for t, _ in rapid(line, detect=False))


def page_boxes(image, preprocess):
    """Whole-page RapidOCR boxes in original pixel coordinates."""
    from PIL import Image
    if preprocess == "current":
        pil = ocr.preprocess(Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB)))
        prepared = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
    else:
        prepared = form_ocr.prepare_field(image, min_height=0)
    fx = image.shape[1] / prepared.shape[1]
    return [(t, [v * fx for v in box]) for t, box in rapid(prepared)]

# ---------------------------------------------------------------- template-free checkboxes


def find_checkboxes(image):
    """Small printed squares on the page: [(x0, y0, x1, y1)]."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    ink = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 31, 15)
    contours, _ = cv2.findContours(ink, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    unit = max(image.shape[:2]) / 1754
    boxes = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if not (12 * unit <= w <= 45 * unit and 0.75 <= w / max(h, 1) <= 1.33):
            continue
        approx = cv2.approxPolyDP(contour, 0.1 * cv2.arcLength(contour, True), True)
        if len(approx) == 4 and cv2.contourArea(contour) > 0.6 * w * h:
            if not any(abs(x - b[0]) < w / 2 and abs(y - b[1]) < h / 2 for b in boxes):
                boxes.append((x, y, x + w, y + h))
    return boxes


def match_free_checkboxes(image, boxes, template):
    """Give each found square the template id whose caption is the text right of it and whose row label is left of it."""
    squares = find_checkboxes(image)
    groups = {b["group"] for b in template["checkboxes"]}
    found, used = {}, set()
    for x0, y0, x1, y1 in sorted(squares, key=lambda s: (s[1], s[0])):
        side, cy = x1 - x0, (y0 + y1) / 2
        row = [b for b in boxes if abs((b[1][1] + b[1][3]) / 2 - cy) < side * 1.2]
        left = sorted((b for b in row if b[1][2] <= x0 + 4 and any(form_ocr._is_label(b[0], g) for g in groups)),
                      key=lambda b: -b[1][2])
        group = left[0][0] if left else ""
        # OCR often reads a whole row of captions as one line; place each caption by its character offset in that line.
        best, best_gap = None, side * 2.5
        for text, (bx0, _, bx1, _) in row:
            if bx1 < x1 or not text:
                continue
            per_char = (bx1 - bx0) / len(text)
            for option in template["checkboxes"]:
                if option["id"] in used or (group and not form_ocr._is_label(group, option["group"])):
                    continue
                at = text.find(option["label"])
                if at < 0:
                    continue
                gap = abs(bx0 + at * per_char - x1)
                if gap < best_gap or (best and gap == best_gap and len(option["label"]) > len(best["label"])):
                    best, best_gap = option, gap
        if best:
            used.add(best["id"])
            found[best["id"]] = form_ocr.checkbox_state(image, (x0, y0, x1, y1))[0]
    return found

# ---------------------------------------------------------------- OvisOCR2 output


def html_table_boxes(markdown):
    """Turn OvisOCR2's Markdown/HTML into pseudo boxes (one per cell, row by row) so pair_fields can read it."""
    boxes, row = [], 0
    for part in re.split(r"(<table.*?</table>)", markdown, flags=re.S):
        if part.startswith("<table"):
            for tr in re.findall(r"<tr>(.*?)</tr>", part, flags=re.S):
                col = 0
                for attrs, cell in re.findall(r"<td([^>]*)>(.*?)</td>", tr, flags=re.S):
                    span = int((re.search(r'colspan="?(\d+)', attrs) or [0, 1])[1])
                    text = re.sub(r"<[^>]+>", "", cell).strip()
                    boxes.append((text, [col * 100, row * 60, col * 100 + 90 * span, row * 60 + 40]))
                    col += span
                row += 1
        else:
            for line in part.splitlines():
                if line.strip():
                    boxes.append((line.strip(), [0, row * 60, 90, row * 60 + 40]))
                    row += 1
    return boxes


def symbol_checkboxes(markdown, template):
    """Checkbox states only if OvisOCR2 wrote a box symbol right before the caption; otherwise unknown."""
    found = {}
    segments = re.findall(r"<tr>.*?</tr>", markdown, flags=re.S) + markdown.splitlines()
    for box in template["checkboxes"]:
        # Several rows share a caption (合格 on every line of a checklist): look inside the row that carries the box's row label.
        rows = [s for s in segments if box["group"] in s] or [markdown]
        for row in rows:
            hit = re.search(r"([☑✓✔■☒√☐□])\s*" + re.escape(box["label"]), row)  # "☑不合格" never matches 合格
            if hit:
                found[box["id"]] = "checked" if CHECK_SYMBOLS[hit.group(1)] else "unchecked"
                break
    return found


def ovis_box_state(answer):
    """OvisOCR2 is an OCR model: asked yes/no about a box crop it mostly transcribes the box itself (☑, ☐, ☒), and with
    only 4 new tokens it often starts a second turn ("yes / no", "☑ / No"). Its first answer counts: a box symbol, an
    X/V mark, or a leading yes/no; anything else is unsure. (Rule set after seeing the output formats on all pages.)"""
    text = answer.strip()
    if text[:1] in CHECK_SYMBOLS:
        return "checked" if CHECK_SYMBOLS[text[0]] else "unchecked"
    if text[:1] in ("X", "x", "V", "v"):
        return "checked"
    first = text.split()[0].lower() if text.split() else ""
    if first.startswith("yes"):
        return "checked"
    if first.startswith("no"):
        return "unchecked"
    return "unsure"


def run_ovis(args, images, prompt, name):
    if not args.ovis_python:
        return {}
    listing = args.out / f"ovis-{name}.txt"
    listing.write_text("\n".join(str(p) for p in images), encoding="utf-8")
    result = args.out / f"ovis-{name}.json"
    subprocess.run([str(args.ovis_python), str(Path(__file__).resolve().parent / "ocr-eval/forms/ovis_run.py"),
                    "--model", str(args.ovis_model), "--out", str(result), "--list", str(listing), "--prompt", prompt], check=True)
    return json.loads(result.read_text(encoding="utf-8"))

# ---------------------------------------------------------------- main loop


def evaluate(args):
    templates = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in TEMPLATES.glob("*.json")}
    pages = sorted(args.samples.glob("*.jpg"))
    if args.limit:
        pages = pages[:args.limit]
    crops_dir = args.out / "crops"
    crops_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    field_crops, box_crops = [], []
    ocr.engine()(np.full((32, 32, 3), 255, np.uint8))  # load the model before any timing
    for path in pages:
        truth = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
        template = templates[truth["template"]]
        image = cv2.imread(str(path))
        labels = {f["id"]: f["label"] for f in template["fields"]}
        captions = [c["label"] for c in template["checkboxes"]] + [p["text"] for p in template["printed"] if not p.get("label")]
        pred, seconds = {}, {}

        started = time.perf_counter()
        boxes = page_boxes(image, "current")
        pred["P0"] = {"fields": form_ocr.pair_fields(boxes, labels, captions), "checkboxes": {}}
        seconds["P0"] = time.perf_counter() - started

        started = time.perf_counter()
        boxes = page_boxes(image, "clean")
        pred["P1-free"] = {"fields": form_ocr.pair_fields(boxes, labels, captions),
                           "checkboxes": match_free_checkboxes(image, boxes, template)}
        seconds["P1-free"] = time.perf_counter() - started

        started = time.perf_counter()
        aligned, ok = form_ocr.align(image, template)
        fields, states, pieces = {}, {}, {}
        page_dir = crops_dir / path.stem
        page_dir.mkdir(exist_ok=True)
        for field in template["fields"]:
            x0, y0, x1, y1 = field["box"]
            pieces[field["id"]] = form_ocr.crop(aligned, [x0 + 4, y0 + 4, x1 - 4, y1 - 4], pad=0)
        prepared = time.perf_counter() - started  # alignment and cropping, shared by P1, P2 and P3
        started = time.perf_counter()
        for box in template["checkboxes"]:
            states[box["id"]] = form_ocr.checkbox_state(aligned, box["box"])
        ink_rule = time.perf_counter() - started
        started = time.perf_counter()
        for field_id, piece in pieces.items():
            fields[field_id] = form_ocr.normalize(read_field(piece))
        seconds["P1"] = prepared + ink_rule + time.perf_counter() - started
        seconds["_prepared"], seconds["_ink"] = prepared, ink_rule
        for field_id, piece in pieces.items():
            cv2.imwrite(str(page_dir / f"field-{field_id}.png"), piece)
            field_crops.append(page_dir / f"field-{field_id}.png")
        for box in template["checkboxes"]:
            cv2.imwrite(str(page_dir / f"box-{box['id']}.png"), form_ocr.crop(aligned, box["box"], pad=14))
            box_crops.append(page_dir / f"box-{box['id']}.png")
        pred["P1"] = {"fields": fields, "checkboxes": {k: v[0] for k, v in states.items()}, "scores": {k: v[1] for k, v in states.items()},
                      "aligned": ok}
        cv2.imwrite(str(page_dir / "aligned.jpg"), aligned)
        rows.append({"page": path.stem, "split": truth["split"], "template": truth["template"], "level": truth["level"],
                     "truth": truth, "pred": pred, "seconds": seconds})
        print(f"{path.stem}: aligned={ok}", flush=True)

    ovis_pages = run_ovis(args, pages, "page", "page")
    ovis_fields = run_ovis(args, field_crops, "field", "fields")
    ovis_boxes = run_ovis(args, box_crops, "checkbox", "boxes")
    for row, path in zip(rows, pages):
        if not ovis_pages:
            break
        template = templates[row["template"]]
        labels = {f["id"]: f["label"] for f in template["fields"]}
        captions = [c["label"] for c in template["checkboxes"]] + [p["text"] for p in template["printed"] if not p.get("label")]
        page = ovis_pages.get(str(path), {"text": "", "seconds": 0})
        row["pred"]["P2-page"] = {"fields": form_ocr.pair_fields(html_table_boxes(page["text"]), labels, captions),
                                  "checkboxes": symbol_checkboxes(page["text"], template), "raw": page["text"]}
        row["seconds"]["P2-page"] = page["seconds"]
        page_dir = crops_dir / row["page"]
        fields = {f["id"]: form_ocr.normalize(ovis_fields.get(str(page_dir / f"field-{f['id']}.png"), {}).get("text", ""))
                  for f in template["fields"]}
        states = {}
        for box in template["checkboxes"]:
            states[box["id"]] = ovis_box_state(ovis_boxes.get(str(page_dir / f"box-{box['id']}.png"), {}).get("text", ""))
        row["pred"]["P2"] = {"fields": fields, "checkboxes": states}
        row["pred"]["P3"] = {"fields": fields, "checkboxes": row["pred"]["P1"]["checkboxes"]}
        # GPU seconds are model.generate() only (image preprocessing in the processor is not counted).
        field_gpu = sum(ovis_fields.get(str(page_dir / f"field-{f['id']}.png"), {}).get("seconds", 0) for f in template["fields"])
        box_gpu = sum(ovis_boxes.get(str(page_dir / f"box-{b['id']}.png"), {}).get("seconds", 0) for b in template["checkboxes"])
        row["seconds"]["P2"] = row["seconds"]["_prepared"] + field_gpu + box_gpu
        row["seconds"]["P3"] = row["seconds"]["_prepared"] + field_gpu + row["seconds"]["_ink"]
    test = [r for r in rows if r["split"] == "test"] or rows  # report test pages only
    return rows, {m: round(float(np.mean([r["seconds"][m] for r in test if m in r["seconds"]])), 2)
                  for m in METHODS if any(m in r["seconds"] for r in test)}

# ---------------------------------------------------------------- scoring and report


def summarize(rows, templates, split):
    table = {}
    for method in METHODS:
        fields, boxes = [], []
        for row in rows:
            if row["split"] != split or method not in row["pred"]:
                continue
            template = templates[row["template"]]
            kinds = {f["id"]: f["type"] for f in template["fields"]}
            for field_id, truth in row["truth"]["fields"].items():
                if truth:
                    got = row["pred"][method]["fields"].get(field_id, "")
                    fields.append({**score_text(truth, got), "level": row["level"], "type": kinds[field_id],
                                   "template": row["template"], "truth": truth, "got": got, "page": row["page"], "id": field_id})
            for box_id, truth in row["truth"]["checkboxes"].items():
                state = row["pred"][method]["checkboxes"].get(box_id, "unknown")
                boxes.append({"mark": truth["mark"], "truth": truth["checked"], "state": state, "level": row["level"],
                              "ok": state == ("checked" if truth["checked"] else "unchecked"), "page": row["page"], "id": box_id})
        if not fields:
            continue
        mean = lambda items, key: round(float(np.mean([i[key] for i in items])), 4) if items else None
        decided = [b for b in boxes if b["state"] in ("checked", "unchecked")]
        table[method] = {
            "fields": len(fields), "acc": mean(fields, "acc"), "exact": mean(fields, "exact"), "mapped": mean(fields, "mapped"),
            "by_level": {lv: mean([f for f in fields if f["level"] == lv], "acc") for lv in ("neat", "normal", "messy")},
            "exact_by_level": {lv: mean([f for f in fields if f["level"] == lv], "exact") for lv in ("neat", "normal", "messy")},
            "by_type": {t: mean([f for f in fields if f["type"] == t], "acc") for t in sorted({f["type"] for f in fields})},
            "held_out_acc": mean([f for f in fields if f["template"] == "new_hire"], "acc"),
            "held_out_mapped": mean([f for f in fields if f["template"] == "new_hire"], "mapped"),
            "boxes": len(boxes), "box_acc": mean(boxes, "ok"),
            "box_unsure": round(sum(b["state"] == "unsure" for b in boxes) / len(boxes), 4) if boxes else None,
            "box_unknown": round(sum(b["state"] == "unknown" for b in boxes) / len(boxes), 4) if boxes else None,
            "box_acc_decided": mean(decided, "ok"),
            "box_by_mark": {m: mean([b for b in boxes if b["mark"] == m], "ok") for m in sorted({b["mark"] for b in boxes})},
            "_fields": fields, "_boxes": boxes,
        }
    return table


def pct(value):
    return "—" if value is None else f"{value:.1%}"


def report(rows, seconds, table, tune, out, samples):
    names = {"P0": "P0 現行（整頁 RapidOCR）", "P1-free": "P1-free 不用版型座標（去線、整頁辨識、位置配對、找方框）",
             "P1": "P1 座標定位＋RapidOCR", "P2-page": "P2-page OvisOCR2 整頁端到端", "P2": "P2 座標定位＋OvisOCR2", "P3": "P3 組合：OvisOCR2 讀欄位＋筆跡比例判斷勾選"}
    head = "<tr><th>做法</th><th>手寫欄位 1−CER</th><th>欄位完全正確</th><th>大致讀對（1−CER≥50%）</th><th>工整／普通／潦草 1−CER</th>" \
           "<th>沒看過的版型 1−CER</th><th>勾選正確</th><th>需人工確認</th><th>沒輸出／沒找到</th><th>默默判錯</th><th>每頁秒數</th></tr>"

    def row(m, t, sec):
        wrong = 1 - (t["box_acc"] or 0) - (t["box_unsure"] or 0) - (t["box_unknown"] or 0)
        return (f"<tr><td>{names[m]}</td><td>{pct(t['acc'])}</td><td>{pct(t['exact'])}</td><td>{pct(t['mapped'])}</td>"
                f"<td>{' ／ '.join(pct(t['by_level'][lv]) for lv in ('neat', 'normal', 'messy'))}</td><td>{pct(t['held_out_acc'])}</td>"
                f"<td>{pct(t['box_acc'])}</td><td>{pct(t['box_unsure'])}</td><td>{pct(t['box_unknown'])}</td>"
                f"<td>{pct(max(0.0, wrong)) if t['box_unknown'] != 1 else '—'}</td><td>{sec}</td></tr>")
    body = "".join(row(m, t, seconds.get(m, "—")) for m, t in table.items())
    marks = sorted({k for t in table.values() for k in t["box_by_mark"]})
    mark_names = {"check": "打勾", "cross": "打叉", "fill": "塗滿", "outside": "勾出框外", "faint": "很淡", "empty": "空白", "stray": "旁邊有雜筆"}
    mark_rows = "".join(f"<tr><td>{names[m]}</td>" + "".join(f"<td>{pct(t['box_by_mark'].get(k))}</td>" for k in marks) + "</tr>"
                        for m, t in table.items())
    examples = []
    best = "P2" if "P2" in table else "P1"
    for item in [f for f in table.get("P0", {}).get("_fields", []) if f["level"] == "messy"][:40:4]:
        others = {m: next((g["got"] for g in table[m]["_fields"] if g["page"] == item["page"] and g["id"] == item["id"]), "")
                  for m in table}
        crop_path = Path("crops") / item["page"] / f"field-{item['id']}.png"
        examples.append(f"<tr><td><img src='{crop_path.as_posix()}' style='max-width:360px'></td><td>{escape(item['truth'])}</td>"
                        + "".join(f"<td>{escape(others[m])}</td>" for m in table) + "</tr>")
    html = f"""<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>手寫表單辨識成效</title><style>body{{font-family:'Microsoft JhengHei',sans-serif;margin:24px;color:#222}}
table{{border-collapse:collapse;margin:12px 0}}td,th{{border:1px solid #ccc;padding:6px 8px;font-size:14px;vertical-align:middle}}
th{{background:#f3f1ea}}.m{{color:#666;font-size:13px}}</style>
<h1>手寫表單辨識成效（OCR-FORMS）</h1>
<p class="m">測試集 {sum(r['split'] == 'test' for r in rows)} 頁（其中「新人報到資料表」10 頁的版型完全沒拿來調參數）；樣本是用南臺科大真人手寫字合成的虛構繁中表單，數字與勾選標記為程式畫的筆跡，再加手機翻拍劣化。對照：現有乾淨樣本的 1−CER 是 91.7%（docs/ocr-pipeline-report.md）。</p>
<h2>總表（測試集）</h2><table>{head}{body}</table>
<h2>勾選框：各種標記的正確率（測試集）</h2><table><tr><th>做法</th>{''.join(f'<th>{mark_names.get(k, k)}</th>' for k in marks)}</tr>{mark_rows}</table>
<h2>調整集（只用來選門檻）</h2><table>{head}{''.join(row(m, t, '—') for m, t in tune.items())}</table>
<h2>潦草欄位實例（測試集，P0 做法下的潦草頁）</h2><table><tr><th>原圖（對齊後切出）</th><th>正確答案</th>{''.join(f'<th>{m}</th>' for m in table)}</tr>{''.join(examples)}</table>
</html>"""
    (out / "report.html").write_text(html, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--models", type=Path, required=True, help="folder with the Traditional Chinese RapidOCR model")
    parser.add_argument("--ovis-python", type=Path)
    parser.add_argument("--ovis-model", type=Path)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    os.environ["PF_AI_OCR"] = "true"
    os.environ["PF_AI_OCR_MODEL_DIR"] = str(args.models.resolve())
    args.out.mkdir(parents=True, exist_ok=True)
    rows, seconds = evaluate(args)
    templates = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in TEMPLATES.glob("*.json")}
    table, tune = summarize(rows, templates, "test"), summarize(rows, templates, "tune")
    clean = {m: {k: v for k, v in t.items() if not k.startswith("_")} for m, t in table.items()}
    clean_tune = {m: {k: v for k, v in t.items() if not k.startswith("_")} for m, t in tune.items()}
    (args.out / "result.json").write_text(json.dumps({"seconds_per_page": seconds, "test": clean, "tune": clean_tune,
                                                      "pages": [{k: v for k, v in r.items()} for r in rows]},
                                                     ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    report(rows, seconds, table, tune, args.out, args.samples)
    for method, t in clean.items():
        print(f"{method:8s} acc {pct(t['acc'])} exact {pct(t['exact'])} mapped {pct(t['mapped'])} box {pct(t['box_acc'])} "
              f"unsure {pct(t['box_unsure'])} unknown {pct(t['box_unknown'])} levels {t['by_level']} sec {seconds.get(method)}")


if __name__ == "__main__":
    main()
