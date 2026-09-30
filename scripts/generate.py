#!/usr/bin/env python3
"""Generates assets/heatmap.svg and assets/profile.svg for the profile README."""
import datetime as dt, html, io, json, re, urllib.request
from pathlib import Path
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
CFG = json.loads((ROOT / "profile.json").read_text())
USER = CFG["username"]
OUT = ROOT / "assets"
OUT.mkdir(exist_ok=True)

FONT = "ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace"
BG, BAR, FG, DIM, ACC = "#0d1117", "#161b22", "#c9d1d9", "#6e7681", "#39d353"
LEVELS = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def esc(s):
    return html.escape(str(s), quote=True)


def chrome(w, h, title):
    return (
        f'<rect width="{w}" height="{h}" rx="10" fill="{BG}" stroke="#30363d"/>'
        f'<path d="M0 10a10 10 0 0 1 10-10h{w-20}a10 10 0 0 1 10 10v22H0z" fill="{BAR}"/>'
        '<circle cx="20" cy="16" r="5" fill="#ff5f56"/>'
        '<circle cx="38" cy="16" r="5" fill="#ffbd2e"/>'
        '<circle cx="56" cy="16" r="5" fill="#27c93f"/>'
        f'<text x="{w/2}" y="20" text-anchor="middle" font-size="12" fill="{DIM}">{esc(title)}</text>'
    )


def svg(w, h, body, css=""):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
        f'<style>text{{font-family:{FONT}}}{css}</style>{body}</svg>'
    )


def heatmap():
    page = fetch(f"https://github.com/users/{USER}/contributions").decode("utf-8", "ignore")
    days = []
    for tag in re.findall(r"<td[^>]*ContributionCalendar-day[^>]*>", page):
        d = re.search(r'data-date="([\d-]+)"', tag)
        l = re.search(r'data-level="(\d)"', tag)
        if d and l:
            days.append((dt.date.fromisoformat(d.group(1)), int(l.group(1))))
    days.sort()
    if not days:
        raise RuntimeError("No contribution data found")
    m = re.search(r"([\d,]+)\s+contributions?\s+in\s+the\s+last\s+year", page)
    total = f"{m.group(1)} contributions in the last year" if m else "contributions"

    first = days[0][0]
    start = first - dt.timedelta(days=(first.weekday() + 1) % 7)  # Sunday
    cell, gap, x0, y0 = 12, 3, 24, 66
    cols = (days[-1][0] - start).days // 7 + 1
    w = x0 * 2 + cols * (cell + gap) - gap
    h = y0 + 7 * (cell + gap) + 16

    rects = []
    for d, lvl in days:
        c = (d - start).days // 7
        r = (d.weekday() + 1) % 7
        delay = round(0.6 + (c + r) * 0.03, 3)
        rects.append(
            f'<rect class="d" x="{x0 + c*(cell+gap)}" y="{y0 + r*(cell+gap)}" '
            f'width="{cell}" height="{cell}" rx="2" fill="{LEVELS[min(lvl, 4)]}" '
            f'style="animation-delay:{delay}s"/>'
        )
    body = (
        chrome(w, h, f"{USER} - contributions")
        + f'<text x="{x0}" y="50" font-size="13" fill="{ACC}">$ <tspan fill="{FG}">'
        f'gh contributions --user {esc(USER)}</tspan> <tspan fill="{DIM}"># {esc(total)}</tspan></text>'
        + "".join(rects)
    )
    css = (
        ".d{opacity:0;transform-box:fill-box;transform-origin:center;"
        "animation:pop .4s ease-out forwards}"
        "@keyframes pop{from{opacity:0;transform:scale(.3)}to{opacity:1;transform:scale(1)}}"
    )
    (OUT / "heatmap.svg").write_text(svg(w, h, body, css))


def portrait(cols=44, cw=5.4, ch=10.0):
    img = Image.open(io.BytesIO(fetch(f"https://github.com/{USER}.png?size=200"))).convert("L")
    img = ImageOps.autocontrast(img, cutoff=2)
    rows = max(1, round(cols * img.height / img.width * cw / ch))
    img = img.resize((cols, rows))
    ramp = " .:-=+*#%@"  # bright pixels -> dense glyphs (dark background)
    px = img.load()
    return ["".join(ramp[px[x, y] * (len(ramp) - 1) // 255] for x in range(cols)) for y in range(rows)]


def profile():
    cols, cw, ch = 44, 5.4, 10.0
    lines = portrait(cols, cw, ch)
    px0, py0 = 24, 78
    ph = len(lines) * ch
    cx = px0 + cols * cw + 40
    w = 820

    art = "".join(
        f'<text x="{px0}" y="{py0 + i*ch + ch}" font-size="9" fill="{FG}" '
        f'xml:space="preserve" style="white-space:pre">{esc(row)}</text>'
        for i, row in enumerate(lines)
    )
    wipe = (
        f'<clipPath id="wipe"><rect x="{px0}" y="{py0}" width="{cols*cw+4}" height="0">'
        f'<animate attributeName="height" from="0" to="{ph+ch}" dur="3s" begin="0.5s" fill="freeze"/>'
        "</rect></clipPath>"
        f'<rect x="{px0}" y="{py0}" width="{cols*cw}" height="2" fill="{ACC}">'
        f'<animate attributeName="y" from="{py0}" to="{py0+ph}" dur="3s" begin="0.5s" fill="freeze"/>'
        '<animate attributeName="opacity" from="1" to="0" dur="0.2s" begin="3.5s" fill="freeze"/></rect>'
    )

    card, y, n = [], py0 + 14, 0

    def line(inner):
        nonlocal y, n
        card.append(
            f'<text class="l" x="{cx}" y="{y}" font-size="13" style="animation-delay:{round(1+n*0.18,2)}s">{inner}</text>'
        )
        y += 21
        n += 1

    line(f'<tspan fill="{ACC}" font-weight="bold">{esc(USER)}</tspan><tspan fill="{FG}">@</tspan>'
         f'<tspan fill="{ACC}" font-weight="bold">github</tspan>')
    line(f'<tspan fill="{DIM}">{"-" * (len(USER) + 7)}</tspan>')
    for k, v in CFG["card"]:
        line(f'<tspan fill="{ACC}" font-weight="bold">{esc(k)}</tspan><tspan fill="{FG}">: {esc(v)}</tspan>')
    y += 4
    card.append(
        f'<g class="l" style="animation-delay:{round(1+n*0.18,2)}s">'
        + "".join(f'<rect x="{cx + i*22}" y="{y}" width="18" height="12" rx="2" fill="{c}"/>'
                  for i, c in enumerate(LEVELS)) + "</g>"
    )
    y += 12

    h = int(max(py0 + ph + ch, y) + 28)
    body = (
        chrome(w, h, f"{USER}@github: ~")
        + f'<text x="{px0}" y="56" font-size="13" fill="{ACC}">$ <tspan fill="{FG}">neofetch</tspan></text>'
        + wipe + f'<g clip-path="url(#wipe)">{art}</g>' + "".join(card)
    )
    css = ".l{opacity:0;animation:in .5s ease-out forwards}@keyframes in{from{opacity:0;transform:translateX(-6px)}to{opacity:1;transform:none}}"
    (OUT / "profile.svg").write_text(svg(w, h, body, css))


if __name__ == "__main__":
    heatmap()
    profile()
    print("Generated assets/heatmap.svg and assets/profile.svg")
