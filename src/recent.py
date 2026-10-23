# -*- coding: utf-8 -*-
"""近一月涨跌轨迹（纯展示，**不参与打分**）。

为什么单独一个模块：分数回答「贵不贵」，涨跌回答「最近在发生什么」。
这两件事混在一起最容易误读 —— 分数高但价格在跌，是「越跌越便宜」，不是「分数算错了」。
页面上的走势条必须和分数分开摆，且明确标注「这是价格涨跌，不是分数」。

口径：
  · 窗口按**自然日** 30 天回溯，取窗口内所有交易日 → 不同标的的交易日数会不同
    （A 股遇长假会少几天），所以对比图必须按日期铺横轴，不能按索引，否则线会错位。
  · 基准 = 窗口内**第一个交易日**的收盘，曲线的第一个点就是它（恒为 0%）。
    与「近一月涨幅 = 现在 / 一个月前 - 1」的通行定义一致。
  · 近 7 天同样按自然日回溯，页面上会同时给出覆盖的交易日数，
    免得「近 7 天」被理解成「7 个交易日」（那其实是近 10 个自然日）。
"""
import datetime as dt

MONTH_DAYS = 30      # 自然日
WEEK_DAYS = 7        # 自然日
MIN_PTS = 9          # 少于这个点数（约两周）就不画，画出来也读不出趋势


def _d(s):
    return dt.date.fromisoformat(str(s)[:10])


def month_track(dates, closes, month_days=MONTH_DAYS, week_days=WEEK_DAYS,
                min_pts=MIN_PTS):
    """返回近一月累计涨跌轨迹。数据不足返回 None。

    返回字段：
        pts        [[date, 累计涨跌%], ...]  首点恒为 0
        chg_month  近一月涨跌幅（%），等于 pts 末点
        chg_week   近 7 天涨跌幅（%）
        week_from  近 7 天窗口的起点日期（曲线高亮段从这里开始）
        week_n     近 7 天覆盖的交易日数
        hi/lo      窗口内累计涨跌的最高/最低（%），画 y 轴用
    """
    n = min(len(dates), len(closes))
    if n < min_pts:
        return None
    dates, closes = dates[:n], closes[:n]

    end = n - 1
    try:
        d_end = _d(dates[end])
        # 往前找到「距末日不超过 month_days 个自然日」的最早交易日
        start = end
        while start > 0 and (d_end - _d(dates[start - 1])).days <= month_days:
            start -= 1
    except (ValueError, TypeError):
        return None

    if end - start + 1 < min_pts:
        return None

    # 基准 = 窗口**首个交易日**的收盘，曲线的第一个点就是它（0%）。
    # 不用「首日前一日」：那样首点会是 +0.45% 这种非零值，图上起点不在 0 轴上，
    # 读起来像「这一个月一开始就已经涨了」，而「近一月涨跌」的通行定义是从
    # 一个月前的收盘算起 —— 起点必须落在 0。
    base = closes[start]
    if not base:
        return None

    pts = [[dates[i], round((closes[i] / base - 1) * 100, 2)] for i in range(start, end + 1)]

    # 近 7 天：从末日往前退，直到再退一天就超出 7 个自然日
    i7 = end
    try:
        while i7 > start and (d_end - _d(dates[i7 - 1])).days <= week_days:
            i7 -= 1
    except (ValueError, TypeError):
        i7 = end
    wbase = closes[i7]
    chg_week = round((closes[end] / wbase - 1) * 100, 2) if wbase else None

    vals = [p[1] for p in pts]
    return {
        "base_date": dates[start],
        "base": round(base, 4),
        "end_date": dates[end],
        "end": round(closes[end], 4),
        "n": len(pts),
        "pts": pts,
        "chg_month": vals[-1],
        "chg_week": chg_week,
        "week_from": dates[i7],
        "week_n": end - i7,
        "hi": max(vals),
        "lo": min(vals),
    }


def track_all(assets_daily, month_days=MONTH_DAYS, week_days=WEEK_DAYS):
    """批量生成，保持输入顺序。assets_daily = [(id, dates, closes), ...]

    单个标的失败不影响其他标的 —— 这条链路纯展示，挂了就不画，不能让整页跑批崩。
    """
    out = {}
    for aid, dates, closes in assets_daily:
        try:
            t = month_track(dates, closes, month_days, week_days)
        except Exception:  # noqa: BLE001
            t = None
        if t:
            out[aid] = t
    return out
