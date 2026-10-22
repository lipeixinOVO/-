# -*- coding: utf-8 -*-
"""观察型模块：把两张「长期规则图」变成每天重算的动态指标。

不参与打分、不影响倍率 —— 它们回答的是另一类问题：
    「这个资产现在离长期锚有多远」「如果换标的，现在该偏向哪一边」

① 中证红利月线锚（来源：民间经验规则，非学术结论）
   - 40 月均线 ≈ 估值中枢；90 月均线 ≈ 深度低估的参考买点
   - 页面只呈现「当前点位 vs 这两条线偏离多少」，不给买卖指令
② 创业板指 / 中证红利 比值（"直接指数相除"）
   - 0.3 附近被视为创业板相对红利便宜的观察点
③ 沪深300全收益 vs 全市场全收益：22 年长期曲线（对数轴）

口径说明（必须写清楚，否则数字会被误读）：
- ① 用中证指数官网 000922 全历史日线，按月取最后交易日收盘再算均线；
  MA90 需要 90 个月，所以均线从 2012 年前后才有值，早期是空白。
- ② 创业板指用新浪 sz399006，接口单次上限 3000 条 → 历史只到 2014-06；
  因此分位数是「近 12 年」分位，不是全历史。
- ③ 原始图用的是万得全A(800707.WI)，属 Wind 商业数据、公开接口取不到，
  改用中证全指全收益 (H00985) 替代：同为全市场口径、含分红再投、
  同样以 2004-01-01 = 1000 为基点，与万得全A 的起点只差一天，形态可比但不完全等价。
"""
import datetime as dt

from . import sources as S


# ------------------------------------------------------------------ 工具
def _monthly(rows):
    """日线 [(date, close, ...)] → [(YYYY-MM, close)]，取每月最后一个交易日。

    输入必须按日期升序（csindex_perf 已排序），后者自然覆盖前者。
    """
    m = {}
    for r in rows:
        d = str(r[0])
        if len(d) != 10:
            continue
        m[d[:7]] = float(r[1])
    return sorted(m.items())


def _ma(series, w):
    """月序列的滚动均值，前 w-1 个返回 None。"""
    out, s = [], 0.0
    for i, (_k, v) in enumerate(series):
        s += v
        if i >= w:
            s -= series[i - w][1]
        out.append(round(s / w, 2) if i >= w - 1 else None)
    return out


def _downsample(pts, cap):
    """等间隔抽稀到 cap 点以内，保留首尾。"""
    n = len(pts)
    if n <= cap:
        return pts
    step = n / float(cap)
    keep = [pts[int(i * step)] for i in range(cap)]
    if keep[-1] is not pts[-1]:
        keep[-1] = pts[-1]
    return keep


def _pct_rank(vals, cur):
    """cur 在 vals 里的分位（0–100，越小越便宜）。"""
    n = len(vals)
    if not n:
        return None
    return round(100.0 * sum(1 for v in vals if v <= cur) / n, 1)


def _cagr(first, last, d0, d1):
    try:
        years = (dt.date.fromisoformat(d1) - dt.date.fromisoformat(d0)).days / 365.25
        if years <= 0 or first <= 0 or last <= 0:
            return None
        return round((last / first) ** (1.0 / years) * 100 - 100, 2)
    except Exception:  # noqa: BLE001
        return None


# ------------------------------------------------------------------ 三个模块
def dividend_anchor(rows):
    """中证红利月线与 40/90 月均线。"""
    ms = _monthly(rows)
    if len(ms) < 40:
        raise RuntimeError(f"中证红利月线不足 40 期（{len(ms)}）")
    ma40, ma90 = _ma(ms, 40), _ma(ms, 90)
    series = [[ms[i][0], round(ms[i][1], 2), ma40[i], ma90[i]] for i in range(len(ms))]
    cur = series[-1]
    close, m40, m90 = cur[1], cur[2], cur[3]

    def dev(base):
        return round((close / base - 1) * 100, 2) if base else None

    # 当前偏离在历史上的分位（按同一口径：收盘 / 对应均线）
    d90 = [(s[1] / s[3] - 1) for s in series if s[3]]
    d40 = [(s[1] / s[2] - 1) for s in series if s[2]]
    return {
        "as_of": rows[-1][0],
        "month": cur[0],
        "close": close,
        "ma40": m40,
        "ma90": m90,
        "dev40": dev(m40),
        "dev90": dev(m90),
        "dev90_pct": _pct_rank(d90, close / m90 - 1) if m90 else None,
        "dev40_pct": _pct_rank(d40, close / m40 - 1) if m40 else None,
        "months": len(ms),
        "series": series,
    }


