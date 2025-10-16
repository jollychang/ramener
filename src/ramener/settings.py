from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

SETTINGS_DIR = Path.home() / ".config" / "ramener"
SETTINGS_FILE = SETTINGS_DIR / "settings.json"


@dataclass
class UserSettings:
    service_name: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None
    ocr_model: Optional[str] = None
    page_limit: Optional[int] = None
    request_timeout: Optional[float] = None
    max_text_chars: Optional[int] = None
    log_path: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserSettings":
        return cls(
            service_name=_coerce_str(data.get("service_name")),
            api_key=_coerce_str(data.get("api_key")),
            base_url=_coerce_str(data.get("base_url")),
            model=_coerce_str(data.get("model")),
            ocr_model=_coerce_str(data.get("ocr_model")),
            page_limit=_coerce_int(data.get("page_limit")),
            request_timeout=_coerce_float(data.get("request_timeout")),
            max_text_chars=_coerce_int(data.get("max_text_chars")),
            log_path=_coerce_str(data.get("log_path")),
        )

    def to_serializable(self) -> Dict[str, Any]:
        data = asdict(self)
        return {key: value for key, value in data.items() if value is not None}


def load_user_settings(path: Path = SETTINGS_FILE) -> UserSettings:
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return UserSettings()
    except OSError as exc:
        logging.getLogger(__name__).warning("Failed to read settings file %s: %s", path, exc)
        return UserSettings()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logging.getLogger(__name__).warning("Invalid JSON in settings file %s: %s", path, exc)
        return UserSettings()

    if not isinstance(data, dict):
        logging.getLogger(__name__).warning("Settings file %s must contain a JSON object.", path)
        return UserSettings()

    return UserSettings.from_dict(data)


def save_user_settings(settings: UserSettings, path: Path = SETTINGS_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = settings.to_serializable()
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        # Ignore chmod errors (e.g., on non-POSIX filesystems).
        pass


def _coerce_str(value: Any) -> Optional[str]:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _coerce_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _coerce_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None
