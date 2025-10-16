from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
from pathlib import Path

from .config import AppConfig, DEFAULT_KEY_FILE
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
from .settings import load_user_settings


def _configure_logging(log_path: str | None, verbose: bool) -> None:
    handlers = [logging.StreamHandler(sys.stderr)]
    if log_path:
        log_file = Path(log_path).expanduser()
        try:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            handlers.append(logging.FileHandler(log_file))
        except OSError as exc:  # pragma: no cover - filesystem permissions
            print(f"Warning: failed to open log file {log_file}: {exc}", file=sys.stderr)
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        handlers=handlers,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def _collect_mac_open_documents(timeout: float = 1.25) -> list[str]:
    """Capture Finder 'open document' events when running as a macOS app bundle."""
    if sys.platform != "darwin":
        return []
    try:
        from Cocoa import (  # type: ignore
            NSApplication,
            NSApplicationActivationPolicyProhibited,
            NSObject,
        )
        from PyObjCTools import AppHelper  # type: ignore
        import objc  # type: ignore
    except ImportError:
        return []

    class _OpenCollector(NSObject):  # type: ignore
        def init(self):  # pragma: no cover - macOS only
            self = objc.super(_OpenCollector, self).init()
            if self is None:
                return None
            self._paths = []
            return self

        def application_openFile_(self, _app, filename):  # pragma: no cover - macOS only
            if filename:
                self._paths.append(str(filename))
            AppHelper.callAfter(AppHelper.stopEventLoop)
            return True

        def application_openFiles_(self, _app, filenames):  # pragma: no cover - macOS only
            for name in filenames or []:
                if name:
                    self._paths.append(str(name))
            AppHelper.callAfter(AppHelper.stopEventLoop)

    app = NSApplication.sharedApplication()
    collector = _OpenCollector.alloc().init()  # type: ignore[call-arg]
    if collector is None:  # pragma: no cover - defensive
        return []
    app.setDelegate_(collector)
    if hasattr(app, "setActivationPolicy_"):
        app.setActivationPolicy_(NSApplicationActivationPolicyProhibited)

    AppHelper.callLater(timeout, AppHelper.stopEventLoop)
    AppHelper.runConsoleEventLoop(installInterrupt=False)  # pragma: no cover - macOS only

    paths = [str(Path(path).expanduser()) for path in collector._paths]  # type: ignore[attr-defined]
    app.setDelegate_(None)
    return paths


def _finder_selected_pdfs() -> list[str]:
    """Read the current Finder selection via AppleScript."""
    if sys.platform != "darwin":
        return []

    script = r"""
        tell application "Finder"
            set theSelection to selection as list
            if theSelection is {} then return ""
            set collected to {}
            repeat with anItem in theSelection
                try
                    set end of collected to POSIX path of (anItem as alias)
                end try
            end repeat
            set AppleScript's text item delimiters to "\n"
            return collected as string
        end tell
    """
    try:
        result = subprocess.run(
            ["/usr/bin/osascript", "-e", script],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return []

    if result.returncode != 0:
        return []

    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _prompt_for_pdf_dialog() -> str | None:
    """Fallback to an AppleScript open panel when no path is supplied."""
    if sys.platform != "darwin":
        return None

    script = r"""
        try
            set theFile to choose file of type {"com.adobe.pdf"} with prompt "请选择要重命名的 PDF 文件："
            return POSIX path of theFile
        on error number -128 -- user cancelled the dialog
            return ""
        on error errMsg number errNum
            try
                display alert "Ramener" message errMsg
            end try
            return ""
        end try
    """

    try:
        result = subprocess.run(
            ["/usr/bin/osascript", "-e", script],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None

    if result.returncode != 0:
        return None

    path = result.stdout.strip()
    return path or None


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rename PDF using AI metadata extraction.")
    parser.add_argument("pdf", nargs="?", help="Path to the PDF file to process.")
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
    parser.add_argument(
        "--settings",
        dest="open_settings",
        action="store_true",
        help="Open the macOS settings window and exit.",
    )
    args, extras = parser.parse_known_args(argv)

    pdf_candidates: list[str] = []
    unexpected: list[str] = []
    saw_process_serial = False

    for item in extras:
        if item.startswith("-psn_"):
            saw_process_serial = True
            continue
        candidate = Path(item).expanduser()
        if candidate.exists():
            pdf_candidates.append(str(candidate))
        else:
            unexpected.append(item)

    if not args.pdf and pdf_candidates:
        args.pdf = pdf_candidates.pop(0)

    if not args.pdf and (saw_process_serial or getattr(sys, "frozen", False)):
        for candidate in _collect_mac_open_documents():
            path = Path(candidate).expanduser()
            if not path.exists():
                continue
            if path.suffix.lower() != ".pdf":
                continue
            if args.pdf:
                pdf_candidates.append(str(path))
            else:
                args.pdf = str(path)
        if args.pdf and pdf_candidates:
            parser.error("Only one PDF can be processed at a time.")
        if not args.pdf:
            selection = _finder_selected_pdfs()
            pdf_paths = []
            for item in selection:
                candidate = Path(item).expanduser()
                if not candidate.exists():
                    continue
                if candidate.suffix.lower() != ".pdf":
                    continue
                pdf_paths.append(str(candidate))
            if pdf_paths:
                args.pdf = pdf_paths.pop(0)
                pdf_candidates.extend(pdf_paths)
    if pdf_candidates:
        parser.error("Only one PDF can be processed at a time.")

    if unexpected:
        parser.error(f"Unexpected arguments: {' '.join(unexpected)}")

    if not args.pdf and not (saw_process_serial or getattr(sys, "frozen", False)):
        parser.error("You must provide a PDF file path.")

    setattr(args, "_saw_process_serial", saw_process_serial)

    return args


def _launch_settings_ui() -> int:
    try:
        from .settings_ui import main as settings_main
    except ImportError as exc:  # pragma: no cover - defensive
        logging.error("Settings UI unavailable: %s", exc)
        return 1
    return settings_main()


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


def _user_has_configuration() -> bool:
    if os.environ.get("RAMENER_API_KEY"):
        return True
    api_key_file = os.environ.get("RAMENER_API_KEY_FILE")
    if api_key_file and Path(api_key_file).expanduser().exists():
        return True
    if DEFAULT_KEY_FILE.expanduser().exists():
        return True
    settings = load_user_settings()
    return settings.api_key is not None


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    if args.open_settings:
        return _launch_settings_ui()

    if not args.pdf and (getattr(args, "_saw_process_serial", False) or getattr(sys, "frozen", False)):
        if _user_has_configuration():
            chosen = _prompt_for_pdf_dialog()
            if chosen:
                args.pdf = chosen
        else:
            return _launch_settings_ui()

    if not args.pdf:
        print("No PDF file supplied. Relaunch with a PDF or run Finder integration.", file=sys.stderr)
        return 2

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
