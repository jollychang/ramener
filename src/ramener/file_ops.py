from __future__ import annotations

import shutil
from pathlib import Path

from send2trash import send2trash


class FileOperationError(Exception):
    pass


def generate_destination(original: Path, target_name: str) -> Path:
    destination = original.with_name(target_name)
    counter = 1
    while destination.exists():
        destination = original.with_name(
            f"{destination.stem}-{counter}{destination.suffix}"
        )
        counter += 1
    return destination


def copy_pdf(original: Path, destination: Path) -> None:
    try:
        shutil.copy2(original, destination)
    except Exception as exc:  # pragma: no cover - defensive
        raise FileOperationError(f"Failed to copy file: {exc}") from exc


def move_original_to_trash(original: Path) -> None:
    try:
        send2trash(str(original))
    except Exception as exc:  # pragma: no cover - defensive
        raise FileOperationError(f"Failed to move original to trash: {exc}") from exc
