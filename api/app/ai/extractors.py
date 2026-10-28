"""Bounded text extraction; never runs Office programs or follows external links."""
import io
from pathlib import Path
import zipfile
from xml.etree import ElementTree as ET

from pypdf import PdfReader

from app.ai import ocr

MAX_TEXT = 200_000
IMAGES = {".png", ".jpg", ".jpeg"}
MAX_IMAGES_PER_PAGE = 10
MAX_OCR_IMAGES = 60  # Per file: bounds how long one large or hostile PDF can hold the index lock.
MAX_BYTES = 10_000_000


class ExtractionError(ValueError):
    pass


def checked(text):
    if len(text) > MAX_TEXT:
        raise ExtractionError("文字超過20萬字，請拆成較小文件")
    if not text.strip():
        raise ExtractionError("無可索引文字；圖片或掃描文件需OCR")
    return text.strip()


def extract(data, filename):
    return extract_document(data, filename)[0]


def ocr_result(lines, pages=None, dropped=0):
    """Turn OCR lines into marked text plus an index note; low overall confidence is skipped."""
    text, average = ocr.lines_text(lines)
    if not text:
        raise ExtractionError("OCR沒有辨識到可用文字")
    if average < ocr.MIN_AVERAGE:
        raise ExtractionError(f"OCR信心不足（平均{average:.2f}），請提供較清楚的檔案")
    where = f"，{pages}頁" if pages else ""
    extra = f"；{dropped}頁影像無法可靠辨識，未採用" if dropped else ""
    return f"OCR辨識{where}，平均信心{average:.2f}{extra}"


def ocr_page(page, budget):
    """OCR one scanned page; returns its kept lines, or [] when the page is unreadable or the budget is spent."""
    lines = []
    for image in page.images[:MAX_IMAGES_PER_PAGE]:  # Sliced lazily: unused images are never decoded.
        if budget[0] <= 0:
            break
        budget[0] -= 1
        try:
            lines += ocr.recognize(image.data)
        except ocr.OCRError:
            continue  # One bad image (too large, undecodable) only costs that image.
    text, average = ocr.lines_text(lines)
    return [(t, s) for t, s in lines if s >= ocr.MIN_LINE] if text and average >= ocr.MIN_AVERAGE else ([] if not lines else None)


