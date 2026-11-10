"""Generate fictional Traditional-Chinese handwritten forms with answers for OCR-FORMS (毛研食品 is fictional).

    <eval-python> deploy/ocr-eval/forms/make_forms.py --chars ../output/ocr-forms/datasets/stust --out ../output/ocr-forms/samples

Handwritten characters come from the STUST / AI-FREE-Team Traditional Chinese handwriting set (real people, one
character per 50x50 image, CC BY-SA 4.0). The set has no digits, so digits and '/.-:' are drawn as jittered pen
strokes, like the checkbox marks. Generated images stay outside git; templates/*.json (field and box coordinates on
the clean page) are written by --templates and committed.

Each page gets <name>.jpg and <name>.json: template, split (tune/test), messiness, ink, the true field text, the true
state and mark type of every checkbox, and the warp applied (for debugging only; methods must not read it).
"""
import argparse
import io
import json
import math
from pathlib import Path
import random
import zipfile

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
TEMPLATES = HERE / "templates"
FONT = Path(r"C:\Windows\Fonts\msjh.ttc")
W, H = 1240, 1754  # A4 at 150 dpi
MARKS_CHECKED = {"check", "cross", "fill", "outside", "faint"}
STROKE_CHARS = set("0123456789/.-:一")

# ---------------------------------------------------------------- templates


def _layout(name, title, number, rows):
    """rows: (height, [cell, ...]); cell = ('label', text, width) | ('field', id, type, width) | ('checks', [(id, text)], width)."""
    printed = [{"text": "毛研食品股份有限公司（虛構）", "box": [80, 70, 600, 100], "size": 22},
               {"text": f"表單編號 {number}", "box": [920, 70, 1160, 100], "size": 22},
               {"text": title, "box": [0, 120, W, 175], "size": 40, "center": True}]
    lines, fields, checkboxes = [], [], []
    x0, y, right = 80, 220, 1160
    lines.append([x0, y, right, y])
    for height, cells in rows:
        x = x0
        for cell in cells:
            kind, width = cell[0], cell[-1]
            box = [x, y, x + width, y + height]
            if kind == "label":
                printed.append({"text": cell[1], "box": [x + 14, y, x + width - 8, y + height], "size": 28, "label": True})
            elif kind == "field":
                fields.append({"id": cell[1], "label": _label_before(printed), "type": cell[2], "box": box})
            else:
                bx, by = x + 18, y + 22
                for box_id, text in cell[1]:
                    advance = 34 + 28 * len(text) + 30
                    if bx + advance > x + width:
                        bx, by = x + 18, by + 50
                    checkboxes.append({"id": box_id, "label": text, "group": _label_before(printed),
                                       "box": [bx, by, bx + 26, by + 26]})
                    printed.append({"text": text, "box": [bx + 34, by - 4, bx + 34 + 28 * len(text) + 4, by + 32], "size": 26})
                    bx += advance
            lines.append([x, y, x, y + height])
            x += width
        lines.append([right, y, right, y + height])
        y += height
        lines.append([x0, y, right, y])
    printed.append({"text": "※ 本表單為虛構示範資料。", "box": [80, y + 20, 700, y + 50], "size": 22})
    return {"name": name, "title": title, "size": [W, H], "printed": printed, "lines": lines,
            "fields": fields, "checkboxes": checkboxes}


def _label_before(printed):
    return next(p["text"] for p in reversed(printed) if p.get("label"))


