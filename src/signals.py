# -*- coding: utf-8 -*-
"""阈值提示（signals）：把「现在在哪个位置」翻译成几句人话，不喊买卖。

设计原则（与打分逻辑严格分开）：
- **纯派生**：只读 latest（分数/倍率/长期锚）+ history 累积，不改任何分数，也不参与算分。
- **阈值固定、可复核**：每条规则的阈值都写成常量、在页面上公开，改阈值只改这里。
- **有就报、没有就报距离**：任何一条没触发时，页面会显示「离提示线还有多远」，
  而不是整块消失——空着会让人以为坏了。
- **措辞只说位置**：「低于」「逼近」「换档」，不说「买入」「卖出」「抄底」。

规则清单
--------
A 倍率换档        本期倍数 vs 上一期，变化 ≥0.15 就报
B 临近换档        分数距最近的档位边界 ≤2 分
C 极值档          分数 ≤28（0.8× 及以下）或 ≥82（2.0×）
D 连续低压        连续 3 期分数 ≤28
E 创红比          创业板指÷中证红利 ≤0.40（≤0.35 加重）；≥0.75 反向
F 红利月线锚      vs 90 月均线 ≤-10%（≥+40% 反向）；vs 40 月均线 ≤-8%
"""

# ---- 阈值（改这里即可，页面会显示「口径」）----
NEAR_BOUND_PTS = 2.0        # B：距档位边界多少分算「临近」
MULT_JUMP = 0.15            # A：倍数变化多少算「换档」
EXTREME_LOW = 28.0          # C：低于此分进 0.8× 及以下
EXTREME_HIGH = 82.0         # C：高于此分进 2.0×
LOW_STREAK_N = 3            # D：连续几期
LOW_STREAK_PTS = 28.0
CYB_WARN = 0.40             # E：创红比提示线
CYB_HOT = 0.35              # E：创红比强提示（更极端）
CYB_EXPENSIVE = 0.75        # E：反向（创业板相对红利偏贵）
DIV_MA90_LOW = -10.0        # F：低于 90 月均线百分比
DIV_MA90_HIGH = 40.0
DIV_MA40_LOW = -8.0

RULE_TEXT = (
    f"A 倍数变化 ≥{MULT_JUMP:.2f} 即报　·　B 距档位边界 ≤{NEAR_BOUND_PTS:.0f} 分　·　"
    f"C 分数 ≤{EXTREME_LOW:.0f} 或 ≥{EXTREME_HIGH:.0f}　·　"
    f"D 连续 {LOW_STREAK_N} 期 ≤{LOW_STREAK_PTS:.0f} 分　·　"
    f"E 创红比 ≤{CYB_WARN:g}（≤{CYB_HOT:g} 加重）/ ≥{CYB_EXPENSIVE:g}　·　"
    f"F 红利 vs 90 月线 ≤{DIV_MA90_LOW:.0f}% 或 ≥+{DIV_MA90_HIGH:.0f}% / vs 40 月线 ≤{DIV_MA40_LOW:.0f}%"
)


def _sig(level, tag, text, num=None):
    return {"lv": level, "tag": tag, "tx": text, "num": num}


