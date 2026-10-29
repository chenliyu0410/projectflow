# OCR-PIPE：文件解析與 OCR 模組

依 WORKFLOW §14（精簡流程），規格和計畫合併在本文件。

**Goal:** 依架構圖做出一條完整的文件解析管線：上傳檔案 → 格式判斷 → 三路擷取 → 清理與正規化 → 統一輸出（文字＋檔名／頁碼）→ 切成可交給 RAG 的段落，再用 1−CER 和每頁秒數產生驗證報告，作為展示和報告的素材。

**Architecture:** 新增 `app/ai/ingest.py` 作為統一入口，逐頁判斷要走哪一條路，並沿用既有的 `extractors`（pypdf、docx／xlsx 安全解析）和 `ocr`（RapidOCR 繁中模型）；新增 `cleanup.py` 負責清理與正規化，`ocr_metrics.py` 負責 CER 和分路統計。展示用 `deploy/ocr_pipeline.py` 一行指令處理一整個資料夾，輸出 HTML 報告。既有的正式索引 `extract_document` 不改，避免影響已經驗收過的行為。

**Tech Stack:** Python 3.13、pypdf 6.10、rapidocr-onnxruntime 1.4.4＋繁中辨識模型 `chinese_cht_PP-OCRv3_rec_mobile.onnx`、Pillow（前處理）、python-docx（產生樣本）、pytest。


## Global Constraints

- OCR 模型和 OCR 套件放在 repo 外或 `.venv`，不 commit 模型檔。OCR 預設關閉，只有在 `PF_AI_OCR=true`（Task 7 新增）或 `PF_ACCEPTANCE_MODE=true` 時，才會讀取 `PF_AI_OCR_MODEL_DIR`。
- 沿用既有上限：單檔 10MB、PDF 30 頁、單張影像 4000 萬像素、每檔 OCR 影像 60 張、行信心低於 0.5 丟棄、整份平均低於 0.6 不採用。
- 範例資料全部虛構（毛研食品），不放真實個資。
- **可隨處地端部署**：OCR 推論全部在本機 CPU 上執行，不呼叫任何雲端服務；Windows 和 Linux 都要能跑；模型能離線攜帶並用 SHA-256 核對；斷網時也要能完成整條管線。預設維持關閉，既有部署不受影響。
- 測試指令一律從 repo 根目錄執行：`api/.venv/Scripts/python.exe -m pytest -c api/pyproject.toml <path> -q`

---

## 架構圖對照

| 架構圖方塊 | 現況 | 本計畫 |
|---|---|---|
| 上傳檔案 | 正式文件上傳已存在 | 展示改用 CLI 讀資料夾（延後：API／網頁上傳） |
| 格式判斷（副檔名・有無文字層） | `extract_document` 內有，但只回傳整份字串 | `ingest.ingest()` 逐頁判斷並**記錄**走哪一路（Task 3） |
| 文字層 PDF：pypdf 直接擷取 | 已有 | 沿用 |
| 掃描檔 → OCR：前處理＋RapidOCR 繁中 | 有 OCR，**沒有前處理** | `ocr.preprocess()`：灰階、自動對比、小圖放大（Task 1） |
| Word／Excel：python-docx・openpyxl | 已有安全的 XML 解析（防 zip bomb／XXE） | 沿用既有解析，**不加 openpyxl**（決定 1） |
| 清理與正規化：去頁首尾・合併斷行・表格轉文字 | 沒有 | `cleanup.py`（Task 2） |
| 統一輸出：文字＋metadata（檔名・頁碼） | 只有「第N頁」字串標記 | `ingest.Result`／`Page` 資料結構＋JSON（Task 3） |
| 可搜尋索引：交給 RAG 切分 | `extractors.chunks()` | `Result.chunks()`：每段帶檔名、頁碼、路徑（Task 3） |
| 驗證點：辨識正確率 1−CER、人工標註頁 | 沒有 | `ocr_metrics.cer()`＋`*.gt.txt` 標註檔（Task 4、5） |
| 驗證點：處理時間（每頁秒數，分路統計） | 沒有 | `Page.seconds`＋`ocr_metrics.route_stats()`（Task 3、4） |

## 實作中已採用的決定

1. **Excel 不加 openpyxl**：既有的 xlsx 解析已經有解壓上限、拒絕 DTD／ENTITY 等防護，加 openpyxl 會多一個依賴，也會繞過這些防護。圖上的 openpyxl 改用既有解析器實現同樣的功能。
2. **展示入口用 CLI＋HTML 報告，不做網頁上傳**：網頁上傳要處理登入、權限和前端畫面，一天內做不完。CLI 報告可以完整呈現架構圖的每一步和兩個驗證點。
3. **標註資料用程式產生**：用微軟正黑體把已知文字畫成「掃描圖」，原文就是標註答案（`.gt.txt`）。
4. **CER 以整份文件比對、忽略空白**：清理後的斷行位置可能和標註不同，所以忽略空白和換行，只比對字元。
5. **清理只套用在 PDF 和圖片**：Word 段落本來就是完整的句子，不需要合併斷行；Excel 只做表格轉文字。
6. **頁碼只在頁面邊緣移除**：只檢查每頁的前兩行和最後兩行，避免把表單裡的數字誤刪。
7. **前處理預設開啟，並在報告裡做開／關 A/B 比較**：開關為 `ocr.PREPROCESS`，用來量化前處理的效果。
8. **地端部署：模型不放進映像檔，改用唯讀 volume 掛載**：映像檔可以公開重建，模型則依各地環境放置，並用 SHA-256 核對；換模型時不必重建映像檔。OCR 用獨立的 `PF_AI_OCR` 開關，不必為了開 OCR 而啟用測試用的 `PF_ACCEPTANCE_MODE`。
9. **不做 GPU 版**：CPU 版 onnxruntime 在任何 x64／arm64 機器上都能跑，GPU 版要配合 CUDA 版本，會降低可攜性。

## 範圍與延後

**本次範圍：** Task 0–7。

**延後：** API／網頁上傳畫面、把 `ingest` 接進正式索引（`formal_index`）、Word 表格結構化、傾斜校正（deskew）、多欄版面、手寫字、PostgreSQL 部署、GPU 加速。

## 基本權限與資料

- 沒有新的 API，也沒有 migration，不寫入業務資料庫。
- CLI 只讀取指定的資料夾，輸出到指定路徑；預設輸出到 `output/ocr-report/`（新增到 `.gitignore`）。

## 檔案結構

