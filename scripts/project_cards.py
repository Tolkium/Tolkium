"""Render project cards: the picture fills the whole card, its bottom fades dark
so the name and language read on top of it.

Pictures live in assets/projects/src/<repo>.<ext>; cards are written to
assets/projects/<repo>.svg with the picture embedded (GitHub blocks external
images inside SVGs).

Usage: python scripts/project_cards.py
"""
import base64
import io
from html import escape

from PIL import Image

from card import ROOT, USER, graphql

REPOS = ["QRHant", "manga-reader", "Antenna-Field-Configurator", "WebNovelScraper"]
FIT_WIDTH = {"Antenna-Field-Configurator"}  # wide screenshots shown whole instead of side-cropped
W, H = 400, 300
BG, TEXT, DIM = "#0b0c15", "#f0f3f8", "#c9d1d9"
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"


def combine(images, gap=6):
    """Screenshots side by side at a common height, edge to edge (cropped to fill later)."""
    h = 900
    scaled = [im.resize((round(im.width * h / im.height), h), Image.LANCZOS) for im in images]
    canvas = Image.new("RGB", (sum(im.width for im in scaled) + gap * (len(scaled) - 1), h), BG)
    x = 0
    for im in scaled:
        canvas.paste(im, (x, 0))
        x += im.width + gap
    return canvas


def picture(repo):
    folder = ROOT / "assets" / "projects" / "src"
    sources = sorted(folder.glob(f"{repo}.*")) or sorted(folder.glob(f"{repo}-*.*"))
    images = [Image.open(p).convert("RGB") for p in sources]
    im = images[0] if len(images) == 1 else combine(images)
    # Crop to the card's aspect ratio so the picture fills it edge to edge (2x for sharpness).
    target = W / H
    w, h = im.size
    if repo in FIT_WIDTH and w / h > target:
        # Show the whole width; extend top/bottom with the screenshot's own edge colour.
        bg = tuple(int(v) for v in im.crop((0, 0, w, 4)).resize((1, 1), Image.BOX).getpixel((0, 0)))
        canvas = Image.new("RGB", (w, round(w / target)), bg)
        canvas.paste(im, (0, round((canvas.height - h) * 0.25)))  # a bit high: the bottom holds the title
        im = canvas
    elif w / h > target:
        nw = round(h * target)
        im = im.crop(((w - nw) // 2, 0, (w + nw) // 2, h))
    else:
        nh = round(w / target)
        im = im.crop((0, 0, w, nh))  # keep the top: titles and headers live there
    im = im.resize((W * 2, H * 2), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=82, optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


def render(repo, info):
    lang = info["primaryLanguage"] or {"name": "", "color": DIM}
    stars = info["stargazerCount"]
    star_txt = f"★ {stars}" if stars else ""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<defs>
  <clipPath id="c"><rect width="{W}" height="{H}" rx="14"/></clipPath>
  <linearGradient id="fade" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0.45" stop-color="{BG}" stop-opacity="0"/>
    <stop offset="0.75" stop-color="{BG}" stop-opacity="0.88"/>
    <stop offset="1" stop-color="{BG}" stop-opacity="0.97"/>
  </linearGradient>
</defs>
<g clip-path="url(#c)">
  <image width="{W}" height="{H}" preserveAspectRatio="xMidYMid slice" xlink:href="data:image/jpeg;base64,{picture(repo)}"/>
  <rect width="{W}" height="{H}" fill="url(#fade)"/>
</g>
<text x="18" y="{H - 42}" font-family="{FONT}" font-size="24" font-weight="700" fill="{TEXT}">{escape(repo)}</text>
<circle cx="25" cy="{H - 22}" r="6" fill="{lang["color"] or DIM}"/>
<text x="38" y="{H - 16}" font-family="{FONT}" font-size="17" fill="{DIM}">{escape(lang["name"])}</text>
<text x="{W - 18}" y="{H - 16}" text-anchor="end" font-family="{FONT}" font-size="17" fill="{DIM}">{star_txt}</text>
</svg>'''


def main():
    out = ROOT / "assets" / "projects"
    for repo in REPOS:
        info = graphql(
            """query($owner: String!, $name: String!) { repository(owner: $owner, name: $name) {
                 stargazerCount primaryLanguage { name color } } }""",
            owner=USER, name=repo,
        )["repository"]
        (out / f"{repo}.svg").write_text(render(repo, info), encoding="utf-8")
        print(repo, info)


if __name__ == "__main__":
    main()
