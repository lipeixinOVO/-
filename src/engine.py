# -*- coding: utf-8 -*-
"""评分引擎：指标 → 历史分位 → 维度分 → 加权综合分 → 倍数。

设计原则（与提示词一致）：
1. 分数 0-100，**越高越该买**（越便宜 / 越恐慌）。
2. 所有分数由规则算出，同一份数据必得同一分，可复现。
3. 200 日均线斜率不做打分项，改作"趋势破位"风险标记——避免均值回归与趋势跟随互相抵消。
"""
import datetime as dt

WINDOW = 2500  # 约 10 年交易日


# ---------------------------------------------------------------- 基础统计

def pct_rank(hist, cur):
    """cur 在 hist 中的分位（0-1）。空历史返回 None。"""
    n = len(hist)
    if n == 0:
        return None
    less = sum(1 for x in hist if x < cur)
    eq = sum(1 for x in hist if x == cur)
    return (less + 0.5 * eq) / n


def dev_series(closes, n=200):
    """收盘价相对 n 日均线的偏离（小数）。"""
    if len(closes) < n:
        return []
    res, s = [], sum(closes[:n])
    for i in range(n - 1, len(closes)):
        if i >= n:
            s += closes[i] - closes[i - n]
        res.append(closes[i] / (s / n) - 1)
    return res


def dd_series(closes, win=252):
    """距滚动窗口内最高点的回撤（<=0）。"""
    res = []
    for i in range(len(closes)):
        lo = max(0, i - win + 1)
        res.append(closes[i] / max(closes[lo:i + 1]) - 1)
    return res


def vol_series(closes, n=20):
    """n 日已实现波动率年化。"""
    if len(closes) < n + 1:
        return []
    rets = [closes[i] / closes[i - 1] - 1 for i in range(1, len(closes))]
    res = []
    for i in range(n - 1, len(rets)):
        w = rets[i - n + 1:i + 1]
        m = sum(w) / n
        var = sum((x - m) ** 2 for x in w) / (n - 1)
        res.append((var ** 0.5) * (252 ** 0.5))
    return res


def ratio_series(a, b):
    """两条 [(date, close)] 按日期对齐后求比值序列。"""
    db = dict(b)
    out = []
    for d, x in a:
        y = db.get(d)
        if y:
            out.append((d, x / y))
    return out


def log_resid_series(closes, win=2500, step=21):
    """对数价格的滚动线性回归残差（CAPE 近似思路）。

    对每个采样点，取它之前 win 个交易日做 log(price) ~ t 的最小二乘拟合，
    残差 = 实际对数价 − 拟合对数价。残差为正说明当前涨得超前长期轨道（偏贵）。

    step 控制采样密度：全量算 7000 点 × 2500 窗口在纯 Python 下太慢，
    月频（21 交易日）采样已足够支撑分位排序。
    """
    return [v for _, v in log_resid_dated(closes, None, win, step)]


def log_resid_dated(closes, dates, win=2500, step=21):
    """同 log_resid_series，但返回 [(date, resid)]，便于按 as_of 截断（回填时不重算）。"""
    import math
    n = len(closes)
    if n < win:
        return []
    idxs = list(range(win - 1, n, step))
    if idxs[-1] != n - 1:
        idxs.append(n - 1)
    res = []
    for i in idxs:
        seg = closes[i - win + 1:i + 1]
        if any(v is None or v <= 0 for v in seg):
            continue
        ys = [math.log(v) for v in seg]
        m = len(ys)
        sx = m * (m - 1) / 2.0
        sxx = (m - 1) * m * (2 * m - 1) / 6.0
        sy = sum(ys)
        sxy = sum(t * y for t, y in enumerate(ys))
        den = m * sxx - sx * sx
        if den == 0:
            continue
        b = (m * sxy - sx * sy) / den
        a = (sy - b * sx) / m
        res.append((dates[i] if dates else str(i), ys[-1] - (a + b * (m - 1))))
    return res


# ---------------------------------------------------------------- 指标构造

def mk_metric(name, series_slice, higher_is_cheaper, weight, source, fetched_at,
              unit="", note="", raw=None):
    """从「历史值序列 + 当前值」造一个指标条目。series_slice 最后一项为当前值。"""
    s = [x for x in series_slice if x is not None]
    if len(s) < 30:
        return None
    cur = s[-1] if raw is None else raw
    pct = pct_rank(s[:-1], cur)
    if pct is None:
        return None
    score = pct * 100 if higher_is_cheaper else (1 - pct) * 100
    return {
        "name": name,
        "raw": round(cur, 4),
        "unit": unit,
        "pct": round(pct * 100, 2),
        "score": round(score, 2),
        "weight": weight,
        "higher_is_cheaper": higher_is_cheaper,
        "source": source,
        "fetched_at": fetched_at,
        "note": note,
    }


