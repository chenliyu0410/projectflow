"""Local OCR for isolated previews: RapidOCR with the Traditional Chinese recognition model.

The OCR packages are optional (api/requirements-ocr.txt) and are imported only when OCR is enabled.
"""
import io
import os
from pathlib import Path
import re
import threading

MODEL = "chinese_cht_PP-OCRv3_rec_mobile.onnx"
KEYS = "chinese_cht_dict.txt"
MIN_LINE = 0.5
MIN_AVERAGE = 0.6
MAX_PIXELS = 40_000_000
MIN_WIDTH = 1000
PREPROCESS = True
HEADER = "（OCR 辨識文字，可能有錯字；請以原檔核對）"
_engines = {}
_load_lock = threading.Lock()
_run_lock = threading.Lock()


class OCRError(ValueError):
    pass


def model_dir():
    if os.environ.get("PF_ACCEPTANCE_MODE") != "true":
        return None
    value = os.environ.get("PF_AI_OCR_MODEL_DIR", "").strip()
    if not value:
        return None
    path = Path(value)
    return path if (path / MODEL).is_file() and (path / KEYS).is_file() else None


def enabled():
    return model_dir() is not None


def identity():
    """Changes when OCR is switched on or off or the model file changes, so sources are re-parsed."""
    path = model_dir()
    if path is None:
        return "off"
    stat = (path / MODEL).stat()
    return f"rapidocr-1.4.4:{MODEL}:{stat.st_size}:{stat.st_mtime_ns}"


def engine():
    path = model_dir()
    if path is None:
        raise OCRError("OCR未啟用")
    with _load_lock:
        if str(path) not in _engines:
            try:
                from rapidocr_onnxruntime import RapidOCR
            except ImportError:
                raise OCRError("OCR套件未安裝（api/requirements-ocr.lock）") from None
            _engines[str(path)] = RapidOCR(rec_model_path=str(path / MODEL), rec_keys_path=str(path / KEYS))
        return _engines[str(path)]


def preprocess(image):
    """Grayscale, stretch contrast and upscale small scans so faint or tiny text reaches the model."""
    from PIL import ImageOps
    gray = ImageOps.autocontrast(ImageOps.grayscale(image), cutoff=1)
    if gray.width < MIN_WIDTH:
        gray = gray.resize((MIN_WIDTH, round(gray.height * MIN_WIDTH / gray.width)))
    return gray.convert("RGB")


def normalize(text):
    # The model reads a full-width comma between Chinese characters as a middle dot.
    return re.sub(r"(?<=[一-鿿])[·•](?=[一-鿿])", "，", text).strip()


def recognize(data):
    """Return [(text, confidence)] for one encoded image; the size is checked before decoding."""
    try:
        from PIL import Image
    except ImportError:
        raise OCRError("OCR套件未安裝（api/requirements-ocr.lock）") from None
    try:
        with Image.open(io.BytesIO(data)) as image:
            width, height = image.size
            if width * height > MAX_PIXELS:
                raise OCRError("影像超過4000萬像素，請縮小後再上傳")
            buffer = io.BytesIO()
            (preprocess(image) if PREPROCESS else image.convert("RGB")).save(buffer, "PNG")
    except OCRError:
        raise
    except Exception:
        raise OCRError("影像無法解析") from None
    with _run_lock:
        result, _ = engine()(buffer.getvalue())
    return [(normalize(text), float(score)) for _, text, score in result or [] if normalize(text)]


def lines_text(lines):
    """Keep confident lines; return (text, average confidence of kept lines)."""
    kept = [(text, score) for text, score in lines if score >= MIN_LINE]
    if not kept:
        return "", 0.0
    return "\n".join(text for text, _ in kept), sum(score for _, score in kept) / len(kept)
