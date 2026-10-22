# -*- coding: utf-8 -*-
"""数据合理性校验：序列极值、日期、异常跳变、回撤来源。"""
import sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src import sources as S


def report(label, series):
    dates = [x[0] for x in series]
    vals = [x[1] for x in series]
    n = len(vals)
    hi = max(vals); hi_d = dates[vals.index(hi)]
    lo = min(vals); lo_d = dates[vals.index(lo)]
    cur = vals[-1]
    w52 = vals[-252:]
    hi52 = max(w52); hi52_d = dates[-252:][w52.index(hi52)]
    # 单日异常跳变
    jumps = []
    for i in range(1, n):
        if vals[i - 1] > 0:
            ch = vals[i] / vals[i - 1] - 1
            if abs(ch) > 0.12:
                jumps.append((dates[i], round(ch * 100, 2)))
    print(f"\n{label}")
    print(f"  样本 {n} 条 | {dates[0]} → {dates[-1]} | 当前 {cur}")
    print(f"  历史最高 {hi} ({hi_d}) | 历史最低 {lo} ({lo_d})")
    print(f"  52周最高 {hi52} ({hi52_d}) | 当前回撤 {round(cur/hi52-1,4)}")
    print(f"  距历史高点 {round(cur/hi-1,4)}")
    if jumps:
        print(f"  ⚠ 单日跳变 >12% 共 {len(jumps)} 处: {jumps[:8]}")


print("=" * 80)
report("IXIC 纳斯达克综合（新浪日线）", S.sina_us_daily(".IXIC"))
report("NDX 纳指100（新浪日线）", S.sina_us_daily(".NDX"))
report("COMEX黄金 GC00Y（东财）", [(r[0], r[1]) for r in S.em_kline("101.GC00Y")])
report("中证红利 000922（东财）", [(r[0], r[1]) for r in S.em_kline("1.000922")])
nav1, _ = S.fund_nav_history("160213")
report("160213 国泰纳指100 单位净值", nav1)
nav2, _ = S.fund_nav_history("000369")
report("000369 广发全球医疗 单位净值", nav2)
nav3, _ = S.fund_nav_history("009051")
report("009051 易方达中证红利联接A 单位净值", nav3)
