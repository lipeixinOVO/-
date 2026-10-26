# -*- coding: utf-8 -*-
"""把 dca-dashboard 推到 GitHub（绕过被墙的 git，全走 REST API）。

用 Git Data API 做**单次提交**：blobs → tree → commit → 更新 ref，
比逐个文件 Contents API 快一个数量级（1 次 commit 而不是 N 次）。

两个曾经造成事故的点，改之前先读：

1. **tree 必须带 base_tree**。不带就是「用这份 tree 完全替换仓库」，
   远端不在本次清单里的文件会被**删除**。2026-10-26 就这么把云端跑批累积的
   data/out/*.json 每日快照清空了（远端只剩 latest.json），分数历史图直接断档。

2. **docs/ 是跑批产物，默认不推**。data.json / index.html 由 Actions 每次跑批
   重新生成并提交；本地这份是上次手工 build 的，一旦推上去就把线上数据回退。
   2026-10-26 就是这样把 10-26 的最新数据覆盖成 10-24 的旧数据，
   页面上「创业板指÷中证红利」「二十二年两条线」全部退回 10-23。

   改完源码（src/、tools/）后正确姿势是：推代码 → 触发一次 workflow_dispatch，
   让云端用最新数据重新渲染。要本地渲染预览用 --site。

用法：
    python push_github.py                  # 建仓库（若不存在）+ 推源码
    python push_github.py -m "说明"        # 自定义提交信息
    python push_github.py --dry            # 只列要推的文件
    python push_github.py --site           # 连 docs/ 一起推（离线预览用，慎用）
    python push_github.py --with-data      # 连 data/out 每日快照一起推（恢复历史用）
"""
import base64
import json
import os
import re
import sys
from pathlib import Path

import requests

OWNER = "lipeixinOVO"
REPO = os.environ.get("GH_REPO", "-")   # 实际仓库名就是一个减号
BRANCH = "main"
LOCAL = Path(r"C:/Users/27576/Desktop/ai/定投台/dca-dashboard")
CRED = Path(os.path.expanduser("~")) / ".git-credentials"
API = "https://api.github.com"

# 不进仓库的：接口缓存（易变、体积大）、每日完整快照（本地复盘用）、本地截图
SKIP_DIRS = {"cache", "__pycache__", ".git", "node_modules"}
# 截图相关目录用**前缀**匹配：shot.py / peek.py 每次换个 _shot_profile<N> 名字，
# 写死名单会漏（2026-10-24 就因为 _shot_profile2~5 各 13MB 被当成源码上传，推了 6 分钟）。
SKIP_DIR_PREFIX = ("_shot", "_peek")
SKIP_NAMES = {".DS_Store", "_selfcheck.js", "_shot_wrap.html", "_peek.html"}   # 临时产物不进仓库


def token():
    for line in CRED.read_text(encoding="utf-8").splitlines():
        m = re.match(r"https://([^@\s]+)@github\.com/?$", line.strip())
        if m:
            c = m.group(1)
            return c.split(":")[0] if ":" in c else c
    raise RuntimeError("未找到 GitHub token")