| 檔案 | 動作 | 責任 |
|---|---|---|
| `api/app/ai/ocr.py` | 修改 | 新增 `PREPROCESS`、`preprocess()`，讓 `recognize()` 先做前處理 |
| `api/app/ai/cleanup.py` | 新增 | 去除重複的頁首尾和頁碼、合併斷行、表格轉文字 |
| `api/app/ai/ingest.py` | 新增 | 統一入口：格式判斷、逐頁分路、計時、套用清理、輸出 `Result` |
| `api/app/ai/ocr_metrics.py` | 新增 | `cer()`、`accuracy()`、`route_stats()` |
| `api/tests/test_ocr_pipeline.py` | 新增 | 以上模組的單元測試（用假 OCR，不需要模型） |
| `deploy/ocr-eval/make_samples.py` | 新增 | 產生虛構樣本和標註答案 |
| `deploy/ocr-eval/samples/` | 新增 | 產生出的樣本（commit，讓展示可以重現） |
| `deploy/ocr_pipeline.py` | 新增 | CLI：處理資料夾、評分、A/B 比較、輸出 JSON 和 HTML 報告 |
| `.gitignore` | 修改 | 加入 `output/`、`deploy/ocr-models/` |
| `deploy/ocr-models.sha256` | 新增 | 繁中模型的完整 SHA-256，供離線部署時核對 |
| `deploy/api.Dockerfile`、`deploy/docker-compose.yml` | 修改 | 可選的 OCR 映像檔（`WITH_OCR`），模型用唯讀 volume 掛載 |
| `docs/ai-assistant.md`、`docs/PROGRESS.md` | 修改 | 記錄結果與限制（Task 6） |

---

### Task 0：環境準備

**Files:** 無程式變更（只在 `.venv` 安裝套件，在 repo 外放模型）

**Interfaces:**
- Produces：環境變數 `PF_AI_OCR_MODEL_DIR` 指向的資料夾內有 `chinese_cht_PP-OCRv3_rec_mobile.onnx`、`chinese_cht_dict.txt`；後續 Task 5 和 6 會用到。

- [ ] **Step 1：開分支**

```bash
git checkout -b feature/ocr-pipeline
```

- [ ] **Step 2：安裝 OCR 套件（鎖版）**

```bash
uv pip install --python api/.venv/Scripts/python.exe -r api/requirements-ocr.lock
```

預期：安裝 `rapidocr-onnxruntime==1.4.4`、`onnxruntime`、`opencv-python`、`pillow` 等，沒有錯誤。

- [ ] **Step 3：從 ModelScope `RapidAI/RapidOCR` 下載繁中辨識模型到 repo 外的 `../ocr-models/`**

先列出檔案，找出兩個檔案在 repo 裡的實際路徑：

```bash
curl -s "https://www.modelscope.cn/api/v1/models/RapidAI/RapidOCR/repo/files?Recursive=true" | grep -o '"Path":"[^"]*chinese_cht[^"]*"'
```

再用找到的路徑下載（`<path>` 換成上一步輸出的 Path）：

```bash
mkdir -p ../ocr-models
curl -L -o ../ocr-models/chinese_cht_PP-OCRv3_rec_mobile.onnx "https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/master/<path-of-onnx>"
curl -L -o ../ocr-models/chinese_cht_dict.txt "https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/master/<path-of-dict>"
sha256sum ../ocr-models/*
```

預期 SHA-256 開頭和結尾要符合 `docs/ai-assistant.md` 記錄的值：onnx 為 `779656d0…28cc6`，dict 為 `832551fe…c1a83`。不符合就不要使用。核對通過後，把完整雜湊值存進 repo，供之後離線部署時核對（Task 7）：

```bash
(cd ../ocr-models && sha256sum chinese_cht_PP-OCRv3_rec_mobile.onnx chinese_cht_dict.txt) > deploy/ocr-models.sha256
```

- [ ] **Step 4：用既有的真模型測試確認模型可以運作**

既有的 `test_real_traditional_chinese_model_reads_rendered_text` 使用固定路徑，所以這裡改用一次性指令驗證：

```bash
PF_ACCEPTANCE_MODE=true PF_AI_OCR_MODEL_DIR=../ocr-models api/.venv/Scripts/python.exe -c "import sys; sys.path.insert(0,'api'); from app.ai import ocr; print(ocr.enabled(), ocr.identity())"
```

預期：`True rapidocr-1.4.4:chinese_cht_PP-OCRv3_rec_mobile.onnx:...`

---

### Task 1：OCR 前處理

**Files:**
- Modify: `api/app/ai/ocr.py`（`recognize()` 內的 `image.convert("RGB")`）
- Test: `api/tests/test_ocr_pipeline.py`

**Interfaces:**
- Produces：`ocr.PREPROCESS: bool`（預設 `True`）；`ocr.preprocess(image: PIL.Image.Image) -> PIL.Image.Image`（回傳 RGB）。`ocr.recognize(data)` 的介面不變。

- [ ] **Step 1：寫失敗測試**

建立 `api/tests/test_ocr_pipeline.py`：

```python
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
```

- [ ] **Step 2：執行測試，確認失敗**

執行：`api/.venv/Scripts/python.exe -m pytest -c api/pyproject.toml api/tests/test_ocr_pipeline.py -q`
預期：FAIL，`AttributeError: module 'app.ai.ocr' has no attribute 'preprocess'`

- [ ] **Step 3：實作**

在 `api/app/ai/ocr.py` 的常數區加入 `MIN_WIDTH = 1000` 和 `PREPROCESS = True`，並在 `normalize()` 之前加入：

```python
def preprocess(image):
    """Grayscale, stretch contrast and upscale small scans so faint or tiny text reaches the model."""
    from PIL import ImageOps

    gray = ImageOps.autocontrast(ImageOps.grayscale(image), cutoff=1)
    if gray.width < MIN_WIDTH:
        gray = gray.resize((MIN_WIDTH, round(gray.height * MIN_WIDTH / gray.width)))
    return gray.convert("RGB")
```

把 `recognize()` 裡的：

```python
            image.convert("RGB").save(buffer, "PNG")
```

改成：

```python
            (preprocess(image) if PREPROCESS else image.convert("RGB")).save(buffer, "PNG")
```

（像素上限檢查在放大之前執行，而且只有寬度小於 1000 的圖才會放大，所以不會突破上限。）

- [ ] **Step 4：執行新測試和既有的 OCR 測試**

執行：`api/.venv/Scripts/python.exe -m pytest -c api/pyproject.toml api/tests/test_ocr_pipeline.py api/tests/test_ai_ocr.py -q`
預期：全部 PASS（真模型那一題沒有模型時會 skip）

- [ ] **Step 5：Commit**

```bash
git add api/app/ai/ocr.py api/tests/test_ocr_pipeline.py
git commit -m "OCR-PIPE: preprocess scans before OCR"
```

---

### Task 2：清理與正規化

**Files:**
- Create: `api/app/ai/cleanup.py`
- Test: `api/tests/test_ocr_pipeline.py`（加在檔尾）

**Interfaces:**
- Produces：
  - `cleanup.clean_pages(texts: list[str]) -> list[str]`：輸入每頁文字，回傳每頁清理後的文字，長度不變
  - `cleanup.sheet_to_text(text: str) -> str`：把 `extractors` 的 xlsx 輸出轉成「欄位：值」句子
  - `cleanup.merge_lines(lines: list[str]) -> list[str]`

