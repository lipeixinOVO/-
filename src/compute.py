# -*- coding: utf-8 -*-
"""各标的的维度组装。

v3 关键变更：**一律用指数本身的行情序列打分，不用基金净值。**
原因：基金净值有三重失真——
  1. 分红/份额折算会造成单日跳降（160213 曾出现 -38%），趋势与回撤全废；
  2. QDII 净值 T+1/T+2 披露，日期与指数错位一天，直接对比会算出 20%+ 的假跟踪误差；
  3. 管理费、申赎冲击持续侵蚀净值，长期跑输指数，会把"便宜"误判成"更便宜"。
落地基金只在 execution 字段给出，不参与打分。
"""
import datetime as dt

from . import engine as E
from . import sources as S


def _now():
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M")


def _src(name):
    return f"{name}（{_now()} 取）"


# ---------------------------------------------------------------- 序列获取

_FETCHERS = {
    "sina_us": lambda d: (S.sina_us_daily(d["symbol"]),
                          f"新浪财经 US_MinKService {d['symbol']}"),
    "em_kline": lambda d: (S.em_kline(d["secid"]),
                           f"东方财富 push2his {d['secid']}"),
    "msci": lambda d: (S.msci_index(d["code"], d.get("variant", "NETR")),
                       f"MSCI 官方指数接口 index_codes={d['code']}（{d.get('variant', 'NETR')}）"),
    "csindex": lambda d: (S.csindex_perf(d["code"], d.get("start", "2004-01-01")),
                          f"中证指数官网 indexCode={d['code']}"),
    "sina_gold": lambda d: (S.sina_gold_daily(d.get("symbol", "GC")),
                            f"新浪外盘期货 {d.get('symbol', 'GC')} 日线"),
    "tx_kline": lambda d: (S.tx_kline(d["secid"]),
                           f"腾讯财经 {d['secid']}"),
}


def try_chain(spec, ctx=None, label=""):
    """按 config 里写的顺序逐个数据源尝试，返回 (rows, 来源说明)。

    东财部分 secid 会间歇性断连（实测 1.000922 / 101.GC00Y 都中过），
    所以任何一个标的都不允许只挂一个源；全部失败才抛错，并把每个源的失败原因一起抛出来。
    """
    specs = [spec] + list(spec.get("fallback") or [])
    errs = []
    for s in specs:
        t = s.get("type")
        if t not in _FETCHERS:
            raise ValueError(f"未知 data.type: {t}")
        try:
            rows, src = _FETCHERS[t](s)
            if rows:
                if errs and ctx is not None:
                    ctx.setdefault("notes", []).append(
                        f"{label}主力源失败（{errs[0][:60]}），已回退到 {src}")
                return rows, src
            errs.append(f"{t}: 空数据")
        except Exception as e:  # noqa: BLE001
            errs.append(f"{t}: {e}")
    raise RuntimeError(f"{label}全部数据源失败 → " + "；".join(errs))


def load_series(cfg, as_of=None, ctx=None):
    """按 config.data 取行情序列。as_of 给定时截断到该日（回填历史用，避免前视偏差）。"""
    d = cfg["data"]
    rows, src = try_chain(d, ctx, label=cfg.get("name", ""))

    if as_of:
        rows = [r for r in rows if r[0] <= as_of]
    if not rows:
        raise RuntimeError(f"{d} 在 {as_of} 之前无数据")

    amounts = [x[2] if len(x) > 2 else 0.0 for x in rows]
    return {"closes": [x[1] for x in rows],
            "dates": [x[0] for x in rows],
            "amounts": amounts if any(amounts) else None,
            "date": rows[-1][0],
            "src": _src(src)}


# ---------------------------------------------------------------- 估值锚（蛋卷）

def load_valuation_anchors(ctx):
    """蛋卷只覆盖 A 股与主流指数；MSCI 全球医疗不在其中（已实测 detail 返回空）。

    pe_hist 保留日期，回填历史时才不会用到"未来"的 PE 数据。
    """
    ctx["dj"] = {}
    for code in ("NDX", "SH000922", "SH000300"):
        try:
            ctx["dj"][code] = {
                "detail": S.dj_detail(code),
                "pe_hist": S.dj_pe_history(code),
            }
        except Exception as e:  # noqa: BLE001
            ctx.setdefault("errors", []).append(f"蛋卷 {code}: {e}")
            ctx["dj"][code] = {"detail": {}, "pe_hist": []}