def build_templates():
    lab, val = 170, 370
    equipment = _layout("equipment_loan", "設備借用簽收單", "IT-F-012", [
        (90, [("label", "借用人", lab), ("field", "borrower", "name", val), ("label", "部門", lab), ("field", "dept", "dept", val)]),
        (90, [("label", "借用日期", lab), ("field", "loan_date", "date", val), ("label", "預計歸還", lab), ("field", "due_date", "date", val)]),
        (90, [("label", "聯絡分機", lab), ("field", "extension", "number", val), ("label", "資產編號", lab), ("field", "asset_no", "number", val)]),
        (120, [("label", "借用品項", lab), ("checks", [("item_laptop", "筆記型電腦"), ("item_mouse", "滑鼠"), ("item_adapter", "轉接頭"),
                                                    ("item_projector", "投影機"), ("item_cable", "延長線"), ("item_other", "其他")], 910)]),
        (170, [("label", "用途說明", lab), ("field", "purpose", "text", 910)]),
        (90, [("label", "主管簽核", lab), ("field", "approver", "name", val), ("label", "資訊室點收", lab),
              ("checks", [("received", "已點收"), ("damaged", "有損壞")], val)]),
    ])
    items = ["外箱標示", "封口完整", "重量抽測", "金屬檢測", "溫度紀錄", "異物檢查", "批號噴印", "棧板整齊"]
    quality = _layout("quality_check", "出貨品質檢查表", "QA-F-031", [
        (90, [("label", "檢查日期", lab), ("field", "check_date", "date", val), ("label", "檢查人", lab), ("field", "inspector", "name", val)]),
        (90, [("label", "產線", lab), ("field", "line", "dept", val), ("label", "批號", lab), ("field", "lot", "number", val)]),
        *[(64, [("label", item, 250), ("checks", [(f"q{i}_pass", "合格"), (f"q{i}_fail", "不合格")], 400), ("field", f"q{i}_note", "short", 430)])
          for i, item in enumerate(items, 1)],
        (150, [("label", "異常說明", lab), ("field", "issue", "text", 910)]),
        (90, [("label", "覆核主管", lab), ("field", "reviewer", "name", 910)]),
    ])
    hire = _layout("new_hire", "新人報到資料表", "HR-F-005", [
        (90, [("label", "姓名", lab), ("field", "name", "name", val), ("label", "到職日", lab), ("field", "start_date", "date", val)]),
        (90, [("label", "部門", lab), ("field", "dept", "dept", val), ("label", "分機", lab), ("field", "extension", "number", val)]),
        (120, [("label", "需求設備", lab), ("checks", [("need_laptop", "筆電"), ("need_desktop", "桌機"), ("need_badge", "識別證"),
                                                    ("need_parking", "停車證"), ("need_uniform", "制服")], 910)]),
        (90, [("label", "已完成", lab), ("checks", [("done_signin", "簽到"), ("done_badge", "領識別證"), ("done_training", "教育訓練")], 910)]),
        (90, [("label", "緊急聯絡人", lab), ("field", "contact", "name", val), ("label", "電話", lab), ("field", "phone", "phone", val)]),
        (170, [("label", "備註", lab), ("field", "note", "text", 910)]),
    ])
    return [equipment, quality, hire]


def render_blank(template):
    page = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(page)
    for x0, y0, x1, y1 in template["lines"]:
        draw.line([x0, y0, x1, y1], fill=(30, 30, 30), width=2)
    for item in template["printed"]:
        font = ImageFont.truetype(str(FONT), item["size"])
        x0, y0, x1, y1 = item["box"]
        width = draw.textlength(item["text"], font=font)
        x = (x0 + x1 - width) / 2 if item.get("center") else x0
        draw.text((x, (y0 + y1) / 2), item["text"], fill=(20, 20, 20), font=font, anchor="lm")
    for box in template["checkboxes"]:
        draw.rectangle(box["box"], outline=(20, 20, 20), width=2)
    return page

# ---------------------------------------------------------------- content

SURNAMES = "陳林黃張李王吳劉蔡楊許鄭謝郭洪曾邱廖賴周"
GIVEN = ["冠廷", "志明", "怡君", "雅婷", "家豪", "俊傑", "宗翰", "淑芬", "美玲", "建宏", "佳穎", "信宏", "彥廷", "柏宇", "淑惠", "文雄"]
DEPTS = ["品保課", "資訊室", "業務部", "生產二課", "人事室", "採購課", "倉儲組", "研發部", "包裝線", "客服中心"]
SHORT = ["", "", "", "", "抽三箱", "已補貼", "重印", "待複驗", "偏高", "已處理", "見附件"]
TEXTS = {
    "purpose": ["客戶稽核要帶去現場簡報，可能會延一週", "新人教育訓練使用，結束後歸還", "筆電故障送修期間暫借",
                "外包廠商測試用，請資訊室協助設定", "展覽攤位展示使用，週五下午歸還"],
    "issue": ["第三箱外箱破損，已退回重工", "封口不良兩件，已隔離待確認", "溫度紀錄缺上午一筆，已補記",
              "金屬檢測機誤報一次，複驗正常", "無異常"],
    "note": ["週一上午先到人事室報到", "需要申請停車證，車號另附", "識別證照片已寄出", "教育訓練改到下週三", "無"],
}


