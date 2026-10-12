"""Convert an image (default: GitHub avatar) to ASCII art for a dark background.

Bright areas get dense characters, the line-art outlines stay blank so they
draw the face, and dark fills (hair, hoodie) get mid-density characters.

Usage: python scripts/ascii.py <image> [cols] [rows] > assets/ascii.txt
"""
import sys

import numpy as np
from PIL import Image, ImageOps

RAMP = " .,:;i1tfLCG08@"
CROP = (40, 0, 430, 440)  # head and shoulders of the 460x460 avatar
FILL = 0.38  # minimum density for non-outline foreground
OUTLINE = 0.14  # darker than this = outline -> blank


def convert(path, cols=48, rows=26):
    src = Image.open(path).convert("RGBA").resize((460, 460)).crop(CROP)
    img = Image.new("RGBA", src.size, "white")
    img.alpha_composite(src)  # transparent background -> white
    gray = np.asarray(ImageOps.autocontrast(img.convert("L"), cutoff=1), dtype=np.float32) / 255
    fg = np.asarray(src.split()[3], dtype=np.float32) / 255 > 0.5

    val = np.where(gray < OUTLINE, 0, FILL + (1 - FILL) * gray)
    val = np.where(fg, val, 0)

    h, w = val.shape
    out = []
    for r in range(rows):
        y0, y1 = r * h // rows, (r + 1) * h // rows
        line = ""
        for c in range(cols):
            v = val[y0:y1, c * w // cols:(c + 1) * w // cols].mean()
            line += RAMP[min(int(v * len(RAMP)), len(RAMP) - 1)]
        out.append(line.rstrip())
    return "\n".join(out)


if __name__ == "__main__":
    args = sys.argv[1:]
    cols = int(args[1]) if len(args) > 1 else 48
    rows = int(args[2]) if len(args) > 2 else 26
    print(convert(args[0], cols, rows))