- [ ] **Step 1：寫失敗測試**（加到 `api/tests/test_ocr_pipeline.py` 檔尾，並在檔頭的 import 加上 `from app.ai import cleanup`）

```python
from app.ai import cleanup


def test_running_headers_footers_and_page_numbers_are_removed():
    pages = [
        "毛研食品 內部文件\n設備借用規則一\n第 1 頁",
        "毛研食品 內部文件\n設備借用規則二\n- 2 -",
        "毛研食品 內部文件\n設備借用規則三\n3/3",
    ]
    assert cleanup.clean_pages(pages) == [
        "設備借用規則一",
        "設備借用規則二",
        "設備借用規則三",
    ]


def test_numbers_inside_the_page_are_kept():
    assert cleanup.clean_pages(["品名：筆電\n數量\n3\n備註：新人用。"]) == [
        "品名：筆電\n數量\n3\n備註：新人用。"
    ]


def test_wrapped_sentences_are_rejoined_but_headings_and_items_stay_apart():
    lines = [
        "借用設備時請先填寫簽收單並交由部門",
        "主管簽名後再到資訊室領取。",
        "注意事項",
        "1. 歸還時須當面點收。",
    ]
    assert cleanup.merge_lines(lines) == [
        "借用設備時請先填寫簽收單並交由部門主管簽名後再到資訊室領取。",
        "注意事項",
        "1. 歸還時須當面點收。",
    ]


def test_sheet_rows_become_field_sentences():
    text = "工作表：sheet1（儲存值；公式不重新計算）\nA1=品名 | B1=數量 | C1=單價\nA2=鮪魚罐 | B2=3 | C2=45\nA3=歡迎卡 | C3=12"
    assert (
        cleanup.sheet_to_text(text)
        == "工作表：sheet1\n品名：鮪魚罐；數量：3；單價：45\n品名：歡迎卡；單價：12"
    )
```

- [ ] **Step 2：執行測試，確認失敗**

執行：`api/.venv/Scripts/python.exe -m pytest -c api/pyproject.toml api/tests/test_ocr_pipeline.py -q`
預期：FAIL，`ImportError: cannot import name 'cleanup'`

- [ ] **Step 3：實作 `api/app/ai/cleanup.py`**

```python
"""Clean extracted page text before indexing: drop running headers/footers and page numbers,
rejoin wrapped lines, and turn spreadsheet rows into field sentences."""

from collections import Counter
import re

PAGE_NUMBER = re.compile(
    r"^\s*(?:第\s*\d+\s*頁(?:\s*[/，,]\s*共\s*\d+\s*頁)?|[-–—]\s*\d+\s*[-–—]|\d+\s*/\s*\d+|\d+|page\s*\d+(?:\s*of\s*\d+)?)\s*$",
    re.IGNORECASE,
)
SENTENCE_END = tuple("。！？；：」』）)!?;:")
CJK = re.compile(r"[一-鿿]")
CELL = re.compile(r"^([A-Z]+)\d+=(.*)$")
MIN_WRAPPED = 15  # Shorter lines are headings or labels, never the first half of a wrapped sentence.


def repeated_edges(pages):
    """Lines at the top or bottom of at least half of the pages (and of two or more) are running headers/footers."""
    if len(pages) < 2:
        return set()
    counts = Counter()
    for lines in pages:
        counts.update({line for line in lines[:2] + lines[-2:]})
    return {
        line for line, count in counts.items() if count >= max(2, (len(pages) + 1) // 2)
    }


def strip_edges(lines, repeated):
    def noise(line):
        return line in repeated or PAGE_NUMBER.match(line)

    head = 0
    while head < min(2, len(lines)) and noise(lines[head]):
        head += 1
    tail = len(lines)
    while tail > max(head, len(lines) - 2) and noise(lines[tail - 1]):
        tail -= 1
    return lines[head:tail]


def merge_lines(lines):
    """Rejoin a line that the page or scan width broke mid-sentence; keep headings and list items apart."""
    merged = []
    for line in lines:
        previous = merged[-1] if merged else ""
        if (
            len(previous) >= MIN_WRAPPED
            and not previous.endswith(SENTENCE_END)
            and CJK.match(previous[-1])
            and CJK.match(line)
        ):
            merged[-1] = previous + line
        else:
            merged.append(line)
    return merged


def clean_pages(texts):
    pages = [
        [line.strip() for line in text.splitlines() if line.strip()] for text in texts
    ]
    repeated = repeated_edges(pages)
    return ["\n".join(merge_lines(strip_edges(lines, repeated))) for lines in pages]


def sheet_to_text(text):
    """Turn 'A1=品名 | B1=數量' rows into '品名：鮪魚；數量：3', using each sheet's first row as the header."""
    output, header = [], None
    for line in text.splitlines():
        if line.startswith("工作表："):
            output.append(line.split("（")[0])
            header = None
            continue
        cells = [CELL.match(cell) for cell in line.split(" | ")]
        if not all(cells):
            output.append(line)
            continue
        row = {match[1]: match[2] for match in cells}
        if header is None:
            header = row
            continue
        output.append(
            "；".join(
                f"{header.get(column, column)}：{value}"
                for column, value in row.items()
            )
        )
    return "\n".join(output)
```

- [ ] **Step 4：執行測試，確認通過**

執行：`api/.venv/Scripts/python.exe -m pytest -c api/pyproject.toml api/tests/test_ocr_pipeline.py -q`
預期：全部 PASS

- [ ] **Step 5：Commit**

```bash
git add api/app/ai/cleanup.py api/tests/test_ocr_pipeline.py
git commit -m "OCR-PIPE: clean headers, page numbers, wrapped lines and sheet rows"
```

---

### Task 3：統一入口與 metadata（格式判斷 → 三路 → 清理 → 統一輸出 → RAG 段落）

**Files:**
- Create: `api/app/ai/ingest.py`
- Test: `api/tests/test_ocr_pipeline.py`（加在檔尾）

**Interfaces:**
- Consumes：`cleanup.clean_pages`、`cleanup.sheet_to_text`（Task 2）；既有的 `extractors.extract_document`、`extractors.ocr_page`、`extractors.chunks`、`extractors.ExtractionError`、`extractors.MAX_BYTES`、`extractors.MAX_OCR_IMAGES`、`extractors.IMAGES`；`ocr.enabled`、`ocr.recognize`、`ocr.lines_text`、`ocr.MIN_AVERAGE`。
- Produces：
  - `ingest.Page(page: int, route: str, text: str, seconds: float, confidence: float | None = None)`；`route` 是 `"text_pdf" | "ocr" | "office" | "plain" | "skipped"` 其中之一
  - `ingest.Result(filename: str, pages: list[Page])`，方法：`.text() -> str`、`.chunks() -> list[dict]`（每段有 `filename, page, route, text`）、`.as_dict() -> dict`
  - `ingest.ingest(data: bytes, filename: str) -> Result`；失敗時拋出 `extractors.ExtractionError`

