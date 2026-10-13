"""Pink-framed pieces that replace GitHub's grey lines on the profile.

Outputs:
  assets/creators-{dark,light}.png - favourite creators: icons + names, transparent background
  assets/games-{dark,light}.png    - currently playing: icons + names, transparent background
  assets/line.svg                - thin pink line used under section headings
  profile-picture/avatar-pink-ring.png - original avatar with a thin pink ring (upload manually)

Usage: python scripts/panels.py [--no-ring | --split]
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
PINK = (255, 42, 109)
BG = (11, 12, 21)
TEXT = (240, 243, 248)
FONT = "C:/Windows/Fonts/segoeui.ttf"
S = 2  # render at 2x for sharp edges

CREATORS = [
    ("davepl", "Dave's Attic"), ("lowleveltv", "Low Level"), ("theprimetimeagen", "ThePrimeTime"),
    ("t3dotgg", "Theo"), ("fireship", "Fireship"), ("codebullet", "Code Bullet"),
    ("willjum", "Willjum"), ("gamermeld", "Gamer Meld"), ("eevblog", "EEVblog"),
    ("jerryrigeverything", "JerryRigEverything"), ("linustechtips", "Linus Tech Tips"), ("markrober", "Mark Rober"),
]
GAMES = [("the-finals", "THE FINALS"), ("wardogs", "WARDOGS"), ("palworld", "Palworld")]


THEMES = {"dark": (240, 243, 248), "light": (31, 35, 40)}  # label colour per GitHub theme
RING = 1.5  # icon ring width, same weight as the card and heading lines


def icon(folder, key, size, ring, shape):
    """Icon from its original source, cropped to a circle (creators) or rounded square (games)."""
    src_dir = ROOT / "assets" / folder / "src"
    src = next(src_dir.glob(f"{key}.*"))
    im = Image.open(src)
    if src.suffix == ".ico":
        im.size = max(im.info["sizes"])
        im.load()
    im = im.convert("RGBA")
    big = size * S * 2
    w, h = im.size
    m = min(w, h)
    im = im.crop(((w - m) // 2, (h - m) // 2, (w + m) // 2, (h + m) // 2)).resize((big, big), Image.LANCZOS)
    radius = big // 2 if shape == "circle" else big // 5
    mask = Image.new("L", (big, big), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, big - 1, big - 1), radius, fill=255)
    out = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    out.paste(im, mask=mask)
    if ring:
        k = big / size
        ImageDraw.Draw(out).rounded_rectangle((k * 0.5, k * 0.5, big - 1 - k * 0.5, big - 1 - k * 0.5), radius,
                                              outline=PINK + (220,), width=round(RING * k))
    return out.resize((size * S, size * S), Image.LANCZOS)


def grid(items, folder, cols, out, ring, shape, cell=(130, 104), size=64):
    """Icons + names on a transparent background (no panel, no frame); one image per GitHub theme."""
    rows = (len(items) + cols - 1) // cols
    w, h = cols * cell[0], rows * cell[1]
    # ring: True / False, or "split" = left half of the columns ringed, right half plain (side-by-side comparison)
    half = (cols + 1) // 2
    icons = [icon(folder, key, size, (i % cols) < half if ring == "split" else ring, shape)
             for i, (key, _) in enumerate(items)]
    font = ImageFont.truetype(FONT, 15 * S)
    for theme, text in THEMES.items():
        img = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        for i, ((_, name), ic) in enumerate(zip(items, icons)):
            r, c = divmod(i, cols)
            row_n = min(cols, len(items) - r * cols)
            x0 = (cols - row_n) * cell[0] / 2 + c * cell[0]
            y0 = r * cell[1]
            img.alpha_composite(ic, (int((x0 + (cell[0] - size) / 2) * S), int((y0 + 4) * S)))
            tw = d.textlength(name, font=font)
            d.text(((x0 + cell[0] / 2) * S - tw / 2, (y0 + size + 12) * S), name, font=font, fill=text)
        img.save(ROOT / "assets" / f"{out}-{theme}.png", optimize=True)


def line_svg():
    """1px heading line in GitHub's own border grey (dark and light theme variants)."""
    for theme, colour in (("dark", "#3d444d"), ("light", "#d1d9e0")):
        (ROOT / "assets" / f"line-{theme}.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="900" height="3" viewBox="0 0 900 3" preserveAspectRatio="none">'
            f'<rect x="0" y="1" width="900" height="1" fill="{colour}"/></svg>', encoding="utf-8")


def ring_avatar(size=640, ring=4, gap=6):
    big = size * S * 2
    out = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    ringimg = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    k = big / size
    r = big / 2 - ring * k / 2 - 2 * k
    ImageDraw.Draw(ringimg).ellipse((big / 2 - r, big / 2 - r, big / 2 + r, big / 2 + r),
                                    outline=PINK + (255,), width=round(ring * k))
    out = Image.alpha_composite(out, ringimg.filter(ImageFilter.GaussianBlur(3 * k)))  # faint glow
    out = Image.alpha_composite(out, ringimg)
    inner = round(big - 2 * (ring + gap + 2) * k)
    av = Image.open(ROOT / "assets" / "avatar.png").convert("RGBA").resize((inner, inner), Image.LANCZOS)
    disc = Image.new("RGBA", (inner, inner), BG + (255,))
    disc.alpha_composite(av)
    mask = Image.new("L", (inner, inner), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, inner - 1, inner - 1), fill=255)
    out.paste(disc, ((big - inner) // 2, (big - inner) // 2), mask)
    (ROOT / "profile-picture").mkdir(exist_ok=True)
    out.resize((size, size), Image.LANCZOS).save(ROOT / "profile-picture" / "avatar-pink-ring.png", optimize=True)


def main():
    ring = "split" if "--split" in sys.argv else "--no-ring" not in sys.argv
    grid(CREATORS, "creators", cols=6, out="creators", ring=ring, shape="circle")
    grid(GAMES, "games", cols=3, out="games", ring=ring, shape="rounded")
    line_svg()
    ring_avatar()


if __name__ == "__main__":
    main()