def _pe_upto(ctx, code, as_of):
    """取蛋卷 PE 序列（(date, pe)），按 as_of 截断，返回纯值列表。"""
    rows = (ctx["dj"].get(code) or {}).get("pe_hist") or []
    if as_of:
        rows = [r for r in rows if r[0] <= as_of]
    return [r[1] for r in rows]


def _val_from_dj(ctx, dj_code, w_pe, w_pb, anchor_label, extra_note="", as_of=None):
    """蛋卷 PE 历史自算分位 + 蛋卷 PB 分位。

    PB 分位来自蛋卷 detail（只有当前值，无历史序列），回填历史时无法还原 → 跳过，
    由 PE 单项承担该维度权重（口径已在报告标注）。
    """
    pe_hist = _pe_upto(ctx, dj_code, as_of)
    det = (ctx["dj"].get(dj_code) or {}).get("detail") or {}
    ms = []
    if pe_hist:
        ms.append(E.mk_metric(
            f"{anchor_label} PE-TTM 10年分位", pe_hist[-E.WINDOW:], False, w_pe,
            _src("蛋卷基金 index_eva pe_history"), "",
            note=extra_note or "PE 越低分位越低，价格越便宜、分数越高"))
    if det.get("pb_percentile") is not None:
        # 蛋卷只给 PB 当前分位、没有历史序列 → 回填历史时取当前值固定。
        # 代价是 PB 这部分在曲线上是常量；收益是权重口径与当天完全一致，
        # 不会出现"最后一天凭空跳 4~5 分"的假突变（比失真更误导）。
        ms.append(E.mk_metric_by_pct(
            f"{anchor_label} PB 分位", det.get("pb"), det.get("pb_percentile"), False, w_pb,
            _src("蛋卷基金 index_eva detail"), "",
            note=f"蛋卷口径；交叉校验 PE 分位={det.get('pe_percentile')}"
                 + ("；历史 PB 序列不可得，回填期取当前分位固定" if as_of else "")))
    return ms


# ---------------------------------------------------------------- 通用维度

def _trend_dims(closes, w_dev, w_dd, source):
    ms = []
    dv = E.dev_series(closes, 200)
    if dv:
        ms.append(E.mk_metric("距 200 日均线偏离", dv[-E.WINDOW:], False, w_dev,
                              source, "", unit="%",
                              note="偏离越大越贵，分位越高分数越低"))
    dd = E.dd_series(closes, 252)
    if dd:
        # 回撤是负值且越深越小 → higher_is_cheaper=False（=100−分位）才能让"跌得越深分数越高"
        ms.append(E.mk_metric("距 52 周高点回撤", dd[-E.WINDOW:], False, w_dd,
                              source, "", unit="%",
                              note="回撤越深（历史分位越低）分数越高"))
    return ms


def _sentiment_dims(closes, amounts, source, w_vol=60, w_other=40):
    ms = []
    vs = E.vol_series(closes, 20)
    if vs:
        ms.append(E.mk_metric("20 日年化波动率", vs[-E.WINDOW:], True, w_vol,
                              source, "", unit="%", note="波动放大=恐慌，分数升高"))
    use_amount = bool(amounts) and sum(amounts[-60:]) > 0 and len(amounts) > 70
    if use_amount:
        series = []
        for i in range(60, len(amounts)):
            base = sum(amounts[max(0, i - 60):i + 1]) / len(amounts[max(0, i - 60):i + 1])
            series.append(amounts[i] / base if base > 0 else 1.0)
        ms.append(E.mk_metric("成交额 / 60 日均额", series[-E.WINDOW:], True, w_other,
                              source, "", unit="倍", note="放量（恐慌或狂热）给分，需结合趋势看"))
    elif len(closes) > 70:
        mom = [closes[i] / closes[i - 60] - 1 for i in range(60, len(closes)) if closes[i - 60] > 0]
        ms.append(E.mk_metric("60 日动量", mom[-E.WINDOW:], False, w_other,
                              source, "", unit="%",
                              note="无成交额数据，改用动量：涨得越多越热，分数越低"))
    return ms


