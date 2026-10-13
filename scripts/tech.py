"""Technologies section: icons + names per category, transparent background.

Reads the ticked items from tech-checklist.md (falls back to assets/tech/selection.json),
fetches icons from Devicon (MIT) or Simple Icons (CC0) into assets/tech/src/, and renders
assets/tech/stack-{dark,light}.png: one tight grid of icons, no names.

Usage: python scripts/tech.py
"""
import io
import json
import re
import urllib.request
from pathlib import Path

import numpy as np
import resvg_py
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "tech"
SRC = OUT / "src"
DEVICON = "https://cdn.jsdelivr.net/npm/devicon@2.17.0/icons/{0}/{0}-{1}.svg"
SIMPLE = "https://cdn.simpleicons.org/{0}"
FONT = "C:/Windows/Fonts/segoeui.ttf"
S = 2
ICON, CELL_W, CELL_H, COLS = 40, 104, 80, 9
THEMES = {"dark": {"text": (240, 243, 248)}, "light": {"text": (31, 35, 40)}}

# name -> (devicon name or None, simple-icons slug or None)
ICONS = {
    "TypeScript": ("typescript", "typescript"), "JavaScript": ("javascript", "javascript"),
    "Python": ("python", "python"), "C": ("c", "c"), "C++": ("cplusplus", "cplusplus"),
    "C#": ("csharp", None), "Java": ("java", "openjdk"), "PHP": ("php", "php"),
    "SQL": ("azuresqldatabase", None), "Bash / Shell": (None, "gnubash"), "PowerShell": ("powershell", None),
    "HTML": ("html5", "html5"), "CSS": ("css3", "css"), "Sass / SCSS": ("sass", "sass"),
    "React": ("react", "react"), "Next.js": ("nextjs", "nextdotjs"), "Vue": ("vuejs", "vuedotjs"),
    "Nuxt": ("nuxtjs", "nuxt"), "Angular": ("angular", "angular"), "Svelte": ("svelte", "svelte"),
    "Bootstrap": ("bootstrap", "bootstrap"), "Node.js": ("nodejs", "nodedotjs"), "Express": ("express", "express"),
    "NestJS": ("nestjs", "nestjs"), "Bun": ("bun", "bun"), "REST API": (None, "openapiinitiative"),
    "GraphQL": ("graphql", "graphql"), "WebSockets": ("socketio", "socketdotio"),
    "MySQL": ("mysql", "mysql"), "SQLite": ("sqlite", "sqlite"), "Firebase": ("firebase", "firebase"),
    "Supabase": ("supabase", "supabase"), ".NET / WPF": ("dot-net", "dotnet"), "Unity": ("unity", "unity"),
    "Blender": ("blender", "blender"), "Figma": ("figma", "figma"), "Photoshop": ("photoshop", None),
    "GIMP": ("gimp", "gimp"), "ESP32": (None, "espressif"), "Arduino": ("arduino", "arduino"),
    "Raspberry Pi": ("raspberrypi", "raspberrypi"), "PlatformIO": (None, "platformio"),
    "Node-RED": ("nodered", "nodered"), "Home Assistant": (None, "homeassistant"),
    "PrusaSlicer / Cura": (None, "prusa3d"), "Linux": ("linux", "linux"), "Ubuntu": ("ubuntu", "ubuntu"),
    "Windows": ("windows11", None), "Windows Server": ("windows8", None), "Proxmox": (None, "proxmox"),
    "CasaOS": (None, "casaos"), "Docker": ("docker", "docker"), "Docker Compose": ("docker", "docker"),
    "Portainer": ("portainer", "portainer"), "Nginx": ("nginx", "nginx"), "Cloudflare": ("cloudflare", "cloudflare"),
    "Omarchy": (None, "archlinux"), "Microsoft Azure": ("azure", None), "Google Cloud": ("googlecloud", "googlecloud"),
    "AWS": ("amazonwebservices", None), "Vercel": ("vercel", "vercel"), "GitHub Pages": ("github", None),
    "Ollama": ("ollama", "ollama"), "PyTorch": ("pytorch", "pytorch"), "TensorFlow": ("tensorflow", "tensorflow"),
    "OpenCV": ("opencv", "opencv"), "Hugging Face": (None, "huggingface"), "Pandas / NumPy": ("pandas", "pandas"),
    "Solidity": ("solidity", "solidity"), "RxJS": ("rxjs", "reactivex"), "WordPress": (None, "wordpress"),
    "Jest": ("jest", "jest"), "Vitest": ("vitest", "vitest"), "Postman": ("postman", "postman"),
    "Git": ("git", "git"), "GitHub": ("github", "github"), "GitHub Actions": ("githubactions", "githubactions"),
    "GitLab": ("gitlab", "gitlab"), "Slack": ("slack", "slack"), "Microsoft Teams": (None, None),
    "VS Code": ("vscode", None), "JetBrains IDEs": ("jetbrains", "jetbrains"), "Claude Code": (None, "claude"),
}
LABELS = {"Bash / Shell": "Bash", "Sass / SCSS": "Sass", ".NET / WPF": ".NET / WPF",
          "PrusaSlicer / Cura": "PrusaSlicer", "Pandas / NumPy": "Pandas", "JetBrains IDEs": "JetBrains",
          "Microsoft Azure": "Azure", "Microsoft Teams": "Teams"}