- [ ] **Step 1：寫失敗測試**（加到檔尾，並把下列 import 補到檔頭）

```python
from pypdf import PdfReader, PdfWriter
from app.ai import extractors, ingest
from test_ai_ocr import STARTER_PDF, png


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
    monkeypatch.setattr(
        ocr,
        "recognize",
        lambda data: [
            ("借用設備時請先填寫簽收單並交由部門", 0.95),
            ("主管簽名後再到資訊室領取。", 0.9),
            ("雜訊", 0.2),
        ],
    )


def test_each_pdf_page_records_its_route_time_and_confidence(fake_ocr):
    result = ingest.ingest(mixed_pdf(), "混合文件.pdf")
    assert [p.route for p in result.pages] == ["text_pdf", "ocr"]
    assert [p.page for p in result.pages] == [1, 2]
    scanned = result.pages[1]
    assert (
        scanned.text == "借用設備時請先填寫簽收單並交由部門主管簽名後再到資訊室領取。"
    )
    assert scanned.confidence == 0.93 and scanned.seconds >= 0


def test_chunks_carry_file_name_and_page(fake_ocr):
    chunks = ingest.ingest(mixed_pdf(), "混合文件.pdf").chunks()
    assert {c["page"] for c in chunks} == {1, 2}
    assert all(c["filename"] == "混合文件.pdf" and c["text"] for c in chunks)
    assert next(c for c in chunks if c["page"] == 2)["route"] == "ocr"


def test_scanned_page_is_marked_skipped_when_ocr_is_off(monkeypatch):
    monkeypatch.setattr(ocr, "enabled", lambda: False)
    result = ingest.ingest(mixed_pdf(), "混合文件.pdf")
    assert [p.route for p in result.pages] == ["text_pdf", "skipped"] and result.pages[
        1
    ].text == ""


def test_images_go_through_ocr(fake_ocr):
    result = ingest.ingest(png(), "公告.png")
    assert [(p.page, p.route) for p in result.pages] == [(1, "ocr")]


def test_images_need_ocr(monkeypatch):
    monkeypatch.setattr(ocr, "enabled", lambda: False)
    with pytest.raises(extractors.ExtractionError, match="需OCR"):
        ingest.ingest(png(), "公告.png")


def test_spreadsheets_become_sentences(monkeypatch):
    monkeypatch.setattr(
        extractors,
        "extract_document",
        lambda data, name: (
            "工作表：s（儲存值；公式不重新計算）\nA1=品名 | B1=數量\nA2=鮪魚罐 | B2=3",
            "",
        ),
    )
    result = ingest.ingest(b"zip", "清單.xlsx")
    assert (
        result.pages[0].route == "office"
        and result.text() == "工作表：s\n品名：鮪魚罐；數量：3"
    )


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
```

- [ ] **Step 2：執行測試，確認失敗**

執行：`api/.venv/Scripts/python.exe -m pytest -c api/pyproject.toml api/tests/test_ocr_pipeline.py -q`
預期：FAIL，`ImportError: cannot import name 'ingest'`

- [ ] **Step 3：實作 `api/app/ai/ingest.py`**

```python
"""Unified document intake: judge the format and text layer page by page, extract, clean,
and return text with file-name and page metadata ready for RAG chunking."""

from dataclasses import asdict, dataclass
import io
from pathlib import Path
import time

from pypdf import PdfReader

from app.ai import cleanup, extractors, ocr

TEXT_LAYER_MIN = (
    10  # Same threshold as extractors: fewer characters means the page is a scan.
)


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
        return [
            {
                "filename": self.filename,
                "page": page.page,
                "route": page.route,
                "text": chunk,
            }
            for page in self.pages
            if page.text
            for chunk in extractors.chunks(page.text, size, overlap)
        ]

    def as_dict(self):
        return {
            "filename": self.filename,
            "pages": [asdict(page) for page in self.pages],
            "chunks": self.chunks(),
        }


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
            raise extractors.ExtractionError(
                "檔案無法解析；請確認格式或重新上傳"
            ) from None
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
```

- [ ] **Step 4：執行測試，確認通過**

執行：`api/.venv/Scripts/python.exe -m pytest -c api/pyproject.toml api/tests/test_ocr_pipeline.py api/tests/test_ai_ocr.py -q`
預期：全部 PASS

- [ ] **Step 5：Commit**

```bash
git add api/app/ai/ingest.py api/tests/test_ocr_pipeline.py
git commit -m "OCR-PIPE: unified ingest with per-page route, timing and metadata"
```

---

### Task 4：驗證指標＋虛構標註樣本

**Files:**
- Create: `api/app/ai/ocr_metrics.py`
- Create: `deploy/ocr-eval/make_samples.py`
- Create（由程式產生）：`deploy/ocr-eval/samples/*`
- Test: `api/tests/test_ocr_pipeline.py`（加在檔尾）

**Interfaces:**
- Consumes：`ingest.Page`（Task 3）
- Produces：
  - `ocr_metrics.cer(reference: str, hypothesis: str) -> float`（忽略所有空白）
  - `ocr_metrics.accuracy(reference, hypothesis) -> float`＝`max(0, 1 - cer)`
  - `ocr_metrics.route_stats(pages: list[Page]) -> dict[str, dict]`，每個路徑回傳 `{"pages": int, "seconds": float, "per_page": float}`
  - 樣本資料夾：每個樣本檔旁邊可能有 `<檔名>.gt.txt` 標註答案

- [ ] **Step 1：寫失敗測試**（加到檔尾，並在檔頭的 import 補上 `ocr_metrics`）

```python
from app.ai import ocr_metrics


def test_cer_ignores_whitespace_and_counts_edits():
    assert ocr_metrics.cer("新人 報到\n五樓", "新人報到五樓") == 0
    assert ocr_metrics.cer("新人報到五樓", "新入報到五樓") == pytest.approx(1 / 6)
    assert ocr_metrics.accuracy("新人報到", "") == 0
    assert (
        ocr_metrics.accuracy("新人", "新人報到五樓多出很多字") == 0
    )  # Never negative.


def test_route_stats_report_seconds_per_page():
    pages = [
        ingest.Page(1, "text_pdf", "a", 0.01),
        ingest.Page(2, "ocr", "b", 1.2),
        ingest.Page(3, "ocr", "c", 0.8),
    ]
    stats = ocr_metrics.route_stats(pages)
    assert stats["ocr"] == {"pages": 2, "seconds": 2.0, "per_page": 1.0}
    assert stats["text_pdf"]["pages"] == 1
```

- [ ] **Step 2：執行測試，確認失敗**

執行：`api/.venv/Scripts/python.exe -m pytest -c api/pyproject.toml api/tests/test_ocr_pipeline.py -q`
預期：FAIL，`ImportError: cannot import name 'ocr_metrics'`

- [ ] **Step 3：實作 `api/app/ai/ocr_metrics.py`**

