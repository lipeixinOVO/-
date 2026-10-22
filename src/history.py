# -*- coding: utf-8 -*-
"""历史分数累积文件 data/history.json。

为什么单独存一份而不是直接扫 data/out/*.json：
- data/out 里每天一份完整快照（含全部指标明细），120 天就有几 MB，
  推到 GitHub 要上百次 API 调用，Actions 每天也得拉全量。
- 画曲线只需要 date + 每个标的的 score/multiplier，压成一份几十 KB 的文件，
  每天只改这一个文件，同步成本降到最低。
- data/out 保留在本地用于复盘（不进仓库）。
"""
import json
import os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(HERE, "data", "history.json")


def load():
    """返回 [{'d': 'YYYY-MM-DD', 'a': {id: {'s': score, 'm': mult, 'p': band_pos}}}, ...]"""
    if not os.path.exists(PATH):
        return []
    try:
        with open(PATH, encoding="utf-8") as f:
            rows = json.load(f)
        return rows if isinstance(rows, list) else []
    except Exception:  # noqa: BLE001
        return []


def append(trade_date, assets):
    """写入/覆盖某一天的记录（同日重跑不会重复）。"""
    rows = load()
    rec = {"d": trade_date, "a": {}}
    for a in assets:
        rec["a"][a["id"]] = {"s": a["score"], "m": a["multiplier"],
                             "p": a.get("band_pos")}
    rows = [r for r in rows if r.get("d") != trade_date]
    rows.append(rec)
    rows.sort(key=lambda r: r.get("d") or "")
    os.makedirs(os.path.dirname(PATH), exist_ok=True)
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=0)
    return len(rows)


def to_series_payload(rows, names):
    """转成 build_site 需要的 series 结构。"""
    ids, series = [], {}
    for r in rows:
        for aid in (r.get("a") or {}):
            if aid not in series:
                ids.append(aid)
                series[aid] = []
            v = r["a"][aid]
            series[aid].append({"d": r["d"], "s": v.get("s"), "m": v.get("m"),
                                "p": v.get("p")})
    return ids, {i: names.get(i, i) for i in ids}, series