def selection():
    path = ROOT / "tech-checklist.md"
    if not path.exists():
        return json.loads((OUT / "selection.json").read_text(encoding="utf-8"))
    groups, current = [], None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## ") and "missing" not in line.lower():
            current = [line[3:].strip(), []]
            groups.append(current)
        elif current and re.match(r"- \[[xX]\] ", line):
            current[1].append(line[6:].strip())
    groups = [g for g in groups if g[1]]
    (OUT / "selection.json").write_text(json.dumps(groups, indent=1, ensure_ascii=False), encoding="utf-8")
    return groups


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "profile-tech"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = r.read()
        return data if data.lstrip().startswith(b"<svg") else None
    except Exception:
        return None


def svg_for(name):
    key = name.lower().replace("+", "plus").replace("#", "sharp")
    cache = SRC / (re.sub(r"[^a-z0-9]+", "-", key).strip("-") + ".svg")
    if cache.exists():
        return cache.read_bytes()
    dev, simple = ICONS.get(name, (None, None))
    data = None
    for variant in ("original", "plain", "original-wordmark"):
        if dev and not data:
            data = fetch(DEVICON.format(dev, variant))
    if simple and not data:
        data = fetch(SIMPLE.format(simple))
    if data:
        cache.write_bytes(data)
    return data


def raster(svg, size):
    png = bytes(resvg_py.svg_to_bytes(svg_string=svg.decode("utf-8"), width=size, height=size))
    im = Image.open(io.BytesIO(png)).convert("RGBA")
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))  # keep aspect, centre
    im.thumbnail((size, size), Image.LANCZOS)
    canvas.alpha_composite(im, ((size - im.width) // 2, (size - im.height) // 2))
    return canvas


def tile(label, size):
    """Fallback icon: initials in a rounded square."""
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, size - 1, size - 1), size // 5, fill=(88, 96, 105, 255))
    letters = "".join(w[0] for w in re.findall(r"[A-Za-z]+", label))[:2].upper()
    f = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", size // 2 - 2)
    tw = d.textlength(letters, font=f)
    d.text(((size - tw) / 2, size * 0.18), letters, font=f, fill=(255, 255, 255, 255))
    return im


def for_theme(im, theme):
    """Black-and-white logos that would vanish on this background (black on dark, white on light)
    are inverted; colourful logos are left alone."""
    a = np.asarray(im, dtype=np.float32)
    mask = a[..., 3] > 40
    if not mask.any():
        return im
    rgb = a[..., :3][mask]
    lum = (rgb @ [0.299, 0.587, 0.114]).mean() / 255
    sat = ((rgb.max(1) - rgb.min(1)) / np.maximum(rgb.max(1), 1)).mean()
    if sat < 0.15 and ((theme == "dark" and lum < 0.3) or (theme == "light" and lum > 0.8)):
        a[..., :3] = 255 - a[..., :3]
        return Image.fromarray(a.astype("uint8"))
    return im


def render(items, slug):
    size = ICON * S
    icons = {}
    for name in items:
        svg = svg_for(name)
        icons[name] = raster(svg, size) if svg else tile(name, size)
    rows = (len(items) + COLS - 1) // COLS
    w, h = min(len(items), COLS) * CELL_W, rows * CELL_H
    font = ImageFont.truetype(FONT, 13 * S)
    for theme, cfg in THEMES.items():
        img = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        for i, name in enumerate(items):
            r, c = divmod(i, COLS)
            x0, y0 = c * CELL_W, r * CELL_H
            img.alpha_composite(for_theme(icons[name], theme), (int((x0 + (CELL_W - ICON) / 2) * S), int((y0 + 6) * S)))
            label = LABELS.get(name, name)
            tw = d.textlength(label, font=font)
            d.text(((x0 + CELL_W / 2) * S - tw / 2, (y0 + ICON + 14) * S), label, font=font, fill=cfg["text"])
        img.save(OUT / f"{slug}-{theme}.png", optimize=True)
    return w


def render_flat(items, icon=30, gap=12, cols=21):
    """All icons in one tight grid, no names, no categories (names live in the alt text)."""
    size = icon * S
    step = icon + gap
    rows = (len(items) + cols - 1) // cols
    w, h = min(len(items), cols) * step - gap, rows * step - gap
    icons = [raster(svg, size) if (svg := svg_for(n)) else tile(n, size) for n in items]
    for theme in THEMES:
        img = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
        for i, ic in enumerate(icons):
            r, c = divmod(i, cols)
            img.alpha_composite(for_theme(ic, theme), (c * step * S, r * step * S))
        img.save(OUT / f"stack-{theme}.png", optimize=True)


def main():
    SRC.mkdir(parents=True, exist_ok=True)
    items, seen = [], set()
    for _, group in selection():
        for n in group:
            key = svg_for(n) or n  # identical logos (Docker / Docker Compose, ...) are shown once
            if key not in seen:
                seen.add(key)
                items.append(n)
    render_flat(items)
    print("icons:", len(items), "| no icon found (initials tile used):", [n for n in items if not svg_for(n)])
    (OUT / "readme-block.md").write_text(
        '<picture>\n  <source media="(prefers-color-scheme: dark)" srcset="./assets/tech/stack-dark.png">\n'
        f'  <img src="./assets/tech/stack-light.png" alt="Tech stack: {", ".join(items)}" width="100%">\n</picture>\n',
        encoding="utf-8")


if __name__ == "__main__":
    main()