```python
"""Validation numbers for the intake pipeline: character error rate and seconds per page by route."""


def cer(reference, hypothesis):
    """Levenshtein distance over characters divided by the reference length; whitespace is ignored."""
    reference, hypothesis = "".join(reference.split()), "".join(hypothesis.split())
    if not reference:
        return 0.0 if not hypothesis else 1.0
    previous = list(range(len(hypothesis) + 1))
    for i, expected in enumerate(reference, 1):
        current = [i]
        for j, got in enumerate(hypothesis, 1):
            current.append(
                min(
                    previous[j] + 1,
                    current[j - 1] + 1,
                    previous[j - 1] + (expected != got),
                )
            )
        previous = current
    return previous[-1] / len(reference)


def accuracy(reference, hypothesis):
    return max(0.0, 1 - cer(reference, hypothesis))


def route_stats(pages):
    stats = {}
    for page in pages:
        item = stats.setdefault(page.route, {"pages": 0, "seconds": 0.0})
        item["pages"] += 1
        item["seconds"] = round(item["seconds"] + page.seconds, 3)
    for item in stats.values():
        item["per_page"] = round(item["seconds"] / item["pages"], 3)
    return stats
```

- [ ] **Step 4：執行測試，確認通過**

執行：`api/.venv/Scripts/python.exe -m pytest -c api/pyproject.toml api/tests/test_ocr_pipeline.py -q`
預期：全部 PASS

- [ ] **Step 5：寫樣本產生器 `deploy/ocr-eval/make_samples.py`**

```python
"""Generate fictional, labeled samples for the OCR pipeline demo (毛研食品 is fictional).

    api/.venv/Scripts/python.exe deploy/ocr-eval/make_samples.py

Each scanned sample gets <name>.gt.txt with the text a person would type from it (headers, footers and
page numbers excluded, because the cleaned output should not contain them).
"""

import io
from pathlib import Path
import shutil
import zipfile

from docx import Document
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from pypdf import PdfReader, PdfWriter

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "samples"
FONTS = [
    Path(r"C:\Windows\Fonts\msjh.ttc"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    Path("/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc"),
    Path("/System/Library/Fonts/PingFang.ttc"),
]
FONT = next(
    (font for font in FONTS if font.is_file()), None
)  # Windows, Debian/Ubuntu, Arch/Fedora, macOS.
TEXT_PDF = ROOT / "deploy/rag-starter/corpus/04_PDF文件/PDF-001_新人報到簡易指南.pdf"

NOTICE = [
    "新人報到動線公告",
    "十月新人報到改在五樓大會議室，",
    "請於上午九點前完成簽到並領取識別證。",
    "報到當天請攜帶公司配發的筆電與充電器。",
    "如有疑問請洽人資窗口林小姐分機二一五。",
]
LOAN = [
    [
        "設備借用簽收單",
        "借用設備時請先填寫本簽收單並交由部門",
        "主管簽名後再到資訊室領取。",
        "借用品項：筆電一台、滑鼠一個、轉接頭一個。",
    ],
    [
        "歸還與點收",
        "歸還時須由資訊室人員當面點收，若有",
        "損壞請於三個工作天內填寫報修單。",
        "逾期未歸還者將通知部門主管。",
    ],
]
HEADER, FOOTER = "毛研食品 內部文件", "第 {} 頁"


def scan(lines, header=None, footer=None, faint=False):
    font = ImageFont.truetype(str(FONT), 34)
    small = ImageFont.truetype(str(FONT), 22)
    image = Image.new(
        "RGB", (1240, 160 + 70 * len(lines)), (235, 235, 230) if faint else "white"
    )
    draw = ImageDraw.Draw(image)
    ink = (120, 120, 120) if faint else "black"
    if header:
        draw.text((60, 30), header, fill=ink, font=small)
    for index, line in enumerate(lines):
        draw.text((60, 90 + 70 * index), line, fill=ink, font=font)
    if footer:
        draw.text((560, image.height - 50), footer, fill=ink, font=small)
    if faint:
        image = image.rotate(0.8, fillcolor=(235, 235, 230), expand=True).filter(
            ImageFilter.GaussianBlur(1.1)
        )
        image = image.resize((image.width // 2, image.height // 2))
    return image


def png_bytes(image):
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


def xlsx(rows):
    cells = lambda r, row: "".join(
        f'<c r="{"ABC"[c]}{r}" t="inlineStr"><is><t>{v}</t></is></c>'
        for c, v in enumerate(row)
    )
    sheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
        + "".join(
            f'<row r="{r}">{cells(r, row)}</row>' for r, row in enumerate(rows, 1)
        )
        + "</sheetData></worksheet>"
    )
    files = {
        "[Content_Types].xml": '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>',
        "_rels/.rels": '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        "xl/workbook.xml": '<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="採購清單" sheetId="1" r:id="rId1"/></sheets></workbook>',
        "xl/_rels/workbook.xml.rels": '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>',
        "xl/worksheets/sheet1.xml": sheet,
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return buffer.getvalue()


def main():
    if FONT is None:
        raise SystemExit(
            "找不到中文字型；請安裝 Noto Sans CJK（Linux：fonts-noto-cjk）"
        )
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    notice = "\n".join(NOTICE)
    (OUT / "報到公告-清晰.png").write_bytes(png_bytes(scan(NOTICE)))
    (OUT / "報到公告-清晰.png.gt.txt").write_text(notice, encoding="utf-8")
    (OUT / "報到公告-模糊.png").write_bytes(png_bytes(scan(NOTICE, faint=True)))
    (OUT / "報到公告-模糊.png.gt.txt").write_text(notice, encoding="utf-8")

    pages = [scan(lines, HEADER, FOOTER.format(n)) for n, lines in enumerate(LOAN, 1)]
    pages[0].save(
        OUT / "設備借用簽收單-掃描2頁.pdf",
        save_all=True,
        append_images=pages[1:],
        resolution=150,
    )
    (OUT / "設備借用簽收單-掃描2頁.pdf.gt.txt").write_text(
        "\n\n".join("\n".join(p) for p in LOAN), encoding="utf-8"
    )

    scanned = io.BytesIO()
    scan(LOAN[1]).save(scanned, "PDF", resolution=150)
    writer = PdfWriter()
    writer.add_page(PdfReader(TEXT_PDF).pages[0])
    writer.add_page(PdfReader(io.BytesIO(scanned.getvalue())).pages[0])
    with open(OUT / "混合文件-文字頁加掃描頁.pdf", "wb") as stream:
        writer.write(stream)

    shutil.copy(TEXT_PDF, OUT / "文字層PDF-新人報到指南.pdf")

    document = Document()
    document.add_heading("十月新人報到準備會議紀錄", 1)
    document.add_paragraph("時間：十月二十日上午十點，地點：B會議室。")
    document.add_paragraph(
        "決議：新人課程改在十月二十八日上午十點舉行，由人資準備簽到表。"
    )
    document.save(OUT / "會議紀錄.docx")

    (OUT / "採購清單.xlsx").write_bytes(
        xlsx([["品名", "數量", "單價"], ["鮪魚罐", "3", "45"], ["歡迎卡", "20", "12"]])
    )
    print(f"samples written to {OUT}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 6：產生樣本並檢查**

```bash
api/.venv/Scripts/python.exe deploy/ocr-eval/make_samples.py
ls deploy/ocr-eval/samples
```

預期：7 個樣本檔，加上 3 個 `.gt.txt`。用圖片檢視器打開 `報到公告-模糊.png`，確認確實偏灰、模糊、略傾斜，但人眼仍然看得懂。

- [ ] **Step 7：Commit**

```bash
git add api/app/ai/ocr_metrics.py api/tests/test_ocr_pipeline.py deploy/ocr-eval
git commit -m "OCR-PIPE: CER and per-route timing metrics with fictional labeled samples"
```

---

### Task 5：展示 CLI 與 HTML 報告

**Files:**
- Create: `deploy/ocr_pipeline.py`
- Modify: `.gitignore`（加入一行 `output/`）

**Interfaces:**
- Consumes：`ingest.ingest`、`ingest.Result`（Task 3）；`ocr_metrics.accuracy`、`ocr_metrics.route_stats`（Task 4）；`ocr.PREPROCESS`（Task 1）
- Produces：指令 `python deploy/ocr_pipeline.py <資料夾> --models <模型資料夾> [--out output/ocr-report] [--compare-preprocess]`，輸出 `<out>/report.html`、`<out>/result.json`。

- [ ] **Step 1：實作 `deploy/ocr_pipeline.py`**

```python
"""Run the document intake pipeline over a folder and write an HTML + JSON report.

    api/.venv/Scripts/python.exe deploy/ocr_pipeline.py deploy/ocr-eval/samples --models ../ocr-models --compare-preprocess

Files with a <name>.gt.txt beside them are scored by 1-CER. Only reads the folder; writes to --out.
"""

