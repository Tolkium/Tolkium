"""Recreate the avatar from tiny coloured text (for use as a profile picture).

Styles:
  ramp  - character density follows brightness, colour follows the picture
  fill  - a repeating phrase, every character coloured by the picture
  match - colour-accurate: each character's colour is solved so the cell's
          average (ink + dark background) equals the picture's colour; the
          lightest character that can reach that colour is used

Usage: python scripts/text_avatar.py <style> <rows> [out.png]
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
SIZE = 2048
BG = (11, 12, 21)
RAMP = " .,:;i1tfLCG08@"
PHRASE = "TOLKIUM/SIMON "
GLYPHS = ".:-=+*ilt1LCGO08BNMWHDRKAE#%"  # no descenders or tall glyphs, so the font can be larger
SPACING = 1.0  # letter advance as a fraction of the glyph width (tighter = brighter)
VARIETY = 0.08  # glyphs within this much coverage of the best fit are mixed
LINE_DROP = 0.3  # a pixel this much darker than its cell is part of an ink line
LINE_FRAC = 0.05  # line coverage at which a cell becomes fully 'line'
LINE_INK = 0.35  # darken line colour toward the black ink it really is
DENSEST = 6  # how many of the densest glyphs to mix where nothing reaches the colour
FONT = "C:/Windows/Fonts/consolab.ttf"


def coverage(font, cell_w, cell_h, chars):
    """Fraction of the cell each character's ink covers."""
    w, h = round(cell_w), round(cell_h)
    out = {}
    for ch in chars:
        m = Image.new("L", (w, h), 0)
        ImageDraw.Draw(m).text((0, 0), ch, font=font, fill=255)
        out[ch] = np.asarray(m, dtype=np.float32).mean() / 255
    return sorted(out.items(), key=lambda kv: kv[1])


def fitting_font(cell_h):
    """Largest font whose glyphs all fit inside one cell: exactly one character per place."""
    size = round(cell_h * 1.2)
    while size > 4:
        font = ImageFont.truetype(FONT, size)
        adv = font.getlength("M")
        boxes = [font.getbbox(ch) for ch in GLYPHS]
        if all(b[1] >= 0 and b[3] <= cell_h and b[0] >= 0 and b[2] <= adv for b in boxes):
            return font
        size -= 1
    return ImageFont.truetype(FONT, size)


def sample_keep_lines(src, cols, rows, sub=6):
    """One colour per cell that keeps thin dark lines (mouth, brows, outlines).

    Each cell is sampled at sub x sub points; if the cell contains a dark line
    (pixels much darker than the cell average) the colour leans toward it
    instead of averaging it away into the skin.
    """
    px = np.asarray(Image.open(src).convert("RGBA").resize((cols * sub, rows * sub), Image.LANCZOS), dtype=np.float32)
    px = px.reshape(rows, sub, cols, sub, 4).transpose(0, 2, 1, 3, 4).reshape(rows, cols, sub * sub, 4)
    rgb, a = px[..., :3], px[..., 3:] / 255
    lum = rgb @ np.array([0.299, 0.587, 0.114]) / 255
    w = a[..., 0]
    mean = (rgb * a).sum(2) / np.maximum(w.sum(2, keepdims=True), 1e-6)
    mean_lum = (lum * w).sum(2) / np.maximum(w.sum(2), 1e-6)
    # A cell with even a little of a line takes the line's colour, so thin lines survive
    # as dark gaps between letters.
    # Far darker than the rest of its cell: a thin anti-aliased ink line (mouth, brows, outlines).
    line = (lum < mean_lum[..., None] - LINE_DROP) & (w > 0.5)
    frac = line.mean(2)
    dark_rgb = (rgb * line[..., None]).sum(2) / np.maximum(line.sum(2, keepdims=True), 1)
    k = np.clip(frac / LINE_FRAC, 0, 1)[..., None]
    # Ink lines are black in the artwork; at this size they only look grey because they're thin.
    dark_rgb = dark_rgb * LINE_INK
    return mean * (1 - k) + dark_rgb * k, w.mean(2)


def render(style, rows, src=ROOT / "assets" / "avatar.png"):
    cell_h = SIZE / rows
    font = fitting_font(cell_h) if style == "match" else ImageFont.truetype(FONT, round(cell_h * 0.95))
    cell_w = font.getlength("M") * (SPACING if style == "match" else 1)
    cols = int(SIZE / cell_w)

    if style == "match":
        rgb, alpha = sample_keep_lines(src, cols, rows)
    else:
        px = np.asarray(Image.open(src).convert("RGBA").resize((cols, rows), Image.LANCZOS), dtype=np.float32)
        rgb, alpha = px[..., :3], px[..., 3] / 255
    lum = (0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]) / 255

    glyphs = [g for g in coverage(font, cell_w, cell_h, GLYPHS) if g[1] > 0.04]
    rng = np.random.default_rng(7)  # fixed seed: same picture every run
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
            if style == "match":
                target = colour * a + np.array(BG) * (1 - a)
                bg = np.array(BG, dtype=np.float32)
                # Glyphs dense enough to reach the target colour, lightest first.
                fits = [(g, cov) for g, cov in glyphs if ((target - bg * (1 - cov)) / cov).max() <= 255]
                if fits:
                    # Mix similar-coverage glyphs so flat areas read as text, not a pattern.
                    pool = [g for g in fits if g[1] <= fits[0][1] + VARIETY] 
                else:
                    pool = glyphs[-DENSEST:]
                ch, cov = pool[rng.integers(len(pool))]
                colour = (target - bg * (1 - cov)) / cov
                if colour.max() > 255:  # densest glyphs can't get there: full brightness, true hue
                    colour = colour * 255 / colour.max()
                k += 1
                draw.text((x0 + c * cell_w, r * cell_h), ch, font=font,
                          fill=tuple(int(np.clip(v, 0, 255)) for v in colour))
                continue
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
    img = render(style, rows)
    if style == "match":  # 256-colour palette keeps the 2048px picture under GitHub's 1 MB limit
        img = img.quantize(256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    img.save(out, optimize=True)
    print(out)
