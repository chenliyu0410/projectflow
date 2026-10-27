import io
from pathlib import Path

import pytest
from pypdf import PdfReader, PdfWriter

from app.ai import extractors, ocr
from test_ai_formal_index import isolated, refresh, ask, upload_doc
from test_report_lifecycle import setup

PIL = pytest.importorskip("PIL.Image")
MODELS = Path(__file__).resolve().parents[3] / "output/rag-starter-acceptance/local-model/ocr-models"
FONT = Path(r"C:\Windows\Fonts\msjh.ttc")
STARTER_PDF = next((Path(__file__).resolve().parents[1].parent / "deploy/rag-starter/corpus").rglob("*.pdf"))


def png(size=(40, 20)):
    buffer = io.BytesIO()
    PIL.new("RGB", size, "white").save(buffer, "PNG")
    return buffer.getvalue()


def scanned_pdf_with_text_page():
    scan = io.BytesIO()
    PIL.new("RGB", (60, 30), "white").save(scan, "PDF")
    writer = PdfWriter()
    writer.add_page(PdfReader(STARTER_PDF).pages[0])
    writer.add_page(PdfReader(io.BytesIO(scan.getvalue())).pages[0])
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


@pytest.fixture()
def fake_ocr(monkeypatch):
    calls = []
    monkeypatch.setattr(ocr, "enabled", lambda: True)
    monkeypatch.setattr(ocr, "identity", lambda: "fake-ocr")

    def recognize(data):
        calls.append(len(data))
        return [("新人報到改在五樓", 0.97), ("模糊雜訊", 0.3), ("上午九點集合", 0.93)]
    monkeypatch.setattr(ocr, "recognize", recognize)
    return calls


def test_images_are_skipped_when_ocr_is_off(monkeypatch):
    monkeypatch.delenv("PF_AI_OCR_MODEL_DIR", raising=False)
    assert not ocr.enabled()
    with pytest.raises(extractors.ExtractionError, match="需OCR"):
        extractors.extract_document(png(), "scan.png")


def test_image_text_is_marked_and_low_confidence_lines_dropped(fake_ocr):
    text, note = extractors.extract_document(png(), "scan.PNG")
    assert text.startswith(ocr.HEADER) and "五樓" in text and "模糊雜訊" not in text
    assert note == "OCR辨識，平均信心0.95"


def test_low_overall_confidence_skips_the_file(fake_ocr, monkeypatch):
    monkeypatch.setattr(ocr, "recognize", lambda data: [("看不清", 0.55), ("也看不清", 0.52)])
    with pytest.raises(extractors.ExtractionError, match="信心不足"):
        extractors.extract_document(png(), "scan.jpg")


def test_scanned_pages_use_ocr_while_text_pages_keep_their_text_layer(fake_ocr):
    text, note = extractors.extract_document(scanned_pdf_with_text_page(), "mixed.pdf")
    assert len(fake_ocr) == 1  # Only the image-only page went through OCR.
    assert "第1頁" in text and "第2頁\n新人報到改在五樓" in text and text.startswith(ocr.HEADER)
    assert note == "OCR辨識，1頁，平均信心0.95"


def test_oversized_images_are_rejected_before_decoding(monkeypatch):
    monkeypatch.setattr(ocr, "enabled", lambda: True)
    monkeypatch.setattr(ocr, "MAX_PIXELS", 100)
    monkeypatch.setattr(ocr, "engine", lambda: pytest.fail("engine must not run"))
    with pytest.raises(extractors.ExtractionError, match="4000萬像素"):
        extractors.extract_document(png((20, 20)), "huge.png")


def test_index_reads_images_once_ocr_turns_on(client, engine, isolated, monkeypatch):
    nid, pid, _ = setup(client, engine, "yu")
    upload_doc(client, nid, png(), name="報到公告.png")
    result = refresh(client)
    assert result["counts"]["skipped"] == 1
    calls = []
    monkeypatch.setattr(ocr, "enabled", lambda: True)
    monkeypatch.setattr(ocr, "identity", lambda: "fake-ocr")
    monkeypatch.setattr(ocr, "recognize", lambda data: calls.append(1) or [("新人報到改在五樓", 0.97)])
    result = refresh(client)  # Turning OCR on changes the source signature.
    assert calls and result["counts"]["skipped"] == 0
    item = next(i for i in result["items"] if i["title"] == "報到公告.png")
    assert item["state"] == "indexed" and item["reason"].startswith("OCR辨識")
    answer = ask(client, question="新人報到在幾樓", project_id=pid).json()
    assert any("五樓" in s["excerpt"] and "OCR" in s["excerpt"] for s in answer["sources"])


@pytest.mark.skipif(not (MODELS / ocr.MODEL).is_file() or not FONT.is_file(), reason="needs the isolated OCR model and a CJK font")
def test_real_traditional_chinese_model_reads_rendered_text(monkeypatch):
    from PIL import ImageDraw, ImageFont
    monkeypatch.setenv("PF_ACCEPTANCE_MODE", "true")
    monkeypatch.setenv("PF_AI_OCR_MODEL_DIR", str(MODELS))
    image = PIL.new("RGB", (900, 160), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(str(FONT), 36)
    draw.text((30, 20), "新人報到改在五樓，請攜帶公司筆電。", fill="black", font=font)
    draw.text((30, 90), "掃描教材測試：鮪魚與歡迎卡。", fill="black", font=font)
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    text, note = extractors.extract_document(buffer.getvalue(), "scan.png")
    for phrase in ["新人報到改在五樓", "攜帶公司筆電", "掃描教材", "鮪魚", "歡迎卡"]:
        assert phrase in text, text
    assert note.startswith("OCR辨識")


def test_unreadable_scanned_page_is_dropped_without_failing_the_document(fake_ocr, monkeypatch):
    monkeypatch.setattr(ocr, "recognize", lambda data: [("logo", 0.3)])
    text, note = extractors.extract_document(scanned_pdf_with_text_page(), "cover.pdf")
    assert "第1頁" in text and "logo" not in text and not text.startswith(ocr.HEADER)
    assert note == "1頁掃描影像無法可靠辨識，未採用"
    def broken(data):
        raise ocr.OCRError("影像無法解析")
    monkeypatch.setattr(ocr, "recognize", broken)
    assert "第1頁" in extractors.extract_document(scanned_pdf_with_text_page(), "cover.pdf")[0]


def test_ocr_switch_only_reparses_images_and_pdfs(monkeypatch):
    from app.ai import formal_index
    sources = {name: dict(fingerprint=name, storage_key="0" * 32, title=name) for name in ["a.txt", "b.png", "c.pdf"]}
    monkeypatch.setattr(formal_index, "source_path", lambda source: (_ for _ in ()).throw(OSError()))
    monkeypatch.setattr(ocr, "identity", lambda: "off")
    before = formal_index.source_signatures(sources)
    monkeypatch.setattr(ocr, "identity", lambda: "on")
    after = formal_index.source_signatures(sources)
    assert before["a.txt"] == after["a.txt"] and before["b.png"] != after["b.png"] and before["c.pdf"] != after["c.pdf"]