import argparse
from html import escape
import json
import os
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))
from app.ai import extractors, ingest, ocr, ocr_metrics  # noqa: E402

SUPPORTED = {".pdf", ".png", ".jpg", ".jpeg", ".docx", ".xlsx", ".txt", ".csv"}
ROUTE_NAMES = {
    "text_pdf": "文字層PDF",
    "ocr": "掃描→OCR",
    "office": "Word／Excel",
    "plain": "純文字",
    "skipped": "略過",
}


def run(path):
    started = time.perf_counter()
    try:
        result = ingest.ingest(path.read_bytes(), path.name)
    except extractors.ExtractionError as exc:
        return {
            "filename": path.name,
            "error": str(exc),
            "pages": [],
            "chunks": [],
            "seconds": 0,
            "_pages": [],
        }
    item = result.as_dict()
    item["seconds"] = round(time.perf_counter() - started, 3)
    truth = path.with_name(path.name + ".gt.txt")
    if truth.is_file():
        item["accuracy"] = round(
            ocr_metrics.accuracy(truth.read_text(encoding="utf-8"), result.text()), 4
        )
    item["text"] = result.text()
    item["_pages"] = result.pages
    return item


def badge(route):
    return f'<span class="b {route}">{ROUTE_NAMES.get(route, route)}</span>'


def pct(item):
    return f"{item['accuracy']:.1%}" if "accuracy" in item else "—"


