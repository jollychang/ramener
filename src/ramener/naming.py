from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Optional

from dateutil import parser

from .metadata import DocumentMetadata


INVALID_CHARS_PATTERN = re.compile(r"[\\/:*?\"<>|]+")
WHITESPACE_COLLAPSE = re.compile(r"\s+")


class FilenameBuildError(Exception):
    pass


def _sanitize_segment(value: str, max_length: int = 60) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKC", value)
    printable = "".join(ch for ch in normalized if ch.isprintable())
    cleaned = INVALID_CHARS_PATTERN.sub("_", printable)
    cleaned = WHITESPACE_COLLAPSE.sub(" ", cleaned)
    cleaned = cleaned.replace("\u2028", " ").replace("\u2029", " ")
    cleaned = cleaned.strip(" _-")
    if not cleaned:
        return ""
    limited = cleaned[:max_length].rstrip()
    return limited


def _normalize_date(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    try:
        dt = parser.parse(value, default=datetime(2000, 1, 1))
    except (parser.ParserError, ValueError):
        return None
    return dt.date().isoformat()


def build_filename(
    metadata: DocumentMetadata,
    original_path: Path,
    fallback_prefix: Optional[str] = None,
) -> str:
    if original_path.suffix.lower() != ".pdf":
        raise FilenameBuildError("Only PDF files are supported for renaming.")

    date_value = _normalize_date(metadata.date) or datetime.now().date().isoformat()
    source_value = _sanitize_segment(metadata.source or "")
    title_value = _sanitize_segment(metadata.title or fallback_prefix or original_path.stem)

    parts = [date_value]
    if source_value:
        parts.append(source_value)
    if title_value:
        parts.append(title_value)

    filename = "_".join(parts) + original_path.suffix.lower()
    return filename
