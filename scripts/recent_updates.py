"""刷新个人主页 README 的三块内容（由 .github/workflows/recent-updates.yml 定时跑）：

- 近期更新：公开、非 fork 仓库按最新 Release 发布时间取前 5，写进 README 的 recent 标记之间
- assets/issues.svg：各仓库未关闭 Issue / PR 数量看板
- assets/langs.svg：各仓库语言占比
"""
import datetime
import json
import os
import re
import urllib.error
import urllib.request

USER = "Lianzy-Baimiao"
TOP = 5
TZ = datetime.timezone(datetime.timedelta(hours=8))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README = os.path.join(ROOT, "README.md")

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


def write(rel_path, text):
    path = os.path.join(ROOT, rel_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def own_repos():
    repos = api(f"/users/{USER}/repos?per_page=100&type=owner") or []
    return [r for r in repos if not r["fork"] and not r["archived"] and r["name"] != USER]


# ---------------------------------------------------------------------------
# 近期更新
# ---------------------------------------------------------------------------


def recent_updates(repos):
    items = []
    for repo in repos:
        rel = api(f"/repos/{USER}/{repo['name']}/releases/latest")
        if not rel or not rel.get("published_at"):
            continue
        when = datetime.datetime.fromisoformat(rel["published_at"].replace("Z", "+00:00")).astimezone(TZ)
        items.append((when, repo["name"], rel["tag_name"], rel["html_url"], repo.get("description") or ""))
    items.sort(reverse=True)

    rows = ["| 项目 | 版本 | 日期 | 简介 |", "| --- | :-: | :-: | --- |"]
    for when, name, tag, url, desc in items[:TOP]:
        desc = desc.replace("|", "/")
        if len(desc) > 24:
            desc = desc[:24] + "…"
        # U+2011 不换行连字符，日期列不会被挤成两行
        date = when.strftime("%Y-%m-%d").replace("-", "‑")
        rows.append(f"| [{name}](https://github.com/{USER}/{name}) | [{tag}]({url}) | {date} | {desc} |")
    block = (
        "<!-- recent:start -->\n<div align=\"center\">\n\n#### 近期更新 · Recent Releases\n\n"
        + "\n".join(rows)
        + "\n\n</div>\n<!-- recent:end -->"
    )

    with open(README, encoding="utf-8") as fh:
        text = fh.read()
    if "<!-- recent:start -->" in text:
        text = re.sub(r"<!-- recent:start -->.*?<!-- recent:end -->", lambda _: block, text, flags=re.S)
    else:
        text = text.rstrip() + "\n\n" + block + "\n"
    with open(README, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


# ---------------------------------------------------------------------------
# Issue / PR 看板
# ---------------------------------------------------------------------------


def pill(x, y, label, n, color):
    """一个「Issue 3」样式的胶囊；数量为 0 时置灰。"""
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
    height = top + rows * row_h + 10
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}">',
        f"<style>.n{{font:500 15px {FONT};fill:#c9d1d9}}.p{{font:700 14px {FONT}}}</style>",
        f'<rect width="{WIDTH}" height="{height}" rx="8" fill="{BG}"/>',
    ]
    for i, (name, issues, prs) in enumerate(data):
        x = (i % cols) * col_w + 16
        y = top + (i // cols) * row_h
        short = name.replace("astrbot_plugin_", "")
        if len(short) > 15:
            short = short[:14] + "…"
        out.append(f'<text x="{x}" y="{y + 17}" class="n">{esc(short)}</text>')
        out.append(pill(x + col_w - 160, y, "Iss", issues, "#e3b341"))
        out.append(pill(x + col_w - 96, y, "PR", prs, "#58a6ff"))
    out.append("</svg>")
    write("assets/issues.svg", "\n".join(out) + "\n")


# ---------------------------------------------------------------------------
# 语言占比
# ---------------------------------------------------------------------------

COLORS = {
    "Python": "#3572A5", "C#": "#178600", "JavaScript": "#f1e05a", "TypeScript": "#3178c6",
    "Lua": "#000080", "HTML": "#e34c26", "CSS": "#663399", "Vue": "#41b883", "Go": "#00ADD8",
    "Rust": "#dea584", "Java": "#b07219", "C++": "#f34b7d", "C": "#555555", "Shell": "#89e051",
    "PowerShell": "#012456", "Kotlin": "#A97BFF", "Swift": "#F05138", "Dart": "#00B4AB",
    "Slint": "#2379F4",
}
FALLBACK = ["#8b949e", "#d2a8ff", "#ffa657", "#7ee787", "#79c0ff", "#ff7b72"]


def languages_svg(repos, count=10):
    total = {}
    for repo in repos:
        for lang, size in (api(f"/repos/{USER}/{repo['name']}/languages") or {}).items():
            total[lang] = total.get(lang, 0) + size
    langs = sorted(total.items(), key=lambda kv: -kv[1])[:count]
    s = sum(v for _, v in langs) or 1

    x0, bar_w, cols = 30, WIDTH - 60, 5
    col_w = bar_w // cols
    rows = (len(langs) + cols - 1) // cols
    height = 110 + rows * 34
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}">',
        f"<style>.t{{font:600 22px {FONT};fill:#39d353}}.l{{font:500 15px {FONT};fill:#c9d1d9}}</style>",
        f'<rect width="{WIDTH}" height="{height}" rx="8" fill="{BG}"/>',
        f'<text x="{x0}" y="40" class="t">语言 · Languages</text>',
        f'<clipPath id="c"><rect x="{x0}" y="58" width="{bar_w}" height="12" rx="6"/></clipPath><g clip-path="url(#c)">',
    ]
    x = x0
    colors = []
    for i, (lang, v) in enumerate(langs):
        color = COLORS.get(lang, FALLBACK[i % len(FALLBACK)])
        colors.append(color)
        w = bar_w * v / s
        out.append(f'<rect x="{x:.2f}" y="58" width="{w + 0.5:.2f}" height="12" fill="{color}"/>')
        x += w
    out.append("</g>")
    for i, (lang, v) in enumerate(langs):
        cx = x0 + (i % cols) * col_w
        cy = 104 + (i // cols) * 34
        out.append(f'<circle cx="{cx + 6}" cy="{cy - 5}" r="6" fill="{colors[i]}"/>')
        out.append(f'<text x="{cx + 18}" y="{cy}" class="l">{esc(lang)} {v * 100 / s:.1f}%</text>')
    out.append("</svg>")
    write("assets/langs.svg", "\n".join(out) + "\n")


if __name__ == "__main__":
    repos = own_repos()
    recent_updates(repos)
    issues_svg(repos)
    languages_svg(repos)
