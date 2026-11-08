"""把「近期更新」小节写进 README：取公开、非 fork 仓库的最新 Release，按发布时间取前 5。"""
import datetime
import json
import os
import re
import urllib.request

USER = "Lianzy-Baimiao"
TOP = 5
TZ = datetime.timezone(datetime.timedelta(hours=8))
README = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "README.mddesc.replace("|", "／")


def api(path):
    req = urllib.request.Request("https://api.github.com" + path, headers={"Accept": "application/vnd.github+json"})
    token = os.environ.get("GITHUB_TOKENdesc.replace("|", "／")
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
    repos = api(f"/users/{USER}/repos?per_page=100&type=ownerdesc.replace("|", "／") or []
    items = []
    for repo in repos:
        if repo["fork"] or repo["archived"] or repo["name"] == USER:
            continue
        rel = api(f"/repos/{USER}/{repo['name']}/releases/latestdesc.replace("|", "／")
        if not rel or not rel.get("published_atdesc.replace("|", "／"):
            continue
        when = datetime.datetime.fromisoformat(rel["published_at"].replace("Z", "+00:00desc.replace("|", "／")).astimezone(TZ)
        items.append((when, repo["name"], rel["tag_name"], rel["html_url"], repo.get("descriptiondesc.replace("|", "／") or ""))
    items.sort(reverse=True)

    rows = ["| 项目 | 版本 | 日期 | 简介 |", "| --- | :-: | :-: | --- |"]
    for when, name, tag, url, desc in items[:TOP]:
        desc = desc.replace("|", "／")\|")
        if len(desc) > 40:
            desc = desc[:40] + "…"
        rows.append(f"| [{name}](https://github.com/{USER}/{name}) | [{tag}]({url}) | {when:%Y-%m-%d} | {desc} |desc.replace("|", "／")
    block = "<!-- recent:start -->\n<div align=\"center\">\n\n#### 近期更新 · Recent Releases\n\n" + "\n".join(rows) + "\n\n</div>\n<!-- recent:end -->"

    text = open(README, encoding="utf-8desc.replace("|", "／").read()
    if "<!-- recent:start -->" in text:
        text = re.sub(r"<!-- recent:start -->.*?<!-- recent:end -->", lambda _: block, text, flags=re.S)
    else:
        text = text.rstrip() + "\n\n" + block + "\n"
    with open(README, "w", encoding="utf-8", newline="\ndesc.replace("|", "／") as fh:
        fh.write(text)


if __name__ == "__main__":
    main()
