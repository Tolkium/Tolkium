"""Recreate the avatar from tiny coloured text (for use as a profile picture).

Styles:
  ramp  - character density follows brightness, colour follows the picture
  fill  - a repeating phrase, every character coloured by the picture

Usage: python scripts/text_avatar.py <style> <rows> [out.png]
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
SIZE = 1024
BG = (11, 12, 21)
RAMP = " .,:;i1tfLCG08@"
PHRASE = "TOLKIUM/SIMON "
FONT = "C:/Windows/Fonts/consolab.ttf"


def render(style, rows, src=ROOT / "assets" / "avatar.png"):
    cell_h = SIZE / rows
    font = ImageFont.truetype(FONT, round(cell_h * 0.95))
    cell_w = font.getlength("M")
    cols = int(SIZE / cell_w)

    im = Image.open(src).convert("RGBA").resize((cols, rows), Image.LANCZOS)
    px = np.asarray(im, dtype=np.float32)
    rgb, alpha = px[..., :3], px[..., 3] / 255
    lum = (0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]) / 255

    out = Image.new("RGB", (SIZE, SIZE), BG)
    draw = ImageDraw.Draw(out)
    x0 = (SIZE - cols * cell_w) / 2
    k = 0
    for r in range(rows):
        for c in range(cols):
            a = alpha[r, c]
            if a < 0.3:
                k += 1
                continue
            colour = rgb[r, c]
            if style == "ramp":
                v = lum[r, c] ** 0.65
                ch = RAMP[min(int(v * len(RAMP)), len(RAMP) - 1)]
                boost = min(2.5, 255 / max(colour.max(), 1))
                colour = colour * boost
            else:
                ch = PHRASE[k % len(PHRASE)]
                colour = colour * 1.15 + 12  # text is thin, so nudge it brighter to match the picture
            k += 1
            if ch.strip():
                fill = tuple(int(min(255, v * a + BG[i] * (1 - a))) for i, v in enumerate(colour))
                draw.text((x0 + c * cell_w, r * cell_h), ch, font=font, fill=fill)
    return out


if __name__ == "__main__":
    style, rows = sys.argv[1], int(sys.argv[2])
    out = Path(sys.argv[3]) if len(sys.argv) > 3 else ROOT / f"avatar-text-{style}-{rows}.png"
    render(style, rows).save(out, optimize=True)
    print(out)
