"""Render a horizontal 3D contributions calendar (calendar.svg).

Weeks run left to right, weekdays recede diagonally, bar height = contributions.
Token in GITHUB_TOKEN or GH_TOKEN.

Usage: python scripts/contrib_calendar.py
"""
from pathlib import Path

from card import ROOT, USER, graphql

CELL = 14  # week step (x)
DX, DY = 5, 6  # weekday step (depth)
MAX_H = 56  # tallest bar
PAD = 16

LEVELS = {  # top, left side, front side
    "NONE": ("#ebedf0", "#c9cdd3", "#d8dbe0"),
    "FIRST_QUARTILE": ("#9be9a8", "#6fc07d", "#82d592"),
    "SECOND_QUARTILE": ("#40c463", "#2b9a49", "#35ae55"),
    "THIRD_QUARTILE": ("#30a14e", "#1f7a39", "#278d44"),
    "FOURTH_QUARTILE": ("#216e39", "#144d26", "#1a5d30"),
}


def fetch_days():
    cal = graphql(
        """query($login: String!) { user(login: $login) { contributionsCollection {
             contributionCalendar { weeks { contributionDays {
               date weekday contributionCount contributionLevel } } } } } }""",
        login=USER,
    )["user"]["contributionsCollection"]["contributionCalendar"]
    return [day for week in cal["weeks"] for day in week["contributionDays"]]


def streaks(days):
    best = run = 0
    for d in days:
        run = run + 1 if d["contributionCount"] else 0
        best = max(best, run)
    current = 0
    # Today may not have contributions yet; don't break the streak for it.
    for i, d in enumerate(reversed(days)):
        if d["contributionCount"]:
            current += 1
        elif i:
            break
    return current, best


def poly(points, fill):
    return f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in points)}" fill="{fill}"/>'


def render(days):
    weeks = (len(days) + days[0]["weekday"] + 6) // 7
    peak = max(d["contributionCount"] for d in days) or 1
    width = PAD * 2 + weeks * CELL + 7 * DX
    top = PAD + MAX_H
    floor_h = 7 * DY
    height = top + floor_h + PAD + 48

    cells = []
    for i, d in enumerate(days):
        idx = i + days[0]["weekday"]
        w, wd = idx // 7, d["weekday"]
        h = 3 + (MAX_H - 3) * (d["contributionCount"] / peak) ** 0.7 if d["contributionCount"] else 0
        cells.append((wd, w, h, LEVELS.get(d["contributionLevel"], LEVELS["NONE"])))

    # Floor under the tiles so the gaps read as thin grid lines.
    fx, fy = PAD, top
    out = [poly([(fx - 1, fy - 1), (fx + weeks * CELL, fy - 1),
                 (fx + weeks * CELL + 7 * DX, fy + floor_h), (fx + 7 * DX - 1, fy + floor_h)], "#d0d7de")]
    # Back rows first; within a row right-to-left so nearer bars cover left faces.
    for wd, w, h, (c_top, c_left, c_front) in sorted(cells, key=lambda c: (c[0], -c[1])):
        x = PAD + w * CELL + wd * DX
        y = top + wd * DY
        a, b = (x, y), (x + CELL - 1, y)  # back edge
        c, d = (x + CELL - 1 + DX - 1, y + DY - 1), (x + DX - 1, y + DY - 1)  # front edge
        up = lambda p: (p[0], p[1] - h)
        if h:
            out.append(poly([a, d, up(d), up(a)], c_left))
            out.append(poly([d, c, up(c), up(d)], c_front))
        out.append(poly([up(a), up(b), up(c), up(d)], c_top))

    total = sum(d["contributionCount"] for d in days)
    current, best = streaks(days)
    stats = [
        ("Contributions", f"{total:,}"),
        ("Current streak", f"{current} day{'s' * (current != 1)}"),
        ("Best streak", f"{best} day{'s' * (best != 1)}"),
        ("Highest in a day", f"{peak}"),
        ("Average per day", f"~{total / len(days):.2f}"),
    ]
    col = (width - PAD * 2) / len(stats)
    text_y = top + floor_h + PAD + 16
    for i, (label, value) in enumerate(stats):
        cx = PAD + col * i + col / 2
        out.append(f'<text x="{cx:.0f}" y="{text_y}" text-anchor="middle" class="v">{value}</text>')
        out.append(f'<text x="{cx:.0f}" y="{text_y + 20}" text-anchor="middle" class="l">{label}</text>')

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
        "<style>text{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif}"
        ".v{font-size:16px;font-weight:600;fill:#2f81f7}.l{font-size:12px;fill:#8b949e}</style>"
        + "".join(out)
        + "</svg>"
    )


def main():
    (Path(ROOT) / "calendar.svg").write_text(render(fetch_days()), encoding="utf-8")


if __name__ == "__main__":
    main()
