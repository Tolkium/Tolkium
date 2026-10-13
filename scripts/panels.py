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
    ("jerryrigeverything", "JerryRig"), ("linustechtips", "Linus Tech Tips"), ("markrober", "Mark Rober"),
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


TITLE_H = 30


def title_font():
    return ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 15 * S)


def emoji(ch, px):
    """Colour emoji rendered from Segoe UI Emoji."""
    f = ImageFont.truetype("C:/Windows/Fonts/seguiemj.ttf", 109)
    im = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
    ImageDraw.Draw(im).text((8, 8), ch, font=f, embedded_color=True)
    return im.crop(im.getbbox()).resize((px, px), Image.LANCZOS)


def grid(items, folder, cols, out, ring, shape, title, cell=(86, 74), size=44, height=None):
    """Title + icons + names on a transparent background; one image per GitHub theme.
    Returns the size (1x) so a neighbouring block can be given the same height."""
    rows = (len(items) + cols - 1) // cols
    w, h = cols * cell[0], TITLE_H + rows * cell[1]
    h = max(h, height or 0)
    # ring: True / False, or "split" = left half of the columns ringed, right half plain (side-by-side comparison)
    half = (cols + 1) // 2
    icons = [icon(folder, key, size, (i % cols) < half if ring == "split" else ring, shape)
             for i, (key, _) in enumerate(items)]
    font = ImageFont.truetype(FONT, 12 * S)
    emo, text_title = title.split(" ", 1)
    em = emoji(emo, 18 * S)
    for theme, text in THEMES.items():
        img = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        img.alpha_composite(em, (6 * S, 4 * S))
        d.text((30 * S, 2 * S), text_title, font=title_font(), fill=text)
        for i, ((_, name), ic) in enumerate(zip(items, icons)):
            r, c = divmod(i, cols)
            x0, y0 = c * cell[0], TITLE_H + r * cell[1]
            img.alpha_composite(ic, (int((x0 + (cell[0] - size) / 2) * S), int((y0 + 4) * S)))
            label = name
            while d.textlength(label, font=font) > (cell[0] - 4) * S:  # keep long names inside the cell
                label = label[:-2] + "…"
            tw = d.textlength(label, font=font)
            d.text(((x0 + cell[0] / 2) * S - tw / 2, (y0 + size + 9) * S), label, font=font, fill=text)
        img.save(ROOT / "assets" / f"{out}-{theme}.png", optimize=True)
    return w, h


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
    cw, ch = grid(CREATORS, "creators", cols=6, out="creators", ring=ring, shape="circle", title="📺 Favorite Creators")
    gw, _ = grid(GAMES, "games", cols=3, out="games", ring=ring, shape="rounded", title="🎮 Currently Playing", height=ch)
    (ROOT / "assets" / "hobbies-size.txt").write_text(f"{cw} {gw}", encoding="utf-8")
    line_svg()
    ring_avatar()


if __name__ == "__main__":
    main()
