#!/usr/bin/env python3
"""Generate static GitHub profile stat SVGs from the GitHub REST API.

No third-party dependencies, no auth required for public data
(set GITHUB_TOKEN to lift the rate limit when run in Actions).
"""

import json
import os
import sys
import urllib.request

USER = os.environ.get("GITHUB_USER", "Alexyzy1")
API = "https://api.github.com"
TOKEN = os.environ.get("GITHUB_TOKEN")

# GitHub linguist colors, fall back to a neutral grey
LANG_COLORS = {
    "Python": "#3776AB", "JavaScript": "#f1e05a", "HTML": "#e34c26",
    "CSS": "#563d7c", "TypeScript": "#3178c6", "Shell": "#89e051",
    "Dockerfile": "#384d54", "Jupyter Notebook": "#DA5B0B", "C++": "#f34b7d",
    "C": "#555555", "Go": "#00ADD8", "Rust": "#dea584", "Java": "#b07219",
}

FG = "#24292f"      # primary text
FG_SUB = "#57606a"  # secondary text
ACCENT = "#0969da"  # GitHub blue
BORDER = "#d0d7de"
BG = "#ffffff"
FONT = "Segoe UI, -apple-system, Helvetica, Arial, sans-serif"


def api_get(path):
    req = urllib.request.Request(API + path, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "profile-stats-generator",
    })
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.headers, json.loads(r.read().decode())


def commit_count(full_name):
    """Total commits on the default branch = page count of per_page=1."""
    req = urllib.request.Request(
        f"{API}/repos/{full_name}/commits?per_page=1",
        headers={"User-Agent": "profile-stats-generator"},
    )
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            link = r.headers.get("Link", "")
            for part in link.split(","):
                if 'rel="last"' in part:
                    return int(part.split("&page=")[1].split(">")[0])
            return 1  # single commit -> no Link header
    except Exception:
        return 0


def escape(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def wrap(w, h, inner):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}">'f'<rect width="100%" height="100%" rx="10" '
            f'fill="{BG}" stroke="{BORDER}"/>{inner}</svg>')


def text(x, y, s, size=14, fill=FG, weight="normal", anchor="start"):
    return (f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" '
            f'fill="{fill}" font-weight="{weight}" text-anchor="{anchor}">'
            f'{escape(s)}</text>')


def banner_svg(tagline):
    name = "Hi there, I'm Alex"
    inner = (
        text(36, 52, name + " \U0001f44b", 30, FG, "600")
        + text(38, 84, tagline, 15, FG_SUB)
        + f'<rect x="{38 + len(tagline) * 7.4:.0f}" y="70" width="9" height="19" '
          f'rx="1.5" fill="{ACCENT}">'
          f'<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;.5;.5;1" '
          f'dur="1.1s" repeatCount="indefinite"/></rect>'
    )
    return wrap(760, 110, inner)


def stats_svg(stats):
    rows = [
        ("\u2605  Total stars earned", f"{stats['stars']:,}"),
        ("\u2387  Commits (own repos)", f"{stats['commits']:,}"),
        ("\u25a6  Own repositories", str(stats["own_repos"])),
        ("\u25a6  Total public repos", str(stats["total_repos"])),
        ("\u25cc  Followers", str(stats["followers"])),
    ]
    inner = text(24, 38, f"{USER}'s GitHub Stats", 17, FG, "600")
    inner += f'<line x1="24" y1="50" x2="476" y2="50" stroke="{BORDER}"/>'
    y = 78
    for label, value in rows:
        inner += text(24, y, label, 13.5, FG_SUB)
        inner += text(472, y, value, 13.5, FG, "600", "end")
        y += 24
    return wrap(500, 210, inner)


def langs_svg(langs):
    total = sum(langs.values())
    top = sorted(langs.items(), key=lambda kv: -kv[1])[:6]
    inner = text(24, 38, "Most Used Languages", 17, FG, "600")
    inner += f'<line x1="24" y1="50" x2="476" y2="50" stroke="{BORDER}"/>'
    y = 76
    bar_x = 176
    bar_max = 472 - bar_x
    for name, nbytes in top:
        pct = nbytes / total * 100
        color = LANG_COLORS.get(name, "#8b949e")
        inner += text(24, y, name, 13, FG_SUB)
        inner += (f'<rect x="{bar_x}" y="{y - 11}" width="{bar_max}" height="11" '
                  f'rx="5.5" fill="#f6f8fa"/>'
                  f'<rect x="{bar_x}" y="{y - 11}" width="{max(bar_max * pct / 100, 6):.0f}" '
                  f'height="11" rx="5.5" fill="{color}"/>')
        inner += text(472, y, f"{pct:.1f}%", 12.5, FG, "600", "end")
        y += 26
    return wrap(500, 40 + 26 * len(top) + 14, inner)


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    _, user = api_get(f"/users/{USER}")
    _, repos = api_get(f"/users/{USER}/repos?per_page=100")

    own = [r for r in repos if not r["fork"]]
    stars = sum(r["stargazers_count"] for r in own)
    commits = sum(commit_count(r["full_name"]) for r in own)

    langs = {}
    for r in own:
        try:
            _, langs_repo = api_get(f"/repos/{r['full_name']}/languages")
            for lang, nbytes in langs_repo.items():
                langs[lang] = langs.get(lang, 0) + nbytes
        except Exception:
            pass

    stats = {
        "stars": stars, "commits": commits,
        "own_repos": len(own), "total_repos": len(repos),
        "followers": user["followers"],
    }
    print("stats:", stats)
    print("languages:", {k: v for k, v in sorted(langs.items(), key=lambda kv: -kv[1])})

    for fname, svg in [
        ("banner.svg", banner_svg("ML / LLM enthusiast \u00b7 building knowledge-base QA systems")),
        ("stats.svg", stats_svg(stats)),
        ("languages.svg", langs_svg(langs)),
    ]:
        path = os.path.join(out_dir, fname)
        with open(path, "w") as f:
            f.write(svg)
        print("wrote", path)


if __name__ == "__main__":
    main()
