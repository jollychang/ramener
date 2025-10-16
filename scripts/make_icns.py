#!/usr/bin/env python3
"""Convert ramener.png into ramener.icns without relying on iconutil."""
from __future__ import annotations

import io
import struct
from pathlib import Path

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PNG_PATH = PROJECT_ROOT / "packaging" / "ramener.png"
ICNS_PATH = PROJECT_ROOT / "packaging" / "ramener.icns"

ICON_SIZES = [
    ("icp4", 16),
    ("icp5", 32),
    ("icp6", 64),
    ("ic07", 128),
    ("ic08", 256),
    ("ic09", 512),
    ("ic10", 1024),
]


def encode_chunk(tag: str, image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    payload = buffer.getvalue()
    header = tag.encode("ascii") + struct.pack(">I", len(payload) + 8)
    return header + payload


def main() -> int:
    if not PNG_PATH.exists():
        raise SystemExit(f"Missing source PNG: {PNG_PATH}")

    base = Image.open(PNG_PATH)
    base = base.convert("RGBA")

    chunks: list[bytes] = []
    for tag, size in ICON_SIZES:
        resized = base.resize((size, size), Image.LANCZOS)
        chunks.append(encode_chunk(tag, resized))

    body = b"".join(chunks)
    icns_header = b"icns" + struct.pack(">I", len(body) + 8)

    ICNS_PATH.write_bytes(icns_header + body)
    print(f"ICNS written to {ICNS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
