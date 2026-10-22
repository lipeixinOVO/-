# -*- coding: utf-8 -*-
"""定投台每日跑批：拉数据 → 算分 → 出快照 + 报告。

用法：
    python run_daily.py            # 跑一次，写 data/out/
    python run_daily.py --dry      # 只打印，不落盘
"""
import json
import os
import sys
import time
import datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from src import sources as S          # noqa: E402
from src import engine as E           # noqa: E402
from src import compute as C          # noqa: E402

DJ_H = {"Referer": "https://danjuanfunds.com/"}


def load_ctx():
    ctx = {"errors": []}
    ty = dt.date.today().year
    # 利率取全历史（TIPS 2003 年起）而不是近 10 年：2010 年代是人为低利率的异常期，
    # 只拿这 10 年做分位会把当前的 2.7% 打成 99 分位，机械地压低所有美元资产的分数。
    years = list(range(2003, ty + 1))

    print("· 拉取美债实际利率（美国财政部，逐年 CSV）…", flush=True)
    ctx["ust_real"] = S.treasury_curve("real", years)
    print(f"  → {len(ctx['ust_real'])} 个交易日", flush=True)

    print("· 拉取美债名义利率…", flush=True)
    ctx["ust_nominal"] = S.treasury_curve("nominal", years)
    print(f"  → {len(ctx['ust_nominal'])} 个交易日", flush=True)

    print("· 拉取沪深300（宏观用）…", flush=True)
    try:
        rows, src = C.try_chain({"type": "sina_cn", "symbol": "sh000300",
                                 "fallback": [{"type": "em_kline", "secid": "1.000300"},
                                              {"type": "tx_kline", "secid": "1.000300"}]},
                                ctx, label="hs300")
        ctx["hs300"] = [(r[0], r[1]) for r in rows]
        print(f"  → hs300: {len(rows)} 条（{src}）", flush=True)
    except Exception as e:  # noqa: BLE001
        ctx["hs300"] = []
        ctx["errors"].append(f"hs300: {e}")

    # 美元指数 / 离岸人民币：**仅用于页面展示，不参与打分**。
    # 这两个东财 secid（100.UDI / 133.USDCNH）在 GitHub Runner 上必断连，
    # 若拿来打分会让"同一天、不同机器"算出不同倍率，所以只做参考显示。
    for key, secid in (("dxy", "100.UDI"), ("usdcny", "133.USDCNH")):
        try:
            rows = S.em_kline(secid)
            ctx[key] = [(r[0], r[1]) for r in rows]
            print(f"  → {key}: {len(rows)} 条（仅展示）", flush=True)
        except Exception:  # noqa: BLE001
            ctx[key] = []
            ctx.setdefault("notes", []).append(f"{key} 本期取不到（仅展示项，不影响分数）")
        time.sleep(0.8)

    try:
        ctx["spx"] = S.sina_us_daily(".INX")
        print(f"  → spx: {len(ctx['spx'])} 条", flush=True)
    except Exception as e:  # noqa: BLE001
        ctx["spx"] = []
        ctx["errors"].append(f"spx: {e}")

    try:
        ctx["gold_spot"] = S.sina_snapshot("hf_XAU")
    except Exception:  # noqa: BLE001
        ctx["gold_spot"] = {}

    print("· 拉取指数估值（蛋卷）…", flush=True)
    C.load_valuation_anchors(ctx)
    return ctx


def explain(a):
    """用规则生成一句人话结论，不经过 LLM。"""
    dims = {d["key"]: d for d in a["dimensions"]}
    parts = []
    val = dims.get("valuation", {}).get("score")
    tr = dims.get("trend", {}).get("score")
    if val is not None:
        parts.append("估值偏贵" if val < 40 else ("估值偏便宜" if val > 60 else "估值中性"))
    if tr is not None:
        parts.append("价格在均值下方" if tr > 60 else ("价格明显高于均值" if tr < 40 else "价格居中"))
    head = f"综合 {a['score']:.1f} 分 → {a['multiplier']:.1f} 倍（{a['label']}）"
    return head + "：" + "，".join(parts) + "。"