def _macro_us(ctx, w_real, w_dxy, w_nom, w_cny=0, as_of=None):
    """统一约定：unit='%' 的指标，raw 一律存小数（0.0276 = 2.76%）。"""
    def _cut(rows):
        return [r for r in (rows or []) if r[0] <= as_of] if as_of else (rows or [])

    ms = []
    real = _cut(ctx.get("ust_real"))
    if real:
        ms.append(E.mk_metric("美债 10Y 实际利率(TIPS)", [x[1] / 100 for x in real][-E.WINDOW:], False,
                              w_real, _src("美国财政部 real_yield_curve"), "", unit="%",
                              note="实际利率越高，折现压力越大，分数越低"))
    nom = _cut(ctx.get("ust_nominal"))
    if nom and w_nom:
        ms.append(E.mk_metric("美债 10Y 名义利率", [x[1] / 100 for x in nom][-E.WINDOW:], False,
                              w_nom, _src("美国财政部 yield_curve"), "", unit="%"))
    dxy = _cut(ctx.get("dxy"))
    if dxy:
        ms.append(E.mk_metric("美元指数(DXY)", [x[1] for x in dxy][-E.WINDOW:], False, w_dxy,
                              _src("新浪财经 DINIW 日采样"), "", unit="",
                              note="美元走强推高非美元投资者成本"))
    cny = _cut(ctx.get("usdcny"))
    if cny and w_cny:
        ms.append(E.mk_metric("USDCNY 汇率", [x[1] for x in cny][-E.WINDOW:], False, w_cny,
                              _src("东财 133.USDCNH"), "", unit="",
                              note="人民币走弱时买美元资产成本更高"))
    return ms


def _out(ser, dims):
    return {"closes": ser["closes"], "dims": dims,
            "price": ser["closes"][-1], "price_date": ser["date"]}


# ---------------------------------------------------------------- 各标的

def compute_ixic(cfg, ctx, as_of=None):
    ser = load_series(cfg, as_of, ctx)
    dims = [
        E.build_dimension("valuation", cfg["weights"]["valuation"],
                          _val_from_dj(ctx, "NDX", 50, 50, "纳指100", as_of=as_of),
                          anchor="纳斯达克综合指数自身 PE 不可得，用纳指100(NDX) 估值代理"),
        E.build_dimension("trend", cfg["weights"]["trend"],
                          _trend_dims(ser["closes"], 50, 50, ser["src"])),
        E.build_dimension("sentiment", cfg["weights"]["sentiment"],
                          _sentiment_dims(ser["closes"], None, ser["src"])),
        E.build_dimension("macro", cfg["weights"]["macro"],
                          _macro_us(ctx, 40, 25, 15, 20, as_of)),
    ]
    return _out(ser, dims)


def compute_ndx(cfg, ctx, as_of=None):
    ser = load_series(cfg, as_of, ctx)
    dims = [
        E.build_dimension("valuation", cfg["weights"]["valuation"],
                          _val_from_dj(ctx, "NDX", 60, 40, "纳指100", as_of=as_of),
                          anchor="纳指100(NDX) 指数自身 PE/PB，蛋卷口径"),
        E.build_dimension("trend", cfg["weights"]["trend"],
                          _trend_dims(ser["closes"], 50, 50, ser["src"])),
        E.build_dimension("sentiment", cfg["weights"]["sentiment"],
                          _sentiment_dims(ser["closes"], None, ser["src"])),
        E.build_dimension("macro", cfg["weights"]["macro"],
                          _macro_us(ctx, 40, 25, 15, 20, as_of)),
    ]
    return _out(ser, dims)


