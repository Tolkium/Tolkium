"""Convert an image (default: GitHub avatar) to ASCII art.

Usage: python scripts/ascii.py <image> [cols] [rows] > assets/ascii.txt
"""
import sys

import numpy as np
from PIL import Image, ImageFilter, ImageOps

RAMP = " .'`^,:;!i|lI1jrtfxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"


def background_mask(gray, threshold=235):
    """Near-white pixels connected to the image border."""
    h, w = gray.shape
    light = gray >= threshold
    mask = np.zeros_like(light)
    stack = [(y, x) for y in (0, h - 1) for x in range(w)] + [(y, x) for x in (0, w - 1) for y in range(h)]
    while stack:
        y, x = stack.pop()
        if 0 <= y < h and 0 <= x < w and light[y, x] and not mask[y, x]:
            mask[y, x] = True
            stack.extend(((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)))
    return mask


def convert(path, cols=46, rows=26, edge_weight=0.6):
    src = Image.open(path).convert("RGBA")
    img = Image.new("RGBA", src.size, "white")
    img.alpha_composite(src)  # transparent background -> white
    img = img.convert("L")
    img = ImageOps.autocontrast(img, cutoff=1)
    gray = np.asarray(img, dtype=np.float32)
    bg = background_mask(gray.astype(np.uint8))
    edges = np.asarray(img.filter(ImageFilter.FIND_EDGES), dtype=np.float32)

    # "Ink" density: dark areas and outlines get dense characters.
    ink = (255 - gray) / 255
    ink = np.clip(ink + edge_weight * edges / 255, 0, 1)
    ink[bg] = 0

    h, w = ink.shape
    out = []
    for r in range(rows):
        y0, y1 = r * h // rows, (r + 1) * h // rows
        line = ""
        for c in range(cols):
            x0, x1 = c * w // cols, (c + 1) * w // cols
            cell = ink[y0:y1, x0:x1]
            if bg[y0:y1, x0:x1].mean() > 0.85:
                line += " "
                continue
            v = cell.mean() ** 0.8
            line += RAMP[min(int(v * len(RAMP)), len(RAMP) - 1)]
        out.append(line.rstrip())
    return "\n".join(out)


if __name__ == "__main__":
    args = sys.argv[1:]
    cols = int(args[1]) if len(args) > 1 else 46
    rows = int(args[2]) if len(args) > 2 else 26
    print(convert(args[0], cols, rows))
