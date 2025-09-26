import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_MODEL = "qwen3-omni-flash"
DEFAULT_PAGE_LIMIT = 3
DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_TEXT_CHARS = 12000
DEFAULT_KEY_FILE = Path.home() / ".config" / "ramener" / "api_key"


@dataclass
class AppConfig:
    api_key: str
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    page_limit: int = DEFAULT_PAGE_LIMIT
    request_timeout: float = DEFAULT_TIMEOUT
    max_text_chars: int = DEFAULT_MAX_TEXT_CHARS
    log_path: Optional[str] = None
    ocr_model: Optional[str] = None

    @classmethod
    def from_env(
        cls,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        ocr_model: Optional[str] = None,
        page_limit: Optional[int] = None,
        request_timeout: Optional[float] = None,
        max_text_chars: Optional[int] = None,
        log_path: Optional[str] = None,
    ) -> "AppConfig":
        key = api_key or os.environ.get("RAMENER_API_KEY")
        if not key:
            key = _load_api_key_from_file()
        if not key:
            raise ValueError(
                "API key not provided. Set RAMENER_API_KEY, define RAMENER_API_KEY_FILE, "
                "or pass --api-key to the script."
            )

        base = base_url or os.environ.get("RAMENER_BASE_URL") or DEFAULT_BASE_URL
        model_name = model or os.environ.get("RAMENER_MODEL") or DEFAULT_MODEL
        page_limit_value = page_limit if page_limit is not None else int(
            os.environ.get("RAMENER_PAGE_LIMIT", DEFAULT_PAGE_LIMIT)
        )
        timeout_value = request_timeout or float(
            os.environ.get("RAMENER_TIMEOUT", DEFAULT_TIMEOUT)
        )
        max_chars_value = max_text_chars if max_text_chars is not None else int(
            os.environ.get("RAMENER_MAX_TEXT_CHARS", DEFAULT_MAX_TEXT_CHARS)
        )
        ocr_model_value = ocr_model or os.environ.get("RAMENER_OCR_MODEL")
        log_path_value = log_path or os.environ.get("RAMENER_LOG_PATH")

        return cls(
            api_key=key,
            base_url=base,
            model=model_name,
            page_limit=page_limit_value,
            request_timeout=timeout_value,
            max_text_chars=max_chars_value,
            log_path=log_path_value,
            ocr_model=ocr_model_value,
        )


def _load_api_key_from_file() -> Optional[str]:
    file_override = os.environ.get("RAMENER_API_KEY_FILE")
    candidates: list[tuple[Path, bool]] = []
    if file_override:
        candidates.append((Path(file_override).expanduser(), True))
    candidates.append((DEFAULT_KEY_FILE.expanduser(), False))

    for path, is_required in candidates:
        try:
            if not path.exists():
                if is_required:
                    raise ValueError(f"API key file not found: {path}")
                continue
            key = path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise ValueError(f"Failed to read API key file {path}: {exc}") from exc
        if key:
            return key
        if is_required:
            raise ValueError(f"API key file {path} is empty.")
    return None
