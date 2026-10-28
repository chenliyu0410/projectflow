"""Unified document intake: judge the format and text layer page by page, extract, clean,
and return text with file-name and page metadata ready for RAG chunking."""
from dataclasses import asdict, dataclass
import io
from pathlib import Path
import time

from pypdf import PdfReader

from app.ai import cleanup, extractors, ocr

TEXT_LAYER_MIN = 10  # Same threshold as extractors: fewer characters means the page is a scan.


@dataclass
class Page:
    page: int
    route: str  # text_pdf | ocr | office | plain | skipped
    text: str
    seconds: float
    confidence: float | None = None


@dataclass
class Result:
    filename: str
    pages: list

    def text(self):
        return "\n\n".join(page.text for page in self.pages if page.text)

    def chunks(self, size=1200, overlap=150):
        """RAG chunks never cross a page, so every chunk can cite its file and page."""
        return [{"filename": self.filename, "page": page.page, "route": page.route, "text": chunk}
                for page in self.pages if page.text for chunk in extractors.chunks(page.text, size, overlap)]

    def as_dict(self):
        return {"filename": self.filename, "pages": [asdict(page) for page in self.pages], "chunks": self.chunks()}


def since(start):
    return round(time.perf_counter() - start, 3)


def pdf_pages(data):
    reader = PdfReader(io.BytesIO(data))
    if reader.is_encrypted or len(reader.pages) > 30:
        raise extractors.ExtractionError("PDF加密或超過30頁")
    pages, budget = [], [extractors.MAX_OCR_IMAGES]
    for number, page in enumerate(reader.pages, 1):
        start = time.perf_counter()
        text = page.extract_text() or ""
        if len(text.strip()) >= TEXT_LAYER_MIN:
            pages.append(Page(number, "text_pdf", text, since(start)))
            continue
        lines = extractors.ocr_page(page, budget) if ocr.enabled() else None
        if lines:
            text, average = ocr.lines_text(lines)
            pages.append(Page(number, "ocr", text, since(start), round(average, 2)))
        else:
            pages.append(Page(number, "skipped", "", since(start)))
    return pages


def image_page(data):
    if not ocr.enabled():
        raise extractors.ExtractionError("圖片需OCR；尚未設定OCR模型")
    start = time.perf_counter()
    try:
        lines = ocr.recognize(data)
    except ocr.OCRError as exc:
        raise extractors.ExtractionError(str(exc)) from None
    text, average = ocr.lines_text(lines)
    if not text or average < ocr.MIN_AVERAGE:
        raise extractors.ExtractionError("OCR信心不足，請提供較清楚的檔案")
    return Page(1, "ocr", text, since(start), round(average, 2))


def ingest(data, filename):
    extension = Path(filename).suffix.lower()
    if not data or len(data) > extractors.MAX_BYTES:
        raise extractors.ExtractionError("檔案為空或超過10MB")
    if extension == ".pdf":
        try:
            pages = pdf_pages(data)
        except extractors.ExtractionError:
            raise
        except Exception:
            raise extractors.ExtractionError("檔案無法解析；請確認格式或重新上傳") from None
    elif extension in extractors.IMAGES:
        pages = [image_page(data)]
    elif extension in {".docx", ".xlsx", ".txt", ".csv"}:
        start = time.perf_counter()
        text, _ = extractors.extract_document(data, filename)
        if extension == ".xlsx":
            text = cleanup.sheet_to_text(text)
        route = "office" if extension in {".docx", ".xlsx"} else "plain"
        return Result(filename, [Page(1, route, text, since(start))])
    else:
        raise extractors.ExtractionError("不支援此格式")
    for page, text in zip(pages, cleanup.clean_pages([page.text for page in pages])):
        page.text = text
    return Result(filename, pages)
