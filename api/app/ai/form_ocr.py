"""OCR-FORMS: coordinate-based reading of filled-in forms (alignment, per-field crops, checkbox state, label pairing).

Measured in deploy/ocr_forms_eval.py; not wired into the upload pipeline. Needs OpenCV and NumPy (installed with the
optional OCR packages, api/requirements-ocr.txt).
"""
import difflib
import re
import unicodedata

import cv2
import numpy as np

CHECKED_AT = 0.06  # interior ink share at or above this: checked
EMPTY_BELOW = 0.03  # below this: unchecked; in between: ask a person
PUNCTUATION = re.compile(r"[\s:：,，、。;；|｜()（）「」『』\[\]【】*#_~'\"`]+")


def normalize(text):
    """For scoring: full-width to half-width (NFKC), no spaces, no punctuation except . / - used in dates and numbers."""
    return PUNCTUATION.sub("", unicodedata.normalize("NFKC", text or ""))


def _ink(gray, block=31, offset=12):
    """Ink mask that also catches faint pencil: darker than the local background by `offset`."""
    background = cv2.medianBlur(gray, block) if min(gray.shape) > block else np.full_like(gray, int(np.median(gray)))
    return ((background.astype(np.int16) - gray.astype(np.int16)) > offset).astype(np.uint8) * 255


def _gray(image):
    return image if image.ndim == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def _line_mask(ink, horizontal, length):
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(3, int(length)), 1) if horizontal else (1, max(3, int(length))))
    return cv2.morphologyEx(ink, cv2.MORPH_OPEN, kernel)


def _order(points):
    points = np.asarray(points, np.float32).reshape(-1, 2)
    total, diff = points.sum(1), np.diff(points, axis=1).ravel()
    return np.float32([points[total.argmin()], points[diff.argmin()], points[total.argmax()], points[diff.argmax()]])