def html_report(items, stats, comparison):
    scored = [i["accuracy"] for i in items if "accuracy" in i]
    rows = "".join(
        f"<tr><td>{escape(i['filename'])}</td><td>{''.join(badge(p['route']) for p in i['pages']) or escape(i.get('error', ''))}</td>"
        f"<td>{len(i['pages'])}</td><td>{', '.join(str(p['confidence']) for p in i['pages'] if p['confidence'] is not None) or '—'}</td>"
        f"<td>{i['seconds']}</td><td>{pct(i)}</td><td>{len(i['chunks'])}</td></tr>"
        for i in items
    )
    route_rows = "".join(
        f"<tr><td>{badge(r)}</td><td>{s['pages']}</td><td>{s['seconds']}</td><td>{s['per_page']}</td></tr>"
        for r, s in stats.items()
    )
    ab = "".join(
        f"<tr><td>{escape(n)}</td><td>{off:.1%}</td><td>{on:.1%}</td><td>{on - off:+.1%}</td></tr>"
        for n, off, on in comparison
    )
    details = "".join(
        f"<details><summary>{escape(i['filename'])}</summary><pre>{escape(i.get('text') or i.get('error', ''))}</pre>"
        f"<p class='m'>前 3 段 RAG chunk（含 metadata）</p><pre>{escape(json.dumps([{k: c[k] for k in ('filename', 'page', 'route')} | {'text': c['text'][:60]} for c in i['chunks'][:3]], ensure_ascii=False, indent=1))}</pre></details>"
        for i in items
    )
    average = f"{sum(scored) / len(scored):.1%}" if scored else "—"
    return f"""<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>OCR 管線報告</title><style>
body{{font-family:system-ui,'Microsoft JhengHei',sans-serif;margin:24px auto;max-width:1000px;padding:0 16px;color:#222;background:#fff}}
table{{border-collapse:collapse;width:100%;margin:8px 0 24px}}td,th{{border-bottom:1px solid #ddd;padding:6px 8px;text-align:left}}
.cards{{display:flex;gap:12px;flex-wrap:wrap}}.card{{border:1px solid #ddd;border-radius:8px;padding:12px 16px;min-width:150px}}.card b{{font-size:24px;display:block}}
.b{{display:inline-block;border-radius:4px;padding:1px 6px;margin-right:4px;font-size:12px;color:#fff}}.text_pdf{{background:#2e7d5b}}.ocr{{background:#5b4bb7}}
.office{{background:#2f6f9f}}.plain{{background:#666}}.skipped{{background:#b55}}pre{{white-space:pre-wrap;background:#f6f6f6;padding:8px}}.m{{color:#666}}
</style><h1>OCR 管線報告</h1>
<div class="cards"><div class="card">檔案<b>{len(items)}</b></div><div class="card">頁數<b>{sum(len(i["pages"]) for i in items)}</b></div>
<div class="card">平均辨識正確率（1−CER）<b>{average}</b></div><div class="card">RAG 段落<b>{sum(len(i["chunks"]) for i in items)}</b></div></div>
<h2>逐檔結果</h2><table><tr><th>檔案</th><th>逐頁路徑</th><th>頁</th><th>OCR 信心</th><th>秒</th><th>1−CER</th><th>段落</th></tr>{rows}</table>
<h2>處理時間（分路統計）</h2><table><tr><th>路徑</th><th>頁數</th><th>總秒數</th><th>每頁秒數</th></tr>{route_rows}</table>
{"<h2>前處理 A/B（1−CER）</h2><table><tr><th>檔案</th><th>關閉</th><th>開啟</th><th>差異</th></tr>" + ab + "</table>" if comparison else ""}
<h2>清理後全文與 RAG 段落</h2>{details}</html>"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("folder", type=Path)
    parser.add_argument(
        "--models", type=Path, help="Folder with the Traditional Chinese OCR model"
    )
    parser.add_argument("--out", type=Path, default=Path("output/ocr-report"))
    parser.add_argument("--compare-preprocess", action="store_true")
    args = parser.parse_args()
    if args.models:
        os.environ["PF_ACCEPTANCE_MODE"] = (
            "true"  # The OCR switch is only honoured in isolated runs.
        )
        os.environ["PF_AI_OCR_MODEL_DIR"] = str(args.models.resolve())
    print(
        "OCR", "on" if ocr.enabled() else "off (images and scanned pages are skipped)"
    )
    files = sorted(p for p in args.folder.iterdir() if p.suffix.lower() in SUPPORTED)
    image = next((p for p in files if p.suffix.lower() in extractors.IMAGES), None)
    if ocr.enabled() and image:
        run(image)  # Warm-up so model loading is not counted in the per-page seconds.
    items = [run(path) for path in files]
    stats = ocr_metrics.route_stats([page for item in items for page in item["_pages"]])
    comparison = []
    if args.compare_preprocess and ocr.enabled():
        for item, path in zip(items, files):
            if "accuracy" in item and any(p["route"] == "ocr" for p in item["pages"]):
                ocr.PREPROCESS = False
                off = run(path).get("accuracy", 0.0)
                ocr.PREPROCESS = True
                comparison.append((item["filename"], off, item["accuracy"]))
    for item in items:
        del item["_pages"]
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "result.json").write_text(
        json.dumps(
            {"items": items, "routes": stats, "preprocess_ab": comparison},
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )
    (args.out / "report.html").write_text(
        html_report(items, stats, comparison), encoding="utf-8"
    )
    for item in items:
        print(
            f"{item['filename']}: {[p['route'] for p in item['pages']]} {item.get('accuracy', item.get('error', ''))}"
        )
    print(f"report: {(args.out / 'report.html').resolve()}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2：在 `.gitignore` 加入 `output/`**

- [ ] **Step 3：不使用 OCR 跑一次（確認文字層、Office 路徑和略過標示）**

```bash
api/.venv/Scripts/python.exe deploy/ocr_pipeline.py deploy/ocr-eval/samples --out output/ocr-report-off
```

預期：顯示 `OCR off`。`文字層PDF`、`會議紀錄.docx`、`採購清單.xlsx` 正常；混合文件為 `['text_pdf', 'skipped']`；兩張 PNG 顯示「需OCR」錯誤。命令不會整個失敗。

- [ ] **Step 4：使用真模型並做 A/B 比較**

```bash
api/.venv/Scripts/python.exe deploy/ocr_pipeline.py deploy/ocr-eval/samples --models ../ocr-models --compare-preprocess
```

預期：顯示 `OCR on`。掃描 2 頁 PDF 的路徑為 `['ocr', 'ocr']`，混合文件為 `['text_pdf', 'ocr']`；清晰圖的 1−CER ≥ 95%。打開 `output/ocr-report/report.html`，確認四張卡片、分路統計、A/B 表、每份文件全文裡都沒有「毛研食品 內部文件」和「第 1 頁」。

如果模糊圖在開啟前處理後反而變差，把 `ocr.preprocess` 裡 `autocontrast` 的 `cutoff` 從 1 改成 0，重跑一次並保留兩次結果中較好的設定。不論最後結果好壞，都如實寫進報告；不要為了讓數字好看而挑選樣本。

- [ ] **Step 5：跑一次全量後端測試（排除需要本地模型的測試）**

```bash
api/.venv/Scripts/python.exe -m pytest -c api/pyproject.toml api/tests -q --deselect api/tests/test_ai_local_model.py
```

預期：除了 PROGRESS 已記錄的既有問題外，沒有新的失敗。

- [ ] **Step 6：Commit**

```bash
git add deploy/ocr_pipeline.py .gitignore
git commit -m "OCR-PIPE: demo CLI with HTML report, per-route timing and preprocess A/B"
```

---

### Task 7：可隨處地端部署（OCR 開關、Docker、離線模型、斷網驗證）

RapidOCR 本身在本機用 onnxruntime 在 CPU 上推論，不呼叫雲端。補上「正式環境能開啟」、「映像檔內含 OCR」、「模型可以離線攜帶並驗證」、「斷網也能跑」四件事。時間不夠時，Docker 的部分（Step 5–7）可以延到隔天做，但 Step 1–4 要完成。

**Files:**
- Modify: `api/app/ai/ocr.py`（`model_dir()`）
- Modify: `deploy/ocr_pipeline.py`（`--models` 改設 `PF_AI_OCR`）
- Modify: `deploy/api.Dockerfile`
- Modify: `deploy/docker-compose.yml`（api 服務的 environment 和 volumes）
- Create: `deploy/ocr-models.sha256`（Task 0 下載並核對後產生）
- Test: `api/tests/test_ocr_pipeline.py`（加在檔尾）

**Interfaces:**
- Produces：環境變數 `PF_AI_OCR=true`＋`PF_AI_OCR_MODEL_DIR=<dir>` 可以在任何模式下啟用 OCR；兩者缺一，或模型檔不存在時，OCR 自動關閉，不會報錯。Docker build 參數 `WITH_OCR=true`。

- [ ] **Step 1：寫失敗測試**

```python
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
```

- [ ] **Step 2：執行測試，確認失敗**

執行：`api/.venv/Scripts/python.exe -m pytest -c api/pyproject.toml api/tests/test_ocr_pipeline.py -q -k outside_acceptance`
預期：FAIL，在 `assert ocr.enabled()` 失敗

- [ ] **Step 3：實作**

`api/app/ai/ocr.py` 的 `model_dir()` 開頭：

```python
    if os.environ.get("PF_ACCEPTANCE_MODE") != "true":
        return None
```

改成：

```python
if (
    os.environ.get("PF_AI_OCR") != "true"
    and os.environ.get("PF_ACCEPTANCE_MODE") != "true"
):
    return None  # OCR stays off unless switched on explicitly (any deployment) or in isolated acceptance runs.
```

`deploy/ocr_pipeline.py` 的 `main()` 裡：

```python
os.environ["PF_ACCEPTANCE_MODE"] = (
    "true"  # The OCR switch is only honoured in isolated runs.
)
```

改成：

```python
os.environ["PF_AI_OCR"] = "true"
```

正式文件索引仍然要 `PF_ACCEPTANCE_MODE` 和 `PF_AI_FORMAL_INDEX` 才會啟動，所以這個開關不會讓正式索引自動開始跑 OCR。

- [ ] **Step 4：執行 OCR 相關測試**

執行：`api/.venv/Scripts/python.exe -m pytest -c api/pyproject.toml api/tests/test_ocr_pipeline.py api/tests/test_ai_ocr.py -q`
預期：全部 PASS

- [ ] **Step 5：Dockerfile 加上可選的 OCR**

`deploy/api.Dockerfile` 的：

```dockerfile
COPY api/requirements.lock ./requirements.lock
RUN pip install --no-cache-dir -r requirements.lock
```

改成：

```dockerfile
COPY api/requirements.lock api/requirements-ocr.lock ./
RUN pip install --no-cache-dir -r requirements.lock
# OCR is optional: opencv needs libGL/glib on slim images. Models are mounted at runtime, never baked in.
ARG WITH_OCR=false
RUN if [ "$WITH_OCR" = "true" ]; then \
      apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
      && rm -rf /var/lib/apt/lists/* \
      && pip install --no-cache-dir -r requirements-ocr.lock; \
    fi
```

`deploy/docker-compose.yml` 的 api 服務：在 `environment` 加上

```yaml
      PF_AI_OCR: ${PF_AI_OCR:-false}
      PF_AI_OCR_MODEL_DIR: /opt/ocr-models
```

在 `volumes` 加上

```yaml
      - ${PF_OCR_MODELS_HOST:-./ocr-models}:/opt/ocr-models:ro
```

在 `build` 加上

```yaml
      args:
        WITH_OCR: ${PF_AI_OCR:-false}
```

（沒有設定時，compose 會建立一個空的 `deploy/ocr-models/` 掛進去，`model_dir()` 找不到模型檔，OCR 就會自動關閉。請把 `deploy/ocr-models/` 加進 `.gitignore`。）

- [ ] **Step 6：建置含 OCR 的映像檔，並在斷網容器裡跑完整條管線**（PowerShell，從 repo 根目錄執行）

```powershell
docker build -f deploy/api.Dockerfile --build-arg WITH_OCR=true -t projectflow-api-ocr .
docker run --rm --network none -e PF_AI_OCR=true -e PYTHONPATH=/app `
  -v "${PWD}\..\ocr-models:/opt/ocr-models:ro" `
  -v "${PWD}\deploy\ocr_pipeline.py:/work/ocr_pipeline.py:ro" `
  -v "${PWD}\deploy\ocr-eval\samples:/work/samples:ro" `
  projectflow-api-ocr python /work/ocr_pipeline.py /work/samples --models /opt/ocr-models --out /tmp/report
```

預期：在 `--network none`（完全沒有網路）的 Linux 容器中顯示 `OCR on`，逐檔路徑和 Windows 本機的結果一致，1−CER 的差距在 2 個百分點以內。這同時證明了兩件事：可以跨平台（Windows／Linux），而且完全離線。

如果出現 `libGL.so.1` 錯誤，表示 Step 5 的 apt 套件沒有裝到，檢查 `--build-arg`。如果 rapidocr 嘗試連網下載偵測或方向模型，失敗訊息會出現在這裡。遇到這種情況，從套件的 `site-packages/rapidocr_onnxruntime/models/` 複製 det／cls 模型到 `ocr-models/`，並在 `ocr.engine()` 加上 `det_model_path`、`cls_model_path` 參數。

- [ ] **Step 7：離線攜帶說明**

把下面內容加到 `docs/ai-assistant.md` 的 OCR-PIPE 段落：

- **Docker 主機**：先在有網路的機器上執行 `docker save projectflow-api-ocr -o projectflow-api-ocr.tar`，再把 tar 檔和 `ocr-models/`、`deploy/ocr-models.sha256` 一起帶到目標主機。在目標主機執行 `docker load -i projectflow-api-ocr.tar`，並在 `ocr-models/` 裡執行 `sha256sum -c ../deploy/ocr-models.sha256`，核對通過後才設定 `PF_AI_OCR=true`。
- **沒有 Docker 的 Windows／Linux 主機**：在有網路的機器上執行 `pip download -r api/requirements.lock -r api/requirements-ocr.lock -d wheelhouse --platform <目標平台> --python-version 3.13 --only-binary=:all:`，到目標主機再執行 `pip install --no-index --find-links wheelhouse -r ...`。
- **Windows 免安裝版**：沿用既有的 `deploy/portable`，它已經打包好 OCR 和 C++ runtime。

- [ ] **Step 8：Commit**

```bash
git add api/app/ai/ocr.py api/tests/test_ocr_pipeline.py deploy/ocr_pipeline.py deploy/api.Dockerfile deploy/docker-compose.yml deploy/ocr-models.sha256 .gitignore docs/ai-assistant.md
git commit -m "OCR-PIPE: switch OCR on in any deployment, optional OCR image, offline model check"
```

---

### Task 6：實跑記錄、文件、報告亮點與 Demo 排練

**Files:**
- Modify: `docs/ai-assistant.md`（OCR 段落後加一段「OCR-PIPE」）
- Modify: `docs/PROGRESS.md`（「▶ 現在」）
- Create: `docs/ocr-pipeline-report.md`（報告亮點，數字取自 `output/ocr-report/result.json`）

- [ ] **Step 1（可選，建議做）：加 1～2 張真實翻拍樣本**

用手機拍一張紙本公告（只用虛構或公開內容），放進 `deploy/ocr-eval/samples/`，並手打標註答案到 `<檔名>.gt.txt`，再跑一次 Task 5 Step 4。真實照片的數字要和合成樣本**分開**報告。

- [ ] **Step 2：寫 `docs/ocr-pipeline-report.md`**

依下方「報告亮點」的 9 點撰寫，每點填入 `result.json` 的實際數字（例如：文字層每頁 x 秒、OCR 每頁 y 秒，約 y/x 倍；前處理模糊圖 a%→b%）。最後列出限制：合成樣本、單機 CPU、沒有手寫字和多欄版面、尚未接進正式索引。

- [ ] **Step 3：更新 `docs/ai-assistant.md` 和 `docs/PROGRESS.md`**

`ai-assistant.md` 加一段 3～5 行：入口、指令、輸出位置、與正式索引的關係（尚未接上）、限制。`PROGRESS.md` 的「▶ 現在」：目前工作項目改為 `OCR-PIPE 

---

## 驗收情境

1. 從 repo 根目錄執行 Task 5 Step 4 的指令會成功，並產生 `report.html`。
2. 混合 PDF 的逐頁路徑是「文字層 PDF、掃描→OCR」。
3. 掃描 2 頁 PDF 清理後，不含頁首「毛研食品 內部文件」和頁尾「第 N 頁」，被拆開的句子已經接回。
4. Excel 輸出為「欄位：值」句子；Word 的段落文字完整。
5. 報告顯示每檔的 1−CER、分路每頁秒數，以及前處理 A/B 比較。
6. 每個 RAG 段落都帶 `filename`、`page`、`route`。
7. 沒有設定模型時不會崩潰：圖片顯示「需OCR」，掃描頁標示為「略過」。
8. `test_ocr_pipeline.py` 全部通過，既有的 `test_ai_ocr.py` 不受影響。
9. 在 `--network none` 的 Linux 容器內跑完整條管線，結果和 Windows 本機一致（Task 7 Step 6）。
10. 沒有設定 `PF_AI_OCR`，或沒有模型檔時，OCR 會自動關閉，既有的部署行為不變。