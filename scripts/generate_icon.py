#!/usr/bin/env python3
"""Generate the Ramener app icon PNG."""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SIZE = 1024
OUTPUT = Path(__file__).resolve().parent.parent / "packaging" / "ramener.png"

FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Times.ttc",
    "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
    "/Library/Fonts/Times New Roman.ttf",
    "/System/Library/Fonts/NewYork.ttf",
]


def load_font(size: int) -> ImageFont.FreeTypeFont:
    for font_path in FONT_CANDIDATES:
        path = Path(font_path)
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size)
            except OSError:
                continue
    return ImageFont.load_default()


def main() -> int:
    output_path = OUTPUT
    output_path.parent.mkdir(parents=True, exist_ok=True)

    img = Image.new("RGBA", (SIZE, SIZE), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)

    font = load_font(760)
    text = "R"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    text_x = (SIZE - text_width) / 2 - 20
    text_y = (SIZE - text_height) / 2 - 80
    draw.text((text_x, text_y), text, font=font, fill=(0, 0, 0, 255))

    tag_outline = [
        (620, 610),
        (700, 560),
        (870, 660),
        (780, 780),
        (640, 700),
    ]
    draw.polygon(tag_outline, fill=(255, 255, 255, 255), outline=(0, 0, 0, 255))

    hole_center = (770, 660)
    hole_radius = 22
    hole_bbox = [
        hole_center[0] - hole_radius,
        hole_center[1] - hole_radius,
        hole_center[0] + hole_radius,
        hole_center[1] + hole_radius,
    ]
    draw.ellipse(hole_bbox, fill=(255, 255, 255, 255), outline=(0, 0, 0, 255), width=8)

    strap = [(640, 700), (610, 730)]
    draw.line(strap, fill=(0, 0, 0, 255), width=14)

    img.save(output_path, format="PNG")
    print(f"Icon written to {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
