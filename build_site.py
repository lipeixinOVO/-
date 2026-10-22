# -*- coding: utf-8 -*-
"""把 data/out/*.json 汇总成站点：site/index.html（数据内联，无需 fetch）+ site/data.json。

设计取舍：
- 数据**内联进 HTML**，不在前端 fetch。GitHub Pages 是纯静态托管，
  fetch 同源 JSON 在本地 file:// 打开时会被 CORS 拦掉，内联则在本地双击和线上都能跑。
- 历史曲线来自 data/out/ 下每天一个的快照文件，累积越多越有意义。
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, "data", "out")
# GitHub Pages 只支持「根目录」或「/docs」，所以站点输到 docs/
SITE_DIR = os.path.join(HERE, "docs")

sys.path.insert(0, HERE)


def load_history():
    """读所有日快照，按日期升序。"""
    rows = []
    for p in sorted(glob.glob(os.path.join(OUT_DIR, "*.json"))):
        name = os.path.basename(p)
        if name in ("latest.json", "history.json"):
            continue
        try:
            with open(p, encoding="utf-8") as f:
                d = json.load(f)
            if d.get("assets"):
                rows.append(d)
        except Exception:  # noqa: BLE001
            continue
    rows.sort(key=lambda x: x.get("trade_date") or "")
    return rows


def build_series(history):
    """抽出每个标的的 (date, score, multiplier) 序列。

    只保留画曲线需要的字段——完整快照含全部指标明细，120 天内联进 HTML 会到 1.8MB，
    手机上打开会明显卡。latest 保留完整数据用于卡片渲染。
    """
    ids, names, series = [], {}, {}
    for snap in history:
        d = snap.get("trade_date")
        for a in snap["assets"]:
            aid = a["id"]
            if aid not in series:
                ids.append(aid)
                names[aid] = a["name"]
                series[aid] = []
            series[aid].append({"d": d, "s": a["score"], "m": a["multiplier"]})
    return ids, names, series


def slim_history(history):
    return [{"trade_date": s.get("trade_date"),
             "assets": [{"id": a.get("id"), "score": a.get("score"),
                         "multiplier": a.get("multiplier"),
                         "band_pos": a.get("band_pos")} for a in s.get("assets", [])]}
            for s in history]


def main():
    latest_path = os.path.join(OUT_DIR, "latest.json")
    if not os.path.exists(latest_path):
        raise SystemExit("没有 latest.json，先跑 run_daily.py")
    with open(latest_path, encoding="utf-8") as f:
        latest = json.load(f)

    from src import history as H
    rows = H.load()
    names = {a["id"]: a["name"] for a in latest["assets"]}
    ids, names, series = H.to_series_payload(rows, names)
    payload = {"latest": latest,
               "history": [{"trade_date": r["d"]} for r in rows],
               "series": {"ids": ids, "names": names, "data": series}}

    os.makedirs(SITE_DIR, exist_ok=True)
    with open(os.path.join(SITE_DIR, "data.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    from src import site_template as T
    html = T.render(payload)
    with open(os.path.join(SITE_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print(f"已生成 docs/index.html（{len(html)/1024:.1f} KB），历史 {len(rows)} 期")


if __name__ == "__main__":
    main()
