from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

PAGE_TAG_PATTERN = re.compile(r"\[Page \d+\]\s*")
COMPANY_SUFFIX_PATTERN = re.compile(
    r"(股份有限责任公司|股份有限公司|集团股份有限公司|集团有限公司|有限责任公司|有限公司)$"
)

REPORT_PATTERN = re.compile(
    r"(?P<company>[\u4e00-\u9fffA-Za-z（）()·\s]{2,60}?)"
    r"\s*(?:股份有限责任公司|股份有限公司|集团股份有限公司|集团有限公司|有限责任公司|有限公司)?"
    r"\s*(?P<year>19\d{2}|20\d{2})年"
    r"\s*(?P<period>第?[一二三四1234]季度|半年度|半年|年度|上半年|下半年|全年)?"
    r"\s*(?P<type>报告书|报告|报)",
    re.IGNORECASE,
)


def _normalize_company(name: str) -> str:
    collapsed = re.sub(r"\s+", " ", name).strip()
    collapsed = COMPANY_SUFFIX_PATTERN.sub("", collapsed)
    return collapsed.strip(" _-")


def _normalize_descriptor(period: str, type_word: str) -> str:
    period_clean = (period or "").strip()
    type_clean = (type_word or "").strip()
    label = f"{period_clean}{type_clean}" or type_clean or period_clean

    replacements = {
        "半年度报告书": "半年报",
        "半年度报告": "半年报",
        "半年报告": "半年报",
        "年度报告书": "年报",
        "年度报告": "年报",
        "年报告": "年报",
        "报告书": "报告",
    }
    for key, value in replacements.items():
        if key in label:
            return value

    if label in {"报", "报告"}:
        return "报告"

    if "季度" in label and "报告" not in label:
        return f"{label}报告"

    return label or "报告"


@dataclass(frozen=True)
class TitleGuess:
    title: str
    source: Optional[str] = None


def guess_title_from_text(text: str) -> Optional[TitleGuess]:
    if not text:
        return None

    searchable = PAGE_TAG_PATTERN.sub(" ", text)

    for match in REPORT_PATTERN.finditer(searchable):
        company_raw = match.group("company") or ""
        company = _normalize_company(company_raw)
        if len(company) < 2:
            continue

        year = match.group("year") or ""
        descriptor = _normalize_descriptor(match.group("period") or "", match.group("type") or "")

        title = f"{company} {year} 年{descriptor}"
        title = re.sub(r"\s+", " ", title).strip()
        if title:
            return TitleGuess(title=title[:120], source=company)

    return None
