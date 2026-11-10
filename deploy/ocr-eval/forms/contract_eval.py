"""OCR-FORMS set C: the user's real handwritten lease pages (redacted copies only), run once after parameters are frozen.

    <eval-python> deploy/ocr-eval/forms/contract_eval.py --truth ../output/ocr-forms/contract/truth.json --out ../output/ocr-forms/results-contract \
        --models ... [--ovis-python ... --ovis-model ...]

truth.json (kept outside git): per page the redacted image, field boxes with hand-transcribed answers, checkbox boxes with
their true state. No blank copy of the contract exists, so positions were marked on the photo itself and alignment is
skipped: the coordinate methods get exact positions here, which the report states.
Whole-page methods (P0, P2-page) are scored generously: each answer is matched to the most similar stretch of the page
text, so they are not penalised for not knowing where a value belongs.
"""
import argparse
import json
import os
from pathlib import Path
import sys

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "api"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import ocr_forms_eval as ev  # noqa: E402
from app.ai import form_ocr, ocr_metrics  # noqa: E402


def best_stretch(truth, page_text):
    """Most similar stretch of the page text to the answer (length within ±2 characters)."""
    t, p = form_ocr.normalize(truth), form_ocr.normalize(ev.to_traditional(page_text))
    best, best_acc = "", -1.0
    for size in range(max(1, len(t) - 2), len(t) + 3):
        for start in range(0, max(1, len(p) - size + 1)):
            piece = p[start:start + size]
            acc = ocr_metrics.accuracy(t, piece)
            if acc > best_acc:
                best, best_acc = piece, acc
    return best


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--truth", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--models", type=Path, required=True)
    parser.add_argument("--ovis-python", type=Path)
    parser.add_argument("--ovis-model", type=Path)
    args = parser.parse_args()
    os.environ["PF_AI_OCR"] = "true"
    os.environ["PF_AI_OCR_MODEL_DIR"] = str(args.models.resolve())
    args.out.mkdir(parents=True, exist_ok=True)
    pages = json.loads(args.truth.read_text(encoding="utf-8"))
    rows, field_crops, box_crops = {}, [], []
    for key, page in pages.items():
        image = cv2.imread(str(args.truth.parent / page["image"]))
        page_text = ev.reading_order(ev.page_boxes(image, "current"))
        row = {"page_text_P0": page_text, "fields": {}, "boxes": {}}
        for field in page["fields"]:
            piece = form_ocr.crop(image, field["box"])
            name = args.out / "crops" / f"{key}-field-{field['id']}.png"
            name.parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(name), piece)
            field_crops.append(name)
            row["fields"][field["id"]] = {"truth": field["truth"], "P0": best_stretch(field["truth"], page_text),
                                          "P1": form_ocr.normalize(ev.read_field(piece)), "crop": str(name)}
        for box in page["checkboxes"]:
            name = args.out / "crops" / f"{key}-box-{box['id']}.png"
            cv2.imwrite(str(name), form_ocr.crop(image, box["box"], pad=14))
            box_crops.append(name)
            state, score = form_ocr.checkbox_state(image, box["box"])
            row["boxes"][box["id"]] = {"truth": box["checked"], "caption": box["caption"], "P0": "unknown", "P1": state,
                                       "P1_score": score, "crop": str(name)}
        rows[key] = row
    ovis = argparse.Namespace(out=args.out, ovis_python=args.ovis_python, ovis_model=args.ovis_model)
    ovis_pages = ev.run_ovis(ovis, [args.truth.parent / p["image"] for p in pages.values()], "page", "page")
    ovis_fields = ev.run_ovis(ovis, field_crops, "field", "fields")
    ovis_boxes = ev.run_ovis(ovis, box_crops, "checkbox", "boxes")
    for key, row in rows.items():
        if not ovis_pages:
            break
        text = ovis_pages.get(str(args.truth.parent / pages[key]["image"]), {}).get("text", "")
        row["page_text_P2"] = text
        for field in row["fields"].values():
            field["P2-page"] = best_stretch(field["truth"], text)
            field["P2"] = form_ocr.normalize(ovis_fields.get(field["crop"], {}).get("text", ""))
        for box_id, box in row["boxes"].items():
            answer = ovis_boxes.get(box["crop"], {}).get("text", "").lower()
            box["P2"] = "checked" if answer.startswith("yes") else "unchecked" if answer.startswith("no") else "unsure"
            # Whole-page output: a box symbol written right before the caption printed beside the box (全部, 有, 其 ...).
            hit = [s for s in ev.CHECK_SYMBOLS if f"{s}{box['caption']}" in text.replace(" ", "")]
            box["P2-page"] = ("checked" if ev.CHECK_SYMBOLS[hit[0]] else "unchecked") if hit else "unknown"
    summary = {}
    for method in ("P0", "P1", "P2-page", "P2"):
        fields = [ev.score_text(f["truth"], f[method]) for r in rows.values() for f in r["fields"].values() if method in f]
        boxes = [b for r in rows.values() for b in r["boxes"].values() if method in b]
        if not fields:
            continue
        summary[method] = {
            "fields": len(fields), "acc": round(float(np.mean([s["acc"] for s in fields])), 4),
            "exact": round(float(np.mean([s["exact"] for s in fields])), 4),
            "boxes": len(boxes),
            "box_correct": sum(b[method] == ("checked" if b["truth"] else "unchecked") for b in boxes),
            "box_unsure": sum(b[method] == "unsure" for b in boxes),
            "box_unknown": sum(b[method] == "unknown" for b in boxes),
        }
    (args.out / "result.json").write_text(json.dumps({"summary": summary, "pages": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
    for method, s in summary.items():
        print(f"{method:8s} fields {s['fields']} acc {s['acc']:.1%} exact {s['exact']:.1%} | boxes {s['box_correct']}/{s['boxes']} correct, "
              f"{s['box_unsure']} unsure, {s['box_unknown']} unknown")


if __name__ == "__main__":
    main()
