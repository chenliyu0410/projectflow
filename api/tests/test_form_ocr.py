"""OCR-FORMS: alignment, line removal, checkbox state and label-value pairing (no OCR model needed)."""
import pytest

cv2 = pytest.importorskip("cv2")
np = pytest.importorskip("numpy")
from app.ai import form_ocr  # noqa: E402

BOX = [100, 100, 126, 126]


def page_with_box(mark=None):
    page = np.full((240, 240, 3), 255, np.uint8)
    cv2.rectangle(page, (BOX[0], BOX[1]), (BOX[2], BOX[3]), (20, 20, 20), 2)
    ink = (40, 60, 150)
    if mark == "check":
        cv2.polylines(page, [np.array([[103, 113], [110, 123], [130, 92]])], False, ink, 3)
    elif mark == "faint":
        cv2.polylines(page, [np.array([[103, 113], [110, 123], [130, 92]])], False, (170, 175, 200), 2)
    elif mark == "outside":
        cv2.polylines(page, [np.array([[118, 100], [125, 110], [145, 78]])], False, ink, 3)
    elif mark == "stray":
        cv2.line(page, (95, 140), (135, 139), ink, 2)
        cv2.line(page, (138, 102), (150, 120), ink, 2)
    return page


@pytest.mark.parametrize("mark,expected", [(None, "unchecked"), ("stray", "unchecked"), ("check", "checked")])
def test_checkbox_state(mark, expected):
    state, score = form_ocr.checkbox_state(page_with_box(mark), BOX)
    assert state == expected, score


def test_filled_in_box_is_checked():
    page = page_with_box()
    cv2.rectangle(page, (102, 102), (124, 124), (40, 60, 150), -1)
    assert form_ocr.checkbox_state(page, BOX)[0] == "checked"


def test_text_lines_splits_a_field_into_tight_lines():
    crop = np.full((170, 600, 3), 255, np.uint8)
    cv2.line(crop, (0, 168), (599, 168), (0, 0, 0), 2)
    cv2.putText(crop, "first line", (40, 55), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (40, 60, 150), 3)
    cv2.putText(crop, "second", (60, 130), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (40, 60, 150), 3)
    lines = form_ocr.text_lines(crop)
    assert len(lines) == 2
    assert all(line.shape[0] < 80 for line in lines)
    assert lines[1].shape[1] < lines[0].shape[1]  # trimmed to the writing, not the cell
    assert form_ocr.text_lines(np.full((80, 300, 3), 255, np.uint8)) == []


@pytest.mark.parametrize("mark", ["faint", "outside"])
def test_faint_or_off_centre_tick_is_never_called_empty(mark):
    """A tick that only clips the box corner may go to a person, but must not be read as 'not ticked'."""
    state, _ = form_ocr.checkbox_state(page_with_box(mark), BOX)
    assert state in ("checked", "unsure")