def content(kind, rng, field_id=""):
    if kind == "name":
        return rng.choice(SURNAMES) + rng.choice(GIVEN)
    if kind == "dept":
        return rng.choice(DEPTS)
    if kind == "date":
        m, d = rng.randint(1, 12), rng.randint(1, 28)
        return rng.choice([f"115.{m}.{d}", f"2026/{m}/{d}", f"{m}月{d}日", f"115年{m}月{d}日", f"{m}/{d}"])
    if kind == "number":
        return rng.choice([str(rng.randint(100, 9999)), f"{rng.randint(10, 99)}-{rng.randint(100, 999)}", f"{rng.randint(100000, 999999)}"])
    if kind == "phone":
        return f"09{rng.randint(10, 99)}-{rng.randint(100, 999)}-{rng.randint(100, 999)}"
    if kind == "short":
        return rng.choice(SHORT)
    key = next((k for k in TEXTS if k in field_id), "note")
    return rng.choice(TEXTS[key])

# ---------------------------------------------------------------- handwriting


class Glyphs:
    """Character images from the STUST zips, indexed by character; writer index kept so one page can prefer one writer."""

    def __init__(self, folder):
        self.index, self.zips = {}, {}
        for path in sorted(Path(folder).glob("*.zip")):
            archive = zipfile.ZipFile(path)
            self.zips[path.name] = archive
            for name in archive.namelist():
                if name.endswith(".png"):
                    char, number = name.rsplit("/", 1)[-1][:-4].rsplit("_", 1)
                    self.index.setdefault(char, []).append((int(number), path.name, name))

    def has(self, char):
        return char in self.index or char in STROKE_CHARS

    def get(self, char, writer, rng):
        options = self.index[char]
        chosen = next((o for o in options if o[0] == writer), None) or rng.choice(options)
        gray = np.array(Image.open(io.BytesIO(self.zips[chosen[1]].read(chosen[2]))).convert("L"))
        ink = 255 - gray
        ys, xs = np.nonzero(ink > 60)
        if len(xs) == 0:
            return ink
        return ink[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


DIGITS = {  # pen strokes in a unit box (x right, y down)
    "0": [[(.5, 0), (.15, .2), (.1, .6), (.4, 1), (.8, .8), (.9, .35), (.6, 0), (.45, .02)]],
    "1": [[(.3, .2), (.55, 0), (.55, 1)]],
    "2": [[(.1, .25), (.4, 0), (.8, .1), (.8, .4), (.1, 1), (.9, 1)]],
    "3": [[(.15, .1), (.5, 0), (.8, .2), (.45, .48), (.85, .7), (.5, 1), (.1, .9)]],
    "4": [[(.65, 1), (.65, 0), (.05, .7), (.95, .7)]],
    "5": [[(.85, 0), (.2, 0), (.15, .45), (.6, .4), (.85, .7), (.5, 1), (.1, .9)]],
    "6": [[(.75, 0), (.3, .3), (.12, .7), (.4, 1), (.8, .8), (.7, .5), (.2, .6)]],
    "7": [[(.1, 0), (.9, 0), (.4, 1)]],
    "8": [[(.5, .48), (.15, .25), (.5, 0), (.85, .25), (.5, .48), (.1, .75), (.5, 1), (.9, .75), (.5, .48)]],
    "9": [[(.85, .35), (.5, .5), (.15, .3), (.5, 0), (.85, .3), (.75, 1)]],
    "/": [[(.85, 0), (.15, 1)]],
    ".": [[(.45, .9), (.55, .95), (.5, 1)]],
    "-": [[(.15, .55), (.85, .5)]],
    ":": [[(.5, .3), (.52, .35)], [(.5, .8), (.52, .85)]],
    "一": [[(.05, .55), (.5, .48), (.95, .5)]],
}


def smooth(points, steps=6):
    """Catmull-Rom through the points so pen strokes curve like handwriting."""
    if len(points) < 3:
        return points
    padded = [points[0]] + points + [points[-1]]
    out = []
    for i in range(1, len(padded) - 2):
        p0, p1, p2, p3 = (np.array(p, float) for p in padded[i - 1:i + 3])
        for t in np.linspace(0, 1, steps, endpoint=False):
            out.append(tuple(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                                    + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3)))
    out.append(points[-1])
    return out