def compute_gold(cfg, ctx, as_of=None):
    ser = load_series(cfg, as_of, ctx)
    closes = ser["closes"]
    ms = [E.mk_metric("金价 10 年名义分位", closes[-E.WINDOW:], False, 60, ser["src"], "", unit="",
                      note="未做通胀调整，属近似口径")]
    spx = [r for r in (ctx.get("spx") or []) if not as_of or r[0] <= as_of]
    if spx and closes:
        try:
            ratio = E.ratio_series(list(zip(ser["dates"], closes)), spx)
            if len(ratio) > 250:
                ms.append(E.mk_metric("金价 / 标普500 比价分位", [x[1] for x in ratio][-E.WINDOW:],
                                      False, 40, _src("东财 GC00Y ÷ 新浪 .INX"), "", unit="",
                                      note="金/股比价越高说明黄金相对股票越贵"))
        except Exception as e:  # noqa: BLE001
            ctx.setdefault("errors", []).append(f"金/标普比价: {e}")
    dims = [
        E.build_dimension("valuation", cfg["weights"]["valuation"], ms,
                          anchor="黄金无 PE，用 10 年价格分位 + 金/股比价"),
        E.build_dimension("trend", cfg["weights"]["trend"],
                          _trend_dims(closes, 50, 50, ser["src"])),
        E.build_dimension("sentiment", cfg["weights"]["sentiment"],
                          _sentiment_dims(closes, ser["amounts"], ser["src"], 60, 40)),
        E.build_dimension("macro", cfg["weights"]["macro"],
                          _macro_us(ctx, 50, 30, 20, as_of=as_of)),
    ]
    r = _out(ser, dims)
    r["spot"] = ctx.get("gold_spot")
    return r


def compute_health(cfg, ctx, as_of=None):
    """MSCI 全球医疗保健指数（106801）。

    估值缺口：MSCI 官方仅提供当前快照 PE/PB（www.msci.com/indexes/index/106801），
    历史 PE 序列需订阅（接口 404 实测），蛋卷亦未覆盖该指数。
    因此估值维度用两个**真实可得**的代理：
      ① 医疗 / MSCI World 比价 10 年分位 —— 衡量"医疗相对全球大盘贵不贵"（相对估值）
      ② 距 10 年对数回归趋势偏离 —— 近似 CAPE 思路，衡量"涨得超前长期轨道多少"（绝对估值代理）
    """
    ser = load_series(cfg, as_of, ctx)
    closes = ser["closes"]
    ms = []

    bm_cfg = cfg.get("benchmark")
    if bm_cfg:
        try:
            bm = load_series({"data": bm_cfg}, as_of, ctx)
            ratio = E.ratio_series(list(zip(ser["dates"], closes)),
                                   list(zip(bm["dates"], bm["closes"])))
            if len(ratio) > 250:
                ms.append(E.mk_metric("医疗 / MSCI World 比价 10年分位", [x[1] for x in ratio][-E.WINDOW:],
                                      False, 60, _src("MSCI 106801 ÷ MSCI 990100"), "", unit="",
                                      note="比价越高=医疗相对全球大盘越贵，分数越低"))
        except Exception as e:  # noqa: BLE001
            ctx.setdefault("errors", []).append(f"医疗/全球比价: {e}")

    # 残差每个点只依赖它之前的 win 个交易日 → **必须用全量序列算一次**再缓存。
    # 早期版本用截断后的 closes 算，导致回填期全部复用最早那一天的残差，
    # 10-21 的回填分（50.9）与实际（43.2）差 7.7 分。
    if "_health_resid" not in ctx:
        full = load_series(cfg, None, ctx)
        ctx["_health_resid"] = E.log_resid_dated(full["closes"], full["dates"], 2500, 21)
    resid = [v for d, v in ctx["_health_resid"] if not as_of or d <= as_of]
    if resid:
        ms.append(E.mk_metric("距 10 年对数趋势偏离", resid[-600:], False, 40,
                              ser["src"], "", unit="%",
                              note="偏离长期对数趋势越多=越贵；CAPE 近似思路，MSCI 历史 PE 序列不可得时用它代理"))

    dims = [
        E.build_dimension("valuation", cfg["weights"]["valuation"], ms,
                          anchor="MSCI 官方 PE 历史不可得（需订阅）；用相对 MSCI World 比价 + 对数趋势偏离代理。"
                                 "官方快照 2026-08-31：PE 22.44、PB 4.85、股息率 1.77%"),
        E.build_dimension("trend", cfg["weights"]["trend"],
                          _trend_dims(closes, 50, 50, ser["src"])),
        E.build_dimension("sentiment", cfg["weights"]["sentiment"],
                          _sentiment_dims(closes, None, ser["src"])),
        E.build_dimension("macro", cfg["weights"]["macro"],
                          _macro_us(ctx, 40, 25, 15, 20, as_of)),
    ]
    return _out(ser, dims)