def compute(latest, rows):
    """返回信号列表；rows 为 history.load() 结构（按日期升序）。"""
    out = []
    assets = [a for a in (latest.get("assets") or []) if not a.get("advisory_only")]
    seq = [r.get("a") or {} for r in (rows or [])]
    prev = seq[-2] if len(seq) >= 2 else {}

    # ---------- A 倍率换档 ----------
    for a in assets:
        p = prev.get(a["id"]) or {}
        pm = p.get("m")
        if pm is None:
            continue
        d = a["multiplier"] - pm
        if abs(d) >= MULT_JUMP:
            up = d > 0
            out.append(_sig(
                "hi" if up else "mid", "换档",
                f"<b>{a['name']}</b> 从 {pm:.1f}× 调到 <b>{a['multiplier']:.1f}×</b>"
                f"（分数 {p.get('s', 0):.1f} → {a['score']:.1f}，{'上' if up else '下'}跨一档）",
                f"{pm:.1f}× → {a['multiplier']:.1f}×"))

    # ---------- C 极值档 ----------
    for a in assets:
        sc = a["score"]
        if sc <= EXTREME_LOW:
            out.append(_sig("hi", "极值",
                            f"<b>{a['name']}</b> {sc:.1f} 分，已进入 0.8× 及以下档（≤{EXTREME_LOW:.0f} 分）",
                            f"{sc:.1f} 分"))
        elif sc >= EXTREME_HIGH:
            out.append(_sig("hi", "极值",
                            f"<b>{a['name']}</b> {sc:.1f} 分，已进入 2.0× 档（≥{EXTREME_HIGH:.0f} 分）",
                            f"{sc:.1f} 分"))

    # ---------- D 连续低压 ----------
    if len(seq) >= LOW_STREAK_N:
        tail = seq[-LOW_STREAK_N:]
        for a in assets:
            vals = [(t.get(a["id"]) or {}).get("s") for t in tail]
            if all(v is not None and v <= LOW_STREAK_PTS for v in vals):
                out.append(_sig(
                    "hi", "连续",
                    f"<b>{a['name']}</b> 已连续 {LOW_STREAK_N} 期 ≤{LOW_STREAK_PTS:.0f} 分"
                    f"（{', '.join(f'{v:.1f}' for v in vals)}），不是单日抖动",
                    f"{LOW_STREAK_N} 期"))

    # ---------- B 临近换档（只报最近的边界，且已有 A/C 的不重复）----------
    tbl = sorted(latest.get("multiplier_table") or [], key=lambda x: x["min"])
    bounds = [b for b in tbl if 0 < b["min"] < 100]
    flagged = {a["id"] for a in assets if abs(a["multiplier"] - (prev.get(a["id"]) or {}).get("m", a["multiplier"])) >= MULT_JUMP}
    for a in assets:
        if a["id"] in flagged or a["score"] <= EXTREME_LOW or a["score"] >= EXTREME_HIGH:
            continue
        sc = a["score"]
        if not bounds:
            break
        b = min(bounds, key=lambda x: abs(sc - x["min"]))
        d = sc - b["min"]
        if abs(d) <= NEAR_BOUND_PTS:
            if d < 0:
                where = f"距 {b['mult']:.1f}× 档（{b['min']} 分）还差"
            else:
                where = f"刚站上 {b['mult']:.1f}× 档下沿（{b['min']} 分）"
            out.append(_sig(
                "mid", "临界",
                f"<b>{a['name']}</b> {sc:.1f} 分，{where} {abs(d):.1f} 分，"
                f"当前 {a['multiplier']:.1f}×",
                f"{abs(d):.1f} 分"))

    # ---------- E 创红比 / F 红利月线锚 ----------
    labs = latest.get("labs") or {}
    cy = labs.get("cyb_ratio") or {}
    da = labs.get("div_anchor") or {}

    hit_cy = False
    if cy.get("ratio") is not None:
        r = cy["ratio"]
        if r <= CYB_HOT:
            hit_cy = True
            out.append(_sig("hi", "创红比",
                            f"创业板指÷中证红利 <b>{r:.4f}</b>，已跌破 {CYB_HOT:g}——"
                            f"成长相对红利在近 12 年里属最便宜的区间（历史分位 {cy.get('pct', 0):.1f}%）",
                            f"{r:.4f}"))
        elif r <= CYB_WARN:
            hit_cy = True
            out.append(_sig("mid", "创红比",
                            f"创业板指÷中证红利 <b>{r:.4f}</b>，低于 {CYB_WARN:g} 提示线"
                            f"（历史分位 {cy.get('pct', 0):.1f}%）",
                            f"{r:.4f}"))
        elif r >= CYB_EXPENSIVE:
            hit_cy = True
            out.append(_sig("mid", "创红比",
                            f"创业板指÷中证红利 <b>{r:.4f}</b>，高于 {CYB_EXPENSIVE:g}——"
                            f"成长相对红利偏贵（历史分位 {cy.get('pct', 0):.1f}%）",
                            f"{r:.4f}"))

    hit_div = False
    if da.get("dev90") is not None:
        d90 = da["dev90"]
        if d90 <= DIV_MA90_LOW:
            hit_div = True
            out.append(_sig("hi", "月线锚",
                            f"中证红利 <b>{da.get('close', 0):,.2f}</b>，低于 90 月均线 "
                            f"{abs(d90):.1f}%（深度低估参考区）",
                            f"{d90:+.1f}%"))
        elif d90 >= DIV_MA90_HIGH:
            hit_div = True
            out.append(_sig("mid", "月线锚",
                            f"中证红利 <b>{da.get('close', 0):,.2f}</b>，高于 90 月均线 "
                            f"{d90:.1f}%（远期偏贵）",
                            f"{d90:+.1f}%"))
    if da.get("dev40") is not None and da["dev40"] <= DIV_MA40_LOW:
        hit_div = True
        out.append(_sig("mid", "月线锚",
                        f"中证红利低于 40 月均线 {abs(da['dev40']):.1f}%"
                        f"（40 月线是中期估值中枢，跌破多在出清阶段）",
                        f"{da['dev40']:+.1f}%"))

    # 没触发就给「还有多远」——空着会让人以为坏了
    if not hit_cy and cy.get("ratio") is not None and cy.get("ratio") < CYB_EXPENSIVE:
        gap = (cy["ratio"] / CYB_WARN - 1) * 100
        out.append(_sig("calm", "创红比",
                        f"创业板指÷中证红利 <b>{cy['ratio']:.4f}</b>，距 {CYB_WARN:g} 提示线还有 "
                        f"<b>{gap:+.1f}%</b>（历史分位 {cy.get('pct', 0):.1f}%，区间 "
                        f"{cy.get('min', 0):.4f}–{cy.get('max', 0):.4f}）",
                        f"{cy['ratio']:.4f}"))
    if not hit_div and da.get("dev90") is not None:
        out.append(_sig("calm", "月线锚",
                        f"中证红利 {da.get('close', 0):,.2f}：vs 40 月线 {da.get('dev40', 0):+.2f}%、"
                        f"vs 90 月线 {da['dev90']:+.2f}%，两条提示线（{DIV_MA40_LOW:.0f}% / "
                        f"{DIV_MA90_LOW:.0f}%）都未触及",
                        f"{da['dev90']:+.1f}%"))

    order = {"hi": 0, "mid": 1, "calm": 2}
    out.sort(key=lambda s: order.get(s["lv"], 3))
    return out
