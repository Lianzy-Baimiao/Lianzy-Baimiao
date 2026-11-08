"""生成个人主页 README 用的两张图（由 .github/workflows/recent-updates.yml 定时跑）：

- assets/issues.svg：各仓库未关闭 Issue / PR 数量看板
- assets/recent.svg：近期更新，公开、非 fork 仓库按最新 Release 发布时间取前 5

两张图都是 840 宽，和 README 里贪吃蛇图的宽度一致。
"""
import datetime
import json
import os
import urllib.error
import urllib.request

USER = "Lianzy-Baimiao"
TOP = 5
TZ = datetime.timezone(datetime.timedelta(hours=8))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

WIDTH = 840
BG = "#0d1117"
FONT = '"Segoe UI",Ubuntu,"Microsoft YaHei",sans-serif'


def api(path):
    req = urllib.request.Request("https://api.github.com" + path, headers={"Accept": "application/vnd.github+json"})
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def clip(s, n):
    return s if len(s) <= n else s[: n - 1] + "…"


def write(rel_path, lines):
    path = os.path.join(ROOT, rel_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")


def svg_head(height, style):
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}">',
        f"<style>{style}</style>",
        f'<rect width="{WIDTH}" height="{height}" rx="8" fill="{BG}"/>',
    ]


def own_repos():
    repos = api(f"/users/{USER}/repos?per_page=100&type=owner") or []
    return [r for r in repos if not r["fork"] and not r["archived"] and r["name"] != USER]


# ---------------------------------------------------------------------------
# 近期更新
# ---------------------------------------------------------------------------


def recent_svg(repos):
    items = []
    for repo in repos:
        rel = api(f"/repos/{USER}/{repo['name']}/releases/latest")
        if not rel or not rel.get("published_at"):
            continue
        when = datetime.datetime.fromisoformat(rel["published_at"].replace("Z", "+00:00")).astimezone(TZ)
        items.append((when, repo["name"], rel["tag_name"], repo.get("description") or ""))
    items.sort(reverse=True)
    items = items[:TOP]

    row_h, top = 40, 18
    height = top + max(len(items), 1) * row_h + 8
    out = svg_head(
        height,
        f".n{{font:600 15px {FONT};fill:#c9d1d9}}.v{{font:700 13px {FONT};fill:#0d1117}}"
        f".d{{font:500 14px {FONT};fill:#8b949e}}.s{{font:400 14px {FONT};fill:#8b949e}}",
    )
    for i, (when, name, tag, desc) in enumerate(items):
        y = top + i * row_h
        if i:
            out.append(f'<line x1="16" y1="{y - 8}" x2="{WIDTH - 16}" y2="{y - 8}" stroke="#21262d"/>')
        out.append(f'<text x="16" y="{y + 17}" class="n">{esc(clip(name, 30))}</text>')
        out.append(f'<rect x="270" y="{y}" width="78" height="24" rx="12" fill="#39d353"/>')
        out.append(f'<text x="309" y="{y + 17}" text-anchor="middle" class="v">{esc(clip(tag, 10))}</text>')
        out.append(f'<text x="364" y="{y + 17}" class="d">{when:%Y-%m-%d}</text>')
        out.append(f'<text x="470" y="{y + 17}" class="s">{esc(clip(desc, 24))}</text>')
    out.append("</svg>")
    write("assets/recent.svg", out)


# ---------------------------------------------------------------------------
# Issue / PR 看板
# ---------------------------------------------------------------------------


def pill(x, y, label, n, color):
    """一个「Iss 3」样式的胶囊；数量为 0 时置灰。"""
    fill = color if n else "#21262d"
    fg = "#0d1117" if n else "#8b949e"
    w = 58
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="24" rx="12" fill="{fill}"/>'
        f'<text x="{x + w / 2}" y="{y + 17}" text-anchor="middle" class="p" fill="{fg}">{label} {n}</text>'
    )


def issues_svg(repos):
    data = []
    for repo in repos:
        prs = len(api(f"/repos/{USER}/{repo['name']}/pulls?state=open&per_page=100") or [])
        issues = max(repo.get("open_issues_count", 0) - prs, 0)
        data.append((repo["name"], issues, prs))
    data.sort(key=lambda d: (-(d[1] + d[2]), d[0].lower()))

    cols, col_w, row_h, top = 3, WIDTH // 3, 44, 20
    rows = (len(data) + cols - 1) // cols
    out = svg_head(top + rows * row_h + 10, f".n{{font:500 15px {FONT};fill:#c9d1d9}}.p{{font:700 14px {FONT}}}")
    for i, (name, issues, prs) in enumerate(data):
        x = (i % cols) * col_w + 16
        y = top + (i // cols) * row_h
        out.append(f'<text x="{x}" y="{y + 17}" class="n">{esc(clip(name.replace("astrbot_plugin_", ""), 15))}</text>')
        out.append(pill(x + col_w - 160, y, "Iss", issues, "#e3b341"))
        out.append(pill(x + col_w - 96, y, "PR", prs, "#58a6ff"))
    out.append("</svg>")
    write("assets/issues.svg", out)


if __name__ == "__main__":
    repos = own_repos()
    issues_svg(repos)
    recent_svg(repos)
