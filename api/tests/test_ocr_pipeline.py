import io

import pytest

from app.ai import ocr

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
