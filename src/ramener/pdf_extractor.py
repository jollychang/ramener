from __future__ import annotations

from pathlib import Path
from typing import Iterable

from pypdf import PdfReader


class PdfExtractionError(Exception):
    pass


def extract_text(path: Path, page_limit: int, max_chars: int) -> str:
    if page_limit <= 0:
        raise ValueError("page_limit must be positive")

    try:
        reader = PdfReader(str(path))
    except Exception as exc:  # pragma: no cover - defensive
        raise PdfExtractionError(f"Failed to read PDF: {exc}") from exc

    pages_to_read: Iterable[int] = range(min(page_limit, len(reader.pages)))
    collected: list[str] = []

    for idx in pages_to_read:
        try:
            page = reader.pages[idx]
            text = page.extract_text() or ""
        except Exception as exc:  # pragma: no cover - defensive
            raise PdfExtractionError(f"Failed to extract page {idx + 1}: {exc}") from exc
        cleaned = " ".join(text.split())
        if cleaned:
            collected.append(f"[Page {idx + 1}] {cleaned}")
        if sum(len(chunk) for chunk in collected) >= max_chars:
            break

    merged = "\n".join(collected)[:max_chars]
    if not merged:
        raise PdfExtractionError("No extractable text found in the first pages of the PDF.")

    return merged
