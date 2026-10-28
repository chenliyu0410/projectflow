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
FONTS = [Path(r"C:\Windows\Fonts\msjh.ttc"), Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
         Path("/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc"), Path("/System/Library/Fonts/PingFang.ttc")]
FONT = next((font for font in FONTS if font.is_file()), None)  # Windows, Debian/Ubuntu, Arch/Fedora, macOS.
TEXT_PDF = ROOT / "deploy/rag-starter/corpus/04_PDF文件/PDF-001_新人報到簡易指南.pdf"

NOTICE = ["新人報到動線公告", "十月新人報到改在五樓大會議室，", "請於上午九點前完成簽到並領取識別證。",
          "報到當天請攜帶公司配發的筆電與充電器。", "如有疑問請洽人資窗口林小姐分機二一五。"]
LOAN = [["設備借用簽收單", "借用設備時請先填寫本簽收單並交由部門", "主管簽名後再到資訊室領取。",
         "借用品項：筆電一台、滑鼠一個、轉接頭一個。"],
        ["歸還與點收", "歸還時須由資訊室人員當面點收，若有", "損壞請於三個工作天內填寫報修單。",
         "逾期未歸還者將通知部門主管。"]]
HEADER, FOOTER = "毛研食品 內部文件", "第 {} 頁"


def scan(lines, header=None, footer=None, faint=False):
    font = ImageFont.truetype(str(FONT), 34)
    small = ImageFont.truetype(str(FONT), 22)
    image = Image.new("RGB", (1240, 160 + 70 * len(lines)), (235, 235, 230) if faint else "white")
    draw = ImageDraw.Draw(image)
    ink = (120, 120, 120) if faint else "black"
    if header:
        draw.text((60, 30), header, fill=ink, font=small)
    for index, line in enumerate(lines):
        draw.text((60, 90 + 70 * index), line, fill=ink, font=font)
    if footer:
        draw.text((560, image.height - 50), footer, fill=ink, font=small)
    if faint:
        image = image.rotate(0.8, fillcolor=(235, 235, 230), expand=True).filter(ImageFilter.GaussianBlur(1.1))
        image = image.resize((image.width // 2, image.height // 2))
    return image


def png_bytes(image):
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


def xlsx(rows):
    cells = lambda r, row: "".join(
        f'<c r="{"ABC"[c]}{r}" t="inlineStr"><is><t>{v}</t></is></c>' for c, v in enumerate(row))
    sheet = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
             + "".join(f'<row r="{r}">{cells(r, row)}</row>' for r, row in enumerate(rows, 1))
             + "</sheetData></worksheet>")
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
        raise SystemExit("找不到中文字型；請安裝 Noto Sans CJK（Linux：fonts-noto-cjk）")
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    notice = "\n".join(NOTICE)
    (OUT / "報到公告-清晰.png").write_bytes(png_bytes(scan(NOTICE)))
    (OUT / "報到公告-清晰.png.gt.txt").write_text(notice, encoding="utf-8")
    (OUT / "報到公告-模糊.png").write_bytes(png_bytes(scan(NOTICE, faint=True)))
    (OUT / "報到公告-模糊.png.gt.txt").write_text(notice, encoding="utf-8")

    pages = [scan(lines, HEADER, FOOTER.format(n)) for n, lines in enumerate(LOAN, 1)]
    pages[0].save(OUT / "設備借用簽收單-掃描2頁.pdf", save_all=True, append_images=pages[1:], resolution=150)
    (OUT / "設備借用簽收單-掃描2頁.pdf.gt.txt").write_text("\n\n".join("\n".join(p) for p in LOAN), encoding="utf-8")

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
    document.add_paragraph("決議：新人課程改在十月二十八日上午十點舉行，由人資準備簽到表。")
    document.save(OUT / "會議紀錄.docx")

    (OUT / "採購清單.xlsx").write_bytes(xlsx([["品名", "數量", "單價"], ["鮪魚罐", "3", "45"], ["歡迎卡", "20", "12"]]))
    print(f"samples written to {OUT}")


if __name__ == "__main__":
    main()