H = {"Authorization": f"Bearer {token()}", "Accept": "application/vnd.github+json",
     "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "workbuddy-sync"}


def collect(include_site=False, include_data=False):
    out = []
    for p in sorted(LOCAL.rglob("*")):
        if p.is_dir():
            continue
        rel = p.relative_to(LOCAL)
        parts = set(rel.parts)
        if parts & SKIP_DIRS or p.name in SKIP_NAMES:
            continue
        # 前缀匹配截图/调试目录（_shot_profile2、_shots、_peek…）
        if any(part.startswith(SKIP_DIR_PREFIX) for part in rel.parts):
            continue
        # docs/ 整体是跑批产物（index.html / data.json / report.md），云端生成。
        # 推本地这份 = 用陈旧数据覆盖线上，务必只在明确要离线预览时加 --site。
        if rel.parts[:1] == ("docs",) and not include_site:
            continue
        # data/out 只留 latest 与 report，其余每日快照默认不推（云端累积）
        if rel.parts[:2] == ("data", "out") and p.name not in ("latest.json", "report.md"):
            if not include_data:
                continue
        if p.suffix in (".pyc", ".log"):
            continue
        out.append((rel.as_posix(), p))
    return out


def ensure_repo():
    r = requests.get(f"{API}/repos/{OWNER}/{REPO}", headers=H, timeout=25)
    if r.status_code == 200:
        print(f"仓库已存在：{r.json()['full_name']}（{r.json().get('visibility')}）")
        return r.json()
    if r.status_code != 404:
        raise RuntimeError(f"查询仓库失败 {r.status_code}: {r.text[:200]}")
    print("仓库不存在，创建中…")
    r = requests.post(f"{API}/user/repos", headers=H, timeout=30, json={
        "name": REPO,
        "description": "定投台 · 五标的定投倍数看板（纳指100 / 黄金 / MSCI全球医疗 / 中证红利 / 纳指综指）",
        "private": False,
        "has_issues": True,
        "has_wiki": False,
        "auto_init": True,          # 生成 initial commit，便于建 ref
    })
    if r.status_code not in (200, 201):
        raise RuntimeError(f"创建仓库失败 {r.status_code}: {r.text[:300]}")
    print(f"已创建：{r.json()['html_url']}")
    return r.json()


def get_head_sha():
    import time
    for _ in range(6):
        r = requests.get(f"{API}/repos/{OWNER}/{REPO}/git/ref/heads/{BRANCH}",
                         headers=H, timeout=25)
        if r.status_code == 200:
            return r.json()["object"]["sha"]
        time.sleep(2)   # auto_init 建 ref 有一两秒延迟
    # 仓库是空的（没有 initial commit）→ 用 Contents API 建个 README 触发首次提交
    print("仓库为空，先创建初始提交…")
    r = requests.put(f"{API}/repos/{OWNER}/{REPO}/contents/README.md", headers=H, timeout=30,
                     json={"message": "init", "content": base64.b64encode(b"# dca-dashboard\n").decode()})
    if r.status_code not in (200, 201):
        raise RuntimeError(f"初始化失败 {r.status_code}: {r.text[:300]}")
    r = requests.get(f"{API}/repos/{OWNER}/{REPO}/git/ref/heads/{BRANCH}", headers=H, timeout=25)
    r.raise_for_status()
    return r.json()["object"]["sha"]


def blob(p):
    data = p.read_bytes()
    r = requests.post(f"{API}/repos/{OWNER}/{REPO}/git/blobs", headers=H, timeout=60,
                      json={"content": base64.b64encode(data).decode(), "encoding": "base64"})
    r.raise_for_status()
    return r.json()["sha"]


def enable_pages():
    """启用 GitHub Pages，源指向 main /docs。已开启或权限不足都不算失败。"""
    r = requests.get(f"{API}/repos/{OWNER}/{REPO}", headers=H, timeout=25)
    if r.status_code == 200 and r.json().get("has_pages"):
        print(f"Pages 已启用：https://{OWNER.lower()}.github.io/{REPO}/")
        return
    r = requests.post(f"{API}/repos/{OWNER}/{REPO}/pages", headers=H, timeout=30,
                      json={"source": {"branch": BRANCH, "path": "/docs"}})
    if r.status_code in (201, 204):
        print(f"Pages 已启用：https://{OWNER.lower()}.github.io/{REPO}/")
    elif r.status_code == 409:
        print(f"Pages 之前已启用：https://{OWNER.lower()}.github.io/{REPO}/")
    else:
        print(f"⚠ Pages 自动启用失败（{r.status_code}）——首次启用必须手动到 Settings → Pages，"
              f"Source 选 Deploy from a branch，Branch 选 main / docs（个人 token 与 GITHUB_TOKEN 都无权建站）")


def head_tree(commit_sha):
    """取 HEAD commit 的 tree sha，作为新建 tree 的 base_tree。

    少了这个字段，Git Data API 会把「本次给的 tree」当成仓库的全部内容，
    远端其余文件一律删除 —— 不是「只改我推的这几个」。
    """
    r = requests.get(f"{API}/repos/{OWNER}/{REPO}/git/commits/{commit_sha}",
                     headers=H, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"取 commit 失败 {r.status_code}: {r.text[:200]}")
    return r.json()["tree"]["sha"]


def main(dry=False, include_site=False, include_data=False, message=None):
    files = collect(include_site, include_data)
    total = sum(p.stat().st_size for _, p in files)
    print(f"待推 {len(files)} 个文件，共 {total/1024:.0f} KB")
    if not include_site:
        print("（docs/ 不推：那是跑批产物，改了 src/ 就触发一次 workflow_dispatch 让云端重渲染）")
    if dry:
        for rel, p in files:
            print(f"  {rel}  ({p.stat().st_size/1024:.1f} KB)")
        return

    ensure_repo()
    head = get_head_sha()
    base = head_tree(head)
    print(f"当前 HEAD: {head[:8]}  base_tree: {base[:8]}")

    tree = []
    for i, (rel, p) in enumerate(files, 1):
        sha = blob(p)
        tree.append({"path": rel, "mode": "100644", "type": "blob", "sha": sha})
        print(f"  [{i}/{len(files)}] {rel}", flush=True)

    r = requests.post(f"{API}/repos/{OWNER}/{REPO}/git/trees", headers=H, timeout=60,
                      json={"tree": tree, "base_tree": base})
    r.raise_for_status()
    tree_sha = r.json()["sha"]

    import time as _t
    msg = message or f"chore: 同步源码 {_t.strftime('%Y-%m-%d %H:%M')}"
    r = requests.post(f"{API}/repos/{OWNER}/{REPO}/git/commits", headers=H, timeout=60, json={
        "message": msg,
        "tree": tree_sha,
        "parents": [head],
    })
    if r.status_code not in (200, 201):
        raise RuntimeError(f"建 commit 失败 {r.status_code}: {r.text[:400]}")
    commit_sha = r.json()["sha"]

    r = requests.patch(f"{API}/repos/{OWNER}/{REPO}/git/refs/heads/{BRANCH}", headers=H,
                       timeout=30, json={"sha": commit_sha, "force": False})
    if r.status_code not in (200, 201):
        raise RuntimeError(f"更新 ref 失败 {r.status_code}: {r.text[:400]}")
    print(f"\n推送完成：https://github.com/{OWNER}/{REPO}/commit/{commit_sha[:8]}")
    enable_pages()


if __name__ == "__main__":
    argv = sys.argv[1:]
    msg = None
    if "-m" in argv:
        i = argv.index("-m")
        if i + 1 < len(argv):
            msg = argv[i + 1]
            argv = argv[:i] + argv[i + 2:]
    main(dry="--dry" in argv,
         include_site="--site" in argv,
         include_data="--with-data" in argv,
         message=msg)