def mk_metric_by_pct(name, raw, pct, higher_is_cheaper, weight, source, fetched_at,
                     unit="", note=""):
    """已知分位（如蛋卷 pb_percentile）时直接用。pct 为 0-1。"""
    if pct is None:
        return None
    score = pct * 100 if higher_is_cheaper else (1 - pct) * 100
    return {
        "name": name, "raw": raw, "unit": unit,
        "pct": round(pct * 100, 2), "score": round(score, 2),
        "weight": weight, "higher_is_cheaper": higher_is_cheaper,
        "source": source, "fetched_at": fetched_at, "note": note,
    }


def build_dimension(key, weight, metrics, anchor=None):
    ms = [m for m in metrics if m]
    wsum = sum(m["weight"] for m in ms)
    if ms and wsum > 0:
        score = sum(m["score"] * m["weight"] for m in ms) / wsum
    else:
        score = 50.0
    return {
        "key": key,
        "weight": weight,
        "score": round(score, 2),
        "anchor": anchor,
        "metrics": ms,
        "missing_ratio": round(1 - wsum / 100.0, 3) if ms else 1.0,
    }


# ---------------------------------------------------------------- 趋势标记

def trend_flag(closes):
    """200 日均线斜率 + 位置，判定是否"趋势破位"。不打分，只做风险标记。"""
    if len(closes) < 260:
        return {"flag": "unknown", "ma200_slope_60d": None, "dev": None}
    ma200 = sum(closes[-200:]) / 200
    ma200_prev = sum(closes[-260:-60]) / 200
    dev = closes[-1] / ma200 - 1
    slope = ma200 / ma200_prev - 1
    if slope < 0 and dev < -0.15:
        flag = "breakdown"      # 深度破位 + 均线转头向下
    elif slope < 0:
        flag = "weakening"
    else:
        flag = "healthy"
    return {"flag": flag, "ma200_slope_60d": round(slope, 4), "dev": round(dev, 4)}


# ---------------------------------------------------------------- 综合分与倍数

def composite(dimensions):
    ws = sum(d["weight"] for d in dimensions)
    if ws <= 0:
        return 50.0
    return round(sum(d["score"] * d["weight"] for d in dimensions) / ws, 2)


def multiplier_for(score, table):
    for row in table:
        if score >= row["min"]:
            return row["mult"], row["label"]
    return 1.0, "基准"


def band_position(score, table):
    """分数在当前倍数档**内部**的相对位置（0=贴本档下沿，100=贴本档上沿）。

    用途：中性带拓宽到 16 分后，多个标的会同处一档、倍数相同。
    档内位置让"同是 1.0 倍"的标的仍能排出先后（越靠上沿越接近上调档）。
    """
    for i, row in enumerate(table):
        if score >= row["min"]:
            lo = float(row["min"])
            hi = float(table[i - 1]["min"]) if i > 0 else 100.0
            if hi <= lo:
                return 50.0
            return round((score - lo) / (hi - lo) * 100, 1)
    return 50.0


def apply_gates(score, mult, dims, completeness, trend):
    """闸门只做两件事：数据不可信时强制回基准、破位时封顶。

    v3 移除：申购状态不再影响倍数（用户明确要求只输出评分与倍率）。
    申购/限额属于「执行可行性」，由 run_daily 单独写进 execution_hint 展示，
    不参与打分——否则同一份行情会因为代销渠道的临时限购而给出不同倍率，历史曲线也会断。
    """
    hits = []
    if completeness < 0.7:
        return 1.0, hits + [{"gate": "low_completeness",
                             "detail": f"数据完整度 {completeness:.0%} < 70%，强制基准 1.0×"}]
    if trend.get("flag") == "breakdown":
        if mult > 1.0:
            hits.append({"gate": "trend_breakdown",
                         "detail": "深度破位（跌破年线且年线转头向下），倍数封顶 1.0×，建议分批慢投"})
            mult = 1.0
        else:
            hits.append({"gate": "trend_breakdown",
                         "detail": "深度破位（跌破年线且年线转头向下），已非加码区间"})
    # macro 是全体共用的宏观因子，利率极高位属真实状态而非数据错误；
    # trend 的极端值（跌到十年最深 / 涨到历史最高）本身就是市场事实，天天报警会让闸门失去意义。
    # 只有估值与情绪维度的极端值才可能指向数据异常，保留复核提示。
    extremes = [d["key"] for d in dims
                if d["key"] not in ("macro", "trend") and (d["score"] < 10 or d["score"] > 90)]
    if extremes:
        hits.append({"gate": "extreme_dimension",
                     "detail": "维度极端值：" + "、".join(extremes) + "，请复核数据源或确认为真实极端行情"})
    return mult, hits


def completeness_of(dims):
    """参与计算的权重占比。"""
    total_w = sum(d["weight"] for d in dims) * 100 / 100.0
    ok = 0.0
    for d in dims:
        got = sum(m["weight"] for m in d["metrics"])
        ok += d["weight"] * (got / 100.0)
    return round(ok / total_w, 4) if total_w else 0.0
