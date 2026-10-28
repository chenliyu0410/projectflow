import io

import pytest
from pypdf import PdfReader, PdfWriter

from app.ai import cleanup, extractors, ingest, ocr, ocr_metrics
from test_ai_ocr import STARTER_PDF, png

PIL = pytest.importorskip("PIL.Image")


def test_preprocess_upscales_small_scans_and_stretches_contrast():
    faint = PIL.new("RGB", (400, 100), (150, 150, 150))
    faint.paste((170, 170, 170), (0, 0, 200, 100))
    result = ocr.preprocess(faint)
    assert result.mode == "RGB" and result.width == 1000 and result.height == 250
    low, high = result.convert("L").getextrema()
    assert low == 0 and high == 255  # Faint gray text becomes black on white.


def test_preprocess_keeps_large_scans_at_their_size():
    assert ocr.preprocess(PIL.new("RGB", (1600, 900), "white")).size == (1600, 900)


def test_running_headers_footers_and_page_numbers_are_removed():
    pages = [
        "毛研食品 內部文件\n設備借用規則一\n第 1 頁",
        "毛研食品 內部文件\n設備借用規則二\n- 2 -",
        "毛研食品 內部文件\n設備借用規則三\n3/3",
    ]
    assert cleanup.clean_pages(pages) == ["設備借用規則一", "設備借用規則二", "設備借用規則三"]


def test_numbers_inside_the_page_are_kept():
    assert cleanup.clean_pages(["品名：筆電\n數量\n3\n備註：新人用。"]) == ["品名：筆電\n數量\n3\n備註：新人用。"]


def test_wrapped_sentences_are_rejoined_but_headings_and_items_stay_apart():
    lines = ["借用設備時請先填寫簽收單並交由部門", "主管簽名後再到資訊室領取。", "注意事項", "1. 歸還時須當面點收。"]
    assert cleanup.merge_lines(lines) == ["借用設備時請先填寫簽收單並交由部門主管簽名後再到資訊室領取。", "注意事項", "1. 歸還時須當面點收。"]


def test_sheet_rows_become_field_sentences():
    text = "工作表：sheet1（儲存值；公式不重新計算）\nA1=品名 | B1=數量 | C1=單價\nA2=鮪魚罐 | B2=3 | C2=45\nA3=歡迎卡 | C3=12"
    assert cleanup.sheet_to_text(text) == "工作表：sheet1\n品名：鮪魚罐；數量：3；單價：45\n品名：歡迎卡；單價：12"


def mixed_pdf():
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
    monkeypatch.setattr(ocr, "enabled", lambda: True)
    monkeypatch.setattr(ocr, "recognize", lambda data: [
        ("借用設備時請先填寫簽收單並交由部門", 0.95), ("主管簽名後再到資訊室領取。", 0.9), ("雜訊", 0.2)])


def test_each_pdf_page_records_its_route_time_and_confidence(fake_ocr):
    result = ingest.ingest(mixed_pdf(), "混合文件.pdf")
    assert [p.route for p in result.pages] == ["text_pdf", "ocr"]
    assert [p.page for p in result.pages] == [1, 2]
    scanned = result.pages[1]
    assert scanned.text == "借用設備時請先填寫簽收單並交由部門主管簽名後再到資訊室領取。"
    assert scanned.confidence == 0.93 and scanned.seconds >= 0


def test_chunks_carry_file_name_and_page(fake_ocr):
    chunks = ingest.ingest(mixed_pdf(), "混合文件.pdf").chunks()
    assert {c["page"] for c in chunks} == {1, 2}
    assert all(c["filename"] == "混合文件.pdf" and c["text"] for c in chunks)
    assert next(c for c in chunks if c["page"] == 2)["route"] == "ocr"


def test_scanned_page_is_marked_skipped_when_ocr_is_off(monkeypatch):
    monkeypatch.setattr(ocr, "enabled", lambda: False)
    result = ingest.ingest(mixed_pdf(), "混合文件.pdf")
    assert [p.route for p in result.pages] == ["text_pdf", "skipped"] and result.pages[1].text == ""


def test_images_go_through_ocr(fake_ocr):
    result = ingest.ingest(png(), "公告.png")
    assert [(p.page, p.route) for p in result.pages] == [(1, "ocr")]


def test_images_need_ocr(monkeypatch):
    monkeypatch.setattr(ocr, "enabled", lambda: False)
    with pytest.raises(extractors.ExtractionError, match="需OCR"):
        ingest.ingest(png(), "公告.png")


def test_spreadsheets_become_sentences(monkeypatch):
    monkeypatch.setattr(extractors, "extract_document",
                        lambda data, name: ("工作表：s（儲存值；公式不重新計算）\nA1=品名 | B1=數量\nA2=鮪魚罐 | B2=3", ""))
    result = ingest.ingest(b"zip", "清單.xlsx")
    assert result.pages[0].route == "office" and result.text() == "工作表：s\n品名：鮪魚罐；數量：3"


def test_word_documents_use_the_office_route():
    from docx import Document
    document = Document()
    document.add_paragraph("十月新人報到會議紀錄")
    buffer = io.BytesIO()
    document.save(buffer)
    result = ingest.ingest(buffer.getvalue(), "會議紀錄.docx")
    assert result.pages[0].route == "office" and "新人報到" in result.text()


def test_unknown_format_is_rejected():
    with pytest.raises(extractors.ExtractionError, match="不支援"):
        ingest.ingest(b"x", "a.exe")


def test_cer_ignores_whitespace_and_counts_edits():
    assert ocr_metrics.cer("新人 報到\n五樓", "新人報到五樓") == 0
    assert ocr_metrics.cer("新人報到五樓", "新入報到五樓") == pytest.approx(1 / 6)
    assert ocr_metrics.accuracy("新人報到", "") == 0
    assert ocr_metrics.accuracy("新人", "新人報到五樓多出很多字") == 0  # Never negative.


def test_route_stats_report_seconds_per_page():
    pages = [ingest.Page(1, "text_pdf", "a", 0.01), ingest.Page(2, "ocr", "b", 1.2), ingest.Page(3, "ocr", "c", 0.8)]
    stats = ocr_metrics.route_stats(pages)
    assert stats["ocr"] == {"pages": 2, "seconds": 2.0, "per_page": 1.0}
    assert stats["text_pdf"]["pages"] == 1


def test_a_line_final_dot_after_chinese_is_a_full_stop():
    assert ocr.normalize("請準時報到·") == "請準時報到。"
    assert ocr.normalize("新人·報到") == "新人，報到"  # Existing rule between characters is kept.
    assert ocr.normalize("v1.2 ·") == "v1.2 ·"  # Only after Chinese text.


def test_ocr_switch_works_outside_acceptance_mode(monkeypatch, tmp_path):
    (tmp_path / ocr.MODEL).write_bytes(b"model")
    (tmp_path / ocr.KEYS).write_text("keys", encoding="utf-8")
    monkeypatch.delenv("PF_ACCEPTANCE_MODE", raising=False)
    monkeypatch.delenv("PF_AI_OCR", raising=False)
    monkeypatch.setenv("PF_AI_OCR_MODEL_DIR", str(tmp_path))
    assert not ocr.enabled()  # Off by default, so existing deployments do not change.
    monkeypatch.setenv("PF_AI_OCR", "true")
    assert ocr.enabled()
    monkeypatch.setenv("PF_AI_OCR_MODEL_DIR", str(tmp_path / "missing"))
    assert not ocr.enabled()  # A missing model folder turns OCR off instead of failing.
