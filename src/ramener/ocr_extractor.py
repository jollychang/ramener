from __future__ import annotations

import logging
import base64
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, TYPE_CHECKING


logger = logging.getLogger(__name__)


class OcrUnavailableError(Exception):
    """Raised when optional OCR dependencies are missing."""


class OcrExtractionError(Exception):
    """Raised when OCR processing fails despite dependencies being present."""


@dataclass
class OcrOptions:
    page_limit: int
    dpi: int = 300


if TYPE_CHECKING:  # pragma: no cover - import cycle guard
    from .llm_client import BailianClient


def _load_dependencies():
    try:
        from pdf2image import convert_from_path  # type: ignore
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise OcrUnavailableError(
            "pdf2image is not installed. Install optional OCR dependencies to enable fallback."
        ) from exc

    try:
        from PIL import Image  # noqa: F401
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise OcrUnavailableError(
            "Pillow is not installed. Install optional OCR dependencies to enable fallback."
        ) from exc

    return convert_from_path


def _encode_image(image) -> str:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return encoded


def extract_text_via_ocr(
    client: "BailianClient", path: Path, options: OcrOptions
) -> str:
    convert_from_path = _load_dependencies()

    limit = options.page_limit if options.page_limit > 0 else None

    try:
        images = convert_from_path(
            str(path),
            dpi=options.dpi,
            first_page=1,
            last_page=limit,
        )
    except Exception as exc:  # pragma: no cover - defensive
        raise OcrExtractionError(f"Failed to render PDF pages for OCR: {exc}") from exc

    if not images:
        raise OcrExtractionError("OCR conversion produced no images.")

    encoded_images = []
    for image in images:
        encoded_images.append(_encode_image(image))

    from .llm_client import BailianError  # Local import to avoid circular dependency

    try:
        transcription = client.ocr_images(encoded_images)
    except BailianError as exc:
        raise OcrExtractionError(f"LLM OCR failed: {exc}") from exc
    except Exception as exc:  # pragma: no cover - defensive
        raise OcrExtractionError(f"LLM OCR failed: {exc}") from exc

    cleaned = transcription.strip()
    if not cleaned:
        raise OcrExtractionError("LLM OCR returned empty transcription.")

    logger.info(
        "LLM OCR fallback extracted %d characters across %d pages (limit=%s)",
        len(cleaned),
        len(encoded_images),
        limit if limit is not None else "all",
    )

    return cleaned
