"""Render the terminal-style profile card (dark_mode.svg / light_mode.svg).

Reads card.json + assets/ascii.json, fetches live stats from the GitHub API
(token in GITHUB_TOKEN or GH_TOKEN) and writes the SVGs to the repo root.

Usage: python scripts/card.py [--offline]
"""
import base64
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.request
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
USER = os.environ.get("GITHUB_USER", "Tolkium")
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")

WIDTH = 66  # characters in the info column
FONT_SIZE = 16
ADVANCE = 0.5859375  # glyph advance (em) of the embedded Cascadia Mono subset
FONT_FILE = ROOT / "assets" / "fonts" / "card-mono.woff2"  # SIL OFL, see assets/fonts/OFL.txt
CHAR_W = FONT_SIZE * ADVANCE
LINE_H = FONT_SIZE * 1.25
ART_COLS = 52

# Shown instead of a detected language (JSON never appears in GitHub's language stats).
COMPUTER_SWAP = {"Makefile": "JSON"}

# Linguist languages shown under Languages.Computer (markup, styles, data, config).
COMPUTER_LANGS = {"HTML", "CSS", "SCSS", "Sass", "Less", "Markdown", "MDX", "JSON", "YAML", "TOML", "XML",
                  "Dockerfile", "Makefile", "CMake", "Jupyter Notebook", "TeX", "Batchfile", "PowerShell", "Shell"}

# Cyberpunk accents on white text.
THEMES = {
    "dark": {
        "bg": "#0b0c15", "border": "#ff2a6d", "text": "#f0f3f8", "dim": "#4b5068",
        "key": "#05d9e8", "title": "#ff2a6d", "rule": "#3d444d", "num": "#fcee0a", "add": "#39ff88", "del": "#ff3864",
        "art": ("#f0f3f8", "#f0f3f8"),
    },
    "light": {
        "bg": "#f6f8fa", "border": "#d300c5", "text": "#1f2328", "dim": "#a0a7b4",
        "key": "#0089a8", "title": "#c2185b", "rule": "#d1d9e0", "num": "#9a6700", "add": "#1a7f37", "del": "#cf222e",
        "art": ("#1f2328", "#1f2328"),
    },
}


# ---------------------------------------------------------------- GitHub API
def _request(url, body=None):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "profile-card"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.status, json.loads(resp.read() or "null")


def graphql(query, **variables):
    _, data = _request("https://api.github.com/graphql", {"query": query, "variables": variables})
    if data.get("errors"):
        raise RuntimeError(data["errors"])
    return data["data"]


def fetch_stats():
    info = graphql(
        """query($login: String!) { user(login: $login) {
             createdAt
             followers { totalCount }
             repositoriesContributedTo(contributionTypes: [COMMIT, PULL_REQUEST, REPOSITORY]) { totalCount }
           } }""",
        login=USER,
    )["user"]

    repos, cursor = [], None
    while True:
        page = graphql(
            """query($login: String!, $cursor: String) { user(login: $login) {
                 repositories(first: 100, after: $cursor, ownerAffiliations: OWNER) {
                   nodes { nameWithOwner isFork stargazerCount
                           languages(first: 20) { edges { size node { name } } } }
                   pageInfo { hasNextPage endCursor }
                 } } }""",
            login=USER, cursor=cursor,
        )["user"]["repositories"]
        repos += page["nodes"]
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]

    # Commits: sum contribution years since the account was created.
    commits = 0
    start = dt.datetime.fromisoformat(info["createdAt"].replace("Z", "+00:00")).year
    for year in range(start, dt.date.today().year + 1):
        cc = graphql(
            """query($login: String!, $from: DateTime!, $to: DateTime!) { user(login: $login) {
                 contributionsCollection(from: $from, to: $to) {
                   totalCommitContributions restrictedContributionsCount } } }""",
            login=USER, **{"from": f"{year}-01-01T00:00:00Z", "to": f"{year}-12-31T23:59:59Z"},
        )["user"]["contributionsCollection"]
        commits += cc["totalCommitContributions"]

    # Lines of code: per-repo contributor stats (GitHub computes them lazily -> 202).
    added = deleted = 0
    for repo in (r for r in repos if not r["isFork"]):
        for _ in range(6):
            try:
                status, data = _request(f"https://api.github.com/repos/{repo['nameWithOwner']}/stats/contributors")
            except urllib.error.HTTPError:
                break
            if status == 202:
                time.sleep(3)
                continue
            for author in data or []:
                if author.get("author") and author["author"]["login"].lower() == USER.lower():
                    added += sum(w["a"] for w in author["weeks"])
                    deleted += sum(w["d"] for w in author["weeks"])
            break

    # Languages: bytes per language across own (non-fork) repos, largest first.
    sizes = {}
    for repo in (r for r in repos if not r["isFork"]):
        for edge in repo["languages"]["edges"]:
            sizes[edge["node"]["name"]] = sizes.get(edge["node"]["name"], 0) + edge["size"]
    ranked = sorted(sizes, key=sizes.get, reverse=True)

    return {
        "created": info["createdAt"][:10],
        "langs_programming": [l for l in ranked if l not in COMPUTER_LANGS],
        "langs_computer": [COMPUTER_SWAP.get(l, l) for l in ranked if l in COMPUTER_LANGS],
        "repos": len([r for r in repos if not r["isFork"]]),
        "contributed": info["repositoriesContributedTo"]["totalCount"],
        "stars": sum(r["stargazerCount"] for r in repos),
        "commits": commits,
        "followers": info["followers"]["totalCount"],
        "added": added,
        "deleted": deleted,
    }


