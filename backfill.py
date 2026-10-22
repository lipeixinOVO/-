# -*- coding: utf-8 -*-
"""回填历史分数：用同一套规则重算过去 N 个交易日，让页面曲线上来就有内容。

关键：**不是造假数据**。每个历史日都用该日之前（as_of 截断）的数据重算，
不使用任何未来信息，因此曲线可复盘。

已知折衷（已在报告与页面标注）：
- 蛋卷 PB 分位只有当前值 → 回填期固定用当前分位（保证权重口径与当天一致，避免曲线上假跳变）
- 蛋卷 PE 历史为周频，回填到非周末日时取最近一周的值

用法：python backfill.py [天数，默认 120]
"""
import glob
import json
import os
import sys
import datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from src import sources as S      # noqa: E402
from src import engine as E       # noqa: E402
from src import compute as C      # noqa: E402
from src import history as HIST   # noqa: E402
from run_daily import load_ctx, _last  # noqa: E402

OUT_DIR = os.path.join(HERE, "data", "out")


def main(n_days=120, force=False):
    with open(os.path.join(HERE, "config.json"), encoding="utf-8") as f:
        cfg = json.load(f)

    print("· 加载数据（含全量历史）…", flush=True)
    ctx = load_ctx()

    # 交易日历用中证红利（A股）的日期；宏观序列按 as_of 各自截断
    cal = [r[0] for r in S.em_kline("1.000922")]
    cal = [d for d in cal if d >= "2021-01-01"]
    dates = cal[-n_days:]

    os.makedirs(OUT_DIR, exist_ok=True)
    written = skipped = 0
    for d in dates:
        path = os.path.join(OUT_DIR, f"{d}.json")
        if os.path.exists(path) and not force:
            skipped += 1
            continue
        assets = []
        for a in cfg["assets"]:
            try:
                r = C.COMPUTERS[a["id"]](a, ctx, as_of=d)
            except Exception as e:  # noqa: BLE001
                print(f"  ! {d} {a['id']} 跳过：{str(e)[:70]}", flush=True)
                continue
            score = E.composite(r["dims"])
            mult, label = E.multiplier_for(score, cfg["multiplier_table"])
            comp = E.completeness_of(r["dims"])
            trend = E.trend_flag(r["closes"])
            mult, gates = E.apply_gates(score, mult, r["dims"], comp, trend)
            assets.append({
                "id": a["id"], "name": a["name"], "kind": a["kind"],
                "advisory_only": a.get("advisory_only", False),
                "price": r.get("price"), "price_date": r.get("price_date"),
                "score": score, "multiplier": round(mult, 2), "label": label,
                "band_pos": E.band_position(score, cfg["multiplier_table"]),
                "completeness": comp,
                "suggest_amount": (round(cfg["base_amount"] * mult, 0)
                                   if not a.get("advisory_only") else None),
                "dimensions": r["dims"], "trend_flag": trend,
                "execution": {}, "gates": gates, "note": a.get("note", ""),
            })
        if not assets:
            continue
        snap = {
            "generated_at": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "trade_date": d,
            "backfilled": True,
            "base_amount": cfg["base_amount"],
            "scoring_basis": cfg.get("scoring_basis", "index"),
            "assets": assets,
            "macro": {
                "ust_10y_real": _last([x for x in (ctx.get("ust_real") or []) if x[0] <= d]),
                "ust_10y_nominal": _last([x for x in (ctx.get("ust_nominal") or []) if x[0] <= d]),
                "dxy": _last([x for x in (ctx.get("dxy") or []) if x[0] <= d]),
                "usdcnh": _last([x for x in (ctx.get("usdcny") or []) if x[0] <= d]),
            },
            "errors": [],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(snap, f, ensure_ascii=False, indent=2)
        HIST.append(d, assets)
        written += 1
        print(f"  ✓ {d}  " + "  ".join(f"{x['id']}={x['score']:.1f}" for x in assets), flush=True)

    print(f"\n回填完成：新写 {written} 天，跳过已存在 {skipped} 天")
    print("下一步：python build_site.py")


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 120
    main(n, force="--force" in sys.argv)