def test_remove_lines_keeps_handwriting():
    crop = np.full((80, 400, 3), 255, np.uint8)
    cv2.line(crop, (0, 70), (399, 70), (0, 0, 0), 2)  # cell border
    cv2.line(crop, (5, 0), (5, 79), (0, 0, 0), 2)
    cv2.putText(crop, "ab", (60, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (40, 60, 150), 3)
    cleaned = cv2.cvtColor(form_ocr.remove_lines(crop), cv2.COLOR_BGR2GRAY)
    assert cleaned[70, 200] > 200 and cleaned[40, 5] > 200  # lines gone
    assert (cleaned[20:60, 55:120] < 128).sum() > 100  # writing kept


def test_align_undoes_a_phone_photo_warp():
    template = {"size": [600, 800], "lines": [[50, 100, 550, 100], [50, 700, 550, 700], [50, 100, 50, 700], [550, 100, 550, 700],
                                              [50, 300, 550, 300], [300, 100, 300, 700]]}
    page = np.full((800, 600, 3), 255, np.uint8)
    for x0, y0, x1, y1 in template["lines"]:
        cv2.line(page, (x0, y0), (x1, y1), (20, 20, 20), 2)
    src = np.float32([[0, 0], [600, 0], [600, 800], [0, 800]])
    dst = np.float32([[30, 20], [610, 45], [590, 830], [10, 790]])
    warp = cv2.getPerspectiveTransform(src, dst)
    photo = cv2.warpPerspective(page, warp, (660, 880), borderValue=(150, 150, 150))
    aligned, ok = form_ocr.align(photo, template)
    assert ok
    assert aligned.shape[:2] == (800, 600)
    gray = cv2.cvtColor(aligned, cv2.COLOR_BGR2GRAY)
    for x, y in [(50, 400), (550, 400), (300, 200), (200, 300)]:  # points on the template's lines are dark after alignment
        assert gray[y - 4:y + 5, x - 4:x + 5].min() < 100, (x, y)


def test_align_ignores_the_paper_edge_on_a_dark_desk():
    template = {"size": [600, 800], "lines": [[150, 200, 450, 200], [150, 400, 450, 400], [150, 200, 150, 400], [450, 200, 450, 400],
                                              [300, 200, 300, 400]]}
    page = np.full((800, 600, 3), 235, np.uint8)
    for x0, y0, x1, y1 in template["lines"]:
        cv2.line(page, (x0, y0), (x1, y1), (20, 20, 20), 2)
    src = np.float32([[0, 0], [600, 0], [600, 800], [0, 800]])
    dst = np.float32([[40, 30], [600, 50], [580, 840], [20, 800]])
    photo = cv2.warpPerspective(page, cv2.getPerspectiveTransform(src, dst), (660, 880), borderValue=(90, 80, 70))
    aligned, ok = form_ocr.align(photo, template)
    assert ok
    gray = cv2.cvtColor(aligned, cv2.COLOR_BGR2GRAY)
    for x, y in [(150, 300), (450, 300), (300, 300), (225, 200), (375, 400)]:
        assert gray[y - 4:y + 5, x - 4:x + 5].min() < 100, (x, y)


def test_align_keeps_a_tilted_table_border():
    """A 3-degree tilt over a wide table: the top border must still count as the table's edge."""
    template = {"size": [1240, 1754], "lines": [[80, 220, 1160, 220], [80, 900, 1160, 900], [80, 220, 80, 900], [1160, 220, 1160, 900],
                                                [80, 400, 1160, 400], [600, 220, 600, 900]]}
    page = np.full((1754, 1240, 3), 240, np.uint8)
    for x0, y0, x1, y1 in template["lines"]:
        cv2.line(page, (x0, y0), (x1, y1), (20, 20, 20), 2)
    rotation = cv2.getRotationMatrix2D((620, 877), 3.5, 0.6)
    photo = cv2.warpAffine(page, rotation, (1240, 1754), borderValue=(110, 100, 90))
    aligned, ok = form_ocr.align(photo, template)
    assert ok
    gray = cv2.cvtColor(aligned, cv2.COLOR_BGR2GRAY)
    for x, y in [(80, 600), (1160, 600), (600, 300), (300, 220), (900, 900), (300, 400)]:
        assert gray[y - 6:y + 7, x - 6:x + 7].min() < 110, (x, y)


def test_align_reports_failure_on_a_blank_photo():
    _, ok = form_ocr.align(np.full((500, 400, 3), 200, np.uint8), {"size": [600, 800], "lines": [[50, 100, 550, 100]]})
    assert not ok


def test_pair_fields_takes_the_text_right_of_or_below_each_label():
    boxes = [("借用人", [10, 10, 80, 40]), ("陳冠廷", [120, 12, 220, 42]), ("部門", [300, 10, 360, 40]), ("品保課", [400, 8, 500, 44]),
             ("用途說明", [10, 100, 110, 130]), ("客戶稽核", [20, 140, 200, 175]), ("要帶去", [210, 142, 300, 176])]
    pairs = form_ocr.pair_fields(boxes, {"borrower": "借用人", "dept": "部門", "purpose": "用途說明", "missing": "電話"})
    assert pairs == {"borrower": "陳冠廷", "dept": "品保課", "purpose": "客戶稽核要帶去", "missing": ""}


def test_wide_box_uses_its_own_height():
    page = np.full((240, 300, 3), 255, np.uint8)
    box = [100, 100, 160, 124]  # 60 x 24, not square
    cv2.rectangle(page, (100, 100), (160, 124), (20, 20, 20), 2)
    assert form_ocr.checkbox_state(page, box)[0] == "unchecked"
    cv2.line(page, (110, 112), (150, 113), (40, 60, 150), 3)
    cv2.line(page, (112, 108), (148, 118), (40, 60, 150), 3)
    assert form_ocr.checkbox_state(page, box)[0] == "checked"


def test_box_at_the_page_edge_is_read_in_place():
    page = np.full((200, 200, 3), 255, np.uint8)
    box = [2, 2, 28, 28]  # the padded crop is clipped at the top-left corner
    cv2.rectangle(page, (2, 2), (28, 28), (20, 20, 20), 2)
    cv2.rectangle(page, (60, 60), (120, 120), (40, 60, 150), -1)  # ink elsewhere must not leak in
    assert form_ocr.checkbox_state(page, box)[0] == "unchecked"
    cv2.polylines(page, [np.array([[5, 15], [12, 25], [30, 0]])], False, (40, 60, 150), 3)
    assert form_ocr.checkbox_state(page, box)[0] == "checked"


def test_align_rejects_a_border_with_the_wrong_shape():
    """A wide table found where the template expects a tall one is a wrong match, not a page to warp."""
    template = {"size": [600, 800], "lines": [[100, 50, 500, 50], [100, 750, 500, 750], [100, 50, 100, 750], [500, 50, 500, 750]]}
    photo = np.full((800, 800, 3), 240, np.uint8)
    cv2.rectangle(photo, (50, 300), (750, 500), (20, 20, 20), 2)
    cv2.line(photo, (400, 300), (400, 500), (20, 20, 20), 2)
    assert not form_ocr.align(photo, template)[1]


def test_label_match_does_not_confuse_opposites():
    assert not form_ocr._is_label("不合格", "合格")
    assert form_ocr._is_label("合格", "合格")
    assert form_ocr._is_label("借用人：", "借用人")


def test_normalize_for_scoring():
    assert form_ocr.normalize(" 115．11．３ ") == "115.11.3"
    assert form_ocr.normalize("借用人：陳冠廷") == "借用人陳冠廷"
