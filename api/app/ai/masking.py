"""Rule-based masking for content that could leave the company. The mapping never leaves this process.

Free text cannot be masked perfectly (for example "提高到六成"), so confidential documents are excluded
from cloud content entirely instead of relying on masking.
"""
import re

# Order matters: amounts before bare percentages so "NT$185" is one placeholder, not two.
RULES = [
    ("Email", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    # Needs a separator or a mobile prefix, so tax IDs and order numbers are not taken for phones.
    ("電話", re.compile(r"(?<![\d-])(?:(?:\+886[-\s]?|0)\d{1,2}[-\s]\d{3,4}[-\s]?\d{3,4}|\(0\d{1,2}\)\s?\d{3,4}[-\s]?\d{4}|09\d{2}[-\s]?\d{3}[-\s]?\d{3})(?!\d)")),
    ("金額", re.compile(r"(?:NT\$|NTD|新臺幣|新台幣|台幣|\$)\s*\d[\d,]*(?:\.\d+)?(?:\s*(?:萬|億|千)?元?)?|\d[\d,]*(?:\.\d+)?\s*(?:(?:萬|億)元?|千元|元)(?![件素])")),
    ("比例", re.compile(r"\d+(?:\.\d+)?\s*(?:%|％)|百分之[零一二兩三四五六七八九十百\d]+")),
]


class Masker:
    """Same value, same placeholder, across every text masked by one instance."""

    def __init__(self, terms=()):
        # Longest names first so "青禾原料行" wins over "青禾".
        names = sorted({t.strip() for t in terms if t and len(t.strip()) >= 2}, key=len, reverse=True)
        self.rules = ([("廠商", re.compile("|".join(map(re.escape, names))))] if names else []) + RULES
        self.mapping, self.counts, self._values = {}, {}, {}

    def placeholder(self, kind, value):
        key = (kind, value)
        if key not in self._values:
            self.counts[kind] = self.counts.get(kind, 0) + 1
            token = "{{" + f"{kind}_{self.counts[kind]}" + "}}"
            self._values[key] = token
            self.mapping[token] = value
        return self._values[key]

    def mask(self, text):
        for kind, pattern in self.rules:
            text = pattern.sub(lambda match: self.placeholder(kind, match.group(0)), text)
        return text


def unmask(text, mapping):
    """Restore placeholders from a cloud reply; unknown placeholders are left untouched."""
    return re.sub(r"\{\{[^{}]{1,40}\}\}", lambda match: mapping.get(match.group(0), match.group(0)), text)
