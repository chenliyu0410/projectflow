"""OCR-FORMS set B: 10 real Chinese forms from XFUND zh.val (Simplified, values mostly typed) as a real-layout check.

    <eval-python> deploy/ocr-eval/forms/xfund_eval.py --xfund ../output/ocr-forms/datasets/xfund --out ../output/ocr-forms/results-xfund \
        [--ovis-python ... --ovis-model ...]

Each question->answer link in the annotation is one field. RapidOCR uses its bundled Chinese model here (it reads Simplified;
the Traditional model would turn a script mismatch into errors). Both answer and output go through OpenCC s2t before scoring.
  P0       whole page, values paired to question labels by position
  P1       answer box cropped by its annotated coordinates, split into lines, recognizer only
  P2-page  OvisOCR2 whole page, values paired from its table/markdown output
  P2       OvisOCR2 on the same answer crops
"""
import argparse
import json
from pathlib import Path
import sys

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "api"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import ocr_forms_eval as ev  # noqa: E402
from app.ai import form_ocr, ocr  # noqa: E402


def fields_of(document):
    by_id = {e["id"]: e for e in document["document"]}
    fields = []
    for entity in document["document"]:
        if entity["label"] != "question":
            continue
        answers = [by_id[a] for q, a in entity["linking"] if q == entity["id"] and a in by_id and by_id[a]["label"] == "answer"]
        answers.sort(key=lambda a: (a["box"][1] // 30, a["box"][0]))
        text = "".join(a["text"] for a in answers)
        if form_ocr.normalize(text) and form_ocr.normalize(entity["text"]):
            fields.append({"id": str(entity["id"]), "label": entity["text"].rstrip(":：").strip(), "truth": text,
                           "boxes": [a["box"] for a in answers]})
    return fields


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--xfund", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--pages", type=int, default=10)
    parser.add_argument("--ovis-python", type=Path)
    parser.add_argument("--ovis-model", type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    from rapidocr_onnxruntime import RapidOCR
    bundled = RapidOCR()
    ocr.engine = lambda: bundled  # bundled Chinese (Simplified-capable) model for this set only
    documents = json.loads((args.xfund / "zh.val.json").read_text(encoding="utf-8"))["documents"][:args.pages]
    rows, crops = [], []
    for document in documents:
        path = args.xfund / "images" / document["img"]["fname"]
        image = cv2.imread(str(path))
        fields = fields_of(document)
        labels = {f["id"]: f["label"] for f in fields}
        boxes = [(t, b) for t, b in ev.rapid(image)]
        p0 = form_ocr.pair_fields(boxes, labels)
        p1 = {}
        for field in fields:
            pieces = []
            for k, box in enumerate(field["boxes"]):
                piece = form_ocr.crop(image, box, pad=6)
                name = args.out / "crops" / f"{path.stem}-{field['id']}-{k}.png"
                name.parent.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(name), piece)
                crops.append(name)
                pieces.append(ev.read_field(piece))
            p1[field["id"]] = "".join(pieces)
        rows.append({"page": path.stem, "path": str(path), "fields": fields, "pred": {"P0": p0, "P1": p1}})
        print(path.stem, len(fields), "fields", flush=True)
    args.out_dir = args.out
    ovis_pages = ev.run_ovis(argparse.Namespace(out=args.out, ovis_python=args.ovis_python, ovis_model=args.ovis_model),
                             [Path(r["path"]) for r in rows], "page", "page")
    ovis_crops = ev.run_ovis(argparse.Namespace(out=args.out, ovis_python=args.ovis_python, ovis_model=args.ovis_model),
                             crops, "field", "fields")
    for row in rows:
        if ovis_pages:
            labels = {f["id"]: f["label"] for f in row["fields"]}
            row["pred"]["P2-page"] = form_ocr.pair_fields(ev.html_table_boxes(ovis_pages.get(row["path"], {}).get("text", "")), labels)
            row["pred"]["P2"] = {f["id"]: "".join(ovis_crops.get(str(args.out / "crops" / f"{row['page']}-{f['id']}-{k}.png"), {}).get("text", "")
                                              for k in range(len(f["boxes"]))) for f in row["fields"]}
    summary = {}
    for method in ("P0", "P1", "P2-page", "P2"):
        scores = [ev.score_text(f["truth"], r["pred"][method].get(f["id"], "")) for r in rows if method in r["pred"] for f in r["fields"]]
        if scores:
            summary[method] = {"fields": len(scores), "acc": round(float(np.mean([s["acc"] for s in scores])), 4),
                               "exact": round(float(np.mean([s["exact"] for s in scores])), 4),
                               "mapped": round(float(np.mean([s["mapped"] for s in scores])), 4)}
    (args.out / "result.json").write_text(json.dumps({"summary": summary, "pages": rows}, ensure_ascii=False, indent=1), encoding="utf-8")
    for method, s in summary.items():
        print(f"{method:8s} fields {s['fields']} acc {s['acc']:.1%} exact {s['exact']:.1%} mapped {s['mapped']:.1%}")


if __name__ == "__main__":
    main()
