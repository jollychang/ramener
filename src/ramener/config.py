import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .settings import load_user_settings


DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_MODEL = "qwen3-omni-flash"
DEFAULT_PAGE_LIMIT = 3
DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_TEXT_CHARS = 12000
DEFAULT_KEY_FILE = Path.home() / ".config" / "ramener" / "api_key"
DEFAULT_LOG_PATH = Path.home() / "Library" / "Logs" / "Ramener" / "ramener.log"


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
    service_name: Optional[str] = None

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
        service_name: Optional[str] = None,
    ) -> "AppConfig":
        settings = load_user_settings()

        key = api_key or os.environ.get("RAMENER_API_KEY")
        if not key:
            key = settings.api_key
        if not key:
            key = _load_api_key_from_file()
        if not key:
            raise ValueError(
                "API key not provided. Set RAMENER_API_KEY, define RAMENER_API_KEY_FILE, "
                "or pass --api-key to the script."
            )

        base = base_url or os.environ.get("RAMENER_BASE_URL") or settings.base_url or DEFAULT_BASE_URL
        model_name = model or os.environ.get("RAMENER_MODEL") or settings.model or DEFAULT_MODEL
        page_limit_value = _resolve_int(
            page_limit,
            os.environ.get("RAMENER_PAGE_LIMIT"),
            settings.page_limit,
            DEFAULT_PAGE_LIMIT,
            "RAMENER_PAGE_LIMIT",
        )
        timeout_value = _resolve_float(
            request_timeout,
            os.environ.get("RAMENER_TIMEOUT"),
            settings.request_timeout,
            DEFAULT_TIMEOUT,
            "RAMENER_TIMEOUT",
        )
        max_chars_value = _resolve_int(
            max_text_chars,
            os.environ.get("RAMENER_MAX_TEXT_CHARS"),
            settings.max_text_chars,
            DEFAULT_MAX_TEXT_CHARS,
            "RAMENER_MAX_TEXT_CHARS",
        )
        ocr_model_value = ocr_model or os.environ.get("RAMENER_OCR_MODEL") or settings.ocr_model
        log_path_value = (
            log_path
            or os.environ.get("RAMENER_LOG_PATH")
            or settings.log_path
            or (str(DEFAULT_LOG_PATH) if sys.platform == "darwin" else None)
        )
        service_name_value = service_name or os.environ.get("RAMENER_SERVICE_NAME") or settings.service_name

        return cls(
            api_key=key,
            base_url=base,
            model=model_name,
            page_limit=page_limit_value,
            request_timeout=timeout_value,
            max_text_chars=max_chars_value,
            log_path=log_path_value,
            ocr_model=ocr_model_value,
            service_name=service_name_value,
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


def _resolve_int(
    direct_value: Optional[int],
    env_value: Optional[str],
    stored_value: Optional[int],
    default_value: int,
    env_name: str,
) -> int:
    if direct_value is not None:
        return direct_value
    if env_value is not None:
        try:
            return int(env_value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid integer for {env_name}: {env_value}") from exc
    if stored_value is not None:
        return stored_value
    return default_value


def _resolve_float(
    direct_value: Optional[float],
    env_value: Optional[str],
    stored_value: Optional[float],
    default_value: float,
    env_name: str,
) -> float:
    if direct_value is not None:
        return direct_value
    if env_value is not None:
        try:
            return float(env_value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid float for {env_name}: {env_value}") from exc
    if stored_value is not None:
        return stored_value
    return default_value
