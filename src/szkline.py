# -*- coding: utf-8 -*-
"""指数技术位：日 K + 斐波那契回调线 + 压力/支撑距离。

覆盖深证成指、创业板指、科创50、创业板50 四个指数，纯展示模块，不参与打分。
斐波那契回调线基于「最近一轮明显趋势」的 swing 低点/高点：

    swing high = 最近 WINDOW 个交易日内的最高价（最高价的那一天）
    swing low  = swing high 出现之前、同一窗口内的最低价

这套规则可复现、随数据自动更新（未来创新高/新低会自动重画），不人工指定日期。
与用户提供的参考图核对过：深成指 swing low=2024-02-05 的 7683.63、
swing high=2026-06-22 的 16374.02，反推出的 5 条线 9734.56 / 11003.36 / 12028.83 /
13054.29 / 14714.16 与图上一一吻合（图上的 50% 标注 12028.03 是原作者的舍入误差，
精确值是 12028.83）。
"""
from . import sources as S

WINDOW = 1200                       # 约 5 年交易日，足够覆盖「最近一轮明显趋势」
FIB_LEVELS = [0.236, 0.382, 0.5, 0.618, 0.809]   # 只标 5 条中间线；0%/100% 是边界

# 覆盖四个指数（市场前缀 sh/sz 与腾讯行情一致）。
# 科创50 基日 2019-12-31、2020 年才发布，历史 K 线偏短（约 1600 根），其余三个都 2000 根。
INDICES = [
    ("sz399001", "深证成指"),
    ("sz399006", "创业板指"),
    ("sh000688", "科创50"),
    ("sz399673", "创业板50"),
]


def _fib_levels(low, high):
    rng = high - low
    out = [{"pct": 0.0, "price": round(low, 2)}]
    out += [{"pct": p, "price": round(low + rng * p, 2)} for p in FIB_LEVELS]
    out.append({"pct": 1.0, "price": round(high, 2)})
    return out


def _nearest(fib, cur):
    """返回 (上方最近的压力线, 下方最近的支撑线)。各为 None 表示当前价越界。"""
    res = sup = None
    for f in fib:
        if f["price"] > cur and (res is None or f["price"] < res["price"]):
            res = f
        if f["price"] < cur and (sup is None or f["price"] > sup["price"]):
            sup = f
    return res, sup


def _one(symbol, name):
    """单个指数的技术位。"""
    klines = S.cn_ohlc(symbol)[-WINDOW:]
    if len(klines) < 120:
        raise RuntimeError(f"{symbol} K 线不足 120 根，无法画斐波那契")

    hi = max(klines, key=lambda r: r[3])            # 窗口内最高 high
    hi_date = hi[0]
    before = [r for r in klines if r[0] <= hi_date]
    lo = min(before, key=lambda r: r[4])            # 高点之前的最低 low
    low, high = lo[4], hi[3]

    fib = _fib_levels(low, high)
    last = klines[-1]
    cur = last[2]                                    # 最新收盘价（前端每分钟用实时价覆盖）
    res, sup = _nearest(fib, cur)

    return {
        "symbol": symbol,
        "name": name,
        # K 线只画「swing low 之后」那段：起点就是低点，图上就是「低点→高点→回落到当前」
        # 的完整故事，斐波那契 0%~100% 全部落在图内。
        "klines": [{"d": r[0], "o": r[1], "c": r[2], "h": r[3], "l": r[4]}
                   for r in klines if r[0] >= lo[0]],
        "swing_low": {"date": lo[0], "price": round(low, 2)},
        "swing_high": {"date": hi_date, "price": round(high, 2)},
        "fib": fib,
        "cur": round(cur, 2),
        "cur_date": last[0],
        "resistance": res,
        "support": sup,
    }


def run():
    """返回各指数的技术位列表。单个指数失败就跳过，不拖累整块。"""
    out = []
    for symbol, name in INDICES:
        try:
            out.append(_one(symbol, name))
        except Exception:  # noqa: BLE001
            continue
    return out