def cyb_ratio(cyb_rows, div_rows, cap=620):
    """创业板指 / 中证红利。"""
    div = {str(r[0]): float(r[1]) for r in div_rows if float(r[1]) > 0}
    pts = []
    for r in cyb_rows:
        d = str(r[0])
        if d in div:
            pts.append([d, round(float(r[1]) / div[d], 4)])
    if len(pts) < 250:
        raise RuntimeError(f"创红比可用天数不足（{len(pts)}）")
    vals = [p[1] for p in pts]
    cur = vals[-1]
    lo = min(range(len(vals)), key=lambda i: vals[i])
    hi = max(range(len(vals)), key=lambda i: vals[i])
    return {
        "as_of": pts[-1][0],
        "from": pts[0][0],
        "cyb": round(float(cyb_rows[-1][1]), 2),
        "div": round(float(div_rows[-1][1]), 2),
        "ratio": cur,
        "ref": 0.3,
        "pct": _pct_rank(vals, cur),
        "min": vals[lo],
        "min_d": pts[lo][0],
        "max": vals[hi],
        "max_d": pts[hi][0],
        "n": len(pts),
        "series": _downsample(pts, cap),
    }


def equity_long(h300_rows, hall_rows, start="2004-01-01", cap=300):
    """沪深300全收益 vs 全市场全收益，月度采样。"""
    a = dict(_monthly([r for r in h300_rows if str(r[0]) >= start]))
    b = dict(_monthly([r for r in hall_rows if str(r[0]) >= start]))
    keys = sorted(set(a) & set(b))
    if len(keys) < 60:
        raise RuntimeError(f"长期曲线可用月份不足（{len(keys)}）")
    series = [[k, round(a[k], 2), round(b[k], 2)] for k in keys]
    f, l = series[0], series[-1]
    return {
        "as_of": f"{l[0]}（月末）",
        "from": f[0],
        "h300": l[1],
        "hall": l[2],
        "cagr300": _cagr(f[1], l[1], f[0] + "-01", l[0] + "-01"),
        "cagr_all": _cagr(f[2], l[2], f[0] + "-01", l[0] + "-01"),
        "months": len(series),
        "series": _downsample(series, cap),
    }


# ------------------------------------------------------------------ 组装
def _try(fn, errors, label, *a, **kw):
    try:
        print(f"  · {label} …", flush=True)
        return fn(*a, **kw)
    except Exception as e:  # noqa: BLE001
        print(f"    ✗ {label}: {e}", flush=True)
        errors.append(f"{label}: {e}")
        return None


def run():
    """拉数 + 计算，返回可直接塞进 latest.json 的 labs 段。"""
    errors = []
    out = {"errors": errors, "notes": []}

    div = _try(lambda: S.csindex_perf("000922", start="2004-01-01"), errors, "中证红利日线")
    cyb = _try(lambda: S.sina_cn_daily("sz399006"), errors, "创业板指日线")
    h300 = _try(lambda: S.csindex_perf("H00300", start="2004-01-01"), errors, "沪深300全收益")
    hall = _try(lambda: S.csindex_perf("H00985", start="2004-01-01"), errors, "中证全指全收益")

    if div:
        v = _try(dividend_anchor, errors, "红利月线锚", div)
        if v:
            out["div_anchor"] = v

    if div and cyb:
        v = _try(cyb_ratio, errors, "创红比", cyb, div)
        if v:
            out["cyb_ratio"] = v

    # 主源缺失时退化到价格指数（会丢分红，年化会偏低，必须在页面标注）
    if not h300:
        h300 = _try(lambda: S.csindex_perf("000300", start="2004-01-01"), errors, "沪深300价格(备用)")
        if h300:
            out["notes"].append("沪深300全收益(H00300)取不到，图上用的是价格指数 000300，年化会偏低约 2 个百分点")
    if not hall:
        hall = _try(lambda: S.csindex_perf("000985", start="2004-01-01"), errors, "中证全指价格(备用)")
        if hall:
            out["notes"].append("中证全指全收益(H00985)取不到，图上用的是价格指数 000985，年化会偏低约 2 个百分点")

    if h300 and hall:
        v = _try(equity_long, errors, "长期双线", h300, hall)
        if v:
            out["equity_long"] = v

    out["notes"].append("· 万得全A(800707.WI) 属 Wind 商业数据、公开接口取不到，"
                        "此线改用中证全指全收益 H00985 替代（同口径、同基点）")
    return out
