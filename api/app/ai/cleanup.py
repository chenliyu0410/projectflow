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
    return {line for line, count in counts.items() if count >= max(2, (len(pages) + 1) // 2)}


def strip_edges(lines, repeated):
    """Only the first and last two lines are checked, so numbers inside a form are never dropped."""
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
        if (len(previous) >= MIN_WRAPPED and not previous.endswith(SENTENCE_END)
                and CJK.match(previous[-1]) and CJK.match(line)):
            merged[-1] = previous + line
        else:
            merged.append(line)
    return merged


def clean_pages(texts):
    pages = [[line.strip() for line in text.splitlines() if line.strip()] for text in texts]
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
        output.append("；".join(f"{header.get(column, column)}：{value}" for column, value in row.items()))
    return "\n".join(output)