def run(dry=False):
    with open(os.path.join(HERE, "config.json"), encoding="utf-8") as f:
        cfg = json.load(f)

    print("=" * 72)
    print("定投台 · 每日跑批")
    print("=" * 72)
    ctx = load_ctx()

    results = []
    for a in cfg["assets"]:
        print(f"· 计算 {a['name']} …", flush=True)
        fn = C.COMPUTERS[a["id"]]
        try:
            r = fn(a, ctx)
        except Exception as e:  # noqa: BLE001
            ctx["errors"].append(f"{a['id']}: {e}")
            print(f"  ✗ 失败：{e}", flush=True)
            continue

        score = E.composite(r["dims"])
        mult, label = E.multiplier_for(score, cfg["multiplier_table"])
        comp = E.completeness_of(r["dims"])
        trend = E.trend_flag(r["closes"])
        mult, gates = E.apply_gates(score, mult, r["dims"], comp, trend)

        # 执行可行性：只作提示，不影响倍数（用户要求只输出评分与倍率）
        ex = a.get("execution") or {}
        ex_status = {}
        if ex.get("fund_code"):
            def _probe(code, name, te=None):
                try:
                    st = S.fund_status(code)
                    return {"fund_code": code, "fund_name": name, "tracking_error": te, **st}
                except Exception as e:  # noqa: BLE001
                    return {"fund_code": code, "fund_name": name, "tracking_error": te, "error": str(e)}

            ex_status = {"why": ex.get("why"), **_probe(ex["fund_code"], ex.get("fund_name"),
                                                       ex.get("tracking_error"))}
            time.sleep(0.8)
            fbs = []
            for fb in ex.get("fallbacks") or []:
                fbs.append(_probe(fb["code"], fb.get("name"), fb.get("tracking_error")))
                time.sleep(0.8)
            ex_status["fallbacks"] = fbs

        item = {
            "id": a["id"],
            "name": a["name"],
            "kind": a["kind"],
            "advisory_only": a.get("advisory_only", False),
            "price": r.get("price"),
            "price_date": r.get("price_date"),
            "score": score,
            "multiplier": round(mult, 2),
            "label": label,
            "band_pos": E.band_position(score, cfg["multiplier_table"]),
            "completeness": comp,
            "suggest_amount": round(cfg["base_amount"] * mult, 0) if not a.get("advisory_only") else None,
            "dimensions": r["dims"],
            "trend_flag": trend,
            "execution": ex_status,
            "fund_meta": r.get("fund_meta") or {},
            "gates": gates,
            "note": a.get("note", ""),
        }
        item["conclusion"] = explain(item)
        results.append(item)
        print(f"  → {item['score']:.1f} 分 / {item['multiplier']:.1f} 倍 / 完整度 {comp:.0%}"
              + (f" / 闸门 {len(gates)}" if gates else ""), flush=True)
        print("     维度 " + " ".join(
            f"{d['key'][:5]}={d['score']:.0f}(w{d['weight']},缺{d.get('missing_ratio', 0):.0%})"
            for d in item["dimensions"]), flush=True)
        time.sleep(0.6)

    alts = []
    for a in cfg["assets"]:
        for alt in a.get("alternatives") or []:
            try:
                st = S.fund_status(alt["code"])
                alts.append({"code": alt["code"], "name": alt["name"], **st})
            except Exception as e:  # noqa: BLE001
                alts.append({"code": alt["code"], "name": alt["name"], "error": str(e)})
            time.sleep(0.8)

    if ctx.get("errors"):
        print("\n· 数据源错误汇总（这些缺口会直接压低完整度）：", flush=True)
        for e in ctx["errors"]:
            print(f"   ✗ {str(e)[:200]}", flush=True)

    out = {
        "generated_at": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "trade_date": dt.date.today().isoformat(),
        "base_amount": cfg["base_amount"],
        "scoring_basis": cfg.get("scoring_basis", "index"),
        "multiplier_table": cfg["multiplier_table"],
        "assets": results,
        "alternatives": alts,
        "macro": {
            "ust_10y_real": _last(ctx.get("ust_real")),
            "ust_10y_nominal": _last(ctx.get("ust_nominal")),
            "dxy": _last(ctx.get("dxy")),
            "usdcnh": _last(ctx.get("usdcny")),
            "gold_spot": (ctx.get("gold_spot") or {}).get("price"),
        },
        "errors": ctx.get("errors", []),
        # 主力源失败、自动回退到备用源时记在这里，页面上要能看见（否则数据"悄悄换源"）
        "data_notes": ctx.get("notes", []),
    }

    if not dry:
        os.makedirs(os.path.join(HERE, "data", "out"), exist_ok=True)
        day_path = os.path.join(HERE, "data", "out", f"{out['trade_date']}.json")
        with open(day_path, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        with open(os.path.join(HERE, "data", "out", "latest.json"), "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        from src import render as R
        from src import history as H
        md = R.to_markdown(out)
        for p in (os.path.join(HERE, "data", "out", "report.md"),
                  os.path.join(HERE, "docs", "report.md")):
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                f.write(md)
        n = H.append(out["trade_date"], out["assets"])
        print(f"\n历史序列已更新：{n} 期")
        print(f"\n已写出：{day_path}")
        print(f"已写出：data/out/report.md")

    return out


def _last(seq):
    if not seq:
        return None
    last = seq[-1]
    return last[1] if isinstance(last, tuple) else last


if __name__ == "__main__":
    run(dry="--dry" in sys.argv)
