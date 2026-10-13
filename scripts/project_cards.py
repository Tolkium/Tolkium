"""Render project cards: picture on the top 3/4, name + language below.

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

REPOS = ["QRHant", "manga-reader", "Antenna-Field-Configurator", "hmstrsoc"]
W, H = 400, 300
IMG_H = H * 3 // 4
BG, BORDER, TEXT, DIM = "#0b0c15", "#ff2a6d", "#f0f3f8", "#8b949e"
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"


def picture(repo):
    src = next((ROOT / "assets" / "projects" / "src").glob(f"{repo}.*"))
    im = Image.open(src).convert("RGB")
    # Centre-crop to the picture area's aspect ratio, render at 2x for sharpness.
    target = W / IMG_H
    w, h = im.size
    if w / h > target:
        nw = round(h * target)
        im = im.crop(((w - nw) // 2, 0, (w + nw) // 2, h))
    else:
        nh = round(w / target)
        im = im.crop((0, (h - nh) // 2, w, (h + nh) // 2))
    im = im.resize((W * 2, IMG_H * 2), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=82, optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


def render(repo, info):
    lang = info["primaryLanguage"] or {"name": "", "color": DIM}
    stars = info["stargazerCount"]
    star_txt = f"★ {stars}" if stars else ""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<defs>
  <clipPath id="c"><rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="14"/></clipPath>
  <linearGradient id="fade" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0.55" stop-color="{BG}" stop-opacity="0"/><stop offset="1" stop-color="{BG}" stop-opacity="1"/>
  </linearGradient>
</defs>
<g clip-path="url(#c)">
  <rect width="{W}" height="{H}" fill="{BG}"/>
  <image width="{W}" height="{IMG_H}" preserveAspectRatio="xMidYMid slice" xlink:href="data:image/jpeg;base64,{picture(repo)}"/>
  <rect y="0" width="{W}" height="{IMG_H}" fill="url(#fade)"/>
  <line x1="0" y1="{IMG_H}" x2="{W}" y2="{IMG_H}" stroke="{BORDER}" stroke-opacity="0.6"/>
</g>
<text x="18" y="{IMG_H + 33}" font-family="{FONT}" font-size="24" font-weight="700" fill="{TEXT}">{escape(repo)}</text>
<circle cx="25" cy="{IMG_H + 56}" r="6" fill="{lang["color"] or DIM}"/>
<text x="38" y="{IMG_H + 62}" font-family="{FONT}" font-size="17" fill="{DIM}">{escape(lang["name"])}</text>
<text x="{W - 18}" y="{IMG_H + 62}" text-anchor="end" font-family="{FONT}" font-size="17" fill="{DIM}">{star_txt}</text>
<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="14" fill="none" stroke="{BORDER}" stroke-opacity="0.55"/>
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
