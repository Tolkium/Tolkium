"""Convert an image (default: GitHub avatar) to coloured ASCII art for a dark background.

On a dark card the perceived brightness of a character is roughly
(character density x colour brightness). So density follows the pixel's
luminance and the colour carries the pixel's hue at full brightness - the
result reads like the original picture: bright skin, brown hair, a dark hoodie
that fades into the background, and black outlines that stay blank.

Usage: python scripts/ascii.py <image> [cols] [rows]   -> writes assets/ascii.json
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
RAMP = " .,:;i1tfLCG08@"
CROP = (40, 0, 430, 440)  # head and shoulders of the 460x460 avatar
OUTLINE = 0.10  # darker than this = outline -> blank
MAX_BOOST = 2.5  # how much a dark colour may be brightened (density does the rest)
GAMMA = 0.65  # <1 lifts mid-tones (hair) so they read like the picture
QUANT = 24  # colour quantisation step, merges neighbouring characters into runs


def lift(rgb):
    """Pixel hue at (near) full brightness; the character density supplies the darkness."""
    boost = min(MAX_BOOST, 255 / max(max(rgb), 1))
    r, g, b = (min(255, round(c * boost / QUANT) * QUANT) for c in rgb)
    return f"#{r:02x}{g:02x}{b:02x}"


def convert(path, cols=52, rows=28):
    src = Image.open(path).convert("RGBA").resize((460, 460)).crop(CROP)
    img = Image.new("RGBA", src.size, "white")
    img.alpha_composite(src)  # transparent background -> white
    rgb = np.asarray(img.convert("RGB"), dtype=np.float32)
    gray = np.asarray(ImageOps.autocontrast(img.convert("L"), cutoff=1), dtype=np.float32) / 255
    fg = np.asarray(src.split()[3], dtype=np.float32) / 255 > 0.5

    val = np.where(fg & (gray >= OUTLINE), gray ** GAMMA, 0)
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
    cols = int(args[1]) if len(args) > 1 else 52
    rows = int(args[2]) if len(args) > 2 else 28
    art = {"cols": cols, "rows": convert(args[0], cols, rows)}
    (ROOT / "assets" / "ascii.json").write_text(json.dumps(art, separators=(",", ":")), encoding="utf-8")
