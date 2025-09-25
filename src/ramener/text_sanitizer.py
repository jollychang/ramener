from __future__ import annotations

import re


EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
LONG_NUMBER_PATTERN = re.compile(r"\b\d{6,}\b")
ID_TOKEN_PATTERN = re.compile(
    r"(booking|order|invoice|reservation|confirmation)[^\w\n]{0,5}#?\s*\d+",
    re.IGNORECASE,
)
PHONE_PATTERN = re.compile(r"\+?\d[\d\s-]{7,}\d")


def sanitize_excerpt(text: str) -> str:
    """Redact obvious PII fragments before sending to the LLM."""

    def _mask_match(match: re.Match[str]) -> str:
        token = match.group(0)
        return "<REDACTED>"

    redacted = EMAIL_PATTERN.sub("<REDACTED_EMAIL>", text)
    redacted = LONG_NUMBER_PATTERN.sub("<REDACTED_NUMBER>", redacted)
    redacted = ID_TOKEN_PATTERN.sub("<REDACTED_ID>", redacted)
    redacted = PHONE_PATTERN.sub("<REDACTED_PHONE>", redacted)
    return redacted
