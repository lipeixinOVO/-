# -*- coding: utf-8 -*-
"""把跑批结果渲染成人看的 Markdown。"""

DIM_CN = {"valuation": "估值", "trend": "趋势", "sentiment": "情绪", "macro": "宏观"}


def _fmt(v, nd=2):
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:,.{nd}f}"
    return str(v)


def _price(v):
    """按量级取合理小数位，避免 26,702.8600 这种尾巴。"""
    if v is None:
        return "—"
    if abs(v) >= 100:
        return f"{v:,.2f}"
    return f"{v:.4f}"


def _pct(v, nd=1):
    if v is None or not isinstance(v, (int, float)):
        return "—"
    return f"{v * 100:.{nd}f}%"


def _metric_val(m):
    """按指标单位格式化原始值：% 类的小数要 ×100，别把 -0.0943 直接摆出来。"""
    r = m.get("raw")
    if r is None:
        return "—"
    u = m.get("unit") or ""
    if u == "%":
        return f"{r * 100:.2f}%"
    if u == "倍":
        return f"{r:.2f}×"
    return _price(r)


def _te(v):
    """跟踪误差：没有就是 —，不要出现「—%」。"""
    return f"{v:.2f}%" if isinstance(v, (int, float)) else "—"


def to_markdown(out):
    L = []
    A = L.append
    A(f"# 定投台 · {out['trade_date']}")
    A("")
    A(f"生成时间：{out['generated_at']}　　基准金额：{out['base_amount']} 元/月　　评分口径：指数本身（非基金净值）")
    A("")
    m = out.get("macro") or {}
    A("**宏观快照**：" + "　".join([
        f"美债10Y实际利率 {_fmt(m.get('ust_10y_real'))}%",
        f"名义 {_fmt(m.get('ust_10y_nominal'))}%",
        f"美元指数 {_fmt(m.get('dxy'))}",
        f"USDCNH {_fmt(m.get('usdcnh'), 4)}",
        f"伦敦金 {_fmt(m.get('gold_spot'))}",
    ]))
    A("")
    A("## 一、本期结论")
    A("")
    A("| 标的 | 综合分 | 档内位置 | 倍数 | 建议金额 | 落地基金 |")
    A("|---|---|---|---|---|---|")
    for a in out["assets"]:
        ex = a.get("execution") or {}
        tip = "参考，不执行" if a["advisory_only"] else (
            f"{ex.get('fund_code') or '—'} {ex.get('fund_name') or ''}".strip())
        amt = "—" if a["advisory_only"] else f"{a['suggest_amount']:,.0f} 元"
        A(f"| {a['name']} | {a['score']:.1f} | {a.get('band_pos', 50):.0f}% | **{a['multiplier']:.1f}×** | "
          f"{amt} | {tip} |")
    A("")
    A("> 档内位置：同一倍数档内部，越靠上沿越接近上调一档。中性带宽 40–56 分，"
      "所以多个标的可能同为 1.0×，此时看档内位置排先后。")
    A("")
    for a in out["assets"]:
        if a.get("gates"):
            for g in a["gates"]:
                A(f"> ⚠ **{a['name']}**：{g['detail']}")
    A("")
    A("## 二、逐标的拆解")
    A("")
    for a in out["assets"]:
        A(f"### {a['name']}")
        A("")
        tf = a.get("trend_flag") or {}
        A(f"- 当前指数点位：**{_price(a['price'])}**（{a.get('price_date') or '—'}）")
        A(f"- 综合分：**{a['score']:.1f}** → **{a['multiplier']:.1f}×**（{a['label']}，档内 {a.get('band_pos', 50):.0f}%）")
        A(f"- 趋势判定：{tf.get('flag')}（距年线 {_pct(tf.get('dev'))}，年线60日斜率 {_pct(tf.get('ma200_slope_60d'))}）")
        if a.get("note"):
            A(f"- 备注：{a['note']}")
        A("")
        A("| 维度 | 得分 | 权重 | 指标拆解 |")
        A("|---|---|---|---|")
        for d in a["dimensions"]:
            parts = []
            for m2 in d["metrics"]:
                parts.append(f"{m2['name']} = {_metric_val(m2)} → 分位 {_fmt(m2['pct'])}% → {m2['score']:.0f} 分")
            A(f"| {DIM_CN.get(d['key'], d['key'])} | {d['score']:.1f} | {d['weight']}% | "
              + ("；<br>".join(parts) if parts else "**无可用指标**") + " |")
        if any(d.get("anchor") for d in a["dimensions"]):
            anchors = [d["anchor"] for d in a["dimensions"] if d.get("anchor")]
            A("")
            A("**估值锚**：" + "；".join(anchors))
        A("")

    # 执行方案：只讲怎么买，不影响上面的倍数
    A("## 三、执行方案")
    A("")
    A("| 标的 | 首选基金 | 跟踪误差 | 单位净值 | 净值日 | 申购状态 |")
    A("|---|---|---|---|---|---|")
    for a in out["assets"]:
        ex = a.get("execution") or {}
        if a["advisory_only"] or not ex.get("fund_code"):
            continue
        A(f"| {a['name']} | `{ex['fund_code']}` {ex.get('fund_name') or '—'} | "
          f"{_te(ex.get('tracking_error'))} | {_price(ex.get('nav'))} | "
          f"{ex.get('nav_date') or '—'} | {ex.get('subscribe_status') or '—'} |")
    A("")
    # 首选暂时买不进时，按跟踪误差排序给备选
    fb_lines = []
    for a in out["assets"]:
        ex = a.get("execution") or {}
        fbs = ex.get("fallbacks") or []
        if not fbs:
            continue
        ok = [x for x in fbs if "暂停" not in str(x.get("subscribe_status") or "")]
        if "暂停" in str(ex.get("subscribe_status") or "") and ok:
            best = ok[0]
            fb_lines.append(f"- **{a['name']}**：首选 `{ex['fund_code']}` 暂停申购 → "
                            f"改 `{best['fund_code']}` {best.get('fund_name')}（跟踪误差 "
                            f"{_te(best.get('tracking_error'))}，{best.get('subscribe_status')}）")
        elif "暂停" in str(ex.get("subscribe_status") or "") and not ok:
            fb_lines.append(f"- **{a['name']}**：首选与全部备选均暂停或限额，本期可能无法落地")
    if fb_lines:
        A("**备选链（首选买不进时用）**")
        A("")
        for ln in fb_lines:
            A(ln)
        A("")
    A("> 申购状态**不参与打分、不改倍数**——同一份行情不应因为渠道临时限购而给出不同倍率。"
      "限购只影响「这笔钱能不能落到这只基金上」。")
    A("")

    A("## 四、口径与数据来源")
    A("")
    A("- 分数 0–100，**越高越该买**（越便宜 / 越恐慌）；50 分 = 1.0 倍基准。")
    A("- 所有指标先转为「历史分位」，估值类取 10 年、价格类取近 10 年交易日；分位越高说明当前值在历史上越极端。")
    A("- **全部标的直接用指数行情打分，不用基金净值。** 基金净值有三重失真：分红/折算造成单日跳降、"
      "QDII 净值 T+1/T+2 披露导致日期错位、管理费持续侵蚀净值。")
    A("- 数据来源：")
    A("  - 纳斯达克综合/纳指100/标普500 日线：新浪财经 US_MinKService（.IXIC / .NDX / .INX）")
    A("  - 黄金/中证红利/沪深300 日线：东方财富 push2his（101.GC00Y / 1.000922 / 1.000300）")
    A("  - **MSCI 全球医疗保健指数：MSCI 官方指数接口（index_codes=106801，NETR 净总回报口径）**")
    A("  - MSCI World（比价基准）：同上，index_codes=990100")
    A("  - 美元指数：东财 100.UDI；离岸人民币：东财 133.USDCNH")
    A("  - 美债实际/名义收益率：美国财政部 official CSV（daily_treasury_real_yield_curve / yield_curve）")
    A("  - 指数估值：蛋卷基金 index_eva（PE 周频序列 2016-10 至今日 + PB 分位）")
    A("  - 落地基金的净值与申购状态：天天基金 pingzhongdata + f10/lsjz")
    A("- 已知口径缺口（不掩盖）：")
    A("  - 纳斯达克**综合**指数自身 PE 不可得，用纳指100(NDX) 估值代理。")
    A("  - **MSCI 全球医疗保健指数的 PE 历史序列不可得**（MSCI 官方基本面接口需订阅，实测 404；蛋卷未覆盖）。"
      "估值维度改用「医疗/MSCI World 比价分位」+「距 10 年对数趋势偏离」两个真实可得的代理，已标注在估值锚。"
      "官方快照 2026-08-31：PE 22.44、PB 4.85、股息率 1.77%，可人工对照。")
    A("  - 中证红利真实股息率历史序列不可得，用 PE 分位反向代理。")
    A("  - A 股 10Y 国债收益率未接入（中债接口需鉴权），红利宏观用「相对沪深300 强弱」+「沪深300 PE 分位」替代。")
    A("  - 黄金价格分位为名义口径，未做通胀调整。")
    A("")
    A("## 五、免责声明")
    A("")
    A("> 本工具仅为个人定投纪律辅助，所有分数与倍数由公开数据按固定规则机械计算，不构成任何投资建议。"
      "数据可能存在延迟或错误，请自行核验后决策。历史分位不代表未来。")
    return "\n".join(L)
