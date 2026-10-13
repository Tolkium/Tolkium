"""Pink-framed pieces that replace GitHub's grey lines on the profile.

Outputs:
  assets/creators-panel.png      - favourite creators grid in one pink frame
  assets/games-panel.png         - currently-playing grid in one pink frame
  assets/line.svg                - thin pink line used under section headings
  profile-picture/avatar-pink-ring.png - original avatar with a thin pink ring (upload manually)

Usage: python scripts/panels.py
"""
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


def frame(size, radius=14):
    """Dark card with the same thin pink border as the terminal card."""
    w, h = size
    img = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, w * S - 1, h * S - 1), radius * S, fill=BG + (255,))
    border = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(border).rounded_rectangle((S, S, w * S - 1 - S, h * S - 1 - S), radius * S,
                                             outline=PINK + (190,), width=S)
    return Image.alpha_composite(img, border)


def grid(items, folder, cols, cell=(130, 112), icon=64, out="panel.png"):
    rows = (len(items) + cols - 1) // cols
    pad = 18
    w, h = cols * cell[0] + 2 * pad, rows * cell[1] + 2 * pad
    img = frame((w, h))
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT, 15 * S)
    for i, (key, name) in enumerate(items):
        r, c = divmod(i, cols)
        # centre a short last row
        row_n = min(cols, len(items) - r * cols)
        x0 = pad + (cols - row_n) * cell[0] / 2 + c * cell[0]
        y0 = pad + r * cell[1]
        ic = Image.open(ROOT / "assets" / folder / f"{key}.png").convert("RGBA").resize((icon * S, icon * S), Image.LANCZOS)
        img.alpha_composite(ic, (int((x0 + (cell[0] - icon) / 2) * S), int((y0 + 8) * S)))
        tw = d.textlength(name, font=font)
        d.text(((x0 + cell[0] / 2) * S - tw / 2, (y0 + icon + 16) * S), name, font=font, fill=TEXT)
    img.save(ROOT / "assets" / out, optimize=True)


def line_svg():
    (ROOT / "assets" / "line.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="900" height="6" viewBox="0 0 900 6" preserveAspectRatio="none">'
        '<rect x="0" y="2" width="900" height="2" fill="#ff2a6d" fill-opacity="0.75"/></svg>',
        encoding="utf-8")


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
    grid(CREATORS, "creators", cols=6, out="creators-panel.png")
    grid(GAMES, "games", cols=3, out="games-panel.png")
    line_svg()
    ring_avatar()


if __name__ == "__main__":
    main()