def align(image, template):
    """Warp a photo or scan onto the template's page by finding the outer border of its printed table.

    Returns (image in template coordinates, ok). When no table border is found, ok is False and the image is only resized.
    """
    width, height = template["size"]
    gray = _gray(image)
    ink = _ink(gray, block=51, offset=25)
    scale = max(gray.shape) / 1000
    # Thicken first: a 2 px border tilted a few degrees in a phone photo drifts off a thin structuring element.
    thick = cv2.dilate(ink, np.ones((3, 3), np.uint8))
    grid = cv2.bitwise_or(_line_mask(thick, True, 35 * scale), _line_mask(thick, False, 35 * scale))
    contours, _ = cv2.findContours(grid, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = [c for c in contours if cv2.contourArea(cv2.convexHull(c)) > 0.05 * gray.size]
    if not contours:
        return cv2.resize(image, (width, height)), False
    hull = cv2.convexHull(max(contours, key=lambda c: cv2.contourArea(cv2.convexHull(c)))).reshape(-1, 2).astype(np.float32)
    total, diff = hull.sum(1), hull[:, 0] - hull[:, 1]
    quad = np.float32([hull[total.argmin()], hull[diff.argmax()], hull[total.argmax()], hull[diff.argmin()]])
    xs = [v for x0, _, x1, _ in template["lines"] for v in (x0, x1)]
    ys = [v for _, y0, _, y1 in template["lines"] for v in (y0, y1)]
    target = np.float32([[min(xs), min(ys)], [max(xs), min(ys)], [max(xs), max(ys)], [min(xs), max(ys)]])
    matrix = cv2.getPerspectiveTransform(quad, target)
    warped = cv2.warpPerspective(image, matrix, (width, height), flags=cv2.INTER_CUBIC, borderValue=(255, 255, 255))
    return warped, True


def crop(image, box, pad=0):
    x0, y0, x1, y1 = (int(round(v)) for v in box)
    h, w = image.shape[:2]
    return image[max(0, y0 - pad):min(h, y1 + pad), max(0, x0 - pad):min(w, x1 + pad)].copy()


def remove_lines(image):
    """Paint printed cell borders white so they are not read as 1, l or 一; handwriting strokes are much shorter."""
    gray = _gray(image)
    ink = _ink(gray, block=31, offset=40)
    h, w = gray.shape
    lines = cv2.bitwise_or(_line_mask(ink, True, max(60, w * 0.35)), _line_mask(ink, False, max(40, h * 0.7)))
    lines = cv2.dilate(lines, np.ones((3, 3), np.uint8))
    out = image.copy()
    out[lines > 0] = 255
    return out


def prepare_field(image, min_height=96):
    """Crop clean-up before recognition: borders removed, light evened out, small crops enlarged."""
    cleaned = remove_lines(image)
    gray = _gray(cleaned)
    background = cv2.medianBlur(gray, 31) if min(gray.shape) > 31 else np.full_like(gray, 255)
    even = np.clip(gray.astype(np.float32) / np.maximum(background.astype(np.float32), 1) * 255, 0, 255).astype(np.uint8)
    if even.shape[0] < min_height:
        factor = min(4.0, min_height / max(1, even.shape[0]))
        even = cv2.resize(even, None, fx=factor, fy=factor, interpolation=cv2.INTER_CUBIC)
    return cv2.cvtColor(even, cv2.COLOR_GRAY2BGR)


def text_lines(image, pad=6):
    """Split a field crop into tight single-line crops (top to bottom) by the rows that carry writing.

    The recognizer reads one tight line far better than its own text detector does on a small, busy crop.
    """
    cleaned = remove_lines(image)
    ink = _ink(_gray(cleaned), block=31, offset=30)
    ink = cv2.morphologyEx(ink, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    rows = (ink > 0).sum(1)
    on = rows > max(2, 0.004 * ink.shape[1])
    bands, start = [], None
    for y, value in enumerate(list(on) + [False]):
        if value and start is None:
            start = y
        elif not value and start is not None:
            bands.append([start, y])
            start = None
    merged = []
    for band in bands:  # rejoin pieces of one line split by a thin gap (e.g. between strokes of 二)
        if merged and band[0] - merged[-1][1] < 12:
            merged[-1][1] = band[1]
        else:
            merged.append(band)
    out = []
    for top, bottom in merged:
        if bottom - top < 10:
            continue
        cols = np.nonzero((ink[top:bottom] > 0).sum(0))[0]
        if len(cols) == 0:
            continue
        out.append(crop(cleaned, [cols[0], top, cols[-1] + 1, bottom], pad=pad))
    return out


def checkbox_state(image, box):
    """('checked' | 'unchecked' | 'unsure', score) from the ink inside the box once its printed border is removed.

    Strokes that start inside the box and leave it (a tick drawn too big or off-centre) count in full; marks that never
    enter the box (a stray line under it, writing beside it) do not.
    """
    x0, y0, x1, y1 = box
    side = max(8, x1 - x0)
    margin = int(side * 0.8)
    region = crop(image, box, pad=margin)
    gray = _gray(region)
    ink = _ink(gray, block=max(15, (side * 4) | 1), offset=18)
    inset = max(3, int(side * 0.12))
    ox, oy = margin + inset, margin + inset
    interior = np.zeros_like(ink)
    interior[oy:oy + side - 2 * inset, ox:ox + side - 2 * inset] = 255
    raw_share = ((interior > 0) & (ink > 0)).sum() / float((side - 2 * inset) ** 2)
    if raw_share >= 0.45:  # filled in: removing "lines" below would erase the fill itself
        return "checked", round(float(raw_share), 4)
    ink = cv2.subtract(ink, cv2.bitwise_or(_line_mask(ink, True, side * 0.9), _line_mask(ink, False, side * 0.9)))
    count, labels = cv2.connectedComponents(ink)
    touching = set(np.unique(labels[(interior > 0) & (ink > 0)])) - {0}
    inside = ((interior > 0) & (ink > 0)).sum()
    attached = np.isin(labels, list(touching)).sum() - inside if touching else 0
    area = float((side - 2 * inset) ** 2)
    score = (inside + 0.5 * attached) / area
    if score >= CHECKED_AT:
        return "checked", round(score, 4)
    if score < EMPTY_BELOW:
        return "unchecked", round(score, 4)
    return "unsure", round(score, 4)


def _is_label(text, label):
    text, label = normalize(text), normalize(label)
    return bool(label) and (text.startswith(label) or difflib.SequenceMatcher(None, text, label).ratio() >= 0.67)


def pair_fields(boxes, labels, stop=()):
    """Template-free key-value pairing: each label's value is the text right of it on the same row, else just below it.

    boxes: [(text, [x0, y0, x1, y1]), ...] from whole-page OCR; labels: {field_id: printed label}; stop: other printed
    words (checkbox captions, titles) that are never values.
    """
    stops = list(labels.values()) + list(stop)
    found = {}
    for field_id, label in labels.items():
        matches = [b for b in boxes if _is_label(b[0], label)]
        if not matches:
            found[field_id] = ""
            continue
        text, (lx0, ly0, lx1, ly1) = max(matches, key=lambda b: difflib.SequenceMatcher(None, normalize(b[0]), normalize(label)).ratio())
        rest = normalize(text)[len(normalize(label)):] if normalize(text).startswith(normalize(label)) else ""
        if rest:
            found[field_id] = rest
            continue
        height = ly1 - ly0
        row = sorted((b for b in boxes if b[1][0] >= lx1 - 5 and abs((b[1][1] + b[1][3]) / 2 - (ly0 + ly1) / 2) < height * 0.8),
                     key=lambda b: b[1][0])
        values = []
        for candidate in row:
            if any(_is_label(candidate[0], word) for word in stops):
                break
            values.append(candidate[0])
        if not values:
            below = sorted((b for b in boxes if ly1 - 5 <= b[1][1] <= ly1 + 3 * height and b[1][2] > lx0 - 20
                            and not any(_is_label(b[0], word) for word in stops)), key=lambda b: (round(b[1][1] / height), b[1][0]))
            values = [b[0] for b in below]
        found[field_id] = normalize("".join(values))
    return found
