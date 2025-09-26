from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable

from pypdf import PdfReader


logger = logging.getLogger(__name__)


class PdfExtractionError(Exception):
    pass


def extract_text(path: Path, page_limit: int, max_chars: int) -> str:
    try:
        reader = PdfReader(str(path))
    except Exception as exc:  # pragma: no cover - defensive
        raise PdfExtractionError(f"Failed to read PDF: {exc}") from exc

    total_pages = len(reader.pages)
    limit = page_limit if page_limit > 0 else total_pages
    limit = min(limit, total_pages)
    pages_to_read: Iterable[int] = range(limit)
    collected: list[str] = []
    char_limit = max_chars if max_chars > 0 else None
    current_length = 0

    for idx in pages_to_read:
        try:
            page = reader.pages[idx]
            text = page.extract_text() or ""
        except Exception as exc:  # pragma: no cover - defensive
            raise PdfExtractionError(f"Failed to extract page {idx + 1}: {exc}") from exc
        cleaned = " ".join(text.split())
        if cleaned:
            chunk = f"[Page {idx + 1}] {cleaned}"
            collected.append(chunk)
            if char_limit is not None:
                current_length += len(chunk)
        if char_limit is not None and current_length >= char_limit:
            break

    merged = "\n".join(collected)
    if char_limit is not None:
        merged = merged[:char_limit]
    if not merged:
        raise PdfExtractionError("No extractable text found in the PDF.")

    logger.info(
        "PDF text extracted → pages_with_text=%d total_pages=%d chars=%d char_limit=%s",
        len(collected),
        total_pages,
        len(merged),
        char_limit if char_limit is not None else "none",
    )

    return merged