def extract_document(data, filename):
    """Return (text, note); note says how the text was obtained when it is not a plain text layer."""
    extension = Path(filename).suffix.lower()
    if extension not in {".txt", ".csv", ".pdf", ".docx", ".xlsx"} and not (extension in IMAGES and ocr.enabled()):
        raise ExtractionError("不支援此格式；圖片、掃描文件需OCR")
    if not data or len(data) > MAX_BYTES:
        raise ExtractionError("檔案為空或超過10MB")
    try:
        if extension in {".txt", ".csv"}:
            return checked(data.decode("utf-8-sig")), ""
        if extension in IMAGES:
            lines = ocr.recognize(data)
            note = ocr_result(lines)
            return checked(ocr.HEADER + "\n" + ocr.lines_text(lines)[0]), note
        if extension == ".pdf":
            reader = PdfReader(io.BytesIO(data))
            if reader.is_encrypted or len(reader.pages) > 30:
                raise ExtractionError("PDF加密或超過30頁")
            pages, ocr_lines, ocr_pages, dropped, budget = [], [], 0, 0, [MAX_OCR_IMAGES]
            for number, page in enumerate(reader.pages, 1):
                text = page.extract_text() or ""
                # A page with (almost) no text layer is a scan: read the images placed on it. Each page is
                # judged alone, so a blurry logo page never makes an otherwise good document unindexable.
                if len(text.strip()) < 10 and ocr.enabled():
                    lines = ocr_page(page, budget)
                    if lines:
                        ocr_pages += 1
                        ocr_lines += lines
                        text = "\n".join(t for t, _ in lines)
                    elif lines is None:
                        dropped += 1
                if text.strip():
                    pages.append(f"第{number}頁\n{text}")
                if sum(map(len, pages)) > MAX_TEXT:
                    raise ExtractionError("文字超過20萬字，請拆成較小文件")
            if ocr_pages:
                note = ocr_result(ocr_lines, ocr_pages, dropped)
                return checked(ocr.HEADER + "\n" + "\n\n".join(pages)), note
            if dropped and not "".join(pages).strip():
                raise ExtractionError("掃描頁OCR信心不足，請提供較清楚的檔案")
            return checked("\n\n".join(pages)), ("" if not dropped else f"{dropped}頁掃描影像無法可靠辨識，未採用")
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            if len(entries) > 1000 or sum(e.file_size for e in entries) > 12_000_000:
                raise ExtractionError("Office解壓後內容過大")
            if len({e.filename for e in entries}) != len(entries):
                raise ExtractionError("Office內部檔名重複")

            def xml(name):
                item = archive.getinfo(name)
                if item.file_size > 4_000_000 or item.flag_bits & 1:
                    raise ExtractionError("Office XML過大或加密")
                with archive.open(item) as stream:
                    value = stream.read(4_000_001)
                if len(value) > 4_000_000 or b"\x00" in value or b"<!DOCTYPE" in value.upper() or b"<!ENTITY" in value.upper():
                    raise ExtractionError("不允許XML宣告或內容過大")
                return ET.fromstring(value)

            if extension == ".docx":
                ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
                body = xml("word/document.xml")
                return checked("\n".join("".join(p.itertext()) for p in body.findall(".//w:p", ns))), ""
            ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
            names = {e.filename for e in entries}
            shared = []
            if "xl/sharedStrings.xml" in names:
                shared = ["".join(t.text or "" for t in item.findall(".//s:t", ns))
                          for item in xml("xl/sharedStrings.xml").findall("s:si", ns)]
            sheets = sorted(n for n in names if n.startswith("xl/worksheets/") and n.endswith(".xml") and n.count("/") == 2)
            output = []
            text_length = 0

            def reserve(length):
                nonlocal text_length
                if text_length + length > MAX_TEXT:
                    raise ExtractionError("文字超過20萬字，請拆成較小文件")
                text_length += length

            for name in sheets:
                header = f"工作表：{Path(name).stem}（儲存值；公式不重新計算）"
                reserve(len(header) + (1 if output else 0))
                output.append(header)
                for row in xml(name).findall(".//s:sheetData/s:row", ns):
                    cells = []
                    for cell in row.findall("s:c", ns):
                        value = cell.findtext("s:v", "", ns)
                        if cell.get("t") == "s":
                            index = int(value)
                            if not 0 <= index < len(shared):
                                raise ExtractionError("Excel共用字串索引無效")
                            value = shared[index]
                        elif cell.get("t") == "inlineStr":
                            value = "".join(t.text or "" for t in cell.findall(".//s:t", ns))
                        formula = cell.findtext("s:f", None, ns)
                        coordinate = cell.get("r", "?")
                        if formula is not None:
                            value_length = len("公式=；儲存值=") + len(formula) + len(value or "無")
                        else:
                            value_length = len(value)
                        if value or formula is not None:
                            # Account for the row newline or cell separator before
                            # copying shared strings into rendered cell text.
                            reserve((3 if cells else 1) + len(coordinate) + 1 + value_length)
                        if formula is not None:
                            value = f"公式={formula}；儲存值={value or '無'}"
                        if value:
                            cells.append(f"{coordinate}={value}")
                    if cells:
                        output.append(" | ".join(cells))
            # Empty worksheets are not counted as successfully extracted content.
            if not any("=" in line for line in output):
                raise ExtractionError("Excel沒有可索引的儲存格內容")
            return checked("\n".join(output)), ""
    except ExtractionError:
        raise
    except ocr.OCRError as exc:
        raise ExtractionError(str(exc)) from None
    except Exception:
        raise ExtractionError("檔案無法解析；請確認格式或重新上傳") from None


def chunks(text, size=1200, overlap=150):
    for start in range(0, len(text), size - overlap):
        yield text[start:start + size]
        if start + size >= len(text):
            break
