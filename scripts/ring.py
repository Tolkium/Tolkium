"""Animated neon ring in the profile's cyberpunk colours.

Outputs:
  avatar-ring.gif   - the text avatar with a rotating neon ring (upload as GitHub avatar)
  ring.svg          - a standalone CSS-animated ring (real @keyframes; renders in a README)

Usage: python scripts/ring.py
"""
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
SS = 4                      # supersampling for smooth edges
SIZE = 440
FRAMES = 36                 # one full rotation
RING = 26                   # ring thickness at SIZE
GLOW = 10
BG = (11, 12, 21)
STOPS = ["#05d9e8", "#d300c5", "#fcee0a", "#05d9e8"]  # cyan -> magenta -> yellow -> cyan


def hex_to_rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def wheel(t):
    """Colour at position t (0..1) around the gradient, cyclic."""
    stops = [hex_to_rgb(s) for s in STOPS]
    n = len(stops) - 1
    x = (t % 1.0) * n
    i = int(x)
    f = x - i
    a, b = stops[i], stops[i + 1]
    return tuple(round(a[k] + (b[k] - a[k]) * f) for k in range(3))


def ring_frame(phase):
    big = SIZE * SS
    img = Image.new("RGB", (big, big), BG)
    draw = ImageDraw.Draw(img)
    cx = cy = big / 2
    r = big / 2 - RING * SS
    # Draw the ring as many short coloured arcs so the gradient flows around it.
    segs = 360
    for s in range(segs):
        a0 = s / segs
        col = wheel(a0 + phase)
        ang0 = a0 * 360 - 90
        ang1 = (s + 1) / segs * 360 - 90 + 0.6
        draw.arc([cx - r, cy - r, cx + r, cy + r], ang0, ang1, fill=col, width=RING * SS)
    img = img.resize((SIZE, SIZE), Image.LANCZOS)
    glow = img.filter(ImageFilter.GaussianBlur(GLOW))
    return Image.blend(glow, img, 0.65)


def compose(avatar_path):
    av = Image.open(avatar_path).convert("RGB").resize((SIZE, SIZE), Image.LANCZOS)
    inner = SIZE - 2 * (RING + 6)
    small = av.resize((inner, inner), Image.LANCZOS)
    mask = Image.new("L", (inner, inner), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, inner - 1, inner - 1], fill=255)
    off = (SIZE - inner) // 2

    rgb_frames = []
    for n in range(FRAMES):
        frame = ring_frame(n / FRAMES)
        frame.paste(small, (off, off), mask)
        rgb_frames.append(frame)

    # One shared palette for the whole loop, from the most colourful frame (keeps the static centre stable).
    pal_src = rgb_frames[0].quantize(colors=200, method=Image.MAXCOVERAGE)
    frames = [f.quantize(palette=pal_src, dither=Image.Dither.NONE) for f in rgb_frames]
    frames[0].save(ROOT / "profile-picture" / "avatar-ring.gif", save_all=True,
                   append_images=frames[1:], duration=70, loop=0, optimize=True, disposal=1)


def svg():
    """A standalone ring animated with real CSS @keyframes (rotating conic gradient)."""
    stops = "".join(f'<stop offset="{i/(len(STOPS)-1):.3f}" stop-color="{c}"/>' for i, c in enumerate(STOPS))
    r, w = 230, 22
    circ = 2 * math.pi * r
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">{stops}</linearGradient>
    <filter id="glow"><feGaussianBlur stdDeviation="5"/></filter>
    <style>
      @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
      .ring {{ transform-origin: 256px 256px; animation: spin 6s linear infinite; }}
    </style>
  </defs>
  <rect width="512" height="512" rx="256" fill="{'#%02x%02x%02x' % BG}"/>
  <g class="ring">
    <circle cx="256" cy="256" r="{r}" fill="none" stroke="url(#g)" stroke-width="{w}"
            stroke-linecap="round" stroke-dasharray="{circ*0.72:.0f} {circ*0.28:.0f}" filter="url(#glow)"/>
    <circle cx="256" cy="256" r="{r}" fill="none" stroke="url(#g)" stroke-width="{w}"
            stroke-linecap="round" stroke-dasharray="{circ*0.72:.0f} {circ*0.28:.0f}"/>
  </g>
</svg>'''


def main():
    (ROOT / "profile-picture").mkdir(exist_ok=True)
    avatar = ROOT / "profile-picture" / "avatar-text-128-color.png"
    if not avatar.exists():
        avatar = ROOT / "assets" / "avatar.png"
    compose(avatar)
    (ROOT / "ring.svg").write_text(svg(), encoding="utf-8")


if __name__ == "__main__":
    main()