# ---------------------------------------------------------------- formatting
def uptime(birthday):
    born, today = dt.date.fromisoformat(birthday), dt.date.today()
    months = (today.year - born.year) * 12 + today.month - born.month
    if today.day < born.day:
        months -= 1
    anchor_month = born.month - 1 + months
    anchor = born.replace(year=born.year + anchor_month // 12, month=anchor_month % 12 + 1, day=1)
    anchor += dt.timedelta(days=born.day - 1)
    days = (today - anchor).days
    y, m = divmod(months, 12)
    plural = lambda n, w: f"{n} {w}{'' if n == 1 else 's'}"
    return f"{plural(y, 'year')}, {plural(m, 'month')}, {plural(days, 'day')}"


# A line is a list of (text, color-key) segments.
def kv(key, value, width=WIDTH, value_role="text"):
    head = [(". ", "dim")] + [(part, "key") if i % 2 == 0 else (".", "text")
                               for i, part in enumerate(_split_key(key))] + [(":", "text")]
    used = sum(len(t) for t, _ in head) + len(value) + 2
    return head + [(" " + "." * max(width - used, 1) + " ", "dim"), (value, value_role)]


def fit_list(items, max_len, limit=6):
    """Comma-join as many items as fit on one line."""
    out = ""
    for item in items[:limit]:
        candidate = f"{out}, {item}" if out else item
        if len(candidate) > max_len:
            break
        out = candidate
    return out


def _split_key(key):
    parts = key.split(".")
    out = []
    for i, p in enumerate(parts):
        if i:
            out.append(".")
        out.append(p)
    return out


def rule(title, width=WIDTH):
    label = f"- {title} " if title else ""
    return [(label, "title" if title else "text"), ("─" * (width - len(label)), "rule")]


def stat(key, value, width):
    return kv(key, f"{value:,}", width, "num")


def build_lines(cfg, stats):
    lines = [[(cfg["header"] + " ", "text"), ("─" * (WIDTH - len(cfg["header"]) - 1), "rule")]]
    for i, section in enumerate(cfg["sections"]):
        rows = []
        for key, value in section["rows"]:
            if value == "{uptime}":
                value = uptime(cfg["birthday"]) if cfg.get("birthday") else ""
            elif value == "{account_age}":
                value = uptime(stats["created"]) if stats.get("created") else ""
            elif value in ("{langs_programming}", "{langs_computer}"):
                value = fit_list(stats.get(value[1:-1], []), WIDTH - len(key) - 8)
            if value:
                rows.append(kv(key, value))
        if not rows:
            continue
        if section.get("title"):
            lines += [[]] + [rule(section["title"])]
        elif i:
            lines.append([(". ", "dim")])
        lines += rows

    if stats:
        half = (WIDTH - 3) // 2
        lines += [[], rule("GitHub Stats")]
        contrib = [(" {", "text"), ("Contributed", "key"), (": ", "text"), (f"{stats['contributed']:,}", "num"), ("}", "text")]
        repos = kv("Repos", f"{stats['repos']:,}", half - _len(contrib), "num") + contrib
        lines.append(repos + [(" | ", "dim")] + stat("Stars", stats["stars"], WIDTH - half - 1)[1:])
        commits = stat("Commits", stats["commits"], half)
        lines.append(commits + [(" | ", "dim")] + stat("Followers", stats["followers"], WIDTH - half - 1)[1:])
        loc = stats["added"] - stats["deleted"]
        tail = [(" ( ", "text"), (f"{stats['added']:,}++", "add"), (", ", "text"), (f"{stats['deleted']:,}--", "del"), (" )", "text")]
        lines.append(kv("Lines of Code on GitHub", f"{loc:,}", WIDTH - _len(tail), "num") + tail)
    return lines


def _len(segments):
    return sum(len(t) for t, _ in segments)


# ---------------------------------------------------------------- SVG
def shade(colour, theme):
    """Art colours are tuned for the dark card; darken them for the light one."""
    if theme == "dark":
        return colour
    r, g, b = (int(colour[i:i + 2], 16) * 0.55 for i in (1, 3, 5))
    return f"#{int(r):02x}{int(g):02x}{int(b):02x}"


def render(lines, art, theme):
    c = THEMES[theme]
    pad = 14
    art_w = ART_COLS * CHAR_W
    art_fs = art_w / (art["cols"] * ADVANCE)  # fit the art columns into the art box
    art_lh = art_fs * 1.25
    art_h = len(art["rows"]) * art_lh
    # Spread the info lines so the text column spans the same height as the portrait.
    info_lh = max(LINE_H, (art_h - FONT_SIZE * 0.25) / len(lines))
    info_h = len(lines) * info_lh
    inner = max(art_h, info_h)
    info_x = pad + art_w + 12
    width = info_x + WIDTH * CHAR_W + pad
    height = pad * 2 + inner
    art_top = pad + (inner - art_h) / 2
    info_top = pad + (inner - info_h) / 2

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" xml:space="preserve" width="{width:.0f}" height="{height:.0f}" '
        f'font-family="CardMono,\'Cascadia Mono\',Consolas,monospace" font-size="{FONT_SIZE}px">',
        # The font is embedded so every viewer gets identical glyph widths: lines end exactly at the margin.
        "<style>@font-face{font-family:CardMono;src:url(data:font/woff2;base64,"
        + base64.b64encode(FONT_FILE.read_bytes()).decode() + ") format('woff2');}"
        "text, tspan { white-space: pre; }</style>",
        # No frame and no background: the card sits directly on the GitHub page.
    ]
    for i, runs in enumerate(art["rows"]):
        segs = "".join(
            f'<tspan fill="{shade(colour, theme)}">{escape(text)}</tspan>' if colour else escape(text)
            for text, colour in runs)
        out.append(f'<text x="{pad}" y="{art_top + art_fs + i * art_lh:.1f}" font-size="{art_fs:.2f}px" '
                   f'fill="{c["text"]}">{segs or " "}</text>')
    for i, line in enumerate(lines):
        y = info_top + FONT_SIZE + i * info_lh
        segs, col = "", 0
        for text, role in line:
            if role == "rule":
                # A real 1px line (same weight as the README heading lines) instead of thick "─" glyphs.
                x0 = info_x + (col + 0.5) * CHAR_W
                out.append(f'<rect x="{x0:.1f}" y="{y - FONT_SIZE * 0.32:.1f}" width="{(len(text) - 0.5) * CHAR_W:.1f}" '
                           f'height="1" fill="{c["rule"]}"/>')  # GitHub's own border grey
            elif text:
                segs += f'<tspan fill="{c[role]}">{escape(text)}</tspan>'
            col += len(text)
        out.append(f'<text x="{info_x:.1f}" y="{y:.1f}" fill="{c["text"]}">{segs or " "}</text>')
    out.append("</svg>")
    return "\n".join(out)


def main():
    cfg = json.loads((ROOT / "card.json").read_text(encoding="utf-8"))
    art = json.loads((ROOT / "assets" / "ascii.json").read_text(encoding="utf-8"))
    if "--offline" in sys.argv:
        stats = {"repos": 0, "contributed": 0, "stars": 0, "commits": 0, "followers": 0, "added": 0, "deleted": 0}
    else:
        stats = fetch_stats()
        print(json.dumps(stats))
    lines = build_lines(cfg, stats)
    for theme in THEMES:
        (ROOT / f"{theme}_mode.svg").write_text(render(lines, art, theme), encoding="utf-8")


if __name__ == "__main__":
    main()
