#!/usr/bin/env python3
"""Render a commit-rhythm SVG from the GitHub contributions calendar.

Usage: GITHUB_TOKEN=... activity_graph.py <user> <out.svg> [days]
"""
import json
import os
import sys
import urllib.request
from datetime import date

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""

W, H = 900, 300
PAD_L, PAD_R, PAD_T, PAD_B = 48, 24, 56, 44
BG, GRID, TEXT, MUTED, RED, RED_LIGHT = "#0D1117", "#21262D", "#C9D1D9", "#8B949E", "#FF2E2E", "#FF6B6B"


def fetch(user, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": user}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        body = json.load(resp)
    if "errors" in body:
        sys.exit(f"graphql error: {body['errors']}")
    weeks = body["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return [(d["date"], d["contributionCount"]) for w in weeks for d in w["contributionDays"]]


def render(days):
    counts = [c for _, c in days]
    peak = max(max(counts), 1)
    # round the y axis up to a tidy step
    step = max(1, -(-peak // 4))
    top = step * 4

    pw, ph = W - PAD_L - PAD_R, H - PAD_T - PAD_B
    x = lambda i: PAD_L + pw * i / (len(days) - 1)
    y = lambda v: PAD_T + ph * (1 - v / top)

    pts = [(x(i), y(c)) for i, c in enumerate(counts)]
    line = " ".join(f"{px:.1f},{py:.1f}" for px, py in pts)
    area = f"{PAD_L},{PAD_T + ph} {line} {PAD_L + pw},{PAD_T + ph}"

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'font-family="Segoe UI, Ubuntu, sans-serif">',
        '<defs><linearGradient id="fill" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{RED}" stop-opacity="0.45"/>'
        f'<stop offset="1" stop-color="{RED}" stop-opacity="0"/></linearGradient></defs>',
        f'<rect width="{W}" height="{H}" rx="8" fill="{BG}"/>',
        f'<text x="{PAD_L}" y="32" fill="{RED}" font-size="18" font-weight="700">Commit rhythm</text>',
        f'<text x="{W - PAD_R}" y="32" fill="{MUTED}" font-size="13" text-anchor="end">'
        f"{sum(counts)} contributions · last {len(days)} days</text>",
    ]

    for k in range(5):
        v = step * k
        gy = y(v)
        out.append(f'<line x1="{PAD_L}" y1="{gy:.1f}" x2="{PAD_L + pw}" y2="{gy:.1f}" stroke="{GRID}"/>')
        out.append(f'<text x="{PAD_L - 10}" y="{gy + 4:.1f}" fill="{MUTED}" font-size="11" text-anchor="end">{v}</text>')

    for i in range(0, len(days), 7):
        d = date.fromisoformat(days[i][0])
        out.append(
            f'<text x="{x(i):.1f}" y="{H - 18}" fill="{MUTED}" font-size="11" text-anchor="middle">'
            f"{d.strftime('%b %d')}</text>"
        )

    out.append(f'<polygon points="{area}" fill="url(#fill)"/>')
    out.append(f'<polyline points="{line}" fill="none" stroke="{RED}" stroke-width="2.5" stroke-linejoin="round"/>')
    for (px, py), (d, c) in zip(pts, days):
        out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3" fill="{RED_LIGHT}"><title>{d}: {c}</title></circle>')

    out.append("</svg>")
    return "\n".join(out)


def main():
    user, path = sys.argv[1], sys.argv[2]
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 60
    days = [d for d in fetch(user, os.environ["GITHUB_TOKEN"]) if d[0] <= date.today().isoformat()][-n:]
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        f.write(render(days))


if __name__ == "__main__":
    main()
