from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from .config import AppConfig
from .file_ops import (
    FileOperationError,
    copy_pdf,
    generate_destination,
    move_original_to_trash,
)
from .llm_client import BailianClient, BailianError
from .metadata import DocumentMetadata
from .naming import FilenameBuildError, build_filename
from .ocr_extractor import (
    OcrExtractionError,
    OcrOptions,
    OcrUnavailableError,
    extract_text_via_ocr,
)
from .pdf_extractor import PdfExtractionError, extract_text
from .text_sanitizer import sanitize_excerpt
from .title_heuristics import guess_title_from_text


def _configure_logging(log_path: str | None, verbose: bool) -> None:
    handlers = [logging.StreamHandler(sys.stderr)]
    if log_path:
        handlers.append(logging.FileHandler(log_path))
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        handlers=handlers,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rename PDF using AI metadata extraction.")
    parser.add_argument("pdf", help="Path to the PDF file to process.")
    parser.add_argument("--api-key", dest="api_key", help="Override API key.")
    parser.add_argument("--base-url", dest="base_url", help="Override API base URL.")
    parser.add_argument("--model", dest="model", help="Model name to use.")
    parser.add_argument(
        "--ocr-model",
        dest="ocr_model",
        help="Model to use when performing OCR via the LLM (defaults to --model).",
    )
    parser.add_argument(
        "--page-limit",
        dest="page_limit",
        type=int,
        help="Limit pages read from the PDF (default 3; set 0 to read all).",
    )
    parser.add_argument(
        "--timeout", dest="timeout", type=float, help="HTTP timeout in seconds."
    )
    parser.add_argument(
        "--max-text-chars",
        dest="max_text_chars",
        type=int,
        help="Limit characters sent to the model (default 12000; set 0 to send all).",
    )
    parser.add_argument("--log-file", dest="log_file", help="Write detailed logs to this file.")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true", help="Do not modify files.")
    parser.add_argument(
        "--verbose", dest="verbose", action="store_true", help="Enable verbose logging."
    )
    return parser.parse_args(argv)


def _validate_pdf_path(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Input file does not exist: {path}")
    if not path.is_file():
        raise FileNotFoundError(f"Input path is not a file: {path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError("Only PDF files are supported.")


def _log_metadata(metadata: DocumentMetadata) -> None:
    logging.info(
        "Metadata extracted: date=%s source=%s title=%s confidence=%s",
        metadata.date,
        metadata.source,
        metadata.title,
        metadata.confidence,
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    config = AppConfig.from_env(
        api_key=args.api_key,
        base_url=args.base_url,
        model=args.model,
        ocr_model=args.ocr_model,
        page_limit=args.page_limit,
        request_timeout=args.timeout,
        max_text_chars=args.max_text_chars,
        log_path=args.log_file,
    )

    _configure_logging(config.log_path, args.verbose)

    logging.info(
        "Effective limits → page_limit=%s, max_text_chars=%s",
        "all" if config.page_limit <= 0 else config.page_limit,
        "all" if config.max_text_chars <= 0 else config.max_text_chars,
    )
    logging.info(
        "Using models → metadata=%s ocr=%s",
        config.model,
        config.ocr_model or config.model,
    )

    pdf_path = Path(args.pdf).expanduser()

    try:
        _validate_pdf_path(pdf_path)
    except (FileNotFoundError, ValueError) as exc:
        logging.error("%s", exc)
        return 2

    logging.info("Processing %s", pdf_path)

    client = BailianClient(config)

    try:
        excerpt = extract_text(pdf_path, config.page_limit, config.max_text_chars)
    except PdfExtractionError as exc:
        logging.warning("PDF extraction failed: %s. Attempting OCR fallback.", exc)
        try:
            excerpt = extract_text_via_ocr(
                client,
                pdf_path,
                OcrOptions(page_limit=config.page_limit),
            )
        except OcrUnavailableError as ocr_exc:
            logging.error("OCR fallback unavailable: %s", ocr_exc)
            return 3
        except OcrExtractionError as ocr_exc:
            logging.error("OCR fallback failed: %s", ocr_exc)
            return 3
        else:
            logging.info("OCR fallback succeeded; continuing with extracted text.")

    sanitized_excerpt = sanitize_excerpt(excerpt)
    if sanitized_excerpt != excerpt:
        logging.debug("Excerpt sanitized before LLM request.")

    logging.info(
        "Excerpt for LLM → original_chars=%d sanitized_chars=%d",
        len(excerpt),
        len(sanitized_excerpt),
    )

    try:
        generation = client.analyze_document(sanitized_excerpt)
    except BailianError as exc:
        logging.error("LLM request failed: %s", exc)
        return 4

    metadata = generation.metadata

    if not metadata.title or not metadata.title.strip():
        guess = guess_title_from_text(excerpt)
        if guess:
            metadata.title = guess.title
            if not metadata.source and guess.source:
                metadata.source = guess.source
            logging.info("Title fallback applied from PDF text: %s", metadata.title)

    _log_metadata(metadata)

    try:
        target_name = build_filename(metadata, pdf_path)
    except FilenameBuildError as exc:
        logging.error("Filename creation failed: %s", exc)
        return 5

    destination = generate_destination(pdf_path, target_name)

    if args.dry_run:
        logging.info("Dry run enabled. New file would be: %s", destination)
        return 0

    try:
        copy_pdf(pdf_path, destination)
        move_original_to_trash(pdf_path)
    except FileOperationError as exc:
        logging.error("File operations failed: %s", exc)
        return 6

    logging.info("Renamed copy saved to %s", destination)
    print(destination)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
