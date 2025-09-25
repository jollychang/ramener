from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict
from typing import Any, Dict, List, Optional

import requests

from .config import AppConfig
from .metadata import DocumentMetadata, GenerationResult


logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are an assistant that extracts metadata from PDF documents. "
    "Always respond with a single JSON object using keys date, source, title, confidence. "
    "Use null for unknown values. Date must use the YYYY-MM-DD format. "
    "Do not include any extra commentary."
)

JSON_SCHEMA_EXAMPLE = {
    "date": "2024-03-01",
    "source": "World Health Organization",
    "title": "Influenza Weekly Report",
    "confidence": 0.76,
}

DATE_PATTERN = re.compile(
    r"(20\d{2}|19\d{2})[./-](0?[1-9]|1[0-2])[./-](0?[1-9]|[12]\d|3[01])"
)


class BailianError(Exception):
    pass


def _find_candidate_dates(text: str, limit: int = 5) -> List[str]:
    seen: List[str] = []
    for match in DATE_PATTERN.finditer(text):
        candidate = match.group(0)
        if candidate not in seen:
            seen.append(candidate)
        if len(seen) >= limit:
            break
    return seen


def _build_user_prompt(excerpt: str) -> str:
    candidates = _find_candidate_dates(excerpt)
    guidance = "Candidate dates: " + ", ".join(candidates) if candidates else "No obvious dates detected."
    template = (
        "Extract publication metadata from the following document excerpt.\n"
        "Return a JSON object matching this schema: {schema}.\n"
        "If the excerpt only contains month and year, output the first day of that month.\n"
        "If the source is an author or organization, return their name.\n"
        "Truncate title to under 120 characters if needed.\n\n"
        "Excerpt:\n---\n{excerpt}\n---\n\n{guidance}"
    )
    return template.format(schema=json.dumps(JSON_SCHEMA_EXAMPLE), excerpt=excerpt, guidance=guidance)


def _extract_json_block(content: str) -> str:
    try:
        return json.dumps(json.loads(content))
    except json.JSONDecodeError:
        pass

    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise BailianError("Model response did not contain JSON data.")
    raw = content[start : end + 1]
    try:
        json.loads(raw)
    except json.JSONDecodeError as exc:
        raise BailianError("Unable to parse JSON from model response.") from exc
    return raw


def _coerce_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class BailianClient:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        base = config.base_url.rstrip("/")
        self.endpoint = f"{base}/chat/completions"

    def _request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        response = requests.post(
            self.endpoint,
            json=payload,
            headers=headers,
            timeout=self.config.request_timeout,
        )
        if response.status_code >= 400:
            raise BailianError(
                f"HTTP {response.status_code}: {response.text[:400]}"
            )
        return response.json()

    def analyze_document(self, excerpt: str) -> GenerationResult:
        user_prompt = _build_user_prompt(excerpt)
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }

        logger.debug("Sending payload: %s", json.dumps(payload))
        data = self._request(payload)

        try:
            choices = data["choices"]
            message = choices[0]["message"]
            content = message["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise BailianError(f"Unexpected API response: {data}") from exc

        json_block = _extract_json_block(content)
        parsed = json.loads(json_block)

        metadata = DocumentMetadata(
            date=parsed.get("date"),
            source=parsed.get("source"),
            title=parsed.get("title"),
            confidence=_coerce_float(parsed.get("confidence")),
        )

        logger.debug("Parsed metadata: %s", asdict(metadata))
        return GenerationResult(metadata=metadata, raw_response=json_block)
