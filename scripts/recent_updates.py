"""把「近期更新」小节写进 README：取公开、非 fork 仓库的最新 Release，按发布时间取前 5。"""
import datetime
import json
import os
import re
import urllib.error
import urllib.request

USER = "Lianzy-Baimiao"
TOP = 5
TZ = datetime.timezone(datetime.timedelta(hours=8))
README = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "README.md")


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


def main():
    repos = api(f"/users/{USER}/repos?per_page=100&type=owner") or []
    items = []
    for repo in repos:
        if repo["fork"] or repo["archived"] or repo["name"] == USER:
            continue
        rel = api(f"/repos/{USER}/{repo['name']}/releases/latest")
        if not rel or not rel.get("published_at"):
            continue
        when = datetime.datetime.fromisoformat(rel["published_at"].replace("Z", "+00:00")).astimezone(TZ)
        items.append((when, repo["name"], rel["tag_name"], rel["html_url"], repo.get("description") or ""))
    items.sort(reverse=True)

    rows = ["| 项目 | 版本 | 日期 | 简介 |", "| --- | :-: | :-: | --- |"]
    for when, name, tag, url, desc in items[:TOP]:
        desc = desc.replace("|", "/")
        if len(desc) > 40:
            desc = desc[:40] + "…"
        rows.append(f"| [{name}](https://github.com/{USER}/{name}) | [{tag}]({url}) | {when:%Y-%m-%d} | {desc} |")
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


COLORS = {
    "Python": "#3572A5", "C#": "#178600", "JavaScript": "#f1e05a", "TypeScript": "#3178c6",
    "Lua": "#000080", "HTML": "#e34c26", "CSS": "#663399", "Vue": "#41b883", "Go": "#00ADD8",
    "Rust": "#dea584", "Java": "#b07219", "C++": "#f34b7d", "C": "#555555", "Shell": "#89e051",
    "PowerShell": "#012456", "Kotlin": "#A97BFF", "Swift": "#F05138", "Dart": "#00B4AB",
}
FALLBACK = ["#8b949e", "#d2a8ff", "#ffa657", "#7ee787", "#79c0ff", "#ff7b72"]


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def languages_svg(count=10):
    """汇总公开、非 fork 仓库的语言字节数，画成和原来 top-langs compact 布局类似的 SVG。"""
    total = {}
    for repo in api(f"/users/{USER}/repos?per_page=100&type=owner") or []:
        if repo["fork"] or repo["archived"]:
            continue
        for lang, size in (api(f"/repos/{USER}/{repo['name']}/languages") or {}).items():
            total[lang] = total.get(lang, 0) + size
    langs = sorted(total.items(), key=lambda kv: -kv[1])[:count]
    s = sum(v for _, v in langs) or 1
    width, x0, bar_w = 350, 25, 300
    rows = (len(langs) + 1) // 2
    height = 95 + rows * 25
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<rect width="{width}" height="{height}" rx="6" fill="#0d1117"/>',
        '<style>.t{font:600 18px "Segoe UI",Ubuntu,sans-serif;fill:#39d353}.l{font:400 11px "Segoe UI",Ubuntu,sans-serif;fill:#c9d1d9}</style>',
        '<text x="25" y="35" class="t">语言 · Languages</text>',
        f'<clipPath id="c"><rect x="{x0}" y="55" width="{bar_w}" height="8" rx="4"/></clipPath><g clip-path="url(#c)">',
    ]
    x = x0
    colors = []
    for i, (lang, v) in enumerate(langs):
        color = COLORS.get(lang, FALLBACK[i % len(FALLBACK)])
        colors.append(color)
        w = bar_w * v / s
        out.append(f'<rect x="{x:.2f}" y="55" width="{w + 0.5:.2f}" height="8" fill="{color}"/>')
        x += w
    out.append("</g>")
    for i, (lang, v) in enumerate(langs):
        cx = x0 + (i % 2) * 150
        cy = 90 + (i // 2) * 25
        out.append(f'<circle cx="{cx + 5}" cy="{cy - 4}" r="5" fill="{colors[i]}"/>')
        out.append(f'<text x="{cx + 15}" y="{cy}" class="l">{esc(lang)} {v * 100 / s:.2f}%</text>')
    out.append("</svg>")
    path = os.path.join(os.path.dirname(README), "assets", "langs.svg")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
    languages_svg()
