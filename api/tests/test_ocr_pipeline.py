import io

import pytest

from app.ai import cleanup, ocr

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