def pen(canvas, strokes, rng, jitter, width):
    draw = ImageDraw.Draw(canvas)
    for stroke in strokes:
        pts = [(x + rng.gauss(0, jitter), y + rng.gauss(0, jitter)) for x, y in stroke]
        draw.line(smooth(pts), fill=255, width=width, joint="curve")


def stroke_glyph(char, size, rng, messy):
    w = int(size * (0.62 if char not in ".:" else 0.3) if char != "一" else size)
    canvas = Image.new("L", (w + 8, size + 8), 0)
    strokes = [[(4 + x * w, 4 + y * size) for x, y in stroke] for stroke in DIGITS[char]]
    pen(canvas, strokes, rng, jitter=size * (0.02 + 0.05 * messy), width=max(2, size // 14))
    return np.array(canvas)


LEVELS = {"neat": 0.0, "normal": 0.5, "messy": 1.0}


def write_line(page_ink, text, box, glyphs, writer, rng, level, size):
    """Draw text into page_ink (uint8 ink mask) starting inside box; returns the drawn ink bounding box."""
    messy = LEVELS[level]
    x0, y0, x1, y1 = box
    x = x0 + rng.uniform(10, 30)
    base = (y0 + y1) / 2 + size * 0.45 + rng.uniform(-6, 6) * (1 + messy)
    slope = math.tan(math.radians(rng.uniform(-1.5, 1.5) * (1 + 3 * messy)))
    start = x
    for char in text:
        if char == " ":
            x += size * 0.4
            continue
        scale = size * (1 + rng.uniform(-1, 1) * (0.05 + 0.2 * messy))
        if char in STROKE_CHARS:
            glyph = stroke_glyph(char, int(scale * (0.8 if char not in "一" else 1)), rng, messy)
        else:
            raw = glyphs.get(char, writer, rng)
            ratio = scale / max(raw.shape)
            glyph = cv2.resize(raw, (max(1, int(raw.shape[1] * ratio)), max(1, int(raw.shape[0] * ratio))), interpolation=cv2.INTER_CUBIC)
        angle = rng.uniform(-1, 1) * (3 + 10 * messy)
        shear = rng.uniform(-1, 1) * (0.05 + 0.3 * messy)
        h, w = glyph.shape
        pad = int(max(h, w) * 0.4) + 4
        glyph = cv2.copyMakeBorder(glyph, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=0)
        center = (glyph.shape[1] / 2, glyph.shape[0] / 2)
        matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        matrix[0, 1] += shear
        matrix[0, 2] -= shear * center[1]
        glyph = cv2.warpAffine(glyph, matrix, (glyph.shape[1], glyph.shape[0]))
        if messy > 0.6 and rng.random() < 0.4:
            glyph = cv2.dilate(glyph, np.ones((2, 2), np.uint8))
        y_char = base + slope * (x - start) - h - pad + rng.gauss(0, 1 + 4 * messy)
        _paste_ink(page_ink, glyph, int(x - pad), int(y_char))
        x += w * (1 + rng.uniform(-0.1, 0.12) - 0.25 * messy * rng.random()) + 2
    return x


def _paste_ink(page_ink, glyph, x, y):
    h, w = glyph.shape
    ys, xs = max(0, y), max(0, x)
    ye, xe = min(page_ink.shape[0], y + h), min(page_ink.shape[1], x + w)
    if ye <= ys or xe <= xs:
        return
    region = glyph[ys - y:ye - y, xs - x:xe - x]
    np.maximum(page_ink[ys:ye, xs:xe], region, out=page_ink[ys:ye, xs:xe])


def write_field(page_ink, text, field, glyphs, writer, rng, level):
    x0, y0, x1, y1 = field["box"]
    height = y1 - y0
    size = int(min(54, height * 0.55) * rng.uniform(0.85, 1.05))
    if field["type"] != "text":
        write_line(page_ink, text, field["box"], glyphs, writer, rng, level, size)
        return
    size = int(rng.uniform(40, 50))
    per_line = max(4, int((x1 - x0 - 40) / (size * 1.05)))
    lines = [text[i:i + per_line] for i in range(0, len(text), per_line)]
    line_h = (height - 10) / max(2, len(lines))
    for k, line in enumerate(lines):
        write_line(page_ink, line, [x0, y0 + k * line_h, x1, y0 + (k + 1) * line_h], glyphs, writer, rng, level, size)

# ---------------------------------------------------------------- checkbox marks


def draw_mark(page_ink, box, mark, rng, messy):
    x0, y0, x1, y1 = box
    s = x1 - x0
    canvas = Image.new("L", (s * 4, s * 4), 0)
    o = s * 1.5  # box sits at (o, o)..(o+s, o+s) on the canvas
    jitter, width = s * 0.04, rng.choice([3, 4, 5])
    if mark in ("check", "faint"):
        pen(canvas, [[(o + .1 * s, o + .5 * s), (o + .4 * s, o + .9 * s), (o + 1.2 * s, o - .3 * s)]], rng, jitter, width if mark == "check" else 2)
    elif mark == "outside":
        dx, dy = rng.choice([(.55, -.55), (.6, .1), (-.4, -.5)])
        pen(canvas, [[(o + (.1 + dx) * s, o + (.5 + dy) * s), (o + (.4 + dx) * s, o + (.9 + dy) * s), (o + (1.2 + dx) * s, o + (-.3 + dy) * s)]], rng, jitter, width)
    elif mark == "cross":
        pen(canvas, [[(o + .1 * s, o + .1 * s), (o + .9 * s, o + .9 * s)], [(o + .9 * s, o + .1 * s), (o + .1 * s, o + .9 * s)]], rng, jitter, width)
    elif mark == "fill":
        rows = [[(o + .1 * s, o + (k / 8) * s), (o + .9 * s, o + (k / 8 + .06) * s)] for k in range(1, 8)]
        pen(canvas, rows, rng, jitter, width + 1)
    elif mark == "stray":
        side = rng.choice(["right", "below", "dot"])
        if side == "right":
            pen(canvas, [[(o + 1.4 * s, o + .2 * s), (o + 1.8 * s, o + .8 * s)]], rng, jitter, 2)
        elif side == "below":
            pen(canvas, [[(o - .2 * s, o + 1.35 * s), (o + 1.2 * s, o + 1.3 * s)]], rng, jitter, 2)
        else:
            pen(canvas, [[(o + .45 * s, o + .45 * s), (o + .5 * s, o + .5 * s)]], rng, 0, 3)
    if mark == "empty":
        return
    ink = np.array(canvas)
    if mark == "faint":
        ink = (ink * 0.45).astype(np.uint8)
    angle = rng.uniform(-10, 10) * (1 + messy)
    matrix = cv2.getRotationMatrix2D((o + s / 2, o + s / 2), angle, 1.0)
    ink = cv2.warpAffine(ink, matrix, (ink.shape[1], ink.shape[0]))
    _paste_ink(page_ink, ink, int(x0 - o), int(y0 - o))


def choose_marks(template, rng):
    marks = {}
    if template["name"] == "quality_check":
        rows = sorted({b["id"].split("_")[0] for b in template["checkboxes"]})
        for row in rows:
            chosen = rng.choices(["pass", "fail", "none"], [0.75, 0.18, 0.07])[0]
            for side in ("pass", "fail"):
                if side == chosen:
                    marks[f"{row}_{side}"] = rng.choices(["check", "cross", "fill", "outside", "faint"], [45, 15, 10, 20, 10])[0]
                else:
                    marks[f"{row}_{side}"] = rng.choices(["empty", "stray"], [80, 20])[0]
        return marks
    for box in template["checkboxes"]:
        marks[box["id"]] = rng.choices(["check", "cross", "fill", "outside", "faint", "empty", "stray"],
                                       [28, 10, 8, 10, 8, 26, 10])[0]
    return marks

# ---------------------------------------------------------------- photo degradation


def degrade(image, rng, messy):
    """Phone-photo look: perspective, rotation, uneven light, blur, noise, JPEG. Returns (BGR image, 3x3 matrix)."""
    src = np.float32([[0, 0], [W, 0], [W, H], [0, H]])
    amount = 0.015 + 0.03 * messy
    dst = np.float32([[x + rng.uniform(-amount, amount) * W, y + rng.uniform(-amount, amount) * H] for x, y in src])
    out_w, out_h = int(W * 1.08), int(H * 1.08)
    dst += np.float32([W * 0.04, H * 0.04])
    matrix = cv2.getPerspectiveTransform(src, dst)
    paper = rng.randint(215, 245)
    warped = cv2.warpPerspective(np.array(image)[:, :, ::-1], matrix, (out_w, out_h), borderValue=(paper - 70, paper - 60, paper - 50))
    yy, xx = np.mgrid[0:out_h, 0:out_w].astype(np.float32)
    angle = rng.uniform(0, 2 * math.pi)
    shade = (np.cos(angle) * xx / out_w + np.sin(angle) * yy / out_h)
    shade = 1 - (0.15 + 0.25 * messy) * (shade - shade.min()) / (np.ptp(shade) + 1e-6)
    warped = np.clip(warped.astype(np.float32) * shade[..., None] * (paper / 255), 0, 255)
    warped += np.random.default_rng(rng.randint(0, 10 ** 9)).normal(0, 3 + 4 * messy, warped.shape)
    warped = np.clip(warped, 0, 255).astype(np.uint8)
    blur = rng.choice([1, 3, 3, 5]) if messy > 0.4 else rng.choice([1, 1, 3])
    if blur > 1:
        warped = cv2.GaussianBlur(warped, (blur, blur), 0)
    scale = rng.uniform(0.55, 0.8) if messy > 0.4 else rng.uniform(0.7, 0.9)
    warped = cv2.resize(warped, (int(out_w * scale), int(out_h * scale)), interpolation=cv2.INTER_AREA)
    matrix = np.diag([scale, scale, 1.0]) @ matrix
    ok, encoded = cv2.imencode(".jpg", warped, [cv2.IMWRITE_JPEG_QUALITY, rng.randint(45, 80)])
    return cv2.imdecode(encoded, cv2.IMREAD_COLOR), matrix

# ---------------------------------------------------------------- pages

INKS = {"blue": (35, 60, 150), "black": (25, 25, 30)}
PLAN = [  # (template, split, count): new_hire is held out of the tune split entirely
    ("equipment_loan", "tune", 7), ("quality_check", "tune", 8),
    ("equipment_loan", "test", 7), ("quality_check", "test", 8), ("new_hire", "test", 10),
]


def make_page(template, glyphs, rng, level, ink_name):
    writer = rng.randint(0, 50)
    ink = np.zeros((H, W), np.uint8)
    answers = {}
    for field in template["fields"]:
        for _ in range(20):
            text = content(field["type"], rng, field["id"])
            if all(glyphs.has(c) or c == " " for c in text):
                break
        answers[field["id"]] = text
        if text:
            write_field(ink, text, field, glyphs, writer, rng, level)
    marks = choose_marks(template, rng)
    for box in template["checkboxes"]:
        draw_mark(ink, box["box"], marks[box["id"]], rng, LEVELS[level])
    page = np.array(render_blank(template)).astype(np.float32)
    alpha = (ink.astype(np.float32) / 255)[..., None]
    page = page * (1 - alpha) + np.array(INKS[ink_name], np.float32) * alpha
    image, matrix = degrade(Image.fromarray(page.astype(np.uint8)), rng, LEVELS[level])
    truth = {"template": template["name"], "level": level, "ink": ink_name, "fields": answers,
             "checkboxes": {k: {"checked": v in MARKS_CHECKED, "mark": v} for k, v in marks.items()},
             "warp": matrix.tolist()}
    return image, truth


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chars", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20261110)
    parser.add_argument("--templates", action="store_true", help="also rewrite templates/*.json")
    args = parser.parse_args()
    templates = {t["name"]: t for t in build_templates()}
    if args.templates:
        TEMPLATES.mkdir(exist_ok=True)
        for name, template in templates.items():
            (TEMPLATES / f"{name}.json").write_text(json.dumps(template, ensure_ascii=False, indent=1), encoding="utf-8")
    glyphs = Glyphs(args.chars)
    rng = random.Random(args.seed)
    args.out.mkdir(parents=True, exist_ok=True)
    for name, split, count in PLAN:
        for k in range(count):
            level = ["neat", "normal", "messy"][k % 3]
            image, truth = make_page(templates[name], glyphs, rng, level, rng.choice(list(INKS)))
            stem = f"{split}-{name}-{k + 1:02d}-{level}"
            cv2.imwrite(str(args.out / f"{stem}.jpg"), image)
            (args.out / f"{stem}.json").write_text(json.dumps({"split": split, **truth}, ensure_ascii=False, indent=1), encoding="utf-8")
            render_blank(templates[name]).save(args.out.parent / f"blank-{name}.png") if k == 0 else None
    print(f"pages written to {args.out}")


if __name__ == "__main__":
    main()
