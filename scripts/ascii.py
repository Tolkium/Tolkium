"""Convert an image (default: GitHub avatar) to coloured ASCII art for a dark background.

Bright areas get dense characters, the line-art outlines stay blank so they
draw the face, and dark fills (hair, hoodie) get mid-density characters.
Each character takes the average colour of its cell, lifted so dark colours
stay visible on a dark card.

Usage: python scripts/ascii.py <image> [cols] [rows]   -> writes assets/ascii.json
"""
import colorsys
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
RAMP = " .,:;i1tfLCG08@"
CROP = (40, 0, 430, 440)  # head and shoulders of the 460x460 avatar
FILL = 0.38  # minimum density for non-outline foreground
OUTLINE = 0.14  # darker than this = outline -> blank
MIN_VALUE = 0.45  # lift dark colours (HSV value) so they show on the dark card
QUANT = 24  # colour quantisation step, merges neighbouring characters into runs


def lift(rgb):
    h, s, v = colorsys.rgb_to_hsv(*(c / 255 for c in rgb))
    v = MIN_VALUE + (1 - MIN_VALUE) * v
    s = min(1.0, s * 1.5)
    r, g, b = (min(255, round(c * 255 / QUANT) * QUANT) for c in colorsys.hsv_to_rgb(h, s, v))
    return f"#{r:02x}{g:02x}{b:02x}"


def convert(path, cols=96, rows=52):
    src = Image.open(path).convert("RGBA").resize((460, 460)).crop(CROP)
    img = Image.new("RGBA", src.size, "white")
    img.alpha_composite(src)  # transparent background -> white
    rgb = np.asarray(img.convert("RGB"), dtype=np.float32)
    gray = np.asarray(ImageOps.autocontrast(img.convert("L"), cutoff=1), dtype=np.float32) / 255
    fg = np.asarray(src.split()[3], dtype=np.float32) / 255 > 0.5

    val = np.where(gray < OUTLINE, 0, FILL + (1 - FILL) * gray)
    val = np.where(fg, val, 0)
    colour_mask = fg & (gray >= OUTLINE)  # average colour without the black outlines

    h, w = val.shape
    out = []
    for r in range(rows):
        y0, y1 = r * h // rows, (r + 1) * h // rows
        runs = []
        for c in range(cols):
            x0, x1 = c * w // cols, (c + 1) * w // cols
            ch = RAMP[min(int(val[y0:y1, x0:x1].mean() * len(RAMP)), len(RAMP) - 1)]
            m = colour_mask[y0:y1, x0:x1]
            colour = lift(rgb[y0:y1, x0:x1][m].mean(axis=0)) if ch != " " and m.any() else None
            if runs and (runs[-1][1] == colour or ch == " "):
                runs[-1][0] += ch
            else:
                runs.append([ch, colour])
        while runs and not runs[-1][0].strip():
            runs.pop()
        out.append(runs)
    return out


if __name__ == "__main__":
    args = sys.argv[1:]
    cols = int(args[1]) if len(args) > 1 else 96
    rows = int(args[2]) if len(args) > 2 else 52
    art = {"cols": cols, "rows": convert(args[0], cols, rows)}
    (ROOT / "assets" / "ascii.json").write_text(json.dumps(art, separators=(",", ":")), encoding="utf-8")
