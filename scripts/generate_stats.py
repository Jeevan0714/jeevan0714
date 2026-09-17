#!/usr/bin/env python3
"""
generate_stats.py — Generates a custom dark GitHub stats SVG card for Jeevan0714.
Design inspired by Harshith C's profile card (github.com/harxhithc).
Outputs: dist/github-stats.svg  (light)
         dist/github-stats-dark.svg  (dark)
"""

import os
import json
import base64
import urllib.request
import urllib.error

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────
USERNAME = "Jeevan0714"
TOKEN    = os.environ.get("GITHUB_TOKEN", "")

# Repos to EXCLUDE from language breakdown (large auto-generated / framework code)
EXCLUDE_REPOS = {"Smart-Traffic-light-controller", "shared-living"}

# Language brand colours
LANG_COLORS = {
    "Verilog":        "#5f9ea0",
    "SystemVerilog":  "#3b6fa4",
    "C++":            "#f34b7d",
    "C":              "#9daaaa",
    "Python":         "#3572a5",
    "JavaScript":     "#f1e05a",
    "TypeScript":     "#2b7489",
    "CSS":            "#8a5fd8",
    "HTML":           "#e34c26",
    "Tcl":            "#e4cc98",
    "TCL":            "#e4cc98",
    "Shell":          "#89e051",
    "Makefile":       "#427819",
    "Cython":         "#fedf5b",
}

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────
def gh_fetch(url: str):
    headers = {
        "User-Agent": "stats-card-bot/1.0",
        "Accept":     "application/json",
    }
    if TOKEN:
        headers["Authorization"] = f"token {TOKEN}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def fetch_avatar_b64(url: str) -> tuple[str, str]:
    """Returns (base64_data, mime_type)."""
    req = urllib.request.Request(url, headers={"User-Agent": "stats-card-bot/1.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        content_type = r.headers.get("Content-Type", "image/jpeg").split(";")[0].strip()
        return base64.b64encode(r.read()).decode(), content_type


def fetch_commit_count(username: str) -> int:
    """Approximate total commits via GitHub search API."""
    try:
        url = f"https://api.github.com/search/commits?q=author:{username}&per_page=1"
        headers = {
            "User-Agent": "stats-card-bot/1.0",
            "Accept":     "application/vnd.github.cloak-preview+json",
        }
        if TOKEN:
            headers["Authorization"] = f"token {TOKEN}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read()).get("total_count", 0)
    except Exception:
        return 0


# ──────────────────────────────────────────────
# Data collection
# ──────────────────────────────────────────────
def collect_data() -> dict:
    user  = gh_fetch(f"https://api.github.com/users/{USERNAME}")
    repos = gh_fetch(f"https://api.github.com/users/{USERNAME}/repos?per_page=100&type=owner")

    stars   = sum(r.get("stargazers_count", 0) for r in repos)
    commits = fetch_commit_count(USERNAME)

    # Language breakdown — skip excluded repos
    raw_langs: dict[str, int] = {}
    for repo in repos:
        if repo["name"] in EXCLUDE_REPOS:
            continue
        try:
            lang_data: dict = gh_fetch(repo["languages_url"])
            for lang, byte_count in lang_data.items():
                raw_langs[lang] = raw_langs.get(lang, 0) + byte_count
        except Exception:
            pass

    total_bytes = sum(raw_langs.values()) or 1
    langs = [
        {"name": l, "pct": round(b / total_bytes * 100, 1)}
        for l, b in sorted(raw_langs.items(), key=lambda x: -x[1])
    ][:8]

    avatar_b64, avatar_mime = fetch_avatar_b64(user["avatar_url"])

    return {
        "name":        user.get("name") or user.get("login"),
        "login":       user.get("login"),
        "followers":   user.get("followers", 0),
        "repos":       user.get("public_repos", 0),
        "stars":       stars,
        "commits":     commits,
        "langs":       langs,
        "avatar":      avatar_b64,
        "avatar_mime": avatar_mime,
    }


# ──────────────────────────────────────────────
# SVG rendering
# ──────────────────────────────────────────────
def render_svg(data: dict, dark: bool = True) -> str:
    W, H = 780, 240

    # Colour tokens
    bg        = "#0d0d0d" if dark else "#ffffff"
    border    = "#2a2a2a" if dark else "#d0d7de"
    card_bg   = "#111111" if dark else "#f6f8fa"
    text_main = "#e8e8e8" if dark else "#1f2328"
    text_mute = "#666666" if dark else "#848d97"
    sep_col   = "#1e1e1e" if dark else "#e8ebee"
    accent    = "#58a6ff" if dark else "#0969da"

    def esc(s: object) -> str:
        return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # ── avatar ───────────────────────────────
    AX, AY, AR = 48, 48, 28   # centre x, centre y, radius
    avatar_uri = f"data:{data['avatar_mime']};base64,{data['avatar']}"

    # ── overview stat cells ───────────────────
    # 2×2 grid starting at y=125
    def stat_block(x: int, y: int, value: str, label: str) -> str:
        return (
            f'<text x="{x}" y="{y}" class="stat-val">{esc(value)}</text>'
            f'<text x="{x}" y="{y + 18}" class="stat-lbl">{esc(label)}</text>'
        )

    stars_s   = f"{data['stars']:,}"
    commits_s = f"{data['commits']:,}" if data["commits"] else "—"
    repos_s   = str(data["repos"])
    followers = str(data["followers"])

    stats_svg = (
        stat_block(20,  160, stars_s,   "STARS")    +
        stat_block(135, 160, commits_s, "COMMITS")  +
        stat_block(20,  200, repos_s,   "REPOS")    +
        stat_block(135, 200, followers, "FOLLOWERS")
    )

    # ── divider ──────────────────────────────
    DIV_X = 390

    # ── language rows (4 rows × 2 cols) ──────
    langs     = data["langs"]
    PANEL_X   = DIV_X + 15          # right panel left edge
    ROW_H     = 34                  # row height
    COL_W     = 180                 # column width
    LANG_Y0   = 75                  # first row y

    lang_rows = ""
    for i, l in enumerate(langs[:8]):
        col   = i % 2
        row   = i // 2
        lx    = PANEL_X + col * COL_W
        ly    = LANG_Y0 + row * ROW_H
        color = LANG_COLORS.get(l["name"], accent)
        pct_s = f"{l['pct']}%"
        bar_w = max(2, int(l["pct"] * 1.5))   # max ~150px at 100%

        lang_rows += (
            f'<circle cx="{lx + 6}" cy="{ly + 6}" r="5" fill="{color}"/>'
            f'<text x="{lx + 16}" y="{ly + 11}" class="lang-name">{esc(l["name"])}</text>'
            f'<text x="{lx + COL_W - 10}" y="{ly + 11}" class="lang-pct">{esc(pct_s)}</text>'
            f'<rect x="{lx}" y="{ly + 18}" width="{bar_w}" height="3" rx="1.5" fill="{color}" opacity="0.65"/>'
        )

    # ── stacked bar at top of right panel ────
    bar_svg = ""
    bx = PANEL_X
    bar_total_w = W - PANEL_X - 15
    for l in langs[:8]:
        bw    = max(1, round(l["pct"] / 100 * bar_total_w))
        color = LANG_COLORS.get(l["name"], accent)
        bar_svg += f'<rect x="{bx}" y="55" width="{bw}" height="7" fill="{color}"/>'
        bx += bw
    # rounded caps
    bar_svg = (
        f'<rect x="{PANEL_X}" y="55" width="{bar_total_w}" height="7" rx="4" fill="none" clip-path="url(#bar-clip)"/>'
        f'<clipPath id="bar-clip"><rect x="{PANEL_X}" y="55" width="{bar_total_w}" height="7" rx="4"/></clipPath>'
        + bar_svg.replace("<rect", f'<rect clip-path="url(#bar-clip)"', )
    )

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:xlink="http://www.w3.org/1999/xlink"
     width="{W}" height="{H}" viewBox="0 0 {W} {H}">

  <defs>
    <clipPath id="avatar-clip">
      <circle cx="{AX}" cy="{AY}" r="{AR}"/>
    </clipPath>
    <clipPath id="bar-clip">
      <rect x="{PANEL_X}" y="55" width="{W - PANEL_X - 15}" height="7" rx="4"/>
    </clipPath>
    <style>
      text {{ font-family: 'Segoe UI', 'Inter', 'Helvetica Neue', sans-serif; }}
      .card-title  {{ font-size:17px; font-weight:700; fill:{text_main}; }}
      .handle      {{ font-size:12px; fill:{text_mute}; }}
      .section-lbl {{ font-size:9px;  font-weight:700; letter-spacing:1.8px; fill:{text_mute}; }}
      .stat-val    {{ font-size:17px; font-weight:700; fill:{text_main}; }}
      .stat-lbl    {{ font-size:9px;  font-weight:600; letter-spacing:1px;  fill:{text_mute}; }}
      .lang-name   {{ font-size:11px; fill:{text_main}; }}
      .lang-pct    {{ font-size:10px; fill:{text_mute}; text-anchor:end; }}
      .section-title {{ font-size:9px; font-weight:700; letter-spacing:1.8px; fill:{text_mute}; }}
    </style>
  </defs>

  <!-- Card background -->
  <rect width="{W}" height="{H}" rx="14" fill="{bg}" stroke="{border}" stroke-width="1"/>

  <!-- Vertical divider -->
  <line x1="{DIV_X}" y1="18" x2="{DIV_X}" y2="{H - 18}"
        stroke="{border}" stroke-width="1"/>

  <!-- ══════════════ LEFT PANEL ══════════════ -->

  <!-- Avatar circle + image -->
  <circle cx="{AX}" cy="{AY}" r="{AR + 3}" fill="{card_bg}" stroke="{accent}" stroke-width="1.5"/>
  <image href="{avatar_uri}"
         x="{AX - AR}" y="{AY - AR}" width="{AR * 2}" height="{AR * 2}"
         clip-path="url(#avatar-clip)"
         preserveAspectRatio="xMidYMid slice"/>

  <!-- Name + handle -->
  <text x="{AX * 2 + 10}" y="38" class="card-title">{esc(data["name"])}</text>
  <text x="{AX * 2 + 10}" y="58" class="handle">@{esc(data["login"])}</text>

  <!-- OVERVIEW label + separator -->
  <text x="20" y="108" class="section-lbl">OVERVIEW</text>
  <line x1="20" y1="114" x2="{DIV_X - 20}" y2="114" stroke="{sep_col}" stroke-width="1"/>

  <!-- Stat grid -->
  {stats_svg}

  <!-- ══════════════ RIGHT PANEL ══════════════ -->

  <!-- TOP LANGUAGES label -->
  <text x="{PANEL_X}" y="42" class="section-title">TOP LANGUAGES</text>
  <line x1="{PANEL_X}" y1="48" x2="{W - 15}" y2="48" stroke="{sep_col}" stroke-width="1"/>

  <!-- Stacked language bar -->
  {bar_svg}

  <!-- Language rows -->
  {lang_rows}

</svg>"""

    return svg


# ──────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────
def main():
    os.makedirs("dist", exist_ok=True)

    print("Collecting GitHub data …")
    data = collect_data()
    print(f"  name={data['name']}, stars={data['stars']}, commits={data['commits']}")
    print(f"  langs={[l['name'] for l in data['langs']]}")

    for dark in (True, False):
        svg  = render_svg(data, dark=dark)
        name = "github-stats-dark.svg" if dark else "github-stats.svg"
        path = os.path.join("dist", name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(svg)
        size_kb = len(svg.encode()) / 1024
        print(f"  Wrote {path}  ({size_kb:.1f} KB)")

    print("Done ✓")


if __name__ == "__main__":
    main()