def compute_dividend(cfg, ctx, as_of=None):
    ser = load_series(cfg, as_of, ctx)
    closes = ser["closes"]
    det = (ctx["dj"].get("SH000922") or {}).get("detail") or {}
    pe_hist = _pe_upto(ctx, "SH000922", as_of)

    ms = []
    if pe_hist:
        # 股息率 ∝ 1/PE，用 PE 分位反向作股息率分位代理；PE 本身不再单独计权，避免共线相消
        ms.append(E.mk_metric("股息率分位（PE 分位反向代理）", pe_hist[-E.WINDOW:], False, 60,
                              _src("蛋卷基金 index_eva pe_history"), "", unit="",
                              note=f"真实股息率={det.get('yeild')}，历史股息率序列不可得，用 PE 分位反向代理"))
    if det.get("pb_percentile") is not None:
        ms.append(E.mk_metric_by_pct("PB 分位", det.get("pb"), det.get("pb_percentile"), False, 40,
                                     _src("蛋卷基金 index_eva detail"), "", note="蛋卷口径"))

    macro_ms = []
    hs300 = [r for r in (ctx.get("hs300") or []) if not as_of or r[0] <= as_of]
    if hs300:
        try:
            ratio = E.ratio_series(list(zip(ser["dates"], closes)), hs300)
            if len(ratio) > 250:
                macro_ms.append(E.mk_metric("中证红利 / 沪深300 相对强弱", [x[1] for x in ratio][-E.WINDOW:],
                                            False, 60, _src("东财 000922 ÷ 000300"), "", unit="",
                                            note="红利相对大盘越强，性价比越低"))
        except Exception as e:  # noqa: BLE001
            ctx.setdefault("errors", []).append(f"红利/沪深300: {e}")
    # A 股 10Y 国债收益率暂未接入（中债接口需鉴权）。用沪深300 PE 分位代理「A股整体估值环境」：
    # 大盘越贵，资金越倾向防御性高股息，红利相对越有吸引力 → 方向为正（分位高=分数高）。
    hs_pe = _pe_upto(ctx, "SH000300", as_of)
    if hs_pe:
        macro_ms.append(E.mk_metric(
            "沪深300 PE 分位（A股整体估值环境）", hs_pe[-E.WINDOW:], True, 40,
            _src("蛋卷基金 index_eva pe_history SH000300"), "", unit="",
            note="大盘越贵，资金越倾向高股息防御，红利相对吸引力上升 → 方向为正"))

    dims = [
        E.build_dimension("valuation", cfg["weights"]["valuation"], ms,
                          anchor="中证红利(000922) 指数估值，蛋卷口径"),
        E.build_dimension("trend", cfg["weights"]["trend"],
                          _trend_dims(closes, 50, 50, ser["src"])),
        E.build_dimension("sentiment", cfg["weights"]["sentiment"],
                          _sentiment_dims(closes, ser["amounts"], ser["src"])),
        E.build_dimension("macro", cfg["weights"]["macro"], macro_ms,
                          anchor="A股10Y国债未接入，股债性价比暂用相对沪深300 强弱替代"),
    ]
    r = _out(ser, dims)
    r["fund_meta"] = {"yeild": det.get("yeild"), "pe": det.get("pe"), "pb": det.get("pb")}
    return r


COMPUTERS = {
    "IXIC": compute_ixic,
    "NDX": compute_ndx,
    "GOLD": compute_gold,
    "MSCI_HEALTH": compute_health,
    "CSI_DIVIDEND": compute_dividend,
}
